############################################################################################
# Imports
############################################################################################
# Dataglen imports
from solarrms.models import PredictionData, NewPredictionData, WeatherData, SolarPlant
from solarrms.solarutils import get_minutes_aggregated_power
from xgboost import XGBRegressor
# Django imports
from django.utils import timezone
from django.conf import settings
from cassandra.cqlengine.query import BatchQuery
from django.core.exceptions import ObjectDoesNotExist
# Python imports
from datetime import datetime, timedelta, time
import pytz
# analytics
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error,r2_score,mean_absolute_error

############################################################################################
# Variables change here if needed
############################################################################################
START_DATE = "2018-1-31 22:00:00"
END_DATE = "2018-2-28 22:00:00"
NO_OF_TRAINING_DAYS = 60
# Plant Production Starting hour and ending hour...
PROD_START_HOUR = 6
PROD_END_HOUR = 18
OPERATIONS_END_HOUR = 20
MIN_POINTS_PER_DAY = 30
BOUNDS_ON_CAPACITY = 0.15
DEFAULT_TIMEZONE = "Asia/Kolkata"
PREDICTION_TIMEPERIOD = settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES
LOWER_QUARTILE= 0.10
UPPER_QUARTILE=0.90
IGNORE_ANOMALY_SLOTS= [360,375,390,405,420,435,450,465,480,1080,1095,1110]
OUTPUT_STREAM_NAMES = ['GBM_DAY_AHEAD_SOLCAST','GBM_LATEST_SOLCAST',
                       'STATISTICAL_LATEST_BONSAI_GOVT']

# ############################################################################################################################


# Function 1
# This function reads the data from cassandra and creates a dataframe and passes it on the parent function
'''
:params 
property => property for which data needs to be obtained
current_time => currenttime in UTC.
'''


def get_plant_df(plant, current_time, irrad_type='current'):
    try:
        # Subtract the current time -7 days and that becomes the start_time.
        start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0, minute=0, second=0,
                                                                                  microsecond=0)

        # Call the function which basically returns the power values.
        # The function would basically return dictionary of the following format
        '''[{'power': 6.0960000000000001,'timestamp': Timestamp('2017-09-14 12:30:00+0000', tz='UTC')},
        {'power': 1.143,'timestamp': Timestamp('2017-09-14 12:45:00+0000', tz='UTC')}]'''
        dict_power = get_minutes_aggregated_power(start_time, current_time, plant, 'MINUTE', PREDICTION_TIMEPERIOD / 60,
                                                  split=False, meter_energy=True)

        # Check if the API has returned any values.
        if len(dict_power) > 0:
            power_df = pd.DataFrame(dict_power)
            power_df['timestamp'] = pd.to_datetime(power_df['timestamp']).dt.tz_convert(plant.metadata.dataTimezone)
            # Filter only those power values whch are greater than zero
            power_df = power_df[power_df['power'] > 0]
            # filter out those rows which are greater than 1.5*capacity
            power_df = power_df[power_df['power'] < (1.5 * plant.capacity)]
        else:
            print("get_plant_df() get_minutes_aggregated_power() returned an empty list plant >>> " + plant.slug)
            return "NO POWER DATA"

        print("get_plant_df() get_minutes_aggregated_power API call completed..")

        print("get_plant_df() Printing the head of the POWER Dataframe..")
        print(power_df.head())
        # comment after testing
        # for index,row in power_df.iterrows():
        #    print(row)

        # Get the GHI Data in another dataframe
        weather_data = WeatherData.objects.filter(api_source='solcast',
                                                  timestamp_type='hourly',
                                                  identifier=plant.slug,
                                                  prediction_type=irrad_type,
                                                  ts__gte=start_time, ts__lt=current_time) \
            .values_list('ts', 'ghi')

        if len(weather_data) > 0:
            try:
                weather_df = pd.DataFrame(weather_data[:], columns=['timestamp', 'ghi'])
                # convert the ghi column to a float value.
                weather_df['ghi'] = weather_df['ghi'].astype(float)
                # localize the timestamp column to UTC
                weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp']).dt.tz_localize("UTC").dt.tz_convert(
                    plant.metadata.dataTimezone)
            except Exception as e:
                print("get_plant_df() WeatherData returned an empty list plant >>> " + plant.slug + str(e))
                return "NO WEATHER DATA PRESENT"
        else:
            print("get_plant_df() WeatherData returned an empty list plant >>> " + plant.slug)
            return "NO WEATHER DATA PRESENT"

        print("get_plant_df() Printing the head of the WEATHER Data Dataframe..")
        print(weather_df.head())
        # comment after testing
        # for index,row in weather_df.iterrows():
        #    print(row)

        # Now Merge Both the Dataframe based on timestamp.
        merged_df = pd.merge(power_df, weather_df, how='left', on=['timestamp'])
        # Handle missing data
        merged_df['modified_ghi'] = merged_df['ghi'].fillna((merged_df['ghi'].shift() + merged_df['ghi'].shift(-1)) / 2)
        # handle NaN
        merged_df['modified_ghi'].fillna('0', inplace=True)
        merged_df['modified_ghi'] = merged_df['modified_ghi'].astype(float)
        # convert the timestamp to australian timezone
        merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp']).dt.tz_convert(plant.metadata.dataTimezone)

        # filter only the power and the modified ghi column
        merged_df = merged_df[['timestamp', 'power', 'modified_ghi']]
        # rename the columns accordingly
        merged_df.rename(columns={'power': 'active_power', 'modified_ghi': 'irradiation'}, inplace=True)

        # Filter only those data which are > 6 and < 18
        merged_df = merged_df[(merged_df['timestamp'].dt.hour >= PROD_START_HOUR) &
                              (merged_df['timestamp'].dt.hour <= PROD_END_HOUR)]
        # remove those which has na
        merged_df.dropna(inplace=True)
        # Filter only those days which has enough data in it.
        merged_df['date'] = merged_df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d'))

        # find the number of records  per date
        merged_df = pd.merge(merged_df, merged_df.groupby(['date']).size().reset_index(name='counts'), on='date',
                             how='inner')

        # Filter out those rows which have < MIN_POINTS_PER_DAY
        merged_df = merged_df[merged_df['counts'] >= MIN_POINTS_PER_DAY]

        # Filter those rows whose irradiation is not zero
        merged_df = merged_df[merged_df['irradiation'] > 0]

        print("get_plant_df() printing the head of the final dataframe")
        print(merged_df.head())
        print(merged_df.tail())

        # check if merged_df is not empty
        if merged_df.shape[0] > 0:
            # drop the date column as its no longer needed.
            merged_df.drop(['date', 'counts'], axis=1, inplace=True)
            return merged_df
        else:
            return pd.DataFrame()
    except Exception as e:
        print("get_plant_df() raised an Generic Exception please debug " + str(e))


# Function 2
# This function splits the dataframe in to Features / labels which can be used for furthur processing
# It doesnt return a dataframe but return features / labels as numpy arrays...
def feature_label_split(plant_df):
    try:
        # get the slot
        plant_df['slot'] = (plant_df['timestamp'].dt.hour * 60) + plant_df['timestamp'].dt.minute
        # not required for now
        # features['minute'] = features['timestamp'].dt.minute

        # drop the timestamp field as its not required now
        plant_df = plant_df.drop('timestamp', axis=1)

        # Labels are the values we want to predict
        labels = np.array(plant_df['active_power'])

        # Remove the labels from the features
        # axis 1 refers to the columns
        plant_df = plant_df.drop('active_power', axis=1)

        # Saving feature names for later use
        # feature_list = list(features.columns)

        # Convert to numpy array
        features = np.array(plant_df)

        print('feature_label_split() Full dataset Features Shape >>> ' + str(features.shape))
        print('feature_label_split() Full dataset Labels Shape >>> ' + str(labels.shape))

        # return the labels
        return features, labels
    except Exception as e:
        print('feature_label_split() raised an Exception please checck it ' + str(e))


# Function 3
# This function basically splits the dataset in to training and test dataset..
def train_test_array_split(features, labels, test_size=0.25):
    # Split the data into training and testing sets
    train_features, test_features, train_labels, test_labels = train_test_split(features, labels, test_size,
                                                                                random_state=42)

    # Show the shape of the numpy array after the split
    print('Training Features Shape >>> ' + str(train_features.shape))
    print('Training Labels Shape >>> ' + str(train_labels.shape))
    print('Testing Features Shape >>> ' + str(test_features.shape))
    print('Testing Labels Shape >>> ' + str(test_labels.shape))

    # return the training and test dataset..
    return train_features, test_features, train_labels, test_labels


# Function to calculate the MAPE
def mean_absolute_percentage_error(y_true, y_pred):
   return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# Function 4
# Function which basically fits and returns the classifier current classifier is XBGBoost Regressor
def classifier(features, labels):
    try:
        # Instantiate model
        # Gradient boosting model
        rf = XGBRegressor(random_state=42)
        #rf = XGBRegressor(n_estimators=50, random_state=42, max_depth=12)

        # Train the model on training data
        rf.fit(features, labels)

        # serialize the model into a file if needed for now not required.
        # joblib.dump(rf, filepath)

        # make predictions for test data
        predictions = rf.predict(features)
        # print(predictions)
        print('XGBOOST Metrics')
        print("R2 Score")
        print(r2_score(labels, predictions))
        print("Sqrt Mean Square error")
        print(np.sqrt(mean_squared_error(labels, predictions)))
        print("MAE")
        print(mean_absolute_error(labels, predictions))
        print("MAPE")
        print(mean_absolute_percentage_error(labels,predictions))

        # returns the classifier
        return rf
    except Exception as e:
        print("classifier() raised an Exception please check" + str(e))


# Function 5
# Function which returns residuals along with the accuracy
# labels are the actual expected output
def predict_power(rf, plant, current_time):
    # Now Get the next day future
    next_day_weather_data = WeatherData.objects.filter(api_source='solcast', timestamp_type='hourly',
                                                       identifier=plant.slug,
                                                       prediction_type='future',
                                                       ts__gte=(current_time + timedelta(days=1)).replace(hour=0,
                                                                                                          minute=0,
                                                                                                          second=0,
                                                                                                          microsecond=0),
                                                       ts__lt=(current_time + timedelta(days=1)).replace(hour=23,
                                                                                                         minute=59,
                                                                                                         second=59,
                                                                                                         microsecond=59))\
        .values_list('ts', 'ghi')

    try:
        next_day_weather_df = pd.DataFrame(next_day_weather_data[:], columns=['timestamp', 'ghi'])
        # convert the ghi column to a float value.
        next_day_weather_df['ghi'] = next_day_weather_df['ghi'].astype(float)
        # convert the  timestamp to the plant timezone.
        next_day_weather_df['timestamp'] = pd.to_datetime(next_day_weather_df['timestamp']).dt.tz_localize(
            "UTC").dt.tz_convert(plant.metadata.dataTimezone)
        # Filter only those data which are > 6 and < 18
        next_day_weather_df = next_day_weather_df[(next_day_weather_df['timestamp'].dt.hour >= PROD_START_HOUR) &
                                                  (next_day_weather_df['timestamp'].dt.hour <= PROD_END_HOUR)]
        # fill in the missing timestamps
        next_day_weather_df = next_day_weather_df.set_index('timestamp').resample('15T').reset_index()
        # handle missing ghi values.
        next_day_weather_df['ghi'] = next_day_weather_df['ghi'].fillna(
            (next_day_weather_df['ghi'].shift() + next_day_weather_df['ghi'].shift(-1)) / 2)
        # convert timestamp to number
        next_day_weather_df['slot'] = (next_day_weather_df['timestamp'].dt.hour * 60) + next_day_weather_df[
            'timestamp'].dt.minute
        # conver the dataframe into numpy array
        unseen_features = np.array(next_day_weather_df.drop('timestamp', axis=1))
        # Use the forest's predict method on the test data
        predictions = rf.predict(unseen_features)
        # add the results to the next_day_weather_df
        next_day_weather_df['predicted_power'] = predictions
        # Calculate the upper bounds and lower bounds basec on plants capacity
        # TODO remove multiplying by 1000
        next_day_weather_df["lower_bound"] = next_day_weather_df["predicted_power"] - (
            BOUNDS_ON_CAPACITY * plant.capacity)
        next_day_weather_df["upper_bound"] = next_day_weather_df["predicted_power"] + (
            BOUNDS_ON_CAPACITY * plant.capacity)

        # create an index to fill in the other timeslots in the output frame
        next_date = (current_time + timedelta(days=1)).strftime("%Y-%m-%d")
        todays_ts = pd.DataFrame({'timestamp':pd.date_range(next_date + " 00:00",next_date+ " 23:59", freq='15T')})
        todays_ts['timestamp'] = pd.to_datetime(todays_ts['timestamp']).dt.tz_localize(plant.metadata.dataTimezone)
        final_df = pd.merge(todays_ts, next_day_weather_df, how='left', on='timestamp')
        print("predict_power() printing the final predicted values using Gradient Boosting..")
        print(final_df[final_df['timestamp'].dt.time > time(5,0)].head(500))
        final_df.fillna(0, inplace=True)

        # Convert the median value to a list
        list_predicted_median = final_df["predicted_power"].tolist()
        # convert timestamp column to a list.
        list_timestamp_hour = final_df["timestamp"].tolist()
        print("Printing the list of predicted_median")
        print(list_predicted_median)
        list_predicted_lower_bound = final_df["lower_bound"].tolist()
        list_predicted_upper_bound = final_df["upper_bound"].tolist()

        for stream in OUTPUT_STREAM_NAMES:
            # Insert the entries in to Cassandra...
            save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                      count_time_period=PREDICTION_TIMEPERIOD,
                                      identifier_type='plant',
                                      plant_slug=plant.slug,
                                      identifier=plant.slug,
                                      stream_name='plant_power',
                                      model_name=stream,
                                      list_prediction=list_predicted_median,
                                      list_upper_bound=list_predicted_upper_bound,
                                      list_lower_bound=list_predicted_lower_bound,
                                      list_timestamp=list_timestamp_hour)

        print("predict_power() day ahead prediction uing solcast added")

    except Exception as e:
        print("predict_power() raised some exception while getting next day weather data " + str(e))


# Function 6
# Small function which basically checks for Nan
def NAN_check(*args):
    # print(args)
    NAN_list = []
    for array in args:
        # print(array)
        # array.size gives total numberr of elements in array..
        numpy_array = array.reshape(array.size, 1)
        # convert the elements in to a floating piint objects
        final_array = numpy_array.astype(np.float64, copy=False)
        # find if there is any nan in the numpy array if so append true.
        NAN_list.append(np.isnan(final_array).any())
    return NAN_list


# Function 7
# This function basically Creates new entries into cassandra..
def save_day_ahead_prediction(timestamp_type, count_time_period, identifier_type, plant_slug, identifier, stream_name,
                              model_name, list_prediction, list_upper_bound, list_lower_bound, list_timestamp):
    try:
        dt_current_time_UTC = timezone.now()

        # Now populate the database - create a Batch Request
        # Keep in mind that BatchQuery should be only used when inserting rows related to a single partition.
        # If Batch Queries are used on Inserts accessing multiple partitions Performace will degrade.
        # https://docs.datastax.com/en/cql/3.3/cql/cql_using/useBatchBadExample.html
        batch_query = BatchQuery()

        for i in range(0, len(list_prediction)):
            PredictionData.batch(batch_query).create(timestamp_type=timestamp_type,
                                                     count_time_period=count_time_period,
                                                     identifier=identifier,
                                                     stream_name=stream_name,
                                                     model_name=model_name,
                                                     ts=list_timestamp[i].astimezone(pytz.timezone('UTC')),
                                                     value=list_prediction[i],
                                                     lower_bound=list_lower_bound[i],
                                                     upper_bound=list_upper_bound[i],
                                                     update_at=dt_current_time_UTC)

            # Save data in NewPredictionData table for R app  STATISTICAL_DAY_AHEAD
            NewPredictionData.batch(batch_query).create(timestamp_type=timestamp_type,
                                                        count_time_period=count_time_period,
                                                        identifier_type=identifier_type,
                                                        plant_slug=plant_slug,
                                                        identifier=identifier,
                                                        stream_name=stream_name,
                                                        model_name=model_name,
                                                        ts=list_timestamp[i].astimezone(pytz.timezone('UTC')),
                                                        value=list_prediction[i],
                                                        lower_bound=list_lower_bound[i],
                                                        upper_bound=list_upper_bound[i],
                                                        update_at=dt_current_time_UTC)

        # execute the batch query.
        batch_query.execute()

    except Exception as ex:
        print("save_day_ahead_prediction() Exception in saving day ahead prediction: " + str(ex))


# Function 8
# removes anomaly rows using quartiles.
def remove_anomalies(df):
    # find the slots for the dataframe
    df['slot'] = (df['timestamp'].dt.hour * 60) + df['timestamp'].dt.minute
    # uniqueslots
    unique_slots = list(df['slot'].unique())
    final_df = pd.DataFrame()
    # loop through each of the slots
    for slot in unique_slots:
        print("remove_anomalies() working on slot "+str(slot))
        slot_df = df[df['slot']==slot]
        # if the slot is not supposed to be ignored then find the quantiles.
        if slot not in IGNORE_ANOMALY_SLOTS:
            IRRAD_Q1 = df['irradiation'].quantile(LOWER_QUARTILE)
            IRRAD_Q3 = df['irradiation'].quantile(UPPER_QUARTILE)
            print("remove_anomalies() Quartiles for Irradiation .. Values below/above these will be eliminated")
            print(IRRAD_Q1, IRRAD_Q3)
            POWER_Q1 = df['active_power'].quantile(LOWER_QUARTILE)
            POWER_Q3 = df['active_power'].quantile(UPPER_QUARTILE)
            print("remove_anomalies() Quartiles for ActivePower .. Values below/above these will be eliminated")
            print(POWER_Q1, POWER_Q3)
            # filter out the quartiles.
            slot_df = slot_df[(slot_df['active_power'] >= POWER_Q1) & (slot_df['active_power'] <= POWER_Q3) &
                              (slot_df['irradiation'] >= IRRAD_Q1) & (slot_df['irradiation'] <= IRRAD_Q3) ]
        # append the filtered results to the final df
        final_df =pd.concat([final_df,slot_df])
    print(final_df.head())
    print(final_df.tail())
    return final_df



# Function 9
# main function which performs the cleaning..
def GBM_Power_Prediction(today=timezone.now()):
    try:
        print("GBM_Power_Prediction() GBM Power Prediction cron job started >>>> %s", datetime.now())

        # Get all the properties raise exception if no properties
        try:
            plants = SolarPlant.objects.all()
            #plants = SolarPlant.objects.filter(slug='airportmetrodepot')
        except ObjectDoesNotExist:
            print("GBM_Power_Prediction() No properties found .. ")

        # Loop through each of the plants and call the power prediction algorithm..
        for plant in plants:
            try:
                print("\n\nGBM_Power_Prediction()  Prediction started for plant >>>> " + str(plant.slug))

                # Get the current timezone and convert it in to plant timezone
                try:
                    # get the current time .. Returns system time along with system timezone usually in UTC.
                    current_time = today
                    # convert the time to  plant timeone
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.dataTimezone))
                    print("GBM_Power_Prediction() current_time is >>>>" + str(current_time))
                except Exception as exc:
                    print(
                        "GBM_Power_Prediction() Exception occured in converting currenttime to property's TimeZone. " +
                        str(exc))
                    current_time = timezone.now()

                # Check if ready to do day_ahead_statistical_forecast
                operations_end_time = OPERATIONS_END_HOUR

                print("GBM_Power_Prediction() operations_end_time >>> " + str(operations_end_time))
                print("GBM_Power_Prediction() current_time.hour >>> " + str(current_time.hour))

                # check if current hour is greater than operations_end_time
                if current_time.hour >= operations_end_time:
                    print("GBM_Power_Prediction() Current time.hour > operations end time")

                    # Call the function which gets the data for the property
                    plant_df = get_plant_df(plant, current_time, irrad_type='current')
                    #print(plant_df.head())
                    # filter the anomalies
                    no_anomaly_df = remove_anomalies(plant_df)
                    # check if the property df is empty
                    if no_anomaly_df.shape[0] > 0:
                        # split in to features and labels
                        features, labels = feature_label_split(no_anomaly_df)
                        print("GBM_Power_Prediction() Check for NAN in Numpy arrays")
                        print(NAN_check(features, labels))
                        # create the classifier
                        rf = classifier(features, labels)
                        # call the predict power function
                        predict_power(rf, plant, current_time)

                    else:
                        print(
                            "GBM_Power_Prediction() get_plant_df() function returned an empty dataframe .. Nothing to "
                            "do skipping for property " + plant.slug)

            except Exception as e:
                print("GBM_Power_Prediction() raised an exception while predicting for property " + plant.slug + str(e))

    except Exception as e:
        print("cleaning_schedule() raised a generic Exception please correct the error " + str(e))


# Function 10
# Wrapper function on top of run_statistical_power_prediction
def gbm_prediction_wrapper():
    # Localize to India time..
    local_tz = pytz.timezone(DEFAULT_TIMEZONE)

    # Parse the end date
    end_date = datetime.strptime(END_DATE, '%Y-%m-%d %H:%M:%S')
    # localize to Asia kolkata
    end_date = local_tz.localize(end_date)
    # Parse the START_TIME.
    today = datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')
    # Localize to IST time.
    today = local_tz.localize(today)

    while today < end_date:
        print("gbm_prediction_wrapper()  Running for Date >>>> " + str(today))

        # call the prediction function
        GBM_Power_Prediction(today)

        # Increment today date
        today = today + timedelta(days=1)