from dataglen.models import ValidDataStorageByStream
import pandas as pd
from solarrms.solarutils import get_energy_from_power, get_minutes_aggregated_energy
from solarrms.settings import ENERGY_CALCULATION_STREAMS, ENERGY_METER_STREAM_UNITS, ENERGY_METER_STREAM_UNIT_FACTOR

# Compute DC loss using DC Power values of AJB and Inverter

def compute_dc_loss(starttime, endtime, plant):
    try:
        result = {}
        if len(plant.ajb_units.all()) == 0:
            return result
        else:
            dc_energy_inverters = 0.0
            dc_energy_ajbs = 0.0
            inverters = plant.independent_inverter_units.all().filter(isActive=True)
            for inverter in inverters:
                try:
                    df_ajbs = pd.DataFrame()
                    ajbs = inverter.ajb_units.all().filter(isActive=True)
                    for ajb in ajbs:
                        df_ajb_power = pd.DataFrame()
                        ajb_power_values = ValidDataStorageByStream.objects.filter(source_key=str(ajb.sourceKey),
                                                                                   stream_name='POWER',
                                                                                   timestamp_in_data__gte=starttime,
                                                                                   timestamp_in_data__lte=endtime).\
                                                                                   limit(0).order_by('timestamp_in_data').\
                                                                                   values_list('stream_value','timestamp_in_data')
                        ajb_power = []
                        ajb_timestamp = []
                        for data_point in ajb_power_values:
                            try:
                                ajb_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                                ajb_power.append(float(data_point[0]))
                            except:
                                continue
                        df_ajb_power['timestamp'] = ajb_timestamp
                        df_ajb_power[str(ajb.name)] = ajb_power
                        if not df_ajb_power.empty:
                            df_ajb_power = df_ajb_power[df_ajb_power[str(ajb.name)]>0]

                        if df_ajbs.empty and not df_ajb_power.empty:
                            df_ajbs = df_ajb_power
                        elif not df_ajbs.empty and not df_ajb_power.empty:
                            df_ajbs = df_ajbs.merge(df_ajb_power.drop_duplicates('timestamp'), on='timestamp', how='inner')
                        else:
                            pass
                    df_inverter = pd.DataFrame()
                    inverter_power_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                                    stream_name='DC_POWER',
                                                                                    timestamp_in_data__gte=starttime,
                                                                                    timestamp_in_data__lte=endtime).\
                                                                                    limit(0).order_by('timestamp_in_data').\
                                                                                    values_list('stream_value','timestamp_in_data')
                    inverter_power = []
                    inverter_timestamp = []
                    for data_point in inverter_power_values:
                        try:
                            inverter_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                            inverter_power.append(float(data_point[0]))
                        except:
                            continue

                    if len(inverter_power_values)>0:
                        df_inverter['timestamp'] = inverter_timestamp
                        df_inverter[str(inverter.name)] = inverter_power

                    if len(inverter_power_values) == 0:
                        df_inverter_voltage = pd.DataFrame()
                        inverter_dc_voltage_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                                    stream_name='DC_VOLTAGE',
                                                                                    timestamp_in_data__gte=starttime,
                                                                                    timestamp_in_data__lte=endtime).\
                                                                                    limit(0).order_by('timestamp_in_data').\
                                                                                    values_list('stream_value','timestamp_in_data')
                        inverter_voltage = []
                        inverter_voltage_timestamp = []
                        for data_point in inverter_dc_voltage_values:
                            try:
                                inverter_voltage_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                                inverter_voltage.append(float(data_point[0]))
                            except:
                                continue
                        df_inverter_voltage['timestamp'] = inverter_voltage_timestamp
                        df_inverter_voltage['DC_VOLTAGE'] = inverter_voltage

                        df_inverter_current = pd.DataFrame()
                        inverter_dc_current_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                                    stream_name='DC_CURRENT',
                                                                                    timestamp_in_data__gte=starttime,
                                                                                    timestamp_in_data__lte=endtime).\
                                                                                    limit(0).order_by('timestamp_in_data').\
                                                                                    values_list('stream_value','timestamp_in_data')
                        inverter_current = []
                        inverter_current_timestamp = []
                        for data_point in inverter_dc_current_values:
                            try:
                                inverter_current_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                                inverter_current.append(float(data_point[0]))
                            except:
                                continue
                        df_inverter_current['timestamp'] = inverter_current_timestamp
                        df_inverter_current['DC_CURRENT'] = inverter_current

                        if not df_inverter_voltage.empty and not df_inverter_current.empty:
                            df = df_inverter_voltage.merge(df_inverter_current.drop_duplicates('timestamp'), on='timestamp', how='inner')
                            df_inverter['timestamp'] = df['timestamp']
                            df_inverter[str(inverter.name)] = (df['DC_VOLTAGE']*df['DC_CURRENT'])/1000.0

                    if not df_inverter.empty:
                        df_inverter = df_inverter[df_inverter[str(inverter.name)]>0]

                    if not df_inverter.empty and not df_ajbs.empty:
                        df_final = df_inverter.merge(df_ajbs.drop_duplicates('timestamp'), on='timestamp', how='inner')
                        df_ajbs_merge = pd.DataFrame()
                        df_ajbs_merge['timestamp'] = df_final['timestamp']
                        for ajb in ajbs:
                            try:
                                df_ajbs_merge[str(ajb.name)] = df_final[str(ajb.name)]
                            except:
                                continue
                        df_ajbs_merge['sum'] = df_ajbs_merge.sum(axis=1)
                        ajbs_dc_energy = get_energy_from_power(df_ajbs_merge, True)
                        if not ajbs_dc_energy.empty:
                            result['dc_energy_ajb_'+str(inverter.name)] = ajbs_dc_energy['energy'].sum()
                            dc_energy_ajbs += float(ajbs_dc_energy['energy'].sum())
                        df_inverters_merge = pd.DataFrame()
                        df_inverters_merge['timestamp'] = df_final['timestamp']
                        df_inverters_merge[str(inverter.name)] = df_final[str(inverter.name)]
                        df_inverters_merge['sum'] = df_inverters_merge.sum(axis=1)
                        inverters_dc_energy = get_energy_from_power(df_inverters_merge, True)
                        if not inverters_dc_energy.empty:
                            result['dc_energy_'+str(inverter.name)] = inverters_dc_energy['energy'].sum()
                            dc_energy_inverters += float(inverters_dc_energy['energy'].sum())
                except Exception as exception:
                    print str(exception)
                    continue
            result['dc_energy_from_ajb'] = dc_energy_ajbs
            result['dc_energy_from_inverter'] = dc_energy_inverters
        return result
    except Exception as exception:
        print str(exception)
        return {}


# Compute Conversion Loss using DC and AC Power of Inverter

def compute_conversion_loss(starttime, endtime, plant):
    try:
        result = {}
        dc_energy_inverter = 0.0
        ac_energy_inverter = 0.0
        inverters = plant.independent_inverter_units.all().filter(isActive=True)
        df_final = pd.DataFrame()
        for inverter in inverters:
            df_dc_power = pd.DataFrame()
            df_ac_power = pd.DataFrame()
            dc_power_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                      stream_name='DC_POWER',
                                                                      timestamp_in_data__gte=starttime,
                                                                      timestamp_in_data__lte=endtime).\
                                                                      limit(0).order_by('timestamp_in_data').\
                                                                      values_list('stream_value','timestamp_in_data')
            dc_power = []
            dc_power_timestamp = []
            for data_point in dc_power_values:
                try:
                    dc_power_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                    dc_power.append(float(data_point[0]))
                except:
                    continue
            df_dc_power['timestamp'] = dc_power_timestamp
            df_dc_power[str(inverter.name)+"_dc_power"] = dc_power
            if not df_dc_power.empty:
                df_dc_power = df_dc_power[df_dc_power[str(inverter.name)+"_dc_power"]>0]

            if len(dc_power_values) == 0:
                dc_voltage_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                      stream_name='DC_VOLTAGE',
                                                                      timestamp_in_data__gte=starttime,
                                                                      timestamp_in_data__lte=endtime).\
                                                                      limit(0).order_by('timestamp_in_data').\
                                                                      values_list('stream_value','timestamp_in_data')
                dc_voltage = []
                dc_voltage_timestamp = []
                pd_dc_voltage = pd.DataFrame()
                for data_point in dc_voltage_values:
                    try:
                        dc_voltage_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                        dc_voltage.append(float(data_point[0]))
                    except:
                        continue
                pd_dc_voltage['DC_VOLTAGE'] = dc_voltage
                pd_dc_voltage['timestamp'] = dc_voltage_timestamp
                if not pd_dc_voltage.empty:
                    pd_dc_voltage = pd_dc_voltage[pd_dc_voltage['DC_VOLTAGE']>0]
                dc_current_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                      stream_name='DC_CURRENT',
                                                                      timestamp_in_data__gte=starttime,
                                                                      timestamp_in_data__lte=endtime).\
                                                                      limit(0).order_by('timestamp_in_data').\
                                                                      values_list('stream_value','timestamp_in_data')
                dc_current = []
                dc_current_timestamp = []
                pd_dc_current = pd.DataFrame()
                for data_point in dc_current_values:
                    try:
                        dc_current_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                        dc_current.append(float(data_point[0]))
                    except:
                        continue
                pd_dc_current['DC_CURRENT'] = dc_current
                pd_dc_current['timestamp'] = dc_current_timestamp
                if not pd_dc_current.empty:
                    pd_dc_current = pd_dc_current[pd_dc_current['DC_CURRENT']>0]

                if not pd_dc_current.empty and not pd_dc_voltage.empty:
                    dc_values = pd_dc_current.merge(pd_dc_voltage.drop_duplicates('timestamp'), on='timestamp', how='inner')
                    dc_values[str(inverter.name)+"_dc_power"] = (dc_values['DC_VOLTAGE']*dc_values['DC_CURRENT'])/1000.0
                    df_dc_power[str(inverter.name)+"_dc_power"] = dc_values[str(inverter.name)+"_dc_power"]
                    df_dc_power['timestamp'] = dc_values['timestamp']

            if df_final.empty and not df_dc_power.empty:
                df_final = df_dc_power
            elif not df_final.empty and not df_dc_power.empty:
                df_final = df_final.merge(df_dc_power.drop_duplicates('timestamp'), on='timestamp', how='inner')
            else:
                pass
            ac_power_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                      stream_name='ACTIVE_POWER',
                                                                      timestamp_in_data__gte=starttime,
                                                                      timestamp_in_data__lte=endtime).\
                                                                      limit(0).order_by('timestamp_in_data').\
                                                                      values_list('stream_value','timestamp_in_data')
            ac_power = []
            ac_power_timestamp = []
            for data_point in ac_power_values:
                try:
                    ac_power_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                    ac_power.append(float(data_point[0]))
                except:
                    continue
            df_ac_power['timestamp'] = ac_power_timestamp
            df_ac_power[str(inverter.name)+"_ac_power"] = ac_power
            df_ac_power = df_ac_power[df_ac_power[str(inverter.name)+"_ac_power"]>0]

            if df_final.empty and not df_ac_power.empty:
                df_final = df_ac_power
            elif not df_final.empty and not df_ac_power.empty:
                df_final = df_final.merge(df_ac_power.drop_duplicates('timestamp'), on='timestamp', how='inner')
            else:
                pass
        for inverter in inverters:
            try:
                df_inverter_dc_power = pd.DataFrame()
                df_inverter_dc_power[str(inverter.name)+"_dc_power"] = df_final[str(inverter.name)+"_dc_power"]
                df_inverter_dc_power['timestamp'] = df_final['timestamp']
                df_inverter_dc_power['sum'] = df_inverter_dc_power.sum(axis=1)
                inverter_dc_energy = get_energy_from_power(df_inverter_dc_power, True)
                result['dc_energy_'+str(inverter.name)] = inverter_dc_energy['energy'].sum()
                dc_energy_inverter += inverter_dc_energy['energy'].sum()
                df_inverter_ac_power = pd.DataFrame()
                df_inverter_ac_power[str(inverter.name)+"_ac_power"] = df_final[str(inverter.name)+"_ac_power"]
                df_inverter_ac_power['timestamp'] = df_final['timestamp']
                df_inverter_ac_power['sum'] = df_inverter_ac_power.sum(axis=1)
                inverter_ac_energy = get_energy_from_power(df_inverter_ac_power, True)
                result['ac_energy_'+str(inverter.name)] = inverter_ac_energy['energy'].sum()
                ac_energy_inverter += inverter_ac_energy['energy'].sum()
            except Exception as exception:
                print str(exception)
                continue
        result['dc_energy_inverter'] = dc_energy_inverter
        result['ac_energy_inverter'] = ac_energy_inverter
        return result
    except Exception as exception:
        print str(exception)
        return {}


# Compute AC loss using inverter's TOTAL_YIELD and meters energy

def compute_ac_loss(starttime, endtime, plant):
    try:
        result = {}
        if len(plant.energy_meters.all()) == 0 or len(plant.independent_inverter_units.all().filter(isActive=True)) == 0:
            return result
        else:
            inverter_ac_energy = 0.0
            meter_ac_energy = 0.0
            if len(plant.independent_inverter_units.all().filter(isActive=True))>0:
                df_final = pd.DataFrame()
                inverters = plant.independent_inverter_units.all().filter(isActive=True)
                for inverter in inverters:
                    df_inverter = pd.DataFrame()
                    total_yield_values = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                                 stream_name='TOTAL_YIELD',
                                                                                 timestamp_in_data__gte=starttime,
                                                                                 timestamp_in_data__lte=endtime).\
                                                                                 limit(0).order_by('timestamp_in_data').\
                                                                                 values_list('stream_value','timestamp_in_data')
                    total_yield = []
                    total_yield_timestamp = []
                    for data_point in total_yield_values:
                        try:
                            total_yield_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                            total_yield.append(float(data_point[0]))
                        except:
                            continue
                    df_inverter['timestamp'] = total_yield_timestamp
                    df_inverter[str(inverter.name)] = total_yield

                    if not df_inverter.empty:
                        df_inverter = df_inverter[df_inverter[str(inverter.name)]>0]

                    if df_final.empty and not df_inverter.empty:
                        df_final = df_inverter
                    elif not df_final.empty and not df_inverter.empty:
                        df_final = df_final.merge(df_inverter.drop_duplicates('timestamp'), on='timestamp', how='inner')
                    else:
                        pass

            if len(plant.energy_meters.all())>0:
                meters = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)
                energy_unit = False
                try:
                    stream = ENERGY_CALCULATION_STREAMS[str(plant.slug)]
                except:
                    stream = 'Wh_RECEIVED'
                try:
                    unit = ENERGY_METER_STREAM_UNITS[str(plant.slug)]
                    unit_factor = ENERGY_METER_STREAM_UNIT_FACTOR[unit]
                except:
                    energy_unit = True
                for meter in meters:
                    df_meter = pd.DataFrame()
                    meter_data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name=stream,
                                                                         timestamp_in_data__gte=starttime,
                                                                         timestamp_in_data__lte=endtime).\
                                                                         limit(0).order_by('timestamp_in_data').\
                                                                         values_list('stream_value', 'timestamp_in_data')
                    meter_values = []
                    meter_timestamp = []
                    for data_point in meter_data:
                        meter_timestamp.append(data_point[1].replace(second=0, microsecond=0))
                        if energy_unit:
                            meter_values.append(float(data_point[0]))
                        else:
                            meter_values.append(float(data_point[0])*unit_factor)
                    df_meter['timestamp'] = meter_timestamp
                    df_meter[str(meter.name)] = meter_values
                    if not df_meter.empty:
                        df_meter = df_meter[df_meter[str(meter.name)]>0]
                    if df_final.empty and not df_meter.empty:
                        df_final = df_meter
                    elif not df_final.empty and not df_meter.empty:
                        df_final = df_final.merge(df_meter.drop_duplicates('timestamp'), on='timestamp', how='inner')
                    else:
                        pass
            df_final_diff = df_final.diff()
            df_final_diff = df_final_diff.rename(columns={'timestamp':'ts'})
            df_final_diff['timestamp'] = df_final['timestamp']
            for inverter in inverters:
                try:
                    df_final_diff_inverter = pd.DataFrame()
                    df_final_diff_inverter[str(inverter.name)] = df_final_diff[str(inverter.name)]
                    df_final_diff_inverter['timestamp'] = df_final_diff['timestamp']
                    df_final_diff_inverter = df_final_diff_inverter[df_final_diff_inverter[str(inverter.name)]>0]
                    sum = df_final_diff_inverter[str(inverter.name)].sum()
                    result[str(inverter.name)+"_ac_energy"] = sum
                    inverter_ac_energy += sum
                except:
                    continue
            for meter in meters:
                try:
                    df_final_diff_meter = pd.DataFrame()
                    df_final_diff_meter[str(meter.name)] = df_final_diff[str(meter.name)]
                    df_final_diff_meter['timestamp'] = df_final_diff['timestamp']
                    df_final_diff_meter = df_final_diff_meter[df_final_diff_meter[str(meter.name)]>0]
                    sum = df_final_diff_meter[str(meter.name)].sum()
                    result[str(meter.name)+"_ac_energy"] = sum
                    meter_ac_energy += sum
                except:
                    continue
            result['inverter_ac_energy'] = inverter_ac_energy
            result['meter_ac_energy'] = meter_ac_energy
        return result
    except Exception as exception:
        print str(exception)
        return {}