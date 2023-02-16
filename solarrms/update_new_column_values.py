import datetime
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.models import SolarPlant, PlantCompleteValues, HistoricEnergyValues, PerformanceRatioTable, CUFTable,\
    PlantDownTime, EnergyLossTable, PlantSummaryDetails, KWHPerMeterSquare, SpecificYieldTable, AggregatedPlantParameters
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import calculate_pr, calculate_CUF, get_down_time,calculate_total_plant_generation, \
    get_energy_meter_values, get_aggregated_energy, get_plant_power
from helpdesk.dg_functions import update_ticket, get_plant_tickets
from monitoring.views import get_user_data_monitoring_status
import collections
from dashboards.models import DataglenClient, Dashboard
#from solarrms.api_views import fix_generation_units
import pandas as pd
import copy

start_date = "2016-01-01 00:00:00"

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

def fix_generation_units(generation):
    if generation > 1000000.0:
        return "{0:.1f} GWh".format(generation/1000000.0)
    if generation > 1000.0:
        return "{0:.1f} MWh".format(generation/1000.0)
    else:
        return "{0:.1f} kWh".format(generation)

def compute_values_for_new_columns():
    try:
        try:
            dashboard = Dashboard.objects.get(slug='solar')
        except Exception as exception:
            print("Solar Dashboard not found " + str(exception))
        clients = DataglenClient.objects.filter(clientDashboard=dashboard)
        #clients = DataglenClient.objects.filter(slug='renew-power')
        for client in clients:
            print("computing for client : " + str(client.name))
            plants = SolarPlant.objects.filter(groupClient=client)
            for plant in plants:
                print ("computing for plant " + str(plant.slug))
                if plant.isOperational and plant.metadata.plantmetasource:
                    try:
                        current_time = timezone.now()
                        current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    except Exception as exc:
                        print("Error in converting the timezone" + str(exc))

                    last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        print(last_entry)

                    duration = (current_time - last_entry)
                    duration_days = duration.days
                    print duration_days
                    loop_count = 0
                    last_entry_daily = last_entry
                    while loop_count <= duration_days:
                        initial_time = last_entry_daily.replace(hour=0, minute=0, second= 0, microsecond=0)
                        final_time = last_entry_daily.replace(hour=23, minute=59, second=59, microsecond=59)
                        month_start_day = initial_time.replace(day=1)
                        month_end_day = final_time

                        # get the average irradiation values
                        aggregated_values = AggregatedPlantParameters.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                     count_time_period=86400,
                                                                                     identifier=str(plant.slug),
                                                                                     ts__gte=initial_time,
                                                                                     ts__lte=final_time)

                        # monthly average irradiation values
                        monthly_aggregated_values = AggregatedPlantParameters.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                             count_time_period=86400,
                                                                                             identifier=str(plant.slug),
                                                                                             ts__gte=month_start_day,
                                                                                             ts__lte=month_end_day)

                        # calculate average module temperature of the month
                        try:
                            sum_module_temperature = 0.0
                            count_module_temperature = 0
                            for value in monthly_aggregated_values:
                                if float(value.average_module_temperature)>0.0:
                                    sum_module_temperature += float(value.average_module_temperature)
                                    count_module_temperature += 1
                            monthly_module_temperature = float(sum_module_temperature)/float(count_module_temperature)
                        except Exception as exception:
                            print("Error in getting the average module temperature of the month : " + str(exception))
                            monthly_module_temperature = None
                            pass

                        # calculate average ambient temperature of the month
                        try:
                            sum_ambient_temperature = 0.0
                            count_ambient_temperature = 0
                            for value in monthly_aggregated_values:
                                if float(value.average_ambient_temperature)>0.0:
                                    sum_ambient_temperature += float(value.average_ambient_temperature)
                                    count_ambient_temperature += 1
                            monthly_ambient_temperature = float(sum_ambient_temperature)/float(count_ambient_temperature)
                        except Exception as exception:
                            print("Error in getting the average ambient temperature of the month : " + str(exception))
                            monthly_ambient_temperature = None
                            pass

                        # calculate average wind speed of the month
                        try:
                            sum_wind_speed = 0.0
                            count_wind_speed = 0
                            for value in monthly_aggregated_values:
                                if float(value.average_windspeed)>0.0:
                                    sum_wind_speed += float(value.average_windspeed)
                                    count_wind_speed += 1
                            monthly_wind_speed = float(sum_wind_speed)/float(count_wind_speed)
                        except Exception as exception:
                            print("Error in getting the average wind speed of the month : " + str(exception))
                            monthly_wind_speed = None
                            pass

                        try:
                            daily_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                  identifier=plant.slug,
                                                                                  ts=aggregated_values[0].ts)
                            daily_summary_entry.update(average_module_temperature=aggregated_values[0].average_module_temperature,
                                                       average_ambient_temperature=aggregated_values[0].average_ambient_temperature,
                                                       average_wind_speed=aggregated_values[0].average_windspeed)
                        except:
                            pass

                        # store the monthly values

                        try:
                            monthly_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                    identifier=plant.slug,
                                                                                    ts=month_start_day)
                            monthly_summary_entry.update(average_module_temperature=monthly_module_temperature,
                                                         average_ambient_temperature=monthly_ambient_temperature,
                                                         average_wind_speed=monthly_wind_speed)
                        except:
                            pass

                        last_entry_daily = last_entry_daily + datetime.timedelta(days=1)
                        duration_days -= 1
                        print duration_days

    except Exception as exception:
        print(str(exception))