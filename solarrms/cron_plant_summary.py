import datetime
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.models import SolarPlant, PlantCompleteValues, HistoricEnergyValues, PerformanceRatioTable, CUFTable,\
    PlantDownTime, EnergyLossTable, PlantSummaryDetails, KWHPerMeterSquare, SpecificYieldTable,\
    AggregatedPlantParameters, EnergyLossTableNew, MaxValuesTable
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import calculate_pr, calculate_CUF, get_down_time,calculate_total_plant_generation, \
    get_energy_meter_values, get_aggregated_energy, get_plant_power, get_minutes_aggregated_energy, convert_new_energy_data_format_to_old_format
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

def compute_plant_summary_details():
    try:
        try:
            dashboard = Dashboard.objects.get(slug='solar')
        except Exception as exception:
            print("Solar Dashboard not found " + str(exception))
        clients = DataglenClient.objects.filter(clientDashboard=dashboard)
        #clients = DataglenClient.objects.filter(slug='sri-power')
        for client in clients:
            print("computing for client : " + str(client.name))
            plants = SolarPlant.objects.filter(groupClient=client)
            for plant in plants:
                try:
                    print ("computing for plant " + str(plant.slug))
                    if plant.isOperational and plant.metadata.plantmetasource:
                        try:
                            current_time = timezone.now()
                            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        except Exception as exc:
                            print("Error in converting the timezone" + str(exc))

                        plant_summary_last_entry = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                      identifier=plant.slug).limit(1).values_list('ts')

                        if plant_summary_last_entry:
                            last_entry_values = [item[0] for item in plant_summary_last_entry]
                            last_entry = last_entry_values[0]
                            if last_entry.tzinfo is None:
                                last_entry = pytz.utc.localize(last_entry)
                                last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                                print(last_entry)
                        else:
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
                        while loop_count < duration_days:
                            initial_time = last_entry_daily.replace(hour=0, minute=0, second= 0, microsecond=0)
                            final_time = last_entry_daily.replace(hour=23, minute=59, second=59, microsecond=59)
                            month_start_day = initial_time.replace(day=1)
                            month_end_day = final_time

                            # get daily energy values
                            try:
                                historical_energy_values = HistoricEnergyValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                               count_time_period=86400,
                                                                                               identifier=str(plant.slug),
                                                                                               ts__gte=initial_time,
                                                                                               ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting historical energy values : " + str(exception))

                            # get monthly energy values
                            try:
                                monthly_historical_energy_values = HistoricEnergyValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                       count_time_period=86400,
                                                                                                       identifier=str(plant.slug),
                                                                                                       ts__gte=month_start_day,
                                                                                                       ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting historical energy values : " + str(exception))

                            # calculate total energy of the month
                            try:
                                total_monthly_energy_value = 0.0
                                for monthly_energy_value in monthly_historical_energy_values:
                                    total_monthly_energy_value += float(monthly_energy_value.energy)
                            except Exception as exception:
                                print("Error in calculating the total energy of the month : " + str(exception))
                                pass

                            # get daily PR
                            try:
                                performance_ratio_values = PerformanceRatioTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                count_time_period=86400,
                                                                                                identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                                ts__gte=initial_time,
                                                                                                ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting pr values: " + str(exception))

                            # get monthly PR
                            try:
                                monthly_performance_ratio_values = PerformanceRatioTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                        count_time_period=86400,
                                                                                                        identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                                        ts__gte=month_start_day,
                                                                                                        ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting pr values: " + str(exception))

                            # calculate average pr of the month
                            try:
                                sum_pr = 0.0
                                count_pr = 0
                                for monthly_pr_value in monthly_performance_ratio_values:
                                    if float(monthly_pr_value.performance_ratio)>0.0:
                                        sum_pr += float(monthly_pr_value.performance_ratio)
                                        count_pr += 1
                                monthly_pr = float(sum_pr)/float(count_pr)
                            except Exception as exception:
                                print("Error in getting the average pr of the month : " + str(exception))
                                monthly_pr = 0.0
                                pass

                            # daily cuf values
                            try:
                                cuf_values = CUFTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                     ts__gte=initial_time,
                                                                     ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting the cuf values : " + str(exception))

                            #monthly cuf values
                            try:
                                monthly_cuf_values = CUFTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                     ts__gte=month_start_day,
                                                                     ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting the cuf values : " + str(exception))

                            # calculate average cuf of the month
                            try:
                                sum_cuf = 0.0
                                count_cuf = 0
                                for monthly_cuf_value in monthly_cuf_values:
                                    if float(monthly_cuf_value.CUF)>0.0:
                                        sum_cuf += float(monthly_cuf_value.CUF)
                                        count_cuf += 1
                                monthly_cuf = float(sum_cuf)/float(count_cuf)
                            except Exception as exception:
                                print("Error in getting the average cuf of the month : " + str(exception))
                                monthly_cuf = 0.0
                                pass

                            # daily specific yield values
                            try:
                                specific_yield_value = SpecificYieldTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                   count_time_period=86400,
                                                                                   identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                   ts__gte=initial_time,
                                                                                   ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting the specific yield values : " + str(exception))

                            #monthly specific yield values
                            try:
                                monthly_specific_yield = SpecificYieldTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                           count_time_period=86400,
                                                                                           identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                           ts__gte=month_start_day,
                                                                                           ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting the specific yield values : " + str(exception))


                            # calculate specific yield values per month
                            try:
                                sum_specific_yield_per_month = 0.0
                                for monthly_yield_value in monthly_specific_yield:
                                    if float(monthly_yield_value.specific_yield)>0.0:
                                        sum_specific_yield_per_month += float(monthly_yield_value.specific_yield)
                            except Exception as exception:
                                print("Error in getting the specific yield per month : " + str(exception))
                                pass

                            # daily Energy losses
                            try:
                                energy_losses = EnergyLossTableNew.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                               count_time_period=86400,
                                                                               identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                               ts__gte=initial_time,
                                                                               ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting the energy losses values: " + str(exception))

                            # monthly energy losses
                            try:
                                monthly_energy_losses = EnergyLossTableNew.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                       count_time_period=86400,
                                                                                       identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                       ts__gte=month_start_day,
                                                                                       ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting the energy losses values: " + str(exception))

                            # calculate monthly losses
                            total_monthly_dc_loss = 0.0
                            total_monthly_conversion_loss = 0.0
                            total_monthly_ac_loss = 0.0
                            for monthly_loss in monthly_energy_losses:
                                try:
                                    if monthly_loss.dc_energy_loss is not None and float(monthly_loss.dc_energy_loss)>0:
                                        total_monthly_dc_loss += monthly_loss.dc_energy_loss
                                    if monthly_loss.conversion_loss is not None and float(monthly_loss.conversion_loss)>0:
                                        total_monthly_conversion_loss += monthly_loss.conversion_loss
                                    if monthly_loss.ac_energy_loss is not None and float(monthly_loss.ac_energy_loss)>0:
                                        total_monthly_ac_loss += monthly_loss.ac_energy_loss
                                except:
                                    continue
                            # daily equipment availability
                            inverters_down_time = 0
                            inverters = plant.independent_inverter_units.all()
                            for inverter in inverters:
                                equipment_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                   count_time_period=86400,
                                                                                   identifier=str(inverter.sourceKey),
                                                                                   ts__gte=initial_time,
                                                                                   ts__lte=final_time)
                                if len(equipment_down_time)>0:
                                    try:
                                        inverters_down_time += int(equipment_down_time[0].down_time)
                                    except:
                                        pass

                            try:
                                average_equipment_down_time = float(float(inverters_down_time)/len(inverters))
                            except:
                                average_equipment_down_time = 0

                            # monthly equipment availability
                            total_monthly_equipment_down_time = 0
                            for inverter in inverters:
                                monthly_equipment_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                           count_time_period=86400,
                                                                                           identifier=str(inverter.sourceKey),
                                                                                           ts__gte=month_start_day,
                                                                                           ts__lte=month_end_day)
                                if len(monthly_equipment_down_time)>0:
                                    for inverter_down_time in monthly_equipment_down_time:
                                        try:
                                            total_monthly_equipment_down_time += int(inverter_down_time.down_time)
                                        except:
                                            pass
                            try:
                                average_monthly_down_time = float(total_monthly_equipment_down_time/len(inverters))
                            except:
                                average_monthly_down_time = 0

                            # if plant.groupClient.slug == 'renew-power':
                            #     try:
                            #         final_equipment_down_time = 100.0 - float(average_monthly_down_time)
                            #     except:
                            #         final_equipment_down_time = 100.0
                            # else:
                            try:
                                final_equipment_down_time = ((11*60*len(monthly_equipment_down_time) - average_monthly_down_time)/(11*60*len(monthly_equipment_down_time)))*100 if (len(monthly_equipment_down_time) and average_monthly_down_time) else 100
                            except Exception as exception:
                                print("final equipment down time" + str(exception))
                                final_equipment_down_time = 100

                            # grid availability
                            grid_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                          count_time_period=86400,
                                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                          ts__gte=initial_time,
                                                                          ts__lte=final_time)

                            # monthly grid availability
                            monthly_grid_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                  count_time_period=86400,
                                                                                  identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                  ts__gte=month_start_day,
                                                                                  ts__lte=month_end_day)

                            total_monthly_down_time = 0.0
                            for down_time in monthly_grid_down_time:
                                total_monthly_down_time += down_time.down_time
                            try:
                                average_monthly_down_time = ((11*60*len(monthly_grid_down_time) - total_monthly_down_time)/(11*60*len(monthly_grid_down_time)))*100 if (len(monthly_grid_down_time) and total_monthly_down_time) else 100
                            except Exception as exception:
                                print ("average_monthly_down_time" + str(exception))
                                average_monthly_down_time = 100

                            # get the average irradiation values
                            irradiation_values = KWHPerMeterSquare.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                  count_time_period=86400,
                                                                                  identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                  ts__gte=initial_time,
                                                                                  ts__lte=final_time)

                            # monthly average irradiation values
                            monthly_irradiation_values = KWHPerMeterSquare.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                          count_time_period=86400,
                                                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                          ts__gte=month_start_day,
                                                                                          ts__lte=month_end_day)

                            # calculate average insolation of the month
                            try:
                                sum_insolation = 0.0
                                count_insolation = 0
                                for monthly_insolation_value in monthly_irradiation_values:
                                    if float(monthly_insolation_value.value)>0.0:
                                        sum_insolation += float(monthly_insolation_value.value)
                                        count_insolation += 1
                                monthly_insolation = float(sum_insolation)/float(count_insolation)
                            except Exception as exception:
                                print("Error in getting the average insolation of the month : " + str(exception))
                                monthly_insolation = 0.0
                                pass

                            # get the aggregated values (like ambient temp, module temp, wind speed etc.)
                            aggregated_values = AggregatedPlantParameters.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                         count_time_period=86400,
                                                                                         identifier=str(plant.slug),
                                                                                         ts__gte=initial_time,
                                                                                         ts__lte=final_time)

                            # monthly aggregated values
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

                            # daily max irradiation values and inverters energy
                            max_values = MaxValuesTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                       count_time_period=86400,
                                                                       identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                       ts__gte=initial_time,
                                                                       ts__lte=final_time)

                            for index in range(len(historical_energy_values)):
                                try:
                                    try:
                                        energy = float(historical_energy_values[index].energy) if historical_energy_values[index].energy else None
                                    except Exception as exception:
                                        print("energy"+ str(exception))
                                    try:
                                        pr = float(performance_ratio_values[index].performance_ratio) if (len(performance_ratio_values)>0 and performance_ratio_values[index].performance_ratio) else None
                                    except Exception as exception:
                                        print("pr"+str(exception))
                                    try:
                                        cuf = float(cuf_values[index].CUF) if (len(cuf_values)>0 and cuf_values[index].CUF) else None
                                    except Exception as exception:
                                        print("cuf"+str(exception))

                                    try:
                                        specific_yield = float(specific_yield_value[index].specific_yield) if (len(specific_yield_value)>0 and specific_yield_value[index].specific_yield) else None
                                    except Exception as exception:
                                        print("specific yield"+str(exception))

                                    try:
                                        dc_loss = float(energy_losses[index].dc_energy_loss) if (len(energy_losses) and energy_losses[index].dc_energy_loss and float(energy_losses[index].dc_energy_loss)>0) else None
                                    except Exception as exception:
                                        print("dc_loss"+str(exception))
                                    try:
                                        conversion_loss = float(energy_losses[index].conversion_loss) if (len(energy_losses) and energy_losses[index].conversion_loss and float(energy_losses[index].conversion_loss)>0) else None
                                    except Exception as exception:
                                        print("conversion loss"+str(exception))
                                    try:
                                        ac_loss = float(energy_losses[index].ac_energy_loss) if (len(energy_losses) and energy_losses[index].ac_energy_loss and float(energy_losses[index].ac_energy_loss)>0) else None
                                    except Exception as exception:
                                        print("ac loss"+str(exception))
                                    try:
                                        grid_availability = (((11*60)-float(grid_down_time[index].down_time))/(11*60))*100 if (len(grid_down_time) and grid_down_time[index].down_time) else 100
                                    except Exception as exception:
                                        grid_availability = 100
                                        print("grid availability"+str(exception))

                                    if plant.groupClient.slug == 'renew-power':
                                        try:
                                            equipment_availability = 100.0 - float(average_equipment_down_time)
                                        except:
                                            equipment_availability = 100.0
                                    else:
                                        try:
                                            equipment_availability = (((11*60)-float(average_equipment_down_time))/(11*60))*100 if average_equipment_down_time else 100
                                        except Exception as exception:
                                            equipment_availability = 100
                                            print("equipment availability"+str(exception))

                                    try:
                                        average_daily_insolation = float(irradiation_values[index].value) if (irradiation_values and irradiation_values[index].value) else 0.0
                                    except Exception as exception:
                                        average_daily_insolation = 0.0
                                        print("average irradiation error"+str(exception))

                                    try:
                                        average_ambient_temperature = float(aggregated_values[index].average_ambient_temperature) if (aggregated_values and aggregated_values[index].average_ambient_temperature) else None
                                    except Exception as exception:
                                        print("average ambient temperature error"+str(exception))

                                    try:
                                        average_module_temperature = float(aggregated_values[index].average_module_temperature) if (aggregated_values and aggregated_values[index].average_module_temperature) else None
                                    except Exception as exception:
                                        print("average ambient temperature error"+str(exception))

                                    try:
                                        average_wind_speed = float(aggregated_values[index].average_windspeed) if (aggregated_values and aggregated_values[index].average_windspeed) else None
                                    except Exception as exception:
                                        print("average ambient temperature error"+str(exception))
                                        average_wind_speed = None

                                    try:
                                        max_irradiance = float(max_values[index].max_irradiance) if (max_values and max_values[index].max_irradiance) else None
                                    except Exception as exception:
                                        print("max irradiance error "+str(exception))
                                        max_irradiance = None

                                    try:
                                        inverters_generation = float(max_values[index].inverters_generation) if (max_values and max_values[index].inverters_generation) else None
                                    except Exception as exception:
                                        print("max irradiance error "+str(exception))
                                        inverters_generation = None

                                    try:
                                        daily_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                              count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                              identifier=plant.slug,
                                                                                              ts=historical_energy_values[index].ts)
                                        daily_summary_entry.update(generation=energy,
                                                                   performance_ratio=pr,
                                                                   cuf=cuf,
                                                                   specific_yield=specific_yield,
                                                                   dc_loss=dc_loss,
                                                                   conversion_loss=conversion_loss,
                                                                   ac_loss=ac_loss,
                                                                   grid_availability=grid_availability,
                                                                   equipment_availability=equipment_availability,
                                                                   average_irradiation=average_daily_insolation,
                                                                   average_module_temperature=average_module_temperature,
                                                                   average_ambient_temperature=average_ambient_temperature,
                                                                   average_wind_speed=average_wind_speed,
                                                                   max_irradiance=max_irradiance,
                                                                   inverter_generation=inverters_generation,
                                                                   updated_at=current_time)
                                    except:
                                        daily_summary_entry = PlantSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                 count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                 identifier=plant.slug,
                                                                                                 ts=historical_energy_values[index].ts,
                                                                                                 generation=energy,
                                                                                                 performance_ratio=pr,
                                                                                                 cuf=cuf,
                                                                                                 specific_yield=specific_yield,
                                                                                                 dc_loss=dc_loss,
                                                                                                 conversion_loss=conversion_loss,
                                                                                                 ac_loss=ac_loss,
                                                                                                 grid_availability=grid_availability,
                                                                                                 equipment_availability=equipment_availability,
                                                                                                 average_irradiation = average_daily_insolation,
                                                                                                 average_module_temperature=average_module_temperature,
                                                                                                 average_ambient_temperature=average_ambient_temperature,
                                                                                                 average_wind_speed=average_wind_speed,
                                                                                                 max_irradiance=max_irradiance,
                                                                                                 inverter_generation=inverters_generation,
                                                                                                 updated_at=current_time)
                                        daily_summary_entry.save()
                                except Exception as exception:
                                    print(str(exception))
                                    continue

                            # store the monthly values

                            try:
                                monthly_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                        identifier=plant.slug,
                                                                                        ts=month_start_day)
                                monthly_summary_entry.update(generation=total_monthly_energy_value,
                                                             performance_ratio=monthly_pr,
                                                             cuf=monthly_cuf,
                                                             specific_yield=sum_specific_yield_per_month,
                                                             dc_loss=total_monthly_dc_loss,
                                                             conversion_loss=total_monthly_conversion_loss,
                                                             ac_loss=total_monthly_ac_loss,
                                                             grid_availability=average_monthly_down_time,
                                                             equipment_availability=final_equipment_down_time,
                                                             average_irradiation = monthly_insolation,
                                                             average_module_temperature=monthly_module_temperature,
                                                             average_ambient_temperature=monthly_ambient_temperature,
                                                             average_wind_speed=monthly_wind_speed,
                                                             updated_at=current_time)
                            except:
                                monthly_summary_entry = PlantSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                           count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                           identifier=plant.slug,
                                                                                           ts=month_start_day,
                                                                                           generation=total_monthly_energy_value,
                                                                                           performance_ratio=monthly_pr,
                                                                                           cuf=monthly_cuf,
                                                                                           specific_yield=sum_specific_yield_per_month,
                                                                                           dc_loss=total_monthly_dc_loss,
                                                                                           conversion_loss=total_monthly_conversion_loss,
                                                                                           ac_loss=total_monthly_ac_loss,
                                                                                           grid_availability=average_monthly_down_time,
                                                                                           equipment_availability=final_equipment_down_time,
                                                                                           average_irradiation = monthly_insolation,
                                                                                           average_module_temperature=monthly_module_temperature,
                                                                                           average_ambient_temperature=monthly_ambient_temperature,
                                                                                           average_wind_speed=monthly_wind_speed,
                                                                                           updated_at=current_time)
                                monthly_summary_entry.save()

                            last_entry_daily = last_entry_daily + datetime.timedelta(days=1)
                            duration_days -= 1
                            print duration_days

                        if duration_days == 0:
                            initial_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                            final_time = current_time
                            month_start_day = initial_time.replace(day=1)
                            month_end_day = final_time
                            # get the stored historical energy value
                            # try:
                            #     historical_energy_values = HistoricEnergyValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                            #                                                                    count_time_period=86400,
                            #                                                                    identifier=str(plant.slug),
                            #                                                                    ts__gte=initial_time,
                            #                                                                    ts__lte=final_time)
                            # except Exception as exception:
                            #     print("Error in getting historical energy values : " + str(exception))

                            # get monthly energy values
                            try:
                                monthly_historical_energy_values = HistoricEnergyValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                       count_time_period=86400,
                                                                                                       identifier=str(plant.slug),
                                                                                                       ts__gte=month_start_day,
                                                                                                       ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting historical energy values : " + str(exception))

                            # calculate total energy of the month
                            try:
                                total_monthly_energy_value = 0.0
                                for monthly_energy_value in monthly_historical_energy_values:
                                    total_monthly_energy_value += float(monthly_energy_value.energy)
                            except Exception as exception:
                                print("Error in calculating the total energy of the month : " + str(exception))
                                pass

                            # calculate today's energy
                            try:
                                todays_energy = get_minutes_aggregated_energy(initial_time,final_time,plant,'DAY',1)
                                print todays_energy
                            except Exception as exception:
                                print("Error in getting the energy values" + str(exception))
                            try:
                                if todays_energy and len(todays_energy) > 0:
                                    #energy_values = [item['energy'] for item in todays_energy]
                                    if len(todays_energy) > 0:
                                        today_energy_value = todays_energy[len(todays_energy)-1]['energy']
                                    else:
                                        today_energy_value = 0.0
                                else:
                                    today_energy_value = 0.0
                            except Exception as exception:
                                print str(exception)
                                today_energy_value = 0.0

                            total_monthly_energy_value += today_energy_value

                            # daily PR
                            try:
                                performance_ratio_values = PerformanceRatioTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                count_time_period=86400,
                                                                                                identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                                ts__gte=initial_time,
                                                                                                ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting pr values: " + str(exception))

                            try:
                                pr = float(performance_ratio_values[len(performance_ratio_values)-1].performance_ratio) if (len(performance_ratio_values)>0 and performance_ratio_values[len(performance_ratio_values)-1].performance_ratio) else 0.0
                            except Exception as exception:
                                print(str(exception))

                            # get monthly PR
                            try:
                                monthly_performance_ratio_values = PerformanceRatioTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                        count_time_period=86400,
                                                                                                        identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                                        ts__gte=month_start_day,
                                                                                                        ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting pr values: " + str(exception))

                            # calculate average pr of the month
                            try:
                                sum_pr = 0.0
                                count_pr = 0
                                for monthly_pr_value in monthly_performance_ratio_values:
                                    if float(monthly_pr_value.performance_ratio)>0.0:
                                        sum_pr += float(monthly_pr_value.performance_ratio)
                                        count_pr += 1
                                monthly_pr = float(sum_pr)/float(count_pr)
                            except Exception as exception:
                                print("Error in getting the average pr of the month : " + str(exception))
                                monthly_pr = 0.0
                                pass


                            # cuf values
                            try:
                                cuf_values = CUFTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                     ts__gte=initial_time,
                                                                     ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting the cuf values : " + str(exception))

                            try:
                                cuf = float(cuf_values[len(cuf_values)-1].CUF) if (len(cuf_values)>0 and cuf_values[len(cuf_values)-1].CUF) else 0.0
                            except Exception as exception:
                                print(str(exception))

                            #monthly cuf values
                            try:
                                monthly_cuf_values = CUFTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                     ts__gte=month_start_day,
                                                                     ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting the cuf values : " + str(exception))

                            # calculate average cuf of the month
                            try:
                                sum_cuf = 0.0
                                count_cuf = 0
                                for monthly_cuf_value in monthly_cuf_values:
                                    if float(monthly_cuf_value.CUF)>0.0:
                                        sum_cuf += float(monthly_cuf_value.CUF)
                                        count_cuf += 1
                                monthly_cuf = float(sum_cuf)/float(count_cuf)
                            except Exception as exception:
                                print("Error in getting the average cuf of the month : " + str(exception))
                                monthly_cuf = 0.0
                                pass

                            # specific yield values
                            try:
                                specific_yield_values = SpecificYieldTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                          count_time_period=86400,
                                                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                          ts__gte=initial_time,
                                                                                          ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting the specific yield values : " + str(exception))

                            try:
                                specific_yield = float(specific_yield_values[len(specific_yield_values)-1].specific_yield) if (len(specific_yield_values)>0 and specific_yield_values[len(specific_yield_values)-1].specific_yield) else 0.0
                            except Exception as exception:
                                print(str(exception))

                            #monthly specific yield values
                            try:
                                monthly_specific_yield_values = SpecificYieldTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                  count_time_period=86400,
                                                                                                  identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                                  ts__gte=month_start_day,
                                                                                                  ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting monthly specific yield values : " + str(exception))

                            # calculate specific yield values per month
                            try:
                                sum_specific_yield_value = 0.0
                                for monthly_specific_yield in monthly_specific_yield_values:
                                    if float(monthly_specific_yield.specific_yield)>0.0:
                                        sum_specific_yield_value += float(monthly_specific_yield.specific_yield)
                            except Exception as exception:
                                print("Error in getting the average cuf of the month : " + str(exception))
                                pass

                            # Energy losses
                            try:
                                energy_losses = EnergyLossTableNew.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                               count_time_period=86400,
                                                                               identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                               ts__gte=initial_time,
                                                                               ts__lte=final_time)
                            except Exception as exception:
                                print("Error in getting the energy losses values" + str(exception))
                            try:
                                dc_loss = float(energy_losses[len(energy_losses)-1].dc_energy_loss) if (len(energy_losses) and energy_losses[len(energy_losses)-1].dc_energy_loss and float(energy_losses[len(energy_losses)-1].dc_energy_loss)>0) else None
                            except Exception as exception:
                                print(str(exception))
                            try:
                                conversion_loss = float(energy_losses[len(energy_losses)-1].conversion_loss) if (len(energy_losses) and energy_losses[len(energy_losses)-1].conversion_loss and float(energy_losses[len(energy_losses)-1].conversion_loss)>0) else None
                            except Exception as exception:
                                print(str(exception))
                            try:
                                ac_loss = float(energy_losses[len(energy_losses)-1].ac_energy_loss) if (len(energy_losses) and energy_losses[len(energy_losses)-1].ac_energy_loss and float(energy_losses[len(energy_losses)-1].ac_energy_loss)>0) else None
                            except Exception as exception:
                                print(str(exception))

                            # monthly energy losses
                            try:
                                monthly_energy_losses = EnergyLossTableNew.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                       count_time_period=86400,
                                                                                       identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                       ts__gte=month_start_day,
                                                                                       ts__lte=month_end_day)
                            except Exception as exception:
                                print("Error in getting the energy losses values: " + str(exception))

                            # calculate monthly losses
                            total_monthly_dc_loss = 0.0
                            total_monthly_conversion_loss = 0.0
                            total_monthly_ac_loss = 0.0
                            for monthly_loss in monthly_energy_losses:
                                try:
                                    if monthly_loss.dc_energy_loss is not None and float(monthly_loss.dc_energy_loss)>0:
                                        total_monthly_dc_loss += monthly_loss.dc_energy_loss
                                    if monthly_loss.conversion_loss is not None and float(monthly_loss.conversion_loss)>0:
                                        total_monthly_conversion_loss += monthly_loss.conversion_loss
                                    if monthly_loss.ac_energy_loss is not None and float(monthly_loss.ac_energy_loss)>0:
                                        total_monthly_ac_loss += monthly_loss.ac_energy_loss
                                except:
                                    continue

                            # max irradiance and inverters generation
                            max_values = MaxValuesTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                       count_time_period=86400,
                                                                       identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                       ts__gte=initial_time,
                                                                       ts__lte=final_time)
                            try:
                                max_irradiance = float(max_values[len(max_values)-1].max_irradiance) if (len(max_values) and max_values[len(max_values)-1].max_irradiance) else None
                            except Exception as exception:
                                print(str(exception))
                                max_irradiance = None

                            try:
                                inverters_generation = float(max_values[len(max_values)-1].inverters_generation) if (len(max_values) and max_values[len(max_values)-1].inverters_generation) else None
                            except Exception as exception:
                                print(str(exception))
                                inverters_generation = None

                            # daily equipment availability
                            inverters_down_time = 0
                            inverters = plant.independent_inverter_units.all()
                            for inverter in inverters:
                                equipment_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                   count_time_period=86400,
                                                                                   identifier=str(inverter.sourceKey),
                                                                                   ts__gte=initial_time,
                                                                                   ts__lte=final_time)
                                if len(equipment_down_time)>0:
                                    try:
                                        inverters_down_time += int(equipment_down_time[0].down_time)
                                    except:
                                        pass
                            try:
                                average_equipment_down_time = float(float(inverters_down_time)/len(inverters))
                            except:
                                average_equipment_down_time = 0

                            # monthly equipment availability
                            total_monthly_equipment_down_time = 0
                            for inverter in inverters:
                                monthly_equipment_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                           count_time_period=86400,
                                                                                           identifier=str(inverter.sourceKey),
                                                                                           ts__gte=month_start_day,
                                                                                           ts__lte=month_end_day)
                                if len(monthly_equipment_down_time)>0:
                                    for inverter_down_time in monthly_equipment_down_time:
                                        try:
                                            total_monthly_equipment_down_time += int(inverter_down_time.down_time)
                                        except:
                                            pass
                            try:
                                average_monthly_down_time = float(total_monthly_equipment_down_time/len(inverters))
                            except:
                                average_monthly_down_time = 0

                            # if plant.groupClient.slug=='renew-power':
                            #     try:
                            #         final_equipment_down_time = (100.0 - float(average_monthly_down_time))
                            #     except:
                            #         final_equipment_down_time = 100
                            try:
                                final_equipment_down_time = ((11*60*len(monthly_equipment_down_time) - average_monthly_down_time)/(11*60*len(monthly_equipment_down_time)))*100
                            except Exception as exception:
                                print("final equipment down time" + str(exception))
                                final_equipment_down_time = 100

                            # grid availability
                            grid_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                          count_time_period=86400,
                                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                          ts__gte=initial_time,
                                                                          ts__lte=final_time)

                            # monthly grid availability
                            monthly_grid_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                  count_time_period=86400,
                                                                                  identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                  ts__gte=month_start_day,
                                                                                  ts__lte=month_end_day)

                            total_monthly_down_time = 0.0
                            for down_time in monthly_grid_down_time:
                                total_monthly_down_time += down_time.down_time
                            try:
                                average_monthly_down_time = ((11*60*len(monthly_grid_down_time) - total_monthly_down_time)/(11*60*len(monthly_grid_down_time)))*100
                            except Exception as exception:
                                print ("average_monthly_down_time" + str(exception))
                                average_monthly_down_time = 100

                            try:
                                grid_availability = (((11*60)-float(grid_down_time[len(grid_down_time)-1].down_time))/(11*60))*100 if (len(grid_down_time) and grid_down_time[len(grid_down_time)-1].down_time) else 100
                            except Exception as exception:
                                grid_availability = None
                                print("grid availability"+str(exception))

                            if plant.groupClient.slug == 'renew-power':
                                try:
                                    equipment_availability = 100.0 - float(average_equipment_down_time)
                                except:
                                    equipment_availability = 100.0
                            else:
                                try:
                                    equipment_availability = (((11*60)-float(average_equipment_down_time))/(11*60))*100 if average_equipment_down_time else 100
                                except Exception as exception:
                                    equipment_availability = 100
                                    print("equipment availability"+str(exception))


                            # get the average irradiation values
                            irradiation_values = KWHPerMeterSquare.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                  count_time_period=86400,
                                                                                  identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                  ts__gte=initial_time,
                                                                                  ts__lte=final_time)

                            # monthly average irradiation values
                            monthly_irradiation_values = KWHPerMeterSquare.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                          count_time_period=86400,
                                                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                                          ts__gte=month_start_day,
                                                                                          ts__lte=month_end_day)

                            # calculate average insolation of the month
                            try:
                                sum_insolation = 0.0
                                count_insolation = 0
                                for monthly_insolation_value in monthly_irradiation_values:
                                    if float(monthly_insolation_value.value)>0.0:
                                        sum_insolation += float(monthly_insolation_value.value)
                                        count_insolation += 1
                                monthly_insolation = float(sum_insolation)/float(count_insolation)
                            except Exception as exception:
                                print("Error in getting the average insolation of the month : " + str(exception))
                                monthly_insolation = 0.0
                                pass

                            try:
                                average_daily_insolation = float(irradiation_values[len(irradiation_values)-1].value) if (len(irradiation_values)>0 and irradiation_values[len(irradiation_values)-1].value) else 0.0
                            except Exception as exception:
                                print(str(exception))

                            # get the aggregated values (like ambient temp, module temp, wind speed etc.)
                            aggregated_values = AggregatedPlantParameters.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                         count_time_period=86400,
                                                                                         identifier=str(plant.slug),
                                                                                         ts__gte=initial_time,
                                                                                         ts__lte=final_time)

                            # monthly aggregated values
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
                                average_module_temperature = float(aggregated_values[len(aggregated_values)-1].average_module_temperature) if (len(aggregated_values)>0 and aggregated_values[len(aggregated_values)-1].average_module_temperature) else None
                            except Exception as exception:
                                print(str(exception))

                            try:
                                average_ambient_temperature = float(aggregated_values[len(aggregated_values)-1].average_ambient_temperature) if (len(aggregated_values)>0 and aggregated_values[len(aggregated_values)-1].average_ambient_temperature) else None
                            except Exception as exception:
                                print(str(exception))

                            try:
                                average_wind_speed = float(aggregated_values[len(aggregated_values)-1].average_windspeed) if (len(aggregated_values)>0 and aggregated_values[len(aggregated_values)-1].average_windspeed) else None
                            except Exception as exception:
                                print(str(exception))

                            try:
                                daily_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                      identifier=plant.slug,
                                                                                      ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                                daily_summary_entry.update(generation=today_energy_value,
                                                           performance_ratio=pr,
                                                           cuf=cuf,
                                                           specific_yield=specific_yield,
                                                           dc_loss=dc_loss,
                                                           conversion_loss=conversion_loss,
                                                           ac_loss=ac_loss,
                                                           grid_availability=grid_availability,
                                                           equipment_availability=equipment_availability,
                                                           average_irradiation=average_daily_insolation,
                                                           average_module_temperature=average_module_temperature,
                                                           average_ambient_temperature=average_ambient_temperature,
                                                           average_wind_speed=average_wind_speed,
                                                           max_irradiance=max_irradiance,
                                                           inverter_generation=inverters_generation,
                                                           updated_at=final_time)
                            except:
                                daily_summary_entry = PlantSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                         identifier=plant.slug,
                                                                                         ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                         generation=today_energy_value,
                                                                                         performance_ratio=pr,
                                                                                         cuf=cuf,
                                                                                         specific_yield=specific_yield,
                                                                                         dc_loss=dc_loss,
                                                                                         conversion_loss=conversion_loss,
                                                                                         ac_loss=ac_loss,
                                                                                         grid_availability=grid_availability,
                                                                                         equipment_availability=equipment_availability,
                                                                                         average_irradiation=average_daily_insolation,
                                                                                         average_module_temperature=average_module_temperature,
                                                                                         average_ambient_temperature=average_ambient_temperature,
                                                                                         average_wind_speed=average_wind_speed,
                                                                                         max_irradiance=max_irradiance,
                                                                                         inverter_generation=inverters_generation,
                                                                                         updated_at=final_time)
                                daily_summary_entry.save()

                            try:
                                monthly_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                        identifier=plant.slug,
                                                                                        ts=month_start_day)

                                monthly_summary_entry.update(generation=total_monthly_energy_value,
                                                             performance_ratio=monthly_pr,
                                                             cuf=monthly_cuf,
                                                             specific_yield=sum_specific_yield_value,
                                                             dc_loss=total_monthly_dc_loss,
                                                             conversion_loss=total_monthly_conversion_loss,
                                                             ac_loss=total_monthly_ac_loss,
                                                             grid_availability=average_monthly_down_time,
                                                             equipment_availability=final_equipment_down_time,
                                                             average_irradiation=monthly_insolation,
                                                             average_module_temperature=monthly_module_temperature,
                                                             average_ambient_temperature=monthly_ambient_temperature,
                                                             average_wind_speed=monthly_wind_speed,
                                                             updated_at=final_time)

                            except:
                                monthly_summary_entry = PlantSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                           count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                           identifier=plant.slug,
                                                                                           ts=month_start_day,
                                                                                           generation=total_monthly_energy_value,
                                                                                           performance_ratio=monthly_pr,
                                                                                           cuf=monthly_cuf,
                                                                                           specific_yield=sum_specific_yield_value,
                                                                                           dc_loss=total_monthly_dc_loss,
                                                                                           conversion_loss=total_monthly_conversion_loss,
                                                                                           ac_loss=total_monthly_ac_loss,
                                                                                           grid_availability=average_monthly_down_time,
                                                                                           equipment_availability=final_equipment_down_time,
                                                                                           average_irradiation=monthly_insolation,
                                                                                           average_module_temperature=monthly_module_temperature,
                                                                                           average_ambient_temperature=monthly_ambient_temperature,
                                                                                           average_wind_speed=monthly_wind_speed,
                                                                                           updated_at=final_time)
                                monthly_summary_entry.save()
                except:
                    continue
    except Exception as exception:
        print(str(exception))
