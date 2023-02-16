"""
This Program calls the Opencpu R API to Run Energy Prediction Algorithm based on GLM.
It would predict the next hours energy
"""
###################################################################################
# Imports
###################################################################################
from django.conf import settings
# Model in which prediction results needs to be written
from solarrms.models import PredictionData,NewPredictionData
# Import datetime for date manipulatioins...
from datetime import datetime, timedelta
from django.utils import timezone
# handling HTTP requests..
import requests
# Parsing json..
import json
import sys
# importing pytz for timezone manipulations.
import pytz
# Importing SolarPlant to get all the plants.
from solarrms.models import SolarPlant
# Importing the function which returns the energy
from solarrms.solarutils import get_minutes_aggregated_energy
# Importing Pandas
import pandas as pd
import numpy as np


###################################################################################
# Variables Required for the below cron to work.
###################################################################################

tz_ist = pytz.timezone('Asia/Kolkata')
header = {'Content-Type': 'application/json'}
KPI_WINDOW_SIZE = 15
# OpenCPU R Server Address..
from_server_address = 'http://13.127.17.99'
PREDICTION_TIMEPERIOD_SPECIFIED = 900

####################################################################################
# Functions
####################################################################################


# Function 1
# THis is the Main Function which Basically calls the Energy Prediction Function written in R
def energy_prediction_glm(today=timezone.now(),recalculate=False):
    try:

        print("Energy Prediction CronJob using GLM model STARTED.. %s",datetime.now().isoformat())

        # Create the HTTP URL.for issuing the Open CPU Request
        # OpenCPU Prediction API path...
        sources_url = '/ocpu/user/dataglen/library/PredictionEnergyLag/R/EnergyPredict/json'

        # Get all the solar plants.
        #plants = SolarPlant.objects.all()
        plants = SolarPlant.objects.filter(slug__in=['airportmetrodepot','yerangiligi','gupl','ranergy'])   

        # Loop through each of the plants ....
        for plant in plants:

            # Get the plant slug. This needs to be passed to the API..
            plant_name = plant.slug

            # Get the plant Timezone
            plant_timezone = plant.metadata.dataTimezone

            # Now that we have the timezone of the plant Convert Todays time to the plant Timezone
            try:
                # Convert the current time to the plant timezone...
                current_time = today.astimezone(pytz.timezone(plant_timezone))

                print("\n\ncurrent_time "+str(current_time)+ " plant  "+plant_name)

            except Exception as exc:
                print("Timezone conversion Raised an exception " + str(exc))
                # PREDICTION WOULD GO WRONG IN THIS CASE
                #Use the UTC time if one cannot change to Plant's timezone.
                current_time = today


            # Perform the below operations only after 8 o clock...
            if current_time.hour >= 7 and current_time.hour <= 18:

                # Generate the plant Start time and shutdown time...
                # will be used for getting the current days energy.....
                plant_shut_down_time = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)

                # Call the function which basically returns the energy
                # Returns a List
                # Below is the example output returned by this function...
                """
                [{'energy': 3817.0,
                  'timestamp': Timestamp('2017-07-28 06:00:00+0000', tz='UTC')},
                 {'energy': 3740.0,
                  'timestamp': Timestamp('2017-07-28 06:15:00+0000', tz='UTC')},
                 {'energy': 3645.0,
                  'timestamp': Timestamp('2017-07-28 06:30:00+0000', tz='UTC')},
                 {'energy': 3861.0,
                  'timestamp': Timestamp('2017-07-28 06:45:00+0000', tz='UTC')}
                  ]
                """
                print("Calling the get_minutes_aggregated_energy() to get the energy() for plant "+plant_name)

                energy_list = get_minutes_aggregated_energy\
                    (plant_start_time,plant_shut_down_time,plant,"MINUTE","15",split=False,meter_energy=True)

                #print(energy_list)

                # Check if energy_list has Data if not do nothing.
                if len(energy_list) > 0:

                    # Convert the List in to a Dataframe...
                    energy_df = pd.DataFrame(energy_list)

                    # Convert the timestamp column to the plant timezone
                    energy_df['timestamp'] = pd.to_datetime(energy_df['timestamp']).dt.tz_convert(
                        plant_timezone)

                    # Get the current date
                    current_date = plant_start_time.strftime("%Y-%m-%d")

                    # Generate the current days full timestamps
                    todays_ts = pd.DataFrame(
                        {'timestamp': pd.date_range(current_date + " 6:00", current_date + " 18:45", freq="15min")})

                    # convert it in to Dataframe
                    todays_ts['timestamp'] = pd.to_datetime(todays_ts['timestamp']).dt.tz_localize(plant_timezone)

                    # Now merge these two dataframes.
                    combined_df = pd.merge(todays_ts, energy_df, how='left', on='timestamp')
                    print(combined_df.head(10000))

                    if recalculate == False:
                        # read the Prediction data from the prediction_data cassandra table.
                        # returns predicted_energy along with timestamp..
                        forecast_df = getPredictionDataEnergy(plant, 'GLM_MODEL',
                                                              plant_start_time, plant_shut_down_time,
                                                              PREDICTION_TIMEPERIOD_SPECIFIED)

                        print(forecast_df.head(10000))
                    else:
                        # create an empty dataframe for forecasting
                        forecast_df = pd.DataFrame()

                    # check if any slots predictions are already completed.
                    if forecast_df.shape[0] > 0:

                        # Merge this thing with the energy_df
                        final_combined = pd.merge(combined_df,forecast_df,how='left',on='timestamp')

                        # create the lags.
                        final_combined['lag5'] = final_combined['energy'].shift(5)
                        final_combined['lag6'] = final_combined['energy'].shift(6)
                        final_combined['lag7'] = final_combined['energy'].shift(7)
                        final_combined['lag8'] = final_combined['energy'].shift(8)
                        print(final_combined.head(10000))

                        # Filter out those rows which has the predicted energy as Null...if it has values means prediction is already completed for that slot.
                        final_combined = final_combined[final_combined['predicted_energy'].isnull()]

                    else:

                        # if there is no prediction data then just use the combined df
                        final_combined = combined_df

                        # create the lags.
                        final_combined['lag5'] = final_combined['energy'].shift(5)
                        final_combined['lag6'] = final_combined['energy'].shift(6)
                        final_combined['lag7'] = final_combined['energy'].shift(7)
                        final_combined['lag8'] = final_combined['energy'].shift(8)



                    # Select only the required columns of the Dataframe.
                    prediction_df = final_combined[['timestamp','lag5','lag6','lag7','lag8']]

                    # Remove those rows having the lags as nan.
                    # These are the slots for which computation needs to be done..
                    prediction_df.dropna(inplace=True)
                    print(prediction_df.head(10000))


                    # check if there any slots for which prediction can be done.
                    if prediction_df.shape[0] > 0:

                        # Now that we have the final Dataframe for which the prediction can be computed ...iterate to call the R prediction function
                        for index, row in prediction_df.iterrows():

                            # Get the current slot minute .. This will be passed to the OpenCPU API
                            current_slot_minute = row['timestamp'].hour * 60 + row['timestamp'].minute
                            print('\n Current slot  in minutes for which computation is done >>>>>> '+str(current_slot_minute))

                            # Convert the current_slot to UTC
                            current_slot_utc = row['timestamp'].astimezone(pytz.timezone('UTC'))

                            # The Open cpu URL which needs to be called
                            from_url = from_server_address + sources_url

                            # Pass in the plant name,Current minute slot , lag5 , lag6 , lag7 , lag8
                            # Pass in the plant name and date
                            params = {'plantname': plant_name, 'minute1': current_slot_minute, 'lag5': row['lag5'], 'lag6': row['lag6'],
                                      'lag7': row['lag7'], 'lag8': row['lag8']}

                            print datetime.now().isoformat(), today, plant_name, 'making API call...'
                            print params

                            # issue the HTTP post request
                            response = requests.post(from_url, headers=header, data=json.dumps(params))
                            # print(response)

                            # check if the post request returned a dictionary
                            try:
                                response_json = json.loads(response.content)
                            except:
                                response_json = {}

                            print datetime.now().isoformat(), today, plant_name, 'saving The prediction Results..'

                            # if it has returned a dictionary and has results in it Handle the result and save it in to cassandra..
                            if handle_prediction_result(plant_name, response_json, current_slot_utc):
                                print datetime.now().isoformat(), today, plant_name, response.status_code
                            else:
                                print datetime.now().isoformat(), today, plant_name, response.status_code, response.text

                    else:
                        print("skipping since there are no slots to predict in the Dataframe "+plant_name)
                else:
                    print("skipping since the energy dataframe doesnot contain any rows for plant " + plant_name)
            else:
                print("Skipping since the current time is not within 7:00 to 19:00 for plant " + plant_name)

        print datetime.now().isoformat(), "cleaning_schedule CRONJOB STOPPED"

    except Exception as ex:
        print("Exception occured in cleaning_schedule cronjob "+str(ex))




# Function 2
# This Function handles the data retured by the R API.
# The http response will contain a key called results
def handle_prediction_result(plant_name, response_json,current_slot_utc):
    print(response_json)

    # Check if the dictionary returned by Opencpu has results in it. It may contain an error also
    # if it has result proceed else return
    if not response_json.has_key('results'):
        return False

    # get the results
    results  = response_json['results']
    #print(results)

    # get the predicted energy along with the lower and upper bound values.
    predicted_energy   = results['predicted_energy'][0]
    lower_bound = results['lower_bound'][0]
    upper_bound = results['upper_bound'][0]

    print('saving plantname >>>'+plant_name+" UTC TIME >>>"+str(current_slot_utc)+" PREDICTED_ENERGY >>>>"+str(predicted_energy))

    # Call the function which basically writes data back to cassandra..
    save_energy_prediction(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                              count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                              identifier=plant_name,
                              stream_name='plant_energy',
                              model_name='GLM_MODEL',
                              ts=current_slot_utc,
                              value=predicted_energy,
                              lower_bound=lower_bound,
                              upper_bound=upper_bound)

    return True



# Function 3
# Function which basically writes data in to Cassandra.Uses the Django Model to write data back to cassandra..
# Data will be Inserted in to PredictedValues..
def save_energy_prediction(timestamp_type,count_time_period,identifier,stream_name,
                           model_name, ts, value,lower_bound,upper_bound):
    try:
        # Get the current time  in UTC
        dt_current_time_UTC = timezone.now().replace(tzinfo=None)

        #utc_ts = dt_current_time_UTC.astimezone(pytz.timezone('UTC'))
        print "Updated_at timestamp",dt_current_time_UTC

        # import pdb;pdb.set_trace()

        # Insert in to Cassandra.
        PredictionData.objects.create(timestamp_type=timestamp_type,
                                      count_time_period=count_time_period,
                                      identifier=identifier,
                                      stream_name = stream_name,
                                      model_name = model_name,
                                      ts = ts,
                                      value = value,
                                      lower_bound = lower_bound,
                                      upper_bound=upper_bound,
                                      update_at = dt_current_time_UTC)

        NewPredictionData.objects.create(timestamp_type=timestamp_type,
                                       count_time_period=count_time_period,
                                       identifier_type='plant',
                                       plant_slug=identifier,
                                       identifier=identifier,
                                       stream_name=stream_name,
                                       model_name=model_name,
                                       ts=ts,
                                       value=value,
                                       lower_bound=lower_bound,
                                       upper_bound=upper_bound,
                                       update_at=dt_current_time_UTC)

    except Exception as ex:
        print("Exception in saving day ahead prediction: "+str(ex))



# Function 4
# This function reads the data from Prediction Data Cassandra Table and returns the rows as a Dataframe.
def getPredictionDataEnergy(plant, modelName, tsStart, tsEnd, PREDICTION_TIMEPERIOD_SPECIFIED):

    try:
        # Get the plant Slug
        identifier_slug = plant.slug

        # Get the plant Timezone
        plant_timezone = plant.metadata.dataTimezone

        # Stream name which needs to be queried.
        stream_name = 'plant_energy'

        # Get the predicted results from Cassandra...
        # Sort by timestamp and select only the timestamp along with the predicted value..
        prediction_list = PredictionData.objects.filter(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
            count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
            identifier=identifier_slug,
            stream_name=stream_name,
            model_name=modelName,
            ts__gte=tsStart,
            ts__lt=tsEnd).order_by('ts').values_list('ts', 'value')


        # check if cassandra had returned any result.
        if len(prediction_list) > 0:

            #create the dataframe out the results
            prediction_df = pd.DataFrame(prediction_list[:], columns=['timestamp', 'predicted_energy'])


            # Replace the seconds and milliseconds part
            # It would be already zero anyways
            prediction_df['timestamp'] = prediction_df['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))

            # Convert the timestamp to the plant timestamp.
            prediction_df['timestamp'] = pd.to_datetime(prediction_df['timestamp']).dt.tz_localize('UTC').dt.tz_convert(plant_timezone)

            # set the timestamp as the index
            #prediction_df.set_index('timestamp', inplace=True)

            # return the dataframe..
            return prediction_df
        else:
            # Return an empty dataframe.
            return pd.DataFrame()


    except Exception as ex:
        print "Exception in getPredictionDataEnergy: " + str(ex)



# Function 5
# Function which prepares training dataset and fits for each plant.
# Calls the opencpu function fetch_oneday_fromDjango
# One needs to pass in the plant name as Input.
def generate_currentday_glm_fits():
    try:

        # Loop through each of the plants
        # Call the API
        # check if its success..
        print("Energy Prediction Fit CronJOB for GLM model STARTED.."+datetime.now().isoformat())

        # Create the HTTP URL.for issuing the Open CPU Request
        # OpenCPU Prediction API path...
        fit_source_url = '/ocpu/user/dataglen/library/PredictionEnergyLag/R/CurrentDayFit/json'

        # Get all the solar plants.
        #plants = SolarPlant.objects.all()
        plants = SolarPlant.objects.filter(slug__in=['airportmetrodepot','yerangiligi','gupl','ranergy'])

        # Loop through each of the plants ....
        for plant in plants:

            # Get the plant slug. This needs to be passed to the API..
            plant_name = plant.slug

            # The Open cpu URL which needs to be called
            from_url = from_server_address + fit_source_url

            # Pass in the plant name.
            params = {'plantname': str(plant_name)}

            print datetime.now().isoformat(), plant_name, 'making API call...'
            #print from_url
            #print params

            response = requests.post(from_url, headers=header, data=json.dumps(params))
            print(response.text)

            try:
                response_json = json.loads(response.content)
            except:
                response_json = {}

            # Check if R API returned results or error
            if response_json.has_key("results"):
                print datetime.now().isoformat(), plant_name, response.status_code
            else:
                print datetime.now().isoformat(), plant_name, response.status_code, response.text

    except Exception as ex:
        print("Prepare_fits raised an Exception please fix: " + str(ex))




# Function 6
# Function which prepares training dataset and fits for each plant.
# Calls the opencpu function fetch_oneday_fromDjango
# One needs to pass in the plant name as Input.
def initialize_training_data():
    try:

        # Loop through each of the plants
        # Call the API
        # check if its success..
        print("initialize_training_data for GLM model STARTED.."+datetime.now().isoformat())

        # Create the HTTP URL.for issuing the Open CPU Request
        # OpenCPU Prediction API path...
        fit_source_url = '/ocpu/user/dataglen/library/PredictionEnergyLag/R/initialize_energy_training/json'

        # Get all the solar plants.
        #plants = SolarPlant.objects.all()
        plants = SolarPlant.objects.filter(slug='airportmetrodepot')

        # Loop through each of the plants ....
        for plant in plants:

            # Get the plant slug. This needs to be passed to the API..
            plant_name = plant.slug

            # The Open cpu URL which needs to be called
            from_url = from_server_address + fit_source_url

            # Pass in the plant name.
            params = {'plantname': str(plant_name)}

            print datetime.now().isoformat(), plant_name, 'making API call...'
            #print from_url
            #print params

            response = requests.post(from_url, headers=header, data=json.dumps(params))
            print(response.text)

            try:
                response_json = json.loads(response.content)
            except:
                response_json = {}

            # Check if R API returned results or error
            if response_json.has_key("results"):
                print datetime.now().isoformat(), plant_name, response.status_code
            else:
                print datetime.now().isoformat(), plant_name, response.status_code, response.text

    except Exception as ex:
        print("initialize_training_data raised an Exception please fix: " + str(ex))