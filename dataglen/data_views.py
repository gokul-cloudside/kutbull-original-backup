from django.http import HttpResponse, JsonResponse
from action.models import ActionsStorageByStream
from config.models import ConfigStorageByStream
from django.conf import settings
from django.utils import timezone

from cassandra import ConsistencyLevel
from cassandra.cqlengine.query import BatchQuery, BatchType
from dataglen.models import Sensor, Field, \
    ValidDataStorageByStream

from errors.models import ErrorStorageByStream


from monitoring.views import write_a_data_write_ttl

from logger.views import log_a_success
from utils.errors import log_and_return_error, log_and_return_independent_error, \
    log_and_return_bad_data_write_request, \
    generate_exception_comments

from logger.tasks import update_counters
from dataglen.misc import get_payload, split_payload, split_single_entry
from logger.models import DataWriteHistoryByUser, DataWriteHistoryBySource

import datetime, httplib, logging, sys
from dateutil import parser
import pytz, json
from django.contrib.auth.models import AnonymousUser
import pandas as pd
from dgkafka.views import create_kafka_producers
from dgkafka.settings import kafka_producers
#from confluent_kafka import Producer
from kutbill.settings import KAFKA_WRITE, KAFKA_WRITE_TO_HOSTS

logger = logging.getLogger('dataglen.views')
# TODO: Change the logging status to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)


def get_processed_values(data_field, raw_value):
    # returns raw_value, processed_value, mf
    try:
        if data_field.streamDataType == "INTEGER" or data_field.streamDataType == "FLOAT" or data_field.streamDataType == "LONG":
            return raw_value, raw_value * (data_field.multiplicationFactor), data_field.multiplicationFactor
        else:
            return raw_value, raw_value, data_field.multiplicationFactor
    except:
        return raw_value, raw_value, data_field.multiplicationFactor

def csv_data_type_validation(data_field, data_value):
    '''
        casted_value, if casting was successful
    '''
    data_value = data_value.strip()
    # TODO make this more efficient (worst case is super bad)
    try:
        if data_field.streamDataType == "INTEGER":
            updated_value = int(data_value)
        elif data_field.streamDataType == "BOOLEAN":
            assert(int(data_value) == 0 or int(data_value) == 1)
            updated_value = int(data_value)
        elif data_field.streamDataType == "STRING":
            updated_value = str(data_value)
        elif data_field.streamDataType == "FLOAT":
            updated_value = float(data_value)
        elif data_field.streamDataType == "LONG":
            updated_value = long(data_value)
        elif data_field.streamDataType == "MAC":
            updated_value = str(data_value)
        elif data_field.streamDataType == "TIMESTAMP":
            if data_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(data_value), str(data_field.streamDateTimeFormat))
            else:
                updated_value = parser.parse(str(data_value))
        elif data_field.streamDataType == "DATE":
            if data_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(data_value), str(data_field.streamDateTimeFormat)).date()
            else:
                updated_value = parser.parse(str(data_value)).date()
        elif data_field.streamDataType == "TIME":
            if data_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(data_value), str(data_field.streamDateTimeFormat)).time()
            else:
                updated_value = parser.parse(str(data_value)).time()
        else:
            return None, False

        return updated_value, True
    except Exception as E:
        return None, False


def json_data_type_validation(data_field, data_value):
    try:
        if data_field.streamDataType == "INTEGER":
            assert(type(data_value) is int)
            updated_value = data_value
        elif data_field.streamDataType == "BOOLEAN":
            assert(data_value == 0 or data_value == 1)
            updated_value = data_value
        elif data_field.streamDataType == "FLOAT":
            assert(type(data_value) is float)
            updated_value = data_value
        elif data_field.streamDataType == "LONG":
            assert(type(data_value) is long)
            updated_value = data_value
        elif data_field.streamDataType == "STRING" or data_field.streamDataType == "MAC":
            assert(type(data_value) is unicode)
            updated_value = data_value
        elif data_field.streamDataType == "TIMESTAMP":
            assert(type(data_value) is unicode)
            if data_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(data_value), str(data_field.streamDateTimeFormat))
            else:
                updated_value = parser.parse(str(data_value))
        elif data_field.streamDataType == "DATE":
            assert(type(data_value) is unicode)
            if data_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(data_value), str(data_field.streamDateTimeFormat)).date()
            else:
                updated_value = parser.parse(str(data_value)).date()
        elif data_field.streamDataType == "TIME":
            assert(type(data_value) is unicode)
            if data_field.streamDateTimeFormat:
                updated_value = datetime.datetime.strptime(str(data_value), str(data_field.streamDateTimeFormat)).time()
            else:
                updated_value = parser.parse(str(data_value)).time()
        else:
            return None, False

        return updated_value, True

    except Exception as E:
        return None, False


def atoll_data_type_validation(data_field, data_value):
    # it's same as csv_data_type_validation
    return csv_data_type_validation(data_field, data_value)

# TODO : minimize database lookups in this view and increase caching
def data_write(request, request_arrival_time, source_key, response_type,
               allowed_sources=None, external_payload=None):
    is_external = False
    if external_payload:
        is_external = True
    try:
        try:
            # Do a DataSource lookup IMP - keep the user
            source = Sensor.objects.get(sourceKey=source_key,
                                        user=request.user)
        except Sensor.DoesNotExist:
            # Key not found
            # now check if it's an owner account and the source is there
            if allowed_sources is None:
                return log_and_return_independent_error(request, request_arrival_time,
                                                        settings.ERRORS.INVALID_SOURCE_KEY,
                                                        response_type, False,
                                                        {'function_name': sys._getframe().f_code.co_name}) if not is_external else settings.ERRORS.INVALID_SOURCE_KEY
            try:
                source = Sensor.objects.get(sourceKey=source_key)
                if source not in allowed_sources:
                    return log_and_return_independent_error(request, request_arrival_time,
                                                            settings.ERRORS.INVALID_SOURCE_KEY,
                                                            response_type, False,
                                                            {'function_name': sys._getframe().f_code.co_name}) if not is_external else settings.ERRORS.INVALID_SOURCE_KEY
            except Sensor.DoesNotExist:
                    return log_and_return_independent_error(request, request_arrival_time,
                                                            settings.ERRORS.INVALID_SOURCE_KEY,
                                                            response_type, False,
                                                            {'function_name': sys._getframe().f_code.co_name}) if not is_external else settings.ERRORS.INVALID_SOURCE_KEY
        except Exception as exc:
            logger.debug(exc)
            return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.INVALID_API_KEY,
                                                    response_type, False,
                                                    {'function_name': sys._getframe().f_code.co_name}) if not is_external else settings.ERRORS.INVALID_SOURCE_KEY

        if source.isActive is False:
            # TODO check if it's an invalid data or we should report a different error message
            write_a_data_write_ttl(source.user.id, source.sourceKey,
                                   source.timeoutInterval,
                                   False, request_arrival_time)
            return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.SOURCE_INACTIVE,
                                                    response_type, False,
                                                    {'function_name': sys._getframe().f_code.co_name}) if not is_external else settings.ERRORS.SOURCE_INACTIVE

        # get sensor fields ordered by their position
        if source.dataFormat == 'CSV':
            data_fields = Field.objects.filter(source=source).order_by('streamPositionInCSV')
        else:
            data_fields = Field.objects.filter(source=source)

        # get the payload
        if is_external:
            payload = external_payload
        else:
            payload = get_payload(source, request)

        logger.debug("checking atoll")
        logger.debug(source_key)
        logger.debug(payload)
        logger.debug(request.data)

        if payload is None:
            write_a_data_write_ttl(source.user.id, source.sourceKey,
                                   source.timeoutInterval,
                                   False, request_arrival_time)
            return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                         request_arrival_time,
                                                         settings.ERRORS.ERROR_RETRIEVING_PAYLOAD,
                                                         source) if not is_external else settings.ERRORS.ERROR_RETRIEVING_PAYLOAD
        # check for multiple entries and split
        data_values_list = split_payload(source, payload)
        if data_values_list is None:
            write_a_data_write_ttl(source.user.id, source.sourceKey,
                                   source.timeoutInterval,
                                   False, request_arrival_time)
            return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                         request_arrival_time,
                                                         settings.ERRORS.ERROR_SPLITTING_RECORDS,
                                                         source)  if not is_external else settings.ERRORS.ERROR_SPLITTING_RECORDS

        # parse entries, error in parsing even a single one will return an error
        n_entries = 0
        for data_values in data_values_list:
            # split single entry into multiple fields
            data_values = split_single_entry(source, data_values)
            if data_values is None:
                write_a_data_write_ttl(source.user.id, source.sourceKey,
                                       source.timeoutInterval,
                                       False, request_arrival_time)
                return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                             request_arrival_time,
                                                             settings.ERRORS.ERROR_SPLITTING_STREAMS,
                                                             source)  if not is_external else settings.ERRORS.ERROR_SPLITTING_RECORDS

            #check if the data write has happned from the kafka-based transformation app. If yes, do not send the data
            # back to the same kafka topic. At this point, teh transformation is mainly expected on data write and not on event, action or config
            try:
                transformed = 0
                transformed_key = 'transformed'
                if source.dataFormat == 'JSON':
                    transformed = data_values.get(transformed_key,0)
                    try:
                        if transformed_key in data_values:
                            data_values.pop(transformed_key, None)
                    except Exception as ex:
                        continue
            except Exception as ex:
                continue

            try:
                try:
                    # check if the length of both data fields and values are same,
                    # otherwise raise an assertion error
                    if source.dataFormat == 'CSV':
                        assert(len(data_fields) == len(data_values))
                    elif source.dataFormat == 'JSON' or source.dataFormat == 'ATOLL':
                        stream_names = [field.name for field in data_fields]
                        for stream_name in data_values.keys():
                            assert(stream_name in stream_names)

                except AssertionError:
                    write_a_data_write_ttl(source.user.id, source.sourceKey,
                                           source.timeoutInterval,
                                           False, request_arrival_time)
                    return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                                 request_arrival_time,
                                                                 settings.ERRORS.INVALID_DATA,
                                                                 source)  if not is_external else settings.ERRORS.INVALID_DATA

                # extract date/time field if available
                extracted_timestamp_from_data = {}
                stream_data_tuples = []
                stream_data_dict = dict()

                # iterate through the fields, extract timestamp (if available) and do a type level validation
                for field_number in range(len(data_fields)):
                    # validate the field
                    # csv format
                    if source.dataFormat == "CSV":
                        updated_value, validation_output = csv_data_type_validation(data_fields[field_number],
                                                                                    data_values[field_number])
                    # json format
                    elif source.dataFormat == "JSON":
                        stream_instance = data_fields[field_number]
                        try:
                            updated_value, validation_output = json_data_type_validation(stream_instance,
                                                                                         data_values[stream_instance.name])
                        except Exception as E:
                            continue
                    # atoll format validation (same as csv)
                    elif source.dataFormat == "ATOLL":
                        stream_instance = data_fields[field_number]
                        try:
                            updated_value, validation_output = atoll_data_type_validation(stream_instance,
                                                                                         data_values[stream_instance.name])
                            # logger.debug("*****")
                            # logger.debug("atoll stream validation", str(stream_instance))
                            # logger.debug("atoll stream validation", str(updated_value))
                            # logger.debug("atoll stream validation", str(validation_output))
                        except Exception as E:
                            continue
                    else:
                        updated_value, validation_output = 0, False

                    if validation_output is True:
                        raw_value, processed_value, mf = get_processed_values(data_fields[field_number], updated_value)
                        stream_data_tuples.append((data_fields[field_number].name, str(processed_value), str(raw_value), str(mf)))
                        stream_data_dict[data_fields[field_number].name] = processed_value
                        if data_fields[field_number].streamDataType in ("TIMESTAMP", "DATE", "TIME"):
                            # It's a datetime/date/time field
                            # keep as a datetime object for ts field of the entry
                            extracted_timestamp_from_data[data_fields[field_number].streamDataType] = updated_value
                    else:
                        write_a_data_write_ttl(source.user.id, source.sourceKey,
                                               source.timeoutInterval,
                                               False, request_arrival_time)
                        return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                                     request_arrival_time,
                                                                     settings.ERRORS.STREAM_PARSING_FAILED,
                                                                     source)  if not is_external else settings.ERRORS.STREAM_PARSING_FAILED

                # If timestamp not present, use timezone.now()
                #insertion_time = timezone.now()
                # keep insertion time in source's timezone
                try:
                    insertion_time = timezone.now()
                    # astimezone does the conversion and updates the tzinfo part
                    insertion_time = insertion_time.astimezone(pytz.timezone(source.dataTimezone))
                except Exception as exc:
                    insertion_time = timezone.now()
                try:
                    timestamp_in_data = extracted_timestamp_from_data["TIMESTAMP"]
                except KeyError:
                    try:
                        timestamp_in_data = datetime.datetime.combine(extracted_timestamp_from_data["DATE"],
                                                                      extracted_timestamp_from_data["TIME"])
                    except:
                        timestamp_in_data = insertion_time

                # add tzinfo info in timestamp_in_data if absent
                try:
                    if timestamp_in_data.tzinfo is None:
                        tz = pytz.timezone(str(source.dataTimezone))
                        # localize only adds tzinfo and does not change the dt value
                        timestamp_in_data = tz.localize(timestamp_in_data)
                except:
                    pass

                if timestamp_in_data > insertion_time + datetime.timedelta(seconds=60):
                    write_a_data_write_ttl(source.user.id, source.sourceKey,
                                           source.timeoutInterval,
                                           False, request_arrival_time)
                    return log_and_return_bad_data_write_request(request, settings.RESPONSE_TYPES.DJANGO,
                                                                 request_arrival_time,
                                                                 settings.ERRORS.FUTURE_TIMESTAMP,
                                                                 source)  if not is_external else settings.ERRORS.FUTURE_TIMESTAMP

                # TODO - decide: we can perhaps create a single batch request now, i.e. in case of multiple
                # TODO - entries, either all succeed or None
                # Now populate the database - create a Batch Request
                batch_query = BatchQuery()
                if settings.CASSANDRA_UPDATE:
                    batch_query = BatchQuery(batch_type=BatchType.Unlogged, consistency=ConsistencyLevel.ONE)
                # add data streams
                for stream in stream_data_tuples:
                    ValidDataStorageByStream.batch(batch_query).create(source_key=source_key,
                                                                       stream_name=stream[0],
                                                                       insertion_time=insertion_time,
                                                                       stream_value=str(stream[1]),
                                                                       timestamp_in_data=timestamp_in_data,
                                                                       raw_value=str(stream[2]),
                                                                       multiplication_factor=str(stream[3]))
                # add data write history for user
                # TODO validated will change to false later
                DataWriteHistoryByUser.batch(batch_query).create(user_id=source.user.id,
                                                                 success=True,
                                                                 date=insertion_time.date(),
                                                                 ts=insertion_time,
                                                                 source_key=source_key,
                                                                 validated=True)
                # add data write history for source
                DataWriteHistoryBySource.batch(batch_query).create(source_key=source_key,
                                                                   success=True,
                                                                   ts=insertion_time,
                                                                   user_id=source.user.id,
                                                                   validated=True)

                batch_query.execute()

                if KAFKA_WRITE:
                    if transformed == 0: #if the request is not from the transformed data app
                        # ----------------------------------#
                        # Calling publish_to_kafka_broker
                        #logger.debug('Before calling kafka broker function from data_write')
                        data_dict_for_kafka = stream_data_dict
                        data_dict_for_kafka['source_key'] = source_key
                        data_dict_for_kafka['user_name'] = str(request.user)
                        data_dict_for_kafka['source_name'] = str(source.name)
                        data_dict_for_kafka['sensor_type'] = Sensor.objects.get(sourceKey=source_key).templateName
                        time_stamp_in_dict = data_dict_for_kafka.get("TIMESTAMP",None)

                        logger.debug(source_key)
                        logger.debug(time_stamp_in_dict)
                        try:
                            tz = pytz.timezone(source.dataTimezone)
                        except:
                            tz = pytz.timezone("UTC")
                        ####### Adding below lines to send all the timestamp in UTC to KAFKA
                        if time_stamp_in_dict:
                            try:
                                time_stamp_in_dict = parser.parse(time_stamp_in_dict)
                            except:
                                time_stamp_in_dict = time_stamp_in_dict
                            try:
                                time_stamp_in_dict = time_stamp_in_dict.astimezone(pytz.timezone("UTC"))
                            except:
                                try:
                                    time_stamp_in_dict = tz.localize(time_stamp_in_dict).astimezone(pytz.timezone("UTC"))
                                except:
                                    time_stamp_in_dict = None

                            data_dict_for_kafka["TIMESTAMP"] = time_stamp_in_dict
                        #########################################################################

                        if not time_stamp_in_dict:
                            time_stamp_in_dict = timestamp_in_data
                            try:
                                time_stamp_in_dict = parser.parse(time_stamp_in_dict)
                            except:
                                time_stamp_in_dict = time_stamp_in_dict
                            try:
                                time_stamp_in_dict = time_stamp_in_dict.astimezone(pytz.timezone("UTC"))
                            except:
                                try:
                                    time_stamp_in_dict = tz.localize(time_stamp_in_dict).astimezone(pytz.timezone("UTC"))
                                except:
                                    time_stamp_in_dict = None

                            data_dict_for_kafka["TIMESTAMP"] = timestamp_in_data

                        logger.debug("time_stamp_in_dict")
                        logger.debug(time_stamp_in_dict)
                        logger.debug(data_dict_for_kafka["TIMESTAMP"])

                        global kafka_producers
                        if not kafka_producers:
                            try:
                                kafka_producers = create_kafka_producers()
                                logger.debug('Created kafka producer from data_write')
                            except Exception as ex:
                                logger.debug("exception in create_kafka: %s"% str(ex))
                        for iWrite in range(len(kafka_producers)):
                            if KAFKA_WRITE_TO_HOSTS[iWrite] and kafka_producers[iWrite]:
                                try:
                                    kafka_producers[iWrite].send_message(topic='data_'+Sensor.objects.get(sourceKey=source_key).templateName,key=source_key,json_msg=data_dict_for_kafka,sync=True)
                                except Exception as ex:
                                    logger.debug("exception in data send_message: %s"% str(ex))
                            else:
                                logger.debug('kafka_producer is None or kafka producer ' + str(iWrite) + ' is False')
                        #logger.debug('After calling kafka broker function')
                        #logger.debug('message sent')
                        # ----------------------------------#
                # TODO Has to be changed later
                update_counters(source.user.id, source.sourceKey, timestamp_in_data, True, 1)
                n_entries += 1
            except:
                write_a_data_write_ttl(source.user.id, source.sourceKey,
                                       source.timeoutInterval,
                                       False, request_arrival_time)
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(source.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR,
                                            response_type, False,
                                            comments, source_key=source.sourceKey) if not is_external else settings.ERRORS.INTERNAL_SERVER_ERROR

        # data has been saved, send a response back
        # if actuation is enabled, it will be a JSON response - otherwise, it will be a plain text
        if source.actuationEnabled:
            try:
                # check the status of the actuation flag
                ack_flag = 0
                status = ActionsStorageByStream.objects.filter(source_key = source.sourceKey, acknowledgement = 0)
                if len(status) > 0:
                    ack_flag = 1
                # check the status of the config flag
                config_flag = 0
                status = ConfigStorageByStream.objects.filter(source_key = source.sourceKey, acknowledgement = 0)
                if len(status) > 0:
                    config_flag = 1
                if source.textMessageWithHTTP200:
                    response = JsonResponse({'action': ack_flag,'config': config_flag, 'textMessageWithHTTP200': source.textMessageWithHTTP200}, status=httplib.OK)
                else:
                    response = JsonResponse({'action': ack_flag,'config': config_flag}, status=httplib.OK)
            except Exception as E:
                return HttpResponse(status=httplib.INTERNAL_SERVER_ERROR)
        else:
            if is_external:
                response_message = {'status': httplib.OK}
                if source.textMessageWithHTTP200:
                    response_message['message'] = source.textMessageWithHTTP200
                write_a_data_write_ttl(source.user.id, source.sourceKey,
                                       source.timeoutInterval,
                                       True, request_arrival_time)
                log_a_success(source.user.id, request, 200,
                              request_arrival_time, source_key=source.sourceKey)
                return response_message
            else:
                if source.textMessageWithHTTP200:
                    response = HttpResponse(source.textMessageWithHTTP200, status=httplib.OK)
                else:
                    response = HttpResponse(status=httplib.OK)
        # TODO: log a data write for monitoring, logging and volume calculation - all of this would be offline process
        write_a_data_write_ttl(source.user.id, source.sourceKey,
                               source.timeoutInterval,
                               True, request_arrival_time)
        log_a_success(source.user.id, request, response.status_code,
                      request_arrival_time, source_key=source.sourceKey)
        return response
    except:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR,
                                                response_type, False,
                                                comments)  if not is_external else settings.ERRORS.INTERNAL_SERVER_ERROR

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

# used for solarrms app
def get_all_sources_data(sources,
                         starttime,
                         endtime,
                         union=True,
                         json=False,
                         ffill=False):
    order = ['timestamp']
    logger.debug(ffill)
    df_list = []
    # get the data
    for source in sources.keys():
        try:
            source_instance = Sensor.objects.get(sourceKey=source)
        except:
            logger.debug("no source")
            return -1
        # a hack for sterling and wilson to provide irradiance values in W/m2
        sterling = False
        if source_instance.user.id == 43:
            sterling = True
        for stream in sources[source]:
            try:
                stream_instance = Field.objects.get(source=source_instance, name=stream)
                if stream_instance.streamDataUnit:
                    index_name = "_".join([source_instance.name, stream + " (" + stream_instance.streamDataUnit + ")"])
                else:
                    index_name = "_".join([source_instance.name, stream])
            except:
                continue
            try:
                stream_data = ValidDataStorageByStream.objects.filter(source_key=source_instance.sourceKey,
                                                                      stream_name=stream,
                                                                      timestamp_in_data__gte=update_tz(starttime, source_instance.dataTimezone),
                                                                      timestamp_in_data__lte=update_tz(endtime, source_instance.dataTimezone)).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                timestamps = []
                values = []
                for data_point in stream_data:
                    udt = update_tz(data_point[1].replace(microsecond=0, second=0, tzinfo=pytz.UTC), str(source_instance.dataTimezone))
                    timestamps.append(str(udt))
                    if sterling and "IRRADIATION" in stream:
                        values.append(float(data_point[0])*1000.0)
                    else:
                        values.append(data_point[0])
                df_list.append(pd.DataFrame({index_name: values,
                                             'timestamp': timestamps}))
                order.append(index_name)
            except Exception as exc:
                logger.debug(exc)
                return -1
    # merge data points
    try:
        if len(df_list) >= 2:
            results = df_list[0]
            for i in range(1, len(df_list)):
                if union:
                    results = results.merge(df_list[i], how='outer', on='timestamp')
                else:
                    results = results.merge(df_list[i], how='inner', on='timestamp')
        else:
            results = df_list[0]

        sorted_results = results.sort(['timestamp'])
        results = sorted_results
        if ffill:
            updated_results = results.ffill(limit=1)
            results = updated_results

        if json:
            data = results.to_json()
        else:
            data = results.to_csv(date_format="%Y-%m-%d %H:%M:%S%Z",
                                  index=False,
                                  columns=order)
    except Exception as exc:
        logger.debug(exc)
        #comments = generate_exception_comments(sys._getframe().f_code.co_name)
        return -1
    return data


# used for achira app
def get_timeseries_data(user, starttime, endtime, exclude_streams, archived=False):
    try:
        sources = Sensor.objects.filter(user=user)
        data_points = {}
        for source in sources:
            for stream in source.fields.all():
                if stream.name not in exclude_streams:
                    data_records = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                           stream_name=stream.name,
                                                                           timestamp_in_data__gte=update_tz(starttime, source.dataTimezone),
                                                                           timestamp_in_data__lte=update_tz(endtime, source.dataTimezone))
                    for record in data_records:
                        updated_tz = update_tz(record.timestamp_in_data.replace(tzinfo=pytz.UTC), source.dataTimezone)
                        if str(updated_tz) in data_points.keys():
                            data_points[str(updated_tz)][stream.name] = record.stream_value
                        else:
                            data_points[str(updated_tz)] = {}
                            data_points[str(updated_tz)]['TIMESTAMP'] = str(updated_tz)
                            data_points[str(updated_tz)][stream.name] = record.stream_value
                            data_points[str(updated_tz)]["SOURCE_NAME"] = source.name
                            data_points[str(updated_tz)]["SOURCE_KEY"] = source.sourceKey

            for stream in source.errorfields.all():
                if stream.name not in exclude_streams:
                    data_records = ErrorStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                       stream_name=stream.name,
                                                                       timestamp_in_data__gte=update_tz(starttime, source.dataTimezone),
                                                                       timestamp_in_data__lte=update_tz(endtime, source.dataTimezone))
                    for record in data_records:
                        updated_tz = update_tz(record.timestamp_in_data.replace(tzinfo=pytz.UTC), source.dataTimezone)
                        if str(updated_tz) in data_points.keys():
                            data_points[str(updated_tz)][stream.name] = record.stream_value
                        else:
                            continue
                            data_points[str(updated_tz)] = {}
                            data_points[str(updated_tz)]['TIMESTAMP'] = str(updated_tz)
                            data_points[str(updated_tz)][stream.name] = record.stream_value
                            data_points[str(updated_tz)]["SOURCE_NAME"] = source.name
                            data_points[str(updated_tz)]["SOURCE_KEY"] = source.sourceKey

        data = []
        for ts in sorted(data_points):
            try:
                data_archive = (data_points[ts]["DATA_ARCHIVED"])
                if archived and data_archive == 'False':
                    continue
                elif archived is False and data_archive == 'True':
                    continue
                else:
                    pass
            except:
                continue
            dp = {}
            # dp['SOURCE_NAME'] = ts.split("#")[1]
            # dp['TIMESTAMP'] = ts.split("#")[0]
            # dp['SOURCE_KEY'] = ts.split("#")[2]
            # dp['SOURCE_UID'] = ts.split("#")[3]
            for k in data_points[ts].keys():
                dp[k] = data_points[ts][k]
            data.append(dp)
        return data
    except Exception as exc:
        logger.debug(exc)
        return -1


def mqtt_data_write(payload, request_arrival_time, source_key, user):
    try:
        try:
            # Do a DataSource lookup IMP - keep the user
            source = Sensor.objects.get(sourceKey=source_key)
        except Sensor.DoesNotExist:
            return settings.ERRORS.SOURCE_INACTIVE

        except Exception as exc:
            logger.debug(exc)
            return settings.ERRORS.INTERNAL_SERVER_ERROR

        if source.isActive is False:
            # TODO check if it's an invalid data or we should report a different error message
            write_a_data_write_ttl(source.user.id, source.sourceKey,
                                   source.timeoutInterval,
                                   False, request_arrival_time)
            return settings.ERRORS.SOURCE_INACTIVE

        # get sensor fields ordered by their position
        if source.dataFormat == 'CSV':
            data_fields = Field.objects.filter(source=source).order_by('streamPositionInCSV')
        else:
            data_fields = Field.objects.filter(source=source)

        if payload is None:
            write_a_data_write_ttl(source.user.id, source.sourceKey,
                                   source.timeoutInterval,
                                   False, request_arrival_time)
            return settings.ERRORS.ERROR_RETRIEVING_PAYLOAD

        # check for multiple entries and split
        data_values_list = split_payload(source, payload)
        if data_values_list is None:
            write_a_data_write_ttl(source.user.id, source.sourceKey,
                                   source.timeoutInterval,
                                   False, request_arrival_time)
            return settings.ERRORS.ERROR_SPLITTING_RECORDS

        # parse entries, error in parsing even a single one will return an error
        n_entries = 0
        for data_values in data_values_list:
            # split single entry into multiple fields
            data_values = split_single_entry(source, data_values)
            if data_values is None:
                write_a_data_write_ttl(source.user.id, source.sourceKey,
                                       source.timeoutInterval,
                                       False, request_arrival_time)
                return settings.ERRORS.ERROR_SPLITTING_RECORDS

            #check if the data write has happned from the kafka-based transformation app. If yes, do not send the data
            # back to the same kafka topic. At this point, teh transformation is mainly expected on data write and not on event, action or config
            try:
                transformed = 0
                transformed_key = 'transformed'
                if source.dataFormat == 'JSON':
                    transformed = data_values.get(transformed_key,0)
                    try:
                        if transformed_key in data_values:
                            data_values.pop(transformed_key, None)
                    except Exception as ex:
                        continue
            except Exception as ex:
                continue

            try:
                try:
                    # check if the length of both data fields and values are same,
                    # otherwise raise an assertion error
                    if source.dataFormat == 'CSV':
                        assert(len(data_fields) == len(data_values))
                    elif source.dataFormat == 'JSON' or source.dataFormat == 'ATOLL':
                        stream_names = [field.name for field in data_fields]
                        for stream_name in data_values.keys():
                            assert(stream_name in stream_names)

                except AssertionError:
                    write_a_data_write_ttl(source.user.id, source.sourceKey,
                                           source.timeoutInterval,
                                           False, request_arrival_time)
                    return settings.ERRORS.INVALID_DATA

                # extract date/time field if available
                extracted_timestamp_from_data = {}
                stream_data_tuples = []
                stream_data_dict = dict()

                # iterate through the fields, extract timestamp (if available) and do a type level validation
                for field_number in range(len(data_fields)):
                    # validate the field
                    # csv format
                    if source.dataFormat == "CSV":
                        updated_value, validation_output = csv_data_type_validation(data_fields[field_number],
                                                                                    data_values[field_number])
                    # json format
                    elif source.dataFormat == "JSON":
                        stream_instance = data_fields[field_number]
                        try:
                            updated_value, validation_output = json_data_type_validation(stream_instance,
                                                                                         data_values[stream_instance.name])
                        except Exception as E:
                            continue
                    # atoll format validation (same as csv)
                    elif source.dataFormat == "ATOLL":
                        stream_instance = data_fields[field_number]
                        try:
                            updated_value, validation_output = atoll_data_type_validation(stream_instance,
                                                                                         data_values[stream_instance.name])
                            logger.debug("*****")
                            logger.debug("atoll stream validation", str(stream_instance))
                            logger.debug("atoll stream validation", str(updated_value))
                            logger.debug("atoll stream validation", str(validation_output))
                        except Exception as E:
                            continue
                    else:
                        updated_value, validation_output = 0, False

                    if validation_output is True:
                        raw_value, processed_value, mf = get_processed_values(data_fields[field_number], updated_value)
                        stream_data_tuples.append((data_fields[field_number].name, str(processed_value), str(raw_value), str(mf)))
                        stream_data_dict[data_fields[field_number].name] = processed_value
                        if data_fields[field_number].streamDataType in ("TIMESTAMP", "DATE", "TIME"):
                            # It's a datetime/date/time field
                            # keep as a datetime object for ts field of the entry
                            extracted_timestamp_from_data[data_fields[field_number].streamDataType] = updated_value
                    else:
                        write_a_data_write_ttl(source.user.id, source.sourceKey,
                                               source.timeoutInterval,
                                               False, request_arrival_time)
                        return settings.ERRORS.STREAM_PARSING_FAILED

                # If timestamp not present, use timezone.now()
                #insertion_time = timezone.now()
                # keep insertion time in source's timezone
                try:
                    insertion_time = timezone.now()
                    # astimezone does the conversion and updates the tzinfo part
                    insertion_time = insertion_time.astimezone(pytz.timezone(source.dataTimezone))
                except Exception as exc:
                    insertion_time = timezone.now()
                try:
                    timestamp_in_data = extracted_timestamp_from_data["TIMESTAMP"]
                except KeyError:
                    try:
                        timestamp_in_data = datetime.datetime.combine(extracted_timestamp_from_data["DATE"],
                                                                      extracted_timestamp_from_data["TIME"])
                    except:
                        timestamp_in_data = insertion_time

                # add tzinfo info in timestamp_in_data if absent
                try:
                    if timestamp_in_data.tzinfo is None:
                        tz = pytz.timezone(str(source.dataTimezone))
                        # localize only adds tzinfo and does not change the dt value
                        timestamp_in_data = tz.localize(timestamp_in_data)
                except:
                    pass

                if timestamp_in_data > insertion_time + datetime.timedelta(seconds=300):
                    write_a_data_write_ttl(source.user.id, source.sourceKey,
                                           source.timeoutInterval,
                                           False, request_arrival_time)
                    return settings.ERRORS.FUTURE_TIMESTAMP

                # TODO - decide: we can perhaps create a single batch request now, i.e. in case of multiple
                # TODO - entries, either all succeed or None
                # Now populate the database - create a Batch Request
                batch_query = BatchQuery()
                # add data streams
                for stream in stream_data_tuples:
                    ValidDataStorageByStream.batch(batch_query).create(source_key=source_key,
                                                                       stream_name=stream[0],
                                                                       insertion_time=insertion_time,
                                                                       stream_value=str(stream[1]),
                                                                       timestamp_in_data=timestamp_in_data,
                                                                       raw_value=str(stream[2]),
                                                                       multiplication_factor=str(stream[3]))
                # add data write history for user
                # TODO validated will change to false later
                DataWriteHistoryByUser.batch(batch_query).create(user_id=source.user.id,
                                                                 success=True,
                                                                 date=insertion_time.date(),
                                                                 ts=insertion_time,
                                                                 source_key=source_key,
                                                                 validated=True)
                # add data write history for source
                DataWriteHistoryBySource.batch(batch_query).create(source_key=source_key,
                                                                   success=True,
                                                                   ts=insertion_time,
                                                                   user_id=source.user.id,
                                                                   validated=True)

                batch_query.execute()

                if KAFKA_WRITE:
                    if transformed == 0: #if the request is not from the transformed data app
                        # ----------------------------------#
                        # Calling publish_to_kafka_broker
                        #logger.debug('Before calling kafka broker function from data_write')
                        data_dict_for_kafka = stream_data_dict
                        data_dict_for_kafka['source_key'] = source_key
                        data_dict_for_kafka['user_name'] = str(user)
                        data_dict_for_kafka['source_name'] = str(source.name)
                        data_dict_for_kafka['sensor_type'] = Sensor.objects.get(sourceKey=source_key).templateName
                        time_stamp_in_dict = data_dict_for_kafka.get("TIMESTAMP",None)
                        if not time_stamp_in_dict:
                            data_dict_for_kafka["TIMESTAMP"] = timestamp_in_data
                        global kafka_producers
                        if not kafka_producers:
                            try:
                                kafka_producers = create_kafka_producers()
                                logger.debug('Created kafka producer from data_write')
                            except Exception as ex:
                                logger.debug("exception in create_kafka: %s"% str(ex))
                        for iWrite in range(len(kafka_producers)):
                            if KAFKA_WRITE_TO_HOSTS[iWrite] and kafka_producers[iWrite]:
                                try:
                                    kafka_producers[iWrite].send_message(topic='data_'+Sensor.objects.get(sourceKey=source_key).templateName,key=source_key,json_msg=data_dict_for_kafka,sync=True)
                                except Exception as ex:
                                    logger.debug("exception in data send_message: %s"% str(ex))
                            else:
                                logger.debug('kafka_producer is None or kafka producer ' + str(iWrite) + ' is False')
                        #logger.debug('After calling kafka broker function')
                        #logger.debug('message sent')
                        # ----------------------------------#
                # TODO Has to be changed later
                update_counters(source.user.id, source.sourceKey, timestamp_in_data, True, 1)
                n_entries += 1
            except:
                write_a_data_write_ttl(source.user.id, source.sourceKey,
                                       source.timeoutInterval,
                                       False, request_arrival_time)
                return settings.ERRORS.INTERNAL_SERVER_ERROR

        # data has been saved, send a response back
        # if actuation is enabled, it will be a JSON response - otherwise, it will be a plain text
        if source.actuationEnabled:
            try:
                # check the status of the actuation flag
                ack_flag = 0
                status = ActionsStorageByStream.objects.filter(source_key = source.sourceKey, acknowledgement = 0)
                if len(status) > 0:
                    ack_flag = 1
                # check the status of the config flag
                config_flag = 0
                status = ConfigStorageByStream.objects.filter(source_key = source.sourceKey, acknowledgement = 0)
                if len(status) > 0:
                    config_flag = 1
                if source.textMessageWithHTTP200:
                    response = JsonResponse({'action': ack_flag,'config': config_flag, 'textMessageWithHTTP200': source.textMessageWithHTTP200}, status=httplib.OK)
                else:
                    response = JsonResponse({'action': ack_flag,'config': config_flag}, status=httplib.OK)
            except Exception as E:
                return HttpResponse(status=httplib.INTERNAL_SERVER_ERROR)
        else:
            response = httplib.OK, source.textMessageWithHTTP200
        # TODO: log a data write for monitoring, logging and volume calculation - all of this would be offline process
        write_a_data_write_ttl(source.user.id, source.sourceKey,
                               source.timeoutInterval,
                               True, request_arrival_time)
        return response
    except:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        logger.debug(comments)
        return settings.ERRORS.INTERNAL_SERVER_ERROR
