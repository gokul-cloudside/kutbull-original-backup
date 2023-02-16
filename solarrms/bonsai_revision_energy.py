############################ ###############################################################
# Imports
import pandas as pd
import numpy as np
#import django
import sys
import os
#sys.path.append("/var/www/kutbill")
sys.path.append("/var/www/EdgeML_TF/tf")
#os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
#django.setup()
from solarrms.models import WeatherData, NewPredictionData, SolarPlant, PredictionData
from dataglen.models import ValidDataStorageByStream
from datetime import datetime, timedelta, time
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings
import shutil
from solarrms.solarutils import get_minutes_aggregated_energy, get_minutes_aggregated_power
import pytz
from edgeml.predictor.bonsaiPredictorOptim import bonsaiPredictorOptim
import pickle
from cassandra.cqlengine.query import BatchQuery



##############################################################################################
# Model related variables.
ENERGY_MODEL_NAME = 'GBM_DAY_AHEAD_SOLCAST'
POWER_MODEL_NAME = 'GBM_DAY_AHEAD_SOLCAST'
OUTPUT_MODEL_NAME='STATISTICAL_LATEST_BONSAI_GOVT'
PLANTS = ['bbagewadi', 'rayanpur', 'periyapattana', 'kurnool', 'krpet', 'dhamdha']

# Output Folder related variables
ENERGY_OUTPUT_FOLDER = "/usr/local/lib/BONSAI_N/ENERGY/"
POWER_OUTPUT_FOLDER = "/usr/local/lib/BONSAI_N/POWER/"
TRAIN_ENERGY_OUTPUT_FOLDER = "/usr/local/lib/BONSAI_TRAIN/ENERGY/"
TRAIN_POWER_OUTPUT_FOLDER = "/usr/local/lib/BONSAI_TRAIN/POWER/"
EDGEML_DIR = "/var/www/EdgeML_TF"

# Plant related variables.
PROD_START_HOUR = 6
PROD_END_HOUR = 18
TRAINING_DAYS = 60
OPERATIONS_END_HOUR = 20
POINTS_PER_DAY = 48
PREDICTION_TIMEPERIOD_SPECIFIED = 900

# Forecast error related variables.
# Starttime for realtime
DAY_START_TIME = time(8, 0)
# Forecast vs Actual method  change here if needed change it to MEAN_MEDIAN if needs to be changed
FORECAST_ERROR_METHOD = 'MEAN_MEDIAN'
if FORECAST_ERROR_METHOD == 'CORRELATION':
    # if the correlation coefficient is less than 1-MAX_FORECAST_ERROR
    MAX_FORECAST_ERROR = 0.20
    PERCENT_ERROR_UPPER_BOUND = 0.50
elif FORECAST_ERROR_METHOD == 'MEAN_MEDIAN':
    # this is when MEAN_MEDIAN is invoked.
    MAX_FORECAST_ERROR = 8
    PERCENT_ERROR_UPPER_BOUND = 50

# Slot related variables.
# Number of slots..
LOOK_BACK_SLOTS = 8
NO_OF_SLOTS = 9
# Variables to be used in the program edit here if needed
BOUNDS_ON_CAPACITY = 0.15
# SLOT NUMBER 1,2,3,4,5,6,7,8,9
PLANT_SLOT_DICT = {
    'bbagewadi': {'REVISION_START_SLOTNUMBER': 4, 'REVISION_END_SLOTNUMBER': 9},
    'rayanpur': {'REVISION_START_SLOTNUMBER': 4, 'REVISION_END_SLOTNUMBER': 9},
    'periyapattana': {'REVISION_START_SLOTNUMBER': 4, 'REVISION_END_SLOTNUMBER': 9},
    'kurnool': {'REVISION_START_SLOTNUMBER': 4, 'REVISION_END_SLOTNUMBER': 9},
    'krpet': {'REVISION_START_SLOTNUMBER': 4, 'REVISION_END_SLOTNUMBER': 9},
    'dhamdha': {'REVISION_START_SLOTNUMBER': 4, 'REVISION_END_SLOTNUMBER': 9}
}


# Historical Predictions edit the start and end time here
START_DATE = "2018-10-1 00:00:00"
END_DATE   = "2018-10-10 3:30:00"

##############################################################################################
# Functions

# Function 1
# Read the required data from cassandra for the given plant. It preps both power and energy data pass appropriate parameters
def read_cassandra_data(plant, starttime, endtime, training=True, energy=True, real_time=False):
    """
        :param plant:
        :param start_time_planttimezone:
        :param end_time_planttimezone:
        :param training true or false
        :param energy true or false
        :param real_time true or false
        :return: pandas dataframe
    """

    #################################################################################################################
    # get the predicted and actual irradiation data.
    try:
        future_weather_data = WeatherData.objects.filter(api_source='solcast',
                                                         timestamp_type=WeatherData.HOURLY,
                                                         identifier=plant.slug,
                                                         prediction_type=WeatherData.FUTURE,
                                                         ts__gte=starttime,
                                                         ts__lt=endtime) \
            .values_list('ts', 'ghi')
        # create a dataframe from the above list
        future_weather_df = pd.DataFrame(future_weather_data[:], columns=['timestamp', 'predicted_irradiation'])
        future_weather_df['timestamp'] = pd.to_datetime(future_weather_df['timestamp']).dt.tz_localize('UTC')
        # replace seconds and  micro seconds to zero.
        future_weather_df['timestamp'] = future_weather_df['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
        # drop the duplicate rows
        future_weather_df.drop_duplicates(inplace=True)
        print("\n\n read_cassandra_data() weather_df printing the head/tail")
        print(future_weather_df.head())
        print(future_weather_df.tail())


        # Download the current irradiation data from valid data storage.
        current_weather_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                       stream_name='IRRADIATION',
                                                                       timestamp_in_data__gte=starttime,
                                                                       timestamp_in_data__lt=endtime)\
            .limit(0).values_list('timestamp_in_data', 'stream_value')
        # create a dataframe from the above list
        current_weather_df = pd.DataFrame(current_weather_data[:], columns=['timestamp', 'actual_irradiation'])
        current_weather_df['timestamp'] = pd.to_datetime(current_weather_df['timestamp']).dt.tz_localize('UTC')
        current_weather_df['timestamp'] = current_weather_df['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
        # Multiply actual_irradiation by 1000 as solcast is in that range..
        current_weather_df['actual_irradiation'] = current_weather_df['actual_irradiation'].apply(lambda x: float(x) * 1000)
        # drop the duplicate rows
        current_weather_df.drop_duplicates(inplace=True)
        print("\n\n read_cassandra_data() weather_df printing the head/tail")
        print(current_weather_df.head())
        print(current_weather_df.tail())

        # Merge the Current with the future weather data.
        # join the above two Dataframes..
        merged_weather_df = current_weather_df.merge(future_weather_df, how='outer', on='timestamp')
        print("read_cassandra_data() merged_weather_df printing the head")
        print(merged_weather_df.head())


    except Exception as e:
        print("read_cassandra_data() Exception occurred while trying to fetch the solcast weather data " + str(e))
        # return an empty dataframe
        return pd.DataFrame()

    ##############################################################################################################
    # assign proper variable names which would be used later for filtering the right data...
    if energy:
        STREAM_NAME = 'plant_energy'
        MODEL_NAME = ENERGY_MODEL_NAME
        UNIT = 'energy'
    else:
        STREAM_NAME = 'plant_power'
        MODEL_NAME = POWER_MODEL_NAME
        UNIT = 'power'

    try:
        # get the dayahead predicted energy.
        predicted_plant_data = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                count_time_period=900,
                                                                identifier_type='plant',
                                                                plant_slug=str(plant.slug),
                                                                identifier=str(plant.slug),
                                                                stream_name=STREAM_NAME,
                                                                model_name=MODEL_NAME,
                                                                ts__gte=starttime,
                                                                ts__lte=endtime).values_list('ts', 'value')
        # convert it in to a dataframe.
        predicted_plant_df = pd.DataFrame(predicted_plant_data[:], columns=['timestamp', 'predicted_' + UNIT])
        # convert timestamp to datetime
        predicted_plant_df['timestamp'] = pd.to_datetime(predicted_plant_df['timestamp']).dt.tz_localize('UTC')
        # convert the predicted power column to a float..
        predicted_plant_df['predicted_' + UNIT] = predicted_plant_df['predicted_' + UNIT].astype(float)
        print('read_cassandra_data() printing the head/tail of the predicted_plant_df dataframe..')
        print(predicted_plant_df.head())
        print(predicted_plant_df.tail())

        if real_time:
            print("read_cassandra_data() getting the realtime data from cassandra...")

            if energy:
                # Call the function which basically returns the Energy Values.
                actual_plant_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'MINUTE',
                                                                  PREDICTION_TIMEPERIOD_SPECIFIED / 60,
                                                                  split=False)
            else:
                actual_plant_dict = get_minutes_aggregated_power(starttime, endtime, plant, 'MINUTE',
                                                                 PREDICTION_TIMEPERIOD_SPECIFIED / 60, split=False,
                                                                 meter_energy=True)

            print("read_cassandra_data() Call to  API completed..")
            # print(actual_plant_dict)

            # convert the energy to a dict
            # convert it to a dataframe
            actual_plant_df = pd.DataFrame(actual_plant_dict)
            actual_plant_df = actual_plant_df[['timestamp', UNIT]]
            actual_plant_df.columns = ['timestamp', 'actual_' + UNIT]
            # no needd to localize to UTC as the api is already sending in UTC..
            actual_plant_df['timestamp'] = pd.to_datetime(actual_plant_df['timestamp'])
            actual_plant_df['actual_' + UNIT] = actual_plant_df['actual_' + UNIT].astype(float)

        else:
            # get the dayahead predicted energy.
            actual_plant_list = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                 count_time_period=900,
                                                                 identifier_type='plant',
                                                                 plant_slug=str(plant.slug),
                                                                 identifier=str(plant.slug),
                                                                 stream_name=STREAM_NAME,
                                                                 model_name='ACTUAL',
                                                                 ts__gte=starttime,
                                                                 ts__lte=endtime).values_list('ts', 'value')

            # convert it to a dataframe
            actual_plant_df = pd.DataFrame(actual_plant_list[:], columns=['timestamp', 'actual_' + UNIT])
            actual_plant_df['timestamp'] = pd.to_datetime(actual_plant_df['timestamp']).dt.tz_localize('UTC')

        print("read_cassandra_data() printing the head/tail of actual_plant_df Dataframe ")
        print(actual_plant_df.head())
        print(actual_plant_df.tail())

        # combine both the dataframes changed from inner join to outer join to support realtime..
        plant_df = predicted_plant_df.merge(actual_plant_df, how='outer', on='timestamp')
        print("read_cassandra_data() printing the head/tail of Merged Dataframe actual and predicted. ")
        print(plant_df.head())
        print(plant_df.tail())

    except Exception as e:
        print("read_cassandra_data() Exception occurred while trying to fetch the " + UNIT + "data " + str(e))
        # return an empty dataframe
        return pd.DataFrame()

        ########################################################################################################

    # if both the energy df and the weather df is not empty merge these two dataframes.
    if not plant_df.empty and not merged_weather_df.empty:

        try:

            # merge operation
            final_df = plant_df.merge(merged_weather_df, how='outer', on='timestamp')

            # convert it in to plant timezone
            final_df['timestamp'] = pd.to_datetime(final_df['timestamp']).dt.tz_convert(plant.metadata.dataTimezone)

            # sort the dataframe based on timestamp
            final_df.sort_values(by=['timestamp'], ascending=True, inplace=True)

            # create the slot
            final_df['minute'] = final_df['timestamp'].dt.hour * 60 + final_df['timestamp'].dt.minute
            # now filter only those data between 6 and 18
            # Filter only those data which are > 6 and < 18
            final_df = final_df[(final_df['timestamp'].dt.hour >= PROD_START_HOUR) &
                                (final_df['timestamp'].dt.hour <= PROD_END_HOUR)]

            # as the solcast data comes only every half hour find the average.
            # Handle missing data
            final_df['predicted_irradiation'] = final_df['predicted_irradiation'].fillna(
                (final_df['predicted_irradiation'].shift() + final_df['predicted_irradiation'].shift(-1)) / 2)

            # IF  the dataset is created for training drop the na's
            if training == True:
                # drop the na
                final_df = final_df.dropna()

            # FILTER ONLY THOSE DAYS WHICH HAVE ALL THE POINTS IN THEM FOR TRAINING.
            # Filter only those days which has enough data in it.
            final_df['date'] = final_df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d'))

            # find the number of records  per date
            final_df = pd.merge(final_df, final_df.groupby(['date']).size().reset_index(name='counts'), on='date',
                                how='inner')

            if training:
                # Filter out those rows which have < POINTS_PER_DAY
                final_df = final_df[final_df['counts'] >= POINTS_PER_DAY]

            # drop the date column
            final_df.drop('counts', axis=1, inplace=True)

            # IMPORTANT TO KEEP ACTUAL ENERGY AS THE SECOND COLUMN...
            final_df = final_df[
                ['timestamp', 'actual_' + UNIT, 'actual_irradiation', 'predicted_' + UNIT, 'predicted_irradiation',
                 'minute', 'date']]

            # if computing in realtime shift by 1 becuasse of grouped = df_final.groupby(pd.TimeGrouper("15Min")) instead of
            # grouped = df_final.groupby(pd.TimeGrouper("15Min",label='right'))
            if energy:
                final_df['actual_' + UNIT] = final_df['actual_' + UNIT].shift(1)

            # pritning the final merged dataframe
            print("read_cassandra_data() printing the final merged dataframe...")
            print(final_df.head(300))

            # now that all the opration is done return the dataframe
            return final_df
        except Exception as e:
            print("read_cassandra_data() Exception occurred while trying to merge " + UNIT + " and weather " + str(e))
            return pd.DataFrame()

    else:
        pd.DataFrame()


####################################################################################################################

# Function 2
# Function which splits the dataframe in to training and test numpy arrays for bonsai..
def train_test_split(df, path, slot):
    try:
        print("train_test_split() number of NULL values present : ", np.sum(df.isnull().sum(axis=0)))
        print("train_test_split() Shape of the df : ", df.shape)
        # Calculate the split.
        split = int(0.8 * df.shape[0])

        # split the dataframe in to 80 20 split
        train = df.values[:split, :]
        test = df.values[split:, :]

        print("train_test_split() train dataframe shape >>> " + str(train.shape))
        print("train_test_split() test dataframe shape >>> " + str(test.shape))

        out_path = path.rstrip("/") + "/slot" + str(slot)
        os.mkdir(out_path)

        # pickle the numpy arrays on disk
        np.save(out_path.rstrip("/") + "/train.npy", train)
        np.save(out_path.rstrip("/") + "/test.npy", test)
    except Exception as e:
        print('train_test_split() generic exception raised in the function check it ' + str(e))



#####################################################################################################################

# Function 3
# inline function used for sorting columns
def getcolnumber(col):
    list1 = col.split("-")
    if len(list1) > 1:
        # print(float(list1[1]))
        l2 = list1[1].split(".")
        return float(l2[0]) * 1000 + float(l2[1])
    else:
        return 1



# Function 4
# Function which performs the required shifts for creating the final Input Datasets for Bonsai.
def bonsai_dataframe_prep(df, plant, training=True, energy=True):

    # assign proper output folder based on the input being passed...
    if energy:
        OUTPUT_FOLDER = TRAIN_ENERGY_OUTPUT_FOLDER
        UNIT = 'energy'
    else:
        OUTPUT_FOLDER = TRAIN_POWER_OUTPUT_FOLDER
        UNIT = 'power'

    # sort the dataframe by timestamp in ascending order
    s_df = df.sort_values(by='timestamp')

    # create the shifts which were done in microsoft..
    slots = list(range(1, NO_OF_SLOTS + 1))
    # create the date field
    grouped = s_df.groupby('date')

    # delete the directories only for training..
    if training:
        try:
            shutil.rmtree(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug, ignore_errors=True)
            # make the plant directory
            # make the pandas directory for each plant
            # make the numpy directory for each plant.
            os.makedirs(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug)
            os.makedirs(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/pandas")
            os.makedirs(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai")
        except Exception as e:
            print("bonsai_dataframe_prep() exception raised while creating folder for plant >> " + str(plant.slug)+ str(e))

    OUTPUT_DATAFRAME_LIST = []
    # perform the shift operation for each of the slots.
    for slot in slots:

        # deep copy the dataframe..
        slot_df = s_df.copy(deep=True)

        # Create the dataframes for each of the slots..
        for i in list(range(slot, slot + LOOK_BACK_SLOTS)):
            # perform the required shifts for actual energy/power and irradiation..
            slot_df[UNIT + '-1.' + str(i)] = grouped['actual_' + UNIT].shift(i)
            slot_df['actual_irradiation-2.' + str(i)] = grouped['actual_irradiation'].shift(i)
            # slot_df['day_ahead_prediction-3.' + str(i)] = grouped['predicted_energy'].shift(i)
            # slot_df['predicted_irradiation-4.' + str(i)] = grouped['predicted_irradiation'].shift(i)

        # create the dayahead and predicted irradiation columns..
        for i in list(range(1, LOOK_BACK_SLOTS + 1)):
            slot_df['day_ahead_' + UNIT + '-3.' + str(i)] = grouped['predicted_' + UNIT].shift(i)
            slot_df['predicted_irradiation-4.' + str(i)] = grouped['predicted_irradiation'].shift(i)

        # reindex based on column order
        slot_df = slot_df.reindex_axis(sorted(slot_df.columns, key=lambda x: float(getcolnumber(x))), axis=1)

        # Drop the NAN rows
        slot_df = slot_df.dropna()

        # if training is done drop all the nan and also drop the timestamp and date column
        if training:
            # drop the timestamp and date columns
            slot_df.drop(['timestamp', 'date', 'actual_irradiation'], axis=1, inplace=True)

        print("\n\n\n###########################################################################")
        print("Printing the the head / tail of the slot " + str(slot))
        print(slot_df.head())
        print(slot_df.tail())
        print("\n\n Slot columns >>> " + str(list(slot_df.columns)))
        print("###########################################################################")

        # write it to a file only if training=true
        if training:
            # write pandasdf as a csv
            slot_df.to_csv(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/pandas/slot" + str(slot) + ".csv",
                           index=False)
            # Now call the function which creates trainng and test numpy arrays.
            train_test_split(slot_df, OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai", slot)
        else:
            OUTPUT_DATAFRAME_LIST.append(slot_df)

    # if its not training return the dataframe list...
    if training == False:
        return OUTPUT_DATAFRAME_LIST



###############################################################################################################
# Function 5
# Bonsai revision prep function which loops through each of the plant
def bonsai_revision_prep(today=timezone.now()):
    try:
        print("bonsai_revision_prep() bonsai revision dataset preparation job started current time is  >>>> %s",datetime.now())

        # Get all the properties raise exception if no properties
        try:
            # plants = SolarPlant.objects.all()
            plants = SolarPlant.objects.filter(slug__in=PLANTS)
        except ObjectDoesNotExist:
            print("bonsai_revision_prep() No plants found .. ")

        # delete the output folder
        shutil.rmtree(TRAIN_ENERGY_OUTPUT_FOLDER, ignore_errors=True)
        shutil.rmtree(TRAIN_POWER_OUTPUT_FOLDER, ignore_errors=True)

        # Loop through each of the plants and call the function which prepares the dataset for bonsai..
        for plant in plants:
            try:
                print("\n\n Working on slug >>>> " + str(plant.slug))

                # Get the current timezone and convert it in to plant timezone
                try:
                    # get the current time .. Returns system time along with system timezone usually in UTC.
                    enddate = today
                    # convert the time to  plant timeone
                    enddate = enddate.astimezone(pytz.timezone(plant.metadata.dataTimezone))
                    print("bonsai_revision_prep() current_time is >>>>" + str(enddate))
                except Exception as exc:
                    print("bonsai_revision_prep() Exception occured in converting currenttime to property's TimeZone."
                          + str(exc))
                    enddate = timezone.now()

                # Check if ready to do day_ahead_statistical_forecast
                operations_end_time = OPERATIONS_END_HOUR
                print("bonsai_revision_prep() operations_end_time >>> " + str(operations_end_time))
                print("bonsai_revision_prep() current_time.hour >>> " + str(enddate.hour))

                # check if current hour is greater than operations_end_time
                if enddate.hour >= operations_end_time:
                    # compute the start time which is enddate - 60 days
                    startdate = enddate - timedelta(days=TRAINING_DAYS)
                    startdate = startdate.replace(hour=0, minute=0, second=0)

                    print("bonsai_revision_prep() Final STARTDATE IS >>> " + str(startdate))
                    print("bonsai_revision_prep() Final ENDDATE IS >>> " + str(enddate))

                    # ENERGY  PREP
                    energy_cassandra_df = read_cassandra_data(plant, startdate, enddate, energy=True)
                    print("bonsai_revision_prep() printing the energy dataframe received by the read_cassandra_data() function")
                    print(energy_cassandra_df.head())
                    bonsai_dataframe_prep(energy_cassandra_df, plant)

                    # POWER PREP
                    power_cassandra_df = read_cassandra_data(plant, startdate, enddate, energy=False)
                    print("bonsai_revision_prep() printing the  power dataframe received by the read_cassandra_data() function")
                    print(power_cassandra_df.head())
                    bonsai_dataframe_prep(power_cassandra_df, plant, energy=False)


            except Exception as e:
                print("bonsai_revision_prep() Exception occured while working for plant >>> "+ str(plant.slug) + " exception >>> " + str(e))

    except Exception as e:
        print("bonsai_revision_prep() raised a generic Exception please correct the error " + str(e))





###############################################################################################################
# Function 6
# This function basically Creates new entries into cassandra..
def save_revision_prediction(plant, bonsai_df, UNIT):
    try:
        if UNIT == 'energy':
            STREAM_NAME = 'plant_energy'
        elif UNIT == 'power':
            STREAM_NAME = 'plant_power'
        else:
            sys.exit(1)

        dt_current_time_UTC = timezone.now()
        # convert timestamp backto UTC
        # bonsai_df.reset_index(inplace=True)
        bonsai_df['bonsai_ts'] = bonsai_df['bonsai_ts'].dt.tz_localize(plant.metadata.dataTimezone).dt.tz_convert('UTC')
        batch_query = BatchQuery()

        for index, row in bonsai_df.iterrows():

            if UNIT == 'power':
                value = row['bonsai_prediction']

            elif UNIT == 'energy':
                # convert the energy value to power.
                value = row['bonsai_prediction'] * 4
            else:
                sys.exit(1)

            # calculate the lower and the upper bounds.
            lower_bound = value - BOUNDS_ON_CAPACITY * plant.capacity
            upper_bound = value + BOUNDS_ON_CAPACITY * plant.capacity

            print("save_revision_prediction() Inserting the record  into cassandra" + str(row['bonsai_ts']) + ">>>" + str(value))
            print(" stream_name >>> plant_power   model_name >>> " + OUTPUT_MODEL_NAME)

            # push to cassandra..
            PredictionData.batch(batch_query).create(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                count_time_period=900,
                identifier=plant.slug,
                stream_name='plant_power',
                model_name=OUTPUT_MODEL_NAME,
                ts=row['bonsai_ts'],
                value=value,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                update_at=dt_current_time_UTC)

            NewPredictionData.batch(batch_query).create(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                count_time_period=900,
                identifier_type='plant',
                plant_slug=plant.slug,
                identifier=plant.slug,
                stream_name='plant_power',
                model_name=OUTPUT_MODEL_NAME,
                ts=row['bonsai_ts'],
                value=value,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                update_at=dt_current_time_UTC)

        # execute the batch query.
        batch_query.execute()
        print("save_revision_prediction() Revisions  added successfully to cassandra..")
        # return zero if there are no exceptions
        return 0
    except Exception as ex:
        print("save_day_ahead_prediction() Exception in saving day ahead prediction: " + str(ex))
        return 1



##########################################################################################################
# Function 7
# Round to the nearest minutes
def round_time(dt=None, date_delta=timedelta(minutes=1)):
    round_to = date_delta.total_seconds()
    if dt is None:
        dt = datetime.now()
    # print("round_time() received time is >>> "+str(dt))
    seconds = (dt - dt.replace(hour=0, minute=0, second=0)).total_seconds()
    # print(seconds)
    rounding = (seconds // round_to) * round_to
    # print(rounding)
    return dt + timedelta(0, rounding - seconds, -dt.microsecond)




############################################################################################################
# function 8
# Realtime dataframe prep function
def realtime_df_prep(cassandra_df, currenttime, revision_start_time, revision_end_time, UNIT):
    try:
        # drop the date column
        cassandra_df.drop(['date'], axis=1, inplace=True)
        # sort in ascending order
        cassandra_df.sort_values(by='timestamp', ascending=True, inplace=True)
        # remove the date part from the dataframe.
        cassandra_df['timestamp'] = cassandra_df['timestamp'].dt.time
        # set the index as the time.
        bonsai_df = cassandra_df.set_index('timestamp')

        # filter 9 values before the current timestamp and convert it to a list
        actual_data_list = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'actual_' + UNIT].tail(LOOK_BACK_SLOTS).values)[::-1]
        actual_irradiation_list = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'actual_irradiation'].tail(LOOK_BACK_SLOTS).values)[::-1]
        # predicted_power_list        = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'predicted_energy'].tail(LOOK_BACK_SLOTS).values)[::-1]
        # predicted_irradiation_list  = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'predicted_irradiation'].tail(LOOK_BACK_SLOTS).values)[::-1]
        # append the active_energy values..
        bonsai_df[[UNIT + '-1.' + str(i) for i in range(1, len(actual_data_list) + 1)]] = pd.DataFrame([actual_data_list], index=bonsai_df.index)
        bonsai_df[['actual_irradiation-2.' + str(i) for i in range(1, len(actual_irradiation_list) + 1)]] = pd.DataFrame([actual_irradiation_list], index=bonsai_df.index)
        # bonsai_df[['day_ahead_irradiation-3.' + str(i) for i in range(1, len(predicted_energy_list) + 1)]] = pd.DataFrame([predicted_energy_list],index=bonsai_df.index)
        # bonsai_df[['predicted_irradiation-4.' + str(i) for i in range(1, len(predicted_irradiation_list) + 1)]] = pd.DataFrame([active_power_list],index=bonsai_df.index)

        # now that we are done with energy perform the required shift for predicted energy and irradiation.
        # Create the dataframes for each of the slots..
        for i in list(range(1, LOOK_BACK_SLOTS + 1)):
            bonsai_df['day_ahead_' + UNIT + '-3.' + str(i)] = bonsai_df['predicted_' + UNIT].shift(i)
            bonsai_df['predicted_irradiation-4.' + str(i)] = bonsai_df['predicted_irradiation'].shift(i)

        # since we can update from 4 th slot filter those rows greater than 30 mins
        bonsai_df = bonsai_df[(bonsai_df.index >= revision_start_time.time()) &
                              (bonsai_df.index <= revision_end_time.time())]
        # drop the actual_power as its not needed
        bonsai_df.drop(['actual_' + UNIT, 'actual_irradiation'], axis=1, inplace=True)
        # drop the na rows
        bonsai_df = bonsai_df.dropna()
        # reindex based on column order
        bonsai_df = bonsai_df.reindex_axis(sorted(bonsai_df.columns, key=lambda x: float(getcolnumber(x))), axis=1)
        print("\n\n\n#######################################################################################")
        print("realtime_df_prep() final dataframe prepared for Bonsai is >>>")
        # for each of the rows call the predictor model and send it to cassandra.
        print(bonsai_df.head(100))
        print("prnting the columns>>>")
        print(bonsai_df.columns)
        print("###############################################################################################")
        return bonsai_df
    except Exception as e:
        print("realtime_df_prep() raised an exception please check the function " + str(e))
        return pd.DataFrame()





###########################################################################################################
# Function 9
# this function copies the gbm stream to the output stream.
def create_final_merged_stream(plant,UNIT,current_time):

    if UNIT == "energy":
        STREAM_NAME = "plant_energy"
        MODEL_NAME = ENERGY_MODEL_NAME
    elif UNIT == "power":
        STREAM_NAME = "plant_power"
        MODEL_NAME = POWER_MODEL_NAME
    else:
        print("create_final_merged_stream() got a wrong UNIT NAME >>> "+str(UNIT))
        sys.exit(1)


    # get the dayahead predicted energy/ power
    predicted_plant_data = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                            count_time_period=900,
                                                            identifier_type='plant',
                                                            plant_slug=str(plant.slug),
                                                            identifier=str(plant.slug),
                                                            stream_name=STREAM_NAME,
                                                            model_name=MODEL_NAME,
                                                            ts__gte=current_time.replace(hour=0, minute=0, second=0),
                                                            ts__lte=current_time.replace(hour=23, minute=59, second=59))\
        .values_list('ts', 'value')

    # convert in to a dataframe.
    if len(predicted_plant_data) > 0:
        copy_df = pd.DataFrame(predicted_plant_data[:],columns=['bonsai_ts','bonsai_prediction'])
        copy_df['bonsai_ts'] = copy_df['bonsai_ts'].dt.tz_localize('UTC').dt.tz_convert(plant.metadata.dataTimezone)
        copy_df['bonsai_ts'] = copy_df['bonsai_ts'].apply(lambda x: datetime.replace(x, tzinfo=None))
        print("create_final_merged_stream() Printing the head of the copy dataframe ..")
        print(copy_df.head())

        # copy the predicted data to the output stream.
        save_revision_prediction(plant,copy_df,UNIT)




###########################################################################################################
# Function 10
# Bonsai function for revisions in real time.
def bonsai_realtime_m(currenttime=timezone.now(), energy=True, historical=False):

    # route the proper output folder..
    #if energy:
    #    OUTPUT_FOLDER = ENERGY_OUTPUT_FOLDER
    #    UNIT = 'energy'
    #else:
    #    OUTPUT_FOLDER = POWER_OUTPUT_FOLDER
    #    UNIT = 'power'

    #################################################################################################
    # Plants for which revision needs to be run...
    try:
        # plants = SolarPlant.objects.all()
        plants = SolarPlant.objects.filter(slug__in=PLANTS)
    except ObjectDoesNotExist:
        print("bonsai_realtime() No plants found .. ")


    #################################################################################################

    # Perform this for each of the plants
    for plant in plants:

        print("\n\n\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        print("bonsai_realtime() Working on plant slug >>> " + str(plant.slug))
        # added newly for supporting both energy/power.
        # for bbagewadi use the energy stream and for others use power
        if plant.slug == 'bbagewadi':
            # configure the output folder / unit / energy
            OUTPUT_FOLDER = POWER_OUTPUT_FOLDER
            UNIT = 'power'
        else:
            OUTPUT_FOLDER = ENERGY_OUTPUT_FOLDER
            UNIT = "energy"
        # assign proper value for the energy boolean
        energy = True if UNIT=="energy" else False
        print("bonsai_realtime() Plant >>>  " + str(plant.slug) + " UNIT >>> " + str(UNIT) + " OUTPUT_FOLDER >>> " + str(OUTPUT_FOLDER))


        #################################################################################################
        # Time manipulation..
        currenttime = currenttime.replace(second=0)
        # round to the nearest 15th minute
        currenttime = round_time(currenttime, date_delta=timedelta(minutes=15))
        # convert it to the plant timezone..
        currenttime = currenttime.astimezone(pytz.timezone(plant.metadata.dataTimezone))
        if historical is True:
            pickle_file_path = OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/cassandra_dict_historical.pickle"
        else:
            pickle_file_path = OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/cassandra_dict.pickle"
        #################################################################################################
        # CASSANDRA Time manipulations..
        # calculate startdate and end date for the cassandra query based on current time..
        cassandra_startdate = currenttime - timedelta(minutes=(LOOK_BACK_SLOTS + 1) * 15)
        cassandra_enddate = currenttime + timedelta(minutes=(LOOK_BACK_SLOTS + 3) * 15)
        print("\n####################################################################################")
        print("bonsai_realtime() Current time calculated is >>>> " + str(currenttime) + " >>> " + str(plant.slug))
        print("bonsai_realtime() Pickle file path for the plant is >>> " + str(pickle_file_path) + " >>> " + str(plant.slug))
        print("bonsai_realtime() Calculated Cassandra query start end is >>> " + str(cassandra_startdate) + " >>> " + str(plant.slug))
        print("bonsai_realtime() Calculated Cassandra query end date is >>> " + str(cassandra_enddate) + " >>> " + str(plant.slug))
        print("####################################################################################")



        ###################################################################################################
        # if current time is greater than 7 check if the pickle file is there if so delete
        if currenttime.time() > time(19, 0) or currenttime.time() < DAY_START_TIME:

            # if the current time is between
            if currenttime.time() > time(1,0) and currenttime.time() < time(2,0):
                print("bonsai_realtime() Its time to copy the Dayahead streams to the Final Stream >>> "+str(OUTPUT_MODEL_NAME))
                # copy the streams to the final merged stream.
                create_final_merged_stream(plant, UNIT, currenttime)

            # delete the pickle file if available
            try:
                os.remove(pickle_file_path)
            except OSError:
                pass
            print("bonsai_revision_prep() revisions cannot happen since its outside production hours >>> " + str(plant.slug))
            continue


        # Check if the pickle file exists..
        if os.path.exists(pickle_file_path):
            # if the pickle file exists for the plant then read the next_revision timestamp from the file
            with open(pickle_file_path, 'rb') as handle:
                last_update_dict = pickle.load(handle)
            print("#################################################################################################")
            print("bonsai_revision_prep() Dictionary being read from the pickle file is >>> " + str(last_update_dict)+ " >>> " + str(plant.slug))
            # check if the next_revision_timestamp key is present in the file
            if 'next_revision_timestamp' in last_update_dict:
                REVISION_TIMESTAMP = last_update_dict['next_revision_timestamp']
            else:
                REVISION_TIMESTAMP = currenttime
        else:
            REVISION_TIMESTAMP = currenttime
        print("bonsai_revision_prep() REVISION TIMESTAMP IS  >>> " + str(REVISION_TIMESTAMP))
        print("######################################################################################")


        # Check if the currenttime is greater than or equal to REVISION_TIMESTAMP...
        if currenttime >= REVISION_TIMESTAMP:

            #####################################################################################################
            # Read the data from cassandra and convert in to bonsai format
            if energy:
                cassandra_df = read_cassandra_data(plant, cassandra_startdate, cassandra_enddate,training=False, energy=True, real_time=True)
            else:
                cassandra_df = read_cassandra_data(plant, cassandra_startdate, cassandra_enddate,training=False, energy=False, real_time=True)

            if cassandra_df is None or cassandra_df.empty:
                print("bonsai_revision_prep() No data returned from cassandra hence skipping for plant >>> " + str(plant.slug))
                continue

            print("bonsai_realtime() Dataset received from cassandra")
            print(cassandra_df.head(100))
            print("\n######################################################################################")
            # Get the revision timeslots for the plant
            revision_start_slotnumber = PLANT_SLOT_DICT[plant.slug]['REVISION_START_SLOTNUMBER']
            revision_end_slotnumber = PLANT_SLOT_DICT[plant.slug]['REVISION_END_SLOTNUMBER']
            revision_diff = (revision_end_slotnumber - revision_start_slotnumber)
            # based on the revision slot number calculate the start date and end date.
            revision_start_time = (currenttime + timedelta(minutes=(revision_start_slotnumber - 1) * 15))
            revision_end_time = revision_start_time + timedelta(minutes=revision_diff * 15)
            print("bonsai_realtime() REVISION START SLOTNUMBER >>> " + str(revision_start_slotnumber) + " >>> " + str(plant.slug))
            print("bonsai_realtime() REVISION END SLOTNUMBER >>> " + str(revision_end_slotnumber) + " >>> " + str(plant.slug))
            print("bonsai_realtime() Revision starttime >>>> " + str(revision_start_time) + " >>> " + str(plant.slug))
            print("bonsai_realtime() Revision endtime >>>> " + str(revision_end_time) + " >>> " + str(plant.slug))

            # add a condition here to check if the previous slot value is empty
            last_four_unit_values = cassandra_df[cassandra_df['timestamp'] <= currenttime]['actual_'+UNIT].tolist()[-5:-1]
            print("bonsai_realtime() Last Four slot Values >>>> "+str(last_four_unit_values))
            # if the last four values is zero then replace the next one and a half hour with zero.
            if all(value==0.0 or np.isnan(value) for value in last_four_unit_values):
                print("bonsai_realtime() Since the last four slots have actual values as zero pushing the prediction as zero")
                revision_df = cassandra_df[((cassandra_df['timestamp']>= revision_start_time) & (cassandra_df['timestamp'] <= revision_end_time))]
                # remove the timezone information
                revision_df['timestamp'] = revision_df['timestamp'].dt.tz_localize(None)
                # put the prediction as zero.
                revision_df['bonsai_prediction'] = 0.0
                revision_df.rename(columns={'timestamp':'bonsai_ts'},inplace=True)
                # Push the prediction as zero for the next one and a half hour and proceed to the next plant.
                return_code = save_revision_prediction(plant, revision_df, UNIT)
                if return_code == 0:
                    print("bonsai_realtime() Final timeslot for which revision was done was " + str(revision_end_time) + " >>> " + str(plant.slug))
                    next_revision_time = revision_end_time + timedelta(minutes=15) - timedelta(minutes=(revision_start_slotnumber - 1) * 15)
                    print("bonsai_realtime() Next timeslot for which revision can be done is >>>" + str(next_revision_time) + " >>> " + str(plant.slug))
                    last_update_dict = {}
                    last_update_dict['next_revision_timestamp'] = next_revision_time
                    # pickle the timestamp in the dictionary and save it.
                    with open(pickle_file_path, 'wb') as handle:
                        pickle.dump(last_update_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
                continue
            elif last_four_unit_values[-1] == 0.0 or np.isnan(last_four_unit_values[-1]):
                # skip as the previous slot value is zero
                continue


            # adding a condition here to check any of the actual_irradiation is zero or NaN
            # if so copy the data from predicted irradiation
            cassandra_df.loc[((cassandra_df['timestamp'] < currenttime) &
                              ((cassandra_df['actual_irradiation'] == 0.0) | (
                              cassandra_df['actual_irradiation'].isnull()))), 'actual_irradiation'] \
                = cassandra_df['predicted_irradiation']

            # # adding a condition here to check if the actual_energy is zero or Nan if so copy from predicted_energy.
            # cassandra_df.loc[((cassandra_df['timestamp'] < currenttime) &
            #                   ((cassandra_df['actual_' + UNIT].isnull()))), 'actual_' + UNIT] \
            #     = cassandra_df['predicted_' + UNIT]

            print("bonsai_realtime() Dataset received from cassandra")
            print(cassandra_df.head(100))

            # convert the cassandra data in to a format for bonsai
            bonsai_df = realtime_df_prep(cassandra_df, currenttime, revision_start_time, revision_end_time, UNIT)

            if not bonsai_df.empty:
                ########################################################################################################
                # for each of the revision slot call the predictor get predictions and push to cassandra
                output_predictions = []
                output_ts = []
                i = revision_start_slotnumber
                while revision_start_time <= revision_end_time:
                    try:
                        timeobject = revision_start_time.time()
                        print("\n\n\n#####################################################################")
                        print("Working on Prediction for the timeslot " + str(timeobject) + " >>> " + str(plant.slug))
                        slot_array = bonsai_df.loc[[timeobject]]
                        print(slot_array)
                        bonsai_slot_dataset = OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot" + str(i) + "/"
                        print(bonsai_slot_dataset)
                        bonsai_predictor_obj = bonsaiPredictorOptim(bonsai_slot_dataset, log_level="warn")
                        slot_predictions = bonsai_predictor_obj.predict(slot_array)
                        print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>" + " >>> " + str(plant.slug))
                        print(slot_predictions)
                        # append to the output list
                        output_predictions.append(slot_predictions.item(0))
                        revision_start_time = revision_start_time + timedelta(minutes=15)
                        i += 1
                        print("##################################################################################")
                    except Exception as e:
                        revision_start_time = revision_start_time + timedelta(minutes=15)
                        print("bonsai_realtime() Exception occured while working on revision slot " + str(i)+ ">>>>" + str(e) + " >>> " + str(plant.slug))
            else:
                print("bonsai_realtime() realtime_df_prep() returned an empty dataframe not doing revisions.>>> " + str(plant.slug))
                continue

            ####################################################################################################
            # We need to find the error or deviation in the dayahead and forecast.
            # find the difference between actual and forecast
            print(output_predictions)
            bonsai_df['bonsai_prediction'] = output_predictions
            bonsai_df['bonsai_ts'] = bonsai_df.index.to_series().apply(lambda x: datetime(revision_start_time.year, revision_start_time.month, revision_start_time.day,x.hour,x.minute))
            percent_diff_df = bonsai_df[['bonsai_ts','predicted_' + UNIT, 'bonsai_prediction']].dropna()

            if not percent_diff_df.empty:
                percent_diff_df['diff'] = percent_diff_df['predicted_' + UNIT] - percent_diff_df['bonsai_prediction']
                #  proceed based on the error method choosen...
                if FORECAST_ERROR_METHOD == 'MEAN_MEDIAN':
                    # find the error percentage based on the unit..
                    if energy:
                        # find percentage difference
                        percent_diff_df['diff_percentage'] = abs((percent_diff_df['predicted_'+ UNIT] - percent_diff_df['bonsai_prediction']) / (plant.capacity / 4) * 100)
                    else:
                        percent_diff_df['diff_percentage'] = abs((percent_diff_df['predicted_'+ UNIT] - percent_diff_df['bonsai_prediction']) / plant.capacity) * 100
                    print("bonsai_realtime() Percent error df")
                    print(percent_diff_df.head(100))
                    # get the median of the percentage difference
                    mean_percentage = abs(round(percent_diff_df['diff_percentage'].mean()))
                    median_percentage = abs(round(percent_diff_df['diff_percentage'].median()))
                    print("bonsai_realtime() Plant capacity is >>> " + str(plant.capacity) + " >>> " + str(plant.slug))
                    print("bonsai_realtime() Mean of percentage difference is >>>> " + str(mean_percentage) + " >>> " + str(plant.slug))
                    print("bonsai_realtime() Median of percentage difference is >>>> " + str(median_percentage) + " >>> " + str(plant.slug))
                    percentage_error = max(mean_percentage, median_percentage)
                    print("bonsai_realtime() Max of Mean/ median is >>> " + str(percentage_error) + " >>> " + str(plant.slug))
                    '''
                                    predicted_energy  bonsai_prediction         diff  diff_percentage
                        timestamp
                        12:00:00             3990.0        3917.242072    72.757928         1.499391
                        12:15:00             2840.0        1057.451712  1782.548288        36.734638
                        12:30:00             2080.0       -1175.549571  3255.549571        67.090151
                        12:45:00             5490.0          62.037495  5427.962505       111.859093
                        13:00:00             3630.0        1555.053671  2074.946329        42.760357
                        13:15:00             2080.0        2949.375378  -869.375378        17.916030
                    '''
                    # sometimes Bonsai predicts in negative adding a condition to remove the negatives
                    percent_diff_df = percent_diff_df[percent_diff_df['bonsai_prediction'] > 0]
                    # remove too much variations in the predictions
                    percent_diff_df = percent_diff_df[percent_diff_df['diff_percentage'] < PERCENT_ERROR_UPPER_BOUND]



                # elif FORECAST_ERROR_METHOD == 'CORRELATION':
                #     print("bonsai_realtime() Percent error df")
                #     print(percent_diff_df.head(100))
                #     correlation = percent_diff_df['predicted_power'].astype('float64').corr(percent_diff_df['bonsai_prediction'].astype('float64'))
                #     percentage_error = 1-correlation
                #     print("bonsai_realtime() Correlation calculated is >>>> " + str(correlation) + " >>> " + str(plant.slug))
                #     print("bonsai_realtime() Error percentage >>>> " + str(percentage_error) + " >>> " + str(plant.slug))

                # update only if there are atleast half of revision diff points else dont proceed.
                print("bonsai_realtime() No of rows in the final dataframe  >>> " + str(percent_diff_df.shape[0]) + " >>> " + str(plant.slug))

                # adding the rolling mean smoothning to change the variations in the predictions.
                #percent_diff_df['bonsai_prediction'] = pd.rolling_mean(percent_diff_df['bonsai_prediction'], window=3, min_periods=1)

                if percentage_error > MAX_FORECAST_ERROR and percentage_error < PERCENT_ERROR_UPPER_BOUND and percent_diff_df.shape[0] > (revision_diff+1)/2:
                    print("bonsai_realtime() Error percentage is greater than allowed percentage  >>> " + str(percentage_error) + " >>> " + str(plant.slug))
                    print("bonsai_realtime() Error percentage is greater than allowed percentage  >>> " + str(MAX_FORECAST_ERROR) + " >>> " + str(plant.slug))

                    return_code = save_revision_prediction(plant, percent_diff_df, UNIT)

                    if return_code == 0:
                        print("bonsai_realtime() Final timeslot for which revision was done was " + str(revision_end_time) + " >>> " + str(plant.slug))
                        next_revision_time = revision_end_time + timedelta(minutes=15) - timedelta(minutes=(revision_start_slotnumber - 1) * 15)
                        print("bonsai_realtime() Next timeslot for which revision can be done is >>>" + str(next_revision_time) + " >>> " + str(plant.slug))
                        last_update_dict = {}
                        last_update_dict['next_revision_timestamp'] = next_revision_time
                        # pickle the timestamp in the dictionary and save it.
                        with open(pickle_file_path, 'wb') as handle:
                            pickle.dump(last_update_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

        else:
            print("\n\n\n#############################################################################################")
            print("bonsai_realtime() we are not allowed to revise for the current time " + str(currenttime) + " >>> " + str(plant.slug))
            print("Exiting the calculation for the plant." + " >>> " + str(plant.slug))
            print("############################################################################################")
            # End of revision loop...




###################################################################################################
# wrapper functions

# Wrapper function for predicting historical data.
def bonsai_historical_prediction():
    # Localize to India time..
    local_tz = pytz.timezone('Asia/Kolkata')
    # Parse the end date
    end_date = datetime.strptime(END_DATE, '%Y-%m-%d %H:%M:%S')
    # localize to Asia kolkata
    end_date = local_tz.localize(end_date)
    # Parse the START_TIME.
    start_date = datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')
    # Localize to IST time.
    start_date = local_tz.localize(start_date)
    while start_date < end_date:
        print("bonsai_realtime_wrapper()  Running for Date >>>> " + str(start_date))
        # call the prediction function
        bonsai_realtime_m(currenttime=start_date, historical=True)
        # Increment today date
        start_date = start_date + timedelta(minutes=15)



#bonsai_historical_prediction()
################################################################################################################
# End of program.
