import pandas as pd
from solarrms.api_views import update_tz
from solarrms.solar_reports import get_multiple_devices_single_stream_data
from dgkafka.views import create_kafka_producers
from solarrms.pvsyst_reports import get_list_of_days_per_month
import datetime
from calendar import monthrange
import calendar
from solarrms.models import SolarPlant, SolarField
import numpy as np

import logging

logger = logging.Logger('FS>>>')
logger.setLevel(logging.INFO)
print(logger)
print(logger.level)


# create a file handler
fh = logging.FileHandler('/var/log/kutbill/first_solar_druid_ingestion.log')



# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

logger.addHandler(fh)

def get_inverter_mod_temp_irr_data_in_df(plant,starttime,endtime):
    st = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
    et = update_tz(endtime, plant.metadata.plantmetasource.dataTimezone)

    df_result = pd.DataFrame()

    inverters = plant.independent_inverter_units.all()

    inverter_keys = inverters.values_list("sourceKey", flat=True)

    sf = SolarField.objects.get(source=inverter_keys[0], displayName="DC Power")
    df_inverters = get_multiple_devices_single_stream_data(st, et, plant, inverter_keys, sf.name)

    inv_name_sourekey_dict = {}
    for inv_sourcekey_list in inverters.values("sourceKey", "name"):
        sourcekey = inv_sourcekey_list["sourceKey"]
        inverter_name = inv_sourcekey_list["name"]
        inv_name_sourekey_dict[inverter_name] = sourcekey

    df_inverters = df_inverters.rename(columns=inv_name_sourekey_dict)

    sf = SolarField.objects.get(source="6gIOG1udZEDQNSE", displayName="Irradiation")
    df_irradiation = get_multiple_devices_single_stream_data(st, et, plant, ["6gIOG1udZEDQNSE"], sf.name)

    df_irradiation = df_irradiation.rename(columns={'FSINDIADEVCOLTD_Plant_Meta': 'IRRADIATION'})

    try:
        df_result = df_inverters.merge(df_irradiation, on='Timestamp', how='outer')
    except:
        df_inverters = df_inverters.rename(columns={'timestamp': 'Timestamp'})
        df_irradiation = df_irradiation.rename(columns={'timestamp': 'Timestamp'})
        df_result = df_inverters.merge(df_irradiation, on='Timestamp', how='outer')

    sf = SolarField.objects.get(source="6gIOG1udZEDQNSE", displayName="Module Temperature")
    df_mod_temp = get_multiple_devices_single_stream_data(st, et, plant, ["6gIOG1udZEDQNSE"], sf.name)
    df_mod_temp = df_mod_temp.rename(columns={'FSINDIADEVCOLTD_Plant_Meta': 'MODULE_TEMP'})

    try:
        df_result = df_result.merge(df_mod_temp, on='Timestamp', how='outer')
    except:
        df_mod_temp = df_mod_temp.rename(columns={'timestamp': 'Timestamp'})
        df_result = df_result.merge(df_mod_temp, on='Timestamp', how='outer')


    try:
        df_result['Timestamp'] = df_result['Timestamp'].dt.tz_localize('UTC').dt.tz_convert(plant.metadata.dataTimezone)
    except:
        df_result['Timestamp'] = df_result['timestamp'].dt.tz_localize('UTC').dt.tz_convert(plant.metadata.dataTimezone)

    df_result.fillna("", inplace=True)

    df_result = df_result.sort("Timestamp")
    # df_result = df_result.set_index('Timestamp')
    df_result.to_csv("first_solar2016.csv")
    return df_result

# df needs to have Timestamp column with timezone info
def send_df_to_kafka(df, plant, stream_name, device_type):
    try:
        df["Timestamp"]=df["Timestamp"].dt.tz_convert("UTC")
    except:
        pass
    plant_slug = plant.slug
    plant_id = plant.id
    client_slug = plant.groupClient.slug
    # df2 = df.reset_index()
    df_dict = df.to_dict(orient="records")
    kafka_producer = create_kafka_producers()[0]

    for item in df_dict:
        temp_range_str = ""
        if "Temperature_range" in item:
            temp_range_category = item.pop("Temperature_range")
            temp_range_str = "-".join([x.strip() for x in temp_range_category[1:-1].split(",")])
        irr_range_str = ""
        if "irr_range" in item:
            irr_range_category = item.pop("irr_range")
            irr_range_str = "-".join([x.strip() for x in irr_range_category[1:-1].split(",")])

            # irr_range = item['irr_range']

        timestamp = item.pop('Timestamp')
        iso_timestamp_in_data = str(timestamp.isoformat())
        for key, val in item.iteritems():
            if not np.isnan(val):
                payload_json_for_kafka = {}
                payload_json_for_kafka["timestamp_in_data"] = iso_timestamp_in_data
                payload_json_for_kafka["year"] = timestamp.year
                payload_json_for_kafka["month"] = timestamp.month
                payload_json_for_kafka["day"] = timestamp.day
                payload_json_for_kafka["hour"] = timestamp.hour
                payload_json_for_kafka["quarter"] = timestamp.quarter
                payload_json_for_kafka["weekofyear"] = timestamp.weekofyear

                payload_json_for_kafka["plant_slug"] = plant_slug
                payload_json_for_kafka["client_slug"] = client_slug

                payload_json_for_kafka["plant_id"] = plant_id

                payload_json_for_kafka["raw_value"] = val
                payload_json_for_kafka["stream_value"] = val

                payload_json_for_kafka["source_key"] = key
                payload_json_for_kafka["stream_name"] = stream_name
                payload_json_for_kafka["device_type"] = device_type
                if stream_name in ["ESTIMATED_IRR_COEFF","ESTIMATED_TEMP_COEFF"]:
                    payload_json_for_kafka["model_name"] = "MODEL_1_" + stream_name
                else:
                    if temp_range_str != "":
                        payload_json_for_kafka["model_name"] = temp_range_str
                    elif irr_range_str != "":
                        payload_json_for_kafka["model_name"] = irr_range_str
                    else:
                        payload_json_for_kafka["model_name"] = "MODEL_" + stream_name

                print payload_json_for_kafka
                logger.warning(str(payload_json_for_kafka))

                try:
                    kafka_producer.send_message(topic="druid_prod_metrics_topic",key = key, json_msg=payload_json_for_kafka, sync=True)
                    # kafka_producer.send_message(topic="druid_test_topic",key = key, json_msg=payload_json_for_kafka, sync=True)
                except Exception as ex:
                    print("Exception in data send_message: %s" % str(ex))
                    logger.warning("Exception in data send_message: %s" % str(ex))




# Filtering the data on basis of timestamp (Considering only between 11:00 am to 1:00 pm )
def timeFilter(df):
    list_time = []
    for i in range(df.shape[0]):
        hours = int(df['Timestamp'].iloc[i].hour)
        minutes = int(df['Timestamp'].iloc[i].minute)
        if (hours in [11, 12]):
            list_time.append(True)
        elif (hours == 13 and minutes == 0):
            list_time.append(True)
        else:
            list_time.append(False)

    return list_time

# Calculating actual DC power that will be generated if there will be no loss
def computePower(df, col_name):
    list_actual_power = []
    for i in range(df.shape[0]):
        # Adding temperature loss to the DC power (Assume temperature coefficient as -0.32%/degree C)
        P_temp = df[col_name].iloc[i] * (1 + ((df['MODULE_TEMP'].iloc[i] - 25) * 0.32 / 100))
        # Adding irradiation loss after adding temperature loss to the DC power(Assume irradiation to be linearly related to power)
        P_actual = P_temp / (df['IRRADIATION'].iloc[i])
        list_actual_power.append(P_actual)
        # print i," / " ,df.shape[0]

    # Returning the list of actual DC powers
    return list_actual_power

"""
Filter Conditions based on seasonality are 
Time : 11 AM to 1 PM
Jan, Feb, Oct, Nov, Dec 
Irradiation > 0.7
Module Temperature 55 to 60
March, April, May
Irradiation > 0.7
Module Temperature 60 to 70
June, July, Aug, Sep
Irradiation > 0.4
Module Temperature 40 to 55
"""
def filterData(df):
    month_names = df['month'].unique().tolist()
    month_names_new = []
    for month_name in month_names:
        df_new = df.loc[df['month'] == month_name]
        winter_season = ['January' , 'February' , 'October' , 'November' , 'December']
        summer_season = ['March','April','May']
        if month_name in winter_season:
            df_new1 = df_new[df_new.IRRADIATION > 0.7]
            df_new2 = df_new1[(df_new1.MODULE_TEMP >= 55) & (df_new1.MODULE_TEMP <= 60)]
            month_names_new.append(df_new2)
        elif month_name in summer_season:
            df_new1 = df_new[df_new.IRRADIATION > 0.7]
            df_new2 = df_new1[(df_new1.MODULE_TEMP >= 60) & (df_new1.MODULE_TEMP <= 70)]
            month_names_new.append(df_new2)
        else:
            df_new1 = df_new[df_new.IRRADIATION > 0.4]
            df_new2 = df_new1[(df_new1.MODULE_TEMP >= 40) & (df_new1.MODULE_TEMP <= 55)]
            month_names_new.append(df_new2)

    filtered_df = pd.concat(month_names_new)
    return filtered_df

def DCCapacityEstimator(solar_data):
    # renaming column names

    # Filtering the data on basis of timestamp (Considering only between 11:00 am to 1:00 pm )
    solar_data = solar_data[timeFilter(solar_data)]

    # Add Month to data frame
    solar_data['month'] = solar_data['Timestamp'].dt.month
    solar_data['month'] = solar_data['month'].apply(lambda x: calendar.month_name[x])

    # Add Month Number
    # solar_data['month_no'] = solar_data['Timestamp'].map(addMonthNum)

    # Filering data based on seasonality
    solar_df = filterData(solar_data)
    # getting list of inverters
    inverter_names = list(solar_df.columns)
    # Removing column names other than inverters names
    [inverter_names.remove(col) for col in ['IRRADIATION','Timestamp','MODULE_TEMP','month']]
    #creating new dataframe for estimated DC power
    solar_df1 = pd.DataFrame()
    solar_df1['Timestamp'] = solar_df['Timestamp']
    for name in inverter_names:
        # Appending actual_DC power column to the dataframe after adding all the losses to  each inverter DC Power Output
        solar_df1[name] = computePower(solar_df, name)
    solar_df1.to_csv("Output.csv", sep=',')
    return solar_df1



# Function to get estimated irradiation coefficient of all inverters
def TempAndIrrCoeffEstimator(solar_data,dc_capacity_dict):
    inverter_names = dc_capacity_dict.keys()
    # creating new dataframe for estimated irradiation coefficient
    solar_data_est_Irr = pd.DataFrame()
    solar_data_est_temp = pd.DataFrame()
    solar_data_est_Irr['Timestamp'] = solar_data['Timestamp']
    solar_data_est_temp['Timestamp'] = solar_data['Timestamp']
    for name in inverter_names:
        # Appending estimated irradiation coefficient column to the dataframe
        # PT = DC_Power * (1 + ((MODULE_TEMP - 25) * (0.32/100)))
        # Formulas are as follows
        # Irradiation Coefficient
        # PT = Pa * (1 + [(M - 25) * Tc/100])
        # Irr_Coef = PT/(PDc * Ir)
        # PT = Power Transformed to Temp
        # M = Module Temperature
        # Pa = PV Power(DC Power)
        # Tc = Temperature coefficient
        # PDc = Inverter DC capacity
        # Ir = Irradiation

        solar_data['PT'] = solar_data[name] * (1 + ((solar_data['MODULE_TEMP'] - 25) * (0.32 / 100)))

        # Estimated Irradiation Coefficient = PT/(Plant_DC_Capacity* Irradiation)
        solar_data_est_Irr[name] = solar_data['PT'] / (dc_capacity_dict[name] * solar_data['IRRADIATION'])

        # Appending estimated temperature coefficient column to the dataframe
        # Pi = DC power of Inverter/Irradiaction

        # Module Temperature Coefficient
        # ModTemp_Coef = 100 * (PDc/PI - 1)/(M-25)
        # PI = Power Transformed to Irradiation
        # PDc = Inverter DC capacity
        # M = Module Temperature
        # ***************one change
        # Irr_Coef = PT/(PDc * Ir)
        solar_data['PI'] = solar_data[name] / solar_data['IRRADIATION']

        # Estimated Temp Coefficient = 100*(((Inverter_DC_capacity/Pi)-1)/(MODULE_TEMP - 25))
        solar_data_est_temp[name] = 100 * (((dc_capacity_dict[name] / solar_data['PI']) - 1) / (solar_data['MODULE_TEMP'] - 25))
    return solar_data_est_Irr, solar_data_est_temp


# Function to get estimated irradiation coefficient of all inverters
def IrrCoeffEstimatorMedian(solar_data, dc_capacity_dict):
    # Getting the list of column names
    inverter_names = dc_capacity_dict.keys()


    # creating new dataframe for estimated irradiation coefficient
    irrCoeffEstimatorMedian_df = pd.DataFrame()
    #
    # solar_data['IRRADIATION'] = solar_data.IRRADIATION.round(1)
    # irrCoeffEstimatorMedian_df['irr_range'] = solar_data.IRRADIATION.unique()

    for name in inverter_names:
        # PT = DC_Power * (1 + ((MODULE_TEMP - 25) * (0.32/100)))
        solar_data['PT'] = solar_data[name] * (1 + ((solar_data['MODULE_TEMP'] - 25) * (0.32 / 100)))

        # Getting DC capacity for the inverter
        dc_capacity_inverter = dc_capacity_dict[name]
        solar_data['Estimated_Irr_Coeff'] = solar_data['PT'] / (dc_capacity_inverter * solar_data['IRRADIATION'])

        irrCoeffEstimatorMedian_df[name] = solar_data.groupby(pd.cut(solar_data["IRRADIATION"], np.arange(0, 1.3, 0.1)))['Estimated_Irr_Coeff'].median()
        #
        # irrCoeffEstimatorMedian_df[name] = (
        #     solar_data.IRRADIATION.map(solar_data.groupby(['IRRADIATION']).Estimated_Irr_Coeff.median())).unique()

    ts = solar_data["Timestamp"][0]
    ts_median = ts.replace(day=15, hour=0, minute=0, second=0)
    irrCoeffEstimatorMedian_df["Timestamp"] = ts_median
    irrCoeffEstimatorMedian_df.reset_index(inplace=True)
    irrCoeffEstimatorMedian_df.rename(columns={"IRRADIATION": "irr_range"}, inplace=True)

    return irrCoeffEstimatorMedian_df



# Function to get estimated temperature coefficient of all inverters
def TempCoeffEstimatorMedian(solar_data,dc_capacity_dict):
    # Getting the list of column names
    inverter_names = dc_capacity_dict.keys()

    # creating new dataframe for estimated temperature coefficient
    solar_data1 = pd.DataFrame()

    for name in inverter_names:
        # Pi = DC power of Inverter/Irradiaction
        solar_data['PI'] = solar_data[name] / solar_data['IRRADIATION']

        # Getting inverter name from the string
        dc_capacity_inverter = dc_capacity_dict[name]

        # Estimated Temp Coefficient = 100*(((Inverter_DC_capacity/Pi)-1)/(MODULE_TEMP - 25))
        solar_data['Estimated_Temp_Coef'] = 100 * (((dc_capacity_inverter / solar_data['PI']) - 1) / (solar_data['MODULE_TEMP'] - 25))

        # Appending estimated temperature coefficient column to the dataframe
        solar_data1[name] = solar_data.groupby(pd.cut(solar_data["MODULE_TEMP"], np.arange(0, 100, 5)))['Estimated_Temp_Coef'].median()
        #df.groupby('StationID', as_index=False)['BiasTemp'].mean()


    ts = solar_data["Timestamp"][0]
    ts_median = ts.replace(day=15,hour=0,minute=0,second=0)
    solar_data1["Timestamp"] = ts_median
    solar_data1.reset_index(inplace=True)
    solar_data1.rename(columns = {"MODULE_TEMP":"Temperature_range"}, inplace=True)

    return solar_data1


# NOTE: It is going to calculate for minimum one month even if you pass same start and end time
def cron_send_firstsolar_estimated_dc_power_to_druid(starttime=None,endtime=None):
    plant = SolarPlant.objects.get(slug="fsindiadevcoltd")

    vals = plant.independent_inverter_units.all().values("sourceKey", "total_capacity")
    dc_capacity_dict = {}
    for val in vals:
        dc_capacity_dict[val["sourceKey"]] = val["total_capacity"]

    # if times not specified then calculate values for last month. Will be used by default to run this cron.
    if not starttime or not endtime:
        today = datetime.datetime.now()
        if today.month == 1:
            last_month = 12
            last_year = today.year - 1
            starttime = today.replace(month=last_month, year=last_year)
        else:
            starttime = today.replace(day=1)
        endtime = starttime.replace(day = monthrange(starttime.year,starttime.month)[1])

    # if both timestamps are in same month
    if starttime.month == endtime.month and starttime.year == endtime.year:
        first_date_of_month, last_date_of_month = monthrange(starttime.year,starttime.month)
        starttime = starttime.replace(day=1)
        endtime = endtime.replace(day=last_date_of_month)
        list_of_days = [[starttime,endtime]]
    else:
        list_of_days = get_list_of_days_per_month(starttime,endtime)
    # starttime = datetime.datetime(2018, 01, 22, 00, 00)
    # endtime = datetime.datetime(2019, 01, 22, 23, 59)
    # list_of_days = [[starttime,endtime]]

    for month_range in list_of_days:
        starttime,endtime = month_range
        logger.warning( "**************************************")
        logger.warning("Starttime: %s"%starttime)
        logger.warning("Endtime %s" %endtime)
        logger.warning("**************************************")

        df_inv_mod_temp_irr = get_inverter_mod_temp_irr_data_in_df(plant, starttime, endtime)
        logger.warning("This is the raw dataframe head as input:")
        logger.warning(str(df_inv_mod_temp_irr.head()))
        df_inv_mod_temp_irr.replace('', np.nan,inplace=True)
        df_inv_mod_temp_irr.dropna(inplace=True)

        # return df_inv_mod_temp_irr

        # Expected DC Capacity
        df_expected_dc_capacity = DCCapacityEstimator(df_inv_mod_temp_irr)
        logger.warning("Expected DC Capacity head: ")
        logger.warning(str(df_expected_dc_capacity.head()))


        # Expected DC Capacity MEDIAN
        logger.warning("Expected DC Capacity head MEDIAN: ")
        df_to_find_median = df_expected_dc_capacity.set_index("Timestamp")
        df_expected_dc_capacity_median = df_to_find_median.resample('M').median()
        df_expected_dc_capacity_median.reset_index(inplace=True)

        ts = df_expected_dc_capacity["Timestamp"][0]
        ts_median = ts.replace(day=15, hour=0, minute=0,second=0)
        df_expected_dc_capacity_median["Timestamp"] = ts_median


        send_df_to_kafka(df_expected_dc_capacity, plant, "ESTIMATED_DC_POWER", "INVERTER")
        logger.warning("Expected DC Capacity sent to kafka======================>")

        send_df_to_kafka(df_expected_dc_capacity_median, plant, "ESTIMATED_DC_POWER_MEDIAN", "INVERTER")
        logger.warning("Expected DC Capacity MEDIAN sent to kafka======================>")


        # Expected Irradiation and Temperature Coefficient Calculation
        df_inv_mod_temp_irr.set_index("Timestamp", inplace=True)
        df_inv_mod_temp_irr = df_inv_mod_temp_irr.apply(pd.to_numeric)
        df_inv_mod_temp_irr = df_inv_mod_temp_irr.reset_index()

        solar_data_est_Irr, solar_data_est_temp = TempAndIrrCoeffEstimator(df_inv_mod_temp_irr, dc_capacity_dict)
        logger.warning("Estimated Irradiation Coefficient df head:")
        logger.warning(str(solar_data_est_Irr.head()))
        logger.warning("Estimated Temperature Coefficient df head: ")
        logger.warning(str(solar_data_est_temp.head()))
        send_df_to_kafka(solar_data_est_Irr, plant, "ESTIMATED_IRR_COEFF", "INVERTER")
        logger.warning("Expected Irradiation Coefficient sent to kafka======================>")

        send_df_to_kafka(solar_data_est_temp, plant, "ESTIMATED_TEMP_COEFF", "INVERTER")
        logger.warning("Expected Temperature Coefficient sent to kafka======================>")


        # Median for Expected Irradiation and Temperature Coefficient Calculation
        df_irr_coefficient_median = IrrCoeffEstimatorMedian(df_inv_mod_temp_irr, dc_capacity_dict)
        send_df_to_kafka(df_irr_coefficient_median, plant, "ESTIMATED_IRR_COEFF_MEDIAN", "INVERTER")

        df_temp_coefficient_median= TempCoeffEstimatorMedian(df_inv_mod_temp_irr, dc_capacity_dict)
        send_df_to_kafka(df_temp_coefficient_median, plant, "ESTIMATED_TEMP_COEFF_MEDIAN", "INVERTER")


# starttime = datetime.datetime(2017,01,01,00,00)
# endtime = datetime.datetime(2017,12,31,23,59)
# cron_send_firstsolar_estimated_dc_power_to_druid(starttime,endtime)