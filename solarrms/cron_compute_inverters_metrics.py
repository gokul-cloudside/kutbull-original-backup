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
from solarrms.solarutils import get_plant_power
import pandas as pd
import numpy as np

COMPUTE_INVERETRS_PR_PLANT_SLUGS = ['cgocomplex','airportmetrodepot','ranergy','demo1','yerangiligi','lohia','palladam','gmr']
start_date = "2017-07-01 00:00:00"

def calculate_pr_for_inverter(starttime, endtime, plant, inverter):
    try:
        df_plant_energy = get_plant_power(starttime, endtime, plant, True, True, True, False)
        df_inverter_energy = pd.DataFrame()
        try:
            df_inverter_energy['energy'] = df_plant_energy[str(inverter.name)]
            df_inverter_energy['timestamp'] = df_plant_energy['timestamp']
            df_inverter_energy['energy'] = df_inverter_energy['energy'].astype(float)
            df_inverter_energy['timestamp'] = df_inverter_energy['timestamp'].apply( lambda x: x.replace(second=0, microsecond=0))
            df_inverter_energy = df_inverter_energy.dropna()
            df_inverter_energy = df_inverter_energy.sort('timestamp')
        except Exception as exception:
            print str(exception)
            return 0

        irradiation_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name='IRRADIATION',
                                                                   timestamp_in_data__gte=starttime,
                                                                   timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
        if len(irradiation_data) == 0:
            irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                   stream_name='IRRADIATION',
                                                                   timestamp_in_data__gte=starttime,
                                                                   timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
        if len(irradiation_data) == 0:
            irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                       stream_name='EXTERNAL_IRRADIATION',
                                                                       timestamp_in_data__gte=starttime,
                                                                       timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

        try:
            idf = pd.DataFrame(irradiation_data[:], columns=['irradiance','timestamp'])
            idf["irradiance"] = idf["irradiance"].astype(float)
            # this call would be slow, look if there's a native pandas function for this using cython
            idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
            idf = idf.sort('timestamp')
            idf = idf.dropna()
        except:
            return 0.00

        if plant.metadata.plantmetasource.energy_from_power:
            pr_values = df_inverter_energy.merge(idf, how='inner', on='timestamp')
            pr_values['average_irradiance'] = (pr_values["irradiance"] + pr_values["irradiance"].shift(+1))/2.0
            pr_values['delta'] = pr_values.diff()['timestamp']
            delta = pd.Timedelta(seconds=20*60)
            pr_values = pr_values[(pr_values['delta']) < delta]
            pr_values = pr_values[(pr_values['energy']) > 0.0]
            try:
                pr_values = pr_values[pr_values['energy'] < 1.5*(inverter.total_capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))] \
                    if inverter.total_capacity else pr_values[pr_values['energy'] < 1.5*(inverter.actual_capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))]
                pr_values['irradiance_energy'] = pr_values['average_irradiance']*(inverter.total_capacity)*(pr_values['delta']/np.timedelta64(1, 'h'))\
                    if inverter.total_capacity else pr_values['average_irradiance']*(inverter.actual_capacity)*(pr_values['delta']/np.timedelta64(1, 'h'))
            except Exception as exception:
                print str(exception)
                pass
            if float(pr_values["irradiance_energy"].sum())==0.0:
                pr = 0.0
            else:
                pr = pr_values["energy"].sum()/pr_values["irradiance_energy"].sum()
            return pr
        else:
            pr_values = df_inverter_energy.merge(idf, how='inner', on='timestamp')
            pr_values['average_irradiance'] = (pr_values["irradiance"] + pr_values["irradiance"].shift(+1))/2.0
            pr_values['energy_diff'] = pr_values["energy"] - pr_values["energy"].shift(+1)
            pr_values['delta'] = pr_values.diff()['timestamp']
            delta = pd.Timedelta(seconds=20*60)
            pr_values = pr_values[(pr_values['delta']) < delta]
            pr_values = pr_values[(pr_values['energy_diff']) > 0.0]
            try:
                pr_values = pr_values[pr_values['energy_diff'] < 1.5*(inverter.total_capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))] \
                    if inverter.total_capacity else pr_values[pr_values['energy_diff'] < 1.5*(inverter.actual_capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))]
                pr_values['irradiance_energy'] = pr_values['average_irradiance']*(inverter.total_capacity)*(pr_values['delta']/np.timedelta64(1, 'h'))\
                    if inverter.total_capacity else pr_values['average_irradiance']*(inverter.actual_capacity)*(pr_values['delta']/np.timedelta64(1, 'h'))
            except Exception as exception:
                print str(exception)
                pass

            if float(pr_values["irradiance_energy"].sum())==0.0:
                pr = 0.0
            else:
                pr = pr_values["energy_diff"].sum()/pr_values["irradiance_energy"].sum()
            return pr

    except Exception as exception:
        print str(exception)
        return 0



def compute_daily_performance_ratio_for_inverters():
    print(" Daily PR cron job started - %s", datetime.datetime.now())
    try:
        try:
            plant_meta_sources = PlantMetaSource.objects.all()
        except ObjectDoesNotExist:
            print("No plant meta source found.")

        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone("Asia/Kolkata"))
            print("current_time %s", current_time)
        except Exception as exc:
            print("inside exception " + str(exc))
            current_time = timezone.now()

        for plant_meta_source in plant_meta_sources:
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
                print("tz", tz)
            except:
                print("error in converting current time to source timezone")
            print("current_time %s", current_time)

            plant = plant_meta_source.plant
            if str(plant.slug) in COMPUTE_INVERETRS_PR_PLANT_SLUGS:
                inverters = plant.independent_inverter_units.all()
                for inverter in inverters:
                    # get the last entry made for the daily performance ratio
                    performance_last_entry = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                  identifier=inverter.sourceKey).limit(1).values_list('updated_at')
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
                                                                                          identifier=inverter.sourceKey).limit(1).values_list('ts')
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
                        print("historical PR computation for plant{0}".format(str(inverter.name)))
                        plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                        plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                        last_entry = plant_start_time

                        # get the entry daily PR entry as per current time
                        daily_performance = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                 count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                 identifier=inverter.sourceKey,
                                                                                 ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                        #result = get_PR_value(plant_start_time, plant_shut_down_time, plant_meta_source)
                        try:
                            print("PR start time: %s", plant_start_time)
                            print("PR end time: %s", plant_shut_down_time)
                            print("plant: plant{0}".format(str(plant_meta_source.plant)))
                            pr_value = calculate_pr_for_inverter(plant_start_time,plant_shut_down_time,plant_meta_source.plant, inverter)
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
                                                                                   identifier=inverter.sourceKey,
                                                                                   ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                   performance_ratio=pr_value,
                                                                                   irradiation=0,
                                                                                   count=0,
                                                                                   sum_irradiation=0,
                                                                                   updated_at=current_time)
                                daily_entry.save()
                            else:
                                daily_performance.update(performance_ratio=pr_value,
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
                                                                                 identifier=inverter.sourceKey,
                                                                                 ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                        #result = get_PR_value(initial_time, final_time, plant_meta_source)
                        try:
                            print("PR start time: %s", plant_start_time)
                            print("PR end time: %s", plant_shut_down_time)
                            print("plant: plant{0}".format(str(plant_meta_source.plant)))
                            pr_value = calculate_pr_for_inverter(plant_start_time,current_time,plant_meta_source.plant, inverter)
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
                                                                                   identifier=inverter.sourceKey,
                                                                                   ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                   performance_ratio=pr_value,
                                                                                   irradiation=0.0,
                                                                                   count=0,
                                                                                   sum_irradiation=0.0,
                                                                                   updated_at=final_time)
                                daily_entry.save()

                                hourly_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                   identifier=inverter.sourceKey,
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
                                                         updated_at=final_time)
                                hourly_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                    identifier=inverter.sourceKey,
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

