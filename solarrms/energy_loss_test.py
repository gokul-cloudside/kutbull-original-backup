from dataglen.models import ValidDataStorageByStream
from .settings import INVERTER_CHART_FIELDS, INVERTER_CHART_LEN
from .settings import INPUT_PARAMETERS, OUTPUT_PARAMETERS, STATUS_PARAMETERS, VALID_ENERGY_CALCULATION_DELTA_MINUTES
import logging
import pandas as pd
import pytz, sys
from utils.errors import generate_exception_comments
import numpy as np
from kutbill import settings
from solarrms.models import PerformanceRatioTable, CUFTable, SolarPlant, SolarGroup, IndependentInverter
from django.utils import timezone

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

from .settings import PLANT_POWER_STREAM, PLANT_ENERGY_STREAM, INVERTER_ENERGY_FIELD, INVERTER_POWER_FIELD, \
    INVERTER_VALID_LAST_ENTRY_MINUTES, INVERTER_TOTAL_ENERGY_FIELD
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
import json
from solarrms.solarutils import get_plant_power

def fill_results(results):
    return results

def get_energy_from_power(power_values):
    power_values['average'] = (power_values["sum"] + power_values["sum"].shift(+1))/2.0
    power_values['delta'] = power_values.diff()['timestamp']
    delta = pd.Timedelta(seconds=VALID_ENERGY_CALCULATION_DELTA_MINUTES*60)
    accepted_values = power_values[(power_values['delta']) < delta]
    accepted_values['energy'] = accepted_values['average']*(accepted_values['delta']/np.timedelta64(1, 'h'))
    return accepted_values

def calculate_DC_energy_of_inverters_from_ajb(starttime, endtime, plant, timesplit=False):
    try:
       inverter_power_values_from_ajbs = get_ajb_power(starttime, endtime, plant)
       inverters = plant.independent_inverter_units.all()
       inverters = [inverters[0], inverters[1]]
       final_inverter_energy = pd.DataFrame()
       if not type(inverter_power_values_from_ajbs) is list and not inverter_power_values_from_ajbs.empty:
           for inverter in inverters:
               inverter_power = pd.DataFrame()
               inverter_energy = pd.DataFrame()
               try:
                   if not inverter_power_values_from_ajbs[str(inverter.name)].empty:
                       print inverter_power_values_from_ajbs[str(inverter.name)]
                       inverter_power['sum'] = inverter_power_values_from_ajbs[str(inverter.name)]
                       inverter_power['timestamp'] = inverter_power_values_from_ajbs['timestamp']
                       inverter_energy_temp = get_energy_from_power(inverter_power)
                       print inverter_energy_temp
                       inverter_energy['timestamp'] = inverter_energy_temp['timestamp']
                       inverter_energy[str(inverter.name)] = inverter_energy_temp['energy']
                       if not inverter_energy.empty:
                           if final_inverter_energy.empty:
                                final_inverter_energy = inverter_energy
                           else:
                                df_new = pd.merge(final_inverter_energy, inverter_energy, on='timestamp', how='outer')
                                final_inverter_energy = df_new
                       #print final_inverter_energy
               except Exception as exception:
                   print(str(exception))
                   continue
           final_inverter_energy['total_energy'] = final_inverter_energy.sum(axis=1)
       if timesplit:
           result = json.loads(final_inverter_energy.to_json(orient='records',date_format='iso'))
       else:
           result = []
           result_temp = final_inverter_energy.sum(axis=0)
           result_temp = json.loads(pd.DataFrame({'Inverter':result_temp.index, 'Energy':result_temp.values}).to_json(orient='records'))
           print(type(result_temp))
           for i in range(len(result_temp)):
               dict_temp = {}
               dict_temp[result_temp[i]['Inverter']] = result_temp[i]['Energy']
               result.append(dict_temp)
       return result
    except Exception as exception:
        print(str(exception))
        return []

def get_ajb_power(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0], inverters[1]]
        df_list_power = []
        for inverter in inverters:
            df_list_voltage = []
            df_results_current = pd.DataFrame
            ajbs = inverter.ajb_units.all()
            if ajbs:
                for ajb in ajbs:
                    df_results_current_temp = pd.DataFrame
                    streams = ajb.fields.all()
                    for stream in streams:
                        if str(stream.name).startswith('S'):
                            df_list_current_temp = []
                            ajb_data_current_temp = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                                           stream_name= stream.name,
                                                                                           timestamp_in_data__gte = starttime,
                                                                                           timestamp_in_data__lte = endtime
                                                                                           ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                            values_current_temp = []
                            timestamp_current_temp = []
                            for data_point in ajb_data_current_temp:
                                timestamp_current_temp.append(data_point[1].replace(second=0, microsecond=0))
                                values_current_temp.append(float(data_point[0])/1000)
                            if len(values_current_temp) > 0:
                                df_list_current_temp.append(pd.DataFrame({stream.name: values_current_temp,
                                                                         'timestamp': pd.to_datetime(timestamp_current_temp)}))

                            if len(df_list_current_temp) > 0:
                                results_current_temp = df_list_current_temp[0]
                                for i in range(1, len(df_list_current_temp)):
                                    results_current_temp = results_current_temp.merge(df_list_current_temp[i], how='outer', on='timestamp')
                                    updated_results_current_temp = fill_results(results_current_temp)
                                    results_current_temp = updated_results_current_temp
                                if df_results_current_temp.empty:
                                    df_results_current_temp = results_current_temp
                                else:
                                    df_new = pd.merge(df_results_current_temp, results_current_temp, on='timestamp', how='outer')
                                    df_results_current_temp = df_new
                    #print df_results_current_temp

                    try:
                        if not df_results_current_temp.empty:
                            df_results_current_temp.set_index('timestamp', inplace=True)
                            df_results_sum = df_results_current_temp.sum(axis=1)
                            df_results_current_temp = pd.DataFrame({'timestamp':df_results_sum.index, ajb.name:df_results_sum.values})
                    except Exception as exception:
                        print(str(exception))
                        continue
                    try:
                        if df_results_current.empty and not df_results_current_temp.empty:
                            df_results_current = df_results_current_temp
                        elif not df_results_current_temp.empty:
                            df_new = pd.merge(df_results_current, df_results_current_temp, on='timestamp', how='outer')
                            df_results_current = df_new
                        else:
                            pass
                    except Exception as exception:
                        print(str(exception))
                        continue

                    ajb_data_voltage = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                               stream_name='VOLTAGE',
                                                                               timestamp_in_data__gte = starttime,
                                                                               timestamp_in_data__lte = endtime
                                                                               ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')

                    values_voltage = []
                    timestamp_voltage = []
                    for data_point in ajb_data_voltage:
                        timestamp_voltage.append(data_point[1].replace(second=0, microsecond=0))
                        values_voltage.append(float(data_point[0]))
                    df_list_voltage.append(pd.DataFrame({ajb.name: values_voltage,
                                                        'timestamp': pd.to_datetime(timestamp_voltage)}))

                try:
                    df_results_current.set_index('timestamp', inplace=True)
                    #print("current")
                    #print(df_results_current)
                    if len(df_list_voltage) > 0:
                        results_voltage = df_list_voltage[0]
                        for i in range(1, len(df_list_voltage)):
                            results_voltage = results_voltage.merge(df_list_voltage[i], how='outer', on='timestamp')
                            updated_results_voltage = fill_results(results_voltage)
                            results_voltage = updated_results_voltage
                        results_voltage.set_index('timestamp', inplace=True)
                        #print("voltage")
                        #print results_voltage
                    df_results_power = df_results_current.mul(results_voltage, axis=0)
                    df_results_power['timestamp'] = df_results_power.index
                    sorted_results = df_results_power.sort()
                    results = sorted_results
                    results = results.ffill(limit=1)
                    #print("power")
                    #print df_results_power

                    results[inverter.name] = results.sum(axis=1)
                    #return json.loads(results.to_json(orient = 'records'))
                    #print results[inverter.name]
                    if not results.empty:
                        df_list_power.append(pd.DataFrame({inverter.name: results[inverter.name],
                                                          'timestamp': results['timestamp']}))
                except Exception as exception:
                    print(str(exception))
        if len(df_list_power)>0:
            results_power = df_list_power[0]
            for i in range(1, len(df_list_power)):
                results_power = results_power.merge(df_list_power[i], how='outer', on='timestamp')
                updated_results_power = fill_results(results_power)
                results_power = updated_results_power
            results_power.set_index('timestamp', inplace=True)
            #results_power['sum'] = results_power.sort().sum(axis=1)
            results_power['timestamp'] = results_power.index
            #print("final_power")
            #print(results_power.sort())
            return results_power.sort()
        else:
            return []
    except Exception as exception:
        print(str(exception))


def get_DC_Power_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0]]
        df_results_power = pd.DataFrame()
        for inverter in inverters:
            df_list_power = []
            dc_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'DC_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_dc_power = []
            timestamp_dc_power = []
            for data_point in dc_power_data:
                timestamp_dc_power.append(data_point[1].replace(second=0, microsecond=0))
                values_dc_power.append(float(data_point[0]))
            df_list_power.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_dc_power),
                                               'DC_POWER': values_dc_power}))

            if len(df_list_power) > 0:
                results_power_temp = df_list_power[0]
                for i in range(1, len(df_list_power)):
                    results_power_temp = results_power_temp.merge(df_list_power[i], how='outer', on='timestamp')
                    updated_results_power_temp = fill_results(results_power_temp)
                    results_power_temp = updated_results_power_temp
                if df_results_power.empty:
                    df_results_power = results_power_temp
                else:
                    df_new = pd.merge(df_results_power, results_power_temp, on='timestamp', how='outer')
                    df_results_power = df_new
        return df_results_power
    except Exception as exception:
        print(str(exception))
        return []


def get_AC_Power_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0]]
        df_results_power = pd.DataFrame()
        for inverter in inverters:
            df_list_power = []
            ac_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'ACTIVE_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_ac_power = []
            timestamp_ac_power = []
            for data_point in ac_power_data:
                timestamp_ac_power.append(data_point[1].replace(second=0, microsecond=0))
                values_ac_power.append(float(data_point[0]))
            df_list_power.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_ac_power),
                                               'AC_POWER': values_ac_power}))

            if len(df_list_power) > 0:
                results_power_temp = df_list_power[0]
                for i in range(1, len(df_list_power)):
                    results_power_temp = results_power_temp.merge(df_list_power[i], how='outer', on='timestamp')
                    updated_results_power_temp = fill_results(results_power_temp)
                    results_power_temp = updated_results_power_temp
                if df_results_power.empty:
                    df_results_power = results_power_temp
                else:
                    df_new = pd.merge(df_results_power, results_power_temp, on='timestamp', how='outer')
                    df_results_power = df_new
        return df_results_power
    except Exception as exception:
        print(str(exception))

def get_DC_Energy_of_inverters(starttime, endtime, plant, timesplit=False):
    try:
        inverters_dc_power_values = get_DC_Power_of_inverters(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0]]
        final_inverter_dc_energy = pd.DataFrame()
        if not type(inverters_dc_power_values) is list and not inverters_dc_power_values.empty:
           for inverter in inverters:
               inverter_dc_power = pd.DataFrame()
               inverter_dc_energy = pd.DataFrame()
               try:
                   if not inverters_dc_power_values['DC_POWER'].empty:
                       #print inverters_dc_power_values[str(inverter.name)]
                       inverter_dc_power['sum'] = inverters_dc_power_values['DC_POWER']
                       inverter_dc_power['timestamp'] = inverters_dc_power_values['timestamp']
                       inverter_dc_energy_temp = get_energy_from_power(inverter_dc_power)
                       print inverter_dc_energy_temp
                       inverter_dc_energy['timestamp'] = inverter_dc_energy_temp['timestamp']
                       inverter_dc_energy['DC_Energy'] = inverter_dc_energy_temp['energy']
                       if not inverter_dc_energy.empty:
                           if final_inverter_dc_energy.empty:
                                final_inverter_dc_energy = inverter_dc_energy
                           else:
                                df_new = pd.merge(final_inverter_dc_energy, inverter_dc_energy, on='timestamp', how='outer')
                                final_inverter_dc_energy = df_new
                       #print final_inverter_energy
               except Exception as exception:
                   print(str(exception))
                   continue
           final_inverter_dc_energy = final_inverter_dc_energy.sort(['timestamp'])
           return final_inverter_dc_energy
    except Exception as exception:
        print(str(exception))

def get_AC_Energy_of_inverters(starttime, endtime, plant, timesplit=False):
    try:
        inverters_ac_power_values = get_AC_Power_of_inverters(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0]]
        final_inverter_ac_energy = pd.DataFrame()
        if not type(inverters_ac_power_values) is list and not inverters_ac_power_values.empty:
           for inverter in inverters:
               inverter_ac_power = pd.DataFrame()
               inverter_ac_energy = pd.DataFrame()
               try:
                   if not inverters_ac_power_values['APPARENT_POWER'].empty:
                       #print inverters_dc_power_values[str(inverter.name)]
                       inverter_ac_power['sum'] = inverters_ac_power_values['AC_POWER']
                       inverter_ac_power['timestamp'] = inverters_ac_power_values['timestamp']
                       inverter_ac_energy_temp = get_energy_from_power(inverter_ac_power)
                       print inverter_ac_energy_temp
                       inverter_ac_energy['timestamp'] = inverter_ac_energy_temp['timestamp']
                       inverter_ac_energy['AC_Energy'] = inverter_ac_energy_temp['energy']
                       if not inverter_ac_energy.empty:
                           if final_inverter_ac_energy.empty:
                                final_inverter_ac_energy = inverter_ac_energy
                           else:
                                df_new = pd.merge(final_inverter_ac_energy, inverter_ac_energy, on='timestamp', how='outer')
                                final_inverter_ac_energy = df_new
                       #print final_inverter_energy
               except Exception as exception:
                   print(str(exception))
                   continue
           final_inverter_ac_energy = final_inverter_ac_energy.sort(['timestamp'])
           return final_inverter_ac_energy
    except Exception as exception:
        print(str(exception))

def get_TotalYield_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0]]
        df_results_total_yield = pd.DataFrame()
        for inverter in inverters:
            df_list_total_yield = []
            total_yield_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                        stream_name= 'TOTAL_YIELD',
                                                                        timestamp_in_data__gte = starttime,
                                                                        timestamp_in_data__lte = endtime
                                                                        ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_total_yield = []
            timestamp_total_yield = []
            for data_point in total_yield_data:
                timestamp_total_yield.append(data_point[1].replace(second=0, microsecond=0))
                values_total_yield.append(float(data_point[0]))
            df_list_total_yield.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_total_yield),
                                                     'TOTAL_YIELD': values_total_yield}))

            if len(df_list_total_yield) > 0:
                results_total_yield_temp = df_list_total_yield[0]
                for i in range(1, len(df_list_total_yield)):
                    results_total_yield_temp = results_total_yield_temp.merge(df_list_total_yield[i], how='outer', on='timestamp')
                    updated_results_total_yield_temp = fill_results(results_total_yield_temp)
                    results_total_yield_temp = updated_results_total_yield_temp
                if df_results_total_yield.empty:
                    df_results_total_yield = results_total_yield_temp
                else:
                    df_new = pd.merge(df_results_total_yield, results_total_yield_temp, on='timestamp', how='outer')
                    df_results_total_yield = df_new
        return df_results_total_yield
    except Exception as exception:
        print(str(exception))

def get_inverter_parameter_values(starttime, endtime, plant):
    try:
        final_result = pd.DataFrame()
        dc_power = get_DC_Power_of_inverters(starttime, endtime, plant)
        dc_energy = get_DC_Energy_of_inverters(starttime, endtime, plant)
        ac_power = get_AC_Power_of_inverters(starttime, endtime, plant)
        ac_energy = get_AC_Energy_of_inverters(starttime, endtime, plant)
        total_yield = get_TotalYield_of_inverters(starttime, endtime, plant)

        final_result = dc_power
        df_new = pd.merge(final_result, ac_power, on='timestamp', how='outer')
        final_result = df_new
        df_new = pd.merge(final_result, dc_energy, on='timestamp', how='outer')
        final_result = df_new
        df_new = pd.merge(final_result, ac_energy, on='timestamp', how='outer')
        final_result = df_new
        df_new = pd.merge(final_result, total_yield, on='timestamp', how='outer')
        final_result = df_new
        return final_result
    except Exception as exception:
        print(str(exception))


# Inverter and grid loss code:

def get_AC_Power_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0]]#, inverters[1], inverters[2], inverters[3]]
        df_results_power = pd.DataFrame()
        for inverter in inverters:
            df_list_power = []
            ac_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'ACTIVE_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_ac_power = []
            timestamp_ac_power = []
            for data_point in ac_power_data:
                valid_timestamp = data_point[1].replace(second=0, microsecond=0)
                if valid_timestamp.hour > 1 and valid_timestamp.hour<13:
                    timestamp_ac_power.append(valid_timestamp)
                    values_ac_power.append(float(data_point[0]))
            df_list_power.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_ac_power),
                                               inverter.name: values_ac_power}))

            if len(df_list_power) > 0:
                results_power_temp = df_list_power[0]
                for i in range(1, len(df_list_power)):
                    results_power_temp = results_power_temp.merge(df_list_power[i], how='outer', on='timestamp')
                    updated_results_power_temp = fill_results(results_power_temp)
                    results_power_temp = updated_results_power_temp
                if df_results_power.empty:
                    df_results_power = results_power_temp
                else:
                    df_new = pd.merge(df_results_power, results_power_temp, on='timestamp', how='outer')
                    df_results_power = df_new
        return df_results_power.sort('timestamp')
    except Exception as exception:
        print("ac power exception: " + str(exception))


def get_total_loss(starttime, endtime, plant):
    try:
        result_sum = {}
        final_energy = {}
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0]]
        active_power = get_AC_Power_of_inverters(starttime, endtime, plant)
        total_yield = get_loss_final(starttime, endtime, plant, 'INVERTER')
        for inverter in inverters:
            result = pd.DataFrame()
            final_result = pd.DataFrame()
            active_power_inverter = pd.DataFrame()
            total_yield_inverter = pd.DataFrame()
            active_power_inverter[inverter.name] = active_power[inverter.name]
            active_power_inverter['timestamp'] = active_power['timestamp']
            total_yield_inverter[inverter.name] = total_yield[inverter.name]
            total_yield_inverter['timestamp'] = total_yield['timestamp']
            result1 = active_power_inverter.merge(total_yield_inverter, on='timestamp', how='inner')
            result[inverter.name+"_active_power"] = result1[inverter.name+'_x']
            result['timestamp'] = result1['timestamp']
            result = result.dropna()
            result_power = pd.DataFrame()
            result_power['sum'] = result[inverter.name+"_active_power"]
            result_power['timestamp'] = result['timestamp']
            result_energy = get_energy_from_power(result_power)
            final_energy[inverter.name] = result_energy['energy'].sum()
            result[inverter.name+"_average_active_power"] = (result[inverter.name+"_active_power"] + result[inverter.name+"_active_power"].shift(-1))/2
            final_result[inverter.name+'_average_active_power'] = result[inverter.name+"_average_active_power"]
            final_result[inverter.name+'_timedelta'] = result.diff()['timestamp']
            delta = pd.Timedelta(seconds=30*60)
            final_result = final_result[final_result[inverter.name+'_timedelta']< delta]
            final_result[inverter.name+'_active_energy'] = final_result[inverter.name+'_average_active_power']*(final_result[inverter.name+'_timedelta']/np.timedelta64(1, 'h'))
            final_result[inverter.name+'_active_energy'] = final_result[final_result[inverter.name+'_active_energy'] >0]
            result_sum[str(inverter.name)] = final_result[inverter.name+'_active_energy'].sum()
        #return result_sum
        return final_energy
    except Exception as exception:
        print(str(exception))


def get_grid_loss(starttime, endtime, plant):
    try:
        result_sum = {}
        final_energy = {}
        inverters = plant.independent_inverter_units.all()
        active_power = get_AC_Power_of_inverters(starttime, endtime, plant)
        total_yield = get_loss_final(starttime, endtime, plant, 'GRID')
        for inverter in inverters:
            try:
                result = pd.DataFrame()
                final_result = pd.DataFrame()
                active_power_inverter = pd.DataFrame()
                total_yield_inverter = pd.DataFrame()
                active_power_inverter[inverter.name] = active_power[inverter.name]
                active_power_inverter['timestamp'] = active_power['timestamp']
                total_yield_inverter[inverter.name] = total_yield[inverter.name]
                total_yield_inverter['timestamp'] = total_yield['timestamp']
                result1 = active_power_inverter.merge(total_yield_inverter, on='timestamp', how='inner')
                result[inverter.name+"_active_power"] = result1[inverter.name+'_x']
                result['timestamp'] = result1['timestamp']
                result = result.dropna()
                result_power = pd.DataFrame()
                result_power['sum'] = result[inverter.name+"_active_power"]
                result_power['timestamp'] = result['timestamp']
                result_energy = get_energy_from_power(result_power)
                final_energy[inverter.name] = result_energy['energy'].sum()
                result[inverter.name+"_average_active_power"] = (result[inverter.name+"_active_power"] + result[inverter.name+"_active_power"].shift(-1))/2
                final_result[inverter.name+'_average_active_power'] = result[inverter.name+"_average_active_power"]
                final_result[inverter.name+'_timedelta'] = result.diff()['timestamp']
                delta = pd.Timedelta(seconds=8*60*60)
                final_result = final_result[final_result[inverter.name+'_timedelta']< delta]
                final_result[inverter.name+'_active_energy'] = final_result[inverter.name+'_average_active_power']*(final_result[inverter.name+'_timedelta']/np.timedelta64(1, 'h'))
                final_result[inverter.name+'_active_energy'] = final_result[final_result[inverter.name+'_active_energy'] >0]
                final_result.dropna()
                result_sum[str(inverter.name)] = final_result[inverter.name+'_active_energy'].sum()
            except Exception as exception:
                print(str(exception))
                continue
        #return result_sum
        return final_energy
    except Exception as exception:
        print(str(exception))


def get_inverter_grid_loss(starttime, endtime, plant):
    try:
        final_result = []
        total_loss = get_total_loss(starttime, endtime, plant)
        grid_loss = get_grid_loss(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            inv_dict = {}
            loss_dict = {}
            loss_dict['total_loss'] = total_loss[str(inverter.name)]
            loss_dict['grid_loss'] = grid_loss[str(inverter.name)]
            loss_dict['equipment_loss'] = loss_dict['total_loss'] - loss_dict['grid_loss']
            inv_dict[str(inverter.name)] = loss_dict
            final_result.append(inv_dict)
        return final_result
    except Exception as exception:
        print(str(exception))

def get_loss_final(starttime, endtime, plant, level):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0]]
        df_grid = pd.DataFrame()
        df_inverter = pd.DataFrame()
        df = get_plant_power(starttime, endtime, plant, pandas_df=True, energy=True, split=True, meter_energy=False)
        dff = df.set_index('timestamp')
        dff = dff.between_time(start_time='01:30', end_time='12:30')
        dff['ts'] = dff.index
        data = dff
        data = data - data.shift(1)
        dd = data.drop('ts',1)
        dd = dd.drop('sum',1)
        for inverter in inverters:
            a = data.loc[dd[inverter.name] == 0]
            b = data.loc[~(dd!=0).any(1)]
            df_grid[inverter.name] = b[inverter.name]
            #df_inverter['timestamp'] = b.index
            c = a.drop(b.index)
            df_inverter[inverter.name] = c[inverter.name]
        if level == 'INVERTER':
            return df_inverter.reset_index()
        elif level == 'GRID':
            return df_grid.reset_index()
    except Exception as exception:
        print(str(exception))