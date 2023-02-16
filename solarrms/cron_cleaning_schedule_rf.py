############################################################################################
# Imports
############################################################################################
# Dataglen imports
from dataglen.models import ValidDataStorageByStream
from solarrms.models import SolarPlant,IndependentInverter,PredictedValues
from helpdesk.dg_functions import create_ticket
from helpdesk.models import Queue, Ticket
from solarrms.cron_new_tickets import close_ticket
# Django imports
from django.utils import timezone
from django.conf import settings
# Python imports
from datetime import  datetime,timedelta
import pytz
from copy import copy
import os
import pickle
# scikit learn imports
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.externals import joblib
from sklearn.tree import export_graphviz
import pydot


############################################################################################
# Variables change here if needed
############################################################################################
# Testing showed this gave proper results than 90 / 120 days..
TRAINING_DAYS=60
# Plant Production Starting hour and ending hour...
PROD_START_HOUR = 6
PROD_END_HOUR = 18
CLEANING_ERROR_THRESHOLD = 0.15
MIN_POINTS_PER_DAY = 30
FITS_DIR = '/usr/local/lib/cleaning/'

DEFAULT_STREAMS= ['IRRADIATION','MODULE_TEMPERATURE']

# Below are the plants for which IRRADIATION  / MODULE_TEMPERATURE are not the stream names..
EXCEPTION_PLANTS= {
    'waaneep': ['AMBIENT_TEMPERATURE','IRRADIATION'],
    'palladam': ['MODULE_TEMPERATURE','EXTERNAL_IRRADIATION'],
    'yerangiligi': ['IRRADIATION'],
    'kmrlibldepo': ['IRRADIATION'],
    'kmrlmuttommetrostation': ['IRRADIATION'],
    'kmrlpulinchodumetrostation': ['IRRADIATION'],
    'mohanestate': ['IRRADIATION','AMBIENT_TEMPERATURE'],
    'gupl': ['IRRADIATION','MODULE_TEMPERATURE','AMBIENT_TEMPERATURE'],
    'omya': ['EXTERNAL_IRRADIATION','MODULE_TEMPERATURE']
}


# Below are the plants for which cleaning needs to be done.
PLANTS = {'waaneep', 'palladam', 'dominicus', 'airportmetrodepot', 'ranergy', 'rbl', 'ranetrw', 'yerangiligi', 'gmr',
          'immigrationbuilding', 'rafcoimbatore', 'aaykarbhawan', 'adminblockbbmb', 'avonispat', 'avonispat2', 'bhu',
          'centralcustom', 'centralexcise', 'cfti', 'cgocomplex', 'customhouse', 'delhihaat', 'derasachasauda', 'dtu',
          'eastman', 'gmhs', 'gmhssec45c', 'gmhs1', 'gmhs2', 'gsi2', 'gsinagpur', 'gsss', 'hmchalol', 'ibmindirabhawan',
          'ibmpilot', 'igdtuw', 'iicpt', 'institutefortheblinds', 'jnarddc', 'jnpt', 'kaleeswarar', 'kmrlibldepo',
          'kmrlmuttommetrostation', 'kmrlpulinchodumetrostation', 'nariniketan', 'ncdccollege', 'nsbuilding', 'nsit',
          'obchb', 'oldchairmanoffice', 'ordinancefactory', 'pioneerspinnermill', 'pratyakshkarbhawan', 'rgniyd', 'rie',
          'rsv', 'seniorcitizenhome', 'sch', 'sscbs', 'tankno1cap1mgtankno1cap2mgmcphlab2mwwaterworks', 'tscsl',
          'unani', 'vtcashakiran', 'akshardham', 'hacgocomplex', 'councilhouse', 'dgcis', 'ezcc', 'gisochurchlane',
          'goiformstoretemplestreet', 'goipresssantragachi', 'gsi', 'hyderabadhouse', 'nizampalace',
          'oldjnuclubbuilding', 'oldjnulibraryandclubbuilding', 'rashtrapatibhawanauditorium', 'sardarpatelbhawan',
          'shramsaktibhawan', 'rswm', 'demo', 'demo1', 'pavagada', 'mohanestate', 'gupl', 'omya', 'parishirwal',
          'ultratechcementlimited', 'ultratechcementlimitedjhajjar', 'balajiirrigation', 'ballupur', 'shiningsunpower',
          'ccrtdwarka', 'gcgocomplex', 'cuh', 'dmrcanandvihar115kwp', 'dmrcmetroenclave50kwp', 'dmrcpragatimaidan85kwp',
          'electronicsniketan', 'fsi100kwp', 'gjustuniversity', 'governmentofindiapress180kwp',
          'governmentofindiapress30kwp', 'igncajnapath', 'iiwbrkarnal', 'jppllalitpur', 'jppl1', 'jppl2',
          'krishibhavanrajpath200kwp', 'loknayakbhawan90kwp', 'maharashtrasadan150kwp', 'mdu', 'mtnl80kwp',
          'nacen200kwp', 'nehrumemorialmuseumlibrarynmml', 'nirmanbhawan200kwp', 'rmlhospital', 'shastribhawan250kwp',
          'udyogbhavan208kwp', 'upsc100kwp', 'vigyanbhawan', 'ysc400kwp'}



#############################################################################################################################


# Function 1
# This function reads the data from cassandra and creates a dataframe and passes it on the parent function
'''
:params 
obj => object for which data needs to be retreived it can be a plant / inverter
device_type => just a string representing if the obj is a plant / inverter or any other thing
stream_names => list of streams for which data needs to be read
startdate => starttime datetime object
enddate =>endtime datetime object.
'''
def fetch_n_days_stream_data(obj,device_type,stream_names,startdate,enddate,aggregator='MINUTE',aggregation_period=15):
    try:
        # Set How the Data needs to be aggregated. By default keep it right now 15 mins.Change here to add hourly also for now proceed.
        aggregation = str(aggregation_period) + 'Min' if aggregator == 'MINUTE' else '15min'
        #Get the Sourcekey
        sourceKey = obj.metadata.sourceKey if device_type == 'PLANT' else obj.sourceKey
        print("fetch_n_days_stream_data() currently working on sourcekey >>> "+sourceKey+ " device type >>> "+device_type)
        # Final Dataframe which contains the result.
        final_df = pd.DataFrame()

        # Loop through each of the list.
        for stream in stream_names:
            print("fetch_n_days_stream_data() currently working on stream >>> " + stream)

            # Now get the Data from valid_data_storage for the stream being passed.
            device_data = ValidDataStorageByStream.objects.filter(source_key=sourceKey,
                                                                   stream_name=stream,
                                                                   timestamp_in_data__gte=startdate,
                                                                   timestamp_in_data__lte=enddate).\
                limit(0).order_by('timestamp_in_data').values_list('timestamp_in_data', 'stream_value')

            # Try to convert it to a dataframe
            try:
                # try to convert it to a dataframe..
                device_df = pd.DataFrame(device_data[:], columns=['timestamp_in_data', 'stream_value'])
                # rename the power_df columns
                device_df.rename(columns={'timestamp_in_data': 'timestamp','stream_value':stream.lower()}, inplace=True)
                # Replace the seconds and microseconds part to zero..
                device_df['timestamp'] = device_df['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                # convert stream value field to a float
                device_df[stream.lower()] = device_df[stream.lower()].astype(float)
                # Groupby hourly for now
                device_df = device_df.set_index('timestamp').groupby(pd.TimeGrouper(freq=aggregation)).mean().reset_index()
                #TODO Add 15 mins after the  grouping check if this right for plants getting 15 mins interval already..
                if aggregation_period !=60:
                    device_df['timestamp'] = device_df['timestamp'] + pd.Timedelta(minutes=aggregation_period)
            except Exception as e:
                print("fetch_n_days_stream_data() Exception occured while converting device data in to a Dataframe.. "+str(e))
                device_df = pd.DataFrame()

            print("fetch_n_days_stream_data() Printing the head/tail for the stream >>> "+stream)
            print(device_df.head())
            print(device_df.tail())

            # Perform the merging of the dataframes.
            final_df = device_df if final_df.empty else final_df.merge(device_df, on='timestamp', how='inner')

        # return the final dataframe
        return final_df
    except Exception as e:
        print("fetch_n_days_stream_data() Generic Exception raised in the function please check it and fix it"+str(e))
        return pd.DataFrame()



# Function 2
# This function basically merges the features and label dataframes.
'''
feature_df => dataframe containing the features which will be used for prediction
label_df => dataframe containing the target parameter.
'''
def merge_feature_label_df(plant,feature_df,label_df,today):
    try:
        # Merge both the dataframe
        merged_df = pd.merge(label_df, feature_df, how='inner', on='timestamp')

        # Convert the timestamp to datetime and the data from cassandra comes in UTC convert to Asia/Kolkata
        merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp']).dt.tz_localize('UTC').dt.tz_convert(plant.metadata.plantmetasource.dataTimezone)

        # Filter only those data which are > 6 and < 18
        merged_df = merged_df[(merged_df['timestamp'].dt.hour >= PROD_START_HOUR) &
                            (merged_df['timestamp'].dt.hour <= PROD_END_HOUR)]

        # remove those which has na
        merged_df.dropna(inplace=True)

        # Filter only those days which has enough data in it.
        merged_df['date'] = merged_df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d'))

        # find the number of records  per date
        merged_df = pd.merge(merged_df,merged_df.groupby(['date']).size().reset_index(name='counts'),on='date',how='inner')

        # Filter out those rows which have < MIN_POINTS_PER_DAY
        merged_df = merged_df[merged_df['counts']>=MIN_POINTS_PER_DAY]

        # check if today entry has enough rows in it.
        print("merge_feature_label_df() todays date is >>> "+today.strftime('%Y-%m-%d'))
        if merged_df[merged_df['date']== today.strftime('%Y-%m-%d')].shape[0] >= MIN_POINTS_PER_DAY:
            # drop the date column as its no longer needed.
            merged_df.drop(['date','counts'],axis=1,inplace=True)
            return merged_df
        else:
            print(merged_df[merged_df['date']== today.strftime('%Y-%m-%d')].head(1000))
            print("merge_feature_label_df() Todays data has less than "+str(MIN_POINTS_PER_DAY)+"points in the Dataframe.Not enough data hence skipping")
            return pd.DataFrame()

    except Exception as e:
        print("merge_feature_label_df() raised an exception pplease correct it"+str(e))
        return pd.DataFrame()




# Function 3
# This function splits the dataframe in to Features / labels which can be used for furthur processing
# It doesnt return a dataframe but return features / labels as numpy arrays...
def feature_label_split(device_df):
    try:
        # get the slot
        device_df['slot'] = (device_df['timestamp'].dt.hour * 60 ) + device_df['timestamp'].dt.minute
        # not required for now
        # features['minute'] = features['timestamp'].dt.minute

        # drop the timestamp field as its not required now
        device_df = device_df.drop('timestamp', axis=1)

        # Labels are the values we want to predict
        labels = np.array(device_df['active_power'])

        # Remove the labels from the features
        # axis 1 refers to the columns
        device_df = device_df.drop('active_power', axis=1)

        # Saving feature names for later use
        # feature_list = list(features.columns)

        # Convert to numpy array
        features = np.array(device_df)

        print('feature_label_split() Full dataset Features Shape >>> ' + str(features.shape))
        print('feature_label_split() Full dataset Labels Shape >>> ' + str(labels.shape))

        # return the labels
        return features, labels
    except Exception as e:
        print('feature_label_split() raised an Exception please checck it '+str(e))



# Function 4
# This function basically splits the dataset in to training and test dataset..
def train_test_array_split(features,labels,test_size=0.25):

    # Split the data into training and testing sets
    train_features, test_features, train_labels, test_labels = train_test_split(features, labels, test_size = 0.25,random_state = 42)

    # Show the shape of the numpy array after the split
    print('Training Features Shape >>> '+ str(train_features.shape))
    print('Training Labels Shape >>> '+ str(train_labels.shape))
    print('Testing Features Shape >>> '+ str(test_features.shape))
    print('Testing Labels Shape >>> ' + str(test_labels.shape))

    # return the training and test dataset..
    return train_features,test_features,train_labels,test_labels



# Function 5
# Function which basically fits and returns the classifier
def classifier(features,labels,plant_obj,device_obj):
    try:
        # prepare the pickle file name
        filename = plant_obj.slug+'-'+device_obj.displayName+'.sav'
        # prepare the full path
        filepath = FITS_DIR.rstrip("/")+"/"+filename
        print("classifier() full path of the file is >>> "+filepath)
        # checck if today is a sunday.
        if timezone.now().weekday() == 6 or not os.path.exists(filepath):

            print("classifier() recreating the model and pickling it"+str(timezone.now()))
            # Instantiate model
            # below values are set from the output of the gridsearchcv parmameters
            rf = RandomForestRegressor(n_estimators=250, random_state=42,n_jobs=4,max_depth=12)

            # Train the model on training data
            rf.fit(features, labels)

            # serialize the model into a file
            #pickle.dump(rf, open(filepath, 'wb'),-1)
            joblib.dump(rf, filepath)
        else:
            print("classifier() reading from the existing classifier")
            #rf = pickle.load(open(filepath, 'rb'))
            rf = joblib.load(filepath)

        # returns the classifier
        return rf
    except Exception as e:
        print("classifier() raised an Exception please check"+str(e))



# Function 6
# Function which returns residuals along with the accuracy
# labels are the actual expected output
def performance_metrics(rf, features, labels):

    # Use the forest's predict method on the test data
    predictions = rf.predict(features)

    # Calculate the absolute errors
    errors = predictions - labels

    # Print out the mean absolute error
    mae = np.mean(errors)
    print('performance_metrics() Mean Absolute Error >>> '+str(mae) +' degrees.')

    # Calculate mean absolute percentage error (MAPE)
    mape = 100 * (errors / labels)

    print("performance_metrics() Number of Infinite entries are >>>> " + str(len(mape[mape == np.inf])))
    # Replace infinity with zero
    mape[mape == np.inf] = 0
    # Replace nan with zero.
    mape[np.isnan(mape)] = 0

    # Calculate and display accuracy
    accuracy = 100 - np.mean(mape)
    print('performance_metrics() Accuracy >>> '+str(round(accuracy, 2)))
    return predictions,mae,accuracy



# Function 7
# Small function which basically checks for Nan
def NAN_check(*args):
    #print(args)
    NAN_list = []
    for array in args:
        #print(array)
        # array.size gives total numberr of elements in array..
        numpy_array = array.reshape(array.size,1)
        # convert the elements in to a floating piint objects
        final_array = numpy_array.astype(np.float64, copy=False)
        # find if there is any nan in the numpy array if so append true.
        NAN_list.append(np.isnan(final_array).any())
    return NAN_list





# Function 8
# calculate cleaning residuals
def calculate_cleaning_residuals(final_df,device_obj,plant_obj):
    try:
        # Split the dataframe in to features and labels.
        features, labels = feature_label_split(final_df)
        print("calculate_cleaning_residuals() Printing the first three elements of the features and labels numpy array..")
        print(features[1:3])
        print(labels[1:3])
        print("calculate_cleaning_residuals() Check for NAN in Numpy arrays")
        print(NAN_check(features, labels))

        # Fit the model using full data
        full_data_classifier = classifier(features, labels,plant_obj,device_obj)
        # Pull out one tree from the forest
        #tree = full_data_classifier.estimators_[10]
        # Export the image to a dot file
        #export_graphviz(tree, out_file = '/home/dgadmin/'+plant_obj.slug+'-'+device_obj.displayName+'.dot',feature_names=['irrad','mod_temp','slot'])

        print("calculate_cleaning_residuals() Running Full Dataset Classifier against Full dataset")
        full_predictions, mae, accuracy = performance_metrics(full_data_classifier, features, labels)
        # Add the predictions to the dataframe
        final_df['predicted_power'] = full_predictions


        # calculate the residuals
        final_df['residuals'] = final_df['active_power'] - final_df['predicted_power']
        print("calculate_cleaning_residuals() printing the head/tail after calculating the residuals.")
        print(final_df.head())

        # Get the Inverters Caparity information
        inverter_capacity = 0
        try:
            inverter_capacity = device_obj.actual_capacity if device_obj.actual_capacity else device_obj.total_capacity
            print("calculate_cleaning_residuals() Inverter capacity found is >>>> "+str(inverter_capacity))
        except Exception as e:
            print("calculate_cleaning_residuals() exception raised while getting Inverter information " + str(e))

        # Find the percentage of residuals
        if inverter_capacity > 0:
            final_df['percent_residuals'] = abs(final_df['residuals'] / inverter_capacity)
            # filter based on the cleaning error threshold
            final_df = final_df[final_df['percent_residuals'] < CLEANING_ERROR_THRESHOLD]
            print("calculate_cleaning_residuals() printing the head/tail after calculatng the  percentage residuals.")
            print(final_df.head())

            # TODO check if 15 mins predicted power needs to be added to cassandra if so handle it here.

            # Save the Dataframe as the CSV File for dashboarding Remove after testing is done
            # final_df.to_csv('/home/dgadmin/rbl/' + plant_obj.slug + '-' + device_obj.displayName + '.csv', index=False,header=True)

            # aggregate per day
            final_df = final_df.set_index('timestamp').groupby(pd.TimeGrouper(freq='1D', base=0)).sum().reset_index()
            # Get only the required columns
            final_df = final_df[['timestamp', 'active_power', 'predicted_power', 'residuals', 'percent_residuals']]
            #final_df['residual_plantcapacity'] = final_df['residuals'] / (inverter_capacity*52)
            #final_df['residual_predicted_power'] = final_df['residuals'] /final_df['predicted_power']

            final_df = final_df[final_df['active_power']>0]
            final_df = final_df[final_df['percent_residuals'] < 2 ]
            # calculate the losses
            positive_residual_df = final_df[final_df['residuals'] > 0]
            # calculate the loss threshold
            loss_threshold = positive_residual_df['residuals'].mean() if positive_residual_df.shape[0] > 0 else 0
            # calculate the losses
            final_df['losses'] = loss_threshold - final_df['residuals']
            # drop na
            final_df.dropna(inplace=True)
            print("calculate_cleaning_residuals() printing the head/tail after calculatng the  losses / residuals per day")
            print(final_df.head(500))

            # trend reset
            #final_df = final_df.set_index('timestamp').resample('D').mean().reset_index().fillna(0)
            #final_df['residuals'] = residual_trend_reset(final_df['residuals'].tolist())
            #final_df = final_df[final_df['residuals'] != 0]
            #print("calculate_cleaning_residuals() printing after trend reset")
            #print(final_df.head(10000))

            # Handle prediction result.
            save_cleaning_schedule(final_df,device_obj,plant_obj,check_and_update=False)

        else:
            print("cleaning_schedule() invertercapacity is zero hence skipping >>> " + device_obj.sourceKey)

    except Exception as e:
        print("calculate_cleaning_residuals() Generic exception occured "+str(e))


# Function 9
# Normalize the trend.
def residual_trend_reset(residual_list):
    try:
        # Now loop through each of the residuals and normalist
        for currRow in range(1, len(residual_list)-1):
            # if current row is positive and the previous and next row is negative
            if residual_list[currRow] > 0 and residual_list[currRow+1] < 0 and residual_list[currRow-1] < 0:
                residual_list[currRow] = -residual_list[currRow]
            elif residual_list[currRow] < 0 and residual_list[currRow+1] > 0 and residual_list[currRow-1] > 0:
                residual_list[currRow] = abs(residual_list[currRow])
        print(residual_list)
        return residual_list
    except Exception as e:
        print("residual_trend_reset() raised an Exception .. Please check "+str(e))


# Function 10
# Basically inserts an Entry in to Cassandra..
def save_cleaning_schedule(final_df,device_obj,plant_obj,check_and_update=True):
    try:
        model_name = 'regression'
        stream_name = 'cleaning'
        plant_name = plant_obj.slug + "-" + device_obj.name
        # Now loop through each of the rows in the dataframe and insert it in to cassandra.
        for index, row in final_df.iterrows():
            #print(row['timestamp'])
            if check_and_update == True:
                try:
                    predict = PredictedValues.objects.get(
                            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                            count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                            identifier = plant_name,
                            stream_name = stream_name,
                            ts = row['timestamp'])

                except PredictedValues.DoesNotExist:
                    predict = PredictedValues.objects.create(
                            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                            count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                            identifier = plant_name,
                            stream_name = stream_name,
                            model_name = model_name,
                            actual_value = row['active_power'],
                            predicted_value = row['predicted_power'],
                            residual  = row['residuals'],
                            residual_sum=row['residuals'],
                            losses = row['losses'],
                            ts = row['timestamp'],
                            updated_at = timezone.now() )
                    predict.save()

                    print("save_cleaning_schedule() new value inserted in to cassandra database >>> "+str(predict))

                except Exception as ex:
                    print("save_cleaning_schedule() Exception in creating new predict record: " + str(ex))

            else:
                predict = PredictedValues.objects.create(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=plant_name,
                    stream_name=stream_name,
                    model_name=model_name,
                    actual_value=row['active_power'],
                    predicted_value=row['predicted_power'],
                    residual=row['residuals'],
                    residual_sum=row['residuals'],
                    losses=row['losses'],
                    ts=row['timestamp'],
                    updated_at=timezone.now())
                predict.save()

                print("save_cleaning_schedule() new value inserted in to cassandra database >>> " + str(predict))

    except Exception as ex:
        print("save_cleaning_schedule() Exception occured while saving predictions : %s %s", str(ex), str(timezone.now()))




# Function 11
# helper function to print the decision tree.
def explore_tree(estimator,feature,threshold,X,feature_names,sample_id=0):

    # get the decision path of all the features # node_indicator is a sparse matrix.
    node_indicator = estimator.decision_path(X)
    # get the nodes through which the sample passes through in the tree.
    node_index = node_indicator.indices[node_indicator.indptr[sample_id]:node_indicator.indptr[sample_id + 1]]
    # leaf id's
    leaf_ids = estimator.apply(X)
    # for each node in the node_index
    for node_id in node_index:
        if leaf_ids[sample_id] == node_id:
            print("==> Predicted leaf index")
        if (X[sample_id, feature[node_id]] <= threshold[node_id]):
            threshold_sign = "<="
        else:
            threshold_sign = ">"

        print("decision id node %s : (features[%s, '%s'] (Condition : %s %s %s)"% (node_id,sample_id,
                    feature_names[feature[node_id]],X[sample_id, feature[node_id]],threshold_sign,threshold[node_id]))



# Function 12
# This function is a helper function this basically prints the path followed by indivial tree in the forest.
# This function also prints the individual tree's prediction.
# Pass in the plant
def random_forest_debugger(final_df,slot_index,feature_names_list,plant_obj,device_obj,PRINT_DECISION_PATH=False):
    # Split the dataframe in to features and labels.
    features, labels = feature_label_split(final_df)
    print("random_forest_debugger() Check for NAN in Numpy arrays")
    print(NAN_check(features, labels))
    # Fit the model using full data
    full_data_classifier = classifier(features, labels,plant_obj,device_obj)

    if PRINT_DECISION_PATH == True:
        # calculate the nodes left children / right children etc..
        n_nodes_ = [t.tree_.node_count for t in full_data_classifier.estimators_]
        # List of numpy arrays
        children_left_ = [t.tree_.children_left for t in full_data_classifier.estimators_]
        # List of Numpy arrays
        children_right_ = [t.tree_.children_right for t in full_data_classifier.estimators_]
        feature_ = [t.tree_.feature for t in full_data_classifier.estimators_]
        threshold_ = [t.tree_.threshold for t in full_data_classifier.estimators_]

        # estimator,feature,threshold,X,feature_names,sample_id=0
        for i, e in enumerate(full_data_classifier.estimators_):
            print("\nTree %d" % i)
            explore_tree(full_data_classifier.estimators_[i], feature_[i], threshold_[i], features, sample_id=slot_index,
                         feature_names=feature_names_list)


    # print the prediction of each of the estimator here..
    prediction_list = []
    for estimator in full_data_classifier.estimators_:
        #print("Prediction for sample %d: %s" % (sample_id, estimator.predict(features)[sample_id]))
        prediction_list.append(estimator.predict(features)[slot_index])
    print("\n\nrandom_forest_debugger() Printing the predictions of each tree in the forest..")
    print(prediction_list)



# Function 13
# helper function for debugging.
def rf_debugger_helper(plant_name='omya',inverter_source_key='WM3boKR2p7gmaN8',slot='2018-03-23 11:00:00',today = timezone.now()-timedelta(days=1)):
    # get the plant object
    plant=SolarPlant.objects.get(slug=plant_name)
    # get the Inverter object
    inverter = IndependentInverter.objects.get(sourceKey=inverter_source_key)
    # Compute the endtime..
    enddate = today.astimezone(pytz.timezone(plant.metadata.dataTimezone))
    # Compute the starttime..
    startdate = enddate - timedelta(days=TRAINING_DAYS)
    # Get the Stream names for the plant
    stream_names = copy(EXCEPTION_PLANTS[plant.slug]) if plant.slug in EXCEPTION_PLANTS.keys() else copy(DEFAULT_STREAMS)
    # Localize the slot to plant timezone..
    local_tz = pytz.timezone('Asia/Kolkata')
    final_slot = local_tz.localize(datetime.strptime(slot, '%Y-%m-%d %H:%M:%S'))

    # call the random forest debugger
    # Call the function which returns the plant level data leave aggregation to 15 minutes for now.
    feature_df = fetch_n_days_stream_data(plant, 'PLANT', stream_names, startdate, enddate)
    # get the lable df
    label_df = fetch_n_days_stream_data(inverter, 'INVERTER', ['ACTIVE_POWER'], startdate, enddate)
    # append slot to the feature
    stream_names.append('SLOT')
    # if both are not empty join them.
    if  not feature_df.empty and not label_df.empty:
        # inner join
        final_df = merge_feature_label_df(plant, feature_df, label_df, today)
        # print the head of the dataframe...
        print(final_df.head())
        # get the index location for which
        index_list = final_df.index[final_df['timestamp']==final_slot].tolist()
        if len(index_list) == 1:
            random_forest_debugger(final_df, index_list[0],stream_names ,plant,inverter,PRINT_DECISION_PATH=True)
        else:
            print("rf_debugger_helper() >>>>> Invalid slot specified proceeding ahead with the default slot of ZERO")
            random_forest_debugger(final_df, 0,stream_names, plant,inverter,PRINT_DECISION_PATH=False)



# Function 15
# main function which performs the cleaning..
def cleaning_schedule_latest(today = timezone.now()-timedelta(days=1)+timedelta(hours=2)):
    try:
        # Get all the plants for which cleaning needs to be done.issues just one query in mysql.
        #plants = SolarPlant.objects.filter(slug__in=['airportmetrodepot'])
        plants = SolarPlant.objects.filter(slug__in=PLANTS)
        # Now loop through each of the plants
        for plant in plants:
            try:
                # Compute the endtime..
                enddate = today.astimezone(pytz.timezone(plant.metadata.dataTimezone))
                # Compute the starttime..
                startdate = enddate - timedelta(days=TRAINING_DAYS)

                print("\n\n\ncleaning_schedule() todays time is >>> "+str(today))
                print("cleaning_schedule() Started working on plant >>> " + str(plant))
                print("cleaning_schedule() Computed start date is >>> " + str(startdate))
                print("cleaning_schedule() Computed end date is >>>> "+str(enddate))

                # Get all the Inverters for the plant.
                inverter_list = plant.independent_inverter_units.all()
                #inverter_list = [inverter_list[0]]

                # Get the stream names for the plant
                stream_names = copy(EXCEPTION_PLANTS[plant.slug]) if plant.slug in EXCEPTION_PLANTS.keys() else copy(DEFAULT_STREAMS)
                print("cleaning_schedule() Stream names got for the plant is >>>> "+str(stream_names))

                # Call the function which returns the plant level data leave aggregation to 15 minutes for now.
                feature_df = fetch_n_days_stream_data(plant,'PLANT',stream_names,startdate,enddate)
                #print("cleaning_schedule() Printing the head/tail after getting the features ")
                #print(feature_df.head())
                #print(feature_df.tail())

                if not feature_df.empty:
                    # Loop through each of the inverters of the plant
                    for inverter in inverter_list:
                        # printing the Inverter sourcekey
                        print("\n\ncleaning_schedule()  working on inverter with sourcekey >>> "+inverter.sourceKey+ " Device name >>>"+inverter.displayName)
                        # call the function which returns Inverter level data. Leave aggregation to 15 minutes for now..
                        label_df = fetch_n_days_stream_data(inverter,'INVERTER',['ACTIVE_POWER'],startdate,enddate)
                        print("cleaning_schedule() printing the head/tail after getting the labels")
                        print(label_df.head())
                        print(label_df.tail())

                        if not label_df.empty:
                            # Merge the feature and label dataframes.
                            final_df = merge_feature_label_df(plant,feature_df,label_df,enddate)

                            if not final_df.empty:
                                print("cleaning_schedule() printing the head/tail after combining features and labels")
                                print(final_df.head())
                                print(final_df.tail())

                                # call the function which calculates the residual for the dataframe.
                                calculate_cleaning_residuals(final_df,inverter,plant)

                            else:
                                print("cleaning_schedule() feature label merge code returned an Empty dataframe hence skipping >>>"+inverter.sourceKey)
                        else:
                            print("cleaning_schedule() label_df is empty skipping for inverter >>> "+inverter.sourceKey)
                else:
                    print("cleaning_schedule() feature_df is empty skipping for plant >>> "+plant.slug)

                # Call the function to create tickets..
                new_create_cleaning_ticket(str(plant.slug), 'cleaning')

            except Exception as e:
                print("cleaning_schedule() Exception occured for plant >>> "+plant.slug+" " +str(e))
    except Exception as e:
        print("cleaning_schedule() raised a generic Exception please correct the error "+str(e))



########################################################################################################################
# Ticket Creation Functions
########################################################################################################################

# Function 1
# This function is used to create a Incident ticket for PLANEL CLEANING
def create_panel_cleaning_ticket(plant, priority, due_date):
    try:
        ticket_name = "Cleaning of solar panels required : " + str(plant.location)
        ticket_description = 'The generation has been decreasing over past 3 days at ' + str(plant.location) + '. Hence, cleaning of solar panels are required. '
        event_type = "PANEL_CLEANING"
        open_comment = "Tickets created automatically based on the residual values of inverters."
        # Calling the function which creates the tickets
        new_panel_cleaning_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date,
                                                  ticket_name=ticket_name,
                                                  ticket_description=ticket_description,
                                                  open_comment=open_comment, event_type=event_type)
        return new_panel_cleaning_ticket
    except Exception as exception:
        print("create_panel_cleaning_ticket() error in creating panel cleaning ticket: " + str(exception))



# Function 2
# Function which create the ticket and its associations
# ticket => ticketassiociation => analyticassociation  tables in mysql will get updated.
def new_create_cleaning_ticket(plant_name, stream_name):
    try:
        # Get the plant object
        try:
            plant = SolarPlant.objects.get(slug=plant_name)
        except Exception as exception:
            print("new_create_cleaning_ticket() No plant found with name : " + str(plant_name))

        # Get all the inverters of the plant..
        inverters = plant.independent_inverter_units.all()
        panel_cleaning_inverters_dict = {}
        panel_cleaning_inverters_list = []

        # check if a queue is present for the plant.
        try:
            queue = Queue.objects.get(plant=plant)
        except Exception as exception:
            print ("new_create_cleaning_ticket() Queue does not exist for plant : " + str(plant.slug))

        # Loop through each of the Inverters of the plant..
        for inverter in inverters:
            panel_cleaning_list_temp = []

            # get the last 3 entry from the predicted table for this plant
            values = PredictedValues.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                                                    count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                    identifier=str(plant.slug)+'-'+str(inverter.name),
                                                    stream_name='cleaning').limit(3)

            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()


            if len(values) == 3 and inverter.total_capacity:
                # If the last three residual is negative generate ticket if it doesntexist r else update it
                if values[0].residual_sum< 0 and values[1].residual_sum < 0 and values[2].residual_sum < 0:
                    print("new_create_cleaning_ticket() Residuals are negative for the last three days for the plant >>> "+str(plant.slug))
                    panel_cleaning_inverters_list.append(str(inverter.sourceKey))
                    panel_cleaning_dict_temp = {}
                    panel_cleaning_dict_temp['st'] = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                    panel_cleaning_dict_temp['et'] = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
                    panel_cleaning_dict_temp['identifier'] = str(inverter.name)
                    panel_cleaning_dict_temp['residual'] = values[0].residual_sum
                    panel_cleaning_list_temp.append(panel_cleaning_dict_temp)
                    panel_cleaning_inverters_dict[str(inverter.sourceKey)] = panel_cleaning_list_temp

        print("new_create_cleaning_ticket() panel_cleaning_inverters_list list of Inverters for which tickets are being created/updated")
        print (panel_cleaning_inverters_list)
        # Below dictionary would be used to insert into analytic association table.
        print("new_create_cleaning_ticket()() panel_cleaning_inverters_dict dictionary associated with each Inverter")
        print(panel_cleaning_inverters_dict)

        # check if an open ticket exists for Panel Cleaning..
        panels_cleaning_ticket = Ticket.objects.filter(queue=queue, event_type='PANEL_CLEANING', status=1)
        if len(panels_cleaning_ticket)>0:
            # Ticket exists, update the association
            print("new_create_cleaning_ticket() Ticket exists /problem exists ..calling the function to update associations.")
            panels_cleaning_ticket[0].update_ticket_associations(panel_cleaning_inverters_list, performance_dict=panel_cleaning_inverters_dict)
            if len(panel_cleaning_inverters_dict)==0:
                print("new_create_cleaning_ticket() Ticket exists /problem does not exists ..calling the function to close_ticket")
                # Ticket exist, but the problem does not exist now, close the ticket
                close_ticket(plant=plant, ticket=panels_cleaning_ticket[0], request_arrival_time=timezone.now())
        elif len(panels_cleaning_ticket) == 0 and len(panel_cleaning_inverters_dict)>0:
            # Ticket does not exist,problem has occurred just now, create a new ticket.
            print("new_create_cleaning_ticket() Ticket doesnt exists /problem exists ..calling the function to create_ticket")
            new_panel_cleaning_ticket = create_panel_cleaning_ticket(plant, 1, None)
            new_panel_cleaning_ticket.update_ticket_associations(panel_cleaning_inverters_list, performance_dict=panel_cleaning_inverters_dict)
        else:
            pass
    except Exception as exception:
        print("Error in panel cleaning ticket : " + str(exception))
