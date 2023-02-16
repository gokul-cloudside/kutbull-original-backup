#!/usr/bin/python

import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()

from dataglen.models import Sensor, Field
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from django.contrib.auth.models import User
from django.conf import settings
from dataglen.models import ValidDataStorageByStream
from solarrms.models import PredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_energy
from solarrms.cron_statistical_generation_prediction import getPredictionDataEnergy
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import sys
import pytz
import pandas as pd
import numpy as np
from solarrms.cron_stat_generation_prediction_new import save_actual_energy_generation_for_inverters

start_time_str = "2016-09-09 00:00:00"
NO_OF_TRAINING_DAYS = 7
BOUNDS_ON_CAPACITY = 0.15

print "starting offline analysis script"
try:
    plant_meta_sources = PlantMetaSource.objects.all()
except ObjectDoesNotExist:
    print("No plant meta source found.")

#for plant_meta_source in plant_meta_sources:
plant = SolarPlant.objects.get(slug='airportmetrodepot')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
try:
    print ("For plant: "+ str(plant_meta_source.plant.slug))
    #plant = plant_meta_source.plant
    print("Get prediction data")
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
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
    if start_time.tzinfo is None:
        tz = pytz.timezone(plant_meta_source.dataTimezone)
        start_time = tz.localize(start_time)
    start_time_UTC = start_time.astimezone(pytz.timezone('UTC'))
    start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0,minute=0,second=0,microsecond=0)
    dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', 15, split=True, meter_energy=True)
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
        print(df_energy)
        df_energy['timestamp'] = pd.to_datetime(df_energy['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)
        #df_energy.set_index('timestamp',inplace=True)
        #grouped = df_energy.groupby(df_energy['timestamp'].dt.hour,df_energy['timestamp'].dt.minute)
        grouped = df_energy.groupby(df_energy['timestamp'].map(lambda x: (x.hour, x.minute)))
        #grouped = df_energy.groupby(df_energy['timestamp'].map(lambda x: (x.tz_convert(plant_meta_source.dataTimezone).hour, x.tz_convert(plant_meta_source.dataTimezone).minute))
        print grouped
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
    '''
    #dict_actual_energy = get_minutes_aggregated_energy(start_time.replace(minute=0,second=0,microsecond=0), current_time.replace(minute=0,second=0,microsecond=0), plant_meta_source.plant, 'MINUTE', 60, split=False, meter_energy=True)
    actual_energy = pd.DataFrame(dict_actual_energy, columns=['timestamp', 'energy'])
    print "actual energy"
    print actual_energy
    #""""
    actual_energy = getPredictionDataEnergy(plant_meta_source, 'ACTUAL', start_time_utc, end_time_utc)
    if len(actual_energy) == 0:
        print("No actual energy data for last hours")
        return
    #""""
    forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', start_time_UTC, dt_current_time_UTC)
    print "forecast_energy"
    print forecast_energy

    combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
    combined.columns = ['energy', 'forecast']

    print "combined"
    print combined

    actual = combined['energy']
    forecast = combined['forecast']
    combined['diff'] = actual - forecast
    combined['diff_percentage'] = [round(p,1) for p in ((forecast - actual)/plant_meta_source.plant.capacity*100)] # TODO: is this correct?
    list_percent_error = combined['diff_percentage'].to_list()
    print("error distribution:")
    print str(list_percent_error)

    combined['penalty_excess'] = np.where(combined['diff_percentage']<-15,1,0)
    combined['penalty_shortfall'] = np.where(combined['diff_percentage']>15,1,0)

    excess_penalty_percent = (combined['penalty_excess'].sum()/len(combined['penalty_excess']))*100
    shortfall_penalty_percent = (combined['penalty_shortfall'].sum()/len(combined['penalty_shortfall']))*100

    print ("excess_penalty_percent"+ str(excess_penalty_percent))
    print ("shortfall_penalty_percent"+ str(shortfall_penalty_percent))
    '''


except Exception as exc:
        print("inside exception " + str(exc))

tsStart = timezone.now();
tsEnd = tsStart + timedelta(days=2)
type = 'PLANT'
PREDICTION_TIMEPERIOD_SPECIFIED = settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES

df = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD', tsStart, tsEnd, type,PREDICTION_TIMEPERIOD_SPECIFIED)


plant = SolarPlant.objects.get(slug='airportmetrodepot')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
current_time = timezone.now()
save_actual_energy_generation_for_inverters(plant_meta_source,current_time,24,3600)


from solarrms.models import PredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from django.utils import timezone
PREDICTION_TIMEPERIOD_SPECIFIED = 3600
plant = SolarPlant.objects.get(slug='dtu')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
current_time = timezone.now()
start_time = current_time - timedelta(days=1)
dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=True, meter_energy=True)
df_energy = pd.DataFrame()
list_meter_keys =[]
BOUNDS_ON_CAPACITY = 0.15
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
if not df_energy.empty:
            #grouped = df_energy.groupby(df_energy['timestamp'].map(lambda x: x.tz_convert(plant_meta_source.dataTimezone).hour,x.tz_convert(plant_meta_source.dataTimezone).minute))
            df_energy['timestamp'] = pd.to_datetime(df_energy['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)
            grouped = df_energy.groupby(df_energy['timestamp'].map(lambda x: (x.hour, x.minute)))
            df_predicted_median = grouped.median()
            print "df_predicted_median"
            print df_predicted_median
            df_predicted_median.reset_index(inplace = True)
            df_predicted_median["median_sum"] = df_predicted_median[list_meter_keys].sum(axis=1)
            #instead of putting bounds based on quantiles, we would put bound based on % deviation w.r.t to plant capcity for penalty
            df_predicted_median["lower_boud"] = df_predicted_median["median_sum"] - (BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/3600
            df_predicted_median["upper_boud"] = df_predicted_median["median_sum"] + (BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/3600

            list_predicted_median = df_predicted_median["median_sum"].tolist()
            list_timestamp_hour = df_predicted_median["timestamp"].tolist()
            print "list_predicted_median"
            print list_predicted_median
            list_predicted_lower_bound = df_predicted_median["lower_boud"].tolist()
            list_predicted_upper_bound =  df_predicted_median["upper_boud"].tolist()


from solarrms.models import PredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from solarrms.cron_stat_generation_prediction_new import run_generation_prediction_adjustments, run_old_generation_prediction_adjustment
from django.utils import timezone
import pytz
import pandas as pd
PREDICTION_TIMEPERIOD_SPECIFIED = 900
plant = SolarPlant.objects.get(slug='airportmetrodepot')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
tz = pytz.timezone(plant_meta_source.dataTimezone)
current_time = timezone.now()
current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
#start_time = current_time - timedelta(hours=1)
#dict_energy = get_minutes_aggregated_energy(start_time, current_time, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
run_generation_prediction_adjustments(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED)


start_time = timezone.now()
start_time.replace(hour=0,minute=0,second=0,microsecond=0)
#start_time = start_time - timedelta(days=2)
end_time = timezone.now()
start_time = start_time - timedelta(days=7)
run_old_generation_prediction_adjustment(start_time,end_time)