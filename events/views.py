from utils.errors import generate_exception_comments, log_and_return_error, log_and_return_independent_error,log_and_return_bad_data_write_request

from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions

from dashboards.mixins import ProfileDataMixin, ProfileDataInAPIs

from cassandra.cqlengine.query import BatchQuery

from logger.views import log_a_success
import datetime, sys, dateutil, logging, httplib

from .models import EventsByTime, EventsByError, Events, UserEventAlertsPreferences, AlertManagement
from .serializers import ErrorByTimeValues

import json
from dataglen.models import Sensor
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
import pytz
from .forms import AlertPreferencesForm, EventChoiceForm
from django.views.generic.edit import FormView, UpdateView
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError
from django.core.mail import send_mail
from dashboards.mixins import AddSensorsMixin, EntryPointMixin
from braces.views import JSONResponseMixin
from django.views.generic.base import TemplateView
from dgkafka.views import create_kafka_producers
from kutbill.settings import KAFKA_WRITE, KAFKA_WRITE_TO_HOSTS

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


def get_event_records(identifier,
                      request,
                      key):
    request_arrival_time = timezone.now()
    try:
        source = Sensor.objects.get(sourceKey=key)
    except ObjectDoesNotExist as exception:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        return log_and_return_error(request.user.id, request, request_arrival_time,
                                    settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                    False, comments)
    try:
        try:
            st = request.query_params["startTime"]
            et = request.query_params["endTime"]
            try:
                tz = pytz.timezone(source.dataTimezone)
            except:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.SOURCE_CONFIGURATION_ISSUE, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            # convert into datetime objects
            st = dateutil.parser.parse(st)
            if st.tzinfo is None:
                st = tz.localize(st)
            et = dateutil.parser.parse(et)
            if et.tzinfo is None:
                et = tz.localize(et)

        except Exception as exception:
            logger.debug(exception)
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        event_names = [item for sublist in Events.objects.all().order_by('event_name').values_list('event_name') for item in sublist]
        try:
            event_names_request = request.query_params["eventNames"].split(",")
            event_names_request = [event_name_request.strip().lstrip() for event_name_request in event_names_request]
            for event_name_request in event_names_request:
                assert(event_name_request in event_names)
        except AssertionError as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_EVENT_NAME, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            event_names_request = event_names
        values_final = []
        try:
            source = Sensor.objects.get(sourceKey=identifier)
            name = source.name
            key = source.sourceKey
        except:
            name = None
            key = None

        for event_name in range(len(event_names_request)):
            events = EventsByError.objects.filter(identifier=identifier,
                                                  event_name=event_names_request[event_name],
                                                  insertion_time__gte=st,
                                                  insertion_time__lt=et).limit(0).values_list('insertion_time',
                                                                                              'event_name',
                                                                                              'event_time')

            values = [{'insertion_time': entry[0],
                       'event_name':entry[1],
                       'event_time':entry[2],
                       'source_key':key,
                       'source_name':name} for entry in events]
            values_final.extend(values)

        # TODO add a try catch here..what all can go wrong while converting values into a serializer
        reply = ErrorByTimeValues(data=values_final,
                                  many=True)
        if reply.is_valid():
            response = Response(reply.data,
                                status=status.HTTP_200_OK)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, comments=None)
            return response
        else:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, {})

    except Exception as exception:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        logger.debug(comments)
        return log_and_return_error(request.user.id, request, request_arrival_time,
                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                    False, comments)

    
def events_write(request,
                 request_arrival_time,
                 key):
    try:
        try:
            source = Sensor.objects.get(sourceKey=key,
                                        user=request.user)
        except Sensor.DoesNotExist:
            return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.INVALID_SOURCE_KEY,
                                                    settings.RESPONSE_TYPES.DRF, False,
                                                    {'function_name': sys._getframe().f_code.co_name})

        data = request.data
        data_dumps = json.dumps(data)
        request_dict = json.loads(data_dumps)
        if 'event_time' in request_dict.keys():
            event_time = request_dict['event_time']
            event_time = dateutil.parser.parse(event_time)
        else:
            event_time = request_arrival_time
        if 'event_name' not in request_dict.keys():
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.EVENT_NAME_REQUIRED, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
        else:
            event_name = request_dict['event_name']
        try:
            event_names = [item for sublist in Events.objects.all().order_by('event_name').values_list('event_name') for item in sublist]
            assert(event_name in event_names)
        except AssertionError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_EVENT_NAME, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:
            insertion_time = request_arrival_time
            # astimezone does the conversion and updates the tzinfo part
            insertion_time = insertion_time.astimezone(pytz.timezone(source.dataTimezone))
        except Exception as exc:
            logger.debug(exc)
            # TODO why this UTC timestamp - what errors can come while converting into a different timezone
            insertion_time = timezone.now()
        
        try:
            if event_time.tzinfo is None:
                tz = pytz.timezone(str(source.dataTimezone))
                # localize only adds tzinfo and does not change the dt value
                event_time = tz.localize(event_time)
                logger.debug(event_time)
        except:
            # TODO no errors?
            pass

        if event_time > insertion_time + datetime.timedelta(seconds=60):
            return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                         request_arrival_time,
                                                         settings.ERRORS.FUTURE_TIMESTAMP,
                                                         source)

        # TODO why the USER_ID here? as the keys are always unique. we use ids with slugs.
        identifier = key
        batch_query = BatchQuery()
        EventsByTime.batch(batch_query).create(identifier=identifier,
                                               insertion_time=insertion_time,
                                               event_name=event_name,
                                               event_time=event_time)

        EventsByError.batch(batch_query).create(identifier=identifier,
                                                event_name=event_name,
                                                insertion_time=insertion_time,
                                                event_time=event_time)

        batch_query.execute()

        # ----------------------------------#
        # Calling publish_to_kafka_broker

        if KAFKA_WRITE:
            #logger.debug('Before calling kafka broker function from action_write')
            data_dict_for_kafka = request_dict
            source_key = key
            data_dict_for_kafka['source_key'] = source_key
            data_dict_for_kafka['user_name'] = str(request.user)
            data_dict_for_kafka['source_name'] = str(source.name)
            data_dict_for_kafka['sensor_type'] = Sensor.objects.get(sourceKey=source_key).templateName
            time_stamp_in_dict = data_dict_for_kafka.get("TIMESTAMP",None)
            if not time_stamp_in_dict:
                data_dict_for_kafka["TIMESTAMP"] = event_time
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
                        kafka_producers[iWrite].send_message(topic='event_'+Sensor.objects.get(sourceKey=source_key).templateName,key=source_key,json_msg=data_dict_for_kafka,sync=True)
                    except Exception as ex:
                        logger.debug("exception in event send_message: %s"% str(ex))
                else:
                    logger.debug('kafka_producer is still None')
            #logger.debug('After calling kafka broker function')
            #logger.debug('message sent')

        # TODO send an alert - will this function always succeed/fail silently?
        sendAlerts(identifier,
                   request_arrival_time,
                   event_name, event_time)

        response = HttpResponse("event logged", status=httplib.OK)

        return response

    except Exception as exception:
        logger.debug(str(exception))
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR,
                                                settings.RESPONSE_TYPES.DRF, False,
                                                comments)


def sendAlerts(identifier,
               request_arrival_time,
               event_name, event_time):
    try:
        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=identifier,
                                                                  event=event,
                                                                  alert_active=True)

        for alert in active_alerts:
            logger.debug("inside for")
            email = alert.email_id
            alert_interval = alert.alert_interval
            last_alert_time = AlertManagement.objects.filter(identifier=identifier,
                                                             event=event,
                                                             email_id=email).order_by("-alert_time")
            if len(last_alert_time) > 0:
                if last_alert_time[0].alert_time + datetime.timedelta(minutes=alert_interval) < request_arrival_time:
                    logger.debug("inside if")
                    try:
                        new_alert = AlertManagement(identifier=identifier,
                                                    alert_time=request_arrival_time,
                                                    event_time=event_time,
                                                    event=event,
                                                    email_id=email)
                        new_alert.save()

                        send_mail(event_name + ' occurred on dataglen.com',
                                  event.description, 'admin@dataglen.com',
                                  [email], fail_silently=False)
                    except IntegrityError:
                        return HttpResponseBadRequest("Error in saving new alerts")
            else:
                logger.debug("inside else")
                try:
                    new_alert = AlertManagement(identifier=identifier,
                                                alert_time=request_arrival_time,
                                                event_time=event_time,
                                                event=event,
                                                email_id=email)
                    new_alert.save()
                    try:
                        send_mail(event_name + ' occurred on dataglen.com',
                                event.description, 'admin@dataglen.com',
                                [email], fail_silently=False)
                    except:
                        logger.debug("Error in sending email")
                except IntegrityError:
                    return HttpResponseBadRequest("Error in saving new alerts")
    except Exception as exception:
        logger.debug(str(exception))
        return 0


class EventsViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication,
                              authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, source_key=None, **kwargs):
        request_arrival_time = timezone.now()
        return events_write(request, request_arrival_time, source_key)

    def list(self, request, source_key=None, **kwargs):
        return get_event_records(source_key, request, source_key)


class AlertPreferencesAdd(EntryPointMixin, AddSensorsMixin, FormView):
    #template_name = 'events/alert_preferences.html'
    form_class = EventChoiceForm

    def get_success_url(self):
        return reverse_lazy('events:list-alert-preferences', kwargs={'source_key': self.kwargs.get('source_key')})

    def form_valid(self, form, *args, **kwargs):
        try:
            event = get_object_or_404(Events, event_name=form.cleaned_data['Event'])
            preference = form.save(commit=False)
            preference.identifier = str(self.kwargs.get('source_key'))
            preference.event = event
            preference.save()
            return super(AlertPreferencesAdd, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("Alerts for this event have already been set for the same "
                                          "email-id and phone no. Please use a different email-id or phone no.")
        except Exception as exception:
            logger.debug(str(exception))
            return HttpResponseServerError("Something went wrong, please contact us at contact@datalen.com")


class ListPreferencesView(EntryPointMixin, AddSensorsMixin,
                          JSONResponseMixin, TemplateView):
    template_name = "events/list_preferences.html"

    def get(self, request, *args, **kwargs):
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'),
                                        user=request.user)
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(ListPreferencesView, self).get_context_data(**kwargs)
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'),
                                        user=self.request.user)
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404

        identifier = str(self.kwargs.get('source_key'))
        preferences = UserEventAlertsPreferences.objects.filter(identifier=identifier).order_by('event_id')

        context['preferences'] = preferences
        context['source'] = source

        return context


class UpdatePreferences(UpdateView):
    template_name = "events/preference_update.html"
    form_class = AlertPreferencesForm
    model = UserEventAlertsPreferences
    slug_url_kwarg = 'preference_id'
    slug_field = 'id'

    def get_success_url(self):
        return reverse_lazy('events:list-alert-preferences', kwargs={'source_key': self.kwargs.get('source_key')})
