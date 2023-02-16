from dataglen.models import Sensor
from .models import ErrorField, ErrorStorageByStream
from .serializers import ErrorStreamSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
import sys, logging, dateutil
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
import json
from django.http import HttpResponse, JsonResponse
from rest_framework import authentication, permissions
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from kutbill import settings
from django.db import IntegrityError
from rest_framework.exceptions import ParseError
from .forms import ErrorFieldForm
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse_lazy
from rest_framework.parsers import JSONParser
from dateutil import parser
import pytz
from .serializers import ErrorDataValues, ErrorSourceDataValuesLatest
import pandas as pd
from monitoring.models import SourceMonitoring
import datetime
from utils.errors import generate_exception_comments
from dataglen.models import ValidDataStorageByStream

from dashboards.mixins import AddSensorsMixin, EntryPointMixin, ProfileDataMixin
from django.views.generic.edit import CreateView, FormView, UpdateView

from dgkafka.views import create_kafka_producers
from kutbill.settings import KAFKA_WRITE,KAFKA_HOSTS,KAFKA_WRITE_TO_HOSTS
from dgkafka.settings import kafka_producers
from solarrms.cron_new_tickets import new_solar_events_check_for_a_plant

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

class ErrorStreamsViewSet(viewsets.ViewSet):
    """
    Manage your streams
    """

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'error_stream_name'

    def list(self, request, source_key=None):
        """
            Get a list of error streams for a source.
            ---
            response_serializer: ErrorStreamSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            try:
                source = Sensor.objects.get(sourceKey=source_key)
            except ObjectDoesNotExist:
                return Response('INVALID_SOURCE_KEY', status=status.HTTP_400_BAD_REQUEST)
            error_streams = ErrorField.objects.filter(source=source, isActive=True)
            serializer = ErrorStreamSerializer(error_streams, many=True)
            response = Response(serializer.data, status=status.HTTP_200_OK)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return Response('INVALID_SOURCE_KEY', status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response('INTERNAL_SERVER_ERROR', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def retrieve(self, request, error_stream_name=None, source_key=None):
        """
            Get a error stream with the mentioned key.
            ---
            response_serializer: StreamSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the specified source key does not exist (INVALID_SOURCE_KEY) or
                            If the specified stream name does not exist (INVALID_ERROR_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key)
        except ObjectDoesNotExist:
            return Response('INVALID_SOURCE_KEY', status=status.HTTP_400_BAD_REQUEST)
        try:
            error_stream = ErrorField.objects.get(source=source,
                                                  name=error_stream_name)
            serializer = ErrorStreamSerializer(error_stream,
                                          many=False)
            response = Response(serializer.data, status=status.HTTP_200_OK)
            return response
        except ObjectDoesNotExist:
            return Response('INVALID_ERROR_STREAM_NAME', status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response('INTERNAL_SERVER_ERROR', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def partial_update(self, request, error_stream_name=None, source_key=None):
        """
            Update an existing error stream.
            ---
            parameters:
                - name: body
                  type: WriteErrorStreamSerializer
                  description: Updated details of the stream.
                  required: True
                  paramType: body
            response_serializer: ErrorStreamSerializer
            responseMessages:
                - code : 201
                  message : Success
                - code : 401
                  message : Not authenticated
                - code : 400
                  message : If the specified key does not exist (INVALID_SOURCE_KEY) or
                            If the specified key does not exist (INVALID_ERROR_STREAM).
        """

        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key, user=request.user)
        except ObjectDoesNotExist:
            return Response("INVALID_SOURCE_KEY", status=status.HTTP_400_BAD_REQUEST)

        try:
            error_stream = ErrorField.objects.get(source=source,
                                                  name=error_stream_name)
            serializer = ErrorStreamSerializer(error_stream,
                                               data=request.data,
                                               partial=True)
            if serializer.is_valid():
                serializer.save(user=request.user)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                return response
            else:
                response = Response(serializer.errors,
                                    status=status.HTTP_400_BAD_REQUEST)
                return response
        except ObjectDoesNotExist:
            return Response("INVALID_ERROR_STREAM", status=status.HTTP_400_BAD_REQUEST)
        except ParseError:
            return Response("JSON_PARSE_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exception:
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def create(self, request, source_key=None):
        """
            Create a new error stream.
            ---
            parameters:
                - name: body
                  type: WriteErrorStreamSerializer
                  description: Details of the new error stream to be created.
                  required: True
                  paramType: body
            response_serializer: ErrorStreamSerializer
            responseMessages:
                - code : 201
                  message : Success. Accompanied with details of the new stream.
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If any of the essential parameters are missing/invalid (BAD_REQUEST).
                - code : 409
                  message : If a stream with the mentioned name OR position already exists (DUPLICATE_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        # get the source first
        try:
            source = Sensor.objects.get(sourceKey=source_key,
                                        user=request.user)
        except ObjectDoesNotExist as exception:
            return Response('INVALID_SOURCE_KEY', status=status.HTTP_400_BAD_REQUEST)
        # save the new error stream
        try:
            serializer = ErrorStreamSerializer(data=request.data)
            if serializer.is_valid():
                if source.dataFormat == "CSV":
                    try:
                        assert(serializer['streamPositionInCSV'].value)
                    except AssertionError:
                        return Response('BAD_REQUEST', status=status.HTTP_400_BAD_REQUEST)
                serializer.save(source=source)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                return response
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                return response

        except IntegrityError as exception:
            try:
                error_field = ErrorField.objects.get(source=source,
                                                    name=request.data["name"])
            except ObjectDoesNotExist:
                try:
                    error_field = ErrorField.objects.get(source=source,
                                                        streamPositionInCSV=request.data["streamPositionInCSV"])
                except:
                    return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response("DUPLICATE_ERROR_STREAM_NAME", status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist:
            return Response("INVALID_SOURCE_KEY", status=status.HTTP_400_BAD_REQUEST)
        except ParseError as exception:
            logger.debug(str(exception))
            return Response("JSON_PARSE_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exception:
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def destroy(self, request, error_stream_name=None, source_key=None):
        """
            Delete an error stream.
            ---
            responseMessages:
                - code : 204
                  message : Success. The error stream has been deleted.
                - code : 400
                  message : If the specified source key does not exist (INVALID_SOURCE_KEY) or
                            If the specified stream name does not exist (INVALID_ERROR_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key, user=request.user)
        except ObjectDoesNotExist as exception:
            return Response("INVALID_SOURCE_KEY", status=status.HTTP_400_BAD_REQUEST)
        try:
            error_stream = ErrorField.objects.get(source=source,
                                                  name=error_stream_name)
            error_stream.delete()
            response = Response("error stream deleted",status=status.HTTP_204_NO_CONTENT)
            return response
        except ObjectDoesNotExist as exception:
            return Response("INVALID_ERROR_STREAM", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ErrorStreamCreateView(EntryPointMixin, AddSensorsMixin, CreateView):
    form_class = ErrorFieldForm
    template_name = "errors/add_error_stream.html"

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.kwargs.get('source_key')})

    def form_valid(self, form):
        try:
            source = get_object_or_404(Sensor, isTemplate=False, sourceKey = self.kwargs.get('source_key'))
            new_error_stream = form.save(commit=False)
            new_error_stream.source = source
            new_error_stream.save()
            return super(ErrorStreamCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The stream name should be unique.")
        except Exception as exception:
            logger.debug(str(exception))
            raise Http404()

def json_error_type_validation(error_field, error_value):
    try:
        if error_field.streamDataType == "INTEGER":
            assert(type(error_value) is int)
            raw_value = error_value
            mf = error_field.multiplicationFactor
            updated_value = error_value * mf
        elif error_field.streamDataType == "BOOLEAN":
            assert(error_value == 0 or error_value == 1)
            raw_value = error_value
            mf = error_field.multiplicationFactor
            updated_value = error_value
        elif error_field.streamDataType == "FLOAT":
            assert(type(error_value) is float)
            raw_value = error_value
            mf = error_field.multiplicationFactor
            updated_value = error_value * mf
        elif error_field.streamDataType == "LONG":
            assert(type(error_value) is long)
            raw_value = error_value
            mf = error_field.multiplicationFactor
            updated_value = error_value * mf
        elif error_field.streamDataType == "STRING" or error_field.streamDataType == "MAC":
            assert(type(error_value) is unicode)
            raw_value = error_value
            mf = error_field.multiplicationFactor
            updated_value = error_value
        elif error_field.streamDataType == "TIMESTAMP":
            assert(type(error_value) is unicode)
            if error_field.streamDateTimeFormat:
                raw_value = datetime.datetime.strptime(str(error_value), str(error_field.streamDateTimeFormat))
                updated_value = datetime.datetime.strptime(str(error_value), str(error_field.streamDateTimeFormat))
                mf = error_field.multiplicationFactor
            else:
                raw_value = parser.parse(str(error_value))
                updated_value = parser.parse(str(error_value))
                mf = error_field.multiplicationFactor
        elif error_field.streamDataType == "DATE":
            assert(type(error_value) is unicode)
            if error_field.streamDateTimeFormat:
                raw_value = datetime.datetime.strptime(str(error_value), str(error_field.streamDateTimeFormat)).date()
                updated_value = datetime.datetime.strptime(str(error_value), str(error_field.streamDateTimeFormat)).date()
                mf = error_field.multiplicationFactor
            else:
                raw_value = parser.parse(str(error_value)).date()
                updated_value = parser.parse(str(error_value)).date()
                mf = error_field.multiplicationFactor
        elif error_field.streamDataType == "TIME":
            assert(type(error_value) is unicode)
            if error_field.streamDateTimeFormat:
                raw_value = datetime.datetime.strptime(str(error_value), str(error_field.streamDateTimeFormat)).time()
                updated_value = datetime.datetime.strptime(str(error_value), str(error_field.streamDateTimeFormat)).time()
                mf = error_field.multiplicationFactor
            else:
                raw_value = parser.parse(str(error_value)).time()
                updated_value = parser.parse(str(error_value)).time()
                mf = error_field.multiplicationFactor
        else:
            return None, None, None, False

        return updated_value, raw_value, mf, True

    except Exception as E:
        logger.debug(str(E))
        return None, None, None, False


def error_write(request, request_arrival_time, source_key, response_type):
    try:
        try:
            source = Sensor.objects.get(sourceKey=source_key, user=request.user)
        except ObjectDoesNotExist as exception:
            return Response("INVALID_SOURCE_KEY", status=status.HTTP_400_BAD_REQUEST)

        error_fields = ErrorField.objects.filter(source=source)
        # get the payload
        try:
            payload = request.data
        except Exception as e:
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if payload is None:
            return Response("ERROR_RETRIEVING_PAYLOAD", status=status.HTTP_400_BAD_REQUEST)

        error_values_list = payload
        n_entries = 0
        stream_data_tuples = []
        extracted_timestamp_from_error = {}
        error_data_dict = dict()
        timestamp_in_data = None
        data_packet = False
        for error_field_key, error_field_value in payload.items():
            # logger.debug(",".join(["ERROR_WRITE", str(error_field_key), str(error_field_value)]))
            # split single entry into multiple fields
            if error_field_value is None:
                return Response("ERROR_SPLITTING_STREAMS", status=status.HTTP_400_BAD_REQUEST)
            #check the datatypes match and if the given stream name is valid ErrorField
            error_field_valid_count = ErrorField.objects.filter(source=source,name=error_field_key).count()
            if error_field_valid_count == 0:
                logger.debug(",".join(["ERROR_WRITE", str("Checking for solar status"), str(source)]))
                # check if it's solar_status
                stream_instance = source.fields.filter(name=error_field_key)
                if len(stream_instance) == 0:
                    return Response("INVALID_DATA", status=status.HTTP_400_BAD_REQUEST)
                else:
                    stream_instance = stream_instance[0]
                    logger.debug(",".join(["ERROR_WRITE", str("stream_instance"), str(stream_instance)]))
                    updated_value, raw_value, mf, validation_output = json_error_type_validation(stream_instance,
                                                                                                 error_field_value)
                    data_packet = True
                    logger.debug(",".join(["ERROR_WRITE", str("data_packet"), str(data_packet)]))
            else:
                stream_instance = ErrorField.objects.get(source=source,name=error_field_key)
                updated_value, raw_value, mf, validation_output = json_error_type_validation(stream_instance,
                                                                                             error_field_value)

            if validation_output is True:
                stream_data_tuples.append((error_field_key.strip(), str(updated_value), str(raw_value), str(mf)))
                error_data_dict[stream_instance.name] = updated_value
                if stream_instance.streamDataType in ("TIMESTAMP", "DATE", "TIME"):
                    # It's a datetime/date/time field
                    # keep as a datetime object for ts field of the entry
                    extracted_timestamp_from_error[stream_instance.streamDataType] = updated_value
                if error_field_key == 'ERROR_TIMESTAMP' or error_field_key == 'TIMESTAMP':
                    timestamp_in_data = updated_value
                    try:
                        if timestamp_in_data.tzinfo is None:
                            tz = pytz.timezone(str(source.dataTimezone))
                            # localize only adds tzinfo and does not change the dt value
                            timestamp_in_data = tz.localize(timestamp_in_data)
                    except Exception as exception:
                        pass
            else:
                return Response("STREAM_PARSING_FAILED", status=status.HTTP_400_BAD_REQUEST)
            n_entries += 1

        try:
            insertion_time = timezone.now()
            # astimezone does the conversion and updates the tzinfo part
            insertion_time = insertion_time.astimezone(pytz.timezone(source.dataTimezone))
        except Exception as exc:
            insertion_time = timezone.now()

        if timestamp_in_data is None:
            timestamp_in_data = insertion_time

        # add tzinfo info in timestamp_in_data if absent
        try:
            if timestamp_in_data.tzinfo is None:
                tz = pytz.timezone(str(source.dataTimezone))
                # localize only adds tzinfo and does not change the dt value
                timestamp_in_data = tz.localize(timestamp_in_data)
        except:
            pass

        try:
            timestamp_in_error = extracted_timestamp_from_error["TIMESTAMP"]
        except KeyError:
            try:
                timestamp_in_error = datetime.datetime.combine(extracted_timestamp_from_error["DATE"],
                                                              extracted_timestamp_from_error["TIME"])
            except:
                timestamp_in_error = insertion_time

        # add tzinfo info in timestamp_in_error if absent
        try:
            if timestamp_in_error.tzinfo is None:
                tz = pytz.timezone(str(source.dataTimezone))
                # localize only adds tzinfo and does not change the dt value
                timestamp_in_error = tz.localize(timestamp_in_error)
        except:
            pass

        for stream in stream_data_tuples:
            if not data_packet:
                error_storage = ErrorStorageByStream.objects.create(source_key=source_key,
                                                                    stream_name=stream[0],
                                                                    insertion_time=insertion_time,
                                                                    stream_value=str(stream[1]),
                                                                    timestamp_in_data=timestamp_in_data,
                                                                    raw_value=str(stream[2]),
                                                                    multiplication_factor=str(stream[3]))

                error_storage.save()
            else:
                logger.debug(",".join(["ERROR_WRITE", str("writing ValidDataStorageByStream"),str(stream[0]),
                                       str(stream[1]), str(timestamp_in_data)]))
                data_point = ValidDataStorageByStream.objects.create(source_key=source_key,
                                                                     stream_name=stream[0],
                                                                     insertion_time=insertion_time,
                                                                     stream_value=str(stream[1]),
                                                                     timestamp_in_data=timestamp_in_data,
                                                                     raw_value=str(stream[2]),
                                                                     multiplication_factor=str(stream[3]))
                data_point.save()

        # ----------------------------------#
        # Calling publish_to_kafka_broker
        if KAFKA_WRITE:
            logger.debug('Before calling kafka broker function from error_write')
            data_dict_for_kafka = error_data_dict
            data_dict_for_kafka['source_key'] = source_key
            data_dict_for_kafka['user_name'] = str(request.user)
            data_dict_for_kafka['source_name'] = str(source.name)
            data_dict_for_kafka['sensor_type'] = Sensor.objects.get(sourceKey=source_key).templateName
            time_stamp_in_dict = data_dict_for_kafka.get("TIMESTAMP",None)
            if not time_stamp_in_dict:
                data_dict_for_kafka["TIMESTAMP"] = timestamp_in_error
            global kafka_producers
            if not kafka_producers:
                try:
                    kafka_producers = create_kafka_producers()
                    logger.debug('Created kafka producer from error_write')
                except Exception as ex:
                    logger.debug("exception in create_kafka: %s"% str(ex))
            for iWrite in range(len(kafka_producers)):
                if KAFKA_WRITE_TO_HOSTS[iWrite] and kafka_producers[iWrite]:
                    try:
                        kafka_producers[iWrite].send_message(topic='error_'+Sensor.objects.get(sourceKey=source_key).templateName,key=source_key,json_msg=data_dict_for_kafka,sync=True)
                    except Exception as ex:
                        logger.debug("exception in create_kafka: %s"% str(ex))
                else:
                    logger.debug('kafka_producer is still None')
            logger.debug('After calling kafka broker function')
            logger.debug('message sent')

    # Errors has been saved, send a response back
        try:
            if hasattr(source, "independentinverter"):
                logger.debug(",".join(["ERROR_WRITE",
                                       str(source),
                                       str(hasattr(source, "independentinverter"))]))
                logger.debug(",".join(["ERROR_WRITE",
                                       str("Scheduling a run for plant"),
                                       str(source.independentinverter.plant.id)]))
                # analyse_ticket.apply_async(args=[ticket.id], countdown=60*30)
                new_solar_events_check_for_a_plant.apply_async(
                    args=[int(source.independentinverter.plant.id)], countdown=60)
        except:
            pass
        response = Response("Error Created",status=status.HTTP_201_CREATED)
        return response

    except Exception as exception:
        logger.debug(str(exception))
        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ErrorRecordsSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication,authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (JSONParser,)
    lookup_field = "timestamp"

    def list(self, request, source_key=None):
        """
            Get a list of pending errors for a given source.
            ---
            response_serializer: SourceErrorValues
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
            return Response("INVALID_SOURCE_KEY", status=status.HTTP_400_BAD_REQUEST)

        latest = request.query_params.get("latest","FALSE")
        time_zone = request.query_params.get("timezone", None)
        aggregated_streams = request.query_params.get("aggregated_streams","FALSE")

        try:
            if time_zone:
                if time_zone.upper() == 'UTC':
                    tz = pytz.timezone(pytz.utc.zone)
                else:
                    tz = pytz.timezone(time_zone)
            else:
                tz = pytz.timezone(source.dataTimezone)
        except:
            return Response("SOURCE_CONFIGURATION_ISSUE", status=status.HTTP_400_BAD_REQUEST)

        error_streams = [item for sublist in ErrorField.objects.filter(source=source).order_by('name').values_list('name') for item in sublist]
        try:
            streams = request.query_params["streamNames"].split(",")
            streams = [stream.strip().lstrip() for stream in streams]
            for stream in streams:
                assert(stream in error_streams)
        except AssertionError:
            return Response("INVALID_DATA_STREAM", status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            streams = error_streams

        df_all = pd.DataFrame()
        if latest.upper() == 'FALSE':
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                #acknowledgement = request.query_params.get("acknowledgement", 0)
                # convert into datetime objects
                st = parser.parse(st)
                if st.tzinfo is None:
                    st = tz.localize(st)
                et = parser.parse(et)
                if et.tzinfo is None:
                    et = tz.localize(et)
            except:
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            try:
                streams_data_dicts = []
                for stream_num in range(len(streams)):
                    stream = streams[stream_num]
                    stream_data = ErrorStorageByStream.objects.filter(source_key=source_key,
                                                                      stream_name=stream,
                                                                      timestamp_in_data__gte=st,
                                                                      timestamp_in_data__lte=et).limit(settings.CASSANDRA_READ_RECORDS_LIMIT).values_list('stream_value', 'timestamp_in_data')

                    values = [item[0] for item in stream_data]
                    # populate timestamps
                    timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in stream_data]
                    if len(timestamps) > 2:
                        startTime = timestamps[-1]
                        endTime = timestamps[0]
                    elif len(timestamps) == 1:
                        startTime = endTime = timestamps[0]
                    else:
                        startTime = endTime = None
                    if startTime:
                        streams_data_dicts.append({'name': stream,
                                                   'count': len(values),
                                                   'startTime': startTime,
                                                   'endTime': endTime,
                                                   'timestamps': timestamps,
                                                   'values': values})
                    else:
                        streams_data_dicts.append({'name': stream,
                                                   'count': len(values),
                                                   'timestamps': timestamps,
                                                   'values': values})

                    # Make data frame for every stream               
                    try:
                        df_stream = pd.DataFrame(pd.Series(values),columns=[stream])
                        df_stream['timestamp'] = timestamps
                    except Exception as exception:
                        logger.debug(str(exception))
                    if df_all.empty:
                        df_all = df_stream
                    else:
                        df_new = pd.merge(df_all, df_stream, on='timestamp', how='outer')
                        df_all = df_new

                reply = ErrorDataValues(data={'sourceKey': source_key,
                                                   'streams': streams_data_dicts})

                if aggregated_streams.upper() == 'TRUE':
                    try:
                        response = Response(json.loads(df_all.to_json(orient='records')),
                                                status=status.HTTP_200_OK)
                        return response
                    except:
                        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                else:
                    if reply.is_valid():
                        response = Response(reply.data,
                                            status=status.HTTP_200_OK)
                        return response
                    else:
                        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif latest.upper() == 'TRUE':
            current = request.query_params.get("current","FALSE")
            try:
                current_data = SourceMonitoring.objects.filter(source_key=source_key)

                if current.upper() == 'TRUE' and len(current_data) == 0:
                    reply = ErrorSourceDataValuesLatest(data={'sourceKey': source_key,
                                                         'streams': []})
                else:
                    streams_data_dicts = []
                    for stream_num in range(len(streams)):
                        stream = streams[stream_num]
                        stream_data = ErrorStorageByStream.objects.filter(source_key=source_key,
                                                                          stream_name=stream).limit(1).values_list('stream_value', 'timestamp_in_data')
                        # populate data
                        values = [item[0] for item in stream_data]
                        # populate timestamps
                        timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in stream_data]
                        if len(values)>0:
                            streams_data_dicts.append({'name': stream,
                                                       'timestamp': timestamps[0],
                                                       'value': values[0]})
                        # Make data frame for every stream               
                        try:
                            df_stream = pd.DataFrame(pd.Series(values),columns=[stream])
                            df_stream['timestamp'] = timestamps
                        except Exception as exception:
                            logger.debug(str(exception))
                        if df_all.empty:
                            df_all = df_stream
                        else:
                            df_new = pd.merge(df_all, df_stream, on='timestamp', how='outer')
                            df_all = df_new

                    reply = ErrorSourceDataValuesLatest(data={'sourceKey': source_key,
                                                        'streams': streams_data_dicts})

                if aggregated_streams.upper() == 'TRUE':
                    try:
                        response = Response(json.loads(df_all.to_json(orient='records')),
                                                status=status.HTTP_200_OK)
                        return response
                    except:
                        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    if reply.is_valid():
                        response = Response(reply.data,
                                            status=status.HTTP_200_OK)
                        return response
                    else:
                        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)


    def create(self, request, source_key=None):
        """
            Write a new error record. Payload should be in the semantics as specified in the sensor configuration.
            ---
            parameters:
                - name : body
                  type: body
                  required: True
                  description: Actual body.
                  paramType: body
            responseMessages:
                - code : 201
                  message : Success. New error has been written into the database.
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If any of the essential parameters are missing/invalid (BAD_REQUEST) or
                            If there is an error retrieving the payload (ERROR_RETRIEVING_PAYLOAD) or
                            If there is an error splitting multiple records (ERROR_SPLITTING_RECORDS) or
                            If there is an error in parsing multiple error streams (ERROR_SPLITTING_STREAMS) or
                            If the data provided in the request body is not proper as per the data units of streams (INVALID_DATA).
                - code : 401
                  message : Not authenticated
        """

        request_arrival_time = timezone.now()
        try:
            return error_write(request,
                              request_arrival_time,
                              source_key,
                              settings.RESPONSE_TYPES.DRF)
        except:
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def partial_update(self, request, timestamp=None, source_key=None):
        try:
            try:
                source = Sensor.objects.get(sourceKey=source_key, user=request.user)
            except ObjectDoesNotExist as exception:
                return Response("INVALID_SOURCE_KEY", status=status.HTTP_400_BAD_REQUEST)

            request_arrival_time = datetime.datetime.utcnow()
            try:
                payload = request.data
            except Exception as e:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if payload is None:
                return Response("ERROR_RETRIEVING_PAYLOAD", status=status.HTTP_400_BAD_REQUEST)

            timestamp = parser.parse(timestamp)
            timestamp = update_tz(timestamp, pytz.utc.zone)
            stream_data_tuples = []
            no_of_records = 0
            for error_field_key, error_field_value in payload.items():
                # split single entry into multiple fields
                if error_field_value is None:
                    return Response("ERROR_SPLITTING_STREAMS", status=status.HTTP_400_BAD_REQUEST)
                #check the datatypes match and if the given stream name is valid ErrorField
                error_field_valid_count = ErrorField.objects.filter(source=source,name=error_field_key).count()
                if error_field_valid_count == 0:
                    return Response("INVALID_DATA", status=status.HTTP_400_BAD_REQUEST)
                else:
                    stream_instance = ErrorField.objects.get(source=source,name=error_field_key)
                    updated_value, raw_value, mf, validation_output = json_error_type_validation(stream_instance,
                                                                                                 error_field_value)

                    logger.debug(updated_value, raw_value, mf, validation_output)

                if validation_output is True:
                    stream_data_tuples.append((error_field_key.strip(), str(updated_value), str(raw_value), str(mf)))
                else:
                    return Response("STREAM_PARSING_FAILED", status=status.HTTP_400_BAD_REQUEST)
            try:
                for stream in stream_data_tuples:
                    try:
                        record = ErrorStorageByStream.objects.filter(source_key=source_key,
                                                                     stream_name=str(stream[0]),
                                                                     timestamp_in_data__gte=timestamp,
                                                                     timestamp_in_data__lte=timestamp)
                    except Exception as exception:
                        logger.debug(str(exception))
                    if len(record)>0:
                        no_of_records = no_of_records + 1
                        #logger.debug(record[0].stream_value)
                        record[0].stream_value = stream[1]
                        record[0].raw_value= stream[2]
                        record[0].multiplication_factor = stream[3]
                        record[0].updated_time = request_arrival_time
                        record[0].save()
            except ObjectDoesNotExist as exception:
                logger.debug(str(exception))
                return Response("NO_RECORD_FOUND", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("ERROR_IN_UPDATING_THE_RECORD", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if no_of_records == 0 :
                return Response("INVALID_TIMESTAMP", status=status.HTTP_400_BAD_REQUEST)
            elif no_of_records == 1 :
                return Response(str(no_of_records) + " RECORD_UPDATED_SUCCESSFULLY", status=status.HTTP_201_CREATED)
            else:
                return Response(str(no_of_records) + " RECORDS_UPDATED_SUCCESSFULLY", status=status.HTTP_201_CREATED)   

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)