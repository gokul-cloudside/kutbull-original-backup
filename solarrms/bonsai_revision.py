############################ ###############################################################
# Imports
import pandas as pd
import numpy as np
import django
import sys
import os
#sys.path.append("/var/www/kutbill")
sys.path.append("/var/www/EdgeML_TF/tf")
#os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from solarrms.models import WeatherData, NewPredictionData, SolarPlant, PredictionData
from dataglen.models import  ValidDataStorageByStream
from datetime import datetime, timedelta, time
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings
import pytz
import shutil
from edgeml.predictor.bonsaiPredictorOptim import bonsaiPredictorOptim
from solarrms.solarutils import get_minutes_aggregated_power
import pickle
from cassandra.cqlengine.query import BatchQuery

##############################################################################################
# Variables to be used in the program edit here if needed
POWER_MODEL_NAME = 'GBM_DAY_AHEAD_SOLCAST'
PROD_START_HOUR = 6
PROD_END_HOUR = 18
TRAINING_DAYS = 60
OPERATIONS_END_HOUR = 20
POINTS_PER_DAY = 48
PREDICTION_STARTTIME = "2018-06-18 22:00:00"
PREDICTION_ENDTIME = "2018-07-1 22:00:00"
BOUNDS_ON_CAPACITY = 0.15
PREDICTION_TIMEPERIOD_SPECIFIED = 900


EDGEML_DIR = "/var/www/EdgeML_TF"
#OUTPUT_FOLDER = "/usr/local/lib/prediction/BONSAI/"
OUTPUT_FOLDER = "/usr/local/lib/BONSAI/"

# Number of slots..
LOOK_BACK_SLOTS  = 8
# SLot starts from 1,2,3,4,5,6,7,8,9
NO_OF_SLOTS = 9
# SLOT NUMBER 1,2,3,4,5,6,7,8,9
PLANT_SLOT_DICT = {
    'bbagewadi':{'REVISION_START_SLOTNUMBER':4,'REVISION_END_SLOTNUMBER':9},
    'rayanpur':{'REVISION_START_SLOTNUMBER':4,'REVISION_END_SLOTNUMBER':9},
    'periyapattana':{'REVISION_START_SLOTNUMBER':4,'REVISION_END_SLOTNUMBER':9},
    'kurnool':{'REVISION_START_SLOTNUMBER':4,'REVISION_END_SLOTNUMBER':9},
    'krpet':{'REVISION_START_SLOTNUMBER':4,'REVISION_END_SLOTNUMBER':9},
    'dhamdha':{'REVISION_START_SLOTNUMBER':4,'REVISION_END_SLOTNUMBER':9}
}
# Starttime for realtime
DAY_START_TIME = time(8,0)
#Forecast vs Actual method  change here if needed change it to MEAN_MEDIAN if needs to be changed
FORECAST_ERROR_METHOD = 'MEAN_MEDIAN'
if FORECAST_ERROR_METHOD=='CORRELATION':
    # if the correlation coefficient is less than 1-MAX_FORECAST_ERROR
    MAX_FORECAST_ERROR = 0.20
elif FORECAST_ERROR_METHOD=='MEAN_MEDIAN':
    # this is when MEAN_MEDIAN is invoked.
    MAX_FORECAST_ERROR = 8

PLANTS = ['bbagewadi', 'rayanpur', 'periyapattana', 'kurnool', 'krpet', 'dhamdha']


##############################################################################################
# Functions

# Function 1
# Read the required data from cassandra for the given plant.
def read_cassandra_data(plant, starttime, endtime, training=True, real_time = False):
    """
        :param plant:
        :param start_time_planttimezone:
        :param end_time_planttimezone:
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
        print("\n\n read_cassandra_data() weather_df printing the head/tail")
        print(future_weather_df.head())
        print(future_weather_df.tail())


        # Download the current irradiation data from valid data storage.
        current_weather_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                       stream_name='IRRADIATION',
                                                       timestamp_in_data__gte=starttime,
                                                       timestamp_in_data__lt=endtime).limit(0).values_list('timestamp_in_data', 'stream_value')
        # create a dataframe from the above list
        current_weather_df = pd.DataFrame(current_weather_data[:], columns=['timestamp', 'actual_irradiation'])
        current_weather_df['timestamp'] = pd.to_datetime(current_weather_df['timestamp']).dt.tz_localize('UTC')
        current_weather_df['timestamp'] = current_weather_df['timestamp'].apply(lambda x: x.replace(second=0,microsecond=0))
        # Multiply actual_irradiation by 1000 as solcast is in the same range..
        current_weather_df['actual_irradiation'] = current_weather_df['actual_irradiation'].apply(lambda x: float(x)*1000)
        # remove the seconds part from the timestamp
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
    try:
        # get the dayahead predicted power.
        predicted_power = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                           count_time_period=900,
                                                           identifier_type='plant',
                                                           plant_slug=str(plant.slug),
                                                           identifier=str(plant.slug),
                                                           stream_name='plant_power',
                                                           model_name=POWER_MODEL_NAME,
                                                           ts__gte=starttime,
                                                           ts__lte=endtime).values_list('ts', 'value')
        # convert it in to a dataframe.
        predicted_power_df = pd.DataFrame(predicted_power[:], columns=['timestamp', 'predicted_power'])
        # convert timestamp to datetime
        predicted_power_df['timestamp'] = pd.to_datetime(predicted_power_df['timestamp']).dt.tz_localize('UTC')
        # convert the predicted power column to a float..
        predicted_power_df['predicted_power'] = predicted_power_df['predicted_power'].astype(float)
        print('read_cassandra_data() printing the head/tail of the predicted_power_df dataframe..')
        print(predicted_power_df.head())
        print(predicted_power_df.tail())


        if real_time:
            print("get_cassandra_data() getting the realtime data from cassandra...")
            # Call the function which basically returns the power values.
            # The function would basically return dictionary of the following format
            '''[{'power': 6.0960000000000001,'timestamp': Timestamp('2017-09-14 12:30:00+0000', tz='UTC')},
            {'power': 1.143,'timestamp': Timestamp('2017-09-14 12:45:00+0000', tz='UTC')}]'''

            dict_power = get_minutes_aggregated_power(starttime, endtime, plant, 'MINUTE',
                                                      PREDICTION_TIMEPERIOD_SPECIFIED / 60, split=False,
                                                      meter_energy=True)
            print("read_cassandra_data() get_minutes_aggregated_power API call completed..")
            #print(dict_power)

            # convert the power to a dict
            # convert it to a dataframe
            actual_power_df = pd.DataFrame.from_records(dict_power)
            actual_power_df = actual_power_df[['timestamp','power']]
            actual_power_df.columns = ['timestamp','actual_power']
            # no needd to localize to UTC as the api is already sending in UTC..
            actual_power_df['timestamp'] = pd.to_datetime(actual_power_df['timestamp'])
            actual_power_df['actual_power'] = actual_power_df['actual_power'].astype(float)

        else:
            # get the dayahead predicted power.
            actual_power = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                            count_time_period=900,
                                                            identifier_type='plant',
                                                            plant_slug=str(plant.slug),
                                                            identifier=str(plant.slug),
                                                            stream_name='plant_power',
                                                            model_name='ACTUAL',
                                                            ts__gte=starttime,
                                                            ts__lte=endtime).values_list('ts', 'value')

            # convert it to a dataframe
            actual_power_df = pd.DataFrame(actual_power[:], columns=['timestamp', 'actual_power'])
            actual_power_df['timestamp'] = pd.to_datetime(actual_power_df['timestamp']).dt.tz_localize('UTC')


        print("read_cassandra_data() printing the head/tail of Actual Power Dataframe ")
        print(actual_power_df.head())
        print(actual_power_df.tail())

        # combine both the dataframes changed from inner join to outer join to support realtime..
        power_df = predicted_power_df.merge(actual_power_df, how='outer', on='timestamp')
        print("read_cassandra_data() printing the head/tail of Merged.Power Dataframe ")
        print(power_df.head())
        print(power_df.tail())

    except Exception as e:
        print("read_cassandra_data() Exception occurred while trying to fetch the power data " + str(e))
        # return an empty dataframe
        return pd.DataFrame()



    ########################################################################################################

    # if both the power df and the weather df is not empty merge these two dataframes.
    if not power_df.empty and not merged_weather_df.empty:

        try:

            # merge operation
            final_df = power_df.merge(merged_weather_df, how='outer', on='timestamp')

            # convert it in to plant timezone
            final_df['timestamp'] = pd.to_datetime(final_df['timestamp']) \
                .dt.tz_convert(plant.metadata.dataTimezone)

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

            if training == True:
                # Filter out those rows which have < POINTS_PER_DAY
                final_df = final_df[final_df['counts'] >= POINTS_PER_DAY]

            # drop the date column
            final_df.drop('counts', axis=1, inplace=True)

            # IMPORTANT TO KEEP ACTUAL POWER AS THE SECOND COLUMN...
            final_df = final_df[['timestamp','actual_power','actual_irradiation','predicted_power','predicted_irradiation','minute','date']]

            # pritning the final merged dataframe
            print("read_cassandra_data() printing the final merged dataframe...")
            print(final_df.head(300))

            # now that all the opration is done return the dataframe
            return final_df
        except Exception as e:
            print("read_cassandra_data() Exception occurred while trying to merge power and weather " + str(e))
            return pd.DataFrame()
    
    else:
        pd.DataFrame()





####################################################################################################################

# Function 2
# Function which splits the dataframe in to trainng and test numpy arrays for bonsai..
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

#  inline function used for sorting columns
def getcolnumber(col):
    list1 = col.split("-")
    if len(list1) > 1:
        # print(float(list1[1]))
        l2 = list1[1].split(".")
        return float(l2[0]) * 1000 + float(l2[1])
    else:
        return 1


# Function 3
# Function which performs the required shifts for creating the final Input Datasets for Bonsai.
def bonsai_dataframe_prep(df, plant, training=True):
    # sort the dataframe by timestamp in ascending order
    s_df = df.sort_values(by='timestamp')

    # create the shifts which were done in microsoft..
    slots = list(range(1, NO_OF_SLOTS+1))
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
            print("bonsai_dataframe_prep() exception raised while creating folder for plant >> " + str(plant.slug)
                  + str(e))


    OUTPUT_DATAFRAME_LIST = []
    # perform the shift operation for each of the slots.
    for slot in slots:

        # deep copy the dataframe..
        slot_df = s_df.copy(deep=True)

        # Create the dataframes for each of the slots..
        for i in list(range(slot, slot+LOOK_BACK_SLOTS)):
            # perform the required shifts for power day_ahead and predicted_irradiation.
            slot_df['power-1.' + str(i)] = grouped['actual_power'].shift(i)
            slot_df['actual_irradiation-2.' + str(i)] = grouped['actual_irradiation'].shift(i)
            #slot_df['day_ahead_prediction-3.' + str(i)] = grouped['predicted_power'].shift(i)
            #slot_df['predicted_irradiation-4.' + str(i)] = grouped['predicted_irradiation'].shift(i)

        # create the dayahead and predicted irradiation columns..
        for i in list(range(1, LOOK_BACK_SLOTS+1)):
            slot_df['day_ahead_irradiation-3.' + str(i)] = grouped['predicted_power'].shift(i)
            slot_df['predicted_irradiation-4.' + str(i)] = grouped['predicted_irradiation'].shift(i)

        # reindex based on column order
        slot_df = slot_df.reindex_axis(sorted(slot_df.columns, key=lambda x: float(getcolnumber(x))), axis=1)

        # Drop the NAN rows
        slot_df = slot_df.dropna()

        # if training is done drop all the nan and also drop the timestamp and date column
        if training:
            # drop the timestamp and date columns
            slot_df.drop(['timestamp', 'date','actual_irradiation'], axis=1, inplace=True)

        print("\n\n\n###########################################################################")
        print("Printing the the head / tail of the slot "+str(slot))
        print(slot_df.head())
        print(slot_df.tail())
        print("\n\n Slot columns >>> " + str(list(slot_df.columns)))
        print("###########################################################################")

        # write it to a file only if training=true
        if training:
            # write pandasdf as a csv
            slot_df.to_csv(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/pandas/slot"+str(slot)+".csv", index=False)
            # Now call the function which creates trainng and test numpy arrays.
            train_test_split(slot_df, OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai", slot)
        else:
            OUTPUT_DATAFRAME_LIST.append(slot_df)


    # if its not training return the dataframe list...
    if training == False:
        return OUTPUT_DATAFRAME_LIST





###############################################################################################################
# Function 4
# function which loops through each of the plant
def bonsai_revision_prep(today=timezone.now()):
    try:
        print("bonsai_revision_prep() bonsai revision dataset preparation job started current time is  >>>> %s",
              datetime.now())

        # Get all the properties raise exception if no properties
        try:
            # plants = SolarPlant.objects.all()
            plants = SolarPlant.objects.filter(slug__in=PLANTS)
        except ObjectDoesNotExist:
            print("bonsai_revision_prep() No plants found .. ")

        # delete the output folder
        shutil.rmtree(OUTPUT_FOLDER, ignore_errors=True)

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
                    startdate = enddate - timedelta(days=60)
                    startdate = startdate.replace(hour=0, minute=0, second=0)

                    print("bonsai_revision_prep() Final STARTDATE IS >>> " + str(startdate))
                    print("bonsai_revision_prep() Final ENDDATE IS >>> " + str(enddate))

                    cassandra_df = read_cassandra_data(plant, startdate, enddate)
                    print(
                        "bonsai_revision_prep() printing the dataframe received by the read_cassandra_data() function")
                    print(cassandra_df.head())

                    bonsai_dataframe_prep(cassandra_df, plant)

            except Exception as e:
                print("bonsai_revision_prep() Exception occured while working for plant >>> "
                      + str(plant.slug) + " exception >>> " + str(e))

    except Exception as e:
        print("bonsai_revision_prep() raised a generic Exception please correct the error " + str(e))








###############################################################################################################
# Function 5
# function calls the bonsai tensorflow code for each of the plants and each of the slots.
def bonsai_trainer():
    # Calls the edgeml code for training.
    plant_directory = [OUTPUT_FOLDER.rstrip("/") + "/" + directory + "/bonsai/" for directory in
                       os.listdir(OUTPUT_FOLDER) if
                       os.path.isdir(OUTPUT_FOLDER + directory)]
    print(plant_directory)

    for plant in plant_directory:
        print("\n\n")
        print("---------------------------------------------------")
        print("Currently Working for plant >>> : ", plant)

        slots = [directory for directory in os.listdir(plant) if os.path.isdir(plant + directory)]
        print(slots)

        for slot in slots:
            print("-------------------------------------------------")
            print("Currently working for slot >>> : ", slot)
            print(plant + slot)

            # pass the right parameters for PREDICTION REVISION. Below parms were decided in microsoft
            # TODO add Gridsearch to this code in future.
            print(os.system(
                "python " + EDGEML_DIR.rstrip("/") + "/tf/examples/bonsai_example.py -dir "
                + plant + slot + " -e 500 -d 4 -p 10 -b 32 -s 0.1 -lr 0.05 -rW 0.00001 -rZ 0.000001"))





####################################################################################################################
# Function 6
# This function basically Creates new entries into cassandra..
def save_revision_prediction(plant,bonsai_df):
    try:

        dt_current_time_UTC = timezone.now()
        # convert timestamp backto UTC
        #bonsai_df.reset_index(inplace=True)
        bonsai_df['bonsai_ts'] = bonsai_df['bonsai_ts'].dt.tz_localize(plant.metadata.dataTimezone).dt.tz_convert('UTC')
        batch_query = BatchQuery()

        for index,row in bonsai_df.iterrows():
            print("save_revision_prediction() Inserting the record  into cassandra"+str(row['bonsai_ts'])+">>>"+str(row['bonsai_prediction']))
            # push to cassandra..
            PredictionData.batch(batch_query).create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                    count_time_period=900,
                                    identifier=plant.slug, stream_name='plant_power',
                                    model_name='STATISTICAL_LATEST_BONSAI_GOVT',
                                    ts=row['bonsai_ts'],
                                    value=row['bonsai_prediction'],
                                    lower_bound=row['bonsai_prediction'] - BOUNDS_ON_CAPACITY * plant.capacity,
                                    upper_bound=row['bonsai_prediction'] - BOUNDS_ON_CAPACITY * plant.capacity,
                                    update_at=dt_current_time_UTC)

            NewPredictionData.batch(batch_query).create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                           count_time_period=900,
                                           identifier_type='plant',
                                           plant_slug=plant.slug,
                                           identifier=plant.slug,
                                           stream_name='plant_power',
                                           model_name='STATISTICAL_LATEST_BONSAI_GOVT',
                                           ts=row['bonsai_ts'],
                                           value=row['bonsai_prediction'],
                                           lower_bound=row['bonsai_prediction'] - BOUNDS_ON_CAPACITY * plant.capacity,
                                           upper_bound=row['bonsai_prediction'] - BOUNDS_ON_CAPACITY * plant.capacity,
                                           update_at=dt_current_time_UTC)

        # execute the batch query.
        batch_query.execute()
        print("save_revision_prediction() Revisions  added successfully to cassandra..")
        # return zero if there are no exceptions
        return 0
    except Exception as ex:
        print("save_day_ahead_prediction() Exception in saving day ahead prediction: " + str(ex))
        return 1






#TODO THIS FUNCTION NEEDS UPDATE REMOVE UNNECESSARY MULTIPLE IF CONDITIONS
#TODO BELOW FUNCTION NOT USED
######################################################################################################################
# Function 7
# Funtion which predcts the revisions for Historical data.
def bonsai_prediction_revision_historical_day(plant, startdate, enddate):
    # get the data from cassandra
    cassandra_df = read_cassandra_data(plant, startdate, enddate, training=False)

    if cassandra_df is None or cassandra_df.empty:
        return

    # prep the dataframe for bonsai predictor
    slot_list = bonsai_dataframe_prep(cassandra_df, plant, training=False)

    for slot in slot_list:
        # reset the index of all the 8 dataframes..
        slot.reset_index(drop=True, inplace=True)

    print("\n\nbonsai_prediction_revision_historical_day() Bonsai predict dataframes..")
    print("-------------------------------------------------------------------")
    print(slot_list[0].head())
    print(slot_list[-1].head())

    # create the bonsai predictor objects.
    # Bonsai Class object
    slot1_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot1/",
                                            log_level="warn")
    slot2_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot2/",
                                            log_level="warn")
    slot3_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot3/",
                                            log_level="warn")
    slot4_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot4/",
                                            log_level="warn")
    slot5_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot5/",
                                            log_level="warn")
    slot6_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot6/",
                                            log_level="warn")
    slot7_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot7/",
                                            log_level="warn")
    slot8_bonsai_obj = bonsaiPredictorOptim(OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/slot8/",
                                            log_level="warn")

    # now that we have got slot1 to slot8 dataframes of a particular day
    # loop through each of the points and get the prediction.
    # Loop through the first dataset and get the predictions accordingly.
    print(slot_list[0].shape)
    for i in range(slot_list[0].shape[0]):
        # for i in range(1):

        print("\n\n#################################################################################")
        try:
            ###############################################################################
            # Work on slot1
            ###############################################################################
            print("\n\n Working on slot 1")
            f_slot1 = slot_list[0].iloc[[i]]
            timestamp = f_slot1.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            actual_power = f_slot1.loc[i].actual_power
            print(actual_power)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot1.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot1_array = f_slot1.values
            # print(slot1_array)
            slot1_predictions = slot1_bonsai_obj.predict(slot1_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>> ")
            print(slot1_predictions)

            # issue the post requests
            print("\n\n Pushing the prediction results to cassandra ..")
            save_revision_prediction(plant,timestamp,slot1_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("bonsai_prediction_revision_historical_day() Exception occured at Slot 1 " + str(e))

        try:
            ###############################################################################
            # Work on slot2
            ###############################################################################
            print("\n\n Working on slot 2")
            f_slot2 = slot_list[1].iloc[[i]]
            timestamp = f_slot2.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot2.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot2_array = f_slot2.values
            # print(slot2_array)
            # print(slot2_array.shape)
            slot2_predictions = slot2_bonsai_obj.predict(slot2_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>>")
            print(slot2_predictions)
            # issue the post requests
            save_revision_prediction(plant,timestamp, slot2_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 2 " + str(e))

        try:
            ###############################################################################
            # Work on slot3
            ###############################################################################
            print("\n\n Working on slot 3")
            f_slot3 = slot_list[2].iloc[[i]]
            timestamp = f_slot3.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot3.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot3_array = f_slot3.values
            # print(slot3_array)
            # print(slot3_array.shape)
            slot3_predictions = slot3_bonsai_obj.predict(slot3_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>>")
            print(slot3_predictions)
            # issue the post requests
            save_revision_prediction(plant,timestamp, slot3_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 3 " + str(e))

        try:
            ###############################################################################
            # Work on slot4
            ###############################################################################
            print("\n\n Working on slot 4")
            f_slot4 = slot_list[3].iloc[[i]]
            timestamp = f_slot4.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot4.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot4_array = f_slot4.values
            # print(slot4_array)
            # print(slot4_array.shape)
            slot4_predictions = slot4_bonsai_obj.predict(slot4_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>")
            print(slot4_predictions)
            # issue the post requests
            save_revision_prediction(plant,timestamp, slot4_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 4" + str(e))

        try:
            ###############################################################################
            # Work on slot5
            ###############################################################################
            print("\n\n Working on slot 5")
            f_slot5 = slot_list[4].iloc[[i]]
            # required for all the slots
            timestamp = f_slot5.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot5.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot5_array = f_slot5.values
            # print(slot5_array)
            # print(slot5_array.shape)
            slot5_predictions = slot5_bonsai_obj.predict(slot5_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>")
            print(slot5_predictions)
            # issue the post requests
            save_revision_prediction(plant,timestamp, slot5_predictions.item(0))


            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 5" + str(e))

        try:
            ###############################################################################
            # Work on slot6
            ###############################################################################
            print("\n Working on slot 6")
            f_slot6 = slot_list[5].iloc[[i]]
            timestamp = f_slot6.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot6.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot6_array = f_slot6.values
            # print(slot1_array)
            # print(slot1_array.shape)
            slot6_predictions = slot6_bonsai_obj.predict(slot6_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>")
            print(slot6_predictions)
            # issue the post requests
            save_revision_prediction(plant, timestamp, slot6_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 6" + str(e))

        try:
            ###############################################################################
            # Work on slot7
            ###############################################################################
            print("\nWorking on slot 7")
            f_slot7 = slot_list[6].iloc[[i]]
            # required for all the slots
            timestamp = f_slot7.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot7.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot7_array = f_slot7.values
            # print(slot7_array)
            # print(slot7_array.shape)
            slot7_predictions = slot7_bonsai_obj.predict(slot7_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>")
            print(slot7_predictions)
            # issue the post requests
            save_revision_prediction(plant, timestamp, slot7_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 7" + str(e))

        try:
            ###############################################################################
            # Work on slot8
            ###############################################################################
            print("\nWorking on slot 8")
            f_slot8 = slot_list[7].iloc[[i]]
            # required for all the slots
            timestamp = f_slot8.loc[i].timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(timestamp)
            # extract the numpy array to be passed to the bonsai predictor
            f_slot8.drop(['timestamp', 'actual_power', 'date'], axis=1, inplace=True)
            slot8_array = f_slot8.values
            # print(slot8_array)
            # print(slot8_array.shape)
            slot8_predictions = slot8_bonsai_obj.predict(slot8_array)
            print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>")
            print(slot8_predictions)
            # issue the post requests
            save_revision_prediction(plant, timestamp, slot8_predictions.item(0))

            ################################################################################
        except Exception as e:
            print("Exception occured at Slot 8" + str(e))




#####################################################################################################################
# function 8
# function which loops thorugh each of the plants.
def bonsai_prediction_revision_historical():
    print("bonsai_prediction_revision_historical() currentime  >>>> %s",
          datetime.now())

    # Get all the properties raise exception if no properties
    try:
        # plants = SolarPlant.objects.all()
        plants = SolarPlant.objects.filter(slug__in=PLANTS)
    except ObjectDoesNotExist:
        print("bonsai_revision_prep() No plants found .. ")

    # now loop through each of the plants.
    for plant in plants:

        print(" \n\n\n ################################################################################")
        print(" bonsai_prediction_revision_historical () Working on plant " + str(plant))

        # COnvert the starttime and endtime to objects
        O_PREDICTION_STARTTIME = datetime.strptime(PREDICTION_STARTTIME, '%Y-%m-%d %H:%M:%S')
        O_PREDICTION_ENDTIME = datetime.strptime(PREDICTION_ENDTIME, '%Y-%m-%d %H:%M:%S')

        # Loop through each of the days till the end time
        while O_PREDICTION_STARTTIME <= O_PREDICTION_ENDTIME:
            starttime = O_PREDICTION_STARTTIME.replace(hour=0, minute=0, second=0)
            # compute the endtime
            endtime = O_PREDICTION_STARTTIME.replace(hour=23, minute=59, second=59)
            local_tz = pytz.timezone('Asia/Kolkata')
            starttime = local_tz.localize(starttime)
            endtime = local_tz.localize(endtime)

            print("bonsai_prediction_revision_historical() Calculated starttime is >>> " + str(starttime))
            print("bonsai_prediction_revision_historical() Calculated endtime is >>> " + str(endtime))

            # now call the predctor function.
            bonsai_prediction_revision_historical_day(plant, starttime, endtime)

            O_PREDICTION_STARTTIME = O_PREDICTION_STARTTIME + timedelta(days=1)




##########################################################################################################
# Function 9
# ROund to the nearest minutes
def round_time(dt=None, date_delta=timedelta(minutes=1)):
    round_to = date_delta.total_seconds()
    if dt is None:
        dt = datetime.now()
    #print("round_time() received time is >>> "+str(dt))
    seconds = (dt - dt.replace(hour=0, minute=0, second=0)).total_seconds()
    #print(seconds)
    rounding = (seconds // round_to) * round_to
    #print(rounding)
    return dt + timedelta(0, rounding - seconds, -dt.microsecond)





############################################################################################################
# function 10
# Realtime dataframe prep function
def realtime_df_prep(cassandra_df,currenttime,revision_start_time,revision_end_time):
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
        active_power_list           = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'actual_power'].tail(LOOK_BACK_SLOTS).values)[::-1]
        actual_irradiation_list     = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'actual_irradiation'].tail(LOOK_BACK_SLOTS).values)[::-1]
        #predicted_power_list        = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'predicted_power'].tail(LOOK_BACK_SLOTS).values)[::-1]
        #predicted_irradiation_list  = list(bonsai_df.loc[:(currenttime - timedelta(minutes=15)).time(), 'predicted_irradiation'].tail(LOOK_BACK_SLOTS).values)[::-1]
        # append the active_power values..
        bonsai_df[['power-1.' + str(i) for i in range(1, len(active_power_list) + 1)]] = pd.DataFrame([active_power_list],index=bonsai_df.index)
        bonsai_df[['actual_irradiation-2.' + str(i) for i in range(1, len(actual_irradiation_list) + 1)]] = pd.DataFrame([actual_irradiation_list], index=bonsai_df.index)
        #bonsai_df[['day_ahead_irradiation-3.' + str(i) for i in range(1, len(predicted_power_list) + 1)]] = pd.DataFrame([predicted_power_list],index=bonsai_df.index)
        #bonsai_df[['predicted_irradiation-4.' + str(i) for i in range(1, len(predicted_irradiation_list) + 1)]] = pd.DataFrame([active_power_list],index=bonsai_df.index)

        # now that we are done with power perform the required shift for predicted power and irradiation.
        # Create the dataframes for each of the slots..
        for i in list(range(1, LOOK_BACK_SLOTS + 1)):
            bonsai_df['day_ahead_irradiation-3.' + str(i)] = bonsai_df['predicted_power'].shift(i)
            bonsai_df['predicted_irradiation-4.' + str(i)] = bonsai_df['predicted_irradiation'].shift(i)

        # since we can update from 4 th slot filter those rows greater than 30 mins
        bonsai_df = bonsai_df[(bonsai_df.index >= revision_start_time.time()) &
                              (bonsai_df.index <= revision_end_time.time())]
        # drop the actual_power as its not needed
        bonsai_df.drop(['actual_power','actual_irradiation'], axis=1, inplace=True)
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
        print("realtime_df_prep() raised an exception please check the function "+str(e))
        return pd.DataFrame()





###########################################################################################################
# Function 10
# Bonsai function for revisions in real time.
def bonsai_realtime(currenttime = timezone.now(),historical=False):

    #################################################################################################
    # Plants for which revision needs to be run...
    try:
        # plants = SolarPlant.objects.all()
        plants = SolarPlant.objects.filter(slug__in=PLANTS)
    except ObjectDoesNotExist:
        print("bonsai_revision_prep() No plants found .. ")

    #################################################################################################

    # Perform this for each of the plants
    for plant in plants:
        print("\n\n\n$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        print(" Working on plant slug >>> "+str(plant.slug))

        #################################################################################################
        # Time manipulation..
        currenttime = currenttime.replace(second=0)
        # round to the nearest 15th minute
        currenttime = round_time(currenttime,  date_delta=timedelta(minutes=15))
        # convert it to the plant timezone..
        currenttime = currenttime.astimezone(pytz.timezone(plant.metadata.dataTimezone))
        if historical is True:
            pickle_file_path = OUTPUT_FOLDER.rstrip("/") + "/" + plant.slug + "/bonsai/cassandra_dict_historical.pickle"
        else:
            pickle_file_path = OUTPUT_FOLDER.rstrip("/")+"/"+plant.slug+ "/bonsai/cassandra_dict.pickle"
        #################################################################################################
        # CASSANDRA Time manipulations..
        # calculate startdate and end date for the cassandra query based on current time..
        cassandra_startdate = currenttime - timedelta(minutes=(LOOK_BACK_SLOTS+1)*15)
        cassandra_enddate = currenttime + timedelta(minutes=(LOOK_BACK_SLOTS+3)*15)
        print("\n####################################################################################")
        print("bonsai_realtime() Current time calculated is >>>> "+str(currenttime)+" >>> "+str(plant.slug))
        print("bonsai_realtime() Pickle file path for the plant is >>> "+str(pickle_file_path)+" >>> "+str(plant.slug))
        print("bonsai_realtime() Calculated Cassandra query start end is >>> "+str(cassandra_startdate)+" >>> "+str(plant.slug))
        print("bonsai_realtime() Calculated Cassandra query end date is >>> "+str(cassandra_enddate)+" >>> "+str(plant.slug))
        print("####################################################################################")


        ###################################################################################################
        # if current time is greater than 7 check if the pickle file is there if so delete
        if currenttime.time() > time(19,0) or currenttime.time() < DAY_START_TIME:
            # delete the pickle file if available
            try:
                os.remove(pickle_file_path)
            except OSError:
                pass
            print("bonsai_revision_prep() revisions cannot happen since its outside production hours >>> "+str(plant.slug))
            continue

        # Check if the pickle file exists..
        if os.path.exists(pickle_file_path):
            # if the pickle file exists for the plant then read the next_revision timestamp from the file
            with open(pickle_file_path, 'rb') as handle:
                last_update_dict = pickle.load(handle)
            print("#################################################################################################")
            print("bonsai_revision_prep() Dictionary being read from the pickle file is >>> "+str(last_update_dict)
                  +" >>> "+str(plant.slug))
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
            cassandra_df = read_cassandra_data(plant, cassandra_startdate, cassandra_enddate,
                                               training=False,real_time=True)
            if cassandra_df is None or cassandra_df.empty:
                print("bonsai_revision_prep() No data returned from cassandra hence skipping for plant >>> "+str(plant.slug))
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
            print("bonsai_realtime() REVISION START SLOTNUMBER >>> "+str(revision_start_slotnumber)+" >>> "+str(plant.slug))
            print("bonsai_realtime() REVISION END SLOTNUMBER >>> "+str(revision_end_slotnumber)+" >>> "+str(plant.slug))
            print("bonsai_realtime() Revision starttime >>>> "+str(revision_start_time)+" >>> "+str(plant.slug))
            print("bonsai_realtime() Revision endtime >>>> " + str(revision_end_time)+" >>> "+str(plant.slug))
            # convert the cassandra data in to a format for bonsai
            bonsai_df = realtime_df_prep(cassandra_df,currenttime,revision_start_time,revision_end_time)

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
                        print("Working on Prediction for the timeslot "+str(timeobject)+" >>> "+str(plant.slug))
                        slot_array = bonsai_df.loc[[timeobject]]
                        print(slot_array)
                        bonsai_slot_dataset = OUTPUT_FOLDER.rstrip("/") + "/"+ plant.slug+ "/bonsai/slot"+str(i)+"/"
                        print(bonsai_slot_dataset)
                        bonsai_predictor_obj = bonsaiPredictorOptim(bonsai_slot_dataset,log_level="warn")
                        slot_predictions = bonsai_predictor_obj.predict(slot_array)
                        print("\n\n OUTPUT PREDICTIONS FROM BONSAI >>>>>"+" >>> "+str(plant.slug))
                        print(slot_predictions)
                        # append to the output list
                        output_predictions.append(slot_predictions.item(0))
                        revision_start_time = revision_start_time +timedelta(minutes=15)
                        i+=1
                        print("##################################################################################")
                    except Exception as e:
                        revision_start_time = revision_start_time + timedelta(minutes=15)
                        print("bonsai_realtime() Exception occured while working on revision slot "+str(i)
                              +">>>>"+str(e)+" >>> "+str(plant.slug))
            else:
                print("bonsai_realtime() realtime_df_prep() returned an empty dataframe not doing revisions.>>> "+str(plant.slug))
                continue


            ####################################################################################################
            # We need to find the error or deviation in the dayahead and forecast.
            # find the difference between actual and forecast
            print(output_predictions)
            bonsai_df['bonsai_prediction'] = output_predictions
            bonsai_df['bonsai_ts'] = bonsai_df.index.to_series()\
                .apply(lambda x: datetime(revision_start_time.year,revision_start_time.month,revision_start_time.day,x.hour,x.minute))
            percent_diff_df = bonsai_df[['predicted_power', 'bonsai_prediction']].dropna()
            if not percent_diff_df.empty:
                percent_diff_df['diff'] = percent_diff_df['predicted_power'] - percent_diff_df['bonsai_prediction']
                if FORECAST_ERROR_METHOD == 'MEAN_MEDIAN':
                    # find percentage difference
                    percent_diff_df['diff_percentage'] = abs(
                        (percent_diff_df['predicted_power'] - percent_diff_df['bonsai_prediction']) / plant.capacity) * 100
                    print("bonsai_realtime() Percent error df")
                    print(percent_diff_df.head(100))
                    # get the median of the percentage difference
                    mean_percentage = abs(round(percent_diff_df['diff_percentage'].mean()))
                    median_percentage = abs(round(percent_diff_df['diff_percentage'].median()))
                    print("bonsai_realtime() Plant capacity is >>> " + str(plant.capacity)+" >>> "+str(plant.slug))
                    print("bonsai_realtime() Mean of percentage difference is >>>> " + str(mean_percentage)+" >>> "+str(plant.slug))
                    print("bonsai_realtime() Median of percentage difference is >>>> " + str(median_percentage)+" >>> "+str(plant.slug))
                    percentage_error = max(mean_percentage, median_percentage)
                    print("bonsai_realtime() Max of Mean/ median is >>> " + str(percentage_error)+" >>> "+str(plant.slug))
                # elif FORECAST_ERROR_METHOD == 'CORRELATION':
                #     print("bonsai_realtime() Percent error df")
                #     print(percent_diff_df.head(100))
                #     correlation = percent_diff_df['predicted_power'].astype('float64').corr(percent_diff_df['bonsai_prediction'].astype('float64'))
                #     percentage_error = 1-correlation
                #     print("bonsai_realtime() Correlation calculated is >>>> " + str(correlation) + " >>> " + str(plant.slug))
                #     print("bonsai_realtime() Error percentage >>>> " + str(percentage_error) + " >>> " + str(plant.slug))


                if percentage_error > MAX_FORECAST_ERROR:
                    print("bonsai_realtime() Error percentage is greater than allowed percentage  >>> "+str(percentage_error)+" >>> "+str(plant.slug))
                    print("bonsai_realtime() Error percentage is greater than allowed percentage  >>> " + str(MAX_FORECAST_ERROR)+" >>> "+str(plant.slug))
                    return_code = save_revision_prediction(plant, bonsai_df)

                    if return_code==0:
                        print("bonsai_realtime() Final timeslot for which revision was done was "+str(revision_end_time)+" >>> "+str(plant.slug))
                        next_revision_time = revision_end_time+timedelta(minutes=15) - timedelta(minutes=(revision_start_slotnumber-1)*15)
                        print("bonsai_realtime() Next timeslot for which revision can be done is >>>"+str(next_revision_time)+" >>> "+str(plant.slug))
                        last_update_dict = {}
                        last_update_dict['next_revision_timestamp'] = next_revision_time
                        # pickle the timestamp in the dictionary and save it.
                        with open(pickle_file_path, 'wb') as handle:
                            pickle.dump(last_update_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

        else:
            print("\n\n\n#############################################################################################")
            print("bonsai_realtime() we are not allowed to revise for the current time "+str(currenttime)+" >>> "+str(plant.slug))
            print("Exiting the calculation for the plant."+" >>> "+str(plant.slug))
            print("############################################################################################")
    # End of revision loop...



###################################################################################################
# Wrapper functions for testing purposes.
def bonsai_revision_prep_wrapper():
    # testing..
    currenttime = timezone.now() + timedelta(hours=2)
    # prepare the trainning datasets
    bonsai_revision_prep(currenttime)


def bonsai_trainer_wrapper():
    # Call the  tensorflow training code ...
    bonsai_trainer()


def bonsai_realtime_wrapper():
    # for testing a particular timeslot uncomment these lines
    # Lets assume the currenttime is at 08:15 IST 2:45 UTC
    START_DATE = "2018-8-1 08:00:00"
    END_DATE = "2018-8-1 19:30:00"
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
    while (start_date < end_date):
        print("bonsai_realtime_wrapper()  Running for Date >>>> " + str(start_date))
        # call the prediction function
        bonsai_realtime(start_date,historical=True)
        # Increment today date
        start_date = start_date + timedelta(minutes=15)


###################################################################################################


# final function to call by default s
#bonsai_revision_prep_wrapper()
#bonsai_trainer_wrapper()
#bonsai_realtime_wrapper()