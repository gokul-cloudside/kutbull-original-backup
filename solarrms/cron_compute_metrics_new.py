from logger.views import log_a_success
import sys, dateutil, logging
import datetime
from solarrms.models import PerformanceRatioTable, PlantMetaSource, EnergyGenerationTable, SolarPlant
from utils.errors import generate_exception_comments, log_and_return_error
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import pytz
from dataglen.models import ValidDataStorageByStream
from dateutil import parser
from solarrms.solarutils import get_aggregated_energy, get_energy_meter_values

logger = logging.getLogger('dataglen.log')
logger.setLevel(logging.DEBUG)

start_date = "2016-07-25 12:00:00"


def compute_performance_ratio():
    print("Cron job started - %s",datetime.datetime.now())

    try:
        try:
            plant_meta_sources = PlantMetaSource.objects.all()
        except ObjectDoesNotExist:
            print("No plant meta source found.")
        for plant_meta_source in plant_meta_sources:
            print("For plant_meta_source: ", plant_meta_source.sourceKey)
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
                print("tz" , tz)
            except:
                print("error in converting current time to source timezone")

            try:
                current_time = timezone.now()
                current_time = tz.localize(current_time)
                # astimezone does the conversion and updates the tzinfo part
                current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            #current_time = datetime.datetime.now()
            print("current time outside: ", current_time)
            performance_last_entry = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                          count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                          identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')

            if performance_last_entry:
                last_entry_values = values = [item[0] for item in performance_last_entry]
                last_entry  = last_entry_values[0]
                print("last_time_entry: ", last_entry)
                if last_entry.tzinfo is None:
                    #the time value is UTC here and we dont want to localize it.
                    last_entry =pytz.utc.localize(last_entry)
                    #last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            print(last_entry)
            duration = (current_time-last_entry)
            days, seconds = duration.days, duration.seconds
            print( days, seconds)
            duration_hours = days * 24 + seconds/3600
            x = 0
            #Run the while loop for the duration for which this job was not running.
            #TODO: change the order of running while iterations
            process_start_time = last_entry
            while(x != duration_hours):
                print(x)
                #initial_time = current_time - datetime.timedelta(hours=1)
                initial_time = process_start_time
                initial_time = initial_time.replace(minute=0,second=0,microsecond=0)
                next_time = initial_time + datetime.timedelta(hours=1)
                next_time = next_time + datetime.timedelta(minutes=20)
                plant_shut_down_time = next_time.replace(hour=18,minute=30,second=0,microsecond=0)
                #plant_start_time = next_time.replace(hour=6,minute=0,second=0,microsecond=0)
                if next_time > plant_shut_down_time:
                    next_time = plant_shut_down_time
                    #break
                #elif next_time < plant_start_time:
                #    next_time = plant_start_time
                #    #break
                #else:
                #    pass
                print("loop initial time: ", initial_time)
                print("loop next time: ", next_time)
                try:
                    stream_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                          stream_name='IRRADIATION',
                                                                          timestamp_in_data__gte=initial_time,
                                                                          timestamp_in_data__lte=next_time).values_list('stream_value')
                except:
                    print("Error in getting the values of solar irradiation")

                #calculate the count of solar irradiation values in the last hour
                irradiation_values = [item[0] for item in stream_data]
                count = len(irradiation_values)
                if count == 0:
                    try:
                        stream_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                              stream_name='EXTERNAL_IRRADIATION',
                                                                              timestamp_in_data__gte=initial_time,
                                                                              timestamp_in_data__lte=next_time).values_list('stream_value')
                    except:
                        print("Error in getting the values of solar irradiation")
                    irradiation_values = [item[0] for item in stream_data]
                    print("irradiation_values", irradiation_values)
                    count = len(irradiation_values)
                print("count", count)
                sum_values = 0
                # get the energy value generated in the last hour
                latest_energy_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                             stream_name='DAILY_PLANT_ENERGY',
                                                                             timestamp_in_data__gte=initial_time,
                                                                             timestamp_in_data__lte=next_time).values_list('stream_value')
                energy_values_data = [item[0] for item in latest_energy_data]
                print(str(len(energy_values_data)))
                if len(energy_values_data) > 0:
                    latest_energy_value = float(energy_values_data[0]) - float(energy_values_data[len(energy_values_data)-1])
                    print("latest energy from plant source", latest_energy_value)

                # Get the energy values using method.
                try:
                    plant_generation_hourly = get_aggregated_energy(initial_time,next_time,plant_meta_source.plant,'HOUR')
                    energy_values = [item['energy'] for item in plant_generation_hourly]
                    print(str(len(energy_values)))
                    if len(energy_values) > 0:
                        latest_energy = energy_values[len(energy_values)-1]
                    else:
                        latest_energy = 0.0
                    print('latest energy calculated from method: ', latest_energy)
                except Exception as exception:
                    logger.debug("Error in getting the energy values : " + str(exception))

                if count > 0:
                    #calculate the average value of solar irradiation
                    #TODO: convert to more efficient pandas functions and parallelize the job operations

                    for i in range(count):
                        sum_values += float(irradiation_values[i]) #check
                    average_irradiation = sum_values/count
                    if average_irradiation > 0:
                        print("average_irradiation", average_irradiation)
                        # calculated energy values
                        calculated_energy = average_irradiation * plant_meta_source.PV_panel_area * plant_meta_source.PV_panel_efficiency
                        print("calculated_energy", calculated_energy)
                        #calculate performance ratio
                        hourly_performance_ratio = latest_energy/calculated_energy
                        if hourly_performance_ratio < 0:
                            hourly_performance_ratio = 0

                        print("hourly performance ratio: ", hourly_performance_ratio)
                        # Check if an hourly entry already exists for this time period.
                        try:
                            hour_entry_exists = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                     identifier=plant_meta_source.sourceKey,
                                                                                     ts=next_time.replace(minute=0,second=0,microsecond=0))
                            print("hour_entry_exists: ",hour_entry_exists)
                        except Exception as exception:
                            print(str(exception))

                        #if entry does not exist, make an hourly entry for performance ratio and irradiation
                        try:
                            if len(hour_entry_exists) == 0:
                                hour_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                  identifier=plant_meta_source.sourceKey,
                                                                                  ts=next_time.replace(minute=0,second=0,microsecond=0),
                                                                                  performance_ratio=hourly_performance_ratio,
                                                                                  irradiation=average_irradiation,
                                                                                  count=count,
                                                                                  sum_irradiation=sum_values)
                                hour_entry.save()
                                #TODO: update the entry if it's already there?
                        except Exception as exception:
                            print("Error in adding hourly entry of performance ratio" + str(exception))

                        #update the daily entry for performance ratio and irradiation
                        try:
                            print("inside daily performance")
                            daily_performance = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=plant_meta_source.sourceKey,
                                                                                     ts=next_time.replace(hour=0,minute=0,second=0,microsecond=0))
                            if len(daily_performance)>0:
                                try:
                                    # get the time difference between current time and plant operational start time
                                    today_start_time = next_time
                                    today_start_time = today_start_time.replace(hour=6,minute=30,second=0,microsecond=0)
                                    difference_time = next_time - today_start_time
                                    difference_minute = difference_time.seconds/60
                                    difference_hour = difference_minute/60
                                    print("difference hour: ", difference_hour)
                                    print("next_time: ",next_time)
                                    print("today_start_time: ",today_start_time)
                                    #print(difference_hour)

                                    # get the energy generated till this time since morning

                                    if plant_meta_source.energy_meter_installed == True:
                                        print("inside energy meter")
                                        plant_generation_daily = get_energy_meter_values(today_start_time,next_time,plant_meta_source.plant,'DAY')
                                    else:
                                        plant_generation_daily = get_aggregated_energy(today_start_time,next_time,plant_meta_source.plant,'DAY')
                                    daily_energy_values = [item['energy'] for item in plant_generation_daily]
                                    print(str(len(daily_energy_values)))
                                    if len(daily_energy_values) > 0:
                                        daily_latest_energy = daily_energy_values[len(daily_energy_values)-1]
                                    else:
                                        daily_latest_energy = 0.0
                                    print('daily latest energy calculated from method: ', daily_latest_energy)

                                    # get the irradiation values till this time since morning
                                    try:
                                        stream_data_daily = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                                                    stream_name='EXTERNAL_IRRADIATION',
                                                                                                    timestamp_in_data__gte=today_start_time,
                                                                                                    timestamp_in_data__lte=next_time).values_list('stream_value')
                                    except:
                                        print("Error in getting the values of solar irradiation")

                                    #calculate the count of solar irradiation values till this time since morning
                                    irradiation_values_daily = [item[0] for item in stream_data_daily]
                                    count_daily = len(irradiation_values_daily)
                                    if count_daily == 0:
                                        try:
                                            stream_data_daily = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                                                        stream_name='IRRADIATION',
                                                                                                        timestamp_in_data__gte=today_start_time,
                                                                                                        timestamp_in_data__lte=next_time).values_list('stream_value')
                                        except:
                                            print("Error in getting the values of solar irradiation")
                                        irradiation_values_daily = [item[0] for item in stream_data_daily]
                                        print("daily irradiation_values", irradiation_values_daily)
                                        count_daily = len(irradiation_values_daily)

                                    # Get the average value of irradiation 
                                    sum_irradiation_values_daily = 0
                                    for i in range(count_daily):
                                       sum_irradiation_values_daily +=float(irradiation_values_daily[i]) 
                                    daily_average_irradiation = sum_irradiation_values_daily/count_daily
                                    print('daily_average_irradiation : ', daily_average_irradiation)
                                    daily_calculated_energy = daily_average_irradiation * plant_meta_source.PV_panel_area * plant_meta_source.PV_panel_efficiency * difference_hour
                                    print('daily_calculated_energy: ', daily_calculated_energy)
                                    if daily_calculated_energy > 0:
                                        daily_performance_ratio = daily_latest_energy/daily_calculated_energy
                                    else:
                                        daily_performance_ratio = 0

                                    daily_performance.update(performance_ratio=daily_performance_ratio,
                                                             irradiation=daily_average_irradiation,
                                                             count=count_daily,
                                                             sum_irradiation=sum_irradiation_values_daily)

                                except Exception as exception:
                                    print("Error in updating the daily performance ratio")

                            else:
                                print("inside else")
                                try:
                                    daily_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                       identifier=plant_meta_source.sourceKey,
                                                                                       ts=next_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                       performance_ratio=hourly_performance_ratio,
                                                                                       irradiation=average_irradiation,
                                                                                       count=count,
                                                                                       sum_irradiation=average_irradiation)
                                    daily_entry.save()
                                except Exception as exception:
                                    print("error in creating daily_entry record" + str(exception))
                        except Exception as exception:
                            print("Error" + str(exception))

                #duration_hours = duration_hours-1
                x = x+1
                #current_time = current_time - datetime.timedelta(hours=1)
                process_start_time = process_start_time + datetime.timedelta(hours=1)
    except Exception as exception:
        print("Error: " + str(exception))
