from django.shortcuts import render
from ioelab.models import ValidUID,Invite
from ioelab.serializers import ValidUIDSerializer,InviteSerializer
from django.views.generic.edit import CreateView, FormView, UpdateView
from ioelab.forms import ValidateUIDForm
from action.models import ActionField
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.http import QueryDict
from logger.views import log_a_success, log_an_error
from utils.errors import log_and_return_error
from django.utils import timezone
from django.conf import settings
from utils.errors import generate_exception_comments
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework import authentication, permissions
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets
import sys, logging, dateutil
from dataglen.models import Sensor, Field
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
from dashboards.utils import create_a_group, delete_a_group, add_a_sensor, remove_a_sensor, add_a_member, remove_a_member
from dashboards.models import Dashboard,DataglenClient,DataglenGroup
from django.core.urlresolvers import reverse_lazy
from cassandra.cqlengine.query import BatchQuery
from config.models import ConfigStorageByStream, ConfigField
from django.contrib.sites.models import Site

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


'''class InviteList(generics.ListCreateAPIView):
    queryset = Invite.objects.all()
    serializer_class = InviteSerializer


class InviteDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invite.objects.all()
    serializer_class = InviteSerializer
    '''

class InviteViewSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def list(self, request):

        request_arrival_time = timezone.now()
        invites = Invite.objects.filter(invitee=request.user)
        serializer = InviteSerializer(invites, many=True)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        log_a_success(request.user.id, request, response.status_code,
                                                      request_arrival_time)
        return response

    def retrieve(self, request, id=None):

        request_arrival_time = timezone.now()
        try:
            invite = Invite.objects.get(invitee=request.user,id=id)
            serializer = InviteSerializer(invite)
            response = Response(serializer.data, status=status.HTTP_200_OK)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return ##log_and_return_error(request.user.id, request,request_arrival_time, settings.ERRORS.INVALID_SOURCE_KEY,
                                                                        #settings.RESPONSE_TYPES.DRF, False,
                                                                        #comments, source_key=key)
        # check for broad errors (ones we don't know yet)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return ##log_and_return_error(request.user.id, request,request_arrival_time, settings.ERRORS.INTERNAL_SERVER_ERROR,
                                                                                    #settings.RESPONSE_TYPES.DRF, False,
                                                                                    #comments, source_key=key)

    def create(self, request):

        request_arrival_time = timezone.now()
        try:
            serializer = InviteSerializer(data=request.data)
            ###
            #response = Response("serializer initialized" , status=status.HTTP_409_CONFLICT)
            #return response
            dataglenclient_name = "RS_IOELab"
            dataglenclient_email = "ioelabs@radiostudio.biz"
            if serializer.is_valid():
                try:
                    user_exists = False
                    sensor_UID_match = True
                    emailid = request.data["emailid"]
                    # check if user has already registered
                    u = User.objects.filter(email=emailid).count()
                    if u != 0:
                        user_exists = True
                        #send_mail("device added")
                        #response = Response({"detail":"User with this emailid already exists."}, status=status.HTTP_409_CONFLICT)
                        #return response
                    else:
                        user_exists = False
                except ObjectDoesNotExist:
                    user_exists = False
                except :
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    logger.debug(comments)
                    response = Response(comments, status=status.HTTP_400_BAD_REQUEST)
                    log_an_error(request.user.id, request, str(serializer.errors), response.status_code,settings.ERRORS.ERROR_NONMATCHING_STREAMS_UID_OWNER.description, request_arrival_time, False)
                    e = sys.exc_info()[0]
                    return response
                try:
                    #if default_load TRUE, do not check if the device belongs to the requesting user.
                    #default_load = request.POST.get('default_load', False)
                    default_load = serializer.validated_data.get('default_load', False)
                    if default_load:
                        if request.user.email == dataglenclient_email:
                            sensor_count = Sensor.objects.filter(sourceKey=request.data["source"],name=request.data["UID"]).count()
                        else:
                            sensor_count = 0
                    else:
                        #source key and UID do not match or belong to you.
                        sensor_count = Sensor.objects.filter(user=request.user,sourceKey=request.data["source"],name=request.data["UID"]).count()
                    if sensor_count == 1:
                        sensor_UID_match = True
                    else:
                        sensor_UID_match = False
                    ###
                    #response = Response("after source key:" +str(sensor_UID_match) , status=status.HTTP_409_CONFLICT)
                    #return response
                except ObjectDoesNotExist:
                    sensor_UID_match = False
                except :
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    logger.debug(comments)
                    response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    log_an_error(request.user.id, request, str(serializer.errors), response.status_code,settings.ERRORS.ERROR_NONMATCHING_STREAMS_UID_OWNER.description, request_arrival_time, False)
                    e = sys.exc_info()[0]
                    return response
                
                if sensor_UID_match == False:
                    message = "Source and UID do not match with each other, or the device belongs to some other user."
                    response = Response(message, status=status.HTTP_409_CONFLICT)
                    return response
                else:
                    #apply template and activate the device
                    sensor = Sensor.objects.get(sourceKey=request.data["source"])

                    #create a group for new UID if it does not already exists. Add this sensor to the new group #,groupClient=dataglenclient_name
                    existing_group_count = DataglenGroup.objects.filter(name=request.data["UID"]).count()
                    #response = Response("existing_group_count" + str(existing_group_count) , status=status.HTTP_409_CONFLICT)
                    #return response
                    if existing_group_count==0:
                        #add new group and add new sensor
                        new_group = create_a_group(dataglenclient_name, dataglenclient_email,
                                            request.data["UID"], True, [])

                    #response = Response("new group created", status=status.HTTP_409_CONFLICT)
                    #return response

                    if user_exists == True:
                        send_mail('A new device is added to your DataGlen account!', 'A new device is added to your DataGlen account.\n Request you to login to http://'+ Site.objects.get_current().domain +'/dataglen/dashboard and  navigate to Data Sources -> Pending Sources to validate the device.\n Thanks\n Team DataGlen', dataglenclient_email,[request.data["emailid"].strip()], fail_silently=False)

                    else:
                        #invite new user as a member to the new_group
                        add_a_member(request.data["UID"], request.data["emailid"].strip(), False)
                        #send_mail('You have been invited to join DataGlen!', 'Hi, You have been invited to join dataglen.com. Request you to signup at http://www.dataglen.com and verify the device added to your account providing the device UID.', 'admin@dataglen.com',[request.data["emailid"].strip()], fail_silently=False)

                    #TODO: add appropriate template on the server if the application switched to different server
                    template_name = 'RS_IOELabKit'
                    # look for template
                    template = Sensor.objects.get(isTemplate=True,name=template_name)

                    # copy fields
                    fields = Field.objects.filter(source=template)
                    # copy all the fields
                    for field in fields:
                        existing_field_count = Field.objects.filter(source = sensor,name=field.name).count()
                        if existing_field_count == 0:
                            new_field = Field()
                            new_field.source = sensor
                            new_field.name = field.name
                            new_field.streamDataType = field.streamDataType
                            new_field.streamPositionInCSV = field.streamPositionInCSV
                            new_field.streamDataUnit = field.streamDataUnit
                            new_field.streamDateTimeFormat = field.streamDateTimeFormat
                            # save the field
                            new_field.save()

                    #response = Response("after fields added:" , status=status.HTTP_409_CONFLICT)
                    #return response
                    # copy action fields
                    actionfields = ActionField.objects.filter(source=template)
                    # copy all the fields
                    for field in actionfields:
                        existing_field_count = ActionField.objects.filter(source = sensor,name=field.name).count()
                        if existing_field_count == 0:
                            new_field = ActionField()
                            new_field.source = sensor
                            new_field.name = field.name
                            new_field.streamDataType = field.streamDataType
                            new_field.streamPositionInCSV = field.streamPositionInCSV
                            new_field.streamDataUnit = field.streamDataUnit
                            new_field.streamDateTimeFormat = field.streamDateTimeFormat
                            # save the field
                            new_field.save()

                    # copy config fields
                    configfields = ConfigField.objects.filter(source=template)
                    # copy all the fields
                    for field in configfields:
                        existing_field_count = ConfigField.objects.filter(source = sensor,name=field.name).count()
                        if existing_field_count == 0:
                            new_field = ConfigField()
                            new_field.source = sensor
                            new_field.name = field.name
                            new_field.streamDataType = field.streamDataType
                            new_field.streamPositionInCSV = field.streamPositionInCSV
                            new_field.streamDataUnit = field.streamDataUnit
                            new_field.streamDateTimeFormat = field.streamDateTimeFormat
                            # save the field
                            new_field.save()

                    # update the sensor details

                    sensor.templateName = template.templateName
                    sensor.textMessageWithHTTP200 = template.textMessageWithHTTP200
                    sensor.textMessageWithError = template.textMessageWithError
                    sensor.csvDataKeyName = template.csvDataKeyName
                    #sensor.IsActive = 1
                    #response = Response("update Isactive",status=status.HTTP_409_CONFLICT)
                    #return response
                    #sensor.IsMonitored = template.IsMonitored
                    # TODO: IsActive and IsMonitored not working from code

                    sensor.save()

                    #delete the existng invites with the same emailid, source and UID, if exists
                    try:
                        invite_count = Invite.objects.filter(UID=serializer.validated_data.get("UID",""),
                                            emailid=serializer.validated_data.get("emailid","")).count()
                        #response = Response(str(invite_count) + " "+serializer.validated_data.get("UID","") +" "+serializer.validated_data.get("emailid",""), status=status.HTTP_400_BAD_REQUEST)
                        #return response
                        if invite_count == 1:
                            invite = Invite.objects.get(UID=serializer.validated_data.get("UID",""),
                                            emailid=serializer.validated_data.get("emailid",""))
                            invite.delete()
                    except Exception as e:
                        response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
                        return response

                    serializer.save(invitee=request.user)
                    response = Response(serializer.data, status=status.HTTP_201_CREATED)
                    log_a_success(request.user.id, request, response.status_code,
                                                  request_arrival_time, comments={'response': serializer.data})
                    return response
                

                #emailid = request.data["emailid"]
                # check if user has already registered
                #try:
                #    registered_users =
                    # check if user invitation already sent
                    # check if the device belongs to some other user

            else:
                if len(serializer.errors.keys())==1 and serializer.errors.has_key('non_field_errors'):
                    try:
                        invite_count = Invite.objects.filter(UID=request.data["UID"],
                                            emailid=request.data["emailid"],
                                            status=0).count()
                        if invite_count == 1:
                            invite = Invite.objects.get(UID=request.data["UID"],
                                            emailid=request.data["emailid"],
                                            status=0)
                            serializer = InviteSerializer(invite)
                            response = Response(serializer.data, status=status.HTTP_201_CREATED)
                            return response
                        else:
                            response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            log_an_error(request.user.id, request, str(serializer.errors), response.status_code,settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                            return response

                    except Exception as e:
                        response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
                        return response
                else:
                    response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    log_an_error(request.user.id, request, str(serializer.errors), response.status_code,settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                    return response
        except IntegrityError:
            try:
                invite_count = Invite.objects.filter(UID=request.data["UID"],
                                            emailid=request.data["emailid"],
                                            status=0).count()
                if invite_count == 1:
                    invite = Invite.objects.get(UID=request.data["UID"],
                                            emailid=request.data["emailid"],
                                            status=0)
                    serializer = InviteSerializer(invite)
                    response = Response(serializer.data, status=status.HTTP_201_CREATED)
                    return response

            except Exception as e:
                response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
                return response

        except Exception as e:
            response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            return response






    def delete(self, request, pk=None):
        request_arrival_time = timezone.now()
        try:
            UID = request.data["UID"]
            emailid = request.data["emailid"]
            invite = Invite.objects.get(UID=UID,
                                        emailid=emailid, status=0)
            invite.delete()
            response = Response(status=status.HTTP_204_NO_CONTENT)
            return response

        # check for broad errors (ones we don't expect)
        except Exception as exception:
            response = Response('Bad request - '+str(exception), status=status.HTTP_400_BAD_REQUEST)
            return response

class ValidateUIDView(FormView):
    template_name = "ioelab/validate_UID.html"
    form_class = ValidateUIDForm
    
    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.key})
    
    def form_valid(self, form):
        try:
            #validate_UID = form.save(commit=False)
            #If the UID and user email id is not present in the Invites with status =0, raise an error, else redirect to sources page

            if self.request.user.is_authenticated:
                user_email = self.request.user.email
                count_Invites = Invite.objects.filter(emailid=user_email,UID=form.cleaned_data['UID'],status=0).count()
                if count_Invites>0:
                    selected_invite = Invite.objects.get(emailid=user_email,UID=form.cleaned_data['UID'],status=0)
                    self.key = selected_invite.source.sourceKey
                    #add user to UID group and assign ownership of the sensor to the user
                    #TODO add IOELab template, user and client IDs in configuration file
                    existing_group_count = DataglenGroup.objects.filter(name=form.cleaned_data['UID']).count()
                    dataglenclient_name = "RS_IOELab"
                    dataglenclient_email = "ioelabs@radiostudio.biz"
                    dataglenclient_user = User.objects.get(email=dataglenclient_email)

                    if user_email != dataglenclient_email:
                        #check if the current device belongs to vendor account or else ask to de-register from the existing user first.
                        try:
                            sensor = Sensor.objects.get(sourceKey=selected_invite.source.sourceKey,user=dataglenclient_user)
                        except ObjectDoesNotExist:
                            try:
                                sensor = Sensor.objects.get(sourceKey=selected_invite.source.sourceKey,user=self.request.user)
                            except ObjectDoesNotExist:
                                return HttpResponseBadRequest("This source is already owned by you. No further action required.")
                            return HttpResponseBadRequest("This source is currently owned by some other user. Please de-register the source from existing owner account and try it again.")

                    if existing_group_count==0:
                        #add new group and add new sensor
                        new_group = create_a_group(dataglenclient_name, dataglenclient_email,
                                            form.cleaned_data['UID'], True, [])
                    try:
                        add_a_member(form.cleaned_data['UID'], user_email, False)
                    except:
                        #if member already exists as a group-member, then pass
                        pass


                    sensor = Sensor.objects.get(sourceKey=selected_invite.source.sourceKey)
                    sensor.user = self.request.user
                    sensor.save()

                    try:
                        #if sensor is already part of group sensors, pass
                        if user_email != dataglenclient_email: #if the current user is the client, then dont add sensor to the group sensors, since we do not want the user to start seeing the sensor immediately.
                            add_a_sensor(form.cleaned_data['UID'],sensor)
                    except:
                        pass
                    
                    #Make required changes to set the configuration flag 1 in data response and adding to configuration OWNERSHIP_CHANGE
                    try:
                        new_API_key = Token.objects.get(user=self.request.user)
                        batch_query = BatchQuery()
                        ConfigStorageByStream.batch(batch_query).create(source_key=sensor.sourceKey,
                                                                       stream_name='OWNERSHIP_CHANGE',
                                                                       insertion_time=timezone.now(),
                                                                       stream_value=str(new_API_key),
                                                                       acknowledgement=0,
                                                                       comments='')

                        batch_query.execute()
                    except:
                        return HttpResponseBadRequest("Error while creating configuration change")
                    #change the status of invite to 1
                    selected_invite.status = 1
                    selected_invite.save()
                    return super(ValidateUIDView, self).form_valid(form)
                else:
                    return HttpResponseBadRequest("Invalid UID")
        except IntegrityError as e:
            return HttpResponseBadRequest("IntegrityError - Invalid UID :" + str(e))

        except Exception as e:
            return HttpResponseServerError("Sorry, something went wrong, please try again later." + str(e))