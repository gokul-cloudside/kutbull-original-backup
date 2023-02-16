from django.conf import settings
from solarrms.models import PredictionData, NewPredictionData,PlantMetaSource,WeatherData,SolarPlant
from datetime import datetime
from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_power
from django.core.exceptions import ObjectDoesNotExist
import pytz
import pandas as pd
from datetime import timedelta
from cassandra.cqlengine.query import BatchQuery
import numpy as np

###########################################################################################################
# Variables
# Change here if needed.
###########################################################################################################

START_DATE = "2018-2-2 22:30:00"
#END_DATE = "2017-12-26 22:30:00"
END_DATE = "2018-2-28 22:30:00"
NO_OF_TRAINING_DAYS = 7
PREDICTION_TIMEPERIOD = settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES
BOUNDS_ON_CAPACITY = 0.15
OPERATIONS_END_TIME = 20
OPERATIONS_START_TIME = 6
NO_OF_VALIDATION_HOURS = 1
NO_OF_ADJUSTMENT_HOURS = 1
ADJUSTMENT_FACTOR = 0.8
MAX_FORECAST_ERROR = 9
#LOWER_BOUND_PERCENTILE = 0.1
#UPPER_BOUND_PERCENTILE = 0.9
#NO_OF_VALIDATION_MINS = 30
#MAX_FORECAST_ERROR_NEW = 7.5
#NO_OF_ADJUSTMENT_HOURS = 1
#MAX_FORECAST_MAPE_ERROR = 0.15
#ADJUSTMENT_PLANTS_15MIN = ['gupl', 'airportmetrodepot', 'yerangiligi']
#MODIFIED_STATISTICAL = ('gupl', 'airportmetrodepot', 'yerangiligi')
#MAX_CLOUD_COVER = 0.25


############################################################################################################
# Functions...
############################################################################################################


# Function 1
'''
This Function loops through each of the plants and calls the function which basically calls the day ahead
prediction function.
'''
def run_statistical_power_prediction(today=timezone.now(),recalculate=False):
    try:

        print("run_statistical_power_prediction() Statistical Power Prediction cron job started >>>> %s", datetime.now())

        # Get all the plants raise exception if no plants
        try:
            plant_meta_sources = PlantMetaSource.objects.all()
            #yerangiligi_plant = SolarPlant.objects.get(slug='gupl')
            #plant_meta_sources = [PlantMetaSource.objects.get(plant_id=yerangiligi_plant.id)]

        except ObjectDoesNotExist:
            print("No plant meta source found.")

        # Loop through each of the plants and call the power prediction algorithm..
        for plant_meta_source in plant_meta_sources:
            try:
                print ("\n\nrun_statistical_power_prediction() Statistical Power Prediction started for plant >>>> "+ str(plant_meta_source.plant.slug))
                if plant_meta_source.prediction_enabled:
                    # Get the current timezone and convert it in to plant timezone
                    try:
                        # get the current time .. Returns system time along with system timezone usually in UTC.
                        current_time = today
                        # convert the time to  plant timeone
                        current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                        print("run_statistical_power_prediction() current_time is >>>>"+ str(current_time))
                    except Exception as exc:
                        print("run_statistical_power_prediction() Exception occured in converting currenttime to plant's TimeZone. " + str(exc))
                        current_time = timezone.now()

                    # Get the UTC time not sure where its being used.
                    dt_current_time_UTC = current_time.astimezone(pytz.timezone('UTC'))
                    print("run_statistical_power_prediction() Current time in UTC is >>> "+str(dt_current_time_UTC))

                    #Check if ready to do day_ahead_statistical_forecast
                    operations_end_time = OPERATIONS_END_TIME

                    # Boolean variable used for Day Ahead prediction.
                    create_day_ahead_prediction = False

                    print("run_statistical_power_prediction() operations_end_time >>> " + str(operations_end_time))
                    print("run_statistical_power_prediction() current_time.hour >>> "+ str(current_time.hour))

                    # check if current hour is greater than operations_end_time
                    if current_time.hour >= operations_end_time:
                        print("run_statistical_power_prediction() Current time.hour > operations end time")

                        # if boolean is true call the function which calls the day ahead forecast..
                        if check_last_entry(plant_meta_source,'STATISTICAL_DAY_AHEAD',current_time,recalculate):
                            print("run_statistical_power_prediction() Create day ahead power prediction >>> True")
                            # call the function which computes the day ahead power forecast
                            compute_day_ahead_statistical_prediction_power(
                                plant_meta_source,
                                current_time,
                                settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)

                            print("run_statistical_power_prediction() 15 min power prediction completed for plant "+str(plant_meta_source.plant.slug))

                        # if boolean is true call the function which calls the day ahead forecast..
                        if check_last_entry(plant_meta_source, 'STATISTICAL_DAY_AHEAD_SOLCAST', current_time, recalculate):
                            print("run_statistical_power_prediction() Create day ahead power prediction using Solcast>>> True")
                            # call the function which computes the day ahead power forecast
                            compute_day_ahead_statistical_prediction_for_plant_solcast(
                                plant_meta_source,
                                current_time,
                                settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)

                            print("run_statistical_power_prediction() 15 min power prediction using solcast completed for plant " + str(plant_meta_source.plant.slug))

                    # below function call is not required for now.
                    save_actual_power_generation_for_plant(plant_meta_source,
                                                  current_time,
                                                  time_period_hours=24,
                                                  PREDICTION_TIMEPERIOD_SPECIFIED=settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)

                    print("run_statistical_power_prediction() actual values saved into Casandra.")

                else:
                    print("run_statistical_power_prediction() Prediction skipped for the plant since its not enabled for it >>> "+plant_meta_source.plant.slug)

            except Exception as ex:
                print("run_statistical_power_prediction() Exception raised while computing Day ahead prediction : "+str(ex))
                continue
    except Exception as ex:
        print("run_statistical_power_prediction() Exception raised please check the function.. "+str(ex))




# Function 2
# This function basically check if prediction needs to be run by checking the rows in the DB.
def check_last_entry(plant_meta_source,model_name,current_time,recalculate):

    #Check if Recalculate is True if so return True.
    if recalculate == False:

        # Get the predictionData and check till where the future prediction data is available.
        day_ahead_prediction_last_entry = PredictionData.objects. \
            filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                   count_time_period=settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES,
                   identifier=plant_meta_source.plant.slug,
                   stream_name='plant_power',
                   model_name=model_name).limit(1).values_list('ts')

        # if the last entry is not empty proceed ahead
        if day_ahead_prediction_last_entry:
            print("check_last_entry() Got some rows from the PredictionData table..")
            # Get the last entry timestamp.
            day_ahead_prediction_last_entry = [item[0] for item in day_ahead_prediction_last_entry]
            last_entry = day_ahead_prediction_last_entry[0]

            # Check if timezone information is present in datetime object if not localize to UTC as cassandra
            # returns time in UTC formatl
            if last_entry.tzinfo is None:
                # Localize the last_entry to UTC time.Cassandra usually returns in UTC timezone
                last_entry = pytz.utc.localize(last_entry)

            # convert the last_entry to plant timezone and check if its equal to current time.
            if last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone)).replace(hour=0, minute=0, second=0,microsecond=0) \
                    <= current_time.replace(hour=0, minute=0, second=0, microsecond=0):
                return True

            print("run_statistical_power_prediction() Last entry timestamp identified from Prediction table is >>> " + str(last_entry))
            return False
        else:
            # Set the day ahead to true since no entry is there in prediction data.
            return True
    else:
        print("check_last_entry() Recalculate is specified true ")
        return True



# Function 3
# Intermediate function to calculate day ahead prediction for plant
def compute_day_ahead_statistical_prediction_power(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        compute_day_ahead_statistical_prediction_for_plant(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED)
    except Exception as ex:
        print("compute_day_ahead_statistical_prediction_power() Exception raised please check: "+str(ex))



# Function 4
'''
This is the Main Function which calculates the next day prediction for the plant.
THis basically uses the ensemble approach.
where 3 day /5 day/7 day 15 min power values are calculated and a median value is taken as the result
'''
def compute_day_ahead_statistical_prediction_for_plant(plant_meta_source,current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        # Ensemble days list..
        ENSEMBLE_DAYS = [3,5,7]

        # Subtract the current time -7 days and that becomes the start_time.
        start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0,minute=0,second=0,microsecond=0)

        # Call the function which basically returns the power values.
        # The function would basically return dictionary of the following format
        '''
        Dictionary with key as device name and list of dict containing the power values.
         u'Inverter9-N': [{'power': 0.22433333333333336,
               'timestamp': Timestamp('2018-01-23 01:15:00+0000', tz='UTC')},
              {'power': 0.55220000000000002,
               'timestamp': Timestamp('2018-01-23 01:30:00+0000', tz='UTC')}]
        '''
        dict_power = get_minutes_aggregated_power(
            start_time,
            current_time,
            plant_meta_source.plant,
            'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60,
            split=True,
            meter_energy=True)

        print("compute_day_ahead_statistical_prediction_for_plant() get_minutes_aggregated_power API call completed..")
        # Create an empty dataframe to store the power values.
        df_power = pd.DataFrame()
        list_meter_keys =[]
        # Loop through each of the device key
        for meter_key in dict_power:
            print(meter_key)
            #print dict_energy[meter_key]
            df_stream = pd.DataFrame(dict_power[meter_key])
            # if the dataframe is not empty
            if not df_stream.empty:
                # rename the power column to the device key
                df_stream = df_stream.rename(columns={'power': meter_key})
                # convert the timestamp column to Pandas datatime object
                df_stream['timestamp'] = pd.to_datetime(df_stream['timestamp'])
                # set the timestamp as the index of the dataframe
                df_stream.set_index('timestamp')
                # append the meter key to the list not sure where its being used.
                list_meter_keys.append(meter_key)
            # if the final power dataframe is empty assign df_stream as df_power
            if df_power.empty:
                df_power = df_stream
            else:
                # else perform an outer join
                if not df_stream.empty:
                    df_new = pd.merge(df_power, df_stream, on='timestamp', how='outer')
                    df_power = df_new

        print("compute_day_ahead_statistical_prediction_for_plant() printing the head of dataframe after device merge.")
        print(df_power.head())

        '''
        Sample DF after the above operation.
                  Inverter28-S                 timestamp  Inverter5-S  Inverter16-S  \
        0         0.2210 2018-01-23 01:15:00+00:00       0.2070        0.1915
        1         0.6232 2018-01-23 01:30:00+00:00       0.6244        0.5924
        '''

        # If df_power is not empty
        if not df_power.empty:
            # create an empty dataframe
            ensemble_median=pd.DataFrame()

            # convert the timestamp column to  the plant timezone
            df_power['timestamp'] = pd.to_datetime(df_power['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)

            # Loop through each of the ensemble days.
            for d in ENSEMBLE_DAYS:

                # compute the new starttime
                start_time_new = (current_time - timedelta(days=d)).replace(hour=0,minute=0,second=0,microsecond=0)
                print("compute_day_ahead_statistical_prediction_for_plant() ensemble loop..New starttime is  "+str(start_time_new))

                df_energy_new = df_power[df_power['timestamp']>=start_time_new]
                #print df_energy_new.info()

                # Perform the groupby based on Hour and minute tuple.
                grouped = df_energy_new.groupby(df_energy_new['timestamp'].map(lambda x: (x.hour, x.minute)))

                # find the median of each of the group.
                df_predicted_median = grouped.median()

                #print "df_predicted_median"
                #print df_predicted_median

                df_predicted_median.reset_index(inplace = True)

                # find the horizontal sum
                df_predicted_median["median_sum"] = df_predicted_median[list_meter_keys].sum(axis=1)
                #instead of putting bounds based on quantiles, we would put bound based on % deviation w.r.t to plant capcity for penalty

                if ensemble_median.empty:
                    print("ensemble_median is empty")
                    ensemble_median = df_predicted_median
                    ensemble_median = ensemble_median.rename(columns={"median_sum":"median_sum"+str(d)})
                    ensemble_median = ensemble_median[["timestamp","median_sum"+str(d)]]
                    #ensemble_median.set_index('timestamp',inplace = True)
                else:
                    ensemble_stream = df_predicted_median
                    ensemble_stream = ensemble_stream.rename(columns={"median_sum":"median_sum"+str(d)})
                    ensemble_stream = ensemble_stream[["timestamp","median_sum"+str(d)]]
                    #ensemble_stream.set_index('timestamp',inplace = True)
                    ensemble_median = pd.merge(ensemble_median,ensemble_stream, on='timestamp', how='outer')

            print(ensemble_median.head())
            '''           Sample DF after the above operation..
                           timestamp  median_sum3  median_sum5  median_sum7
                        0     (1, 0)     0.022000     0.022000     0.022000
                        1    (1, 15)     8.693300     8.503133     8.659317
                        2    (1, 30)    25.494800    24.524600    24.906000
                        3    (1, 45)    49.175850    47.836500    47.711900
                        4     (2, 0)    78.724900    75.901800    77.920600
                        5    (2, 15)   116.551200   112.039200   108.932400
            '''
            # Find the median of the above three values
            ensemble_median['median_sum'] = ensemble_median[['median_sum3', 'median_sum5','median_sum7']].median(axis=1)
            # FInd the upper bound and the lower bounds
            ensemble_median["lower_bound"] = ensemble_median["median_sum"] - (BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity)
            ensemble_median["upper_bound"] = ensemble_median["median_sum"] + (BOUNDS_ON_CAPACITY*plant_meta_source.plant.capacity)

            print(ensemble_median.head())

            # Convert the median value to a list
            list_predicted_median = ensemble_median["median_sum"].tolist()
            # convert timestamp column to a list.
            list_timestamp_hour = ensemble_median["timestamp"].tolist()
            print("Printing the list of predicted_median")
            print(list_predicted_median)
            list_predicted_lower_bound = ensemble_median["lower_bound"].tolist()
            list_predicted_upper_bound = ensemble_median["upper_bound"].tolist()

            # Find tomorrows date
            dt_tomorrow = (current_time + timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)


            # Insert the entries in to Cassandra...
            save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                      count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                      identifier_type = 'plant',
                                      plant_slug = plant_meta_source.plant.slug,
                                      identifier=plant_meta_source.plant.slug,
                                      stream_name = 'plant_power',
                                      model_name = 'STATISTICAL_DAY_AHEAD',
                                      date_day_ahead= dt_tomorrow,
                                      list_prediction = list_predicted_median,
                                      list_upper_bound=list_predicted_upper_bound,
                                      list_lower_bound = list_predicted_lower_bound,
                                      list_ts_hour_min = list_timestamp_hour)

            # Insert entries into cassandra.
            save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                      count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                      identifier_type = 'plant',
                                      plant_slug = plant_meta_source.plant.slug,
                                      identifier=plant_meta_source.plant.slug,
                                      stream_name = 'plant_power',
                                      model_name = 'STATISTICAL_LATEST',
                                      date_day_ahead= dt_tomorrow,
                                      list_prediction = list_predicted_median,
                                      list_upper_bound=list_predicted_upper_bound,
                                      list_lower_bound = list_predicted_lower_bound,
                                      list_ts_hour_min = list_timestamp_hour)

            print("compute_day_ahead_statistical_prediction_for_plant() day ahead prediction added")

    except Exception as ex:
        print("compute_day_ahead_statistical_prediction_for_plant Exception raised please check.. " + str(ex))




# Function 5
'''
This Function Basically calculates the Power based on SOLCAST IRRADIATION DATA.
Following approach is done.
1) Get the Power data for the training period
2) Get the GHI data for the training period
3) Merge both the dataframe based on timestamp..
4) compute the following ratio power /GHI for each of the datapoint.
5) Find median over various ENSEMBLE days for each of the 15 min slot
6) Finally multiply the median ratio with next days Future GHI vales to  compute power.
'''
def compute_day_ahead_statistical_prediction_for_plant_solcast(plant_meta_source, current_time,PREDICTION_TIMEPERIOD_SPECIFIED):
    try:

        # Subtract the current time -7 days and that becomes the start_time.
        start_time = (current_time - timedelta(days=NO_OF_TRAINING_DAYS)).replace(hour=0, minute=0, second=0,microsecond=0)

        # Call the function which basically returns the power values.
        # The function would basically return dictionary of the following format
        '''[{'power': 6.0960000000000001,'timestamp': Timestamp('2017-09-14 12:30:00+0000', tz='UTC')},{'power': 1.143,'timestamp': Timestamp('2017-09-14 12:45:00+0000', tz='UTC')}]'''
        dict_power = get_minutes_aggregated_power(start_time,current_time,plant_meta_source.plant,'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED / 60,split=False,meter_energy=True)
        print("compute_day_ahead_statistical_prediction_for_plant() get_minutes_aggregated_power API call completed..")

        #Check if the API has returned any values.
        if len(dict_power) > 0:
            power_df = pd.DataFrame(dict_power)
            power_df['timestamp'] = pd.to_datetime(power_df['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)
            # Filter only those power values whch are greater than zero
            power_df = power_df[power_df['power'] > 0]
            # filter out those rows which are greater than 1.5*capacity
            power_df = power_df[power_df['power'] < (1.5 * plant_meta_source.plant.capacity)]
        else:
            print("compute_day_ahead_statistical_prediction_for_plant_solcast() get_minutes_aggregated_power() returned an empty list plant >>> "+plant_meta_source.plant.slug)
            return "NO POWER DATA"
        print("Printing the head of the POWER Dataframe..")
        print(power_df.head(50))

        # Get the GHI Data in another dataframe
        weather_data = WeatherData.objects.filter(api_source='solcast',timestamp_type='hourly',identifier=plant_meta_source.plant.slug,prediction_type='future',
                                                  ts__gte=start_time,ts__lt=current_time).order_by('prediction_type','ts').values_list('ts', 'ghi')

        try:
            weather_df = pd.DataFrame(weather_data[:],columns=['timestamp','ghi'])
            # convert the ghi column to a float value.
            weather_df['ghi'] = weather_df['ghi'].astype(float)
            # localize the timestamp column to UTC
            weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp']).dt.tz_localize("UTC").dt.tz_convert(plant_meta_source.dataTimezone)
        except Exception as e:
            print("compute_day_ahead_statistical_prediction_for_plant_solcast() WeatherData returned an empty list plant >>> "+plant_meta_source.plant.slug)
            return "NO WEATHER DATA PRESENT"
        print("Printing the head of the WEATHER Data Dataframe..")
        print(weather_df.head(50))

        # Now Merge Both the Dataframe based on timestamp.
        merged_df = pd.merge(power_df,weather_df,how='left',on=['timestamp'])
        # Handle missing data
        merged_df['modified_ghi'] = merged_df['ghi'].fillna((merged_df['ghi'].shift() + merged_df['ghi'].shift(-1)) / 2)
        # handle NaN
        merged_df['modified_ghi'].fillna('0',inplace=True)
        merged_df['modified_ghi'] = merged_df['modified_ghi'].astype(float)
        #print(merged_df.head(10000))
        #print(merged_df.dtypes)
        # find the ratio of POWER to GHI
        merged_df['ratio'] = merged_df['power'].divide(merged_df['modified_ghi'])
        # handle infinite values.
        merged_df['ratio'].replace(np.inf,0,inplace=True)
        # convert the timestamp column to  the plant timezone
        merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp']).dt.tz_convert(plant_meta_source.dataTimezone)
        print("Printing the head after merging Weather_DF and Power_DF")
        print(merged_df.head(50))

        # Groupby timeslots and take median of each of the slots.
        ensemble_median = merged_df.groupby(merged_df['timestamp'].map(lambda x: (x.hour, x.minute)))
        # find the median of each of the group.
        ensemble_median = ensemble_median.median()
        # reset the index of the dataframe..
        ensemble_median.reset_index(inplace=True)
        # select only the timestamp and the ratio column
        ensemble_median = ensemble_median[['timestamp','ratio']]
        # rename the ratio to median_ratio
        ensemble_median.rename(columns={'ratio': 'median_ratio'},inplace=True)
        print("Printing the head after the median operation for each slot")
        print(ensemble_median.head(50))


        # Now Get the next day future
        next_day_weather_data = WeatherData.objects.filter(api_source='solcast', timestamp_type='hourly',identifier=plant_meta_source.plant.slug, prediction_type='future',
                                                  ts__gte=(current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                                                  ts__lt=(current_time + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=59))\
            .order_by('prediction_type','ts').values_list('ts', 'ghi')

        try:
            next_day_weather_df = pd.DataFrame(next_day_weather_data[:],columns=['timestamp','ghi'])
            # convert the ghi column to a float value.
            next_day_weather_df['ghi'] = next_day_weather_df['ghi'].astype(float)
            # convert the  timestamp to the plant timezone.
            next_day_weather_df['timestamp'] = pd.to_datetime(next_day_weather_df['timestamp']).dt.tz_localize("UTC").dt.tz_convert(plant_meta_source.dataTimezone)
            #print("")
            #print(next_day_weather_df.head(50))

        except Exception as e:
            print("compute_day_ahead_statistical_prediction_for_plant_solcast() Future_Weather_Data returned an empty list plant >>> " + plant_meta_source.plant.slug + str(e))
            return "NO WEATHER DATA PRESENT"

        try:
            # Get the current date
            next_day_date = (current_time + timedelta(days=1)).strftime("%Y-%m-%d")
            # Generate the current days full timestamps
            next_day_ts_df = pd.DataFrame({'timestamp': pd.date_range(next_day_date + " 6:00", next_day_date + " 18:45", freq="15min")})
            # convert to timestamp and localize to plant timezone
            next_day_ts_df['timestamp'] = pd.to_datetime(next_day_ts_df['timestamp']).dt.tz_localize(plant_meta_source.dataTimezone)
            # perform the left join..
            final_next_day_df = pd.merge(next_day_ts_df,next_day_weather_df,on=['timestamp'],how='left')
            # handle missing values.
            final_next_day_df['ghi'] = final_next_day_df['ghi'].fillna((final_next_day_df['ghi'].shift() + final_next_day_df['ghi'].shift(-1)) / 2)
            # extract the hour/minute so that it can be merged with the ensemble median df
            final_next_day_df['timestamp'] = final_next_day_df['timestamp'].map(lambda x: (x.hour, x.minute))
            print("Printing the Final Next day Dataframe head")
            print(final_next_day_df.head(50))

            # merge both the dataframe
            prediction_df =pd.merge(ensemble_median,final_next_day_df,how='inner',on=['timestamp'])
            # Extract only the required columns
            prediction_df = prediction_df[['timestamp','ghi','median_ratio']]
            # find the predicted power
            prediction_df['predicted_power'] = prediction_df['ghi'] * prediction_df['median_ratio']
            # Replace the nans
            prediction_df['predicted_power'].fillna(0,inplace=True)
            # Calculate the upper bounds and lower bounds basec on plants capacity
            prediction_df["lower_bound"] = prediction_df["predicted_power"] - (BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity)
            prediction_df["upper_bound"] = prediction_df["predicted_power"] + (BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity)
            print("Printing the Final prediction Dataframe head")
            print(prediction_df.head(500))

        except Exception as e:
            print("compute_day_ahead_statistical_prediction_for_plant_solcast() Exception occured while Predicting next day energy >>> " + plant_meta_source.plant.slug + str(e))


        # Convert the median value to a list
        list_predicted_median = prediction_df["predicted_power"].tolist()
        # convert timestamp column to a list.
        list_timestamp_hour = prediction_df["timestamp"].tolist()
        print("Printing the list of predicted_median")
        print(list_predicted_median)
        list_predicted_lower_bound = prediction_df["lower_bound"].tolist()
        list_predicted_upper_bound = prediction_df["upper_bound"].tolist()

        # Find tomorrows date
        dt_tomorrow = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Insert the entries in to Cassandra...
        save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                  count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                  identifier_type='plant',
                                  plant_slug=plant_meta_source.plant.slug,
                                  identifier=plant_meta_source.plant.slug,
                                  stream_name='plant_power',
                                  model_name='STATISTICAL_DAY_AHEAD_SOLCAST',
                                  date_day_ahead=dt_tomorrow,
                                  list_prediction=list_predicted_median,
                                  list_upper_bound=list_predicted_upper_bound,
                                  list_lower_bound=list_predicted_lower_bound,
                                  list_ts_hour_min=list_timestamp_hour)

        # Insert entries into cassandra.
        save_day_ahead_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                  count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                  identifier_type='plant',
                                  plant_slug=plant_meta_source.plant.slug,
                                  identifier=plant_meta_source.plant.slug,
                                  stream_name='plant_power',
                                  model_name='STATISTICAL_LATEST_SOLCAST',
                                  date_day_ahead=dt_tomorrow,
                                  list_prediction=list_predicted_median,
                                  list_upper_bound=list_predicted_upper_bound,
                                  list_lower_bound=list_predicted_lower_bound,
                                  list_ts_hour_min=list_timestamp_hour)

        print("compute_day_ahead_statistical_prediction_for_plant() day ahead prediction uing solcast added")

    except Exception as ex:
        print("compute_day_ahead_statistical_prediction_for_plant Exception raised please check.. " + str(ex))




# Function 6
# This function basically Creates new entries into cassandra..
def save_day_ahead_prediction(timestamp_type,count_time_period,identifier_type,plant_slug, identifier,stream_name, model_name,
                              date_day_ahead, list_prediction, list_upper_bound, list_lower_bound, list_ts_hour_min):
    try:
        dt_current_time_UTC = timezone.now()

        print(date_day_ahead)

        # Now populate the database - create a Batch Request
        # Keep in mind that BatchQuery should be only used when inserting rows related to a single partition.
        # If Batch Queries are used on Inserts accessing multiple partitions Performace will degrade.
        # https://docs.datastax.com/en/cql/3.3/cql/cql_using/useBatchBadExample.html
        batch_query = BatchQuery()

        for i in range(0,len(list_prediction)):

            #Save data in PredictionData table as STATISTICAL_DAY_AHEAD
            #print(date_day_ahead)
            new_ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1])
            #print(new_ts)
            utc_ts = new_ts.astimezone(pytz.timezone('UTC'))
            #print(utc_ts)

            PredictionData.batch(batch_query).create(timestamp_type=timestamp_type,
                                          	count_time_period=count_time_period,
                                          	identifier=identifier,
                                          	stream_name = stream_name,
                                          	model_name = model_name,
                                          	ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1]).astimezone(pytz.timezone('UTC')),
                                          	value = list_prediction[i],
                                          	lower_bound = list_lower_bound[i],
                                          	upper_bound=list_upper_bound[i],
                                          	update_at = dt_current_time_UTC)


            #Save data in NewPredictionData table for R app  STATISTICAL_DAY_AHEAD
            NewPredictionData.batch(batch_query).create(timestamp_type=timestamp_type,
                                             	count_time_period=count_time_period,
                                             	identifier_type =identifier_type,
                                             	plant_slug = plant_slug,
                                             	identifier=identifier,
                                             	stream_name = stream_name,
                                             	model_name = model_name,
                                             	ts = date_day_ahead.replace(hour = list_ts_hour_min[i][0],minute=list_ts_hour_min[i][1]).astimezone(pytz.timezone('UTC')),
                                             	value = list_prediction[i],
                                             	lower_bound = list_lower_bound[i],
                                             	upper_bound=list_upper_bound[i],
                                             	update_at = dt_current_time_UTC)

        # execute the batch query.
        batch_query.execute()
    except Exception as ex:
        print("Exception in saving day ahead prediction: "+str(ex))


# Function 7
# Purpose of this function is to Save the actual Power values in to Cassandra DB for Dashboarding.
def save_actual_power_generation_for_plant(plant_meta_source, current_time, time_period_hours,
                                            PREDICTION_TIMEPERIOD_SPECIFIED):
    try:
        # calculate the starttime which is 24 hours minus current time.
        start_time = (current_time - timedelta(hours=time_period_hours))
        print("save_actual_power_generation_for_plant() current time is >>> "+str(current_time))
        print("save_actual_power_generation_for_plant() start time is >>> "+str(start_time))

        # Get the current time in UTC
        dt_current_time_UTC = timezone.now()

        # Below is the value returned by this function list of dictionaries.
        '''[{'power': 6.0960000000000001,'timestamp': Timestamp('2017-09-14 12:30:00+0000', tz='UTC')},{'power': 1.143,'timestamp': Timestamp('2017-09-14 12:45:00+0000', tz='UTC')}]'''
        # Get the actual Power values...
        dict_power = get_minutes_aggregated_power(
            start_time.replace(minute=0, second=0, microsecond=0),
            current_time.replace(minute=0, second=0, microsecond=0),
            plant_meta_source.plant,
            'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED / 60,
            split=False,
            meter_energy=True)


        # check if the length returned by the function is greater than zero if so insert into cassandra
        if len(dict_power) > 0:
            print(dict_power)

            # Now populate the database - create a Batch Request
            # Keep in mind that BatchQuery should be only used when inserting rows related to a single partition.
            # If Batch Queries are used on Inserts accessing multiple partitions Performace will degrade.
            # https://docs.datastax.com/en/cql/3.3/cql/cql_using/useBatchBadExample.html
            batch_query = BatchQuery()

            # Loop through each of the power values
            for i in range(0, len(dict_power)):
                try:
                    print(dict_power[i]['timestamp'], dict_power[i]['power'])


                    PredictionData.batch(batch_query).create(
                                            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                            count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                            identifier=plant_meta_source.plant.slug,
                                            stream_name='plant_power',
                                            model_name='ACTUAL',
                                            ts=dict_power[i]['timestamp'],
                                            value=dict_power[i]['power'],
                                            lower_bound=dict_power[i]['power'],
                                            upper_bound=dict_power[i]['power'],
                                            update_at=dt_current_time_UTC)

                    NewPredictionData.batch(batch_query).create(
                                               timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                               count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                               identifier_type='plant',
                                               plant_slug=plant_meta_source.plant.slug,
                                               identifier=plant_meta_source.plant.slug,
                                               stream_name='plant_power',
                                               model_name='ACTUAL',
                                               ts=dict_power[i]['timestamp'],
                                               value=dict_power[i]['power'],
                                               lower_bound=dict_power[i]['power'],
                                               upper_bound=dict_power[i]['power'],
                                                update_at=dt_current_time_UTC)

                except Exception as ex:
                    print("save_actual_power_generation_for_plant() raised an exception while preparing batch request "+str(ex))

            # execute the batch query.
            batch_query.execute()

            print("save_actual_power_generation_for_plant() actual power added")
        else:
            print("save_actual_power_generation_for_plant() No actual power for past 24 hours")

    except Exception as ex:
        print("save_actual_power_generation_for_plant() generic exception raised please check function " + str(ex))


# Function 9
# Adjustment Main Function .. .this would be called from kutbill/settings.py file.
def run_periodic_power_adjustments(current_time=timezone.now()):
    print(" run_periodic_prediction_adjustments() Periodic prediction adjustment cron job started "+str(datetime.now()))

    # Get all the Plantmetasources.
    try:
        plant_meta_sources = PlantMetaSource.objects.all()
    except ObjectDoesNotExist:
        print("run_periodic_prediction_adjustments() No plant meta source found.Check if mysql is working..")

    # Loop through each of the plantmetasources...
    for plant_meta_source in plant_meta_sources:
        try:
            if plant_meta_source.prediction_enabled:
                # Convert the current time to plant timezone
                current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))

                if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
                    print("\n\nrun_periodic_prediction_adjustments() Running prediction power adjustment for plant >>>"
                          +plant_meta_source.plant.slug)
                    # Call the function which does the periodic adjustments for solcast data
                    run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES,'GBM_DAY_AHEAD_SOLCAST','GBM_LATEST_SOLCAST')

                    # Call the function which does the periodic adjustments for solcast data
                    run_generation_prediction_adjustments(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES,'STATISTICAL_DAY_AHEAD_SOLCAST','STATISTICAL_LATEST_SOLCAST')
                    # call the function which does the periodic adjustments for power data
                    run_generation_prediction_adjustments(plant_meta_source, current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES,'STATISTICAL_DAY_AHEAD','STATISTICAL_LATEST')
            else:
                print("run_periodic_prediction_adjustments() Prediction skipped for plant since its not enabled "+str(plant_meta_source.plant.slug))
        except Exception as ex:
            print("run_periodic_prediction_adjustments() raised a generic exception please check "+str(ex))



# Function 10
# Perform Periodic Adjustment for each of the plants
'''
Below are the steps done by this function.
1) get the last one hour actual power data
2) get the day ahead prediction data for the same hour 
3) Merge both the dataframes and calculate the difference between actual and predicted and also the percentage difference. 
4) Find the median of the percentage difference
5) if the median percent difference is greater than the allowed error limit then get the next hour data and adjust 
those values and update in cassandra as a batch query for each partition.
'''
def run_generation_prediction_adjustments(plant_meta_source, current_time, PREDICTION_TIMEPERIOD_SPECIFIED,MODEL_NAME,ADJUSTMENT_MODEL_NAME):
    try:
        end_time = current_time.replace(minute=0, second=0, microsecond=0)
        # convert the end time to UTC as energy function which reads from cassandra returns in UTC
        end_time_utc = end_time.astimezone(pytz.timezone('UTC'))
        # get the start time by subtracting one hour
        start_time_utc = end_time_utc - timedelta(hours=NO_OF_VALIDATION_HOURS)
        print("run_generation_prediction_adjustments() computed endtime in UTC is >>> "+str(end_time_utc)+" Model name >>> "+MODEL_NAME)
        print("run_generation_prediction_adjustments() computed starttime in UTC is >>> " + str(start_time_utc) + " Model Name >>> "+MODEL_NAME)

        # Below is the value returned by this function list of dictionaries.
        '''[{'power': 6.0960000000000001,'timestamp': Timestamp('2017-09-14 12:30:00+0000', tz='UTC')},{'power': 1.143,'timestamp': Timestamp('2017-09-14 12:45:00+0000', tz='UTC')}]'''
        # Get the actual Power values...
        dict_power = []
        dict_power = get_minutes_aggregated_power(
            start_time_utc,
            end_time_utc,
            plant_meta_source.plant,
            'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED / 60,
            split=False,
            meter_energy=True)

        # check if the length of the dictionary is greater than zero
        if len(dict_power) > 0:
            # convert the list to dataframe
            actual_power = pd.DataFrame(dict_power)
            # convert the timestamp to datetime
            actual_power['timestamp'] = pd.to_datetime(actual_power['timestamp'])
            # set the timestamp as index of dataframe.
            actual_power.set_index('timestamp', inplace=True)


            # get the prediction data
            forecast_power = return_predictiondata_df(PREDICTION_TIMEPERIOD_SPECIFIED,plant_meta_source,start_time_utc,end_time_utc,MODEL_NAME)
            # check if the forecast_power is empty
            if forecast_power.empty:
                print("run_generation_prediction_adjustments() forecast_power is empty model name >>> "+MODEL_NAME)
                return "NO DAY_AHEAD PREDICTION DATA"

            print("run_generation_prediction_adjustments() printing the head of actual_power dataframe Model >>> "+MODEL_NAME)
            print(actual_power.head(50))
            print("run_generation_prediction_adjustments() printing the head of the forecast power dataframe Model >>> "+MODEL_NAME)
            print(forecast_power.head(50))

            # Now Merge both the dataframe based on timestamp.
            combined = pd.merge(actual_power, forecast_power, how='inner', left_index=True, right_index=True)

            print("run_generation_prediction_adjustments() printing the head of Dataframe after merging Model >>> "+MODEL_NAME)
            print(combined.head(50))
            # change the columns of the Dataframe
            combined.columns = ['actual', 'forecast']
            # filter only those rows greater than zero.
            combined = combined[combined['actual'] > 0]

            # Check if there are four slots present in the dataframe if not dont do any adjustments.
            if combined.shape[0] == 3600 / PREDICTION_TIMEPERIOD_SPECIFIED:
                # find the difference between actual and forecast
                combined['diff'] = combined['actual'] - combined['forecast']
                # find percentage difference
                combined['diff_percentage'] = ((combined['actual'] - combined['forecast']) / plant_meta_source.plant.capacity) *100
                # get the median of the percentage difference
                mean_percentage = combined['diff_percentage'].median()
                print("run_generation_prediction_adjustments() printing the combined_df after percentage difference calc Model >>> "+MODEL_NAME)
                print(combined.head(50))
                print("run_generation_prediction_adjustments() Median of percentage difference is >>>> "+str(mean_percentage))

                # set the endtime as start time for adjustments
                start_time_adjustment_utc = end_time_utc
                # get the new end time for adjustments
                end_time_adjustment_utc = start_time_adjustment_utc + timedelta(hours=NO_OF_ADJUSTMENT_HOURS)

                # check if the mean_percentage is greater than allowed error limit if its greater perform adjustments current limit is 9
                if abs(mean_percentage) >= MAX_FORECAST_ERROR:

                    adjustments = mean_percentage * ADJUSTMENT_FACTOR
                    print('run_generation_prediction_adjustments() Final adjustment value is >>>> '+str(adjustments))

                    #Get the next hour Data from the predicted table
                    powerData = PredictionData.objects.filter(
                        timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                        count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                        identifier=plant_meta_source.plant.slug,
                        stream_name='plant_power',
                        model_name=MODEL_NAME,
                        ts__gte=start_time_adjustment_utc,
                        ts__lt=end_time_adjustment_utc)

                    # Now populate the database - create a Batch Request
                    # Keep in mind that BatchQuery should be only used when inserting rows related to a single partition.
                    # If Batch Queries are used on Inserts accessing multiple partitions Performace will degrade.
                    # https://docs.datastax.com/en/cql/3.3/cql/cql_using/useBatchBadExample.html
                    batch_query = BatchQuery()

                    # Now loop through the
                    for i in range(0, NO_OF_ADJUSTMENT_HOURS * 3600 / PREDICTION_TIMEPERIOD_SPECIFIED):
                        try:
                            adjusted_value = powerData[i]['value'] + \
                            (adjustments * plant_meta_source.plant.capacity) / (100)


                            PredictionData.batch(batch_query).create(
                                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                identifier=plant_meta_source.plant.slug,
                                stream_name='plant_power',
                                model_name=ADJUSTMENT_MODEL_NAME,
                                ts=powerData[i]['ts'],
                                value=adjusted_value,
                                lower_bound=adjusted_value - BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity,
                                upper_bound=adjusted_value + BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity,
                                update_at=end_time_utc)



                            NewPredictionData.batch(batch_query).create(
                                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                identifier_type='plant',
                                plant_slug=plant_meta_source.plant.slug,
                                identifier=plant_meta_source.plant.slug,
                                stream_name='plant_power',
                                model_name=ADJUSTMENT_MODEL_NAME,
                                ts=powerData[i]['ts'],
                                value=adjusted_value,
                                lower_bound=adjusted_value - BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity,
                                upper_bound=adjusted_value + BOUNDS_ON_CAPACITY * plant_meta_source.plant.capacity,
                                update_at=end_time_utc)

                            print("ADJUSTED: prediction value adjusted: " + str(
                                adjusted_value) + " from original value: " + str(powerData[i]['value']))

                        except Exception as ex:
                            print("run_generation_prediction_adjustments() Creation of Batch Query raised an exception: " +str(ex))

                    # execute the batch query.
                    batch_query.execute()
            else:
                print("run_generation_prediction_adjustments() there is no four slots present in the dataframe.. Model >>> "+MODEL_NAME)
                return "NO FOUR SLOTS"
        else:
            print("run_generation_prediction_adjustments() get_minutes_aggregated_power() returned an empty Dataframe.. Model >>> "+MODEL_NAME)
            return "NO POWER DATA"

    except Exception as ex:
        print("run_generation_prediction_adjustments() Generic exception raised something wrong with function check it.... " + str(ex))




# Function 11
# THis function basically returns the prediction data as a dataframe.
def return_predictiondata_df(PREDICTION_TIMEPERIOD_SPECIFIED,plant_meta_source,start_time_utc,end_time_utc,model_name):

    # Now we need to get the forecast  Dataframe...
    forecast_power_list = PredictionData.objects.filter(
        timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
        count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
        identifier=plant_meta_source.plant.slug,
        stream_name='plant_power',
        model_name=model_name,
        ts__gte=start_time_utc,
        ts__lt=end_time_utc).order_by('ts').values_list('ts', 'value')

    try:
        forecast_power = pd.DataFrame(forecast_power_list[:], columns=['timestamp', 'value'])
        # convert the value column to a float value.
        forecast_power['value'] = forecast_power['value'].astype(float)
        forecast_power['value'] = forecast_power['value'].round(4)
        # convert timestamp column to datetime
        forecast_power['timestamp'] = pd.to_datetime(forecast_power['timestamp']).dt.tz_localize("UTC")
        # set the timestamp  column as the index
        forecast_power.set_index('timestamp', inplace=True)
        # return the forecast_power dataframe
        return forecast_power
    except Exception as e:
        print("return_predictiondata_df() Predicion data returned nothing >>> " + plant_meta_source.plant.slug + str(e))
        # return an empty Dataframe
        return pd.DataFrame()



# Function 12
# Wrapper function on top of run_statistical_power_prediction
def prediction_wrapper():
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
        print("prediction_wrapper()  Running for Date >>>> "+str(today))

        # call the prediction function
        run_statistical_power_prediction(today,recalculate=False)

        # Increment today date
        today = today + timedelta(days=1)