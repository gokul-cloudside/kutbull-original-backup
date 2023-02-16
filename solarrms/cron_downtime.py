import datetime
from solarrms.models import PlantMetaSource, PlantDownTime
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.solarutils import get_down_time
from solarrms.cron_plant_devices_summary import compute_equipment_availability_from_working_hours_daily

start_date = "2016-07-01 00:00:00"

def calculate_down_time():
    try:
        print("Downtime calculation cronjob started")
        plant_meta_sources = PlantMetaSource.objects.all()
        for plant_meta_source in plant_meta_sources:
            print("Energy loss calculation for : " + str(plant_meta_source.plant.slug))
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
            except:
                print ("Error in getting tz")
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            except Exception as exc:
                print(str(exc))
                current_time = timezone.now()
            downtime_last_entry = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')
            if downtime_last_entry:
                last_entry_values = [item[0] for item in downtime_last_entry]
                last_entry  = last_entry_values[0]
                print("last_time_entry: ", last_entry)
                if last_entry.tzinfo is None:
                    last_entry =pytz.utc.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))

            duration = (current_time - last_entry)
            duration_days = duration.days
            loop_count = 0

            while loop_count < duration_days:
                print(duration_days)
                print last_entry
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                last_entry = plant_start_time

                daily_downtime = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                              identifier=plant_meta_source.sourceKey,
                                                              ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    if plant_meta_source.plant.groupClient.slug == 'renew-power':
                        downtime = compute_equipment_availability_from_working_hours_daily(plant_start_time, plant_shut_down_time,plant_meta_source.plant)
                    else:
                        downtime = get_down_time(plant_start_time, plant_shut_down_time,plant_meta_source.plant)
                except Exception as exception:
                    print("Exception in calculating down time : " + str(exception))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                    continue

                try:
                    grid_downtime = downtime['grid']
                except:
                    grid_downtime = 0.0

                try:
                    if len(daily_downtime) == 0:
                        daily_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant_meta_source.sourceKey,
                                                                   ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                   down_time=grid_downtime,
                                                                   updated_at=current_time)
                        daily_entry.save()
                    else:
                        daily_downtime.update(down_time=grid_downtime,
                                              updated_at=current_time)

                    inverters = plant_meta_source.plant.independent_inverter_units.all()
                    for inverter in inverters:
                        inverter_daily_down_time = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                identifier=inverter.sourceKey,
                                                                                ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                        try:
                            inverter_down_time = downtime[str(inverter.name)]
                        except:
                            inverter_down_time = 0.0

                        if len(inverter_daily_down_time) == 0:
                            inverter_daily_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                identifier=inverter.sourceKey,
                                                                                ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                down_time=inverter_down_time,
                                                                                updated_at=current_time)
                            inverter_daily_entry.save()
                        else:
                            inverter_daily_down_time.update(down_time=inverter_down_time,
                                                            updated_at=current_time)

                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                except Exception as exception:
                    print("Error in creating entry for downtime : " + str(exception))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                    continue
            if duration_days == 0 :
                print("Current downtime computation for plant : {0}".format(str(plant_meta_source.plant)))
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                final_time = current_time
                plant_shut_down_time = final_time.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = final_time.replace(hour=6, minute=0, second=0, microsecond=0)
                daily_downtime = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                              identifier=plant_meta_source.sourceKey,
                                                              ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    if plant_meta_source.plant.groupClient.slug == 'renew-power':
                        downtime = compute_equipment_availability_from_working_hours_daily(plant_start_time,current_time,plant_meta_source.plant)
                    else:
                        downtime = get_down_time(plant_start_time,current_time,plant_meta_source.plant)
                except:
                    print("Exception in calculating down time : " + str(exception))
                    continue

                try:
                    grid_downtime = downtime['grid']
                except:
                    grid_downtime = 0.0

                try:
                    if len(daily_downtime) == 0:
                        print("first Daily loss entry for current data")
                        daily_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant_meta_source.sourceKey,
                                                                   ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                   down_time=grid_downtime,
                                                                   updated_at=current_time)
                        daily_entry.save()

                        hourly_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                    count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                    identifier=plant_meta_source.sourceKey,
                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                    down_time=grid_downtime,
                                                                    updated_at=current_time)
                        hourly_entry.save()

                        inverters = plant_meta_source.plant.independent_inverter_units.all()
                        for inverter in inverters:
                            inverter_daily_down_time = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                            try:
                                inverter_down_time = downtime[str(inverter.name)]
                            except:
                                inverter_down_time = 0.0

                            if len(inverter_daily_down_time) == 0:
                                inverter_daily_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                    down_time=inverter_down_time,
                                                                                    updated_at=current_time)
                                inverter_daily_entry.save()
                                inverter_hourly_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                    down_time=inverter_down_time,
                                                                                    updated_at=current_time)
                                inverter_hourly_entry.save()

                    elif len(daily_downtime) > 0 and final_time < plant_shut_down_time and final_time > plant_start_time:
                        print("updating downtime in operational hour")
                        daily_downtime.update(down_time=grid_downtime,
                                              updated_at=current_time)
                        hourly_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                    count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                    identifier=plant_meta_source.sourceKey,
                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                    down_time=grid_downtime,
                                                                    updated_at=current_time)
                        hourly_entry.save()
                        inverters = plant_meta_source.plant.independent_inverter_units.all()
                        for inverter in inverters:
                            inverter_daily_down_time = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                            try:
                                inverter_down_time = downtime[str(inverter.name)]
                            except:
                                inverter_down_time = 0.0

                            inverter_daily_down_time.update(down_time=inverter_down_time,
                                                            updated_at=current_time)
                            inverter_hourly_entry = PlantDownTime.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                 count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                 identifier=inverter.sourceKey,
                                                                                 ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0),
                                                                                 down_time=inverter_down_time,
                                                                                 updated_at=current_time)
                            inverter_hourly_entry.save()
                    else:
                        daily_downtime.update(down_time=grid_downtime)
                        inverters = plant_meta_source.plant.independent_inverter_units.all()
                        for inverter in inverters:
                            inverter_daily_down_time = PlantDownTime.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                            inverter_daily_down_time.update(updated_at=current_time)

                except Exception as exception:
                    print("Exception in downtime calculation : " + str(exception))

    except Exception as exception:
        print(str(exception))