from dataglen.models import ValidDataStorageByStream
import logging
import pandas as pd
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)
import math
from solarrms.solarutils import fill_results, get_energy_from_power, get_aggregated_energy, get_energy_meter_values
import numpy as np



def calculate_DC_energy_of_inverters_from_ajb(starttime, endtime, plant, timesplit=False):
    try:
       inverter_power_values_from_ajbs = get_ajb_power(starttime, endtime, plant)
       inverters = plant.independent_inverter_units.all()
       #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
       final_inverter_energy = pd.DataFrame()
       if not type(inverter_power_values_from_ajbs) is list and not inverter_power_values_from_ajbs.empty:
           for inverter in inverters:
               inverter_power = pd.DataFrame()
               inverter_energy = pd.DataFrame()
               try:
                   if not inverter_power_values_from_ajbs[str(inverter.name)].empty:
                       #print inverter_power_values_from_ajbs[str(inverter.name)]
                       inverter_power['sum'] = inverter_power_values_from_ajbs[str(inverter.name)]
                       inverter_power['timestamp'] = inverter_power_values_from_ajbs['timestamp']
                       inverter_energy_temp = get_energy_from_power(inverter_power)
                       #print inverter_energy_temp
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
           final_inverter_energy = final_inverter_energy[final_inverter_energy.total_energy > 0]
           return final_inverter_energy
       #     print(final_inverter_energy)
       # if timesplit:
       #     result = json.loads(final_inverter_energy.to_json(orient='records',date_format='iso'))
       # else:
       #     result = []
       #     result_temp = final_inverter_energy.sum(axis=0)
       #     result_temp = json.loads(pd.DataFrame({'Inverter':result_temp.index, 'Energy':result_temp.values}).to_json(orient='records'))
       #     for i in range(len(result_temp)):
       #         dict_temp = {}
       #         dict_temp[result_temp[i]['Inverter']] = result_temp[i]['Energy']
       #         result.append(dict_temp)
       # return result
    except Exception as exception:
        print(str(exception))
        return []

def get_ajb_power(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
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
            #results_power.set_index('timestamp', inplace=True)
            #results_power['sum'] = results_power.sort().sum(axis=1)
            #results_power['timestamp'] = results_power.index
            #print("final_power")
            #print(results_power.sort())
            return results_power.sort()
        else:
            return []
    except Exception as exception:
        print(str(exception))

def get_ajb_dc_energy_aggregated(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        aggregated_dc_energy = 0.0
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
                    results[inverter.name] = results.sum(axis=1)

                    results_energy = pd.DataFrame()
                    results_energy['timestamp'] = results['timestamp']
                    results_energy['sum'] = results[inverter.name]
                    energy_from_ajb = get_energy_from_power(results_energy)
                    sum = energy_from_ajb['energy'].sum()
                    if not energy_from_ajb.empty and not math.isnan(sum):
                        aggregated_dc_energy += sum
                except Exception as exception:
                    print(str(exception))
        return aggregated_dc_energy
    except Exception as exception:
        print(str(exception))


def get_DC_Power_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
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
                                               inverter.name: values_dc_power}))

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
        print("dc power exception: " + str(exception))
        return []


def get_AC_Power_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        inverters = [inverters[0], inverters[1], inverters[2], inverters[3]]
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
        return df_results_power
    except Exception as exception:
        print("ac power exception: " + str(exception))

def get_DC_Energy_of_inverters(starttime, endtime, plant, timesplit=False):
    try:
        inverters_dc_power_values = get_DC_Power_of_inverters(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        final_inverter_dc_energy = pd.DataFrame()
        if not type(inverters_dc_power_values) is list and not inverters_dc_power_values.empty:
           for inverter in inverters:
               inverter_dc_power = pd.DataFrame()
               inverter_dc_energy = pd.DataFrame()
               try:
                   if not inverters_dc_power_values[str(inverter.name)].empty:
                       #print inverters_dc_power_values[str(inverter.name)]
                       inverter_dc_power['sum'] = inverters_dc_power_values[str(inverter.name)]
                       inverter_dc_power['timestamp'] = inverters_dc_power_values['timestamp']
                       inverter_dc_energy_temp = get_energy_from_power(inverter_dc_power)
                       inverter_dc_energy['timestamp'] = inverter_dc_energy_temp['timestamp']
                       inverter_dc_energy[str(inverter.name)] = inverter_dc_energy_temp['energy']
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
           final_inverter_dc_energy['total_energy'] = final_inverter_dc_energy.sum(axis=1)
           # if timesplit:
           #     result = json.loads(final_inverter_dc_energy.to_json(orient='records',date_format='iso'))
           # else:
           #     result = []
           #     result_temp = final_inverter_dc_energy.sum(axis=0)
           #     result_temp = json.loads(pd.DataFrame({'Inverter':result_temp.index, 'Energy':result_temp.values}).to_json(orient='records'))
           #     #print(type(result_temp))
           #     for i in range(len(result_temp)):
           #         dict_temp = {}
           #         dict_temp[result_temp[i]['Inverter']] = result_temp[i]['Energy']
           #         result.append(dict_temp)
           return final_inverter_dc_energy
        else:
            return []
    except Exception as exception:
        print("dc energy exception" + str(exception))
        return []

def get_AC_Energy_of_inverters(starttime, endtime, plant, timesplit=False):
    try:
        inverters_ac_power_values = get_AC_Power_of_inverters(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        final_inverter_ac_energy = pd.DataFrame()
        if not type(inverters_ac_power_values) is list and not inverters_ac_power_values.empty:
           for inverter in inverters:
               inverter_ac_power = pd.DataFrame()
               inverter_ac_energy = pd.DataFrame()
               try:
                   if not inverters_ac_power_values[str(inverter.name)].empty:
                       #print inverters_dc_power_values[str(inverter.name)]
                       inverter_ac_power['sum'] = inverters_ac_power_values[str(inverter.name)]
                       inverter_ac_power['timestamp'] = inverters_ac_power_values['timestamp']
                       inverter_ac_energy_temp = get_energy_from_power(inverter_ac_power)
                       #print inverter_ac_energy_temp
                       inverter_ac_energy['timestamp'] = inverter_ac_energy_temp['timestamp']
                       inverter_ac_energy[str(inverter.name)] = inverter_ac_energy_temp['energy']
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
           final_inverter_ac_energy['total_energy'] = final_inverter_ac_energy.sum(axis=1)
           final_inverter_ac_energy = final_inverter_ac_energy.sort(['timestamp'])
           return final_inverter_ac_energy
        else:
            return []
    except Exception as exception:
        print(str(exception))
        return []

def get_dc_energy_loss(starttime, endtime, plant):
    try:
        dc_energy_from_ajbs = calculate_DC_energy_of_inverters_from_ajb(starttime, endtime, plant)
        dc_energy_from_inverters = get_DC_Energy_of_inverters(starttime, endtime, plant)
        dc_energy_loss = dc_energy_from_ajbs-dc_energy_from_inverters
        dc_energy_loss['timestamp'] = dc_energy_from_ajbs.merge(dc_energy_from_inverters, how='outer', on='timestamp')['timestamp']
        dc_energy_loss['ajb_dc_energy'] = dc_energy_from_ajbs['total_energy']
        dc_energy_loss['inverter_dc_energy'] = dc_energy_from_inverters['total_energy']
        return dc_energy_loss
    except Exception as exception:
        print(str(exception))
        return []

def get_dc_energy_loss_aggregated(starttime, endtime, plant):
    try:
        dc_energy_loss_df = {}
        dc_energy_from_ajbs = get_ajb_dc_energy_aggregated(starttime, endtime, plant)
        print(dc_energy_from_ajbs)
        dc_energy_from_inverters = get_DC_Energy_of_inverters(starttime, endtime, plant)
        print(dc_energy_from_inverters['total_energy'].sum())
        dc_energy_loss_value = dc_energy_from_ajbs-dc_energy_from_inverters['total_energy'].sum()
        #dc_energy_loss['timestamp'] = dc_energy_from_ajbs.merge(dc_energy_from_inverters, how='outer', on='timestamp')['timestamp']
        dc_energy_loss_df['ajb_dc_energy'] = dc_energy_from_ajbs
        dc_energy_loss_df['inverter_dc_energy'] = dc_energy_from_inverters['total_energy'].sum()
        dc_energy_loss_df['dc_energy_loss'] = dc_energy_loss_df['ajb_dc_energy'] - dc_energy_loss_df['inverter_dc_energy']
        return dc_energy_loss_df
    except Exception as exception:
        print(str(exception))
        return []

def get_conversion_loss(starttime, endtime, plant):
    try:
        dc_energy = get_DC_Energy_of_inverters(starttime, endtime, plant)
        #ac_energy = get_AC_Energy_of_inverters(starttime, endtime, plant)
        ac_energy = get_AC_energy_of_inverters_from_total_yield(starttime, endtime, plant)
        if type(dc_energy) is not list and type(ac_energy) is not list:
            dc_energy = dc_energy[dc_energy.total_energy > 0]
            ac_energy = ac_energy[ac_energy.total_energy > 0]
            conversion_loss = dc_energy-ac_energy
            conversion_loss['timestamp'] = dc_energy.merge(ac_energy, how='outer', on='timestamp')['timestamp']
            conversion_loss['inverter_dc_energy'] = dc_energy['total_energy']
            conversion_loss['inverter_ac_energy'] = ac_energy['total_energy']
            return conversion_loss
        else:
            return []
    except Exception as exception:
        print(str(exception))
        return []

def get_AC_energy_of_inverters_from_total_yield(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        inverters = inverters = [inverters[0], inverters[1], inverters[2], inverters[3]]
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
                                                     inverter.name: values_total_yield}))

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
        df_results_total_yield['total_energy'] = df_results_total_yield.sum(axis=1)
        df_results =  df_results_total_yield.diff()
        df_results['timestamp'] = df_results_total_yield['timestamp']
        #print(df_results)
        return df_results
    except Exception as exception:
        print(str(exception))
        return []

def get_AC_energy_from_meters(starttime, endtime, plant):
    try:
        meters = plant.energy_meters.all()
        df_results_meters = pd.DataFrame()
        if len(meters)>0:
            for meter in meters:
                df_list_meter = []
                meter_data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name= 'KWH',
                                                                     timestamp_in_data__gte = starttime,
                                                                     timestamp_in_data__lte = endtime
                                                                     ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                values_meter = []
                timestamp_meter = []
                for data_point in meter_data:
                    timestamp_meter.append(data_point[1].replace(second=0, microsecond=0))
                    values_meter.append(float(data_point[0])*1000)
                df_list_meter.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_meter),
                                                   meter.name: values_meter}))

                if len(df_list_meter) > 0:
                    results_meter_temp = df_list_meter[0]
                    for i in range(1, len(df_list_meter)):
                        results_meter_temp = results_meter_temp.merge(df_list_meter[i], how='outer', on='timestamp')
                        updated_results_meter_temp = fill_results(results_meter_temp)
                        results_meter_temp = updated_results_meter_temp
                    if df_results_meters.empty:
                        df_results_meters = results_meter_temp
                    else:
                        df_new = pd.merge(df_results_meters, results_meter_temp, on='timestamp', how='outer')
                        df_results_meters = df_new
            df_results_meters['total_energy'] = df_results_meters.sum(axis=1)
            df_results =  df_results_meters.diff()
            df_results['timestamp'] = df_results_meters['timestamp']
            #print(df_results_meters)
            #print(df_results)
            return df_results
        elif hasattr(plant, 'metadata') and plant.metadata.fields.get(name="ENERGY_METER_DATA").isActive:
            meter_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                  stream_name='ENERGY_METER_DATA',
                                                                  timestamp_in_data__gte=starttime,
                                                                  timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            values_meter = []
            timestamp_meter = []
            df_list_meter = []
            for data_point in meter_data:
                timestamp_meter.append(data_point[1].replace(second=0, microsecond=0))
                values_meter.append(float(data_point[0])*1000)
            df_list_meter.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_meter),
                                               'total_energy': values_meter}))
            if len(df_list_meter) > 0:
                results_meter_temp = df_list_meter[0]
                for i in range(1, len(df_list_meter)):
                    results_meter_temp = results_meter_temp.merge(df_list_meter[i], how='outer', on='timestamp')
                    updated_results_meter_temp = fill_results(results_meter_temp)
                    results_meter_temp = updated_results_meter_temp
            df_results_meters = results_meter_temp
            #print(df_results_meters)
            df_results =  df_results_meters.diff()
            df_results['timestamp'] = df_results_meters['timestamp']
            return df_results
    except Exception as exception:
        print(str(exception))
        return []

def get_ac_loss_timesplit(starttime, endtime, plant):
    try:
        ac_energy_loss = pd.DataFrame()
        ac_energy_from_total_yield = get_AC_energy_of_inverters_from_total_yield(starttime, endtime, plant)
        ac_energy_from_meters = get_AC_energy_from_meters(starttime, endtime, plant)
        ac_energy_loss['total_yield'] = ac_energy_from_total_yield['total_energy']
        ac_energy_loss['energy_meter'] = ac_energy_from_meters['total_energy']
        ac_energy_loss['ac_energy_loss'] = ac_energy_from_total_yield['total_energy'] - ac_energy_from_meters['total_energy']
        ac_energy_loss['timestamp'] = ac_energy_from_total_yield.merge(ac_energy_from_meters, on='timestamp', how='outer')['timestamp']
        total_energy_loss = ac_energy_loss.sum(axis=0)
        return ac_energy_loss
    except Exception as exception:
        print(str(exception))
        return []

def get_ac_loss_aggregated(starttime, endtime, plant, aggregator):
    try:
        meters =  plant.energy_meters.all()
        if len(meters)>0:
            energy_from_inverters = get_aggregated_energy(starttime, endtime, plant, aggregator)
            energy_from_meters = get_AC_energy_from_meters(starttime, endtime, plant)
            result_energy_loss = []
            if energy_from_inverters and not energy_from_meters.empty:
                for i in range(len(energy_from_inverters)):
                    result = {}
                    result['inverter_ac_energy'] = energy_from_inverters[i]['energy']
                    result['meter_energy'] = energy_from_meters['total_energy'].sum()
                    result['ac_energy_loss'] = result['inverter_ac_energy'] - result['meter_energy']
                    result['timestamp'] = energy_from_inverters[i]['timestamp']
                    result_energy_loss.append(result)
                return result_energy_loss
            else:
                return []
        else:
            energy_from_inverters = get_aggregated_energy(starttime, endtime, plant, aggregator)
            energy_from_meters = get_energy_meter_values(starttime, endtime, plant, aggregator)
            result_energy_loss = []
            if energy_from_inverters and energy_from_meters:
                for i in range(len(energy_from_inverters)):
                    result = {}
                    result['inverter_ac_energy'] = energy_from_inverters[i]['energy']
                    result['meter_energy'] = energy_from_meters[i]['energy']
                    result['ac_energy_loss'] = result['inverter_ac_energy'] - result['meter_energy']
                    result['timestamp'] = energy_from_inverters[i]['timestamp']
                    result_energy_loss.append(result)
                return result_energy_loss
            else:
                return []
    except Exception as exception:
        print("energy_from_meters: " + str(exception))
        return[]

def get_all_energy_losses(starttime, endtime, plant):
    try:
        final_result = []
        ajbs = plant.ajb_units.all()
        try:
            dc_energy = {}
            if ajbs:
                dc_energy_loss_df = get_dc_energy_loss_aggregated(starttime, endtime, plant)
                if type(dc_energy_loss_df) is not list:
                    dc_energy['ajb_dc_energy'] = dc_energy_loss_df['ajb_dc_energy']
                    dc_energy['inverter_dc_energy'] = dc_energy_loss_df['inverter_dc_energy']
                    dc_energy['dc_energy_loss'] = dc_energy_loss_df['dc_energy_loss']
                else:
                    dc_energy['dc_energy_loss'] = 'NA'
            else:
                dc_energy['dc_energy_loss'] = 'NA'
        except Exception as exception:
            print("inside dc loss exception: "+ str(exception))
            dc_energy['dc_energy_loss'] = 'NA'
            pass

        final_result.append(dc_energy)
        try:
            conversion = {}
            conversion_loss = get_conversion_loss(starttime, endtime, plant)
            if type(conversion_loss) is not list:
                conversion['inverter_dc_energy'] = conversion_loss['inverter_dc_energy'].sum()
                conversion['inverter_ac_energy'] = conversion_loss['inverter_ac_energy'].sum()
                conversion['conversion_loss'] = conversion['inverter_dc_energy'] - conversion['inverter_ac_energy']
            else:
                conversion['conversion_loss'] = 'NA'
        except Exception as exception:
            print("inside conversion exception: " + str(exception))
            conversion['conversion_loss'] = 'NA'
            pass
        final_result.append(conversion)

        try:
            ac_energy = {}
            ac_energy_loss = get_ac_loss_aggregated(starttime, endtime, plant, 'DAY')
            if len(ac_energy_loss)> 0:
                ac_energy['inverter_ac_energy'] = ac_energy_loss[0]['inverter_ac_energy']
                ac_energy['meter_energy'] = ac_energy_loss[0]['meter_energy']
                ac_energy['ac_energy_loss'] = ac_energy_loss[0]['ac_energy_loss']
            else:
                ac_energy['ac_energy_loss'] = 'NA'
        except Exception as exception:
            print("inside ac loss exception: "+str(exception))
            ac_energy['ac_energy_loss'] = 'NA'
            pass

        final_result.append(ac_energy)
        return final_result
    except Exception as exception:
        print(str(exception))
        return []

def get_AC_energy_of_inverters_from_total_yield(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[25]]#, inverters[1], inverters[2], inverters[3]]
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
                valid_timestamp = data_point[1].replace(second=0, microsecond=0)
                if valid_timestamp.hour > 1 and valid_timestamp.hour<13:
                    timestamp_total_yield.append(valid_timestamp)
                    values_total_yield.append(float(data_point[0]))
            df_list_total_yield.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_total_yield),
                                                     inverter.name: values_total_yield}))

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
        df_results_total_yield['total_energy'] = df_results_total_yield.sum(axis=1)
        df_results =  df_results_total_yield.diff()
        df_results['timestamp'] = df_results_total_yield['timestamp']
        #print(df_results)
        return df_results.sort('timestamp')
    except Exception as exception:
        print(str(exception))
        return []

def get_AC_Power_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[25]]#, inverters[1], inverters[2], inverters[3]]
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


# Inverter Loss
def get_total_loss(starttime, endtime, plant):
    try:
        result_sum = {}
        active_power = get_AC_Power_of_inverters(starttime, endtime, plant)
        total_yield = get_AC_energy_of_inverters_from_total_yield(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[25]]#, inverters[1], inverters[2], inverters[3]]
        for inverter in inverters:
            result = pd.DataFrame()
            final_result = pd.DataFrame()
            result[inverter.name+"_total_yield"] = total_yield[inverter.name]
            result[inverter.name+"_active_power"] = active_power[inverter.name]
            result['timestamp'] = active_power.merge(total_yield, on='timestamp', how='outer')['timestamp']

            # filter for total yield difference zero values
            result = result[result[inverter.name+"_total_yield"] == 0]
            result = result[result[inverter.name+"_active_power"] > 0]
            # filter values within plant start and shut down time
            # filter nan values
            result = result.dropna()
            result[inverter.name+"_average_active_power"] = (result[inverter.name+"_active_power"] + result[inverter.name+"_active_power"].shift(-1))/2
            final_result[inverter.name+'_delta_total_yield'] = result[inverter.name+"_total_yield"]
            final_result[inverter.name+'_average_active_power'] = result[inverter.name+"_average_active_power"]
            final_result[inverter.name+'_start_time'] = result['timestamp'].shift(+1)
            final_result[inverter.name+'_end_time'] = result['timestamp']
            final_result[inverter.name+'_timedelta'] = result.diff()['timestamp']
            delta = pd.Timedelta(seconds=8*60*60)
            delta1 = pd.Timedelta(seconds=0)
            final_result = final_result[final_result[inverter.name+'_timedelta']< delta]
            final_result = final_result[final_result[inverter.name+'_timedelta']> delta1]
            final_result[inverter.name+'_active_energy'] = final_result[inverter.name+'_average_active_power']*(final_result[inverter.name+'_timedelta']/np.timedelta64(1, 'h'))
            #print final_result
            result_sum[str(inverter.name)] = final_result[inverter.name+'_active_energy'].sum()
            #return final_result
        return result_sum
    except Exception as exception:
        print(str(exception))

# Grid Loss
def get_grid_loss(starttime, endtime, plant):
    try:
        df_grid = {}
        active_power = get_AC_Power_of_inverters(starttime, endtime, plant)
        total_yield = get_AC_energy_of_inverters_from_total_yield(starttime, endtime, plant)
        inverters = plant.independent_inverter_units.all()
        df_final = pd.DataFrame()
        #inverters = [inverters[0], inverters[1], inverters[2], inverters[3]]
        for inverter in inverters:
            result = pd.DataFrame()
            final_result = pd.DataFrame()
            result[inverter.name+"_total_yield"] = total_yield[inverter.name]
            result[inverter.name+"_active_power"] = active_power[inverter.name]
            result['timestamp'] = active_power.merge(total_yield, on='timestamp', how='outer')['timestamp']
            # filter for total yield difference zero values
            result = result[result[inverter.name+"_total_yield"] == 0]
            result = result[result[inverter.name+"_active_power"] > 0]
            # filter values within plant start and shut down time
            # filter nan values
            result = result.dropna()
            result[inverter.name+"_average_active_power"] = (result[inverter.name+"_active_power"] + result[inverter.name+"_active_power"].shift(-1))/2
            final_result[inverter.name+'_delta_total_yield'] = result[inverter.name+"_total_yield"]
            final_result[inverter.name+'_average_active_power'] = result[inverter.name+"_average_active_power"]
            final_result[inverter.name+'_start_time'] = result['timestamp'].shift(+1)
            final_result[inverter.name+'_end_time'] = result['timestamp']
            final_result[inverter.name+'_timedelta'] = result.diff()['timestamp']
            final_result['timestamp'] = result['timestamp']
            delta = pd.Timedelta(seconds=8*60*60)
            delta1 = pd.Timedelta(seconds=0)
            final_result = final_result[final_result[inverter.name+'_timedelta']< delta]
            final_result = final_result[final_result[inverter.name+'_timedelta']> delta1]
            final_result[inverter.name+'_active_energy'] = final_result[inverter.name+'_average_active_power']*(final_result[inverter.name+'_timedelta']/np.timedelta64(1, 'h'))
            #result_sum[str(inverter.name)] = final_result[inverter.name+'_active_energy'].sum()
            if df_final.empty:
                df_final = final_result
            else:
                df_new = pd.merge(df_final, final_result, on='timestamp', how='inner')
                df_final = df_new
        for inverter in inverters:
            try:
                df_grid[str(inverter.name)] = df_final[inverter.name+'_active_energy'].sum()
                #df_grid['timestamp'] = df_final['timestamp']
            except:
                continue
        return df_grid
    except Exception as exception:
        print(str(exception))

# Overall Loss
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


def get_grid_availability_from_AC_frequency(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        df_list = []
        for inverter in inverters:
            try:
                inverter_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                        stream_name='AC_FREQUENCY',
                                                                        timestamp_in_data__gt=starttime,
                                                                        timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                timestamps = []
                values = []
                for data_point in inverter_data:
                    timestamps.append(data_point[1].replace(second=0, microsecond=0))
                    values.append(float(data_point[0]))
                df_list.append(pd.DataFrame({inverter.name: values,
                                             'timestamp': pd.to_datetime(timestamps)}))
            except Exception as exc:
                logger.debug(exc)
                continue
        try:
            if len(df_list) >= 2:
                results = df_list[0]
                for i in range(1, len(df_list)):
                    results = results.merge(df_list[i], how='outer', on='timestamp')
                    updated_results = fill_results(results)
                    results = updated_results
            else:
                if len(df_list) == 1:
                    results = df_list[0]
            results['sum'] = results.sum(axis=1)
            results = results.set_index('timestamp')
            results = results.between_time(start_time='01:30', end_time='12:30')
            return results
        except Exception as exception:
            print(str(exception))
    except Exception as exception:
        print(str(exception))