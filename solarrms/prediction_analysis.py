from solarrms.models import SolarPlant, PredictionData, NewPredictionData
import pandas as pd
import json
from solarrms.solarutils import get_plant_power, get_irradiation_data
import numpy as np
import math

def get_actual_and_latest_predicted_values(starttime, endtime, plant, model_name, count_time_period):
    try:

        # uncomment for reverting
        # stream_name = 'plant_power' if plant.get_client().id == 890 else 'plant_energy'

        # for bbagewadi we are considering input and output streams as in power hence everything would be in power
        # for other plants of adani input would be in energy and the output stream would be in power
        # hence for the  input streams like ACTUAL and GBM_DAY_AHEAD_SOLCAST we need to read the energy data
        # and convert it to power so that other calculations dont need to change.
        if model_name == 'ACTUAL' or model_name == 'GBM_DAY_AHEAD_SOLCAST':
            stream_name = 'plant_power' if plant.slug == 'bbagewadi' else 'plant_energy'
        else:
            stream_name = 'plant_power' if plant.get_client().id == 890 else 'plant_energy'
        #print("get_actual_and_latest_predicted_values() streamname >>> "+str(stream_name))

        df_final = pd.DataFrame()
        timestamps = []
        actual_values = []
        predicted_values = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                            count_time_period=count_time_period,
                                                            identifier_type='plant',
                                                            plant_slug=str(plant.slug),
                                                            identifier=str(plant.slug),
                                                            stream_name=stream_name,
                                                            model_name=model_name,
                                                            ts__gte=starttime,
                                                            ts__lte=endtime)
        for predicted_value in predicted_values:
            actual_values.append(float(predicted_value.value))
            timestamps.append(predicted_value.ts)
        df_final['timestamp'] = timestamps
        df_final[model_name] = actual_values
        return df_final
    except Exception as exception:
        print ("Exception in getting actual and latest predicted values : " + str(exception))

def calculate_dsm_penalty(plant, absolute_error):
    try:
        capacity_factor = float(plant.capacity) if plant.get_client().id == 890 else float(plant.capacity) / 4
        # capacity_factor = float(plant.capacity)/4
        dsm_penalty = 0.0
        if absolute_error < 15:
            value1 = absolute_error-15
            dsm_penalty1 = value1*0
            dsm_penalty = dsm_penalty1
        elif 15 <= absolute_error < 25:
            dsm_penalty1 = 15*0
            value2 = absolute_error - 15
            dsm_penalty2 = value2*0.5
            dsm_penalty = dsm_penalty1 + dsm_penalty2
        elif 25 <= absolute_error < 35:
            dsm_penalty1 = 15*0
            value2 = 25 - 15
            dsm_penalty2 = value2*0.5
            value3 = absolute_error-25
            dsm_penalty3 = value3*1.0
            dsm_penalty = dsm_penalty1 + dsm_penalty2 + dsm_penalty3
        elif absolute_error > 35:
            dsm_penalty1 = 15*0
            value2 = 25 - 15
            dsm_penalty2 = value2*0.5
            value3 = 35-25
            dsm_penalty3 = value3*1.0
            value4 = absolute_error - 35
            dsm_penalty4 = value4*1.5
            dsm_penalty = dsm_penalty1 + dsm_penalty2 + dsm_penalty3 + dsm_penalty4
        if plant.get_client().id == 890:
            return (dsm_penalty*capacity_factor)/(100*4)
        else:
            return (dsm_penalty*capacity_factor)/100
    except Exception as exception:
        print str(exception)
        return 0

def calculate_penalty(starttime, endtime, plant, actual=False):
    try:
        day_ahead_stream = 'GBM_DAY_AHEAD_SOLCAST' if plant.get_client().id == 890 else 'STATISTICAL_DAY_AHEAD'
        latest_stream = 'STATISTICAL_LATEST_BONSAI_MERGED' if plant.get_client().id == 890 else 'STATISTICAL_LATEST'

        if actual==True:
            day_ahead_predicted_values = get_actual_and_latest_predicted_values(starttime, endtime, plant, day_ahead_stream, 900)
            return json.loads(day_ahead_predicted_values.to_json(orient='records', date_format='iso'))
        else:
            penalty_df = pd.DataFrame()
            actual_values = get_actual_and_latest_predicted_values(starttime, endtime, plant, 'ACTUAL', 900)
            latest_predicted_values = get_actual_and_latest_predicted_values(starttime, endtime, plant, latest_stream, 900)
            day_ahead_predicted_values = get_actual_and_latest_predicted_values(starttime, endtime, plant, day_ahead_stream, 900)
            if penalty_df.empty:
                penalty_df = actual_values
            else:
                penalty_df = penalty_df.merge(actual_values.drop_duplicates('timestamp'), on='timestamp', how='outer')
            if penalty_df.empty:
                penalty_df = latest_predicted_values
            else:
                penalty_df = penalty_df.merge(latest_predicted_values.drop_duplicates('timestamp'), on='timestamp', how='outer')
            if penalty_df.empty:
                penalty_df = day_ahead_predicted_values
            else:
                penalty_df = penalty_df.merge(day_ahead_predicted_values.drop_duplicates('timestamp'), on='timestamp', how='outer')

            # check for adani plants and check if the plant is not bbagewadi
            # if so the values of ACTUAL and DAY_AHEAD would be in energy convert to power
            if plant.get_client().id == 890 and plant.id != 894:
                # convert the actual stream to power
                penalty_df['ACTUAL'] = penalty_df['ACTUAL'] * 4
                # convert the day ahead stream to power
                penalty_df[day_ahead_stream] = penalty_df[day_ahead_stream] * 4
                #########################################################################################
                # Now that since all the streams of adani are in power below steps doesnt need to change
                #########################################################################################
            # uncomment for testng.
            #print("calculate_penalty() printing the Dataframe after the calculation")
            #from datetime import time
            #print(penalty_df[(penalty_df['timestamp'].dt.time > time(0,0)) & (penalty_df['timestamp'].dt.time < time(14,0))].head(100))

            capacity_factor = float(plant.capacity) if plant.get_client().id == 890 else float(plant.capacity)/4
            penalty_df['difference'] = penalty_df['ACTUAL']-penalty_df[latest_stream]
            penalty_df['absolute_error'] = (abs(penalty_df['ACTUAL']-penalty_df[latest_stream])/capacity_factor)*100
            penalty_df['dsm_penalty'] = penalty_df['absolute_error'].apply(lambda x : calculate_dsm_penalty(plant, x))
            penalty_df['normalized_dsm_penalty'] = penalty_df['dsm_penalty'].apply(lambda x : (x*1000)/float(plant.capacity))
            #penalty_df = penalty_df.dropna()
            penalty_df = penalty_df.fillna(0)
            penalty_df = penalty_df.sort_values('timestamp')
            error_df = penalty_df[penalty_df['absolute_error']>15]
            penalty_hours = (error_df.shape[0])*15/60
            penalty_error = (float(error_df.shape[0])/float(penalty_df.shape[0]))*100
            prediction_error = (abs(penalty_df[latest_stream].sum()-penalty_df['ACTUAL'].sum())/(capacity_factor*penalty_df.shape[0]))*100

            penalty_df = penalty_df.rename(columns={day_ahead_stream: 'STATISTICAL_DAY_AHEAD',
                                                    latest_stream: 'STATISTICAL_LATEST'})

            if plant.get_client().id == 890:
                # show in MW not in KW for adani
                penalty_df['ACTUAL'] = penalty_df['ACTUAL'] / 1000
                penalty_df['STATISTICAL_DAY_AHEAD'] = penalty_df['STATISTICAL_DAY_AHEAD'] / 1000
                penalty_df['STATISTICAL_LATEST'] = penalty_df['STATISTICAL_LATEST'] / 1000
                penalty_df['difference'] = penalty_df['difference'] / 1000

                error_df['ACTUAL'] = error_df['ACTUAL'] / 1000
                error_df['GBM_DAY_AHEAD_SOLCAST'] = error_df['GBM_DAY_AHEAD_SOLCAST'] / 1000
                error_df[latest_stream] = error_df[latest_stream] / 1000
                error_df['difference'] = error_df['difference'] / 1000


            final_result = {}
            final_result['penalty_hours'] = penalty_hours
            final_result['penalty_error'] = penalty_error
            final_result['prediction_error'] = prediction_error
            final_result['total_dsm_penalty'] = penalty_df['dsm_penalty'].sum()
            final_result['total_normalized_dsm_penalty'] = penalty_df['normalized_dsm_penalty'].sum()
            final_result['total_values'] = json.loads(penalty_df.to_json(orient='records', date_format='iso'))
            final_result['error_values'] = json.loads(error_df.to_json(orient='records', date_format='iso'))
            daily_penalty_df = pd.DataFrame()
            daily_penalty_df['timestamp'] = penalty_df['timestamp']
            daily_penalty_df['dsm_penalty'] = penalty_df['dsm_penalty']
            daily_penalty_df = daily_penalty_df.set_index('timestamp')
            normalized_daily_penalty_df = pd.DataFrame()
            normalized_daily_penalty_df['timestamp'] = penalty_df['timestamp']
            normalized_daily_penalty_df['normalized_dsm_penalty'] = penalty_df['normalized_dsm_penalty']
            normalized_daily_penalty_df = normalized_daily_penalty_df.set_index('timestamp')
            aggregation = '1D'
            if not daily_penalty_df.empty:
                daily_dsm_penalty_data = []
                grouped = daily_penalty_df.groupby(pd.TimeGrouper(aggregation))
                penalty_values = grouped.sum()
                for key, value in penalty_values["dsm_penalty"].iteritems():
                    try:
                        if not math.isnan(value):
                            daily_dsm_penalty_data.append({'timestamp': key.strftime('%Y-%m-%dT%H:%M:%SZ'), 'dsm_penalty': value})
                        else:
                            pass
                    except:
                        continue
            final_result["daily_dsm_penaly"] = daily_dsm_penalty_data
            if not normalized_daily_penalty_df.empty:
                normalized_daily_dsm_penalty_data = []
                grouped = normalized_daily_penalty_df.groupby(pd.TimeGrouper(aggregation))
                normalized_penalty_values = grouped.sum()
                for key, value in normalized_penalty_values["normalized_dsm_penalty"].iteritems():
                    try:
                        if not math.isnan(value):
                            normalized_daily_dsm_penalty_data.append({'timestamp': key.strftime('%Y-%m-%dT%H:%M:%SZ'), 'normalized_dsm_penalty': value})
                        else:
                            pass
                    except:
                        continue
            final_result["daily_dsm_penaly"] = daily_dsm_penalty_data
            final_result["normalized_daily_dsm_penaly"] = normalized_daily_dsm_penalty_data
            return final_result
    except Exception as exception:
        print("Exception in calculating penalty : " + str(exception))
        return {}

def get_grid_down_time_dsm(starttime, endtime, plant):
    try:
        final_result = {}
        if plant.get_client().slug == "adani":
            delta = 15.0
        else:
            delta = 5.0
        energy_values = get_plant_power(starttime, endtime, plant, True, True, False, True, False, False, False)
        final_energy_values = pd.DataFrame()
        final_energy_values['timestamp'] = energy_values['timestamp']
        final_energy_values['sum'] = energy_values['sum']
        final_energy_values = final_energy_values.sort('timestamp')
        irradiation_values = get_irradiation_data(starttime, endtime, plant)
        irradiation_values = irradiation_values[irradiation_values['irradiation']>0]
        irradiation_values = irradiation_values.sort('timestamp')
        final_df = final_energy_values.merge(irradiation_values.drop_duplicates('timestamp'), on='timestamp', how='outer')
        final_df = final_df.dropna()
        final_df = final_df.drop(['irradiation'],axis=1)
        df = pd.DataFrame()
        df['ts'] = (final_df['timestamp'].diff(-1))*-1
        df['sum'] = (final_df['sum'].diff(-1))*-1
        df['timestamp'] = final_df['timestamp']
        df = df.dropna()
        df = df.set_index('timestamp')
        df = df.between_time(start_time='00:00', end_time='14:30')
        df = df.reset_index()
        df_missing_data = df[(df['ts']/np.timedelta64(1, 'm'))>delta]
        df_missing_data = df_missing_data[(df_missing_data['ts']/np.timedelta64(1, 'm'))<600]
        df_missing_data['ts'] = df_missing_data['ts']/np.timedelta64(1, 'm')
        df_missing_data = df_missing_data.drop(['sum'], axis=1)
        df_grid_down = df[df['sum']==0.0]
        df_grid_down = df_grid_down[(df_grid_down['ts']/np.timedelta64(1, 'm'))<600]
        df_grid_down['ts'] = df_grid_down['ts']/np.timedelta64(1, 'm')
        df_grid_down = df_grid_down.drop(['sum'], axis=1)
        final_result['missing_data_timestamp'] = json.loads(df_missing_data.to_json(orient='records', date_format='iso')) if df_missing_data.shape>0 else []
        final_result['grid_down_timestamp'] = json.loads(df_grid_down.to_json(orient='records', date_format='iso')) if df_grid_down.shape>0 else []
        return final_result
    except Exception as exception:
        print str(exception)