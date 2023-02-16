from django.conf import settings
from dataglen.models import ValidDataStorageByStream
from solarrms.models import PredictionData, NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_energy
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import sys
import pytz
import pandas as pd

import traceback

tz_ist = pytz.timezone('Asia/Calcutta')
DG_SERVER = "http://dataglen.com/"
NO_OF_TRAINING_DAYS = 7
PREDICTION_TIMEPERIOD = settings.DATA_COUNT_PERIODS.HOUR
LOWER_BOUND_PERCENTILE = 0.1
UPPER_BOUND_PERCENTILE = 0.9
NO_OF_VALIDATION_HOURS = 3
NO_OF_ADJUSTMENT_HOURS = 1
MAX_FORECAST_ERROR = 10
BOUNDS_ON_CAPACITY = 0.15

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
        print(" Statistical prediction cron job started - %s", datetime.now())
        try:
            try:
                plant_meta_sources = PlantMetaSource.objects.all()
            except ObjectDoesNotExist:
                print("No plant meta source found.")

            for plant_meta_source in plant_meta_sources:
                try:
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
                    #start_time = (current_time - timedelta(hours=1)).replace(minute=0,second=0,microsecond=0)
                    start_time = current_time.replace(hour=0,minute=0,second=0,microsecond=0)
                    #update actual energy for all hours starting from 6:00am
                    #TODO: update for all earlier hours of that day
                    dict_energy = get_minutes_aggregated_energy(start_time, current_time.replace(minute=0,second=0,microsecond=0), plant_meta_source.plant, 'MINUTE', 60, split=False, meter_energy=True)
                    if dict_energy:
                        for i in range(0,len(dict_energy)):
                            pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                  identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'ACTUAL',
                                                                  ts = dict_energy[i]['timestamp'],value = dict_energy[i]['energy'],
                                                                  lower_bound = dict_energy[i]['energy'], upper_bound=dict_energy[i]['energy'],update_at = dt_current_time_UTC)
                            pd_obj.save()
                            pd_obj = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                  identifier_type = 'PLANT',plant_slug=plant_meta_source.plant.slug, identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'ACTUAL',
                                                                  ts = dict_energy[i]['timestamp'],value = dict_energy[i]['energy'],
                                                                  lower_bound = dict_energy[i]['energy'], upper_bound=dict_energy[i]['energy'],update_at = dt_current_time_UTC)
                            pd_obj.save()
                        print("PredictionData actual energy added for last hour")
                    else:
                        print("No actual energy data for last hour")
                    #TODO: Add actual energy data for inverters

                    #if not plant_meta_source.operations_end_time:
                    operations_end_time = 19
                    #else:
                    #    operations_end_time =  plant_meta_source.operations_end_time
                    create_day_ahead_prediction = False
                    print "operations_end_time: " + str(operations_end_time)
                    print "current_time.hour: "+ str(current_time.hour)
                    if current_time.hour >= operations_end_time:
                        #check if day_ahead prediction for tomorow is available
                        day_ahead_prediction_last_entry = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT, count_time_period=PREDICTION_TIMEPERIOD,
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

                        if current_time.hour >= 8:
                            try:
                                run_generation_prediction_adjustments(plant_meta_source, current_time)
                            except Exception as ex:
                                print "Excpetion in hourly prediction adjustments: "+str(ex)

                        if create_day_ahead_prediction:
                                print("Creating day ahead prediction")
                                #create day_ahead_prediction for tomorrow
                                # read last x days energy data
                                start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0,minute=0,second=0,microsecond=0)
                                dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', 60, split=True, meter_energy=True)
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
                                    grouped = df_energy.groupby(df_energy['timestamp'].map(lambda x: x.tz_convert(plant_meta_source.dataTimezone).hour))
                                    df_predicted_median = grouped.median()
                                    print "df_predicted_median"
                                    print df_predicted_median
                                    df_predicted_median.reset_index(inplace = True)
                                    df_predicted_median["median_sum"] = df_predicted_median[list_meter_keys].sum(axis=1)
                                    #instead of putting bounds based on quantiles, we would put bound based on % deviation w.r.t to plant capcity for penalty
                                    df_predicted_median["lower_boud"] = df_predicted_median["median_sum"] - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity
                                    df_predicted_median["upper_boud"] = df_predicted_median["median_sum"] + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity

                                    list_predicted_median = df_predicted_median["median_sum"].tolist()
                                    list_timestamp_hour = df_predicted_median["timestamp"].tolist()
                                    print "list_predicted_median"
                                    print list_predicted_median
                                    list_predicted_lower_bound = df_predicted_median["lower_boud"].tolist()
                                    list_predicted_upper_bound =  df_predicted_median["upper_boud"].tolist()
                                    # save day_ahead prediction
                                    dt_tomorrow = (current_time + timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
                                    for i in range(0,len(list_predicted_median)):
                                        PredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                      identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_DAY_AHEAD',
                                                                      ts = dt_tomorrow.replace(hour = list_timestamp_hour[i]).astimezone(pytz.timezone('UTC')),value = list_predicted_median[i],
                                                                     lower_bound = list_predicted_lower_bound[i], upper_bound=list_predicted_upper_bound[i],update_at = dt_current_time_UTC)

                                        PredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                      identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                      ts = dt_tomorrow.replace(hour = list_timestamp_hour[i]).astimezone(pytz.timezone('UTC')),value = list_predicted_median[i],
                                                                     lower_bound = list_predicted_lower_bound[i], upper_bound=list_predicted_upper_bound[i],update_at = dt_current_time_UTC)

                                        NewPredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                      identifier_type = 'PLANT', plant_slug = plant_meta_source.plant.slug,
                                                                      identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_DAY_AHEAD',
                                                                      ts = dt_tomorrow.replace(hour = list_timestamp_hour[i]).astimezone(pytz.timezone('UTC')),value = list_predicted_median[i],
                                                                     lower_bound = list_predicted_lower_bound[i], upper_bound=list_predicted_upper_bound[i],update_at = dt_current_time_UTC)

                                    print("day ahead prediction added")

                                ### Inverter energy prediction ####
                                start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0,minute=0,second=0,microsecond=0)
                                dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', 60, split=True, meter_energy=False)
                                #dict_energy is a dict
                                df_inverter_energy = pd.DataFrame()
                                list_inverter_keys =[]
                                for inverter_key in dict_energy:
                                    try:
                                        df_stream = pd.DataFrame(dict_energy[inverter_key])
                                        if not df_stream.empty:
                                            df_stream = df_stream.rename(columns={'energy': inverter_key})
                                            df_stream['timestamp'] = pd.to_datetime(df_stream['timestamp'])
                                            df_stream.set_index('timestamp')#,inplace=True)
                                            grouped = df_stream.groupby(df_stream['timestamp'].map(lambda x: x.tz_convert(plant_meta_source.dataTimezone).hour))
                                            df_predicted_median = grouped.median()
                                            print "df_predicted_median"
                                            print df_predicted_median
                                            df_predicted_median.reset_index(inplace = True)
                                            #inverter capacity
                                            inverter_capcity = 0
                                            try:
                                                inverter = IndependentInverter.objects.get(name=inverter_key,plant=plant_meta_source.plant)
                                                #TODO: set appropriate inverter actual or total_capacity
                                                if inverter.actual_capacity or inverter.actual_capacity is not None:
                                                    inverter_capcity = inverter.actual_capacity
                                                elif inverter.total_capacity or inverter.total_capacity is not None:
                                                    inverter_capcity = inverter.total_capacity
                                            except ObjectDoesNotExist:
                                                print "Inverter could not be recognised"

                                            df_predicted_median["lower_boud"] = df_predicted_median[inverter_key] - BOUNDS_ON_CAPACITY*inverter_capcity
                                            df_predicted_median["upper_boud"] = df_predicted_median[inverter_key] + BOUNDS_ON_CAPACITY*inverter_capcity
                                            list_predicted_median = df_predicted_median[inverter_key].tolist()
                                            list_timestamp_hour = df_predicted_median["timestamp"].tolist()
                                            #print "list_predicted_median"
                                            #print list_predicted_median
                                            list_predicted_lower_bound = df_predicted_median["lower_boud"].tolist()
                                            list_predicted_upper_bound =  df_predicted_median["upper_boud"].tolist()
                                            # save day_ahead prediction
                                            dt_tomorrow = (current_time + timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
                                            for i in range(0,len(list_predicted_median)):
                                                PredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                              identifier=inverter.sourceKey, stream_name = 'source_energy', model_name = 'STATISTICAL_DAY_AHEAD',
                                                                              ts = dt_tomorrow.replace(hour = list_timestamp_hour[i]).astimezone(pytz.timezone('UTC')),value = list_predicted_median[i],
                                                                             lower_bound = list_predicted_lower_bound[i], upper_bound=list_predicted_upper_bound[i],update_at = dt_current_time_UTC)

                                                PredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                              identifier=inverter.sourceKey, stream_name = 'source_energy', model_name = 'STATISTICAL_LATEST',
                                                                              ts = dt_tomorrow.replace(hour = list_timestamp_hour[i]).astimezone(pytz.timezone('UTC')),value = list_predicted_median[i],
                                                                             lower_bound = list_predicted_lower_bound[i], upper_bound=list_predicted_upper_bound[i],update_at = dt_current_time_UTC)

                                                NewPredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                              identifier_type = 'SOURCE', plant_slug = plant_meta_source.plant.slug,
                                                                              identifier=inverter.sourceKey, stream_name = 'source_energy', model_name = 'STATISTICAL_DAY_AHEAD',
                                                                              ts = dt_tomorrow.replace(hour = list_timestamp_hour[i]).astimezone(pytz.timezone('UTC')),value = list_predicted_median[i],
                                                                             lower_bound = list_predicted_lower_bound[i], upper_bound=list_predicted_upper_bound[i],update_at = dt_current_time_UTC)

                                            print("day ahead prediction added for inverter: "+ inverter_key)
                                    except Exception as ex:
                                        print("Exception in statistical generation prediction cron job for inverter:  " +inverter_key + " : "+ str(ex))


                except Exception as ex:
                    print("Exception: " + str(ex))
                    continue
        except Exception as ex:
                print("Exception in statistical generation prediction cron job " + str(ex))
    except Exception as ex:
                print("Exception in statistical generation prediction cron job " + str(ex))
                

def run_generation_prediction_adjustments(plant_meta_source, current_time):
    #TODO: add adjustment for inveters
    # get the last NO_OF_VALIDATION_HOURS data of actual and forecasted
    try:
        end_time = current_time.replace(minute=0,second=0,microsecond=0)
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)

        actual_energy = getPredictionDataEnergy(plant_meta_source, 'ACTUAL', start_time_utc, end_time_utc,"PLANT")
        '''
        if actual_energy is None or actual_energy.empty:
            print("No actual energy data for last hours")
            return
        '''
        print "actual energy"
        print actual_energy
        forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"PLANT")
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
        combined['diff'] = actual - forecast
        combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/plant_meta_source.plant.capacity*100)] # TODO: is this correct?
        #combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/actual*100)]
        mean_percentage = combined['diff_percentage'].mean()
        print combined
        print 'mean_percentage', mean_percentage
        start_time_adjustment_utc = end_time_utc
        end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
        forecast_energy_future = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_utc, end_time_utc,"PLANT")
        forecast_energy_future.columns = ['forecast']

        #TODO: check other statistical metrics also, rather just mean error         
        if mean_percentage > MAX_FORECAST_ERROR:
            adjustments = mean_percentage * [0.5] #[0.125, 0.25, 0.5] #Data is coming in reverse order 3rd hour first
            print 'adjustments', adjustments
            start_time_utc = end_time_utc - timedelta(hours=NO_OF_ADJUSTMENT_HOURS)
            energyData = PredictionData.objects.filter(
                timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                count_time_period = PREDICTION_TIMEPERIOD,
                identifier = plant_meta_source.plant.slug,
                stream_name = 'plant_energy',
                model_name = 'STATISTICAL_DAY_AHEAD',
                ts__gte = start_time_adjustment_utc,
                ts__lt  = end_time_adjustment_utc)
            for i in range(0,NO_OF_ADJUSTMENT_HOURS):
                try:
                    adjusted_value = energyData[i]['value'] - adjustments[i]
                    pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD,
                                                                      identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST',
                                                                      ts = energyData[i]['ts'],value = adjusted_value,
                                                                      lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity,
                                                                      upper_bound=adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity,
                                                                      update_at = end_time_utc)
                    pd_obj.save()
                except Exception as ex:
                    print("Exception occured while updating adjustments : " + str(ex))
    except Exception as ex:
        print("Exception in adjustment statistical generation prediction cron job " + str(ex))


def getPredictionDataEnergy(identifier, modelName, tsStart, tsEnd, type):
    # type could be "plant" or "inverter"
    try:
        if type == "PLANT":
            plant_meta_source = identifier
            plantSlug = plant_meta_source.plant.slug
            plantTz   = pytz.timezone(plant_meta_source.dataTimezone)
            identifier_slug = plantSlug
            stream_name = 'plant_energy'
        elif type == "SOURCE":
            plantTz   = pytz.timezone(identifier.dataTimezone)
            identifier_slug = identifier.sourceKey
            stream_name = 'source_energy'
        energyData = PredictionData.objects.filter(
            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
            count_time_period = PREDICTION_TIMEPERIOD,
            identifier = identifier_slug,
            stream_name = stream_name,
            model_name = modelName,
            ts__gte=tsStart,
            ts__lt=tsEnd)
        timestamp = [item.ts.replace(second=0,microsecond=0) for item in energyData]
        timestamp = [pytz.UTC.localize(ts).astimezone(plantTz) for ts in timestamp]
        val = [round(item.value,2) for item in energyData]
        df = pd.DataFrame()
        df = pd.DataFrame({'timestamp': timestamp, modelName: val})
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
