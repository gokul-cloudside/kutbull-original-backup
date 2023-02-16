import csv
from django.http import HttpResponse
import json
from rest_framework.views import APIView


from utils.errors import generate_exception_comments, log_and_return_error

from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions

from dashboards.mixins import ProfileDataMixin, ProfileDataInAPIs

from dataglen.models import Field
from dataglen.models import ValidDataStorageByStream

from logger.views import log_a_success
import sys, dateutil, logging, pytz

from .models import IndependentInverter
from .serializers import PlantSerializer, InverterSerializer, InverterDataValues
from .solarutils import filter_solar_plants
from .models import SolarPlant
from solarutils import get_all_inverters_data
from django.http import StreamingHttpResponse

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


def utc_to_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.localize(tz)
        else:
            dt = dt.replace(tzinfo=pytz.UTC)
            return dt.astimezone(tz)
    except:
        return dt

class CSVDownload(ProfileDataMixin, APIView):
    
    def get(self, request, plant_inverter_key=None, plant_slug=None, **kwargs):
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            plant = None
            for plant_instance in plants:
                if plant_instance.slug == plant_slug:
                    plant = plant_instance
            if plant is None:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            inverter = IndependentInverter.objects.get(plant=plant,
                                                       sourceKey=plant_inverter_key)

        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                # convert into datetime objects
                #TODO fix this - find out a way to ensure we get a date, month and year at least
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, "Asia/Kolkata")
                et = update_tz(et, "Asia/Kolkata")
            except Exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            source_streams = [item for sublist in Field.objects.filter(source=inverter).order_by('name').values_list('name') for item in sublist]
            try:
                streams = request.query_params["streamNames"].split(",")
                for stream in streams:
                    assert(stream in source_streams)
            except AssertionError:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            except KeyError:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.STREAM_NAME_MISSING, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            streams_data_dicts = []

            for stream_num in range(len(streams)):
                stream = streams[stream_num]
                stream_data = ValidDataStorageByStream.objects.filter(source_key=plant_inverter_key,
                                                                      stream_name=stream,
                                                                      timestamp_in_data__gte=st,
                                                                      timestamp_in_data__lte=et).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                # populate data
                values = [item[0] for item in stream_data]
                # populate timestamps
                timestamps = [utc_to_tz(item[1], "Asia/Kolkata").isoformat() for item in stream_data]
                # populate the outer array
                streams_data_dicts.append({'name': stream,
                                           'values': values,
                                           'timestamps': timestamps})

            file_name = "_".join([inverter.name, str(st), str(et), ".csv"]).replace(" ", "_")
            response_csv = HttpResponse(content_type="text/csv")
            response_csv['Content-Disposition'] = 'attachment; filename=' + file_name
            writer = csv.writer(response_csv)

            reply = InverterDataValues(data={'sourceKey': inverter.name,
                                             'streams': streams_data_dicts})
            if reply.is_valid():
                response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments=None)
                response_json = json.dumps(response.data)
                resp_dict = json.loads(response_json)
                len_stream = len(resp_dict['streams'])
                source_details = []
                source_details.append('Inverter Name')
                source_details.append(inverter.name)
                writer.writerow(source_details)
                stream_names = []
                stream_names_values = []
                stream_names.append("Timestamp")
                for i in range(len_stream):
                    stream_names_values.append(resp_dict['streams'][i]['name'])
                stream_names.extend(stream_names_values)
                logger.debug(stream_names)
                writer.writerow(stream_names)
                timestamp_length = []
                for i in range(len_stream):
                    timestamp_length.append(len(resp_dict['streams'][i]['timestamps']))
                logger.debug(timestamp_length)
                logger.debug(max(timestamp_length))
                values_list = [[] for i in range(len_stream)]
                timestamp_list = []
        
                for i in range(len_stream):
                    if(len(resp_dict['streams'][i]['values']) == max(timestamp_length)):
                        for j in range(len(resp_dict['streams'][i]['values'])):
                            timestamp_list.append(resp_dict['streams'][i]['timestamps'][j])
                        break
                for i in range(len(values_list)):
                    for j in range(max(timestamp_length)):
                        if(len(resp_dict['streams'][i]['values'])>0):
                            values_list[i].append(resp_dict['streams'][i]['values'][j])
                        else:
                            values_list[i].append("")
                logger.debug(len(timestamp_list))
                for i in range(len(timestamp_list)):
                    final_values = []
                    final_values.append(timestamp_list[i])
                    for j in range(len(values_list)):                       
                        final_values.append(values_list[j][i])
                    writer.writerow(final_values)
                return response_csv
            else:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
        except Exception as exception:
            logger.debug(str(exception))
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class CSVDownloadUpdated(ProfileDataInAPIs, APIView):

    def get(self, request, plant_slug=None, **kwargs):
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            if plant not in plants:
                raise ObjectDoesNotExist
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:
            try:
                inverters_names = request.query_params["inverters"].split(",")
                # check al the inverter names are there
                inverters = []
                for inverter_name in inverters_names:
                    inverters.append(plant.independent_inverter_units.get(sourceKey=inverter_name))
                # check other parameters are also there
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                streamNames = request.query_params["streamNames"].split(",")
                assert(len(streamNames) == 1)
                # convert st/et into datetime objects and as IST if there's no tzinfo
                #TODO fix this - find out a way to ensure we get a date, month and year at least
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, "Asia/Kolkata")
                et = update_tz(et, "Asia/Kolkata")
            except KeyError:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            except Exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            except IndependentInverter.DoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            isFile = False
            try:
                isFile = request.query_params["file"]
            except:
                pass

            if isFile:
                data = get_all_inverters_data(inverters,streamNames, st, et, True, False)
                file_name = "_".join([streamNames[0], str(st), str(et), ".csv"]).replace(" ", "_")
                response_csv = HttpResponse(content_type="text/csv")
                response_csv['Content-Disposition'] = 'attachment; filename=' + file_name
                writer = csv.writer(response_csv)
                for line in data[streamNames[0]].split("\n"):
                    writer.writerow(line.split(","))
                return response_csv
            else:
                data = get_all_inverters_data(inverters,streamNames, st, et, True, False)
                response_text = HttpResponse(data[streamNames[0]])
                return response_text

        except Exception as exception:
            logger.debug(str(exception))
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

