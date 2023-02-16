from dataglen.models import ValidDataStorageByStream, Sensor
from solarrms.settings import INVERTER_CHART_FIELDS, INVERTER_CHART_LEN
from solarrms.settings import INPUT_PARAMETERS, OUTPUT_PARAMETERS, STATUS_PARAMETERS, VALID_ENERGY_CALCULATION_DELTA_MINUTES
import logging
import pandas as pd
import pytz, sys
from utils.errors import generate_exception_comments
import numpy as np
from kutbill import settings
from solarrms.models import PerformanceRatioTable, CUFTable, SolarPlant, SolarGroup, IndependentInverter, \
    PlantCompleteValues, PlantSummaryDetails, SolarField, PlantDeviceSummaryDetails, EnergyMeter, PlantDeviceSummaryDetails
from django.utils import timezone
from dataglen.models import Field
import base64
import requests
import time
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

from solarrms.settings import PLANT_POWER_STREAM, PLANT_ENERGY_STREAM, INVERTER_ENERGY_FIELD, INVERTER_POWER_FIELD, \
    INVERTER_VALID_LAST_ENTRY_MINUTES, INVERTER_TOTAL_ENERGY_FIELD, WEBDYN_PLANTS_SLUG, \
    VALID_ENERGY_CALCULATION_DELTA_MINUTES_DOMINICUS, PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA, ENERGY_CALCULATION_STREAMS, \
    ENERGY_METER_STREAM_UNITS, ENERGY_METER_STREAM_UNIT_FACTOR, IRRADIATION_UNITS, IRRADIATION_UNITS_FACTOR

from solarrms.solarutils import get_aggregated_energy
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
import math
import json
import collections
from errors.models import ErrorStorageByStream
import datetime
from solarrms.solarutils import sorted_nicely, manipulateColumnNames, manipulateColumnNames2,excelConversion, excelNoData
import calendar
from dateutil import parser

date_col_name='Date'
generation_col_name = 'Generation (kWh)'
inv_total_gen_col_name = 'Inverter Total Generation (kWh)'
pr_col_name = 'PR (%)'
cuf_col_name = 'CUF (%)'
specific_yield_col_name = 'Specific Yield'
grid_avail_col_name = 'Grid Availability (%)'
equip_avail_col_name = 'Equipment Availability (%)'
dc_loss_col_name = 'DC Loss (kWh)'
conversion_loss_col_name = 'Conversion Loss (kWh)'
ac_loss_col_name = 'AC Loss (kWh)'
insolation_col_name = 'Insolation (kWh/m^2)'
max_irradiance_col_name = 'Max Irradiance (kW/m^2)'
avg_irradiation_col_name= 'Average Irradiation (kWh/m^2)'


def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

DEFAULT_STREAM_UNIT=  {
                         "DI1_1": "NA",
                         "DI1_2": "NA",
                         "DI2_1": "NA",
                         "DI2_2": "NA",
                         "DI3_1": "NA",
                         "DI3_2": "NA",
                         "DI4_1": "NA",
                         "DI4_2": "NA",
                         "DI5_1": "NA",
                         "DI5_2": "NA",
                         "DO1_1": "NA",
                         "DO1_2": "NA",
                         "DO2_1": "NA",
                         "DO2_2": "NA",
                         "PREAMBLE_1": "NA",
                         "PREAMBLE_2": "NA",
                         "PREAMBLE_3": "NA",
                         "S10_1": "A",
                         "S10_2": "A",
                         "S11_1": "A",
                         "S11_2": "A",
                         "S12_1": "A",
                         "S12_2": "A",
                         "S13_1": "A",
                         "S13_2": "A",
                         "S14_1": "A",
                         "S14_2": "A",
                         "S15_1": "A",
                         "S15_2": "A",
                         "S16_1": "A",
                         "S16_2": "A",
                         "S17_1": "A",
                         "S17_2": "A",
                         "S18_1": "A",
                         "S18_2": "A",
                         "S19_1": "A",
                         "S19_2": "A",
                         "S1_1": "A",
                         "S1_2": "A",
                         "S20_1": "A",
                         "S20_2": "A",
                         "S21_1": "A",
                         "S21_2": "A",
                         "S22_1": "A",
                         "S22_2": "A",
                         "S23_1": "A",
                         "S23_2": "A",
                         "S24_1": "A",
                         "S24_2": "A",
                         "S2_1": "A",
                         "S2_2": "A",
                         "S3_1": "A",
                         "S3_2": "A",
                         "S4_1": "A",
                         "S4_2": "A",
                         "S5_1": "A",
                         "S5_2": "A",
                         "S6_1": "A",
                         "S6_2": "A",
                         "S7_1": "A",
                         "S7_2": "A",
                         "S8_1": "A",
                         "S8_2": "A",
                         "S9_1": "A",
                         "S9_2": "A",
                         "TEMP1_1": "C",
                         "TEMP1_2": "C",
                         "TEMP2_1": "C",
                         "TEMP2_2": "C",
                         "TEMP3_1": "C",
                         "TEMP3_2": "C",
                         "TIMESTAMP": "TIMESTAMP",
                         "VOLTAGE_1": "V",
                         "VOLTAGE_2": "V",
                         "ACTIVE_ENERGY": "kWh",
                         "ACTIVE_POWER": "kW",
                         "ACTIVE_POWER_B": "kW",
                         "ACTIVE_POWER_R": "kW",
                         "ACTIVE_POWER_Y": "kW",
                         "AC_FREQUENCY": "Hz",
                         "AC_FREQUENCY_B": "Hz",
                         "AC_FREQUENCY_R": "Hz",
                         "AC_FREQUENCY_Y": "Hz",
                         "AC_VOLTAGE": "V",
                         "AC_VOLTAGE_B": "V",
                         "AC_VOLTAGE_R": "V",
                         "AC_VOLTAGE_Y": "V",
                         "AGGREGATED": "NA",
                         "AGGREGATED_COUNT": "NA",
                         "AGGREGATED_END_TIME": "TIMESTAMP",
                         "AGGREGATED_START_TIME": "TIMESTAMP",
                         "APPARENT_POWER": "kW",
                         "APPARENT_POWER_B": "kW",
                         "APPARENT_POWER_R": "kW",
                         "APPARENT_POWER_Y": "kW",
                         "CONVERTER_TEMPERATURE": "C",
                         "CONVERTER_VOLTAGE": "V",
                         "CUBICLE_TEMPERATURE": "C",
                         "CURRENT": "A",
                         "CURRENT_B": "A",
                         "CURRENT_COMPLETE_ERROR": "NA",
                         "CURRENT_ERROR": "NA",
                         "CURRENT_R": "A",
                         "CURRENT_Y": "A",
                         "DAILY_YIELD": "kWh",
                         "DC_CURRENT": "A",
                         "DC_POWER": "kW",
                         "DC_VOLTAGE": "V",
                         "DIGITAL_INPUT": "NA",
                         "FAULT_HIGH": "NA",
                         "FAULT_LOW": "NA",
                         "FEEDIN_TIME": "TIMESTAMP",
                         "HEAT_SINK_TEMPERATURE": "C",
                         "INSIDE_TEMPERATURE": "C",
                         "INVERTER_LOADING": "NA",
                         "INVERTER_TIMESTAMP": "TIMESTAMP",
                         "LIVE": "NA",
                         "OPERATING_TIME": "TIMESTAMP",
                         "PHASE_ANGLE": "NA",
                         "POWER_FACTOR": "NA",
                         "POWER_SUPPLY_CURRENT": "A",
                         "POWER_SUPPLY_VOLTAGE": "V",
                         "POWER_SUPPLY_VOLTAGE_B": "V",
                         "POWER_SUPPLY_VOLTAGE_R": "V",
                         "POWER_SUPPLY_VOLTAGE_Y": "V",
                         "REACTIVE_POWER": "kW",
                         "REACTIVE_POWER_B": "kW",
                         "REACTIVE_POWER_R": "kW",
                         "REACTIVE_POWER_Y": "kW",
                         "SOLAR_STATUS": "NA",
                         "SOLAR_STATUS_MESSAGE": "NA",
                         "TOTAL_YIELD": "kWh",
                         "ActivePower": "kW",
                         "ApparentPower": "kW",
                         "Appliance": "NA",
                         "Cost": "NA",
                         "Energy": "kWh",
                         "Frequency": "Hz",
                         "MACAddress": "NA",
                         "PhaseAngle": "NA",
                         "PowerFactor": "NA",
                         "ReactivePower": "kW",
                         "Voltage": "V",
                         "VOLTAGE": "V",
                         "STRING_1": "A",
                         "STRING_10": "A",
                         "STRING_11": "A",
                         "STRING_12": "A",
                         "STRING_13": "A",
                         "STRING_14": "A",
                         "STRING_15": "A",
                         "STRING_16": "A",
                         "STRING_17": "A",
                         "STRING_18": "A",
                         "STRING_19": "A",
                         "STRING_2": "A",
                         "STRING_20": "A",
                         "STRING_21": "A",
                         "STRING_22": "A",
                         "STRING_23": "A",
                         "STRING_24": "A",
                         "STRING_25": "A",
                         "STRING_3": "A",
                         "STRING_4": "A",
                         "STRING_5": "A",
                         "STRING_6": "A",
                         "STRING_7": "A",
                         "STRING_8": "A",
                         "STRING_9": "A",
                         "TEMPERATURE_1": "C",
                         "TEMPERATURE_2": "C",
                         "TEMPERATURE_3": "C",
                         "S1": "A",
                         "S10": "A",
                         "S11": "A",
                         "S12": "A",
                         "S13": "A",
                         "S14": "A",
                         "S15": "A",
                         "S16": "A",
                         "S17": "A",
                         "S18": "A",
                         "S19": "A",
                         "S2": "A",
                         "S20": "A",
                         "S21": "A",
                         "S22": "A",
                         "S23": "A",
                         "S24": "A",
                         "S25": "A",
                         "S3": "A",
                         "S4": "A",
                         "S5": "A",
                         "S6": "A",
                         "S7": "A",
                         "S8": "A",
                         "S9": "A",
                         "V1":"V",
                         "V2":"V",
                         "V3":"V",
                         "V4":"V",
                         "V5":"V",
                         "V6":"V",
                         "V7":"V",
                         "V8":"V",
                         "V9":"V",
                         "V10":"V",
                         "TEMP1": "C",
                         "TEMP2": "C",
                         "TEMP3": "C",
                         "POWER": "kW",
                         "Checksum": "NA",
                         "AccelerometerXaxis": "NA",
                         "AccelerometerYaxis": "NA",
                         "AccelerometerZaxis": "NA",
                         "AmbientLight": "NA",
                         "BarometricPressure": "NA",
                         "DataCount": "NA",
                         "LinearRelativeHumidity": "NA",
                         "MotionDetectionStatus": "NA",
                         "MotionSensorConnectionStatus": "NA",
                         "SoundLevel": "NA",
                         "Temperature": "C",
                         "TemperatureCompensatedRH": "NA",
                         "Counter": "NA",
                         "Generation": "NA",
                         "Orientation": "NA",
                         "AMBIENT_TEMPERATURE": "C",
                         "DAILY_PLANT_ENERGY": "kWh",
                         "ENERGY_METER_DATA": "kWh",
                         "EXTERNAL_IRRADIATION": "kWh/m^2",
                         "HIGHEST_AMBIENT_TEMPERATURE": "C",
                         "EXTERNAL_IRRADIATION": "kW/m^2",
                         "IRRADIATION": "kW/m^2",
                         "MODULE_TEMPERATURE": "C",
                         "PLANT_ACTIVE_POWER": "kW",
                         "TOTAL_PLANT_ENERGY": "kWh",
                         "WINDSPEED": "km/hr",
                         "CARTRIDGE_ID": "NA",
                         "DATA_VALUES": "NA",
                         "DEVICE_ID": "NA",
                         "LAB_ID": "NA",
                         "PROCESSING_END_TIMESTAMP": "TIMESTAMP",
                         "SAMPLE_ID": "NA",
                         "TEST_COUNT": "NA",
                         "TEST_END_TIMESTAMP": "TIMESTAMP",
                         "TEST_NAMES": "NA",
                         "TEST_START_TIMESTAMP": "TIMESTAMP",
                         "IRR_GHI_PROCESSED": "kW/m^2",
                         "IRR_GHI_RAW": "kW/m^2",
                         "IRR_POA_PROCESSED": "kW/m^2",
                         "IRR_POA_RAW": "kW/m^2",
                         "IRR_PROCESSED": "kW/m^2",
                         "IRR_RAW": "kW/m^2",
                         "PANETT_PROCESSED": "C",
                         "PANETT_RAW": "C",
                         "QAT_PROCESSED": "C",
                         "QAT_RAW": "C",
                         "WIND_SP_PROCESSED": "km/hr",
                         "WIND_SP_RAW": "km/hr",
                         "ActivePowerTotal": "kW",
                         "ActivePower_Phase1": "kW",
                         "ActivePower_Phase2": "kW",
                         "ActivePower_Phase3": "kW",
                         "Ampere1Phase1": "A",
                         "Ampere_Phase2": "A",
                         "Ampere_Phase3": "A",
                         "ApparentPowerTotal": "kW",
                         "ApparentPower_Phase1": "kW",
                         "ApparentPower_Phase2": "kW",
                         "ApparentPower_Phase3": "kW",
                         "AverageCurrent": "A",
                         "AverageFrequency": "Hz",
                         "AveragePowerFactor": "NA",
                         "AverageVoltage": "V",
                         "ForwardActiveEnergy": "kWh",
                         "ForwardApparentEnergy": "kWh",
                         "MaximumDemand": "NA",
                         "MaximumDemandOccurence": "NA",
                         "mSendName": "NA",
                         "OnHours": "NA",
                         "PowerFactor_Phase1": "NA",
                         "PowerFactor_Phase2": "NA",
                         "PowerFactor_Phase3": "NA",
                         "PowerInterruptions": "NA",
                         "PresentDemand": "NA",
                         "RisingDemand": "NA",
                         "Voltage_Phase1ToNeutral": "V",
                         "Voltage_Phase2ToNeutral": "V",
                         "Voltage_Phase3ToNeutral": "V",
                         "HEARTBEAT": "NA",
                         "IRRADIATION1": "kW/m^2",
                         "IRRADIATION2": "kW/m^2",
                         "AMP": "A",
                         "HZ": "Hz",
                         "KWH": "MWh",
                         "PF": "NA",
                         "VA": "kW",
                         "VAR": "kW",
                         "VOLT_LTL": "V",
                         "VOLT_LTN": "V",
                         "W": "W",
                         "Reading": "NA",
                         "PANETT_RAW_processed": "C",
                         "QAT_RAW_processed": "C",
                         "Humidity": "%",
                         "Pressure": "NA",
                         "DC Bus voltage": "V",
                         "Device code": "NA",
                         "External counter input": "NA",
                         "HDI frequency": "NA",
                         "Input of AI1": "NA",
                         "Input of AI2": "NA",
                         "Input terminal status": "NA",
                         "Inv fault address info": "NA",
                         "Output current": "A",
                         "Output Frequency": "Hz",
                         "Output power": "kW",
                         "Output terminal status": "NA",
                         "Output torque": "NA",
                         "Output voltage": "V",
                         "PID feedback value": "NA",
                         "PID preset value": "NA",
                         "Reference Frequency": "Hz",
                         "Rotation speed": "m/s",
                         "Step No. of PLC or multi-step": "NA",
                         "Torque setting": "NA",
                         "test_stream1": "NA",
                         "test_stream2": "NA",
                         "test_stream3": "NA",
                         "DATA_SET": "NA",
                         "stream1": "NA",
                         "stream2": "NA",
                         "stream3": "NA",
                         "STATUS": "NA",
                         "Active Energy Counter Total": "NA",
                         "Apparent Power L1": "kW",
                         "Apparent Power L2": "kW",
                         "Apparent Power L3": "kW",
                         "Apparent Power Total": "kW",
                         "Current L1": "A",
                         "Current L2": "A",
                         "Current L3": "A",
                         "DC Supply Term": "NA",
                         "F BB L1": "NA",
                         "F BB L2": "NA",
                         "F BB L3": "NA",
                         "Frequency L1": "Hz",
                         "Frequency L2": "Hz",
                         "Frequency L3": "Hz",
                         "Power L1": "kW",
                         "Power L2": "kW",
                         "Power L3": "kW",
                         "Power Total": "kW",
                         "Reactive Power L1": "kW",
                         "Reactive Power L2": "kW",
                         "Reactive Power L3": "kW",
                         "Reactive Power Total": "kW",
                         "U BB L1-L2": "NA",
                         "U BB L1-N": "NA",
                         "U BB L2-L3": "NA",
                         "U BB L2-N": "NA",
                         "U BB L3-L1": "NA",
                         "U BB L3-N": "NA",
                         "Voltage L1-L2": "NA",
                         "Voltage L1-N": "NA",
                         "Voltage L2-L3": "NA",
                         "Voltage L2-N": "NA",
                         "Voltage L3-L1": "NA",
                         "Voltage L3-N": "NA",
                         "AVG_RADIATION": "kWh/m^2",
                         "CUF": "NA",
                         "PR": "NA",
                         "SPECIFIC_YIELD":"NA",
                         "TODAY_ACTIVE_ENERGY": "kWh",
                         "TOTAL_ACTIVE_ENERGY": "kWh",
                         "YESTERDAY_ACTIVE_ENERGY": "kWh",
                         "WING_SP_RAW": "km/hr",
                         "RAINFALL": "mm",
                         "WIND_DIRECTION": "NA",
                         "string-test": "NA",
                         "string_test101": "NA",
                         "string_test102": "NA",
                         "string_testExternal100": "NA",
                         "string_testExternal101": "NA",
                         "string_testExternal104": "NA",
                         "string_testExternal106": "NA",
                         "ARCHIVED": "NA",
                         "A12": "A",
                         "A23": "A",
                         "A31": "A",
                         "FQ": "Hz",
                         "I1": "A",
                         "I2": "A",
                         "I3": "A",
                         "KA": "NA",
                         "KA1": "NA",
                         "KA2": "NA",
                         "KA3": "NA",
                         "KT": "kW",
                         "KT1": "kW",
                         "KT2": "kW",
                         "KT3": "kW",
                         "KV": "kVA",
                         "KV1": "kVA",
                         "KV2": "kVA",
                         "KV3": "kVA",
                         "kVAh(ABS)": "kVA",
                         "kVAh(E)": "kVA",
                         "kVAh(I)": "kVA",
                         "kVArh(E)": "kVA",
                         "kVArh(E)_WE": "kVA",
                         "kVArh(E)_WI": "kVA",
                         "kVArh(I)": "kVA",
                         "kVArh(I)_WE": "kVA",
                         "kVArh(I)_WI": "kVA",
                         "kWh(ABS)": "kWh",
                         "kWhLag(ABS)": "kWh",
                         "kWhLead(ABS)": "kWh",
                         "kWhT(E)": "kWh",
                         "kWhT(E)_FE": "kWh",
                         "kWhT(I)": "kWh",
                         "kWhT(I)_FI": "kWH",
                         "L1": "A",
                         "L2": "A",
                         "L3": "A",
                         "LN": "A",
                         "Q1": "NA",
                         "Q2": "NA",
                         "Q3": "NA",
                         "QA": "NA",
                         "R1": "NA",
                         "R2": "NA",
                         "R3": "NA",
                         "RT": "NA",
                         "THDC1": "NA",
                         "THDC2": "NA",
                         "THDC3": "NA",
                         "THDP1": "NA",
                         "THDP2": "NA",
                         "THDP3": "NA",
                         "THDV1": "NA",
                         "THDV2": "NA",
                         "THDV3": "NA",
                         "V1": "V",
                         "V12": "V",
                         "V2": "V",
                         "V23": "V",
                         "V3": "V",
                         "V31": "V",
                         "Vavg": "V",
                         "data": "NA",
                         "KWH_E": "kWh",
                         "KWH_I": "kWh",
                         "key": "NA",
                         "latitude": "NA",
                         "longitude": "NA",
                         "WATT_TOTAL": "kW",
                         "WATTS_R_PHASE": "kW",
                         "WATTS_Y_PHASE": "kW",
                         "WATTS_B_PHASE": "kW",
                         "VAR_TOTAL": "kVA",
                         "VAR_R_PHASE": "kVA",
                         "VAR_Y_PHASE": "kVA",
                         "VAR_B_PHASE": "kVA",
                         "PF_AVG": "NA",
                         "PF_R_PHASE": "NA",
                         "PF_Y_PHASE": "NA",
                         "PF_B_PHASE": "NA",
                         "VA_TOTAL": "kVA",
                         "VA_R_PHASE": "kVA",
                         "VA_Y_PHASE": "kVA",
                         "VA_B_PHASE": "kVA",
                         "VLL_AVG": "V",
                         "VRY_PHASE": "V",
                         "VYB_PHASE": "V",
                         "VBR_PHASE": "V",
                         "VLN_AVG": "V",
                         "VR_PAHSE": "V",
                         "VY_PHASE": "V",
                         "VB_PHASE": "V",
                         "CURRENT_TOTAL": "A",
                         "C_R_PHASE": "A",
                         "C_Y_PHASE": "A",
                         "C_B_PHASE": "A",
                         "Wh_RECEIVED": "kWh",
                         "VAh_RECEIVED": "kWh",
                         "VARh_IMPEDENCE_RECEIVED": "kVA",
                         "VARh_CAPACITANCE_RECEIVED": "kVA",
                         "Wh_DELIVERED": "kWh",
                         "VAh_DELIVERED": "kVA",
                         "VARh_IMPEDENCE_DELIVERED": "kVA",
                         "VARh_CAPACITANCE_DELIVERED": "kVA",
                         "TOTAL_OPERATIONAL_HOURS": "s",
                         "DAILY_OPERATIONAL_HOURS": "s",
                         "DI_STATUS_1" : "NA",
                         "DI_STATUS_2" : "NA",
                         "DI_STATUS_3" : "NA",
                         "DI_STATUS_4" : "NA",
                         "DI_STATUS_5" : "NA",
                         "DO_STATUS_1" : "NA",
                         "DO_STATUS_2" : "NA",
                         "DI_STATUS_1_DESCRIPTION" : "NA",
                         "DI_STATUS_2_DESCRIPTION" : "NA",
                         "DI_STATUS_3_DESCRIPTION" : "NA",
                         "DI_STATUS_4_DESCRIPTION" : "NA",
                         "DI_STATUS_5_DESCRIPTION" : "NA",
                         "DO_STATUS_1_DESCRIPTION" : "NA",
                         "DO_STATUS_2_DESCRIPTION" : "NA",
                         "INVERTERS_DC_POWER" : "kW",
                         "INVERTERS_AC_POWER" : "kW"
                    }

def get_multiple_sources_multiple_streams_data(starttime, endtime, plant, sources_list, streams_list):
    try:
        df_results = pd.DataFrame()
        df_dict = dict()
        for stream in streams_list:
            df_final = pd.DataFrame
            for source_key in sources_list:
                df_list_source = []
                source = Sensor.objects.get(sourceKey=source_key)
                source_data = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                      stream_name= stream,
                                                                      timestamp_in_data__gte = starttime,
                                                                      timestamp_in_data__lte = endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                values_stream = []
                timestamp_stream = []
                for data_point in source_data:
                    timestamp_stream.append(data_point[1].replace(second=0, microsecond=0))
                    values_stream.append(float(data_point[0]))
                df_list_source.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),
                                                     str(source.name)+'_'+str(stream): values_stream}))
                if len(df_list_source) > 0:
                    results_source_temp = df_list_source[0]
                    for i in range(1, len(df_list_source)):
                        results_source_temp = results_source_temp.merge(df_list_source[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    if df_final.empty:
                        df_final = results_source_temp
                    else:
                        df_new = pd.merge(df_final, results_source_temp, on='timestamp', how='outer')
                        df_final = df_new
                #df_dict[stream] = df_final
            if df_results.empty:
                df_results = df_final
            else:
                df_new = pd.merge(df_results, df_final, on='timestamp', how='outer')
                df_results = df_new
            #df_results = df_results.merge(df_final, on='timestamp', how='inner')
        return df_results
    except Exception as exception:
        logger.debug("Error in fetching the data of the multiple sources with multiple streams : %s" % str(exception))



def get_multiple_sources_multiple_streams_data_no_merge(starttime, endtime, sources_stream_association):
    try:
        final_dict = {}
        for source_key in sources_stream_association.keys():
            try:
                source = Sensor.objects.get(sourceKey=source_key)
                for stream_name in sources_stream_association[source_key]:
                    try:
                        stream = Field.objects.get(source=source, name=stream_name)
                        source_data = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                              stream_name=stream_name,
                                                                              timestamp_in_data__gte = starttime,
                                                                              timestamp_in_data__lte = endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                        values = [float(item[0]) for item in source_data]
                        timestamps = [item[1].isoformat() for item in source_data]
                        try:
                            stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                        except:
                            stream_unit = "NA"
                        stream_dict = {}
                        stream_dict_list = []
                        stream_dict['x'] = timestamps
                        stream_dict['y'] = values
                        stream_dict['name'] = str(source.name) +'_'+ stream_name
                        stream_dict['yaxis'] = stream_unit
                        stream_dict['type'] = 'scatter'
                        try:
                            existing_unit_list = final_dict[stream_unit]
                            existing_unit_list.append(stream_dict)
                            final_dict[stream_unit] = existing_unit_list
                        except:
                            stream_dict_list.append(stream_dict)
                            final_dict[str(stream.streamDataUnit)] = stream_dict_list
                    except:
                        continue
            except:
                continue
        return final_dict
    except Exception as exception:
        print("Error in fetching the data of the multiple sources with multiple streams : " + str(exception))


def get_multiple_sources_multiple_streams_data_merge_pandas(starttime, endtime, sources_stream_association, delta, plant):
    try:
        final_dict = {}
        df_final = pd.DataFrame
        for source_key in sources_stream_association.keys():
            try:
                source = Sensor.objects.get(sourceKey=source_key)
                for stream_name in sources_stream_association[source_key]:
                    df_list_stream = []
                    try:
                        try:
                            stream = SolarField.objects.get(source=source, displayName=stream_name)
                            stream_name = str(stream.name)
                            stream_display_name = str(stream.displayName)
                        except:
                            try:
                                stream = Field.objects.get(source=source, name=stream_name)
                                stream_name = stream_name
                                stream_display_name = stream_name
                            except:
                                continue
                        source_data = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                              stream_name=stream_name,
                                                                              timestamp_in_data__gte = starttime,
                                                                              timestamp_in_data__lte= endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')

                        print stream.streamDataType

                        if str(stream_name) == 'IRRADIATION' and str(plant.slug) in IRRADIATION_UNITS.keys():
                            try:
                                values = [float(item[0])*float(IRRADIATION_UNITS_FACTOR[IRRADIATION_UNITS[str(plant.slug)]]) for item in source_data]
                            except:
                                values = [float(item[0]) for item in source_data]
                        else:
                            if stream.streamDataType != 'STRING':
                                values = [float(item[0]) for item in source_data]
                            else:
                                values = [item[0] for item in source_data]
                        if plant.metadata.plantmetasource.binning_interval:
                            timestamps = [item[1].replace(minute=item[1].minute - item[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60),
                                                          second=0,
                                                          microsecond=0) for item in source_data]
                        else:
                            timestamps = [item[1].replace(second=0, microsecond=0) for item in source_data]

                        if str(stream_name) == 'IRRADIATION' and str(plant.slug) in IRRADIATION_UNITS.keys():
                            try:
                                stream_unit = IRRADIATION_UNITS[str(plant.slug)]
                            except:
                                stream_unit = DEFAULT_STREAM_UNIT['IRRADIATION']
                        else:
                            try:
                                stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[str(stream.name)]
                            except:
                                stream_unit = "NA"

                        df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamps),
                                                            str(source.name)+'#'+str(stream_display_name)+'#'+str(stream_unit): values}))

                        if len(df_list_stream) > 0:
                            results_stream_temp = df_list_stream[0]
                            for i in range(1, len(df_list_stream)):
                                results_stream_temp = results_stream_temp.merge(df_list_stream[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                            if df_final.empty:
                                df_final = results_stream_temp
                            else:
                                df_new = pd.merge(df_final.drop_duplicates('timestamp'), results_stream_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                                df_final = df_new
                    except:
                        continue
            except:
                continue
        if not df_final.empty:
            df_final = df_final.sort('timestamp')
            df_final_diff = df_final
            df_final_diff = df_final_diff.diff()
            df_final_diff = df_final_diff.rename(columns={'timestamp':'ts'})
            df_final_diff['timestamp'] = df_final['timestamp']
            df_final['ts'] = df_final_diff['ts']
            df_missing = df_final[(df_final['ts'] / np.timedelta64(1, 'm'))>delta]
            missing_index = df_missing.index.tolist()
            df_filling = pd.DataFrame(columns={'timestamp'})
            filling_timestamp = []
            for index in range(len(missing_index)):
                try:
                    # time_difference = (df_final.iloc[index]['timestamp'] - df_final.iloc[index-1]['timestamp']).total_seconds()/60
                    # filling_timestamp.append(df_final.iloc[index-1]['timestamp']+datetime.timedelta(minutes=time_difference/2))
                    filling_timestamp.append(df_missing.iloc[index]['timestamp']- datetime.timedelta(minutes=((df_missing.iloc[index]['ts'] / np.timedelta64(1, 'm'))/2)))
                except Exception as exception:
                    print str(exception)
                    continue
            df_filling['timestamp'] = filling_timestamp
            df_final = df_final.merge(df_filling.drop_duplicates('timestamp'), on='timestamp', how='outer')
            df_final = df_final.sort('timestamp')
            df_final = df_final.where(pd.notnull(df_final), None)
            column_names = df_final.columns.values.tolist()
            timestamp_list = df_final['timestamp'].tolist()
            # try:
            #     timestamp_list = [pd.to_datetime(x).tz_localize(plant.metadata.plantmetasource.dataTimezone).tz_convert('UTC').strftime("%Y-%m-%dT%H:%M:%SZ") for x in timestamp_list]
            # except:
            #     timestamp_list = [pd.to_datetime(x).tz_convert(plant.metadata.plantmetasource.dataTimezone).strftime("%Y-%m-%dT%H:%M:%SZ") for x in timestamp_list]
            timestamp_list = [x.strftime("%Y-%m-%dT%H:%M:%SZ") for x in timestamp_list]
            for column in column_names:
                if column != 'ts':
                    try:
                        df_column_list_values = df_final[column].tolist()
                        name = column.split('#')
                        device_name = name[0]
                        stream_name = name[1]
                        stream_unit = name[2]
                        stream_dict = {}
                        stream_dict_list = []
                        stream_dict['x'] = timestamp_list
                        stream_dict['y'] = df_column_list_values
                        stream_dict['name'] = str(device_name) + '_' + stream_name
                        stream_dict['yaxis'] = stream_unit
                        stream_dict['type'] = 'scatter'
                        try:
                            existing_unit_list = final_dict[stream_unit]
                            existing_unit_list.append(stream_dict)
                            final_dict[stream_unit] = existing_unit_list
                        except:
                            stream_dict_list.append(stream_dict)
                            final_dict[str(stream_unit)] = stream_dict_list
                    except:
                        continue
            key_count = 1
            for key in final_dict.keys():
                values = final_dict[key]
                for i in range(len(values)):
                    value = values[i]
                    value['yaxis'] = 'y'+str(key_count)
                key_count += 1
        return final_dict
    except Exception as exception:
        print("Error in fetching the data of the multiple sources with multiple streams : " + str(exception))
        return {}


def get_multiple_inverters_single_stream_data(starttime, endtime, plant, sources_list, stream):
    try:
        df_results_stream = pd.DataFrame()
        starttime = update_tz(starttime, 'UTC')
        endtime = update_tz(endtime, 'UTC')
        for source in sources_list:
            df_list_stream = []
            stream_values = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                    stream_name= stream,
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_stream = []
            timestamp_stream = []
            try:
                stream_object = Field.objects.get(source=source, name=stream)
            except:
                return df_results_stream
            for data_point in stream_values:
                timestamp_stream.append(data_point[1].replace(second=0, microsecond=0))
                if stream_object.streamDataType != 'STRING':
                    values_stream.append(float(data_point[0]))
                else:
                    values_stream.append(data_point[0])
            df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),
                                                str(source.name): values_stream}))

            if len(df_list_stream) > 0:
                results_stream_temp = df_list_stream[0]
                for i in range(1, len(df_list_stream)):
                    results_stream_temp = results_stream_temp.merge(df_list_stream[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                if df_results_stream.empty:
                    df_results_stream = results_stream_temp
                else:
                    df_new = pd.merge(df_results_stream, results_stream_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                    df_results_stream = df_new
        if not df_results_stream.empty:
            df_results_stream = df_results_stream.sort('timestamp')
            final_timestamp = df_results_stream['timestamp']
            df_results_stream.drop(labels=['timestamp'], axis=1,inplace = True)
            df_results_stream.insert(0, 'Timestamp', final_timestamp)
            df_results_stream.index = np.arange(1, len(df_results_stream) + 1)
        return df_results_stream
    except Exception as exception:
        print("Error in fetching the data of the multiple sources with multiple streams : " + str(exception))

def get_multiple_devices_single_stream_data(starttime, endtime, plant, sources_list, stream):
    try:
        df_results_stream = pd.DataFrame()
        starttime = update_tz(starttime, 'UTC')
        endtime = update_tz(endtime, 'UTC')
        for key in sources_list:
            try:
                source = Sensor.objects.get(sourceKey=key)
            except Exception as exception:
                print ("Invalid source Key")
                return []

            df_list_stream = []
            stream_values = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                    stream_name= stream,
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_stream = []
            timestamp_stream = []
            try:
                stream_object = Field.objects.get(source=source, name=stream)
            except:
                return df_results_stream
            for data_point in stream_values:
                timestamp_stream.append(data_point[1].replace(second=0, microsecond=0))
                if stream_object.streamDataType != 'STRING':
                    values_stream.append(float(data_point[0]))
                else:
                    values_stream.append(data_point[0])
            df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),
                                                str(source.name): values_stream}))

            if len(df_list_stream) > 0:
                results_stream_temp = df_list_stream[0]
                for i in range(1, len(df_list_stream)):
                    results_stream_temp = results_stream_temp.merge(df_list_stream[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                if df_results_stream.empty:
                    df_results_stream = results_stream_temp
                else:
                    df_new = pd.merge(df_results_stream, results_stream_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                    df_results_stream = df_new
        if not df_results_stream.empty:
            df_results_stream = df_results_stream.sort('timestamp')
            final_timestamp = df_results_stream['timestamp']
            df_results_stream.drop(labels=['timestamp'], axis=1,inplace = True)
            df_results_stream.insert(0, 'Timestamp', final_timestamp)
            df_results_stream.index = np.arange(1, len(df_results_stream) + 1)
        return df_results_stream
    except Exception as exception:
        print("Error in fetching the data of the multiple sources with multiple streams : " + str(exception))


def get_plant_summary_parameters(date, plant):
    try:
        df_summary_result = pd.DataFrame()
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

        print date
        if len(value)>0:
            generation = "{0:.2f}".format(value[0].plant_generation_today)
            pr = "{0:.2f}".format(value[0].pr) if value[0].pr else 0.0
            cuf = "{0:.2f}".format(value[0].cuf) if value[0].cuf else 0.0
            grid_availability = "{0:.2f}".format(100 - float(value[0].grid_unavailability))
            equipment_availability = "{0:.2f}".format(100 - float(value[0].equipment_unavailability))
            dc_loss = "{0:.2f}".format(value[0].dc_loss)
            conversion_loss = "{0:.2f}".format(value[0].conversion_loss)
            ac_loss = "{0:.2f}".format(value[0].ac_loss)
            df_summary_result['Date'] = pd.Series(pd.to_datetime((date.replace(hour=0, minute=0, second=0, microsecond=0)).date()))
            df_summary_result['generation (kWh)'] = pd.Series(generation)
            df_summary_result['PR'] = pr
            df_summary_result['CUF'] = cuf
            df_summary_result['grid_availability (%)'] = grid_availability
            df_summary_result['equipment_availability (%)'] = equipment_availability
            df_summary_result['dc_loss (kWh)'] = dc_loss
            df_summary_result['conversion_loss (kWh)'] = conversion_loss
            df_summary_result['ac_loss (kWh)'] = ac_loss
        return df_summary_result
    except Exception as exception:
        print(str(exception))


EXCLUDE_STREAMS = ['LIVE', 'AGGREGATED', 'TIMESTAMP', 'AGGREGATED_START_TIME', 'AGGREGATED_END_TIME', 'AGGREGATED_COUNT']
def get_single_device_multiple_streams_data(starttime, endtime, plant, source, streams_list):
    try:
        df_results_stream = pd.DataFrame()
        for stream in streams_list:
            df_list_stream = []
            if stream.upper() not in EXCLUDE_STREAMS:
                try:
                    stream_object = SolarField.objects.get(source=source, displayName=stream)
                    stream = stream_object.name
                    stream_display_name = str(stream_object.displayName)
                except:
                    stream_object = Field.objects.get(source=source, name=stream)
                    stream = stream
                    stream_display_name = stream
                stream_values = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                        stream_name= stream,
                                                                        timestamp_in_data__gte = starttime,
                                                                        timestamp_in_data__lte = endtime
                                                                        ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                values_stream = []
                timestamp_stream = []
                for data_point in stream_values:
                    timestamp_stream.append(data_point[1].replace(second=0, microsecond=0))
                    # print stream_object.streamDataType
                    if stream_object.streamDataType != 'STRING':
                        values_stream.append(float(data_point[0]))
                    else:
                        values_stream.append(data_point[0])
                try:
                    stream_unit = str(stream_object.streamDataUnit) if (stream_object and stream_object.streamDataUnit) else DEFAULT_STREAM_UNIT[str(stream_object.name)]

                    if stream_unit == 'kWh/m^2' or stream_unit == 'kWh/m2':
                        stream_unit = 'kWhm2'
                    if stream_unit == 'kW/m^2' or stream_unit == 'kW/m2':
                        stream_unit = 'kWm2'
                    if stream_unit == 'km/hr':
                        stream_unit = 'kmph'
                    if stream_unit == 'm/s':
                        stream_unit = 'mps'
                except:
                    stream_unit = "NA"

                if stream_unit != 'NA':

                    df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),str(stream_display_name)+'('+str(stream_unit)+')': values_stream}))
                else:
                    df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),str(stream_display_name): values_stream}))

                if len(df_list_stream) > 0:
                    results_stream_temp = df_list_stream[0]
                    for i in range(1, len(df_list_stream)):
                        results_stream_temp = results_stream_temp.merge(df_list_stream[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    if df_results_stream.empty:
                        df_results_stream = results_stream_temp
                    else:
                        df_new = pd.merge(df_results_stream, results_stream_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                        df_results_stream = df_new
        if not df_results_stream.empty:
            df_results_stream = df_results_stream.sort('timestamp')
            final_timestamp = df_results_stream['timestamp']
            df_results_stream.drop(labels=['timestamp'], axis=1,inplace = True)
            df_results_stream.insert(0, 'Timestamp', final_timestamp)
            df_results_stream.index = np.arange(1, len(df_results_stream) + 1)
        return df_results_stream
    except Exception as exception:
        print(str(exception))


def get_monthly_report_values(starttime, endtime, plant, accessible_features = None):
    try:
        df_result = pd.DataFrame()
        df_result_final = pd.DataFrame()
        df_meter_all = pd.DataFrame()
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        if len(plant_summary_values)== 0:
            return pd.DataFrame()
        timestamp = []
        generation = []
        inverter_generation = []
        pr = []
        cuf = []
        specific_yield = []
        dc_loss = []
        conversion_loss = []
        ac_loss = []
        grid_availability  = []
        equipment_availability = []
        average_irradiation = []
        max_irradiance = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            generation.append(round(value.generation, 3) if value.generation is not None else value.generation)
            inverter_generation.append(round(value.inverter_generation,3) if value.inverter_generation is not None else value.generation)
            pr.append(round(value.performance_ratio*100,3) if value.performance_ratio is not None else value.performance_ratio)
            cuf.append(round(value.cuf*100,3) if value.cuf is not None else value.cuf)
            specific_yield.append(round(value.specific_yield,3) if value.specific_yield is not None else value.specific_yield)
            dc_loss.append(round(value.dc_loss,3) if value.dc_loss is not None else value.dc_loss)
            conversion_loss.append(round(value.conversion_loss,3) if value.conversion_loss is not None else value.conversion_loss)
            ac_loss.append(round(value.ac_loss,3) if value.ac_loss is not None else value.ac_loss)
            # grid_availability.append(round(value.grid_availability,3) if value.grid_availability is not None else value.grid_availability)
            # equipment_availability.append(round(value.equipment_availability,3) if value.equipment_availability is not None else value.equipment_availability)
            average_irradiation.append(round(value.average_irradiation,3) if value.average_irradiation is not None else value.average_irradiation)
            max_irradiance.append(round(value.max_irradiance,3) if value.max_irradiance is not None else value.max_irradiance)
        df_result[date_col_name] = timestamp
        df_result_final[date_col_name] = timestamp
        df_result[generation_col_name] = generation
        df_result[inv_total_gen_col_name] = inverter_generation
        df_result[pr_col_name] = pr
        df_result[cuf_col_name] = cuf
        df_result[specific_yield_col_name] = specific_yield
        # df_result[grid_avail_col_name] = grid_availability
        # df_result[equip_avail_col_name] = equipment_availability
        df_result[dc_loss_col_name] = dc_loss
        df_result[conversion_loss_col_name] = conversion_loss
        df_result[ac_loss_col_name] = ac_loss
        df_result[insolation_col_name] = average_irradiation
        df_result[max_irradiance_col_name] = max_irradiance
        df_result.sort(date_col_name)
        # drop columns with None values
        try:
            if df_result[dc_loss_col_name].isnull().all():
                del df_result[dc_loss_col_name]
            if df_result[conversion_loss_col_name].isnull().all():
                del df_result[conversion_loss_col_name]
            if df_result[ac_loss_col_name].isnull().all():
                del df_result[ac_loss_col_name]
        except:
            pass

        df_result_inverters = pd.DataFrame()
        df_result_inverters_max = pd.DataFrame()
        df_result_inverters_working_hours = pd.DataFrame()

        inverters = plant.independent_inverter_units.all()
        unsorted_inverter_names = inverters.values_list("name",flat=True)
        sorted_inverter_names = sorted_nicely(unsorted_inverter_names)

        for inverter_name in sorted_inverter_names:
            inverter = inverters.get(name=inverter_name)


            inverter_generations = list(
                PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                         count_time_period=86400,
                                                         identifier=str(inverter.sourceKey),
                                                         ts__gte=starttime,
                                                         ts__lte=endtime).order_by('ts').values_list('ts', 'generation',
                                                                                                     'max_dc_power',
                                                                                                     'max_ac_power',
                                                                                                     'total_working_hours'))
            df_inverters_generations = pd.DataFrame(inverter_generations,
                                                    columns=['ts', 'generation', 'max_dc_power', 'max_ac_power',
                                                             'total_working_hours'])
            df_inverter_gen_only = df_inverters_generations[['ts', 'generation']]
            df_inverter_gen_only = df_inverter_gen_only.round(3)
            df_inverter = df_inverter_gen_only.rename(columns={'ts': 'Date', 'generation': str(inverter.name)})

            df_inverter_max = df_inverters_generations[['ts', 'max_dc_power', 'max_ac_power']]
            df_inverter_max = df_inverter_max.rename(columns={'ts': 'Date', \
                                                              'max_dc_power': str(inverter.name) + ' MAX DC POWER (kW)', \
                                                              'max_ac_power': str(
                                                                  inverter.name) + ' MAX AC POWER (kWh)'})


            if df_inverters_generations["total_working_hours"].sum()>0:
                df_operational_hours = df_inverters_generations[['ts', 'total_working_hours']]

                df_operational_hours = df_operational_hours.rename(columns={'ts': 'Date', \
                                                                            'total_working_hours': str(
                                                                                inverter.name) + ' Working Hours'})
                if df_result_inverters_working_hours.empty:
                    df_result_inverters_working_hours = df_operational_hours
                else:
                    df_result_inverters_working_hours = df_result_inverters_working_hours.merge(
                        df_operational_hours.drop_duplicates('Date'), how='outer', on='Date')

            if df_result_inverters.empty:
                df_result_inverters = df_inverter
            else:
                df_result_inverters = df_result_inverters.merge(df_inverter.drop_duplicates('Date'), how='outer',
                                                                on='Date')

            if df_result_inverters_max.empty:
                df_result_inverters_max = df_inverter_max
            else:
                df_result_inverters_max = df_result_inverters_max.merge(df_inverter_max.drop_duplicates('Date'),
                                                                        how='outer', on='Date')


        # Fetching Energy Meters Data
        if (accessible_features!= None and 'Energy Meter(kWh)' in accessible_features) or (accessible_features==None):
            print "calculating meter power generation"
            # get the meter generation
            meter_objects = plant.energy_meters.all().filter(energy_calculation=True)
            unsorted_meter_names = meter_objects.values_list("name",flat=True)
            sorted_meter_names = sorted_nicely(unsorted_meter_names)

            for meter_name in sorted_meter_names:
                meter = meter_objects.get(name=meter_name)
                meter_values = []
                meter_timestamp = []
                df_meter = pd.DataFrame()
                meter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                             count_time_period=86400,
                                                                             identifier=str(meter.sourceKey),
                                                                             ts__gte=starttime,
                                                                         ts__lte=endtime).order_by('ts')
                for value in meter_generations:
                    meter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                    meter_timestamp.append(pd.to_datetime(value.ts))
                df_meter[str(meter.name)+' (kWh)'] = meter_values
                df_meter['Date'] = meter_timestamp
                df_meter.sort('Date')
                if df_meter_all.empty:
                    df_meter_all = df_meter
                else:
                    df_meter_all = df_meter_all.merge(df_meter.drop_duplicates('Date'), how='outer', on='Date')
        if df_meter_all.empty:
            print "Meter data not available"
        else:
            df_result = df_result.merge(df_meter_all.drop_duplicates('Date'), how='outer', on='Date')
        # Merge the inverters generation values
        if not df_result_inverters.empty:
            df_result = df_result.merge(df_result_inverters.drop_duplicates('Date'), how='outer', on='Date')
        # Merge working hours of inverters
        if not df_result_inverters_working_hours.empty:
            df_result = df_result.merge(df_result_inverters_working_hours.drop_duplicates('Date'), how='outer', on='Date')
        # Merge max power values of inverters
        if not df_result_inverters_max.empty:
            df_result = df_result.merge(df_result_inverters_max.drop_duplicates('Date'), how='outer', on='Date')

        if accessible_features!=None:
            # col_list=['Generation (kWh)','Inverter Total Generation (kWh)','PR (%)','CUF (%)','Specific Yield',
            #  'Grid Availability (%)','Equipment Availability (%)','DC Loss (kWh)',
            #  'Conversion Loss (kWh)','AC Loss (kWh)','Insolation (kWh/m^2)']
            col_list = ['Generation (kWh)', 'Inverter Total Generation (kWh)', 'PR (%)', 'CUF (%)', 'Specific Yield',
                        'DC Loss (kWh)', 'Conversion Loss (kWh)', 'AC Loss (kWh)', 'Insolation (kWh/m^2)']
            df_result_final['Date']=df_result['Date']
            df_result_columns_list = list(df_result.columns)
            for col in col_list:
                if col in accessible_features and col in df_result_columns_list:
                    df_result_final[col]=df_result[col]
            # As there is no 'Max Irradiance (kW/m^2)' feature , Mapping it to Insolution. Means If Insolution is there in accessible_features so the max Irradiance
            if 'Insolation (kWh/m^2)' in accessible_features:
                df_result_final['Max Irradiance (kW/m^2)']=df_result['Max Irradiance (kW/m^2)']

            if 'Energy Meter(kWh)' in accessible_features:
                if not df_meter_all.empty:
                    df_result_final = df_result_final.merge(df_meter_all.drop_duplicates('Date'), how='outer', on='Date')

            if 'Energy Values From Inverters (kWh)' in accessible_features:
                if not df_result_inverters.empty:
                    df_result_final = df_result_final.merge(df_result_inverters.drop_duplicates('Date'), how='outer', on='Date')

            # There is no feature associated with Total Operational Hours So mapping it with 'Inverter Total Generation (kWh)'
            if 'Inverter Total Generation (kWh)' in accessible_features:
                # Merge working hours of inverters
                if not df_result_inverters_working_hours.empty:
                    df_result_final = df_result_final.merge(df_result_inverters_working_hours.drop_duplicates('Date'), how='outer',
                                                on='Date')

            if 'MAX POWER' in accessible_features:
                # Merge max power values of inverters
                if not df_result_inverters_max.empty:
                    df_result_final = df_result_final.merge(df_result_inverters_max.drop_duplicates('Date'), how='outer', on='Date')
            # final sort based on merged values
            df_final = df_result_final.sort("Date").reset_index(drop=True)
            return df_final
        else:
            # final sort based on merged values
            df_final = df_result.sort("Date").reset_index(drop=True)
            return df_final

    except Exception as exception:
        logger.debug("Exception in get_monthly_report_values ====>>"+str(exception))
        return pd.DataFrame()
        print str(exception)

def get_monthly_report_values_pandas_excel_atria(starttime, endtime, plant):
    try:
        df_result = pd.DataFrame()
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        timestamp = []
        generation = []
        pr = []
        cuf = []
        ac_cuf = []
        specific_yield = []
        dc_loss = []
        conversion_loss = []
        ac_loss = []
        #grid_availability  = []
        #equipment_availability = []
        estimated_ghi = []
        average_irradiation = []
        curtailment_loss = []
        estimated_generation = []
        module_temperature = []
        ambient_temperature = []
        plant_start_time = []
        plant_end_time = []
        plant_run_time = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            estimated_generation.append(round(value.estimated_generation,3) if value.estimated_generation is not None else value.estimated_generation)
            generation.append(round(value.generation,3) if value.generation is not None else value.generation)
            pr.append(round(value.performance_ratio,3)*100 if value.performance_ratio is not None else value.performance_ratio)
            cuf.append(round(value.cuf,3)*100 if value.cuf is not None else value.cuf)
            ac_cuf.append(round(value.ac_cuf,3)*100 if value.ac_cuf is not None else value.ac_cuf)
            specific_yield.append(round(value.specific_yield,3) if value.specific_yield is not None else value.specific_yield)
            dc_loss.append(round(value.dc_loss,3) if value.dc_loss is not None else value.dc_loss)
            conversion_loss.append(round(value.conversion_loss,3) if value.conversion_loss is not None else value.conversion_loss)
            ac_loss.append(round(value.ac_loss,3) if value.ac_loss is not None else value.ac_loss)
            #grid_availability.append(round(value.grid_availability,3) if value.grid_availability is not None else value.grid_availability)
            #equipment_availability.append(round(value.equipment_availability,3) if value.equipment_availability is not None else value.equipment_availability)
            estimated_ghi.append(round(value.estimated_ghi,3) if value.estimated_ghi is not None else value.estimated_ghi)
            average_irradiation.append(round(value.average_irradiation,3) if value.average_irradiation is not None else value.average_irradiation)
            curtailment_loss.append(round(value.curtailment_loss,3) if value.curtailment_loss is not None else value.curtailment_loss)
            module_temperature.append(round(value.average_module_temperature,3) if value.average_module_temperature is not None else value.average_module_temperature)
            ambient_temperature.append(round(value.average_ambient_temperature,3) if value.average_ambient_temperature is not None else value.average_ambient_temperature)
            plant_start_time.append(value.plant_start_time)
            plant_end_time.append(value.plant_stop_time)
            plant_run_time.append(value.plant_run_time)
        df_result['Date'] = timestamp
        df_result['Plant Start Time'] = plant_start_time
        df_result['Plant Stop Time'] = plant_end_time
        df_result['Plant Running Time'] = plant_run_time
        df_result['Estimated Generation (kWh)'] = estimated_generation
        df_result['generation (kWh)'] = generation
        df_result['PR (%)'] = pr
        df_result['DC CUF (%)'] = cuf
        df_result['AC CUF (%)'] = ac_cuf
        df_result['Specific Yield'] = specific_yield
        df_result['Estimated GHI (kWh/m^2)'] = estimated_ghi
        df_result['Insolation (kWh/m^2)'] = average_irradiation
        df_result['Module Temperature (C)'] = module_temperature
        df_result['Ambient Temperature (C)'] = ambient_temperature
        #df_result['Grid Availability (%)'] = grid_availability
        #df_result['Equipment Availability (%)'] = equipment_availability
        df_result['Curtailment Loss (kWh)'] = curtailment_loss
        df_result['DC Loss (kWh)'] = dc_loss
        df_result['Conversion Loss (kWh)'] = conversion_loss
        df_result['AC Loss (kWh)'] = ac_loss
        df_result.sort('Date')

        # get the inverters generation
        inverters = plant.independent_inverter_units.all()
        inverters_name = []
        for inverter in inverters:
            inverters_name.append(str(inverter.name))
        inverters_name = sorted_nicely(inverters_name)
        inverters = []
        for name in inverters_name:
            inverter = IndependentInverter.objects.get(plant=plant, name=name)
            inverters.append(inverter)
        for inverter in inverters:
            inverter_values = []
            #inverter_estimated_generation = []
            #inverter_curtailment_loss = []
            inverter_timestamp = []
            df_inverter = pd.DataFrame()
            df_operational_hours = pd.DataFrame()
            inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                            count_time_period=86400,
                                                                            identifier=str(inverter.sourceKey),
                                                                            ts__gte=starttime,
                                                                            ts__lte=endtime).order_by('ts')
            for value in inverter_generations:
                inverter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                #inverter_estimated_generation.append(round(float(value.estimated_generation),3) if value.estimated_generation is not None else value.estimated_generation)
                #inverter_curtailment_loss.append(round(float(value.curtailment_loss),3) if value.curtailment_loss is not None else value.curtailment_loss)
                inverter_timestamp.append(pd.to_datetime(value.ts))
            print inverter_values
            #df_inverter[str(inverter.name)+'_EST_GEN' + ' (kWh)'] = inverter_estimated_generation
            df_inverter[str(inverter.name)+' (kWh)'] = inverter_values
            #df_inverter[str(inverter.name)+'_Curtailment_Loss' + ' (kWh)'] = inverter_curtailment_loss
            df_inverter['Date'] = inverter_timestamp
            df_inverter.sort('Date')
            df_result = df_result.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')

            inverter_operational_values = []
            inverter_operational_timestamp = []
            for value in inverter_generations:
                if value.total_working_hours:
                    inverter_operational_values.append(round(float(value.total_working_hours),3) if value.total_working_hours is not None else value.total_working_hours)
                    inverter_operational_timestamp.append(pd.to_datetime(value.ts))
            if len(inverter_operational_values)>0:
                df_operational_hours[str(inverter.name)+'_Working_Hours'] = inverter_operational_values
                df_operational_hours['Date'] = inverter_operational_timestamp
                df_operational_hours.sort('Date')
            if not df_operational_hours.empty:
                df_result = df_result.merge(df_operational_hours.drop_duplicates('Date'), how='outer', on='Date')

        # get the meter generation
        meters = plant.energy_meters.all().filter(energy_calculation=True)
        meters_name = []
        for meter in meters:
            meters_name.append(str(meter.name))
        meters_name = sorted_nicely(meters_name)
        meters = []
        for name in meters_name:
            meter = EnergyMeter.objects.get(plant=plant, name=name)
            meters.append(meter)
        for meter in meters:
            meter_values = []
            meter_timestamp = []
            df_meter = pd.DataFrame()
            meter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                         count_time_period=86400,
                                                                         identifier=str(meter.sourceKey),
                                                                         ts__gte=starttime,
                                                                         ts__lte=endtime).order_by('ts')
            for value in meter_generations:
                meter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                meter_timestamp.append(pd.to_datetime(value.ts))
            df_meter[str(meter.name)+' (kWh)'] = meter_values
            df_meter['Date'] = meter_timestamp
            df_meter.sort('Date')
            df_result = df_result.merge(df_meter.drop_duplicates('Date'), how='outer', on='Date')

        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        out_path = "/var/tmp/monthly_report/atria/"+file_name
        writer = pd.ExcelWriter(out_path, engine='xlsxwriter')

        if not df_result.empty:
            df_result['Date'] = df_result['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
        df_result, l1, l2 = manipulateColumnNames(df_result, plant, 'Date')
        df_result.to_excel(writer, sheet_name=str(calendar.month_name[starttime.month]))
        sheetName = str(calendar.month_name[starttime.month])
        writer = excelConversion(writer, df_result, l1, l2, sheetName)
        #df_result.to_excel(writer, sheet_name=str(calendar.month_name[starttime.month]), index=False)
        writer.save()

    except Exception as exception:
        logger.debug("Exception in get_monthly_report_values_pandas_excel_atria === "+str(exception))
        print str(exception)


# Returns Normal Monthly Report with Single Sheet of Month Follows New Excel Format
def get_monthly_report_values_pandas_excel(starttime, endtime, plant):
    try:
        df_result = pd.DataFrame()
        df_inverter_all=pd.DataFrame()
        df_operational_hours_all=pd.DataFrame()
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        timestamp = []
        generation = []
        pr = []
        cuf = []
        specific_yield = []
        dc_loss = []
        conversion_loss = []
        ac_loss = []
        grid_availability  = []
        equipment_availability = []
        average_irradiation = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            generation.append(round(value.generation,3) if value.generation is not None else value.generation)
            pr.append(round(value.performance_ratio,3) if value.performance_ratio is not None else value.performance_ratio)
            cuf.append(round(value.cuf,3) if value.cuf is not None else value.cuf)
            specific_yield.append(round(value.specific_yield,3) if value.specific_yield is not None else value.specific_yield)
            dc_loss.append(round(value.dc_loss,3) if value.dc_loss is not None else value.dc_loss)
            conversion_loss.append(round(value.conversion_loss,3) if value.conversion_loss is not None else value.conversion_loss)
            ac_loss.append(round(value.ac_loss,3) if value.ac_loss is not None else value.ac_loss)
            grid_availability.append(round(value.grid_availability,3) if value.grid_availability is not None else value.grid_availability)
            equipment_availability.append(round(value.equipment_availability,3) if value.equipment_availability is not None else value.equipment_availability)
            average_irradiation.append(round(value.average_irradiation,3) if value.average_irradiation is not None else value.average_irradiation)
        df_result['Date'] = timestamp
        df_result['generation (kWh)'] = generation
        df_result['PR'] = pr
        df_result['CUF'] = cuf
        df_result['Specific Yield'] = specific_yield
        df_result['Grid Availability (%)'] = grid_availability
        df_result['Equipment Availability (%)'] = equipment_availability
        df_result['DC Loss (kWh)'] = dc_loss
        df_result['Conversion Loss (kWh)'] = conversion_loss
        df_result['AC Loss (kWh)'] = ac_loss
        df_result['Insolation (kWh/m^2)'] = average_irradiation
        df_result.sort_values('Date')

        # get the inverters generation
        inverters = plant.independent_inverter_units.all()
        inverters_name = []
        for inverter in inverters:
            inverters_name.append(str(inverter.name))
        inverters_name = sorted_nicely(inverters_name)
        inverters = []
        for name in inverters_name:
            inverter = IndependentInverter.objects.get(plant=plant, name=name)
            inverters.append(inverter)
        for inverter in inverters:
            inverter_values = []
            inverter_timestamp = []
            df_inverter = pd.DataFrame()
            df_operational_hours = pd.DataFrame()
            inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                            count_time_period=86400,
                                                                            identifier=str(inverter.sourceKey),
                                                                            ts__gte=starttime,
                                                                            ts__lte=endtime).order_by('ts')
            for value in inverter_generations:
                inverter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                inverter_timestamp.append(pd.to_datetime(value.ts))
            df_inverter[str(inverter.name)+' (kWh)'] = inverter_values
            df_inverter['Date'] = inverter_timestamp
            df_inverter.sort_values('Date')
            if df_inverter_all.empty:
                df_inverter_all=df_inverter
            else:
                df_inverter_all = df_inverter_all.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')

            inverter_operational_values = []
            inverter_operational_timestamp = []
            for value in inverter_generations:
                if value.total_working_hours:
                    inverter_operational_values.append(round(float(value.total_working_hours),3) if value.total_working_hours is not None else value.total_working_hours)
                    inverter_operational_timestamp.append(pd.to_datetime(value.ts))
            if len(inverter_operational_values)>0:
                df_operational_hours[str(inverter.name)+'_Working_Hours'] = inverter_operational_values
                df_operational_hours['Date'] = inverter_operational_timestamp
                df_operational_hours.sort_values('Date')
            if df_operational_hours_all.empty:
                df_operational_hours_all=df_operational_hours
            else:
                df_operational_hours_all = df_operational_hours_all.merge(df_operational_hours.drop_duplicates('Date'), how='outer', on='Date')

        if not df_inverter_all.empty:
            df_result = df_result.merge(df_inverter_all.drop_duplicates('Date'), how='outer', on='Date')
        if not df_operational_hours_all.empty:
            df_result = df_result.merge(df_operational_hours_all.drop_duplicates('Date'), how='outer', on='Date')

        # get the meter generation
        meters = plant.energy_meters.all().filter(energy_calculation=True)
        meters_name = []
        for meter in meters:
            meters_name.append(str(meter.name))
        meters_name = sorted_nicely(meters_name)
        meters = []
        for name in meters_name:
            meter = EnergyMeter.objects.get(plant=plant, name=name)
            meters.append(meter)
        for meter in meters:
            meter_values = []
            meter_timestamp = []
            df_meter = pd.DataFrame()
            meter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                         count_time_period=86400,
                                                                         identifier=str(meter.sourceKey),
                                                                         ts__gte=starttime,
                                                                         ts__lte=endtime).order_by('ts')
            for value in meter_generations:
                meter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                meter_timestamp.append(pd.to_datetime(value.ts))
            df_meter[str(meter.name)+' (kWh)'] = meter_values
            df_meter['Date'] = meter_timestamp
            df_meter.sort('Date')
            df_result = df_result.merge(df_meter.drop_duplicates('Date'), how='outer', on='Date')

        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        out_path = "/var/tmp/monthly_report/"+file_name
        writer = pd.ExcelWriter(out_path, engine='xlsxwriter')

        if not df_result.empty:
            df_result['Date'] = df_result['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
        df_result, l1, l2 = manipulateColumnNames(df_result, plant, 'Date')
        df_result.to_excel(writer, sheet_name=str(calendar.month_name[starttime.month]))
        sheetName = str(calendar.month_name[starttime.month])
        writer = excelConversion(writer, df_result, l1, l2, sheetName)

        # df_result.to_excel(writer, sheet_name=str(calendar.month_name[starttime.month]), index=False)
        writer.save()

    except Exception as exception:
        print str(exception)
        logger.debug("Exception in get_monthly_report_values_pandas_excel"+ str(exception))


def get_monthly_report_values_pandas_excel_sanjeevani_solar(starttime, endtime, plant):
    try:
        df_result = pd.DataFrame()
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        timestamp = []
        generation = []
        pr = []
        cuf = []
        specific_yield = []
        #dc_loss = []
        conversion_loss = []
        #ac_loss = []
        grid_availability  = []
        equipment_availability = []
        average_irradiation = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            generation.append(round(value.generation,3) if value.generation is not None else value.generation)
            pr.append(round(value.performance_ratio,3) if value.performance_ratio is not None else value.performance_ratio)
            cuf.append(round(value.cuf,3) if value.cuf is not None else value.cuf)
            specific_yield.append(round(value.specific_yield,3) if value.specific_yield is not None else value.specific_yield)
            #dc_loss.append(round(value.dc_loss,3) if value.dc_loss is not None else value.dc_loss)
            conversion_loss.append(round(value.conversion_loss,3) if value.conversion_loss is not None else value.conversion_loss)
            #ac_loss.append(round(value.ac_loss,3) if value.ac_loss is not None else value.ac_loss)
            grid_availability.append(round(value.grid_availability,3) if value.grid_availability is not None else value.grid_availability)
            equipment_availability.append(round(value.equipment_availability,3) if value.equipment_availability is not None else value.equipment_availability)
            average_irradiation.append(round(value.average_irradiation,3) if value.average_irradiation is not None else value.average_irradiation)
        df_result['Date'] = timestamp
        df_result['generation (kWh)'] = generation
        df_result['PR'] = pr
        df_result['CUF'] = cuf
        df_result['Specific Yield'] = specific_yield
        #df_result['Grid Availability (%)'] = grid_availability
        #df_result['Equipment Availability (%)'] = equipment_availability
        #df_result['DC Loss (kWh)'] = dc_loss
        #df_result['Conversion Loss (kWh)'] = conversion_loss
        #df_result['AC Loss (kWh)'] = ac_loss
        df_result['Insolation (kWh/m^2)'] = average_irradiation
        df_result.sort('Date')

        # get the inverters generation
        inverters = plant.independent_inverter_units.all()
        inverters_name = []
        for inverter in inverters:
            inverters_name.append(str(inverter.name))
        inverters_name = sorted_nicely(inverters_name)
        inverters = []
        for name in inverters_name:
            inverter = IndependentInverter.objects.get(plant=plant, name=name)
            inverters.append(inverter)
        for inverter in inverters:
            inverter_values = []
            inverter_timestamp = []
            df_inverter = pd.DataFrame()
            df_operational_hours = pd.DataFrame()
            inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                            count_time_period=86400,
                                                                            identifier=str(inverter.sourceKey),
                                                                            ts__gte=starttime,
                                                                            ts__lte=endtime).order_by('ts')
            for value in inverter_generations:
                inverter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                inverter_timestamp.append(pd.to_datetime(value.ts))
            df_inverter[str(inverter.name)+' (kWh)'] = inverter_values
            df_inverter['Date'] = inverter_timestamp
            df_inverter.sort('Date')
            df_result = df_result.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')

            inverter_operational_values = []
            inverter_operational_timestamp = []
            for value in inverter_generations:
                if value.total_working_hours:
                    inverter_operational_values.append(round(float(value.total_working_hours),3) if value.total_working_hours is not None else value.total_working_hours)
                    inverter_operational_timestamp.append(pd.to_datetime(value.ts))
            if len(inverter_operational_values)>0:
                df_operational_hours[str(inverter.name)+'_Working_Hours'] = inverter_operational_values
                df_operational_hours['Date'] = inverter_operational_timestamp
                df_operational_hours.sort('Date')
            if not df_operational_hours.empty:
                df_result = df_result.merge(df_operational_hours.drop_duplicates('Date'), how='outer', on='Date')

        # get the meter generation
        meters = plant.energy_meters.all().filter(energy_calculation=True)
        meters_name = []
        for meter in meters:
            meters_name.append(str(meter.name))
        meters_name = sorted_nicely(meters_name)
        meters = []
        for name in meters_name:
            meter = EnergyMeter.objects.get(plant=plant, name=name)
            meters.append(meter)
        for meter in meters:
            meter_values = []
            meter_timestamp = []
            df_meter = pd.DataFrame()
            meter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                         count_time_period=86400,
                                                                         identifier=str(meter.sourceKey),
                                                                         ts__gte=starttime,
                                                                         ts__lte=endtime).order_by('ts')
            for value in meter_generations:
                meter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                meter_timestamp.append(pd.to_datetime(value.ts))
            df_meter[str(meter.name)+' (kWh)'] = meter_values
            df_meter['Date'] = meter_timestamp
            df_meter.sort('Date')
            df_result = df_result.merge(df_meter.drop_duplicates('Date'), how='outer', on='Date')

        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        out_path = "/var/tmp/monthly_report/"+file_name
        writer = pd.ExcelWriter(out_path, engine='xlsxwriter')

        if not df_result.empty:
            df_result['Date'] = df_result['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
        df_result, l1, l2 = manipulateColumnNames(df_result, plant, 'Date')
        df_result.to_excel(writer, sheet_name=str(calendar.month_name[starttime.month]))
        sheetName = str(calendar.month_name[starttime.month])
        writer = excelConversion(writer, df_result, l1, l2, sheetName)

        #df_result.to_excel(writer, sheet_name=str(calendar.month_name[starttime.month]), index=False)
        writer.save()

    except Exception as exception:
        print str(exception)


def get_monthly_report_to_attach_in_email(plant):
    try:
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            current_time = timezone.now()
        initial_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        final_time = current_time
        month_start_day = initial_time.replace(day=1)
        month_end_day = final_time
        if str(plant.groupClient.slug)=='sanjeevani-solar':
            get_monthly_report_values_pandas_excel_sanjeevani_solar(month_start_day, month_end_day, plant)
        else:
            get_monthly_report_values_pandas_excel(month_start_day, month_end_day, plant)
    except Exception as exception:
        print(str(exception))

def get_monthly_report_to_attach_in_email_for_atria(plant):
    try:
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            current_time = timezone.now()
        final_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        #final_time = initial_time
        month_end_day = final_time - datetime.timedelta(days=1)
        month_start_day = month_end_day.replace(day=1)
        get_monthly_report_values_pandas_excel_atria(month_start_day, month_end_day, plant)
    except Exception as exception:
        print(str(exception))


def get_yearly_report_values(starttime, endtime, plant,accessible_features = None):
    try:
        logger.debug(accessible_features)
        df_result = pd.DataFrame()
        df_inverter_all = pd.DataFrame()
        df_operational_hours_all = pd.DataFrame()
        df_meter_all = pd.DataFrame()
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=2419200,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        timestamp = []
        generation = []
        pr = []
        cuf = []
        dc_loss = []
        conversion_loss = []
        ac_loss = []
        grid_availability  = []
        equipment_availability = []
        average_irradiation = []
        for value in plant_summary_values:
            #timestamp.append(pd.to_datetime(update_tz((value.ts.replace(hour=0, minute=0, second=0, microsecond=0)), plant.metadata.plantmetasource.dataTimezone).date()))
            timestamp.append(pd.to_datetime(value.ts))
            generation.append(round(value.generation,3) if value.generation is not None else value.generation)
            pr.append(round(value.performance_ratio*100,3) if value.performance_ratio is not None else value.performance_ratio)
            cuf.append(round(value.cuf*100,3) if value.cuf is not None else value.cuf)
            dc_loss.append(round(value.dc_loss,3) if value.dc_loss is not None else value.dc_loss)
            conversion_loss.append(round(value.conversion_loss,3) if value.conversion_loss is not None else value.conversion_loss)
            ac_loss.append(round(value.ac_loss,3) if value.ac_loss is not None else value.ac_loss)
            # grid_availability.append(round(value.grid_availability,3) if value.grid_availability is not None else value.grid_availability)
            # equipment_availability.append(round(value.equipment_availability,3) if value.equipment_availability is not None else value.equipment_availability)
            average_irradiation.append(round(value.average_irradiation,3) if value.average_irradiation is not None else value.average_irradiation)
        df_result[date_col_name] = timestamp
        df_result[generation_col_name] = generation
        df_result[pr_col_name] = pr
        df_result[cuf_col_name] = cuf
        # df_result[grid_avail_col_name] = grid_availability
        # df_result[equip_avail_col_name] = equipment_availability
        df_result[dc_loss_col_name] = dc_loss
        df_result[conversion_loss_col_name] = conversion_loss
        df_result[ac_loss_col_name] = ac_loss
        df_result[insolation_col_name] = average_irradiation
        if (accessible_features!=None and 'Energy Values From Inverters (kWh)' in accessible_features) or accessible_features==None:
            # get the inverters generation

            inverters = plant.independent_inverter_units.all()
            unsorted_inverter_names = inverters.values_list("name", flat=True)
            sorted_inverter_names = sorted_nicely(unsorted_inverter_names)
            for inverter_name in sorted_inverter_names:
                inverter = inverters.get(name=inverter_name)
                inverter_values = []
                inverter_timestamp = []
                df_inverter = pd.DataFrame()
                df_operational_hours = pd.DataFrame()
                inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                count_time_period=2419200,
                                                                                identifier=str(inverter.sourceKey),
                                                                                ts__gte=starttime,
                                                                            ts__lte=endtime).order_by('ts')
                for value in inverter_generations:
                    inverter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                    inverter_timestamp.append(pd.to_datetime(value.ts))
                df_inverter[str(inverter.name)+' (kWh)'] = inverter_values
                df_inverter['Date'] = inverter_timestamp
                df_inverter = df_inverter.round(3)
                if df_inverter_all.empty:
                    df_inverter_all = df_inverter
                else:
                    df_inverter_all = df_inverter_all.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')

                inverter_operational_values = []
                inverter_operational_timestamp = []
                for value in inverter_generations:
                    if value.total_working_hours:
                        inverter_operational_values.append(round(float(value.total_working_hours),3) if value.total_working_hours is not None else value.total_working_hours)
                        inverter_operational_timestamp.append(pd.to_datetime(value.ts))
                if len(inverter_operational_values)>0:
                    df_operational_hours[str(inverter.name)+' Working Hours'] = inverter_operational_values
                    df_operational_hours['Date'] = inverter_operational_timestamp
                    df_operational_hours.sort('Date')
                if df_operational_hours_all.empty:
                    df_operational_hours_all = df_operational_hours
                else:
                    df_operational_hours_all = df_operational_hours_all.merge(
                        df_operational_hours.drop_duplicates('Date'), how='outer', on='Date')
            if not df_inverter_all.empty:
                df_result = df_result.merge(df_inverter_all.drop_duplicates('Date'), how='outer', on='Date')
            if not df_operational_hours_all.empty:
                    df_result = df_result.merge(df_operational_hours_all.drop_duplicates('Date'), how='outer',
                                                on='Date')
        # Fetching Energy Meters Data
        if (accessible_features != None and 'Energy Meter(kWh)' in accessible_features) or (accessible_features == None):
            # get the meter generation
            meter_objects = plant.energy_meters.all().filter(energy_calculation=True)
            unsorted_meter_names = meter_objects.values_list("name", flat=True)
            sorted_meter_names = sorted_nicely(unsorted_meter_names)

            for meter_name in sorted_meter_names:
                meter = meter_objects.get(name=meter_name)
                meter_values = []
                meter_timestamp = []
                df_meter = pd.DataFrame()
                meter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                             count_time_period=2419200,
                                                                             identifier=str(meter.sourceKey),
                                                                             ts__gte=starttime,
                                                                         ts__lte=endtime).order_by('ts')
                for value in meter_generations:
                    meter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                    meter_timestamp.append(pd.to_datetime(value.ts))
                df_meter[str(meter.name)+' (kWh)'] = meter_values
                df_meter['Date'] = meter_timestamp
                if df_meter_all.empty:
                    df_meter_all= df_meter
                else:
                    df_meter_all = df_meter_all.merge(df_meter.drop_duplicates('Date'), how='outer', on='Date')
        if df_meter_all.empty:
            print "No meter values"
        else:
            df_result  = df_result.merge(df_meter_all.drop_duplicates('Date'), how='outer', on='Date')
        df_result_final = pd.DataFrame()
        if accessible_features != None:
            # col_list = ['Generation (kWh)', 'PR', 'CUF',
            #             'Grid Availability (%)', 'Equipment Availability (%)', 'DC Loss (kWh)',
            #             'Conversion Loss (kWh)', 'AC Loss (kWh)', 'Insolation (kWh/m^2)']
            col_list = ['Generation (kWh)', 'PR', 'CUF', 'DC Loss (kWh)',
                        'Conversion Loss (kWh)', 'AC Loss (kWh)', 'Insolation (kWh/m^2)']
            df_result_final['Date'] = df_result['Date']
            for col in col_list:
                if col in accessible_features:
                    df_result_final[col] = df_result[col]
            # As there is no 'Max Irradiance (kW/m^2)' feature , Mapping it to Insolution. Means If Insolution is there in accessible_features so the max Irradiance
            # if 'Insolation (kWh/m^2)' in accessible_features:
            #     df_result_final['Max Irradiance (kW/m^2)'] = df_result['Max Irradiance (kW/m^2)']
            if 'Energy Meter(kWh)' in accessible_features:
                if not df_meter_all.empty:
                    df_result_final = df_result_final.merge(df_meter_all.drop_duplicates('Date'), how='outer', on='Date')
            if 'Energy Values From Inverters (kWh)' in accessible_features:
                if not df_inverter_all.empty:
                    df_result_final = df_result_final.merge(df_inverter_all.drop_duplicates('Date'), how='outer',on='Date')
            # There is no feature associated with Total Operational Hours So mapping it with 'Generation (kWh)'
            if 'Generation (kWh)' in accessible_features:
                # Merge working hours of inverters
                if not df_operational_hours_all.empty:
                    logger.debug('df_op hours not empty trying to merge')
                    df_result_final = df_result_final.merge(
                        df_operational_hours_all.drop_duplicates('Date'), how='outer',on='Date')
            return df_result_final
        else:
            return df_result
    except Exception as exception:
        logger.debug("Exception in get_yearly_report_values :"+str(exception))
        print str(exception)
        return pd.DataFrame()


def generate_monthly_report_pdf(starttime, endtime, plant):
    try:
        html = "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.0 Transitional//EN' 'http://www.w3.org/TR/REC-html40/loose.dtd'>"+ \
                        "<html xmlns='http://www.w3.org/1999/xhtml'>"+ \
                        "<head>"+ \
                        "<meta name='viewport' content='width=device-width'>"+ \
                        "<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>"+ \
                        "<title>Actionable emails e.g. reset password</title>"+ \
                        "<style>"+ \
                         "{"+ \
                              "margin: 0;"+ \
                              "font-family: Verdana, Geneva, sans-serif;"+ \
                              "box-sizing: border-box;"+ \
                              "font-size: 14px;"+ \
                            "}"+ \
                            "img {"+ \
                              "max-width: 100%;"+ \
                            "}"+ \
                            "body {"+ \
                              "-webkit-font-smoothing: antialiased;"+ \
                              "-webkit-text-size-adjust: none;"+ \
                              "width: 100% !important;"+ \
                              "height: 100%;"+ \
                              "line-height: 1.6em;"+ \
                                "}"+ \
                                "table td {"+ \
                                  "vertical-align: top;"+ \
                                "}"+ \
                                "body {"+ \
                                  "background-color: #ecf0f5;"+ \
                                  "color: #6c7b88"+ \
                                "}"+ \
                                ".body-wrap {"+ \
                                  "background-color: #ecf0f5;"+ \
                                  "width: 100%;"+ \
                                "}"+ \
                                ".container {"+ \
                                  "display: block !important;"+ \
                                  "max-width: 600px !important;"+ \
                                  "margin: 0 auto !important;"+ \
                                  "/* makes it centered */"+ \
                                  "clear: both !important;"+ \
                                "}"+ \
                                ".content {"+ \
                                  "max-width: 600px;"+ \
                                  "margin: 0 auto;"+ \
                                  "display: block;"+ \
                                  "padding: 20px;"+ \
                                "}"+ \
                                ".main {"+ \
                                  "background-color: #fff;"+ \
                                  "border-bottom: 2px solid #d7d7d7;"+ \
                                "}"+ \
                                ".content-wrap {"+ \
                                  "padding: 20px;"+ \
                                "}"+ \
                                ".content-block {"+ \
                                  "padding: 0 0 20px;"+ \
                                "}"+ \
                                ".header {"+ \
                                  "width: 100%;"+ \
                                  "margin-bottom: 20px;"+ \
                                "}"+ \
                                ".footer {"+ \
                                  "width: 100%;"+ \
                                  "clear: both;"+ \
                                  "color: #999;"+ \
                                  "padding: 20px;"+ \
                                "}"+ \
                                ".footer p, .footer a, .footer td {"+ \
                                  "color: #999;"+ \
                                  "font-size: 12px;"+ \
                                "}"+ \
                                "h1, h2, h3 {"+ \
                                  "font-family: Verdana, Geneva, sans-serif;"+ \
                                  "color: #1a2c3f;"+ \
                                  "margin: 30px 0 0;"+ \
                                  "line-height: 1.2em;"+ \
                                  "font-weight: 400;"+ \
                                "}"+ \
                                "h1 {"+ \
                                  "font-size: 32px;"+ \
                                  "font-weight: 500;"+ \
                                "}"+ \
                                "h2 {"+ \
                                  "font-size: 24px;"+ \
                                "}"+ \
                                "h3 {"+ \
                                  "font-size: 18px;"+ \
                                "}"+ \
                                "h4 {"+ \
                                  "font-size: 14px;"+ \
                                  "font-weight: 600;"+ \
                                "}"+ \
                                "p, ul, ol {"+ \
                                  "margin-bottom: 10px;"+ \
                                  "font-weight: normal;"+ \
                                "}"+ \
                                "p li, ul li, ol li {"+ \
                                  "margin-left: 5px;"+ \
                                  "list-style-position: inside;"+ \
                                "}"+ \
                                "a {"+ \
                                  "color: #348eda;"+ \
                                  "text-decoration: underline;"+ \
                                "}"+ \
                                ".btn-primary {"+ \
                                  "text-decoration: none;"+ \
                                  "color: #FFF;"+ \
                                  "background-color: #42A5F5;"+ \
                                  "border: solid #42A5F5;"+ \
                                  "border-width: 10px 20px;"+ \
                                  "line-height: 2em;"+ \
                                  "font-weight: bold;"+ \
                                  "text-align: center;"+ \
                                  "cursor: pointer;"+ \
                                  "display: inline-block;"+ \
                                  "text-transform: capitalize;"+ \
                                "}"+ \
                                ".last {"+ \
                                  "margin-bottom: 0;"+ \
                                "}"+ \
                                ".first {"+ \
                                  "margin-top: 0;"+ \
                                "}"+ \
                                ".aligncenter {"+ \
                                  "text-align: center;"+ \
                                "}"+ \
                                ".alignright {"+ \
                                  "text-align: right;"+ \
                                "}"+ \
                                ".alignleft {"+ \
                                  "text-align: left;"+ \
                                "}"+ \
                                ".clear {"+ \
                                  "clear: both;"+ \
                                "}"+ \
                                ".alert {"+ \
                                  "font-size: 16px;"+ \
                                  "color: #fff;"+ \
                                  "font-weight: 500;"+ \
                                  "padding: 20px;"+ \
                                  "text-align: center;"+ \
                                "}"+ \
                                ".alert a {"+ \
                                  "color: #fff;"+ \
                                  "text-decoration: none;"+ \
                                  "font-weight: 500;"+ \
                                  "font-size: 16px;"+ \
                                "}"+ \
                                ".alert.alert-warning {"+ \
                                  "background-color: #FFA726;"+ \
                                "}"+ \
                                ".alert.alert-bad {"+ \
                                  "background-color: #ef5350;"+ \
                                "}"+ \
                                ".alert.alert-good {"+ \
                                  "background-color: #8BC34A;"+ \
                                "}"+ \
                                ".invoice {"+ \
                                  "margin: 25px auto;"+ \
                                  "text-align: left;"+ \
                                  "width: 100%;"+ \
                                "}"+ \
                                ".invoice td {"+ \
                                  "padding: 5px 0;"+ \
                                "}"+ \
                                ".invoice .invoice-items {"+ \
                                  "width: 100%;"+ \
                                "}"+ \
                                ".invoice .invoice-items td {"+ \
                                  "border-top: #eee 1px solid;"+ \
                                "}"+ \
                                ".invoice .invoice-items .total td {"+ \
                                  "border-top: 2px solid #6c7b88;"+ \
                                  "font-size: 18px;"+ \
                                "}"+ \
                                "@media only screen and (max-width: 640px) {"+ \
                                  "body {"+ \
                                    "padding: 0 !important;"+ \
                                  "}"+ \
                                  "h1, h2, h3, h4 {"+ \
                                    "font-weight: 800 !important;"+ \
                                    "margin: 20px 0 5px !important;"+ \
                                  "}"+ \
                                  "h1 {"+ \
                                    "font-size: 22px !important;"+ \
                                  "}"+ \
                                  "h2 {"+ \
                                    "font-size: 18px !important;"+ \
                                  "}"+ \
                                  "h3 {"+ \
                                    "font-size: 16px !important;"+ \
                                  "}"+ \
                                  ".container {"+ \
                                    "padding: 0 !important;"+ \
                                    "width: 100% !important;"+ \
                                  "}"+ \
                                  ".content {"+ \
                                    "padding: 0 !important;"+ \
                                  "}"+ \
                                  ".content-wrap {"+ \
                                    "padding: 10px !important;"+ \
                                  "}"+ \
                                  ".invoice {"+ \
                                    "width: 100% !important;"+ \
                                  "}"+ \
                                "}"+ \
                        "</style>"+ \
                        "</head>"+ \
                "<body itemscope itemtype='http://schema.org/EmailMessage' style='-webkit-font-smoothing: antialiased; -webkit-text-size-adjust: none; width: 100% !important; height: 100%; line-height: 1.6em; color: #6c7b88; background-color: #ecf0f5; padding: 0;' bgcolor='#ecf0f5'>"+ \
                "<h1><center> Bill for " + str(starttime) + " to " + str(endtime) +" </h1>"+ \
                "<table class='body-wrap' style='background-color: #ecf0f5; width: 100%;' bgcolor='#ecf0f5'>"
        df = get_monthly_report_values(starttime, endtime, plant)
        for line in df.to_html(bold_rows=True, index_names=False).split("\n"):
            html += str(line)
        html += "</table></center>"
        return html
    except Exception as exception:
        print(str(exception))


def get_generation_and_working_hours(starttime, endtime, plant):
    try:
        result = {}
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            result_temp = {}
            values = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                              count_time_period=86400,
                                                              identifier=str(inverter.sourceKey),
                                                              ts__gte=starttime,
                                                              ts__lte=endtime
                                                              ).values_list('generation', 'total_working_hours')
            generation_values = [float(item[0]) for item in values ]
            working_hour_values = [float(item[1]) for item in values ]
            result_temp['generation'] = str("{0:.2f}".format(sum(generation_values))) + ' kWh'
            result_temp['working_hours'] = str("{0:.2f}".format(sum(working_hour_values))) + ' hrs'
            result[str(inverter.name)] = result_temp
        return result
    except Exception as exception:
        print ("Error in gettting the details of devices : " + str(exception))

# method to return the summary values for any date
def get_daily_report_values(plant, date):
    try:
        try:
            tz = pytz.timezone(plant.metasource.plantmetasource.dataTimezone)
        except:
            tz = pytz.timezone("UTC")
        date = parser.parse(date)
        if date.tzinfo is None:
            date = tz.localize(date)
            date = date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        final_values = {}
        inverter_final_values = {}
        plant_values = {}
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts=time)
        if len(plant_summary_values)>0:
            value = plant_summary_values[0]
            plant_values[generation_col_name] = value.generation
            plant_values[pr_col_name] = value.performance_ratio
            plant_values[cuf_col_name] = value.cuf
            plant_values[specific_yield_col_name] = value.specific_yield
            plant_values[dc_loss_col_name] = value.dc_loss
            plant_values[conversion_loss_col_name] = value.conversion_loss
            plant_values[ac_loss_col_name] = value.ac_loss
            plant_values[grid_avail_col_name] = value.grid_availability
            plant_values[equip_avail_col_name] = value.equipment_availability
            plant_values[avg_irradiation_col_name] = value.average_irradiation
            plant_values['timestamp'] = str(value.ts)
        final_values['plant'] = plant_values
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            inverter_values = {}
            inverter_summary_values = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                               count_time_period=86400,
                                                                               identifier=str(inverter.sourceKey),
                                                                               ts=time)
            if len(inverter_summary_values)>0:
                value = inverter_summary_values[0]
                inverter_values[generation_col_name] = value.generation
                inverter_values['Total Working Hours'] = value.total_working_hours
                inverter_final_values[str(inverter.name)] = inverter_values
            else:
                inverter_final_values[str(inverter.name)] = {}

        final_values['inverters'] = inverter_final_values
        return final_values
    except Exception as exception:
        print str(exception)

def get_daily_report_values_portfolio(plants, date):
    try:
        df_final = pd.DataFrame()
        for plant in plants:
            df_plant = pd.DataFrame()
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=86400,
                                                                      identifier=str(plant.slug),
                                                                      ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
            print len(plant_summary_values)
            if len(plant_summary_values)>0:
                value = plant_summary_values[0]
                df_plant['Plant Name'] = [str(plant.name)]
                df_plant[generation_col_name] = [round(value.generation,2) if value.generation else 0.0]
                df_plant[pr_col_name] = [round(value.performance_ratio,2) if value.performance_ratio else 0.0]
                df_plant[cuf_col_name] = [round(value.cuf,2) if value.cuf else 0.0]
                df_plant[specific_yield_col_name] = [round(value.specific_yield,2) if value.specific_yield else 0.0]
                df_plant[dc_loss_col_name] = [round(value.dc_loss,2) if value.dc_loss else 0.0]
                df_plant[conversion_loss_col_name] = [round(value.conversion_loss,2) if value.conversion_loss else 0.0]
                df_plant[ac_loss_col_name] = [round(value.ac_loss,2) if value.ac_loss else 0.0]
                df_plant[grid_avail_col_name] = [round(value.grid_availability,2) if value.grid_availability else 0.0]
                df_plant[equip_avail_col_name] = [round(value.equipment_availability,2) if value.equipment_availability else 0.0]
                df_plant[avg_irradiation_col_name] = [round(value.average_irradiation,2) if value.average_irradiation else 0.0]
            if df_final.empty and not df_plant.empty:
                df_final = df_plant
            elif not df_plant.empty:
                df_final = df_final.append(df_plant)
            else:
                pass
        return df_final
    except Exception as exception:
        print str(exception)


# NewMod: Creates Excel Files for send_user_customised_daily_performance_report
def excel_creation_for_user_customised_daily_performance_report(file_name,plants,date):
    plant = plants[0]

    out_path = "/var/tmp/monthly_report/test_daily/" + file_name
    pandasWriter = pd.ExcelWriter(out_path, engine='xlsxwriter')

    try:
        daily_summary_report = get_daily_report_values_portfolio(plants, date)
        daily_summary_report.rename(columns={'Average Irradiation (kWh/m^2)': 'Insolation'}, inplace=True)
        # s=daily_summary_report.sum()
        # s[0]='Total'
        # daily_summary_report=daily_summary_report.replace(0,np.nan)
        summary_dict = {}
        # summary_dict['client_name']=plants[0].groupClient.name

        summary_dict['plants']= ",".join(plant.name for plant in plants)
        # cap = 0.0
        # for p in plants:
        #     cap = cap + p.capacity
        #     # print p.capacity
        # summary_dict['capacity'] = cap

        summary = []
        summary.append('Summary')
        sumlist = ['Generation (kWh)', 'DC Loss (kWh)', 'Conversion Loss (kWh)', 'AC Loss (kWh)']
        meanlist = ['PR', 'CUF', 'Specific Yield', 'Grid Availability (%)', 'Equipment Availability (%)',
                    'Insolation']
        for col in list(daily_summary_report):
            if col in sumlist:
                val = sum(daily_summary_report[col])
                print col, val
                summary.append(val)
                summary_dict[col] = val
            elif col in meanlist:
                col_vals = daily_summary_report[col]
                col_vals = col_vals.replace(0, np.nan)
                val = col_vals.mean()
                print col, val
                summary.append(val)
                summary_dict[col] = val
            else:
                print col, "Not handled"
        daily_summary_report.loc[daily_summary_report.shape[0]] = summary
        daily_summary_report, l1, l2 = manipulateColumnNames2(daily_summary_report, 'Plant Name')
        sheetName = 'PLANT_SUMMARY'
        daily_summary_report.to_excel(pandasWriter, sheet_name='PLANT_SUMMARY')
        pandasWriter = excelConversion(pandasWriter, daily_summary_report, l1, l2, sheetName)
        pandasWriter.save()
        return summary_dict
    except Exception as e:
        print "Inside exception of excel_creation_for_user_customised_daily_performance_report", e
        logger.debug("Inside exception of excel_creation_for_user_customised_daily_performance_report"+str(e))
        # pandasDataFrame = pandasDataFrame.set_index('Timestamp')
        sheetName='PLANT_SUMMARY'
        daily_summary_report.to_excel(pandasWriter, sheet_name=sheetName)
        pandasWriter = excelNoData(pandasWriter, daily_summary_report, sheetName)
        pandasWriter.save()
        return None


def update_timestamps(starttime, endtime, plant):
    try:
        try:
            tz = pytz.timezone(plant.metadata.dataTimezone)
            starttime = tz.localize(starttime)
            endtime = tz.localize(endtime)
        except Exception as e:
            tz = pytz.timezone('UTC')
            starttime = tz.localize(starttime)
            endtime = tz.localize(endtime)
        return starttime, endtime
    except:
        return starttime, endtime


def get_data_for_daily_gen_report_cleanmax(starttime, endtime, plant):
    try:
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts').values_list('ts',
                                                                                                              'generation',
                                                                                                              'average_irradiation',
                                                                                                              'specific_yield',
                                                                                                              'inverter_generation',
                                                                                                              'performance_ratio')

        df = pd.DataFrame(list(plant_summary_values),
                          columns=['ts', 'generation', 'average_irradiation', 'specific_yield', 'inverter_generation',
                                   'performance_ratio'])
        # df['ts'] = df['ts'].apply(lambda x: x.date())
        df = df.rename(columns={'ts': 'Date'})
        df['performance_ratio'] = df['performance_ratio'] * 100
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize('UTC').dt.tz_convert("Asia/Kolkata")

        df = df.set_index('Date')
        for col in set(list(df)) - set('Date'):
            df[col] = df[col].apply(lambda x: round(x, 2))

        # df_final = df_result.sort("ts").reset_index(drop=True)
        return df
    except Exception as exception:
        logger.debug(str(exception))


def get_inverters_data_for_one_day(endtime, plant):
    try:
        inverters_sourceKeys = list(plant.independent_inverter_units.all().values_list('sourceKey', flat=True))
        gen = sum(list(
            PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL', count_time_period=86400,
                                                     identifier__in=inverters_sourceKeys,
                                                     ts__gte=endtime.replace(hour=0, minute=0, second=0, microsecond=0),
                                                     ts__lt=endtime.replace(hour=0, minute=0, second=0,
                                                                            microsecond=0) + timedelta(
                                                         days=1)).values_list('generation', flat=True)))
        return gen
    except Exception as exception:
        logger.debug("Exception :" + str(exception))
        return 0


from solarrms.models import PVSystInfo


def get_pvsyst_data_for_one_day(st, plant):
    try:

        pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName__in=['PRODUCED_ENERGY',
                                                                              'GHI_IRRADIANCE',
                                                                              'PERFORMANCE_RATIO'],
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodValue=st.month,
                                                           timePeriodYear__in=[st.year, 0]).values_list(
            'timePeriodValue', 'parameterName', 'parameterValue', 'solar_group_id')
        d = {}
        if len(pv_sys_info_generation) > 0:
            df = pd.DataFrame(list(pv_sys_info_generation))
            df.columns = ['timePeriodValue', 'parameterName', 'parameterValue', 'solar_group_id']
            # As there can be different groups we need to combine data for multiple groups of a plant
            gdf = df.groupby(['parameterName', 'timePeriodValue'])
            d['Plant'] = plant.slug
            for g in gdf:
                if g[0][0] == 'PERFORMANCE_RATIO':
                    d[g[0][0]] = g[1].mean()['parameterValue']
                else:
                    d[g[0][0]] = g[1].sum()['parameterValue']
        else:
            print "No data in PVSystInfo", plant
        data_dict = {}
        if len(d.keys()) > 0:
            no_of_days_of_month_in_st = (st.replace(month=(st.month + 1)) - st).days
            # days_in_st_month = no_of_days_of_month_in_st - st.day + 1
            data_dict['produced_energy_per_day'] = (d['PRODUCED_ENERGY'] / no_of_days_of_month_in_st) * 1000
            data_dict['ghi_irradiance_per_day'] = d['GHI_IRRADIANCE'] / no_of_days_of_month_in_st
            if plant.slug == 'omya':
                data_dict['ghi_irradiance_per_day'] = data_dict['ghi_irradiance_per_day'] / 7.0
            data_dict['performance_ratio_per_day'] = d['PERFORMANCE_RATIO']
        return data_dict
    except Exception as e:
        return {}
        logger.debug(str(e))


def df_leveler2(st, et, plant, df):
    try:
        df = df.reset_index()
        df_empty = pd.DataFrame(columns=list(df))
        df_empty['Date'] = pd.date_range(st, et)
        df_empty['Date'] = pd.to_datetime(df_empty['Date']).dt.tz_localize("Asia/Kolkata")
        df = df.merge(df_empty, how="outer", on="Date")
        df = df.sort('Date')
        return df
    except Exception as e:
        logger.debug("Exception in df_leveler2 " + str(e))
        return df


def get_group_data_for_one_day(endtime, group):
    try:
        inverters_sourceKeys = list(group.groupIndependentInverters.all().values_list('sourceKey', flat=True))
        gen = sum(list(
            PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL', count_time_period=86400,
                                                     identifier__in=inverters_sourceKeys,
                                                     ts__gte=endtime.replace(hour=0, minute=0, second=0, microsecond=0),
                                                     ts__lt=endtime.replace(hour=0, minute=0, second=0,
                                                                            microsecond=0) + timedelta(
                                                         days=1)).values_list('generation', flat=True)))
        return gen
    except Exception as exception:
        logger.debug("Exception :" + str(exception))
        return 0
        print str(exception)


# from .views import feature_dynamic_pdf_ids_feature_ids
# custom_feature_set = {1608L: {'feature_chart_type': None, 'feature_type': None, 'feature_columns': None, 'feature_order': 2, 'feature_title': u'Inverter Production custom title', u'id': 31L, 'feature_description': None, 'feature_unit': None},
#                       1644L: {'feature_chart_type': None, 'feature_type': None, 'feature_columns': None, 'feature_order': 5, 'feature_title': u'PR metrics', u'id': 33L, 'feature_description': None, 'feature_unit': None},
#                       1612L: {'feature_chart_type': None, 'feature_type': None, 'feature_columns': None, 'feature_order': 2, 'feature_title': u'One Day Plant Prod', u'id': 30L, 'feature_description': None, 'feature_unit': None}}
def gen_daily_report_cleanmax(plant, endtime, custom_feature_set):
    try:
        logger.debug("Fetching context for cleanmax daily report: " + (plant.slug))
        # endtime=datetime.datetime.now().replace(hour=23,minute=0,second=0,microsecond=0)
        endtime = endtime.replace(hour=23, minute=0, second=0, microsecond=0)
        td30 = timedelta(days=29)
        starttime = endtime - td30
        starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
        # plant = SolarPlant.objects.get(slug=plant_slug)
        # starttime,endtime = update_timestamps(starttime, endtime, plant)

        context = dict()
        context['plant_capacity'] = plant.capacity
        context['plant_name'] = plant.name
        context['plant_address'] = plant.location
        context['client_name'] = plant.groupClient.name
        context['client_address'] = plant.groupClient.clientContactAddress
        context['period'] = datetime.datetime.now()

        try:
            context['plant_client_logo'] = plant.groupClient.clientLogo \
                if plant.groupClient.clientLogo else plant.dataglengroup.groupLogo
            # fetch file extension and conver it to base64
            image_file_extension = context['plant_client_logo'].split(".")[-1]
            response = requests.get(context['plant_client_logo'])
            context['plant_client_logo'] = " data:image/%s;base64,%s" % (
                image_file_extension, base64.b64encode(response.content))
        except:
            context['plant_client_logo'] = ""

        try:
            context['plant_group_client_logo'] = plant.dataglengroup.groupLogo \
                if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
            # fetch file extension and conver it to base64
            image_file_extension = context['plant_group_client_logo'].split(".")[-1]
            response = requests.get(context['plant_group_client_logo'])
            context['plant_group_client_logo'] = " data:image/%s;base64,%s" % (
                image_file_extension, base64.b64encode(response.content))
        except:
            context['plant_group_client_logo'] = ""

        context['starttime'] = str(starttime.strftime("%d-%b-%Y"))
        context['endtime'] = str(endtime.strftime("%d-%b-%Y"))
        context['endtime_formatted'] = endtime.strftime("%A %d %B %Y")

        df = get_data_for_daily_gen_report_cleanmax(starttime, endtime, plant)
        if df.empty:
            return context
        df = df_leveler2(starttime, endtime, plant, df)
        df = df.set_index('Date')
        df2 = df.reset_index()
        groups = plant.solar_groups.all()
        group_dict = {}

        for sgroup in groups:
            group_inverters = sgroup.groupIndependentInverters.all()
            group_capacity = 0
            for group_inv in group_inverters:
                group_capacity = group_capacity + group_inv.actual_capacity
            group_dict[sgroup.name] = {'no_of_inverters': len(group_inverters), 'group_capacity': group_capacity}
        group_inv_info = ""
        for k, v in group_dict.items():
            group_inv_info = group_inv_info + str(v['no_of_inverters']) + "-" + k + ", "
        context['group_inv_info'] = group_inv_info[:-2]
        td = timedelta(days=7)
        weekdaystart = endtime - td
        context['weekdaystart'] = weekdaystart.strftime("%d-%B-%Y")
        list_of_days = []
        for d_delta in range(6, -1, -1):
            day = endtime.replace(hour=0) - timedelta(days=d_delta)
            list_of_days.append(day)
        context['list_of_days'] = list_of_days

        for item in range(len(list_of_days)):
            context['list_of_days' + str(item)] = (list_of_days[item]).strftime("%d-%m-%Y")
        order_of_sections = {}

        # 1618:POWER_CHART_GENERATION
        if 1618 in custom_feature_set:
            gen_vs_irr_feature = custom_feature_set[1618]
            context['gen_vs_irr_feature_order'] = gen_vs_irr_feature[
                'feature_order'] if 'feature_order' in gen_vs_irr_feature else 1
            order_of_sections[context['gen_vs_irr_feature_order']] = "gen_vs_irr_feature_order"
            context['gen_vs_irr_feature_title'] = gen_vs_irr_feature[
                'feature_title'] if 'feature_title' in gen_vs_irr_feature and gen_vs_irr_feature[
                'feature_title'] else "Generation Vs Irradiation Chart"

            print "1 - Generation v/s Irradiance (Daily- for Month) (from ", starttime, " to ", endtime, ")"
            list_gen_irr = []

            for item in range(df.shape[0]):
                dict_temp = {}
                dt = df2['Date'].iloc[item]
                dict_temp["timestamp"] = str(
                    str(datetime.datetime(dt.year, dt.month, dt.day, 0, 0).date()) + "T00:00:00Z")
                dict_temp["generation"] = df2['generation'].iloc[item]
                dict_temp["insolation"] = df2['average_irradiation'].iloc[item]
                # print dict_temp
                list_gen_irr.append(dict_temp)

            context['list_gen_irr'] = json.dumps(list_gen_irr)
            gen = list(df['generation'])
            irradiance = list(df['average_irradiation'])
            context['gen'] = gen
            context['irradiance'] = irradiance
            # context['statement_period']=endtime.strftime("%A %d %B %Y")
        else:
            context['gen_vs_irr_feature_order'] = 101

        # 1612:TOTAL_ENERGY_GENERATION
        if 1612 in custom_feature_set:
            prod_statement_for_a_day = custom_feature_set[1612]
            context['prod_statement_for_a_day_order'] = prod_statement_for_a_day[
                'feature_order'] if 'feature_order' in prod_statement_for_a_day and prod_statement_for_a_day[
                'feature_order'] else 2
            order_of_sections[context['prod_statement_for_a_day_order']] = "prod_statement_for_a_day_order"
            context['prod_statement_for_a_day_title'] = prod_statement_for_a_day[
                'feature_title'] if 'feature_title' in prod_statement_for_a_day and prod_statement_for_a_day[
                'feature_title'] else "Production Statement for the period"

            print "2 - Inverter production statement for the period : (", endtime.strftime("%A %d %B %Y"), ")"
            # storing plant generation in inv_prod_kwh
            inv_prod_kwh = df.at[endtime.replace(hour=0), 'generation']
            context['inv_prod_kwh'] = inv_prod_kwh
            inv_prod_yield = df.at[endtime.replace(hour=0), 'specific_yield']
            one_day_insolation = df.at[endtime.replace(hour=0), 'average_irradiation']
            one_day_pr = df.at[endtime.replace(hour=0), 'performance_ratio']
            context['inv_prod_yield'] = inv_prod_yield
            context['one_day_insolation'] = one_day_insolation
            context['one_day_pr'] = one_day_pr
            forecasted_value = 0

            data_dict = get_pvsyst_data_for_one_day(endtime, plant)
            if len(data_dict.keys()) == 3:
                forecasted_value = round(data_dict['produced_energy_per_day'], 2)
            else:
                forecasted_value = ''
            print "FORCASTED VALUE PVSYST= ", forecasted_value
            context['forecasted_value'] = forecasted_value
        else:
            context['prod_statement_for_a_day_order'] = 102

        # 1608:INVERTER_ENERGY_GENERATION
        if 1608 in custom_feature_set:
            inverter_prduction = custom_feature_set[1608]
            context['inverter_prduction_order'] = inverter_prduction['feature_order'] if 'feature_order' in \
                                                                                         inverter_prduction and \
                                                                                         inverter_prduction[
                                                                                             'feature_order'] else 3
            order_of_sections[context['inverter_prduction_order']] = "inverter_prduction_order"

            context['inverter_prduction_title'] = inverter_prduction['feature_title'] if \
                'feature_title' in inverter_prduction and inverter_prduction[
                    'feature_title'] else "Summary of Production (Inverter)"

            print "3 - Summary of Production (Inverter) (Last 7 days) (from ", weekdaystart, " to ", endtime
            list_of_inv_gen = []
            for d_delta in range(6, -1, -1):
                day = endtime.replace(hour=0) - timedelta(days=d_delta)
                if d_delta == 0:
                    inv_data = round(get_inverters_data_for_one_day(endtime, plant), 2)
                    list_of_inv_gen.append(inv_data)
                else:
                    list_of_inv_gen.append(df.at[day, 'inverter_generation'])

            context['list_of_inv_gen'] = list_of_inv_gen
            for item in range(len(list_of_inv_gen)):
                context['list_of_inv_gen' + str(item)] = list_of_inv_gen[item]

            print "3.1 adding groups"
            groups_data = []
            t1 = int(round(time.time() * 1000))
            logger.debug("The start time: %s " % t1)
            for group in groups:
                weeks_data = {}
                weeks_data['group_name'] = group.name + " (" + str(group_dict[group.name]['group_capacity']) + "kWp)"
                for d_delta in range(6, -1, -1):
                    day = endtime.replace(hour=0) - timedelta(days=d_delta)
                    group_gen = round(get_group_data_for_one_day(day, group), 2)
                    logger.debug("group data === %s" % group_gen)
                    # print group.name, day, group_gen
                    weeks_data[str(6 - d_delta)] = group_gen
                groups_data.append(weeks_data)
            t2 = int(round(time.time() * 1000))
            logger.debug("The time taken for group calc is : %s " % (t2 - t1))

            context['groups_weeks_inverter_gen'] = groups_data
        else:
            context['inverter_prduction_order'] = 103


        # 1616:METER_POWER_GENERATION
        if 1616 in custom_feature_set:
            meter_production = custom_feature_set[1616]
            context['meter_production_order'] = meter_production[
                'feature_order'] if 'feature_order' in meter_production and meter_production['feature_order'] else 4
            order_of_sections[context['meter_production_order']] = "meter_production_order"

            context['meter_production_title'] = meter_production[
                'feature_title'] if 'feature_title' in meter_production and meter_production[
                'feature_title'] else "Summary of Production (Energy Meters)"

            print "3.5 - Summary of Production (Energy Meter) (Last 7 days) (from ", weekdaystart, " to ", endtime
            # df_meter= get_energy_meter_value_for_range(starttime, endtime, plant)
            if_meter_exists = len(plant.energy_meters.all())

            if not if_meter_exists:
                context['energy_meter_available'] = 0
                logger.debug("No Meters Found 000000")
            else:
                context['energy_meter_available'] = 1
                # df_meter = df_leveler2(starttime, endtime, plant, df_meter)

                # list_of_days = [(endtime - timedelta(days=d)).date() for d in range(6, -1, -1)]
                # df_meter=df_meter.set_index('Date')
                list_of_meter_val = []
                for day in list_of_days:
                    list_of_meter_val.append(df.at[day, 'generation'])
                context['list_of_meter_val'] = list_of_meter_val
                for item in range(len(list_of_meter_val)):
                    context['list_of_meter_val' + str(item)] = list_of_meter_val[item]
        else:
            context['meter_production_order'] = 104

        # 1644:PR_METRICS
        if 1644 in custom_feature_set:
            pr_vals = custom_feature_set[1644]
            context['pr_vals_order'] = pr_vals['feature_order'] if 'feature_order' in pr_vals \
                                                                   and pr_vals['feature_order'] else 5
            order_of_sections[context['pr_vals_order']] = "pr_vals_order"

            context['pr_vals_title'] = pr_vals['feature_title'] if 'feature_title' in pr_vals \
                                                                   and pr_vals['feature_title'] else "Daily Performance Ratio"

            print "4 - Performance Ratio daily (7 days) (from ", starttime, " to ", endtime, ")"
            print "4.1 adding groups pr"
            groups_pr_data = []
            # groups = plant.solar_groups.all()
            from solarrms.solargrouputils import get_solar_groups_pr_cuf_sy
            for group in groups:
                weeks_pr_data = {}
                weeks_pr_data['group_name'] = group.name
                for d_delta in range(6, -1, -1):
                    day = endtime.replace(hour=0) - timedelta(days=d_delta)
                    st = day.replace(hour=0, minute=0, second=0, microsecond=0)
                    et = day.replace(hour=23, minute=59, second=59, microsecond=0)

                    group_pr, cuf, sy = get_solar_groups_pr_cuf_sy(st, et, group, plant)
                    # print group.name, day, group_gen
                    weeks_pr_data[str(6 - d_delta)] = round(group_pr * 100, 2)
                groups_pr_data.append(weeks_pr_data)
            context['groups_weeks_pr'] = groups_pr_data
            # print groups_pr_data

            list_of_pr = []
            for d_delta in range(6, -1, -1):
                day = endtime.replace(hour=0) - timedelta(days=d_delta)
                list_of_pr.append(df.at[day, 'performance_ratio'])
            for item in range(len(list_of_pr)):
                context['list_of_pr' + str(item)] = list_of_pr[item]

            # ******Calculation For PR line graph*****
            # pr_week_list_of_dict = []
            # for i in range(len(list_of_pr)):
            #     dt = list_of_days[i]
            #     day_tz_format = str(str(datetime.datetime(dt.year, dt.month, dt.day, 0, 0).date()) + "T00:00:00Z")
            #     # print str(str(datetime.datetime(dt.year, dt.month, dt.day, 0, 0).date()) + "T00:00:00Z")
            #     pr_week_dict = {"pr": list_of_pr[i], "day": day_tz_format }
            #     # print pr_week_dict
            #     pr_week_list_of_dict.append(pr_week_dict)
            #     context['list_of_pr' + str(item)] = list_of_pr[item]
            #
            #
            #
            # context['pr_week_list_of_dict']=json.dumps(pr_week_list_of_dict)
        else:
            context['pr_vals_order'] = 105

        # 1630:TOTAL_CAPACITY_PLANT_DETAILS
        if 1630 in custom_feature_set:
            plant_desc = custom_feature_set[1630]
            context['plant_desc_order'] = plant_desc['feature_order'] if 'feature_order' in plant_desc and plant_desc[
                'feature_order'] else 6
            order_of_sections[context['plant_desc_order']] = "plant_desc_order"

            context['plant_desc_title'] = plant_desc['feature_title'] if 'feature_title' in plant_desc and plant_desc[
                'feature_title'] else " Plant Details "
            print "5 - Plant(s) Description"
            import collections
            invs = plant.independent_inverter_units.all()
            models = []
            for i in invs:
                models.append(i.manufacturer + "-" + i.model)
            inverters_dict = collections.Counter(models)
            no_of_inverters = ''
            for key in inverters_dict:
                no_of_inverters = no_of_inverters + str(inverters_dict[key]) + " - " + key + " "
            context['no_of_inverters'] = no_of_inverters
            # print "Inverters Data: ", no_of_inverters
            solar_modules = str(
                plant.metadata.no_of_panels) + "-" + plant.metadata.panel_manufacturer + " " + plant.metadata.model_number + " " + str(
                plant.metadata.panel_capacity)
            context['solar_modules'] = solar_modules
            # print "Solar Modules",solar_modules

            all_sensors = plant.metadata.io_sensors.all().values('stream_type')
            if all_sensors:
                module_temp = 0
                amb_temp = 0
                irradiation_sensor = 0
                for sen in all_sensors:
                    if sen['stream_type'] == 'MODULE_TEMPERATURE':
                        module_temp = module_temp + 1
                    if sen['stream_type'] == 'AMBIENT_TEMPERATURE':
                        amb_temp = amb_temp + 1
                    if sen['stream_type'] == 'IRRADIATION':
                        irradiation_sensor = irradiation_sensor + 1
                context['sensor_data'] = "%s-Module Temp," % module_temp + \
                                         " %s-Ambient Temp," % amb_temp + \
                                         " %s-Irradiation Sensor" % irradiation_sensor
                context['total_sensors'] = module_temp + amb_temp + irradiation_sensor
                context['total_solar_modules'] = str(plant.metadata.no_of_panels)
        else:
            context['plant_desc_order'] = 106

        if df.empty:
            context['gen_values'] = 0
        else:
            context['gen_values'] = 1

        context['plant_commissioned_date'] = plant.commissioned_date
        logger.debug("Context is calculated successfully....")
        now = datetime.datetime.now()
        context['copyright_year'] = str(now.year)
        list_order = []
        for order_id in sorted(order_of_sections):
            list_order.append(str(order_of_sections[order_id]))
        context['order'] = list_order
        return context

    except Exception as e:
        logger.debug("Exception===============>>>" + str(e))
        return context

from dataglen.models import ValidDataStorageByStream
from calendar import monthrange
def gen_monthly_report_cleanmax(plant, endtime):
    try:
        logger.debug("Fetching context for cleanmax monthly report: " + (plant.slug))
        days_in_month = monthrange(endtime.year, endtime.month)
        starttime = endtime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        endtime = endtime.replace(day= days_in_month[1], hour=23, minute=59, second=59, microsecond=0)


        context = {}
        context['plant_capacity'] = plant.capacity
        context['plant_name'] = plant.name
        context['plant_address'] = plant.location
        context['client_name'] = plant.groupClient.name
        context['client_address'] = plant.groupClient.clientContactAddress
        context['period'] = datetime.datetime.now()

        try:
            context['plant_client_logo'] = plant.groupClient.clientLogo \
                if plant.groupClient.clientLogo else plant.dataglengroup.groupLogo
            # fetch file extension and conver it to base64
            image_file_extension = context['plant_client_logo'].split(".")[-1]
            response = requests.get(context['plant_client_logo'])
            context['plant_client_logo'] = " data:image/%s;base64,%s" % (
                image_file_extension, base64.b64encode(response.content))
        except:
            context['plant_client_logo'] = ""

        try:
            context['plant_group_client_logo'] = plant.dataglengroup.groupLogo \
                if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
            # fetch file extension and conver it to base64
            image_file_extension = context['plant_group_client_logo'].split(".")[-1]
            response = requests.get(context['plant_group_client_logo'])
            context['plant_group_client_logo'] = " data:image/%s;base64,%s" % (
                image_file_extension, base64.b64encode(response.content))
        except:
            context['plant_group_client_logo'] = ""

        context['starttime'] = str(starttime.strftime("%d-%b-%Y"))
        context['endtime'] = str(endtime.strftime("%d-%b-%Y"))
        context['endtime_formatted'] = endtime.strftime("%A %d %B %Y")
        # 1613:ENERGY_GENERATION
        # if 1613 in custom_feature_set:
        if True:
            context['energy_meter_order'] = 1
            groups = plant.solar_groups.all()
            plant_energy_meters = plant.energy_meters.all().filter(energy_calculation=True)
            groups_meter_gen = []
            meters_with_groups_assigned = []
            plant_total_generation_from_meter = 0
            plant_total_capacity_meter = 0
            # If only one energy meter is present, dont show multiple groups.
            if len(plant_energy_meters) == 1:
                # set table column name as plant name as we are not showing groups
                context['title_group_name'] = 'Plant Name'
                one_meter_data = {}
                one_meter_data['name'] = plant.name
                meter = plant_energy_meters[0]
                one_meter_data['group_name'] = meter.name
                one_meter_data['group_capacity'] = plant.capacity
                stream = 'Wh_RECEIVED'
                output = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey, stream_name=stream,
                                                                 timestamp_in_data__gte=starttime,
                                                                 timestamp_in_data__lte=endtime).limit(0).order_by(
                    'timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

                one_meter_data['starttime_meter_reading'] = round(float(output.first()[0]), 2)
                one_meter_data['endtime_meter_reading'] = round(float(output[len(output) - 1][0]), 2)
                one_meter_data['total_billing_units'] = one_meter_data['endtime_meter_reading'] - one_meter_data[
                    'starttime_meter_reading']
                plant_total_generation_from_meter = plant_total_generation_from_meter + one_meter_data[
                    'total_billing_units']

                groups_meter_gen.append(one_meter_data)
            # if no of energy meters are more than one then try to assign each energy meter to groups
            else:
                context['title_group_name'] = 'Group Name'

                for group in groups:
                    print group
                    group_meters = group.groupEnergyMeters.all()
                    if len(group_meters)!= 1:
                        group_capacity = "--"
                    else:
                        group_capacity = sum(list(group.groupIndependentInverters.all(). \
                                                  values_list('total_capacity', flat=True)))
                        plant_total_capacity_meter = plant_total_capacity_meter + group_capacity
                    if group_meters:
                        for meter in group_meters:
                            meters_with_groups_assigned.append(meter)
                            one_meter_data = {}
                            one_meter_data['name'] = meter.name
                            one_meter_data['group_name'] = group.name
                            one_meter_data['group_capacity'] = group_capacity

                            if meter:
                                # meter = group_meters[0]
                                print "1 - Energy meter counter values (from ", starttime, " to ", endtime, ")"
                                stream = 'Wh_RECEIVED'
                                output = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey, stream_name=stream,
                                                                                 timestamp_in_data__gte=starttime,
                                                                                 timestamp_in_data__lte=endtime).limit(0).order_by(
                                    'timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

                                one_meter_data['starttime_meter_reading'] = round(float(output.first()[0]),2)
                                one_meter_data['endtime_meter_reading'] = round(float(output[len(output)-1][0]),2)
                                one_meter_data['total_billing_units'] = one_meter_data['endtime_meter_reading'] - one_meter_data['starttime_meter_reading']
                                plant_total_generation_from_meter = plant_total_generation_from_meter + one_meter_data['total_billing_units']
                            else:
                                one_meter_data['starttime_meter_reading'] = "--"
                                one_meter_data['endtime_meter_reading'] = "--"
                                one_meter_data['total_billing_units'] = "--"
                            groups_meter_gen.append(one_meter_data)
                    else:
                        one_meter_data = {}
                        one_meter_data['group_name'] = group.name
                        one_meter_data['name'] = "--"
                        group_capacity = sum(list(group.groupIndependentInverters.all().\
                                                  values_list('total_capacity', flat=True)))
                        plant_total_capacity_meter = plant_total_capacity_meter + group_capacity
                        one_meter_data['group_capacity'] = group_capacity
                        one_meter_data['starttime_meter_reading'] = "--"
                        one_meter_data['endtime_meter_reading'] = "--"
                        one_meter_data['total_billing_units'] = "--"
                        groups_meter_gen.append(one_meter_data)
                    context['plant_total_capacity_meter'] = plant_total_capacity_meter

                if len(plant_energy_meters) != meters_with_groups_assigned:
                    remaining_meters_without_groups = list(set(plant_energy_meters) - set(meters_with_groups_assigned))
                    for meter in remaining_meters_without_groups:
                        one_meter_data = {}
                        one_meter_data['name'] = meter.name
                        one_meter_data['group_name'] = "--"

                        one_meter_data['group_capacity'] = "--"
                        stream = 'Wh_RECEIVED'
                        output = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey, stream_name=stream,
                                                                         timestamp_in_data__gte=starttime,
                                                                         timestamp_in_data__lte=endtime).limit(
                            0).order_by(
                            'timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                        if len(output)>0:
                            one_meter_data['starttime_meter_reading'] = round(float(output.first()[0]), 2)
                            one_meter_data['endtime_meter_reading'] = round(float(output[len(output) - 1][0]), 2)
                            one_meter_data['total_billing_units'] = one_meter_data['endtime_meter_reading'] - \
                                                                one_meter_data['starttime_meter_reading']
                            plant_total_generation_from_meter = plant_total_generation_from_meter + one_meter_data['total_billing_units']
                            groups_meter_gen.append(one_meter_data)
                        else:
                            one_meter_data['starttime_meter_reading'] = 0
                            one_meter_data['endtime_meter_reading'] = 0
                            one_meter_data['total_billing_units'] = 0
                            plant_total_generation_from_meter = plant_total_generation_from_meter + one_meter_data['total_billing_units']
                            groups_meter_gen.append(one_meter_data)


            context['plant_total_generation_from_meter'] = plant_total_generation_from_meter
            context['group_meter_energy_data'] = groups_meter_gen
            print groups_meter_gen
        else:
            context['energy_meter_order'] = 101

        total_inverter_cacpacity = 0
        total_inverter_billing_units = 0
        name_list_for_sorting = []
        if True:
            context['inverter_data_order'] = 2
            all_plant_inverters = plant.independent_inverter_units.all()
            list_of_all_inverters_info = []
            for inverter in all_plant_inverters:
                single_inverter_info_dict = {}
                single_inverter_info_dict['name'] = inverter.name
                name_list_for_sorting.append(inverter.name)
                solar_groups_of_inverter = inverter.solar_groups.all()
                if solar_groups_of_inverter:
                    group_name = solar_groups_of_inverter[0].name
                else:
                    group_name = "None"
                single_inverter_info_dict['group_name'] = group_name
                single_inverter_info_dict['capacity'] = inverter.total_capacity
                total_inverter_cacpacity = total_inverter_cacpacity + single_inverter_info_dict['capacity']
                stream = "TOTAL_YIELD"
                output = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey, stream_name=stream,
                                                                 timestamp_in_data__gte=starttime,
                                                                 timestamp_in_data__lte=endtime).limit(0).order_by(
                    'timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

                if output:
                    df = pd.DataFrame(output[:], columns=['stream_value', 'timestamp_in_data'])
                    df.dropna(inplace=True)
                    df['stream_value'] = df['stream_value'].astype(float)
                    df = df[df['stream_value'] > 0]
                    df = df[(df['stream_value'] - df['stream_value'].shift(1)) > 0]
                    single_inverter_info_dict['starttime_inverter_reading'] = df['stream_value'].round(2).values[0]
                    df = df[df['stream_value'] > single_inverter_info_dict['starttime_inverter_reading']]
                    single_inverter_info_dict['endtime_inverter_reading'] = df['stream_value'].round(2).values[-1]
                    single_inverter_info_dict['total_billing_units_inverters'] = single_inverter_info_dict['endtime_inverter_reading'] - single_inverter_info_dict[
                        'starttime_inverter_reading']

                    total_inverter_billing_units = total_inverter_billing_units + single_inverter_info_dict['total_billing_units_inverters']
                else:
                    single_inverter_info_dict['starttime_inverter_reading'] = "--"
                    single_inverter_info_dict['endtime_inverter_reading'] = "--"
                    single_inverter_info_dict['total_billing_units_inverters'] = "--"
                list_of_all_inverters_info.append(single_inverter_info_dict)
            import re
            convert = lambda text: int(text) if text.isdigit() else text
            # sorted_dict = sorted(list_of_all_inverters_info, key=lambda k: [convert(c) for c in re.split('([0-9]+)', k['name'])])
            sorted_dict = sorted(list_of_all_inverters_info,key=lambda k : [ convert(c) for c in re.split('([0-9]+)', k['name']+ k['group_name'])])

            context['list_of_all_inverters_info'] = sorted_dict
            context['total_inverter_cacpacity'] = total_inverter_cacpacity
            context['total_inverter_billing_units'] = total_inverter_billing_units
            print list_of_all_inverters_info
        else:
            context['inverter_data_order'] = 102

        logger.debug("Context is calculated successfully....")
        now = datetime.datetime.now()
        context['copyright_year'] = str(now.year)
        return context

    except Exception as e:
        logger.debug("Exception===============>>>%s>>>%s"%(plant.slug,e))
        return context



