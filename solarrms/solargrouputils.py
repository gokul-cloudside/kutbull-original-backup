import datetime
from datetime import timedelta
import collections
import numpy as np
import pandas as pd
from dataglen.models import ValidDataStorageByStream
from errors.models import ErrorStorageByStream
from solarrms.settings import INVERTER_POWER_FIELD, INVERTER_ENERGY_FIELD, INVERTER_TOTAL_ENERGY_FIELD

import logging
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


def get_solar_groups_irradiation(ts, solar_group):
    """

    :param current_time:
    :param solar_group:
    :return:
    """
    meta_sources = solar_group.groupIOSensors.filter(stream_type="IRRADIATION").\
        values('plant_meta__sourceKey', 'plant_meta__timeoutInterval', 'solar_field__name')
    irradiation_value = 0.0
    irradiation_count = 0
    for meta_source in meta_sources:
        irradiation = list(
            ValidDataStorageByStream.objects.filter(source_key=meta_source['plant_meta__sourceKey'],
                                                    stream_name='%s' % meta_source['solar_field__name'],
                                                    timestamp_in_data__lte=ts,
                                                    timestamp_in_data__gte=ts - datetime.timedelta(
                                                    seconds=meta_source['plant_meta__timeoutInterval'])).limit(1).
                values_list('stream_value', flat=True))
        if irradiation:
            irradiation_value += float(irradiation[0])
        irradiation_count += 1
    return irradiation_value / irradiation_count if irradiation_count > 0 else irradiation_value


def get_solar_groups_windspeed(ts, solar_group):
    """

    :param current_time:
    :param solar_group:
    :return:
    """
    meta_sources = solar_group.groupIOSensors.filter(stream_type="WINDSPEED").\
        values('plant_meta__sourceKey', 'plant_meta__timeoutInterval', 'solar_field__name')
    windspeed_value = 0.0
    windspeed_count = 0
    for meta_source in meta_sources:
        windspeed = list(
            ValidDataStorageByStream.objects.filter(source_key=meta_source['plant_meta__sourceKey'],
                                                    stream_name=meta_source['solar_field__name'],
                                                    timestamp_in_data__lte=ts,
                                                    timestamp_in_data__gte=ts - datetime.timedelta(
                                                    seconds=meta_source['plant_meta__timeoutInterval'])).limit(1)
                .values_list('stream_value', flat=True))
        if windspeed:
            windspeed_value += float(windspeed[0])
        windspeed_count += 1
    return windspeed_value / windspeed_count if windspeed_count > 0 else windspeed_value


def get_solar_groups_module_temperature(ts, solar_group):
    """

    :param current_time:
    :param solar_group:
    :return:
    """
    meta_sources = solar_group.groupIOSensors.filter(stream_type="MODULE_TEMPERATURE").\
        values('plant_meta__sourceKey', 'plant_meta__timeoutInterval', 'solar_field__name')
    module_temperature_value = 0.0
    module_temperature_count = 0
    for meta_source in meta_sources:
        module_temperature = list(
            ValidDataStorageByStream.objects.filter(source_key=meta_source['plant_meta__sourceKey'],
                                                    stream_name=meta_source['solar_field__name'],
                                                    timestamp_in_data__lte=ts,
                                                    timestamp_in_data__gte=ts - datetime.timedelta(
                                                    seconds=meta_source['plant_meta__timeoutInterval'])).limit(1).
                values_list('stream_value', flat=True))
        if module_temperature:
            module_temperature_value += float(module_temperature[0])
        module_temperature_count += 1
    return module_temperature_value / module_temperature_count if module_temperature_count > 0 else module_temperature_value


def get_solar_groups_ambient_temperature(ts, solar_group):
    """

    :param current_time:
    :param solar_group:
    :return:
    """
    meta_sources = solar_group.groupIOSensors.filter(stream_type="AMBIENT_TEMPERATURE").\
        values('plant_meta__sourceKey', 'plant_meta__timeoutInterval', 'solar_field__name')
    ambient_temperature_value = 0.0
    ambient_temperature_count = 0
    for meta_source in meta_sources:
        ambient_temperature = list(
            ValidDataStorageByStream.objects.filter(source_key=meta_source['plant_meta__sourceKey'],
                                                    stream_name=meta_source['solar_field__name'],
                                                    timestamp_in_data__lte=ts,
                                                    timestamp_in_data__gte=ts - datetime.timedelta(
                                                    seconds=meta_source['plant_meta__timeoutInterval'])).limit(1).
                values_list('stream_value', flat=True))
        if ambient_temperature:
            ambient_temperature_value += float(ambient_temperature[0])
        ambient_temperature_count += 1
    return ambient_temperature_value / ambient_temperature_count if ambient_temperature_count > 0 else ambient_temperature_value


def get_solar_groups_today_generation(ts, solar_group):
    """

    :param current_time:
    :param solar_group:
    :return:
    """
    today_energy = 0.0
    try:
        inverter_sources = solar_group.groupIndependentInverters.all().values('sourceKey')
        for inverter in inverter_sources:
            value = list(ValidDataStorageByStream.objects.filter(source_key=inverter['sourceKey'],\
                                                            stream_name='DAILY_YIELD').\
                values_list('stream_value', flat=True).limit(1))
            if value:
                today_energy += float(value[0])
        return today_energy
    except Exception as exception:
        print "get_solar_group_todays_generation %s" % exception
        return today_energy


def get_solar_groups_total_generation(ts, solar_group):
    """

    :param ts:
    :param solar_group:
    :return:
    """
    total_energy = 0.0
    try:
        inverter_sources = solar_group.groupIndependentInverters.all().values('sourceKey')
        for inverter in inverter_sources:
            value = list(ValidDataStorageByStream.objects.filter(source_key=inverter['sourceKey'],\
                                                            stream_name='TOTAL_YIELD').\
                values_list('stream_value', flat=True).limit(1))
            if value:
                total_energy += float(value[0])
        return total_energy
    except Exception as exception:
        print "get_total_solar_group_generation %s" % exception
        return total_energy


def get_solar_groups_power(starttime, endtime, solar_group, plant, pandas_df=False, energy=False,\
                    split=False, live=False):
    """

    :param starttime:
    :param endtime:
    :param plant:
    :param solar_group:
    :param pandas_df:
    :param energy:
    :param split:
    :param live:
    :param aggregated_power:
    :return:
    """
    if energy is True and plant.metadata.plantmetasource.energy_from_power is True:
        inverters = solar_group.groupIndependentInverters.all()
        pd_power_energy = pd.DataFrame()
        for inverter in inverters:
            ac_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'ACTIVE_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').\
                values_list('stream_value','timestamp_in_data')
            if ac_power_data:
                values_ac_power = []
                timestamp_ac_power = []
                df_inverter_power = pd.DataFrame()
                df_inverter_energy = pd.DataFrame()
                df_inverter_final_values = pd.DataFrame()
                for data_point in ac_power_data:
                    timestamp_ac_power.append(data_point[1].replace(second=0, microsecond=0))
                    values_ac_power.append(float(data_point[0]))
                df_inverter_power[str(inverter.name)] = values_ac_power
                df_inverter_power['timestamp'] = timestamp_ac_power
                df_inverter_energy["average"] = (df_inverter_power[str(inverter.name)] + df_inverter_power[str(inverter.name)].shift(+1))/2.0
                df_inverter_energy['timestamp'] = df_inverter_power['timestamp']
                df_inverter_energy = df_inverter_energy.sort('timestamp')
                df_inverter_energy['delta'] = df_inverter_power.diff()['timestamp']
                df_inverter_energy=df_inverter_energy[df_inverter_energy['delta']/np.timedelta64(1, 'h')<30]
                df_inverter_energy['energy'] = df_inverter_energy['average']*(df_inverter_energy['delta']/np.timedelta64(1, 'h'))
                df_inverter_final_values['timestamp'] = df_inverter_energy['timestamp']
                df_inverter_final_values[str(inverter.name)] = df_inverter_energy['energy']
                if pd_power_energy.empty:
                    pd_power_energy = df_inverter_final_values
                else:
                    pd_power_energy = pd_power_energy.merge(df_inverter_final_values.drop_duplicates('timestamp'), on='timestamp', how='outer')
        if split is True:
            return pd_power_energy
        else:
            pd_power_energy_sum = pd.DataFrame()
            pd_power_energy_sum['timestamp'] = pd_power_energy['timestamp']
            pd_power_energy_sum['sum'] = pd_power_energy.sum(axis=1)
            return pd_power_energy_sum
    else:
        try:
            if live:
                from utils.multiprocess import get_inverters_power_or_energy_data_mp
                inverters = solar_group.groupIndependentInverters.all().filter(isActive=True)
                df_list = get_inverters_power_or_energy_data_mp(plant, inverters, energy, starttime, endtime)
            else:
                df_list = []
                order = ['timestamp']
                if energy:
                    if hasattr(plant, 'metadata') and plant.metadata.inverters_sending_daily_generation:
                        stream = INVERTER_ENERGY_FIELD
                    elif hasattr(plant, 'metadata') and plant.metadata.inverters_sending_total_generation:
                        stream = INVERTER_TOTAL_ENERGY_FIELD
                    else:
                        return []
                else:
                    stream = INVERTER_POWER_FIELD

                for inverter in solar_group.groupIndependentInverters.all().filter(isActive=True):
                    try:
                        inverter_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                stream_name=stream,
                                                                                timestamp_in_data__gte=starttime,
                                                                                timestamp_in_data__lte=endtime).\
                            limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                        timestamps = []
                        values = []
                        if plant.metadata.plantmetasource.binning_interval:
                            for data_point in inverter_data:
                                timestamps.append(data_point[1].replace(minute=(data_point[1].minute - data_point[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                                values.append(float(data_point[0]))
                        else:
                            for data_point in inverter_data:
                                timestamps.append(data_point[1].replace(second=0, microsecond=0))
                                values.append(float(data_point[0]))
                        df_list.append(pd.DataFrame({inverter.name: values,
                                                     'timestamp': pd.to_datetime(timestamps)}))
                        order.append(inverter.name)
                    except Exception as exc:
                        logger.debug(exc)
                        continue

            if len(df_list) >= 2:
                results = df_list[0]
                for i in range(1, len(df_list)):
                    if plant.slug == "omya" and energy:
                        results = results.merge(df_list[i].drop_duplicates('timestamp'), how='inner', on='timestamp')
                    else:
                        results = results.merge(df_list[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    updated_results = results
                    results = updated_results
            else:
                results = df_list[0]

            sorted_results = results.sort_values(by=['timestamp'])
            results = sorted_results
            results = results.ffill(limit=1)

            # if pandas_df, sum up the value and send back as more operations might be pending
            if pandas_df:
                results["sum"] = results.sum(axis=1)
                return results

            # otherwise, prepare the final result
            timestamps = results['timestamp'].tolist()
            power_data = results.sum(axis=1)
            values = []
            # stream name
            stream_name = 'power'
            if energy:
                stream_name = 'energy'
            for i in range(results.shape[0]):
                values.append({stream_name: power_data.values[i],
                               'timestamp': timestamps[i].to_datetime()})
            return values

        except Exception as exc:
            logger.error(str(live))
            logger.error(plant.slug)
            logger.error(str(exc))
            return []


def get_solar_groups_pr_cuf_sy(starttime, endtime, solar_group, plant):
    """

    :param starttime:
    :param endtime:
    :param solar_group:
    :param plant:
    :return:
    """
    pr = 0.0
    cuf = 0.0
    sy = 0.0
    inv_capacity = sum(tuple(solar_group.groupIndependentInverters.all().values_list('actual_capacity', flat=True)))
    try:
        df = get_solar_groups_power(starttime, endtime, solar_group, plant, True, True)
        if df.shape[0] > 0:
            df = df.rename(columns={'sum': 'energy'})
            sorted_results = df.sort(['timestamp'])
            df = sorted_results
        else:
            return pr, cuf, sy

        # check if there's data!
        df["energy"] = df["energy"].astype(float)
        df['timestamp'] = df['timestamp'].apply( lambda x: x.replace(second=0, microsecond=0))

        # get irradiation values
        if hasattr(plant, 'metadata'):
            meta_sources = solar_group.groupIOSensors.filter(stream_type="IRRADIATION"). \
                values('plant_meta__sourceKey', 'solar_field__name')
            irradiation_dict = collections.OrderedDict()
            for meta_source in meta_sources:
                irradiation = ValidDataStorageByStream.objects.filter(source_key=meta_source['plant_meta__sourceKey'],
                                                            stream_name=meta_source['solar_field__name'],
                                                            timestamp_in_data__gte=starttime,
                                                            timestamp_in_data__lte=endtime).limit(0).\
                    order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                for irr_data in irradiation:
                    if "%s" % irr_data[1] in irradiation_dict:
                        irradiation_dict["%s" % irr_data[1]].append(float(irr_data[0]))
                    else:
                        irradiation_dict["%s" % irr_data[1]] = [float(irr_data[0])]

            irradiation_data = [(datetime.datetime.strptime(ky, '%Y-%m-%d %H:%M:%S'), sum(vl) / len(vl)) for ky, vl in
                                irradiation_dict.items()]
            if plant.metadata.plantmetasource.binning_interval:
                idf = pd.DataFrame()
                irradiace = []
                timestamps = []
                for data_point in irradiation_data:

                    timestamps.append(data_point[0].replace(minute=(data_point[0].minute - data_point[0].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                    irradiace.append(float(data_point[1]))
                idf['irradiance'] = irradiace
                idf['timestamp'] = timestamps
            else:
                try:
                    idf = pd.DataFrame(irradiation_data[:], columns=['timestamp','irradiance'])
                    idf["irradiance"] = idf["irradiance"].astype(float)
                    idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                except:
                    return pr, cuf, sy

        df_energy = pd.DataFrame()
        df_energy['timestamp'] = df['timestamp']
        df_energy['energy'] = df['energy']
        df = df.dropna()
        df_energy = df_energy.dropna()
        idf = idf.dropna()

        total_energy = 0.0
        delta_hours = 24
        if plant.metadata.plantmetasource.energy_from_power:
            pr_values = df_energy.merge(idf, how='inner', on='timestamp')
            pr_values['average_irradiance'] = (pr_values["irradiance"] + pr_values["irradiance"].shift(+1))/2.0
            pr_values['delta'] = pr_values.diff()['timestamp']
            delta = pd.Timedelta(seconds=20*60)
            pr_values = pr_values[(pr_values['delta']) < delta]
            pr_values = pr_values[(pr_values['energy']) > 0.0]
            pr_values = pr_values[pr_values['energy'] < 1.5*(inv_capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))]
            pr_values['irradiance_energy'] = pr_values['average_irradiance']*(inv_capacity)*(pr_values['delta']/np.timedelta64(1, 'h'))
            if float(pr_values["irradiance_energy"].sum())==0.0:
                pr = 0.0
            else:
                total_energy = pr_values["energy"].sum()
                pr = total_energy/pr_values["irradiance_energy"].sum()
        else:
            pr_values = df_energy.merge(idf, how='inner', on='timestamp')
            pr_values['average_irradiance'] = (pr_values["irradiance"] + pr_values["irradiance"].shift(+1))/2.0
            pr_values['energy_diff'] = pr_values["energy"] - pr_values["energy"].shift(+1)
            pr_values['delta'] = pr_values.diff()['timestamp']
            if plant.slug == 'hmchalol':
                delta = pd.Timedelta(seconds=35*60)
            else:
                delta = pd.Timedelta(seconds=20*60)
            pr_values = pr_values[(pr_values['delta']) < delta]
            pr_values = pr_values[(pr_values['energy_diff']) >= 0.0]
            pr_values = pr_values[pr_values['energy_diff'] < 1.5*(inv_capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))]
            pr_values['irradiance_energy'] = pr_values['average_irradiance']*(inv_capacity)*(pr_values['delta']/np.timedelta64(1, 'h'))

            if float(pr_values["irradiance_energy"].sum())==0.0:
                pr = 0.0
            else:
                total_energy = pr_values["energy_diff"].sum()
                pr = total_energy/pr_values["irradiance_energy"].sum()

            if not len(idf) and len(df_energy)>0:
                pr_values1 = pd.DataFrame()
                pr_values1['energy_diff'] = df_energy["energy"] - df_energy["energy"].shift(+1)
                pr_values1['delta'] = df_energy.diff()['timestamp']
                pr_values1 = pr_values1[(pr_values1['delta']) < delta]
                pr_values1 = pr_values1[(pr_values1['energy_diff']) >= 0.0]
                pr_values1 = pr_values1[pr_values1['energy_diff'] < 1.5 * (inv_capacity / 60.0) * (pr_values1['delta'] / np.timedelta64(1, 'm'))]
                total_energy = pr_values1["energy_diff"].sum()
        if total_energy:
            cuf = total_energy / (delta_hours * inv_capacity)
            sy = total_energy / inv_capacity
        return pr, cuf, sy
    except:
        return 0.0, 0.0, 0.0


def get_group_power_irradiation(starttime, endtime, solar_group, plant, error=False):
    """

    :param starttime:
    :param endtime:
    :param solar_group:
    :param plant:
    :param error:
    :return:
    """
    try:
        power_values_df = get_solar_groups_power(starttime, endtime, solar_group, plant, True, False, True, live=True)
        irradiation_values = get_solar_groups_irradiation_data(starttime, endtime, solar_group, plant)
        try:
            delta = (int(plant.metadata.plantmetasource.dataReportingInterval)/60)*1.5 if plant.gateway.all()[0].isVirtual else 20
        except:
            delta = 30
        if type(power_values_df) is not list and type(irradiation_values) is not list and power_values_df.shape[0] > 0 and irradiation_values.shape[0]:
            power_values = pd.DataFrame()
            power_values['power'] = power_values_df['sum']
            power_values['timestamp'] = power_values_df['timestamp']
            power_values['ts'] = power_values_df['timestamp'].diff()
            power_values = power_values.dropna()

            power_values_missing = power_values[(power_values['ts'] / np.timedelta64(1, 'm'))>delta]
            print "power_values_missing"
            print power_values_missing
            missing_index = power_values_missing.index.tolist()
            print "missing_index"
            print missing_index
            power_values_filling = pd.DataFrame(columns={'timestamp'})
            filling_timestamp = []
            try:
                if str(plant.metadata.plantmetasource.gateway_manufacturer).upper() == 'WEBDYN':
                    reporting_interval = 15
                else:
                    reporting_interval = 5
            except:
                reporting_interval = 15
            print reporting_interval
            for index in range(len(missing_index)):
                try:
                    missing_period = (power_values_missing.iloc[index]['ts'] / np.timedelta64(1, 'm'))/reporting_interval
                    print missing_period
                    for i in range(int(missing_period)):
                        try:
                            filling_timestamp.append(power_values_missing.iloc[index]['timestamp']- timedelta(minutes=(i+1)*reporting_interval))
                        except:
                            continue
                    #filling_timestamp.append(power_values_missing.iloc[index]['timestamp']- timedelta(minutes=((power_values_missing.iloc[index]['ts'] / np.timedelta64(1, 'm'))/2)))
                except Exception as exception:
                    print str(exception)
                    continue
            print "filling_timestamp"
            print filling_timestamp
            power_values_filling['timestamp'] = filling_timestamp
            power_values= power_values[power_values['power']>=0]
            power_values = power_values.merge(power_values_filling, on='timestamp', how='outer')
            power_values = power_values.drop('ts', 1)
            power_values = power_values.sort_values(by=['timestamp'])
            #irradiation_values = irradiation_values[irradiation_values['irradiation']>=0]
            #power_values = power_values.where(pd.notnull(power_values), None)
            final_values = power_values.merge(irradiation_values, on='timestamp', how='outer')
            if error:
                final_values['Inverters_up'] = power_values_df.count(axis=1)-2
                final_values['Inverters_down'] = len(solar_group.groupIndependentInverters.all()) - (power_values_df.count(axis=1)-2)
                modbus_errors = get_solar_groups_modbus_read_errors(starttime, endtime, plant)
                inverter_errors = get_solar_groups_inverter_errors(starttime, endtime, plant)
                if type(modbus_errors) is not list and modbus_errors.size>0:
                    final_values = final_values.merge(modbus_errors, on='timestamp', how='outer')
                if type(inverter_errors) is not list and inverter_errors.size>0:
                    final_values = final_values.merge(inverter_errors, on='timestamp', how='outer')
                try:
                    max_power = power_values_df['sum'].max()
                except:
                    max_power = 0.0
                return final_values.sort_values(by=['timestamp']).to_json(orient='records', date_format='iso'), max_power
            return final_values.sort_values(by=['timestamp']).to_json(orient='records', date_format='iso')
        elif type(power_values_df) is not list and power_values_df.shape[0]>0:
            power_values = pd.DataFrame()
            power_values['power'] = power_values_df['sum']
            power_values['timestamp'] = power_values_df['timestamp']
            power_values['ts'] = power_values['timestamp'].diff()
            power_values = power_values.dropna()
            power_values_missing = power_values[(power_values['ts'] / np.timedelta64(1, 'm'))>delta]
            missing_index = power_values_missing.index.tolist()
            power_values_filling = pd.DataFrame(columns={'timestamp'})
            filling_timestamp = []
            for index in range(len(missing_index)):
                try:
                    filling_timestamp.append(power_values_missing.iloc[index]['timestamp']- timedelta(minutes=((power_values_missing.iloc[index]['ts'] / np.timedelta64(1, 'm'))/2)))
                except Exception as exception:
                    print str(exception)
                    continue
            power_values_filling['timestamp'] = filling_timestamp
            power_values = power_values.merge(power_values_filling, on='timestamp', how='outer')
            power_values = power_values.sort_values(by=['timestamp'])
            power_values = power_values.drop('ts', 1)
            #power_values = power_values.where(pd.notnull(power_values), None)
            if error:
                modbus_errors = get_solar_groups_modbus_read_errors(starttime, endtime, solar_group, plant)
                inverter_errors = get_solar_groups_inverter_errors(starttime, endtime, solar_group, plant)
                if type(modbus_errors) is not list and modbus_errors.size>0:
                    power_values = power_values.merge(modbus_errors, on='timestamp', how='outer')
                if type(inverter_errors) is not list and inverter_errors.size>0:
                    power_values = power_values.merge(inverter_errors, on='timestamp', how='outer')
                try:
                    max_power = power_values_df['sum'].max()
                except:
                    max_power = 0.0
                return power_values.sort_values(by=['timestamp']).to_json(orient='records', date_format='iso'), max_power
            return power_values.sort_values(by=['timestamp']).to_json(orient='records', date_format='iso')
        elif type(irradiation_values) is not list and irradiation_values.shape[0]>0:
            irradiation_values['ts'] = irradiation_values['timestamp'].diff()
            irradiation_values_missing = irradiation_values[(irradiation_values['ts'] / np.timedelta64(1, 'm'))>delta]
            irradiation_missing_index = irradiation_values_missing.index.tolist()
            irradiation_values_filling = pd.DataFrame(columns={'timestamp'})
            filling_timestamp = []
            for index in range(len(irradiation_missing_index)):
                try:
                    filling_timestamp.append(irradiation_values_missing.iloc[index]['timestamp']- timedelta(minutes=((irradiation_values_missing.iloc[index]['ts'] / np.timedelta64(1, 'm'))/2)))
                except Exception as exception:
                    print str(exception)
                    continue
            irradiation_values_filling['timestamp'] = filling_timestamp
            irradiation_values= irradiation_values[irradiation_values['irradiation']>=0]
            irradiation_values = irradiation_values.merge(irradiation_values_filling, on='timestamp', how='outer')
            irradiation_values = irradiation_values.drop('ts', 1)
            irradiation_values = irradiation_values.sort_values(by=['timestamp'])
            return irradiation_values.sort_values(by=['timestamp']).to_json(orient='records', date_format='iso')
        else:
            return []
    except Exception as exception:
        print(str(exception))
        return []


def get_solar_groups_irradiation_data(starttime, endtime, solar_group, plant):
    """

    :param starttime:
    :param endtime:
    :param plant:
    :return:
    """
    meta_sources = solar_group.groupIOSensors.filter(stream_type="IRRADIATION").\
        values('plant_meta__sourceKey', 'solar_field__name', 'solar_field__displayName')
    df_list_irradiation = pd.DataFrame()
    try:
        for meta_source in meta_sources:
            irradiation_data = ValidDataStorageByStream.objects.filter(source_key=meta_source['plant_meta__sourceKey'],
                                                        stream_name=meta_source['solar_field__name'],
                                                        timestamp_in_data__gte=starttime,
                                                        timestamp_in_data__lte=endtime).limit(0).\
                    order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')


            # for data_point in irradiation_data:
            #     timestamp_irradiation.append(data_point[1].replace(second=0, microsecond=0))
            #     values_irradiation.append(float(data_point[0]))
            values_irradiation = []
            timestamp_irradiation = []
            if plant.metadata.plantmetasource.binning_interval:
                for data_point in irradiation_data:
                    timestamp_irradiation.append(data_point[1].replace(minute=(data_point[1].minute - data_point[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                    values_irradiation.append(float(data_point[0]))
            else:
                for data_point in irradiation_data:
                    timestamp_irradiation.append(data_point[1].replace(second=0, microsecond=0))
                    values_irradiation.append(float(data_point[0]))
            pd_data_frame = pd.DataFrame({'timestamp': pd.to_datetime(timestamp_irradiation),
                                        '%s_irradiation' % meta_source['solar_field__displayName']: values_irradiation})

            df_list_irradiation = pd_data_frame if df_list_irradiation.empty else df_list_irradiation.merge(pd_data_frame, on='timestamp', how='outer')
        return df_list_irradiation
    except Exception as exception:
        print(str(exception))
        return []


def get_solar_groups_modbus_read_errors(starttime, endtime, solar_group, plant):
    try:
        df_results_modbus_error = pd.DataFrame()
        df_final_result = pd.DataFrame()
        inverters = solar_group.groupIndependentInverters.all()
        for inverter in inverters:
            df_modbus_error = []
            modbus_errors = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                stream_name='ERROR_MODBUS_READ',
                                                                timestamp_in_data__gte=starttime,
                                                                timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_modbus_error = []
            timestamp_modbus_error = []
            # for data_point in modbus_errors:
            #         timestamp_modbus_error.append(data_point[1].replace(second=0, microsecond=0))
            #         values_modbus_error.append(float(data_point[0]))
            if plant.slug == 'dominicus':
                for data_point in modbus_errors:
                    timestamp_modbus_error.append(data_point[1].replace(minute=data_point[1].minute - data_point[1].minute%5,
                                                            second=0,
                                                            microsecond=0))
                    values_modbus_error.append(float(data_point[0]))
            else:
                for data_point in modbus_errors:
                    timestamp_modbus_error.append(data_point[1].replace(second=0, microsecond=0))
                    values_modbus_error.append(float(data_point[0]))
            df_modbus_error.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_modbus_error),
                                                 str(inverter.name)+'_READ_ERROR': values_modbus_error}))
            if len(df_modbus_error)>0:
                df_results_modbus_error_temp = df_modbus_error[0]
                if df_results_modbus_error.empty:
                    df_results_modbus_error = df_results_modbus_error_temp
                else:
                    df_new = pd.merge(df_results_modbus_error, df_results_modbus_error_temp, on='timestamp', how='outer')
                    df_results_modbus_error = df_new
        #return df_results_modbus_error.sort('timestamp').dropna(axis=1, how='all')
        df_results_modbus_error['modbus_error'] = df_results_modbus_error.sum(axis=1)
        df_final_result['modbus_read_error'] = df_results_modbus_error['modbus_error']
        df_final_result['timestamp'] = df_results_modbus_error['timestamp']
        df_final_result.dropna()
        df_final_result['modbus_read_error'] = True
        return df_final_result
    except Exception as exception:
        print(str(exception))
        return []


def get_solar_groups_inverter_errors(starttime, endtime, solar_group, plant):
    try:
        df_results_inverter_errors = pd.DataFrame()
        df_final_result = pd.DataFrame()
        inverters = solar_group.groupIndependentInverters.all()
        for inverter in inverters:
            df_inverter_error = []
            inverter_errors = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                  stream_name='ERROR_CODE',
                                                                  timestamp_in_data__gte=starttime,
                                                                  timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_inverter_error = []
            timestamp_inverter_error = []
            # for data_point in inverter_errors:
            #         timestamp_inverter_error.append(data_point[1].replace(second=0, microsecond=0))
            #         values_inverter_error.append(float(data_point[0]))
            if plant.slug == 'dominicus':
                for data_point in inverter_errors:
                    try:
                        timestamp_inverter_error.append(data_point[1].replace(minute=data_point[1].minute - data_point[1].minute%5,
                                                                second=0,
                                                                microsecond=0))
                        values_inverter_error.append(float(data_point[0]))
                    except Exception as exception:
                        print(str(exception))
            else:
                for data_point in inverter_errors:
                    timestamp_inverter_error.append(data_point[1].replace(second=0, microsecond=0))
                    values_inverter_error.append(float(data_point[0]))

            df_inverter_error.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_inverter_error),
                                                str(inverter.name)+'_ALARM': values_inverter_error}))

            if len(df_inverter_error)>0:
                df_results_inverter_error_temp = df_inverter_error[0]
                if df_results_inverter_errors.empty:
                    df_results_inverter_errors = df_results_inverter_error_temp
                else:
                    df_new = pd.merge(df_results_inverter_errors, df_results_inverter_error_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                    df_results_inverter_errors = df_new
        #return df_results_inverter_errors.sort('timestamp').dropna(axis=1, how='all')
        df_results_inverter_errors['inverter_error'] = df_results_inverter_errors.sum(axis=1)
        df_final_result['inverter_error'] = df_results_inverter_errors['inverter_error']
        df_final_result['timestamp'] = df_results_inverter_errors['timestamp']
        df_final_result.dropna()
        df_final_result['inverter_error'] = True
        return df_final_result
    except Exception as exception:
        print(str(exception))
        return []
