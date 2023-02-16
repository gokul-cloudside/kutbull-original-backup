import datetime
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.models import SolarPlant, PlantDeviceSummaryDetails
from dashboards.models import DataglenClient, Dashboard
from solarrms.solarutils import get_minutes_aggregated_energy
import calendar
from dataglen.models import ValidDataStorageByStream
from solarrms.settings import TOTAL_OPERATIONAL_HOURS_UNITS, TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION
import numpy as np
from  solarrms.solarutils import get_down_time
from solarrms.cron_max_values import get_max_active_power_inverter_wise, get_max_dc_power_inverter_wise
import pandas as pd

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


def calculate_working_hours_by_inverter(starttime,endtime,invsourceKey,operational_unit_factor):
    total_working_hours=0.0
    try:
        working_hours = ValidDataStorageByStream.objects.filter(source_key=invsourceKey,
                                                                stream_name='TOTAL_OPERATIONAL_HOURS',
                                                                timestamp_in_data__gte=starttime,
                                                                timestamp_in_data__lte=endtime).limit(0).order_by(
            'timestamp_in_data').values_list('timestamp_in_data', 'stream_value')

        if len(working_hours) > 0:
            # print "length of wokring hours",len(working_hours)
            try:
                df1 = pd.DataFrame(working_hours[:], columns=['timestamp_in_data', 'stream_value'])
                df1['stream_value'] = df1['stream_value'].apply(lambda x: float(x))
                df1['deltaD'] = df1['stream_value'].diff()

                df1 = df1[df1['deltaD'] > 0]

                df1['deltaTinMin'] = df1['timestamp_in_data'].diff()
                df1['deltaT'] = df1['deltaTinMin'].apply(lambda t: (t.total_seconds()))

                if operational_unit_factor == 1:
                    print "inside hour"
                    df1['deltaT'] = df1['deltaT'].apply(lambda t: (t / 3600))
                    df1 = df1[(df1['deltaD'] <= df1['deltaT'] * 2)]
                    sumD = df1['deltaD'].sum()
                    # sumT = df1['deltaT'].sum()
                    # print "sumD=",sumD,"sumT=",sumT

                    total_working_hours=sumD

                elif operational_unit_factor == 60:
                    df1['deltaT'] = df1['deltaT'].apply(lambda t: (t / 60.0))
                    df1 = df1[(df1['deltaD'] <= df1['deltaT'] * 2)]
                    sumD = df1['deltaD'].sum()
                    # sumT = df1['deltaT'].sum()
                    # print "sumD=",sumD,"sumT=",sumT

                    total_working_hours=sumD/60
                elif operational_unit_factor==3600:
                    print "inside seconds"
                    df1 = df1[(df1['deltaD'] <= df1['deltaT'] * 2)]
                    sumD = df1['deltaD'].sum()
                    # sumT = df1['deltaT'].sum()
                    # print "sumD=",sumD,"sumT=",sumT

                    total_working_hours=sumD/3600
                else:
                    print "operational_unit_factor is not defined properly"

            except:
                print "inside Exception"
                total_working_hours = 0.0
        else:
            print "No data for device"
    except Exception as exception:
        print(str(exception))
    return total_working_hours

def compute_equipment_availability_from_working_hours_daily(starttime, endtime, plant):
    try:
        try:
            try:
                operational_unit = TOTAL_OPERATIONAL_HOURS_UNITS[str(plant.slug)]
                operational_unit_factor = TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION[operational_unit]
            except:
                operational_unit_factor = 3600
            availability = {}
            equipment_availability_list = []
            max_time = (endtime - starttime).total_seconds()/3600
            max_time = max_time if max_time <= 12 else 12
            for inverter in plant.independent_inverter_units.all():
                # working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                #                                                         stream_name='TOTAL_OPERATIONAL_HOURS',
                #                                                         timestamp_in_data__gte=starttime,
                #                                                         timestamp_in_data__lte=endtime)
                # if len(working_hours)>0:
                try:
                    total_working_hours = calculate_working_hours_by_inverter(starttime,endtime,str(inverter.sourceKey),operational_unit_factor)
                    print total_working_hours
                except:
                    total_working_hours = 0.0
                if total_working_hours >= 12:
                    inverter_equipment_availability = 100
                else:
                    inverter_equipment_availability = (total_working_hours/max_time) * 100
                #equipment_availability_list.append(inverter_equipment_availability)
                try:
                    availability[str(inverter.name)] = 100 - float(inverter_equipment_availability)
                except:
                    availability[str(inverter.name)] = 0
            downtime = get_down_time(starttime, endtime, plant)
            availability['grid'] = downtime['grid']
            #plant_equipment_availability = np.mean(equipment_availability_list) if len(equipment_availability_list) > 0 else 100
            print availability
            return availability
        except Exception as exception:
            print(str(exception))
    except Exception as exception:
        print str(exception)

def compute_equipment_availability_from_working_hours_monthly(starttime, endtime, plant, inverter):
    try:
        try:
            try:
                number_of_days = (endtime - starttime).total_seconds()/86400
                operational_unit = TOTAL_OPERATIONAL_HOURS_UNITS[str(plant.slug)]
                operational_unit_factor = TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION[operational_unit]
            except:
                operational_unit_factor = 3600
            # print "operational unit factor", operational_unit_factor
            # operational_unit_factor='second'

            # working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
            #                                                         stream_name='TOTAL_OPERATIONAL_HOURS',
            #                                                         timestamp_in_data__gte=starttime,
            #                                                         timestamp_in_data__lte=endtime)
            # if len(working_hours)>0:
            try:
                total_working_hours = calculate_working_hours_by_inverter(starttime,endtime,str(inverter.sourceKey),operational_unit_factor)
                print "Total working Hours", total_working_hours
            except:
                total_working_hours = 0.0
            max_time = number_of_days*12
            print "max time",max_time
            equipment_availability = (total_working_hours/max_time) * 100
            print "equipment_availability",equipment_availability
            return equipment_availability
        except Exception as exception:
            print(str(exception))
    except Exception as exception:
        print str(exception)

def compute_inverters_summary(clients_slugs = None):
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
            print("Computing inverter summary for client: "  + str(client.name))
            plants = SolarPlant.objects.filter(groupClient=client)
            for plant  in plants:
                print("Computing for plant: " + str(plant.slug))
                if plant.isOperational and plant.metadata.plantmetasource:
                    try:
                        operational_unit = TOTAL_OPERATIONAL_HOURS_UNITS[str(plant.slug)]
                        operational_unit_factor = TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION[operational_unit]
                    except:
                        operational_unit_factor = 3600

                    inverters = plant.independent_inverter_units.all()
                    if len(inverters)>0:
                        try:
                            current_time = timezone.now()
                            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        except Exception as exc:
                            print("Error in converting the timezone" + str(exc))

                        plant_summary_last_entry = PlantDeviceSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                            identifier=str(inverters[0].sourceKey)).limit(1).values_list('ts')

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
                            initial_time_operational = last_entry_daily.replace(hour=0, minute=30, second= 0, microsecond=0)
                            final_time = last_entry_daily.replace(hour=23, minute=59, second=59, microsecond=59)
                            month_start_day = initial_time.replace(day=1)
                            month_start_day_month = month_start_day.month
                            month_start_day_year = month_start_day.year
                            no_of_days = calendar.monthrange(month_start_day_year,month_start_day_month)[1]
                            month_end_day = final_time

                            # monthly entry
                            if month_end_day.day == no_of_days:
                                print("computing for month " + str(month_end_day.month))
                                print(month_start_day)
                                print(month_end_day)
                                monthly_energy_values = get_minutes_aggregated_energy(month_start_day, month_end_day, plant, 'DAY', 1, split=True, meter_energy=False)
                                if monthly_energy_values and len(monthly_energy_values)>0:
                                    for inverter in inverters:
                                        # energy values
                                        monthly_inverter_energy = 0.0
                                        try:
                                            for i in range(len(monthly_energy_values[str(inverter.name)])):
                                                try:
                                                    monthly_inverter_energy += monthly_energy_values[str(inverter.name)][i]['energy']
                                                except:
                                                    continue
                                        except:
                                            monthly_inverter_energy = 0.0

                                        # total working hours
                                        total_monthly_working_hours = 0.0
                                        try:
                                            # monthly_working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                            #                                                                 stream_name='TOTAL_OPERATIONAL_HOURS',
                                            #                                                                 timestamp_in_data__gte=month_start_day,
                                            #                                                                 timestamp_in_data__lte=month_end_day)
                                            # if len(monthly_working_hours)>0:
                                            try:
                                                # error: list working_hours is not present, it should be monthly_working_hours
                                                total_monthly_working_hours = calculate_working_hours_by_inverter(month_start_day,month_end_day,str(inverter.sourceKey),operational_unit_factor)
                                            except:
                                                total_monthly_working_hours = 0.0
                                        except Exception as exception:
                                            print(str(exception))


                                        try:
                                            daily_monthly_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                               count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                               identifier=str(inverter.sourceKey),
                                                                                                               ts=month_start_day)
                                            try:
                                                daily_monthly_energy_entry.update(generation=monthly_inverter_energy,
                                                                                  total_working_hours=total_monthly_working_hours)
                                            except:
                                                daily_monthly_energy_entry.update(generation=monthly_inverter_energy)
                                        except Exception as exception:
                                            try:
                                                monthly_energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                                count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                                identifier=str(inverter.sourceKey),
                                                                                                                ts=month_start_day,
                                                                                                                generation=monthly_inverter_energy,
                                                                                                                total_working_hours=total_monthly_working_hours,
                                                                                                                updated_at=current_time)
                                                monthly_energy_entry.save()
                                            except:
                                                monthly_energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                                count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                                identifier=str(inverter.sourceKey),
                                                                                                                ts=month_start_day,
                                                                                                                generation=monthly_inverter_energy,
                                                                                                                updated_at=current_time)
                                                monthly_energy_entry.save()

                            # daily enery entry
                            energy_values = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, split=True, meter_energy=False)

                            max_dc_power_values = get_max_dc_power_inverter_wise(initial_time, final_time, plant)
                            max_active_power_values = get_max_active_power_inverter_wise(initial_time, final_time, plant)

                            if energy_values and len(energy_values)>0:
                                for inverter in inverters:
                                    #energy values
                                    try:
                                        inverter_energy = energy_values[str(inverter.name)][0]['energy']
                                    except:
                                        inverter_energy = 0.0

                                    # total working hours
                                    total_working_hours = 0.0
                                    # try:
                                        # working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                        #                                                         stream_name='TOTAL_OPERATIONAL_HOURS',
                                        #                                                         timestamp_in_data__gte=initial_time_operational,
                                        #                                                         timestamp_in_data__lte=final_time)
                                        # if len(working_hours)>0:
                                    try:
                                        total_working_hours = calculate_working_hours_by_inverter(initial_time_operational,final_time,str(inverter.sourceKey),operational_unit_factor)
                                    except:
                                        total_working_hours = 0.0
                                    # except Exception as exception:
                                    #     print(str(exception))

                                    try:
                                        inverter_max_dc_power= float(max_dc_power_values[str(inverter.name)])
                                    except:
                                        inverter_max_dc_power = None

                                    try:
                                        inverter_max_active_power = float(max_active_power_values[str(inverter.name)])
                                    except:
                                        inverter_max_active_power = None

                                    try:
                                        daily_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                   identifier=str(inverter.sourceKey),
                                                                                                   ts=initial_time)
                                        try:
                                            daily_energy_entry.update(generation=inverter_energy,
                                                                      total_working_hours=total_working_hours,
                                                                      max_dc_power=inverter_max_dc_power,
                                                                      max_ac_power=inverter_max_active_power,
                                                                      updated_at=current_time)
                                        except:
                                            daily_energy_entry.update(generation=inverter_energy,
                                                                      max_dc_power=inverter_max_dc_power,
                                                                      max_ac_power=inverter_max_active_power,
                                                                      updated_at=current_time)
                                    except Exception as exception:
                                        try:
                                            energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                    identifier=str(inverter.sourceKey),
                                                                                                    ts=initial_time,
                                                                                                    generation=inverter_energy,
                                                                                                    total_working_hours=total_working_hours,
                                                                                                    max_dc_power=inverter_max_dc_power,
                                                                                                    max_ac_power=inverter_max_active_power,
                                                                                                    updated_at=current_time)
                                            energy_entry.save()
                                        except:
                                            energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                    identifier=str(inverter.sourceKey),
                                                                                                    ts=initial_time,
                                                                                                    generation=inverter_energy,
                                                                                                    max_dc_power=inverter_max_dc_power,
                                                                                                    max_ac_power=inverter_max_active_power,
                                                                                                    updated_at=current_time)
                                            energy_entry.save()

                            last_entry_daily = last_entry_daily + datetime.timedelta(days=1)
                            duration_days -= 1

                        if duration_days == 0:
                            print("computing inverters energy for current day")
                            initial_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                            initial_time_operational = current_time.replace(hour=0, minute=30, second=0, microsecond=0)
                            final_time = current_time

                            # monthly entry
                            month_start_day = initial_time.replace(day=1)
                            month_end_day = final_time
                            monthly_energy_values = get_minutes_aggregated_energy(month_start_day, month_end_day, plant, 'DAY', 1, split=True, meter_energy=False)
                            if monthly_energy_values and len(monthly_energy_values)>0:
                                for inverter in inverters:
                                    # energy values
                                    monthly_inverter_energy = 0.0
                                    try:
                                        for i in range(len(monthly_energy_values[str(inverter.name)])):
                                            try:
                                                monthly_inverter_energy += monthly_energy_values[str(inverter.name)][i]['energy']
                                            except:
                                                continue
                                    except:
                                        monthly_inverter_energy = 0.0

                                    # total working hours
                                    total_monthly_working_hours = 0.0
                                    # try:
                                        # monthly_working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                        #                                                                 stream_name='TOTAL_OPERATIONAL_HOURS',
                                        #                                                                 timestamp_in_data__gte=month_start_day,
                                        #                                                                 timestamp_in_data__lte=month_end_day)
                                        # if len(monthly_working_hours)>0:
                                    try:
                                        total_monthly_working_hours = calculate_working_hours_by_inverter(month_start_day,month_end_day,str(inverter.sourceKey),operational_unit_factor)
                                    except:
                                        total_monthly_working_hours = 0.0
                                    # except Exception as exception:
                                    #     print(str(exception))

                                    try:
                                        daily_monthly_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                           count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                           identifier=str(inverter.sourceKey),
                                                                                                           ts=month_start_day)
                                        try:
                                            daily_monthly_energy_entry.update(generation=monthly_inverter_energy,
                                                                              total_working_hours=total_monthly_working_hours)
                                        except:
                                            daily_monthly_energy_entry.update(generation=monthly_inverter_energy)

                                    except Exception as exception:
                                        try:
                                            monthly_energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                            count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                            identifier=str(inverter.sourceKey),
                                                                                                            ts=month_start_day,
                                                                                                            generation=monthly_inverter_energy,
                                                                                                            total_working_hours=total_monthly_working_hours,
                                                                                                            updated_at=current_time)
                                            monthly_energy_entry.save()
                                        except:
                                            monthly_energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                            count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                            identifier=str(inverter.sourceKey),
                                                                                                            ts=month_start_day,
                                                                                                            generation=monthly_inverter_energy,
                                                                                                            updated_at=current_time)
                                            monthly_energy_entry.save()


                            # daily entry
                            energy_values = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, split=True, meter_energy=False)

                            max_dc_power_values = get_max_dc_power_inverter_wise(initial_time, final_time, plant)
                            max_active_power_values = get_max_active_power_inverter_wise(initial_time, final_time, plant)

                            print max_dc_power_values
                            print max_active_power_values

                            if energy_values and len(energy_values)>0:
                                for inverter in inverters:
                                    # energy
                                    try:
                                        inverter_energy = energy_values[str(inverter.name)][0]['energy']
                                    except:
                                        inverter_energy = 0.0

                                    # total working hours
                                    total_working_hours = 0.0
                                    # try:
                                    #     working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                    #                                                             stream_name='TOTAL_OPERATIONAL_HOURS',
                                    #                                                             timestamp_in_data__gte=initial_time_operational,
                                    #                                                             timestamp_in_data__lte=final_time)
                                    #     if len(working_hours)>0:
                                    try:
                                        total_working_hours = calculate_working_hours_by_inverter(initial_time_operational,final_time,str(inverter.sourceKey),operational_unit_factor)
                                    except:
                                        total_working_hours = 0.0
                                    # except Exception as exception:
                                    #     print(str(exception))

                                    print inverter.name

                                    try:
                                        inverter_max_dc_power= max_dc_power_values[str(inverter.name)]
                                    except:
                                        inverter_max_dc_power = None

                                    try:
                                        inverter_max_active_power = max_active_power_values[str(inverter.name)]
                                    except:
                                        inverter_max_active_power = None

                                    try:
                                        daily_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                   identifier=str(inverter.sourceKey),
                                                                                                   ts=initial_time)
                                        try:
                                            daily_energy_entry.update(generation=inverter_energy,
                                                                      total_working_hours=total_working_hours,
                                                                      max_dc_power=inverter_max_dc_power,
                                                                      max_ac_power=inverter_max_active_power,
                                                                      updated_at=current_time)
                                        except:
                                            daily_energy_entry.update(generation=inverter_energy,
                                                                      max_dc_power=inverter_max_dc_power,
                                                                      max_ac_power=inverter_max_active_power,
                                                                      updated_at=current_time)
                                    except Exception as exception:
                                        try:
                                            energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                    identifier=str(inverter.sourceKey),
                                                                                                    ts=initial_time,
                                                                                                    generation=inverter_energy,
                                                                                                    total_working_hours=total_working_hours,
                                                                                                    max_dc_power=inverter_max_dc_power,
                                                                                                    max_ac_power=inverter_max_active_power,
                                                                                                    updated_at=current_time)
                                            energy_entry.save()
                                        except:
                                            energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                    identifier=str(inverter.sourceKey),
                                                                                                    ts=initial_time,
                                                                                                    generation=inverter_energy,
                                                                                                    max_dc_power=inverter_max_dc_power,
                                                                                                    max_ac_power=inverter_max_active_power,
                                                                                                    updated_at=current_time)
                                            energy_entry.save()

    except Exception as exception:
        print(str(exception))

def compute_energy_meters_summary(clients_slugs = None):
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

        #clients = DataglenClient.objects.filter(slug='greenko-group')
        for client in clients:
            print("Computing meter summary for client: "  + str(client.name))
            plants = SolarPlant.objects.filter(groupClient=client)
            for plant  in plants:
                if len(plant.energy_meters.all())>0:
                    print("Computing for plant: " + str(plant.slug))
                    if plant.isOperational and plant.metadata.plantmetasource:
                        meters = plant.energy_meters.all()
                        try:
                            current_time = timezone.now()
                            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        except Exception as exc:
                            print("Error in converting the timezone" + str(exc))

                        plant_summary_last_entry = PlantDeviceSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                            identifier=str(meters[0].sourceKey)).limit(1).values_list('ts')

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
                            month_start_day_month = month_start_day.month
                            month_start_day_year = month_start_day.year
                            no_of_days = calendar.monthrange(month_start_day_year,month_start_day_month)[1]
                            month_end_day = final_time

                            # monthly entry
                            if month_end_day.day == no_of_days:
                                print("computing for month " + str(month_end_day.month))
                                print(month_start_day)
                                print(month_end_day)
                                monthly_energy_values = get_minutes_aggregated_energy(month_start_day, month_end_day, plant, 'DAY', 1, split=True, meter_energy=True)
                                if monthly_energy_values and len(monthly_energy_values)>0:
                                    for meter in meters:
                                        monthly_meter_energy = 0.0
                                        try:
                                            for i in range(len(monthly_energy_values[str(meter.name)])):
                                                try:
                                                    monthly_meter_energy += monthly_energy_values[str(meter.name)][i]['energy']
                                                except Exception as exception:
                                                    print(str(exception))
                                                    continue
                                        except:
                                            monthly_meter_energy = 0.0
                                        print monthly_meter_energy
                                        try:
                                            daily_monthly_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                               count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                               identifier=str(meter.sourceKey),
                                                                                                               ts=month_start_day,
                                                                                                               generation=monthly_meter_energy,
                                                                                                               updated_at=current_time)
                                            daily_monthly_energy_entry.update(generation=monthly_meter_energy)
                                        except Exception as exception:
                                            monthly_energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                            count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                            identifier=str(meter.sourceKey),
                                                                                                            ts=month_start_day,
                                                                                                            generation=monthly_meter_energy,
                                                                                                            updated_at=current_time)
                                            monthly_energy_entry.save()

                            # daily entry
                            energy_values = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, split=True, meter_energy=True)
                            if energy_values and len(energy_values)>0:
                                for meter in meters:
                                    try:
                                        meter_energy = energy_values[str(meter.name)][0]['energy']
                                    except:
                                        meter_energy = 0.0
                                    try:
                                        daily_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                   identifier=str(meter.sourceKey),
                                                                                                   ts=initial_time,
                                                                                                   generation=meter_energy,
                                                                                                   updated_at=current_time)
                                        daily_energy_entry.update(generation=meter_energy)
                                    except Exception as exception:
                                        energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                identifier=str(meter.sourceKey),
                                                                                                ts=initial_time,
                                                                                                generation=meter_energy,
                                                                                                updated_at=current_time)
                                        energy_entry.save()
                            last_entry_daily = last_entry_daily + datetime.timedelta(days=1)
                            duration_days -= 1

                        if duration_days == 0:
                            print("computing inverters energy for current day")
                            initial_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                            final_time = current_time

                            # monthly entry
                            month_start_day = initial_time.replace(day=1)
                            month_end_day = final_time
                            monthly_energy_values = get_minutes_aggregated_energy(month_start_day, month_end_day, plant, 'DAY', 1, split=True, meter_energy=True)
                            if monthly_energy_values and len(monthly_energy_values)>0:
                                for meter in meters:
                                    monthly_meter_energy = 0.0
                                    try:
                                        for i in range(len(monthly_energy_values[str(meter.name)])):
                                            try:
                                                monthly_meter_energy += monthly_energy_values[str(meter.name)][i]['energy']
                                            except:
                                                continue
                                    except:
                                        monthly_meter_energy = 0.0
                                    try:
                                        daily_monthly_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                           count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                           identifier=str(meter.sourceKey),
                                                                                                           ts=month_start_day,
                                                                                                           generation=monthly_meter_energy,
                                                                                                           updated_at=current_time)
                                        daily_monthly_energy_entry.update(generation=monthly_meter_energy)
                                    except Exception as exception:
                                        monthly_energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                                        identifier=str(meter.sourceKey),
                                                                                                        ts=month_start_day,
                                                                                                        generation=monthly_meter_energy,
                                                                                                        updated_at=current_time)
                                        monthly_energy_entry.save()

                            # daily entry
                            energy_values = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, split=True, meter_energy=True)
                            if energy_values and len(energy_values)>0:
                                for meter in meters:
                                    try:
                                        meter_energy = energy_values[str(meter.name)][0]['energy']
                                    except:
                                        meter_energy = 0.0

                                    try:
                                        daily_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                   identifier=str(meter.sourceKey),
                                                                                                   ts=initial_time,
                                                                                                   generation=meter_energy,
                                                                                                   updated_at=current_time)
                                        daily_energy_entry.update(generation=meter_energy)
                                    except Exception as exception:
                                        energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                                identifier=str(meter.sourceKey),
                                                                                                ts=initial_time,
                                                                                                generation=meter_energy,
                                                                                                updated_at=current_time)
                                        energy_entry.save()

    except Exception as exception:
        print(str(exception))

def compute_device_summary_others():
    try:
        compute_energy_meters_summary()
        compute_inverters_summary()
    except Exception as exception:
        print(str(exception))

def compute_device_summary_hero():
    try:
        compute_energy_meters_summary(clients_slugs=['hero-future-energies'])
        compute_inverters_summary(clients_slugs=['hero-future-energies'])
    except Exception as exception:
        print(str(exception))


def compute_device_summary_cleanmax():
    try:
        compute_energy_meters_summary(clients_slugs=['cleanmax-solar', 'hcleanmax'])
        compute_inverters_summary(clients_slugs=['cleanmax-solar', 'hcleanmax'])
    except Exception as exception:
        print(str(exception))