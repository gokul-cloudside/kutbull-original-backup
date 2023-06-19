from utils.errors import generate_exception_comments, log_and_return_error

from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions

from dashboards.mixins import ProfileDataInAPIs

from dataglen.models import Field
from dataglen.models import ValidDataStorageByStream
from organizations.models import OrganizationUser, Organization
from logger.views import log_a_success
import sys, dateutil, logging
from collections import OrderedDict
from utils.multiprocess import get_plant_live_ajb_status_mp
import pytz
from solarrms.models import IndependentInverter, EnergyGenerationTable, PlantPowerTable, PlantMetaSource, PerformanceRatioTable,\
    SolarGroup, HistoricEnergyValues, CUFTable, PVSystInfo, EnergyLossTable, KWHPerMeterSquare, SpecificYieldTable, \
    PlantSummaryDetails, EnergyMeter, Transformer, AJB, WeatherData
from solarrms.serializers import PlantSerializer, InverterSerializer, InverterDataValues, \
    EnergyDataValues, PowerDataValues, PerformanceRatioValues, PlantStatusSummary, TicketSerializer, \
    FollowUpSerializer, TicketChangeSerializer, FollowUpTicketChangeSerializer, TicketAssociationsSerializer,\
    TicketPatchSerializer, CUFValueSerializer, PlantClientSummary, EnergyLossValues, V1_PlantClientSummary, \
    V1_PlantStatusSummary, V1_InverterLiveStatus, SpecificYieldValues, V1_AJBLiveStatus, V1_MobileClientSummary
from solarrms.solarutils import filter_solar_plants, calculate_total_plant_generation, get_power_irradiation, \
    get_plant_device_details, get_expected_energy, get_client_device_details_across_plants,\
    get_daily_or_hourly_weather_data, get_aggregated_insolation_values, get_inverters_stored_energy_from_power,\
    simpleExcelFormatting,merge_all_sheets,merge_all_sheets2,manipulateColumnNames,manipulateColumnNames2,excelConversion,excelNoData
from solarrms.settings import AGGREGATOR_CHOICES, LAST_CAPACITY_DAYS, ENERGY_METER_STREAM_UNITS, ENERGY_METER_STREAM_UNIT_FACTOR
from kutbill.settings import TIMESTAMP_TYPES, DATA_COUNT_PERIODS
import pytz
from datetime import datetime, timedelta
from monitoring.views import get_user_data_monitoring_status
from events.serializers import ErrorByTimeValues, PlantErrorByTimeValues
from events.models import Events, EventsByError, EventsByTime
from solarrms.models import SolarPlant, PlantCompleteValues, PredictedValues, HistoricEnergyValues, PredictionData,\
    NewPredictionData, SolarField, EnergyLossTable, InverterStatusMappings, AJBStatusMappings, HistoricEnergyValuesWithPrediction
from solarrms.solarutils import get_plant_power, get_plant_energy, \
    get_aggregated_energy, get_energy_meter_values,get_generation_report, get_groups_power, get_TotalYield_of_inverters, \
    get_network_down_time_from_heartbeat, get_minutes_aggregated_energy, get_minutes_aggregated_power, \
    get_predicted_energy_values_timeseries, get_new_generation_report
from helpdesk.models import Ticket, Queue, FollowUp, TicketChange, TicketAssociation, get_alarm_code_name, get_solar_status_code_mapping
from helpdesk.dg_functions import update_ticket, get_plant_tickets, get_plant_tickets_date
from dateutil import parser
import json, collections
import calendar
import ast
from dashboards.utils import is_owner
from errors.models import ErrorStorageByStream

import csv
from django.http import HttpResponse, StreamingHttpResponse
from solarrms.cron_solar_events import check_network_for_virtual_gateways
import copy
from solarrms.cron_plant_all_details import convert_values_to_common_unit
from helpdesk.models import Ticket, TicketAssociation
from solarrms.solar_reports import get_multiple_sources_multiple_streams_data_merge_pandas, \
    get_multiple_sources_multiple_streams_data, get_multiple_inverters_single_stream_data, DEFAULT_STREAM_UNIT, \
    get_plant_summary_parameters, get_single_device_multiple_streams_data, get_monthly_report_values, get_yearly_report_values
from dataglen.models import Sensor
from solarrms.solarutils import sorted_nicely, convert_new_energy_data_format_to_old_format
from solarrms.data_aggregation import get_single_device_multiple_streams_data_aggregated, get_multiple_sources_multiple_streams_data_merge_pandas_aggregation,get_single_stream_multiple_sources_data_aggregated
import StringIO
import pandas as pd
import json
from django.views.decorators.clickjacking import xframe_options_exempt
from solarrms.prediction_analysis import calculate_penalty, get_grid_down_time_dsm
from solarrms.solar_reports import get_daily_report_values_portfolio, get_multiple_devices_single_stream_data
from features.models import RoleAccess
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

TICKET_PRIOTITY = {"1" : "Critical",
                   "2" : "High",
                   "3" : "Normal",
                   "4" : "Low",
                   "5" : "Very Low"}
TICKET_STATUS = {"1" : "Open",
                 "2" : "Reopened",
                 "3" : "Resolved",
                 "4" : "Closed",
                 "5" : "Duplicate",
                 "6" : "Acknowledged"}

EXCLUDE_REPORT_STREAMS = ['LIVE', 'AGGREGATED', 'AGGREGATED_START_TIME', 'AGGREGATED_END_TIME', 'AGGREGATED_COUNT']
EXCLUDE_VISUALIZATION_STREAMS = ['LIVE', 'AGGREGATED', 'AGGREGATED_START_TIME', 'AGGREGATED_END_TIME', 'AGGREGATED_COUNT','TIMESTAMP']
def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
      #      return tz.localize(dt)
        else:
            return tz.localize(dt)
    except:
        return dt

unit_conversion = {'GWh' : 1000000,
                   'MWh' : 1000,
                   'kWh' : 1}

def make_prediction_unit_same_as_generation(generation_list, prediction_list):
    try:
        conversion_scheme = {'kWh_MWh': 0.001,
                             'kWh_GWh': 0.000001,
                             'MWh_kWh': 1000,
                             'GWh_kWh': 1000000,
                             'kWh_kWh': 1,
                             'MWh_MWh': 1,
                             'GWh_GWh': 1}

        for index in range(len(prediction_list)):
           try:
               prediction_unit = str(prediction_list[index]).split(' ')[1]
               generation_unit = str(generation_list[index]).split(' ')[1]
               conversion_unit = str(prediction_unit)+'_'+str(generation_unit)
               prediction_value = str(prediction_list[index]).split(' ')[0]
               final_prediction_value = float(prediction_value) * conversion_scheme[conversion_unit]
               prediction_list[index] = str(final_prediction_value) + ' ' + str(generation_unit)
           except Exception as exception:
               print(str(exception))
               continue
        return prediction_list
    except Exception as exception:
        print(str(exception))

def get_energy_data(identifier, request):
    request_arrival_time = timezone.now()
    try:
        try:
            st = request.query_params["startTime"]
            et = request.query_params["endTime"]
            aggregator = request.query_params["aggregator"]
            try :
                meter = int(request.query_params["meter"])
            except:
                meter = False
            offline = int(request.query_params.get("offline", 0))
            try:
                split = int(request.query_params["split"])
            except:
                split = False

            #old_report_summary = int(request.query_params.get("old_report_summary", 1))

            # convert into datetime objects
            #TODO fix this - find out a way to ensure we get a date, month and year at least
            st = dateutil.parser.parse(st)
            et = dateutil.parser.parse(et)
            assert(aggregator in AGGREGATOR_CHOICES)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            logger.debug(comments)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        try:
            user = request.user
            organization_user = user.organizations_organizationuser.all()[0]
        except Exception as exception:
            return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(str(exception))

        try:
            plant = SolarPlant.objects.get(slug=identifier.split("_")[1])
        except:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, {})

        try:
            st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
            et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
        except:
            st = update_tz(st, "Asia/Kolkata")
            et = update_tz(et, "Asia/Kolkata")

        ctp = None
        if aggregator == "HOUR":
            ctp = DATA_COUNT_PERIODS.HOUR
        elif aggregator == "DAY":
            ctp = DATA_COUNT_PERIODS.DAILY
        elif aggregator == "WEEK":
            ctp = DATA_COUNT_PERIODS.WEEK
        elif aggregator == "FIVE_MINUTES":
            ctp = DATA_COUNT_PERIODS.FIVE_MINTUES
        elif aggregator == "MONTH":
            ctp = DATA_COUNT_PERIODS.MONTH

        logger.debug(split)
        if split:
            # if int(old_report_summary)==1:
            #     data = get_generation_report(st, et, plant, aggregator)
            # else:
            #     data = get_new_generation_report(st, et, plant)
            data = get_new_generation_report(st, et, plant)
            return Response(data, status=status.HTTP_200_OK)

        if aggregator == "FIVE_MINUTES":
            values = get_plant_energy(st, et, plant, aggregator)
        else:
            '''data = EnergyGenerationTable.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                        count_time_period = ctp,
                                                        identifier = identifier,
                                                        ts__gte=st,
                                                        ts__lt=et).limit(0).values_list('energy', 'ts')

            values = [{'energy': entry[0], 'timestamp':entry[1]} for entry in data]'''
            if meter == 1 and (aggregator == "DAY" or aggregator == "MONTH"):
                values = get_energy_meter_values(st, et, plant, aggregator)
            elif offline == 1 and (aggregator == 'DAY' or aggregator == 'MONTH'):
                try:
                    values = []
                    flag = False
                    count_time_period = settings.DATA_COUNT_PERIODS.DAILY if aggregator == 'DAY' else settings.DATA_COUNT_PERIODS.MONTH
                    energy_values = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                      count_time_period=count_time_period,
                                                                                      identifier=plant.slug,
                                                                                      ts__gte=st,
                                                                                      ts__lte=et).order_by('-ts').values_list('energy','ts','predicted_energy','lower_bound','upper_bound')

                    if len(plant.pvsyst_info.all())>0:
                        pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                           parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                           timePeriodType='MONTH',
                                                                           timePeriodDay=0,
                                                                           timePeriodYear=st.year).values_list('timePeriodValue', 'parameterValue')
                        if len(pv_sys_info_generation) == 0:
                            pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                               parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                               timePeriodType='MONTH',
                                                                               timePeriodDay=0,
                                                                               timePeriodYear=0).values_list('timePeriodValue', 'parameterValue')

                        plant_capacity = plant.capacity
                        flag = True
                    for value in energy_values:
                        current_value = {}
                        current_value['energy'] = value[0]
                        current_value['timestamp'] = value[1]
                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                            current_value['predicted_energy'] = value[2]
                            current_value['lower_bound'] = value[3]
                            current_value['upper_bound'] = value[4]
                        recent_time = value[1]
                        recent_time = pytz.utc.localize(recent_time)
                        if plant.metadata.plantmetasource:
                            recent_time = recent_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        current_month = recent_time.month
                        if flag and pv_sys_info_generation[current_month-1][1] is not None:
                            if aggregator == 'DAY':
                                pvsyst_generation = pv_sys_info_generation[current_month-1][1] * plant_capacity
                                logger.debug(pvsyst_generation)
                            elif aggregator == 'MONTH':
                                pvsyst_generation = pv_sys_info_generation[current_month-1][1] * plant_capacity * calendar.monthrange(recent_time.year, recent_time.month)[1]
                            else:
                                pass
                            current_value['pvsyst_generation'] = pvsyst_generation
                        values.append(current_value)
                    current_time = timezone.now()
                    current_time = update_tz(current_time, "Asia/Kolkata")
                    initial_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    initial_time = update_tz(initial_time, pytz.utc._tzname)
                    if aggregator == 'DAY':
                        last_timestamp = values[len(values)-1]['timestamp']
                        last_timestamp = pytz.utc.localize(last_timestamp)
                        end_time = update_tz(et, pytz.utc._tzname)
                        if len(energy_values) == 0 or (last_timestamp!=initial_time and end_time>initial_time):
                            current_energy_values = get_aggregated_energy(initial_time, current_time, plant, aggregator)
                            predicted_energy_values = get_expected_energy(str(plant.slug), 'PLANT', initial_time, current_time)
                            current_value = {}
                            if current_energy_values and len(current_energy_values)>0:
                                current_value['energy'] = current_energy_values[len(current_energy_values)-1]['energy']
                                current_value['timestamp'] = initial_time
                                if predicted_energy_values and len(predicted_energy_values)>0:
                                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                                        current_value['predicted_energy'] = predicted_energy_values[0]
                                        current_value['lower_bound'] = predicted_energy_values[1]
                                        current_value['upper_bound'] = predicted_energy_values[2]
                                if flag and pv_sys_info_generation[current_time.month-1][1] is not None:
                                    pvsyst_generation = pv_sys_info_generation[current_time.month-1][1] * plant_capacity
                                    current_value['pvsyst_generation'] = pvsyst_generation
                                values.append(current_value)
                        # elif str(energy_values[len(energy_values)-1][1]) != str(initial_time).split("+",2)[0] and \
                        #         (et.month == current_time.month+1 or et.month == current_time.month and et.day != 1):
                        #     current_energy_values = get_aggregated_energy(initial_time, current_time, plant, aggregator)
                        #     current_value = {}
                        #     if current_energy_values and len(current_energy_values)>0:
                        #         current_value['energy'] = current_energy_values[len(current_energy_values)-1]['energy']
                        #         current_value['timestamp'] = initial_time
                        #         if flag and pv_sys_info_generation[current_time.month-1][1] is not None:
                        #             pvsyst_generation = pv_sys_info_generation[current_time.month-1][1] * plant_capacity
                        #             current_value['pvsyst_generation'] = pvsyst_generation
                        #         values.append(current_value)
                        # elif float(energy_values[len(energy_values)-1][0]) == 0 and len(energy_values)!= calendar.monthrange(st.year, st.month)[1]:
                        #     current_energy_values = get_aggregated_energy(initial_time, current_time, plant, aggregator)
                        #     current_value = {}
                        #     if current_energy_values and len(current_energy_values)>0:
                        #         current_value['energy'] = current_energy_values[len(current_energy_values)-1]['energy']
                        #         current_value['timestamp'] = initial_time
                        #         if flag and pv_sys_info_generation[current_time.month-1][1] is not None:
                        #             pvsyst_generation = pv_sys_info_generation[current_time.month-1][1] * plant_capacity
                        #             current_value['pvsyst_generation'] = pvsyst_generation
                        #         values.remove(values[len(values)-1])
                        #         values.append(current_value)
                        # else:
                        #     pass
                    elif aggregator == 'MONTH':
                        current_time_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                        current_time_month = update_tz(current_time_month, pytz.utc._tzname)
                        end_time = update_tz(et, pytz.utc._tzname)
                        if current_time> end_time:
                            pass
                        elif str(energy_values[len(energy_values)-1][1]) != str(current_time_month).split("+",2)[0] and et.day != 1:
                            current_energy_values = get_aggregated_energy(initial_time, current_time, plant, aggregator)
                            current_value = {}
                            if current_energy_values and len(current_energy_values)>0:
                                current_value['energy'] = current_energy_values[len(current_energy_values)-1]['energy']
                                current_value['timestamp'] = current_time_month
                                if flag and pv_sys_info_generation[current_time.month-1][1] is not None:
                                    pvsyst_generation = pv_sys_info_generation[current_time.month-1][1] * plant_capacity * calendar.monthrange(current_time.year, current_time.month)[1]
                                    current_value['pvsyst_generation'] = pvsyst_generation
                                values.append(current_value)
                        else:
                            current_energy_values = get_aggregated_energy(initial_time, current_time, plant, aggregator)
                            current_value = {}
                            if current_energy_values and len(current_energy_values)>0:
                                current_value['energy'] = energy_values[len(energy_values)-1][0] + float(current_energy_values[len(current_energy_values)-1]['energy'])
                                current_value['timestamp'] = current_time_month
                                if flag and pv_sys_info_generation[current_time.month-1][1] is not None:
                                    pvsyst_generation = pv_sys_info_generation[current_time.month-1][1] * plant_capacity * calendar.monthrange(current_time.year, current_time.month)[1]
                                    current_value['pvsyst_generation'] = pvsyst_generation
                                values.remove(values[len(values)-1])
                                values.append(current_value)
                except Exception as exception:
                    logger.debug(str(exception))
            else:
                values = get_aggregated_energy(st, et, plant, aggregator)

        energy_final_values = []
        timestamp_final_values = []
        pvsysyt_final_values = []
        predicted_energy_final_values = []
        lower_bound_final_values = []
        upper_bound_final_values = []
        for i in range(len(values)):
            energy_final_values.append(fix_generation_units(float(values[i]['energy'])))
            timestamp_final_values.append(values[i]['timestamp'])
            if flag:
                pvsysyt_final_values.append(fix_generation_units(float(values[i]['pvsyst_generation'])))

            if aggregator == 'DAY':
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                    predicted_energy_final_values.append(fix_generation_units(float(values[i]['predicted_energy'])))
                    lower_bound_final_values.append(fix_generation_units(float(values[i]['lower_bound'])))
                    upper_bound_final_values.append(fix_generation_units(float(values[i]['upper_bound'])))

        common_unit_energy_values = convert_values_to_common_unit(energy_final_values)
        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            common_unit_predicted_energy_values = convert_values_to_common_unit(predicted_energy_final_values)
            common_unit_lower_bound_energy_values = convert_values_to_common_unit(lower_bound_final_values)
            common_unit_upper_bound_energy_values = convert_values_to_common_unit(upper_bound_final_values)

        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            if len(common_unit_predicted_energy_values)>0:
                final_common_unit_predicted_energy_values = make_prediction_unit_same_as_generation(common_unit_energy_values, common_unit_predicted_energy_values)

        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            if len(common_unit_lower_bound_energy_values)>0:
                final_common_unit_lower_bound_energy_values = make_prediction_unit_same_as_generation(common_unit_energy_values, common_unit_lower_bound_energy_values)

        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            if len(common_unit_upper_bound_energy_values)>0:
                final_common_unit_upper_bound_energy_values = make_prediction_unit_same_as_generation(common_unit_energy_values, common_unit_upper_bound_energy_values)

        if flag:
            common_unit_pvsyst_values = convert_values_to_common_unit(pvsysyt_final_values)

        if len(pvsysyt_final_values)>0:
            final_common_unit_pvsyst_values = make_prediction_unit_same_as_generation(common_unit_energy_values, common_unit_pvsyst_values)

        final_values = []
        for i in range(len(common_unit_energy_values)):
            final_values_temp = {}
            final_values_temp['energy'] = common_unit_energy_values[i]
            if flag:
                try:
                    final_values_temp['pvsyst_generation'] = final_common_unit_pvsyst_values[i]
                except:
                    pass
            final_values_temp['timestamp'] = timestamp_final_values[i]
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                if len(common_unit_predicted_energy_values)>0:
                    final_values_temp['predicted_energy'] = final_common_unit_predicted_energy_values[i]
                    final_values_temp['lower_bound'] = final_common_unit_lower_bound_energy_values[i]
                    final_values_temp['upper_bound'] = final_common_unit_upper_bound_energy_values[i]

            final_values.append(final_values_temp)

        reply = EnergyDataValues(data=final_values, many=True)
        #reply = EnergyDataValues(data=values, many=True)
        if reply.is_valid():
            response = Response(reply.data,
                                status=status.HTTP_200_OK)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, comments=None)
            return response
        else:
            logger.debug(reply.errors)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, {})
    except Exception as exception:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        logger.debug(comments)
        return log_and_return_error(request.user.id, request, request_arrival_time,
                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                    False, comments)


def get_power_data(plant_slug, request):
    request_arrival_time = timezone.now()
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
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            logger.debug(comments)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
        except:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, {})

        values = get_plant_power(st, et, plant)
        reply = PowerDataValues(data=values, many=True)
        if reply.is_valid():
            response = Response(reply.data,
                                status=status.HTTP_200_OK)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, comments=None)
            return response
        else:
            logger.debug(reply.errors)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, {})
    except Exception as exception:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        logger.debug(comments)
        return log_and_return_error(request.user.id, request, request_arrival_time,
                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                    False, comments)


class PlantsViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'slug'

    def list(self, request, **kwargs):
        """
            Get a list of solar plants.
            ---
            request_serializer: PlantSerializer
            response_serializer: PlantSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 401
                  message : Not authenticated
                - code : 400
                  message : Bad request
        """
        all_plants = self.request.query_params.get("all_plants","FALSE")
        if str(all_plants).upper() == 'TRUE':
            plants = SolarPlant.objects.all()
        else:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
        for plant in plants:
            try:
                setattr(plant, "timezone", plant.metadata.plantmetasource.dataTimezone)
            except:
                setattr(plant, "timezone", "Asia/Kolkata")
        request_arrival_time = timezone.now()
        serializer = PlantSerializer(plants, many=True)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        log_a_success(request.user.id, request, response.status_code,
                      request_arrival_time)
        return response

    def retrieve(self, request, slug=None, **kwargs):
        """
            Get a plant with the mentioned slug value.
            ---
            request_serializer: PlantSerializer
            response_serializer: PlantSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the specified plant slug does not exist (INVALID_PLANT_SLUG).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
            plants = filter_solar_plants(context)
        try:
            plant = None
            for plant_instance in plants:
                if plant_instance.slug == slug:
                    plant = plant_instance
            if plant is None:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            # TODO check if this is the best way to set a non-model field
            setattr(plant, "total_inverters", len(plant.independent_inverter_units.all()))
            try:
                starttime = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                         second=0, microsecond=0)
                plant_generation_today = get_aggregated_energy(starttime, starttime+timedelta(hours=24), plant, "DAY")
                '''plant_generation_today = EnergyGenerationTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                           identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                                                                           ts=ts)'''
                today_generation = plant_generation_today[0]["energy"]

                '''today_generation = EnergyGenerationTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                                                                     ts=timezone.now())
                today_generation = today_generation.energy'''
            except :
                today_generation = 0.0
            setattr(plant, "today_generation", today_generation)

            ts = timezone.now()
            try:
                delay_minutes = 2
                values = get_plant_power(ts-timedelta(minutes=30),
                                         ts - timedelta(minutes=delay_minutes),
                                         plant)
                if len(values) > 0:
                    current_power = float(values[-1]["power"])
                else:
                    current_power = 0.0
            except Exception as exc:
                logger.debug(exc)
                current_power = 0.0
            setattr(plant, "current_power", current_power)

            stats = get_user_data_monitoring_status(plant.independent_inverter_units)
            if stats is not None:
                active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                stable_len = len(active_alive_valid) + len(deactivated_dead)
                warnings_len = len(active_alive_invalid)
                errors_len = len(active_dead) + len(deactivated_alive)
            else:
                stable_len = None
                warnings_len = None
                errors_len = None
            setattr(plant, 'connected_inverters', stable_len)
            setattr(plant, 'disconnected_inverters', errors_len)

            try:
                setattr(plant, "timezone", plant.metadata.plantmetasource.dataTimezone)
            except:
                setattr(plant, "timezone", "Asia/Kolkata")

            serializer = PlantSerializer(plant, many=False)
            response = Response(serializer.data,
                                status=status.HTTP_200_OK)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request,
                                        request_arrival_time, settings.ERRORS.INVALID_PLANT_SLUG,
                                        settings.RESPONSE_TYPES.DRF, False,
                                        comments)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

# class for Energy values as per new energy method
class V1_PlantEnergyViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            logger.debug("inside energy calculation class")
            # context = self.get_profile_data(**kwargs)
            # plants = filter_solar_plants(context)
            # try:
            #     plant = None
            #     for plant_instance in plants:
            #         if plant_instance.slug == plant_slug:
            #             plant = plant_instance
            #     if plant is None:
            #         return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            # except ObjectDoesNotExist:
            #     return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            # except:
            #     return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
            except:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)

            aggregator = request.query_params.get("aggregator","D")
            aggregation_period = request.query_params.get("period","1")
            split = request.query_params.get("split","False")
            meter = request.query_params.get("meter","True")
            power = request.query_params.get("power","False")
            try:
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("Please provide a valid start and end time", status=status.HTTP_400_BAD_REQUEST)

            if str(split).upper() == "FALSE":
                energy_split = False
            else:
               energy_split = True

            if str(meter).upper() == "FALSE":
                meter_energy = False
            else:
                meter_energy = True

            if str(power).upper() == "TRUE":
                power_values = True
            else:
                power_values = False

            if power_values == True:
                energy_values = get_minutes_aggregated_power(st, et, plant, aggregator, aggregation_period, energy_split, meter_energy)
            else:
                energy_values = get_minutes_aggregated_energy(st, et, plant, aggregator, aggregation_period, energy_split, meter_energy)
            return Response(data=energy_values, status=status.HTTP_200_OK)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PlantsEnergyData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        """
            Get energy generated by the specified plant.
            ---
            parameters:
                - name: startTime
                  type: dateTime
                  required: True
                  description: Start time of data lookup. It should be in ISO 8601 format.
                  paramType: query
                - name: endTime
                  type: dateTime
                  description: End time of data lookup. It should be in ISO 8601 format.
                  required: True
                  paramType: query
                - name: aggregator
                  type: string
                  description: It should be HOUR/DAY/FIVE_MINUTES
                  required: True
                  paramType: query
            response_serializer: EnergyDataValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the plant slug mentioned is invalid (INVALID_PLANT_SLUG) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST).
                - code : 401
                  message : Not authenticated.
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
            plants = filter_solar_plants(context)
        plant = SolarPlant.objects.get(slug=plant_slug)
        if plant not in plants:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, {})

        return get_energy_data(str(plant.owner.organization_user.user_id) + "_" + plant_slug, request)


class PlantsPowerData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        """
            Get power generated by the specified plant.
            ---
            parameters:
                - name: startTime
                  type: dateTime
                  required: True
                  description: Start time of data lookup. It should be in ISO 8601 format.
                  paramType: query
                - name: endTime
                  type: dateTime
                  description: End time of data lookup. It should be in ISO 8601 format.
                  required: True
                  paramType: query
            response_serializer: PowerDataValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the plant slug mentioned is invalid (INVALID_PLANT_SLUG) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST).
                - code : 401
                  message : Not authenticated.
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
            plants = filter_solar_plants(context)
        plant_slugs = [plant.slug for plant in plants]
        if plant_slug not in plant_slugs:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, {})

        return get_power_data(plant_slug, request)


class InvertersViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'inverter_key'

    def list(self, request, plant_slug=None, **kwargs):
        """
            Get a list of inverters for a plant.
            ---
            response_serializer: InverterSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the specified plant slug does not exist (INVALID_PLANT_SLUG).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
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
            inverters = IndependentInverter.objects.filter(plant=plant)
            serializer = InverterSerializer(inverters, many=True)
            response = Response(serializer.data)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def retrieve(self, request, inverter_key=None, plant_slug=None, **kwargs):
        """
            Get an inverter with the mentioned inverter key.
            ---
            response_serializer: InverterSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 401
                  message : Not authenticated
                - code : 400
                  message : If the specified plant slug does not exist (INVALID_PLANT_SLUG) or
                            If the specified inverter key does not exist (INVALID_INVERTER_KEY).
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
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
                                                       sourceKey=inverter_key)
            serializer = InverterSerializer(inverter, many=False)
            response = Response(serializer.data)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_INVERTER_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class InverterEnergyData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_inverter_key=None, plant_slug=None, **kwargs):
        """
            Get energy generated by the specified inverter aggregated over a time period.
            ---
            parameters:
                - name: startTime
                  type: dateTime
                  required: True
                  description: Start time of data lookup. It should be in ISO 8601 format.
                  paramType: query
                - name: endTime
                  type: dateTime
                  description: End time of data lookup. It should be in ISO 8601 format.
                  required: True
                  paramType: query
                - name: aggregator
                  type: string
                  description: It should be HOUR/DAY/FIVE_MINUTES
                  required: True
                  paramType: query
            response_serializer: EnergyDataValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the plant slug mentioned is invalid (INVALID_PLANT_SLUG) or
                            If the inverter key mentioned is invalid (INVALID_INVERTER_KEY) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST).
                - code : 401
                  message : Not authenticated.
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        plant_slugs = [plant.slug for plant in plants]
        if plant_slug not in plant_slugs:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, {})
        try:
            inverter = IndependentInverter.objects.get(sourceKey = plant_inverter_key)
            assert(inverter.plant.slug == plant_slug)
        except:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_INVERTER_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, {})

        return get_energy_data(plant_inverter_key, request)


class InvertersDataSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'data'

    def list(self, request, plant_inverter_key=None, plant_slug=None, **kwargs):
        """
            Get inverter data for a plant slug and inverter key.
            ---
            parameters:
                - name: startTime
                  type: dateTime
                  required: True
                  description: Start time of data lookup. It should be in ISO 8601 format.
                  paramType: query
                - name: endTime
                  type: dateTime
                  description: End time of data lookup. It should be in ISO 8601 format.
                  required: True
                  paramType: query
                - name: streamNames
                  type: string
                  description: A comma separated list of stream names that should be included in the data. There has to be at least one stream mentioned.
                  required: True
                  paramType: query
            response_serializer: InverterDataValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the plant slug mentioned is invalid (INVALID_PLANT_SLUG) or
                            If the inverter key mentioned is invalid (INVALID_INVERTER_KEY) or
                            If there is an invalid stream present in streamsNames (INVALID_DATA_STREAM) or
                            If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
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
                                        settings.ERRORS.INVALID_INVERTER_KEY, settings.RESPONSE_TYPES.DRF,
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
            except Exception as exception:
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
                                                                      timestamp_in_data__lte=et).limit(0).values_list('stream_value', 'timestamp_in_data')
                # populate data
                values = [item[0] for item in stream_data]
                # populate timestamps
                timestamps = [item[1].isoformat() for item in stream_data]
                # populate the outer array
                streams_data_dicts.append({'name': stream,
                                           'values': values,
                                           'timestamps': timestamps})

            reply = InverterDataValues(data={'sourceKey': plant_inverter_key,
                                             'streams': streams_data_dicts})
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
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class PlantEventsViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication,
                              authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            request_arrival_time = timezone.now()
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
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
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            except:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            inverters = IndependentInverter.objects.filter(plant=plant)
            inverter_count = len(inverters)
            events_dict = []
            inverter_event_list = []
            for index in range(len(inverters)):
                value_final = []
                inverter = inverters[index]
                source_key = inverter.sourceKey
                try:
                    st = request.query_params["startTime"]
                    et = request.query_params["endTime"]
                    try:
                        tz = pytz.timezone(inverter.dataTimezone)
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
                    source = IndependentInverter.objects.get(sourceKey=inverter.sourceKey)
                    name = source.name
                    key = source.sourceKey
                except:
                    name = None
                    key = None
                for event_name in range(len(event_names_request)):
                    events = EventsByError.objects.filter(identifier=source_key,
                                                          event_name=event_names_request[event_name],
                                                          insertion_time__gte=st,
                                                          insertion_time__lt=et).limit(0).values_list('insertion_time',
                                                                                                      'event_name',
                                                                                                      'event_time',
                                                                                                      'event_code')

                    if(len(events)>0):
                        inverter_event_list.append(source_key)
                    values = [{'insertion_time': entry[0],
                               'event_name':entry[1],
                               'event_time':entry[2],
                               'event_code':entry[3],
                               'source_key':key,
                               'source_name':name} for entry in events]
                    value_final.extend(values)
                events_dict.extend(value_final)
            count = len(list(set(inverter_event_list)))
            logger.debug(count)
            reply = PlantErrorByTimeValues(data={'plant_slug':plant.slug,
                                                 'plant_name':plant.name,
                                                 'total_inverters':inverter_count,
                                                 'no_of_inverters_affected':count,
                                                 'events': events_dict})
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


#API to get the Performance Ratio values
class PerformanceRatioData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        request_arrival_time = timezone.now()
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
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
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            except Exception as exception:
                logger.debug(str(exception))
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                # return log_and_return_error(request.user.id, request, request_arrival_time,
                #                             settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                #                             False, comments)
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                plant_meta = PlantMetaSource.objects.get(plant=plant)
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.NO_PLANT_META_SOURCE, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                aggregator = request.query_params["aggregator"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant_meta.dataTimezone)
                et = update_tz(et, plant_meta.dataTimezone)
            except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            flag = False
            ctp = None
            if aggregator == "HOUR":
                ctp = DATA_COUNT_PERIODS.HOUR
            elif aggregator == "DAY":
                ctp = DATA_COUNT_PERIODS.DAILY
            elif aggregator == "MONTH":
                ctp = DATA_COUNT_PERIODS.MONTH
            else:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_AGGREGATOR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            if aggregator == "MONTH":
                performance_data = PlantSummaryDetails.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period = ctp,
                                                                         identifier = str(plant.slug),
                                                                         ts__gte=st,
                                                                         ts__lte=et).values_list('performance_ratio', 'ts')
            else:
                performance_data = PerformanceRatioTable.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period = ctp,
                                                                        identifier = plant_meta.sourceKey,
                                                                        ts__gte=st,
                                                                        ts__lte=et).values_list('performance_ratio', 'ts')
            if len(plant.pvsyst_info.all())>0:
                pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='PERFORMANCE_RATIO',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=st.year).values_list('timePeriodValue', 'parameterValue')
                if len(pv_sys_info_pr)==0:
                    pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='PERFORMANCE_RATIO',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=0).values_list('timePeriodValue', 'parameterValue')
                flag = True
            performance_values = []
            for entry in performance_data:
                if entry[0] is not None:
                    performance_value = {}
                    performance_value['performance_ratio'] = entry[0]
                    performance_value['timestamp'] = entry[1]
                    recent_time = entry[1]
                    recent_time = pytz.utc.localize(recent_time)
                    if plant.metadata.plantmetasource:
                        recent_time = recent_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        current_month = recent_time.month
                    if flag:
                        try:
                            if len(pv_sys_info_pr)>0 and pv_sys_info_pr[current_month-1][1] is not None:
                                if aggregator == 'DAY' or aggregator == 'MONTH':
                                    pvsyst_pr = pv_sys_info_pr[current_month-1][1]
                                    performance_value['pvsyst_pr'] = pvsyst_pr
                        except:
                            pass
                    performance_values.append(performance_value)

            reply = PerformanceRatioValues(data=performance_values, many=True)
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

#API to get the Specific Yield values
class SpecificYieldData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        request_arrival_time = timezone.now()
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                plant_meta = plant.metadata.plantmetasource
            except ObjectDoesNotExist:
                return Response("NO_PLANT_META_FOUND", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                aggregator = request.query_params["aggregator"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant_meta.dataTimezone)
                et = update_tz(et, plant_meta.dataTimezone)
            except Exception as exception:
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            flag = False
            ctp = None
            if aggregator == "HOUR":
                ctp = DATA_COUNT_PERIODS.HOUR
            elif aggregator == "DAY":
                ctp = DATA_COUNT_PERIODS.DAILY
            elif aggregator == "MONTH":
                ctp = DATA_COUNT_PERIODS.MONTH
            else:
                return Response("INVALID_AGGREGATOR", status=status.HTTP_400_BAD_REQUEST)

            if aggregator == "MONTH":
                specific_yield_data = PlantSummaryDetails.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period = ctp,
                                                                         identifier = str(plant.slug),
                                                                         ts__gte=st,
                                                                         ts__lte=et).values_list('specific_yield', 'ts')
            else:
                logger.debug("inside else")
                specific_yield_data = SpecificYieldTable.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period = ctp,
                                                                        identifier = plant_meta.sourceKey,
                                                                        ts__gte=st,
                                                                        ts__lte=et).values_list('specific_yield', 'ts')
            if len(plant.pvsyst_info.all())>0:
                pv_sys_info_specific_yield = PVSystInfo.objects.filter(plant=plant,
                                                                       parameterName='SPECIFIC_PRODUCTION',
                                                                       timePeriodType='MONTH',
                                                                       timePeriodDay=0,
                                                                       timePeriodYear=st.year
                                                                       ).values_list('timePeriodValue', 'parameterValue')
                if len(pv_sys_info_specific_yield)==0:
                    pv_sys_info_specific_yield = PVSystInfo.objects.filter(plant=plant,
                                                                       parameterName='SPECIFIC_PRODUCTION',
                                                                       timePeriodType='MONTH',
                                                                       timePeriodDay=0,
                                                                       timePeriodYear=0
                                                                       ).values_list('timePeriodValue', 'parameterValue')
                flag = True
            specific_yield_values = []
            for entry in specific_yield_data:
                if entry[0] is not None:
                    specific_value = {}
                    specific_value['specific_yield'] = entry[0]
                    specific_value['timestamp'] = entry[1]
                    recent_time = entry[1]
                    recent_time = pytz.utc.localize(recent_time)
                    if plant.metadata.plantmetasource:
                        recent_time = recent_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        current_month = recent_time.month
                    if flag:
                        try:
                            if len(pv_sys_info_specific_yield)>0 and pv_sys_info_specific_yield[current_month-1][1] is not None:
                                if aggregator == 'DAY' or aggregator == 'MONTH':
                                    pvsyst_specific_yield = pv_sys_info_specific_yield[current_month-1][1]
                                    specific_value['pvsyst_specific_yield'] = pvsyst_specific_yield
                        except:
                            pass
                    specific_yield_values.append(specific_value)

            reply = SpecificYieldValues(data=specific_yield_values, many=True)
            if reply.is_valid():
                response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                return response
            else:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as exception:
            logger.debug(str(exception))
            return  Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CUFDataView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        request_arrival_time = timezone.now()
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
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
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            except:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            try:
                plant_meta = PlantMetaSource.objects.get(plant=plant)
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.NO_PLANT_META_SOURCE, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                aggregator = request.query_params["aggregator"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant_meta.dataTimezone)
                et = update_tz(et, plant_meta.dataTimezone)
            except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            ctp = None
            if aggregator == "HOUR":
                ctp = DATA_COUNT_PERIODS.HOUR
            elif aggregator == "DAY":
                ctp = DATA_COUNT_PERIODS.DAILY
            elif aggregator == "MONTH":
                ctp = DATA_COUNT_PERIODS.MONTH
            else:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_AGGREGATOR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            if aggregator == "MONTH":
                cuf_data = PlantSummaryDetails.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period = ctp,
                                                              identifier = str(plant.slug),
                                                              ts__gte=st,
                                                              ts__lte=et).values_list('cuf', 'ts')
            else:
                cuf_data = CUFTable.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                  count_time_period = ctp,
                                                  identifier = plant_meta.sourceKey,
                                                  ts__gte=st,
                                                  ts__lte=et).values_list('CUF', 'ts')

            cuf_values = [{'cuf': entry[0], 'timestamp':entry[1]} for entry in cuf_data]

            reply = CUFValueSerializer(data=cuf_values, many=True)
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


def inverter_order(x):
    return int(x.name.split("-")[1])

def string_order(x):
    return int(x.name.split("_")[1])


def fix_generation_units(generation):
    if generation > 1000000.0:
        return "{0:.2f} GWh".format(generation/1000000.0)
    if generation > 10000.0:
        return "{0:.2f} MWh".format(generation/1000.0)
    else:
        return "{0:.2f} kWh".format(generation)

def fix_capacity_units(capacity):
    try:
        if capacity > 1000000.0:
            return "{0:.1f} GWp".format(capacity/1000000.0)
        if capacity > 5000.0:
            return "{0:.1f} MWp".format(capacity/1000.0)
        else:
            return "{0:.1f} kWp".format(capacity)
    except:
        return capacity

def fix_co2_savings(co2):
    if co2 > 1000.0:
        return "{0:.1f} Ton".format((co2)/(907.185))
    else:
        return "{0:.1f} Kg".format(co2)

def get_plant_status_data(plant, fill_inverters=True):
    context = {}
    irradiation = 0.0
    # get the irradiation/external irradiation data
    # TODO fix it later, make sure it's either irradiation or external irradiation
    ts = timezone.now()
    try:
        if plant.metadata:
            irradiation = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                  stream_name = 'IRRADIATION',
                                                                  timestamp_in_data__lte=ts,
                                                                  timestamp_in_data__gte=ts-timedelta(minutes=20)).limit(1)
            if irradiation:
                irradiation = irradiation[0].stream_value
            else:
                irradiation = 0.0
    except Exception as exc:
        irradiation = 0.0

    if irradiation == 0.0:
        try:
            if plant.metadata:
                irradiation = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                      stream_name = 'EXTERNAL_IRRADIATION',
                                                                      timestamp_in_data__lte=ts,
                                                                      timestamp_in_data__gte=ts-timedelta(minutes=20)).limit(1)
                if irradiation:
                    irradiation = irradiation[0].stream_value
                else:
                    irradiation = 0.0
        except Exception as exc:
            irradiation = 0.0
    context['irradiation'] = irradiation

    try:
        if plant.metadata:
            ambient_temperature = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                          stream_name = 'AMBIENT_TEMPERATURE',
                                                                          timestamp_in_data__lte=ts,
                                                                          timestamp_in_data__gte=ts-timedelta(minutes=20)).limit(1)
            if ambient_temperature:
                ambient_temperature = ambient_temperature[0].stream_value
            else:
                ambient_temperature = 0.0
    except Exception as exc:
        ambient_temperature = 0.0
    context['ambient_temperature'] = ambient_temperature

    mt = 0.0
    # get module temperature data
    try:
        if plant.metadata:
            mt = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                  stream_name = 'MODULE_TEMPERATURE',
                                                                  timestamp_in_data__lte=ts,

                                                                  timestamp_in_data__gte=ts-timedelta(minutes=20)).limit(1)
            if mt:
                mt = mt[0].stream_value
            else:
                mt = 0.0
    except Exception as exc:
        mt = 0.0
    context['module_temperature'] = mt

    windspeed = 0.0
    # get module temperature data
    try:
        if plant.metadata:
            windspeed = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                  stream_name = 'WINDSPEED',
                                                                  timestamp_in_data__lte=ts,

                                                                  timestamp_in_data__gte=ts-timedelta(minutes=20)).limit(1)
            if windspeed:
                windspeed = windspeed[0].stream_value
            else:
                windspeed = 0.0
    except Exception as exc:
        windspeed = 0.0
    context['windspeed'] = windspeed

    context['plant_capacity'] = plant.capacity if plant.capacity else 0.0
    context['plant_name'] = plant.name if plant.name else None
    context['plant_location'] = plant.location if plant.location else None

    # get the last power value
    # anything between (ts-30mins, ts-2mins)
    ts = timezone.now()
    try:
        delay_mins=2
        values = get_plant_power(ts-timedelta(minutes=30),
                                 ts - timedelta(minutes=delay_mins),
                                 plant)
        if len(values) > 0:
            current_power = float(values[-1]["power"])
        else:
            current_power = 0.0
    except Exception as exc:
        logger.debug(exc)
        current_power = 0.0

    context['current_power'] = current_power

    # total generation for today
    ts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                             second=0, microsecond=0).astimezone(pytz.UTC)
    try:
        starttime = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                 second=0, microsecond=0)

        if hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed:
            plant_generation_today = get_energy_meter_values(starttime, starttime+timedelta(hours=24), plant, "DAY")
        else:
            plant_generation_today = get_aggregated_energy(starttime, starttime+timedelta(hours=24), plant, "DAY")

        '''plant_generation_today = EnergyGenerationTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                                                                   ts=ts)'''
        plant_generation_today = plant_generation_today[0]["energy"]
    except Exception as exc:
        logger.debug(exc)
        plant_generation_today = 0.0
    context['plant_generation_today'] = plant_generation_today

    # performance ratio
    try:
        plant_meta = PlantMetaSource.objects.get(plant=plant)
    except PlantMetaSource.DoesNotExist:
        plant_meta = None
    if plant_meta:
        tz = pytz.timezone('Asia/Kolkata')
        ts_performance = timezone.now()
        ts_performance = ts_performance.astimezone(tz)
        daily_performance_ratio = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                       identifier=plant_meta.sourceKey,
                                                                       ts=ts_performance.replace(hour=0,minute=0,second=0,microsecond=0)
                                                                       ).limit(1)
        if len(daily_performance_ratio) > 0 and daily_performance_ratio[0].performance_ratio is not None:
            context['performance_ratio'] = "{0:.2f}".format(daily_performance_ratio[0].performance_ratio)
        else:
            context['performance_ratio'] = 0.0
        '''hourly_performance_ratio = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                        identifier=plant_meta.sourceKey,
                                                                        ts=ts_performance.replace(minute=0,second=0,microsecond=0)
                                                                        ).limit(1)
        if hourly_performance_ratio:
            context['hourly_performance_ratio'] = hourly_performance_ratio[0].performance_ratio
        else:
            context['hourly_performance_ratio'] = 0.0'''
        daily_cuf = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                            identifier=plant_meta.sourceKey,
                                            ts=ts_performance.replace(hour=0,minute=0,second=0,microsecond=0)
                                            ).limit(1)
        if len(daily_cuf) > 0 and daily_cuf[0].CUF is not None:
            context['cuf'] = "{0:.2f}".format(daily_cuf[0].CUF)
        else:
            context['cuf'] = 0.0

    else:
        context["performance_ratio"] = 0.0
        context['cuf'] = 0.0

    if len(plant.pvsyst_info.all())>0:
        current_time = timezone.now()
        current_month = current_time.month
        pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='NORMALISED_ENERGY_PER_DAY',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=current_time.year,
                                                           timePeriodValue=current_month)
        if len(pv_sys_info_generation)==0:
            pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='NORMALISED_ENERGY_PER_DAY',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)
        plant_capacity = plant.capacity
        if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
            pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
            context['pvsyst_generation'] = fix_generation_units(pvsyst_generation)

        pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                   parameterName='PERFORMANCE_RATIO',
                                                   timePeriodType='MONTH',
                                                   timePeriodDay=0,
                                                   timePeriodYear=current_time.year,
                                                   timePeriodValue=current_month)
        if len(pv_sys_info_pr)==0:
            pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                       parameterName='PERFORMANCE_RATIO',
                                                       timePeriodType='MONTH',
                                                       timePeriodDay=0,
                                                       timePeriodYear=0,
                                                       timePeriodValue=current_month)

        if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
            pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
            context['pvsyst_pr'] = pvsyst_pr

        pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='TILT_ANGLE',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=current_time.year,
                                                           timePeriodValue=current_month)
        if len(pv_sys_info_tilt_angle) == 0:
            pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='TILT_ANGLE',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)

        if len(pv_sys_info_tilt_angle)> 0 and pv_sys_info_tilt_angle[0].parameterValue is not None:
            pvsyst_tilt_angle = float(pv_sys_info_tilt_angle[0].parameterValue)
            context['pvsyst_tilt_angle'] = pvsyst_tilt_angle

    # inverters details
    if plant.slug == 'rrkabel':
        inverters_unordered = plant.independent_inverter_units.all().order_by('name')
        inverters = sorted(inverters_unordered, key=inverter_order)
    else:
        inverters = plant.independent_inverter_units.all().order_by('id')
    inverters_data = []
    stats = get_user_data_monitoring_status(plant.independent_inverter_units)
    if stats is not None:
        active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
    else:
        active_alive_valid = None
        active_dead = None

    sts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                             second=0, microsecond=0)
    ets = sts+timedelta(hours=24)
    inverters_generation = get_aggregated_energy(sts, ets, plant, aggregator='DAY', split=True, meter_energy=False)

    # Get all the solar groups
    solar_groups_name = plant.solar_groups.all()
    if len(solar_groups_name) == 0:
        context['solar_groups'] = []
        context['total_group_number'] = 0
    else:
        solar_group_list = []
        for i in range(len(solar_groups_name)):
            solar_group_list.append(str(solar_groups_name[i].name))

        context['solar_groups'] = solar_group_list
        context['total_group_number'] = len(solar_groups_name)

    if fill_inverters:
        for inverter in inverters:
            try:
                data = {}

                # get the generation for today
                try:
                    today_generation = float(inverters_generation[0]['energy'][inverter.name])
                except:
                    today_generation = 0.0

                # get current power
                try:
                    last_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                         stream_name='ACTIVE_POWER',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                    last_power = float(last_power[0].stream_value)
                except Exception as exc:
                    logger.debug(exc)
                    last_power = 0.0

                # get the connection status
                if active_alive_valid:
                    if inverter.sourceKey in active_alive_valid:
                        connected = "connected"
                    elif inverter.sourceKey in active_dead:
                        connected = "disconnected"
                    else:
                        connected = "unknown"
                else:
                    connected = "unknown"

                # data for this inverter
                data['name'] = inverter.name
                data['generation'] = today_generation
                data['power'] = last_power
                data['connected'] = connected
                data['key'] = inverter.sourceKey
                data['orientation'] = inverter.orientation
                data['capacity'] = inverter.actual_capacity
                if len(inverter.solar_groups.all()) != 0:
                    data['solar_group'] = str(inverter.solar_groups.all()[0].name)
                else:
                    data['solar_group'] = "NA"


                # populate in the inverters data list
                inverters_data.append(data)
            except Exception as exc:
                logger.debug(str(exc))
                continue

    context['inverters'] = inverters_data

    t_stats = get_plant_tickets(plant)
    if t_stats != -1:
        context['unacknowledged_tickets'] = len(t_stats['open_unassigned_tickets'])
        context['open_tickets'] = len(t_stats['open_assigned_tickets'])
        context['closed_tickets'] = len(t_stats['tickets_closed_resolved'])

    else:
        context['unacknowledged_tickets'] = 0
        context['open_tickets'] = 0
        context['closed_tickets'] = 0

    try:
        context['plant_total_energy'] = calculate_total_plant_generation(plant)
    except :
        context['plant_total_energy'] = 0.0
    return context

def get_plant_status_data_date(plant, date, fill_inverters=True):
    context = {}
    date = parser.parse(date)
    tz = pytz.timezone('Asia/Kolkata')
    if date.tzinfo is None:
        date = tz.localize(date)
    date = date.replace(hour=0, minute=0,second=0, microsecond=0)
    date_utc = date.astimezone(pytz.UTC)

    context['plant_capacity'] = plant.capacity if plant.capacity else 0.0
    context['plant_name'] = plant.name if plant.name else None
    context['plant_location'] = plant.location if plant.location else None

    # total generation for the day
    try:
        if hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed:
            plant_generation_today = get_energy_meter_values(date, date+timedelta(hours=24), plant, "DAY")
        else:
            plant_generation_today = get_aggregated_energy(date, date+timedelta(hours=24), plant, "DAY")

        plant_generation_today = plant_generation_today[0]["energy"]
    except Exception as exc:
        logger.debug(exc)
        plant_generation_today = 0.0
    context['plant_generation_today'] = plant_generation_today

    # performance ratio
    try:
        plant_meta = PlantMetaSource.objects.get(plant=plant)
    except PlantMetaSource.DoesNotExist:
        plant_meta = None
    if plant_meta:
        daily_performance_ratio = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                       identifier=plant_meta.sourceKey,
                                                                       ts=date_utc
                                                                       ).limit(1)
        if len(daily_performance_ratio) > 0 and daily_performance_ratio[0].performance_ratio is not None:
            context['performance_ratio'] = "{0:.2f}".format(daily_performance_ratio[0].performance_ratio)
        else:
            context['performance_ratio'] = 0.0

        daily_cuf = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                            identifier=plant_meta.sourceKey,
                                            ts=date_utc
                                            ).limit(1)
        if len(daily_cuf) > 0 and daily_cuf[0].CUF is not None:
            context['cuf'] = "{0:.2f}".format(daily_cuf[0].CUF)
        else:
            context['cuf'] = 0.0

    else:
        context["performance_ratio"] = 0.0
        context['cuf'] = 0.0

    if len(plant.pvsyst_info.all())>0:
        current_month = date.month
        pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='NORMALISED_ENERGY_PER_DAY',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=date.year,
                                                           timePeriodValue=current_month)
        if len(pv_sys_info_generation)==0:
            pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='NORMALISED_ENERGY_PER_DAY',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)
        plant_capacity = plant.capacity
        if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
            pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
            context['pvsyst_generation'] = fix_generation_units(pvsyst_generation)

        pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                   parameterName='PERFORMANCE_RATIO',
                                                   timePeriodType='MONTH',
                                                   timePeriodDay=0,
                                                   timePeriodYear=date.year,
                                                   timePeriodValue=current_month)
        if len(pv_sys_info_pr) == 0:
            pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                       parameterName='PERFORMANCE_RATIO',
                                                       timePeriodType='MONTH',
                                                       timePeriodDay=0,
                                                       timePeriodYear=0,
                                                       timePeriodValue=current_month)

        if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
            pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
            context['pvsyst_pr'] = pvsyst_pr

        pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='TILT_ANGLE',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=date.year,
                                                           timePeriodValue=current_month)
        if len(pv_sys_info_tilt_angle)==0:
            pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='TILT_ANGLE',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)

        if len(pv_sys_info_tilt_angle)> 0 and pv_sys_info_tilt_angle[0].parameterValue is not None:
            pvsyst_tilt_angle = float(pv_sys_info_tilt_angle[0].parameterValue)
            context['pvsyst_tilt_angle'] = pvsyst_tilt_angle

    # inverters details
    if plant.slug == 'rrkabel':
        inverters_unordered = plant.independent_inverter_units.all().order_by('name')
        inverters = sorted(inverters_unordered, key=inverter_order)
    else:
        inverters = plant.independent_inverter_units.all().order_by('id')
    inverters_data = []

    sts = date
    ets = sts+timedelta(hours=24)
    inverters_generation = get_aggregated_energy(sts, ets, plant, aggregator='DAY', split=True, meter_energy=False)

    # Get all the solar groups
    solar_groups_name = plant.solar_groups.all()
    if len(solar_groups_name) == 0:
        context['solar_groups'] = []
        context['total_group_number'] = 0
    else:
        solar_group_list = []
        for i in range(len(solar_groups_name)):
            solar_group_list.append(str(solar_groups_name[i].name))

        context['solar_groups'] = solar_group_list
        context['total_group_number'] = len(solar_groups_name)

    if fill_inverters:
        for inverter in inverters:
            try:
                data = {}

                # get the generation for today
                try:
                    today_generation = float(inverters_generation[0]['energy'][inverter.name])
                except:
                    today_generation = 0.0

                # data for this inverter
                data['name'] = inverter.name
                data['generation'] = today_generation
                data['key'] = inverter.sourceKey
                data['orientation'] = inverter.orientation
                data['capacity'] = inverter.actual_capacity
                if len(inverter.solar_groups.all()) != 0:
                    data['solar_group'] = str(inverter.solar_groups.all()[0].name)
                else:
                    data['solar_group'] = "NA"


                # populate in the inverters data list
                inverters_data.append(data)
            except Exception as exc:
                logger.debug(str(exc))
                continue

    context['inverters'] = inverters_data

    if date:
        t_stats = get_plant_tickets_date(plant, date, date+timedelta(hours=24))
    else:
        t_stats = get_plant_tickets(plant)
    if t_stats != -1:
        context['unacknowledged_tickets'] = len(t_stats['open_unassigned_tickets'])
        context['open_tickets'] = len(t_stats['open_assigned_tickets'])
        context['closed_tickets'] = len(t_stats['tickets_closed_resolved'])

    else:
        context['unacknowledged_tickets'] = 0
        context['open_tickets'] = 0
        context['closed_tickets'] = 0

    try:
        context['plant_total_energy'] = calculate_total_plant_generation(plant)
    except :
        context['plant_total_energy'] = 0.0
    return context


class PlantSummaryView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        logger.debug(plant_slug)
        request_arrival_time = timezone.now()
        date = request.query_params.get("date", None)
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            profile_data = self.get_profile_data()
            solar_plants = filter_solar_plants(profile_data)
            if plant not in solar_plants:
                raise ObjectDoesNotExist
        except Exception as exc:
            logger.debug(str(exc))
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        # data dict
        if date:
            context = get_plant_status_data_date(plant, date)
        else:
            context = get_plant_status_data(plant)
        context['plant_co2'] = fix_co2_savings(context['plant_generation_today']*0.7)
        context['plant_generation_today'] = fix_generation_units(context['plant_generation_today'])
        context['plant_total_energy'] = fix_generation_units(context['plant_total_energy'])
        context['plant_capacity'] = fix_capacity_units(context['plant_capacity'])

        try:
            reply = PlantStatusSummary(data=context)
            if reply.is_valid():
                response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments=None)
                return response
            else:
                logger.debug(reply.errors)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, {})


        except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)


class SolarClientView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        request_arrival_time = timezone.now()
        date = request.query_params.get("date", None)
        try:
            profile_data = self.get_profile_data()
            solar_plants = filter_solar_plants(profile_data)
            logger.debug(solar_plants)
        except Exception as exc:
            logger.debug(str(exc))
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        context = {}
        context['plants'] = []
        context['total_energy'] = 0.0
        context['energy_today'] = 0.0
        context['total_capacity'] = 0.0

        for plant in solar_plants:
            if date:
                context_plant = get_plant_status_data_date(plant, date, False)
            else:
                context_plant = get_plant_status_data(plant, False)
            context['plants'].append(context_plant)
            context['total_energy'] += float(context_plant['plant_total_energy'])
            context['energy_today'] += float(context_plant['plant_generation_today'])
            context['total_capacity'] += float(context_plant['plant_capacity'])

        context['total_co2'] = fix_co2_savings(context['energy_today']*0.70)
        context['energy_today'] = fix_generation_units(context['energy_today'])
        context['total_energy'] = fix_generation_units(context['total_energy'])
        #context['total_capacity'] = fix_capacity_units(context['total_capacity'])

        for plant in context['plants']:
            plant['plant_co2'] = fix_co2_savings(plant['plant_generation_today']*0.7)
            plant['plant_generation_today'] = fix_generation_units(plant['plant_generation_today'])
            plant['plant_total_energy'] = fix_generation_units(plant['plant_total_energy'])
            #plant['plant_capacity'] = fix_capacity_units(plant['plant_capacity'])

        try:
            reply = PlantClientSummary(data=context)
            if reply.is_valid():
                response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments=None)
                return response
            else:
                logger.debug(reply.errors)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, {})


        except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)


def get_value_or_placeholder(obj, prop, placeholder):
    if obj.getattr(prop):
        return obj.getattr(prop)
    else:
        return placeholder


def get_basic_association_details(association, ticket):
    info = OrderedDict()
    info['identifier_name'] = str(association.identifier_name)
    #info['association_active'] = association.active
    # info['event_type'] = ticket.event_type
    info['created'] = association.created
    info['updated'] = association.updated #get_value_or_placeholder(ticket, "updated", "--").strftime("%Y-%m-%dT%H:%M:%SZ")
    info['closed'] = association.closed #get_value_or_placeholder(ticket, "closed", "--").strftime("%Y-%m-%dT%H:%M:%SZ")
    info['expected_energy'] = association.expected_energy
    info['actual_energy'] = association.actual_energy
    return info


def retrieve_new(plant, ticket, active=True):

    # add tickets information
    ticket_detail = OrderedDict()
    ticket_detail['id'] = ticket.id
    ticket_detail['ticket_type'] = ticket.event_type
    if ticket.title:
        ticket_detail['title'] = ticket.title
    if ticket.created:
        ticket_detail['created'] = ticket.created
    if ticket.status:
        ticket_detail['status'] = TICKET_STATUS[str(int(ticket.status))]
    if ticket.description:
        ticket_detail['description'] = ticket.description
    if ticket.priority:
        ticket_detail['priority'] = TICKET_PRIOTITY[str(int(ticket.priority))]

    ticket_detail['actual_energy'] = ticket.actual_energy
    ticket_detail['expected_energy'] = ticket.expected_energy

    # add associations information
    associations_description = []
    if active:
        associations = ticket.associations.all().filter(active=True)
    else:
        associations = ticket.associations.all().filter(active=False)

    for association in associations:
        logger.debug("inside association")
        try:
            if ticket.event_type == "GATEWAY_POWER_OFF" or ticket.event_type == "GATEWAY_DISCONNECTED" or \
                            ticket.event_type == "INVERTERS_DISCONNECTED" or ticket.event_type == "AJBS_DISCONNECTED":
                info = get_basic_association_details(association, ticket)
                associations_description.append(info)
            else:
                if ticket.event_type == "PANEL_CLEANING":
                    for pa in association.performance_associations.all():
                        info = get_basic_association_details(association, ticket)
                        # info['start_time'] = pa.st
                        # info['end_time'] = pa.et
                        info['created'] = pa.st
                        info['closed'] = pa.et
                        info['residual'] = pa.residual
                        associations_description.append(info)

                elif ticket.event_type == "INVERTERS_ALARMS":
                    if len(association.alarms.filter(active=active)) == 0:
                        info = get_basic_association_details(association, ticket)
                        associations_description.append(info)
                    else:
                        for alarm in association.alarms.filter(active=active):
                            logger.debug("inside alarm")
                            info = get_basic_association_details(association, ticket)
                            # remove association status
                            #info.pop('association_active')
                            info['solar_status'] = str(alarm.device_status_number)
                            if alarm.alarm_code:
                                info['alarm_code'] = alarm.alarm_code
                                info['alarm_description'] = alarm.alarm_description
                            info['solar_status_description'] = alarm.device_status_description
                            info['alarm_status'] = alarm.active
                            info['alarm_start_time'] = alarm.created
                            info['alarm_update_time'] = alarm.updated
                            info['alarm_end_time'] = alarm.closed
                            logger.debug("alarm details captured")
                            associations_description.append(info)

                elif ticket.event_type == "AJB_STRING_CURRENT_ZERO_ALARM":
                    for alarm in association.alarms.filter(active=active):
                        logger.debug("inside alarm")
                        info = get_basic_association_details(association, ticket)
                        # remove association status
                        #info.pop('association_active')
                        info['string_name'] = alarm.alarm_code
                        info['alarm_status'] = alarm.active
                        info['alarm_start_time'] = alarm.created
                        info['alarm_update_time'] = alarm.updated
                        info['alarm_end_time'] = alarm.closed
                        logger.debug("string details captured")
                        associations_description.append(info)

                elif ticket.event_type == "INVERTERS_UNDERPERFORMING":
                    for pa in association.performance_associations.filter(active=active):
                        info = get_basic_association_details(association, ticket)
                        # remove association status
                        #info.pop('association_active')
                        info['start_time'] = pa.st
                        info['end_time'] = pa.et
                        info['delta_energy'] = pa.delta_energy
                        info['mean_energy'] = pa.mean_energy
                        associations_description.append(info)

                elif ticket.event_type == "MPPT_UNDERPERFORMING" or ticket.event_type == "AJB_UNDERPERFORMING":
                    for pa in association.performance_associations.filter(active=active):
                        info = get_basic_association_details(association, ticket)
                        # remove association status
                        #info.pop('association_active')
                        info['start_time'] = pa.st
                        info['end_time'] = pa.et
                        info['delta_current'] = pa.delta_current
                        info['mean_current'] = pa.mean_current
                        associations_description.append(info)


        except Exception as exc:
            logger.debug(exc)
            continue

    from features.utils import get_header_information
    return {'ticket_detail': ticket_detail,
            'associations_header': get_header_information(associations_description),
            'associations_description': associations_description}


class PlantTicketNewViewSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'ticket_id'

    def retrieve(self, request, plant_slug=None, ticket_id=None, **kwargs):
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            logger.debug(plant)
        except ObjectDoesNotExist:
            return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)

        try:
            active = self.request.query_params.get('active', 'True')
        except:
            active = 'False'

        active = True if str(active).upper() == 'TRUE' else False

        try:
            queue = Queue.objects.get(plant=plant)
            logger.debug(queue)
        except ObjectDoesNotExist:
            return Response("Queue Does not exist for the plant.", status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except ObjectDoesNotExist:
            return Response("Invalid ticket id ", status=status.HTTP_400_BAD_REQUEST)
        try:
            data = retrieve_new(plant, ticket, active)
            response = Response(data, status=status.HTTP_200_OK)
            return response
        except Exception as exc:
            return Response(str(exc), status=status.HTTP_400_BAD_REQUEST)


class PlantTicketViewSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'ticket_id'

    def list(self, request, plant_slug=None, **kwargs):
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
        except ObjectDoesNotExist:
            return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)

        try:
            queue = Queue.objects.get(plant=plant)
        except ObjectDoesNotExist:
            return Response("Queue Does not exist for the plant.", status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = self.request.query_params.get("limit", 50)
        except Exception as exception:
            limit = 50

        try:
            mobile = self.request.query_params.get("mobile","FALSE")
            if str(mobile).upper() == "TRUE":
                mobile = True
            else:
                mobile = False
        except:
            mobile = False

        logger.debug(limit)

        try:
            if mobile:
                tickets = Ticket.objects.filter(queue=queue, status__in = [Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS]).order_by('-created')
            else:
                tickets = Ticket.objects.filter(queue=queue).order_by('status','-created')[:limit]
            ticket_list = []
            for ticket in tickets:
                ticket_detail = {}
                ticket_detail['id'] = ticket.id
                ticket_detail['ticket_type'] = ticket.event_type.replace("_", " ").title()
                if ticket.title:
                    ticket_detail['title'] = ticket.title
                if ticket.queue:
                    ticket_detail['queue'] = ticket.queue.title
                if ticket.created:
                    ticket_detail['created'] = ticket.created
                if ticket.modified:
                    ticket_detail['modified'] = ticket.modified
                if ticket.submitter_email:
                    ticket_detail['submitter_email'] = ticket.submitter_email
                if ticket.assigned_to:
                    ticket_detail['assigned_to'] = ticket.assigned_to.username
                ticket_detail['status'] = TICKET_STATUS[str(int(ticket.status))]
                if ticket.description:
                    ticket_detail['description'] = ticket.description
                if ticket.resolution:
                    ticket_detail['resolution'] = ticket.resolution
                ticket_detail['priority'] = TICKET_PRIOTITY[str(int(ticket.priority))]
                if ticket.due_date:
                    ticket_detail['due_date'] = ticket.due_date
                if ticket.last_escalation:
                    ticket_detail['last_escalation'] = ticket.last_escalation
                if mobile:
                    ticket_associations = []
                    associations = ticket.associations.all().filter(active=True)
                    ticket_detail['active_associations'] = len(ticket.associations.all().filter(active=True))
                    for association in associations:
                        info = { 'id' : int(association.id),
                                 'identifier' : association.identifier,
                                 'identifier_name' : association.identifier_name,
                                 'active' : association.active,
                                 'created' : association.created,
                                 'title': str(association.ticket.event_type)
                                }
                        try:
                            ticket = association.ticket
                            description = ""
                            if ticket.event_type == "GATEWAY_POWER_OFF":
                                description = "This gateway is switched off since " + str(association.created.astimezone(pytz.timezone("Asia/Kolkata"))) + " , please check the AC power supply to the device. The data will not be collected until the supply is back on."

                            elif ticket.event_type == "GATEWAY_DISCONNECTED" or \
                                ticket.event_type == "INVERTERS_DISCONNECTED" or ticket.event_type == "AJBS_DISCONNECTED":
                                description = "This device has not been sending data since " + str(association.created.astimezone(pytz.timezone("Asia/Kolkata"))) + " , please check the internet connection to the device."

                            elif ticket.event_type == "PANEL_CLEANING":
                                description = "The solar panels connected to " + str(association.identifier_name) + " need cleaning as they are generating less than average for past couple of days. Please get that cleaned to get higher generation."

                            elif ticket.event_type == "INVERTERS_ALARMS":
                                if len(association.alarms.all()) > 0:
                                    alarm = association.alarms.order_by('created')[0].alarm_code
                                    solar_status = association.alarms.order_by('created')[0].device_status_number
                                    solar_status_description = get_solar_status_code_mapping(association.identifier, solar_status)
                                    created_at = str(association.alarms.order_by('created')[0].created.astimezone(pytz.timezone("Asia/Kolkata")))
                                    description = "This inverter raised an alarm at " + str(created_at) +  " with status : " + solar_status_description
                                    if alarm is not None:
                                        alarm_description = get_alarm_code_name(association.identifier, alarm)
                                        description += " and alarm : " + alarm_description + "."
                                    else:
                                        description += "."
                                else:
                                    description = "This inverter raised an alarm at " + str(association.created.astimezone(pytz.timezone("Asia/Kolkata")))

                            elif ticket.event_type == "INVERTERS_UNDERPERFORMING":
                                description = str(association.identifier_name) + " underperformed from " + str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ")) + " to " +\
                                              str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))

                            elif ticket.event_type == "MPPT_UNDERPERFORMING" or ticket.event_type == "AJB_UNDERPERFORMING":
                                description = str(association.identifier_name) + " underperformed from " + str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ")) + " to " +\
                                              str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))
                        except Exception as exc:
                            logger.debug(exc)
                            description = ""

                        info['description'] = description
                        ticket_associations.append(info)
                    ticket_detail['association_details'] = ticket_associations
                if len(ticket_detail) > 0:
                    ticket_list.append(ticket_detail)
            reply = TicketSerializer(data=ticket_list, many=True)
            if reply.is_valid():
                response = Response(reply.data, status=status.HTTP_200_OK)
                return response
            else:
                return Response(reply.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("Internal Server Error ", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, plant_slug=None, ticket_id= None, **kwargs):
        request_arrival_time = timezone.now()
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            logger.debug(plant)
        except ObjectDoesNotExist:
            return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)

        try:
            queue = Queue.objects.get(plant=plant)
            logger.debug(queue)
        except ObjectDoesNotExist:
            return Response("Queue Does not exist for the plant.", status=status.HTTP_400_BAD_REQUEST)

        try:
            try:
                ticket = Ticket.objects.get(id=ticket_id)
            except ObjectDoesNotExist:
                return Response("Invalid ticket id ", status=status.HTTP_400_BAD_REQUEST)

            try:
                ticket_detail = {}
                ticket_associations = []
                associations = ticket.associations.all()
                active_associations = ticket.associations.filter(ticket=ticket, active=True)
                #ticket_serializer = TicketSerializer(ticket, many=False)
                ticket_detail['id'] = ticket.id
                ticket_detail['ticket_type'] = ticket.event_type
                if ticket.title:
                    ticket_detail['title'] = ticket.title
                ticket_detail['queue'] = ticket.queue.title
                if ticket.modified:
                    ticket_detail['modified'] = ticket.modified
                if ticket.created:
                    ticket_detail['created'] = ticket.created
                if ticket.submitter_email:
                    ticket_detail['submitter_email'] = ticket.submitter_email
                if ticket.assigned_to:
                    ticket_detail['assigned_to'] = ticket.assigned_to.username
                if ticket.status:
                    ticket_detail['status'] = TICKET_STATUS[str(int(ticket.status))]
                if ticket.description:
                    ticket_detail['description'] = ticket.description
                if ticket.resolution:
                    ticket_detail['resolution'] = ticket.resolution
                if ticket.priority:
                    ticket_detail['priority'] = TICKET_PRIOTITY[str(int(ticket.priority))]
                if ticket.due_date:
                    ticket_detail['due_date'] = ticket.due_date
                if ticket.last_escalation:
                    ticket_detail['last_escalation'] = ticket.last_escalation
                ticket_detail['total_associations'] = len(associations)
                ticket_detail['active_associations'] = len(active_associations)
                #ticket_serializer = TicketSerializer(ticket, many=False)
                for association in associations:
                    info = { 'id' : association.id,
                             'identifier' : association.identifier,
                             'identifier_name' : association.identifier_name,
                             'active' : association.active,
                             'created' : association.created
                            }
                    try:
                        if ticket.event_type == "GATEWAY_POWER_OFF" or ticket.event_type == "GATEWAY_DISCONNECTED" or \
                           ticket.event_type == "INVERTERS_DISCONNECTED" or ticket.event_type == "AJBS_DISCONNECTED":
                            info['comment1'] = ticket.event_type
                            info['comment2'] = str(association.updated)

                        elif ticket.event_type == "PANEL_CLEANING":
                            info['comment1'] = str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment2'] = str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment3'] = str(association.performance_associations.all()[0].residual)

                        elif ticket.event_type == "INVERTERS_ALARMS":
                            info['comment1'] = str(association.alarms.order_by('created')[0].device_status_number)
                            info['comment2'] = str(association.alarms.order_by('created')[0].alarm_code)
                            if association.alarms.all()[0].updated:
                                info['comment3'] = str(association.alarms.order_by('created')[0].updated.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            else:
                                info['comment3'] = str(association.alarms.order_by('created')[0].created.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment4'] = str(association.alarms.order_by('created')[0].active)

                        elif ticket.event_type == "INVERTERS_UNDERPERFORMING":
                            info['comment1'] = str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment2'] = str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment3'] = str(association.performance_associations.all()[0].delta_energy)
                            info['comment4'] = str(association.performance_associations.all()[0].mean_energy)

                        elif ticket.event_type == "MPPT_UNDERPERFORMING" or ticket.event_type == "AJB_UNDERPERFORMING":
                            info['comment1'] = str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment2'] = str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))
                            info['comment3'] = str(association.performance_associations.all()[0].delta_current)
                            info['comment4'] = str(association.performance_associations.all()[0].mean_current)
                    except Exception as exc:
                        logger.debug(exc)
                        continue
                    ticket_associations.append(info)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("Error Occurred", status=status.HTTP_400_BAD_REQUEST)

            reply = TicketAssociationsSerializer(data={'ticket': ticket_detail,
                                                       'associations': ticket_associations})

            if reply.is_valid():
                response = Response(reply.data, status=status.HTTP_200_OK)
                return response
            else:
                return Response(reply.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("Internal Server Error ", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, plant_slug=None, ticket_id= None, **kwargs):
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
        except ObjectDoesNotExist:
            return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)

        try:
            queue = Queue.objects.get(plant=plant)
        except ObjectDoesNotExist:
            return Response("Queue Does not exist for the plant.", status=status.HTTP_400_BAD_REQUEST)

        try:
            try:
                ticket = Ticket.objects.get(id=ticket_id)
                serializer = TicketPatchSerializer(ticket,
                                                   data=request.data,
                                                   partial=True)
                if serializer.is_valid():
                    serializer.save(user=request.user)
                    logger.debug("calling update_ticket")
                    update_ticket(plant=plant, ticket_id=ticket.id, followup_user=self.request.user,
                                  comment=request.data.get('comment', None), new_status=request.data.get('new_status', None),
                                  title=request.data.get('title', None),priority=request.data.get('priority', None))
                    logger.debug("done updating the ticket")
                    response = Response(serializer.data, status=status.HTTP_201_CREATED)
                    logger.debug("sending the response back ")
                    return response
                else:
                    response = Response(serializer.errors,
                                        status=status.HTTP_400_BAD_REQUEST)
                    return response
            except ObjectDoesNotExist:
                return Response("Invalid ticket id ", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("Internal Server Error ", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PlantAssociationViewSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'association_id'

    def retrieve(self, request, plant_slug=None, association_id= None, **kwargs):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                logger.debug(plant)
            except ObjectDoesNotExist:
                return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)

            try:
                queue = Queue.objects.get(plant=plant)
                logger.debug(queue)
            except ObjectDoesNotExist:
                return Response("Queue Does not exist for the plant.", status=status.HTTP_400_BAD_REQUEST)

            try:
                logger.debug(association_id)
                association = TicketAssociation.objects.get(id=association_id)
                result = {}
                result['association_id'] = int(association.id)
                result['identifier']=str(association.identifier)
                result['identifier_name']=str(association.identifier_name)
                result['ticket_id']= int(association.ticket.id)
                result['title'] = str(association.ticket.event_type)
                result['priority'] = TICKET_PRIOTITY[str(int(association.ticket.priority))]
                result['created'] = str(association.created)
                try:
                    ticket = association.ticket
                    description = ""
                    if ticket.event_type == "GATEWAY_POWER_OFF":
                        description = str(association.identifier_name) + " is powered off since " +str(association.created)

                    elif ticket.event_type == "GATEWAY_DISCONNECTED" or \
                        ticket.event_type == "INVERTERS_DISCONNECTED" or ticket.event_type == "AJBS_DISCONNECTED":
                        description = str(association.identifier_name) + " is disconnected since " +str(association.created)

                    elif ticket.event_type == "PANEL_CLEANING":
                        description = "Panels of " + str(association.identifier_name) + " needs cleaning. Please get it cleaned soon to increase the generation."

                    elif ticket.event_type == "INVERTERS_ALARMS":
                        description = str(association.identifier_name) + " raised an alarm with alarm code " + str(association.alarms.order_by('created')[0].alarm_code) +\
                                      " at " + str(association.alarms.order_by('created')[0].updated.strftime("%Y-%m-%dT%H:%M:%SZ"))

                    elif ticket.event_type == "INVERTERS_UNDERPERFORMING":
                        description = str(association.identifier_name) + " underperformed from " + str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ")) + " to " +\
                                      str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))

                    elif ticket.event_type == "MPPT_UNDERPERFORMING" or ticket.event_type == "AJB_UNDERPERFORMING":
                        description = str(association.identifier_name) + " underperformed from " + str(association.performance_associations.all()[0].st.strftime("%Y-%m-%dT%H:%M:%SZ")) + " to " +\
                                      str(association.performance_associations.all()[0].et.strftime("%Y-%m-%dT%H:%M:%SZ"))
                except Exception as exception:
                    logger.debug(str(exception))
                    description = ""
                result['description'] = description
                return Response(data=result, status=status.HTTP_200_OK)
            except ObjectDoesNotExist as exc:
                logger.debug(str(exc))
                return Response("Invalid association id ", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("Internal Server Error ", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TicketFollowUpView(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'plant_ticket_id'

    def list(self, request, plant_slug=None, plant_ticket_id=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except ObjectDoesNotExist:
                return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)

            try:
                ticket = Ticket.objects.get(id=plant_ticket_id)
            except ObjectDoesNotExist:
                return Response("Invalid ticket id ", status=status.HTTP_400_BAD_REQUEST)

            try:
                final_ticket_changes = []
                followup_response = []
                ticket_change_response = []
                followups = FollowUp.objects.filter(ticket=ticket)
                for followup in followups:
                    followup_value = {}
                    followup_value['id'] = followup.id
                    if followup.date:
                        followup_value['date'] = followup.date
                    if followup.title:
                        followup_value['title'] = followup.title
                    if followup.comment:
                        followup_value['comment'] = followup.comment
                    if followup.public:
                        followup_value['public'] = followup.public
                    if followup.user:
                        followup_value['user'] = followup.user.username
                    if followup.new_status:
                        followup_value['new_status'] = TICKET_STATUS[str(int(followup.new_status))]
                    if len(followup_value) > 0:
                       followup_response.append(followup_value)

                for followup in followups:
                    ticket_changes = TicketChange.objects.filter(followup=followup)
                    logger.debug(ticket_changes)
                    if len(ticket_changes)>0:
                        final_ticket_changes.extend(ticket_changes)
                for ticket_change in final_ticket_changes:
                    ticket_change_response.append({
                                                   'followup': ticket_change.followup.id,
                                                   'field': ticket_change.field,
                                                   'old_value': ticket_change.old_value,
                                                   'new_value': ticket_change.new_value
                                                   })
                reply = FollowUpTicketChangeSerializer(data={'followups': followup_response,
                                                             'ticket_changes': ticket_change_response})


                if reply.is_valid():
                    return Response(reply.data, status=status.HTTP_200_OK)
                else:
                    return Response(reply.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except Exception as exception:
                logger.debug(str(exception))
                return Response(" ", status=status.HTTP_400_BAD_REQUEST)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("Internal Server Error ", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''
class IndependentInverterData(ProfileDataMixin, AddSensorsMixin,
                              JSONResponseMixin, TemplateView):

    template_name = "solarmonitoring/inverter_profile.html"
    json_include = ['live_chart_data', 'today_generation',
                    'five_minute_generation',
                    'week_generation','status']

    def get(self, request, *args, **kwargs):
        if self.request.is_ajax():
            context = self.get_context_data()
            context_dict = {}
            for key in self.json_include:
                context_dict[key] = context[key]
            response = self.render_json_response(context_dict)
            return response
        else:
            return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(IndependentInverterData, self).get_context_data(**kwargs)
        profile_data = self.get_profile_data()
        for key in profile_data.keys():
            context[key] = profile_data[key]
        try:
            inverter = IndependentInverter.objects.get(sourceKey=self.kwargs.get('inverter_key'))
            plant_slug = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
            assert(inverter in plant_slug.independent_inverter_units.all())
        except IndependentInverter.DoesNotExist:
            raise Http404
        except AssertionError:
            raise Http404
        except SolarPlant.DoesNotExist:
            raise Http404

        # status values
        if inverter.isMonitored:
            try:
                source = SourceMonitoring.objects.get(source_key=inverter.sourceKey,
                                                      valid_entry=True)
                # connected, valid data
                status = 1
            except:
                try:
                    source = SourceMonitoring.objects.get(source_key=inverter.sourceKey,
                                                      valid_entry=False)
                    # connected, invalid data
                    status = 4
                except:
                    # not connected
                    status = 2
        else:
            # not monitored
            status = 3
        context['status'] = status

        # energy values
        ts = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                          second=0, microsecond=0).astimezone(pytz.UTC)
        try:
            today_generation = EnergyGenerationTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                 count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                 identifier=str(inverter.sourceKey),
                                                                 ts=ts)
            today_generation = today_generation.energy
        except :
            today_generation = None
        context['today_generation'] = today_generation

        try:
            five_minute_generation = EnergyGenerationTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.FIVE_MINTUES,
                                                                   identifier=str(inverter.sourceKey),
                                                                   ts__gte=ts).values_list('ts', 'energy')
        except:
            five_minute_generation = []

        context['five_minute_generation'] = [{"key": "Entire Plant Generation", "color": "#00cc66",
                                              "values": [[int(entry[0].strftime("%s"))*1000,
                                                          entry[1]] for entry in reversed(five_minute_generation)]}]

        # get hourly energy value for last week
        ts = datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - datetime.timedelta(days=7)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.UTC)
        try:
            week_generation = EnergyGenerationTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=str(inverter.sourceKey),
                                                                   ts__gte=ts).values_list('ts', 'energy')
        except:
            week_generation = []
        context['week_generation'] = [{"key" : "Energy generation", "values":[[int(entry[0].strftime("%s"))*1000,
                                       float(entry[1])/float(1000)] for entry in reversed(week_generation)]}]

        context['inverter'] = inverter
        context['plant_slug'] = plant_slug
        context['live_chart_data'] = get_inverter_data(inverter)

        return context
'''

class GroupsPowerData(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except ObjectDoesNotExist:
                return Response("Invalid plant slug ", status=status.HTTP_400_BAD_REQUEST)
            try:
                tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                tz = pytz.timezone(pytz.utc._tzname)
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]

                # convert into datetime objects
                st = parser.parse(st)
                if st.tzinfo is None:
                    st = tz.localize(st)
                et = parser.parse(et)
                if et.tzinfo is None:
                    et = tz.localize(et)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            try:
                group_name_list = []
                group_list = []
                group_names = plant.solar_groups.all()
                for group_name in group_names:
                    group_name_list.append(group_name.name)
                groups = request.query_params["groupNames"].split(",")
                groups = [group.strip().lstrip() for group in groups]
                for group in groups:
                    assert (group in group_name_list)
                for group in groups:
                    group_list.append(group)
            except AssertionError:
                return Response("INVALID_GROUP_NAME", status=status.HTTP_400_BAD_REQUEST)
            except KeyError:
                group_list = group_name_list
            try:
                result = get_groups_power(st, et, plant, group_list)
                if result:
                    return Response(json.loads(result), status=status.HTTP_200_OK)
                else:
                    return Response([], status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnergyLossView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                plant_meta = PlantMetaSource.objects.get(plant=plant)
            except ObjectDoesNotExist:
                return Response("NO_PLANT_META_FOUND", status=status.HTTP_400_BAD_REQUEST)
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                aggregator = request.query_params["aggregator"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant_meta.dataTimezone)
                et = update_tz(et, plant_meta.dataTimezone)
            except Exception as exception:
                return Response("MISSING_REQUIRED_QUERY_PARAMS", status=status.HTTP_400_BAD_REQUEST)

            ctp = None
            if aggregator == "HOUR":
                ctp = DATA_COUNT_PERIODS.HOUR
            elif aggregator == "DAY":
                ctp = DATA_COUNT_PERIODS.DAILY
            else:
                return Response("INVALID_AGGREGATOR", status=status.HTTP_400_BAD_REQUEST)
            try:
                energy_loss = EnergyLossTable.objects.filter(timestamp_type = TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period = ctp,
                                                             identifier = plant_meta.sourceKey,
                                                             ts__gte=st,
                                                             ts__lte=et).order_by('-ts').values_list('dc_energy_ajb','dc_energy_inverters','ac_energy_inverters','ac_energy_meters','dc_energy_loss','conversion_loss','ac_energy_loss', 'ts')
            except Exception as exception:
                logger.debug(str(exception))

            energy_loss_values = []
            for entry in energy_loss:
                loss_values = {}
                loss_values['dc_energy_calculated_from_ajbs'] = str(entry[0]) if entry[0] is not None else 'NA'
                loss_values['dc_energy_calculated_from_inverters'] = str(entry[1]) if entry[1] is not None else 'NA'
                loss_values['ac_energy_calculated_from_inverters'] = str(entry[2]) if entry[2] is not None else 'NA'
                loss_values['ac_energy_calculated_from_energy_meters'] = str(entry[3]) if entry[3] is not None else 'NA'
                loss_values['dc_energy_loss'] = str(entry[4]) if entry[4] is not None else 'NA'
                loss_values['conversion_loss'] = str(entry[5]) if entry[5] is not None else 'NA'
                loss_values['ac_energy_loss'] = str(entry[6]) if entry[6] is not None else 'NA'
                loss_values['timestamp'] = entry[7] if entry[7] is not None else 'NA'
                energy_loss_values.append(loss_values)

            reply = EnergyLossValues(data=energy_loss_values, many=True)
            if reply.is_valid():
                response = Response(reply.data,
                                    status=status.HTTP_200_OK)
                return response
            else:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PowerIrradiationData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                tz = pytz.timezone(pytz.utc._tzname)
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]

                # convert into datetime objects
                st = parser.parse(st)
                if st.tzinfo is None:
                    st = tz.localize(st)
                et = parser.parse(et)
                if et.tzinfo is None:
                    et = tz.localize(et)
                error = self.request.query_params.get('error', 'FALSE')
                if error.upper() == 'TRUE':
                    error = True
                else:
                    error = False
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            try:
                if error:
                    result = {}
                    result1 = get_power_irradiation(st, et, plant, error)
                    result['data'] = json.loads(result1[0])
                    result['max_power'] = result1[1]
                    result2 = get_network_down_time_from_heartbeat(st, et, plant)
                    result['network'] = result2
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    result = get_power_irradiation(st, et, plant, error)
                    if result:
                        return Response(json.loads(result), status=status.HTTP_200_OK)
                    else:
                        return Response([], status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_energy_prediction_data(starttime, endtime, plant):
    try:
        predicted_energy_value = 0.0
        predicted_values = PredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                         count_time_period=3600,
                                                         identifier=str(plant.slug),
                                                         stream_name='plant_energy',
                                                         model_name ='STATISTICAL_LATEST',
                                                         ts__gte=starttime,
                                                         ts__lte=endtime)
        for predicted_value in predicted_values:
            predicted_energy_value += float(predicted_value.value)
        return predicted_energy_value
    except Exception as exception:
        print("Error in getting predicted energy values : " + str(exception))


def make_losses_unit_same_as_generation(generation_list, losses_list, energy_type):
    try:
        conversion_scheme = {'kWh_MWh': 0.001,
                             'kWh_GWh': 0.000001,
                             'MWh_kWh': 1000,
                             'GWh_kWh': 1000000,
                             'kWh_kWh': 1,
                             'MWh_MWh': 1,
                             'GWh_GWh': 1}

        for index in range(len(losses_list)):
           try:
               losses_unit = str(losses_list[index][energy_type]).split(' ')[1]
               generation_unit = str(generation_list[index]['energy']).split(' ')[1]
               conversion_unit = str(losses_unit)+'_'+str(generation_unit)
               losses_value = str(losses_list[index][energy_type]).split(' ')[0]
               final_losses_value = float(losses_value) * conversion_scheme[conversion_unit]
               losses_list[index][energy_type] = str(final_losses_value) + ' ' + str(generation_unit)
           except Exception as exception:
               print(str(exception))
               continue
        return losses_list
    except Exception as exception:
        print(str(exception))

def get_current_inverter_error_details(plant, time, cron_interval=5):
    try:
        final_dict = {}
        initial_time = time - timedelta(minutes=cron_interval)
        inverters = plant.independent_inverter_units.all()
        number_of_inverters_with_errors = 0
        for inverter in inverters:
            try:
                associations = TicketAssociation.objects.filter(identifier=str(inverter.sourceKey),
                                                               timestamp__gte=initial_time,
                                                               event_name='INVERTER_ERROR',
                                                               status=True)
                if len(associations)>0:
                    for association in associations:
                        ticket = association.ticket
                        if ticket.status in [Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS]:
                            number_of_inverters_with_errors += 1
            except Exception as exception:
                logger.debug(str(exception))
                continue
        final_dict['plant_name'] = str(plant.slug)
        final_dict['ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_list/'
        final_dict['affected_inverters_number'] = number_of_inverters_with_errors
        return final_dict
    except Exception as exception:
        logger.debug(str(exception))

def get_current_inverter_error_details_without_association(plant, time, cron_interval=5):
    try:
        final_dict = {}
        initial_time = time - timedelta(minutes=cron_interval)
        queue = Queue.objects.get(plant=plant)

        error_tickets = Ticket.objects.filter(queue=queue,
                                              created__gte=initial_time,
                                              title__startswith='Inverter Error',
                                              status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
        final_dict['plant_name'] = str(plant.slug)
        final_dict['ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_list/'
        final_dict['affected_inverters_number'] = len(error_tickets)
        return final_dict
    except Exception as exception:
        print(str(exception))
        return {}

def get_current_inverter_alarms(plant):
    try:
        final_dict = {}
        queue = Queue.objects.get(plant=plant)
        alarm_ticket = Ticket.objects.filter(queue=queue,
                                             event_type='INVERTERS_ALARMS',
                                             status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
        if len(alarm_ticket)>0:
            final_dict['plant_name'] = str(plant.slug)
            final_dict['ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(alarm_ticket[len(alarm_ticket)-1].id)+'/'
            final_dict['affected_inverters_number'] = len(alarm_ticket[len(alarm_ticket)-1].associations.all().filter(active=True))
        return final_dict
    except Exception as exception:
        print str(exception)
        return {}

def get_current_inverter_cleaning_details_without_association(plant, time, cron_interval=1440):
    try:
        final_dict = {}
        initial_time = time - timedelta(minutes=cron_interval)
        queue = Queue.objects.get(plant=plant)

        cleaning_tickets = Ticket.objects.filter(queue=queue,
                                                 created__gte=initial_time,
                                                 title__startswith='Cleaning of solar panels',
                                                 status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
        number_of_inverters_which_require_cleaning = len(cleaning_tickets[len(cleaning_tickets)-1].associations.all().filter(status=True)) if len(cleaning_tickets)>0 else 0
        final_dict['plant_name'] = str(plant.slug)
        if len(cleaning_tickets)>0:
            final_dict['ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(cleaning_tickets[len(cleaning_tickets)-1].id)+'/'
        final_dict['inverters_required_cleaning_numbers'] = number_of_inverters_which_require_cleaning
        return final_dict
    except Exception as exception:
        print(str(exception))
        return {}

def get_current_inverter_cleaning_details(plant):
    try:
        final_dict = {}
        queue = Queue.objects.get(plant=plant)
        panel_cleaning_ticket = Ticket.objects.filter(queue=queue,
                                                      event_type='PANEL_CLEANING',
                                                      status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
        if len(panel_cleaning_ticket)>0:
            final_dict['plant_name'] = str(plant.slug)
            final_dict['ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(panel_cleaning_ticket[len(panel_cleaning_ticket)-1].id)+'/'
            final_dict['inverters_required_cleaning_numbers'] = len(panel_cleaning_ticket[len(panel_cleaning_ticket)-1].associations.all().filter(active=True))
        return final_dict
    except Exception as exception:
        print str(exception)
        return {}

def get_current_string_anomaly_details(plant, time, cron_interval=60):
    try:
        final_dict = {}
        initial_time = time - timedelta(minutes=cron_interval)
        ajbs = plant.ajb_units.all()
        number_of_ajbs_with_low_anomaly = 0
        number_of_ajbs_with_high_anomaly = 0
        for ajb in ajbs:
            try:
                low_associations = TicketAssociation.objects.filter(identifier=str(ajb.sourceKey),
                                                               timestamp__gte=initial_time,
                                                               event_name='STRING_LOW_ERROR',
                                                               status=True)
                if len(low_associations)>0:
                    for low_association in low_associations:
                        low_ticket = low_association.ticket
                        if low_ticket.status in [Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS]:
                            number_of_ajbs_with_low_anomaly += 1

                high_associations = TicketAssociation.objects.filter(identifier=str(ajb.sourceKey),
                                                                     timestamp__gte=initial_time,
                                                                     event_name='STRING_HIGH_ERROR',
                                                                     status=True)
                if len(high_associations)>0:
                    for high_association in high_associations:
                        high_ticket = high_association.ticket
                        if high_ticket.status in [Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS]:
                            number_of_ajbs_with_high_anomaly += 1
            except Exception as exception:
                logger.debug(str(exception))
                continue
        final_dict['plant_name'] = str(plant.slug)
        final_dict['low_anomaly_affected_ajbs_number'] = number_of_ajbs_with_low_anomaly
        if number_of_ajbs_with_low_anomaly > 0:
            final_dict['low_anomaly_ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(low_ticket.id)+'/'
        final_dict['high_anomaly_affected_ajbs_number'] = number_of_ajbs_with_high_anomaly
        if number_of_ajbs_with_high_anomaly > 0:
            final_dict['high_anomaly_ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(high_ticket.id)+'/'
        return final_dict
    except Exception as exception:
        logger.debug(str(exception))

def get_current_string_anomaly_details_without_association(plant, time, cron_interval=60):
    try:
        final_dict = {}
        initial_time = time - timedelta(minutes=cron_interval)
        queue = Queue.objects.get(plant=plant)

        low_tickets = Ticket.objects.filter(queue=queue,
                                            created__gte=initial_time,
                                            title__startswith='STRING_LOW_ERROR',
                                            status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
        high_tickets = Ticket.objects.filter(queue=queue,
                                             created__gte=initial_time,
                                             title__startswith='STRING_HIGH_ERROR',
                                             status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])

        final_dict['plant_name'] = str(plant.slug)
        number_of_ajbs_with_low_anomaly = len(low_tickets[len(low_tickets)-1].associations.all().filter(status=True)) if len(low_tickets)>0 else 0

        if number_of_ajbs_with_low_anomaly > 0:
            final_dict['low_anomaly_ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(low_tickets[len(low_tickets)-1].id)+'/'
        final_dict['low_anomaly_affected_ajbs_number'] = number_of_ajbs_with_low_anomaly

        number_of_ajbs_with_high_anomaly = len(high_tickets[len(high_tickets)-1].associations.all().filter(status=True)) if len(high_tickets)>0 else 0

        if number_of_ajbs_with_high_anomaly > 0:
            final_dict['high_anomaly_ticket_url'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(high_tickets[len(high_tickets)-1].id)+'/'
        final_dict['high_anomaly_affected_ajbs_number'] = number_of_ajbs_with_high_anomaly
        return final_dict
    except Exception as exception:
        print(str(exception))
        return {}


def get_plant_live_ajb_status(plant, current_time, fill_ajbs=True, inverter_name=None):
    try:
        result = {}
        if inverter_name is not None:
            # this call is for ajbs status for an inverter - no multiprocessing will be used
            inverter_list = plant.independent_inverter_units.all().filter(name=inverter_name)
            if len(inverter_list)>0:
                inverter = inverter_list[0]
                ajbs = inverter.ajb_units.all().filter(isActive=True)
            else:
                return result
        else:
            # this call is for plant's ajbs - multiprocessing
            ajbs = plant.ajb_units.all().filter(isActive=True)

        # get solar groups status in any case
        solar_groups_name = plant.solar_groups.all()
        if len(solar_groups_name) == 0:
            result['solar_groups'] = []
            result['total_group_number'] = 0
        else:
            solar_group_list = []
            for i in range(len(solar_groups_name)):
                solar_group_list.append(str(solar_groups_name[i].name))

            result['solar_groups'] = solar_group_list
            result['total_group_number'] = len(solar_groups_name)

        # store ajb data here
        ajb_data = []

        if fill_ajbs:
            ajb_data = get_plant_live_ajb_status_mp(plant=plant, ajbs_query_set=ajbs)

        result['ajbs'] = ajb_data

        if inverter_name is not None:
            result['inverter_details'] = get_plant_live_data_status_individual_inverter(plant, current_time, inverter, True)

        return result
    except Exception as exception:
        logger.debug(str(exception))

def get_plant_live_data_status_individual_ajb(plant, ajb):
    try:
        ajb_fields = SolarField.objects.filter(source=ajb, isActive=True)
        ajb_string_fields_name = []
        ajb_status_fields_name = []
        ajb_other_fields_name = []

        try:
            timeout_interval = plant.metadata.plantmetasource.data_frequency if plant.metadata.plantmetasource and \
                                                                            plant.metadata.plantmetasource.data_frequency \
                                                                            else ajb.timeoutInterval
        except:
            try:
                timeout_interval = ajb.timeoutInterval
            except:
                timeout_interval = 2700

        for field in ajb_fields:
            if str(field.name).startswith("S"):
                try:
                    ajb_string_fields_name.append(str(field.displayName)) if field.displayName is not None else ajb_string_fields_name.append(str(field.name))
                except:
                    ajb_string_fields_name.append(str(field.name))
            elif str(field.name).startswith("D"):
                try:
                    ajb_status_fields_name.append(str(field.displayName)) if field.displayName is not None else ajb_string_fields_name.append(str(field.name))
                except:
                    ajb_status_fields_name.append(str(field.name))
            else:
                try:
                    ajb_other_fields_name.append(str(field.displayName)) if field.displayName is not None else ajb_string_fields_name.append(str(field.name))
                except:
                    ajb_other_fields_name.append(str(field.name))
        ajb_string_fields_name = sorted_nicely(ajb_string_fields_name)
        ajb_status_fields_name = sorted_nicely(ajb_status_fields_name)
        ajb_other_fields_name = sorted_nicely(ajb_other_fields_name)
        result = []
        for name in ajb_string_fields_name:
            try:
                field = SolarField.objects.get(source=ajb, displayName=name)
            except:
                field = SolarField.objects.get(source=ajb, displayName=name)
            if str(field.name) not in EXCLUDE_VISUALIZATION_STREAMS:
                try:
                    values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                     stream_name=str(field.name),
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=timeout_interval)).limit(1)
                    if len(values)>0:
                        try:
                            value = float(values[0].stream_value)
                        except:
                            value = values[0].stream_value
                    else:
                        value = "--"
                except Exception as exception:
                    value = '--'
                try:
                    name = str(field.displayName) if field.displayName else str(field.name)
                    stream_name = str(field.name)
                    stream = SolarField.objects.get(source=ajb, name=stream_name)
                    stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                except:
                    stream_unit = "--"

                value_result = {}
                if value is not "NA" and stream_unit is not "NA":
                    value_result['name'] = name
                    try:
                        value_result['value'] = str(round(float(value),2)) + " " + str(stream_unit)
                    except:
                        value_result['value'] = str(value) + " " + str(stream_unit)
                elif value is not "NA" and stream_unit is "NA":
                    value_result['name'] = name
                    value_result['value'] = value
                else:
                    value_result['name'] = name
                    value_result['value'] = "NA"
                result.append(value_result)

        for name in ajb_other_fields_name:
            try:
                field = SolarField.objects.get(source=ajb, displayName=name)
            except:
                field = SolarField.objects.get(source=ajb, displayName=name)
            if str(field.name) not in EXCLUDE_VISUALIZATION_STREAMS:
                try:
                    values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                     stream_name=str(field.name),
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=timeout_interval)).limit(1)
                    if len(values)>0:
                        try:
                            value = float(values[0].stream_value)
                        except:
                            value = values[0].stream_value
                    else:
                        value = "NA"
                except Exception as exception:
                    value = 'NA'
                try:
                    name = str(field.displayName) if field.displayName else str(field.name)
                    stream_name = str(field.name)
                    stream = SolarField.objects.get(source=ajb, name=stream_name)
                    stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                except:
                    stream_unit = "NA"

                value_result = {}
                if value is not "NA" and stream_unit is not "NA":
                    value_result['name'] = name
                    try:
                        value_result['value'] = str(round(float(value),2)) + " " + str(stream_unit)
                    except:
                        value_result['value'] = str(value) + " " + str(stream_unit)
                elif value is not "NA" and stream_unit is "NA":
                    value_result['name'] = name
                    value_result['value'] = value
                else:
                    value_result['name'] = name
                    value_result['value'] = "NA"
                result.append(value_result)

        for name in ajb_status_fields_name:
            try:
                field = SolarField.objects.get(source=ajb, displayName=name)
            except:
                field = SolarField.objects.get(source=ajb, displayName=name)
            if str(field.name) not in EXCLUDE_VISUALIZATION_STREAMS:
                try:
                    values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                     stream_name=str(field.name),
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=timeout_interval)).limit(1)
                    if len(values)>0:
                        try:
                            value = float(values[0].stream_value)
                        except:
                            value = values[0].stream_value
                    else:
                        value = "NA"
                except Exception as exception:
                    value = 'NA'
                try:
                    name = str(field.displayName) if field.displayName else str(field.name)
                    stream_name = str(field.name)
                    stream = SolarField.objects.get(source=ajb, name=stream_name)
                    stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                except:
                    stream_unit = "NA"

                value_result = {}
                if value is not "NA" and stream_unit is not "NA":
                    value_result['name'] = name
                    try:
                        value_result['value'] = str(round(float(value),2)) + " " + str(stream_unit)
                    except:
                        value_result['value'] = str(value) + " " + str(stream_unit)
                elif value is not "NA" and stream_unit is "NA":
                    value_result['name'] = name
                    value_result['value'] = value
                else:
                    value_result['name'] = name
                    value_result['value'] = "NA"
                result.append(value_result)
        values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                         stream_name='S1').limit(1)

        if len(values)==0:
            values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                         stream_name='S2').limit(1)

        if len(values)==0:
            values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                         stream_name='S_1').limit(1)
        if len(values)==0:
            values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                             stream_name='STRING1').limit(1)
        if len(values)==0:
            values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                             stream_name='STRING_1').limit(1)
        value_result = {}
        value_result['name'] = 'Last Timestamp'
        if len(values)>0:
            try:
                value_result['value'] = update_tz(values[0].timestamp_in_data, plant.metadata.plantmetasource.dataTimezone).strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                value_result['value'] = "NA"
        else:
            value_result["value"] = "NA"
        result.append(value_result)
        return result
    except Exception as exception:
        print(str(exception))
        return []

def get_plant_live_data_status_individual_inverter(plant, current_time,  inverter, fill_inverters=True):
    try:
        #result = {}

        sts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                 second=0, microsecond=0)
        ets = sts+timedelta(hours=24)
        #inverters_generation = get_aggregated_energy(sts, ets, plant, aggregator='DAY', split=True, meter_energy=False)
        inverters_generation = get_minutes_aggregated_energy(sts, ets, plant, 'DAY', 1, split=True, meter_energy=False)
        inverters_generation = convert_new_energy_data_format_to_old_format(inverters_generation)

        # Get all the solar groups
        # solar_groups_name = plant.solar_groups.all()
        # if len(solar_groups_name) == 0:
        #     result['solar_groups'] = []
        #     result['total_group_number'] = 0
        # else:
        #     solar_group_list = []
        #     for i in range(len(solar_groups_name)):
        #         solar_group_list.append(str(solar_groups_name[i].name))
        #
        #     result['solar_groups'] = solar_group_list
        #     result['total_group_number'] = len(solar_groups_name)

        stats = get_user_data_monitoring_status(plant.independent_inverter_units)
        print stats
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
        else:
            active_alive_valid = None
            active_dead = None

        inverters_data = []

        if fill_inverters:
            try:
                data = {}
                # get the generation for today
                try:
                    today_generation = float(inverters_generation[0]['energy'][inverter.name])
                except:
                    today_generation = 0.0

                # get current power
                try:
                    last_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                         stream_name='ACTIVE_POWER',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                    last_power = float(last_power[0].stream_value)
                except Exception as exc:
                    logger.debug(exc)
                    last_power = 0.0

                # get current total yield
                try:
                    last_total_yield = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                               stream_name='TOTAL_YIELD').limit(1)

                    last_total_yield = float(last_total_yield[0].stream_value)
                except Exception as exc:
                    logger.debug(exc)
                    last_total_yield = 0.0

                # get inside temperature
                try:
                    inside_temperature = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                 stream_name='INSIDE_TEMPERATURE',
                                                                                 timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                                 timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                    inside_temperature = float(inside_temperature[0].stream_value)
                except Exception as exc:
                    logger.debug(exc)
                    inside_temperature = 0.0

                # get last 3 inverter errors
                last_three_errors = []
                try:
                    inverter_errors = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                          stream_name='ERROR_CODE').limit(3)
                    for i in range(len(inverter_errors)):
                        error_values = {}
                        error_values['error_code'] = inverter_errors[i].stream_value
                        error_values['timestamp'] = inverter_errors[i].timestamp_in_data
                        last_three_errors.append(error_values)
                except Exception as exc:
                    logger.debug(exc)
                    last_three_errors = []

                # get the connection status
                # if active_alive_valid:
                if inverter.sourceKey in active_alive_valid:
                    connected = "connected"
                elif inverter.sourceKey in active_dead:
                    connected = "disconnected"
                else:
                    connected = "unknown"
                # else:
                #     connected = "unknown"

                # get the inverter status
                latest_inverter_status = []
                try:
                    inverter_status = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                              stream_name='SOLAR_STATUS',
                                                                              timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')),
                                                                              timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                    for i in range(len(inverter_status)):
                        status_values = {}
                        try:
                            status_description = InverterStatusMappings.objects.get(plant=plant, stream_name='SOLAR_STATUS', status_code=float(inverter_status[i].stream_value))
                            status_values['status'] = status_description.status_description
                        except:
                            status_values['status'] = inverter_status[i].stream_value
                        status_values['timestamp'] = inverter_status[i].timestamp_in_data
                        latest_inverter_status.append(status_values)
                except Exception as exc:
                    logger.debug(exc)
                    latest_inverter_status = []

                # data for this inverter
                data['name'] = inverter.name
                data['generation'] = today_generation
                data['power'] = last_power
                data['connected'] = connected
                data['key'] = inverter.sourceKey
                data['orientation'] = inverter.orientation
                data['capacity'] = inverter.actual_capacity
                if len(inverter.solar_groups.all()) != 0:
                    data['solar_group'] = str(inverter.solar_groups.all()[0].name)
                else:
                    data['solar_group'] = "NA"
                data['inside_temperature'] = inside_temperature
                data['total_yield'] = last_total_yield
                data['last_three_errors'] = last_three_errors
                data['last_inverter_status'] = latest_inverter_status


                # get details from energy loss table
                # energy_loss = EnergyLossTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                #                                              count_time_period=86400,
                #                                              identifier=str(inverter.sourceKey),
                #                                              ts=sts)
                # if len(energy_loss)>0:
                #     data['total_dc_generation_ajbs'] = round(float(energy_loss[0].dc_energy_ajb),2) if energy_loss[0].dc_energy_ajb is not None else None
                #     data['total_dc_generation_inverter'] = round(float(energy_loss[0].dc_energy_inverters),2) if energy_loss[0].dc_energy_inverters is not None else None
                #     data['total_ac_generation_inverter'] = round(float(energy_loss[0].ac_energy_inverters_ap),2) if energy_loss[0].ac_energy_inverters_ap is not None else None
                #     data['dc_losses_percent'] = round((float(data['total_dc_generation_ajbs'] - data['total_dc_generation_inverter'])/data['total_dc_generation_ajbs'])*100.0, 2) if data['total_dc_generation_ajbs'] is not None and data['total_dc_generation_inverter'] is not None else None
                #     #data['conversion_loss_percent'] = round((float(data['total_dc_generation_inverter']-data['generation'])/data['total_dc_generation_inverter'])*100.0, 2) if data['total_dc_generation_inverter'] is not None and data['generation'] is not None else None
                #     data['conversion_loss_percent'] = round((float(data['total_dc_generation_inverter']-data['total_ac_generation_inverter'])/data['total_dc_generation_inverter'])*100.0, 2) if data['total_dc_generation_inverter'] is not None and data['total_ac_generation_inverter'] is not None else None

                ajbs = inverter.ajb_units.all()
                # Total DC Power of AJB's
                total_ajb_power = 0.0
                for ajb in ajbs:
                    try:
                        ajb_last_power = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                                 stream_name='POWER',
                                                                                 timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                                 timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                        ajb_last_power = float(ajb_last_power[0].stream_value)
                        total_ajb_power += ajb_last_power
                    except Exception as exc:
                        logger.debug(exc)
                        ajb_last_power = 0.0

                # DC power of inverters
                try:
                    last_dc_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                            stream_name='DC_POWER',
                                                                            timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                            timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                    last_dc_power = float(last_dc_power[0].stream_value)
                except Exception as exc:
                    logger.debug(exc)
                    last_dc_power = 0.0

                data['total_ajb_power'] = total_ajb_power
                data['inverter_dc_power'] = last_dc_power
                data['inverter_ac_power'] = last_power
                inverters_data.append(data)
            except Exception as exc:
                logger.debug(str(exc))

        result = inverters_data
        return result
    except Exception as exception:
        logger.debug(str(exception))
        return {}

def round_off_energy_values(value):
    try:
        if value < 10:
            value = round(float(value),3)
        elif 10 <= value < 100:
            value = round(float(value),2)
        elif 100 <= value < 1000:
            value = value = round(float(value),1)
        else:
            value = int(value)
        return value
    except Exception as exception:
        return value

def get_inverter_sld_parameters_new(plant, inverter_name):
    try:
        result = []
        inverter = IndependentInverter.objects.get(plant=plant, name=inverter_name)
        fields = SolarField.objects.filter(source=inverter, isActive=True)
        inverter_fields = []
        for field in fields:
            inverter_fields.append(str(field.name))
        inverter_fields = sorted_nicely(inverter_fields)
        for name in inverter_fields:
            field = SolarField.objects.get(source=inverter, name=name)
            if str(field.name) not in EXCLUDE_VISUALIZATION_STREAMS:
                try:
                    values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                     stream_name=str(field.name),
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                    print len(values)
                    if len(values)>0:
                        try:
                            value = float(values[0].stream_value)
                        except:
                            value = values[0].stream_value
                    else:
                        value = "NA"
                except Exception as exception:
                    print str(exception)
                    value = 'NA'

                try:
                    name = str(field.displayName) if field.displayName else str(field.name)
                    stream_name = str(field.name)
                    stream = SolarField.objects.get(source=inverter, name=stream_name)
                    stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                except Exception as exception:
                    print str(exception)
                    stream_unit = "NA"

                value_result = {}
                if value is not "NA" and stream_unit is not "NA":
                    value_result['name'] = name
                    try:
                        if str(field.name) in ['TOTAL_YIELD','DAILY_YIELD']:
                            value_result['value'] = str(round_off_energy_values(float(value))) + " " + str(stream_unit)
                        else:
                            value_result['value'] = str(round(float(value),2)) + " " + str(stream_unit)
                    except:
                        value_result['value'] = "NA"
                elif value is not "NA" and stream_unit is "NA":
                    if str(field.name) in ['TOTAL_YIELD','DAILY_YIELD']:
                        value_result['value'] = str(round_off_energy_values(float(value)))
                    else:
                        value_result['value'] = str(value)
                    value_result['name'] = name

                else:
                    value_result['name'] = name
                    value_result['value'] = "NA"
                result.append(value_result)
        return result
    except Exception as exception:
        print str(exception)

def get_inverter_sld_parameters(plant, inverter_name):
    try:
        result= []
        inverter = IndependentInverter.objects.get(plant=plant, name=inverter_name)
        # get DC Voltage
        try:
            last_dc_voltage = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                     stream_name='DC_VOLTAGE',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            last_dc_voltage = float(last_dc_voltage[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            last_dc_voltage = 0.0

        try:
            stream_name = 'DC_VOLTAGE'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"
        last_dc_voltage_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='DC_VOLTAGE')
        last_dc_voltage_result['name'] = solar_field.displayName
        last_dc_voltage_result['value'] = str(last_dc_voltage) + " " + stream_unit
        result.append(last_dc_voltage_result)
        # get DC Current
        try:
            last_dc_current = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name='DC_CURRENT',
                                                                      timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                      timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            last_dc_current = float(last_dc_current[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            last_dc_current = 0.0

        try:
            stream_name = 'DC_CURRENT'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"
        last_dc_current_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='DC_CURRENT')
        last_dc_current_result['name'] = solar_field.displayName
        last_dc_current_result['value'] = str(last_dc_current) + " " + stream_unit
        result.append(last_dc_current_result)

        # get DC Power
        try:
            last_dc_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name='DC_POWER',
                                                                      timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                      timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            last_dc_power = float(last_dc_power[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            last_dc_power = 0.0


        try:
            stream_name = 'DC_POWER'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        last_dc_power_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='DC_POWER')
        last_dc_power_result['name'] = solar_field.displayName
        last_dc_power_result['value'] = str(last_dc_power) + " " + stream_unit
        result.append(last_dc_power_result)

        # get AC Voltage R
        try:
            ac_voltage_r = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='AC_VOLTAGE_R',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_voltage_r = float(ac_voltage_r[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_voltage_r = 0.0

        try:
            stream_name = 'AC_VOLTAGE_R'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_voltage_r_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='AC_VOLTAGE_R')
        ac_voltage_r_result['name'] = solar_field.displayName
        ac_voltage_r_result['value'] = str(ac_voltage_r) + " " + stream_unit
        result.append(ac_voltage_r_result)

        # get AC Voltage Y
        try:
            ac_voltage_y = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='AC_VOLTAGE_Y',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_voltage_y = float(ac_voltage_y[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_voltage_y = 0.0

        try:
            stream_name = 'AC_VOLTAGE_Y'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_voltage_y_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='AC_VOLTAGE_Y')
        ac_voltage_y_result['name'] = solar_field.displayName
        ac_voltage_y_result['value'] = str(ac_voltage_y) + stream_unit
        result.append(ac_voltage_y_result)

        # get AC Voltage B
        try:
            ac_voltage_b = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='AC_VOLTAGE_B',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_voltage_b = float(ac_voltage_b[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_voltage_b = 0.0

        try:
            stream_name = 'AC_VOLTAGE_B'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_voltage_b_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='AC_VOLTAGE_B')
        ac_voltage_b_result['name'] = solar_field.displayName
        ac_voltage_b_result['value'] = str(ac_voltage_b) + " " + stream_unit
        result.append(ac_voltage_b_result)

        # get AC Current R
        try:
            ac_current_r = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='CURRENT_R',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_current_r = float(ac_current_r[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_current_r = 0.0

        try:
            stream_name = 'CURRENT_R'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_current_r_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='CURRENT_R')
        ac_current_r_result['name'] = solar_field.displayName
        ac_current_r_result['value'] = str(ac_current_r) + " " + stream_unit
        result.append(ac_current_r_result)

        # get AC Current Y
        try:
            ac_current_y = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='CURRENT_Y',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_current_y = float(ac_current_y[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_current_y = 0.0

        try:
            stream_name = 'CURRENT_Y'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_current_y_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='CURRENT_Y')
        ac_current_y_result['name'] = solar_field.displayName
        ac_current_y_result['value'] = str(ac_current_y) + " " + stream_unit
        result.append(ac_current_y_result)

        # get AC Current B
        try:
            ac_current_b = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='CURRENT_B',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_current_b = float(ac_current_b[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_current_b = 0.0

        try:
            stream_name = 'CURRENT_B'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_current_b_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='CURRENT_B')
        ac_current_b_result['name'] = solar_field.displayName
        ac_current_b_result['value'] = str(ac_current_b) + " " + stream_unit
        result.append(ac_current_b_result)

        # get current active power
        try:
            ac_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                 stream_name='ACTIVE_POWER',
                                                                 timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                 timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            ac_power = float(ac_power[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            ac_power = 0.0

        try:
            stream_name = 'ACTIVE_POWER'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        ac_power_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='ACTIVE_POWER')
        ac_power_result['name'] = solar_field.displayName
        ac_power_result['value'] = str(ac_power) + " " + stream_unit
        result.append(ac_power_result)

        # get grid impedance
        try:
            try:
                grid_impedance = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                         stream_name='GRID_IMPEDENCE',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                grid_impedance = float(grid_impedance[0].stream_value)
            except Exception as exc:
                logger.debug(exc)
                grid_impedance = 0.0

            try:
                stream_name = 'GRID_IMPEDENCE'
                stream = SolarField.objects.get(source=inverter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "NA"

            grid_impedance_result = {}
            solar_field = SolarField.objects.get(source=inverter, name='GRID_IMPEDENCE')
            grid_impedance_result['name'] = solar_field.displayName
            grid_impedance_result['value'] = str(grid_impedance) + " " + stream_unit
            result.append(grid_impedance_result)
        except:
            pass

        # get insulation impedance
        try:
            try:
                insulation_impedance = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                               stream_name='INSULATION_IMPEDENCE',
                                                                               timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                               timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                insulation_impedance = float(insulation_impedance[0].stream_value)
            except Exception as exc:
                logger.debug(exc)
                insulation_impedance = 0.0

            try:
                stream_name = 'INSULATION_IMPEDENCE'
                stream = SolarField.objects.get(source=inverter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "NA"

            insulation_impedance_result = {}
            solar_field = SolarField.objects.get(source=inverter, name='INSULATION_IMPEDENCE')
            insulation_impedance_result['name'] = solar_field.displayName
            insulation_impedance_result['value'] = str(insulation_impedance) + " " + stream_unit
            result.append(insulation_impedance_result)
        except:
            pass

        # get current reactive power
        try:
            reactive_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                     stream_name='REACTIVE_POWER',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            reactive_power = float(reactive_power[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            reactive_power = 0.0

        try:
            stream_name = 'REACTIVE_POWER'
            stream = SolarField.objects.get(source=inverter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "NA"

        reactive_power_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='REACTIVE_POWER')
        reactive_power_result['name'] = solar_field.displayName
        reactive_power_result['value'] = str(reactive_power) + " " + stream_unit
        result.append(reactive_power_result)

        # get current power factor
        try:
            power_factor = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                     stream_name='POWER_FACTOR',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
            power_factor = float(power_factor[0].stream_value)
        except Exception as exc:
            logger.debug(exc)
            power_factor = 0.0

        power_factor_result = {}
        solar_field = SolarField.objects.get(source=inverter, name='POWER_FACTOR')
        power_factor_result['name'] = solar_field.displayName
        power_factor_result['value'] = power_factor
        result.append(power_factor_result)

        sts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                 second=0, microsecond=0)
        ets = sts+timedelta(hours=24)

        inverters_generation = get_aggregated_energy(sts, ets, plant, aggregator='DAY', split=True, meter_energy=False)
        # get the generation for today
        try:
            today_generation = float(inverters_generation[0]['energy'][inverter.name])
        except:
            today_generation = 0.0
        generation_result = {}
        generation_result['name'] = 'generation'
        generation_result['value'] = str(today_generation) + " kWh"
        result.append(generation_result)

        return result
    except Exception as exception:
        logger.debug(str(exception))

def get_meter_sld_parameters_new(plant, meter_name):
    try:
        result = []
        meter = EnergyMeter.objects.get(plant=plant, name=meter_name)
        fields = SolarField.objects.filter(source=meter, isActive=True)
        meter_fields = []
        for field in fields:
            meter_fields.append(str(field.name))
        meter_fields = sorted_nicely(meter_fields)
        for name in meter_fields:
            field = SolarField.objects.get(source=meter, name=name)
            print field.name
            if str(field.name) not in EXCLUDE_VISUALIZATION_STREAMS:
                print "inside"
                try:
                    values = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name=str(field.name),
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                    print len(values)
                    if len(values)>0:
                        try:
                            value = float(values[0].stream_value)
                        except:
                            value = values[0].stream_value
                    else:
                        value = "NA"
                except Exception as exception:
                    print str(exception)
                    value = 'NA'

                try:
                    name = str(field.displayName) if field.displayName else str(field.name)
                    stream_name = str(field.name)
                    stream = SolarField.objects.get(source=meter, name=stream_name)
                    stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                except:
                    stream_unit = "NA"

                value_result = {}
                if value is not "NA" and stream_unit is not "NA":
                    value_result['name'] = name
                    try:
                        value_result['value'] = str(round(float(value),2)) + " " + str(stream_unit)
                    except:
                        value_result['value'] = "NA"
                elif value is not "NA" and stream_unit is "NA":
                    value_result['name'] = name
                    value_result['value'] = str(value)
                else:
                    value_result['name'] = name
                    value_result['value'] = "NA"
                result.append(value_result)
        return result
    except Exception as exception:
        print str(exception)



def get_meter_sld_parameters(plant, meter_name):
    try:
        result = []
        meter = EnergyMeter.objects.get(plant=plant, name=meter_name)

        # get Frequency
        try:
            stream = SolarField.objects.get(source=meter, name='Frequency')
            last_frequency = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name='Frequency',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            last_frequency = float(last_frequency[0].stream_value)
        except Exception as exc:
            print(str(exc))
            last_frequency = 0.0

        if last_frequency == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='HZ')
                last_frequency = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='HZ',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_frequency = float(last_frequency[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_frequency = 0.0

        if last_frequency == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='FQ')
                last_frequency = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='FQ',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_frequency = float(last_frequency[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_frequency = 0.0

        last_frequency_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='Frequency')
        name = stream.displayName if stream.displayName is not None else stream.name
        last_frequency_result['name'] = name
        last_frequency_result['value'] = str("{0:.2f}".format(last_frequency)) + " Hz"
        result.append(last_frequency_result)

        # get VLL_AVG
        try:
            last_vll_avg = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                   stream_name='VLL_AVG',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            last_vll_avg = float(last_vll_avg[0].stream_value)
        except Exception as exc:
            print(str(exc))
            last_vll_avg = 0.0

        try:
            stream_name = 'VLL_AVG'
            stream = SolarField.objects.get(source=meter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "V"

        if last_vll_avg == 0.0:
            try:
                last_vll_avg = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                       stream_name='VOLT_LTL',
                                                                       timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                       timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_vll_avg = float(last_vll_avg[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_vll_avg = 0.0

            try:
                stream_name = 'VOLT_LTL'
                stream = SolarField.objects.get(source=meter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "V"

        if last_vll_avg == 0.0:
            try:
                last_vll_avg = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                       stream_name='Vavg',
                                                                       timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                       timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_vll_avg = float(last_vll_avg[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_vll_avg = 0.0

            try:
                stream_name = 'Vavg'
                stream = SolarField.objects.get(source=meter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "V"

        last_vll_avg_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='VLL_AVG')
        name = stream.displayName if stream.displayName is not None else stream.name
        last_vll_avg_result['name'] = name
        last_vll_avg_result['value'] = str("{0:.2f}".format(last_vll_avg)) + " " + stream_unit
        result.append(last_vll_avg_result)

        # get C_R_PHASE
        try:
            stream = SolarField.objects.get(source=meter, name='C_R_PHASE')
            last_c_r_phase = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name='C_R_PHASE',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            last_c_r_phase = float(last_c_r_phase[0].stream_value)
        except Exception as exc:
            print(str(exc))
            last_c_r_phase = 0.0

        if last_c_r_phase == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='I1')
                last_c_r_phase = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='I1',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_c_r_phase = float(last_c_r_phase[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_c_r_phase = 0.0

        last_c_r_phase_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='C_R_PHASE')
        name = stream.displayName if stream.displayName is not None else stream.name
        last_c_r_phase_result['name'] = name
        last_c_r_phase_result['value'] = str("{0:.2f}".format(last_c_r_phase)) + " A"
        result.append(last_c_r_phase_result)

        # get C_Y_PHASE
        try:
            stream = SolarField.objects.get(source=meter, name='C_Y_PHASE')
            last_c_y_phase = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name='C_Y_PHASE',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            last_c_y_phase = float(last_c_y_phase[0].stream_value)
        except Exception as exc:
            print(str(exc))
            last_c_y_phase = 0.0

        if last_c_y_phase == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='I2')
                last_c_y_phase = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='I2',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_c_y_phase = float(last_c_y_phase[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_c_y_phase = 0.0

        last_c_y_phase_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='C_Y_PHASE')
        name = stream.displayName if stream.displayName is not None else stream.name
        last_c_y_phase_result['name'] = name
        last_c_y_phase_result['value'] = str("{0:.2f}".format(last_c_y_phase)) + " A"
        result.append(last_c_y_phase_result)

        # get C_B_PHASE
        try:
            stream = SolarField.objects.get(source=meter, name='C_B_PHASE')
            last_c_b_phase = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name='C_B_PHASE',
                                                                     timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                     timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            last_c_b_phase = float(last_c_b_phase[0].stream_value)
        except Exception as exc:
            print(str(exc))
            last_c_b_phase = 0.0

        if last_c_b_phase == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='I3')
                last_c_b_phase = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='I3',
                                                                         timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                         timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                last_c_b_phase = float(last_c_b_phase[0].stream_value)
            except Exception as exc:
                print(str(exc))
                last_c_b_phase = 0.0

        last_c_b_phase_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='C_B_PHASE')
        name = stream.displayName if stream.displayName is not None else stream.name
        last_c_b_phase_result['name'] = name
        last_c_b_phase_result['value'] = str("{0:.2f}".format(last_c_b_phase)) + " A"
        result.append(last_c_b_phase_result)

        # get Power Factor
        try:
            stream = SolarField.objects.get(source=meter, name='PF_AVG')
            power_factor = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                   stream_name='PF_AVG',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            power_factor = float(power_factor[0].stream_value)
        except Exception as exc:
            print(str(exc))
            power_factor = 0.0

        if power_factor == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='PF')
                power_factor = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                       stream_name='PF',
                                                                       timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                       timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                power_factor = float(power_factor[0].stream_value)
            except Exception as exc:
                print(str(exc))
                power_factor = 0.0

        if power_factor == 0.0:
            try:
                stream = SolarField.objects.get(source=meter, name='QA')
                power_factor = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                       stream_name='QA',
                                                                       timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                       timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                power_factor = float(power_factor[0].stream_value)
            except Exception as exc:
                print(str(exc))
                power_factor = 0.0

        power_factor_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='PF_AVG')
        name = stream.displayName if stream.displayName is not None else stream.name
        power_factor_result['name'] = name
        power_factor_result['value'] = power_factor
        result.append(power_factor_result)

        # 3 phase Active Power
        try:
            watt_total = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                   stream_name='WATT_TOTAL',
                                                                   timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                   timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            watt_total = float(watt_total[0].stream_value)
        except Exception as exc:
            print(str(exc))
            watt_total = 0.0

        try:
            stream_name = 'WATT_TOTAL'
            stream = SolarField.objects.get(source=meter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "kW"

        if watt_total == 0.0:
            try:
                watt_total = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                       stream_name='W',
                                                                       timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                       timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                watt_total = float(watt_total[0].stream_value)
            except Exception as exc:
                print(str(exc))
                watt_total = 0.0

            try:
                stream_name = 'W'
                stream = SolarField.objects.get(source=meter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "kW"

        if watt_total == 0.0:
            try:
                watt_total = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                       stream_name='KT',
                                                                       timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                       timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                watt_total = float(watt_total[0].stream_value)
            except Exception as exc:
                print(str(exc))
                watt_total = 0.0

            try:
                stream_name = 'KT'
                stream = SolarField.objects.get(source=meter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "kW"

        watt_total_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='WATT_TOTAL')
        name = stream.displayName if stream.displayName else stream.name
        watt_total_result['name'] = name
        watt_total_result['value'] = str("{0:.2f}".format(watt_total)) + " " + stream_unit
        result.append(watt_total_result)

        # 3 phase Reactive Power
        try:
            var_total = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                stream_name='VAR_TOTAL',
                                                                timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            var_total = float(var_total[0].stream_value)
        except Exception as exc:
            print(str(exc))
            var_total = 0.0

        try:
            stream_name = 'VAR_TOTAL'
            stream = SolarField.objects.get(source=meter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "kVAR"

        if var_total == 0.0:
            try:
                var_total = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                    stream_name='VAR',
                                                                    timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                    timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                var_total = float(var_total[0].stream_value)
            except Exception as exc:
                print(str(exc))
                var_total = 0.0

            try:
                stream_name = 'VAR'
                stream = SolarField.objects.get(source=meter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "kVAR"

        if var_total == 0.0:
            try:
                var_total = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                    stream_name='KV',
                                                                    timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                    timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                var_total = float(var_total[0].stream_value)
            except Exception as exc:
                print(str(exc))
                var_total = 0.0

            try:
                stream_name = 'KV'
                stream = SolarField.objects.get(source=meter, name=stream_name)
                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
            except:
                stream_unit = "kVAR"

        var_total_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='VAR_TOTAL')
        name = stream.displayName if stream.displayName else stream.name
        var_total_result['name'] = name
        var_total_result['value'] = str("{0:.2f}".format(var_total)) + " " + stream_unit
        result.append(var_total_result)

        # sts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
        #                                                          second=0, microsecond=0)
        # ets = sts+timedelta(hours=24)
        # meters_generation = get_aggregated_energy(sts, ets, plant, aggregator='DAY', split=True, meter_energy=True)
        # #solar_field = SolarField.objects.get(source=meter, name='Wh_RECEIVED')
        # generation_result = {}
        # if meters_generation and len(meters_generation)>0:
        #     try:
        #         today_generation = float(meters_generation[0]['energy'][meter.name])
        #         print today_generation
        #         try:
        #             stream_unit = ENERGY_METER_STREAM_UNITS[str(plant.slug)]
        #             conversion_unit = ENERGY_METER_STREAM_UNIT_FACTOR[stream_unit]
        #             today_generation = today_generation/float(conversion_unit)
        #         except:
        #             today_generation = today_generation/1000.0
        #     except:
        #         today_generation = 0.0
        #     try:
        #         stream = SolarField.objects.get(source=meter, name='Wh_RECEIVED')
        #         name = stream.displayName if stream.displayName else stream.name
        #     except:
        #         name = 'MWH Received'
        #     generation_result['name'] = name
        #     generation_result['value'] = str("{0:.2f}".format(today_generation)) + " MWh"
        #
        #     result.append(generation_result)

        #Energy Import
        try:
            energy_import = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                    stream_name='Wh_RECEIVED',
                                                                    timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                    timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            energy_import = float(energy_import[0].stream_value)
        except Exception as exc:
            print(str(exc))
            energy_import = 0.0

        try:
            stream_name = 'Wh_RECEIVED'
            stream = SolarField.objects.get(source=meter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "kWh"

        energy_import_result = {}
        name = stream.displayName if stream.displayName else stream.name
        energy_import_result['name'] = name
        energy_import_result['value'] = str("{0:.2f}".format(energy_import)) + " " + stream_unit
        result.append(energy_import_result)

        #Energy Export
        try:
            energy_export = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                    stream_name='Wh_DELIVERED',
                                                                    timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                    timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            energy_export = float(energy_export[0].stream_value)
        except Exception as exc:
            print(str(exc))
            energy_export = 0.0

        try:
            stream_name = 'Wh_DELIVERED'
            stream = SolarField.objects.get(source=meter, name=stream_name)
            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
        except:
            stream_unit = "kWh"

        energy_export_result = {}
        name = stream.displayName if stream.displayName else stream.name
        energy_export_result['name'] = name
        energy_export_result['value'] = str("{0:.2f}".format(energy_export)) + " " + stream_unit
        result.append(energy_export_result)

        # Circuit Breaker Status
        try:
            circuit_breaker = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                      stream_name='CIRCUIT_BREAKER',
                                                                      timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                      timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
            circuit_breaker = circuit_breaker[0].stream_value
        except Exception as exc:
            print(str(exc))
            circuit_breaker = "NA"

        circuit_breaker_result = {}
        #solar_field = SolarField.objects.get(source=meter, name='CIRCUIT_BREAKER')
        circuit_breaker_result['name'] = 'Circuit Breaker Status'
        circuit_breaker_result['value'] = circuit_breaker
        result.append(circuit_breaker_result)

        return result

    except Exception as exception:
        print(str(exception))
        return []

def get_plant_ac_live_data_status(plant, current_time, fill_meters=True, meter_name=None):
    try:
        result = {}
        # inverters details
        if meter_name:
            meters = plant.energy_meters.all().filter(isActive=True).filter(name=meter_name)
        else:
            meters = plant.energy_meters.all().filter(isActive=True).order_by('id')
        meters_name = []
        for meter in meters:
            meters_name.append(str(meter.name))
        meters_name = sorted_nicely(meters_name)
        meters = []
        for name in meters_name:
            meter = EnergyMeter.objects.get(plant=plant, name=name)
            meters.append(meter)

        meters_data = []

        if plant.slug in ["instaproducts",'beaconsfield', 'ausnetdemosite', 'benalla', 'collingwood', 'leongatha', 'lilydale', 'rowville', 'seymour', 'thomastown', 'traralgon', 'wodonga', 'yarraville']:
            sts = datetime.now(pytz.timezone(plant.metadata.dataTimezone)).replace(hour=0, minute=0,
                                                                      second=0, microsecond=0)
        else:
            sts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                 second=0, microsecond=0)

        ets = sts+timedelta(hours=24)
        meters_generation = get_minutes_aggregated_energy(sts, ets, plant, 'DAY', 1, split=True, meter_energy=True, all_meters=True)
        #print meters_generation
        # Get all the solar groups
        solar_groups_name = plant.solar_groups.all()
        if len(solar_groups_name) == 0:
            result['solar_groups'] = []
            result['total_group_number'] = 0
        else:
            solar_group_list = []
            for i in range(len(solar_groups_name)):
                solar_group_list.append(str(solar_groups_name[i].name))

            result['solar_groups'] = solar_group_list
            result['total_group_number'] = len(solar_groups_name)

        stats = get_user_data_monitoring_status(plant.energy_meters)

        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
        else:
            active_alive_valid = None
            active_dead = None

        if fill_meters:
            for meter in meters:
                try:
                    data = {}

                    # get the generation for today
                    try:
                        today_generation = float(meters_generation[meter.name][0]['energy'])
                        # try:
                        #     stream_unit = ENERGY_METER_STREAM_UNITS[str(plant.slug)]
                        #     conversion_unit = ENERGY_METER_STREAM_UNIT_FACTOR[stream_unit]
                        #     today_generation = today_generation/float(conversion_unit)
                        # except:
                        #     today_generation = today_generation
                        #today_generation  = today_generation/1000.0
                    except:
                        today_generation = 0.0

                    today_generation = str("{0:.2f}".format(today_generation)) + " " + "kWh"

                    # get current power
                    try:
                        last_power = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                             stream_name='WATT_TOTAL',
                                                                             timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                             timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                        last_power = float(last_power[0].stream_value)
                    except Exception as exc:
                        logger.debug(exc)
                        last_power = 0.0

                    try:
                        stream_name = 'WATT_TOTAL'
                        stream = SolarField.objects.get(source=meter, name=stream_name)
                        stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                    except:
                        stream_unit = "kW"

                    if last_power == 0.0:
                        try:
                            last_power = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                                 stream_name='W',
                                                                                 timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                                 timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                            last_power = float(last_power[0].stream_value)
                        except Exception as exc:
                            logger.debug(exc)
                            last_power = 0.0

                        try:
                            stream_name = 'W'
                            stream = SolarField.objects.get(source=meter, name=stream_name)
                            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                        except:
                            stream_unit = "kW"

                    if last_power == 0.0:
                        try:
                            last_power = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                                 stream_name='KT',
                                                                                 timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                                 timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                            last_power = float(last_power[0].stream_value)
                        except Exception as exc:
                            logger.debug(exc)
                            last_power = 0.0

                        try:
                            stream_name = 'KT'
                            stream = SolarField.objects.get(source=meter, name=stream_name)
                            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                        except:
                            stream_unit = "kW"

                    last_power = str("{0:.2f}".format(last_power)) + " " + stream_unit


                    # get current total yield
                    try:
                        last_total_yield = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                                   stream_name='Wh_RECEIVED').limit(1)

                        last_total_yield = float(last_total_yield[0].stream_value)
                    except Exception as exc:
                        logger.debug(exc)
                        last_total_yield = 0.0

                    if last_total_yield == 0.0:
                        try:
                            last_total_yield = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                                       stream_name='KWH').limit(1)

                            last_total_yield = float(last_total_yield[0].stream_value)
                        except Exception as exc:
                            logger.debug(exc)
                            last_total_yield = 0.0

                    if last_total_yield == 0.0:
                        try:
                            last_total_yield = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                                       stream_name='kWhT(I)').limit(1)

                            last_total_yield = float(last_total_yield[0].stream_value)
                        except Exception as exc:
                            logger.debug(exc)
                            last_total_yield = 0.0

                    # get the connection status
                    # if active_alive_valid:
                    if meter.sourceKey in active_alive_valid:
                        connected = "connected"
                    elif meter.sourceKey in active_dead:
                        connected = "disconnected"
                    else:
                        connected = "unknown"

                    # data for this inverter
                    data['name'] = meter.name
                    data['generation'] = today_generation
                    data['power'] = last_power
                    data['connected'] = connected
                    data['key'] = meter.sourceKey
                    if len(meter.solar_groups.all()) != 0:
                        data['solar_group'] = str(meter.solar_groups.all()[0].name)
                    else:
                        data['solar_group'] = "NA"
                    data['total_yield'] = last_total_yield

                    # populate in the inverters data list
                    meters_data.append(data)
                except Exception as exc:
                    logger.debug(str(exc))
                    continue

        result['meters'] = meters_data
        if meter_name:
            result['ac_sld'] = get_meter_sld_parameters_new(plant, meter_name)
        return result
    except Exception as exception:
        print(str(exception))
        return {}

def get_plant_ac_live_data_status_transformer(plant, current_time, fill_transformers=True, transformer_name=None):
    try:
        result = {}
        # inverters details
        if transformer_name:
            transformers = plant.transformers.all().filter(isActive=True).filter(name=transformer_name)
        else:
            transformers = plant.transformers.all().filter(isActive=True).order_by('id')
        transformers_name = []
        for transformer in transformers:
            transformers_name.append(str(transformer.name))
        transformers_name = sorted_nicely(transformers_name)
        transformers = []
        for name in transformers_name:
            transformer = Transformer.objects.get(plant=plant, name=name)
            transformers.append(transformer)

        transformers_data = []

        stats = get_user_data_monitoring_status(plant.transformers)
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
        else:
            active_alive_valid = None
            active_dead = None

        if fill_transformers:
            for transformer in transformers:
                try:
                    data = {}

                    # OTI Status
                    try:
                        oti_status = ValidDataStorageByStream.objects.filter(source_key=transformer.sourceKey,
                                                                             stream_name='OTI_DESCRIPTION',
                                                                             timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                             timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=transformer.timeoutInterval)).limit(1)
                        oti_status = oti_status[0].stream_value
                    except Exception as exc:
                        print(exc)
                        oti_status = "NA"

                    # WTI Status
                    try:
                        wti_status = ValidDataStorageByStream.objects.filter(source_key=transformer.sourceKey,
                                                                             stream_name='WTI_DESCRIPTION',
                                                                             timestamp_in_data__lte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                             timestamp_in_data__gte=datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=transformer.timeoutInterval)).limit(1)
                        wti_status = wti_status[0].stream_value
                    except Exception as exc:
                        print(exc)
                        wti_status = "NA"

                    # get the connection status
                    # if active_alive_valid:
                    if transformer.sourceKey in active_alive_valid:
                        connected = "connected"
                    elif transformer.sourceKey in active_dead:
                        connected = "disconnected"
                    else:
                        connected = "unknown"

                    # data for this inverter
                    data['name'] = transformer.name
                    data['connected'] = connected
                    data['key'] = transformer.sourceKey
                    data['OTI'] = oti_status
                    data['WTI'] = wti_status

                    # populate in the inverters data list
                    transformers_data.append(data)
                except Exception as exc:
                    logger.debug(str(exc))
                    continue

        result['transformers'] = transformers_data
        return result
    except Exception as exception:
        print(str(exception))
        return {}

def get_plant_live_data_status(plant, current_time, fill_inverters=True, inverter_name=None, mobile_app=True):
    try:
        result = {}
        # inverters details
        if plant.slug == 'rrkabel':
            if inverter_name:
                inverters_unordered = plant.independent_inverter_units.all().filter(isActive=True).filter(name=inverter_name)
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters_unordered = plant.independent_inverter_units.all().filter(isActive=True).order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
        else:
            if inverter_name:
                inverters = plant.independent_inverter_units.all().filter(isActive=True).filter(name=inverter_name)
            else:
                inverters = plant.independent_inverter_units.all().filter(isActive=True).order_by('id')
            inverters_name = []
            for inverter in inverters:
                inverters_name.append(str(inverter.name))
            inverters_name = sorted_nicely(inverters_name)
            logger.debug(inverters_name)
            inverters = []
            for name in inverters_name:
                inverter = IndependentInverter.objects.get(plant=plant, name=name)
                inverters.append(inverter)

        inverters_data = []

        # just return the sld parameters if it's a query for a specific inverter
        if inverter_name:
            result['dc_sld'] = get_inverter_sld_parameters_new(plant, inverter_name)
            try:
                last_timestamp_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                              stream_name='TOTAL_YIELD').limit(1)

                if len(last_timestamp_data) == 0:
                    last_timestamp_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                  stream_name='DAILY_YIELD').limit(1)

                if len(last_timestamp_data) > 0:
                    last_timestamp = last_timestamp_data[0].timestamp_in_data
                    last_timestamp = update_tz(last_timestamp, plant.metadata.plantmetasource.dataTimezone).strftime(
                        '%Y-%m-%dT%H:%M:%SZ')
                else:
                    last_timestamp = "NA"
            except Exception as exc:
                print str(exc)
                last_timestamp = "NA"
            result['last_timestamp'] = last_timestamp
            return result

        sts = datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                 second=0, microsecond=0)
        ets = sts+timedelta(hours=24)

        #inverters_generation = get_aggregated_energy(sts, ets, plant, aggregator='DAY', split=True, meter_energy=False)
        inverters_generation = get_minutes_aggregated_energy(sts, ets, plant, 'DAY', 1, split=True, meter_energy=False, live=True)
        inverters_generation = convert_new_energy_data_format_to_old_format(inverters_generation)

        # Get all the solar groups
        solar_groups_name = plant.solar_groups.all()
        if len(solar_groups_name) == 0:
            result['solar_groups'] = []
            result['total_group_number'] = 0
        else:
            solar_group_list = []
            for i in range(len(solar_groups_name)):
                solar_group_list.append(str(solar_groups_name[i].name))

            result['solar_groups'] = solar_group_list
            result['total_group_number'] = len(solar_groups_name)

        if fill_inverters:
            from utils.multiprocess import get_plant_live_inverters_status_mp
            t0 = timezone.now()
            if inverter_name:
                inverters_data = get_plant_live_inverters_status_mp(plant,
                                                                    inverters,
                                                                    inverters_generation)
                # logger.debug("LIVEAPI HUA API: " + str(inverters_data))
            else:
                inverters_data = get_plant_live_inverters_status_mp(plant,
                                                                    inverters,
                                                                    inverters_generation,
                                                                    mobile_app=mobile_app)
            # logger.debug("LIVEAPI HUA _ get_plant_live_data_status: " + str(inverters_data))
            logger.debug("inverters live status time: " + str(timezone.now() - t0))
        result['inverters'] = inverters_data
        # if inverter_name:
        #     result['dc_sld'] = get_inverter_sld_parameters_new(plant, inverter_name)
        return result
    except Exception as exception:
        logger.debug(str(exception))
        return {}


def get_plant_status_data_offline(plant, user, date, clientpage=False, live=False, combined=False):
    try:
        plant_value = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            organization_user = user.organizations_organizationuser.all()[0]
            plant_value['plant_name'] = value[0].name
            plant_value['plant_slug'] = plant.slug
            logo = plant.dataglengroup.groupLogo if plant.dataglengroup and plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
            plant_value['plant_logo'] = logo
            plant_value['plant_capacity'] = float(value[0].capacity)
            plant_value['plant_location'] = value[0].location
            plant_value['latitude'] = value[0].latitude
            plant_value['longitude'] = value[0].longitude
            try:
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                    plant_value['performance_ratio'] = "{0:.2f}".format(value[0].pr) if value[0].pr else 0.0
                    plant_value['cuf'] = "{0:.2f}".format(value[0].cuf) if value[0].cuf else 0.0
            except:
                pass
            plant_value['grid_unavailability'] = str("{0:.2f}".format(value[0].grid_unavailability)) + " %" if value[0].grid_unavailability else "0 %"
            plant_value['equipment_unavailability'] = str("{0:.2f}".format(value[0].equipment_unavailability)) + " %" if value[0].equipment_unavailability else "0 %"
            plant_value['unacknowledged_tickets'] = value[0].unacknowledged_tickets
            plant_value['open_tickets'] = value[0].open_tickets
            plant_value['closed_tickets'] = value[0].closed_tickets
            plant_value['plant_generation_today'] = fix_generation_units(float(value[0].plant_generation_today))
            plant_value['plant_total_energy'] = fix_generation_units(float(value[0].total_generation))
            try:
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].economic_benefits):
                    plant_value['plant_co2'] = fix_co2_savings(float(value[0].co2_savings))
            except:
                pass
            plant_value['dc_loss'] = fix_generation_units(float(value[0].dc_loss))
            plant_value['conversion_loss'] = fix_generation_units(float(value[0].conversion_loss))
            plant_value['ac_loss'] = fix_generation_units(float(value[0].ac_loss))
            if len(plant.pvsyst_info.all())>0:
                current_month = date.month
                pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=date.year,
                                                                   timePeriodValue=current_month)
                if len(pv_sys_info_generation)==0:
                    pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                       parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                       timePeriodType='MONTH',
                                                                       timePeriodDay=0,
                                                                       timePeriodYear=0,
                                                                       timePeriodValue=current_month)
                plant_capacity = plant.capacity
                if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
                    pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
                    plant_value['pvsyst_generation'] = fix_generation_units(pvsyst_generation)

                pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='PERFORMANCE_RATIO',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=date.year,
                                                           timePeriodValue=current_month)
                if len(pv_sys_info_pr) == 0:
                    pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='PERFORMANCE_RATIO',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)

                if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
                    pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
                    plant_value['pvsyst_pr'] = pvsyst_pr

                pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='TILT_ANGLE',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=date.year,
                                                                   timePeriodValue=current_month)
                if len(pv_sys_info_tilt_angle) == 0:
                    pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                                       parameterName='TILT_ANGLE',
                                                                       timePeriodType='MONTH',
                                                                       timePeriodDay=0,
                                                                       timePeriodYear=0,
                                                                       timePeriodValue=current_month)

                if len(pv_sys_info_tilt_angle)> 0 and pv_sys_info_tilt_angle[0].parameterValue is not None:
                    pvsyst_tilt_angle = float(pv_sys_info_tilt_angle[0].parameterValue)
                    plant_value['pvsyst_tilt_angle'] = pvsyst_tilt_angle
            try:
                if plant.gateway.all()[0].isMonitored:
                    if not plant.gateway.all()[0].isVirtual:
                        stats = get_user_data_monitoring_status(plant.gateway)
                        if stats is not None:
                            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                            errors_len = len(active_dead) + len(deactivated_alive)
                            unmonitored = len(unmonitored)
                        else:
                            errors_len = 0
                            unmonitored = 0
                        if unmonitored is not 0 :
                            network_up = 'unknown'
                        elif errors_len is not 0:
                            network_up = 'No'
                        else:
                            network_up = 'Yes'
                    else:
                        isNetworkUp = check_network_for_virtual_gateways(plant)
                        if isNetworkUp:
                            network_up = 'Yes'
                        else:
                            network_up = 'No'
                else:
                    network_up = 'unknown'
            except:
                pass

            try:
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                    plant_value['past_pr'] = ast.literal_eval(str(value[0].past_pr))
            except:
                pass

            try:
                past_monthly_energy_list = []
                past_energy_values = HistoricEnergyValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                         identifier=plant.slug).order_by('-ts').values_list('energy', 'ts')
                for past_energy_value in past_energy_values:
                    past_energy_values = {}
                    past_energy_values['timestamp'] = str(past_energy_value[1])
                    past_energy_values['energy'] = fix_generation_units(past_energy_value[0])
                    past_monthly_energy_list.append(past_energy_values)
            except Exception as exception:
                logger.debug(str(exception))
                pass

            try:
                past_kwh_per_meter_square_list = []
                past_kwh_per_meter_square_values = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=plant.metadata.plantmetasource.sourceKey).order_by('-ts').values_list('value', 'ts').limit(7)
                for past_kwh_value in past_kwh_per_meter_square_values:
                    past_kwh_values = {}
                    past_kwh_values['timestamp'] = str(past_kwh_value[1])
                    past_kwh_values['kwh_value'] = str("{0:.2f}".format(float(past_kwh_value[0]))) + " kWh/m^2"
                    past_kwh_per_meter_square_list.append(past_kwh_values)
                plant_value['past_kwh_per_meter_square'] = past_kwh_per_meter_square_list
            except Exception as exception:
                print(str(exception))
                pass
            try:
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                    # past specific yield
                    try:
                        past_specific_yield_list = []
                        past_specific_yield_values = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                       identifier=plant.metadata.plantmetasource.sourceKey).order_by('-ts').values_list('specific_yield', 'ts').limit(7)
                        for past_specific_yield_value in past_specific_yield_values:
                            past_specific_yield_value_dict = {}
                            past_specific_yield_value_dict['timestamp'] = str(past_specific_yield_value[1])
                            past_specific_yield_value_dict['specific_yield'] = round(float(past_specific_yield_value[0]),2)
                            past_specific_yield_list.append(past_specific_yield_value_dict)
                        plant_value['past_specific_yield'] = past_specific_yield_list
                    except Exception as exception:
                        print(str(exception))
                        pass
                    # today's specific yield
                    try:
                        plant_value['specific_yield'] = round(float(past_specific_yield_values[len(past_specific_yield_values)-1][0]),2)
                    except:
                        plant_value['specific_yield'] = 0.0
            except:
                pass

            # past_monthly_generation_unit = []
            # for index in range(len(past_monthly_energy_list)):
            #     past_monthly_generation_unit.append(str(past_monthly_energy_list[index]['energy']).split(" ")[1].lower())
            # GWh_count = past_monthly_generation_unit.count('GWh'.lower())
            # MWh_count = past_monthly_generation_unit.count('MWh'.lower())
            # kWh_count = past_monthly_generation_unit.count('kWh'.lower())
            # if GWh_count != 0 and MWh_count != 0 and kWh_count != 0:
            #     # convert remaining values to GWh
            #     for index in range(len(past_monthly_generation_unit)):
            #         if past_monthly_generation_unit[index] == 'mwh':
            #             past_monthly_energy_list[index]['energy'] = '{0:.1f} GWh'.format(float(past_monthly_energy_list[index]['energy'].split(" ")[0])/1000.0)
            #         elif past_monthly_generation_unit[index] == 'kwh':
            #             past_monthly_energy_list[index]['energy'] = '{0:.1f} GWh'.format(float(past_monthly_energy_list[index]['energy'].split(" ")[0])/1000000.0)
            #         else:
            #             pass
            # elif GWh_count !=0 and MWh_count != 0 and kWh_count == 0:
            #     # convert remaining values to GWh
            #     for index in range(len(past_monthly_generation_unit)):
            #         if past_monthly_generation_unit[index] == 'mwh':
            #             past_monthly_energy_list[index]['energy'] = '{0:.1f} GWh'.format(float(past_monthly_energy_list[index]['energy'].split(" ")[0])/1000.0)
            #         else:
            #             pass
            # elif GWh_count !=0 and MWh_count == 0 and kWh_count != 0:
            #     # convert remaining values to GWh
            #     for index in range(len(past_monthly_generation_unit)):
            #         if past_monthly_generation_unit[index] == 'kwh':
            #             past_monthly_energy_list[index]['energy'] = '{0:.1f} GWh'.format(float(past_monthly_energy_list[index]['energy'].split(" ")[0])/1000000.0)
            #         else:
            #             pass
            # elif GWh_count == 0 and MWh_count !=0 and kWh_count !=0:
            #     #convert the remaining values to MWh
            #     for index in range(len(past_monthly_generation_unit)):
            #         if past_monthly_generation_unit[index] == 'kwh':
            #             past_monthly_energy_list[index]['energy'] = '{0:.1f} MWh'.format(float(past_monthly_energy_list[index]['energy'].split(" ")[0])/1000.0)
            #         else:
            #             pass
            # else:
            #     pass
            past_monthly_energy_list = convert_values_to_common_unit(past_monthly_energy_list)
            plant_value['past_monthly_generation'] = past_monthly_energy_list

            # SMB's having string high or low errors
            #TODO: Move this parameter(string_errors_smbs) to PlantCompleteValues table
            string_error_smbs = set()
            ajbs = plant.ajb_units.all().filter(isActive=True)
            starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime_prediction = date.replace(hour=6, minute=0, second=0, microsecond=0)
            endtime = date
            endtime_today = date.replace(hour=23, minute=0, second=0, microsecond=0)
            try:
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                    for ajb in ajbs:
                        string_errors = EventsByTime.objects.filter(identifier=str(ajb.sourceKey)+'_ajb',insertion_time__gte=starttime, insertion_time__lte=endtime)
                        if len(string_errors)>0:
                            string_error_smbs.add(str(ajb.name))
                    plant_value['string_errors_smbs'] = len(string_error_smbs)
            except:
                pass

            #Today's predicted energy value
            try:
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                    predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                    plant_value['today_predicted_energy_value_till_time'] = fix_generation_units(predicted_energy_value)

                    duration_hours = (endtime - starttime_prediction).total_seconds()/3600
                    final_duration_hours = min(duration_hours, 12)

                    #Total today's predicted energy value
                    total_predicted_energy_value = get_energy_prediction_data(starttime, endtime_today, plant)
                    plant_value['total_today_predicted_energy_value'] = fix_generation_units(total_predicted_energy_value)

                    if network_up == 'Yes':
                        try:
                            plant_value['prediction_deviation'] = abs(((float(predicted_energy_value)-float(value[0].plant_generation_today))/(float(plant_value['plant_capacity'])*final_duration_hours))*100)
                        except Exception as exception:
                            logger.debug(str(exception))
                            plant_value['prediction_deviation'] = 0.0
                        plant_value['prediction_deviation'] = str("{0:.2f}".format(float(plant_value['prediction_deviation']))) + " %"
                    else:
                        plant_value['prediction_deviation'] = 'NA'
            except:
                pass

            plant_value['plant_capacity'] = fix_capacity_units(float(value[0].capacity))

            if live:
                plant_value['current_power'] = value[0].active_power
                plant_value['irradiation'] = "{0:.2f}".format(value[0].irradiation) if value[0].irradiation else 0.0

                # Adding maximum power
                try:
                    power_df = get_plant_power(starttime, endtime, plant, True, False, False, True)
                    if not power_df.empty:
                        plant_value['max_power'] = power_df['sum'].max()
                    else:
                        plant_value['max_power'] = 0.0
                except:
                    plant_value['max_power'] = 0.0

                try:
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                        plant_value['disconnected_inverters'] = 0
                        plant_value['disconnected_smbs'] = 0
                        plant_value['connected_inverters'] = value[0].connected_inverters
                        #plant_value['disconnected_inverters'] = value[0].disconnected_inverters
                        plant_value['invalid_inverters'] = value[0].invalid_inverters
                        plant_value['connected_smbs'] = value[0].connected_smbs
                        #plant_value['disconnected_smbs'] = value[0].disconnected_smbs
                        plant_value['invalid_smbs'] = value[0].invalid_smbs
                        if network_up == 'Yes':
                            # print(plant.slug)
                            # plant_value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                            #                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                            #                                                  identifier=plant.metadata.plantmetasource.sourceKey,
                            #                                                  ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

                            plant_value['disconnected_inverters'] += int(value[0].disconnected_inverters)
                            plant_value['disconnected_smbs'] += int(value[0].disconnected_smbs)
                except:
                    pass
                plant_value['network_up'] = network_up
                plant_value['status'] = value[0].status
                plant_value['updated_at'] = value[0].updated_at
                plant_value['module_temperature'] = value[0].module_temperature
                plant_value['ambient_temperature'] = value[0].ambient_temperature
                plant_value['windspeed'] = value[0].windspeed
            if clientpage:
                plant_value['past_generations'] = ast.literal_eval(str(value[0].past_generations))

                if len(plant.pvsyst_info.all())>0:
                    for index in range(len(plant_value['past_generations'])):
                        try:
                            generation_dt = plant_value['past_generations'][index]['timestamp']
                            generation_date = parser.parse(generation_dt)
                            generation_date_month = generation_date.month
                            pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                               parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                               timePeriodType='MONTH',
                                                                               timePeriodDay=0,
                                                                               timePeriodYear=generation_date.year,
                                                                               timePeriodValue=generation_date_month)
                            if len(pv_sys_info_generation) == 0:
                                pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                                   parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                                   timePeriodType='MONTH',
                                                                                   timePeriodDay=0,
                                                                                   timePeriodYear=generation_date.year,
                                                                                   timePeriodValue=generation_date_month)
                            plant_capacity = plant.capacity
                            if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
                                pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
                                plant_value['past_generations'][index]['pvsyst_generation'] = fix_generation_units(pvsyst_generation)
                        except:
                            continue
                #plant_value['past_pr'] = ast.literal_eval(str(value[0].past_pr))
                try:
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                        plant_value['past_cuf'] = ast.literal_eval(str(value[0].past_cuf))
                except:
                    plant_value['past_cuf'] = ast.literal_eval(str(value[0].past_cuf))

                plant_value['past_grid_unavailability'] = ast.literal_eval(str(value[0].past_grid_unavailability))
                plant_value['past_equipment_unavailability'] = ast.literal_eval(str(value[0].past_equipment_unavailability))
                plant_value['past_dc_loss'] = ast.literal_eval(str(value[0].past_dc_loss))
                plant_value['past_dc_loss'] = make_losses_unit_same_as_generation(plant_value['past_generations'], plant_value['past_dc_loss'], 'dc_energy_loss')
                plant_value['past_conversion_loss'] = ast.literal_eval(str(value[0].past_conversion_loss))
                plant_value['past_conversion_loss'] = make_losses_unit_same_as_generation(plant_value['past_generations'],plant_value['past_conversion_loss'], 'conversion_loss')
                plant_value['past_ac_loss'] = ast.literal_eval(str(value[0].past_ac_loss))
                plant_value['past_ac_loss'] = make_losses_unit_same_as_generation(plant_value['past_generations'],plant_value['past_ac_loss'], 'ac_energy_loss')

                try:
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                        plant_value['residual'] = get_yesterday_residual_data(plant)
                except:
                    pass

                try:
                    # current inverter error detail
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                        total_inverter_error_numbers = 0
                        plant_current_inverter_error_details = []
                        current_inverter_error_detail = get_current_inverter_alarms(plant)
                        if len(current_inverter_error_detail)>0:
                            total_inverter_error_numbers += int(current_inverter_error_detail['affected_inverters_number'])
                            plant_current_inverter_error_details.append(current_inverter_error_detail)

                    # Current SMB anomaly detail
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                        total_low_anomaly_smb_numbers = 0
                        total_high_anomaly_smb_numbers = 0
                        plant_string_anomaly_details = []
                        current_string_anomaly_detail = get_current_string_anomaly_details_without_association(plant, date, 60)
                        if len(current_string_anomaly_detail)>0:
                            total_low_anomaly_smb_numbers += int(current_string_anomaly_detail['low_anomaly_affected_ajbs_number'])
                            total_high_anomaly_smb_numbers += int(current_string_anomaly_detail['high_anomaly_affected_ajbs_number'])
                            plant_string_anomaly_details.append(current_string_anomaly_detail)

                    # Inverter cleaning details
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                        total_inverter_cleaning_numbers = 0
                        plant_inverter_cleaning_details = []
                        current_cleaning_details = get_current_inverter_cleaning_details(plant)
                        if len(current_cleaning_details)>0:
                            total_inverter_cleaning_numbers += int(current_cleaning_details['inverters_required_cleaning_numbers'])
                            plant_inverter_cleaning_details.append(current_cleaning_details)

                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                        plant_value['total_inverter_error_numbers'] = total_inverter_error_numbers
                        plant_value['plant_current_inverter_error_details'] = plant_current_inverter_error_details

                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                        plant_value['plant_string_anomaly_details'] = plant_string_anomaly_details
                        plant_value['plant_inverter_cleaning_details'] = plant_inverter_cleaning_details
                        plant_value['total_inverter_cleaning_numbers'] = total_inverter_cleaning_numbers
                        plant_value['total_low_anomaly_smb_numbers'] = total_low_anomaly_smb_numbers
                        plant_value['total_high_anomaly_smb_numbers'] = total_high_anomaly_smb_numbers
                except Exception as exception:
                    print(str(exception))

            # Gateways Connection details
            gateways_disconnected_list = []
            gateways_powered_off_list = []
            plants_disconnected_list = []
            plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
            if len(plant_network_details)>0:
                plants_disconnected_list.append(str(plant.slug))
                try:
                    gateways_disconnected_list.extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                except:
                    pass
                try:
                    gateways_powered_off_list.extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                except:
                    pass
            plant_value['gateways_disconnected'] = len(gateways_disconnected_list)
            plant_value['gateways_powered_off'] = len(gateways_powered_off_list)
            plant_value['gateways_disconnected_list'] = gateways_disconnected_list
            plant_value['gateways_powered_off_list'] = gateways_powered_off_list

            try:
                queue = Queue.objects.filter(plant=plant)
                queue = queue[0]
                gateway_disconnected_ticket = Ticket.objects.filter(queue=queue,
                                                                    event_type='GATEWAY_DISCONNECTED',
                                                                    status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
                if len(gateway_disconnected_ticket)>0:
                    plant_value['gateways_disconnected_ticket'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(gateway_disconnected_ticket[len(gateway_disconnected_ticket)-1].id)+'/'

            except:
                pass

            try:
                queue = Queue.objects.filter(plant=plant)
                queue = queue[0]
                gateway_powered_off_ticket = Ticket.objects.filter(queue=queue,
                                                                   event_type='GATEWAY_POWER_OFF',
                                                                   status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
                if len(gateway_powered_off_ticket)>0:
                    plant_value['gateways_powered_off_ticket'] = 'https://dataglen.com/solar/plant/'+str(plant.slug) + '/ticket_view/'+str(gateway_powered_off_ticket[len(gateway_powered_off_ticket)-1].id)+'/'

            except:
                pass

            # Inverter Details
            try:
                inverter_details = {}
                inverter_numbers = len(plant.independent_inverter_units.all().filter(isActive=True))
                inverter_make = plant.independent_inverter_units.all()[0].manufacturer
                inverter_model = plant.independent_inverter_units.all()[0].model if plant.independent_inverter_units.all()[0].model else None
                inverter_capacity = plant.independent_inverter_units.all()[0].total_capacity if plant.independent_inverter_units.all()[0].total_capacity is not None else plant.independent_inverter_units.all()[0].actual_capacity
                capacities = {}
                for inverter in plant.independent_inverter_units.all():
                    try:
                        capacities[inverter.total_capacity] += 1
                    except KeyError:
                        capacities[inverter.total_capacity] = 1
                    except:
                        continue
                inverters_capacity_string = []
                for capacity, number in capacities.iteritems():
                    inverters_capacity_string.append(str(capacity) + " kW X " + str(number))
                inverter_details['numbers'] = inverter_numbers
                inverter_details['make'] = inverter_make
                inverter_details['model'] = inverter_model
                inverter_details['capacity'] = ",".join(inverters_capacity_string)
            except Exception as exception:
                logger.debug(str(exception))
                pass
            plant_value['inverter_details'] = inverter_details

            # Panel Details
            try:
                panel_details = {}
                panel_numbers = plant.metadata.plantmetasource.no_of_panels if plant.metadata.plantmetasource.no_of_panels else 0
                panel_make = plant.metadata.plantmetasource.panel_manufacturer
                panel_model = plant.metadata.plantmetasource.model_number
                panel_capacity = plant.metadata.plantmetasource.panel_capacity
                panel_details['numbers'] = panel_numbers
                panel_details['make'] = panel_make
                panel_details['model'] = panel_model
                panel_details['capacity'] = panel_capacity
            except Exception as exception:
                logger.debug(str(exception))
                pass
            plant_value['panel_details'] = panel_details

        if combined:
            live_data = get_plant_live_data_status(plant, date, True)
            plant_value.update(live_data)
            plant_value['power_irradiation'] = json.loads(get_power_irradiation(date.replace(hour=0, minute=0, second=0), date+timedelta(days=1), plant))
        return plant_value
    except Exception as exception:
        logger.debug(str(exception))
        return {}

def get_plant_status_data_offline_non_client_owner(plant, date, clientpage=False, live=False):
    try:
        plant_value = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            plant_value['plant_name'] = value[0].name
            plant_value['plant_slug'] = plant.slug
            logo = plant.dataglengroup.groupLogo if plant.dataglengroup and plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
            plant_value['plant_logo'] = logo
            plant_value['plant_capacity'] = value[0].capacity
            plant_value['plant_location'] = value[0].location
            plant_value['latitude'] = value[0].latitude
            plant_value['longitude'] = value[0].longitude
            plant_value['performance_ratio'] = value[0].pr
            plant_value['cuf'] = value[0].cuf
            plant_value['grid_unavailability'] = value[0].grid_unavailability
            plant_value['equipment_unavailability'] = value[0].equipment_unavailability
            plant_value['unacknowledged_tickets'] = value[0].unacknowledged_tickets
            plant_value['open_tickets'] = value[0].open_tickets
            plant_value['closed_tickets'] = value[0].closed_tickets
            plant_value['plant_generation_today'] = value[0].plant_generation_today
            plant_value['plant_total_energy'] = value[0].total_generation
            plant_value['plant_co2'] = value[0].co2_savings
            plant_value['dc_loss'] = value[0].dc_loss
            plant_value['conversion_loss'] = value[0].conversion_loss
            plant_value['ac_loss'] = value[0].ac_loss
            if len(plant.pvsyst_info.all())>0:
                current_month = date.month
                pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=date.year,
                                                                   timePeriodValue=current_month)
                if len(pv_sys_info_generation)==0:
                    pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=0,
                                                                   timePeriodValue=current_month)
                plant_capacity = plant.capacity
                if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
                    pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
                    plant_value['pvsyst_generation'] = fix_generation_units(pvsyst_generation)

                pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='PERFORMANCE_RATIO',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=date.year,
                                                           timePeriodValue=current_month)
                if len(pv_sys_info_pr)==0:
                    pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='PERFORMANCE_RATIO',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)

                if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
                    pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
                    plant_value['pvsyst_pr'] = pvsyst_pr

                pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='TILT_ANGLE',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=date.year,
                                                                   timePeriodValue=current_month)

                if len(pv_sys_info_tilt_angle) == 0:
                    pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='TILT_ANGLE',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=0,
                                                                   timePeriodValue=current_month)

                if len(pv_sys_info_tilt_angle)> 0 and pv_sys_info_tilt_angle[0].parameterValue is not None:
                    pvsyst_tilt_angle = float(pv_sys_info_tilt_angle[0].parameterValue)
                    plant_value['pvsyst_tilt_angle'] = pvsyst_tilt_angle

            try:
                if plant.gateway.all()[0].isMonitored:
                    if not plant.gateway.all()[0].isVirtual:
                        stats = get_user_data_monitoring_status(plant.gateway)
                        if stats is not None:
                            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                            errors_len = len(active_dead) + len(deactivated_alive)
                            unmonitored = len(unmonitored)
                        else:
                            errors_len = 0
                            unmonitored = 0
                        if unmonitored is not 0 :
                            network_up = 'unknown'
                        elif errors_len is not 0:
                            network_up = 'No'
                        else:
                            network_up = 'Yes'
                    else:
                        isNetworkUp = check_network_for_virtual_gateways(plant)
                        if isNetworkUp:
                            network_up = 'Yes'
                        else:
                            network_up = 'No'
                else:
                    network_up = 'unknown'
            except:
                pass

            plant_value['past_pr'] = ast.literal_eval(str(value[0].past_pr))
            try:
                past_monthly_energy_list = []
                past_energy_values = HistoricEnergyValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                         identifier=plant.slug).order_by('-ts').values_list('energy', 'ts')
                for past_energy_value in past_energy_values:
                    past_energy_values = {}
                    past_energy_values['timestamp'] = str(past_energy_value[1])
                    past_energy_values['energy'] = fix_generation_units(past_energy_value[0])
                    past_monthly_energy_list.append(past_energy_values)
            except Exception as exception:
                logger.debug(str(exception))
                pass
            past_monthly_energy_list = convert_values_to_common_unit(past_monthly_energy_list)
            plant_value['past_monthly_generation'] = past_monthly_energy_list

            # past specific yield
            try:
                past_specific_yield_list = []
                past_specific_yield_values = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                               identifier=plant.metadata.plantmetasource.sourceKey).order_by('-ts').values_list('specific_yield', 'ts').limit(7)
                for past_specific_yield_value in past_specific_yield_values:
                    past_specific_yield_value_dict = {}
                    past_specific_yield_value_dict['timestamp'] = str(past_specific_yield_value[1])
                    past_specific_yield_value_dict['specific_yield'] = round(float(past_specific_yield_value[0]),2)
                    past_specific_yield_list.append(past_specific_yield_value_dict)
                plant_value['past_specific_yield'] = past_specific_yield_list
            except Exception as exception:
                print(str(exception))
                pass
            # today's specific yield
            try:
                plant_value['specific_yield'] = round(float(past_specific_yield_values[len(past_specific_yield_values)-1][0]),2)
            except:
                plant_value['specific_yield'] = 0.0

            #TODO: Move this parameter(string_errors_smbs) to PlantCompleteValues table
            # SMB's having string high or low error

            string_error_smbs = set()
            ajbs = plant.ajb_units.all().filter(isActive=True)
            starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime_prediction = date.replace(hour=6, minute=0, second=0, microsecond=0)
            endtime = date
            endtime_today = date.replace(hour=23, minute=0, second=0, microsecond=0)
            for ajb in ajbs:
                string_errors = EventsByTime.objects.filter(identifier=str(ajb.sourceKey)+'_ajb',insertion_time__gte=starttime, insertion_time__lte=endtime)
                if len(string_errors)>0:
                    string_error_smbs.add(str(ajb.name))
            plant_value['string_errors_smbs'] = len(string_error_smbs)

            #Today's predicted energy value
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            plant_value['today_predicted_energy_value_till_time'] = fix_generation_units(predicted_energy_value)
            plant_value['today_predicted_energy_value_till_time_without_unit'] = predicted_energy_value

            duration_hours = (endtime - starttime_prediction).total_seconds()/3600
            final_duration_hours = min(duration_hours, 12)

            #Total today's predicted energy value
            total_predicted_energy_value = get_energy_prediction_data(starttime, endtime_today, plant)
            plant_value['total_today_predicted_energy_value'] = fix_generation_units(total_predicted_energy_value)
            plant_value['total_today_predicted_energy_value_without_unit'] = total_predicted_energy_value

            if network_up == 'Yes':
                try:
                    plant_value['prediction_deviation'] = abs(((float(predicted_energy_value)-float(value[0].plant_generation_today))/(float(plant_value['plant_capacity'])*final_duration_hours))*100)
                except:
                    plant_value['prediction_deviation'] = 0.0
                plant_value['prediction_deviation'] = str("{0:.2f}".format(float(plant_value['prediction_deviation']))) + " %"
            else:
                plant_value['prediction_deviation'] = 'NA'

            if live:

                # Adding maximum power
                try:
                    power_df = get_plant_power(starttime, endtime, plant, True, False, False, True)
                    if not power_df.empty:
                        plant_value['max_power'] = power_df['sum'].max()
                    else:
                        plant_value['max_power'] = 0.0
                except:
                    plant_value['max_power'] = 0.0

                plant_value['current_power'] = value[0].active_power
                plant_value['irradiation'] = "{0:.2f}".format(value[0].irradiation) if value[0].irradiation else 0.0
                plant_value['connected_inverters'] = value[0].connected_inverters
                #plant_value['disconnected_inverters'] = value[0].disconnected_inverters
                plant_value['invalid_inverters'] = value[0].invalid_inverters
                plant_value['connected_smbs'] = value[0].connected_smbs
                #plant_value['disconnected_smbs'] = value[0].disconnected_smbs
                plant_value['invalid_smbs'] = value[0].invalid_smbs
                plant_value['network_up'] = network_up
                plant_value['status'] = value[0].status
                plant_value['updated_at'] = value[0].updated_at
                plant_value['module_temperature'] = value[0].module_temperature
                plant_value['ambient_temperature'] = value[0].ambient_temperature
                plant_value['windspeed'] = value[0].windspeed
                plant_value['disconnected_inverters'] = 0
                plant_value['disconnected_smbs'] = 0

                # adding below section of code to show disconnected devices, only if the network is up.
                if network_up == 'Yes':
                    # print(plant.slug)
                    # plant_value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    #                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    #                                                  identifier=plant.metadata.plantmetasource.sourceKey,
                    #                                                  ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

                    plant_value['disconnected_inverters'] += int(value[0].disconnected_inverters)
                    plant_value['disconnected_smbs'] += int(value[0].disconnected_smbs)

            if clientpage:
                plant_value['past_generations'] = ast.literal_eval(str(value[0].past_generations))
                #plant_value['past_pr'] = ast.literal_eval(str(value[0].past_pr))
                plant_value['past_cuf'] = ast.literal_eval(str(value[0].past_cuf))
                plant_value['past_grid_unavailability'] = ast.literal_eval(str(value[0].past_grid_unavailability))
                plant_value['past_equipment_unavailability'] = ast.literal_eval(str(value[0].past_equipment_unavailability))
                plant_value['past_dc_loss'] = ast.literal_eval(str(value[0].past_dc_loss))
                plant_value['past_conversion_loss'] = ast.literal_eval(str(value[0].past_conversion_loss))
                plant_value['past_ac_loss'] = ast.literal_eval(str(value[0].past_ac_loss))
        return plant_value
    except Exception as exception:
        logger.debug(str(exception))
        return {}


def get_plant_status_data_offline_non_client_owner_for_mobiles(plant, date, clientpage=False, live=False):
    try:
        plant_value = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            plant_value['plant_capacity'] = value[0].capacity
            plant_value['plant_generation_today'] = value[0].plant_generation_today
            plant_value['plant_total_energy'] = value[0].total_generation
            plant_value['plant_co2'] = value[0].co2_savings
            try:
                if plant.gateway.all()[0].isMonitored:
                    if not plant.gateway.all()[0].isVirtual:
                        stats = get_user_data_monitoring_status(plant.gateway)
                        if stats is not None:
                            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                            errors_len = len(active_dead) + len(deactivated_alive)
                            unmonitored = len(unmonitored)
                        else:
                            errors_len = 0
                            unmonitored = 0
                        if unmonitored is not 0 :
                            network_up = 'unknown'
                        elif errors_len is not 0:
                            network_up = 'No'
                        else:
                            network_up = 'Yes'
                    else:
                        isNetworkUp = check_network_for_virtual_gateways(plant)
                        if isNetworkUp:
                            network_up = 'Yes'
                        else:
                            network_up = 'No'
                else:
                    network_up = 'unknown'
            except:
                pass
            plant_value['network_up'] = network_up

            # current month energy
            try:
                past_energy_values = HistoricEnergyValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                         identifier=plant.slug).limit(1)
                current_month_generation = float(past_energy_values[0].energy)
            except Exception as exception:
                logger.debug(str(exception))
                current_month_generation = 0.0
                pass
            plant_value['energy_current_month'] = current_month_generation

            starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime_prediction = date.replace(hour=6, minute=0, second=0, microsecond=0)
            endtime = date
            endtime_today = date.replace(hour=23, minute=0, second=0, microsecond=0)

            #Today's predicted energy value
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            plant_value['today_predicted_energy_value_till_time'] = fix_generation_units(predicted_energy_value)
            plant_value['today_predicted_energy_value_till_time_without_unit'] = predicted_energy_value

            duration_hours = (endtime - starttime_prediction).total_seconds()/3600
            final_duration_hours = min(duration_hours, 12)

            #Total today's predicted energy value
            total_predicted_energy_value = get_energy_prediction_data(starttime, endtime_today, plant)
            plant_value['total_today_predicted_energy_value'] = fix_generation_units(total_predicted_energy_value)
            plant_value['total_today_predicted_energy_value_without_unit'] = total_predicted_energy_value

            if network_up == 'Yes':
                try:
                    plant_value['prediction_deviation'] = abs(((float(predicted_energy_value)-float(value[0].plant_generation_today))/(float(plant_value['plant_capacity'])*final_duration_hours))*100)
                except:
                    plant_value['prediction_deviation'] = 0.0
                plant_value['prediction_deviation'] = str("{0:.2f}".format(float(plant_value['prediction_deviation']))) + " %"
            else:
                plant_value['prediction_deviation'] = 'NA'

            if live:
                plant_value['current_power'] = value[0].active_power
                plant_value['updated_at'] = value[0].updated_at

        return plant_value
    except Exception as exception:
        logger.debug(str(exception))
        return {}

def get_final_plant_status_for_non_client_owner_users_for_mobiles(solar_plants, user, date, clientpage=False, live=False):
    try:
        final_values = {}
        final_values['total_energy'] = 0.0
        final_values['energy_today'] = 0.0
        final_values['total_capacity'] = 0.0
        final_values['total_co2'] = 0.0
        final_values['total_active_power'] = 0.0

        final_values['network_up_energy_today'] = 0.0
        final_values['network_up_capacity'] = 0.0
        final_values['total_connected_plants'] = 0
        final_values['total_disconnected_plants'] = 0
        final_values['total_unmonitored_plants'] = 0
        final_values['total_capacity_past_month'] = 0.0
        final_values['total_today_predicted_energy_value'] = 0.0
        final_values['today_predicted_energy_value_till_time'] = 0.0
        final_values['energy_current_month'] = 0.0

        predicted_energy_till_time = 0.0
        total_energy_for_network_up_plants = 0.0
        total_capacity_for_network_up_plants = 0.0

        for plant in solar_plants:
            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
            final_values['client_name'] = plant.groupClient.name if plant.groupClient else plant.name
            final_values['client_slug'] = plant.groupClient.slug if plant.groupClient else plant.slug
            # final_values['client_logo'] = plant.groupClient.clientLogo if plant.groupClient else ""
            try:
                final_values['client_logo'] = str(plant.groupClient.dataglenclient.clientMobileLogo) if plant.groupClient.dataglenclient and plant.groupClient.dataglenclient.clientMobileLogo else ""
            except:
               final_values['client_logo'] = ""
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                logger.debug(str(exc))
                current_time = timezone.now()

            try:
                if plant.commissioned_date and ((current_time.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
                    final_values['total_capacity_past_month'] += float(plant.capacity)
            except Exception as exception:
                print (str(exception))

            try:
                plant_value = get_plant_status_data_offline_non_client_owner_for_mobiles(plant, current_time, True, True)
                starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
                endtime = date
                if len(plant_value)>0:
                    final_values['total_capacity'] += float(value[0].capacity)
                    final_values['total_energy'] += float(value[0].total_generation)
                    final_values['energy_today'] += float(value[0].plant_generation_today)
                    final_values['total_co2'] += float(value[0].co2_savings)

                    try:
                        if plant.gateway.all()[0].isMonitored:
                            if not plant.gateway.all()[0].isVirtual:
                                stats = get_user_data_monitoring_status(plant.gateway)
                                if stats is not None:
                                    active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                                    errors_len = len(active_dead) + len(deactivated_alive)
                                    unmonitored = len(unmonitored)
                                else:
                                    errors_len = 0
                                    unmonitored = 0
                                if unmonitored is not 0 :
                                    network_up = 'unknown'
                                elif errors_len is not 0:
                                    network_up = 'No'
                                else:
                                    network_up = 'Yes'
                            else:
                                isNetworkUp = check_network_for_virtual_gateways(plant)
                                if isNetworkUp:
                                    network_up = 'Yes'
                                else:
                                    network_up = 'No'
                        else:
                            network_up = 'unknown'
                    except:
                        pass

                    final_values['energy_current_month'] += plant_value['energy_current_month']

                    if str(network_up) == 'Yes':
                        final_values['total_connected_plants'] +=1
                    if str(network_up) == 'No':
                        final_values['total_disconnected_plants'] +=1
                    if str(network_up) == 'unknown':
                        final_values['total_unmonitored_plants'] +=1

                    final_values['total_active_power'] += float(value[0].active_power)
                    predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)

                    if network_up == 'Yes':
                        predicted_energy_till_time += float(predicted_energy_value)
                        try:
                            value_plant = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                             identifier=plant.metadata.plantmetasource.sourceKey,
                                                                             ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

                            if len(value_plant)>0:
                                total_energy_for_network_up_plants += float(value_plant[0].plant_generation_today)
                                total_capacity_for_network_up_plants += float(value_plant[0].capacity)
                        except Exception as exception:
                            logger.debug(str(exception))

                    final_values['updated_at'] = plant_value['updated_at']
            except Exception as exception:
                logger.debug(str(exception))

        starttime_prediction = date.replace(hour=6, minute=0, second=0, microsecond=0)
        endtime = date
        duration_hours = (endtime - starttime_prediction).total_seconds()/3600
        final_duration_hours = min(duration_hours, 12)
        try:
            final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time)-float(total_energy_for_network_up_plants))/(float(total_capacity_for_network_up_plants)*final_duration_hours))*100)
        except Exception as exception:
            logger.debug(str(exception))
            final_values['prediction_deviation'] = 0.0
        if predicted_energy_till_time > 0.0:
            final_values['prediction_deviation'] = str("{0:.2f}".format(float(final_values['prediction_deviation']))) + " %"
        else:
            final_values['prediction_deviation'] = "NA"

        final_values['total_diesel'] = "{0:.1f} L".format(float(final_values['energy_today'])/4.0)
        final_values['total_energy'] = fix_generation_units(float(final_values['total_energy']))
        final_values['energy_today'] = fix_generation_units(float(final_values['energy_today']))
        final_values['total_capacity'] = fix_capacity_units(float(final_values['total_capacity']))
        final_values['total_capacity_past_month'] = fix_capacity_units(float(final_values['total_capacity_past_month']))
        final_values['total_co2'] = fix_co2_savings(float(final_values['total_co2']))
        final_values['energy_current_month'] = fix_generation_units(float(final_values['energy_current_month']))

        final_values['total_active_power'] = "{0:.2f}".format(float(final_values['total_active_power'])) if final_values['total_active_power'] else 0.0
        final_values['know_more'] = False
        return final_values
    except Exception as exception:
        print(str(exception))
        return {}


def get_final_plant_status_for_non_client_owner_users(solar_plants, user, date, clientpage=False, live=False):
    try:
        plant = solar_plants[0]
        organization_user = user.organizations_organizationuser.all()[0]
        plant_list = []
        final_values = {}
        pr_count = 0
        cuf_count = 0
        irradiation_count = 0
        final_values['total_energy'] = 0.0
        final_values['energy_today'] = 0.0
        final_values['total_capacity'] = 0.0
        final_values['total_co2'] = 0.0
        final_values['grid_unavailability'] = 0.0
        final_values['equipment_unavailability'] = 0.0
        final_values['total_active_power'] = 0.0
        final_values['total_irradiation'] = 0.0
        plants_disconnected_list = []
        gateways_disconnected_list = []
        gateways_powered_off_list = []
        try:
            role = user.role.role
        except:
            role = "CEO"

        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
            final_values['total_connected_inverters'] = 0
            final_values['total_disconnected_inverters'] = 0
            final_values['total_invalid_inverters'] = 0
            final_values['total_connected_smbs'] = 0
            final_values['total_disconnected_smbs'] = 0
            final_values['total_invalid_smbs'] = 0
            final_values['total_unacknowledged_tickets'] = 0
            final_values['total_open_tickets'] = 0
            final_values['total_closed_tickets'] = 0
            count_unmonitored = 0
            count_connected = 0
            count_disconnected = 0
            count_invalid = 0
            client_current_inverter_error_details = []
            total_inverter_error_numbers = 0

        final_values['total_dc_loss'] = 0.0
        final_values['total_conversion_loss'] = 0.0
        final_values['total_ac_loss'] = 0.0
        final_values['client_past_generations'] = []
        plant = solar_plants[0]
        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
            final_values['total_pr'] = 0.0
            final_values['total_cuf'] = 0.0
            final_values['client_past_pr'] = []
            final_values['client_past_cuf'] = []
            final_values['total_specific_yield'] = 0.0
            count_specific_yield = 0
            final_values['client_past_specific_yield'] = []

        final_values['client_past_grid_unavailability'] = []
        final_values['client_past_equipment_unavailability'] = []
        final_values['client_past_dc_loss'] = []
        final_values['client_past_conversion_loss'] = []
        final_values['client_past_ac_loss'] = []

        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            final_values['string_errors_smbs'] = 0
            final_values['today_predicted_energy_value_till_time'] = 0.0
            final_values['total_today_predicted_energy_value'] = 0.0
            client_current_string_anomaly_details = []
            total_low_anomaly_smb_numbers = 0
            total_high_anomaly_smb_numbers = 0
            client_current_inverter_cleaning_details = []
            total_inverter_cleaning_numbers = 0


        final_values['network_up_energy_today'] = 0.0
        final_values['network_up_capacity'] = 0.0
        final_values['total_connected_plants'] = 0
        final_values['total_disconnected_plants'] = 0
        final_values['total_unmonitored_plants'] = 0
        final_values['total_capacity_past_month'] = 0.0

        logger.debug("before loop")
        logger.debug(timezone.now())
        for plant in solar_plants:
            final_values['client_name'] = plant.groupClient.name if plant.groupClient else plant.name
            final_values['client_slug'] = plant.groupClient.slug if plant.groupClient else plant.slug
            if str(role).upper().startswith("CLIENT"):
                try:
                    final_values['client_logo'] = plant.dataglengroup.groupLogo if plant.dataglengroup and plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
                except:
                    final_values['client_logo'] = ""
            else:
                try:
                    final_values['client_logo'] = plant.groupClient.clientLogo if plant.groupClient else ""
                except:
                    final_values['client_logo'] = ""
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                logger.debug(str(exc))
                current_time = timezone.now()

            try:
                if plant.commissioned_date and ((current_time.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
                    final_values['total_capacity_past_month'] += float(plant.capacity)
            except Exception as exception:
                print (str(exception))

            try:
                plant_value = get_plant_status_data_offline_non_client_owner(plant, current_time, True, True)
                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                    stats = get_user_data_monitoring_status(plant.independent_inverter_units)
                    if stats is not None:
                        active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                        stable_len = len(active_alive_valid) + len(deactivated_dead)
                        warnings_len = len(active_alive_invalid)
                        errors_len = len(active_dead) + len(deactivated_alive)
                        unmonitored = len(unmonitored)
                    else:
                        stable_len = 0
                        warnings_len = 0
                        errors_len = 0
                        unmonitored = 0
                    count_connected += int(stable_len)
                    count_disconnected += int(errors_len)
                    count_invalid += int(warnings_len)
                    count_unmonitored += int(unmonitored)

                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                    # current inverter error detail
                    current_inverter_error_detail = get_current_inverter_alarms(plant)
                    client_current_inverter_error_details.append(current_inverter_error_detail)
                    if len(current_inverter_error_detail)>0:
                        total_inverter_error_numbers += int(current_inverter_error_detail['affected_inverters_number'])

                if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                    # Current SMB anomaly detail
                    current_string_anomaly_detail = get_current_string_anomaly_details_without_association(plant, date, 60)
                    client_current_string_anomaly_details.append(current_string_anomaly_detail)
                    if len(current_string_anomaly_detail)>0:
                        total_low_anomaly_smb_numbers += int(current_string_anomaly_detail['low_anomaly_affected_ajbs_number'])
                        total_high_anomaly_smb_numbers += int(current_string_anomaly_detail['high_anomaly_affected_ajbs_number'])

                    # Inverter cleaning details
                    current_cleaning_details = get_current_inverter_cleaning_details(plant)
                    client_current_inverter_cleaning_details.append(current_cleaning_details)
                    if len(current_cleaning_details)>0:
                        total_inverter_cleaning_numbers += int(current_cleaning_details['inverters_required_cleaning_numbers'])

                plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
                if len(plant_network_details)>0:
                    plants_disconnected_list.append(str(plant.slug))
                    try:
                        gateways_disconnected_list.extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                    except:
                        pass
                    try:
                        gateways_powered_off_list.extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                    except:
                        pass

                if len(plant_value)>0:
                    final_values['total_capacity'] += float(plant_value['plant_capacity'])
                    final_values['total_energy'] += float(plant_value['plant_total_energy'])
                    final_values['energy_today'] += float(plant_value['plant_generation_today'])
                    final_values['total_co2'] += float(plant_value['plant_co2'])
                    final_values['grid_unavailability'] += float(plant_value['grid_unavailability'])
                    final_values['equipment_unavailability'] += float(plant_value['equipment_unavailability'])
                    final_values['total_dc_loss'] += float(plant_value['dc_loss'])
                    final_values['total_conversion_loss'] += float(plant_value['conversion_loss'])
                    final_values['total_ac_loss'] += float(plant_value['ac_loss'])

                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                        final_values['string_errors_smbs'] += int(plant_value['string_errors_smbs'])

                    if str(plant_value['network_up']) == 'Yes':
                        final_values['total_connected_plants'] +=1
                    if str(plant_value['network_up']) == 'No':
                        final_values['total_disconnected_plants'] +=1
                    if str(plant_value['network_up']) == 'unknown':
                        final_values['total_unmonitored_plants'] +=1
                    try:
                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                            if 0.0 < float(plant_value['performance_ratio']) <= 1.0:
                                final_values['total_pr'] += float(plant_value['performance_ratio'])
                                pr_count+=1
                            if 0.0 < float(plant_value['cuf']) <= 1.0:
                                final_values['total_cuf'] += float(plant_value['cuf'])
                                cuf_count+=1
                    except:
                        pass

                    final_values['total_active_power'] += float(plant_value['current_power'])
                    if float(plant_value['irradiation']) > 0.0:
                        final_values['total_irradiation'] += float(plant_value['irradiation'])
                        irradiation_count +=1
                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                        final_values['total_connected_inverters'] += int(plant_value['connected_inverters'])
                        final_values['total_disconnected_inverters'] += int(plant_value['disconnected_inverters'])
                        final_values['total_invalid_inverters'] += int(plant_value['invalid_inverters'])
                        final_values['total_connected_smbs'] += int(plant_value['connected_smbs'])
                        final_values['total_disconnected_smbs'] += int(plant_value['disconnected_smbs'])
                        final_values['total_invalid_smbs'] += int(plant_value['invalid_smbs'])

                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                        if str(plant_value['network_up']) == 'Yes':
                            final_values['today_predicted_energy_value_till_time'] += float(plant_value['today_predicted_energy_value_till_time_without_unit'])
                            final_values['network_up_energy_today'] += float(plant_value['plant_generation_today'])
                            final_values['network_up_capacity'] += float(plant_value['plant_capacity'])
                        final_values['total_today_predicted_energy_value'] += float(plant_value['total_today_predicted_energy_value_without_unit'])

                    if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                        final_values['total_unacknowledged_tickets'] = final_values['total_unacknowledged_tickets'] + int(plant_value['unacknowledged_tickets'])
                        final_values['total_open_tickets'] = final_values['total_open_tickets'] + int(plant_value['open_tickets'])
                        final_values['total_closed_tickets'] = final_values['total_closed_tickets'] + int(plant_value['closed_tickets'])
                    final_values['updated_at'] = plant_value['updated_at']

                    try:
                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                            try:
                                if len(final_values['client_past_specific_yield']) == 0 :
                                    final_values['client_past_specific_yield'] = copy.deepcopy(plant_value['past_specific_yield'])
                                else:
                                    for i in range(len(final_values['client_past_specific_yield'])):
                                        try:
                                            if float(final_values['client_past_specific_yield'][i]['specific_yield']) == 0.0:
                                                final_values['client_past_specific_yield'][i]['specific_yield'] = plant_value['past_specific_yield'][i]['specific_yield']
                                            elif plant_value['past_specific_yield'][i]['specific_yield'] > 0.0:
                                                final_values['client_past_specific_yield'][i]['specific_yield'] = (float(final_values['client_past_specific_yield'][i]['specific_yield']) + plant_value['past_specific_yield'][i]['specific_yield'])/2
                                            else:
                                                pass
                                        except Exception as exception:
                                            print(str(exception))
                                            continue
                            except Exception as exception:
                                print(str(exception))
                    except:
                        pass

                    # today's specific yield
                    try:
                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                            try:
                                if float(plant_value['specific_yield']) > 0.0:
                                    final_values['total_specific_yield'] += float(plant_value['specific_yield'])
                                    count_specific_yield += 1
                            except Exception as exception:
                                print(str(exception))
                                pass
                    except:
                        pass

                    if clientpage:
                        if len(final_values['client_past_generations']) == 0 :
                            final_values['client_past_generations'] = copy.deepcopy(plant_value['past_generations'])
                        else:
                            for i in range(len(final_values['client_past_generations'])):
                                try:
                                    final_values['client_past_generations'][i]['energy'] = float(str(final_values['client_past_generations'][i]['energy']).split(' ')[0])*float(unit_conversion[str(final_values['client_past_generations'][i]['energy']).split(' ')[1]]) + \
                                        float(str(plant_value['past_generations'][i]['energy']).split(' ')[0])*float(unit_conversion[str(plant_value['past_generations'][i]['energy']).split(' ')[1]])
                                except Exception as exception:
                                    try:
                                        final_values['client_past_generations'][i]['energy'] = float(str(final_values['client_past_generations'][i]['energy']).split(' ')[0]) + \
                                        float(str(plant_value['past_generations'][i]['energy']).split(' ')[0])*float(unit_conversion[str(plant_value['past_generations'][i]['energy']).split(' ')[1]])
                                    except:
                                        pass
                                    continue
                        try:
                            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                                if len(final_values['client_past_pr']) == 0 :
                                    final_values['client_past_pr'] = copy.deepcopy(plant_value['past_pr'])
                                else:
                                    for i in range(len(final_values['client_past_pr'])):
                                        try:
                                            if float(final_values['client_past_pr'][i]['pr']) == 0.0:
                                                final_values['client_past_pr'][i]['pr'] = plant_value['past_pr'][i]['pr']
                                            elif 0.0 < float(plant_value['past_pr'][i]['pr']) < 1.0:
                                                final_values['client_past_pr'][i]['pr'] = (float(str(final_values['client_past_pr'][i]['pr']).split(' ')[0]) + float(str(plant_value['client_past_pr'][i]['pr'])))/2
                                            else:
                                                pass
                                        except:
                                            continue
                        except:
                            pass

                        try:
                            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                                if len(final_values['client_past_cuf']) == 0 :
                                    final_values['client_past_cuf'] = copy.deepcopy(plant_value['past_cuf'])
                                else:
                                    for i in range(len(final_values['client_past_cuf'])):
                                        try:
                                            if float(final_values['client_past_cuf'][i]['cuf']) == 0.0:
                                                final_values['client_past_cuf'][i]['cuf'] = plant_value['past_cuf'][i]['cuf']
                                            elif 0.0 < float(plant_value['past_cuf'][i]['cuf']) < 1.0:
                                                final_values['client_past_cuf'][i]['cuf'] = (float(str(final_values['client_past_cuf'][i]['cuf']).split(' ')[0]) + float(str(plant_value['client_past_cuf'][i]['cuf'])))/2
                                            else:
                                                pass
                                        except:
                                            continue
                        except:
                            pass

                        if len(final_values['client_past_grid_unavailability']) == 0 :
                            final_values['client_past_grid_unavailability'] = copy.deepcopy(plant_value['past_grid_unavailability'])
                        else:
                            for i in range(len(final_values['client_past_grid_unavailability'])):
                                try:
                                    final_values['client_past_grid_unavailability'][i]['unavailability'] = (float(str(final_values['client_past_grid_unavailability'][i]['unavailability']).split(' ')[0]) + float(str(plant_value['past_grid_unavailability'][i]['unavailability']).split(' ')[0]))/2
                                except Exception as exc:
                                    logger.debug("grid unavailability error : "+str(exc))
                                    continue

                        if len(final_values['client_past_equipment_unavailability']) == 0 :
                            final_values['client_past_equipment_unavailability'] = copy.deepcopy(plant_value['past_equipment_unavailability'])
                        else:
                            for i in range(len(final_values['client_past_equipment_unavailability'])):
                                try:
                                    final_values['client_past_equipment_unavailability'][i]['unavailability'] = (float(str(final_values['client_past_equipment_unavailability'][i]['unavailability']).split(' ')[0]) + float(str(plant_value['past_equipment_unavailability'][i]['unavailability']).split(' ')[0]))/2
                                except Exception as exc:
                                    logger.debug("equipment unavailability error : " + str(exc))
                                    continue

                        if len(final_values['client_past_dc_loss']) == 0 :
                            final_values['client_past_dc_loss'] = copy.deepcopy(plant_value['past_dc_loss'])
                        else:
                            for i in range(len(final_values['client_past_dc_loss'])):
                                try:
                                    final_values['client_past_dc_loss'][i]['dc_energy_loss'] = float(str(final_values['client_past_dc_loss'][i]['dc_energy_loss']).split(' ')[0])*float(unit_conversion[str(final_values['client_past_dc_loss'][i]['dc_energy_loss']).split(' ')[1]]) + \
                                        float(str(plant_value['past_dc_loss'][i]['dc_energy_loss']).split(' ')[0])*float(unit_conversion[str(plant_value['past_dc_loss'][i]['dc_energy_loss']).split(' ')[1]])
                                except Exception as exc:
                                    logger.debug(" DC loss error : " + str(exc))
                                    continue

                        if len(final_values['client_past_conversion_loss']) == 0 :
                            final_values['client_past_conversion_loss'] = copy.deepcopy(plant_value['past_conversion_loss'])
                        else:
                            for i in range(len(final_values['client_past_conversion_loss'])):
                                try:
                                    final_values['client_past_conversion_loss'][i]['conversion_loss'] = float(str(final_values['client_past_conversion_loss'][i]['conversion_loss']).split(' ')[0])*float(unit_conversion[str(final_values['client_past_conversion_loss'][i]['conversion_loss']).split(' ')[1]]) + \
                                        float(str(plant_value['past_conversion_loss'][i]['conversion_loss']).split(' ')[0])*float(unit_conversion[str(plant_value['past_conversion_loss'][i]['conversion_loss']).split(' ')[1]])
                                except Exception as exc:
                                    logger.debug("conversion loss error : "+str(exc))
                                    continue

                        if len(final_values['client_past_ac_loss']) == 0 :
                            final_values['client_past_ac_loss'] = copy.deepcopy(plant_value['past_ac_loss'])
                        else:
                            for i in range(len(final_values['client_past_ac_loss'])):
                                try:
                                    final_values['client_past_ac_loss'][i]['ac_energy_loss'] = float(str(final_values['client_past_ac_loss'][i]['ac_energy_loss']).split(' ')[0])*float(unit_conversion[str(final_values['client_past_ac_loss'][i]['ac_energy_loss']).split(' ')[1]]) + \
                                        float(str(plant_value['past_ac_loss'][i]['ac_energy_loss']).split(' ')[0])*float(unit_conversion[str(plant_value['past_ac_loss'][i]['ac_energy_loss']).split(' ')[1]])
                                except Exception as exc:
                                    logger.debug("AC loss exception : " + str(exc))
                                    continue

                        del(plant_value['past_generations'])
                        #del(plant_value['past_pr'])
                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                            pass
                        else:
                            del(plant_value['performance_ratio'])
                            del(plant_value['cuf'])
                            del(plant_value['past_pr'])
                            del(plant_value['past_specific_yield'])
                            del(plant_value['specific_yield'])

                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                            pass
                        else:
                            del(plant_value['unacknowledged_tickets'])
                            del(plant_value['open_tickets'])
                            del(plant_value['closed_tickets'])
                            del(plant_value['connected_inverters'])
                            del(plant_value['disconnected_inverters'])
                            del(plant_value['invalid_inverters'])
                            del(plant_value['connected_smbs'])
                            del(plant_value['disconnected_smbs'])
                            del(plant_value['invalid_smbs'])
                        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                            pass
                        else:
                            del(plant_value['prediction_deviation'])
                            del(plant_value['today_predicted_energy_value_till_time'])
                            del(plant_value['total_today_predicted_energy_value'])
                            del(plant_value['string_errors_smbs'])

                        del(plant_value['past_cuf'])
                        del(plant_value['past_grid_unavailability'])
                        del(plant_value['past_equipment_unavailability'])
                        del(plant_value['past_dc_loss'])
                        del(plant_value['past_conversion_loss'])
                        del(plant_value['past_ac_loss'])
                        try:
                            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                                plant_value['cuf'] = "{0:.2f}".format(float(plant_value['cuf'])) if plant_value['cuf'] else 0.0
                                plant_value['performance_ratio'] = "{0:.2f}".format(float(plant_value['performance_ratio'])) if plant_value['performance_ratio'] else 0.0
                        except:
                            pass
                        plant_value['current_power'] = "{0:.2f}".format(float(plant_value['current_power'])) if plant_value['current_power'] else 0.0
                        plant_value['plant_capacity'] = fix_capacity_units(float(plant_value['plant_capacity']))
                        plant_value['plant_generation_today'] = fix_generation_units(float(plant_value['plant_generation_today']))
                        plant_value['grid_unavailability'] = str("{0:.2f}".format(plant_value['grid_unavailability'])) + " %" if plant_value['grid_unavailability'] else "0 %"
                        plant_value['equipment_unavailability'] = str("{0:.2f}".format(plant_value['equipment_unavailability'])) + " %" if plant_value['equipment_unavailability'] else "0 %"
                        plant_value['plant_total_energy'] = fix_generation_units(float(plant_value['plant_total_energy']))
                        plant_value['plant_co2'] = fix_co2_savings(float(plant_value['plant_co2']))
                        plant_value['dc_loss'] = fix_generation_units(float(plant_value['dc_loss']))
                        plant_value['conversion_loss'] = fix_generation_units(float(plant_value['conversion_loss']))
                        plant_value['ac_loss'] = fix_generation_units(float(plant_value['ac_loss']))
                if len(plant_value)>0:
                    plant_list.append(plant_value)
            except Exception as exception:
                logger.debug(str(exception))

        logger.debug("after loop")
        logger.debug(timezone.now())

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                try:
                    final_values['total_specific_yield'] = round(float(final_values['total_specific_yield']/count_specific_yield),2)
                except:
                    final_values['total_specific_yield'] = 0.0
        except:
            pass

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                for i in range(len(final_values['client_past_specific_yield'])):
                    try:
                        final_values['client_past_specific_yield'][i]['specific_yield'] = round(final_values['client_past_specific_yield'][i]['specific_yield'],2)
                    except Exception as exception:
                        print(str(exception))
        except:
            pass

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                final_values['client_past_specific_yield'][i]['specific_yield'] = final_values['total_specific_yield']
        except:
            pass

        starttime_prediction = date.replace(hour=6, minute=0, second=0, microsecond=0)
        endtime = date
        duration_hours = (endtime - starttime_prediction).total_seconds()/3600
        final_duration_hours = min(duration_hours, 12)

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
                if final_values['today_predicted_energy_value_till_time'] > 0.0:
                    try:
                        final_values['prediction_deviation'] =abs(((float(final_values['today_predicted_energy_value_till_time'])-float(final_values['network_up_energy_today']))/(float(final_values['network_up_capacity'])*final_duration_hours))*100)
                    except:
                        final_values['prediction_deviation'] = 0.0
                    final_values['prediction_deviation'] = str("{0:.2f}".format(float(final_values['prediction_deviation']))) + " %"
                else:
                    final_values['prediction_deviation'] = "NA"
        except:
            pass

        final_values['total_energy'] = fix_generation_units(float(final_values['total_energy']))
        final_values['total_capacity'] = fix_capacity_units(float(final_values['total_capacity']))
        final_values['total_capacity_past_month'] = fix_capacity_units(float(final_values['total_capacity_past_month']))
        final_values['client_dc_loss'] = fix_generation_units(float(final_values['total_dc_loss']))
        final_values['client_conversion_loss'] = fix_generation_units(float(final_values['total_conversion_loss']))
        final_values['client_ac_loss'] = fix_generation_units(float(final_values['total_ac_loss']))
        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            final_values['today_predicted_energy_value_till_time'] = fix_generation_units((float(final_values['today_predicted_energy_value_till_time'])))
            final_values['total_today_predicted_energy_value'] = fix_generation_units((float(final_values['total_today_predicted_energy_value'])))
        final_values['total_co2'] = fix_co2_savings(float(final_values['total_co2']))
        final_values['grid_unavailability'] = str("{0:.2f}".format(float(final_values['grid_unavailability'])/len(solar_plants))) + " %" if final_values['grid_unavailability'] else "0 %"
        final_values['equipment_unavailability'] = str("{0:.2f}".format(float(final_values['equipment_unavailability'])/len(solar_plants))) + " %" if final_values['equipment_unavailability'] else "0 %"
        final_values['total_irradiation'] = "{0:.2f}".format(float(final_values['total_irradiation'])/irradiation_count) if irradiation_count is not 0 else 0.0

        final_values['gateways_disconnected'] = len(gateways_disconnected_list)
        final_values['gateways_powered_off'] = len(gateways_powered_off_list)
        final_values['gateways_disconnected_list'] = gateways_disconnected_list
        final_values['gateways_powered_off_list'] = gateways_powered_off_list

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                final_values['total_pr'] = "{0:.2f}".format(float(final_values['total_pr'])/pr_count) if pr_count is not 0 else 0.0
                final_values['total_cuf'] = "{0:.2f}".format(float(final_values['total_cuf'])/cuf_count) if cuf_count is not 0 else 0.0
        except:
            pass
        final_values['total_active_power'] = "{0:.2f}".format(float(final_values['total_active_power'])) if final_values['total_active_power'] else 0.0
        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
                if count_unmonitored is not 0:
                    status = 'unmonitored'
                elif count_disconnected is not 0:
                    status = 'disconnected'
                else:
                    status = 'connected'
                final_values['status'] = status
        except:
            pass

        if len(final_values['client_past_generations'])>0:
            final_values['client_past_generations'][len(final_values['client_past_generations'])-1]['energy'] = final_values['energy_today']
        final_values['energy_today'] = fix_generation_units((float(final_values['energy_today'])))

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                if len(final_values['client_past_pr'])>0:
                    final_values['client_past_pr'][len(final_values['client_past_pr'])-1]['pr'] = final_values['total_pr']
        except:
            pass

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                if len(final_values['client_past_cuf'])>0:
                    final_values['client_past_cuf'][len(final_values['client_past_cuf'])-1]['cuf'] = final_values['total_cuf']
        except:
            pass

        if len(final_values['client_past_grid_unavailability'])>0:
            final_values['client_past_grid_unavailability'][len(final_values['client_past_grid_unavailability'])-1]['unavailability'] = final_values['grid_unavailability']
        if len(final_values['client_past_equipment_unavailability'])>0:
            final_values['client_past_equipment_unavailability'][len(final_values['client_past_equipment_unavailability'])-1]['unavailability'] = final_values['equipment_unavailability']

        for index in range(len(final_values['client_past_generations'])):
            try:
                final_values['client_past_generations'][index]['energy'] = fix_generation_units(float(str(final_values['client_past_generations'][index]['energy']).split(' ')[0])) if len(str(final_values['client_past_generations'][index]['energy']).split(' '))==1 else str(final_values['client_past_generations'][index]['energy'])
            except Exception as exception:
                logger.debug("Energy error : " + str(exception))
                final_values['client_past_generations'][index]['energy'] = "0.0 kWh"
                continue

        final_values['client_past_generations'] = convert_values_to_common_unit(final_values['client_past_generations'])

        for index in range(len(final_values['client_past_dc_loss'])):
            try:
                final_values['client_past_dc_loss'][index]['dc_energy_loss'] = fix_generation_units(float(str(final_values['client_past_dc_loss'][index]['dc_energy_loss']).split(' ')[0]))
            except Exception as exception:
                logger.debug("DC Energy loss error : " + str(exception))
                final_values['client_past_dc_loss'][index]['dc_energy_loss'] = "0.0 kWh"
                continue
        final_values['client_past_dc_loss'] = make_losses_unit_same_as_generation(final_values['client_past_generations'], final_values['client_past_dc_loss'], 'dc_energy_loss')

        for index in range(len(final_values['client_past_conversion_loss'])):
            try:
                final_values['client_past_conversion_loss'][index]['conversion_loss'] = fix_generation_units(float(str(final_values['client_past_conversion_loss'][index]['conversion_loss']).split(' ')[0]))
            except Exception as exception:
                logger.debug("Conversion Loss error : " + str(exception))
                final_values['client_past_conversion_loss'][index]['conversion_loss'] = "0.0 kWh"
                continue

        final_values['client_past_conversion_loss'] = make_losses_unit_same_as_generation(final_values['client_past_generations'], final_values['client_past_conversion_loss'], 'conversion_loss')

        for index in range(len(final_values['client_past_ac_loss'])):
            try:
                final_values['client_past_ac_loss'][index]['ac_energy_loss'] = fix_generation_units(float(str(final_values['client_past_ac_loss'][index]['ac_energy_loss']).split(' ')[0]))
            except Exception as exception:
                logger.debug("AC Energy loss error : " + str(exception))
                final_values['client_past_ac_loss'][index]['ac_energy_loss'] = "0.0 kWh"
                continue
        final_values['client_past_ac_loss'] = make_losses_unit_same_as_generation(final_values['client_past_generations'], final_values['client_past_ac_loss'], 'ac_energy_loss')

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                for index in range(len(final_values['client_past_pr'])):
                    try:
                        final_values['client_past_pr'][index]['pr'] = "{0:.2f}".format(float(final_values['client_past_pr'][index]['pr']))
                    except Exception as exception:
                        logger.debug("pr exception : " + str(exception))
                        final_values['client_past_pr'][index]['pr'] = 0.0
                        continue
        except:
            pass

        try:
            if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].solar_metrics):
                for index in range(len(final_values['client_past_cuf'])):
                    try:
                        final_values['client_past_cuf'][index]['cuf'] = "{0:.2f}".format(float(final_values['client_past_cuf'][index]['cuf']))
                    except:
                        final_values['client_past_cuf'][index]['cuf'] = 0.0
                        continue
        except:
            pass

        for index in range(len(final_values['client_past_grid_unavailability'])):
            try:
                final_values['client_past_grid_unavailability'][index]['unavailability'] = str("{0:.2f}".format(float(str(final_values['client_past_grid_unavailability'][index]['unavailability']).split(' ')[0]))) + " %"
            except Exception as exception:
                logger.debug("grid availability exception : " + str(exception))
                final_values['client_past_grid_unavailability'][index]['unavailability'] = " 0.0 %"
                continue

        for index in range(len(final_values['client_past_equipment_unavailability'])):
            try:
                final_values['client_past_equipment_unavailability'][index]['unavailability'] = str("{0:.2f}".format(float(str(final_values['client_past_equipment_unavailability'][index]['unavailability']).split(' ')[0]))) + " %"
            except Exception as exception:
                logger.debug("equipment availability exception : " + str(exception))
                final_values['client_past_equipment_unavailability'][index]['unavailability'] = " 0.0 %"
                continue
        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].alerts):
            final_values['client_current_inverter_error_details'] = client_current_inverter_error_details
            final_values['total_inverter_error_numbers'] = total_inverter_error_numbers

        if organization_user.is_admin or (not organization_user.is_admin and plant.features_enabled.all()[0].analytics):
            final_values['client_string_anomaly_details'] = client_current_string_anomaly_details
            final_values['client_inverter_cleaning_details'] = client_current_inverter_cleaning_details
            final_values['total_low_anomaly_smb_numbers'] = total_low_anomaly_smb_numbers
            final_values['total_high_anomaly_smb_numbers'] = total_high_anomaly_smb_numbers
            final_values['total_inverter_cleaning_numbers'] = total_inverter_cleaning_numbers
        final_values['plants'] = plant_list
        return final_values
    except Exception as exception:
        print(str(exception))
        return {}


def get_mobile_client_status_data_offline(client, date, solar_plants, live=False):
    try:
        value_client = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                          identifier=client.slug,
                                                          ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
        final_values = {}
        if len(value_client) > 0:
            final_values['client_name'] = str(value_client[0].name)
            final_values['client_slug'] = str(client.slug)
            final_values['client_logo'] = str(client.dataglenclient.clientMobileLogo) if client.dataglenclient and client.dataglenclient.clientMobileLogo else ""
            final_values['total_diesel'] = "{0:.1f} L".format(float(value_client[0].plant_generation_today)/4.0)
            final_values['total_energy'] = fix_generation_units(float(value_client[0].total_generation))
            final_values['energy_today'] = fix_generation_units(float(value_client[0].plant_generation_today))
            final_values['total_capacity'] = fix_capacity_units(float(value_client[0].capacity))
            final_values['total_co2'] = fix_co2_savings(float(value_client[0].co2_savings))

            if live:
                final_values['total_active_power'] = "{0:.2f}".format(value_client[0].active_power) if value_client[0].active_power else 0.0
                final_values['total_irradiation'] = "{0:.2f}".format(value_client[0].irradiation) if value_client[0].irradiation else 0.0
                final_values['updated_at'] = str(value_client[0].updated_at)

            final_values['total_connected_plants'] = 0
            final_values['total_disconnected_plants'] = 0
            final_values['total_unmonitored_plants'] = 0

            predicted_energy_till_time = 0.0
            total_energy_for_network_up_plants = 0.0
            total_capacity_for_network_up_plants = 0.0
            final_values['total_capacity_past_month'] = 0.0
            final_values['energy_current_month'] = 0.0

            # TODO: Move this parameter to PlantCompleteValues table
            for plant in solar_plants:
                starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
                endtime = date
                endtime_today = date.replace(hour=23, minute=0, second=0, microsecond=0)

                try:
                    if plant.commissioned_date and ((date.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
                        final_values['total_capacity_past_month'] += float(plant.capacity)
                except Exception as exception:
                    print (str(exception))

                try:
                    if plant.gateway.all()[0].isMonitored:
                        if not plant.gateway.all()[0].isVirtual:
                            stats = get_user_data_monitoring_status(plant.gateway)
                            if stats is not None:
                                active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                                errors_len = len(active_dead) + len(deactivated_alive)
                                unmonitored = len(unmonitored)
                            else:
                                errors_len = 0
                                unmonitored = 0
                            if unmonitored is not 0 :
                                network_up = 'unknown'
                            elif errors_len is not 0:
                                network_up = 'No'
                            else:
                                network_up = 'Yes'
                        else:
                            isNetworkUp = check_network_for_virtual_gateways(plant)
                            if isNetworkUp:
                                network_up = 'Yes'
                            else:
                                network_up = 'No'
                    else:
                        network_up = 'unknown'

                    if network_up == 'unknown':
                        final_values['total_unmonitored_plants'] +=1
                    elif network_up == 'No':
                        final_values['total_disconnected_plants'] +=1
                    else:
                        final_values['total_connected_plants'] +=1
                except:
                    pass

                # current month's generation
                try:
                    past_energy_values = HistoricEnergyValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                             identifier=plant.slug).limit(1)
                    current_month_generation = float(past_energy_values[0].energy)
                except Exception as exception:
                    logger.debug(str(exception))
                    current_month_generation = 0.0
                    pass

                final_values['energy_current_month'] += current_month_generation

                #Today's predicted energy value till time
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)

                if network_up == 'Yes':
                    predicted_energy_till_time += float(predicted_energy_value)

                    try:
                        value_plant = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant.metadata.plantmetasource.sourceKey,
                                                                         ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

                        if len(value_plant)>0:
                            total_energy_for_network_up_plants += float(value_plant[0].plant_generation_today)
                            total_capacity_for_network_up_plants += float(value_plant[0].capacity)
                    except Exception as exception:
                        logger.debug(str(exception))

            #final_values['energy_current_month'] += float(value_client[0].plant_generation_today)
            final_values['energy_current_month'] = fix_generation_units(final_values['energy_current_month'])
            prediction_starttime = date.replace(hour=6, minute=0, second=0, microsecond=0)
            duration_hours = (endtime - prediction_starttime).total_seconds()/3600
            final_duration_hours = min(duration_hours, 12)

            try:
                final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time)-float(total_energy_for_network_up_plants))/(float(total_capacity_for_network_up_plants)*final_duration_hours))*100)
            except Exception as exception:
                logger.debug(str(exception))
                final_values['prediction_deviation'] = 0.0
            if predicted_energy_till_time > 0.0:
                final_values['prediction_deviation'] = str("{0:.2f}".format(float(final_values['prediction_deviation']))) + " %"
            else:
                final_values['prediction_deviation'] = "NA"
            final_values['total_capacity_past_month'] = fix_capacity_units(float(final_values['total_capacity_past_month']))
            final_values['know_more'] = False
        return final_values
    except Exception as exception:
        print(str(exception))
        return {}

def get_client_status_data_offline(client, date,  solar_plants, live=False):
    try:
        value_client = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                          identifier=client.slug,
                                                          ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
        final_values = {}
        if len(value_client) > 0:
            final_values['total_disconnected_inverters'] = 0
            final_values['total_disconnected_smbs'] = 0
            final_values['client_name'] = str(value_client[0].name)
            final_values['client_slug'] = str(client.slug)
            final_values['client_logo'] = str(client.dataglenclient.clientLogo) if client.dataglenclient and client.dataglenclient.clientLogo else ""
            final_values['total_energy'] = fix_generation_units(float(value_client[0].total_generation))
            final_values['energy_today'] = fix_generation_units(float(value_client[0].plant_generation_today))
            final_values['total_capacity'] = fix_capacity_units(float(value_client[0].capacity))
            final_values['total_co2'] = fix_co2_savings(float(value_client[0].co2_savings))
            final_values['client_dc_loss'] = fix_generation_units(float(value_client[0].dc_loss))
            final_values['client_conversion_loss'] = fix_generation_units(float(value_client[0].conversion_loss))
            final_values['client_ac_loss'] = fix_generation_units(float(value_client[0].ac_loss))
            final_values['grid_unavailability'] = str("{0:.2f}".format(value_client[0].grid_unavailability)) + " %" if value_client[0].grid_unavailability else "0 %"
            final_values['equipment_unavailability'] = str("{0:.2f}".format(value_client[0].equipment_unavailability)) + " %" if value_client[0].equipment_unavailability else "0 %"
            final_values['total_pr'] = "{0:.2f}".format(value_client[0].pr) if value_client[0].pr else 0.0
            final_values['total_cuf'] = "{0:.2f}".format(value_client[0].cuf) if value_client[0].cuf else 0.0
            if live:
                final_values['total_active_power'] = "{0:.2f}".format(value_client[0].active_power) if value_client[0].active_power else 0.0
                final_values['total_irradiation'] = "{0:.2f}".format(value_client[0].irradiation) if value_client[0].irradiation else 0.0
                final_values['total_connected_inverters'] = int(value_client[0].connected_inverters)
                #final_values['total_disconnected_inverters'] = int(value_client[0].disconnected_inverters)
                final_values['total_invalid_inverters'] = int(value_client[0].invalid_inverters)
                final_values['total_connected_smbs'] = int(value_client[0].connected_smbs)
                #final_values['total_disconnected_smbs'] = int(value_client[0].disconnected_smbs)
                final_values['total_invalid_smbs'] = int(value_client[0].invalid_smbs)
                final_values['status'] = str(value_client[0].status)
                final_values['updated_at'] = str(value_client[0].updated_at)
            final_values['total_unacknowledged_tickets'] = int(value_client[0].unacknowledged_tickets)
            final_values['total_open_tickets'] = int(value_client[0].open_tickets)
            final_values['total_closed_tickets'] = int(value_client[0].closed_tickets)
            final_values['client_past_generations'] = ast.literal_eval(str(value_client[0].past_generations))
            final_values['client_past_pr'] = ast.literal_eval(str(value_client[0].past_pr))
            final_values['client_past_cuf'] = ast.literal_eval(str(value_client[0].past_cuf))
            final_values['client_past_grid_unavailability'] = ast.literal_eval(str(value_client[0].past_grid_unavailability))
            final_values['client_past_equipment_unavailability'] = ast.literal_eval(str(value_client[0].past_equipment_unavailability))
            final_values['client_past_dc_loss'] = ast.literal_eval(str(value_client[0].past_dc_loss))
            final_values['client_past_dc_loss'] = make_losses_unit_same_as_generation(final_values['client_past_generations'], final_values['client_past_dc_loss'], 'dc_energy_loss')
            final_values['client_past_conversion_loss'] = ast.literal_eval(str(value_client[0].past_conversion_loss))
            final_values['client_past_conversion_loss'] = make_losses_unit_same_as_generation(final_values['client_past_generations'], final_values['client_past_conversion_loss'], 'conversion_loss')
            final_values['client_past_ac_loss'] = ast.literal_eval(str(value_client[0].past_ac_loss))
            final_values['client_past_ac_loss'] = make_losses_unit_same_as_generation(final_values['client_past_generations'], final_values['client_past_ac_loss'], 'ac_energy_loss')
            final_values['string_errors_smbs'] = 0
            final_values['today_predicted_energy_value_till_time'] = 0.0
            final_values['total_today_predicted_energy_value'] = 0.0
            final_values['client_specific_yield'] = 0.0
            count_specific_yield = 0
            final_values['client_past_specific_yield'] = []
            final_values['total_connected_plants'] = 0
            final_values['total_disconnected_plants'] = 0
            final_values['total_unmonitored_plants'] = 0
            final_values[''] = 0.0
            predicted_energy_till_time = 0.0
            total_energy_for_network_up_plants = 0.0
            total_capacity_for_network_up_plants = 0.0
            client_current_inverter_error_details = []
            total_inverter_error_numbers = 0
            client_current_string_anomaly_details = []
            total_low_anomaly_smb_numbers = 0
            total_high_anomaly_smb_numbers = 0
            client_current_inverter_cleaning_details = []
            total_inverter_cleaning_numbers = 0
            final_values['total_capacity_past_month'] = 0.0
            plants_disconnected_list = []
            gateways_disconnected_list = []
            gateways_powered_off_list = []
            # TODO: Move this parameter to PlantCompleteValues table
            for plant in solar_plants:
                string_error_smbs = set()
                ajbs = plant.ajb_units.all().filter(isActive=True)
                starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
                endtime = date
                endtime_today = date.replace(hour=23, minute=0, second=0, microsecond=0)

                try:
                    if plant.commissioned_date and ((date.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
                        final_values['total_capacity_past_month'] += float(plant.capacity)
                except Exception as exception:
                    print (str(exception))

                for ajb in ajbs:
                    string_errors = EventsByTime.objects.filter(identifier=str(ajb.sourceKey)+'_ajb',insertion_time__gte=starttime, insertion_time__lte=endtime)
                    if len(string_errors)>0:
                        string_error_smbs.add(str(ajb.name))

                #plant connection status from Tickets
                plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
                if len(plant_network_details)>0:
                    plants_disconnected_list.append(str(plant.slug))
                    try:
                        gateways_disconnected_list.extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                    except:
                        pass
                    try:
                        gateways_powered_off_list.extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                    except:
                        pass

                #Total today's predicted energy value
                total_predicted_energy_value = get_energy_prediction_data(starttime, endtime_today, plant)
                final_values['total_today_predicted_energy_value'] += float(total_predicted_energy_value)

                #past specific yield
                try:
                    past_specific_yield_list = []
                    past_specific_yield_values = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                   identifier=plant.metadata.plantmetasource.sourceKey).order_by('-ts').values_list('specific_yield', 'ts').limit(7)
                    for past_specific_yield_value in past_specific_yield_values:
                        past_specific_yield_value_dict = {}
                        past_specific_yield_value_dict['timestamp'] = str(past_specific_yield_value[1])
                        past_specific_yield_value_dict['specific_yield'] = round(float(past_specific_yield_value[0]),2)
                        past_specific_yield_list.append(past_specific_yield_value_dict)
                except Exception as exception:
                    print(str(exception))
                    pass
                # today's specific yield
                try:
                    if float(past_specific_yield_values[len(past_specific_yield_values)-1][0]) > 0.0:
                        final_values['client_specific_yield'] += float(past_specific_yield_values[len(past_specific_yield_values)-1][0])
                        count_specific_yield += 1
                except:
                    pass

                if len(final_values['client_past_specific_yield']) == 0 :
                    final_values['client_past_specific_yield'] = copy.deepcopy(past_specific_yield_list)
                else:
                    for i in range(len(final_values['client_past_specific_yield'])):
                        try:
                            if float(final_values['client_past_specific_yield'][i]['specific_yield']) == 0.0:
                                final_values['client_past_specific_yield'][i]['specific_yield'] = past_specific_yield_list[i]['specific_yield']
                            elif float(past_specific_yield_list[i]['specific_yield']) > 0.0:
                                final_values['client_past_specific_yield'][i]['specific_yield'] = (float(final_values['client_past_specific_yield'][i]['specific_yield'])+float(past_specific_yield_list[i]['specific_yield']))/2
                            else:
                                pass
                        except Exception as exception:
                            print str(exception)
                            continue

                final_values['string_errors_smbs'] += len(string_error_smbs)
                try:
                    if plant.gateway.all()[0].isMonitored:
                        if not plant.gateway.all()[0].isVirtual:
                            stats = get_user_data_monitoring_status(plant.gateway)
                            if stats is not None:
                                active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                                errors_len = len(active_dead) + len(deactivated_alive)
                                unmonitored = len(unmonitored)
                            else:
                                errors_len = 0
                                unmonitored = 0
                            if unmonitored is not 0 :
                                network_up = 'unknown'
                            elif errors_len is not 0:
                                network_up = 'No'
                            else:
                                network_up = 'Yes'
                        else:
                            isNetworkUp = check_network_for_virtual_gateways(plant)
                            if isNetworkUp:
                                network_up = 'Yes'
                            else:
                                network_up = 'No'
                    else:
                        network_up = 'unknown'

                    if network_up == 'unknown':
                        final_values['total_unmonitored_plants'] +=1
                    elif network_up == 'No':
                        final_values['total_disconnected_plants'] +=1
                    else:
                        final_values['total_connected_plants'] +=1
                except:
                    pass

                # adding below section of code to show disconnected devices, only if the network is up.
                if network_up == 'Yes':
                    print(plant.slug)
                    plant_value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=plant.metadata.plantmetasource.sourceKey,
                                                                     ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(plant_value)>0:
                        final_values['total_disconnected_inverters'] += int(plant_value[0].disconnected_inverters)
                        final_values['total_disconnected_smbs'] += int(plant_value[0].disconnected_smbs)

                # current inverter error detail
                current_inverter_error_detail = get_current_inverter_alarms(plant)
                client_current_inverter_error_details.append(current_inverter_error_detail)
                if len(current_inverter_error_detail)>0:
                    total_inverter_error_numbers += int(current_inverter_error_detail['affected_inverters_number'])

                # Current SMB anomaly detail
                current_string_anomaly_detail = get_current_string_anomaly_details_without_association(plant, date, 60)
                client_current_string_anomaly_details.append(current_string_anomaly_detail)
                if len(current_string_anomaly_detail)>0:
                    total_low_anomaly_smb_numbers += int(current_string_anomaly_detail['low_anomaly_affected_ajbs_number'])
                    total_high_anomaly_smb_numbers += int(current_string_anomaly_detail['high_anomaly_affected_ajbs_number'])

                # Inverter cleaning details
                current_cleaning_details = get_current_inverter_cleaning_details(plant)
                client_current_inverter_cleaning_details.append(current_cleaning_details)
                if len(current_cleaning_details)>0:
                    total_inverter_cleaning_numbers += int(current_cleaning_details['inverters_required_cleaning_numbers'])

                #Today's predicted energy value till time
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                final_values['today_predicted_energy_value_till_time'] += float(predicted_energy_value)

                if network_up == 'Yes':
                    predicted_energy_till_time += float(predicted_energy_value)

                    try:
                        value_plant = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant.metadata.plantmetasource.sourceKey,
                                                                         ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

                        if len(value_plant)>0:
                            total_energy_for_network_up_plants += float(value_plant[0].plant_generation_today)
                            total_capacity_for_network_up_plants += float(value_plant[0].capacity)
                    except Exception as exception:
                        logger.debug(str(exception))

            prediction_starttime = date.replace(hour=6, minute=0, second=0, microsecond=0)
            duration_hours = (endtime - prediction_starttime).total_seconds()/3600
            final_duration_hours = min(duration_hours, 12)

            try:
                final_values['total_specific_yield'] = round(final_values['client_specific_yield']/count_specific_yield,2)
            except:
                final_values['total_specific_yield'] = 0.0

            for i in range(len(final_values['client_past_specific_yield'])):
                try:
                    final_values['client_past_specific_yield'][i]['specific_yield'] = round(final_values['client_past_specific_yield'][i]['specific_yield'],2)
                except:
                    continue
            try:
                final_values['client_past_specific_yield'][len(final_values['client_past_specific_yield'])-1]['specific_yield'] = final_values['total_specific_yield']
            except Exception as exception:
                logger.debug(str(exception))
                pass

            try:
                final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time)-float(total_energy_for_network_up_plants))/(float(total_capacity_for_network_up_plants)*final_duration_hours))*100)
            except Exception as exception:
                logger.debug(str(exception))
                final_values['prediction_deviation'] = 0.0
            if predicted_energy_till_time > 0.0:
                final_values['prediction_deviation'] = str("{0:.2f}".format(float(final_values['prediction_deviation']))) + " %"
            else:
                final_values['prediction_deviation'] = "NA"
            final_values['gateways_disconnected'] = len(gateways_disconnected_list)
            final_values['gateways_disconnected_list'] = gateways_disconnected_list
            final_values['gateways_powered_off'] = len(gateways_powered_off_list)
            final_values['gateways_powered_off_list'] = gateways_powered_off_list
            final_values['today_predicted_energy_value_till_time'] = fix_generation_units(final_values['today_predicted_energy_value_till_time'])
            final_values['total_today_predicted_energy_value'] = fix_generation_units(final_values['total_today_predicted_energy_value'])
            final_values['client_current_inverter_error_details'] = client_current_inverter_error_details
            final_values['client_string_anomaly_details'] = client_current_string_anomaly_details
            final_values['client_inverter_cleaning_details'] = client_current_inverter_cleaning_details
            final_values['total_inverter_error_numbers'] = total_inverter_error_numbers
            final_values['total_low_anomaly_smb_numbers'] = total_low_anomaly_smb_numbers
            final_values['total_high_anomaly_smb_numbers'] = total_high_anomaly_smb_numbers
            final_values['total_inverter_cleaning_numbers'] = total_inverter_cleaning_numbers
            final_values['total_capacity_past_month'] = fix_capacity_units(float(final_values['total_capacity_past_month']))
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return {}


class V1_MobileSolarClientView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            profile_data = self.get_profile_data()
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    solar_plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                solar_plants = filter_solar_plants(profile_data)
            logger.debug(solar_plants)
        except Exception as exc:
            logger.debug(str(exc))
            return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

        current_time = timezone.now()
        current_time = current_time.astimezone(pytz.timezone('Asia/Kolkata'))
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                owner=True
                solar_plants = SolarPlant.objects.filter(groupClient=user_client)
                client=user_client
        except Exception as exception:
            logger.debug(str(exception))
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)
        if owner:
            try:
                final_values = get_mobile_client_status_data_offline(client, current_time, solar_plants, True)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            try:
                reply = V1_MobileClientSummary(data=final_values)
                if reply.is_valid():
                    return Response(reply.data, status=status.HTTP_200_OK)
                else:
                    logger.debug(reply.errors)
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                user = self.request.user
                final_values = get_final_plant_status_for_non_client_owner_users_for_mobiles(solar_plants, user, current_time, True, True)
                try:
                    reply = V1_MobileClientSummary(data=final_values)
                    if reply.is_valid():
                        return Response(reply.data, status=status.HTTP_200_OK)
                    else:
                        logger.debug(reply.errors)
                        return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class V1_SolarClientView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            profile_data = self.get_profile_data()
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    solar_plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                solar_plants = filter_solar_plants(profile_data)
            logger.debug(solar_plants)
        except Exception as exc:
            logger.debug(str(exc))
            return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                owner=True
                solar_plants = SolarPlant.objects.filter(groupClient=user_client)
                client=user_client
        except Exception as exception:
            logger.debug(str(exception))
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)

        plant_list = []
        current_time = timezone.now()
        try:
            time_zone = client.dataglenclient.get_groups()[0].solarplant.metadata.plantmetasource.dataTimezone
            current_time = current_time.astimezone(pytz.timezone(time_zone))
        except Exception as exception:
            logger.debug(str(exception))
            current_time = current_time.astimezone(pytz.timezone('Asia/Kolkata'))

        if owner:
            try:
                final_values = get_client_status_data_offline(client, current_time, solar_plants, True)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            try:
                user = self.request.user
                for plant in solar_plants:
                    try:
                        current_time = timezone.now()
                        current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    except Exception as exc:
                        logger.debug(str(exc))
                        current_time = timezone.now()
                    try:
                        plant_value = get_plant_status_data_offline(plant, user, current_time, False, True)
                        if len(plant_value)>0:
                            plant_list.append(plant_value)
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                final_values['plants'] = plant_list
                try:
                    reply = V1_PlantClientSummary(data=final_values)
                    if reply.is_valid():
                        return Response(reply.data, status=status.HTTP_200_OK)
                    else:
                        logger.debug(reply.errors)
                        return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                user = self.request.user
                final_values = get_final_plant_status_for_non_client_owner_users(solar_plants, user, current_time, True, True)
                try:
                    reply = V1_PlantClientSummary(data=final_values)
                    if reply.is_valid():
                        return Response(reply.data, status=status.HTTP_200_OK)
                    else:
                        logger.debug(reply.errors)
                        return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_plant_summary_specific_date(plant, date):
    try:
        plant_values = {}
        plant_values['generation'] = 0.0
        plant_values['performance_ratio'] = 0.0
        plant_values['cuf'] = 0.0
        plant_values['specific_yield'] = 0.0
        plant_values['dc_loss'] = 0.0
        plant_values['conversion_loss'] = 0.0
        plant_values['ac_loss'] = 0.0
        plant_values['grid_availability'] = 0.0
        plant_values['equipment_availability'] = 0.0
        plant_values['insolation'] = 0.0
        plant_values['predicted_energy'] = 0.0
        plant_values['pvsyst_generation'] = 0.0
        plant_values['pvsyst_pr'] = 0.0
        plant_values['pvsyst_tilt_angle'] = 0.0
        plant_values['timestamp'] = str(date)
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts=date)
        if len(plant_summary_values)>0:
            value = plant_summary_values[0]
            plant_values['generation'] = value.generation
            plant_values['plant_co2'] = fix_co2_savings(float(plant_values['generation'])*0.7) if value.generation else 0.0
            plant_values['generation'] = fix_generation_units(plant_values['generation']) if value.generation else 0.0
            plant_values['performance_ratio'] = "{0:.2f}".format(float(value.performance_ratio)) if value.performance_ratio else 0.0
            plant_values['cuf'] = "{0:.2f}".format(float(value.cuf)) if value.cuf else 0.0
            plant_values['specific_yield'] = "{0:.2f}".format(float(value.specific_yield)) if value.specific_yield else 0.0
            plant_values['dc_loss'] = fix_generation_units(float(value.dc_loss)) if value.dc_loss else None
            plant_values['conversion_loss'] = fix_generation_units(value.conversion_loss) if value.conversion_loss else None
            plant_values['ac_loss'] = fix_generation_units(value.ac_loss) if value.ac_loss else None
            plant_values['grid_availability'] = "{0:.2f}".format(float(value.grid_availability)) if value.grid_availability else 100.0
            plant_values['equipment_availability'] = "{0:.2f}".format(float(value.equipment_availability)) if value.equipment_availability else 100.0
            plant_values['insolation'] = "{0:.2f}".format(float(value.average_irradiation)) if value.average_irradiation else 0.0
            plant_values['timestamp'] = str(value.ts)

        historic_energy = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                           count_time_period=86400,
                                                                           identifier=str(plant.slug),
                                                                           ts=date)
        if len(historic_energy)>0:
            plant_values['predicted_energy'] = fix_generation_units(historic_energy[0].predicted_energy) if historic_energy[0].predicted_energy else None

        if len(plant.pvsyst_info.all())>0:
            current_month = date.month
            pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='NORMALISED_ENERGY_PER_DAY',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=date.year,
                                                               timePeriodValue=current_month)
            if len(pv_sys_info_generation)==0:
                pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='NORMALISED_ENERGY_PER_DAY',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)
            plant_capacity = plant.capacity
            if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
                pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
                plant_values['pvsyst_generation'] = fix_generation_units(pvsyst_generation)

            pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                       parameterName='PERFORMANCE_RATIO',
                                                       timePeriodType='MONTH',
                                                       timePeriodDay=0,
                                                       timePeriodYear=date.year,
                                                       timePeriodValue=current_month)
            if len(pv_sys_info_pr)==0:
                pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='PERFORMANCE_RATIO',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=0,
                                                           timePeriodValue=current_month)

            if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
                pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
                plant_values['pvsyst_pr'] = pvsyst_pr

            pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='TILT_ANGLE',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=date.year,
                                                               timePeriodValue=current_month)

            if len(pv_sys_info_tilt_angle) == 0:
                pv_sys_info_tilt_angle = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='TILT_ANGLE',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)

            if len(pv_sys_info_tilt_angle)> 0 and pv_sys_info_tilt_angle[0].parameterValue is not None:
                pvsyst_tilt_angle = float(pv_sys_info_tilt_angle[0].parameterValue)
                plant_values['pvsyst_tilt_angle'] = pvsyst_tilt_angle

        return plant_values
    except Exception as exception:
        logger.debug(str(exception))
        return {}

def get_new_plant_summary_specific_date(starttime, endtime, plant):
    try:
        final_values = {}
        while endtime>starttime:
            plant_values = {}
            plant_values['generation'] = 0.0
            plant_values['performance_ratio'] = 0.0
            plant_values['cuf'] = 0.0
            plant_values['specific_yield'] = 0.0
            plant_values['dc_loss'] = 0.0
            plant_values['conversion_loss'] = 0.0
            plant_values['ac_loss'] = 0.0
            plant_values['grid_availability'] = 0.0
            plant_values['equipment_availability'] = 0.0
            plant_values['insolation'] = 0.0
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=86400,
                                                                      identifier=str(plant.slug),
                                                                      ts=starttime)

            if len(plant_summary_values)>0:
                value = plant_summary_values[0]
                plant_values['generation'] = value.generation
                plant_values['plant_co2'] = float(plant_values['generation'])*0.7 if value.generation else 0.0
                plant_values['generation'] = plant_values['generation'] if value.generation else 0.0
                plant_values['performance_ratio'] = "{0:.2f}".format(float(value.performance_ratio)) if value.performance_ratio else 0.0
                plant_values['cuf'] = "{0:.2f}".format(float(value.cuf)) if value.cuf else 0.0
                plant_values['specific_yield'] = "{0:.2f}".format(float(value.specific_yield)) if value.specific_yield else 0.0
                plant_values['dc_loss'] = value.dc_loss if value.dc_loss else None
                plant_values['conversion_loss'] = value.conversion_loss if value.conversion_loss else None
                plant_values['ac_loss'] = value.ac_loss if value.ac_loss else None
                plant_values['grid_availability'] = "{0:.2f}".format(float(value.grid_availability)) if value.grid_availability else 100.0
                plant_values['equipment_availability'] = "{0:.2f}".format(float(value.equipment_availability)) if value.equipment_availability else 100.0
                plant_values['insolation'] = "{0:.2f}".format(float(value.average_irradiation)) if value.average_irradiation else 0.0
                plant_values['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            final_values[str(starttime.date())] = plant_values
            starttime = starttime+timedelta(days=1)
        return final_values
    except Exception as exception:
        print(str(exception))
        return {}

def get_new_plant_summary_specific_date_range(startTime, endTime, plant):
    try:
        plant_values = {}
        plant_values['generation'] = []
        plant_values['performance_ratio'] = []
        plant_values['cuf'] = []
        plant_values['specific_yield'] = []
        plant_values['dc_loss'] = []
        plant_values['conversion_loss'] = []
        plant_values['ac_loss'] = []
        plant_values['grid_availability'] = []
        plant_values['equipment_availability'] = []
        plant_values['insolation'] = []
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=startTime,
                                                                  ts__lte=endTime)
        for value in plant_summary_values:
            generation = {}
            generation['value'] = value.generation
            generation['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['generation'].append(generation)
            performance_ratio = {}
            performance_ratio['value'] = value.performance_ratio
            performance_ratio['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['performance_ratio'].append(performance_ratio)
            cuf = {}
            cuf['value'] = value.cuf
            cuf['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['cuf'].append(cuf)
            specific_yield = {}
            specific_yield['value'] = value.specific_yield
            specific_yield['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['specific_yield'].append(specific_yield)
            dc_loss = {}
            dc_loss['value'] = value.dc_loss
            dc_loss['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['dc_loss'].append(dc_loss)
            conversion_loss = {}
            conversion_loss['value'] = value.conversion_loss
            conversion_loss['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['conversion_loss'].append(conversion_loss)
            ac_loss = {}
            ac_loss['value'] = value.ac_loss
            ac_loss['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['ac_loss'].append(ac_loss)
            grid_availability = {}
            grid_availability['value'] = value.grid_availability
            grid_availability['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['grid_availability'].append(grid_availability)
            equipment_availability = {}
            equipment_availability['value'] = value.equipment_availability
            equipment_availability['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['equipment_availability'].append(equipment_availability)
            insolation = {}
            insolation['value'] = value.average_irradiation
            insolation['timestamp'] = value.ts.strftime('%Y-%m-%dT%H:%M:%SZ')
            plant_values['insolation'].append(insolation)
        return plant_values
    except Exception as exception:
        print(str(exception))
        return {}

class V1_PlantSummaryView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            logger.debug("slug")
            logger.debug(plant_slug)
            plant = SolarPlant.objects.get(slug=plant_slug)
            profile_data = self.get_profile_data()
            solar_plants = filter_solar_plants(profile_data)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    solar_plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                solar_plants = filter_solar_plants(profile_data)
            if plant not in solar_plants:
                raise ObjectDoesNotExist
        except Exception as exc:
            logger.debug(str(exc))
            return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
        combined = self.request.query_params.get('combined', 'FALSE')
        date = self.request.query_params.get('date',None)
        logger.debug(date)
        if combined.upper() == 'TRUE':
            combined = True
        else:
            combined = False

        if date:
            try:
                try:
                    tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
                except:
                    tz = pytz.timezone("UTC")
                date = parser.parse(date)
                if date.tzinfo is None:
                    date = tz.localize(date)
                    date = date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                date = date.replace(hour=0, minute=0, second=0, microsecond=0)
                logger.debug(date)
                plant_data = get_plant_summary_specific_date(plant, date)
                return Response(plant_data, status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("Invalid Date", status=status.HTTP_400_BAD_REQUEST)

        else:
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                logger.debug(str(exc))
                current_time = timezone.now()
            try:
                user = self.request.user
                plant_data = get_plant_status_data_offline(plant, user, current_time, True, True, combined)
                try:
                    reply = V1_PlantStatusSummary(data=plant_data)
                    if reply.is_valid():
                        return Response(reply.data, status=status.HTTP_200_OK)
                    else:
                        logger.debug(reply.errors)
                        return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from solarrms.spark_values import get_plant_live_data_status_spark
class V1_InverterLiveStatusView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    def list(self, request, plant_slug=None, **kwargs):
        logger.debug(plant_slug)
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            profile_data = self.get_profile_data()
            solar_plants = filter_solar_plants(profile_data)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    solar_plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                solar_plants = filter_solar_plants(profile_data)
            if plant not in solar_plants:
                raise ObjectDoesNotExist
        except Exception as exc:
            return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            logger.debug(str(exc))
            current_time = timezone.now()

        device_type = self.request.query_params.get("device_type","inverter")
        mobile_data = self.request.query_params.get("mobile_data", None)
        try:
            if device_type == 'ajb':
                ajb_name = self.request.query_params.get("ajb_name", None)
                if ajb_name is not None:
                    try:
                        ajb = AJB.objects.get(plant=plant, name=ajb_name)
                        response = get_plant_live_data_status_individual_ajb(plant, ajb)
                        return Response(data=response, status=status.HTTP_200_OK)
                    except:
                        return Response("Invalid AJB name", status=status.HTTP_400_BAD_REQUEST)
                else:
                    inverter_name = self.request.query_params.get("inverter", None)
                    plant_data = get_plant_live_ajb_status(plant, current_time, True, inverter_name)
                    reply = V1_AJBLiveStatus(data=plant_data)
            elif device_type == 'inverter':
                mobile_app = True
                if mobile_data is None:
                    if self.request.META.has_key('HTTP_USER_AGENT'):
                        http_user_agent = str(self.request.META['HTTP_USER_AGENT'])
                        # logger.debug("LIVEAPI HUA : " + http_user_agent)
                        if "okhttp" in http_user_agent or "iOS" in http_user_agent:
                            mobile_app = True
                        else:
                            mobile_app = False

                inverter_name = self.request.query_params.get("inverter", None)
                # logger.debug("LIVEAPI HUA : " + str(inverter_name))
                plant_data = get_plant_live_data_status(plant, current_time, True, inverter_name, mobile_app=mobile_app)
                # logger.debug("LIVEAPI HUA : " + str(plant_data))
                #plant_data = get_plant_live_data_status_spark(plant, current_time, True, inverter_name)
                return Response(data=plant_data, status=status.HTTP_200_OK)
                reply = V1_InverterLiveStatus(data=plant_data)
            else:
                return Response("INVALID_DEVICE_TYPE", status=status.HTTP_400_BAD_REQUEST)
            try:
                if reply.is_valid():
                    return Response(reply.data, status=status.HTTP_200_OK)
                else:
                    logger.debug(reply.errors)
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class V1_AC_SLD_LiveStatusView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    def list(self, request, plant_slug=None, **kwargs):
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            profile_data = self.get_profile_data()
            solar_plants = filter_solar_plants(profile_data)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    solar_plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                solar_plants = filter_solar_plants(profile_data)
            if plant not in solar_plants:
                raise ObjectDoesNotExist
        except Exception as exc:
            return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            logger.debug(str(exc))
            current_time = timezone.now()

        device_type = self.request.query_params.get("device_type","meter")
        try:
            if device_type == 'transformer':
                transformer_name = self.request.query_params.get("transformer", None)
                ac_sld_data = get_plant_ac_live_data_status_transformer(plant, current_time, True, transformer_name)
            elif device_type == 'meter':
                meter_name = self.request.query_params.get("meter", None)
                ac_sld_data = get_plant_ac_live_data_status(plant, current_time, True, meter_name)
            else:
                return Response("INVALID_DEVICE_TYPE", status=status.HTTP_400_BAD_REQUEST)
            try:
                return Response(data=ac_sld_data, status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_yesterday_residual_data(plant):
    try:
        try:
            endtime = timezone.now()
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            endtime = timezone.now()
            logger.debug("Error in converting the timezone" + str(exc))
        endtime = endtime.replace(hour=0, minute=0, second=0, microsecond=0)
        starttime = endtime - timedelta(days=1)
        inverters = plant.independent_inverter_units.all()
        final_residual_values = {}
        logger.debug(starttime)
        logger.debug(endtime)
        for inverter in inverters:
            values = PredictedValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                                                    count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                    identifier=str(plant.slug)+'-'+str(inverter.name),
                                                    stream_name='cleaning',
                                                    ts__gte=starttime,
                                                    ts__lte=endtime
                                                    )
            if len(values)>0:
                final_residual_values[str(inverter.name)] = values[len(values)-1].residual
        return final_residual_values
    except Exception as exception:
        logger.debug(str(exception))

def get_residual_data(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        final_residual_values = {}
        for inverter in inverters:
            residual_values = {}
            values = PredictedValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                                                    count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                    identifier=str(plant.slug)+'-'+str(inverter.name),
                                                    stream_name='cleaning',
                                                    ts__gte=starttime,
                                                    ts__lte=endtime
                                                    )
            for value in values:
                try:
                    residual_values[value.ts.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).strftime('%Y-%m-%dT%H:%M:%SZ')] = value.residual_sum
                except Exception as exception:
                    try:
                        residual_values[pytz.utc.localize(value.ts).astimezone(pytz.timezone("Asia/Kolkata")).strftime('%Y-%m-%dT%H:%M:%SZ')] = value.residual_sum
                    except:
                        residual_values[value.ts.astimezone(pytz.timezone("Asia/Kolkata")).strftime('%Y-%m-%dT%H:%M:%SZ')] = value.residual_sum
                    continue
            final_residual_values[str(inverter.name)] = residual_values
        sorted_residuals = collections.OrderedDict()

        for key in sorted_nicely(final_residual_values.keys()):
            sorted_residuals[key] = final_residual_values[key]
        logger.debug(sorted_residuals)

        return sorted_residuals
    except Exception as exception:
        logger.debug(str(exception))

class PlantResidualData(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        request_arrival_time = timezone.now()
        context = self.get_profile_data(**kwargs)
        plants = filter_solar_plants(context)
        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
            plants = filter_solar_plants(context)
        plant = SolarPlant.objects.get(slug=plant_slug)
        if plant not in plants:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_PLANT_SLUG, settings.RESPONSE_TYPES.DRF,
                                        False, {})

        try:
            endtime = timezone.now()
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            endtime = timezone.now()
            logger.debug("Error in converting the timezone" + str(exc))
        endtime = endtime.replace(hour=0, minute=0, second=0, microsecond=0)
        starttime = endtime - timedelta(days=45)
        data = get_residual_data(starttime, endtime, plant)
        return Response(data)



class InvertersTotalYield(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            plant = SolarPlant.objects.get(slug=plant_slug)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            try:
                tz = pytz.timezone(plant.metasource.plantmetasource.dataTimezone)
            except:
                tz = pytz.timezone("UTC")
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]

                # convert into datetime objects
                st = parser.parse(st)
                if st.tzinfo is None:
                    st = tz.localize(st)
                et = parser.parse(et)
                if et.tzinfo is None:
                    et = tz.localize(et)
            except:
                return Response("Bad request : start time and end time are required.", status=status.HTTP_400_BAD_REQUEST)
            responseType = request.query_params.get("responseType", 'csv')
            if responseType == 'json':
                result = get_TotalYield_of_inverters(st, et, plant)
                if not result.empty:
                    response_data = result.to_json(orient='records', date_format='iso')
                    return Response(data=json.loads(response_data), status=status.HTTP_200_OK)
                else:
                    return Response([], status=status.HTTP_200_OK)
            else:
                file_name = "_".join([plant_slug, 'total_yield', str(st), str(et), ".csv"]).replace(" ", "_")
                response_csv = HttpResponse(content_type="text/csv")
                response_csv['Content-Disposition'] = 'attachment; filename=' + file_name
                writer = csv.writer(response_csv)
                response_data = get_TotalYield_of_inverters(st, et, plant)
                response = response_data.to_csv(date_format="%Y-%m-%dT%H:%M:%S",
                                              index=False)
                for line in response.split("\n"):
                    writer.writerow(line.split(","))
                return response_csv
        except Exception as exception:
            logger.debug("Error in fetching total yield values : " + str(exception))



class PlantDevicesView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(plant)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            response_data = get_plant_device_details(plant)
            return Response(data=response_data, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " +str(plant.slug)+ str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcrossPlantsDevicesView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            final_plants = []
            try:
                payload = self.request.data
                plant_slugs = payload['plant_slugs']
            except:
                return Response("Please specify plant slugs in request body", status=status.HTTP_400_BAD_REQUEST)

            try:
                for plant_slug in plant_slugs:
                    plant = SolarPlant.objects.get(slug=plant_slug)
                    final_plants.append(plant)
                    if plant not in plants:
                        return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            response_data = get_client_device_details_across_plants(final_plants)
            return Response(data=response_data, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " +str(plant.slug)+ str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import xlwt
class InvertersTotalYieldExcel(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            plant = SolarPlant.objects.get(slug=plant_slug)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            try:
                tz = pytz.timezone(plant.metasource.plantmetasource.dataTimezone)
            except:
                tz = pytz.timezone("UTC")
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]

                # convert into datetime objects
                st = parser.parse(st)
                if st.tzinfo is None:
                    st = tz.localize(st)
                et = parser.parse(et)
                if et.tzinfo is None:
                    et = tz.localize(et)
            except:
                return Response("Bad request : start time and end time are required.", status=status.HTTP_400_BAD_REQUEST)
            response = HttpResponse(content_type='application/ms-excel')
            file_name = "_".join([plant_slug, 'total_yield', str(st), str(et), ".xls"]).replace(" ", "_")
            response['Content-Disposition'] = 'attachment; filename=' + file_name

            inverters = plant.independent_inverter_units.all()
            wb = xlwt.Workbook(encoding='utf-8')
            ws = wb.add_sheet('TOTAL_YIELD')
            #ws = wb.add_sheet('User-Details')
            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            font_style.font.bold = True

            #columns = ['Username', 'First name', 'Last name', 'Email address', ]
            columns = []
            for inverter in inverters:
                columns.append(str(inverter.name))

            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()
            for inverter in inverters:
                rows = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                stream_name= 'TOTAL_YIELD',
                                                                timestamp_in_data__gte = st,
                                                                timestamp_in_data__lte = et
                                                                ).limit(0).order_by('timestamp_in_data').values_list('stream_value')
                #rows = User.objects.all().values_list('username', 'first_name', 'last_name', 'email')
                col_num = columns.index(str(inverter.name))
                row_num += 1
                for row in rows:
                        ws.write(row_num, col_num, row[col_num], font_style)
                row_num = 0
            wb.save(response)
            return response
        except Exception as exception:
            logger.debug(str(exception))



class MultipleDevicesMultipleStreamsView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                # if not st.tzinfo:
                #     st = pytz.utc.localize(st)
                # if not et.tzinfo:
                #     et = pytz.utc.localize(et)
                # st = st.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                # et = et.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("start time and end time are required", status=status.HTTP_400_BAD_REQUEST)

            data_aggregation = request.query_params.get("data_aggregation", "FALSE")
            aggregator = request.query_params.get("aggregator", "MINUTE")
            aggregation_period = request.query_params.get("aggregation_period", 60)
            aggregation_type = request.query_params.get("aggregation_type","mean")


            if str(aggregation_type).upper() not in ["MIN","MAX","MEAN"]:
                return Response("INVALID_AGGREGATION_TYPE", status=status.HTTP_400_BAD_REQUEST)

            sources_stream_association = self.request.data
            logger.debug(sources_stream_association)
            try:
                delta = (int(plant.metadata.plantmetasource.dataReportingInterval)/60)*1.5 if plant.gateway.all()[0].isVirtual else 20
            except:
                delta = 30

            if str(data_aggregation).upper() == "TRUE":
                response_data = get_multiple_sources_multiple_streams_data_merge_pandas_aggregation(starttime=st, endtime=et,
                                                                           sources_stream_association=sources_stream_association,
                                                                           delta=delta, plant=plant, aggregator=aggregator,
                                                                           aggregation_period=aggregation_period,
                                                                           aggregation_type=aggregation_type)
            else:
                response_data = get_multiple_sources_multiple_streams_data_merge_pandas(starttime=st, endtime=et, sources_stream_association=sources_stream_association, delta=delta, plant=plant)
            logger.debug(response_data)
            return Response(data=response_data, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " +str(plant.slug)+ str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def transpose_dict(d):
   newdict = {}
   for k in d:
       for v in d[k]:
           newdict.setdefault(v, []).append(k)
   return newdict



# Adding this API to support post call to download the data from solar.dataglen.com

# Adding this API to support post call to download the data from solar.dataglen.com
class MultipleDevicesMultipleStreamsDownloadViewNew(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @xframe_options_exempt
    def create(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("start time and end time are required", status=status.HTTP_400_BAD_REQUEST)

            data_aggregation = request.query_params.get("data_aggregation", "FALSE")
            aggregator = request.query_params.get("aggregator", "MINUTE")
            aggregation_period = request.query_params.get("aggregation_period", 60)
            aggregation_type = request.query_params.get("aggregation_type","mean")
            report_type = request.query_params.get("report_type", "")

            if str(aggregation_type).upper() not in ["MIN","MAX","MEAN"]:
                return Response("INVALID_AGGREGATION_TYPE", status=status.HTTP_400_BAD_REQUEST)

            try:
                #sources_stream_association = dict(self.request.data._iteritems())
                #sources_stream_association = json.loads(sources_stream_association["params"])
                sources_stream_association = dict(self.request.data.iteritems())
            except Exception as exception:
                logger.debug(str(exception))
                sources_stream_association = {}

            sources_list = sources_stream_association.keys()
            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')

            sources_stream_association_transformed = transpose_dict(sources_stream_association)
            streams_list = sources_stream_association_transformed.keys()
            if str(report_type).upper() == 'ONESHEET':
                logger.debug("*********ONESHEET POST CALL********")
                dfs = {}
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name

                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"

                    try:
                        pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                  sources_stream_association_transformed[
                                                                                      stream], solar_field.name)
                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug(
                                "MultipleDevicesMultipleStreamsDownloadView found pandasdf not empty: report type onesheet")
                            try:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))

                            except:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))

                            pandasDataFrame.fillna("", inplace=True)

                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')

                            else:
                                sheetName = str(solar_field_name)

                            dfs[sheetName] = pandasDataFrame
                        else:
                            logger.debug("MultipleDevicesMultipleStreamsDownloadView found pandasdf is empty: report type onesheet")
                    except Exception as e:
                        logger.debug("exception in creating dict of dataframes in MultipleDevicesMultipleStreamsDownloadView ")
                        logger.debug(e)

                try:
                    df, l1, l2 = merge_all_sheets(dfs)
                    sheetName = "All In One Parameter+Device"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)

                    df, l1, l2 = merge_all_sheets2(dfs)
                    sheetName = "All In One Device+Parameter"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)


                except Exception as exception:
                    logger.debug(str(exception))
            else:
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name
                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"
                    try:
                        if str(data_aggregation).upper() == "TRUE":

                            pandasDataFrame = get_single_stream_multiple_sources_data_aggregated(st, et, plant,
                                                                                                 sources_stream_association_transformed[
                                                                                                     stream],
                                                                                                 solar_field.name,
                                                                                                 aggregator,
                                                                                                 aggregation_period,
                                                                                                 aggregation_type)
                        else:
                            pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                      sources_stream_association_transformed[
                                                                                          stream], solar_field.name)
                        logger.debug(pandasDataFrame.head())
                        if not pandasDataFrame.empty:
                            logger.debug("MultipleDevicesMultipleStreamsDownloadView found pandasdf >> NOT EMPTY <<")
                            try:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('Timestamp')

                            except:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('timestamp')

                            pandasDataFrame.fillna("", inplace=True)

                            d = dict()
                            for col in list(pandasDataFrame):
                                d[col] = col.replace('_', ' ')
                                pandasDataFrame[col] = pandasDataFrame[col].apply(lambda x: round(x, 3) if x else x)
                            pandasDataFrame = pandasDataFrame.rename(index=str, columns=d)
                            pandasDataFrame=pandasDataFrame[sorted_nicely(pandasDataFrame.columns)]

                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')
                                if len(sheetName) > 30:
                                    sheetName = sheetName[:28]
                                pandasDataFrame.to_excel(pandasWriter,sheet_name=sheetName)

                            else:
                                sheetName = str(solar_field_name)
                                pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))

                            pandasWriter = simpleExcelFormatting(pandasWriter, pandasDataFrame, sheetName)

                        else:
                            pandasDataFrame = pd.DataFrame()
                            pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))
                            pandasWriter = excelNoData(pandasWriter, pandasDataFrame, str(solar_field_name))
                    except Exception as exception:
                        logger.debug(str(exception))

            pandasWriter.save()

            sio.seek(0)
            workbook = sio.getvalue()
            response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
            startTime=st.strftime('%Y-%b-%d %H-%M')
            endTime=et.strftime('%Y-%b-%d %H-%M')
            if str(data_aggregation).upper() == "TRUE":
                file_name = "-".join([plant.name, 'Aggregated Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            else:
                file_name = "-".join([plant.name, 'Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            response['Content-Disposition'] = 'attachment; filename=' + file_name
            logger.debug(file_name)
            return response
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " + str(plant.slug) + str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @xframe_options_exempt
    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("start time and end time are required", status=status.HTTP_400_BAD_REQUEST)

            data_aggregation = request.query_params.get("data_aggregation", "FALSE")
            aggregator = request.query_params.get("aggregator", "MINUTE")
            aggregation_period = request.query_params.get("aggregation_period", 60)
            aggregation_type = request.query_params.get("aggregation_type", "mean")
            report_type = request.query_params.get("report_type", "onesheet")

            if str(aggregation_type).upper() not in ["MIN", "MAX", "MEAN"]:
                return Response("INVALID_AGGREGATION_TYPE", status=status.HTTP_400_BAD_REQUEST)

            sources_stream_association = self.request.query_params.get("sources_stream_association", None)
            if sources_stream_association is None:
                return Response("Please specify atleast one source and stream", status=status.HTTP_400_BAD_REQUEST)
            try:
                sources_stream_association = ast.literal_eval(sources_stream_association)
            except:
                return Response("Please specify sources streams associations properly",status=status.HTTP_400_BAD_REQUEST)

            if len(sources_stream_association) == 0:
                return Response("Please specify atleast one source and stream", status=status.HTTP_400_BAD_REQUEST)

            sources_list = sources_stream_association.keys()
            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')

            sources_stream_association_transformed = transpose_dict(sources_stream_association)
            streams_list = sources_stream_association_transformed.keys()
            if str(report_type).upper() == 'ONESHEET':
                logger.debug("***************ONESHEET GET REQUEST******************")
                dfs = {}
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name

                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"

                    try:

                        pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                  sources_stream_association_transformed[
                                                                                      stream], solar_field.name)
                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug(
                                "MultipleDevicesMultipleStreamsDownloadView: PANDASDF NOT EMPTY report type onesheet")
                            try:

                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))
                            except Exception as e:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))
                            pandasDataFrame.fillna("", inplace=True)
                            logger.debug("flagggggg")
                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')

                            else:
                                sheetName = str(solar_field_name)
                            dfs[sheetName] = pandasDataFrame

                        else:
                            logger.debug("------EMPTY DATAFRAME IN ONESHEET-------")
                    except Exception as e:
                        logger.debug("exception in creating dict of dataframes in MultipleDevicesMultipleStreamsDownloadView"+str(e))

                try:
                    df, l1, l2 = merge_all_sheets(dfs)
                    sheetName = "All In One Parameter+Device"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)

                    df, l1, l2 = merge_all_sheets2(dfs)
                    sheetName = "All In One Device+Parameter"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)

                except Exception as exception:
                    logger.debug(str(exception))
            # For report_type Normal NOT ONESHEET
            else:
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name
                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"
                    try:
                        if str(data_aggregation).upper() == "TRUE":

                            pandasDataFrame = get_single_stream_multiple_sources_data_aggregated(st, et, plant,
                                                                                                 sources_stream_association_transformed[
                                                                                                     stream],
                                                                                                 solar_field.name,
                                                                                                 aggregator,
                                                                                                 aggregation_period,
                                                                                                 aggregation_type)
                        else:
                            pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                      sources_stream_association_transformed[
                                                                                          stream], solar_field.name)
                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug("MultipleDevicesMultipleStreamsDownloadView found pandasdf not empty")
                            try:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('Timestamp')

                            except:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('timestamp')

                            pandasDataFrame.fillna("", inplace=True)

                            d = dict()
                            for col in list(pandasDataFrame):
                                d[col] = col.replace('_', ' ')
                                pandasDataFrame[col] = pandasDataFrame[col].apply(lambda x: round(x, 3) if x else x)
                            pandasDataFrame = pandasDataFrame.rename(index=str, columns=d)
                            pandasDataFrame=pandasDataFrame[sorted_nicely(pandasDataFrame.columns)]

                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')
                                if len(sheetName) > 30:
                                    sheetName = sheetName[:28]
                                pandasDataFrame.to_excel(pandasWriter, sheet_name=sheetName)

                            else:
                                sheetName = str(solar_field_name)
                                pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))

                            pandasWriter = simpleExcelFormatting(pandasWriter, pandasDataFrame, sheetName)

                        else:
                            logger.debug(solar_field.name)
                            pandasDataFrame = pandasDataFrame.set_index('Timestamp')
                            pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))
                            pandasWriter = excelNoData(pandasWriter, pandasDataFrame, str(solar_field_name))
                    except Exception as exception:
                        logger.debug(str(exception))

            pandasWriter.save()

            sio.seek(0)
            workbook = sio.getvalue()
            response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
            # if str(data_aggregation).upper() == "TRUE":
            #     file_name = "_".join([plant_slug, 'aggregated_data', str(st), str(et)]).replace(" ", "_") + ".xls"
            # else:
            #     file_name = "_".join([plant_slug, 'data', str(st), str(et)]).replace(" ", "_") + ".xls"
            startTime = st.strftime('%Y-%b-%d %H-%M')
            endTime = et.strftime('%Y-%b-%d %H-%M')
            if str(data_aggregation).upper() == "TRUE":
                file_name = "-".join([plant.name, 'Aggregated Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            else:
                file_name = "-".join([plant.name, 'Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            response['Content-Disposition'] = 'attachment; filename=' + file_name
            logger.debug(file_name)
            return response
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " + str(plant.slug) + str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# upendra mod
class MultipleDevicesMultipleStreamsDownloadView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


    @xframe_options_exempt
    def create(self, request, plant_slug=None, **kwargs):
        logger.debug("VISUALIZE DATA POST CALL")
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("start time and end time are required", status=status.HTTP_400_BAD_REQUEST)

            data_aggregation = request.query_params.get("data_aggregation", "FALSE")
            aggregator = request.query_params.get("aggregator", "MINUTE")
            aggregation_period = request.query_params.get("aggregation_period", 60)
            aggregation_type = request.query_params.get("aggregation_type", "mean")
            report_type = request.query_params.get("report_type", "")

            if str(aggregation_type).upper() not in ["MIN", "MAX", "MEAN"]:
                return Response("INVALID_AGGREGATION_TYPE", status=status.HTTP_400_BAD_REQUEST)

            try:
                sources_stream_association = dict(self.request.data._iteritems())
                sources_stream_association = json.loads(sources_stream_association["params"])
                # sources_stream_association = dict(self.request.data.iteritems())
            except Exception as exception:
                logger.debug(str(exception))
                sources_stream_association = {}

            sources_list = sources_stream_association.keys()
            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')

            sources_stream_association_transformed = transpose_dict(sources_stream_association)
            streams_list = sources_stream_association_transformed.keys()
            if str(report_type).upper() == 'ONESHEET':
                logger.debug("*********ONESHEET POST CALL********")
                dfs = {}
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name

                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"

                    try:
                        pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                  sources_stream_association_transformed[
                                                                                      stream], solar_field.name)

                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug(
                                "MultipleDevicesMultipleStreamsDownloadView found pandasdf not empty: report type onesheet")
                            try:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))

                            except:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))

                            pandasDataFrame.fillna("", inplace=True)

                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')

                            else:
                                sheetName = str(solar_field_name)

                            dfs[sheetName] = pandasDataFrame
                        else:
                            logger.debug("MultipleDevicesMultipleStreamsDownloadView found pandasdf is empty: report type onesheet")
                    except Exception as e:
                        logger.debug("exception in creating dict of dataframes in MultipleDevicesMultipleStreamsDownloadView ")
                        logger.debug(e)

                try:
                    df, l1, l2 = merge_all_sheets(dfs)
                    sheetName = "All In One Parameter+Device"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)

                    df, l1, l2 = merge_all_sheets2(dfs)
                    sheetName = "All In One Device+Parameter"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)


                except Exception as exception:
                    logger.debug(str(exception))
            else:
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name
                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"
                    try:
                        if str(data_aggregation).upper() == "TRUE":

                            pandasDataFrame = get_single_stream_multiple_sources_data_aggregated(st, et, plant,
                                                                                                 sources_stream_association_transformed[
                                                                                                     stream],
                                                                                                 solar_field.name,
                                                                                                 aggregator,
                                                                                                 aggregation_period,
                                                                                                 aggregation_type)
                        else:
                            pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                      sources_stream_association_transformed[
                                                                                          stream], solar_field.name)
                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug("MultipleDevicesMultipleStreamsDownloadView found pandasdf >> NOT EMPTY <<")
                            try:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('Timestamp')

                            except:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('timestamp')

                            pandasDataFrame.fillna("", inplace=True)

                            d = dict()
                            for col in list(pandasDataFrame):
                                d[col] = col.replace('_', ' ')
                                pandasDataFrame[col] = pandasDataFrame[col].apply(lambda x: round(x, 3) if x else x)
                            pandasDataFrame = pandasDataFrame.rename(index=str, columns=d)
                            pandasDataFrame=pandasDataFrame[sorted_nicely(pandasDataFrame.columns)]
                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')

                                pandasDataFrame.to_excel(pandasWriter,
                                                         sheet_name=str(solar_field_name + ' (' + stream_unit + ')'))

                            else:
                                sheetName = str(solar_field_name)
                                pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))

                            pandasWriter = simpleExcelFormatting(pandasWriter, pandasDataFrame, sheetName)

                        else:
                            pandasDataFrame = pandasDataFrame.set_index('Timestamp')
                            pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))
                            pandasWriter = excelNoData(pandasWriter, pandasDataFrame, str(solar_field_name))
                    except Exception as exception:
                        logger.debug(str(exception))

            pandasWriter.save()

            sio.seek(0)
            workbook = sio.getvalue()
            response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
            startTime = st.strftime('%Y-%b-%d %H-%M')
            endTime = et.strftime('%Y-%b-%d %H-%M')
            if str(data_aggregation).upper() == "TRUE":
                file_name = "-".join([plant.name, 'Aggregated Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            else:
                file_name = "-".join([plant.name, 'Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            response['Content-Disposition'] = 'attachment; filename=' + file_name
            return response
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " + str(plant.slug) + str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @xframe_options_exempt
    def list(self, request, plant_slug=None, **kwargs):
        logger.debug("VISUALIZE DATA GET CALL")
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("start time and end time are required", status=status.HTTP_400_BAD_REQUEST)

            data_aggregation = request.query_params.get("data_aggregation", "FALSE")
            aggregator = request.query_params.get("aggregator", "MINUTE")
            aggregation_period = request.query_params.get("aggregation_period", 60)
            aggregation_type = request.query_params.get("aggregation_type", "mean")
            report_type = request.query_params.get("report_type", "onesheet")

            if str(aggregation_type).upper() not in ["MIN", "MAX", "MEAN"]:
                return Response("INVALID_AGGREGATION_TYPE", status=status.HTTP_400_BAD_REQUEST)

            sources_stream_association = self.request.query_params.get("sources_stream_association", None)
            if sources_stream_association is None:
                return Response("Please specify atleast one source and stream", status=status.HTTP_400_BAD_REQUEST)
            try:
                sources_stream_association = ast.literal_eval(sources_stream_association)
            except:
                return Response("Please specify sources streams associations properly",status=status.HTTP_400_BAD_REQUEST)

            if len(sources_stream_association) == 0:
                return Response("Please specify atleast one source and stream", status=status.HTTP_400_BAD_REQUEST)

            sources_list = sources_stream_association.keys()
            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')

            sources_stream_association_transformed = transpose_dict(sources_stream_association)
            streams_list = sources_stream_association_transformed.keys()
            if str(report_type).upper() == 'ONESHEET':
                logger.debug("***************ONESHEET GET REQUEST******************")
                dfs = {}
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name

                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"

                    try:

                        pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                  sources_stream_association_transformed[
                                                                                      stream], solar_field.name)
                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug(
                                "MultipleDevicesMultipleStreamsDownloadView: PANDASDF NOT EMPTY report type onesheet")
                            try:

                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))
                            except Exception as e:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))
                            pandasDataFrame.fillna("", inplace=True)
                            logger.debug("flagggggg")
                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')

                            else:
                                sheetName = str(solar_field_name)
                            dfs[sheetName] = pandasDataFrame

                        else:
                            logger.debug("------EMPTY DATAFRAME IN ONESHEET-------")
                    except Exception as e:
                        logger.debug("exception in creating dict of dataframes in MultipleDevicesMultipleStreamsDownloadView"+str(e))

                try:
                    df, l1, l2 = merge_all_sheets(dfs)
                    sheetName = "All In One Parameter+Device"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)

                    df, l1, l2 = merge_all_sheets2(dfs)
                    sheetName = "All In One Device+Parameter"
                    df.to_excel(pandasWriter, sheetName)
                    pandasWriter = excelConversion(pandasWriter, df, l1, l2, sheetName)

                except Exception as exception:
                    logger.debug(str(exception))
            # For report_type Normal NOT ONESHEET
            else:
                for stream in streams_list:
                    try:
                        source = sources_stream_association_transformed[stream][0]
                    except:
                        return Response("Please specify atleast one source", status=status.HTTP_400_BAD_REQUEST)
                    try:
                        solar_field = SolarField.objects.get(source=source, displayName=stream)
                        solar_field_name = solar_field.displayName
                    except:
                        solar_field = SolarField.objects.get(source=source, name=stream)
                        solar_field_name = solar_field.name
                    try:
                        stream_unit = str(solar_field.streamDataUnit) if (solar_field and solar_field.streamDataUnit) else DEFAULT_STREAM_UNIT[str(solar_field.name)]
                        if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                            stream_unit = 'kWhm2'
                        if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                            stream_unit = 'kWm2'
                        if stream_unit == 'km/hr':
                            stream_unit = 'kmph'
                        if stream_unit == 'm/s':
                            stream_unit = 'mps'
                    except:
                        stream_unit = "NA"
                    try:
                        if str(data_aggregation).upper() == "TRUE":

                            pandasDataFrame = get_single_stream_multiple_sources_data_aggregated(st, et, plant,
                                                                                                 sources_stream_association_transformed[
                                                                                                     stream],
                                                                                                 solar_field.name,
                                                                                                 aggregator,
                                                                                                 aggregation_period,
                                                                                                 aggregation_type)
                        else:
                            pandasDataFrame = get_multiple_devices_single_stream_data(st, et, plant,
                                                                                      sources_stream_association_transformed[
                                                                                          stream], solar_field.name)
                        logger.debug(pandasDataFrame)
                        if not pandasDataFrame.empty:
                            logger.debug("MultipleDevicesMultipleStreamsDownloadView found pandasdf not empty")
                            try:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('Timestamp')

                            except:
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['timestamp'] = pandasDataFrame['timestamp'].apply(lambda d: d.replace(tzinfo=None))
                                pandasDataFrame = pandasDataFrame.set_index('timestamp')

                            pandasDataFrame.fillna("", inplace=True)

                            d = dict()
                            for col in list(pandasDataFrame):
                                d[col] = col.replace('_', ' ')
                                pandasDataFrame[col] = pandasDataFrame[col].apply(lambda x: round(x, 3) if x else x)
                            pandasDataFrame = pandasDataFrame.rename(index=str, columns=d)
                            pandasDataFrame=pandasDataFrame[sorted_nicely(pandasDataFrame.columns)]
                            if stream_unit != 'NA':
                                sheetName = str(solar_field_name + ' (' + stream_unit + ')')

                                pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name + ' (' + stream_unit + ')'))

                            else:
                                sheetName = str(solar_field_name)
                                pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))

                            pandasWriter = simpleExcelFormatting(pandasWriter, pandasDataFrame, sheetName)

                        else:
                            logger.debug(solar_field.name)
                            pandasDataFrame = pandasDataFrame.set_index('Timestamp')
                            pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))
                            pandasWriter = excelNoData(pandasWriter, pandasDataFrame, str(solar_field_name))
                    except Exception as exception:
                        logger.debug(str(exception))

            pandasWriter.save()

            sio.seek(0)
            workbook = sio.getvalue()
            response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
            startTime = st.strftime('%Y-%b-%d %H-%M')
            endTime = et.strftime('%Y-%b-%d %H-%M')
            if str(data_aggregation).upper() == "TRUE":
                file_name = "-".join([plant.name, 'Aggregated Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            else:
                file_name = "-".join([plant.name, 'Data', startTime,'To', endTime]).replace(' ','-').replace(',','-') + ".xls"
            response['Content-Disposition'] = 'attachment; filename=' + file_name
            return response
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " + str(plant.slug) + str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


feature_to_df_mappings = {'INVERTER_ENERGY_GENERATION': 'Inverter Total Generation (kWh)',
                          'INVERTER_POWER_GENERATION': 'Energy Values From Inverters (kWh)',
                          'TOTAL_ENERGY_GENERATION': 'Generation (kWh)',
                          'INSOLATION_GENERATION': 'Insolation (kWh/m^2)',
                          'METER_POWER_GENERATION': 'Energy Meter(kWh)',
                          'PEAK_POWER_GENERATION': 'MAX POWER',
                          'GRID_AVAILABILITY_AVAILABILITY': 'Grid Availability (%)',
                          'EQUIPMENT_AVAILABILITY_AVAILABILITY': 'Equipment Availability (%)',
                          'CONVERSION_LOSSES_LOSSES': 'Conversion Loss (kWh)',
                          'DC_LOSSES_LOSSES': 'DC Loss (kWh)', 'AC_LOSSES_LOSSES': 'AC Loss (kWh)',
                          'PR_METRICS': 'PR (%)', 'CUF_METRICS': 'CUF (%)', 'SY_METRICS': 'Specific Yield'}


# upendra mod2
class PlantExcelReport(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @xframe_options_exempt
    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug("Exception in PlantExcelReport : "+str(exception))
                plants = filter_solar_plants(context)
            plant = SolarPlant.objects.get(slug=plant_slug)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                user_features=[]
                accessible_features = []
                user_features_obj_list = RoleAccess.objects.get(role=self.request.user.role.role, dg_client=self.request.user.role.dg_client).features.all()
                for feature_obj in user_features_obj_list:
                    user_features.append(str(feature_obj))
                for feature in user_features:
                    if feature in feature_to_df_mappings:
                        accessible_features.append(feature_to_df_mappings[feature])
                logger.debug("Accessible features list :" + str(accessible_features))
            except Exception as e:
                logger.debug("Exception for RoleAccess in PlantExcelReport : "+str(e))
                accessible_features = ['Generation (kWh)', 'Inverter Total Generation (kWh)', 'PR', 'CUF',
                                       'Specific Yield', 'Insolation (kWh/m^2)']
                logger.debug("Accessible features list after Exception:" + str(accessible_features))
            try:
                tz = pytz.timezone(plant.metasource.plantmetasource.dataTimezone)
            except:
                tz = pytz.timezone("UTC")

            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')

            report_type = self.request.query_params.get("report_type", "daily")
            if str(report_type).upper() == "MONTHLY":
                try:
                    starttime = request.query_params["startTime"]
                    endtime = request.query_params["endTime"]
                    st = parser.parse(starttime)
                    et = parser.parse(endtime)

                    st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                    et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
                except:
                    return Response("startTime and endTime are required for monthly report",
                                    status=status.HTTP_400_BAD_REQUEST)
                try:

                    monthly_summary_report = get_monthly_report_values(st, et, plant, accessible_features)
                    if not monthly_summary_report.empty:
                        monthly_summary_report['Date'] = monthly_summary_report['Date'].map(lambda x: (
                            x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
                        monthly_summary_report, l1, l2 = manipulateColumnNames(monthly_summary_report, plant, 'Date')
                        monthly_summary_report.to_excel(pandasWriter, sheet_name=str(calendar.month_name[st.month]))
                        sheetName = str(calendar.month_name[st.month])
                        pandasWriter = excelConversion(pandasWriter, monthly_summary_report, l1, l2, sheetName)

                    else:
                        logger.debug("As dataframe is empty calling excelNoData plant excel report monthly")
                        # logger.debug(solar_field.name)
                        pandasDataFrame = monthly_summary_report
                        pandasDataFrame.to_excel(pandasWriter, sheet_name=str(calendar.month_name[st.month]))
                        pandasWriter = excelNoData(pandasWriter, pandasDataFrame, str(calendar.month_name[st.month]))

                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.name,'Monthly Report For', str(calendar.month_name[st.month]), str(st.year)]).replace(" ", "-").replace(',','-') + ".xls"
                    except:
                        file_name = "-".join([plant.name, 'Monthly Report']).replace(" ", "-").replace(',','-') + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except Exception as exception:
                    logger.debug("Exception in MONTHLY PlantExcelReport : "+str(exception))

            elif str(report_type).upper() == "YEARLY":
                try:
                    year = request.query_params["year"]
                except Exception as exception:
                    return Response("year is required for the yearly report", status=status.HTTP_400_BAD_REQUEST)

                # yearly details
                try:
                    year_start_date = str(year) + '-01-01'
                    year_end_date = str(year) + '-12-31'
                    year_start_date = parser.parse(year_start_date)
                    year_end_date = parser.parse(year_end_date)

                    year_start_date = update_tz(year_start_date, plant.metadata.plantmetasource.dataTimezone)
                    year_end_date = update_tz(year_end_date, plant.metadata.plantmetasource.dataTimezone)

                    yearly_summary_report = get_yearly_report_values(year_start_date, year_end_date, plant,accessible_features)
                    if not yearly_summary_report.empty:
                        yearly_summary_report['Date'] = yearly_summary_report['Date'].map(lambda x: calendar.month_name[
                            (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).month])
                        yearly_summary_report = yearly_summary_report.rename(columns={'Date': 'Month'})
                        yearly_summary_report, l1, l2 = manipulateColumnNames(yearly_summary_report, plant,dfindex='Month')
                        yearly_summary_report.to_excel(pandasWriter, sheet_name='YEAR_SUMMARY')
                        sheetName = "YEAR_SUMMARY"
                        pandasWriter = excelConversion(pandasWriter, yearly_summary_report, l1, l2, sheetName)
                        logger.debug("yearly summary reporte generated=================")

                except Exception as exception:
                    logger.debug("Exception in YEARLY PlantExcelReport : "+str(exception))

                # monthly details
                try:
                    logger.debug("Calculating yearly report with new code oct 2018")
                    st = datetime(int(year), 1, 1, 0, 0)
                    et = datetime(int(year), 12, 31, 0, 0)
                    year_start_datetime = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                    year_end_datetime = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
                    logger.debug(year_start_datetime)
                    logger.debug(year_end_datetime)
                    one_year_data_in_df = get_monthly_report_values(year_start_datetime, year_end_datetime, plant, accessible_features)

                    # one_year_data_in_df = one_year_data_in_df.reset_index()
                    one_year_data_in_df['Date'] = one_year_data_in_df['Date'].map(lambda x: (
                        x.replace(tzinfo=pytz.utc).astimezone(
                            plant.metadata.plantmetasource.dataTimezone)).date())

                    groups = one_year_data_in_df.groupby(one_year_data_in_df['Date'].map(lambda x: x.month))

                    for group in groups:
                        monthly_summary_report = group[1]
                        # monthly_summary_report = monthly_summary_report.set_index('Date')
                        month_name = str(calendar.month_name[group[0]])
                        sheetName = month_name

                        if not monthly_summary_report.empty:

                            monthly_summary_report, l1, l2 = manipulateColumnNames(monthly_summary_report, plant, 'Date')
                            monthly_summary_report.to_excel(pandasWriter, sheet_name=sheetName)
                            pandasWriter = excelConversion(pandasWriter, monthly_summary_report, l1, l2, sheetName)

                        else:
                            logger.debug("As dataframe is empty calling excelNoData plant excel report monthly")
                            # logger.debug(solar_field.name)
                            pandasDataFrame = pd.DataFrame()
                            pandasDataFrame.to_excel(pandasWriter, sheet_name=sheetName)
                            pandasWriter = excelNoData(pandasWriter, pandasDataFrame,sheetName)

                except Exception as exception:
                    logger.debug("Exception in MONTH OF YEARLY PlantExcelReport : "+str(exception))

                pandasWriter.save()
                sio.seek(0)
                workbook = sio.getvalue()
                response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                try:
                    file_name = "-".join([plant.name, 'Yearly Report For', str(year)]).replace(" ", "-").replace(',','-') + ".xls"
                except:
                    file_name = "-".join([plant.name, 'Monthly Report']).replace(" ", "-").replace(',','-') + ".xls"
                response['Content-Disposition'] = 'attachment; filename=' + file_name
                return response
            # Daily Report
            else:
                try:
                    date = request.query_params["date"]
                    # convert into datetime objects
                    date = parser.parse(date)
                    if date.tzinfo is None:
                        date = tz.localize(date)
                    date = date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
                    endtime = date.replace(hour=23, minute=23, second=23, microsecond=23)
                    sheet_spilt = request.query_params.get("sheet", "streams")
                    summary = request.query_params.get("summary", "TRUE")
                    device_type = request.query_params.get("device_type", "inverter")
                    if sheet_spilt not in ["streams", "devices"]:
                        return Response("Bad request : Invalid sheet name.", status=status.HTTP_400_BAD_REQUEST)
                except:
                    return Response("Bad request : No date specified.", status=status.HTTP_400_BAD_REQUEST)

                streams_list = []
                display_streams_list = []

                if str(device_type).upper() == 'INVERTER':
                    sources_list = plant.independent_inverter_units.all()
                    sources_name = []
                    for source in sources_list:
                        sources_name.append(str(source.name))
                    sources_name = sorted_nicely(sources_name)
                    sources_list = []
                    for name in sources_name:
                        source = IndependentInverter.objects.get(name=name, plant=plant)
                        sources_list.append(source)

                elif str(device_type).upper() == 'AJB':
                    sources_list = plant.ajb_units.all()
                    sources_name = []
                    for source in sources_list:
                        sources_name.append(str(source.name))
                    sources_name = sorted_nicely(sources_name)
                    sources_list = []
                    for name in sources_name:
                        source = AJB.objects.get(name=name, plant=plant)
                        sources_list.append(source)

                elif str(device_type).upper() == 'ENERGY_METER':
                    sources_list = plant.energy_meters.all()
                    sources_name = []
                    for source in sources_list:
                        sources_name.append(str(source.name))
                    sources_name = sorted_nicely(sources_name)
                    sources_list = []
                    for name in sources_name:
                        source = EnergyMeter.objects.get(name=name, plant=plant)
                        sources_list.append(source)

                if str(device_type).upper() == 'TRANSFORMER':
                    sources_list = plant.transformers.all()
                    sources_name = []
                    for source in sources_list:
                        sources_name.append(str(source.name))
                    sources_name = sorted_nicely(sources_name)
                    sources_list = []
                    for name in sources_name:
                        source = Transformer.objects.get(name=name, plant=plant)
                        sources_list.append(source)

                if str(device_type).upper() == 'SOLAR_METRICS':
                    sources_list = plant.solar_metrics.all()

                if str(device_type).upper() == 'WEATHER_STATION':
                    sources_list = [plant.metadata.plantmetasource]

                if str(device_type).upper() in ["INVERTER", "AJB", "ENERGY_METER", "TRANSFORMER", "SOLAR_METRICS",
                                                "WEATHER_STATION"]:
                    if len(sources_list) > 0:
                        source = sources_list[0]
                        source_streams = source.fields.all().filter(isActive=True)
                        for stream in source_streams:
                            if str(stream.name) not in EXCLUDE_REPORT_STREAMS:
                                streams_list.append(str(stream.name))
                        streams_list = sorted_nicely(streams_list)
                        source_display_streams = SolarField.objects.filter(source=source).filter(isActive=True)
                        for source_display_stream in source_display_streams:
                            try:
                                display_streams_list.append(str(source_display_stream.displayName))
                            except:
                                display_streams_list.append(str(source_display_stream.name))
                        display_streams_list = sorted_nicely(display_streams_list)
                else:
                    return Response("INVALID_DEVICE_TYPE", status=status.HTTP_400_BAD_REQUEST)

                # Summary Sheet
                if summary.upper() == "TRUE":
                    # summary_report = get_plant_summary_parameters(date, plant)
                    summary_report = get_monthly_report_values(starttime, endtime, plant,accessible_features)
                    if not summary_report.empty:
                        summary_report['Date'] = summary_report['Date'].dt.date + timedelta(days=1)

                        summary_report, l1, l2 = manipulateColumnNames(summary_report, plant, 'Date')
                        summary_report.to_excel(pandasWriter, sheet_name='PLANT_SUMMARY')
                        sheetName = 'PLANT_SUMMARY'
                        pandasWriter = excelConversion(pandasWriter, summary_report, l1, l2, sheetName)

                if sheet_spilt == 'devices':
                    for source in sources_list:
                        try:
                            pandasDataFrame = get_single_device_multiple_streams_data(starttime, endtime, plant, source,
                                                                                      display_streams_list)
                            logger.debug("sheet_split devices in PlantExcelReport df : =" + str(pandasDataFrame.head()))
                            if not pandasDataFrame.empty:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))

                                pandasDataFrame = pandasDataFrame.set_index('Timestamp')
                                pandasDataFrame.fillna("", inplace=True)
                                d = dict()
                                for col in list(pandasDataFrame):
                                    d[col] = col.replace('_', ' ')
                                    pandasDataFrame[col] = pandasDataFrame[col].apply(lambda x: round(x, 3) if x else x)
                                pandasDataFrame = pandasDataFrame.rename(index=str, columns=d)
                                sheetName = str(source.name)
                                if len(sheetName)>30:
                                    sheetName = sheetName[:28]
                                pandasDataFrame.to_excel(pandasWriter, sheet_name=sheetName)
                                pandasWriter = simpleExcelFormatting(pandasWriter, pandasDataFrame, sheetName)

                                # pandasDataFrame.to_excel(pandasWriter, sheet_name=str(source.name), index=False)
                        except Exception as exception:
                            logger.debug("Exception in if sheep_split == devices in PlantExcelReport : "+str(exception))
                            continue
                else:
                    for stream_name in streams_list:
                        try:
                            try:
                                stream = SolarField.objects.get(source=source, name=stream_name)
                                stream_sheet_name = str(stream.displayName)
                                if len(stream_sheet_name)>24:
                                    stream_sheet_name = stream_sheet_name[:24]
                            except:
                                stream = Field.objects.get(source=source, name=stream_name)
                                stream_sheet_name = str(stream.name)
                                if len(stream_sheet_name)>24:
                                    stream_sheet_name = stream_sheet_name[:24]
                            try:
                                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]

                                if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                                    stream_unit = 'kWhm2'
                                if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                                    stream_unit = 'kWm2'
                                if stream_unit == 'km/hr':
                                    stream_unit = 'kmph'
                                if stream_unit == 'm/s':
                                    stream_unit = 'mps'
                            except:
                                stream_unit = 'NA'

                            pandasDataFrame = get_multiple_inverters_single_stream_data(starttime, endtime, plant,
                                                                                        sources_list, stream_name)
                            if not pandasDataFrame.empty:
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.tz_localize('UTC').tz_convert('Asia/Kolkata'))
                                pandasDataFrame['Timestamp'] = pandasDataFrame['Timestamp'].apply(lambda d: d.replace(tzinfo=None))

                                pandasDataFrame = pandasDataFrame.set_index('Timestamp')
                                pandasDataFrame.fillna("", inplace=True)
                                d = dict()
                                for col in list(pandasDataFrame):
                                    d[col] = col.replace('_', ' ')
                                    pandasDataFrame[col] = pandasDataFrame[col].apply(lambda x: round(x, 3) if x else x)
                                pandasDataFrame = pandasDataFrame.rename(index=str, columns=d)
                                if stream_unit != 'NA':
                                    # pandasDataFrame.to_excel(pandasWriter,sheet_name=stream_sheet_name + '(' + stream_unit + ')',index=False)
                                    sheetName = stream_sheet_name + '(' + stream_unit + ')'
                                    pandasDataFrame.to_excel(pandasWriter, sheet_name=sheetName)
                                else:
                                    sheetName = stream_sheet_name
                                    pandasDataFrame.to_excel(pandasWriter, sheet_name=sheetName)

                                pandasWriter = simpleExcelFormatting(pandasWriter, pandasDataFrame, sheetName)

                        except Exception as exception:
                            logger.debug("Exception in sheet_split is not devices in PlantExcelReport : "+str(exception))
                            continue
                pandasWriter.save()

                sio.seek(0)
                workbook = sio.getvalue()
                response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                file_name = "-".join([plant.name, device_type, 'Daily Report', str(date.date())]).replace(" ","-").replace(',','-') + ".xls"
                response['Content-Disposition'] = 'attachment; filename=' + file_name
                return response
        except Exception as exception:
            logger.debug("Final Exception in PlantExcelReport : "+str(exception))


class PortfolioExcelReport(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @xframe_options_exempt
    def list(self, request, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)

            try:
                user_features=[]
                accessible_features = []
                user_features_obj_list = RoleAccess.objects.get(role=self.request.user.role.role, dg_client=self.request.user.role.dg_client).features.all()
                for feature_obj in user_features_obj_list:
                    user_features.append(str(feature_obj))
                for feature in user_features:
                    if feature in feature_to_df_mappings:
                        accessible_features.append(feature_to_df_mappings[feature])
                logger.debug("Accessible features list : " + str(accessible_features))
            except Exception as e:
                accessible_features = ['Generation (kWh)', 'Inverter Total Generation (kWh)', 'PR (%)', 'CUF (%)',
                                       'Specific Yield', 'Insolation (kWh/m^2)']
                logger.debug("Exception for RoleAccess in PortfolioExcelReport" + str(e))
                logger.debug("Accessible features list after Exception : " + str(accessible_features))

            report_type = self.request.query_params.get("report_type", "daily")

            slugs = self.request.query_params.get("slugs", "all")
            if str(slugs).upper() == "ALL":
                plants = plants
            else:
                plants = []
                try:
                    slugs = str(slugs).split(",")
                except:
                    return Response("Please specify comma separated plant slugs", status=status.HTTP_400_BAD_REQUEST)
                for slug in slugs:
                    try:
                        plant = SolarPlant.objects.get(slug=slug)
                        plants.append(plant)
                    except:
                        return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
            if not str(report_type).upper() == "DAILY":
                empty_df = pd.DataFrame()
                empty_df.to_excel(pandasWriter,sheet_name = "OnePageSummary")

            if str(report_type).upper() == "MONTHLY":
                try:
                    starttime = request.query_params["startTime"]
                    endtime = request.query_params["endTime"]
                    st = parser.parse(starttime)
                    et = parser.parse(endtime)
                except:
                    return Response("startTime and endTime are required for monthly report",
                                    status=status.HTTP_400_BAD_REQUEST)

                plant_name = []
                total_gen = []
                total_inv_gen = []
                total_insolation = []
                avg_pr = []
                avg_cuf = []
                total_sy = []
                total_dc_loss = []
                total_conv_loss = []
                total_ac_loss = []

                for plant in plants:
                    try:
                        st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                        et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
                    except:
                        return Response("startTime and endTime are required for monthly report",
                                        status=status.HTTP_400_BAD_REQUEST)

                    try:
                        monthly_summary_report = get_monthly_report_values(st, et, plant,accessible_features)
                        if not monthly_summary_report.empty:
                            sheetName = str(plant.name)
                            plant_name.append(sheetName)

                            total_gen.append(monthly_summary_report['Generation (kWh)'].sum())
                            total_inv_gen.append(monthly_summary_report['Inverter Total Generation (kWh)'].sum())
                            total_insolation.append(monthly_summary_report['Insolation (kWh/m^2)'].sum())
                            avg_pr.append(monthly_summary_report['PR (%)'].mean())
                            avg_cuf.append(monthly_summary_report['CUF (%)'].mean())
                            total_sy.append(monthly_summary_report['Specific Yield'].sum())
                            #total_dc_loss.append(monthly_summary_report['DC Loss (kWh)'].sum())
                            #total_conv_loss.append(monthly_summary_report['Conversion Loss (kWh)'].sum())
                            #total_ac_loss.append(monthly_summary_report['AC Loss (kWh)'].sum())

                            monthly_summary_report['Date'] = monthly_summary_report['Date'].map(lambda x: (
                                x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())

                            monthly_summary_report, l1, l2 = manipulateColumnNames(monthly_summary_report, plant,'Date')
                            if len(sheetName)>30:
                                sheetName = sheetName[:28]

                            monthly_summary_report.to_excel(pandasWriter, sheetName)
                            pandasWriter = excelConversion(pandasWriter, monthly_summary_report, l1, l2, sheetName)
                    except Exception as exception:
                        logger.debug(str(exception))

                one_page_summary = {"Plant Name":plant_name,
                                    "Generation (kWh)": total_gen,
                                   "Inverter Total Generation (kWh)": total_inv_gen,
                                    "Insolation (kWh/m^2)": total_insolation,
                                   "PR": avg_pr,
                                   "CUF": avg_cuf,
                                   "Specific Yield": total_sy}

                one_page_summary_df = pd.DataFrame(one_page_summary)
                one_page_summary_df = one_page_summary_df[["Plant Name","Generation (kWh)","Inverter Total Generation (kWh)", \
                                                           "Insolation (kWh/m^2)", "PR","CUF","Specific Yield"]]
                one_page_summary_df, l1, l2 = manipulateColumnNames(df = one_page_summary_df, dfindex= 'Plant Name')
                sheetName = 'OnePageSummary'
                if len(sheetName) > 30:
                    sheetName = sheetName[:28]
                one_page_summary_df.to_excel(pandasWriter, sheetName)
                pandasWriter = excelConversion(pandasWriter, one_page_summary_df, l1, l2, sheetName)

                try:
                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.groupClient.name, 'Monthly-Portfolio-Report-For', str(calendar.month_name[st.month]), str(st.year)]).replace(" ", "-") + ".xls"
                    except:
                        file_name = "-".join([plant.groupClient.name,'Monthly-Portfolio-Report']).replace(" ", "-") + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except:
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            elif str(report_type).upper() == "DAILY":
                try:
                    plant = plants[0]
                except:
                    return Response("Please pass atleast one valid plant slug")
                try:
                    tz = pytz.timezone(plant.metasource.plantmetasource.dataTimezone)
                except:
                    tz = pytz.timezone("UTC")
                try:
                    date = request.query_params["date"]
                    # convert into datetime objects
                    date = parser.parse(date)
                    if date.tzinfo is None:
                        date = tz.localize(date)
                except:
                    return Response("Date is required for daily report", status=status.HTTP_400_BAD_REQUEST)

                date = date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                daily_summary_report = get_daily_report_values_portfolio(plants, date)
                daily_summary_report, l1, l2 = manipulateColumnNames2(daily_summary_report, 'Plant Name')
                sheetName = 'PLANT_SUMMARY'
                daily_summary_report.to_excel(pandasWriter, sheet_name='PLANT_SUMMARY')
                pandasWriter = excelConversion(pandasWriter, daily_summary_report, l1, l2, sheetName)

                # daily_summary_report.to_excel(pandasWriter, sheet_name='PLANT_SUMMARY', index=False)
                try:
                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.groupClient.name,'Daily-Portfolio-Report', str(date.date())]).replace(" ", "-") + ".xls"
                    except:
                        file_name = "-".join([plant.groupClient.name,'Daily-Portfolio-Report']).replace(" ", "-") + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except:
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            elif str(report_type).upper() == "YEARLY":
                try:
                    year = request.query_params["year"]
                except Exception as exception:
                    return Response("year is required for the yearly report", status=status.HTTP_400_BAD_REQUEST)
                plant_name = []
                total_gen = []
                total_insolation = []
                avg_pr = []
                avg_cuf = []
                total_dc_loss = []
                total_conv_loss = []
                total_ac_loss = []
                for plant in plants:
                    # yearly details
                    try:
                        year_start_date = str(year) + '-01-01'
                        year_end_date = str(year) + '-12-31'
                        year_start_date = parser.parse(year_start_date)
                        year_end_date = parser.parse(year_end_date)

                        year_start_date = update_tz(year_start_date, plant.metadata.plantmetasource.dataTimezone)
                        year_end_date = update_tz(year_end_date, plant.metadata.plantmetasource.dataTimezone)

                        yearly_summary_report = get_yearly_report_values(year_start_date, year_end_date, plant,accessible_features)
                        if not yearly_summary_report.empty:
                            sheetName = str(plant.name)

                            plant_name.append(sheetName)
                            total_gen.append(yearly_summary_report['Generation (kWh)'].sum())
                            total_insolation.append(yearly_summary_report['Insolation (kWh/m^2)'].sum())
                            avg_pr.append(yearly_summary_report['PR'].mean())
                            avg_cuf.append(yearly_summary_report['CUF'].mean())
                            total_dc_loss.append(yearly_summary_report['DC Loss (kWh)'].sum())
                            total_conv_loss.append(yearly_summary_report['Conversion Loss (kWh)'].sum())
                            total_ac_loss.append(yearly_summary_report['AC Loss (kWh)'].sum())
                            yearly_summary_report['Date'] = yearly_summary_report['Date'].map(
                                lambda x: calendar.month_name[(x.replace(tzinfo=pytz.utc).astimezone(
                                    plant.metadata.plantmetasource.dataTimezone)).month])
                            yearly_summary_report = yearly_summary_report.rename(columns={'Date': 'Month'})

                            yearly_summary_report, l1, l2 = manipulateColumnNames(yearly_summary_report, plant, 'Month')
                            if len(sheetName)>30:
                                sheetName = sheetName[:28]
                            yearly_summary_report.to_excel(pandasWriter, sheet_name=sheetName)
                            pandasWriter = excelConversion(pandasWriter, yearly_summary_report, l1, l2, sheetName)
                    except Exception as exception:
                        logger.debug(str(exception))

                one_page_summary = {"Plant Name": plant_name,
                                    "Generation (kWh)": total_gen,
                                    "Insolation (kWh/m^2)": total_insolation,
                                    "PR": avg_pr,
                                    "CUF": avg_cuf,
                                    "DC Loss (kWh)": total_dc_loss,
                                    "Conversion Loss (kWh)": total_conv_loss,
                                    "AC Loss (kWh)": total_ac_loss}

                one_page_summary_df = pd.DataFrame(one_page_summary)
                one_page_summary_df = one_page_summary_df[
                    ["Plant Name", "Generation (kWh)","Insolation (kWh/m^2)",
                     "PR", "CUF", "DC Loss (kWh)", "Conversion Loss (kWh)", \
                     "AC Loss (kWh)"]]
                one_page_summary_df, l1, l2 = manipulateColumnNames(df=one_page_summary_df, dfindex='Plant Name')
                sheetName = 'OnePageSummary'
                if len(sheetName) > 30:
                    sheetName = sheetName[:28]
                one_page_summary_df.to_excel(pandasWriter, sheetName)
                pandasWriter = excelConversion(pandasWriter, one_page_summary_df, l1, l2, sheetName)

                try:
                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.groupClient.name, 'Yearly Portfolio Report For',str(year)]).replace(" ","-") + ".xls"
                    except:
                        file_name = "-".join('Yearly Portfolio Report For',[str(year)]).replace(" ", "-") + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except:
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

        except Exception as exception:
            logger.debug("Exception in PortfolioExcelReport : " + str(exception))


    @xframe_options_exempt
    def create(self, request, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)

            try:
                user_features=[]
                accessible_features = []
                user_features_obj_list = RoleAccess.objects.get(role=self.request.user.role.role, dg_client=self.request.user.role.dg_client).features.all()
                for feature_obj in user_features_obj_list:
                    user_features.append(str(feature_obj))
                for feature in user_features:
                    if feature in feature_to_df_mappings:
                        accessible_features.append(feature_to_df_mappings[feature])
                logger.debug("Accessible features list : " + str(accessible_features))
            except Exception as e:
                logger.debug("Exception for RoleAccess in PortfolioExcelReport" + str(e))
                accessible_features = ['Generation (kWh)', 'Inverter Total Generation (kWh)', 'PR', 'CUF',
                                       'Specific Yield', 'Insolation (kWh/m^2)']
                logger.debug("Accessible features list after Exception : " + str(accessible_features))

            report_type = self.request.query_params.get("report_type", "daily")

            slugs = self.request.data

            if str(slugs).upper() == "ALL":
                plants = plants
            else:
                plants = []
                # try:
                #     slugs = str(slugs).split(",")
                # except:
                #     return Response("Please specify comma separated plant slugs", status=status.HTTP_400_BAD_REQUEST)
                for slug in slugs:
                    try:
                        plant = SolarPlant.objects.get(slug=slug)
                        plants.append(plant)
                    except:
                        return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            sio = StringIO.StringIO()
            pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
            if not str(report_type).upper() == "DAILY":
                empty_df = pd.DataFrame()
                empty_df.to_excel(pandasWriter,sheet_name = "OnePageSummary")

            if str(report_type).upper() == "MONTHLY":
                try:
                    starttime = request.query_params["startTime"]
                    endtime = request.query_params["endTime"]
                    st = parser.parse(starttime)
                    et = parser.parse(endtime)
                except:
                    return Response("startTime and endTime are required for monthly report",
                                    status=status.HTTP_400_BAD_REQUEST)

                plant_name = []
                total_gen = []
                total_inv_gen = []
                total_insolation = []
                avg_pr = []
                avg_cuf = []
                total_sy = []
                total_dc_loss = []
                total_conv_loss = []
                total_ac_loss = []

                for plant in plants:
                    try:
                        st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                        et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
                    except:
                        return Response("startTime and endTime are required for monthly report",
                                        status=status.HTTP_400_BAD_REQUEST)

                    try:
                        monthly_summary_report = get_monthly_report_values(st, et, plant,accessible_features)
                        if not monthly_summary_report.empty:
                            sheetName = str(plant.name)
                            plant_name.append(sheetName)

                            total_gen.append(monthly_summary_report['Generation (kWh)'].sum())
                            total_inv_gen.append(monthly_summary_report['Inverter Total Generation (kWh)'].sum())
                            total_insolation.append(monthly_summary_report['Insolation (kWh/m^2)'].sum())
                            avg_pr.append(monthly_summary_report['PR'].mean())
                            avg_cuf.append(monthly_summary_report['CUF'].mean())
                            total_sy.append(monthly_summary_report['Specific Yield'].sum())
                            total_dc_loss.append(monthly_summary_report['DC Loss (kWh)'].sum())
                            total_conv_loss.append(monthly_summary_report['Conversion Loss (kWh)'].sum())
                            total_ac_loss.append(monthly_summary_report['AC Loss (kWh)'].sum())

                            monthly_summary_report['Date'] = monthly_summary_report['Date'].map(lambda x: (
                                x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())

                            monthly_summary_report, l1, l2 = manipulateColumnNames(monthly_summary_report, plant,'Date')
                            if len(sheetName)>30:
                                sheetName = sheetName[:28]

                            monthly_summary_report.to_excel(pandasWriter, sheetName)
                            pandasWriter = excelConversion(pandasWriter, monthly_summary_report, l1, l2, sheetName)
                    except Exception as exception:
                        logger.debug(str(exception))
                            # monthly_summary_report.to_excel(pandasWriter, sheet_name=str(plant.name), index=False)
                one_page_summary = {"Plant Name":plant_name,
                                    "Generation (kWh)": total_gen,
                                   "Inverter Total Generation (kWh)": total_inv_gen,
                                    "Insolation (kWh/m^2)": total_insolation,
                                   "PR": avg_pr,
                                   "CUF": avg_cuf,
                                   "Specific Yield": total_sy,
                                   "DC Loss (kWh)": total_dc_loss,
                                   "Conversion Loss (kWh)": total_conv_loss,
                                   "AC Loss (kWh)":total_ac_loss }

                one_page_summary_df = pd.DataFrame(one_page_summary)
                one_page_summary_df = one_page_summary_df[["Plant Name","Generation (kWh)","Inverter Total Generation (kWh)", \
                                                           "Insolation (kWh/m^2)", "PR","CUF","Specific Yield","DC Loss (kWh)",\
                                                           "Conversion Loss (kWh)","AC Loss (kWh)"]]
                one_page_summary_df, l1, l2 = manipulateColumnNames(df = one_page_summary_df, dfindex= 'Plant Name')
                sheetName = 'OnePageSummary'
                if len(sheetName) > 30:
                    sheetName = sheetName[:28]
                one_page_summary_df.to_excel(pandasWriter, sheetName)
                pandasWriter = excelConversion(pandasWriter, one_page_summary_df, l1, l2, sheetName)

                try:
                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.groupClient.name, 'Monthly-Portfolio-Report-For', str(calendar.month_name[st.month]), str(st.year)]).replace(" ", "-") + ".xls"
                    except:
                        file_name = "-".join([plant.groupClient.name,'Monthly-Portfolio-Report']).replace(" ", "-") + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except:
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            elif str(report_type).upper() == "DAILY":
                try:
                    plant = plants[0]
                except:
                    return Response("Please pass atleast one valid plant slug")
                try:
                    tz = pytz.timezone(plant.metasource.plantmetasource.dataTimezone)
                except:
                    tz = pytz.timezone("UTC")
                try:
                    date = request.query_params["date"]
                    # convert into datetime objects
                    date = parser.parse(date)
                    if date.tzinfo is None:
                        date = tz.localize(date)
                except:
                    return Response("Date is required for daily report", status=status.HTTP_400_BAD_REQUEST)

                date = date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                daily_summary_report = get_daily_report_values_portfolio(plants, date)
                daily_summary_report, l1, l2 = manipulateColumnNames2(daily_summary_report, 'Plant Name')
                sheetName = 'PLANT_SUMMARY'
                daily_summary_report.to_excel(pandasWriter, sheet_name='PLANT_SUMMARY')
                pandasWriter = excelConversion(pandasWriter, daily_summary_report, l1, l2, sheetName)

                # daily_summary_report.to_excel(pandasWriter, sheet_name='PLANT_SUMMARY', index=False)
                try:
                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.groupClient.name,'Daily-Portfolio-Report', str(date.date())]).replace(" ", "-") + ".xls"
                    except:
                        file_name = "-".join([plant.groupClient.name,'Daily-Portfolio-Report']).replace(" ", "-") + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except:
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

            elif str(report_type).upper() == "YEARLY":
                try:
                    year = request.query_params["year"]
                except Exception as exception:
                    return Response("year is required for the yearly report", status=status.HTTP_400_BAD_REQUEST)
                plant_name = []
                total_gen = []
                total_insolation = []
                avg_pr = []
                avg_cuf = []
                total_dc_loss = []
                total_conv_loss = []
                total_ac_loss = []
                for plant in plants:
                    # yearly details
                    try:
                        year_start_date = str(year) + '-01-01'
                        year_end_date = str(year) + '-12-31'
                        year_start_date = parser.parse(year_start_date)
                        year_end_date = parser.parse(year_end_date)

                        year_start_date = update_tz(year_start_date, plant.metadata.plantmetasource.dataTimezone)
                        year_end_date = update_tz(year_end_date, plant.metadata.plantmetasource.dataTimezone)

                        yearly_summary_report = get_yearly_report_values(year_start_date, year_end_date, plant,accessible_features)
                        if not yearly_summary_report.empty:
                            sheetName = str(plant.name)

                            plant_name.append(sheetName)
                            total_gen.append(yearly_summary_report['Generation (kWh)'].sum())
                            total_insolation.append(yearly_summary_report['Insolation (kWh/m^2)'].sum())
                            avg_pr.append(yearly_summary_report['PR'].mean())
                            avg_cuf.append(yearly_summary_report['CUF'].mean())
                            total_dc_loss.append(yearly_summary_report['DC Loss (kWh)'].sum())
                            total_conv_loss.append(yearly_summary_report['Conversion Loss (kWh)'].sum())
                            total_ac_loss.append(yearly_summary_report['AC Loss (kWh)'].sum())
                            yearly_summary_report['Date'] = yearly_summary_report['Date'].map(
                                lambda x: calendar.month_name[(x.replace(tzinfo=pytz.utc).astimezone(
                                    plant.metadata.plantmetasource.dataTimezone)).month])
                            yearly_summary_report = yearly_summary_report.rename(columns={'Date': 'Month'})

                            yearly_summary_report, l1, l2 = manipulateColumnNames(yearly_summary_report, plant, 'Month')
                            if len(sheetName)>30:
                                sheetName = sheetName[:28]
                            yearly_summary_report.to_excel(pandasWriter, sheet_name=sheetName)
                            pandasWriter = excelConversion(pandasWriter, yearly_summary_report, l1, l2, sheetName)
                    except Exception as exception:
                        logger.debug(str(exception))

                one_page_summary = {"Plant Name": plant_name,
                                    "Generation (kWh)": total_gen,
                                    "Insolation (kWh/m^2)": total_insolation,
                                    "PR": avg_pr,
                                    "CUF": avg_cuf,
                                    "DC Loss (kWh)": total_dc_loss,
                                    "Conversion Loss (kWh)": total_conv_loss,
                                    "AC Loss (kWh)": total_ac_loss}

                one_page_summary_df = pd.DataFrame(one_page_summary)
                one_page_summary_df = one_page_summary_df[
                    ["Plant Name", "Generation (kWh)","Insolation (kWh/m^2)",
                     "PR", "CUF", "DC Loss (kWh)", "Conversion Loss (kWh)", \
                     "AC Loss (kWh)"]]
                one_page_summary_df, l1, l2 = manipulateColumnNames(df=one_page_summary_df, dfindex='Plant Name')
                sheetName = 'OnePageSummary'
                if len(sheetName) > 30:
                    sheetName = sheetName[:28]
                one_page_summary_df.to_excel(pandasWriter, sheetName)
                pandasWriter = excelConversion(pandasWriter, one_page_summary_df, l1, l2, sheetName)

                try:
                    pandasWriter.save()
                    sio.seek(0)
                    workbook = sio.getvalue()
                    response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
                    try:
                        file_name = "-".join([plant.groupClient.name, 'Yearly Portfolio Report For',str(year)]).replace(" ","-") + ".xls"
                    except:
                        file_name = "-".join('Yearly Portfolio Report For',[str(year)]).replace(" ", "-") + ".xls"
                    response['Content-Disposition'] = 'attachment; filename=' + file_name
                    return response
                except:
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

        except Exception as exception:
            logger.debug("Exception in PortfolioExcelReport : " + str(exception))

def get_prediction_dump(identifier_type=None, plant_slug=None, period=60, modelNames=None, streamNames=None, startTime=None, endTime=None):
    try:
        df_final = pd.DataFrame(columns={'timestamp_type','count_time_period','identifier','stream_name',
                                        'model_name','ts','value','upper_bound','lower_bound','updated_at'})
        timestamp_type = []
        count_time_period = []
        identifier = []
        stream_name = []
        model_name = []
        ts = []
        value = []
        upper_bound = []
        lower_bound = []
        updated_at = []
        time_period = int(period)*60
        if identifier_type != None and plant_slug != None:
            if startTime is not None and endTime is not None:
                if len(modelNames) != len(streamNames):
                    return df_final
                else:
                    for i in range(len(modelNames)):
                        df_temp = pd.DataFrame(columns={'timestamp_type','count_time_period','identifier','stream_name',
                                        'model_name','ts','value','upper_bound','lower_bound','updated_at'})
                        timestamp_type = []
                        count_time_period = []
                        identifier = []
                        stream_name = []
                        model_name = []
                        ts = []
                        value = []
                        upper_bound = []
                        lower_bound = []
                        updated_at = []
                        #df_temp = pd.DataFrame([])
                        prediction_data = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                           count_time_period=time_period,
                                                                           identifier_type=identifier_type,
                                                                           plant_slug=plant_slug,
                                                                           identifier = plant_slug,
                                                                           stream_name = streamNames[i],
                                                                           model_name = modelNames[i],
                                                                           ts__gte=startTime,
                                                                           ts__lte=endTime).limit(0).values_list('timestamp_type','count_time_period','identifier','stream_name',
                                                                                                                'model_name','ts','value','upper_bound','lower_bound','updated_at')
                        for datapoint in prediction_data:
                            timestamp_type.append(str(datapoint[0]))
                            count_time_period.append(int(datapoint[1]))
                            identifier.append(str(datapoint[2]))
                            stream_name.append(str(datapoint[3]))
                            model_name.append(str(datapoint[4]))
                            ts.append(pd.to_datetime(datapoint[5]))
                            value.append(float(datapoint[6]))
                            upper_bound.append(float(datapoint[7]))
                            lower_bound.append(float(datapoint[8]))
                            updated_at.append(pd.to_datetime(datapoint[9]))
                        df_temp['timestamp_type'] = timestamp_type
                        df_temp['count_time_period'] = count_time_period
                        df_temp['identifier'] = identifier
                        df_temp['stream_name'] = stream_name
                        df_temp['model_name'] = model_name
                        df_temp['ts'] = ts
                        df_temp['value'] = value
                        df_temp['upper_bound'] = upper_bound
                        df_temp['lower_bound'] = lower_bound
                        df_temp['updated_at'] = updated_at
                        df_final = df_final.append(df_temp)
                    return df_final
            else:
                prediction_data = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                   count_time_period=time_period,
                                                                   identifier_type=identifier_type,
                                                                   plant_slug=plant_slug).limit(0).values_list('timestamp_type','count_time_period','identifier','stream_name',
                                                                                                            'model_name','ts','value','upper_bound','lower_bound','updated_at')
        elif identifier_type != None:
            if startTime is not None and endTime is not None:
                prediction_data = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                   count_time_period=time_period,
                                                                   identifier_type=identifier_type,
                                                                   ts__gte=startTime,
                                                                   ts__lte=endTime).limit(0).values_list('timestamp_type','count_time_period','identifier','stream_name',
                                                                                    'model_name','ts','value','upper_bound','lower_bound','updated_at')
            else:
                prediction_data = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                   count_time_period=time_period,
                                                                   identifier_type=identifier_type).limit(0).values_list('timestamp_type','count_time_period','identifier','stream_name',
                                                                                    'model_name','ts','value','upper_bound','lower_bound','updated_at')
        else:
            prediction_data = PredictionData.objects.all().limit(0).values_list('timestamp_type','count_time_period','identifier','stream_name',
                                                                                'model_name','ts','value','upper_bound','lower_bound','updated_at')
        for datapoint in prediction_data:
            timestamp_type.append(str(datapoint[0]))
            count_time_period.append(int(datapoint[1]))
            identifier.append(str(datapoint[2]))
            stream_name.append(str(datapoint[3]))
            model_name.append(str(datapoint[4]))
            ts.append(pd.to_datetime(datapoint[5]))
            value.append(float(datapoint[6]))
            upper_bound.append(float(datapoint[7]))
            lower_bound.append(float(datapoint[8]))
            updated_at.append(pd.to_datetime(datapoint[9]))
        df_final['timestamp_type'] = timestamp_type
        df_final['count_time_period'] = count_time_period
        df_final['identifier'] = identifier
        df_final['stream_name'] = stream_name
        df_final['model_name'] = model_name
        df_final['ts'] = ts
        df_final['value'] = value
        df_final['upper_bound'] = upper_bound
        df_final['lower_bound'] = lower_bound
        df_final['updated_at'] = updated_at
        return df_final
    except Exception as exception:
        logger.debug(str(exception))

class EnergyPredictionView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            # if plant not in plants:
            #     return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            identifier_type = self.request.query_params.get('identifier_type', None)
            plant_slug = self.request.query_params.get('plant_slug', None)
            period = self.request.query_params.get("period",60)
            startTime = self.request.query_params.get("startTime", None)
            endTime = self.request.query_params.get("endTime", None)
            if startTime is not None and endTime is not None:
                try:
                    startTime = parser.parse(startTime)
                    endTime = parser.parse(endTime)
                except:
                    return Response("Please specify start and end time in proper formats.", status=status.HTTP_400_BAD_REQUEST)
                modelNames = self.request.query_params.get("modelNames", None)
                streamNames = self.request.query_params.get("streamNames", None)
                if modelNames is None:
                    return Response("Please specify comma separated model names", status=status.HTTP_400_BAD_REQUEST)
                if streamNames is None:
                    return Response("Please specify comma separated stream names", status=status.HTTP_400_BAD_REQUEST)
                modelNames = modelNames.split(",")
                streamNames = streamNames.split(",")
                if len(modelNames) != len(streamNames):
                    return Response("Please specify equal number of model and stream names")

            logger.debug(identifier_type)
            logger.debug(plant_slug)

            file_name = "energy_prediction_dump.csv"
            response_csv = HttpResponse(content_type="text/csv")
            response_csv['Content-Disposition'] = 'attachment; filename=' + file_name
            writer = csv.writer(response_csv)
            if startTime is not None and endTime is not None:
                response_data = get_prediction_dump(identifier_type, plant_slug,period,modelNames, streamNames, startTime, endTime)
            else:
                response_data = get_prediction_dump(identifier_type, plant_slug,period)
            response = response_data.to_csv(date_format="%Y-%m-%dT%H:%M:%S",
                                          index=False)
            for line in response.split("\n"):
                writer.writerow(line.split(","))
            return response_csv

        except Exception as exception:
            logger.debug("Error in getting energy prediction dump : " +str(plant.slug)+ str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_cleaning_dump():
    try:
        df_final = pd.DataFrame(columns={'timestamp_type','count_time_period','identifier','stream_name',
                                        'ts','actual_value','model_name','predicted_value','residual', 'updated_at'})
        timestamp_type = []
        count_time_period = []
        identifier = []
        stream_name = []
        ts = []
        actual_value = []
        model_name = []
        predicted_value = []
        residual = []
        updated_at = []
        prediction_data = PredictedValues.objects.all().limit(0).values_list('timestamp_type','count_time_period','identifier','stream_name',
                                                                            'ts','actual_value','model_name','predicted_value','residual', 'updated_at')
        for datapoint in prediction_data:
            try:
                timestamp_type.append(str(datapoint[0]))
                count_time_period.append(int(datapoint[1]))
                identifier.append(str(datapoint[2]))
                stream_name.append(str(datapoint[3]))
                ts.append(str(datapoint[4]))
                actual_value.append(float(datapoint[5])) if datapoint[5] is not None else actual_value.append(None)
                model_name.append(str(datapoint[6]))
                predicted_value.append(float(datapoint[7])) if datapoint[7] is not None else predicted_value.append(None)
                residual.append(float(datapoint[8])) if datapoint[8] is not None else residual.append(None)
                updated_at.append(pd.to_datetime(datapoint[9]))
            except:
                continue
        df_final['timestamp_type'] = timestamp_type
        df_final['count_time_period'] = count_time_period
        df_final['identifier'] = identifier
        df_final['stream_name'] = stream_name
        df_final['ts'] = ts
        df_final['predicted_value'] = predicted_value
        df_final['actual_value'] = actual_value
        df_final['residual'] = residual
        df_final['model_name'] = model_name
        df_final['updated_at'] = updated_at
        return df_final
    except Exception as exception:
        logger.debug(str(exception))

class CleaningDumpView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            file_name = "cleaning_dump.csv"
            response_csv = HttpResponse(content_type="text/csv")
            response_csv['Content-Disposition'] = 'attachment; filename=' + file_name
            writer = csv.writer(response_csv)
            response_data = get_cleaning_dump()
            logger.debug(response_data)
            response = response_data.to_csv(date_format="%Y-%m-%dT%H:%M:%S",
                                          index=False)
            for line in response.split("\n"):
                writer.writerow(line.split(","))
            return response_csv

        except Exception as exception:
            logger.debug("Error in getting cleaning dump : " +str(plant.slug)+ str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlantKPIValues(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            payload = request.data
            if "timestamp_type" and "count_time_period" and "identifier" and "kpi_type" and "kpi_value" not in payload.keys():
                return Response("Please specify timestamp_type, count_time_period, identifier, kpi_type and kpi_value in the request payload", status=status.HTTP_400_BAD_REQUEST)
            if "timestamp" in payload.keys():
                timestamp = parser.parse(payload['timestamp'])
                ts = update_tz(timestamp, "UTC")
            else:
                ts = timezone.now()

            if str(payload['kpi_type']).upper() == 'PR':
                try:
                    pr_entry = PerformanceRatioTable.objects.create(timestamp_type=str(payload['timestamp_type']),
                                                                    count_time_period=int(payload['count_time_period']),
                                                                    identifier=str(payload['identifier']),
                                                                    ts=ts,
                                                                    performance_ratio=float(payload['kpi_value']),
                                                                    updated_at=timezone.now())
                    pr_entry.save()
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("count_time_period should be integer and kpi_value should be float", status=status.HTTP_400_BAD_REQUEST)
            elif str(payload['kpi_type']).upper() == 'CUF':
                try:
                    cuf_entry = CUFTable.objects.create(timestamp_type=str(payload['timestamp_type']),
                                                        count_time_period=int(payload['count_time_period']),
                                                        identifier=str(payload['identifier']),
                                                        ts=ts,
                                                        CUF=float(payload['kpi_value']),
                                                        updated_at=timezone.now())
                    cuf_entry.save()
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("count_time_period should be integer and kpi_value should be float", status=status.HTTP_400_BAD_REQUEST)
            elif str(payload['kpi_type']).upper() == 'SPECIFIC_YIELD':
                try:
                    specific_yield_entry = SpecificYieldTable.objects.create(timestamp_type=str(payload['timestamp_type']),
                                                                             count_time_period=int(payload['count_time_period']),
                                                                             identifier=str(payload['identifier']),
                                                                             ts=ts,
                                                                             specific_yield=float(payload['kpi_value']),
                                                                             updated_at=timezone.now())
                    specific_yield_entry.save()
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("count_time_period should be integer and kpi_value should be float", status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("Please specify correct kpi_type(PR/CUF/SPECIFIC_YIELD)", status=status.HTTP_400_BAD_REQUEST)

            return Response("KPI entry successful", status=status.HTTP_201_CREATED)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            startTime = self.request.query_params.get("startTime", None)
            endTime = self.request.query_params.get("endTime", None)
            if startTime is None or endTime is None:
                return Response("Please specify start time and end time", status=status.HTTP_400_BAD_REQUEST)

            if startTime is not None and endTime is not None:
                try:
                    startTime = parser.parse(startTime)
                    endTime = parser.parse(endTime)
                except:
                    return Response("Please specify start and end time in proper formats.", status=status.HTTP_400_BAD_REQUEST)
            try:
                st = update_tz(startTime, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(endTime, plant.metadata.plantmetasource.dataTimezone)
            except:
                st = startTime
                et = endTime

            aggregator = self.request.query_params.get("aggregator","DAY")
            if aggregator == "MONTH":
                count_time_period = 2419200
            else:
                count_time_period = 86400

            valid_kpi = ['INSOLATION','PR','CUF','SPECIFIC_YIELD','ENERGY']
            kpis=self.request.query_params.get("kpis", None)
            if kpis is None:
                kpis = valid_kpi
            else:
                try:
                    kpis = str(kpis).split(",")
                except:
                    return Response("Please specify comma separated kpi names", status=status.HTTP_400_BAD_REQUEST)

            for kpi in kpis:
                if kpi not in valid_kpi:
                    return Response("Please specify valid kpi names", status=status.HTTP_400_BAD_REQUEST)

            final_result_df = pd.DataFrame()

            values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                        count_time_period=count_time_period,
                                                        identifier=str(plant.slug),
                                                        ts__gte=st,
                                                        ts__lte=et)
            PR = []
            CUF = []
            SPECIFIC_YIELD = []
            INSOLATION = []
            ENERGY = []
            TIMESTAMP = []
            for value in values:
                TIMESTAMP.append(value.ts)
                PR.append(value.performance_ratio)
                SPECIFIC_YIELD.append(value.specific_yield)
                INSOLATION.append(value.average_irradiation)
                CUF.append(value.cuf)
                ENERGY.append(value.generation)
            final_result_df["timestamp"] = TIMESTAMP
            if "PR" in kpis:
                final_result_df["performance_ratio"] = PR
            if "CUF" in kpis:
                final_result_df["cuf"] = CUF
            if "INSOLATION" in kpis:
                final_result_df["insolation"] = INSOLATION
            if "ENERGY" in kpis:
                final_result_df["energy"] = ENERGY
            if "SPECIFIC_YIELD" in kpis:
                final_result_df["specific_yield"] = SPECIFIC_YIELD
            result = final_result_df.to_json(orient='records', date_format='iso')
            return Response(json.loads(result), status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

valid_event_types = ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED','INVERTERS_DISCONNECTED','AJBS_DISCONNECTED',
                     'INVERTERS_NOT_GENERATING','INVERTERS_ALARMS','PANEL_CLEANING','INVERTERS_UNDERPERFORMING',
                     'MPPT_UNDERPERFORMING','AJB_UNDERPERFORMING']
device_types = ["INVERTERS", "AJBS", "ENERGY_METERS","GATEWAYS","VIRTUAL_GATEWAYS","MPPTS"]
class DeviceTicketDetails(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                starttime = request.query_params["startTime"]
                endtime = request.query_params["endTime"]
                st = parser.parse(starttime)
                et = parser.parse(endtime)

                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("Please specify startTime and endTime", status=status.HTTP_400_BAD_REQUEST)

            device_type = self.request.query_params.get("device_type", "INVERTERS")
            event_types = self.request.query_params.get("event_types", None)
            if str(device_type).upper() not in device_types:
                return Response("INVALID_DEVICE_TYPE", status=status.HTTP_400_BAD_REQUEST)
            if event_types is not None:
                try:
                    event_types = str(event_types).split(",")
                except:
                    return Response("Please provide comma separated event types", status=status.HTTP_400_BAD_REQUEST)
                for event_type in event_types:
                    if str(event_type).upper() not in valid_event_types:
                        return Response("Please provide valid event types", status=status.HTTP_400_BAD_REQUEST)
            if str(device_type).upper() == "ENERGY_METERS":
                devices = plant.energy_meters.all()
            elif str(device_type).upper() == "AJBS":
                devices = plant.ajb_units.all()
            elif str(device_type).upper() == "GATEWAYS":
                devices = plant.gateway.all()
            elif str(device_type).upper() == "VIRTUAL_GATEWAYS":
                plant.virtual_gateway_units.all()
            else:
                devices = plant.independent_inverter_units.all()

            final_values = []
            for device in devices:
                ticket_details = Ticket.get_device_ticket_history(plant, st, et, device.sourceKey, event_types)
                for detail in ticket_details:
                    ticket_detail = {}
                    ticket_detail['association_event_type'] = detail['association_event_type']
                    ticket_detail['association_identifier_name'] = detail['association_identifier_name']
                    ticket_detail['association_created'] = detail['association_created']
                    ticket_detail['association_closed'] = detail['association_closed']
                    ticket_detail['association_duration_seconds'] = detail['association_duration_seconds']
                    final_values.append(ticket_detail)
            return Response(final_values, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import collections
class IdentifierTicketDetails(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                starttime = request.query_params["startTime"]
                endtime = request.query_params["endTime"]
                st = parser.parse(starttime)
                et = parser.parse(endtime)

                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("Please specify startTime and endTime", status=status.HTTP_400_BAD_REQUEST)

            device_type = self.request.query_params.get("device_type", "INVERTERS")
            event_type = self.request.query_params.get("event_type", None)
            if str(device_type).upper() not in device_types:
                return Response("INVALID_DEVICE_TYPE", status=status.HTTP_400_BAD_REQUEST)
            if event_type is not None and event_type not in valid_event_types:
                return Response("Please provide valid event types", status=status.HTTP_400_BAD_REQUEST)
            if str(device_type).upper() == "ENERGY_METERS":
                devices = plant.energy_meters.all()
            elif str(device_type).upper() == "AJBS":
                devices = plant.ajb_units.all()
            elif str(device_type).upper() == "GATEWAYS":
                gateway_devices = plant.gateway.all()
                virtual_gateway_devices = plant.virtual_gateway_units.all()
                devices = []
                devices.extend(gateway_devices)
                devices.extend(virtual_gateway_devices)
            elif str(device_type).upper() == "VIRTUAL_GATEWAYS":
                gateway_devices = plant.gateway.all()
                virtual_gateway_devices = plant.virtual_gateway_units.all()
                devices = []
                devices.extend(gateway_devices)
                devices.extend(virtual_gateway_devices)
            elif str(device_type).upper() == "MPPTS":
                devices = plant.independent_inverter_units.all()
            else:
                devices = plant.independent_inverter_units.all()
            final_values = []
            if str(event_type) == 'INVERTERS_DISCONNECTED' or \
                str(event_type) == 'AJBS_DISCONNECTED':
                    for device in devices:
                        ticket_details = Ticket.get_device_ticket_history(plant, st, et, device.sourceKey, [event_type])
                        for detail in ticket_details:
                            association_detail = collections.OrderedDict()
                            association_detail['Device Name'] = detail['association_identifier_name']
                            association_detail['Start Time'] = str(detail['association_created'])
                            association_detail['End Time'] = str(detail['association_closed'])
                            association_detail['Event Duration (seconds)'] = detail['association_duration_seconds']
                            association_detail['Active'] = detail['association_active_status']
                            association_detail['Ticket Id'] = int(detail['association_ticket_id'])
                            final_values.append(association_detail)
            elif str(event_type) == 'GATEWAY_DISCONNECTED' or \
                 str(event_type) == 'GATEWAY_POWER_OFF':
                    event_type = "GATEWAY_DISCONNECTED,GATEWAY_POWER_OFF"
                    for device in devices:
                        ticket_details = Ticket.get_device_ticket_history(plant, st, et, device.sourceKey, str(event_type).split(","))
                        for detail in ticket_details:
                            association_detail = collections.OrderedDict()
                            association_detail['Event Type'] = detail['association_event_type']
                            association_detail['Device Name'] = detail['association_identifier_name']
                            association_detail['Start Time'] = str(detail['association_created'])
                            association_detail['End Time'] = str(detail['association_closed'])
                            association_detail['Event Duration (seconds)'] = detail['association_duration_seconds']
                            association_detail['Active'] = detail['association_active_status']
                            association_detail['Ticket Id'] = int(detail['association_ticket_id'])
                            final_values.append(association_detail)
            elif str(event_type) == 'INVERTERS_ALARMS':
                for device in devices:
                    associations = Ticket.get_identifier_history(plant, st, et, str(device.sourceKey), [event_type])
                    for association in associations:
                        for solar_status in association['association_alarms']:
                            for alarm in association['association_alarms'][solar_status]:
                                try:
                                    status_desc = str(InverterStatusMappings.objects.get(plant=plant, status_code=float(alarm['device_status'])).status_description)
                                except:
                                    status_desc = alarm['device_status']
                                association_detail = collections.OrderedDict()
                                # association_detail['association_event_type'] = association['association_event_type']
                                association_detail['Device Name'] = association['association_identifier_name']
                                association_detail['Start Time'] = str(update_tz(alarm['alarm_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['End Time'] = str(update_tz(alarm['alarm_closed'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['Duration (sec.)'] = alarm['alarm_duration_seconds']
                                association_detail['Operating Status'] = status_desc
                                association_detail['Alarm Code'] = alarm['alarm_code']
                                association_detail['Active'] = alarm['alarm_active_status']
                                association_detail['Ticket Id'] = int(association['association_ticket_id'])
                                final_values.append(association_detail)
            elif str(event_type) == 'INVERTERS_UNDERPERFORMING':
                for device in devices:
                    associations = Ticket.get_identifier_history(plant, st, et, str(device.sourceKey), [event_type])
                    for association in associations:
                        for inverter_name in association['association_performance_issues']:
                            for performance_issue in association['association_performance_issues'][inverter_name]:
                                association_detail = collections.OrderedDict()
                                # association_detail['association_event_type'] = association['association_event_type']
                                association_detail['Device Name'] = association['association_identifier_name']
                                association_detail['Start Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['End Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None) + timedelta(hours=1))
                                association_detail['Device Generation'] = round(float(performance_issue['actual_energy']),2) if performance_issue['actual_energy'] else performance_issue['actual_energy']
                                association_detail['Mean Generation'] = round(float(performance_issue['mean_energy']),2) if performance_issue['mean_energy'] else performance_issue['mean_energy']
                                association_detail['Generation Difference'] = round(float(performance_issue['delta_energy']),2) if performance_issue['delta_energy'] else performance_issue['delta_energy']
                                association_detail['Ticket Id'] = int(association['association_ticket_id'])
                                final_values.append(association_detail)
            elif str(event_type) == 'PANEL_CLEANING':
                for device in devices:
                    associations = Ticket.get_identifier_history(plant, st, et, str(device.sourceKey), [event_type])
                    for association in associations:
                        for inverter_name in association['association_performance_issues']:
                            for performance_issue in association['association_performance_issues'][inverter_name]:
                                association_detail = collections.OrderedDict()
                                # association_detail['association_event_type'] = association['association_event_type']
                                association_detail['Device Name'] = association['association_identifier_name']
                                association_detail['Start Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['End Time'] = str(update_tz(performance_issue['performance_issue_closed'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['Residual'] = round(float(performance_issue['residual']),2) if performance_issue['residual'] else performance_issue['residual']
                                association_detail['Ticket Id'] = int(association['association_ticket_id'])
                                final_values.append(association_detail)
            elif str(event_type) == 'MPPT_UNDERPERFORMING':
                for device in devices:
                    associations = Ticket.get_identifier_history(plant, st, et, str(device.sourceKey), [event_type])
                    for association in associations:
                        for mppt_name in association['association_performance_issues']:
                            for performance_issue in association['association_performance_issues'][mppt_name]:
                                association_detail = collections.OrderedDict()
                                # association_detail['association_event_type'] = association['association_event_type']
                                association_detail['Device Name'] = association['association_identifier_name']
                                association_detail['Start Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['End Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None) + timedelta(hours=1))
                                association_detail['Device Power'] = round(float(performance_issue['actual_power']),2) if performance_issue['actual_power'] else performance_issue['actual_power']
                                association_detail['Mean Power'] = round(float(performance_issue['mean_power']),2) if performance_issue['mean_power'] else performance_issue['mean_power']
                                association_detail['Power Difference'] = round(float(performance_issue['delta_power']),2) if performance_issue['delta_power'] else performance_issue['delta_power']
                                association_detail['Ticket Id'] = int(association['association_ticket_id'])
                                final_values.append(association_detail)
            elif str(event_type) == 'AJB_UNDERPERFORMING':
                for device in devices:
                    associations = Ticket.get_identifier_history(plant, st, et, str(device.sourceKey), [event_type])
                    for association in associations:
                        for ajb_name in association['association_performance_issues']:
                            for performance_issue in association['association_performance_issues'][ajb_name]:
                                association_detail = collections.OrderedDict()
                                # association_detail['association_event_type'] = association['association_event_type']
                                association_detail['Device Name'] = association['association_identifier_name']
                                association_detail['Start Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                association_detail['End Time'] = str(update_tz(performance_issue['performance_issue_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None) + timedelta(hours=1))
                                association_detail['Device Current'] = round(float(performance_issue['actual_current']),2) if performance_issue['actual_current'] else performance_issue['actual_current']
                                association_detail['Mean Current'] = round(float(performance_issue['mean_current']),2) if performance_issue['mean_current'] else performance_issue['mean_current']
                                association_detail['Current Difference'] = round(float(performance_issue['delta_current']),2) if performance_issue['delta_current'] else performance_issue['delta_current']
                                association_detail['Ticket Id'] = int(association['association_ticket_id'])
                                final_values.append(association_detail)
            return Response(final_values, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("SERVER_ERROR_IN_ALARMS_LIST_API" + str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API to get the summary of list of plant slugs for a given date range

class PlantsSummaryDateRange(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, **kwargs):
        try:
            final_result = {}
            slugs = self.request.query_params.get("slugs",None)
            if slugs==None:
                slugs=[]
                context = self.get_profile_data(**kwargs)
                plants = filter_solar_plants(context)
                try:
                    user_role = self.request.user.role.role
                    user_client = self.request.user.role.dg_client
                    if str(user_role) == 'CEO':
                        plants = SolarPlant.objects.filter(groupClient=user_client)
                except Exception as exception:
                    logger.debug(str(exception))
                    plants = filter_solar_plants(context)
                for plant in plants:
                    slugs.append(str(plant.slug))
            else:
                try:
                    slugs = slugs.split(',')
                except:
                    return Response("Please specify comma separated slugs", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(slugs)
            for slug_name in slugs:
                try:
                    plant = SolarPlant.objects.get(slug=str(slug_name))
                except:
                    return Response("Invalid plant slug : " + str(slug_name), status=status.HTTP_400_BAD_REQUEST)

            startTime = self.request.query_params.get("startTime", None)
            endTime = self.request.query_params.get("endTime", None)

            logger.debug(startTime)
            logger.debug(endTime)

            if startTime is None or endTime is None:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = parser.parse(startTime).replace(hour=0,minute=0,second=0,microsecond=0)
                et = parser.parse(endTime).replace(hour=0,minute=0,second=0,microsecond=0)
            except:
                return Response("Please provide valid start and end time")

            grouping = self.request.query_params.get("grouping", "parameter")
            try:
                tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            except:
                tz = "Asia/Kolkata"

            if str(grouping).upper() == "DATE":
                for slug in slugs:
                    plant = SolarPlant.objects.get(slug=slug)
                    if st.tzinfo is None:
                        st = tz.localize(st)
                        et = tz.localize(et)
                        st = st.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        et = et.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    final_result[str(plant.slug)] = get_new_plant_summary_specific_date(st, et, plant)
            elif str(grouping).upper() == "PARAMETER":
                for slug in slugs:
                    plant = SolarPlant.objects.get(slug=slug)
                    if st.tzinfo is None:
                        st = tz.localize(st)
                        et = tz.localize(et)
                        st = st.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        et = et.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    final_result[str(plant.slug)] = get_new_plant_summary_specific_date_range(st, et, plant)
            else:
                pass
            return Response(final_result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class for Weather Api data
class V1_WeatherDataViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    WEATHER_DATA_CHOICE = (WeatherData.HOURLY, WeatherData.DAILY)
    WEATHER_PREDICTION_CHOICE = (WeatherData.CURRENT, WeatherData.FUTURE)
    WEATHER_SOURCE_CHOICE = ("darksky", "world-weather", 'solcast')

    def list(self, request, plant_slug=None, **kwargs):
        try:
            logger.debug("inside weather data class")
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
                timestamp_type = request.query_params["ts"]
                prediction_type = request.query_params.get("pd", WeatherData.CURRENT)
                source = request.query_params.get("source", "world-weather")
            except:
                return Response("Please provide start and end time and timestamp, prediction_type, source",
                                status=status.HTTP_400_BAD_REQUEST)

            if source not in V1_WeatherDataViewSet.WEATHER_SOURCE_CHOICE:
                return Response("Please provide a valid source", status=status.HTTP_400_BAD_REQUEST)

            if timestamp_type not in V1_WeatherDataViewSet.WEATHER_DATA_CHOICE:
                return Response("Please provide a valid timestamp", status=status.HTTP_400_BAD_REQUEST)

            if prediction_type not in V1_WeatherDataViewSet.WEATHER_PREDICTION_CHOICE:
                return Response("Please provide a valid prediction", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = dateutil.parser.parse(st)
                et = dateutil.parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("Please provide a valid start and end time", status=status.HTTP_400_BAD_REQUEST)

            weather_data_values = get_daily_or_hourly_weather_data(plant, st, et, timestamp_type, prediction_type,
                                                                   source)
            return Response(data=weather_data_values, status=status.HTTP_200_OK)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#Api view to post prediction data from source and save
class V1_NewPredictionDataViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, plant_slug=None, **kwargs):
        """

        :param request: request parameter including post and data
        :param plant_slug: plan_slug from solarplant
        :param kwargs:
        :return:
        """
        model_name_values = ('STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL_VALUE', 'ACTUAL', 'LSTM')
        timestamp_types_values = (value for key, value in settings.TIMESTAMP_TYPES.__dict__.items()
                                             if not key.startswith('__') and not callable(key))
        count_time_period_values = (value for key, value in settings.DATA_COUNT_PERIODS.__dict__.items()
                                             if not key.startswith('__') and not callable(key))
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            post_data = request.data
            if "timestamp_type" and "count_time_period" and "identifier_type" and "identifier"\
                    and "model_name" and "ts" not in post_data:
                return Response("Please specify timestamp_type, count_time_period, identifier_type,\
                 model_name, ts in the request payload",\
                                status=status.HTTP_400_BAD_REQUEST)

            if post_data['ts']:
                try:
                    ts = parser.parse(post_data['ts'])
                    ts = update_tz(ts, "UTC")
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("Please provide valid timestamp", status=status.HTTP_400_BAD_REQUEST)
            else:
                ts = timezone.now()

            if post_data['timestamp_type'] not in timestamp_types_values:
                return Response("Please provide valid timestamp_type", status=status.HTTP_400_BAD_REQUEST)

            if int(post_data['count_time_period']) not in count_time_period_values:
                return Response("Please provide valid count_time_period", status=status.HTTP_400_BAD_REQUEST)

            if post_data['identifier_type'] not in ('plant', 'source'):
                return Response("Please provide valid identifier_type", status=status.HTTP_400_BAD_REQUEST)

            if post_data['model_name'] not in model_name_values:
                return Response("Please provide valid model_name", status=status.HTTP_400_BAD_REQUEST)
            try:
                NewPredictionData.objects.create(timestamp_type="%s" %post_data['timestamp_type'],
                                                 count_time_period=int(post_data['count_time_period']),
                                                 identifier_type="%s" %post_data['identifier_type'],
                                                 plant_slug="%s" %plant.slug,
                                                 identifier="%s" %post_data['identifier'],
                                                 stream_name="%s" %post_data['identifier'],
                                                 model_name="%s" %post_data['model_name'], ts=ts,
                                                 value=float(post_data['value']),
                                                 upper_bound=float(post_data['upper_bound']),
                                                 lower_bound=float(post_data['lower_bound']),
                                                 updated_at=timezone.now())
            except Exception as exception:
                logger.debug(str(exception))
                return Response("value, upper_bound, lower_bound should be float", status=status.HTTP_400_BAD_REQUEST)
            return Response("NewPredictionData entry created successful", status=status.HTTP_201_CREATED)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
            except:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)
            try:
                st = parser.parse(st)
                et = parser.parse(et)
            except:
                return Response("please specify start and end time in correct format", status=status.HTTP_400_BAD_REQUEST)

            interval = self.request.query_params.get("interval", '15')
            split = self.request.query_params.get("split","FALSE")
            glm = self.request.query_params.get("glm","FALSE")
            final_result = {}
            if interval == '15':
                count_time_period = int(interval)*60
            elif interval == '60':
                count_time_period = int(interval)*60
            else:
                return Response("Invalid interval", status=status.HTTP_400_BAD_REQUEST)

            if split.upper() == "TRUE":
                split = True
            else:
                split = False
            if str(glm).upper() == "TRUE":
                model_list = ['GLM_MODEL']
            else:
                model_list = ['STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL']
            for model_name in model_list:
                final_result[model_name] = json.loads(get_predicted_energy_values_timeseries(st, et, plant, model_name, count_time_period, split))

            return Response(data={"PREDICTION_TIMESERIES" : final_result}, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class V1_Insolation_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)

            aggregator = request.query_params.get("aggregator","D")
            aggregation_period = request.query_params.get("period","1")

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
            except:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)
            try:
                st = parser.parse(st)
                et = parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("please specify start and end time in correct format", status=status.HTTP_400_BAD_REQUEST)

            result = get_aggregated_insolation_values(st, et, plant, aggregator, aggregation_period)
            return Response(data=result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvertersEnergyFromPowerDaterange(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, **kwargs):
        try:
            final_result = {}
            slugs = self.request.query_params.get("slugs",None)
            if slugs==None:
                slugs=[]
                context = self.get_profile_data(**kwargs)
                plants = filter_solar_plants(context)
                try:
                    user_role = self.request.user.role.role
                    user_client = self.request.user.role.dg_client
                    if str(user_role) == 'CEO':
                        plants = SolarPlant.objects.filter(groupClient=user_client)
                except Exception as exception:
                    logger.debug(str(exception))
                    plants = filter_solar_plants(context)
                for plant in plants:
                    slugs.append(str(plant.slug))
            else:
                try:
                    slugs = slugs.split(',')
                except:
                    return Response("Please specify comma separated slugs", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(slugs)
            for slug_name in slugs:
                try:
                    plant = SolarPlant.objects.get(slug=str(slug_name))
                except:
                    return Response("Invalid plant slug : " + str(slug_name), status=status.HTTP_400_BAD_REQUEST)

            startTime = self.request.query_params.get("startTime", None)
            endTime = self.request.query_params.get("endTime", None)

            logger.debug(startTime)
            logger.debug(endTime)

            if startTime is None or endTime is None:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)

            try:
                st = parser.parse(startTime).replace(hour=0,minute=0,second=0,microsecond=0)
                et = parser.parse(endTime).replace(hour=0,minute=0,second=0,microsecond=0)
            except:
                return Response("Please provide valid start and end time")

            try:
                tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            except:
                tz = "Asia/Kolkata"

            for slug in slugs:
                try:
                    plant = SolarPlant.objects.get(slug=slug)
                    if st.tzinfo is None:
                        st = tz.localize(st)
                        et = tz.localize(et)
                        st = st.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        et = et.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    final_result[str(plant.slug)] = get_inverters_stored_energy_from_power(st, et, plant)
                except:
                    continue
            return Response(final_result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcrossPlantsInverters(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, **kwargs):
        try:
            final_result = {}
            slugs = self.request.query_params.get("slugs",None)
            if slugs==None:
                slugs=[]
                context = self.get_profile_data(**kwargs)
                plants = filter_solar_plants(context)
                try:
                    user_role = self.request.user.role.role
                    user_client = self.request.user.role.dg_client
                    if str(user_role) == 'CEO':
                        plants = SolarPlant.objects.filter(groupClient=user_client)
                except Exception as exception:
                    logger.debug(str(exception))
                plants = filter_solar_plants(context)
                for plant in plants:
                    slugs.append(str(plant.slug))
            else:
                try:
                    slugs = slugs.split(',')
                except:
                    return Response("Please specify comma separated slugs", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(slugs)
            for slug_name in slugs:
                try:
                    plants_values = []
                    plant = SolarPlant.objects.get(slug=str(slug_name))
                    inverters = plant.independent_inverter_units.all()
                    for inverter in inverters:
                        inverter_values = {}
                        inverter_values["name"] = str(inverter.name)
                        inverter_values["sourceKey"] = str(inverter.sourceKey)
                        inverter_values["manufacturer"] = str(inverter.manufacturer)
                        inverter_values["dataReportingInterval"] = str(inverter.dataReportingInterval)
                        inverter_values["sourceMacAddress"] = str(inverter.sourceMacAddress)
                        inverter_values["isActive"] = str(inverter.isActive)
                        inverter_values["isMonitored"] = str(inverter.isMonitored)
                        inverter_values["timeoutInterval"] = str(inverter.timeoutInterval)
                        inverter_values["dataTimezone"] = str(inverter.dataTimezone)
                        inverter_values["orientation"] = str(inverter.orientation)
                        inverter_values["total_capacity"] = str(inverter.total_capacity)
                        inverter_values["actual_capacity"] = str(inverter.actual_capacity)
                        plants_values.append(inverter_values)
                    final_result[str(plant.slug)] = plants_values
                except:
                    return Response("Invalid plant slug : " + str(slug_name), status=status.HTTP_400_BAD_REQUEST)
            return Response(data=final_result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PlantPdfReport(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        from solarrms.views import PDFReportSummary
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            st = request.query_params["st"]
            st_copy = st
            if len(st_copy.split("-")) == 2:
                st_copy = "01-%s" %(st_copy)
            try:
                st_copy = datetime.strptime(st_copy, "%d-%m-%Y")
            except Exception as exception:
                return Response("Invalid input given", status=status.HTTP_400_BAD_REQUEST)
            pdfs = PDFReportSummary()
            file_name = pdfs.get_pdf_content(st, plant)
            with open('%s' %file_name, 'rb') as pdf:
                file_name=file_name.split('/')[-1]
                response = HttpResponse(pdf.read(), content_type='application/force-download')
                response['Content-Disposition'] = 'inline;filename=%s' %(file_name)
                return response
        except Exception as exception:
            logger.debug(str(exception))
        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class V1_DSM_Charge_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
            except:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)

            actual = self.request.query_params.get("actual", "FALSE")
            if str(actual).upper()=="FALSE":
                actual = False
            elif str(actual).upper()=="TRUE":
                actual=True
            else:
                actual = False
            try:
                st = parser.parse(st)
                et = parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("please specify start and end time in correct format", status=status.HTTP_400_BAD_REQUEST)

            result = calculate_penalty(st, et, plant, actual)
            return Response(data=result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class V1_DSM_Charge_Missing_Data_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                st = request.query_params["startTime"]
                et = request.query_params["endTime"]
            except:
                return Response("Please provide start and end time", status=status.HTTP_400_BAD_REQUEST)
            try:
                st = parser.parse(st)
                et = parser.parse(et)
                st = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                et = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("please specify start and end time in correct format", status=status.HTTP_400_BAD_REQUEST)

            result = get_grid_down_time_dsm(st, et, plant)
            return Response(data=result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# please don't extend code further, write to api_view_v2.py
