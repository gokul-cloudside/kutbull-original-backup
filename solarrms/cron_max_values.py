from solarrms.models import SolarPlant, MaxValuesTable
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import get_irradiation_data, get_minutes_aggregated_energy
import numpy as np
import pandas as pd
import pytz
from django.utils import timezone
import datetime
from django.conf import settings
import math
from dashboards.models import DataglenClient, Dashboard

start_date = "2017-10-01 00:00:00"

# method to get maximum irradiance value
def get_max_irradiance(starttime, endttime, plant):
    try:
        irradiation_data = get_irradiation_data(starttime, endttime, plant)
        if not irradiation_data.empty:
            return np.max(irradiation_data['irradiation'])
        else:
            return None
    except Exception as exception:
        print str(exception)
        return None

# method to get DC power values
def get_dc_power_values_inverter_wise(starttime, endtime, plant):
    try:
        final_df = pd.DataFrame()
        inverters = plant.independent_inverter_units.all().filter(isActive=True)
        for inverter in inverters:
            dc_power = []
            timestamps = []
            df_inverter = pd.DataFrame()
            dc_power_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name= 'DC_POWER',
                                                                      timestamp_in_data__gte = starttime,
                                                                      timestamp_in_data__lte = endtime)
            for datapoint in dc_power_values:
                dc_power.append(float(datapoint.stream_value))
                timestamps.append(datapoint.timestamp_in_data.replace(second=0, microsecond=0))

            df_inverter['timestamp'] = timestamps
            df_inverter[str(inverter.name)] = dc_power

            if final_df.empty:
                final_df = df_inverter
            else:
                final_df = final_df.merge(df_inverter.drop_duplicates('timestamp'), on='timestamp', how='outer')
        return final_df.sort('timestamp')
    except Exception as exception:
        print str(exception)
        return []

# method to get max dc power values
def get_max_dc_power_inverter_wise(starttime, endtime, plant):
    try:
        final_result = {}
        dc_power_values = get_dc_power_values_inverter_wise(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            try:
                if math.isnan(np.max(dc_power_values[str(inverter.name)])):
                    final_result[str(inverter.name)] = None
                else:
                    final_result[str(inverter.name)] = np.max(dc_power_values[str(inverter.name)])
            except:
                final_result[str(inverter.name)] = None
                continue
        return final_result
    except Exception as exception:
        print str(exception)
        return {}

# method to get AC power values
def get_active_power_values_inverter_wise(starttime, endtime, plant):
    try:
        final_df = pd.DataFrame()
        inverters = plant.independent_inverter_units.all().filter(isActive=True)
        for inverter in inverters:
            active_power = []
            timestamps = []
            df_inverter = pd.DataFrame()
            ac_power_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name= 'ACTIVE_POWER',
                                                                      timestamp_in_data__gte = starttime,
                                                                      timestamp_in_data__lte = endtime)
            for datapoint in ac_power_values:
                active_power.append(float(datapoint.stream_value))
                timestamps.append(datapoint.timestamp_in_data.replace(second=0, microsecond=0))

            df_inverter['timestamp'] = timestamps
            df_inverter[str(inverter.name)] = active_power

            if final_df.empty:
                final_df = df_inverter
            else:
                final_df = final_df.merge(df_inverter.drop_duplicates('timestamp'), on='timestamp', how='outer')
        return final_df.sort('timestamp')
    except Exception as exception:
        print str(exception)
        return []

# method to get max active power values
def get_max_active_power_inverter_wise(starttime, endtime, plant):
    try:
        final_result = {}
        active_power_values = get_active_power_values_inverter_wise(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            try:
                if math.isnan(np.max(active_power_values[str(inverter.name)])):
                    final_result[str(inverter.name)] = None
                else:
                    final_result[str(inverter.name)] = np.max(active_power_values[str(inverter.name)])
            except:
                final_result[str(inverter.name)] = None
                continue
        return final_result
    except Exception as exception:
        print str(exception)
        return {}


def cron_max_values():

    try:
        dashboard = Dashboard.objects.get(slug='solar')
        solar_clients = DataglenClient.objects.filter(clientDashboard=dashboard)
        clients = solar_clients.exclude(slug__in=["adani", "alpine-spinning-mills", "atria-power", "jackson",
                                                  "dev-solar", "renew-power"])
        plants = SolarPlant.objects.filter(groupClient__in=clients)
    except Exception as exception:
        print("Solar Dashboard not found " + str(exception))
        return

    for plant in plants:
        try:
            try:
                print "computing for plant : " + str(plant.slug)
                try:
                    tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
                except:
                    print ("Error in getting tz")
                try:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except Exception as exc:
                    print(str(exc))
                    current_time = timezone.now()
            except Exception as exception:
                print str(exception)
                continue

            max_value_last_entry = MaxValuesTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                 count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                 identifier=plant.metadata.plantmetasource.sourceKey).limit(1).values_list('ts')
            if max_value_last_entry:
                last_entry_values = [item[0] for item in max_value_last_entry]
                last_entry  = last_entry_values[0]
                print("last_time_entry: ", last_entry)
                if last_entry.tzinfo is None:
                    last_entry =pytz.utc.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))

            duration = (current_time - last_entry)
            duration_days = duration.days
            loop_count = 0
            while loop_count < duration_days:
                print(duration_days)
                print last_entry
                initial_time = last_entry.replace(hour=0, minute=0, second=0, microsecond=0)
                final_time = last_entry.replace(hour=23, minute=59, second=59, microsecond=59)

                daily_max_value = MaxValuesTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                identifier=plant.metadata.plantmetasource.sourceKey,
                                                                ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                # maximim irradiance value
                max_irradiance = get_max_irradiance(initial_time, final_time, plant)

                # inverter's total generation
                inverters_energy = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, False, False)

                try:
                    if inverters_energy and len(inverters_energy) > 0:
                        #energy_values = [item['energy'] for item in todays_energy]
                        if len(inverters_energy) > 0:
                            today_energy_value = inverters_energy[len(inverters_energy)-1]['energy']
                        else:
                            today_energy_value = 0.0
                    else:
                        today_energy_value = 0.0
                except Exception as exception:
                    print str(exception)
                    today_energy_value = 0.0

                # Max DC Power values for Inverters
                max_dc_power_values = get_max_dc_power_inverter_wise(initial_time, final_time, plant)

                # Max AC power values for inverters
                max_active_power_values = get_max_active_power_inverter_wise(initial_time, final_time, plant)

                inverters = plant.independent_inverter_units.all()
                try:
                    if len(daily_max_value)==0:
                        daily_plant_entry = MaxValuesTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                          identifier=plant.metadata.plantmetasource.sourceKey,
                                                                          ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                          max_irradiance=max_irradiance,
                                                                          inverters_generation=today_energy_value,
                                                                          updated_at=current_time)
                        daily_plant_entry.save()
                    else:
                        daily_max_value.update(max_irradiance=max_irradiance,
                                                 inverters_generation=today_energy_value,
                                                 updated_at=current_time)

                    for inverter in inverters:
                        try:
                            daily_max_inverter_value = MaxValuesTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=inverter.sourceKey,
                                                                                     ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                            max_inverter_dc_power = max_dc_power_values[str(inverter.name)]
                            max_inverter_ac_power  = max_active_power_values[str(inverter.name)]

                            if len(daily_max_inverter_value)==0:
                                daily_inverter_entry = MaxValuesTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=inverter.sourceKey,
                                                                                     ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                     max_dc_power=max_inverter_dc_power,
                                                                                     max_ac_power=max_inverter_ac_power,
                                                                                     updated_at=current_time)
                                daily_inverter_entry.save()
                            else:
                                daily_max_inverter_value.update(max_dc_power=max_inverter_dc_power,
                                                            max_ac_power=max_inverter_ac_power,
                                                            updated_at=current_time)
                        except:
                            continue

                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                except Exception as exception:
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                    continue

            if duration_days ==0:
                print "Current max values computation for plant : " + str(plant.slug)
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                final_time = current_time

                daily_max_value = MaxValuesTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                identifier=plant.metadata.plantmetasource.sourceKey,
                                                                ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                # maximim irradiance value
                max_irradiance = get_max_irradiance(initial_time, final_time, plant)

                # inverter's total generation
                inverters_energy = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, False, False)

                try:
                    if inverters_energy and len(inverters_energy) > 0:
                        #energy_values = [item['energy'] for item in todays_energy]
                        if len(inverters_energy) > 0:
                            today_energy_value = inverters_energy[len(inverters_energy)-1]['energy']
                        else:
                            today_energy_value = 0.0
                    else:
                        today_energy_value = 0.0
                except Exception as exception:
                    print str(exception)
                    today_energy_value = 0.0

                # Max DC Power values for Inverters
                max_dc_power_values = get_max_dc_power_inverter_wise(initial_time, final_time, plant)

                # Max AC power values for inverters
                max_active_power_values = get_max_active_power_inverter_wise(initial_time, final_time, plant)

                inverters = plant.independent_inverter_units.all()
                try:
                    if len(daily_max_value)==0:
                        daily_plant_entry = MaxValuesTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                          identifier=plant.metadata.plantmetasource.sourceKey,
                                                                          ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                          max_irradiance=max_irradiance,
                                                                          inverters_generation=today_energy_value,
                                                                          updated_at=current_time)
                        daily_plant_entry.save()
                    else:
                        daily_max_value.update(max_irradiance=max_irradiance,
                                                 inverters_generation=today_energy_value,
                                                 updated_at=current_time)

                    for inverter in inverters:
                        try:
                            daily_max_inverter_value = MaxValuesTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=inverter.sourceKey,
                                                                                     ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                            max_inverter_dc_power = max_dc_power_values[str(inverter.name)]
                            max_inverter_ac_power  = max_active_power_values[str(inverter.name)]

                            if len(daily_max_inverter_value)==0:
                                daily_inverter_entry = MaxValuesTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=inverter.sourceKey,
                                                                                     ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                     max_dc_power=max_inverter_dc_power,
                                                                                     max_ac_power=max_inverter_ac_power,
                                                                                     updated_at=current_time)
                                daily_inverter_entry.save()
                            else:
                                daily_max_inverter_value.update(max_dc_power=max_inverter_dc_power,
                                                            max_ac_power=max_inverter_ac_power,
                                                            updated_at=current_time)
                        except:
                            continue
                except Exception as exception:
                    print str(exception)
        except Exception as exception:
            print str(exception)
            continue