from dataglen.models import Sensor, Field
from action.models import ActionField, ActionsStorageByStream
from .serializers import SourceActionValues,StreamActionValues,ActionFieldSerializer,AcknowledgmentActionValues
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.http import QueryDict
import json, datetime
from rest_framework.parsers import JSONParser

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
from dataglen.models import ValidDataStorageByStream
from dataglen.data_views import data_write
from logger.views import log_a_success
from utils.errors import log_and_return_error, log_and_return_independent_error, \
    log_and_return_bad_data_write_request, \
    generate_exception_comments
from cassandra.cqlengine.query import BatchQuery
from dateutil import parser

from dashboards.mixins import AddSensorsMixin, EntryPointMixin, ProfileDataMixin
from django.views.generic.edit import CreateView, FormView, UpdateView
from action.forms import ActionFieldForm
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse_lazy
import pytz
from dgkafka.views import create_kafka_producers
from kutbill.settings import KAFKA_WRITE, KAFKA_WRITE_TO_HOSTS
from dgkafka.settings import kafka_producers

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

# Create your views here.
class ActionRecordsSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication,authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (JSONParser,)
    lookup_field = "action"

    #def partial_update(self, request, source_key=None): #Modified to PATCH since ViewSet does not support partial_update()
    def patch(self, request, source_key=None):
        """
            Update pending action records for a given source by providing acknowledgement
            ---
            request_serializer: AcknowledgmentActionValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format.(BAD_REQUEST).
                - code : 401
                  message : Not authenticated
        """
        try:
            request_arrival_time = timezone.now()
            data = request.data
            serializer = AcknowledgmentActionValues(data=data)
            if serializer.is_valid():
                try:
                    #check if the current user has permission to perform actuation
                    source = Sensor.objects.get(sourceKey=source_key,user=request.user)
                except Sensor.DoesNotExist:
                    # Key not found
                    return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.INVALID_SOURCE_KEY,
                                                    settings.RESPONSE_TYPES.DRF, False,
                                                    {'function_name': sys._getframe().f_code.co_name})

                invalid_arguments = False
                acknowledgement_value = serializer.validated_data.get('acknowledgement', 0)
                insertionTime_value = serializer.validated_data.get('insertionTime', None)
                if insertionTime_value:
                    insertionTime_value = dateutil.parser.parse(insertionTime_value)
                comments = serializer.validated_data.get('comments', '')

                '''
                if acknowledgement_value == 2 or acknowledgement_value == 3:
                    if comments == '':
                        response = Response('If the acknowledgement status is 2 or 3, comments field cannot be blank', status=status.HTTP_400_BAD_REQUEST)
                        return response
                '''
                if  invalid_arguments or  insertionTime_value == None or acknowledgement_value == 0:
                    response = Response('Invalid arguments', status=status.HTTP_400_BAD_REQUEST)
                    return response

                action_fields_values = ActionField.objects.filter(source=source).values_list('name')
                action_fields_names = [item[0] for item in action_fields_values]
                for action_fields_name in action_fields_names:

                    action_len = ActionsStorageByStream.objects.filter(source_key=source_key,acknowledgement=0,stream_name=action_fields_name,insertion_time__lte=insertionTime_value).count()
                    if action_len > 0:

                        #delete objects and recreate with appropriate acknowledgement
                        action_data = ActionsStorageByStream.objects.filter(source_key=source_key,acknowledgement=0,stream_name=action_fields_name,insertion_time__lte=insertionTime_value).limit(0).values_list('stream_name','stream_value', 'insertion_time')

                        stream_names = [item[0] for item in action_data]
                        stream_values = [item[1] for item in action_data]
                        insertion_times = [item[2] for item in action_data]

                        for iAction in range(0,action_len):
                            batch_query = BatchQuery()
                            actions = ActionsStorageByStream.objects.filter(source_key=source_key,acknowledgement=0,stream_name=action_fields_name,insertion_time=insertion_times[iAction])
                            actions.batch(batch_query).delete()
                            batch_query.execute()

                        set_acknowledgement = 1
                        comments_value =''
                        if acknowledgement_value == 2:
                            bad_streams = comments.split(',')
                            if action_fields_name in bad_streams:
                                set_acknowledgement = 2
                                comments_value = 'Invalid action'
                        if acknowledgement_value == 3:
                            set_acknowledgement = 3
                            comments_value = comments


                        for iAction in range(0,action_len):
                            batch_query = BatchQuery()
                            ActionsStorageByStream.batch(batch_query).create(source_key=source_key,
                                                                       stream_name=stream_names[iAction],
                                                                       insertion_time=insertion_times[iAction],
                                                                       stream_value=str(stream_values[iAction]),
                                                                       acknowledgement=set_acknowledgement,
                                                                       comments=comments_value)

                            batch_query.execute()

                response = Response('Acknowledgement received successfully', status=status.HTTP_200_OK)
                return response
                #TODO set appropriate stream with negative acknowledgement
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                return response

        except Exception as e:
            response = Response(str(e), status=status.HTTP_409_CONFLICT)
            return response


    def list(self, request, source_key=None):
        """
            Get a list of pending actions for a given source.
            ---
            response_serializer: SourceActionValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned in invalid (INVALID_SOURCE_KEY) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format.(BAD_REQUEST)
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key, user=request.user)
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:

            action_len = None
            streams_action_dicts = []

            action_len = ActionsStorageByStream.objects.filter(source_key=source_key,acknowledgement=0).count()

            if action_len > 0:
                action_data = ActionsStorageByStream.objects.filter(source_key=source_key,
                                                                          acknowledgement=0
                                                                          ).limit(0).values_list('stream_name','stream_value', 'insertion_time')
                # populate data
                raw_stream_names = [item[0] for item in action_data]
                raw_stream_values = [item[1] for item in action_data]

                # populate timestamps
                raw_insertion_times = [item[2] for item in action_data]
                #check if the same stream name has received multiple values

                seen = set()
                stream_names = []
                stream_values = []
                insertion_times = []

                for iAction in range(0,action_len):
                    current_steam_name = raw_stream_names[iAction]
                    if current_steam_name not in seen:
                        stream_names.append(current_steam_name)
                        seen.add(current_steam_name)
                        stream_values.append(raw_stream_values[iAction])
                        insertion_times.append(raw_insertion_times[iAction])
                    else:
                        try:
                            old_iAction = stream_names.index(current_steam_name)
                        except Exception as e:
                            response = Response('current stream not found' + str(e), status=status.HTTP_409_CONFLICT)
                            return response
                        if  raw_insertion_times[iAction] > insertion_times[old_iAction]:
                            insertion_times[old_iAction] = raw_insertion_times[iAction]
                            stream_values[old_iAction] = raw_stream_values[iAction]

                latest_intertiontime = max(insertion_times)
                #latest_intertiontime_str = latest_intertiontime.isoformat()

                #TODO if the same stream name with acknowledgement 0 appears multiple times, set the latest value

                for iAction in range(0,len(stream_names)):
                    streams_action_dicts.append({'name': stream_names[iAction],
                                               'value': stream_values[iAction]})

                reply = SourceActionValues(data={'sourceKey': source_key,
                                           'insertionTime': latest_intertiontime,
                                           'streams': streams_action_dicts})

                if reply.is_valid():
                    response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                    log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments=None)
                    return response
                else:
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            else:
                try:
                    reply = SourceActionValues(data={'sourceKey': source_key,
                                           'insertionTime': timezone.now(),
                                           'streams': []})
                    if reply.is_valid():
                        response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                        log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments=None)
                        return response
                    else:
                        comments = reply.errors
                        #TODO: Create appropriate aerror codes
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
                except Exception as e:
                    response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
                    return response
        except Exception as exception:
                response = Response(str(exception), status=status.HTTP_400_BAD_REQUEST)
                return response
                '''
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
                '''


    def create(self, request, source_key=None):
        """
            Write a new action record. Payload should be in the semantics as specified in the sensor configuration.
            ---
            parameters:
                - name : body
                  type: body
                  required: True
                  description: Actual body.
                  paramType: body
            responseMessages:
                - code : 201
                  message : Success. New action has been written into the database.
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If any of the essential parameters are missing/invalid (BAD_REQUEST) or
                            If there is an error retrieving the payload (ERROR_RETRIEVING_PAYLOAD) or
                            If there is an error splitting multiple records (ERROR_SPLITTING_RECORDS) or
                            If there is an error in parsing multiple action streams (ERROR_SPLITTING_STREAMS) or
                            If the data provided in the request body is not proper as per the data units of streams (INVALID_DATA).
                - code : 401
                  message : Not authenticated
        """

        request_arrival_time = timezone.now()
        try:

            return action_write(request,
                              request_arrival_time,
                              source_key,
                              settings.RESPONSE_TYPES.DRF)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)





def json_action_type_validation(action_field, action_value):
    try:
        if action_field.streamDataType == "INTEGER":
            assert(type(action_value) is int)
            updated_value = action_value
        elif action_field.streamDataType == "BOOLEAN":
            assert(action_value == 0 or action_value == 1)
            updated_value = action_value
        elif action_field.streamDataType == "FLOAT":
            assert(type(action_value) is float)
            updated_value = action_value
        elif action_field.streamDataType == "LONG":
            assert(type(action_value) is long)
            updated_value = action_value
        elif action_field.streamDataType == "STRING" or action_field.streamDataType == "MAC":
            assert(type(action_value) is unicode)
            updated_value = action_value
        elif action_field.streamDataType == "TIMESTAMP":
            assert(type(action_value) is unicode)
            if action_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(action_value), str(action_field.streamDateTimeFormat))
            else:
                updated_value = parser.parse(str(action_value))
        elif action_field.streamDataType == "DATE":
            assert(type(action_value) is unicode)
            if action_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(action_value), str(action_field.streamDateTimeFormat)).date()
            else:
                updated_value = parser.parse(str(action_value)).date()
        elif action_field.streamDataType == "TIME":
            assert(type(action_value) is unicode)
            if action_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(action_value), str(action_field.streamDateTimeFormat)).time()
            else:
                updated_value = parser.parse(str(action_value)).time()
        else:
            return None, False

        return updated_value, True

    except Exception as E:
        return None, False


def action_write(request, request_arrival_time, source_key, response_type):
    try:
        try:
            # TODO check the user for source
            source = Sensor.objects.get(sourceKey=source_key,user=request.user)
        except Sensor.DoesNotExist:
            # Key not found
            return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.INVALID_SOURCE_KEY,
                                                    response_type, False,
                                                    {'function_name': sys._getframe().f_code.co_name})


        action_fields = ActionField.objects.filter(source=source)

        # get the payload
        try:
            payload = request.data
        except Exception as e:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR,
                                                response_type, False,
                                                comments)

        #change action error logs and messages

        if payload is None:
            return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                         request_arrival_time,
                                                         settings.ERRORS.ERROR_RETRIEVING_PAYLOAD,
                                                         source)
        # check for multiple entries and split
        action_values_list = payload
        # parse entries, error in parsing even a single one will return an error
        n_entries = 0
        stream_data_tuples = []
        extracted_timestamp_from_action = {}
        action_data_dict = dict()
        for action_field_key, action_field_value in payload.items():
            # split single entry into multiple fields
            if action_field_value is None:
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                             request_arrival_time,
                                                             settings.ERRORS.ERROR_SPLITTING_STREAMS,
                                                             source)
            #check the datatypes match and if the given stream name is valid ActionField
            action_field_valid_count = ActionField.objects.filter(source=source,name=action_field_key).count()
            if action_field_valid_count == 0:
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                                 request_arrival_time,
                                                                 settings.ERRORS.INVALID_DATA,
                                                                 source)
            else:
                stream_instance = ActionField.objects.get(source=source,name=action_field_key)
                updated_value, validation_output = json_action_type_validation(stream_instance,
                                                                               action_field_value)

            if validation_output is True:
                stream_data_tuples.append((action_field_key.strip(), str(updated_value)))
                action_data_dict[stream_instance.name] = updated_value
                if stream_instance.streamDataType in ("TIMESTAMP", "DATE", "TIME"):
                    # It's a datetime/date/time field
                    # keep as a datetime object for ts field of the entry
                    extracted_timestamp_from_action[stream_instance.streamDataType] = updated_value
            else:
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                             request_arrival_time,
                                                             settings.ERRORS.STREAM_PARSING_FAILED,
                                                             source)
            n_entries += 1

        insertion_time = timezone.now()

        # Now populate the database - create a Batch Request

        # add action streams
        for stream in stream_data_tuples:
            #Open bug on cassandra - https://datastax-oss.atlassian.net/browse/PYTHON-445
            batch_query = BatchQuery()
            ActionsStorageByStream.batch(batch_query).create(source_key=source_key,
                                                                   stream_name=stream[0],
                                                                   insertion_time=insertion_time,
                                                                   stream_value=str(stream[1]),
                                                                   acknowledgement=0,
                                                                   comments='')

            batch_query.execute()

        try:
            insertion_time = timezone.now()
            # astimezone does the conversion and updates the tzinfo part
            insertion_time = insertion_time.astimezone(pytz.timezone(source.dataTimezone))
        except Exception as exc:
            insertion_time = timezone.now()
        try:
            timestamp_in_action = extracted_timestamp_from_action["TIMESTAMP"]
        except KeyError:
            try:
                timestamp_in_action = datetime.datetime.combine(extracted_timestamp_from_action["DATE"],
                                                                extracted_timestamp_from_action["TIME"])
            except:
                timestamp_in_action = insertion_time

        # add tzinfo info in timestamp_in_data if absent
        try:
            if timestamp_in_action.tzinfo is None:
                tz = pytz.timezone(str(source.dataTimezone))
                # localize only adds tzinfo and does not change the dt value
                timestamp_in_action = tz.localize(timestamp_in_action)
        except:
            pass

        # ----------------------------------#
        # Calling publish_to_kafka_broker

        if KAFKA_WRITE:
            #logger.debug('Before calling kafka broker function')
            data_dict_for_kafka = action_data_dict
            data_dict_for_kafka['source_key'] = source_key
            data_dict_for_kafka['user_name'] = str(request.user)
            data_dict_for_kafka['source_name'] = str(source.name)
            data_dict_for_kafka['sensor_type'] = Sensor.objects.get(sourceKey=source_key).templateName
            time_stamp_in_dict = data_dict_for_kafka.get("TIMESTAMP",None)
            if not time_stamp_in_dict:
                data_dict_for_kafka["TIMESTAMP"] = timestamp_in_action
            global kafka_producers
            if not kafka_producers:
                try:
                    kafka_producers = create_kafka_producers()
                    #logger.debug('Created kafka producer from action_write')
                except Exception as ex:
                    logger.debug("exception in create_kafka: %s"% str(ex))
            for iWrite in range(len(kafka_producers)):
                if KAFKA_WRITE_TO_HOSTS[iWrite] and kafka_producers[iWrite]:
                    try:
                        kafka_producers[iWrite].send_message(topic='action_'+Sensor.objects.get(sourceKey=source_key).templateName,key=source_key,json_msg=data_dict_for_kafka,sync=True)
                    except Exception as ex:
                        logger.debug("exception in action send_message: %s"% str(ex))
                else:
                    logger.debug('kafka_producer is still None')
            #logger.debug('After calling kafka broker function')
            #logger.debug('message sent')

    # actions has been saved, send a response back
        response = Response("Action Created",status=status.HTTP_201_CREATED)
        log_a_success(source.user.id, request, response.status_code,
                      request_arrival_time, source_key=source.sourceKey)

        return response
    except:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR,
                                                response_type, False,
                                                comments)
    '''
    except Exception as e:
            response = Response(str(e), status=status.HTTP_409_CONFLICT)
            return response
    '''


class ActionStreamCreateView(EntryPointMixin, AddSensorsMixin, CreateView):
    form_class = ActionFieldForm
    template_name = "action/add_action_stream.html"

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.kwargs.get('source_key')})

    def form_valid(self, form):
        try:
            source = get_object_or_404(Sensor, isTemplate=False, sourceKey = self.kwargs.get('source_key'))
            new_action_stream = form.save(commit=False)
            new_action_stream.source = source
            new_action_stream.save()
            return super(ActionStreamCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The stream name should be unique.")
        except Exception as exception:
            raise Http404()
