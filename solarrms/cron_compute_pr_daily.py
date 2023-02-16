import datetime
from solarrms.models import PerformanceRatioTable, SolarPlant, PlantMetaSource
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import pytz
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import get_aggregated_energy, get_energy_meter_values, calculate_pr
from kutbill.settings import PR_Email
from django.core.mail import send_mail

start_date = "2016-03-15 00:00:00"

def sendAlertforPR(subject, body):
    email = PR_Email
    try:
        send_mail(subject=subject, message=body, from_email='alerts@dataglen.com', recipient_list=email, fail_silently=False)
    except Exception as exception:
        print("Error in sending PR alert email" + str(exception))


def compute_daily_performance_ratio():
    print(" Daily PR cron job started - %s", datetime.datetime.now())
    try:
        try:
            plant_meta_sources = PlantMetaSource.objects.all()
        except ObjectDoesNotExist:
            print("No plant meta source found.")

        for plant_meta_source in plant_meta_sources:
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
                print("tz", tz)
            except:
                print("error in converting current time to source timezone")

            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                temp = current_time
                print("current_time %s", current_time)
            except Exception as exc:
                print("inside exception " + str(exc))
                current_time = timezone.now()

            # get the last entry made for the daily performance ratio
            performance_last_entry = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                          identifier=plant_meta_source.sourceKey).limit(1).values_list('updated_at')
            if performance_last_entry:
                try:
                    last_entry_values = [item[0] for item in performance_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                        print(last_entry)
                except:
                    performance_last_entry = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                          identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')
                    last_entry_values = [item[0] for item in performance_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                        print(last_entry)
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))

            duration = (current_time - last_entry)
            duration_days = duration.days
            print("duration days", duration_days)
            loop_count = 0

            # Calculate PR for historical data
            while loop_count < duration_days:
                print("historical PR computation for plant{0}".format(str(plant_meta_source.plant)))
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                last_entry = plant_start_time

                # get the entry daily PR entry as per current time
                daily_performance = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant_meta_source.sourceKey,
                                                                         ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                #result = get_PR_value(plant_start_time, plant_shut_down_time, plant_meta_source)
                try:
                    print("PR start time: %s", plant_start_time)
                    print("PR end time: %s", plant_shut_down_time)
                    print("plant: plant{0}".format(str(plant_meta_source.plant)))
                    pr_value = calculate_pr(plant_start_time,plant_shut_down_time,plant_meta_source.plant)
                    if float(pr_value) > 1.0:
                        sendAlertforPR("Alert for PR value greater than 1 for plant - " + str(plant_meta_source.plant.slug) + " at : " + str(plant_meta_source.plant.location),
                                       "Hi,\nThe current daily PR value at " + str(plant_meta_source.plant.location) + " is " +
                                       str(pr_value) + "\nPlease Inspect. \n\nThank You,\nTeam DataGlen")
                    print("PR value %s",pr_value)
                except Exception as ex:
                    print("Exception in calculate_pr: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue
                try:
                    # If entry does not exist for daily PR and it is for historical data
                    if len(daily_performance) == 0:
                        daily_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                           identifier=plant_meta_source.sourceKey,
                                                                           ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                           performance_ratio=pr_value,
                                                                           irradiation=0,
                                                                           count=0,
                                                                           sum_irradiation=0,
                                                                           updated_at=current_time)
                        daily_entry.save()
                    else:
                        daily_performance.update(performance_ratio=pr_value,
                                                 #irradiation=result[1],
                                                 #count=result[2],
                                                 #sum_irradiation=result[3],
                                                 updated_at=current_time)
                    #  increase last entry time by 1 day
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                except Exception as ex:
                    print("Exception in calculate_pr: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

            # calculate PR for current day
            if duration_days == 0 :
                print("Current PR computation for plant : {0}".format(str(plant_meta_source.plant)))
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                final_time = current_time
                plant_shut_down_time = final_time.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = final_time.replace(hour=6, minute=0, second=0, microsecond=0)
                # get the entry daily PR entry as per current time
                daily_performance = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant_meta_source.sourceKey,
                                                                         ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                #result = get_PR_value(initial_time, final_time, plant_meta_source)
                try:
                    print("PR start time: %s", plant_start_time)
                    print("PR end time: %s", plant_shut_down_time)
                    print("plant: plant{0}".format(str(plant_meta_source.plant)))
                    pr_value = calculate_pr(plant_start_time,current_time,plant_meta_source.plant)
                    if float(pr_value) > 1.0:
                        sendAlertforPR("Alert for PR value greater than 1 for plant - " + str(plant_meta_source.plant.slug) + " at : " + str(plant_meta_source.plant.location),
                                       "Hi,\nThe current daily PR value at " + str(plant_meta_source.plant.location) + " is " +
                                       str(pr_value) + "\nPlease Inspect. \n\nThank You,\nTeam DataGlen")
                    print("PR value %s",pr_value)
                except Exception as ex:
                    print("Exception in calculate_pr: %s", str(ex))
                    continue
                try:
                    # If entry does not exist for daily PR and it is for current data
                    if len(daily_performance) == 0:
                        print("first PR entry for current data")
                        daily_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                           identifier=plant_meta_source.sourceKey,
                                                                           ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                           performance_ratio=pr_value,
                                                                           irradiation=0.0,
                                                                           count=0,
                                                                           sum_irradiation=0.0,
                                                                           updated_at=final_time)
                        daily_entry.save()

                        hourly_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                           identifier=plant_meta_source.sourceKey,
                                                                           ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                           performance_ratio=pr_value,
                                                                           irradiation=0,
                                                                           count=0,
                                                                           sum_irradiation=0,
                                                                           updated_at=current_time)
                        hourly_entry.save()


                    # If entry exists for daily PR and current time is withing the range of plant operational time
                    elif len(daily_performance) > 0 and final_time < plant_shut_down_time and final_time > plant_start_time:
                        print("updating PR in operational hour")
                        daily_performance.update(performance_ratio=pr_value,
                                                 #irradiation=result[1],
                                                 #count=result[2],
                                                 #sum_irradiation=result[3],
                                                 updated_at=final_time)
                        hourly_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                           identifier=plant_meta_source.sourceKey,
                                                                           ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                           performance_ratio=pr_value,
                                                                           irradiation=0,
                                                                           count=0,
                                                                           sum_irradiation=0,
                                                                           updated_at=current_time)
                        hourly_entry.save()
                    else:
                        daily_performance.update(updated_at=final_time)
                except Exception as ex:
                    print("Exception in calculate_pr: %s", str(ex))
                    continue

    except Exception as exception:
        print(exception)
