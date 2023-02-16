####################################################################################################
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

######################################################################################################


# Variables
tz_ist = pytz.timezone('Asia/Calcutta')
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
PLANTS=['bbagewadi','dhamdha','krpet','kurnool','periyapattana','rayanpur']
START_DATE = "2018-12-12 01:00:00"
END_DATE = "2018-12-12 23:00:00"


#########################################################################################################


# Function 1
def run_periodic_prediction_adjustments_adani(current_time = timezone.now()):
    print("run_periodic_prediction_adjustments_adani() Periodic prediction adjustment cron job started - %s", datetime.now())
    try:
        plants = SolarPlant.objects.filter(slug__in=PLANTS).values_list('id',flat=True)
        plant_meta_sources = PlantMetaSource.objects.filter(plant_id__in=plants)
    except ObjectDoesNotExist:
        print("run_periodic_prediction_adjustments_adani() No plant meta source found.")

    try:
        for plant_meta_source in plant_meta_sources:
            # check if prediction is enabled for this plant
            if plant_meta_source.prediction_enabled:
                try:
                    # get the plant timezone
                    tz = pytz.timezone(plant_meta_source.dataTimezone)
                    print("run_periodic_prediction_adjustments_adani() timezone of the plant is >>> ", str(tz))
                except:
                    print("run_periodic_prediction_adjustments_adani() error in converting current time to source timezone")
                try:
                    # Convert the current time to timezone of the plant
                    current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                    # check if we are within the operation hours
                    if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
                        print("run_periodic_prediction_adjustments_adani() running prediction adjustment for plant: "+plant_meta_source.plant.slug)
                        #run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
                        run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
                except Exception as ex:
                    print("run_periodic_prediction_adjustments_adani() Exception occured while running the adjustments "+str(ex))
            else:
                print("run_periodic_prediction_adjustments_adani() Skipped since prediction is not enabled for plant"+plant_meta_source.plant.slug)
    except Exception as ex:
        print("run_periodic_prediction_adjustments_adani() raised a generic Exception please check the function " + str(ex))


# Function 2
# Function which does the adjustments for adani
def run_generation_prediction_adjustments(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        # calculate the endtime
        end_time = current_time.replace(minute=0,second=0,microsecond=0)
        #convert endtime to utc
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        # calculate the starttime which is endtime -1
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print("run_generation_prediction_adjustments() start_time_utc >>> "+str(start_time_utc))
        print("run_generation_prediction_adjustments() end_time_utc >>> "+str(end_time_utc))

        #get actual energy
        dict_energy = get_minutes_aggregated_energy(start_time_utc, end_time_utc, plant_meta_source.plant, 'MINUTE',
                                                    PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
        # check if the api returned values..
        if dict_energy and len(dict_energy)>0:
            # convert the api output to a dataframe
            actual_energy = pd.DataFrame(dict_energy)
            # convert to datetime object
            actual_energy['timestamp'] = pd.to_datetime(actual_energy['timestamp'])
            # set the timestamp as index..
            actual_energy.set_index('timestamp',inplace=True)
            print("run_generation_prediction_adjustments() actual energy")
            print(actual_energy.head())
            # get the forecasted dayahead energy
            forecast_energy = getPredictionDataEnergy(plant_meta_source, 'STATISTICAL_DAY_AHEAD',
                                                      start_time_utc, end_time_utc,"plant", PREDICTION_TIMEPERIOD_SPECIFIED)

            print("run_generation_prediction_adjustments() forecast_energy")
            print(forecast_energy.head())

            # if the dataframe is empty just return
            if actual_energy.empty or forecast_energy.empty:
                print("run_generation_prediction_adjustments() actual energy or forecast energy is empty")
                return

            # merge the actual and forecasted energy
            combined = pd.merge(actual_energy, forecast_energy, how='inner', left_index=True, right_index=True)
            print("run_generation_prediction_adjustments() actual and forecast dataframe combined")
            # Change the columns
            combined.columns = ['actual', 'forecast']
            combined = combined[combined['actual']>0]
            actual = combined['actual']
            forecast = combined['forecast']
            # calculae the difference between actual and forecast
            combined['diff'] = actual - forecast

            combined['diff_percentage'] = [round(p,3) for p in ((actual - forecast)*3600*100/(plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED))] # TODO: is this correct?
            # median of the percentage difference
            mean_percentage = combined['diff_percentage'].median()
            print("run_generation_prediction_adjustments() printing the combined dataframe")
            print(combined.head())
            print('run_generation_prediction_adjustments() mean_percentage'+str(mean_percentage))

            start_time_adjustment_utc = end_time_utc
            end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)

            if abs(mean_percentage) >= MAX_FORECAST_ERROR:
                adjustments = mean_percentage * ADJUSTMENT_FACTOR
                print('run_generation_prediction_adjustments() adjustments'+str(adjustments))

                energyData = PredictionData.objects.filter(
                    timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                    count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
                    identifier = plant_meta_source.plant.slug,
                    stream_name = 'plant_energy',
                    model_name = 'STATISTICAL_DAY_AHEAD',
                    ts__gte = start_time_adjustment_utc,
                    ts__lt  = end_time_adjustment_utc)

                for i in range(0,len(energyData)):
                    try:
                        adjusted_value = energyData[i]['value'] + (adjustments * plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/(3600*100)

                        # check if the adjusted value is greater than zero
                        if adjusted_value > 0.0:
                            # change the values only if the adjusted value is greater than zero.
                            PredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                    count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                    identifier=plant_meta_source.plant.slug,
                                                    stream_name = 'plant_energy',
                                                    model_name = 'STATISTICAL_LATEST',
                                                    ts = energyData[i]['ts'],
                                                    value = adjusted_value,
                                                    lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                    upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                    update_at = end_time_utc)

                            # adding for dsm temporarily.
                            PredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                          count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                          identifier=plant_meta_source.plant.slug,
                                                          stream_name='plant_power',
                                                          model_name='STATISTICAL_LATEST_BONSAI_MERGED',
                                                          ts=energyData[i]['ts'],
                                                          value=adjusted_value*4,
                                                          lower_bound=(adjusted_value - BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity),
                                                          upper_bound=(adjusted_value + BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity),
                                                          update_at=end_time_utc)

                            NewPredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                           count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                           identifier_type='plant',
                                                           plant_slug=plant_meta_source.plant.slug,
                                                           identifier=plant_meta_source.plant.slug,
                                                           stream_name = 'plant_energy',
                                                           model_name = 'STATISTICAL_LATEST',
                                                           ts = energyData[i]['ts'],
                                                           value = adjusted_value,
                                                           lower_bound = adjusted_value - BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                           upper_bound=adjusted_value + BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED/3600,
                                                           update_at = end_time_utc)

                            # adding for dsm temporarily.
                            NewPredictionData.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                        count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                                        identifier_type='plant',
                                                        plant_slug=plant_meta_source.plant.slug,
                                                        identifier=plant_meta_source.plant.slug,
                                                        stream_name='plant_power',
                                                        model_name='STATISTICAL_LATEST_BONSAI_MERGED',
                                                        ts=energyData[i]['ts'],
                                                        value=adjusted_value*4,
                                                        lower_bound=adjusted_value - BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity,
                                                        upper_bound=adjusted_value + BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity,
                                                        update_at=end_time_utc)

                        print("run_generation_prediction_adjustments() ADJUSTED: prediction value adjusted: "+str(adjusted_value) + " from original value: "+str(energyData[i]['value']) )
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
        #df = pd.DataFrame()
        df = pd.DataFrame({'timestamp': timestamp, 'predicted': val})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp',inplace=True)
        return df
    except Exception as ex:
        print("getPredictionDataEnergy() Exception in getPredictionDataEnergy: " + str(ex))


# Function 5
# Wrapper function on top of run_statistical_power_prediction
def adjusment_wrapper():
    # Localize to India time..
    local_tz = pytz.timezone('Asia/Kolkata')

    # Parse the end date
    end_date = datetime.strptime(END_DATE, '%Y-%m-%d %H:%M:%S')
    # localize to Asia kolkata
    end_date = local_tz.localize(end_date)
    # Parse the START_TIME.
    today = datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')
    # Localize to IST time.
    today = local_tz.localize(today)


    while (today < end_date):
        print("adjustment_wrapper()  Running for Date >>>> "+str(today))

        # call the function which does power adjustments
        run_periodic_prediction_adjustments_adani(today)

        # Increment today date
        today = today + timedelta(hours=1)
