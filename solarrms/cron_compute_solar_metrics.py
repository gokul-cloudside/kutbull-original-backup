import datetime
from solarrms.models import PerformanceRatioTable, SolarPlant, PlantMetaSource,CUFTable, KWHPerMeterSquare, SpecificYieldTable, SolarMetrics
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import pytz
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import get_aggregated_energy, get_energy_meter_values, calculate_pr, calculate_CUF,\
    get_kwh_per_meter_square_value, calculate_specific_yield, calculate_pr_gmr
from kutbill.settings import PR_Email
from django.core.mail import send_mail
from datetime import timedelta

start_date = "2016-03-15 00:00:00"
KPI_WINDOW_SIZE = 15

def sendAlertforPR(subject, body):
    email = PR_Email
    try:
        send_mail(subject=subject, message=body, from_email='alerts@dataglen.com', recipient_list=email, fail_silently=False)
    except Exception as exception:
        print("Error in sending PR alert email" + str(exception))

def write_instantanous_solar_metrics(solar_metric_source_key,stream_name,insertion_time, stream_value,timestamp_in_data):
    solar_metric_record = ValidDataStorageByStream.objects.create(source_key=solar_metric_source_key,
                                    stream_name=stream_name,
                                    insertion_time=insertion_time,
                                    stream_value=str(stream_value),
                                    timestamp_in_data=timestamp_in_data,
                                    raw_value=str(stream_value),
                                    multiplication_factor=str(1))
    solar_metric_record.save()

def write_hourly_cuf_values(plant_meta_source, cuf_value, ts):
    hourly_entry = CUFTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                           count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                           identifier=plant_meta_source.sourceKey,
                                           ts=ts,
                                           CUF=cuf_value,
                                           updated_at=timezone.now())
    hourly_entry.save()

def write_hourly_specific_yield_values(plant_meta_source, sy_value, ts):
    hourly_entry = SpecificYieldTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                     count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                     identifier=plant_meta_source.sourceKey,
                                                     ts=ts,
                                                     specific_yield=sy_value,
                                                     updated_at=timezone.now())
    hourly_entry.save()


def write_hourly_pr_values(plant_meta_source, pr_value, ts):
    hourly_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                        count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                        identifier=plant_meta_source.sourceKey,
                                                        ts=ts,
                                                        performance_ratio=pr_value,
                                                        irradiation=0,
                                                        count=0,
                                                        sum_irradiation=0,
                                                        updated_at=timezone.now())
    hourly_entry.save()

def calculate_metrics_for_missing_data_points(starttime, endtime, plant, aggregator, metric_type, inverters=None):
    try:
        starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
        duration_minutes = (endtime - starttime).total_seconds()/60
        try:
            solar_metric = SolarMetrics.objects.get(plant=plant,solar_group=None)
        except:
            return 0
        if metric_type == 'PR':
            if aggregator == '15_MINUTES':
                window_slots = duration_minutes/15
                while(window_slots)>0:
                    window_starttime = starttime - timedelta(seconds=30)
                    window_endtime = starttime + timedelta(minutes=15, seconds=59)
                    window_pr = calculate_pr(window_starttime, window_endtime, plant)
                    print window_starttime, window_endtime, window_pr
                    write_instantanous_solar_metrics(solar_metric.sourceKey,"PR", timezone.now(), window_pr, window_endtime)
                    starttime = starttime + timedelta(minutes=15)
                    window_slots -= 1
            elif aggregator == 'HOUR':
                while(window_slots)>0:
                    window_slots = duration_minutes/60
                    window_starttime = starttime - timedelta(seconds=30)
                    window_endtime = starttime + timedelta(minutes=60, seconds=59)
                    window_pr = calculate_pr(window_starttime, window_endtime, plant)
                    write_hourly_pr_values(plant.metadata.plantmetasource, window_pr, starttime)
                    starttime = starttime + timedelta(minutes=60)
                    window_slots -= 1
            else:
                pass
        elif metric_type == 'CUF':
            if aggregator == '15_MINUTES':
                window_slots = duration_minutes/15
                while(window_slots)>0:
                    window_starttime = starttime - timedelta(seconds=30)
                    window_endtime = starttime + timedelta(minutes=15, seconds=59)
                    window_cuf = calculate_CUF(window_starttime, window_endtime, plant)
                    print window_starttime, window_endtime, window_cuf
                    write_instantanous_solar_metrics(solar_metric.sourceKey,"CUF", timezone.now(), window_cuf, window_endtime)
                    starttime = starttime + timedelta(minutes=15)
                    window_slots -= 1
            elif aggregator == 'HOUR':
                while(window_slots)>0:
                    window_slots = duration_minutes/60
                    window_starttime = starttime - timedelta(seconds=30)
                    window_endtime = starttime + timedelta(minutes=60, seconds=59)
                    window_cuf = calculate_pr(window_starttime, window_endtime, plant)
                    write_hourly_cuf_values(plant.metadata.plantmetasource, window_cuf, starttime)
                    starttime = starttime + timedelta(minutes=60)
                    window_slots -= 1
            else:
                pass
        elif metric_type == 'SPECIFIC_YIELD':
            if aggregator == '15_MINUTES':
                window_slots = duration_minutes/15
                while(window_slots)>0:
                    window_starttime = starttime - timedelta(seconds=30)
                    window_endtime = starttime + timedelta(minutes=15, seconds=59)
                    window_sy = calculate_specific_yield(window_starttime, window_endtime, plant)
                    print window_starttime, window_endtime, window_sy
                    write_instantanous_solar_metrics(solar_metric.sourceKey,"SPECIFIC_YIELD", timezone.now(), window_sy, window_endtime)
                    starttime = starttime + timedelta(minutes=15)
                    window_slots -= 1
            elif aggregator == 'HOUR':
                while(window_slots)>0:
                    window_slots = duration_minutes/60
                    window_starttime = starttime - timedelta(seconds=30)
                    window_endtime = starttime + timedelta(minutes=60, seconds=59)
                    window_sy = calculate_specific_yield(window_starttime, window_endtime, plant)
                    write_hourly_specific_yield_values(plant.metadata.plantmetasource, window_sy, starttime)
                    starttime = starttime + timedelta(minutes=60)
                    window_slots -= 1
            else:
                pass
        else:
            pass
    except Exception as exception:
        print str(exception)


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
                print("current_time %s", current_time)
            except Exception as exc:
                print("inside exception " + str(exc))
                current_time = timezone.now()
            # try:
            #     current_time = timezone.now()
            #     current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            #     temp = current_time
            #     print("current_time %s", current_time)
            # except Exception as exc:
            #     print("inside exception " + str(exc))
            #     current_time = timezone.now()

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
                    # if float(pr_value) > 1.0:
                    #     sendAlertforPR("Alert for PR value greater than 1 for plant - " + str(plant_meta_source.plant.slug) + " at : " + str(plant_meta_source.plant.location),
                    #                    "Hi,\nThe current daily PR value at " + str(plant_meta_source.plant.location) + " is " +
                    #                    str(pr_value) + "\nPlease Inspect. \n\nThank You,\nTeam DataGlen")
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
                    # if float(pr_value) > 1.0:
                    #     sendAlertforPR("Alert for PR value greater than 1 for plant - " + str(plant_meta_source.plant.slug) + " at : " + str(plant_meta_source.plant.location),
                    #                    "Hi,\nThe current daily PR value at " + str(plant_meta_source.plant.location) + " is " +
                    #                    str(pr_value) + "\nPlease Inspect. \n\nThank You,\nTeam DataGlen")
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
                    try:
                        #compute and update PR for 15 min time window as a time series of 15 min PR values
                        current_window_mins_slot = ((current_time.hour * 60 + current_time.minute) // KPI_WINDOW_SIZE) - 1
                        if current_window_mins_slot >= 0:
                            window_start_time = current_time.replace(hour= (current_window_mins_slot*KPI_WINDOW_SIZE)//60, minute= (current_window_mins_slot*KPI_WINDOW_SIZE)%60, second=0,microsecond=0)
                            window_end_time = current_time.replace(hour= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)//60, minute= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)%60, second=59,microsecond=0)
                            if str(plant_meta_source.plant.slug)== 'gmr':
                                current_window_pr_value = calculate_pr_gmr(window_start_time,window_end_time,plant_meta_source.plant)
                            else:
                                current_window_pr_value = calculate_pr(window_start_time,window_end_time,plant_meta_source.plant)
                            print("Current time: %s, current_window_mins_slot: %s",current_window_pr_value, current_window_mins_slot)
                            print("Current Window PR value: %s window start time: %s window end time %s",current_window_pr_value, window_start_time, window_end_time)

                            try:
                                #write current window PR entry
                                solar_metric = SolarMetrics.objects.get(plant=plant_meta_source.plant,solar_group=None)
                                write_instantanous_solar_metrics(solar_metric.sourceKey,"PR",current_time, current_window_pr_value,window_end_time)
                            except Exception as ex:
                                print("Exception in writing current window PR: %s", str(ex))
                                continue
                    except Exception as ex:
                        print("Exception in calculating PR for current window: %s", str(ex))
                        continue
                except Exception as ex:
                    print("Exception in calculate_pr: %s", str(ex))
                    continue

    except Exception as exception:
        print(exception)


def compute_daily_CUF():
    print("CUF cron job started - %s", datetime.datetime.now())
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
                print("current_time %s", current_time)
            except Exception as exc:
                print("inside exception " + str(exc))
                current_time = timezone.now()

            # get the last entry made for the daily performance ratio
            CUF_last_entry = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                     identifier=plant_meta_source.sourceKey).limit(1).values_list('updated_at')
            if CUF_last_entry:
                try:
                    last_entry_values = [item[0] for item in CUF_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                        print(last_entry)
                except:
                    CUF_last_entry = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                             identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')
                    last_entry_values = [item[0] for item in CUF_last_entry]
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
                print("historical CUF computation for plant{0}".format(str(plant_meta_source.plant)))
                final_time = last_entry.replace(hour=20, minute=59, second=59, microsecond=59)
                initial_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)

                # get the entry daily PR entry as per current time
                daily_CUF = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                    identifier=plant_meta_source.sourceKey,
                                                    ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    print("CUF end time: %s", final_time)
                    print("plant: plant{0}".format(str(plant_meta_source.plant)))
                    cuf_value = calculate_CUF(initial_time,final_time,plant_meta_source.plant)
                except Exception as ex:
                    print("Exception in calculate_CUF: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue
                try:
                    # If entry does not exist for daily PR and it is for historical data
                    if len(daily_CUF) == 0:
                        daily_entry = CUFTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                              identifier=plant_meta_source.sourceKey,
                                                              ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                              CUF=cuf_value,
                                                              updated_at=current_time)
                        daily_entry.save()
                    else:
                        daily_CUF.update(CUF=cuf_value,
                                        updated_at=current_time)

                    #  increase last entry time by 1 day
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                except Exception as ex:
                    print("Exception in calculate_CUF: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

            # calculate PR for current day
            if duration_days == 0 :
                print("Current CUF computation for plant : {0}".format(str(plant_meta_source.plant)))
                final_time = current_time
                initial_time = final_time.replace(hour=6, minute=0, second=0, microsecond=0)
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                # get the entry daily PR entry as per current time
                daily_CUF = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                    identifier=plant_meta_source.sourceKey,
                                                    ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                #result = get_PR_value(initial_time, final_time, plant_meta_source)
                try:
                    print("CUF end time: %s", current_time)
                    print("plant: plant{0}".format(str(plant_meta_source.plant)))
                    cuf_value = calculate_CUF(initial_time,final_time,plant_meta_source.plant)
                except Exception as ex:
                    print("Exception in calculate_CUF: %s", str(ex))
                    continue
                try:
                    # If entry does not exist for daily PR and it is for current data
                    if len(daily_CUF) == 0:
                        print("first CUF entry for current data")
                        daily_CUF = CUFTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                            identifier=plant_meta_source.sourceKey,
                                                            ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                            CUF=cuf_value,
                                                            updated_at=final_time)
                        daily_CUF.save()

                        hourly_entry = CUFTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                           identifier=plant_meta_source.sourceKey,
                                                                           ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                           CUF=cuf_value,
                                                                           updated_at=final_time)
                        hourly_entry.save()

                    # If entry exists for CUF and current time is withing the range of plant operational time
                    elif len(daily_CUF) > 0 and final_time < plant_shut_down_time and final_time > plant_start_time:
                        print("updating CUF in operational hour")
                        daily_CUF.update(CUF=cuf_value,
                                         updated_at=final_time)
                        hourly_entry = CUFTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                           count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                           identifier=plant_meta_source.sourceKey,
                                                                           ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                           CUF=cuf_value,
                                                                           updated_at=final_time)
                        hourly_entry.save()
                    else:
                        daily_CUF.update(updated_at=final_time)
                    try:
                        #compute and update CUF for 15 min time window as a time series of 15 min PR values
                        current_window_mins_slot = ((current_time.hour * 60 + current_time.minute) // KPI_WINDOW_SIZE) - 1
                        if current_window_mins_slot >= 0:
                            window_start_time = current_time.replace(hour= (current_window_mins_slot*KPI_WINDOW_SIZE)//60, minute= (current_window_mins_slot*KPI_WINDOW_SIZE)%60, second=0,microsecond=0)
                            window_end_time = current_time.replace(hour= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)//60, minute= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)%60, second=59,microsecond=0)
                            current_window_CUF_value = calculate_CUF(window_start_time,window_end_time,plant_meta_source.plant)
                            print("Current Window CUF value: %s window start time: %s window end time %s",current_window_CUF_value, window_start_time, window_end_time)

                            try:
                                #write current window PR entry
                                solar_metric = SolarMetrics.objects.get(plant=plant_meta_source.plant,solar_group=None)
                                write_instantanous_solar_metrics(solar_metric.sourceKey,"CUF",current_time, current_window_CUF_value,window_end_time)
                            except Exception as ex:
                                print("Exception in writing current window CUF: %s", str(ex))
                                continue
                    except Exception as ex:
                        print("Exception in calculating CUF for current window: %s", str(ex))
                        continue

                except Exception as ex:
                    print("Exception in calculate_CUF: %s", str(ex))
                    continue

    except Exception as exception:
        print(exception)


def compute_KWH_per_meter_square():
    print("KWH per meter square cron job started - %s", datetime.datetime.now())
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
                print("current_time %s", current_time)
            except Exception as exc:
                print("inside exception " + str(exc))
                current_time = timezone.now()

            # get the last entry made for the daily performance ratio
            KWH_last_entry = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                              identifier=plant_meta_source.sourceKey).limit(1).values_list('updated_at')
            if KWH_last_entry:
                try:
                    last_entry_values = [item[0] for item in KWH_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                        print(last_entry)
                except:
                    KWH_last_entry = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')
                    last_entry_values = [item[0] for item in KWH_last_entry]
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
                print("historical KWH per meter square computation for plant{0} ".format(str(plant_meta_source.plant)))
                final_time = last_entry.replace(hour=23, minute=59, second=59, microsecond=59)
                initial_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)

                # get the entry daily PR entry as per current time
                daily_KWH = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                             identifier=plant_meta_source.sourceKey,
                                                             ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    kwh_value = get_kwh_per_meter_square_value(initial_time,final_time,plant_meta_source.plant)
                except Exception as ex:
                    print("Exception in get_kwh_per_meter_square_value: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue
                try:
                    # If entry does not exist for daily PR and it is for historical data
                    if len(daily_KWH) == 0:
                        daily_entry = KWHPerMeterSquare.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=plant_meta_source.sourceKey,
                                                                     ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                     value=kwh_value,
                                                                     updated_at=current_time)
                        daily_entry.save()
                    else:
                        daily_KWH.update(value=kwh_value,
                                         updated_at=current_time)

                    #  increase last entry time by 1 day
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                except Exception as ex:
                    print("Exception in get_kwh_per_meter_square_value: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

            # calculate PR for current day
            if duration_days == 0 :
                print("Current KWH per meter square computation for plant : {0}".format(str(plant_meta_source.plant)))
                final_time = current_time
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                # get the entry daily PR entry as per current time
                daily_KWH = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                             identifier=plant_meta_source.sourceKey,
                                                             ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                #result = get_PR_value(initial_time, final_time, plant_meta_source)
                try:
                    print("KWH end time: %s", current_time)
                    print("plant: plant{0}".format(str(plant_meta_source.plant)))
                    kwh_value = get_kwh_per_meter_square_value(initial_time,final_time,plant_meta_source.plant)
                except Exception as ex:
                    print("Exception in get_kwh_per_meter_square_value: %s", str(ex))
                    continue
                try:
                    # If entry does not exist for daily PR and it is for current data
                    if len(daily_KWH) == 0:
                        print("first KWH entry for current data")
                        daily_KWH = KWHPerMeterSquare.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=plant_meta_source.sourceKey,
                                                                     ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                     value=kwh_value,
                                                                     updated_at=final_time)
                        daily_KWH.save()

                        hourly_entry = KWHPerMeterSquare.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                               identifier=plant_meta_source.sourceKey,
                                                               ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                               value=kwh_value,
                                                               updated_at=final_time)
                        hourly_entry.save()

                    # If entry exists for KWH and current time is withing the range of plant operational time
                    elif len(daily_KWH) > 0 and final_time < plant_shut_down_time and final_time > plant_start_time:
                        print("updating KWH in operational hour")
                        daily_KWH.update(value=kwh_value,
                                         updated_at=final_time)
                        hourly_entry = KWHPerMeterSquare.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                        identifier=plant_meta_source.sourceKey,
                                                                        ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                        value=kwh_value,
                                                                        updated_at=final_time)
                        hourly_entry.save()
                    else:
                        daily_KWH.update(updated_at=final_time)
                    '''
                    try:
                        #compute and update KWH per m2 for 15 min time window as a time series of 15 min PR values
                        current_window_mins_slot = ((current_time.hour * 60 + current_time.minute) // KPI_WINDOW_SIZE) - 1
                        if current_window_mins_slot >= 0:
                            window_start_time = current_time.replace(hour= (current_window_mins_slot*KPI_WINDOW_SIZE)//60, minute= (current_window_mins_slot*KPI_WINDOW_SIZE)%60, second=0,microsecond=0)
                            window_end_time = current_time.replace(hour= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)//60, minute= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)%60, second=0,microsecond=0)
                            current_window_KWH_value = get_kwh_per_meter_square_value(window_start_time,window_end_time,plant_meta_source.plant)
                            print("Current Window KWH_M2 value %s",current_window_KWH_value)
                            try:
                                #write current window PR entry
                                solar_metric
                                write_instantanous_solar_metrics(solar_metric.sourceKey,"KWH_PER_METER_SQ",current_time, current_window_KWH_value,window_end_time)
                                continue
                            except Exception as ex:
                                print("Exception in writing current window CUF: %s", str(ex))
                                continue
                    except Exception as ex:
                        print("Exception in calculating CUF for current window: %s", str(ex))
                        continue
                    '''
                except Exception as ex:
                    print("Exception in calculate_KWH: %s", str(ex))
                    continue

    except Exception as exception:
        print(exception)


def compute_daily_specific_yield():
    print("Specific yield cronjob started - %s", datetime.datetime.now())
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
                print("current_time %s", current_time)
            except Exception as exc:
                print("inside exception " + str(exc))
                current_time = timezone.now()

            # get the last entry made for the daily performance ratio
            specific_yield_last_last_entry = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                               identifier=plant_meta_source.sourceKey).limit(1).values_list('updated_at')
            if specific_yield_last_last_entry:
                try:
                    last_entry_values = [item[0] for item in specific_yield_last_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                        print(last_entry)
                except:
                    specific_yield_last_last_entry = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                       identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')
                    last_entry_values = [item[0] for item in specific_yield_last_last_entry]
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

            # Calculate specific yield for historical data
            while loop_count < duration_days:
                print("historical specific yield computation for plant{0} ".format(str(plant_meta_source.plant)))
                final_time = last_entry.replace(hour=20, minute=59, second=59, microsecond=59)
                initial_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)

                # get the entry daily specific yield entry as per current time
                daily_specific_yield = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant_meta_source.sourceKey,
                                                                         ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    print("specific yield end time: %s", final_time)
                    print("plant: plant{0} ".format(str(plant_meta_source.plant)))
                    specific_yield = calculate_specific_yield(initial_time,final_time,plant_meta_source.plant)
                except Exception as ex:
                    print("Exception in calculate_specific_yield : %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue
                try:
                    # If entry does not exist for daily PR and it is for historical data
                    if len(daily_specific_yield) == 0:
                        daily_entry = SpecificYieldTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                        identifier=plant_meta_source.sourceKey,
                                                                        ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                        specific_yield=specific_yield,
                                                                        updated_at=current_time)
                        daily_entry.save()
                    else:
                        daily_specific_yield.update(specific_yield=specific_yield,
                                                    updated_at=current_time)

                    #  increase last entry time by 1 day
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                except Exception as ex:
                    print("Exception in calculate_specific_yield: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    # decrease duration day by 1
                    duration_days -= 1
                    continue

            # calculate specfic yield for current day
            if duration_days == 0 :
                print("Current specific yield computation for plant : {0} ".format(str(plant_meta_source.plant)))
                final_time = current_time
                initial_time = final_time.replace(hour=6, minute=0, second=0, microsecond=0)
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                # get the entry daily specific yield entry as per current time
                daily_specific_yield = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant_meta_source.sourceKey,
                                                                         ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    print("specific yield end time: %s", current_time)
                    print("plant: plant{0} ".format(str(plant_meta_source.plant)))
                    specific_yield = calculate_specific_yield(initial_time,final_time,plant_meta_source.plant)
                except Exception as ex:
                    print("Exception in calculate_specific_yield: %s", str(ex))
                    continue
                try:
                    # If entry does not exist for daily PR and it is for current data
                    if len(daily_specific_yield) == 0:
                        print("first specific yield entry for current data")
                        daily_entry = SpecificYieldTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                        identifier=plant_meta_source.sourceKey,
                                                                        ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                        specific_yield=specific_yield,
                                                                        updated_at=final_time)
                        daily_entry.save()

                        hourly_entry = SpecificYieldTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                         identifier=plant_meta_source.sourceKey,
                                                                         ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                         specific_yield=specific_yield,
                                                                         updated_at=final_time)
                        hourly_entry.save()

                    # If entry exists for specific yield and current time is withing the range of plant operational time
                    elif len(daily_specific_yield) > 0 and final_time < plant_shut_down_time and final_time > plant_start_time:
                        print("updating specific yield in operational hour")
                        daily_specific_yield.update(specific_yield=specific_yield,
                                                    updated_at=final_time)
                        hourly_entry = SpecificYieldTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                         identifier=plant_meta_source.sourceKey,
                                                                         ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                         specific_yield=specific_yield,
                                                                         updated_at=final_time)
                        hourly_entry.save()
                    else:
                        daily_specific_yield.update(updated_at=final_time)

                    try:
                        #compute and update Specific_yield for 15 min time window as a time series of 15 min PR values
                        current_window_mins_slot = ((current_time.hour * 60 + current_time.minute) // KPI_WINDOW_SIZE) - 1
                        if current_window_mins_slot >= 0:
                            window_start_time = current_time.replace(hour= (current_window_mins_slot*KPI_WINDOW_SIZE)//60, minute= (current_window_mins_slot*KPI_WINDOW_SIZE)%60, second=0,microsecond=0)
                            window_end_time = current_time.replace(hour= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)//60, minute= ((current_window_mins_slot+1)*KPI_WINDOW_SIZE)%60, second=59,microsecond=0)
                            current_window_sy_value = calculate_specific_yield(window_start_time,window_end_time,plant_meta_source.plant)
                            print("Current Window specific yield value: %s window start time: %s window end time %s",current_window_sy_value, window_start_time, window_end_time)
                            try:
                                #write current window PR entry
                                solar_metric = SolarMetrics.objects.get(plant=plant_meta_source.plant,solar_group=None)
                                write_instantanous_solar_metrics(solar_metric.sourceKey,"SPECIFIC_YIELD",current_time, current_window_sy_value,window_end_time)
                            except Exception as ex:
                                print("Exception in writing current window specific yield: %s", str(ex))
                                continue
                    except Exception as ex:
                        print("Exception in calculating specific yield for current window: %s", str(ex))
                        continue

                except Exception as ex:
                    print("Exception in calculate_specific_yield: %s", str(ex))
                    continue

    except Exception as exception:
        print(exception)


def compute_solar_metrics():
    try:
        compute_daily_performance_ratio()
        compute_daily_CUF()
        compute_KWH_per_meter_square()
        compute_daily_specific_yield()
    except Exception as exception:
        print(str(exception))


