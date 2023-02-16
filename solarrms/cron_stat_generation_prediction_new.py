from django.conf import settings
from dataglen.models import ValidDataStorageByStream
from solarrms.models import PredictionData, NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource, WeatherData
from datetime import datetime, timedelta
from django.utils import timezone
from django_pandas.io import read_frame
from solarrms.solarutils import get_minutes_aggregated_energy
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import sys
import pytz
import pandas as pd
import numpy as np
import logging
from utils.views import send_solutions_infini_sms

SEND_SMS_PLANTS = {'gupl':['9962339300', '9008822822']}

def send_sms(plant, body):
    try:
        numbers = SEND_SMS_PLANTS[str(plant.slug)]
        for number in numbers:
            send_solutions_infini_sms(number, body)
    except Exception as exception:
        print str(exception)

logger = logging.getLogger('cron_stat_prediction')
formatter = logging.Formatter("%(asctime)s - %(levelname)s - " +
                                      "%(filename)s:%(lineno)s - " +
                                      "%(message)s")

file_handler = logging.FileHandler('log_stat_prediction.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


import traceback

tz_ist = pytz.timezone('Asia/Calcutta')
DG_SERVER = "http://dataglen.com/"
NO_OF_TRAINING_DAYS = 7
PREDICTION_TIMEPERIOD = settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES
LOWER_BOUND_PERCENTILE = 0.1
UPPER_BOUND_PERCENTILE = 0.9
NO_OF_VALIDATION_HOURS = 1
NO_OF_VALIDATION_MINS = 30
NO_OF_ADJUSTMENT_HOURS = 1
MAX_FORECAST_ERROR = 9
MAX_FORECAST_ERROR_NEW = 7.5
BOUNDS_ON_CAPACITY = 0.15
OPERATIONS_END_TIME = 20
OPERATIONS_START_TIME = 6
ADJUSTMENT_FACTOR = 0.8
NO_OF_ADJUSTMENT_HOURS = 1
MAX_FORECAST_MAPE_ERROR = 0.15
ADJUSTMENT_PLANTS_15MIN = ['gupl', 'airportmetrodepot', 'yerangiligi']

MODIFIED_STATISTICAL = ('gupl', 'airportmetrodepot', 'yerangiligi')
MAX_CLOUD_COVER = 0.25
ADANI_PLANTS = ['bbagewadi','dhamdha','krpet','kurnool','periyapattana','rayanpur']

'''
    1. read last 30 days total_yield data for all the inverters /meters for each plant
    3. compute statistics metrics - median and percentiles for each inverter for each hour. Sum medians for all inverters for the specific hour to get prediction for that hour.
    4. post-process the prediction if any specific inverter is down etc.
    5. At each hour, check the difference in day-ahead prediction and actual values for last few hours and modify the prediction for next 3 hours
    6. Store day ahead prediction and all revisions in seperate columns day_ahead, 3 hours before, 2 hours before and 1 hour before and actual


    2. prediction model - day_ahead, latest, actual_value (statistical)
    2. if not, generate hourly/ 15 min energy data for each inverter and store it in the processed_historical_energy_data for each plant for each hour. Also, store no. of data points received during that time.
 '''


def run_statistical_generation_prediction():
    try:
        if logger is None:
            print("logger is not specified")
        print(" Statistical prediction cron job started - %s", datetime.now())
        try:
            plant_meta_sources = PlantMetaSource.objects.all()
        except ObjectDoesNotExist:
            logger.debug("No plant meta source found.")

        for plant_meta_source in plant_meta_sources:
            try:
                # Check if prediction needs to be run for this plant if so proceed if not dont proceed.
                if plant_meta_source.prediction_enabled:
                    print ("For plant: "+ str(plant_meta_source.plant.slug))
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
                    dt_current_time_UTC = current_time.astimezone(pytz.timezone('UTC'))
                    print dt_current_time_UTC

                    #Check if ready to do day_ahead_statistical_forecast
                    #if not plant_meta_source.operations_end_time:
                    operations_end_time = OPERATIONS_END_TIME
                    #else:
                    #    operations_end_time =  plant_meta_source.operations_end_time
                    create_day_ahead_prediction = False
                    print "operations_end_time: " + str(operations_end_time)
                    print "current_time.hour: "+ str(current_time.hour)
                    if current_time.hour >= operations_end_time:
                        #check if day_ahead prediction for tomorow is available
                        print("Current time.hour > operations end time")
                        day_ahead_prediction_last_entry = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT, count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                        identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_DAY_AHEAD'
                                                                                        ).limit(1).values_list('ts')
                        if day_ahead_prediction_last_entry:
                            day_ahead_prediction_last_entry = [item[0] for item in day_ahead_prediction_last_entry]
                            last_entry = day_ahead_prediction_last_entry[0]
                            if last_entry.tzinfo is None:
                                last_entry = pytz.utc.localize(last_entry) #TODO: check this
                            if last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone)).replace(hour=0,minute=0,second=0,microsecond=0) <= current_time.replace(hour=0,minute=0,second=0,microsecond=0):
                                create_day_ahead_prediction = True
                            print last_entry
                        else:
                            create_day_ahead_prediction = True
                        if create_day_ahead_prediction:
                            """try:
                                if plant_meta_source.plant.slug == 'gupl':
                                    send_sms(plant_meta_source.plant, "Day ahead prediction has been computed for the plant : " + str(plant_meta_source.plant.name) + ". You can download the report from the portal." )
                            except Exception as exception:
                                print str(exception)
                                pass"""
                            print("Create day ahead predictio: True")
                            compute_day_ahead_statistical_prediction(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
                            print("Hourly prediction completed")
                            compute_day_ahead_statistical_prediction(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
                            print("15 min prediction completed")

                    #Every hour save actual values for last 12 hours
                    save_actual_energy_generation(plant_meta_source,current_time,time_period_hours=24,PREDICTION_TIMEPERIOD_SPECIFIED=settings.DATA_COUNT_PERIODS.HOUR)
                    save_actual_energy_generation(plant_meta_source,current_time,time_period_hours=24,PREDICTION_TIMEPERIOD_SPECIFIED=settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
                    print("actual values saved for last 12 hours")
                else:
                    print("run_statistical_generation_prediction() prediction skipped for plant "+plant_meta_source.plant.slug)
            except Exception as ex:
                print("Exception in run_statistical_generation_prediction: "+str(ex))
                continue
    except Exception as ex:
        print("Exception in run_statistical_generation_prediction: "+str(ex))



def compute_day_ahead_statistical_prediction(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        compute_day_ahead_statistical_prediction_for_plant(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED)
        compute_day_ahead_statistical_prediction_for_inverters(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED)
    except Exception as ex:
        print("Exception in compute_day_ahead_statistical_prediction: "+str(ex))

def save_actual_energy_generation(plant_meta_source,current_time,time_period_hours,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        save_actual_energy_generation_for_plant(plant_meta_source,current_time,time_period_hours,PREDICTION_TIMEPERIOD_SPECIFIED)
        save_actual_energy_generation_for_inverters(plant_meta_source,current_time,time_period_hours,PREDICTION_TIMEPERIOD_SPECIFIED)
    except Exception as ex:
        print("Exception in save_actual_energy_generation: "+str(ex))

def save_actual_energy_generation_for_plant(plant_meta_source,current_time,time_period_hours,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        start_time = (current_time - timedelta(hours=time_period_hours))
        print "current_time", current_time
        print "start_time", start_time
        #update actual energy for all hours starting from 6:00am
        #TODO: update for all earlier hours of that day
        dt_current_time_UTC = timezone.now()
        dict_energy = get_minutes_aggregated_energy(start_time.replace(minute=0,second=0,microsecond=0), current_time.replace(minute=0,second=0,microsecond=0), plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        #print "dict_energy",dict_energy
        if len(dict_energy)>0:
            print dict_energy
            for i in range(0,len(dict_energy)):
                try:
                    print dict_energy[i]['timestamp'], dict_energy[i]['energy']
                    pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                        identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'ACTUAL',
                                        ts = dict_energy[i]['timestamp'],value = dict_energy[i]['energy'],
                                        lower_bound = dict_energy[i]['energy'], upper_bound=dict_energy[i]['energy'],update_at = dt_current_time_UTC)
                    pd_obj.save()
                    pd_obj = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                           identifier_type = 'plant',plant_slug=plant_meta_source.plant.slug, identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'ACTUAL',
                                           ts = dict_energy[i]['timestamp'],value = dict_energy[i]['energy'],
                                           lower_bound = dict_energy[i]['energy'], upper_bound=dict_energy[i]['energy'],update_at = dt_current_time_UTC)
                    pd_obj.save()
                except Exception as ex:
                    print("Exception in save_actual_energy_generation_for_plant inside for: "+str(ex))
            print("PredictionData actual energy added for last hour")
        else:
            print("No actual energy data for last hour")
    except Exception as ex:
        print("Exception in save_actual_energy_generation_for_plant: "+str(ex))

def save_actual_energy_generation_for_inverters(plant_meta_source,current_time,time_period_hours,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        start_time = (current_time - timedelta(hours=time_period_hours))
        dt_current_time_UTC = timezone.now()
        dict_energy = get_minutes_aggregated_energy(start_time.replace(minute=0,second=0,microsecond=0), current_time.replace(minute=0,second=0,microsecond=0), plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=True, meter_energy=False)
        #dict_energy is a dict
        df_inverter_energy = pd.DataFrame()
        list_inverter_keys =[]
        for inverter_name in dict_energy:
            try:
                try:
                    inverter_key = IndependentInverter.objects.get(name=inverter_name,plant=plant_meta_source.plant)
                except Exception as ex:
                    print("inverter key not found for inverter: "+ str(inverter_name))
                    continue
                df_stream = pd.DataFrame(dict_energy[inverter_name])
                #print df_stream
                #df_timestamp = dict_energy["timestamp"]
                if not df_stream.empty:
                    #for i in range(0,len(df_stream)):
                    for index, row in df_stream.iterrows():
                        #print row
                        #print row['timestamp']
                        #print row['energy']
                        pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                            identifier=inverter_key, stream_name = 'source_energy', model_name = 'ACTUAL',
                                            ts = row['timestamp'],value = row['energy'],
                                            lower_bound = row['energy'], upper_bound=row['energy'],update_at = dt_current_time_UTC)
                        pd_obj.save()
                        pd_obj = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                               identifier_type = 'source',plant_slug=plant_meta_source.plant.slug, identifier=inverter_key, stream_name = 'source_energy', model_name = 'ACTUAL',
                                               ts = row['timestamp'],value = row['energy'],
                                               lower_bound = row['energy'], upper_bound=row['energy'],update_at = dt_current_time_UTC)
                        pd_obj.save()
                else:
                    print("No actual energy data for last hour")
                #print("PredictionData actual energy added for last hour")
            except Exception as ex:
                print(str(ex))
                print("Exception in saving actual energy for inverter key: "+inverter_key.souceKey + str(ex))
                continue


    except Exception as ex:
        print("Exception in save_actual_energy_generation_for_inverters: "+str(ex))


def compute_day_ahead_statistical_prediction_for_plant(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:

        ENSEMBLE_DAYS = [3,5,7]
        start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0,minute=0,second=0,microsecond=0)
        dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=True, meter_energy=True)
        #dict_energy is a dict
        print("Received energy info")
        df_energy = pd.DataFrame()
        list_meter_keys =[]
        for meter_key in dict_energy:
            print meter_key
            #print dict_energy[meter_key]
            df_stream = pd.DataFrame(dict_energy[meter_key])
            if not df_stream.empty:
                df_stream = df_stream.rename(columns={'energy': meter_key})
                df_stream['timestamp'] = pd.to_datetime(df_stream['timestamp'])
                df_stream.set_index('timestamp')#,inplace=True)
                list_meter_keys.append(meter_key)
            if df_energy.empty:
                df_energy = df_stream
            else:
                # keep joining series to form a dataframe
                #print(df_stream.info)
                if not df_stream.empty:
                    df_new = pd.merge(df_energy, df_stream, on='timestamp', how='outer')
                    df_energy = df_new
        print df_energy.info()
        # compute statistical parameters
        #if prediction in hour #TODO: change for 15 min
        if not df_energy.empty:
            #grouped = df_energy.groupby(df_energy['timestamp'].map(lambda x: x.tz_convert(plant_meta_source.dataTimezone).hour,x.tz_convert(plant_meta_source.dataTimezone).minute))
            ensemble_median=pd.DataFrame()
            df_energy['timestamp'] = pd.to_datetime(df_energy['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)
            # Find the horizontal sum of each and every row
            df_energy['energy_sum'] = df_energy[list_meter_keys].sum(axis=1)
            # find the timestamp delta between rows
            #df_energy['timestamp_delta'] = df_energy['timestamp'].diff()
            # filter out anomaly rows
            # filter rows less than zero as seen in neelamchowk
            df_energy = df_energy[df_energy['energy_sum'] > 0]
            # filter out those rows which are greater than 1.5*capacity
            df_energy = df_energy[df_energy['energy_sum'] < 1.5*(plant_meta_source.plant.capacity/60.0)*(PREDICTION_TIMEPERIOD_SPECIFIED/60)]
            # now that we have filtered out remove the unwanted columns
            df_energy.drop(['energy_sum'],axis=1,inplace=True)
            #TODO NEED TO CHECK IF ANY SLOTS GETS DELETED BECUASE OF ANOMALY FILTERIING
            # proceed as before
            for d in ENSEMBLE_DAYS:
                start_time_new = (current_time - timedelta(days=d)).replace(hour=0,minute=0,second=0,microsecond=0)
                print start_time_new
                df_energy_new = df_energy[df_energy['timestamp']>=start_time_new]
                print df_energy_new.info()
                grouped = df_energy_new.groupby(df_energy_new['timestamp'].map(lambda x: (x.hour, x.minute)))
                df_predicted_median = grouped.median()
                print "df_predicted_median"
                print df_predicted_median
                df_predicted_median.reset_index(inplace = True)
                df_predicted_median["median_sum"] = df_predicted_median[list_meter_keys].sum(axis=1)
                #instead of putting bounds based on quantiles, we would put bound based on % deviation w.r.t to plant capcity for penalty

                if ensemble_median.empty:
                    print "ensemble_median is empty"
                    ensemble_median = df_predicted_median
                    ensemble_median = ensemble_median.rename(columns={"median_sum":"median_sum"+str(d)})
                    #ensemble_median.set_index('timestamp',inplace = True)
                else:
                    ensemble_stream = df_predicted_median
                    ensemble_stream = ensemble_stream.rename(columns={"median_sum":"median_sum"+str(d)})
                    #ensemble_stream.set_index('timestamp',inplace = True)
                    ensemble_median = pd.merge(ensemble_median,ensemble_stream, on='timestamp', how='outer')
                print ensemble_median

            #ensemble_grouped = ensemble_median.groupby(ensemble_median['timestamp'].map(lambda x: (x.hour, x.minute)))
            #ensemble_predicted_median = ensemble_grouped.median()
            ensemble_median['median_sum'] = ensemble_median[['median_sum3', 'median_sum5','median_sum7']].median(axis=1)
            print ensemble_median
            ensemble_median["lower_bound"] = ensemble_median["median_sum"] - (BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/3600
            ensemble_median["upper_bound"] = ensemble_median["median_sum"] + (BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/3600
            list_predicted_median = ensemble_median["median_sum"].tolist()
            list_timestamp_hour = ensemble_median["timestamp"].tolist()
            print "list_predicted_median"
            print list_predicted_median
            list_predicted_lower_bound = ensemble_median["lower_bound"].tolist()
            list_predicted_upper_bound = ensemble_median["upper_bound"].tolist()
            # save day_ahead prediction
            dt_tomorrow = (current_time + timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                      identifier_type = 'plant', plant_slug = plant_meta_source.plant.slug,identifier=plant_meta_source.plant.slug,
                                      stream_name = 'plant_energy', model_name = 'STATISTICAL_DAY_AHEAD',
                                      date_day_ahead= dt_tomorrow, list_prediction = list_predicted_median,
                                      list_upper_bound=list_predicted_upper_bound, list_lower_bound = list_predicted_lower_bound,
                                      list_ts_hour_min = list_timestamp_hour)
            save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                      identifier_type = 'plant', plant_slug = plant_meta_source.plant.slug,identifier=plant_meta_source.plant.slug,
                                      stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                      date_day_ahead= dt_tomorrow, list_prediction = list_predicted_median,
                                      list_upper_bound=list_predicted_upper_bound, list_lower_bound = list_predicted_lower_bound,
                                      list_ts_hour_min = list_timestamp_hour)

            if plant_meta_source.plant.slug in ADANI_PLANTS:
                power_median = [ item*4 for item in list_predicted_median ]
                power_upper_bound = [ item*4 for item in list_predicted_upper_bound ]
                power_lower_bound =  [ item*4 for item in list_predicted_lower_bound ]
                save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                              count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                              identifier_type='plant', plant_slug=plant_meta_source.plant.slug,
                                              identifier=plant_meta_source.plant.slug,
                                              stream_name='plant_power', model_name='STATISTICAL_LATEST_BONSAI_MERGED',
                                              date_day_ahead=dt_tomorrow, list_prediction=power_median,
                                              list_upper_bound=power_upper_bound,
                                              list_lower_bound=power_lower_bound,
                                              list_ts_hour_min=list_timestamp_hour)

            # STATISTICAL_LATEST_MODIFIED, STATISTICAL_DAY_AHEAD_MODIFIED
            if plant_meta_source.plant.slug in MODIFIED_STATISTICAL:
                save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                          identifier_type = 'plant', plant_slug = plant_meta_source.plant.slug,identifier=plant_meta_source.plant.slug,
                                          stream_name = 'plant_energy', model_name = 'STATISTICAL_DAY_AHEAD_MODIFIED',
                                          date_day_ahead= dt_tomorrow, list_prediction = list_predicted_median,
                                          list_upper_bound=list_predicted_upper_bound, list_lower_bound = list_predicted_lower_bound,
                                          list_ts_hour_min = list_timestamp_hour)
                save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                          identifier_type = 'plant', plant_slug = plant_meta_source.plant.slug,identifier=plant_meta_source.plant.slug,
                                          stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MODIFIED',
                                          date_day_ahead= dt_tomorrow, list_prediction = list_predicted_median,
                                          list_upper_bound=list_predicted_upper_bound, list_lower_bound = list_predicted_lower_bound,
                                          list_ts_hour_min = list_timestamp_hour)

            print("day ahead prediction added")
    except Exception as ex:
        print("Exception: " + str(ex))


def compute_day_ahead_statistical_prediction_for_inverters(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    ### Inverter energy prediction ####
    start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0,minute=0,second=0,microsecond=0)
    dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=True, meter_energy=False)
    #dict_energy is a dict
    df_inverter_energy = pd.DataFrame()
    list_inverter_keys =[]
    for inverter_key in dict_energy:
        try:
            df_stream = pd.DataFrame(dict_energy[inverter_key])
            if not df_stream.empty:
                #df_stream = df_stream.rename(columns={'energy': inverter_key})
                print plant_meta_source.dataTimezone
                print "original timestamp"
                print df_stream['timestamp']
                df_stream['timestamp'] = pd.to_datetime(df_stream['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)

                # inverter capacity
                inverter_capcity = 0
                try:
                    inverter = IndependentInverter.objects.get(name=inverter_key, plant=plant_meta_source.plant)
                    # TODO: set appropriate inverter actual or total_capacity
                    if inverter.actual_capacity or inverter.actual_capacity is not None:
                        inverter_capcity = inverter.actual_capacity
                    elif inverter.total_capacity or inverter.total_capacity is not None:
                        inverter_capcity = inverter.total_capacity
                except ObjectDoesNotExist:
                    print "Inverter could not be recognised"

                print("Inverter Capacity for Inverter >>>> "+inverter_key+" is >>> "+str(inverter_capcity))
                # Perform the filtering
                # find the timestamp delta between rows
                #df_stream['timestamp_delta'] = df_stream['timestamp'].diff()
                # filter out anomaly rows
                # filter rows less than zero as seen in neelamchowk
                df_stream = df_stream[df_stream['energy'] > 0]
                # filter out those rows which are greater than 1.5*capacity
                df_stream = df_stream[df_stream['energy'] < 1.5 * (inverter_capcity / 60.0) * (
                PREDICTION_TIMEPERIOD_SPECIFIED / 60)]
                # now that we have filtered out remove the unwanted columns
                #df_stream.drop(['timestamp_delta'], axis=1, inplace=True)
                #TODO CHECK IF ANY SLOTS GET REMOVED

                df_stream.set_index('timestamp')#,inplace=True)
                grouped = df_stream.groupby(df_stream['timestamp'].map(lambda x: (x.hour,x.minute)))
                df_predicted_median = grouped.median()
                print "df_predicted_median"
                print df_predicted_median
                df_predicted_median.reset_index(inplace = True)

                df_predicted_median["lower_boud"] = df_predicted_median[inverter_key] - (BOUNDS_ON_CAPACITY*inverter_capcity*PREDICTION_TIMEPERIOD_SPECIFIED)/3600
                df_predicted_median["upper_boud"] = df_predicted_median[inverter_key] + (BOUNDS_ON_CAPACITY*inverter_capcity*PREDICTION_TIMEPERIOD_SPECIFIED)/3600
                list_predicted_median = df_predicted_median[inverter_key].tolist()
                list_timestamp_hour = df_predicted_median["timestamp"].tolist()
                #print "list_predicted_median"
                #print list_predicted_median
                list_predicted_lower_bound = df_predicted_median["lower_boud"].tolist()
                list_predicted_upper_bound =  df_predicted_median["upper_boud"].tolist()
                # save day_ahead prediction
                dt_tomorrow = (current_time + timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
                save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                  identifier_type = 'source', plant_slug = plant_meta_source.plant.slug,identifier=inverter.sourceKey,
                                  stream_name = 'source_energy', model_name = 'STATISTICAL_DAY_AHEAD',
                                  date_day_ahead= dt_tomorrow, list_prediction = list_predicted_median,
                                  list_upper_bound=list_predicted_upper_bound, list_lower_bound = list_predicted_lower_bound,
                                  list_ts_hour_min = list_timestamp_hour)
                save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                  identifier_type = 'source', plant_slug = plant_meta_source.plant.slug,identifier=inverter.sourceKey,
                                  stream_name = 'source_energy', model_name = 'STATISTICAL_LATEST',
                                  date_day_ahead= dt_tomorrow, list_prediction = list_predicted_median,
                                  list_upper_bound=list_predicted_upper_bound, list_lower_bound = list_predicted_lower_bound,
                                  list_ts_hour_min = list_timestamp_hour)
        except Exception as ex:
                print("Exception: " + str(ex))
                continue

        print("day ahead prediction added for inverters")


def save_day_ahead_prediction(timestamp_type,count_time_period,identifier_type,plant_slug, identifier,stream_name, model_name, date_day_ahead, list_prediction, list_upper_bound, list_lower_bound, list_ts_hour_min):
    try:
        dt_current_time_UTC = timezone.now()
        for i in range(0,len(list_prediction)):

            #Save data in PredictionData table as STATISTICAL_DAY_AHEAD
            print date_day_ahead
            new_ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1])
            print new_ts
            utc_ts = new_ts.astimezone(pytz.timezone('UTC'))
            print utc_ts

            PredictionData.objects.create(timestamp_type=timestamp_type,count_time_period=count_time_period,
                                          identifier=identifier, stream_name = stream_name, model_name = model_name,
                                          ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1]).astimezone(pytz.timezone('UTC')),value = list_prediction[i],
                                          lower_bound = list_lower_bound[i], upper_bound=list_upper_bound[i],update_at = dt_current_time_UTC)


            #Save data in NewPredictionData table for R app  STATISTICAL_DAY_AHEAD
            NewPredictionData.objects.create(timestamp_type=timestamp_type,count_time_period=count_time_period,
                                             identifier_type =identifier_type, plant_slug = plant_slug,
                                             identifier=identifier, stream_name = stream_name, model_name = model_name,
                                             ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1]).astimezone(pytz.timezone('UTC')),value = list_prediction[i],
                                             lower_bound = list_lower_bound[i], upper_bound=list_upper_bound[i],update_at = dt_current_time_UTC)
    except Exception as ex:
        print("Exception in saving day ahead prediction: "+str(ex))


def save_day_ahead_prediction_inUTC(timestamp_type,count_time_period,identifier_type,plant_slug, identifier,stream_name, model_name, date_day_ahead, list_prediction, list_upper_bound, list_lower_bound, list_ts_hour_min):
    try:
        dt_current_time_UTC = timezone.now()
        for i in range(0,len(list_prediction)):

            #Save data in PredictionData table as STATISTICAL_DAY_AHEAD
            print date_day_ahead
            new_ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1])
            print new_ts
            utc_ts = new_ts.astimezone(pytz.timezone('UTC'))
            print utc_ts

            PredictionData.objects.create(timestamp_type=timestamp_type,count_time_period=count_time_period,
                                          identifier=identifier, stream_name = stream_name, model_name = model_name,
                                          ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1]).astimezone(pytz.timezone('UTC')),value = list_prediction[i],
                                          lower_bound = list_lower_bound[i], upper_bound=list_upper_bound[i],update_at = dt_current_time_UTC)


            #Save data in NewPredictionData table for R app  STATISTICAL_DAY_AHEAD
            NewPredictionData.objects.create(timestamp_type=timestamp_type,count_time_period=count_time_period,
                                             identifier_type =identifier_type, plant_slug = plant_slug,
                                             identifier=identifier, stream_name = stream_name, model_name = model_name,
                                             ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1]).astimezone(pytz.timezone('UTC')),value = list_prediction[i],
                                             lower_bound = list_lower_bound[i], upper_bound=list_upper_bound[i],update_at = dt_current_time_UTC)
    except Exception as ex:
        print("Exception in saving day ahead prediction: "+str(ex))


def run_periodic_prediction_adjustments():
    print(" Periodic prediction adjustment cron job started - %s", datetime.now())
    try:
        plant_meta_sources = PlantMetaSource.objects.all()
    except ObjectDoesNotExist:
        print("No plant meta source found.")

    try:
        for plant_meta_source in plant_meta_sources:
            #if plant_meta_source.plant.slug in ADJUSTMENT_PLANTS_15MIN: #This job is running every 1 hour. So dont; run it for the plants where prediction is being done every 15 mins
            #    return
            #else:
            if plant_meta_source.prediction_enabled:
                try:
                    tz = pytz.timezone(plant_meta_source.dataTimezone)
                    print("tz", tz)
                except:
                    print("error in converting current time to source timezone")
                try:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                    if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
                        print("running prediction adjustment for plant: "+plant_meta_source.plant.slug)
                        run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
                        run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
                except Exception as ex:
                    print("Exception in run_periodic_prediction_adjustments: "+str(ex))
            else:
                print("run_periodic_prediction_adjustments() Skipped since prediction is not enabled for plant"+plant_meta_source.plant.slug)
    except Exception as ex:
        print("run_periodic_prediction_adjustments raised a generic Exception please check the function " + str(ex))


def run_old_generation_prediction_adjustment(start_time,end_time):
    print(" Old prediction adjustment job started - %s", datetime.now())
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
            #current_time = timezone.now()
            current_time = start_time
            while current_time <= end_time:
                current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
                    print("running prediction adjustment for plant: "+plant_meta_source.plant.slug)
                    run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
                    run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
                current_time = current_time+timedelta(hours=1)
        except Exception as ex:
            print("Exception in run_periodic_prediction_adjustments: "+str(ex))


def run_generation_prediction_adjustments(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    try:
        end_time = current_time.replace(minute=0,second=0,microsecond=0)
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print "start_time_utc: "
        print start_time_utc
        print "end_time_utc: "
        print end_time_utc
        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        if dict_energy and len(dict_energy)>0:
            actual_energy = pd.DataFrame(dict_energy)
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            actual_energy.set_index('timestamp',inplace=True)
            print "actual energy"
            print actual_energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
            print "forecast_energy"
            print forecast_energy
            if actual_energy.empty or forecast_energy.empty:
                print "actual energy or forecast energy is empty"
                return
            combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            print "actual and forecast dataframe combined"
            combined.columns = ['actual', 'forecast']
            combined = combined[combined['actual']>0]
            actual = combined['actual']
            forecast = combined['forecast']
            print "len actual: "+str(len(combined))
            #if len(actual) < 3600/PREDICTION_TIMEPERIOD_SPECIFIED:
            #    pass
            #else:
            if len(actual) == 3600/PREDICTION_TIMEPERIOD_SPECIFIED:
                combined['diff'] = actual - forecast
                combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
                #combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/actual*100)]
                mean_percentage = combined['diff_percentage'].median()
                print combined
                print 'mean_percentage', mean_percentage
                start_time_adjustment_utc = end_time_utc
                end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                forecast_energy_future = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
                forecast_energy_future.columns = ['forecast']
                #TODO: check other statistical metrics also, rather just mean error
                if abs(mean_percentage) >= MAX_FORECAST_ERROR:
                    """try:
                        if plant_meta_source.plant.slug == 'gupl' and PREDICTION_TIMEPERIOD_SPECIFIED == settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES:
                            print "sending sms for revised prediction ", timezone.now()
                            send_sms(plant_meta_source.plant, "Predicted generation values have been revised for the plant : " + str(plant_meta_source.plant.name) + ". You can download the revised report from the portal." )
                    except Exception as exception:
                        print str("Exception in sending the sms for revised prediction " + str(exception))
                        pass"""
                    adjustments = mean_percentage * ADJUSTMENT_FACTOR #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
                    print 'adjustments', adjustments
                    start_time_utc = end_time_utc - timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    energyData = PredictionData.objects.filter(
                        timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                        count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                        identifier = plant_meta_source.plant.slug,
                        stream_name = 'plant_energy',
                        model_name = 'STATISTICAL_DAY_AHEAD',
                        ts__gte = start_time_adjustment_utc,
                        ts__lt  = end_time_adjustment_utc)
                    #for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                    for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                        try:
                            adjusted_value = energyData[i]['value'] + (adjustments * plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/(3600*100)
                            pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj.save()
                            pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj_new.save()
                            print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
                        except Exception as ex:
                            print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))



def run_generation_prediction_adjustments_update(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    try:
        end_time = current_time.replace(second=0,microsecond=0)#dont repalce minutes
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        #start_time_utc = end_time_utc - timedelta(minutes=NO_OF_VALIDATION_MINS)
        print "start_time_utc: "
        print start_time_utc
        print "end_time_utc: "
        print end_time_utc
        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        if dict_energy and len(dict_energy)>0:
            actual_energy = pd.DataFrame(dict_energy)
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            actual_energy.set_index('timestamp',inplace=True)
            print "actual energy"
            print actual_energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
            print "forecast_energy"
            print forecast_energy
            if actual_energy.empty or forecast_energy.empty:
                print "actual energy or forecast energy is empty"
                return
            combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            print "actual and forecast dataframe combined"
            combined.columns = ['actual', 'forecast']
            combined = combined[combined['actual']>0]
            actual = combined['actual']
            forecast = combined['forecast']
            print "len actual: "+str(len(combined))
            #if len(actual) < 3600/PREDICTION_TIMEPERIOD_SPECIFIED:
            #    pass
            #else:
            if len(actual) == (3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                combined['diff'] = actual - forecast
                combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
                #combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/actual*100)]
                mean_percentage = combined['diff_percentage'].median()
                print combined
                print 'mean_percentage', mean_percentage
                start_time_adjustment_utc = end_time_utc
                end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                forecast_energy_future = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
                forecast_energy_future.columns = ['forecast']
                #TODO: check other statistical metrics also, rather just mean error
                if abs(mean_percentage) >= MAX_FORECAST_ERROR_NEW:
                    adjustments = mean_percentage * ADJUSTMENT_FACTOR #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
                    print 'adjustments', adjustments
                    start_time_utc = end_time_utc - timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    energyData = PredictionData.objects.filter(
                        timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                        count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                        identifier = plant_meta_source.plant.slug,
                        stream_name = 'plant_energy',
                        model_name = 'STATISTICAL_DAY_AHEAD',
                        ts__gte = start_time_adjustment_utc,
                        ts__lt  = end_time_adjustment_utc)
                    #for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                    for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                        try:
                            adjusted_value = energyData[i]['value'] + (adjustments * plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/(3600*100)
                            pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj.save()
                            pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj_new.save()
                            print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
                        except Exception as ex:
                            print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))

def getPredictionDataEnergy(identifier, modelName, tsStart, tsEnd, type,PREDICTION_TIMEPERIOD_SPECIFIED):
    # type could be "plant" or "inverter"
    try:
        if type == "plant":
            plant_meta_source = identifier
            plantSlug = plant_meta_source.plant.slug
            plantTz   = pytz.timezone(plant_meta_source.dataTimezone)
            identifier_slug = plantSlug
            stream_name = 'plant_energy'
        elif type == "source":
            plantTz   = pytz.timezone(identifier.dataTimezone)
            identifier_slug = identifier.sourceKey
            stream_name = 'source_energy'
        energyData = PredictionData.objects.filter(
            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
            count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
            identifier = identifier_slug,
            stream_name = stream_name,
            model_name = modelName,
            ts__gte=tsStart,
            ts__lt=tsEnd)
        timestamp = [item.ts.replace(second=0,microsecond=0) for item in energyData]
        ##Don't convert the timestamp
        #timestamp = [pytz.UTC.localize(ts).astimezone(plantTz) for ts in timestamp]
        timestamp = [pytz.UTC.localize(ts) for ts in timestamp]
        val = [round(item.value,4) for item in energyData]
        df = pd.DataFrame()
        df = pd.DataFrame({'timestamp': timestamp, 'predicted': val})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp',inplace=True)
        return (df)
    except Exception as ex:
        print "Exception in getPredictionDataEnergy: " + str(ex)

def getInverterCapacity(plant_meta_source):
    inverters = plant_meta_source.plant.independent_inverter_units.all()
    name = [inv.name for inv in inverters]
    capacity = [inv.total_capacity for inv in inverters]
    df = pd.DataFrame({'name': name, 'capacity': capacity})
    return (df)

# get a list of inverters which are active in the past 1 hour or so
# logic is simpple, if there was reading there
def getActiveInverters(plant_meta_source, activeHours):
    plantTz   = pytz.timezone(plant_meta_source.dataTimezone)
    current_time = timezone.now()
    current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
    current_time = current_time.replace(minute=0,second=0)
    start_time = current_time - timedelta(hours=activeHours)
    inv_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', 60, split=True, meter_energy=False)
    inv_active = [inv if len(inv_energy[inv]) > 0 else None for inv in inv_energy]
    inv_active = [inv for inv in inv_active if inv is not None]
    inv_ts = [inv_energy[inv][0]['timestamp'].astimezone(plantTz) for inv in inv_active]
    inv_en = [round(inv_energy[inv][0]['energy'],2) for inv in inv_active]
    df = pd.DataFrame({'name': inv_active, 'timestamp':inv_ts, 'energy': inv_en})
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp',inplace=True)
    return (df)

#Updated periodic djustments only to run for specific plants
def run_periodic_prediction_adjustments_15():
    print(" Periodic prediction adjustment cron job started - %s", datetime.now())
    try:
        plant_meta_sources = PlantMetaSource.objects.filter(plant__slug__in=ADJUSTMENT_PLANTS_15MIN)
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
            if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
                print("running prediction adjustment for plant: "+plant_meta_source.plant.slug)
                run_generation_prediction_adjustments_every_15min(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
                #run_generation_prediction_adjustments_v2(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
                #run_generation_prediction_adjustments_v2(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
        except Exception as ex:
            print("Exception in def run_periodic_prediction_adjustments_MAPE(): "+str(ex))


def run_generation_prediction_adjustments_ensemble(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    """
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    :param plant_meta_source:
    :param current_time:
    :param PREDICTION_TIMEPERIOD_SPECIFIED:
    :return:
    """
    #Run this job every 15 mins and predict for only one slot i.e. 5th slot at present
    #TODO: Predict for 4 slots i.e. 5th to 8th and then apply mechanism to reduce total number of corrections.
    NO_OF_VALIDATION_HOURS = 2
    try:
        end_time = current_time.replace(minute=(current_time.minute-current_time.minute%(PREDICTION_TIMEPERIOD_SPECIFIED/60)),second=0,microsecond=0)
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print "start_time_utc: "
        print start_time_utc
        print "end_time_utc: "
        print end_time_utc
        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        if dict_energy and len(dict_energy)>0:
            actual_energy = pd.DataFrame(dict_energy)
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            #actual_energy.set_index('timestamp',inplace=True)
            print "actual energy"
            print actual_energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
            forecast_energy=forecast_energy.reset_index()
            print "forecast_energy"
            print forecast_energy
            if actual_energy.empty or forecast_energy.empty:
                print "actual energy or forecast energy is empty"
                return
            #combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            combined = pd.merge(actual_energy, forecast_energy, how='inner', on='timestamp')
            print "actual and forecast dataframe combined"
            combined.rename(columns={'energy': 'actual','predicted':'forecast'}, inplace=True)
            print(combined)
            #combined.columns = ['energy', 'forecast']
            combined = combined[combined['actual'] > 0]
            MAPE_ERRORS = []
            PLANT_CAPACITY_ERRORS = []
            #run two loops one for last 1 hour metrics and other loop for last two hours metrics
            start_time_adjustment_utc = end_time_utc+timedelta(hours=1)
            end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
            day_ahead_forecast = PredictionData.objects.filter(
                            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                            count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                            identifier = plant_meta_source.plant.slug,
                            stream_name = 'plant_energy',
                            model_name = 'STATISTICAL_DAY_AHEAD',
                            ts__gte = start_time_adjustment_utc,
                            ts__lt  = end_time_adjustment_utc)
            timestamp = [item.ts.replace(second=0,microsecond=0) for item in day_ahead_forecast]
            ##Don't convert the timestamp
            #timestamp = [pytz.UTC.localize(ts).astimezone(plantTz) for ts in timestamp]
            timestamp = [pytz.UTC.localize(ts) for ts in timestamp]
            val = [round(item.value,4) for item in day_ahead_forecast]
            energyData = pd.DataFrame()
            energyData = pd.DataFrame({'timestamp': timestamp, 'value': val})
            #print day_ahead_forecast
            #energyData = pd.DataFrame(day_ahead_forecast[:], columns=['value','ts'])
            print energyData
            energyData["MAPE1"] = np.nan
            energyData["MAPE2"] = np.nan
            energyData["PCERROR1"] = np.nan
            energyData["PCERROR2"] = np.nan
            #energyData = read_frame(day_ahead_forecast)
            #energyData = pd.DataFrame(list(day_ahead_forecast.objects.all().values()))
            #energyData['timestamp'] = pd.to_datetime(energyData['timestamp'])
            for h in (1,NO_OF_VALIDATION_HOURS):
                start_time_utc_new = end_time_utc - timedelta(hours=h)
                print("generating combined_new: "+str(h))
                combined_new = combined[combined['timestamp']>=start_time_utc_new]
                actual = combined_new['actual']
                forecast = combined_new['forecast']
                print "len actual: "+str(len(combined_new))

                if len(actual) >= 0.5*((3600/PREDICTION_TIMEPERIOD_SPECIFIED)*NO_OF_VALIDATION_HOURS):
                    combined_new['diff'] = actual - forecast
                    #combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
                    combined_new['diff_MAPE'] =  ((actual - forecast)/forecast)
                    median_MAPE = combined_new['diff_MAPE'].median()
                    print combined_new
                    print 'median_MAPE', median_MAPE
                    #TODO: check if absolute value is big enough to consider MAPE error
                    if not np.isnan(median_MAPE) and abs(median_MAPE) >= MAX_FORECAST_MAPE_ERROR:
                        adjustments = median_MAPE * ADJUSTMENT_FACTOR #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
                        print h
                        print 'adjustments', adjustments
                        energyData["MAPE"+str(h)] = (1+adjustments)* energyData["value"]
                    #else:
                    #    energyData["MAPE"+str(h)] = np.nan
                    print("MAPE computation done")
                    combined_new['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))]
                    median_percentage = combined_new['diff_percentage'].median()
                    print "median_percentage", median_percentage
                    if not np.isnan(median_percentage) and abs(median_percentage) >= MAX_FORECAST_ERROR:
                        adjustments = median_percentage * ADJUSTMENT_FACTOR
                        energyData["PCERROR"+str(h)] = energyData["value"] + (adjustments * plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/(3600*100)
                    #else:
                    #    energyData["PCERROR"+str(h)] = np.nan
                    print("PCERROR computation done")
                    print energyData
                    #get ensemble forecast
            if not energyData.empty:
                energyData["ensemble_forecast"]  = energyData[["MAPE1","MAPE2","PCERROR1","PCERROR2"]].median(axis=1)
                print("ensemmble computation done")
                ensemble_forecast = energyData["ensemble_forecast"].dropna()
                print "ensemble_forecast", ensemble_forecast
                if len(ensemble_forecast)>0:
                    #check if ensemble forecast is avaialble
                    energyData_ensemlble = PredictionData.objects.filter(
                            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                            count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                            identifier = plant_meta_source.plant.slug,
                            stream_name = 'plant_energy',
                            model_name = 'STATISTICAL_LATEST_ENSEMBLE',
                            ts__gte = start_time_adjustment_utc,
                            ts__lt  = end_time_adjustment_utc)
                    #energyData_ensemlble = energyData_ensemlble.merge()
                    timestamp = [item.ts.replace(second=0,microsecond=0) for item in energyData_ensemlble]
                    timestamp = [pytz.UTC.localize(ts) for ts in timestamp]
                    val = [round(item.value,4) for item in energyData_ensemlble]
                    print("before old forecast")
                    old_forecast = pd.DataFrame({'timestamp': timestamp, 'old_forecast': val})
                    #old_forecast = read_frame(energyData_ensemlble)
                    #old_forecast['timestamp'] = pd.to_datetime(old_forecast['timestamp'])
                    #old_forecast = old_forecast['timestamp','value']
                    #old_forecast.rename(columns={'value': 'old_forecast'})
                    print "old forecast", old_forecast
                    #old_forecast.set_index('timestamp',inplace=True)
                    energyData = energyData.merge(old_forecast,how='outer',on='timestamp')
                    energyData['forecast_error'] = [round(p,3) for p in ((energyData['old_forecast'] - energyData['ensemble_forecast'])*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))]
                    print("forecast error computed")
                    print "energyData", energyData
                    for index, row in energyData.iterrows():
                        try:
                            #adjusted_value = (1+adjustments)* energyData[i]['value']
                            #TODO: set appropriate % here
                            if not np.isnan(row['forecast_error']) and abs(row['forecast_error'])>= 5:
                                adjusted_value = row["ensemble_forecast"]
                                pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_ENSEMBLE',
                                                                              ts = row['timestamp'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                                pd_obj.save()
                                pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_ENSEMBLE',
                                                                              ts = row['timestamp'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                                pd_obj_new.save()
                                print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(row['old_forecast']) )
                        except Exception as ex:
                            print("Exception occured while updating adjustments : " + str(ex))
                    #for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                        # try:
                        #     #adjusted_value = (1+adjustments)* energyData[i]['value']
                        #     #TODO: set appropriate % here
                        #     if not np.isnan(energyData[i]['forecast_error']) and abs(energyData[i]['forecast_error'])>= 5:
                        #         adjusted_value = energyData[i]["ensemble_forecast"]
                        #         pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                        #                                                       identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_ENSEMBLE',
                        #                                                       ts = energyData[i]['ts'],value = adjusted_value,
                        #                                                       lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                        #                                                       upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                        #                                                       update_at = end_time_utc)
                        #         pd_obj.save()
                        #         pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                        #                                                       identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_ENSEMBLE',
                        #                                                       ts = energyData[i]['ts'],value = adjusted_value,
                        #                                                       lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                        #                                                       upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                        #                                                       update_at = end_time_utc)
                        #         pd_obj_new.save()
                        #         print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
                        # except Exception as ex:
                        #     print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))


def run_generation_prediction_adjustments_MAPE(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    """
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    :param plant_meta_source:
    :param current_time:
    :param PREDICTION_TIMEPERIOD_SPECIFIED:
    :return:
    """
    NO_OF_VALIDATION_HOURS = 1
    try:
        end_time = current_time.replace(minute=(current_time.minute-current_time.minute%(PREDICTION_TIMEPERIOD_SPECIFIED/60)),second=0,microsecond=0)
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print "start_time_utc: "
        print start_time_utc
        print "end_time_utc: "
        print end_time_utc
        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        if dict_energy and len(dict_energy)>0:
            actual_energy = pd.DataFrame(dict_energy)
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            actual_energy.set_index('timestamp',inplace=True)
            print "actual energy"
            print actual_energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
            print "forecast_energy"
            print forecast_energy
            if actual_energy.empty or forecast_energy.empty:
                print "actual energy or forecast energy is empty"
                return
            combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            print "actual and forecast dataframe combined"
            combined.columns = ['actual', 'forecast']
            combined = combined[combined['actual'] > 0]
            actual = combined['actual']
            forecast = combined['forecast']
            print "len actual: "+str(len(combined))
            #if len(actual) < 3600/PREDICTION_TIMEPERIOD_SPECIFIED:
            #    pass
            #else:
            if len(actual) >= 0.5*((3600/PREDICTION_TIMEPERIOD_SPECIFIED)*NO_OF_VALIDATION_HOURS):
                combined['diff'] = actual - forecast
                #combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
                #combined['diff_MAPE'] = [round(p,3) for p in ((actual - forecast)/forecast)]
                combined['diff_MAPE'] =  ((actual - forecast)/forecast)
                #combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/actual*100)]
                median_MAPE = combined['diff_MAPE'].median()
                print combined
                print 'median_MAPE', median_MAPE
                #TODO: check other statistical metrics also, rather just mean error
                if not np.isnan(median_MAPE) and abs(median_MAPE) >= MAX_FORECAST_MAPE_ERROR:
                    start_time_adjustment_utc = end_time_utc+timedelta(hours=1)
                    end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    #forecast_energy_future = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD_MODIFIED', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
                    #forecast_energy_future.columns = ['forecast']

                    adjustments = median_MAPE * ADJUSTMENT_FACTOR #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
                    print 'adjustments', adjustments
                    #start_time_utc = end_time_utc - timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    energyData = PredictionData.objects.filter(
                        timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                        count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                        identifier = plant_meta_source.plant.slug,
                        stream_name = 'plant_energy',
                        model_name = 'STATISTICAL_DAY_AHEAD',
                        ts__gte = start_time_adjustment_utc,
                        ts__lt  = end_time_adjustment_utc)
                    #for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):

                    for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                        try:
                            adjusted_value = (1+adjustments)* energyData[i]['value']
                            pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MAPE',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj.save()
                            pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MAPE',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj_new.save()
                            print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
                        except Exception as ex:
                            print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))


def run_generation_prediction_adjustments_every_15min(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    """
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    :param plant_meta_source:
    :param current_time:
    :param PREDICTION_TIMEPERIOD_SPECIFIED:
    :return:
    """
    NO_OF_VALIDATION_HOURS = 1
    try:
        end_time = current_time.replace(minute=(current_time.minute-current_time.minute%(PREDICTION_TIMEPERIOD_SPECIFIED/60)),second=0,microsecond=0)
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print "start_time_utc: "
        print start_time_utc
        print "end_time_utc: "
        print end_time_utc
        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        if dict_energy and len(dict_energy)>0:
            actual_energy = pd.DataFrame(dict_energy)
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            actual_energy.set_index('timestamp',inplace=True)
            print "actual energy"
            print actual_energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
            print "forecast_energy"
            print forecast_energy
            if actual_energy.empty or forecast_energy.empty:
                print "actual energy or forecast energy is empty"
                return
            combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            print "actual and forecast dataframe combined"
            combined.columns = ['actual', 'forecast']
            combined = combined[combined['actual'] > 0]
            actual = combined['actual']
            forecast = combined['forecast']
            print "len actual: "+str(len(combined))
            #if len(actual) < 3600/PREDICTION_TIMEPERIOD_SPECIFIED:
            #    pass
            #else:
            if len(actual) >= 0.5*((3600/PREDICTION_TIMEPERIOD_SPECIFIED)*NO_OF_VALIDATION_HOURS):
                combined['diff'] = actual - forecast
                combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
                median_diffpercentage = combined['diff_percentage'].median()
                print combined
                print 'median_diffpercentage', median_diffpercentage
                #TODO: check other statistical metrics also, rather just mean error
                if not np.isnan(median_diffpercentage) and abs(median_diffpercentage) >= MAX_FORECAST_ERROR:
                    start_time_adjustment_utc = end_time_utc+timedelta(hours=1)
                    end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    adjustments = median_diffpercentage * ADJUSTMENT_FACTOR #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
                    print 'adjustments', adjustments
                    #start_time_utc = end_time_utc - timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    energyData = PredictionData.objects.filter(
                        timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                        count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                        identifier = plant_meta_source.plant.slug,
                        stream_name = 'plant_energy',
                        model_name = 'STATISTICAL_DAY_AHEAD',
                        ts__gte = start_time_adjustment_utc,
                        ts__lt  = end_time_adjustment_utc)
                    for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                        try:
                            #adjusted_value = (1+adjustments)* energyData[i]['value']
                            adjusted_value = energyData[i]["value"] + (adjustments * plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/(3600*100)
                            pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj.save()
                            pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj_new.save()
                            print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
                        except Exception as ex:
                            print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))


#MODIFIED ADJUSTMENTS
def run_periodic_prediction_adjustments_v2():
    """

    :return:
    """
    print(" Periodic prediction adjustment cron job started - %s", datetime.now())
    try:
        plant_meta_sources = PlantMetaSource.objects.filter(plant__slug__in=MODIFIED_STATISTICAL)
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
            if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
                print("running prediction adjustment for plant: "+plant_meta_source.plant.slug)
                #run_generation_prediction_adjustments_v2(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
                run_generation_prediction_adjustments_v2(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
        except Exception as ex:
            print("Exception in run_periodic_prediction_adjustments: "+str(ex))


def run_generation_prediction_adjustments_v2(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    """
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    :param plant_meta_source:
    :param current_time:
    :param PREDICTION_TIMEPERIOD_SPECIFIED:
    :return:
    """
    try:
        end_time = current_time.replace(minute=0,second=0,microsecond=0)
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print "start_time_utc: "
        print start_time_utc
        print "end_time_utc: "
        print end_time_utc
        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        if dict_energy and len(dict_energy)>0:
            actual_energy = pd.DataFrame(dict_energy)
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            actual_energy.set_index('timestamp',inplace=True)
            print "actual energy"
            print actual_energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD_MODIFIED', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
            print "forecast_energy"
            print forecast_energy
            if actual_energy.empty or forecast_energy.empty:
                print "actual energy or forecast energy is empty"
                return
            combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            print "actual and forecast dataframe combined"
            combined.columns = ['actual', 'forecast']
            actual = combined['actual']
            forecast = combined['forecast']
            print "len actual: "+str(len(combined))
            if len(actual) < 3600/PREDICTION_TIMEPERIOD_SPECIFIED:
                pass
            else:
                combined['diff'] = actual - forecast
                combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
                #combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/actual*100)]
                mean_percentage = combined['diff_percentage'].mean()
                print combined
                print 'mean_percentage', mean_percentage
                start_time_adjustment_utc = end_time_utc
                end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                forecast_energy_future = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD_MODIFIED', start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)
                forecast_energy_future.columns = ['forecast']
                #TODO: check other statistical metrics also, rather just mean error
                if abs(mean_percentage) >= MAX_FORECAST_ERROR:
                    adjustments = mean_percentage * ADJUSTMENT_FACTOR #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
                    print 'adjustments', adjustments
                    start_time_utc = end_time_utc - timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
                    energyData = PredictionData.objects.filter(
                        timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                        count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                        identifier = plant_meta_source.plant.slug,
                        stream_name = 'plant_energy',
                        model_name = 'STATISTICAL_DAY_AHEAD_MODIFIED',
                        ts__gte = start_time_adjustment_utc,
                        ts__lt  = end_time_adjustment_utc)
                    #for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):

                    #get cloudcover for next 4 slot
                    cloud_cover = _get_predicted_cloudcover(start_time_adjustment_utc, end_time_adjustment_utc, plant_meta_source.plant.slug)

                    for i in range(0,NO_OF_ADJUSTMENT_HOURS*3600/PREDICTION_TIMEPERIOD_SPECIFIED):
                        try:
                            if adjustments < 0:
                                adjusted_value = energyData[i]['value'] + (adjustments * plant_meta_source.plant.capacity * PREDICTION_TIMEPERIOD_SPECIFIED) / (3600 * 100)
                            elif adjustments > ADJUSTMENT_FACTOR and cloud_cover > MAX_CLOUD_COVER:
                                adjusted_value = energyData[i]['value'] + (adjustments * plant_meta_source.plant.capacity * PREDICTION_TIMEPERIOD_SPECIFIED) / (3600 * 100)
                            else:
                                adjusted_value = energyData[i]['value']
                            pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MODIFIED',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj.save()
                            pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                                                              identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MODIFIED',
                                                                              ts = energyData[i]['ts'],value = adjusted_value,
                                                                              lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                                              update_at = end_time_utc)
                            pd_obj_new.save()
                            print("ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
                        except Exception as ex:
                            print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))


def _get_predicted_cloudcover(start_time_adjustment_utc, end_time_adjustment_utc, plant_slug):
    """

    :param start_time_adjustment_utc:
    :param end_time_adjustment_utc:
    :param plant_slug:
    :return:
    """
    weather_data = []
    try:
        weather_data = WeatherData.objects.filter(api_source="darksky", timestamp_type=WeatherData.HOURLY,
                                                  identifier=plant_slug, prediction_type=WeatherData.FUTURE,
                                                  ts__gte=start_time_adjustment_utc, ts__lt=end_time_adjustment_utc).order_by('prediction_type', 'ts').values_list('cloudcover')
    except Exception as exception:
        print "exception in _get_predicted_cloudcover"
    return weather_data[0] if weather_data else 0.0
