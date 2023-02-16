import datetime
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.models import SolarPlant, PlantCompleteValues, HistoricEnergyValues, PerformanceRatioTable, CUFTable,\
    PlantDownTime, EnergyLossTable, EnergyLossTableNew
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import calculate_pr, calculate_CUF, get_down_time,calculate_total_plant_generation, \
    get_energy_meter_values, get_aggregated_energy, get_plant_power, get_minutes_aggregated_energy
from helpdesk.dg_functions import update_ticket, get_plant_tickets
from monitoring.views import get_user_data_monitoring_status
import collections
from dashboards.models import DataglenClient, Dashboard
#from solarrms.api_views import fix_generation_units
import pandas as pd
import copy
import time


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
    if generation > 5000.0:
        return "{0:.1f} MWh".format(generation/1000.0)
    else:
        return "{0:.1f} kWh".format(generation)

def convert_values_to_common_unit(source_list):
    try:
        source_list_unit = []
        for index in range(len(source_list)):
            try:
                source_list_unit.append(str(source_list[index]['energy']).split(" ")[1].lower())
            except:
                source_list_unit.append(str(source_list[index]).split(" ")[1].lower())

        GWh_count = source_list_unit.count('GWh'.lower())
        MWh_count = source_list_unit.count('MWh'.lower())
        kWh_count = source_list_unit.count('kWh'.lower())
        if GWh_count != 0 and MWh_count != 0 and kWh_count != 0:
            # convert remaining values to GWh
            for index in range(len(source_list_unit)):
                if source_list_unit[index] == 'mwh':
                    try:
                        source_list[index]['energy'] = '{0:.1f} GWh'.format(float(source_list[index]['energy'].split(" ")[0])/1000.0)
                    except:
                        source_list[index] = '{0:.1f} GWh'.format(float(source_list[index].split(" ")[0])/1000.0)
                elif source_list_unit[index] == 'kwh':
                    try:
                        source_list[index]['energy'] = '{0:.1f} GWh'.format(float(source_list[index]['energy'].split(" ")[0])/1000000.0)
                    except:
                        source_list[index] = '{0:.1f} GWh'.format(float(source_list[index].split(" ")[0])/1000000.0)
                else:
                    pass
        elif GWh_count !=0 and MWh_count != 0 and kWh_count == 0:
            # convert remaining values to GWh
            for index in range(len(source_list_unit)):
                if source_list_unit[index] == 'mwh':
                    try:
                        source_list[index]['energy'] = '{0:.1f} GWh'.format(float(source_list[index]['energy'].split(" ")[0])/1000.0)
                    except:
                        source_list[index] = '{0:.1f} GWh'.format(float(source_list[index].split(" ")[0])/1000.0)
                else:
                    pass
        elif GWh_count !=0 and MWh_count == 0 and kWh_count != 0:
            # convert remaining values to GWh
            for index in range(len(source_list_unit)):
                if source_list_unit[index] == 'kwh':
                    try:
                        source_list[index]['energy'] = '{0:.1f} GWh'.format(float(source_list[index]['energy'].split(" ")[0])/1000000.0)
                    except:
                        source_list[index] = '{0:.1f} GWh'.format(float(source_list[index].split(" ")[0])/1000000.0)
                else:
                    pass
        elif GWh_count == 0 and MWh_count !=0 and kWh_count !=0:
            #convert the remaining values to MWh
            for index in range(len(source_list_unit)):
                if source_list_unit[index] == 'kwh':
                    try:
                        source_list[index]['energy'] = '{0:.1f} MWh'.format(float(source_list[index]['energy'].split(" ")[0])/1000.0)
                    except:
                        source_list[index] = '{0:.1f} MWh'.format(float(source_list[index].split(" ")[0])/1000.0)
                else:
                    pass
        else:
            pass

        return source_list
    except Exception as exception:
        print(str(exception))
        return source_list

def get_all_plant_details(clients_slugs = None):
    start_time = time.time()
    try:
        try:
            dashboard = Dashboard.objects.get(slug='solar')
        except Exception as exception:
            print("Solar Dashboard not found " + str(exception))
        if clients_slugs is None:
            solar_clients = DataglenClient.objects.filter(clientDashboard=dashboard)
            clients = solar_clients.exclude(slug__in=["adani", "alpine-spinning-mills", "atria-power", "jackson",
                                                      "dev-solar", "renew-power", "hero-future-energies",
                                                      "cleanmax-solar", "hcleanmax"])
        else:
            clients = DataglenClient.objects.filter(clientDashboard=dashboard, slug__in=clients_slugs)
        for client in clients:
            if client.slug in ['hcleanmax']:
                continue
            print("computing for client : " + str(client.name))
            plants = SolarPlant.objects.filter(groupClient=client)
            if len(plants) == 0:
                continue
            total_client_capacity = 0.0
            total_client_energy = 0.0
            total_client_energy_today = 0.0
            total_client_co2 = 0.0
            total_client_grid_availability = 0.0
            total_client_equipment_availability = 0.0
            total_client_pr = 0.0
            total_client_cuf = 0.0
            pr_count = 0
            cuf_count = 0
            availability_count = len(plants)
            total_client_unacknowledged_tickets = 0
            total_client_open_tickets = 0
            total_client_closed_tickets = 0
            total_client_active_power = 0.0
            total_client_irradiation = 0.0
            irradiation_count = 0
            total_client_connected_inverters = 0
            total_client_disconnected_inverters = 0
            total_client_invalid_inverters = 0
            total_client_unmonitored_inverters = 0
            total_client_connected_smbs = 0
            total_client_disconnected_smbs = 0
            total_client_invalid_smbs = 0
            total_client_unmonitored_smbs = 0
            total_client_dc_loss = 0.0
            total_client_conversion_loss = 0.0
            total_client_ac_loss = 0.0
            client_past_generations = []
            client_past_grid_unavailability = []
            client_past_equipment_unavailability = []
            client_past_dc_loss = []
            client_past_conversion_loss = []
            client_past_ac_loss = []
            client_past_pr = []
            client_past_cuf = []
            for plant in plants:
                plant_log_start_time = time.time()
                print("computing for plant : " + str(plant.slug))
                try:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except Exception as exc:
                    print(str(exc))
                    current_time = timezone.now()
                inverters = plant.independent_inverter_units.all().filter(isActive=True)
                plant_shut_down_time = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                plant_start_time_generation = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                grid_start_time = current_time.replace(hour=7, minute=0, second=0, microsecond=0)
                grid_shut_time = current_time.replace(hour=18, minute=0, second=0, microsecond=0)

                # plant static parameters
                plant_name = plant.name
                plant_location = plant.location
                plant_capacity = plant.capacity
                latitude = plant.latitude
                longitude = plant.longitude

                #pr
                try:
                    pr = calculate_pr(starttime=plant_start_time, endtime=current_time, plant=plant)
                except Exception as exception:
                    pr = 0.0
                    print("Error in computing pr : " + str(exception))

                #cuf
                try:
                    cuf = calculate_CUF(starttime=plant_start_time, endtime=current_time, plant=plant)
                except Exception as exception:
                    cuf = 0.0
                    print("Error in computing CUF : " + str(exception))

                # # grid availability
                grid_availability = 100.0
                # try:
                #     down_time = get_down_time(starttime=plant_start_time, endtime=plant_shut_down_time, plant=plant)
                #     grid_down_time = float(down_time['grid'])
                #     if current_time > grid_shut_time:
                #         grid_availability = (((11*60)-grid_down_time)/(11*60))*100
                #     else:
                #         total_minutes = float(((current_time - grid_start_time).total_seconds())/60)
                #         grid_availability = ((total_minutes-grid_down_time)/total_minutes)*100
                # except Exception as exception:
                #     grid_availability = 100.0
                #     print("Error in getting grid down time : " + str(exception))
                # # equipment availability
                equipment_down_time = 0
                equipment_availability = 100.0
                # try:
                #     equipment_down_time = 0
                #     for inverter in inverters:
                #         try:
                #             equipment_down_time += float(down_time[str(inverter.name)])
                #         except:
                #             continue
                #     try:
                #         average_equipment_down_time = equipment_down_time/len(inverters)
                #     except:
                #         average_equipment_down_time = 0.0
                #     if current_time > grid_shut_time:
                #         equipment_availability = (((11*60)-average_equipment_down_time)/(11*60))*100
                #     else:
                #         total_minutes = float(((current_time - grid_start_time).total_seconds())/60)
                #         equipment_availability = ((total_minutes-average_equipment_down_time)/total_minutes)*100
                # except exception as exception:
                #     equipment_availability = 100.0

                # Tickets
                t_stats = get_plant_tickets(plant)
                if t_stats != -1:
                    unacknowledged_tickets = len(t_stats['open_unassigned_tickets'])
                    open_tickets = len(t_stats['open_assigned_tickets'])
                    closed_tickets = len(t_stats['tickets_closed_resolved'])
                else:
                    unacknowledged_tickets = 0
                    open_tickets = 0
                    closed_tickets = 0

                # Total generation
                try:
                    total_generation = calculate_total_plant_generation(plant)
                except:
                    total_generation = 0.0

                # Today's generation
                try:
                    if hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed:
                        plant_generation_today = get_energy_meter_values(plant_start_time, plant_start_time+datetime.timedelta(hours=24), plant, "DAY")
                    else:
                        #plant_generation_today = get_aggregated_energy(plant_start_time, plant_start_time+datetime.timedelta(hours=24), plant, "DAY")
                        plant_generation_today = get_minutes_aggregated_energy(plant_start_time, plant_start_time+datetime.timedelta(hours=24), plant, "DAY",1)
                    #plant_generation_today = plant_generation_today[0]["energy"]
                    plant_generation_today = plant_generation_today[len(plant_generation_today)-1]["energy"]
                except:
                    plant_generation_today = 0.0

                # CO2 savings
                co2_savings = plant_generation_today*0.7

                # current active power
                ts = current_time
                try:
                    delay_mins=2
                    if plant.slug == "fsindiadevcoltd":
                        values = get_plant_power(ts - datetime.timedelta(minutes=plant.metadata.timeoutInterval/60),
                                                 ts - datetime.timedelta(minutes=delay_mins),
                                                 plant)
                    else:
                        values = get_plant_power(ts-datetime.timedelta(minutes=30),
                                                 ts - datetime.timedelta(minutes=delay_mins),
                                                 plant)
                    if len(values) > 0:
                        current_power = float(values[-1]["power"])
                    else:
                        current_power = 0.0
                except Exception as exc:
                    current_power = 0.0

                # irradiation values
                ts = current_time
                try:
                    if plant.metadata:
                        irradiation = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                              stream_name = 'IRRADIATION',
                                                                              timestamp_in_data__lte=ts,
                                                                              timestamp_in_data__gte=ts-datetime.timedelta(seconds=plant.metadata.timeoutInterval)).limit(1)
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
                                                                                  timestamp_in_data__gte=ts-datetime.timedelta(seconds=plant.metadata.timeoutInterval)).limit(1)
                            if irradiation:
                                irradiation = irradiation[0].stream_value
                            else:
                                irradiation = 0.0
                    except Exception as exc:
                        irradiation = 0.0

                # wind speed
                windspeed = 0.0
                try:
                    if plant.metadata:
                        windspeed = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                            stream_name = 'WINDSPEED',
                                                                            timestamp_in_data__lte=ts,
                                                                            timestamp_in_data__gte=ts-datetime.timedelta(seconds=plant.metadata.timeoutInterval)).limit(1)
                        if windspeed:
                            windspeed = windspeed[0].stream_value
                        else:
                            windspeed = 0.0
                except Exception as exc:
                    windspeed = 0.0

                # get module temperature data
                mt = 0.0
                try:
                    if plant.metadata:
                        mt = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                     stream_name = 'MODULE_TEMPERATURE',
                                                                     timestamp_in_data__lte=ts,
                                                                     timestamp_in_data__gte=ts-datetime.timedelta(seconds=plant.metadata.timeoutInterval)).limit(1)
                        if mt:
                            mt = mt[0].stream_value
                        else:
                            mt = 0.0
                except Exception as exc:
                    mt = 0.0

                # Ambient temperature
                ambient_temperature = 0.0
                try:
                    if plant.metadata:
                        ambient_temperature = ValidDataStorageByStream.objects.filter(source_key = plant.metadata.sourceKey,
                                                                                      stream_name = 'AMBIENT_TEMPERATURE',
                                                                                      timestamp_in_data__lte=ts,
                                                                                      timestamp_in_data__gte=ts-datetime.timedelta(seconds=plant.metadata.timeoutInterval)).limit(1)
                        if ambient_temperature:
                            ambient_temperature = ambient_temperature[0].stream_value
                        else:
                            ambient_temperature = 0.0
                except Exception as exc:
                    ambient_temperature = 0.0

                # connection status of inverters
                try:
                    stats = get_user_data_monitoring_status(plant.independent_inverter_units.all().filter(isActive=True))
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
                    if unmonitored is not 0 :
                        status = 'unmonitored'
                    elif errors_len is not 0:
                        status = 'disconnected'
                    else:
                        status = 'connected'
                except Exception as exception:
                    print("Error in getting the connection status of inverters : " + str(exception))

                # connection status of SMB's
                try:
                    smb_stats = get_user_data_monitoring_status(plant.ajb_units.all().filter(isActive=True))
                    if smb_stats is not None:
                        smb_active_alive_valid, smb_active_alive_invalid, smb_active_dead, smb_deactivated_alive, smb_deactivated_dead, smb_unmonitored = smb_stats
                        smb_stable_len = len(smb_active_alive_valid) + len(smb_deactivated_dead)
                        smb_warnings_len = len(smb_active_alive_invalid)
                        smb_errors_len = len(smb_active_dead) + len(smb_deactivated_alive)
                        smb_unmonitored = len(smb_unmonitored)
                    else:
                        smb_stable_len = 0
                        smb_warnings_len = 0
                        smb_errors_len = 0
                        smb_unmonitored = 0
                except Exception as exception:
                    print("Error in getting the connection status of inverters : " + str(exception))

                # last 7 days energy values
                final_time = current_time
                initial_time = current_time - datetime.timedelta(days=7)
                #past_energy_values = collections.OrderedDict()
                past_energy_values_list = []
                try:
                    energy_values = HistoricEnergyValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                        identifier=plant.slug,
                                                                        ts__gte=initial_time,
                                                                        ts__lte=final_time).order_by('ts')
                    for value in energy_values:
                        past_energy_values = {}
                        past_energy_values['timestamp'] = str(value.ts)
                        past_energy_values['energy'] = value.energy
                        past_energy_values_list.append(past_energy_values)
                    if len(past_energy_values_list) is not 7:
                        today_date = update_tz(current_time.replace(hour=0, minute=0, second=0, microsecond=0), pytz.utc._tzname)
                        past_energy_values_today = {}
                        past_energy_values_today['timestamp'] = str(today_date).split("+",2)[0]
                        past_energy_values_today['energy'] = plant_generation_today
                        past_energy_values_list.append(past_energy_values_today)
                    else:
                        today_date = update_tz(current_time.replace(hour=0, minute=0, second=0, microsecond=0), pytz.utc._tzname)
                        past_energy_values_today = {}
                        past_energy_values_today['timestamp'] = str(today_date).split("+",2)[0]
                        past_energy_values_today['energy'] = plant_generation_today
                        if len(past_energy_values_list)>0:
                            past_energy_values_list.remove((past_energy_values_list[len(past_energy_values_list)-1]))
                        past_energy_values_list.append(past_energy_values_today)
                except Exception as exception:
                    print('Error in getting the energy values for past days : {0}'.format(str(exception)))


                # last 7 days PR value
                #past_pr_values = collections.OrderedDict()
                past_pr_values_list = []
                try:
                    pr_values = PerformanceRatioTable.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier = plant.metadata.plantmetasource.sourceKey,
                                                                     ts__gte=initial_time,
                                                                     ts__lte=final_time).order_by('ts')
                    for value in pr_values:
                        past_pr_values = {}
                        past_pr_values['timestamp'] = str(value.ts)
                        past_pr_values['pr'] = value.performance_ratio
                        past_pr_values_list.append(past_pr_values)

                    today_date = update_tz(current_time.replace(hour=0, minute=0, second=0, microsecond=0), pytz.utc._tzname)
                    past_pr_values_today = {}
                    past_pr_values_today['timestamp'] = str(today_date).split("+",2)[0]
                    past_pr_values_today['pr'] = pr
                    if len(past_pr_values_list)>0 and len(past_pr_values_list) is 7:
                        past_pr_values_list.remove(past_pr_values_list[len(past_pr_values_list)-1])
                    past_pr_values_list.append(past_pr_values_today)
                except Exception as exception:
                    print('Error in getting past PR values : {0}'.format(str(exception)))

                # past 7 days cuf
                #past_cuf_values = collections.OrderedDict()
                past_cuf_values_list = []
                try:
                    cuf_values = CUFTable.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                         count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                         identifier = plant.metadata.plantmetasource.sourceKey,
                                                         ts__gte=initial_time,
                                                         ts__lte=final_time).order_by('ts')
                    for value in cuf_values:
                        past_cuf_values = {}
                        past_cuf_values['timestamp'] = str(value.ts)
                        past_cuf_values['cuf'] = value.CUF
                        past_cuf_values_list.append(past_cuf_values)

                    today_date = update_tz(current_time.replace(hour=0, minute=0, second=0, microsecond=0), pytz.utc._tzname)
                    past_cuf_values_today = {}
                    past_cuf_values_today['timestamp'] = str(today_date).split("+",2)[0]
                    past_cuf_values_today['cuf'] = cuf
                    if len(past_cuf_values_list)>0 and len(past_cuf_values_list) is 7:
                        past_cuf_values_list.remove(past_cuf_values_list[len(past_cuf_values_list)-1])
                    past_cuf_values_list.append(past_cuf_values_today)
                except Exception as exception:
                    print('Error in getting past PR values : {0}'.format(str(exception)))

                # past 7 days grid availability
                #past_availability_values = collections.OrderedDict()
                past_grid_unavailability_values_list = []
                try:
                    availability_values = PlantDownTime.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                       count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                                       identifier = plant.metadata.plantmetasource.sourceKey,
                                                                       ts__gte=initial_time,
                                                                       ts__lte=final_time).order_by('ts')
                    for value in availability_values:
                        past_unavailability_values = {}
                        past_unavailability_values['timestamp'] = str(value.ts)
                        past_unavailability_values['unavailability'] = float(100.0 - ((11*60-float(value.down_time))/(11*60))*100)
                        past_grid_unavailability_values_list.append(past_unavailability_values)

                    today_date = update_tz(current_time.replace(hour=0, minute=0, second=0, microsecond=0), pytz.utc._tzname)
                    past_unavailability_values_today = {}
                    past_unavailability_values_today['timestamp'] = str(today_date).split("+",2)[0]
                    past_unavailability_values_today['unavailability'] = float(100.0 - grid_availability)
                    if len(past_grid_unavailability_values_list) >0 and len(past_grid_unavailability_values_list) is 7:
                        past_grid_unavailability_values_list.remove(past_grid_unavailability_values_list[len(past_grid_unavailability_values_list)-1])
                    past_grid_unavailability_values_list.append(past_unavailability_values_today)

                except Exception as exception:
                    print('Error in getting the past grid availability data : ' + str(exception))

                # past 7 days equipment availability
                final_equipment_unavailability_list = []
                past_equipment_unavailability_values_list = []
                final_df_past_equipment_unavailability = pd.DataFrame()
                df_past_equipment_unavailability = pd.DataFrame()
                try:
                    for inverter in inverters:
                        equipment_availability_values = PlantDownTime.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier = inverter.sourceKey,
                                                                                     ts__gte=initial_time,
                                                                                     ts__lte=final_time).order_by('ts')
                        values_down_time = []
                        values_timestamp = []
                        for value in equipment_availability_values:
                            values_timestamp.append(value.ts)
                            values_down_time.append(value.down_time)
                        past_equipment_unavailability_values_list.append(pd.DataFrame({'timestamp': pd.to_datetime(values_timestamp),
                                                                                       inverter.name: values_down_time}))
                    if len(past_equipment_unavailability_values_list) > 0:
                        df_past_equipment_unavailability = past_equipment_unavailability_values_list[0]
                        for i in range(1, len(past_equipment_unavailability_values_list)):
                            df_past_equipment_unavailability = df_past_equipment_unavailability.merge(past_equipment_unavailability_values_list[i], how='outer', on='timestamp')
                except Exception as exception:
                    print("Error in getting past equipment availability data : {0}".format(str(exception)))

                list_past_equipment_values = []
                list_past_equipment_timestamp = []
                if not df_past_equipment_unavailability.empty:
                    final_df_past_equipment_unavailability['equipment_down_time'] = df_past_equipment_unavailability.sum(axis=1)/len(inverters)
                    final_df_past_equipment_unavailability['timestamp'] = df_past_equipment_unavailability['timestamp']
                    list_past_equipment_values = list(final_df_past_equipment_unavailability['equipment_down_time'])
                    list_past_equipment_timestamp = list(final_df_past_equipment_unavailability['timestamp'])

                for i in range(len(list_past_equipment_timestamp)):
                    past_equipment_values = {}
                    past_equipment_values['timestamp'] = str(list_past_equipment_timestamp[i])
                    past_equipment_values['unavailability'] = float(100.0 - ((11*60-float(list_past_equipment_values[i]))/(11*60))*100)
                    final_equipment_unavailability_list.append(past_equipment_values)

                today_date = update_tz(current_time.replace(hour=0, minute=0, second=0, microsecond=0), pytz.utc._tzname)
                past_equipment_unavailability_values_today = {}
                past_equipment_unavailability_values_today['timestamp'] = str(today_date).split("+",2)[0]
                past_equipment_unavailability_values_today['unavailability'] = float(100.0 - equipment_availability)
                if len(final_equipment_unavailability_list) >0 and len(final_equipment_unavailability_list) is 7:
                    final_equipment_unavailability_list.remove(final_equipment_unavailability_list[len(final_equipment_unavailability_list)-1])
                final_equipment_unavailability_list.append(past_equipment_unavailability_values_today)

                # Past 7 days energy losses
                dc_energy_loss_list = []
                conversion_loss_list = []
                ac_energy_loss_list = []
                try:
                    energy_loss_values = EnergyLossTableNew.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                                        identifier=plant.metadata.plantmetasource.sourceKey,
                                                                        ts__gte=initial_time,
                                                                        ts__lte=final_time).order_by('ts')
                except:
                    energy_loss_values = []
                for value in energy_loss_values:
                    dc_loss = {}
                    conversion_loss = {}
                    ac_loss = {}
                    dc_loss['timestamp'] = str(value.ts)
                    dc_loss['dc_energy_loss'] = value.dc_energy_loss if value.dc_energy_loss and value.dc_energy_loss is not 'NA' else 0.0
                    conversion_loss['timestamp'] =  str(value.ts)
                    conversion_loss['conversion_loss'] = value.conversion_loss if value.conversion_loss and value.conversion_loss is not 'NA' else 0.0
                    ac_loss['timestamp'] = str(value.ts)
                    ac_loss['ac_energy_loss'] = value.ac_energy_loss if value.ac_energy_loss and value.ac_energy_loss is not 'NA' else 0.0
                    dc_energy_loss_list.append(dc_loss)
                    conversion_loss_list.append(conversion_loss)
                    ac_energy_loss_list.append(ac_loss)

                dc_loss = dc_energy_loss_list[len(dc_energy_loss_list)-1]['dc_energy_loss'] if len(dc_energy_loss_list) is 7 else 0.0
                conversion_loss = conversion_loss_list[len(conversion_loss_list)-1]['conversion_loss'] if len(conversion_loss_list) is 7 else 0.0
                ac_loss = ac_energy_loss_list[len(ac_energy_loss_list)-1]['ac_energy_loss'] if len(ac_energy_loss_list) is 7 else 0.0

                # updating client parameters
                total_client_capacity += float(plant.capacity)
                total_client_energy += float(total_generation)
                total_client_energy_today += float(plant_generation_today)
                total_client_co2 += float(co2_savings)
                if 0.0 < pr <= 1.0:
                    total_client_pr += float(pr)
                    pr_count += 1
                if cuf > 0.0:
                    total_client_cuf += float(cuf)
                    cuf_count += 1
                total_client_grid_availability += float(grid_availability)
                total_client_equipment_availability += float(equipment_availability)
                total_client_unacknowledged_tickets += int(unacknowledged_tickets)
                total_client_open_tickets += int(open_tickets)
                total_client_closed_tickets += int(closed_tickets)
                total_client_active_power += float(current_power)
                if irradiation > 0.0:
                    total_client_irradiation += float(irradiation)
                    irradiation_count += 1
                total_client_connected_inverters += int(stable_len)
                total_client_disconnected_inverters += int(errors_len)
                total_client_invalid_inverters += int(warnings_len)
                total_client_unmonitored_inverters += int(unmonitored)
                total_client_connected_smbs += int(smb_stable_len)
                total_client_disconnected_smbs += int(smb_errors_len)
                total_client_invalid_smbs += int(smb_warnings_len)
                total_client_unmonitored_smbs += int(smb_unmonitored)
                total_client_dc_loss += dc_loss
                total_client_conversion_loss += conversion_loss
                total_client_ac_loss += ac_loss

                if len(client_past_generations) == 0 :
                    client_past_generations = copy.deepcopy(past_energy_values_list)
                else:
                    for i in range(len(client_past_generations)):
                        try:
                            client_past_generations[i]['energy'] = float(str(client_past_generations[i]['energy']).split(' ')[0]) + float(str(past_energy_values_list[i]['energy']))
                        except:
                            continue

                if len(client_past_pr) == 0:
                    client_past_pr = past_pr_values_list
                else:
                    for i in range(len(client_past_pr)):
                        try:
                            if client_past_pr[i]['pr'] == 0.0:
                                client_past_pr[i]['pr'] =  past_pr_values_list[i]['pr']
                            elif past_pr_values[i]['pr'] > 0.0 and past_pr_values_list[i]['pr'] < 1.0:
                                client_past_pr[i]['pr'] = (float(str(client_past_pr[i]['pr'])) + float(str(past_pr_values_list[i]['pr'])))/2
                            else:
                                pass
                        except:
                            continue

                if len(client_past_cuf) == 0:
                    client_past_cuf = past_cuf_values_list
                else:
                    for i in range(len(client_past_cuf)):
                        try:
                            if client_past_cuf[i]['cuf'] == 0.0:
                                client_past_cuf[i]['cuf'] =  past_cuf_values_list[i]['cuf']
                            elif past_cuf_values_list[i]['cuf'] > 0.0 and past_cuf_values_list[i]['cuf'] < 1.0:
                                client_past_cuf[i]['cuf'] = (float(str(client_past_cuf[i]['cuf'])) + float(str(past_cuf_values_list[i]['cuf'])))/2
                            else:
                                pass
                        except:
                            continue

                if len(client_past_grid_unavailability) == 0:
                    client_past_grid_unavailability = past_grid_unavailability_values_list
                else:
                    for i in range(len(client_past_grid_unavailability)):
                        try:
                            client_past_grid_unavailability[i]['unavailability'] = (float(str(client_past_grid_unavailability[i]['unavailability']).split(' ')[0]) + float(str(past_grid_unavailability_values_list[i]['unavailability'])))/2
                        except Exception as exception:
                            print(str(exception))
                            continue

                if len(client_past_equipment_unavailability) == 0:
                    client_past_equipment_unavailability = final_equipment_unavailability_list
                else:
                    for i in range(len(client_past_equipment_unavailability)):
                        try:
                            client_past_equipment_unavailability[i]['unavailability'] = (float(str(client_past_equipment_unavailability[i]['unavailability']).split(' ')[0]) + float(str(final_equipment_unavailability_list[i]['unavailability'])))/2
                        except Exception as exception:
                            print(str(exception))
                            continue

                if len(client_past_dc_loss) == 0 :
                    client_past_dc_loss = dc_energy_loss_list
                else:
                    for i in range(len(client_past_dc_loss)):
                        try:
                            client_past_dc_loss[i]['dc_energy_loss'] = float(str(client_past_dc_loss[i]['dc_energy_loss']).split(' ')[0]) + float(str(dc_energy_loss_list[i]['dc_energy_loss']))
                        except:
                            continue

                if len(client_past_conversion_loss) == 0 :
                    client_past_conversion_loss = conversion_loss_list
                else:
                    for i in range(len(client_past_conversion_loss)):
                        try:
                            client_past_conversion_loss[i]['conversion_loss'] = float(str(client_past_conversion_loss[i]['conversion_loss']).split(' ')[0]) + float(str(conversion_loss_list[i]['conversion_loss']))
                        except:
                            continue

                if len(client_past_ac_loss) == 0 :
                    client_past_ac_loss = ac_energy_loss_list
                else:
                    for i in range(len(client_past_ac_loss)):
                        try:
                            client_past_ac_loss[i]['ac_energy_loss'] = float(str(client_past_ac_loss[i]['ac_energy_loss']).split(' ')[0]) + float(str(ac_energy_loss_list[i]['ac_energy_loss']))
                        except:
                            continue

                for index in range(len(past_energy_values_list)):
                    past_energy_values_list[index]['energy'] = fix_generation_units(float(past_energy_values_list[index]['energy']))

                past_energy_values_list = convert_values_to_common_unit(past_energy_values_list)

                for index in range(len(past_pr_values_list)):
                    past_pr_values_list[index]['pr'] = "{0:.2f}".format(past_pr_values_list[index]['pr'])
                for index in range(len(past_cuf_values_list)):
                    past_cuf_values_list[index]['cuf'] = "{0:.2f}".format(past_cuf_values_list[index]['cuf'])
                for index in range(len(past_grid_unavailability_values_list)):
                    past_grid_unavailability_values_list[index]['unavailability'] = str("{0:.2f}".format(past_grid_unavailability_values_list[index]['unavailability'])) + " %"
                for index in range(len(final_equipment_unavailability_list)):
                    final_equipment_unavailability_list[index]['unavailability'] = str("{0:.2f}".format(final_equipment_unavailability_list[index]['unavailability'])) + " %"
                for index in range(len(dc_energy_loss_list)):
                    dc_energy_loss_list[index]['dc_energy_loss'] = fix_generation_units(float(dc_energy_loss_list[index]['dc_energy_loss']))
                for index in range(len(conversion_loss_list)):
                    conversion_loss_list[index]['conversion_loss'] = fix_generation_units(float(conversion_loss_list[index]['conversion_loss']))
                for index in range(len(ac_energy_loss_list)):
                    ac_energy_loss_list[index]['ac_energy_loss'] = fix_generation_units(float(ac_energy_loss_list[index]['ac_energy_loss']))


                try:
                    try:
                        daily_entry = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant.metadata.plantmetasource.sourceKey,
                                                                         ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0)).limit(1)
                    except:
                        daily_entry = []

                    if len(daily_entry) == 0:
                        try:
                            daily_plant_values = PlantCompleteValues.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=plant.metadata.plantmetasource.sourceKey,
                                                                                    ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                    name=plant_name,
                                                                                    capacity=plant_capacity,
                                                                                    location=plant_location,
                                                                                    latitude=latitude,
                                                                                    longitude=longitude,
                                                                                    pr=pr,
                                                                                    cuf=cuf,
                                                                                    grid_unavailability=(100.0 - grid_availability),
                                                                                    equipment_unavailability=(100.0 - equipment_availability),
                                                                                    unacknowledged_tickets=unacknowledged_tickets,
                                                                                    open_tickets=open_tickets,
                                                                                    closed_tickets=closed_tickets,
                                                                                    total_generation=total_generation,
                                                                                    plant_generation_today=plant_generation_today,
                                                                                    co2_savings=co2_savings,
                                                                                    active_power=current_power,
                                                                                    irradiation=irradiation,
                                                                                    connected_inverters=stable_len,
                                                                                    disconnected_inverters=errors_len,
                                                                                    invalid_inverters=warnings_len,
                                                                                    connected_smbs=smb_stable_len,
                                                                                    disconnected_smbs=smb_errors_len,
                                                                                    invalid_smbs=smb_warnings_len,
                                                                                    windspeed=windspeed,
                                                                                    ambient_temperature=ambient_temperature,
                                                                                    module_temperature=mt,
                                                                                    dc_loss=dc_loss,
                                                                                    conversion_loss=conversion_loss,
                                                                                    ac_loss=ac_loss,
                                                                                    status=status,
                                                                                    past_generations=str(past_energy_values_list),
                                                                                    past_pr=str(past_pr_values_list),
                                                                                    past_cuf=str(past_cuf_values_list),
                                                                                    past_grid_unavailability=str(past_grid_unavailability_values_list),
                                                                                    past_equipment_unavailability=str(final_equipment_unavailability_list),
                                                                                    past_dc_loss=str(dc_energy_loss_list),
                                                                                    past_conversion_loss=str(conversion_loss_list),
                                                                                    past_ac_loss=str(ac_energy_loss_list),
                                                                                    updated_at=current_time)
                            daily_plant_values.save()
                        except Exception as exception:
                            print("inside exception")
                            print(str(exception))
                            try:
                                daily_plant_values = PlantCompleteValues.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                        identifier=plant.metadata.plantmetasource.sourceKey,
                                                                                        ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                        name=plant_name,
                                                                                        capacity=plant_capacity,
                                                                                        location=plant_location,
                                                                                        latitude=latitude,
                                                                                        longitude=longitude,
                                                                                        pr=0.0,
                                                                                        cuf=cuf,
                                                                                        grid_unavailability=(100.0 - grid_availability),
                                                                                        equipment_unavailability=(100.0 - equipment_availability),
                                                                                        unacknowledged_tickets=unacknowledged_tickets,
                                                                                        open_tickets=open_tickets,
                                                                                        closed_tickets=closed_tickets,
                                                                                        total_generation=total_generation,
                                                                                        plant_generation_today=plant_generation_today,
                                                                                        co2_savings=co2_savings,
                                                                                        active_power=current_power,
                                                                                        irradiation=irradiation,
                                                                                        connected_inverters=stable_len,
                                                                                        disconnected_inverters=errors_len,
                                                                                        invalid_inverters=warnings_len,
                                                                                        connected_smbs=smb_stable_len,
                                                                                        disconnected_smbs=smb_errors_len,
                                                                                        invalid_smbs=smb_warnings_len,
                                                                                        windspeed=windspeed,
                                                                                        ambient_temperature=ambient_temperature,
                                                                                        module_temperature=mt,
                                                                                        dc_loss=dc_loss,
                                                                                        conversion_loss=conversion_loss,
                                                                                        ac_loss=ac_loss,
                                                                                        status=status,
                                                                                        past_generations=str(past_energy_values_list),
                                                                                        past_pr=str(past_pr_values_list),
                                                                                        past_cuf=str(past_cuf_values_list),
                                                                                        past_grid_unavailability=str(past_grid_unavailability_values_list),
                                                                                        past_equipment_unavailability=str(final_equipment_unavailability_list),
                                                                                        past_dc_loss=str(dc_energy_loss_list),
                                                                                        past_conversion_loss=str(conversion_loss_list),
                                                                                        past_ac_loss=str(ac_energy_loss_list),
                                                                                        updated_at=current_time)
                                daily_plant_values.save()
                            except:
                                pass

                    else:
                        try:
                            daily_entry.update(name=plant_name,
                                               capacity=plant_capacity,
                                               location=plant_location,
                                               latitude=latitude,
                                               longitude=longitude,
                                               pr=pr,
                                               cuf=cuf,
                                               grid_unavailability=(100.0 - grid_availability),
                                               equipment_unavailability=(100.0 - equipment_availability),
                                               unacknowledged_tickets=unacknowledged_tickets,
                                               open_tickets=open_tickets,
                                               closed_tickets=closed_tickets,
                                               total_generation=total_generation,
                                               plant_generation_today=plant_generation_today,
                                               co2_savings=co2_savings,
                                               active_power=current_power,
                                               irradiation=irradiation,
                                               connected_inverters=stable_len,
                                               disconnected_inverters=errors_len,
                                               invalid_inverters=warnings_len,
                                               connected_smbs=smb_stable_len,
                                               disconnected_smbs=smb_errors_len,
                                               invalid_smbs=smb_warnings_len,
                                               windspeed=windspeed,
                                               ambient_temperature=ambient_temperature,
                                               module_temperature=mt,
                                               dc_loss=dc_loss,
                                               conversion_loss=conversion_loss,
                                               ac_loss=ac_loss,
                                               status=status,
                                               past_generations = str(past_energy_values_list),
                                               past_pr=str(past_pr_values_list),
                                               past_cuf=str(past_cuf_values_list),
                                               past_grid_unavailability=str(past_grid_unavailability_values_list),
                                               past_equipment_unavailability=str(final_equipment_unavailability_list),
                                               past_dc_loss=str(dc_energy_loss_list),
                                               past_conversion_loss=str(conversion_loss_list),
                                               past_ac_loss=str(ac_energy_loss_list),
                                               updated_at=current_time)
                        except Exception as exception:
                            print(str(exception))
                            daily_entry.update(name=plant_name,
                                               capacity=plant_capacity,
                                               location=plant_location,
                                               latitude=latitude,
                                               longitude=longitude,
                                               pr=0.0,
                                               cuf=cuf,
                                               grid_unavailability=(100.0 - grid_availability),
                                               equipment_unavailability=(100.0 - equipment_availability),
                                               unacknowledged_tickets=unacknowledged_tickets,
                                               open_tickets=open_tickets,
                                               closed_tickets=closed_tickets,
                                               total_generation=total_generation,
                                               plant_generation_today=plant_generation_today,
                                               co2_savings=co2_savings,
                                               active_power=current_power,
                                               irradiation=irradiation,
                                               connected_inverters=stable_len,
                                               disconnected_inverters=errors_len,
                                               invalid_inverters=warnings_len,
                                               connected_smbs=smb_stable_len,
                                               disconnected_smbs=smb_errors_len,
                                               invalid_smbs=smb_warnings_len,
                                               windspeed=windspeed,
                                               ambient_temperature=ambient_temperature,
                                               module_temperature=mt,
                                               dc_loss=dc_loss,
                                               conversion_loss=conversion_loss,
                                               ac_loss=ac_loss,
                                               status=status,
                                               past_generations = str(past_energy_values_list),
                                               past_pr=str(past_pr_values_list),
                                               past_cuf=str(past_cuf_values_list),
                                               past_grid_unavailability=str(past_grid_unavailability_values_list),
                                               past_equipment_unavailability=str(final_equipment_unavailability_list),
                                               past_dc_loss=str(dc_energy_loss_list),
                                               past_conversion_loss=str(conversion_loss_list),
                                               past_ac_loss=str(ac_energy_loss_list),
                                               updated_at=current_time)
                except Exception as exception:
                    print("Error in saving plant parameters : " + str(exception))
                plant_log_stop_time = time.time() - plant_log_start_time
                print("--- %s seconds --- %s" % (plant_log_stop_time, plant.slug))
            try:
                if total_client_unmonitored_inverters is not 0 :
                    status = 'unmonitored'
                elif total_client_disconnected_inverters is not 0:
                    status = 'disconnected'
                else:
                    status = 'connected'
                client_pr = float(total_client_pr)/pr_count if total_client_pr and pr_count is not 0 else 0.0
                client_cuf = float(total_client_cuf)/cuf_count if total_client_cuf and cuf_count is not 0 else 0.0
                client_grid_availability = total_client_grid_availability/availability_count if total_client_grid_availability and availability_count is not 0 else 100.0
                client_equipment_availability = total_client_equipment_availability/availability_count if total_client_equipment_availability and availability_count is not 0 else 100.0
                client_irradiation = float(total_client_irradiation)/irradiation_count if total_client_irradiation and irradiation_count is not 0 else 0.0
                if len(client_past_generations)>0:
                    client_past_generations[len(client_past_generations)-1]['energy'] = total_client_energy_today
                if len(client_past_pr)>0:
                    client_past_pr[len(client_past_pr)-1]['pr'] = client_pr
                if len(client_past_cuf)>0:
                    client_past_cuf[len(client_past_cuf)-1]['cuf'] = client_cuf
                if len(client_past_grid_unavailability)>0:
                    client_past_grid_unavailability[len(client_past_grid_unavailability)-1]['unavailability'] = (100.0 - float(client_grid_availability))
                if len(client_past_equipment_unavailability)>0:
                    client_past_equipment_unavailability[len(client_past_equipment_unavailability)-1]['unavailability'] = (100.0 - float(client_equipment_availability))

                for index in range(len(client_past_generations)):
                    try:
                        client_past_generations[index]['energy'] = fix_generation_units(float(str(client_past_generations[index]['energy']).split(' ')[0]))
                    except Exception as exception:
                        print("Energy error : " + str(exception))
                        client_past_generations[index]['energy'] = "0.0 kWh"
                        continue

                client_past_generations = convert_values_to_common_unit(client_past_generations)

                for index in range(len(client_past_pr)):
                    try:
                        client_past_pr[index]['pr'] = "{0:.2f}".format(float(client_past_pr[index]['pr']))
                    except Exception as exception:
                        print("pr exception : " + str(exception))
                        client_past_pr[index]['pr'] = 0.0
                        continue

                for index in range(len(client_past_cuf)):
                    try:
                        client_past_cuf[index]['cuf'] = "{0:.2f}".format(float(client_past_cuf[index]['cuf']))
                    except:
                        client_past_cuf[index]['cuf'] = 0.0
                        continue

                for index in range(len(client_past_grid_unavailability)):
                    try:
                        client_past_grid_unavailability[index]['unavailability'] = str("{0:.2f}".format(float(str(client_past_grid_unavailability[index]['unavailability']).split(' ')[0]))) + " %"
                    except Exception as exception:
                        print("availability exception : " + str(exception))
                        client_past_grid_unavailability[index]['unavailability'] = " 0.0 %"
                        continue

                for index in range(len(client_past_equipment_unavailability)):
                    try:
                        client_past_equipment_unavailability[index]['unavailability'] = str("{0:.2f}".format(float(str(client_past_equipment_unavailability[index]['unavailability']).split(' ')[0]))) + " %"
                    except Exception as exception:
                        print("availability exception : " + str(exception))
                        client_past_equipment_unavailability[index]['unavailability'] = " 0.0 %"
                        continue

                for index in range(len(client_past_dc_loss)):
                    try:
                        client_past_dc_loss[index]['dc_energy_loss'] = fix_generation_units(float(str(client_past_dc_loss[index]['dc_energy_loss']).split(' ')[0]))
                    except Exception as exception:
                        print("DC loss error : " + str(exception))
                        client_past_dc_loss[index]['dc_energy_loss'] = "0.0 kWh"
                        continue

                for index in range(len(client_past_conversion_loss)):
                    try:
                        client_past_conversion_loss[index]['conversion_loss'] = fix_generation_units(float(str(client_past_conversion_loss[index]['conversion_loss']).split(' ')[0]))
                    except Exception as exception:
                        print("conversion loss error : " + str(exception))
                        client_past_conversion_loss[index]['conversion_loss'] = "0.0 kWh"
                        continue

                for index in range(len(client_past_ac_loss)):
                    try:
                        client_past_ac_loss[index]['ac_energy_loss'] = fix_generation_units(float(str(client_past_ac_loss[index]['ac_energy_loss']).split(' ')[0]))
                    except Exception as exception:
                        print("Energy error : " + str(exception))
                        client_past_ac_loss[index]['ac_energy_loss'] = "0.0 kWh"
                        continue

                daily_client_entry = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                        identifier=client.slug,
                                                                        ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0)).limit(1)
                if len(daily_client_entry) == 0:
                    daily_client_values = PlantCompleteValues.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                             identifier=client.slug,
                                                                             ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                             name=client.name,
                                                                             capacity=total_client_capacity,
                                                                             pr=client_pr,
                                                                             cuf=client_cuf,
                                                                             grid_unavailability=(100.0 - client_grid_availability),
                                                                             equipment_unavailability=(100.0 - client_equipment_availability),
                                                                             unacknowledged_tickets=total_client_unacknowledged_tickets,
                                                                             open_tickets=total_client_open_tickets,
                                                                             closed_tickets=total_client_closed_tickets,
                                                                             total_generation=total_client_energy,
                                                                             plant_generation_today=total_client_energy_today,
                                                                             co2_savings=total_client_co2,
                                                                             active_power=total_client_active_power,
                                                                             irradiation=client_irradiation,
                                                                             connected_inverters=total_client_connected_inverters,
                                                                             disconnected_inverters=total_client_disconnected_inverters,
                                                                             invalid_inverters=total_client_invalid_inverters,
                                                                             connected_smbs=total_client_connected_smbs,
                                                                             disconnected_smbs=total_client_disconnected_smbs,
                                                                             invalid_smbs=total_client_invalid_smbs,
                                                                             dc_loss=total_client_dc_loss,
                                                                             conversion_loss=total_client_conversion_loss,
                                                                             ac_loss=total_client_ac_loss,
                                                                             status=status,
                                                                             past_generations=str(client_past_generations),
                                                                             past_pr=str(client_past_pr),
                                                                             past_cuf=str(client_past_cuf),
                                                                             past_grid_unavailability=str(client_past_grid_unavailability),
                                                                             past_equipment_unavailability=str(client_past_equipment_unavailability),
                                                                             past_dc_loss=str(client_past_dc_loss),
                                                                             past_conversion_loss=str(client_past_conversion_loss),
                                                                             past_ac_loss=str(client_past_ac_loss),
                                                                             updated_at=current_time
                                                                             )
                    daily_client_values.save()
                else:
                    daily_client_entry.update(capacity=total_client_capacity,
                                              pr=client_pr,
                                              cuf=client_cuf,
                                              grid_unavailability=(100.0 - client_grid_availability),
                                              equipment_unavailability=(100.0 - client_equipment_availability),
                                              unacknowledged_tickets=total_client_unacknowledged_tickets,
                                              open_tickets=total_client_open_tickets,
                                              closed_tickets=total_client_closed_tickets,
                                              total_generation=total_client_energy,
                                              plant_generation_today=total_client_energy_today,
                                              co2_savings=total_client_co2,
                                              active_power=total_client_active_power,
                                              irradiation=client_irradiation,
                                              connected_inverters=total_client_connected_inverters,
                                              disconnected_inverters=total_client_disconnected_inverters,
                                              invalid_inverters=total_client_invalid_inverters,
                                              connected_smbs=total_client_connected_smbs,
                                              disconnected_smbs=total_client_disconnected_smbs,
                                              invalid_smbs=total_client_invalid_smbs,
                                              dc_loss=total_client_dc_loss,
                                              conversion_loss=total_client_conversion_loss,
                                              ac_loss=total_client_ac_loss,
                                              status=status,
                                              past_generations=str(client_past_generations),
                                              past_pr=str(client_past_pr),
                                              past_cuf=str(client_past_cuf),
                                              past_grid_unavailability=str(client_past_grid_unavailability),
                                              past_equipment_unavailability=str(client_past_equipment_unavailability),
                                              past_dc_loss=str(client_past_dc_loss),
                                              past_conversion_loss=str(client_past_conversion_loss),
                                              past_ac_loss=str(client_past_ac_loss),
                                              updated_at=current_time
                                              )

            except Exception as exception:
                print("Error in saving client parameters : " + str(exception))
    except Exception as exception:
        print(str(exception))
    print("--- %s seconds ---" % (time.time() - start_time))



def get_all_plant_details_hero():
    get_all_plant_details(clients_slugs=['hero-future-energies'])


def get_all_plant_details_cleanmax():
    get_all_plant_details(clients_slugs=['cleanmax-solar', 'hcleanmax'])


def get_all_plant_details_others():
    get_all_plant_details()
