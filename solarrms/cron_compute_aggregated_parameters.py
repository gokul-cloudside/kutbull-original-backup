import datetime
from solarrms.models import AggregatedPlantParameters, SolarPlant
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import pytz
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import get_aggregated_ambient_temperature_values, get_aggregated_module_temperature_values, \
    get_aggregated_wind_speed_values


start_date = "2016-03-15 00:00:00"

def compute_aggregated_parameters():
    print("Aggregated plant parameters cron job started - %s", datetime.datetime.now())
    try:
        try:
            plants = SolarPlant.objects.all()
            #plants = SolarPlant.objects.filter(slug='yerangiligi')
        except ObjectDoesNotExist:
            print("No plant meta source found.")

        for plant in plants:
            try:
                tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            except:
                print("error in converting current time to source timezone")

            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                print("current_time %s", current_time)
            except Exception as exc:
                print("inside exception " + str(exc))
                current_time = timezone.now()

            # get the last entry made for the aggregated values
            aggregated_last_entry = AggregatedPlantParameters.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                             identifier=str(plant.slug)).limit(1).values_list('updated_at')
            if aggregated_last_entry:
                try:
                    last_entry_values = [item[0] for item in aggregated_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        print(last_entry)
                except:
                    aggregated_last_entry = AggregatedPlantParameters.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=str(plant.slug)).limit(1).values_list('ts')
                    last_entry_values = [item[0] for item in aggregated_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        print(last_entry)
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))

            duration = (current_time - last_entry)
            duration_days = duration.days
            print("duration days", duration_days)
            loop_count = 0

            # Calculate aggregated values for historical data
            while loop_count < duration_days:
                print("historical aggregated values computation for plant{0} ".format(str(plant.slug)))
                final_time = last_entry.replace(hour=23, minute=59, second=59, microsecond=59)
                initial_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)

                daily_aggregated_value = AggregatedPlantParameters.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                  identifier=str(plant.slug),
                                                                                  ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    ambient_temperature = get_aggregated_ambient_temperature_values(initial_time,final_time,plant)
                except Exception as ex:
                    print("Exception in getting ambient temp values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

                try:
                    module_temperature = get_aggregated_module_temperature_values(initial_time,final_time,plant)
                except Exception as ex:
                    print("Exception in getting module temp values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

                try:
                    wind_speed = get_aggregated_wind_speed_values(initial_time,final_time,plant)
                except Exception as ex:
                    print("Exception in getting wind speed values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

                try:
                    # If entry does not exist for daily aggregated values and it is for historical data
                    if len(daily_aggregated_value) == 0:
                        daily_entry = AggregatedPlantParameters.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                               identifier=str(plant.slug),
                                                                               ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                               average_ambient_temperature=ambient_temperature,
                                                                               average_module_temperature=module_temperature,
                                                                               average_windspeed=wind_speed,
                                                                               updated_at=current_time)
                        daily_entry.save()
                    else:
                        daily_aggregated_value.update(average_ambient_temperature=ambient_temperature,
                                                      average_module_temperature=module_temperature,
                                                      average_windspeed=wind_speed,
                                                      updated_at=current_time)

                    #  increase last entry time by 1 day
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                except Exception as ex:
                    print("Exception in updating historical aggregated values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

            # calculate aggregated values for current day
            if duration_days == 0 :
                print("Current aggregated values computation for plant : {0}".format(str(plant.slug)))
                final_time = current_time
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)

                daily_aggregated_value = AggregatedPlantParameters.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                  identifier=str(plant.slug),
                                                                                  ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                try:
                    ambient_temperature = get_aggregated_ambient_temperature_values(initial_time,final_time,plant)
                except Exception as ex:
                    print("Exception in getting ambient temp values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

                try:
                    module_temperature = get_aggregated_module_temperature_values(initial_time,final_time,plant)
                except Exception as ex:
                    print("Exception in getting module temp values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

                try:
                    wind_speed = get_aggregated_wind_speed_values(initial_time,final_time,plant)
                except Exception as ex:
                    print("Exception in getting wind speed values: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

                try:
                    # If entry does not exist for daily aggregated data and it is for current data
                    if len(daily_aggregated_value) == 0:
                        print("first aggregated entry for current data")
                        daily_entry = AggregatedPlantParameters.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                               identifier=str(plant.slug),
                                                                               ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                               average_ambient_temperature=ambient_temperature,
                                                                               average_module_temperature=module_temperature,
                                                                               average_windspeed=wind_speed,
                                                                               updated_at=final_time)
                        daily_entry.save()

                        hourly_entry = AggregatedPlantParameters.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                identifier=str(plant.slug),
                                                                                ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                                average_ambient_temperature=ambient_temperature,
                                                                                average_module_temperature=module_temperature,
                                                                                average_windspeed=wind_speed,
                                                                                updated_at=final_time)
                        hourly_entry.save()

                    else:
                        print("updating aggregated vaues in operational hour")
                        daily_aggregated_value.update(average_ambient_temperature=ambient_temperature,
                                                      average_module_temperature=module_temperature,
                                                      average_windspeed=wind_speed,
                                                      updated_at=final_time)
                        hourly_entry = AggregatedPlantParameters.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                        identifier=str(plant.slug),
                                                                        ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                        average_ambient_temperature=ambient_temperature,
                                                                        average_module_temperature=module_temperature,
                                                                        average_windspeed=wind_speed,
                                                                        updated_at=final_time)
                        hourly_entry.save()
                except Exception as ex:
                    print("Exception in updaing current aggregated values: %s", str(ex))
                    continue

    except Exception as exception:
        print(exception)