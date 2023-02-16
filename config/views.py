from dataglen.models import Sensor, Field
from config.models import ConfigField, ConfigStorageByStream
from .serializers import SourceConfigValues,StreamConfigValues,ConfigFieldSerializer,AcknowledgmentConfigValues
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
from config.forms import ConfigFieldForm
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
class ConfigRecordsSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication,authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (JSONParser,)
    lookup_field = "config"

    #def partial_update(self, request, source_key=None): #Modified to PATCH since ViewSet does not support partial_update()
    def patch(self, request, source_key=None):
        """
            Update pending config records for a given source by providing acknowledgement
            ---
            request_serializer: AcknowledgmentConfigValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned in invalid (INVALID_SOURCE_KEY) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST).
                - code : 401
                  message : Not authenticated
        """
        try:
            request_arrival_time = timezone.now()
            serializer = AcknowledgmentConfigValues(data=request.data)
            if serializer.is_valid():
                try:

                    #specifically modified to exclude user check since it would not exceuted in case of OWNERSHIP_CHANGE
                    source = Sensor.objects.get(sourceKey=source_key)
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

                config_fields_values = ConfigField.objects.filter(source=source).values_list('name')
                config_fields_names = [item[0] for item in config_fields_values]
                for config_fields_name in config_fields_names:

                    config_len = ConfigStorageByStream.objects.filter(source_key=source_key,acknowledgement=0,stream_name=config_fields_name,insertion_time__lte=insertionTime_value).count()
                    #response = Response("config_len > 0" +str(insertionTime_value), status=status.HTTP_409_CONFLICT)
                    #return response
                    if config_len > 0:

                        #delete objects and recreate with appropriate acknowledgement
                        config_data = ConfigStorageByStream.objects.filter(source_key=source_key,acknowledgement=0,stream_name=config_fields_name,insertion_time__lte=insertionTime_value).limit(0).values_list('stream_name','stream_value', 'insertion_time')

                        stream_names = [item[0] for item in config_data]
                        stream_values = [item[1] for item in config_data]
                        insertion_times = [item[2] for item in config_data]

                        for iConfig in range(0,config_len):
                            batch_query = BatchQuery()
                            configs = ConfigStorageByStream.objects.filter(source_key=source_key,acknowledgement=0,stream_name=config_fields_name,insertion_time=insertion_times[iConfig])
                            configs.batch(batch_query).delete()
                            batch_query.execute()

                        set_acknowledgement = 1
                        comments_value =''
                        if acknowledgement_value == 2:
                            bad_streams = comments.split(',')
                            if config_fields_name in bad_streams:
                                set_acknowledgement = 2
                                comments_value = 'Invalid config'
                        if acknowledgement_value == 3:
                            set_acknowledgement = 3
                            comments_value = comments


                        for iConfig in range(0,config_len):
                            batch_query = BatchQuery()
                            ConfigStorageByStream.batch(batch_query).create(source_key=source_key,
                                                                       stream_name=stream_names[iConfig],
                                                                       insertion_time=insertion_times[iConfig],
                                                                       stream_value=str(stream_values[iConfig]),
                                                                       acknowledgement=set_acknowledgement,
                                                                       comments=comments_value)

                            batch_query.execute()

                response = Response('Acknowledgement received successfully', status=status.HTTP_200_OK)
                return response
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                return response

        except Exception as e:
            response = Response(str(e), status=status.HTTP_409_CONFLICT)
            return response


    def list(self, request, source_key=None):
        """
            Get a list of pending configs for a given source.
            ---
            response_serializer: SourceConfigValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned in invalid.(INVALID_SOURCE_KEY) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            #user specifically modified to exclude user check since it would not exceuted in case of OWNERSHIP_CHANGE
            source = Sensor.objects.get(sourceKey=source_key)
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:

            config_len = None
            streams_config_dicts = []

            config_len = ConfigStorageByStream.objects.filter(source_key=source_key,acknowledgement=0).count()

            if config_len > 0:
                config_data = ConfigStorageByStream.objects.filter(source_key=source_key,
                                                                          acknowledgement=0
                                                                          ).limit(0).values_list('stream_name','stream_value', 'insertion_time')
                # populate data
                raw_stream_names = [item[0] for item in config_data]
                raw_stream_values = [item[1] for item in config_data]

                # populate timestamps
                raw_insertion_times = [item[2] for item in config_data]
                #TODO check if the same stream name has received multiple values

                '''
                for iConfig in range(0,config_len):
                    current_steam_name = stream_names[iConfig]
                '''
                seen = set()
                stream_names = []
                stream_values = []
                insertion_times = []

                for iConfig in range(0,config_len):
                    current_steam_name = raw_stream_names[iConfig]
                    if current_steam_name not in seen:
                        stream_names.append(current_steam_name)
                        seen.add(current_steam_name)
                        stream_values.append(raw_stream_values[iConfig])
                        insertion_times.append(raw_insertion_times[iConfig])
                    else:
                        try:
                            old_iConfig = stream_names.index(current_steam_name)
                        except Exception as e:
                            response = Response('current stream not found' + str(e), status=status.HTTP_409_CONFLICT)
                            return response
                        if  raw_insertion_times[iConfig] > insertion_times[old_iConfig]:
                            insertion_times[old_iConfig] = raw_insertion_times[iConfig]
                            stream_values[old_iConfig] = raw_stream_values[iConfig]

                latest_intertiontime = max(insertion_times)
                #TODO if the same stream name with acknowledgement 0 appears multiple times, set the latest value

                for iConfig in range(0,len(stream_names)):
                    streams_config_dicts.append({'name': stream_names[iConfig],
                                               'value': stream_values[iConfig]})

                reply = SourceConfigValues(data={'sourceKey': source_key,
                                           'insertionTime': latest_intertiontime,
                                           'streams': streams_config_dicts})

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
                    reply = SourceConfigValues(data={'sourceKey': source_key,
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
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
                except Exception as e:
                    response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
                    return response


        except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


    def create(self, request, source_key=None):
        """
            Write a new config record. Payload should be in the semantics as specified in the sensor configuration.
            ---
            parameters:
                - name : body
                  type: body
                  required: True
                  description: Actual body.
                  paramType: body
            responseMessages:
                - code : 201
                  message : Success. New config has been written into the database.
                - code : 400
                  message : If the specified key does not exist (INVALID_SOURCE_KEY) or
                            If any of the essential parameters are missing/invalid (BAD_REQUEST) or
                            If there is an error retrieving the payload (ERROR_RETRIEVING_PAYLOAD) or
                            If there is an error splitting multiple records (ERROR_SPLITTING_RECORDS) or
                            If there is an error in parsing multiple config streams (ERROR_SPLITTING_STREAMS) or
                            If the data provided in the request body is not proper as per the data units of streams (INVALID_DATA).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            return config_write(request,
                              request_arrival_time,
                              source_key,
                              settings.RESPONSE_TYPES.DRF)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)





def json_config_type_validation(config_field, config_value):
    try:
        if config_field.streamDataType == "INTEGER":
            assert(type(config_value) is int)
            updated_value = config_value
        elif config_field.streamDataType == "BOOLEAN":
            assert(config_value == 0 or config_value == 1)
            updated_value = config_value
        elif config_field.streamDataType == "FLOAT":
            assert(type(config_value) is float)
            updated_value = config_value
        elif config_field.streamDataType == "LONG":
            assert(type(config_value) is long)
            updated_value = config_value
        elif config_field.streamDataType == "STRING" or config_field.streamDataType == "MAC":
            assert(type(config_value) is unicode)
            updated_value = config_value
        elif config_field.streamDataType == "TIMESTAMP":
            assert(type(config_value) is unicode)
            if config_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(config_value), str(config_field.streamDateTimeFormat))
            else:
                updated_value = parser.parse(str(config_value))
        elif config_field.streamDataType == "DATE":
            assert(type(config_value) is unicode)
            if config_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(config_value), str(config_field.streamDateTimeFormat)).date()
            else:
                updated_value = parser.parse(str(config_value)).date()
        elif config_field.streamDataType == "TIME":
            assert(type(config_value) is unicode)
            if config_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(config_value), str(config_field.streamDateTimeFormat)).time()
            else:
                updated_value = parser.parse(str(config_value)).time()
        else:
            return None, False

        return updated_value, True

    except Exception as E:
        return None, False


def config_write(request, request_arrival_time, source_key, response_type):
    try:
        try:
            #check if the user has rights to execute configuration change on this source
            source = Sensor.objects.get(sourceKey=source_key,user=request.user)
        except Sensor.DoesNotExist:
            # Key not found
            return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.INVALID_SOURCE_KEY,
                                                    response_type, False,
                                                    {'function_name': sys._getframe().f_code.co_name})


        config_fields = ConfigField.objects.filter(source=source)
        # get the payload
        try:
            payload = request.data
        except Exception as e:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR,
                                                response_type, False,
                                                comments)

        #change config error logs and messages
        if payload is None:
            return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                         request_arrival_time,
                                                         settings.ERRORS.ERROR_RETRIEVING_PAYLOAD,
                                                         source)
        # check for multiple entries and split
        config_values_list = payload
        # parse entries, error in parsing even a single one will return an error
        n_entries = 0
        stream_data_tuples = []
        extracted_timestamp_from_config = {}
        config_data_dict = dict()
        for config_field_key, config_field_value in payload.items():
            # split single entry into multiple fields
            if config_field_value is None:
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                             request_arrival_time,
                                                             settings.ERRORS.ERROR_SPLITTING_STREAMS,
                                                             source)
            #check the datatypes match and if the given stream name is valid ConfigField
            config_field_valid_count = ConfigField.objects.filter(source=source,name=config_field_key).count()

            if config_field_valid_count == 0:
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                                 request_arrival_time,
                                                                 settings.ERRORS.INVALID_DATA,
                                                                 source)
            else:
                stream_instance = ConfigField.objects.get(source=source,name=config_field_key)
                updated_value, validation_output = json_config_type_validation(stream_instance,
                                                                               config_field_value)

            if validation_output is True:
                stream_data_tuples.append((config_field_key.strip(), str(updated_value)))
                config_data_dict[stream_instance.name] = updated_value
                if stream_instance.streamDataType in ("TIMESTAMP", "DATE", "TIME"):
                    # It's a datetime/date/time field
                    # keep as a datetime object for ts field of the entry
                    extracted_timestamp_from_config[stream_instance.streamDataType] = updated_value
            else:
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                                 request_arrival_time,
                                                                 settings.ERRORS.STREAM_PARSING_FAILED,
                                                                 source)
            n_entries += 1

        insertion_time = timezone.now()

        # Now populate the database - create a Batch Request

        # add data streams
        for stream in stream_data_tuples:
            #Open bug on cassandra - https://datastax-oss.atlassian.net/browse/PYTHON-445

            batch_query = BatchQuery()
            ConfigStorageByStream.batch(batch_query).create(source_key=source_key,
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
            timestamp_in_config = extracted_timestamp_from_config["TIMESTAMP"]
        except KeyError:
            try:
                timestamp_in_config = datetime.datetime.combine(extracted_timestamp_from_config["DATE"],
                                                              extracted_timestamp_from_config["TIME"])
            except:
                timestamp_in_config = insertion_time

        try:
            if timestamp_in_config.tzinfo is None:
                tz = pytz.timezone(str(source.dataTimezone))
                # localize only adds tzinfo and does not change the dt value
                timestamp_in_config = tz.localize(timestamp_in_config)
        except:
            pass

        # ----------------------------------#
        # Calling publish_to_kafka_broker

        if KAFKA_WRITE:
            #logger.debug('Before calling kafka broker function from action_write')
            data_dict_for_kafka = config_data_dict
            data_dict_for_kafka['source_key'] = source_key
            data_dict_for_kafka['user_name'] = str(request.user)
            data_dict_for_kafka['source_name'] = str(source.name)
            data_dict_for_kafka['sensor_type'] = Sensor.objects.get(sourceKey=source_key).templateName
            time_stamp_in_dict = data_dict_for_kafka.get("TIMESTAMP",None)
            if not time_stamp_in_dict:
                data_dict_for_kafka["TIMESTAMP"] = timestamp_in_config
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
                        kafka_producers[iWrite].send_message(topic='config_'+Sensor.objects.get(sourceKey=source_key).templateName,key=source_key,json_msg=data_dict_for_kafka,sync=True)
                    except Exception as ex:
                        logger.debug("exception in config send_message: %s"% str(ex))
                else:
                    logger.debug('kafka_producer is still None')
            #logger.debug('After calling kafka broker function')
            #logger.debug('message sent')

    # configs has been saved, send a response back
        response = Response("Config Created",status=status.HTTP_201_CREATED)
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
            response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            return response
    '''

class ConfigStreamCreateView(EntryPointMixin, AddSensorsMixin, CreateView):
    form_class = ConfigFieldForm
    template_name = "config/add_config_stream.html"

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.kwargs.get('source_key')})

    def form_valid(self, form):
        try:
            source = get_object_or_404(Sensor, isTemplate=False, sourceKey = self.kwargs.get('source_key'))
            new_config_stream = form.save(commit=False)
            new_config_stream.source = source
            new_config_stream.save()
            return super(ConfigStreamCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The stream name should be unique.")
        except Exception as exception:
            raise Http404()
