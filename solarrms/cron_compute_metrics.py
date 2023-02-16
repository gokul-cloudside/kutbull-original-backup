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
from solarrms.solarutils import get_aggregated_energy

logger = logging.getLogger('dataglen.log')
logger.setLevel(logging.DEBUG)

start_date = "2016-03-22 12:00:00"


def compute_performance_ratio():
    print("Cron job started - %s",datetime.datetime.now())

    try:
        try:
            plant_meta_sources = PlantMetaSource.objects.all()
        except ObjectDoesNotExist:
            print("No plant meta source found.")
        for plant_meta_source in plant_meta_sources:
            print("For plant_meta_source: ", plant_meta_source.sourceKey)
            #check if data exists in Performance ratio table for this plant
            #if data exists, take last timestamp from 15 min table as new start_time
            #if data does not exist, start with a default date, say 5th April 2016 00:00:00

            #from start_time till current_time
            #read irradiation data from this source in chunks of 1 hour
            # compute performance ratio for 1 hour and update avg. performance ratio for the day
            # write performance ratio appropriately in performance ratio table.

            # get the current time at which the cron job is run and convert it to source timezone

            # check when was the last entry made in PerformanceRatioTable

            #TODO: check if the daily energy should be taken from plant meta source or from any other place
            
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
                print("tz" , tz)
            except:
                print("error in converting current time to source timezone")

            try:
                current_time = timezone.now()
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

            #Run the while loop for the duration for which this job was not running.
            #TODO: change the order of running while iterations
            while(duration_hours > 0):
                print(duration_hours)
                print("loop current time: ", current_time)
                initial_time = current_time - datetime.timedelta(hours=1)
                initial_time = initial_time.replace(minute=0,second=0,microsecond=0)
                print("loop initial time: ", initial_time)
                try:
                    stream_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                          stream_name='IRRADIATION',
                                                                          timestamp_in_data__gte=initial_time,
                                                                          timestamp_in_data__lte=current_time).values_list('stream_value')
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
                                                                          timestamp_in_data__lte=current_time).values_list('stream_value')
                    except:
                        print("Error in getting the values of solar irradiation")
                    irradiation_values = [item[0] for item in stream_data]
                    print("irradiation_values", irradiation_values)
                    count = len(irradiation_values)
                print("count", count)
                sum_values = 0
                # get the energy value generated in the last hour
                """
                try:

                    latest_energy_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                                 stream_name='DAILY_PLANT_ENERGY',
                                                                                 timestamp_in_data__gte=initial_time,
                                                                                 timestamp_in_data__lte=current_time).values_list('stream_value')
                    energy_values = [item[0] for item in latest_energy_data]
                    print(str(len(energy_values)))
                    if len(energy_values) > 0:
                        latest_energy = float(energy_values[0]) - float(energy_values[len(energy_values)-1])
                        print("latest energy from plant source", latest_energy)
                    else:
                        #Read latest energy value from EnergyGeneration table
                        plant_generation_hourly = EnergyGenerationTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                    count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                    identifier=str(plant_meta_source.user.id) + "_" + plant_meta_source.plant.slug,ts__gte=initial_time,ts__lte=current_time).values_list('energy')
                        energy_values = [item[0] for item in plant_generation_hourly]
                        print("energy calculation for plant identifier: ",str(plant_meta_source.user.id) + "_" + plant_meta_source.plant.slug)
                        if len(energy_values) > 0:
                            latest_energy = energy_values[0]
                        else:
                            latest_energy = 0.0
                    print("latest energy", latest_energy)
                except Exception as exception:
                    print("Error in getting the energy values of last hour: " + str(exception))
                """
                latest_energy_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                             stream_name='DAILY_PLANT_ENERGY',
                                                                             timestamp_in_data__gte=initial_time,
                                                                             timestamp_in_data__lte=current_time).values_list('stream_value')
                energy_values_data = [item[0] for item in latest_energy_data]
                print(str(len(energy_values_data)))
                if len(energy_values_data) > 0:
                    latest_energy_value = float(energy_values_data[0]) - float(energy_values_data[len(energy_values_data)-1])
                    print("latest energy from plant source", latest_energy_value)

                # Get the energy values using method.
                try:
                    plant_generation_hourly = get_aggregated_energy(initial_time,current_time,plant_meta_source.plant,'HOUR')
                    energy_values = [item['energy'] for item in plant_generation_hourly]
                    print(str(len(energy_values)))
                    if len(energy_values) > 0:
                        latest_energy = energy_values[0]
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
                                                                                     ts=current_time.replace(minute=0,second=0,microsecond=0))
                            print("hour_entry_exists: ",hour_entry_exists)
                        except Exception as exception:
                            print(str(exception))

                        #if entry does not exist, make an hourly entry for performance ratio and irradiation
                        try:
                            if len(hour_entry_exists) == 0:
                                hour_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                  identifier=plant_meta_source.sourceKey,
                                                                                  ts=current_time.replace(minute=0,second=0,microsecond=0),
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
                                                                                     ts=current_time.replace(hour=0,minute=0,second=0,microsecond=0))

                            '''
                            plant_latest_energy = ValidDataStorageByStream.objects.filter(source_key=plant_meta_source.sourceKey,
                                                                                         stream_name='DAILY_PLANT_ENERGY',
                                                                                         timestamp_in_data__lte=current_time).limit(1).values_list('stream_value')
                            plant_energy_values = [item[0] for item in plant_latest_energy]

                            plant_energy = float(plant_energy_values[0])
                            '''


                            if len(daily_performance)>0:
                                #print("inside try")
                                print("daily_performance: ",float(daily_performance[0].performance_ratio))
                                if hourly_performance_ratio > 0:
                                    try:
                                        print("count ",int(daily_performance[0].count))
                                        updated_count = int(daily_performance[0].count) + count
                                        print("updated_count ", updated_count)
                                        if updated_count > 0: #TODO: check condition
                                            updated_sum_irradiation = sum_values/count + float(daily_performance[0].sum_irradiation)
                                            updated_irradiation = (updated_sum_irradiation)/(updated_count)
                                        else:

                                            updated_irradiation = float(daily_performance[0].irradiation)
                                            updated_sum_irradiation = float(daily_performance[0].sum_irradiation)

                                        print("updated_irradiation:", updated_irradiation)

                                        '''
                                        calculated_energy_updated = updated_sum_irradiation * plant_meta_source.PV_panel_area * plant_meta_source.PV_panel_efficiency

                                        if calculated_energy_updated > 0:
                                            performance_ratio_updated = plant_energy/calculated_energy_updated
                                        else:
                                            performance_ratio_updated = float(daily_performance[0].performance_ratio)
                                        '''
                                        daily_performance_ratio = (float(daily_performance[0].performance_ratio) * int(daily_performance[0].count) + hourly_performance_ratio * count)/updated_count

                                        if daily_performance_ratio < 0:
                                            daily_performance_ratio = 0

                                        daily_performance.update(performance_ratio=daily_performance_ratio,
                                                                 irradiation=updated_irradiation,
                                                                 count=updated_count,
                                                                 sum_irradiation=updated_sum_irradiation)
                                    except Exception as exception:
                                        print("Error in updating the daily record : " + str(exception))

                            else:
                                print("inside else")

                                try:
                                    daily_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                       identifier=plant_meta_source.sourceKey,
                                                                                       ts=current_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                       performance_ratio=hourly_performance_ratio,
                                                                                       irradiation=average_irradiation,
                                                                                       count=count,
                                                                                       sum_irradiation=average_irradiation)
                                    daily_entry.save()
                                except Exception as exception:
                                    print("error in creating daily_entry record" + str(exception))
                        except Exception as exception:
                            print("Error" + str(exception))

                duration_hours = duration_hours-1
                current_time = current_time - datetime.timedelta(hours=1)
    except Exception as exception:
        print("Error: " + str(exception))


def compute_performance_ratio_test():
    logger.debug("cronjob started")
    try:
        try:
            hour_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                              identifier='hello',
                                                              ts=timezone.now(),
                                                              performance_ratio=0.579,
                                                              irradiation=0.589,
                                                              count=10)
            hour_entry.save()
        except Exception as exception:
            logger.debug("Error in adding hourly entry of performance ratio" + str(exception))

    except Exception as exception:
        logger.debug("Error: "+ str(exception))