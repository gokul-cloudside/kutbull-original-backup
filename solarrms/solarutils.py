from dataglen.models import ValidDataStorageByStream, Sensor
from django.conf import settings
from solarrms.settings import INVERTER_CHART_FIELDS, INVERTER_CHART_LEN
from solarrms.settings import INPUT_PARAMETERS, OUTPUT_PARAMETERS, STATUS_PARAMETERS, VALID_ENERGY_CALCULATION_DELTA_MINUTES
import logging
import pandas as pd
import pytz, sys
from utils.errors import generate_exception_comments
import numpy as np
from kutbill import settings
from solarrms.models import PerformanceRatioTable, CUFTable, SolarPlant, SolarGroup, IndependentInverter, SolarField, \
    PredictionData, PlantMetaSource, WeatherData, NewPredictionData, EnergyLossTableNew, EnergyLossTable, \
    PlantDeviceSummaryDetails, PlantAggregatedInfo
from solarrms.models import KWHPerMeterSquare, PlantSummaryDetails, EnergyMeter

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)
PREDICTION_TIMEPERIOD = settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES

from solarrms.settings import PLANT_POWER_STREAM, PLANT_ENERGY_STREAM, INVERTER_ENERGY_FIELD, INVERTER_POWER_FIELD, \
    INVERTER_VALID_LAST_ENTRY_MINUTES, INVERTER_TOTAL_ENERGY_FIELD, WEBDYN_PLANTS_SLUG, \
    VALID_ENERGY_CALCULATION_DELTA_MINUTES_DOMINICUS, PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA, ENERGY_CALCULATION_STREAMS, \
    ENERGY_METER_STREAM_UNITS, ENERGY_METER_STREAM_UNIT_FACTOR, PLANT_TOTAL_ENERGY_STREAM, TOTAL_ENERGY_CALCULATION_STREAMS

from datetime import timedelta, datetime
from django.core.exceptions import ObjectDoesNotExist
import math
import json
import collections
from errors.models import ErrorStorageByStream
from dashboards.utils import is_owner
from django.utils import timezone
from xlsxwriter.utility import xl_rowcol_to_cell


AGGREGATED_POWER_PLANT_SLUGS = []       

def natural_key(string_):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
            return dt.astimezone(tz).replace(tzinfo=None)
        else:
            return dt.astimezone(tz).replace(tzinfo=None)
    except Exception as exc:
        return dt

def filter_solar_plants(context):
    solar_plants = []
    try:
        for group in context['groups_details']:
            try:
                solar_plant = group['instance'].solarplant
                solar_plants.append(solar_plant)
            except:
                continue
        return solar_plants
    except KeyError:
        return solar_plants

def get_inverter_stream_data(inverter, stream_name):
    try:
        stream_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                              stream_name=stream_name).limit(INVERTER_CHART_LEN)
        data = []
        for value in stream_data:
            ts = value.timestamp_in_data# - timedelta(hours=5, minutes=30)
            data.append([int(ts.strftime("%s")) * 1000,
                         value.stream_value])
        return data
    except Exception as E:
        return None

def get_inverter_data(inverter):
    streams = INVERTER_CHART_FIELDS
    data = {}

    for stream in streams:
        stream_data = get_inverter_stream_data(inverter, stream)
        data[stream] = [{'key': stream, 'values': stream_data}]

    return data

def get_inverter_last_record(inverter):
    input_values = {}
    output_values = {}
    status_values = {}

    try:
        for stream_name in INPUT_PARAMETERS:
            stream_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                  stream_name=stream_name).limit(1)
            if len(stream_data) == 1:
                input_values[stream_name] = stream_data[0].stream_value

        for stream_name in OUTPUT_PARAMETERS:
            stream_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                  stream_name=stream_name).limit(1)
            if len(stream_data) == 1:
                output_values[stream_name] = stream_data[0].stream_value

        for stream_name in STATUS_PARAMETERS:
            stream_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                  stream_name=stream_name).limit(1)
            if len(stream_data) == 1:
                status_values[stream_name] = stream_data[0].stream_value
    except:
        pass

    return input_values, output_values, status_values

def sync_values(data):
    data_dict = {}
    timestamps_list = []
    for entry in data:
        data_dict[entry["key"]] = {}
        ts_list = []
        for value in entry["values"]:
            data_dict[entry["key"]][value[0]] = value[1]
            ts_list.append(value[0])
        timestamps_list.append(set(ts_list))

    if len(timestamps_list) > 0:
        timestamps = sorted(list(set.union(*timestamps_list)))
    else:
        timestamps = []

    final_data = []
    for key in data_dict.keys():
        values = []
        for ts in timestamps:
            try:
                values.append([ts, data_dict[key][ts]])
            except KeyError:
                values.append([ts, 0.0])
        final_data.append({"key": key, "values": values})

    return final_data

def fill_results(results):
    return results

def get_all_inverters_data(inverters, stream_names, starttime, endtime, union=True, json=True):
    data = {}
    order = ['timestamp']
    for stream in stream_names:
        df_list = []
        for inverter in inverters:
            try:
                inverter_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                        stream_name=stream,
                                                                        timestamp_in_data__gte=starttime,
                                                                        timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                timestamps = []
                values = []
                for data_point in inverter_data:
                    timestamps.append(update_tz(data_point[1].replace(microsecond=0, second=0),
                                                                      'Asia/Kolkata'))
                    values.append(data_point[0])
                # get this inverter stream
                try:
                    stream_obj = inverter.fields.get(name=stream)
                    column_name = "_".join([inverter.name, stream_obj.name, stream_obj.streamDataUnit])
                except:
                    column_name = inverter.name

                df_list.append(pd.DataFrame({column_name: values,
                                             'timestamp': pd.to_datetime(timestamps)}))
                order.append(column_name)
            except Exception as exc:
                logger.debug(exc)
                continue
        try:
            if len(df_list) >= 2:
                results = df_list[0]
                for i in range(1, len(df_list)):
                    if union:
                        results = results.merge(df_list[i], how='outer', on='timestamp')
                    else:
                        results = results.merge(df_list[i], how='inner', on='timestamp')
                    updated_results = fill_results(results)
                    results = updated_results
            else:
                results = df_list[0]

            sorted_results = results.sort(['timestamp'])
            results = sorted_results
            results = results.ffill(limit=1)

            if json:
                data[stream] = results.to_json()
            else:
                data[stream] = results.to_csv(date_format="%Y-%m-%dT%H:%M:%SZ",
                                              index=False,
                                              columns=order)
        except Exception as exc:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            logger.debug(comments)
            continue
    return data


def get_plant_power(starttime, endtime, plant, pandas_df=False, energy=False, split=False, meter_energy=True, all_meters=False, live=False, aggregated_power=False):

    try:
        if plant.slug in ["instaproducts", 'beaconsfield', 'ausnetdemosite', 'benalla', 'collingwood', 'leongatha',
                          'lilydale', 'rowville', 'seymour', 'thomastown', 'traralgon', 'wodonga', 'yarraville']:
            PLANT_TZ = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            starttime = PLANT_TZ.localize(starttime).astimezone(pytz.timezone("UTC"))
            endtime = PLANT_TZ.localize(endtime).astimezone(pytz.timezone("UTC"))
    except:
        pass

    if (split is False) and hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_power:
        data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                       stream_name=PLANT_POWER_STREAM,
                                                       timestamp_in_data__gte=starttime,
                                                       timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

        values = [{'power': entry[0], 'timestamp':entry[1].replace(second=0, microsecond=0)} for entry in data]
        return values

    elif hasattr(plant, 'metadata') and plant.metadata.meter_power and (energy is False):
        df = pd.DataFrame()
        active_meters = plant.energy_meters.all().filter(energy_calculation=True)
        print active_meters
        for meter in active_meters:
            meter_df = pd.DataFrame()
            data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                           stream_name='WATT_TOTAL',
                                                           timestamp_in_data__gte=starttime,
                                                           timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

            meter_power = []
            timestamps = []
            if plant.metadata.plantmetasource.binning_interval:
                for data_point in data:
                    timestamps.append(data_point[1].replace(minute=(data_point[1].minute - data_point[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                    meter_power.append(float(data_point[0]))
            else:
                for data_point in data:
                    timestamps.append(data_point[1].replace(second=0, microsecond=0))
                    meter_power.append(float(data_point[0]))
            meter_df['timestamp'] = timestamps
            meter_df[str(meter.name)] = meter_power
            if df.empty:
                df = meter_df
            else:
                df = df.merge(meter_df, on='timestamp', how='outer')
        df['sum'] = df.sum(axis=1)
        if pandas_df:
            return df
        else:
            timestamps = df['timestamp'].tolist()
            #power_data = df.sum(axis=1)
            power_data = df['sum']
            values = []
            stream_name = 'power'
            for i in range(df.shape[0]):
                values.append({stream_name: power_data.values[i],
                               'timestamp': timestamps[i].to_datetime()})
            return values

    elif energy is True and plant.metadata.plantmetasource.energy_from_power is True:
        inverters = plant.independent_inverter_units.all()
        pd_power_energy = pd.DataFrame()
        for inverter in inverters:
            ac_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'ACTIVE_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
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

    elif len(plant.energy_meters.filter(energy_calculation=True)) > 0 and energy and meter_energy:
        df_list = []
        order = ['timestamp']
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

        if all_meters is True:
            meters = plant.energy_meters.all().filter(isActive=True)
        else:
            meters = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)

        for meter in meters:
            try:
                meter_data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name=stream,
                                                                     timestamp_in_data__gte=starttime,
                                                                     timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                timestamps = []
                values = []
                print len(meter_data)
                if plant.metadata.plantmetasource.binning_interval:
                    for data_point in meter_data:
                        timestamps.append(data_point[1].replace(minute=(data_point[1].minute - data_point[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                        if energy_unit:
                            values.append(float(data_point[0]))
                        else:
                            values.append(float(data_point[0])*unit_factor)
                else:
                    for data_point in meter_data:
                        timestamps.append(data_point[1].replace(second=0, microsecond=0))
                        if energy_unit:
                            values.append(float(data_point[0]))
                        else:
                            values.append(float(data_point[0])*unit_factor)
                df_list.append(pd.DataFrame({meter.name: values,
                                             'timestamp': pd.to_datetime(timestamps)}))
                order.append(meter.name)
            except Exception as exc:
                logger.debug(str(exc))
                continue
        try:
            if len(df_list) >= 2:
                results = df_list[0]
                for i in range(1, len(df_list)):
                    results = results.merge(df_list[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    updated_results = fill_results(results)
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
        except:
            return []
    else:
        try:
            if live:
                from utils.multiprocess import get_inverters_power_or_energy_data_mp
                df_list = get_inverters_power_or_energy_data_mp(plant,
                                                                plant.independent_inverter_units.filter(isActive=True),
                                                                energy, starttime, endtime)
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

                if aggregated_power and not energy:
                    try:
                        inverter_data = PlantAggregatedInfo.objects.filter(identifier=str(plant.slug),
                                                                          stream_name='INVERTER_SUM_ACTIVE_POWER',
                                                                          window_st_ts__gte=starttime,
                                                                          window_st_ts__lte=endtime).limit(0).order_by('window_st_ts').values_list('stream_value', 'window_st_ts')
                        timestamps = []
                        values = []
                        for data_point in inverter_data:
                                timestamps.append(data_point[1].replace(second=0, microsecond=0))
                                values.append(float(data_point[0]))
                        df_list.append(pd.DataFrame({str(plant.slug): values,
                                                     'timestamp': pd.to_datetime(timestamps)}))
                        order.append(str(plant.slug))
                    except Exception as exception:
                        print str(exception)

                else:
                    for inverter in plant.independent_inverter_units.all().filter(isActive=True):
                        try:
                            inverter_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                    stream_name=stream,
                                                                                    timestamp_in_data__gte=starttime,
                                                                                    timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
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
                    if (plant.slug == "omya" or plant.slug == "rspllimited" or plant.slug == "instaproducts") and energy:
                        results = results.merge(df_list[i].drop_duplicates('timestamp'), how='inner', on='timestamp')
                    else:
                        results = results.merge(df_list[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    updated_results = fill_results(results)
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


def get_groups_power(starttime, endtime, plant, group_names):
    try:
        df_results = pd.DataFrame
        for group_name in group_names:
            try:
                df_list = []
                order = ['timestamp']
                group = SolarGroup.objects.get(plant=plant, name=group_name)
            except ObjectDoesNotExist as exception:
                logger.debug(str(exception))
                return -1
            inverters = group.groupIndependentInverters.all().filter(isActive=True)
            for inverter in inverters:
                try:
                    inverter_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                            stream_name=INVERTER_POWER_FIELD,
                                                                            timestamp_in_data__gt=starttime,
                                                                            timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
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
                    logger.debug(str(exc))
                    continue
            try:
                if len(df_list) >= 2:
                    results = df_list[0]
                    for i in range(1, len(df_list)):
                        results = results.merge(df_list[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                        updated_results = fill_results(results)
                        results = updated_results
                else:
                    if len(df_list) == 1:
                        results = df_list[0]
                sorted_results = results.sort(['timestamp'])
                results = sorted_results
                timestamps = results['timestamp'].tolist()
                power_data = results.sum(axis=1)
                values = []
                for i in range(results.shape[0]):
                    values.append({group_name: power_data.values[i],
                                   'timestamp': timestamps[i].to_datetime()})

                df_values = pd.DataFrame(data=values, columns=['timestamp', group_name])
                if df_results.empty:
                    df_results = df_values
                else:
                    df_new = pd.merge(df_results, df_values, on='timestamp', how='outer')
                    df_results = df_new
            except Exception as exception:
                logger.debug(str(exception))
        if df_results.empty:
            return []
        else:
            return df_results.to_json(orient='records', date_format='iso')
    except Exception as exception:
        logger.debug(str(exception))


def energy_df_to_packaged_data(energy_df, capacity):
    energy_df_diff = energy_df.diff()
    energy_df["energy"] = energy_df_diff["sum"]
    energy_df["deltas"] = energy_df_diff["timestamp"]
    delta = pd.Timedelta(seconds=INVERTER_VALID_LAST_ENTRY_MINUTES*60)
    accepted_values = energy_df[energy_df['deltas'] < delta]
    accepted_values = accepted_values[(accepted_values['energy'] >= 0) & (accepted_values['energy'] <= capacity)]
    packaged_data = accepted_values[['energy', 'timestamp']].to_dict('records')
    return packaged_data


def get_energy_from_power(power_values, energy_delta=False):
    try:
        power_values['average'] = (power_values["sum"] + power_values["sum"].shift(+1))/2.0
        power_values['delta'] = power_values.diff()['timestamp']
        if energy_delta:
            delta = pd.Timedelta(seconds=20*60)
        else:
            delta = pd.Timedelta(seconds=VALID_ENERGY_CALCULATION_DELTA_MINUTES*60)
        accepted_values = power_values[(power_values['delta']) < delta]
        accepted_values['energy'] = accepted_values['average']*(accepted_values['delta']/np.timedelta64(1, 'h'))
        return accepted_values
    except:
        return []

def get_energy_from_power_dominicus(power_values, energy_delta=False):
    power_values['average'] = (power_values["sum"] + power_values["sum"].shift(+1))/2.0
    power_values['delta'] = power_values.diff()['timestamp']
    if energy_delta:
        delta = pd.Timedelta(seconds=20*60)
    else:
        delta = pd.Timedelta(seconds=VALID_ENERGY_CALCULATION_DELTA_MINUTES_DOMINICUS*60)
    accepted_values = power_values[(power_values['delta']) < delta]
    accepted_values['energy'] = accepted_values['average']*(accepted_values['delta']/np.timedelta64(1, 'h'))
    return accepted_values


def get_plant_energy(starttime, endtime, plant, aggregator):
    # first check if we're getting the data from a gateway
    if hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_power:
        energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                              stream_name=PLANT_ENERGY_STREAM,
                                                              timestamp_in_data__gt=starttime,
                                                              timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

        timestamps = []
        values = []
        for data_point in energy_data:
            timestamps.append(data_point[1].replace(second=0, microsecond=0))
            values.append(float(data_point[0]))
        energy_df = pd.DataFrame({'sum': values,
                                  'timestamp': pd.to_datetime(timestamps)})
        sorted_results = energy_df.sort(['timestamp'])
        energy_df = sorted_results
        return energy_df_to_packaged_data(energy_df, plant.capacity)
    else:
        # consider case where inverters are smart and send daily_yield
        energy_df = get_plant_power(starttime, endtime, plant, True, True)

        if energy_df.shape[0] > 0:
            return energy_df_to_packaged_data(energy_df, plant.capacity)
        else:
            # get a pandas data frame for power values, integration them and send
            power_values = get_plant_power(starttime, endtime, plant, True)
            accepted_values = get_energy_from_power(power_values)
            packaged_data = accepted_values[['energy', 'timestamp']].to_dict('records')
            return packaged_data


def extract_energy_values(group, plant, tail):
    if hasattr(plant, 'metadata') and plant.metadata.inverters_sending_daily_generation:
        sending_daily_generation = True
    else:
        sending_daily_generation = False
    inverters_values = {}
    energy_sum = 0.0
    for col in group:
        try:
            if col not in ["timestamp", "energy"]:
                if sending_daily_generation:
                    value = float(group[col][group[col].last_valid_index() - tail]) - 0.0
                else:
                    value = float(group[col][group[col].last_valid_index()]) - float(group[col][group[col].first_valid_index()])
                inverters_values[col] = value
                # we only consider values that are greater than 0
                if len(plant.energy_meters.all())>0:
                    energy_sum += value
                elif value >=0 and value <= int(plant.capacity)/len(plant.independent_inverter_units.all())*15:
                    energy_sum += value
                elif hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy and value >= 0:
                    energy_sum += value
        except:
            continue
    inverters_values['energy'] = energy_sum
    return inverters_values, energy_sum

def calculate_daily_energy(grouped, plant, sum_energy, split):
    try:
        local_timezone = plant.metadata.plantmetasource.dataTimezone
    except:
        local_timezone = "Asia/Kolkata"
    data = []
    for name, group in grouped:
        inverters_values = {}
        if sum_energy:
            # only energy sum
            energy = group.sum()["energy"]
        else:
            inverters_values, energy = extract_energy_values(group, plant, 0)
        if energy >= 0:
            if split is False:
                data.append({'timestamp': pd.to_datetime(name).tz_localize(local_timezone).tz_convert('UTC'),
                             'energy': energy})
            else:
                data.append({'timestamp': pd.to_datetime(name).tz_localize(local_timezone).tz_convert('UTC'),
                             'energy': inverters_values})
        # a hack for webdyn
        else:
            inverters_values, energy = extract_energy_values(group, plant, 1)
            try:
                if energy >= 0:
                    if split is False:
                        data.append({'timestamp': pd.to_datetime(name).tz_localize(local_timezone).tz_convert('UTC'),
                                     'energy': energy})
                    else:
                        data.append({'timestamp': pd.to_datetime(name).tz_localize(local_timezone).tz_convert('UTC'),
                                     'energy': inverters_values})
            except:
                continue
        # hack ends.
    return data

def energy_packaging(df, capacity, aggregator, plant, sum_energy=False, split=False):
    # drop the negative values and any super large values
    # hack for webdyn's gateway error
    try:
        local_timezone = plant.metadata.plantmetasource.dataTimezone
    except:
        local_timezone = "Asia/Kolkata"
    try:
        # if capacity < 1000:
        #     df = df[df['energy'] < 1000000]

        if aggregator == "HOUR":
            # a data point at 10:00 should not be considered in hour 10:00, but in 09
            grouped = df.groupby(df['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone).replace(
                minute=0, second=0, microsecond=0)))
        elif aggregator == "DAY" or aggregator == "MONTH":
            grouped = df.groupby(df['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone).date()))
        else:
            return []
        data = []
        if aggregator == "DAY":
            data = calculate_daily_energy(grouped, plant, sum_energy, split)
            return data
        elif aggregator == "HOUR":
            if sum_energy:
                energy = grouped.sum()
            else:
                energy = grouped.first().shift(-1).convert_objects(convert_numeric=True) - \
                         grouped.first().convert_objects(convert_numeric=True)
                energy = energy[(energy["energy"] >= 0) &
                                #(energy["energy"] < 10000000) &
                                (energy['timestamp'] < pd.Timedelta(minutes=70))]
            for key, value in energy["energy"].iteritems():
                data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': value})
            return data
        else:
            data = calculate_daily_energy(grouped, plant, sum_energy, split)
            # from day energy to monthly
            try:
                monthly_data = pd.DataFrame(data, columns=['timestamp','energy'])
            except:
                return []
            monthly_grouped = monthly_data.groupby(monthly_data['timestamp'].map(lambda x: x.tz_convert(local_timezone).replace(day=1)))
            data = []
            for name, group in monthly_grouped:
                data.append({'timestamp': pd.to_datetime(name).tz_convert('UTC'),
                             'energy' : group.sum()["energy"]})
            return data
    except:
        return []

# def get_minutes_aggregated_power(starttime, endtime, plant, aggregator, aggregation_period, split=False, meter_energy=False):
#     try:
#         try:
#             starttime = starttime - timedelta(minutes=1)
#         except:
#             starttime = starttime
#         try:
#             endtime = endtime - timedelta(minutes=1)
#         except:
#             endtime = endtime
#         print starttime
#         print endtime
#         try:
#             local_timezone = plant.metadata.plantmetasource.dataTimezone
#         except:
#             local_timezone = 'Asia/Kolkata'
#         if aggregator == 'MINUTE':
#             aggregation = str(aggregation_period) + 'Min'
#         elif aggregator == 'DAY':
#             aggregation = str(aggregation_period) + 'D'
#         elif aggregator == 'MONTH':
#             aggregation = str(aggregation_period) + 'M'
#         else:
#             aggregation = '1D'
#         df = pd.DataFrame()
#         final_values = {}
#         meters = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)
#         inverters = plant.independent_inverter_units.all().filter(isActive=True)
#         if meter_energy is True and len(meters)>0:
#             devices = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)
#             for meter in meters:
#                 sf = SolarField.objects.get(source=meter, name='WATT_TOTAL')
#                 if sf.streamDataUnit == 'MW':
#                     factor = 1000
#                 elif sf.streamDataUnit == 'W':
#                     factor = 0.001
#                 else:
#                     factor = 1
#                 df_meter = pd.DataFrame()
#                 meter_values = []
#                 meter_timestamp = []
#                 power_values = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
#                                                                        stream_name="WATT_TOTAL",
#                                                                        timestamp_in_data__gte=starttime,
#                                                                        timestamp_in_data__lte=endtime)
#                 for value in power_values:
#                     meter_values.append(float(value.stream_value)*factor)
#                     meter_timestamp.append(value.timestamp_in_data)
#                 df_meter['timestamp'] = meter_timestamp
#                 df_meter[meter.name] = meter_values
#                 #df_meter = df_meter[df_meter[meter.name]>0]
#                 if df.empty:
#                     df = df_meter
#                 else:
#                     df = df.merge(df_meter.drop_duplicates('timestamp'), on='timestamp', how='outer')
#             df['sum'] = df.sum(axis=1)
#         else:
#             devices = plant.independent_inverter_units.all().filter(isActive=True)
#             for inverter in inverters:
#                 df_inverter = pd.DataFrame()
#                 inverter_values = []
#                 inverter_timestamp = []
#                 power_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
#                                                                        stream_name="ACTIVE_POWER",
#                                                                        timestamp_in_data__gte=starttime,
#                                                                        timestamp_in_data__lte=endtime)
#                 for value in power_values:
#                     inverter_values.append(float(value.stream_value))
#                     inverter_timestamp.append(value.timestamp_in_data)
#                 df_inverter['timestamp'] = inverter_timestamp
#                 df_inverter[inverter.name] = inverter_values
#                 #df_inverter = df_inverter[df_inverter[inverter.name]>0]
#                 if df.empty:
#                     df = df_inverter
#                 else:
#                     df = df.merge(df_inverter.drop_duplicates('timestamp'), on='timestamp', how='outer')
#             df['sum'] = df.sum(axis=1)
#         if split:
#             for device in devices:
#                 df_device = pd.DataFrame()
#                 df_device['timestamp'] = df['timestamp']
#                 df_device[str(device.name)] = df[(device.name)]
#                 if len(plant.energy_meters.all())==0:
#                     device_capacity = device.total_capacity if device.total_capacity is not None else device.actual_capacity
#                     df_device = df_device[df_device[str(device.name)]>0]
#                     df_device = df_device[df_device[device.name] <= 1.5*device_capacity]
#                 try:
#                     df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_convert(local_timezone))
#                 except:
#                     df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
#                 df_device = df_device.set_index('timestamp')
#                 data = []
#                 if not df_device.empty:
#                     grouped = df_device.groupby(pd.TimeGrouper(aggregation))
#                     power = grouped.mean()
#                     for key, value in power[device.name].iteritems():
#                         try:
#                             if not math.isnan(value):
#                                 data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'power': value})
#                             else:
#                                 #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
#                                 pass
#                         except:
#                             if not math.isnan(value):
#                                 data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'power': value})
#                             else:
#                                 #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
#                                 pass
#                             continue
#                 final_values[device.name] = data
#             return final_values
#         else:
#             df_final = pd.DataFrame()
#             df_final['timestamp'] = df['timestamp']
#             df_final['power'] = df['sum']
#             df_final = df_final[df_final['power']>0]
#             df_final = df_final[df_final['power'] <= 1.5*float(plant.capacity)]
#             try:
#                 df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_convert(local_timezone))
#             except:
#                 df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
#             df_final = df_final.set_index('timestamp')
#             data = []
#             if not df_final.empty:
#                 grouped = df_final.groupby(pd.TimeGrouper(aggregation))
#                 power = grouped.mean()
#                 for key, value in power['power'].iteritems():
#                     try:
#                         if not math.isnan(value):
#                             data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'power': value})
#                         else:
#                             #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
#                             pass
#                     except:
#                         if not math.isnan(value):
#                             data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'power': value})
#                         else:
#                             #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
#                             pass
#                         continue
#             return data
#     except Exception as exception:
#         print str(exception)

def get_minutes_aggregated_power(starttime, endtime, plant, aggregator, aggregation_period, split=False, meter_energy=False):
    try:
        try:
            starttime = starttime - timedelta(minutes=1)
        except:
            starttime = starttime
        try:
            endtime = endtime - timedelta(minutes=1)
        except:
            endtime = endtime
        try:
            local_timezone = plant.metadata.plantmetasource.dataTimezone
        except:
            local_timezone = 'Asia/Kolkata'
        if aggregator == 'MINUTE':
            aggregation = str(aggregation_period) + 'Min'
        elif aggregator == 'DAY':
            aggregation = str(aggregation_period) + 'D'
        elif aggregator == 'MONTH':
            aggregation = str(aggregation_period) + 'M'
        else:
            aggregation = '1D'
        final_values = {}
        df = get_plant_power(starttime, endtime, plant, pandas_df=True, energy=False, split=True, meter_energy=True)
        if plant.metadata.plantmetasource.meter_power:
            devices = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)
            if split:
                for device in devices:
                    try:
                        df_device = pd.DataFrame()
                        df_device['timestamp'] = df['timestamp']
                        df_device[str(device.name)] = df[(device.name)]
                        try:
                            df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_convert(local_timezone))
                        except:
                            df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
                        df_device = df_device.set_index('timestamp')
                        data = []
                        if not df_device.empty:
                            grouped = df_device.groupby(pd.TimeGrouper(aggregation))
                            power = grouped.mean()
                            for key, value in power[device.name].iteritems():
                                try:
                                    if not math.isnan(value):
                                        data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'power': value})
                                    else:
                                        #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                                        pass
                                except:
                                    if not math.isnan(value):
                                        data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'power': value})
                                    else:
                                        #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                                        pass
                                    continue
                        final_values[device.name] = data
                    except:
                        final_values[device.name] = []
                        continue
                    return final_values
            else:
                df_final = pd.DataFrame()
                df_final['timestamp'] = df['timestamp']
                df_final['power'] = df['sum']
                try:
                    df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_convert(local_timezone))
                except:
                    df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
                df_final = df_final.set_index('timestamp')
                data = []
                if not df_final.empty:
                    grouped = df_final.groupby(pd.TimeGrouper(aggregation))
                    power = grouped.mean()
                    for key, value in power['power'].iteritems():
                        try:
                            if not math.isnan(value):
                                data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'power': value})
                            else:
                                #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                                pass
                        except:
                            if not math.isnan(value):
                                data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'power': value})
                            else:
                                #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                                pass
                            continue
                return data
        else:
            devices = plant.independent_inverter_units.all().filter(isActive=True)
            df_device_final = pd.DataFrame()
            for device in devices:
                try:
                    df_device = pd.DataFrame()
                    df_device['timestamp'] = df['timestamp']
                    df_device[str(device.name)] = df[(device.name)]
                    device_capacity = device.total_capacity if device.total_capacity is not None else device.actual_capacity
                    df_device = df_device[df_device[str(device.name)]>0]
                    df_device = df_device[df_device[device.name] <= 1.5*device_capacity]
                    df_device = df_device.sort('timestamp')
                    if df_device_final.empty and not df_device.empty:
                        df_device_final = df_device
                    else:
                        df_device_final = df_device_final.merge(df_device.drop_duplicates('timestamp'), on='timestamp', how='outer')
                except:
                    continue
            if split:
                for device in devices:
                    try:
                        df_device = pd.DataFrame()
                        df_device['timestamp'] = df_device_final['timestamp']
                        df_device[str(device.name)] = df_device_final[str(device.name)]
                        try:
                            df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_convert(local_timezone))
                        except:
                            df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
                        df_device = df_device.set_index('timestamp')
                        data = []
                        if not df_device.empty:
                            grouped = df_device.groupby(pd.TimeGrouper(aggregation))
                            power = grouped.mean()
                            for key, value in power[device.name].iteritems():
                                try:
                                    if not math.isnan(value):
                                        data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'power': value})
                                    else:
                                        #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                                        pass
                                except:
                                    if not math.isnan(value):
                                        data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'power': value})
                                    else:
                                        #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                                        pass
                                    continue
                        final_values[device.name] = data
                    except:
                        final_values[device.name] = []
                        continue
                return final_values
            else:
                df_device_final['power'] = df_device_final.sum(axis=1)
                df_device_final['timestamp'] = df_device_final['timestamp']
                try:
                    df_device_final['timestamp'] = df_device_final['timestamp'].map(lambda x: x.tz_convert(local_timezone))
                except:
                    df_device_final['timestamp'] = df_device_final['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
                df_final = df_device_final.set_index('timestamp')
                data = []
                if not df_final.empty:
                    grouped = df_final.groupby(pd.TimeGrouper(aggregation))
                    power = grouped.mean()
                    for key, value in power['power'].iteritems():
                        try:
                            if not math.isnan(value):
                                data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'power': value})
                            else:
                                #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                                pass
                        except:
                            if not math.isnan(value):
                                data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'power': value})
                            else:
                                #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                                pass
                            continue
                return data
    except Exception as exception:
        print str(exception)


def get_minutes_aggregated_energy(starttime, endtime, plant, aggregator, aggregation_period, split=False, meter_energy=True, all_meters=False, live=False):
    try:
        from django.utils import timezone
        t0 = timezone.now()
        try:
            original_starttime = starttime
            starttime = starttime - timedelta(minutes=1)
        except:
            original_starttime = starttime
            starttime = starttime
        try:
            original_endtime = endtime
            endtime = endtime + timedelta(minutes=1)
        except:
            original_endtime = endtime
            endtime = endtime
        print starttime
        print endtime

        try:
            if plant.slug in ["instaproducts",'beaconsfield', 'ausnetdemosite', 'benalla', 'collingwood', 'leongatha', 'lilydale', 'rowville', 'seymour', 'thomastown', 'traralgon', 'wodonga', 'yarraville']:
                PLANT_TZ = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
                starttime = PLANT_TZ.localize(starttime).astimezone(pytz.timezone("UTC"))
                endtime = PLANT_TZ.localize(endtime).astimezone(pytz.timezone("UTC"))
        except:
            pass

        try:
            local_timezone = plant.metadata.plantmetasource.dataTimezone
        except:
            local_timezone = 'Asia/Kolkata'

        if (split is False) and hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy:
            energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                  stream_name=PLANT_TOTAL_ENERGY_STREAM,
                                                                  timestamp_in_data__gte=starttime,
                                                                  timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            try:
                df = pd.DataFrame(energy_data[:], columns=['energy','timestamp'])
            except Exception as exception:
                print str(exception)
                return []
            sorted_results = df.sort(['timestamp'])
            df = sorted_results
        elif (split is False) and hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed:
            energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                  stream_name='ENERGY_METER_DATA',
                                                                  timestamp_in_data__gte=starttime,
                                                                  timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            try:
                df = pd.DataFrame(energy_data[:], columns=['energy','timestamp'])
            except:
                return []
            sorted_results = df.sort(['timestamp'])
            df = sorted_results
        else:
            df = get_plant_power(starttime, endtime, plant, True, True, split=split, meter_energy=meter_energy, all_meters=all_meters, live=live)
            df = df.drop_duplicates('timestamp')
            df = df.rename(columns={'sum': 'energy'})

            #Adding below section of code to calculate approximate energy values for the missing data case
            #Adding only for gupl now, can be extended to other plants as well once we set up the data frequency for all the plants
            if not plant.metadata.plantmetasource.energy_from_power and len(plant.energy_meters.all())>0 and meter_energy is True and split is False:
                if aggregator=='MINUTE' and aggregation_period==15:
                    df_modified = df
                    try:
                        if plant.metadata.plantmetasource.gateway_manufacturer == 'Webdyn':
                            delta = 15.0
                        elif plant.metadata.plantmetasource.gateway_manufacturer == 'Soekris':
                            delta = 5.0
                        elif plant.metadata.plantmetasource.gateway_manufacturer == 'DataGlen':
                            delta = 5.0
                        else:
                            delta = 5.0
                    except:
                        delta = 5.0
                    df_modified['ts']=df_modified['timestamp'].diff()
                    df_missing = df_modified[(df_modified['ts']/np.timedelta64(1, 'm'))>delta]
                    missing_index = df_missing.index.tolist()
                    missing_ts = (df_missing['ts']/np.timedelta64(1, 'm')).tolist()
                    filling_timestamp = []
                    calculated_values = []
                    for index in range(len(missing_index)):
                        try:
                            generation_missing = (df_modified.iloc[missing_index[index]]['energy'] - df_modified.iloc[missing_index[index]-1]['energy'])/(missing_ts[index]/delta)
                            for i in range(int(missing_ts[index]/delta)-1):
                                try:
                                    filling_timestamp.append(df_modified.iloc[missing_index[index]]['timestamp']-timedelta(minutes=(i+1)*delta))
                                    if generation_missing>0:
                                        calculated_values.append(float(df_modified.iloc[missing_index[index]]['energy']-(i+1)*generation_missing))
                                    else:
                                        calculated_values.append(float(df_modified.iloc[missing_index[index]]['energy']))
                                except Exception as exception:
                                    continue
                        except Exception as exception:
                            continue

                    df_old=pd.DataFrame()
                    df_new=pd.DataFrame()
                    df_old['timestamp'] = df['timestamp']
                    df_old['energy'] = df['energy']
                    df_new['timestamp'] = filling_timestamp
                    df_new['energy'] = calculated_values
                    df_new = df_new.sort('timestamp')
                    df_old = df_old.sort('timestamp')
                    final_df_modified = df_old.append(df_new).sort('timestamp')
                    df=final_df_modified

        final_values = {}
        if aggregator == 'MINUTE':
            aggregation = str(aggregation_period) + 'Min'
        elif aggregator == 'DAY':
            aggregation = str(aggregation_period) + 'D'
        elif aggregator == 'MONTH':
            aggregation = str(aggregation_period) + 'M'
        else:
            aggregation = '1D'

        if type(df) == list:
            # get power data
            df = get_plant_power(starttime, endtime, plant, True, split=split, live=live)
            df = get_energy_from_power(df)

        if meter_energy and len(plant.energy_meters.filter(energy_calculation=True)) > 0:
            devices = plant.energy_meters.all()
            # if plant.slug == "velammaledtrust" or plant.slug == "sedam145mw" or plant.slug == "kmch":
            #     devices = plant.energy_meters.all()
            # else:
            #     devices = plant.energy_meters.filter(energy_calculation=True)
        else:
            devices = plant.independent_inverter_units.all()

        t1 = timezone.now()
        # Adding following line as for some meters are sending zero values in between data, its causing
        # miscalculation on old day plant page energy reading
        # *reference jbma 22dec2018 energy generation showing 957 on plant page and in report shoiwng 1152
        if str(plant.slug) in ['jbmasanand','nmplsanand','ansproject','jbm5project','jbmautosystem','n12']:
            df = df[df['energy'] > 0]
        if live:
            logger.debug("get_plant_power() execution time: " + str(t1-t0))
        if split:
            from utils.multiprocess import generation_grouping_mp
            final_values = generation_grouping_mp(plant, devices, df,
                                                  original_starttime, original_endtime,
                                                  aggregation, local_timezone, meter_energy)
            logger.debug("generation grouping time: "+ str(timezone.now() - t1))
            return final_values
        else:
            if (hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy) or \
                    (hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed):
                df_new = df
                df_final = pd.DataFrame()
                df_final['energy'] = (df['energy'].astype(float).diff())
                df_final['ts'] = df['timestamp'].diff()
                df_final['timestamp'] = df_new['timestamp']
                df_final = df_final[df_final['energy']>0]
                df_final = df_final[df_final['timestamp']>=original_starttime]
                df_final = df_final[df_final['timestamp']<=original_endtime]
                df_final = df_final[df_final['energy'] <= 1.5*(plant.capacity/60)*(df_final['ts'] / np.timedelta64(1, 'm'))]
                try:
                    df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_convert(local_timezone))
                except:
                    df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
                df_final = df_final.set_index('timestamp')
            else:
                df_new = df
                df_final = pd.DataFrame()
                if plant.metadata.plantmetasource.energy_from_power:
                    df_final['ts'] = df['timestamp'].diff()
                else:
                    df = (df.diff(-1))*-1
                    df = df.rename(columns={'timestamp': 'ts'})
                    # df['timestamp'] = df_new['timestamp']

                if not plant.metadata.plantmetasource.energy_from_power and len(df.columns)>2:
                    try:
                        df = df.drop(['energy'], axis=1)
                        df = df.drop(['timestamp'], axis=1)
                    except:
                        pass

                if (len(plant.energy_meters.all())==0 and not plant.metadata.plantmetasource.energy_from_power) or not meter_energy:
                    df_filter = pd.DataFrame()
                    for inverter in plant.independent_inverter_units.all():
                        df_device_new = pd.DataFrame()
                        df_device_new['timestamp'] = df_new['timestamp']
                        df_device_new[str(inverter.name)] = df_new[(inverter.name)]
                        df_device = (df_device_new.dropna(axis=0, how='any').diff(-1)) * -1

                        #df_device = (df_device_new.diff(-1)) * -1
                        df_device = df_device.rename(columns={'timestamp': 'ts'})
                        df_device['timestamp'] = df_device_new['timestamp']
                        df_inverter_filter = df_device
                        inverter_capacity = inverter.total_capacity if inverter.total_capacity is not None else inverter.actual_capacity
                        df_inverter_filter = df_inverter_filter[df_inverter_filter[str(inverter.name)]>0]
                        df_inverter_filter = df_inverter_filter[df_inverter_filter[inverter.name] <= 1.5*(inverter_capacity/60)*(df_inverter_filter['ts'] / np.timedelta64(1, 'm'))]
                        df_inverter_filter = df_inverter_filter.drop(['ts'], axis=1)
                        if df_filter.empty:
                            df_filter = df_inverter_filter
                        else:
                            df_filter = df_filter.merge(df_inverter_filter.drop_duplicates('timestamp'), on='timestamp', how='outer')

                if plant.metadata.plantmetasource.energy_from_power:
                    df_final['energy'] = df.sum(axis=1)
                    df_final['timestamp'] = df_new['timestamp']
                    df_final = df_final[df_final['energy']>=0]
                    df_final = df_final[df_final['timestamp']>=original_starttime]
                    df_final = df_final[df_final['timestamp']<=original_endtime]
                    if len(plant.energy_meters.all().filter(energy_calculation=True)) == 0 or len(plant.energy_meters.all().filter(energy_calculation=True)) == 1:
                        df_final = df_final[df_final['energy'] <= 1.5*(plant.capacity/60)*(df_final['ts'] / np.timedelta64(1, 'm'))]
                    else:
                        pass
                elif (len(plant.energy_meters.all())==0 and not plant.metadata.plantmetasource.energy_from_power) or not meter_energy:
                    df_final['energy'] = df_filter.sum(axis=1)
                    df_final['timestamp'] = df_filter['timestamp']
                    df_final = df_final[df_final['energy']>0]
                    df_final = df_final[df_final['timestamp']>=original_starttime]
                    df_final = df_final[df_final['timestamp']<=original_endtime]
                else:
                    df_final['ts'] = df['ts']
                    df_final['energy'] = df.sum(axis=1)
                    df_final['timestamp'] = df_new['timestamp']
                    df_final = df_final[df_final['energy']>=0]
                    df_final = df_final[df_final['timestamp']>=original_starttime]
                    df_final = df_final[df_final['timestamp']<=original_endtime]
                    # don't know the reason why done.
                    if len(plant.energy_meters.all().filter(energy_calculation=True)) > 0: #== 0 or len(plant.energy_meters.all().filter(energy_calculation=True)) == 1:
                        df_final = df_final[df_final['energy'] <= 1.5*(plant.capacity/60)*(df_final['ts'] / np.timedelta64(1, 'm'))]
                    else:
                        df_final = df_final[df_final['energy'] <= 1.5*(plant.capacity/60)*(df_final['ts'] / np.timedelta64(1, 'm'))]
                        pass
                try:
                    df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_convert(local_timezone))
                except:
                    df_final['timestamp'] = df_final['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
                df_final = df_final.set_index('timestamp')
            if not df_final.empty:
                data = []
                grouped = df_final.groupby(pd.TimeGrouper(aggregation))
                energy = grouped.sum()
                for key, value in energy["energy"].iteritems():
                    try:
                        if not math.isnan(value):
                            data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': value})
                        else:
                            #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                            pass
                    except:
                        if not math.isnan(value):
                            data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': value})
                        else:
                            #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                            pass
                        continue
                return data
            else:
                return []
    except Exception as exception:
        print str(exception)
        return []

def get_aggregated_energy(starttime, endtime, plant, aggregator, include_delta=False, split=False, meter_energy=True, all_meters=False):
    # adding this condition to calculate the energy from power
    if plant.metadata.plantmetasource.energy_from_power:
        if aggregator == 'DAY':
            return get_minutes_aggregated_energy(starttime, endtime, plant, aggregator, 1, split, meter_energy)
        elif aggregator == 'MONTH':
            return get_minutes_aggregated_energy(starttime, endtime, plant, aggregator, 1, split, meter_energy)
        elif aggregator == 'HOUR':
            return get_minutes_aggregated_energy(starttime, endtime, plant, 'MINUTE', 60, split, meter_energy)

    elif (split is False) and hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy:
        energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                              stream_name=PLANT_ENERGY_STREAM,
                                                              timestamp_in_data__gt=starttime,
                                                              timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
        try:
            df = pd.DataFrame(energy_data[:], columns=['plant_meta','timestamp'])
            # Adding this if condition for server error for alpine. Sunil, please verify
            if aggregator == 'HOUR':
                df = df.rename(columns={'plant_meta': 'energy'})
        except:
            return []
        sorted_results = df.sort(['timestamp'])
        df = sorted_results
        return energy_packaging(df, plant.capacity, aggregator, plant=plant)
    else:
        df = get_plant_power(starttime, endtime, plant, True, True, split=split, meter_energy=meter_energy, all_meters=all_meters)
        if type(df) != list and df.shape[0] > 0:
            try:
                df = df.drop(df.index[0])
                df = df.drop(df.index[df.shape[0]-1])
            except:
                pass
            df = df.rename(columns={'sum': 'energy'})
            return energy_packaging(df, plant.capacity, aggregator, plant=plant, split=split)
        elif type(df) == list:
            # get power data
            df = get_plant_power(starttime, endtime, plant, True, split=split)
            accepted_values = get_energy_from_power(df)
            return energy_packaging(accepted_values, plant.capacity, aggregator, plant=plant, sum_energy=True, split=split)
        else:
            return []


def get_generation_report_ranergy(starttime, endtime, plant, aggregator):
    try:
        assert(aggregator == "DAY")
        transposed_values = {}
        transposed_ts = {}
        meter_data = get_minutes_aggregated_energy(starttime,
                                                   endtime,
                                                   plant,
                                                   aggregator, 1, split=True, meter_energy=True)
        for i in range(len(meter_data.keys())):
            key = meter_data.keys()[i]
            try:
                for entry in meter_data[key]:
                    try:
                        transposed_values[key].append(int(round(entry['energy'])))
                        transposed_ts[key].append(entry['timestamp'])
                    except:
                        transposed_values[key] = [int(round(entry['energy']))]
                        transposed_ts[key] = [entry['timestamp']]

                    if i == 0 :
                        timestamp = entry['timestamp']
                        # check for insolation data
                        try:
                            insolation_values = KWHPerMeterSquare.objects.filter(
                                timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                count_time_period=86400,
                                identifier=str(plant.metadata.plantmetasource.sourceKey),
                                ts__gte=pd.to_datetime(timestamp).tz_convert('Asia/Kolkata'),
                                ts__lt=pd.to_datetime(timestamp).tz_convert('Asia/Kolkata') + timedelta(hours=24))
                            if len(insolation_values) > 0:
                                logger.debug(insolation_values[0].value)
                                try:
                                    transposed_values['Insolation (kWh/m2)'].append(round(float(insolation_values[0].value),2))
                                    transposed_ts['Insolation (kWh/m2)'].append(timestamp)
                                except:
                                    transposed_values['Insolation (kWh/m2)'] = [round(float(insolation_values[0].value),2)]
                                    transposed_ts['Insolation (kWh/m2)'] = [timestamp]
                        except:
                            pass
                        # check for PR
                        try:
                            if hasattr(plant, 'metadata') and plant.metadata.fields.get(name="IRRADIATION").isActive:
                                daily_performance_ratio = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                               identifier=plant.metadata.sourceKey,
                                                                                               ts=pd.to_datetime(timestamp).tz_convert('Asia/Kolkata').replace(hour=0,minute=0,second=0,microsecond=0)
                                                                                               ).limit(1)
                                if len(daily_performance_ratio) > 0 and daily_performance_ratio[0].performance_ratio is not None:
                                    performance_ratio = "{0:.2f}".format(daily_performance_ratio[0].performance_ratio)
                                    try:
                                        transposed_values['PR'].append(float(performance_ratio))
                                        transposed_ts['PR'].append(timestamp)
                                    except:
                                        transposed_values['PR'] = [float(performance_ratio)]
                                        transposed_ts['PR'] = [timestamp]
                                else:
                                    pass
                        except:
                            pass
            except:
                pass

        df_list = []
        order = []
        for inverter in reversed(sorted(transposed_values.keys(), key=natural_key)):
            if inverter not in ['Energy Meter', 'PR']:
                order.append(inverter)
            df_list.append(pd.DataFrame({inverter: transposed_values[inverter],
                                        'timestamp': pd.to_datetime(transposed_ts[inverter]).tz_convert('Asia/Kolkata').date}))

        if hasattr(plant, 'metadata') and plant.metadata.fields.get(name="IRRADIATION").isActive:
            order.append('PR')
        order.append('timestamp')
        if len(df_list) >= 2:
            results = df_list[0]
            for i in range(1, len(df_list)):
                results = results.merge(df_list[i], how='outer', on='timestamp')
                updated_results = fill_results(results)
                results = updated_results
        else:
            results = df_list[0]
            sorted_results = results.sort(['timestamp'])
            results = sorted_results
        return results.to_csv(date_format="%Y-%m-%d",
                              index=False,
                              columns=reversed(order))
    except Exception as exception:
        logger.debug(str(exception))
        return []


def convert_new_energy_data_format_to_old_format(new_format):
    try:
        final_result = []
        max = 0
        for key in new_format.keys():
            try:
                if len(new_format[key])>max:
                    max = len(new_format[key])
                    max_inverter = key
                else:
                    max=max
            except:
                continue
        print "max", max_inverter
        for j in range(max):
            try:
                r = {}
                result = {}
                for inv in new_format.keys():
                    try:
                        r[inv] = new_format[inv][j]['energy']
                    except:
                        continue
                result['energy'] = r
                result['timestamp'] = new_format[max_inverter][j]['timestamp']
                final_result.append(result)
            except Exception as exception:
                print str(exception)
                continue
        return final_result
    except Exception as exception:
        print str(exception)
        return []

def get_generation_report(starttime, endtime, plant, aggregator):
    try:
        assert(aggregator == "DAY")
        if plant.slug == "rbl" or plant.slug == "ranetrw" or plant.slug == "ranergy":
            return get_generation_report_ranergy(starttime, endtime, plant, aggregator)

        inverters_data = get_minutes_aggregated_energy(starttime, endtime, plant, aggregator, 1, split=True, meter_energy=False)
        print inverters_data
        inverters_data = convert_new_energy_data_format_to_old_format(inverters_data)
        solar_groups = plant.solar_groups.all()
        inverters = IndependentInverter.objects.filter(plant=plant)
        groups_energy = {}
        if len(solar_groups)>0:
            for inverter in inverters:
                inverter_groups = inverter.solar_groups.all()
                for group in inverter_groups:
                    try:
                        groups_energy[group.name] = groups_energy[group.name]+ float(inverters_data[0]['energy'][inverter.name])
                    except:
                        try:
                            groups_energy[group.name] = float(inverters_data[0]['energy'][inverter.name])
                        except:
                            groups_energy[group.name] = 0.0
        transposed_values = {}
        transposed_ts = {}
        for ts in inverters_data:
            timestamp = ts['timestamp']
            for inverter in ts['energy'].keys():
                if inverter == 'energy':
                    continue
                try:
                    transposed_values[inverter].append(float(ts['energy'][inverter]))
                    transposed_ts[inverter].append(timestamp)
                except:
                    transposed_values[inverter] = [float(ts['energy'][inverter])]
                    transposed_ts[inverter] = [timestamp]
            # add pr and energy meter
            try:
                if len(plant.energy_meters.all()) > 0:
                    meter_data = get_minutes_aggregated_energy(pd.to_datetime(timestamp).tz_convert('Asia/Kolkata'),
                                                                pd.to_datetime(timestamp).tz_convert('Asia/Kolkata') + timedelta(hours=24),
                                                                plant,
                                                                aggregator, 1, split=True, meter_energy=True)
                    logger.debug(meter_data)
                    for key in meter_data.keys():
                        try:
                            # assert there's max one day data
                            assert(len(meter_data[key]) <= 1)
                        except :
                            continue

                        for entry in meter_data[key]:
                            try:
                                transposed_values[key].append(float(entry['energy']))
                                transposed_ts[key].append(entry['timestamp'])
                            except:
                                transposed_values[key] = [float(entry['energy'])]
                                transposed_ts[key] = [entry['timestamp']]

                elif hasattr(plant, 'metadata') and plant.metadata.fields.get(name="ENERGY_METER_DATA").isActive:
                    energy_meter_data = get_energy_meter_values(pd.to_datetime(timestamp).tz_convert('Asia/Kolkata'),
                                                                pd.to_datetime(timestamp).tz_convert('Asia/Kolkata') + timedelta(hours=24),
                                                                plant,
                                                                aggregator)[0]['energy']
                    energy_meter_data = round(energy_meter_data, 2)
                    try:
                        transposed_values['Energy Meter'].append(float(energy_meter_data))
                        transposed_ts['Energy Meter'].append(timestamp)
                    except:
                        transposed_values['Energy Meter'] = [float(energy_meter_data)]
                        transposed_ts['Energy Meter'] = [timestamp]
            except:
                pass

            # check for insolation data
            try:
                insolation_values = KWHPerMeterSquare.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                     ts__gte=pd.to_datetime(timestamp).tz_convert('Asia/Kolkata'),
                                                                     ts__lt=pd.to_datetime(timestamp).tz_convert('Asia/Kolkata') + timedelta(hours=24))
                if len(insolation_values) > 0:
                    logger.debug(insolation_values[0].value)
                    try:
                        transposed_values['Insolation (kWh/m2)'].append(float(insolation_values[0].value))
                        transposed_ts['Insolation (kWh/m2)'].append(timestamp)
                    except:
                        transposed_values['Insolation (kWh/m2)'] = [float(insolation_values[0].value)]
                        transposed_ts['Insolation (kWh/m2)'] = [timestamp]
            except:
                pass

            try:
                if hasattr(plant, 'metadata') and plant.metadata.fields.get(name="IRRADIATION").isActive:
                    daily_performance_ratio = PerformanceRatioTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                   identifier=plant.metadata.sourceKey,
                                                                                   ts=pd.to_datetime(timestamp).tz_convert('Asia/Kolkata').replace(hour=0,minute=0,second=0,microsecond=0)
                                                                                   ).limit(1)
                    if len(daily_performance_ratio) > 0 and daily_performance_ratio[0].performance_ratio is not None:
                        performance_ratio = "{0:.2f}".format(daily_performance_ratio[0].performance_ratio)
                        try:
                            transposed_values['PR'].append(float(performance_ratio))
                            transposed_ts['PR'].append(timestamp)
                        except:
                            transposed_values['PR'] = [float(performance_ratio)]
                            transposed_ts['PR'] = [timestamp]

                    else:
                        pass
            except:
                pass
        try:
            if len(groups_energy)>0:
                for group in solar_groups:
                    try:
                        transposed_values["group_" + str(group.name)] = [float(groups_energy[group.name])]
                        transposed_ts["group_" + str(group.name)] = [timestamp]
                    except:
                        transposed_values["group_" + str(group.name)] = [0.0]
                        transposed_ts["group_" + str(group.name)] = [timestamp]
        except Exception as exception:
            pass
        df_list = []
        order = []
        for inverter in reversed(sorted(transposed_values.keys(), key=natural_key)):
            if inverter not in ['Energy Meter', 'PR']:
                order.append(inverter)
            df_list.append(pd.DataFrame({inverter: transposed_values[inverter],
                                        'timestamp': pd.to_datetime(transposed_ts[inverter]).tz_convert('Asia/Kolkata').date}))

        if hasattr(plant, 'metadata') and plant.metadata.fields.get(name="IRRADIATION").isActive:
            order.append('PR')
        if hasattr(plant, 'metadata') and plant.metadata.fields.get(name="ENERGY_METER_DATA").isActive:
            order.append('Energy Meter')
        order.append('timestamp')
        if len(df_list) >= 2:
            results = df_list[0]
            for i in range(1, len(df_list)):
                results = results.merge(df_list[i], how='outer', on='timestamp')
                updated_results = fill_results(results)
                results = updated_results
        else:
            results = df_list[0]
            sorted_results = results.sort(['timestamp'])
            results = sorted_results
        return results.to_csv(date_format="%Y-%m-%d",
                              index=False,
                              columns=reversed(order))
    except Exception as exception:
        logger.debug(str(exception))
        return []


def get_sections_and_groups(plant):
    try:
        sections = []
        groups = []
        for section in plant.solar_section.all():
            section_groups = []
            for solar_group in section.solar_groups.all():
                inverters = []
                for inverter in solar_group.get_independent_inverters():
                    inverters.append(str(inverter.name))
                groups.append({str(solar_group.name): inverters})
                section_groups.append(str(solar_group.name))
            sections.append({str(section.name): section_groups})

        return sections, groups
    except:
        return [], []

def get_new_generation_report(starttime, endtime, plant):
    try:
        df_result = pd.DataFrame()
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by("ts")
        timestamp = []
        generation = []
        pr = []
        cuf = []
        specific_yield = []
        average_irradiation = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            generation.append(round(value.generation, 3) if value.generation is not None else value.generation)
            pr.append(round(value.performance_ratio*100,3) if value.performance_ratio is not None else value.performance_ratio)
            cuf.append(round(value.cuf*100,3) if value.cuf is not None else value.cuf)
            specific_yield.append(round(value.specific_yield,3) if value.specific_yield is not None else value.specific_yield)
            average_irradiation.append(round(value.average_irradiation,3) if value.average_irradiation is not None else value.average_irradiation)

        df_result['timestamp'] = timestamp
        df_result['Total Generation (kWh)'] = generation
        df_result['PR (%)'] = pr
        df_result['CUF (%)'] = cuf
        df_result['Specific Yield'] = specific_yield
        df_result['Insolation (kWh/m^2)'] = average_irradiation
        df_result.sort('timestamp')

        df_inverters = pd.DataFrame()
        if len(plant.solar_groups.all())>0:
            groups = plant.solar_groups.all()
            group_names = []
            for group in groups:
                group_names.append(str(group.name))
                groups_name = sorted_nicely(group_names)
            groups = []
            for name in groups_name:
                group = SolarGroup.objects.get(plant=plant, name=name)
                groups.append(group)
            for group in groups:
                df_group = pd.DataFrame()
                inverters = group.groupIndependentInverters.all()
                if len(inverters)>0:
                    inverters_name = []
                    for inverter in inverters:
                        inverters_name.append(str(inverter.name))
                    inverters_name = sorted_nicely(inverters_name)
                    inverters = []
                    for name in inverters_name:
                        try:
                            inverter = IndependentInverter.objects.get(plant=plant, name=name)
                            inverters.append(inverter)
                        except:
                            print str(name)
                            continue
                    for inverter in inverters:
                        try:
                            inverter_values = []
                            inverter_timestamp = []
                            df_inverter = pd.DataFrame()
                            inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                            count_time_period=86400,
                                                                                            identifier=str(inverter.sourceKey),
                                                                                            ts__gte=starttime,
                                                                                            ts__lte=endtime).order_by("ts")
                            for value in inverter_generations:
                                inverter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                                inverter_timestamp.append(pd.to_datetime(value.ts))
                            df_inverter[str(inverter.name) + ' (kWh)'] = inverter_values
                            df_inverter['timestamp'] = inverter_timestamp
                            #print df_inverter
                            try:
                                if df_group.empty:
                                    df_group = df_inverter
                                else:
                                    df_group = df_group.merge(df_inverter.drop_duplicates('timestamp'), on='timestamp', how='outer')
                            except Exception as exception:
                                print str(exception)
                        except Exception as exception:
                            print str(exception)
                            continue
                    try:
                        if df_inverters.empty:
                            df_inverters = df_group
                        else:
                            df_inverters = df_inverters.merge(df_group.drop_duplicates('timestamp'), on='timestamp', how='outer', suffixes=('_',''))
                            for column in df_inverters.columns:
                                try:
                                    df_inverters.drop(str(column)+'_', axis=1, inplace=True)
                                except:
                                    continue
                    except Exception as exception:
                        print str(exception)

                    df_group_sum = pd.DataFrame()
                    df_group_sum['timestamp'] = df_group['timestamp']
                    df_group_sum[str(group.name)+' (kWh)'] = df_group.sum(axis=1)

                    try:
                        if df_result.empty:
                            df_result = df_group_sum
                        else:
                            df_result = df_result.merge(df_group_sum.drop_duplicates('timestamp'), on='timestamp', how='outer')
                    except Exception as exception:
                        print str(exception)
        else:
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
                try:
                    inverter_values = []
                    inverter_timestamp = []
                    df_inverter = pd.DataFrame()
                    inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                    count_time_period=86400,
                                                                                    identifier=str(inverter.sourceKey),
                                                                                    ts__gte=starttime,
                                                                                    ts__lte=endtime).order_by("ts")
                    for value in inverter_generations:
                        inverter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                        inverter_timestamp.append(pd.to_datetime(value.ts))
                    df_inverter[str(inverter.name) + ' (kWh)'] = inverter_values
                    df_inverter['timestamp'] = inverter_timestamp

                    if df_inverters.empty:
                        df_inverters = df_inverter
                    else:
                        df_inverters = df_inverters.merge(df_inverter.drop_duplicates('timestamp'), on='timestamp', how='outer', suffixes=('_',''))
                        for column in df_inverters.columns:
                            try:
                                df_inverters.drop(str(column)+'_', axis=1, inplace=True)
                            except:
                                continue
                except:
                    continue
        df_meters = pd.DataFrame()
        if len(plant.energy_meters.all())>0:
            meters = plant.energy_meters.all()
            for meter in meters:
                meter_values = []
                meter_timestamp = []
                df_meter = pd.DataFrame()
                meter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                             count_time_period=86400,
                                                                             identifier=str(meter.sourceKey),
                                                                             ts__gte=starttime,
                                                                             ts__lte=endtime).order_by("ts")
                for value in meter_generations:
                    meter_values.append(round(float(value.generation),3) if value.generation is not None else value.generation)
                    meter_timestamp.append(pd.to_datetime(value.ts))
                df_meter[str(meter.name) + ' (kWh)'] = meter_values
                df_meter['timestamp'] = meter_timestamp

                if df_meters.empty:
                    df_meters = df_meter
                else:
                    df_meters = df_meters.merge(df_meter.drop_duplicates('timestamp'), on='timestamp', how='outer')
                    for column in df_meters.columns:
                        try:
                            df_meters.drop(str(column)+'_', axis=1, inplace=True)
                        except:
                            continue


        if not df_meters.empty:
            df_result = df_result.merge(df_meters.drop_duplicates('timestamp'), on='timestamp', how='outer')
        if not df_inverters.empty:
            df_result = df_result.merge(df_inverters.drop_duplicates('timestamp'), on='timestamp', how='outer')
        if not df_result.empty:
            df_result['timestamp'] = df_result['timestamp'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())

        df_final = df_result.sort("timestamp").reset_index(drop=True)

        csv_data = df_final.to_csv(index=False)
        sections, groups = get_sections_and_groups(plant)
        return {
            'csvdata': csv_data,
            'sections': sections,
            'groups': groups
        }

    except Exception as exception:
        print str(exception)
        return []


def get_inverters_split(starttime, endtime, plant, aggregator):
    df = get_plant_power(starttime, endtime, plant, True, True, split=True, meter_energy=False)
    sum_energy = False

    if df.shape[0] == 0:
        df = get_plant_power(starttime, endtime, plant, True, split=True, meter_energy=False)
        accepted_values = get_energy_from_power(df)
        df = accepted_values
        sum_energy = True
    else:
        df = df.rename(columns={'sum': 'energy'})

    if aggregator == "HOUR":
        # a data point at 10:00 should not be considered in hour 10:00, but in 09
        grouped = df.groupby(df['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert('Asia/Kolkata').replace(
            minute=0, second=0, microsecond=0)))
    elif aggregator == "DAY" or aggregator == "MONTH":
        grouped = df.groupby(df['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert('Asia/Kolkata').date()))
    else:
        return []

    data = []
    if aggregator == "DAY":
        for name, group in grouped:
            if sum_energy:
                logger.debug(group.sum())
                energy = group.sum().to_csv(date_format="%Y-%m-%d %H:%M:%S%Z",
                                  index=False)
            else:
                logger.debug(group.tail(1))
                # filtering of delta noisy data
                if float(group.tail(1)["energy"]) < 1000000:
                    energy = group.tail(1).to_csv(date_format="%Y-%m-%d %H:%M:%S%Z",
                                  index=False)
                else:
                    energy = group.tail(2).head(1).to_csv(date_format="%Y-%m-%d %H:%M:%S%Z",
                                  index=False)
            data.append({'timestamp': pd.to_datetime(name).tz_localize('Asia/Kolkata').tz_convert('UTC'),
                         'energy': energy})
    return data

def get_energy_meter_values(starttime, endtime, plant, aggregator):
    if hasattr(plant, 'metadata') and plant.metadata.fields.get(name="ENERGY_METER_DATA").isActive:
        energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                              stream_name='ENERGY_METER_DATA',
                                                              timestamp_in_data__gte=starttime,
                                                              timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
        try:
            df = pd.DataFrame(energy_data[:], columns=['energy','timestamp'])
        except:
            return []
        sorted_results = df.sort(['timestamp'])
        df = sorted_results

        # group the data as per the aggregator
        if aggregator == "DAY" or aggregator == "MONTH":
            grouped = df.groupby(df['timestamp'].map(lambda x: x.tz_localize('UTC').tz_convert('Asia/Kolkata').date()))
        else:
            return []
        data = []
        if aggregator == "DAY":
            for name, group in grouped:
                energy = float(group["energy"][group.last_valid_index()]) - float(group["energy"][group.first_valid_index()])
                if 0 <= energy < 10000000:
                    data.append({'timestamp': pd.to_datetime(name).tz_localize('Asia/Kolkata').tz_convert('UTC'),
                             'energy': energy})
            return data
        elif aggregator == "MONTH":
            for name, group in grouped:
                energy = float(group["energy"][group.last_valid_index()]) - float(group["energy"][group.first_valid_index()])
                if 0 <= energy < 10000000:
                    data.append([pd.to_datetime(name), energy])

            # from day energy to monthly
            try:
                monthly_data = pd.DataFrame(data, columns=['timestamp','energy'])
            except:
                return []
            monthly_grouped = monthly_data.groupby(monthly_data['timestamp'].map(lambda x: x.date().replace(day=1)))
            data = []
            for name, group in monthly_grouped:
                data.append({'timestamp': pd.to_datetime(name).tz_localize('Asia/Kolkata').tz_convert('UTC'),
                             'energy' : group.sum()["energy"]})
            return data


def calculate_pr(starttime, endtime, plant):
    try:
        if hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed:
            energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                  stream_name='ENERGY_METER_DATA',
                                                                  timestamp_in_data__gte=starttime,
                                                                  timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            try:
                df = pd.DataFrame(energy_data[:], columns=['energy','timestamp'])
            except:
                return 0.00
            sorted_results = df.sort(['timestamp'])
            df = sorted_results

        elif hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy:
            energy_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                  stream_name=PLANT_ENERGY_STREAM,
                                                                  timestamp_in_data__gte=starttime,
                                                                  timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            try:
                df = pd.DataFrame(energy_data[:], columns=['energy','timestamp'])
            except:
                return 0.00
            sorted_results = df.sort(['timestamp'])
            df = sorted_results

        else:
            df = get_plant_power(starttime, endtime, plant, True, True)
            if df.shape[0] > 0:
                df = df.rename(columns={'sum': 'energy'})
                sorted_results = df.sort(['timestamp'])
                df = sorted_results
            else:
                return 0.0

        # check if there's data!

        df["energy"] = df["energy"].astype(float)
        # eliminating noisy data for sterling

        # if plant.capacity < 2000:
        #     df = df[df["energy"] < 1000000]

        # this call would be slow, look if there's a native pandas function for this using cython
        df['timestamp'] = df['timestamp'].apply( lambda x: x.replace(second=0, microsecond=0))

        # get irradiation values
        if hasattr(plant, 'metadata'):
            irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                       stream_name='IRRADIATION',
                                                                       timestamp_in_data__gte=starttime,
                                                                       timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            if len(irradiation_data) == 0:
                irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                           stream_name='EXTERNAL_IRRADIATION',
                                                                           timestamp_in_data__gte=starttime,
                                                                           timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            if plant.metadata.plantmetasource.binning_interval:
                idf = pd.DataFrame()
                irradiace = []
                timestamps = []
                for data_point in irradiation_data:
                    timestamps.append(data_point[1].replace(minute=(data_point[1].minute - data_point[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                    irradiace.append(float(data_point[0]))
                idf['irradiance'] = irradiace
                idf['timestamp'] = timestamps
            else:
                try:
                    idf = pd.DataFrame(irradiation_data[:], columns=['irradiance','timestamp'])
                    idf["irradiance"] = idf["irradiance"].astype(float)
                    # this call would be slow, look if there's a native pandas function for this using cython
                    idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                except:
                    return 0.00

        # drop the NA values
        df_energy = pd.DataFrame()
        df_energy['timestamp'] = df['timestamp']
        df_energy['energy'] = df['energy']
        df = df.dropna()
        df_energy = df_energy.dropna()
        idf = idf.dropna()

        if plant.metadata.plantmetasource.energy_from_power:
            pr_values = df_energy.merge(idf, how='inner', on='timestamp')
            pr_values['average_irradiance'] = (pr_values["irradiance"] + pr_values["irradiance"].shift(+1))/2.0
            pr_values['delta'] = pr_values.diff()['timestamp']
            delta = pd.Timedelta(seconds=20*60)
            pr_values = pr_values[(pr_values['delta']) < delta]
            pr_values = pr_values[(pr_values['energy']) > 0.0]
            pr_values = pr_values[pr_values['energy'] < 1.5*(plant.capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))]
            pr_values['irradiance_energy'] = pr_values['average_irradiance']*(plant.metadata.PV_panel_area*plant.metadata.PV_panel_efficiency)*(pr_values['delta']/np.timedelta64(1, 'h'))
            if float(pr_values["irradiance_energy"].sum())==0.0:
                pr = 0.0
            else:
                pr = pr_values["energy"].sum()/pr_values["irradiance_energy"].sum()
            return pr
        else:
            #pr_values = df.merge(idf, how='inner', on='timestamp')
            pr_values = df_energy.merge(idf, how='inner', on='timestamp')
            pr_values['average_irradiance'] = (pr_values["irradiance"] + pr_values["irradiance"].shift(+1))/2.0
            pr_values['energy_diff'] = pr_values["energy"] - pr_values["energy"].shift(+1)
            pr_values['delta'] = pr_values.diff()['timestamp']
            # if plant.slug == 'hmchalol':
            #     delta = pd.Timedelta(seconds=35*60)
            # else:
            #     delta = pd.Timedelta(seconds=20*60)
            delta = pd.Timedelta(seconds=35 * 60)
            pr_values = pr_values[(pr_values['delta']) < delta]
            pr_values = pr_values[(pr_values['energy_diff']) >= 0.0]
            pr_values = pr_values[pr_values['energy_diff'] < 1.5*(plant.capacity/60.0)*(pr_values['delta']/np.timedelta64(1, 'm'))]
            pr_values['irradiance_energy'] = pr_values['average_irradiance']*(plant.metadata.PV_panel_area*plant.metadata.PV_panel_efficiency)*(pr_values['delta']/np.timedelta64(1, 'h'))
            # try:
            #     pr = pr_values["energy_diff"].sum()/pr_values["irradiance_energy"].sum()
            # except ZeroDivisionError:
            #     return 0.0
            if float(pr_values["irradiance_energy"].sum())==0.0:
                pr = 0.0
            else:
                pr = pr_values["energy_diff"].sum()/pr_values["irradiance_energy"].sum()
            return pr
    except:
        return 0.0

from solarrms.gmr_expected_module_temperature import GMR_EXPECTED_MODULE_TEMPERATURE
# starttime and endtime shour be passed in IST, as the expected module temperature is stored as IST
def calculate_pr_gmr(starttime, endtime, plant):
    try:
        plant_capacity = float(plant.capacity)
        actual_energy_values = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, False, True)
        try:
            actual_energy = actual_energy_values[len(actual_energy_values)-1]['energy']
        except:
            actual_energy = 0.0
        insolation = get_kwh_per_meter_square_value(starttime, endtime, plant)
        module_temperature = get_aggregated_module_temperature_values(starttime, endtime, plant)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        month = starttime.month
        hour = starttime.hour
        print month
        print hour
        expected_module_temerature = GMR_EXPECTED_MODULE_TEMPERATURE[month][hour]
        print expected_module_temerature
        print module_temperature
        temperature_coefficient = 0.41
        multiplication_factor = (1-((temperature_coefficient)*(expected_module_temerature-module_temperature))/100.0)
        print multiplication_factor
        print actual_energy
        print insolation
        print multiplication_factor
        denominator = plant_capacity*insolation*multiplication_factor
        try:
            if float(denominator)==0.0:
                return 0.0
            else:
                pr = actual_energy/(plant_capacity*insolation*multiplication_factor)
                return pr
        except:
            return 0.0
    except Exception as exception:
        print str(exception)
        return 0.0

# from solarrms.models import SolarMetrics
# from solarrms.cron_compute_solar_metrics import write_instantanous_solar_metrics, write_hourly_pr_values,\
#     write_hourly_cuf_values, write_hourly_specific_yield_values
# def calculate_metrics_for_missing_data_points(starttime, endtime, plant, aggregator, metric_type, inverters=None):
#     try:
#         starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
#         duration_minutes = (endtime - starttime).total_seconds()/60
#         try:
#             solar_metric = SolarMetrics.objects.get(plant=plant,solar_group=None)
#         except:
#             return 0
#         if metric_type == 'PR':
#             if aggregator == '15_MINUTES':
#                 window_slots = duration_minutes/15
#                 while(window_slots)>0:
#                     window_starttime = starttime - timedelta(seconds=30)
#                     window_endtime = starttime + timedelta(minutes=15, seconds=59)
#                     window_pr = calculate_pr(window_starttime, window_endtime, plant)
#                     print window_starttime, window_endtime, window_pr
#                     write_instantanous_solar_metrics(solar_metric.sourceKey,"PR", timezone.now(), window_pr, window_endtime)
#                     starttime = starttime + timedelta(minutes=15)
#                     window_slots -= 1
#             elif aggregator == 'HOUR':
#                 while(window_slots)>0:
#                     window_slots = duration_minutes/60
#                     window_starttime = starttime - timedelta(seconds=30)
#                     window_endtime = starttime + timedelta(minutes=60, seconds=59)
#                     window_pr = calculate_pr(window_starttime, window_endtime, plant)
#                     write_hourly_pr_values(plant.metadata.plantmetasource, window_pr, starttime)
#                     starttime = starttime + timedelta(minutes=60)
#                     window_slots -= 1
#             else:
#                 pass
#         elif metric_type == 'CUF':
#             if aggregator == '15_MINUTES':
#                 window_slots = duration_minutes/15
#                 while(window_slots)>0:
#                     window_starttime = starttime - timedelta(seconds=30)
#                     window_endtime = starttime + timedelta(minutes=15, seconds=59)
#                     window_cuf = calculate_CUF(window_starttime, window_endtime, plant)
#                     print window_starttime, window_endtime, window_cuf
#                     write_instantanous_solar_metrics(solar_metric.sourceKey,"CUF", timezone.now(), window_cuf, window_endtime)
#                     starttime = starttime + timedelta(minutes=15)
#                     window_slots -= 1
#             elif aggregator == 'HOUR':
#                 while(window_slots)>0:
#                     window_slots = duration_minutes/60
#                     window_starttime = starttime - timedelta(seconds=30)
#                     window_endtime = starttime + timedelta(minutes=60, seconds=59)
#                     window_cuf = calculate_pr(window_starttime, window_endtime, plant)
#                     write_hourly_cuf_values(plant.metadata.plantmetasource, window_cuf, starttime)
#                     starttime = starttime + timedelta(minutes=60)
#                     window_slots -= 1
#             else:
#                 pass
#         elif metric_type == 'SPECIFIC_YIELD':
#             if aggregator == '15_MINUTES':
#                 window_slots = duration_minutes/15
#                 while(window_slots)>0:
#                     window_starttime = starttime - timedelta(seconds=30)
#                     window_endtime = starttime + timedelta(minutes=15, seconds=59)
#                     window_sy = calculate_specific_yield(window_starttime, window_endtime, plant)
#                     print window_starttime, window_endtime, window_sy
#                     write_instantanous_solar_metrics(solar_metric.sourceKey,"SPECIFIC_YIELD", timezone.now(), window_sy, window_endtime)
#                     starttime = starttime + timedelta(minutes=15)
#                     window_slots -= 1
#             elif aggregator == 'HOUR':
#                 while(window_slots)>0:
#                     window_slots = duration_minutes/60
#                     window_starttime = starttime - timedelta(seconds=30)
#                     window_endtime = starttime + timedelta(minutes=60, seconds=59)
#                     window_sy = calculate_specific_yield(window_starttime, window_endtime, plant)
#                     write_hourly_specific_yield_values(plant.metadata.plantmetasource, window_sy, starttime)
#                     starttime = starttime + timedelta(minutes=60)
#                     window_slots -= 1
#             else:
#                 pass
#         else:
#             pass
#     except Exception as exception:
#         print str(exception)


def calculate_CUF(starttime, endtime, plant):
    actual_energy = 0.0
    CUF = 0.0
    if plant.metadata.energy_meter_installed:
        energy_values = get_energy_meter_values(starttime,endtime,plant,'MONTH')
    else:
        energy_values = get_minutes_aggregated_energy(starttime,endtime,plant,'MONTH',1)

    if plant.slug in ["nizampalace", "ezcc", "gsi", "dgcis"]:
        plant_capacity = plant.capacity
    else:
        try:
            plant_capacity = plant.ac_capacity if plant.ac_capacity else plant.capacity
        except:
            plant_capacity = plant.capacity

    #plant_capacity = plant.capacity
    if energy_values and len(energy_values)>0:
        for value in energy_values:
            actual_energy += float(value['energy'])
        #delta = endtime - starttime
        #delta_hours = delta.total_seconds()/3600
        delta_hours=24
        #if delta_hours > 0:
        CUF = actual_energy/(delta_hours * plant_capacity)
    return CUF


def calculate_specific_yield(starttime, endtime, plant):
    actual_energy = 0.0
    specific_yield = 0.0
    if plant.metadata.energy_meter_installed:
        energy_values = get_energy_meter_values(starttime,endtime,plant,'MONTH')
    else:
        energy_values = get_minutes_aggregated_energy(starttime,endtime,plant,'MONTH',1)

    if energy_values and len(energy_values)>0:
        for value in energy_values:
            actual_energy += float(value['energy'])
        specific_yield = float(actual_energy)/float(plant.capacity)
    return specific_yield

def calculate_total_plant_generation(plant):
    try:
        total_energy = 0.0
        if hasattr(plant, 'metadata') and plant.metadata.energy_meter_installed:
            value = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                            stream_name='ENERGY_METER_DATA').limit(1).values_list('stream_value')
            total_energy += float(value[0][0])

        elif hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy:
            value = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                            stream_name='TOTAL_PLANT_ENERGY').limit(1).values_list('stream_value')
            total_energy += float(value[0][0])
        elif len(plant.energy_meters.filter(isActive=True, energy_calculation=True))>0:
            meters = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)
            try:
                stream = TOTAL_ENERGY_CALCULATION_STREAMS[str(plant.slug)]
            except:
                try:
                    stream = ENERGY_CALCULATION_STREAMS[str(plant.slug)]
                except:
                    stream = 'Wh_RECEIVED'
            print stream

            energy_unit = False
            try:
                unit = ENERGY_METER_STREAM_UNITS[str(plant.slug)]
                unit_factor = ENERGY_METER_STREAM_UNIT_FACTOR[unit]
            except:
                energy_unit = True

            for meter in meters:
                value = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                stream_name=stream).values_list('stream_value').limit(1)
                if len(value)>0:
                    if energy_unit:
                        total_energy += float(value[0][0])
                    else:
                        total_energy += float(value[0][0])*unit_factor
        else:
            inverters = IndependentInverter.objects.filter(plant=plant)
            if plant.metadata.plantmetasource.inverters_sending_total_generation:
                for inverter in inverters:
                    value = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name='TOTAL_YIELD').values_list('stream_value').limit(1)
                    if len(value)>0:
                        total_energy += float(value[0][0])
        return total_energy
    except Exception as exception:
        logger.debug(str(exception))
        return 0.0


def get_ajb_dc_energy_aggregated(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[9]]#, inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        aggregated_dc_energy_from_ajb = 0.0
        final_dc_energy_values_from_ajb = {}
        for inverter in inverters:
            df_list_voltage = []
            df_results_current = pd.DataFrame()
            ajbs = inverter.ajb_units.all()
            if ajbs:
                for ajb in ajbs:
                    try:
                        df_results_current_temp = pd.DataFrame()
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
                                        results_current_temp = results_current_temp.merge(df_list_current_temp[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                                        updated_results_current_temp = fill_results(results_current_temp)
                                        results_current_temp = updated_results_current_temp
                                    if df_results_current_temp.empty:
                                        df_results_current_temp = results_current_temp
                                    else:
                                        df_new = pd.merge(df_results_current_temp, results_current_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                                        df_results_current_temp = df_new
                        #print df_results_current_temp
                    except Exception as exception:
                        print("Error : " + str(exception))
                        continue

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
                            df_new = pd.merge(df_results_current, df_results_current_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
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
                    if not df_results_current.empty:
                        df_results_current.set_index('timestamp', inplace=True)
                    #print("current")
                    #print(df_results_current)
                    results_voltage = pd.DataFrame()
                    results_energy = pd.DataFrame()
                    energy_from_ajb = pd.DataFrame()
                    if len(df_list_voltage) > 0:
                        results_voltage = df_list_voltage[0]
                        for i in range(1, len(df_list_voltage)):
                            results_voltage = results_voltage.merge(df_list_voltage[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                            updated_results_voltage = fill_results(results_voltage)
                            results_voltage = updated_results_voltage
                        results_voltage.set_index('timestamp', inplace=True)
                        #print("voltage")
                        #print results_voltage
                    if not df_results_current.empty and not results_voltage.empty:
                        df_results_power = df_results_current.mul(results_voltage, axis=0)
                        df_results_power['timestamp'] = df_results_power.index
                        sorted_results = df_results_power.sort()
                        results = sorted_results
                        results = results.ffill(limit=1)
                        results[inverter.name] = results.sum(axis=1)

                        results_energy = pd.DataFrame()
                        results_energy['timestamp'] = results['timestamp']
                        results_energy['sum'] = results[inverter.name]
                        if not results_energy.empty:
                            results_energy = results_energy[results_energy['sum'] > 0]
                            results_energy = results_energy[results_energy['sum'] < plant.capacity]
                    if plant.gateway.all()[0].isVirtual:
                        energy_from_ajb = get_energy_from_power(results_energy, True)
                    elif plant.slug in PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA:
                        energy_from_ajb = get_energy_from_power_dominicus(results_energy)
                    else:
                        energy_from_ajb = get_energy_from_power(results_energy)
                    if not energy_from_ajb.empty:
                        sum = energy_from_ajb['energy'].sum()
                        if not energy_from_ajb.empty and not math.isnan(sum):
                            final_dc_energy_values_from_ajb[inverter.name] = sum
                            aggregated_dc_energy_from_ajb += sum
                except Exception as exception:
                    print(str(exception))
        final_dc_energy_values_from_ajb['aggregated_dc_energy_from_ajb'] = aggregated_dc_energy_from_ajb
        if aggregated_dc_energy_from_ajb == 0.0:
            return []
        return final_dc_energy_values_from_ajb
    except Exception as exception:
        print(str(exception))
        return []

def get_inverter_dc_energy_aggregated(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        aggregated_dc_energy_from_inverters = 0.0
        final_dc_energy_values_from_inverters = {}
        for inverter in inverters:
            df_list_power = []
            df_list_current = []
            df_list_voltage = []
            pd_power = pd.DataFrame()
            dc_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'DC_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            if dc_power_data:
                values_dc_power = []
                timestamp_dc_power = []
                for data_point in dc_power_data:
                    timestamp_dc_power.append(data_point[1].replace(second=0, microsecond=0))
                    values_dc_power.append(float(data_point[0]))
                df_list_power.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_dc_power),
                                                   inverter.name: values_dc_power}))
                if len(df_list_power)>0:
                    pd_power['sum'] = df_list_power[0][inverter.name]
                    pd_power['timestamp'] = df_list_power[0]['timestamp']
                    if not pd_power.empty:
                        pd_power = pd_power[pd_power['sum'] > 0]
                        pd_power = pd_power[pd_power['sum'] < plant.capacity]
                    if plant.gateway.all()[0].isVirtual:
                        energy_from_inverter = get_energy_from_power(pd_power, True)
                    elif plant.slug in PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA:
                        energy_from_inverter = get_energy_from_power_dominicus(pd_power)
                    else:
                        energy_from_inverter = get_energy_from_power(pd_power)
                    sum = energy_from_inverter['energy'].sum()
                    if not energy_from_inverter.empty and not math.isnan(sum):
                        final_dc_energy_values_from_inverters[inverter.name] = sum
                        aggregated_dc_energy_from_inverters += sum
            else:
                dc_current_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                          stream_name= 'DC_CURRENT',
                                                                          timestamp_in_data__gte = starttime,
                                                                          timestamp_in_data__lte = endtime
                                                                          ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                dc_voltage_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                          stream_name= 'DC_VOLTAGE',
                                                                          timestamp_in_data__gte = starttime,
                                                                          timestamp_in_data__lte = endtime
                                                                          ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                values_dc_current = []
                timestamp_dc_current = []
                for data_point in dc_current_data:
                    timestamp_dc_current.append(data_point[1].replace(second=0, microsecond=0))
                    values_dc_current.append(float(data_point[0])/1000)
                df_list_current.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_dc_current),
                                                     inverter.name: values_dc_current}))

                values_dc_voltage = []
                timestamp_dc_voltage = []
                for data_point in dc_voltage_data:
                    timestamp_dc_voltage.append(data_point[1].replace(second=0, microsecond=0))
                    values_dc_voltage.append(float(data_point[0]))
                df_list_voltage.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_dc_voltage),
                                                     inverter.name: values_dc_voltage}))
                if len(df_list_voltage) > 0:
                    results_voltage = df_list_voltage[0]
                    for i in range(1, len(df_list_voltage)):
                        results_voltage = results_voltage.merge(df_list_voltage[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                        updated_results_voltage = fill_results(results_voltage)
                        results_voltage = updated_results_voltage
                    results_voltage.set_index('timestamp', inplace=True)

                if len(df_list_current) > 0:
                    results_current = df_list_current[0]
                    for i in range(1, len(df_list_current)):
                        results_current = results_current.merge(df_list_current[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                        updated_results_current = fill_results(results_current)
                        results_current = updated_results_current
                    results_current.set_index('timestamp', inplace=True)

                if len(df_list_current)>0 and len(df_list_voltage)>0:
                    df_power = results_current.mul(results_voltage, axis=0)
                    pd_power['sum'] = df_power[inverter.name]
                    pd_power['timestamp'] = df_power.index
                    if not pd_power.empty:
                        pd_power = pd_power[pd_power['sum'] > 0]
                        pd_power = pd_power[pd_power['sum'] < plant.capacity]
                    if plant.gateway.all()[0].isVirtual:
                        energy_from_inverter = get_energy_from_power(pd_power, True)
                    elif plant.slug in PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA:
                        energy_from_inverter = get_energy_from_power_dominicus(pd_power)
                    else:
                        energy_from_inverter = get_energy_from_power(pd_power)
                    sum = energy_from_inverter['energy'].sum()
                    if not energy_from_inverter.empty and not math.isnan(sum):
                        final_dc_energy_values_from_inverters[inverter.name] = sum
                        aggregated_dc_energy_from_inverters += sum
        final_dc_energy_values_from_inverters['aggregated_dc_energy_from_inverters'] = aggregated_dc_energy_from_inverters
        if aggregated_dc_energy_from_inverters == 0.0:
            return []
        return final_dc_energy_values_from_inverters
    except Exception as exception:
        print("dc power exception: " + str(exception))
        return []

def get_dc_energy_loss_aggregated(starttime, endtime, plant):
    try:
        final_dc_energy_values_from_ajb = get_ajb_dc_energy_aggregated(starttime, endtime, plant)
        final_dc_energy_values_from_inverters = get_inverter_dc_energy_aggregated(starttime, endtime, plant)
        dc_energy_values = {}
        inverters = plant.independent_inverter_units.all()
        if type(final_dc_energy_values_from_ajb) is not list:
            for inverter in inverters:
                try:
                    dc_energy_values["dc_energy_ajb_"+inverter.name] = final_dc_energy_values_from_ajb[inverter.name]
                except:
                    dc_energy_values["dc_energy_ajb_"+inverter.name] = 'NA'
                    continue
            dc_energy_values['dc_energy_from_ajb'] = final_dc_energy_values_from_ajb['aggregated_dc_energy_from_ajb']
        else:
            for inverter in inverters:
                dc_energy_values["dc_energy_ajb_"+inverter.name] = 'NA'
            dc_energy_values['dc_energy_from_ajb'] = 'NA'
        if type(final_dc_energy_values_from_inverters) is not list:
            for inverter in inverters:
                try:
                        dc_energy_values["dc_energy_inverter_"+inverter.name] = final_dc_energy_values_from_inverters[inverter.name]
                except:
                    dc_energy_values["dc_energy_inverter_"+inverter.name] = 'NA'
                    continue
            dc_energy_values['dc_energy_from_inverters'] = final_dc_energy_values_from_inverters['aggregated_dc_energy_from_inverters']
        else:
            for inverter in inverters:
                dc_energy_values["dc_energy_inverter_"+inverter.name] = 'NA'
            dc_energy_values['dc_energy_from_inverters'] = 'NA'
        if type(final_dc_energy_values_from_ajb) is not list and type(final_dc_energy_values_from_inverters) is not list:
            dc_energy_values['dc_energy_loss'] = dc_energy_values['dc_energy_from_ajb'] - dc_energy_values['dc_energy_from_inverters']
        else:
            dc_energy_values['dc_energy_loss'] = 'NA'
        return dc_energy_values
    except Exception as exception:
        print(str(exception))
        return []

def get_inverter_ac_energy_aggregated(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        aggregated_ac_energy_from_inverters = 0.0
        final_ac_energy_values_from_inverters = {}
        for inverter in inverters:
            df_list_total_yield = []
            results_total_yield_temp = pd.DataFrame()
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
                results_total_yield_temp = results_total_yield_temp.diff().rename(columns={inverter.name : 'total_yield'})
                results_total_yield_temp = results_total_yield_temp[results_total_yield_temp['total_yield'] > 0]
                results_total_yield_temp = results_total_yield_temp[results_total_yield_temp['total_yield'] < plant.capacity]
                sum = results_total_yield_temp['total_yield'].sum()
                if not math.isnan(sum):
                    final_ac_energy_values_from_inverters[inverter.name] = sum
                    aggregated_ac_energy_from_inverters += sum
        final_ac_energy_values_from_inverters['aggregated_ac_energy_from_inverters'] = aggregated_ac_energy_from_inverters
        if aggregated_ac_energy_from_inverters == 0.0:
            return []
        return final_ac_energy_values_from_inverters
    except Exception as exception:
        print(str(exception))
        return []


def get_inverter_ac_energy_aggregated_from_ACTIVE_POWER(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0], inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        aggregated_ac_energy_from_inverters = 0.0
        final_ac_energy_values_from_inverters = {}
        for inverter in inverters:
            df_list_power = []
            pd_power = pd.DataFrame()
            ac_power_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                    stream_name= 'ACTIVE_POWER',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            if ac_power_data:
                values_ac_power = []
                timestamp_ac_power = []
                for data_point in ac_power_data:
                    timestamp_ac_power.append(data_point[1].replace(second=0, microsecond=0))
                    values_ac_power.append(float(data_point[0]))
                df_list_power.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_ac_power),
                                                   inverter.name: values_ac_power}))
                if len(df_list_power)>0:
                    pd_power['sum'] = df_list_power[0][inverter.name]
                    pd_power['timestamp'] = df_list_power[0]['timestamp']
                    if not pd_power.empty:
                        pd_power = pd_power[pd_power['sum'] > 0]
                        pd_power = pd_power[pd_power['sum'] < plant.capacity]
                    if plant.gateway.all()[0].isVirtual:
                        energy_from_inverter = get_energy_from_power(pd_power, True)
                    elif plant.slug in PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA:
                        energy_from_inverter = get_energy_from_power_dominicus(pd_power)
                    else:
                        energy_from_inverter = get_energy_from_power(pd_power)
                    sum = energy_from_inverter['energy'].sum()
                    if not energy_from_inverter.empty and not math.isnan(sum):
                        final_ac_energy_values_from_inverters[inverter.name] = sum
                        aggregated_ac_energy_from_inverters += sum

        final_ac_energy_values_from_inverters['aggregated_ac_energy_from_inverters_ap'] = aggregated_ac_energy_from_inverters
        if aggregated_ac_energy_from_inverters == 0.0:
            return []
        return final_ac_energy_values_from_inverters
    except Exception as exception:
        print("ac power exception: " + str(exception))
        return []

def get_conversion_loss_aggregated(starttime, endtime, plant):
    try:
        final_dc_energy_values_from_inverters = get_inverter_dc_energy_aggregated(starttime, endtime, plant)
        final_ac_energy_values_from_inverters = get_inverter_ac_energy_aggregated_from_ACTIVE_POWER(starttime, endtime, plant)
        conversion_values = {}
        inverters = plant.independent_inverter_units.all()
        if type(final_dc_energy_values_from_inverters) is not list:
            for inverter in inverters:
                try:
                    conversion_values["dc_energy_"+inverter.name] = final_dc_energy_values_from_inverters[inverter.name]
                except:
                    conversion_values["dc_energy_"+inverter.name] = 'NA'
                    continue
            conversion_values['dc_energy_from_inverters'] = final_dc_energy_values_from_inverters['aggregated_dc_energy_from_inverters']
        else:
            for inverter in inverters:
                conversion_values["dc_energy_"+inverter.name] = 'NA'
            conversion_values['dc_energy_from_inverters'] = 'NA'
        if type(final_ac_energy_values_from_inverters) is not list:
            for inverter in inverters:
                try:
                    conversion_values["ac_energy_ap_"+inverter.name] = final_ac_energy_values_from_inverters[inverter.name]
                except:
                    conversion_values["ac_energy_ap_"+inverter.name] = 'NA'
                    continue
            conversion_values['ac_energy_from_inverters_ap'] = final_ac_energy_values_from_inverters['aggregated_ac_energy_from_inverters_ap']
        else:
            for inverter in inverters:
                conversion_values["ac_energy_ap_"+inverter.name] = 'NA'
            conversion_values['ac_energy_from_inverters_ap'] = 'NA'
        if type(final_dc_energy_values_from_inverters) is not list and type(final_ac_energy_values_from_inverters) is not list:
            conversion_values['conversion_loss'] = conversion_values['dc_energy_from_inverters'] - conversion_values['ac_energy_from_inverters_ap']
        else:
            conversion_values['conversion_loss'] = 'NA'
        return conversion_values
    except Exception as exception:
        print(str(exception))
        return []

def get_ac_energy_from_meters(starttime, endtime, plant):
    try:
        meters = plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True)
        aggregated_ac_energy_from_meters = 0.0
        final_ac_energy_values_from_meters = {}
        energy_unit = False
        try:
            stream = ENERGY_CALCULATION_STREAMS[str(plant.slug)]
        except:
            stream = 'KWH'
        try:
            unit = ENERGY_METER_STREAM_UNITS[str(plant.slug)]
            unit_factor = ENERGY_METER_STREAM_UNIT_FACTOR[unit]
        except:
            energy_unit = True
        if len(meters)>0:
            for meter in meters:
                df_list_meter = []
                pd_meter = pd.DataFrame()
                meter_data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name= stream,
                                                                     timestamp_in_data__gte = starttime,
                                                                     timestamp_in_data__lte = endtime
                                                                     ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                print(len(meter_data))
                values_meter = []
                timestamp_meter = []
                for data_point in meter_data:
                    timestamp_meter.append(data_point[1].replace(second=0, microsecond=0))
                    if energy_unit:
                        values_meter.append(float(data_point[0]))
                    else:
                        values_meter.append(float(data_point[0])*unit_factor)
                df_list_meter.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_meter),
                                                   meter.name: values_meter}))

                if len(df_list_meter) > 0:
                    energy_meter = df_list_meter[0]
                    results_energy_meter = energy_meter.diff().rename(columns={meter.name : 'total_yield'})
                    results_energy_meter = results_energy_meter[results_energy_meter['total_yield'] > 0]
                    results_energy_meter = results_energy_meter[results_energy_meter['total_yield'] < plant.capacity]
                    sum = results_energy_meter['total_yield'].sum()
                    if not math.isnan(sum):
                        final_ac_energy_values_from_meters[meter.name] = sum
                        aggregated_ac_energy_from_meters += sum
        final_ac_energy_values_from_meters['aggregated_ac_energy_from_meters'] = aggregated_ac_energy_from_meters
        if aggregated_ac_energy_from_meters == 0.0:
            return []
        return final_ac_energy_values_from_meters
    except Exception as exception:
        print(str(exception))
        return []

def get_ac_energy_loss_aggregated(starttime, endtime, plant):
    try:
        final_ac_energy_values_from_inverters = get_inverter_ac_energy_aggregated(starttime, endtime, plant)
        final_ac_energy_values_from_meters = get_ac_energy_from_meters(starttime, endtime, plant)
        ac_energy_values = {}
        inverters = plant.independent_inverter_units.all()
        if type(final_ac_energy_values_from_inverters) is not list:
            for inverter in inverters:
                try:
                    ac_energy_values['ac_energy_'+inverter.name] = final_ac_energy_values_from_inverters[inverter.name]
                except:
                    ac_energy_values['ac_energy_'+inverter.name] = 'NA'
                    continue
            ac_energy_values['ac_energy_from_inverters'] = final_ac_energy_values_from_inverters['aggregated_ac_energy_from_inverters']
        else:
            for inverter in inverters:
                ac_energy_values['ac_energy_'+inverter.name] = 'NA'
            ac_energy_values['ac_energy_from_inverters'] = 'NA'
        if type(final_ac_energy_values_from_meters) is not list:
            ac_energy_values['ac_energy_from_meters'] = final_ac_energy_values_from_meters['aggregated_ac_energy_from_meters']
        else:
            ac_energy_values['ac_energy_from_meters'] = 'NA'
        if type(final_ac_energy_values_from_inverters) is not list and type(final_ac_energy_values_from_meters) is not list:
            ac_energy_values['ac_energy_loss'] = ac_energy_values['ac_energy_from_inverters'] - ac_energy_values['ac_energy_from_meters']
        else:
            ac_energy_values['ac_energy_loss'] = 'NA'
        return ac_energy_values
    except Exception as exception:
        print(str(exception))
        return []

def get_ac_energy_loss_from_plant_meta(starttime, endtime, plant):
    try:
        final_ac_energy_values_from_inverters = get_inverter_ac_energy_aggregated(starttime, endtime, plant)
        if hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_energy:
            final_ac_energy_values_from_meters = get_aggregated_energy(starttime, endtime, plant, 'DAY')
        elif hasattr(plant, 'metadata') and plant.metadata.fields.get(name="ENERGY_METER_DATA").isActive:
            final_ac_energy_values_from_meters = get_energy_meter_values(starttime, endtime, plant, 'DAY')
        else:
            final_ac_energy_values_from_meters = []
        ac_energy_values = {}
        inverters = plant.independent_inverter_units.all()
        if type(final_ac_energy_values_from_inverters) is not list:
            for inverter in inverters:
                try:
                    ac_energy_values['ac_energy_'+inverter.name] = final_ac_energy_values_from_inverters[inverter.name]
                except:
                    ac_energy_values['ac_energy_'+inverter.name] = 'NA'
                    continue
            ac_energy_values['ac_energy_from_inverters'] = final_ac_energy_values_from_inverters['aggregated_ac_energy_from_inverters']
        else:
            for inverter in inverters:
                ac_energy_values['ac_energy_'+inverter.name] = 'NA'
            ac_energy_values['ac_energy_from_inverters'] = 'NA'
        if final_ac_energy_values_from_meters:
            ac_energy_values['ac_energy_from_meters'] = float(str(final_ac_energy_values_from_meters[len(final_ac_energy_values_from_meters)-1]['energy']))
        else:
            ac_energy_values['ac_energy_from_meters'] = 'NA'
        if type(final_ac_energy_values_from_inverters) is not list and final_ac_energy_values_from_meters:
            ac_energy_values['ac_energy_loss'] = ac_energy_values['ac_energy_from_inverters'] - ac_energy_values['ac_energy_from_meters']
        else:
            ac_energy_values['ac_energy_loss'] = 'NA'
        return ac_energy_values
    except Exception as exception:
        print(str(exception))
        return []


def get_all_energy_losses_aggregated(starttime, endtime, plant):
    try:
        dc_loss = get_dc_energy_loss_aggregated(starttime, endtime, plant)
        conversion_loss = get_conversion_loss_aggregated(starttime, endtime, plant)
        if plant.energy_meters.all():
            ac_loss = get_ac_energy_loss_aggregated(starttime, endtime, plant)
        else:
            ac_loss = get_ac_energy_loss_from_plant_meta(starttime, endtime, plant)
        #final_energy_loss.append(dc_loss)
        #final_energy_loss.append(conversion_loss)
        #final_energy_loss.append(ac_loss)
        dc_loss.update(conversion_loss)
        dc_loss.update(ac_loss)
        final_energy_loss = dc_loss
        return final_energy_loss
    except Exception as exception:
        print(str(exception))
        return []

def get_irradiation_data(starttime, endtime, plant):
    try:
        plant_meta = plant.metadata.plantmetasource
        df_list_irradiation = []
        irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta.sourceKey,
                                                                    stream_name= 'IRRADIATION',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
        if len(irradiation_data)==0:
            irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant_meta.sourceKey,
                                                                    stream_name= 'EXTERNAL_IRRADIATION',
                                                                    timestamp_in_data__gte = starttime,
                                                                    timestamp_in_data__lte = endtime
                                                                    ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
        values_irradiation = []
        timestamp_irradiation = []
        # for data_point in irradiation_data:
        #     timestamp_irradiation.append(data_point[1].replace(second=0, microsecond=0))
        #     values_irradiation.append(float(data_point[0]))
        if plant.metadata.plantmetasource.binning_interval:
            for data_point in irradiation_data:
                timestamp_irradiation.append(data_point[1].replace(minute=(data_point[1].minute - data_point[1].minute%(int(plant.metadata.plantmetasource.binning_interval)/60)),second=0, microsecond=0))
                values_irradiation.append(float(data_point[0]))
        else:
            for data_point in irradiation_data:
                timestamp_irradiation.append(data_point[1].replace(second=0, microsecond=0))
                values_irradiation.append(float(data_point[0]))
        df_list_irradiation.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_irradiation),
                                                 'irradiation': values_irradiation}))
        df_results_irradiation = df_list_irradiation[0]
        return df_results_irradiation
    except Exception as exception:
        print(str(exception))
        return []

def get_modbus_read_errors(starttime, endtime, plant):
    try:
        df_results_modbus_error = pd.DataFrame()
        df_final_result = pd.DataFrame()
        inverters = plant.independent_inverter_units.all()
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

def get_network_down_time_from_heartbeat(starttime, endtime, plant):
    try:
        df_final_result = pd.DataFrame()
        gateway_sources = plant.gateway.all()
        missing_time = []
        if len(gateway_sources)>0:
            source = gateway_sources[0]
            gateway_data = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                                  stream_name= 'HEARTBEAT',
                                                                  timestamp_in_data__gte = starttime,
                                                                  timestamp_in_data__lte = endtime
                                                                  ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
            values_heartbeat = []
            timestamp_heartbeat = []
            for data_point in gateway_data:
                timestamp_heartbeat.append(data_point[1].replace(second=0, microsecond=0))
                values_heartbeat.append(float(data_point[0]))
            if update_tz(starttime,'UTC') not in timestamp_heartbeat:
                timestamp_heartbeat.append(update_tz(starttime,'UTC'))
            if update_tz(endtime,'UTC') not in timestamp_heartbeat:
                timestamp_heartbeat.append(update_tz(endtime,'UTC'))
            missing_length = len(timestamp_heartbeat) - len(values_heartbeat)
            for i in range(missing_length):
                values_heartbeat.append(1.0)
            df_final_result['timestamp'] = timestamp_heartbeat
            df_final_result['heartbeat'] = values_heartbeat
            df_final_result = df_final_result.sort(['timestamp'])
            df_final_result = df_final_result.reset_index(drop=True)
            df_final_result['ts'] = df_final_result['timestamp'].diff()/np.timedelta64(1, 'm')
            if plant.gateway.all()[0].isVirtual:
                df_down_time = df_final_result[df_final_result['ts']>20]
            else:
                df_down_time = df_final_result[df_final_result['ts']>2]
            down_index = df_down_time.index.tolist()
            print df_final_result
            print down_index
            for index in down_index:
                try:
                    network_down_time = {}
                    network_down_time['network_down'] = df_final_result.loc[index-1]['timestamp']
                    network_down_time['network_up'] = df_down_time.loc[index]['timestamp']
                    missing_time.append(network_down_time)
                except Exception as exception:
                    print str(exception)
                    continue
        #return df_final_result
        return missing_time
    except Exception as exception:
        print(str(exception))
        return []

def get_inverter_errors(starttime, endtime, plant):
    try:
        df_results_inverter_errors = pd.DataFrame()
        df_final_result = pd.DataFrame()
        inverters = plant.independent_inverter_units.all()
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

def get_power_irradiation(starttime, endtime, plant, error=False):
    try:
        if str(plant.slug) in AGGREGATED_POWER_PLANT_SLUGS:
            power_values_df = get_plant_power(starttime, endtime, plant, True, False, True, live=False, aggregated_power=True)
            if power_values_df.empty:
                power_values_df = get_plant_power(starttime, endtime, plant, True, False, True, live=False, aggregated_power=False)
        else:
            power_values_df = get_plant_power(starttime, endtime, plant, True, False, True, live=True)
        irradiation_values = get_irradiation_data(starttime, endtime, plant)
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
            irradiation_values = irradiation_values[irradiation_values['irradiation']>=0]
            #power_values = power_values.where(pd.notnull(power_values), None)
            final_values = power_values.merge(irradiation_values, on='timestamp', how='outer')
            if error:
                final_values['Inverters_up'] = power_values_df.count(axis=1)-2
                final_values['Inverters_down'] = len(plant.independent_inverter_units.all()) - (power_values_df.count(axis=1)-2)
                modbus_errors = get_modbus_read_errors(starttime, endtime, plant)
                inverter_errors = get_inverter_errors(starttime, endtime, plant)
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
                modbus_errors = get_modbus_read_errors(starttime, endtime, plant)
                inverter_errors = get_inverter_errors(starttime, endtime, plant)
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

def get_power_irradiation_mobile(starttime, endtime, plant, error=False):
    try:
        power_values_df = get_plant_power(starttime, endtime, plant, True, False, True)
        irradiation_values = get_irradiation_data(starttime, endtime, plant)
        try:
            delta = (int(plant.metadata.plantmetasource.dataReportingInterval)/60)*1.5 if plant.gateway.all()[0].isVirtual else 20
        except:
            delta = 30
        if type(power_values_df) is not list and type(irradiation_values) is not list:
            power_values = pd.DataFrame()
            power_values['power'] = power_values_df['sum']
            power_values['timestamp'] = power_values_df['timestamp']
            power_values['ts'] = power_values_df['timestamp'].diff()
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
            power_values = power_values.drop('ts', 1)
            power_values = power_values.sort('timestamp')
            power_values= power_values[power_values['power']>0]
            irradiation_values = irradiation_values[irradiation_values['irradiation']>0]
            #power_values = power_values.where(pd.notnull(power_values), None)
            final_values = power_values.merge(irradiation_values, on='timestamp', how='outer')
            if error:
                final_values['Inverters_up'] = power_values_df.count(axis=1)-2
                final_values['Inverters_down'] = len(plant.independent_inverter_units.all()) - (power_values_df.count(axis=1)-2)
                modbus_errors = get_modbus_read_errors(starttime, endtime, plant)
                inverter_errors = get_inverter_errors(starttime, endtime, plant)
                if type(modbus_errors) is not list and modbus_errors.size>0:
                    final_values = final_values.merge(modbus_errors, on='timestamp', how='outer')
                if type(inverter_errors) is not list and inverter_errors.size>0:
                    final_values = final_values.merge(inverter_errors, on='timestamp', how='outer')
                try:
                    max_power = power_values_df['sum'].max()
                except:
                    max_power = 0.0
                final_values['timestamp'] = final_values['timestamp'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%SZ'))
                return final_values.sort(['timestamp']).to_json(orient='records'), max_power
            final_values['timestamp'] = final_values['timestamp'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%SZ'))
            return final_values.sort(['timestamp']).to_json(orient='records')
        elif type(power_values_df) is not list:
            power_values = pd.DataFrame()
            power_values['power'] = power_values_df['sum']
            power_values['timestamp'] = power_values_df['timestamp']
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
            power_values = power_values.sort('timestamp')
            #power_values = power_values.where(pd.notnull(power_values), None)
            if error:
                modbus_errors = get_modbus_read_errors(starttime, endtime, plant)
                inverter_errors = get_inverter_errors(starttime, endtime, plant)
                if type(modbus_errors) is not list and modbus_errors.size>0:
                    power_values = power_values.merge(modbus_errors, on='timestamp', how='outer')
                if type(inverter_errors) is not list and inverter_errors.size>0:
                    power_values = power_values.merge(inverter_errors, on='timestamp', how='outer')
                try:
                    max_power = power_values_df['sum'].max()
                except:
                    max_power = 0.0
                power_values['timestamp'] = power_values['timestamp'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%SZ'))
                return power_values.sort(['timestamp']).to_json(orient='records'), max_power
            power_values['timestamp'] = power_values['timestamp'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%SZ'))
            return power_values.sort(['timestamp']).to_json(orient='records')
        else:
            return []
    except Exception as exception:
        print(str(exception))

# from scipy.stats.stats import pearsonr
# import numpy
#
# def get_power_irradiation_correlation_coefficient_plant(starttime, endtime, plant):
#     try:
#         power_values_df = get_plant_power(starttime, endtime, plant, True, False, True)
#         irradiation_values = get_irradiation_data(starttime, endtime, plant)
#         if type(power_values_df) is not list and type(irradiation_values) is not list:
#             power_values = pd.DataFrame()
#             power_values['power'] = power_values_df['sum']
#             power_values['timestamp'] = power_values_df['timestamp']
#             final_values = power_values.merge(irradiation_values, on='timestamp', how='outer')
#             final_values = final_values.dropna()
#             power_list = final_values['power'].tolist()
#             irradiation_list = final_values['irradiation'].tolist()
#             scipy_corelation_coefficient = pearsonr(power_list, irradiation_list)
#             numpy_corelation_coefficient = numpy.corrcoef(power_list,irradiation_list)
#             #print "scipy_corelation_coefficient", scipy_corelation_coefficient[0]
#             return str(starttime.date()), numpy_corelation_coefficient[0][1]
#             #return numpy_corelation_coefficient
#     except Exception as exception:
#         print str(exception)
#
# def get_power_irradiation_correlation_coefficient_inverter(starttime, endtime, plant):
#     try:
#         power_values_df = get_plant_power(starttime, endtime, plant, True, False, True)
#         #print power_values_df
#         irradiation_values = get_irradiation_data(starttime, endtime, plant)
#         invertes = plant.independent_inverter_units.all()
#         inverter_namaes = []
#         for inverter in invertes:
#             inverter_namaes.append(str(inverter.name))
#         if type(power_values_df) is not list and type(irradiation_values) is not list:
#             for inverter_name in inverter_namaes:
#                 power_values = pd.DataFrame()
#                 power_values['power'] = power_values_df['sum']
#                 power_values['timestamp'] = power_values_df['timestamp']
#                 final_values = power_values_df.merge(irradiation_values, on='timestamp', how='outer')
#                 final_values = final_values.dropna()
#                 power_list = final_values[str(inverter_name)].tolist()
#                 irradiation_list = final_values['irradiation'].tolist()
#                 # print power_list
#                 # print irradiation_list
#                 numpy_corelation_coefficient = numpy.corrcoef(power_list,irradiation_list)
#                 print  str(inverter_name) + "," + str(starttime.date())+"," + str(numpy_corelation_coefficient[0][1])
#             #return numpy_corelation_coefficient
#     except Exception as exception:
#         print str(exception)
#
# def calculate_corelation_coefficient_mean_values(starttime, endtime, plant):
#     try:
#         duration_days = (endtime - starttime).days
#         count = 0
#         while count<duration_days:
#             start_time = starttime
#             end_time = starttime + timedelta(days=1)
#             get_power_irradiation_mean_corelation_coefficient_inverters(start_time, end_time, plant, 'MINUTE', 60)
#             starttime = starttime + timedelta(days=1)
#             count+=1
#     except Exception as exception:
#         print str(exception)
#
# def calculate_corelation_coefficient(starttime, endtime, plant):
#     try:
#         duration_days = (endtime - starttime).days
#         count = 0
#         while count<duration_days:
#             start_time = starttime
#             end_time = starttime + timedelta(days=1)
#             get_power_irradiation_correlation_coefficient_inverter(start_time, end_time, plant)
#             starttime = starttime + timedelta(days=1)
#             count+=1
#     except Exception as exception:
#         print str(exception)
#
# from solarrms.data_aggregation import get_average_value_specified_interval
# def get_power_irradiation_mean_corelation_coefficient_inverters(starttime, endtime, plant, aggregator, aggregation_period):
#     try:
#         df_irradiation = pd.DataFrame()
#         streams_list_power = ['ACTIVE_POWER']
#         streams_list_irradiation = ['IRRADIATION']
#         plant_meta = plant.metadata.plantmetasource
#         aggregated_irradiation_values = get_average_value_specified_interval(starttime, endtime, plant_meta,
#                                                                              streams_list_irradiation, aggregator,
#                                                                              aggregation_period)
#         aggregated_irradiation_values_meta = aggregated_irradiation_values[plant_meta.name]['IRRADIATION']
#         timestamp_irradiation = []
#         values_irradiation = []
#         for i in range(len(aggregated_irradiation_values_meta)):
#             timestamp_irradiation.append(aggregated_irradiation_values_meta[i]['timestamp'])
#             values_irradiation.append(aggregated_irradiation_values_meta[i]['mean_value'])
#         df_irradiation['timestamp'] = timestamp_irradiation
#         df_irradiation['irradiation'] = values_irradiation
#         df_irradiation = df_irradiation.sort('timestamp')
#         for source in plant.independent_inverter_units.all():
#             df_active_power = pd.DataFrame()
#             timestamp_active_power = []
#             values_active_power = []
#             aggregated_power_values = get_average_value_specified_interval(starttime, endtime, source,
#                                                                            streams_list_power, aggregator,
#                                                                            aggregation_period)
#             aggregated_active_power_values_source = aggregated_power_values[source.name]['ACTIVE_POWER']
#             for i in range(len(aggregated_active_power_values_source)):
#                 timestamp_active_power.append(aggregated_active_power_values_source[i]['timestamp'])
#                 values_active_power.append(aggregated_active_power_values_source[i]['mean_value'])
#             df_active_power['timestamp'] = timestamp_active_power
#             df_active_power['active_power'] = values_active_power
#             df_active_power = df_active_power.sort('timestamp')
#             df_final = df_irradiation.merge(df_active_power, on='timestamp', how='inner')
#             df_final = df_final.sort('timestamp')
#             final_power_values = df_final['active_power'].tolist()
#             final_irradiation_values = df_final['irradiation'].tolist()
#             numpy_corelation_coefficient = numpy.corrcoef(final_power_values,final_irradiation_values)
#             print  str(str(source.name)) + "," + str(starttime.date())+"," + str(numpy_corelation_coefficient[0][1])
#     except Exception as exception:
#         print str(exception)

POWER_BACKUP_PLANTS=['hirschvogelcomponents']

def get_down_time(starttime, endtime, plant):
    try:
        down_time = {}
        down_time_final = {}
        inverters = plant.independent_inverter_units.all()
        df = get_plant_power(starttime, endtime, plant, pandas_df=True, energy=True, split=True, meter_energy=False)
        if type(df) is not list and not df.empty:
            dff = df.set_index('timestamp')
            dff = dff.between_time(start_time='01:30', end_time='12:30')
            dff['ts'] = dff.index
            data = dff
            data = data - data.shift(1)
            dd = data.drop('ts',1)
            dd = dd.drop('sum',1)
            b = data.loc[~(dd!=0).any(1)]
            for inverter in inverters:
                df_inverter = pd.DataFrame()
                a = data.loc[dd[inverter.name] == 0]
                c = a.drop(b.index)
                df_inverter[inverter.name] = c[inverter.name]
                df_inverter['delta'] = c['ts'] / np.timedelta64(1, 'm')
                if str(plant.slug) in POWER_BACKUP_PLANTS:
                    df_inverter_delta = df_inverter
                elif plant.gateway.all()[0].isVirtual:
                    df_inverter_delta = df_inverter[df_inverter['delta']>20]
                elif plant.slug in PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA:
                    df_inverter_delta = df_inverter[df_inverter['delta']>10]
                else:
                    df_inverter_delta = df_inverter[df_inverter['delta']>5]
                down_time[str(inverter.name)] = df_inverter['delta'].sum()
                down_time_final[str(inverter.name)] = df_inverter_delta['delta'].sum()
            df_grid = pd.DataFrame()
            df_grid['delta'] = b['ts'] / np.timedelta64(1, 'm')
            if str(plant.slug) in POWER_BACKUP_PLANTS:
                df_grid_delta = df_grid
            elif plant.gateway.all()[0].isVirtual:
                df_grid_delta = df_grid[df_grid['delta']>20]
                #df_grid_delta = df_grid
            elif plant.slug in PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA:
                df_grid_delta = df_grid[df_grid['delta']>10]
            else:
                df_grid_delta = df_grid[df_grid['delta']>5]
            down_time_final['grid'] = df_grid_delta['delta'].sum()
            # down_time_final['grid'] = df_grid['delta'].sum()
            # down_time['grid'] = df_grid['delta'].sum()
        return down_time_final
    except Exception as exception:
        print(str(exception))
        return {}



def get_TotalYield_of_inverters(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[0]]
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
                                                     str(inverter.name): values_total_yield}))

            if len(df_list_total_yield) > 0:
                results_total_yield_temp = df_list_total_yield[0]
                for i in range(1, len(df_list_total_yield)):
                    results_total_yield_temp = results_total_yield_temp.merge(df_list_total_yield[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    updated_results_total_yield_temp = fill_results(results_total_yield_temp)
                    results_total_yield_temp = updated_results_total_yield_temp
                if df_results_total_yield.empty:
                    df_results_total_yield = results_total_yield_temp
                else:
                    df_new = pd.merge(df_results_total_yield, results_total_yield_temp, on='timestamp', how='outer')
                    df_results_total_yield = df_new
        return df_results_total_yield
        # if response_format == 'json':
        #     return df_results_total_yield.to_json(orient='records', date_format='iso')
        # else:
        #     return df_results_total_yield.to_csv(date_format="%Y-%m-%dT%H:%M:%S",
        #                                          index=False)
    except Exception as exception:
        print(str(exception))

#fancy sorting.
import re
def sorted_nicely(list_to_be_sorted):
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(list_to_be_sorted, key = alphanum_key)

def sort_inverters(plant, inverters):
    inverters_name = []
    for inverter in inverters:
        inverters_name.append(str(inverter.name))
    inverters_name = sorted_nicely(inverters_name)
    inverters = []
    for name in inverters_name:
        inverter = IndependentInverter.objects.get(plant=plant, name=name)
        inverters.append(inverter)
    return inverters

def sort_ajbs(plant, ajbs):
    from solarrms.models import AJB

    ajbs_name = []
    for ajb in ajbs:
        ajbs_name.append(str(ajb.name))
    ajbs_name = sorted_nicely(ajbs_name)
    ajbs = []
    for name in ajbs_name:
        ajb = AJB.objects.get(plant=plant, name=name)
        ajbs.append(ajb)
    return ajbs

def get_plant_device_details(plant):
    try:
        devices_details = collections.OrderedDict()
        inverter_details = collections.OrderedDict()
        ajb_details = collections.OrderedDict()
        energy_meter_details = collections.OrderedDict()
        transformer_details = collections.OrderedDict()
        plant_meta_details = collections.OrderedDict()
        #solar_metrics_details = collections.OrderedDict()
        weather_station_details = collections.OrderedDict()

        inverters = plant.independent_inverter_units.all()
        inverters = sort_inverters(plant, inverters)

        ajbs = plant.ajb_units.all()
        ajbs = sort_ajbs(plant, ajbs)

        plant_meta_source = plant.metadata.plantmetasource
        energy_meters = plant.energy_meters.all().filter(isActive=True)
        transformers = plant.transformers.all().filter(isActive=True)
        solar_groups = plant.solar_groups.all().filter(isActive=True)
        #solar_metrics = plant.solar_metrics.all().filter(isActive=True)
        weather_stations = plant.weather_stations.all().filter(isActive=True)
        inverter_fields_list = []
        ajb_fields_list = []
        energy_meter_fields_list = []
        transformer_fields_list = []
        solar_metric_fields_list = []
        weather_station_fields_list = []
        plant_meta_fields_list = []
        group_names = []
        if len(solar_groups)>0:
            for group in solar_groups:
                group_inverters = group.groupIndependentInverters.all()
                group_inverters = sort_inverters(plant, group_inverters)

                group_ajbs = group.groupAJBs.all()
                group_ajbs = sort_ajbs(plant, group_ajbs)

                group_inverters_name = collections.OrderedDict()
                group_ajbs_name = collections.OrderedDict()
                group_energy_meters_name = collections.OrderedDict()
                group_transformers_name = collections.OrderedDict()
                group_solar_metrics_name = collections.OrderedDict()
                group_weather_stations_name = collections.OrderedDict()
                for inverter in group_inverters:
                    group_inverters_name[str(inverter.name)] = str(inverter.sourceKey)
                inverter_details[str(group.name)] = group_inverters_name
                for ajb in group_ajbs:
                    group_ajbs_name[str(ajb.name)] = str(ajb.sourceKey)
                ajb_details[str(group.name)] = group_ajbs_name
                group_names.append(str(group.name))
            for energy_meter in energy_meters:
                group_energy_meters_name[str(energy_meter.name)] = str(energy_meter.sourceKey)
            energy_meter_details['energy_meter_names'] = group_energy_meters_name
            for transformer in transformers:
                group_transformers_name[str(transformer.name)] = str(transformer.sourceKey)
            transformer_details['transformer_names'] = group_transformers_name
            # for solar_metric in solar_metrics:
            #     group_solar_metrics_name[str(solar_metric.name)] = str(solar_metric.sourceKey)
            # solar_metrics_details['solar_metric_names'] = group_solar_metrics_name
            for weather_station in weather_stations:
                group_weather_stations_name[str(weather_station.name)] = str(weather_station.sourceKey)
            weather_station_details['weather_station_names'] = group_weather_stations_name
        else:
            group_inverters_name = collections.OrderedDict()
            group_ajbs_name = collections.OrderedDict()
            group_energy_meters_name = collections.OrderedDict()
            group_transformers_name = collections.OrderedDict()
            group_solar_metrics_name = collections.OrderedDict()
            group_weather_stations_name = collections.OrderedDict()
            for inverter in inverters:
                group_inverters_name[str(inverter.name)] = str(inverter.sourceKey)
            inverter_details['inverter_names'] = group_inverters_name
            for ajb in ajbs:
                group_ajbs_name[str(ajb.name)] = str(ajb.sourceKey)
            ajb_details['ajb_names'] = group_ajbs_name
            for energy_meter in energy_meters:
                group_energy_meters_name[str(energy_meter.name)] = str(energy_meter.sourceKey)
            energy_meter_details['energy_meter_names'] = group_energy_meters_name
            for transformer in transformers:
                group_transformers_name[str(transformer.name)] = str(transformer.sourceKey)
            transformer_details['transformer_names'] = group_transformers_name
            # for solar_metric in solar_metrics:
            #     group_solar_metrics_name[str(solar_metric.name)] = str(solar_metric.sourceKey)
            # solar_metrics_details['solar_metric_names'] = group_solar_metrics_name
            for weather_station in weather_stations:
                group_weather_stations_name[str(weather_station.name)] = str(weather_station.sourceKey)
            weather_station_details['weather_station_names'] = group_weather_stations_name

        if len(group_names)>0:
            devices_details['group_names'] = group_names
        if len(inverters)>0:
            inverter_fields = inverter.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            for inverter_field in inverter_fields:
                try:
                    inverter_solar_field = SolarField.objects.get(source=inverter,name=inverter_field.name)
                    inverter_fields_list.append(str(inverter_solar_field.displayName))
                except:
                    inverter_fields_list.append(str(inverter_field.name))
            inverter_details['inverter_streams'] = sorted_nicely(inverter_fields_list)
            devices_details['inverters'] = inverter_details
        if len(ajbs)>0:
            ajb_fields = ajbs[0].fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            for ajb_field in ajb_fields:
                try:
                    ajb_solar_field = SolarField.objects.get(source=ajbs[0], name=ajb_field.name)
                    ajb_fields_list.append(str(ajb_solar_field.displayName))
                except:
                    ajb_fields_list.append(str(ajb_field.name))
            ajb_details['ajb_streams'] = sorted_nicely(ajb_fields_list)
            devices_details['ajbs'] = ajb_details
        if len(energy_meters)>0:
            energy_meter_fields = energy_meters[0].fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            for energy_meter_field in energy_meter_fields:
                try:
                    energy_meter_solar_field = SolarField.objects.get(source=energy_meters[0], name=energy_meter_field.name)
                    energy_meter_fields_list.append(str(energy_meter_solar_field.displayName))
                except:
                    energy_meter_fields_list.append(str(energy_meter_field.name))
            energy_meter_details['energy_meter_streams'] = sorted_nicely(energy_meter_fields_list)
            devices_details['energy_meters'] = energy_meter_details
        if len(transformers)>0:
            transformer_fields = transformers[0].fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            for transformer_field in transformer_fields:
                try:
                    transformer_solar_field = SolarField.objects.get(source=transformers[0], name=transformer_field.name)
                    transformer_fields_list.append(str(transformer_solar_field.displayName))
                except:
                    transformer_fields_list.append(str(transformer_field.name))
            transformer_details['transformer_streams'] = sorted_nicely(transformer_fields_list)
            devices_details['transformers'] = transformer_details
        # if len(solar_metrics)>0:
        #     solar_metric_fields = solar_metric.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
        #     for solar_metric_field in solar_metric_fields:
        #         try:
        #             solar_metric_solar_field = SolarField.objects.get(source=solar_metric, name=solar_metric_field.name)
        #             solar_metric_fields_list.append(str(solar_metric_solar_field.name))
        #         except:
        #             solar_metric_fields_list.append(str(solar_metric_field.name))
        #     solar_metrics_details['solar_metric_streams'] = sorted_nicely(solar_metric_fields_list)
        #     devices_details['solar_metrics'] = solar_metrics_details
        if len(weather_stations)>0:
            weather_station_fields = weather_stations[0].fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            for weather_station_field in weather_station_fields:
                try:
                    weather_station_solar_field = SolarField.objects.get(source=weather_stations[0], name=weather_station_field.name)
                    weather_station_fields_list.append(str(weather_station_solar_field.displayName))
                except:
                    weather_station_fields_list.append(str(weather_station_field.name))
            weather_station_details['weather_station_streams'] = sorted_nicely(weather_station_fields_list)
            devices_details['weather_stations'] = weather_station_details

        group_plant_meta_name = {}
        if plant_meta_source:
            group_plant_meta_name[str(plant_meta_source.name)] = str(plant_meta_source.sourceKey)
            plant_meta_fields = plant_meta_source.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            for plant_meta_field in plant_meta_fields:
                try:
                    plant_meta_solar_field = SolarField.objects.get(source=plant_meta_source, name=plant_meta_field.name)
                    plant_meta_fields_list.append(str(plant_meta_solar_field.displayName))
                except:
                    plant_meta_fields_list.append(str(plant_meta_field.name))
            plant_meta_details['plant_meta_source_names'] = group_plant_meta_name
            plant_meta_details['plant_meta_streams'] = sorted_nicely(plant_meta_fields_list)
            devices_details['plant_meta_source'] = plant_meta_details
        return devices_details
    except Exception as exception:
        logger.debug(str(exception))
        return {}


def get_client_device_details_across_plants(plants):
    try:
        final_device_details = {}
        inverter_fields_list = set()
        ajb_fields_list = set()
        energy_meter_fields_list = set()
        transformer_fields_list = set()
        #solar_metric_fields_list = set()
        weather_station_fields_list = set()
        plant_meta_fields_list = set()
        for plant in plants:
            devices_details = collections.OrderedDict()
            inverter_details = collections.OrderedDict()
            ajb_details = collections.OrderedDict()
            energy_meter_details = collections.OrderedDict()
            transformer_details = collections.OrderedDict()
            plant_meta_details = collections.OrderedDict()
            #solar_metrics_details = collections.OrderedDict()
            weather_station_details = collections.OrderedDict()
            inverters = plant.independent_inverter_units.all()
            ajbs = plant.ajb_units.all()
            plant_meta_source = plant.metadata.plantmetasource
            energy_meters = plant.energy_meters.all().filter(isActive=True)
            transformers = plant.transformers.all().filter(isActive=True)
            solar_groups = plant.solar_groups.all().filter(isActive=True)
            #solar_metrics = plant.solar_metrics.all().filter(isActive=True)
            weather_stations = plant.weather_stations.all().filter(isActive=True)
            group_names = []
            if len(solar_groups)>0:
                for group in solar_groups:
                    group_inverters = group.groupIndependentInverters.all().filter(isActive=True)
                    group_ajbs = group.groupAJBs.all().filter(isActive=True)
                    group_inverters_name = collections.OrderedDict()
                    group_ajbs_name = collections.OrderedDict()
                    group_energy_meters_name = collections.OrderedDict()
                    group_transformers_name = collections.OrderedDict()
                    group_solar_metrics_name = collections.OrderedDict()
                    group_weather_stations_name = collections.OrderedDict()
                    for inverter in group_inverters:
                        group_inverters_name[str(inverter.name)] = str(inverter.sourceKey)
                    inverter_details[str(group.name)] = group_inverters_name
                    for ajb in group_ajbs:
                        group_ajbs_name[str(ajb.name)] = str(ajb.sourceKey)
                    ajb_details[str(group.name)] = group_ajbs_name
                    group_names.append(str(group.name))
                for energy_meter in energy_meters:
                    group_energy_meters_name[str(energy_meter.name)] = str(energy_meter.sourceKey)
                energy_meter_details['energy_meter_names'] = group_energy_meters_name
                for transformer in transformers:
                    group_transformers_name[str(transformer.name)] = str(transformer.sourceKey)
                transformer_details['transformer_names'] = group_transformers_name
                # for solar_metric in solar_metrics:
                #     group_solar_metrics_name[str(solar_metric.name)] = str(solar_metric.sourceKey)
                # solar_metrics_details['solar_metric_names'] = group_solar_metrics_name
                for weather_station in weather_stations:
                    group_weather_stations_name[str(weather_station.name)] = str(weather_station.sourceKey)
                weather_station_details['weather_station_names'] = group_weather_stations_name
            else:
                group_inverters_name = collections.OrderedDict()
                group_ajbs_name = collections.OrderedDict()
                group_energy_meters_name = collections.OrderedDict()
                group_transformers_name = collections.OrderedDict()
                #group_solar_metrics_name = collections.OrderedDict()
                group_weather_stations_name = collections.OrderedDict()
                for inverter in inverters:
                    group_inverters_name[str(inverter.name)] = str(inverter.sourceKey)
                inverter_details['inverter_names'] = group_inverters_name
                for ajb in ajbs:
                    group_ajbs_name[str(ajb.name)] = str(ajb.sourceKey)
                ajb_details['ajb_names'] = group_ajbs_name
                for energy_meter in energy_meters:
                    group_energy_meters_name[str(energy_meter.name)] = str(energy_meter.sourceKey)
                energy_meter_details['energy_meter_names'] = group_energy_meters_name
                for transformer in transformers:
                    group_transformers_name[str(transformer.name)] = str(transformer.sourceKey)
                transformer_details['transformer_names'] = group_transformers_name
                # for solar_metric in solar_metrics:
                #     group_solar_metrics_name[str(solar_metric.name)] = str(solar_metric.sourceKey)
                # solar_metrics_details['solar_metric_names'] = group_solar_metrics_name
                for weather_station in weather_stations:
                    group_weather_stations_name[str(weather_station.name)] = str(weather_station.sourceKey)
                weather_station_details['weather_station_names'] = group_weather_stations_name

            if len(group_names)>0:
                devices_details['group_names'] = group_names
            if len(inverters)>0:
                inverter_fields = inverter.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
                for inverter_field in inverter_fields:
                    try:
                        inverter_solar_field = SolarField.objects.get(source=inverter,name=inverter_field.name)
                        inverter_fields_list.add(str(inverter_solar_field.displayName))
                    except:
                        inverter_fields_list.add(str(inverter_field.name))
                #inverter_details['inverter_streams'] = sorted_nicely(inverter_fields_list)
                devices_details['inverters'] = inverter_details
            if len(ajbs)>0:
                ajb_fields = ajb.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
                for ajb_field in ajb_fields:
                    try:
                        ajb_solar_field = SolarField.objects.get(source=ajb, name=ajb_field.name)
                        ajb_fields_list.add(str(ajb_solar_field.displayName))
                    except:
                        ajb_fields_list.add(str(ajb_field.name))
                #ajb_details['ajb_streams'] = sorted_nicely(ajb_fields_list)
                devices_details['ajbs'] = ajb_details
            if len(energy_meters)>0:
                energy_meter_fields = energy_meter.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
                for energy_meter_field in energy_meter_fields:
                    try:
                        energy_meter_solar_field = SolarField.objects.get(source=energy_meter, name=energy_meter_field.name)
                        energy_meter_fields_list.add(str(energy_meter_solar_field.displayName))
                    except:
                        energy_meter_fields_list.add(str(energy_meter_field.name))
                #energy_meter_details['energy_meter_streams'] = sorted_nicely(energy_meter_fields_list)
                devices_details['energy_meters'] = energy_meter_details
            if len(transformers)>0:
                transformer_fields = transformer.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
                for transformer_field in transformer_fields:
                    try:
                        transformer_solar_field = SolarField.objects.get(source=transformer, name=transformer_field.name)
                        transformer_fields_list.add(str(transformer_solar_field.displayName))
                    except:
                        transformer_fields_list.add(str(transformer_field.name))
                #transformer_details['transformer_streams'] = sorted_nicely(transformer_fields_list)
                devices_details['transformers'] = transformer_details
            # if len(solar_metrics)>0:
            #     solar_metric_fields = solar_metric.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
            #     for solar_metric_field in solar_metric_fields:
            #         try:
            #             solar_metric_solar_field = SolarField.objects.get(source=solar_metric, name=solar_metric_field.name)
            #             solar_metric_fields_list.add(str(solar_metric_solar_field.name))
            #         except:
            #             solar_metric_fields_list.add(str(solar_metric_field.name))
            #     #solar_metrics_details['solar_metric_streams'] = sorted_nicely(solar_metric_fields_list)
            #     devices_details['solar_metrics'] = solar_metrics_details
            if len(weather_stations)>0:
                weather_station_fields = weather_station.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
                for weather_station_field in weather_station_fields:
                    try:
                        weather_station_solar_field = SolarField.objects.get(source=weather_station, name=weather_station_field.name)
                        weather_station_fields_list.add(str(weather_station_solar_field.displayName))
                    except:
                        weather_station_fields_list.add(str(weather_station_field.name))
                #weather_station_details['weather_station_streams'] = sorted_nicely(weather_station_fields_list)
                devices_details['weather_stations'] = weather_station_details

            group_plant_meta_name = {}
            if plant_meta_source:
                group_plant_meta_name[str(plant_meta_source.name)] = str(plant_meta_source.sourceKey)
                plant_meta_fields = plant_meta_source.fields.all().filter(isActive=True).filter(streamDataType='FLOAT')
                for plant_meta_field in plant_meta_fields:
                    try:
                        plant_meta_solar_field = SolarField.objects.get(source=plant_meta_source, name=plant_meta_field.name)
                        plant_meta_fields_list.add(str(plant_meta_solar_field.displayName))
                    except:
                        plant_meta_fields_list.add(str(plant_meta_field.name))
                plant_meta_details['plant_meta_source_names'] = group_plant_meta_name
                #plant_meta_details['plant_meta_streams'] = sorted_nicely(plant_meta_fields_list)
                devices_details['plant_meta_source'] = plant_meta_details
            final_device_details[str(plant.slug)]  = devices_details
        if inverter_fields_list:
            final_device_details['inverter_streams'] = sorted_nicely(inverter_fields_list)
        if ajb_fields_list:
            final_device_details['ajb_streams'] = sorted_nicely(ajb_fields_list)
        if energy_meter_fields_list:
            final_device_details['energy_meter_streams'] = sorted_nicely(energy_meter_fields_list)
        if transformer_fields_list:
            final_device_details['transformer_streams'] = sorted_nicely(transformer_fields_list)
        # if solar_metric_fields_list:
        #     final_device_details['solar_metric_streams'] = sorted_nicely(solar_metric_fields_list)
        if weather_station_fields_list:
            final_device_details['weather_station_streams'] = sorted_nicely(weather_station_fields_list)
        if plant_meta_fields_list:
            final_device_details['plant_meta_streams'] = sorted_nicely(plant_meta_fields_list)
        return final_device_details
    except Exception as exception:
        logger.debug(str(exception))
        return {}



def get_kwh_per_meter_square_value(starttime, endtime, plant):
    try:
        # get the irradiation values
        if hasattr(plant, 'metadata'):
            if plant.slug == "gupl2":
                irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                           stream_name='EXTERNAL_IRRADIATION',
                                                                           timestamp_in_data__gte=starttime,
                                                                           timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            else:
                irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                           stream_name='IRRADIATION',
                                                                           timestamp_in_data__gte=starttime,
                                                                           timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                if len(irradiation_data) == 0:
                    irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                               stream_name='EXTERNAL_IRRADIATION',
                                                                               timestamp_in_data__gte=starttime,
                                                                               timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            try:
                idf = pd.DataFrame(irradiation_data[:], columns=['irradiance','timestamp'])
                idf["irradiance"] = idf["irradiance"].astype(float)
                idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                idf['average_irradiance'] = (idf["irradiance"] + idf["irradiance"].shift(+1))/2.0
                idf = idf.set_index('timestamp')
                idf = idf.between_time(start_time='00:00', end_time='13:30')
                idf = idf.reset_index()
                idf['delta'] = idf['timestamp'] - idf['timestamp'].shift(+1)
                idf['delta'] = idf['delta'] / np.timedelta64(1, 'h')
                idf = idf[idf['delta'] < 0.6]
                idf['values'] = idf['average_irradiance'] * idf['delta']
                return idf['values'].sum()
            except Exception as exception:
                print str(exception)
                return 0.00
    except Exception as exception:
        print(str(exception))
        return 0.0

def get_aggregated_insolation_values(starttime, endtime, plant, aggregator, aggregation_period):
    try:
        # get the irradiation values
        if hasattr(plant, 'metadata'):
            irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                       stream_name='IRRADIATION',
                                                                       timestamp_in_data__gte=starttime,
                                                                       timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            if len(irradiation_data) == 0:
                irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                           stream_name='EXTERNAL_IRRADIATION',
                                                                           timestamp_in_data__gte=starttime,
                                                                           timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
            try:
                idf = pd.DataFrame(irradiation_data[:], columns=['irradiance','timestamp'])
                idf["irradiance"] = idf["irradiance"].astype(float)
                idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                idf['average_irradiance'] = (idf["irradiance"] + idf["irradiance"].shift(+1))/2.0
                idf = idf.set_index('timestamp')
                idf = idf.between_time(start_time='00:00', end_time='13:30')
                idf = idf.reset_index()
                idf['delta'] = idf['timestamp'] - idf['timestamp'].shift(+1)
                idf['delta'] = idf['delta'] / np.timedelta64(1, 'h')
                idf = idf[idf['delta'] < 0.5]
                idf['values'] = idf['average_irradiance'] * idf['delta']
                final_df = pd.DataFrame()
                final_df['timestamp'] = idf['timestamp']
                final_df['insolation'] = idf['values']

                if aggregator == 'MINUTE':
                    aggregation = str(aggregation_period) + 'Min'
                elif aggregator == 'DAY':
                    aggregation = str(aggregation_period) + 'D'
                elif aggregator == 'MONTH':
                    aggregation = str(aggregation_period) + 'M'
                else:
                    aggregation = '1D'
                data = []
                if not final_df.empty:
                    final_df = final_df.set_index('timestamp')
                    grouped = final_df.groupby(pd.TimeGrouper(aggregation))
                    insolation = grouped.sum()
                    for key, value in insolation['insolation'].iteritems():
                        try:
                            if not math.isnan(value):
                                data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'insolation': value})
                            else:
                                #data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                                pass
                        except:
                            if not math.isnan(value):
                                data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'insolation': value})
                            else:
                                #data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                                pass
                            continue
                return data
            except Exception as exception:
                print str(exception)
    except Exception as exception:
        logger.debug(str(exception))
        return []

# method to get aggregated ambient temperature values
def get_aggregated_ambient_temperature_values(starttime, endtime, plant):
    try:
        # get the ambient temperature values
        if hasattr(plant, 'metadata'):
            ambient_temperature_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                               stream_name='AMBIENT_TEMPERATURE',
                                                                               timestamp_in_data__gt=starttime,
                                                                               timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

            try:
                adf = pd.DataFrame(ambient_temperature_data[:], columns=['ambient_temperature','timestamp'])
                adf["ambient_temperature"] = adf["ambient_temperature"].astype(float)
                adf['timestamp'] = adf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                adf = adf.set_index('timestamp')
                adf = adf.between_time(start_time='00:30', end_time='12:30')
                return adf['ambient_temperature'].mean()
            except Exception as exception:
                print str(exception)
                return 0.00
    except Exception as exception:
        print(str(exception))

# method to get aggregated module temperature values
def get_aggregated_module_temperature_values(starttime, endtime, plant):
    try:
        # get the module temperature values
        if hasattr(plant, 'metadata'):
            module_temperature_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                              stream_name='MODULE_TEMPERATURE',
                                                                              timestamp_in_data__gte=starttime,
                                                                              timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

            try:
                mdf = pd.DataFrame(module_temperature_data[:], columns=['module_temperature','timestamp'])
                mdf["module_temperature"] = mdf["module_temperature"].astype(float)
                mdf['timestamp'] = mdf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                mdf = mdf.set_index('timestamp')
                mdf = mdf.between_time(start_time='00:00', end_time='13:30')
                if not math.isnan(mdf['module_temperature'].mean()):
                    return mdf['module_temperature'].mean()
                else:
                    return 0.0
            except Exception as exception:
                print str(exception)
                return 0.00
    except Exception as exception:
        print(str(exception))

# method to get aggregated wind speed values
def get_aggregated_wind_speed_values(starttime, endtime, plant):
    try:
        # get the module temperature values
        if hasattr(plant, 'metadata'):
            wind_speed_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                                      stream_name='WINDSPEED',
                                                                      timestamp_in_data__gt=starttime,
                                                                      timestamp_in_data__lt=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

            try:
                wdf = pd.DataFrame(wind_speed_data[:], columns=['wind_speed','timestamp'])
                wdf["wind_speed"] = wdf["wind_speed"].astype(float)
                wdf['timestamp'] = wdf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
                wdf = wdf.set_index('timestamp')
                wdf = wdf.between_time(start_time='00:00', end_time='13:30')
                return wdf['wind_speed'].mean()
            except Exception as exception:
                print str(exception)
                return 0.00
    except Exception as exception:
        print(str(exception))


def get_user_feature_enabled(plant, user):
    try:
        features_list = {}
        features_list['solar_metrics'] = True
        features_list['economic_benefits'] = True
        features_list['analytics'] = True
        features_list['alerts'] = True
        owner, client = is_owner(user)
        organization_user = user.organizations_organizationuser.all()[0]
        if owner or organization_user.is_admin:
            return features_list
        else:
            try:
                feature = plant.features_enabled.all()[0]
                features_list['solar_metrics'] = feature.solar_metrics
                features_list['economic_benefits'] = feature.economic_benefits
                features_list['analytics'] = feature.analytics
                features_list['alerts'] = feature.alerts
                return features_list
            except:
                return features_list
    except Exception as exception:
        print str(exception)
        return features_list


def get_expected_energy(identifier, identifier_type, starttime, endtime):
    total_expected_energy = 0
    try:
        if identifier_type == 'PLANT':
            try:
                plant = SolarPlant.objects.get(slug=identifier)
                plant_meta_source = PlantMetaSource.objects.get(plant=plant)
            except Exception as ex:
                print ("plant slug does not exist.")
                return total_expected_energy
            stream_name = 'plant_energy'
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
                print("tz", tz)
            except:
                print("error in converting current time to source timezone")

        else: #if identifier type is SOURCE
            try:
                source = Sensor.objects.get(sourceKey = identifier)
            except Exception as ex:
                print ("sourceKey does not exist.")
                return total_expected_energy
            stream_name = 'source_energy'
            try:
                tz = pytz.timezone(source.dataTimezone)
                print("tz", tz)
            except:
                print("error in converting current time to source timezone")

        try:
            if starttime.tzinfo is None:
                starttime = pytz.utc.localize(starttime)
            if endtime.tzinfo is None:
                endtime = pytz.utc.localize(endtime)

            starttime_tz = starttime.astimezone(tz)
            endtime_tz = endtime.astimezone(tz)

            duration = endtime_tz - starttime_tz
            if (duration.total_seconds() < 3600) and (starttime_tz.hour == endtime_tz.hour):
                minutes = duration.total_seconds() //60
                new_starttime = starttime_tz
                new_starttime = new_starttime.replace(minute=0, second=0, microsecond=0)
                new_endtime = starttime_tz + timedelta(hours=1)
                new_endtime = new_endtime.replace( minute=0, second=0, microsecond=0)

                expected_energy = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT, count_time_period=PREDICTION_TIMEPERIOD,
                                                                                          identifier=identifier, stream_name = stream_name, model_name = 'STATISTICAL_LATEST',
                                                                                          ts__gte=new_starttime, ts__lt=new_endtime).values_list('value','lower_bound','upper_bound')


                if expected_energy:
                    total_energy = expected_energy[0][0]
                    lower_bound = expected_energy[0][1]
                    upper_bound = expected_energy[0][2]
                    print ('minutes', minutes)
                    print('total_energy', total_energy)
                    total_expected_energy = (minutes / 60) * total_energy
                    total_lower_bound = (minutes / 60) * lower_bound
                    total_upper_bound = (minutes / 60) * upper_bound
                    return [total_expected_energy, total_lower_bound, total_upper_bound]

            else:
                new_starttime = starttime_tz + timedelta(hours=1)
                new_starttime = new_starttime.replace(minute=0, second=0, microsecond=0)
                new_endtime = endtime_tz
                new_endtime = new_endtime.replace(minute=0, second=0, microsecond=0)

                # time btween startime+1 and endtime hours
                expected_energy = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT, count_time_period=PREDICTION_TIMEPERIOD,
                                                                                          identifier=identifier, stream_name = stream_name, model_name = 'STATISTICAL_LATEST',
                                                                                          ts__gte=new_starttime, ts__lt=new_endtime).values_list('value','lower_bound','upper_bound')
                mid_energy = 0
                mid_lower_bound = 0
                mid_upper_bound = 0
                if expected_energy:
                    print ('expected energy:', expected_energy)
                    expected_energy_list = [i[0] for i in expected_energy]
                    expected_lower_bound_list = [i[1] for i in expected_energy]
                    expected_upper_bound_list = [i[2] for i in expected_energy]
                    print('expected_energy_list',expected_energy_list)
                    mid_energy = sum(expected_energy_list)
                    mid_lower_bound = sum(expected_lower_bound_list)
                    mid_upper_bound = sum(expected_upper_bound_list)
                    print ('mid_energy:', mid_energy)

                # time btween startime and starttime+1 hours
                new_starttime = starttime_tz
                new_starttime = new_starttime.replace(minute=0, second=0, microsecond=0)
                new_endtime = starttime_tz + timedelta(hours=1)
                new_endtime = new_endtime.replace(minute=0, second=0, microsecond=0)

                expected_energy = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT, count_time_period=PREDICTION_TIMEPERIOD,
                                                                                          identifier=identifier, stream_name = stream_name, model_name = 'STATISTICAL_LATEST',
                                                                                          ts__gte=new_starttime, ts__lt=new_endtime).values_list('value','lower_bound','upper_bound')
                start_energy = 0
                start_lower_bound = 0
                start_upper_bound = 0
                if expected_energy:
                    start_energy = expected_energy[0][0]
                    start_lower_bound = expected_energy[0][1]
                    start_upper_bound = expected_energy[0][2]
                duration =  new_endtime - starttime_tz
                if duration.total_seconds() > 0:
                    minutes = (duration.total_seconds()) // 60
                    print ('minutes', minutes)
                    start_energy = (minutes / 60) * start_energy
                    start_lower_bound = (minutes / 60) * start_lower_bound
                    start_upper_bound = (minutes / 60) * start_upper_bound
                    print('start_energy', start_energy)
                else:
                    start_energy = 0
                    start_lower_bound = 0
                    start_upper_bound = 0

                # time between last hour and actual end time
                new_starttime = endtime_tz
                new_starttime = new_starttime.replace(minute=0, second=0, microsecond=0)

                new_endtime = endtime_tz + timedelta(hours=1)
                new_endtime = new_endtime.replace(minute=0, second=0, microsecond=0)
                expected_energy = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT, count_time_period=PREDICTION_TIMEPERIOD,
                                                                                          identifier=identifier, stream_name = stream_name, model_name = 'STATISTICAL_LATEST',
                                                                                          ts__gte=new_starttime, ts__lt=new_endtime).values_list('value','lower_bound','upper_bound')
                end_energy = 0
                end_lower_bound = 0
                end_upper_bound = 0
                if expected_energy:
                    end_energy = expected_energy[0][0]
                    end_lower_bound = expected_energy[0][1]
                    end_upper_bound = expected_energy[0][2]
                duration =  endtime_tz - new_starttime
                if duration.total_seconds() > 0:
                    minutes = (duration.total_seconds()) // 60
                    print('minutes',minutes)
                    end_energy = (minutes / 60) * end_energy
                    end_lower_bound = (minutes / 60) * end_lower_bound
                    end_upper_bound = (minutes / 60) * end_upper_bound
                    print ('end_energy', end_energy)
                else:
                    end_energy = 0
                    end_lower_bound = 0
                    end_upper_bound = 0

                total_expected_energy = start_energy + mid_energy + end_energy
                total_lower_bound = start_lower_bound +mid_lower_bound + end_lower_bound
                total_upper_bound = start_upper_bound + mid_upper_bound + end_upper_bound
                print('total_expected_energy', total_expected_energy)
                return [total_expected_energy, total_lower_bound, total_upper_bound]

        except Exception as ex:
            print str(ex)


    except Exception as ex:
        print str(ex)

'''
slugs = ['palladam']
from dateutil import parser
from datetime import timedelta
from solarrms.models import *
from solarrms.solarutils import *
starttime = parser.parse("2016-07-01 03:00:00+05:30")
endtime = parser.parse("2016-07-02 00:00:00+05:30")
td = timedelta(hours=24)
#fd = open("pr_values.txt", "w")
for slug in slugs:
    plant = SolarPlant.objects.get(slug=slug)
    st = starttime
    et = endtime
    while st < parser.parse("2016-08-11 00:00:00+05:30"):
        pr = calculate_pr_new(st, et, plant)
        #fd.write(",".join([plant.slug, str(st.date()), str(pr), "\n"]))
        print ",".join([plant.slug, str(st.date()), str(pr), "\n"])
        st = st + td
        et = et + td
        '''


def get_daily_or_hourly_weather_data(splant, starttime, endtime, timestamp_type, prediction_type, source):
    weather_data = WeatherData.objects.filter(api_source=source, timestamp_type=timestamp_type,
                                              identifier=splant.slug, prediction_type=prediction_type,
                                              ts__gte=starttime, ts__lt=endtime).order_by('prediction_type',
                                                                                          'ts').values_list(
        'api_source', 'timestamp_type', 'identifier', 'ts', 'city', 'latitude', 'longitude', 'sunrise', 'sunset',
        'cloudcover', 'humidity', 'windspeed', 'precipMM', 'prediction_type', 'updated_at', 'chanceofrain', 'ghi',
        'ghi_10','ghi_90', 'dni', 'dni_10', 'dni_90', 'dhi', 'air_temp')
    weather_data_modified = list()
    for wd in weather_data:
        try:
            weather_data_inner = dict()
            weather_data_inner['api_source'] = wd[0]
            weather_data_inner['timestamp_type'] = wd[1]
            weather_data_inner['identifier'] = wd[2]
            weather_data_inner['ts'] = datetime.strftime(wd[3], "%Y-%m-%dT%H:%M:%SZ")
            weather_data_inner['city'] = wd[4]
            weather_data_inner['latitude'] = "%s" % wd[5]
            weather_data_inner['longitude'] = "%s" % wd[6]
            weather_data_inner['sunrise'] = datetime.strftime(wd[7], "%Y-%m-%dT%H:%M:%SZ") if wd[7] else None
            weather_data_inner['sunset'] = datetime.strftime(wd[8], "%Y-%m-%dT%H:%M:%SZ") if wd[8] else None
            weather_data_inner['cloudcover'] = "%s" % wd[9]
            weather_data_inner['humidity'] = "%s" % wd[10]
            weather_data_inner['windspeed'] = "%s" % wd[11]
            weather_data_inner['precipMM'] = "%s" % wd[12]
            weather_data_inner['prediction_type'] = "%s" % wd[13]
            weather_data_inner['updated_at'] = datetime.strftime(wd[14], "%Y-%m-%dT%H:%M:%SZ")
            weather_data_inner['chanceofrain'] = "%s" % wd[15]
            #solcast parameters
            weather_data_inner['ghi'] = "%s" % wd[16]
            weather_data_inner['ghi_10'] = "%s" % wd[17]
            weather_data_inner['ghi_90'] = "%s" % wd[18]
            weather_data_inner['dni'] = "%s" % wd[19]
            weather_data_inner['dni_10'] = "%s" % wd[20]
            weather_data_inner['dni_90'] = "%s" % wd[21]
            weather_data_inner['dhi'] = "%s" % wd[22]
            weather_data_inner['air_temp'] = "%s" % wd[23]
            weather_data_modified.append(weather_data_inner)
        except Exception as exception:
            logger.debug(exception)
            continue
    return weather_data_modified


def get_predicted_energy_values_timeseries(starttime, endtime, plant, model_name, count_time_period, split=False):
    try:
        if split is False:
            df_final = pd.DataFrame()
            predicted_values = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                count_time_period=count_time_period,
                                                                identifier_type='plant',
                                                                plant_slug=str(plant.slug),
                                                                identifier=str(plant.slug),
                                                                stream_name='plant_energy',
                                                                model_name=model_name,
                                                                ts__gte=starttime,
                                                                ts__lte=endtime)
            timestamp = []
            lower_bound = []
            upper_bound = []
            actual_value = []
            for predicted_value in predicted_values:
                timestamp.append(predicted_value.ts)
                try:
                    lower_bound_value = predicted_value.lower_bound if float(predicted_value.lower_bound)>0 else 0.0
                except:
                    lower_bound_value = 0.0
                try:
                    upper_bound_value = predicted_value.upper_bound if float(predicted_value.upper_bound)>0 else 0.0
                except:
                    upper_bound_value = 0.0
                try:
                    value = predicted_value.value if float(predicted_value.value)>0 else 0.0
                except:
                    value = 0.0
                lower_bound.append(lower_bound_value)
                upper_bound.append(upper_bound_value)
                actual_value.append(value)
            df_final['lower_bound'] = lower_bound
            df_final['upper_bound'] = upper_bound
            df_final['actual_value'] = actual_value
            df_final['timestamp'] = timestamp
            return df_final.sort_values('timestamp').to_json(orient='records',date_format='iso')
        else:
            final_result = {}
            inverters = plant.independent_inverter_units.all().filter(isActive=True)
            for inverter in inverters:
                df_inverter = pd.DataFrame()
                predicted_values = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                    count_time_period=count_time_period,
                                                                    identifier_type='source',
                                                                    plant_slug=str(plant.slug),
                                                                    identifier=str(inverter.sourceKey),
                                                                    stream_name='source_energy',
                                                                    model_name=model_name,
                                                                    ts__gte=starttime,
                                                                    ts__lte=endtime)
                timestamp = []
                lower_bound = []
                upper_bound = []
                actual_value = []
                for predicted_value in predicted_values:
                    timestamp.append(predicted_value.ts)
                    try:
                        lower_bound_value = predicted_value.lower_bound if float(predicted_value.lower_bound)>0 else 0.0
                    except:
                        lower_bound_value = 0.0
                    try:
                        upper_bound_value = predicted_value.upper_bound if float(predicted_value.upper_bound)>0 else 0.0
                    except:
                        upper_bound_value = 0.0
                    try:
                        value = predicted_value.value if float(predicted_value.value)>0 else 0.0
                    except:
                        value = 0.0
                    lower_bound.append(lower_bound_value)
                    upper_bound.append(upper_bound_value)
                    actual_value.append(value)
                df_inverter['lower_bound'] = lower_bound
                df_inverter['upper_bound'] = upper_bound
                df_inverter['actual_value'] = actual_value
                df_inverter['timestamp'] = timestamp
                final_result[str(inverter.name)] = df_inverter.sort_values('timestamp').to_json(orient='records',date_format='iso')
            return final_result
    except Exception as exception:
        print str(exception)

def get_portfolio_predicted_energy_values_timeseries(starttime, endtime, plants, model_name, count_time_period, split=False):
    try:
        df_upper_bound = pd.DataFrame()
        df_lower_bound = pd.DataFrame()
        df_actual_value = pd.DataFrame()
        df_final = pd.DataFrame()
        for plant in plants:
            local_tz = pytz.timezone(plant.metadata.dataTimezone)
            starttime = local_tz.localize(starttime.replace(tzinfo=None))
            endtime = local_tz.localize(endtime.replace(tzinfo=None))
            df_upper_bound_plant = pd.DataFrame()
            df_lower_bound_plant = pd.DataFrame()
            df_actual_value_plant = pd.DataFrame()
            timestamp = []
            lower_bound = []
            upper_bound = []
            actual_value = []
            predicted_values = NewPredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                                count_time_period=count_time_period,
                                                                identifier_type='plant',
                                                                plant_slug=str(plant.slug),
                                                                identifier=str(plant.slug),
                                                                stream_name='plant_energy',
                                                                model_name=model_name,
                                                                ts__gte=starttime,
                                                                ts__lte=endtime)
            for predicted_value in predicted_values:
                timestamp.append(predicted_value.ts)
                try:
                    lower_bound_value = predicted_value.lower_bound if float(predicted_value.lower_bound)>0 else 0.0
                except:
                    lower_bound_value = 0.0
                try:
                    upper_bound_value = predicted_value.upper_bound if float(predicted_value.upper_bound)>0 else 0.0
                except:
                    upper_bound_value = 0.0
                try:
                    value = predicted_value.value if float(predicted_value.value)>0 else 0.0
                except:
                    value = 0.0
                lower_bound.append(lower_bound_value)
                upper_bound.append(upper_bound_value)
                actual_value.append(value)

            df_lower_bound_plant[str(plant.slug)+'_lower_bound'] = lower_bound
            df_lower_bound_plant['timestamp'] = timestamp
            df_upper_bound_plant[str(plant.slug)+'_upper_bound'] = upper_bound
            df_upper_bound_plant['timestamp'] = timestamp
            df_actual_value_plant[str(plant.slug)+'_actual_value'] = actual_value
            df_actual_value_plant['timestamp'] = timestamp

            if df_upper_bound.empty:
                df_upper_bound = df_upper_bound_plant
            else:
                df_upper_bound = df_upper_bound.merge(df_upper_bound_plant.drop_duplicates('timestamp'), on='timestamp', how='outer')

            if df_lower_bound.empty:
                df_lower_bound = df_lower_bound_plant
            else:
                df_lower_bound = df_lower_bound.merge(df_lower_bound_plant.drop_duplicates('timestamp'), on='timestamp', how='outer')

            if df_actual_value.empty:
                df_actual_value = df_actual_value_plant
            else:
                df_actual_value = df_actual_value.merge(df_actual_value_plant.drop_duplicates('timestamp'), on='timestamp', how='outer')
        df_upper_bound['upper_bound'] = df_upper_bound.sum(axis=1)
        df_lower_bound['lower_bound'] = df_lower_bound.sum(axis=1)
        df_actual_value['actual_value'] = df_actual_value.sum(axis=1)

        df_final['upper_bound'] = df_upper_bound['upper_bound']
        df_final['lower_bound'] = df_lower_bound['lower_bound']
        df_final['actual_value'] = df_actual_value['actual_value']
        df_final['timestamp'] = df_actual_value['timestamp']
        return df_final.sort_values('timestamp').to_json(orient='records',date_format='iso')
    except Exception as exception:
        print str(exception)

def get_inverters_stored_energy_from_power(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        final_result = {}
        for inverter in inverters:
            final_result_inverter = {}
            inverter_values_dc_energy = []
            inverter_values_ac_energy = []
            loss_values = EnergyLossTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                            count_time_period=86400,
                                                            identifier=str(inverter.sourceKey),
                                                            ts__gte=starttime,
                                                            ts__lte=endtime)
            for loss_value in loss_values:
                value_dict_dc_energy = {}
                value_dict_ac_energy = {}
                value_dict_dc_energy['value'] = float(loss_value.dc_energy_inverters) if loss_value.dc_energy_inverters else 0.0
                value_dict_dc_energy['timestamp'] = loss_value.ts
                value_dict_ac_energy['value'] = float(loss_value.ac_energy_inverters_ap) if loss_value.ac_energy_inverters_ap else 0.0
                value_dict_ac_energy['timestamp'] = loss_value.ts
                inverter_values_dc_energy.append(value_dict_dc_energy)
                inverter_values_ac_energy.append(value_dict_ac_energy)
                final_result_inverter['dc_energy'] = inverter_values_dc_energy
                final_result_inverter['ac_energy'] = inverter_values_ac_energy
            final_result[str(inverter.sourceKey)] =  final_result_inverter
        return final_result
    except Exception as exception:
        print str(exception)

def get_daily_energy_from_scada_values_date_range(starttime, endtime, plant, split=False):
    try:
        meta_source = plant.metadata.plantmetasource
        try:
            # ensure hours etc. are 0 and timestamps are with proper timezones
            start_time = starttime.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(meta_source.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = endtime.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(meta_source.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception as exc:
            start_time = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = endtime.replace(hour=0, minute=0, second=0, microsecond=0)

        # tp keep the format same as of get_minutes_.., keep it as a dict and a list
        if split:
            data = {}
        else:
            data = []

        while start_time < end_time:
            generation_date = start_time
            total_energy = 0.0
            for inverter in plant.independent_inverter_units.all():
                if split and inverter.name not in data.keys():
                        data[inverter.name] = []

                # go through generation_date + 30 days - in case there's a value, that would be there
                days_considered = 1
                inv_energy = None
                while days_considered <= 30 and inv_energy is None:
                    # print generation_date, days_considered, 'DAILY_SCADA_ENERGY_DAY_' + str(days_considered),generation_date + timedelta(days=days_considered)
                    energy_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                            stream_name='DAILY_SCADA_ENERGY_DAY_' + str(days_considered),
                                                                            timestamp_in_data__gte=generation_date + timedelta(days=days_considered),
                                                                            timestamp_in_data__lt=generation_date + timedelta(days=days_considered+1)).limit(1)
                    if len(energy_values) > 0:
                        inv_energy = float(energy_values[0].stream_value)
                        if inv_energy > 10 * inverter.actual_capacity:
                            inv_energy /= 1000.0
                        total_energy += inv_energy
                        if split:
                            data[inverter.name].append({'timestamp': generation_date.astimezone(pytz.UTC),
                                                        'energy': inv_energy})
                    else:
                        days_considered += 1
            if not split:
                data.append({'timestamp': generation_date.astimezone(pytz.UTC),
                             'energy': total_energy})
            start_time = start_time + timedelta(days=1)
        return data

    except:
        return None

def get_energy_from_scada_values(plant, split=False, est=False):
    try:
        try:
            meta_source = plant.metadata.plantmetasource
            current_time = timezone.now().astimezone(pytz.timezone(meta_source.dataTimezone))
            current_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception as exception:
            current_time = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if est:
            stream_name = 'DAILY_SCADA_ENERGY_EST_DAY_'
        else:
            stream_name = 'DAILY_SCADA_ENERGY_DAY_'
        scada_energy_null_from_plantmeta = False
        if not split:
            final_result = []
            for i in range(30):
                temp_result = {}
                energy_values = ValidDataStorageByStream.objects.filter(source_key=meta_source.sourceKey,
                                                                        stream_name=stream_name+str(i),
                                                                        timestamp_in_data__gte=current_time).limit(1)
                if len(energy_values)>0 :
                    temp_result['energy'] = float(energy_values[0].stream_value)
                    try:
                        temp_result['timestamp'] = (current_time-timedelta(days=i)).astimezone(pytz.utc)
                    except Exception as exception:
                        temp_result['timestamp'] = (current_time-timedelta(days=i))
                    final_result.append(temp_result)
            if not final_result:
                scada_energy_null_from_plantmeta = True

        if split or scada_energy_null_from_plantmeta:
            final_result = {}
            inverters = plant.independent_inverter_units.all()
            final_plant_result = {}
            for inverter in inverters:
                inverter_result = []
                for i in range(30):
                    temp_result = {}
                    energy_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                            stream_name=stream_name+str(i),
                                                                            timestamp_in_data__gte=current_time).limit(1)
                    if len(energy_values)>0:
                        temp_result['energy'] = float(energy_values[0].stream_value)
                        try:
                            temp_result['timestamp'] = (current_time-timedelta(days=i)).astimezone(pytz.utc)
                        except Exception as exception:
                            print str(exception)
                            temp_result['timestamp'] = (current_time-timedelta(days=i))

                        #calculating energy for plant
                        if temp_result['timestamp'] in final_plant_result:
                            final_plant_result[temp_result['timestamp']] += temp_result['energy']
                        else:
                            final_plant_result[temp_result['timestamp']] = temp_result['energy']

                        inverter_result.append(temp_result)
                final_result[str(inverter.sourceKey)] = inverter_result

        if scada_energy_null_from_plantmeta:
            final_result = []
            for result in final_plant_result:
                temp_result= {}
                temp_result['energy'] = float(final_plant_result[result])
                temp_result['timestamp'] = result
                final_result.append(temp_result)

        return final_result
    except Exception as exception:
        print str(exception)

# NewMods For Excel Formatting
def simpleExcelFormatting(pandasWriter, df, sheetName):
    try:
        l1 = list(df)
        d = dict()
        for item in l1:
            d[item] = item.replace('_', ' ')
        workbook = pandasWriter.book

        for worksheet in workbook.worksheets():
            if worksheet.name == sheetName:
                print "Got worksheet", worksheet.name
                w1 = worksheet
            else:
                print "sheet Name not specified"
        rows, cols = df.shape
        border_format = workbook.add_format({'border': 1})
        format3 = workbook.add_format({'bg_color': '#52AC95', 'font_color': '#FFFFFF', 'bold': True, 'border': 2})

        # Just Adding Formatting for first two rows
        cell1 = xl_rowcol_to_cell(0, 0)
        cell2 = xl_rowcol_to_cell(0, cols)
        r = cell1 + ":" + cell2
        w1.conditional_format(r, {'type': 'no_errors', 'format': format3})

        # Just Adding Border to all cells
        cell1 = xl_rowcol_to_cell(1, 1)
        cell2 = xl_rowcol_to_cell(rows, cols)
        r = cell1 + ":" + cell2
        w1.conditional_format(r, {'type': 'no_errors', 'format': border_format})
        w1.set_column(0, 0, 20)
        w1.set_row(0, 18)
        for i in range(cols):
            print i
            le = len(l1[i]) + 4
            w1.set_column(i + 1, i + 1, le)
        w1.freeze_panes(1, 1)
        return pandasWriter
    except Exception as e:
        logger.debug("Exception in simpleExcelFormatting as : "+str(e))

def merge_all_sheets(dfs):
    try:
        df = pd.DataFrame()
        df_result = pd.DataFrame()
        for k, v in dfs.iteritems():
            cl = {}
            cl['Timestamp'] = 'Timestamp'
            for col in list(v):
                # print "col name======",col
                if col=='timestamp':
                    cl[col]='Timestamp'
                elif col!='Timestamp':
                    cl[col] = (k + "$*$" + col)
            v = v.rename(columns=cl)
            if df_result.empty:
                df_result = v
            else:
                df_result = df_result.merge(v, on='Timestamp', how='outer')
        for col in list(df_result):
            if col != 'Timestamp':
                df_result[col] = df_result[col].apply(lambda x: round(x, 3) if x else x)
        df = df_result.sort_values('Timestamp')
        df = df.reset_index(drop=True)

        l1 = []
        l2 = []
        for cname in list(df):
            if cname == 'Timestamp':
                l1.append(cname)
                l2.append(cname)
            else:
                splitl = cname.split('$*$')
                l1.append(splitl[0])
                l2.append(splitl[1])
        l1 = [l.replace('_', ' ') for l in l1]
        l2 = [l.replace('_', ' ') for l in l2]

        dfindex = 'Timestamp'
        df.columns = l1
        df.loc[-1] = list(l2)
        df.index = df.index + 1  # shifting index
        df = df.sort_index()  # sorting by index
        df = df.set_index(dfindex)
        return df, l1, l2
    except Exception as e:
        logger.debug("Exception in merge_all_sheets as : "+str(e))

def merge_all_sheets2(dfs):
    try:
        df = pd.DataFrame()
        df_result = pd.DataFrame()
        for k, v in dfs.iteritems():
            cl = {}
            cl['Timestamp'] = 'Timestamp'
            for col in list(v):
                print "col name======",col
                if col=='timestamp':
                    cl[col]='Timestamp'
                elif col!='Timestamp':
                    cl[col] = (col + "$*$" + k)
            v = v.rename(columns=cl)
            if df_result.empty:
                df_result = v
            else:
                df_result = df_result.merge(v, on='Timestamp', how='outer')
        df_result = df_result.reindex_axis(sorted(df_result.columns), axis=1)

        for col in list(df_result):
            if col != 'Timestamp':
                df_result[col] = df_result[col].apply(lambda x: round(x, 3) if x else x)
        df = df_result.sort_values('Timestamp')
        df = df.reset_index(drop=True)
        l1 = []
        l2 = []
        for cname in list(df):
            if cname == 'Timestamp':
                l1.append(cname)
                l2.append(cname)
            else:
                splitl = cname.split('$*$')
                l1.append(splitl[0])
                l2.append(splitl[1])

        l1 = [l.replace('_', ' ') for l in l1]
        l2 = [l.replace('_', ' ') for l in l2]

        dfindex = 'Timestamp'
        df.columns = l1
        df.loc[-1] = list(l2)
        df.index = df.index + 1  # shifting index
        df = df.sort_index()  # sorting by index
        df = df.set_index(dfindex)
        l1.remove('Timestamp')
        l1 = ['Timestamp'] + l1
        l2.remove('Timestamp')
        l2 = ['Timestamp'] + l2
        return df, l1, l2
    except Exception as e:
        logger.debug("Exception in merge_all_sheets2 as : "+str(e))


def manipulateColumnNames(df, plant=None, dfindex=None):
    try:
        all_columns = list(df)
        inv_list = []
        l1 = []
        l2 = []
        if plant:
            inverters = plant.independent_inverter_units.all()
            for i in inverters:
                inv_name = str(i.name)
                inv_name = inv_name.replace('_', ' ')
                inv_list.append(inv_name + " (kWh)")
        for row2data in all_columns:

            row1data = ''
            row2data = row2data.replace('_', ' ')
            if row2data in inv_list:
                row1data = 'Energy Values From Inverters (kWh)'
                row2data = row2data.replace(' (kWh)', '')
            elif row2data.find('Working Hours') != -1:
                row2data = row2data.replace(' Working Hours', '')
                row1data = 'Working Hours'
            elif row2data.find('Availability') != -1:
                row2data = row2data.replace(' Availability (%)', '')
                row1data = 'Availability (%)'
            elif row2data.find('Loss (kWh)') != -1:
                row2data = row2data.replace(' Loss (kWh)', '')
                row1data = 'Loss (kWh)'
            elif row2data.find(' MAX DC POWER') != -1:
                row1data = row2data.replace(' MAX DC POWER (kW)', ' (kW)')
                row2data = 'MAX DC POWER'
            elif row2data.find(' MAX AC POWER') != -1:
                row1data = row2data.replace(' MAX AC POWER (kWh)', ' (kW)')
                row2data = 'MAX AC POWER'
            elif row2data.find('(Operational hours)') != -1:
                row1data = 'Operational Hours'
                row2data = row2data.replace(' (Operational hours)', '')
            elif row2data.find('Temp (C)') != -1:
                row1data = 'Temperature (C)'
                row2data = row2data.replace(' Temp (C)', '')
            elif row2data.find('Status Code') != -1:
                row1data = row2data.replace(' Status Code','')
                row2data = 'Status Code'
            elif row2data.find('Alarm Code') != -1:
                row1data = row2data.replace(' Alarm Code','')
                row2data = 'Alarm Code'
            elif row2data.find('No of Alarms') != -1:
                row1data = row2data.replace(' No of Alarms','')
                row2data = 'No of Alarms'
            elif row2data.find('Avg Alarm Duration') != -1:
                row1data = row2data.replace(' Avg Alarm Duration','')
                row2data = 'Avg Alarm Duration'
            else:
                row2data = row2data.replace('_', ' ')
                row1data = row2data = row2data[0].upper() + row2data[1:]
            l1.append(row1data)
            l2.append(row2data)
        if dfindex == 'Date':
            df['Date'] = pd.to_datetime(df['Date']).dt.date

        df.columns = l1
        df.loc[-1] = list(l2)
        df.index = df.index + 1  # shifting index
        df = df.sort_index()  # sorting by index
        if dfindex:
            df = df.set_index(dfindex)
        return df, l1, l2
    except Exception as e:
        logger.debug("Exception in manipulateColumnNames as : "+str(e))
        print("Exception in manipulateColumnNames as : "+str(e))

# Customised for Daily Report
def manipulateColumnNames2(df, dfindex):
    try:
        all_columns = list(df)
        l1 = []
        l2 = []
        for row2data in all_columns:
            row1data = ''
            if row2data.find(' Availability') != -1:
                row2data = row2data.replace(' Availability (%)', '')
                row1data = 'Availability (%)'
            elif row2data.find(' Loss') != -1:
                row2data = row2data.replace(' Loss (kWh)', '')
                row1data = 'Loss (kWh)'
            else:
                row1data = row2data
            l1.append(row1data)
            l2.append(row2data)
        if dfindex == 'Date':
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        df.columns = l1
        df.loc[-1] = list(l2)
        df.index = df.index + 1  # shifting index
        df = df.sort_index()  # sorting by index
        df = df.set_index(dfindex)
        return df, l1, l2
    except Exception as e:
        logger.debug("Exception in manipulateColumnNames2 as : "+str(e))

def excelConversion(pandasWriter, df, l1, l2, sheetName):
    try:
        workbook = pandasWriter.book
        for worksheet in workbook.worksheets():
            if worksheet.name == sheetName:
                print "Got worksheet", worksheet.name
                w1 = worksheet
            else:
                print "sheet Name not specified"
        merge_format = workbook.add_format(
            {'bold': True, 'border': 1, 'fg_color': '#D7E4BC', 'align': 'center', 'valign': 'vcenter'})
        merge_format.set_text_wrap()
        border_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cformat = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
        cformat.set_text_wrap()
        format3 = workbook.add_format({'bg_color': '#52AC95', 'font_color': '#FFFFFF', 'bold': True,
                                       'align': 'center', 'valign': 'vcenter', 'border': 2})
        rows, cols = df.shape
        # print "dataframe shape in rows and columns", rows,cols
        # Setting Columns Width, And Start Merging
        # Merge Type1: vertical merge
        w1.set_row(0, 22)
        # w1.set_row(1, 22)
        row1_max_cell_len = 0
        row2_max_cell_len = 0
        for i in range(cols + 1):
            celltext = l2[i]
            if celltext.strip() in ['Inverter Total Generation (kWh)', 'Insolation (kWh/m^2)', 'Max Irradiance (kW/m^2)',
                                    'MAX DC POWER', 'MAX AC POWER ']:
                w1.set_column(i, i, 15)
            elif celltext.strip() in ['Generation (kWh)', 'PR', 'PR (%)','CUF', 'CUF (%)', 'Specific Yield', 'Grid',\
                                      'Equipment', 'DC', 'Conversion', 'AC']:
                w1.set_column(i, i, 12)
            elif celltext.strip() in ['Plant Name']:
                w1.set_column(i, i, 30)
            else:
                wd = len(l2[i])
                # print "inside else-------- ",l2[i],wd
                if (wd + 4) < 10:
                    wd = 10
                elif wd > 16:
                    # print "======",l2[i], wd
                    wd = 20
                else:
                    wd = wd + 4
                w1.set_column(i, i, wd)
                # print "final width set is == ", l2[i], wd

                row1_cell_len = len(l1[i])
                row2_cell_len = len(l2[i])
                if row1_cell_len > row2_max_cell_len:
                    row1_max_cell_len = row1_cell_len
                if row2_cell_len > row2_max_cell_len:
                    row2_max_cell_len = row2_cell_len

            if l1[i] == l2[i]:
                cell1 = xl_rowcol_to_cell(0, i)
                cell2 = xl_rowcol_to_cell(1, i)
                r = (cell1 + ':' + cell2)
                w1.merge_range(r, l1[i], merge_format)
                # logger.debug("vertically merged " + l1[i])

        # Merge Type 2 : horizontal merge
        from itertools import groupby
        grouped_L = [(k, sum(1 for i in g)) for k, g in groupby(l1)]
        i = 0
        for item in grouped_L:
            if item[1] >= 2:
                cell1 = xl_rowcol_to_cell(0, i)
                i = i + item[1] - 1
                cell2 = xl_rowcol_to_cell(0, i)
                r = (cell1 + ':' + cell2)
                w1.merge_range(r, l1[i], merge_format)
            i = i + 1

        # Just Adding Formatting for first two rows
        cell1 = xl_rowcol_to_cell(0, 0)
        cell2 = xl_rowcol_to_cell(1, cols)
        r = cell1 + ":" + cell2
        # print "Range for first two rows",r
        w1.conditional_format(r, {'type': 'no_errors', 'format': format3})
        # Just Adding Border to all cells
        cell1 = xl_rowcol_to_cell(2, 0)
        cell2 = xl_rowcol_to_cell(rows, cols)
        r = cell1 + ":" + cell2
        w1.conditional_format(r, {'type': 'no_errors', 'format': border_format})

        if 'Energy Values From Inverters (kWh)' in list(df):
            c = list(df).count('Energy Values From Inverters (kWh)')
            if c <= 2:
                i = list(df).index('Energy Values From Inverters (kWh)')
                if c == 1:
                    w1.set_row(0, 32)
                    w1.set_column(i + 1, i + 1, 20)
                else:
                    w1.set_row(0, 30)
                cell1 = xl_rowcol_to_cell(0, i + 1)
                w1.write(cell1, 'Energy Values From Inverters (kWh)', merge_format)
        if row2_max_cell_len > 20:
            h = row2_max_cell_len / 18
            h = (h + 1) * 15
            if h<22:
                # logger.debug("setting default height is "+str(h))
                w1.set_row(1, 30, cformat)
            else:
                # logger.debug("setting custom height "+str(h))
                w1.set_row(1, h, cformat)
            # logger.debug("row is out of range")
        else:
            w1.set_row(1, 30, cformat)

        if l1[0] == 'Timestamp':
            w1.set_column(0, 0, 20)
        w1.freeze_panes(2, 1)
        logger.debug("excelConversion completed Successfully.")
        return pandasWriter
    except Exception as e:
        logger.debug("Exception in excelConversion as : "+str(e))

def excelNoData(pandasWriter, df, sheetName):
    try:
        workbook = pandasWriter.book
        for worksheet in workbook.worksheets():
            if worksheet.name == sheetName:
                print "Got worksheet", worksheet.name
                w1 = worksheet
            else:
                print "sheet Name not specified"

        # Create a format to use in the merged range.
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': 'yellow'})

        w1.merge_range('B2:C3', 'No Data', merge_format)

        return pandasWriter
    except Exception as e:
        logger.debug("Exception in excelNoData as : "+str(e))


# from dateutil import parser
# from datetime import timedelta
#
# def get_kwh_per_meter_square_value_all_sensors(plant_slug):
#     plant = SolarPlant.objects.get(slug=plant_slug)
#     starttime = parser.parse("2018-01-01")
#     data = {}
#
#     while starttime < parser.parse("2019-04-18"):
#         endtime = starttime + timedelta(hours=24)
#         print starttime, endtime
#         data[str(starttime)] = {}
#         try:
#             # get the irradiation values
#             if hasattr(plant, 'metadata'):
#                 if plant.slug == "gupl2":
#                     irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
#                                                                                stream_name='EXTERNAL_IRRADIATION',
#                                                                                timestamp_in_data__gte=starttime,
#                                                                                timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
#                 else:
#                     irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
#                                                                                stream_name='IRRADIATION',
#                                                                                timestamp_in_data__gte=starttime,
#                                                                                timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
#                     if len(irradiation_data) == 0:
#                         irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
#                                                                                    stream_name='EXTERNAL_IRRADIATION',
#                                                                                    timestamp_in_data__gte=starttime,
#                                                                                    timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
#                 try:
#                     idf = pd.DataFrame(irradiation_data[:], columns=['irradiance','timestamp'])
#                     idf["irradiance"] = idf["irradiance"].astype(float)
#                     idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
#                     idf['average_irradiance'] = (idf["irradiance"] + idf["irradiance"].shift(+1))/2.0
#                     idf = idf.set_index('timestamp')
#                     idf = idf.between_time(start_time='00:00', end_time='13:30')
#                     idf = idf.reset_index()
#                     idf['delta'] = idf['timestamp'] - idf['timestamp'].shift(+1)
#                     idf['delta'] = idf['delta'] / np.timedelta64(1, 'h')
#                     idf = idf[idf['delta'] < 0.6]
#                     idf['values'] = idf['average_irradiance'] * idf['delta']
#                     print starttime, endtime, idf['values'].sum()
#                     data[str(starttime)]['IRRADIATION_1'] = idf['values'].sum()
#                 except Exception as exception:
#                     starttime = endtime
#                     print str(exception)
#                     continue
#         except Exception as exception:
#             starttime = endtime
#             print(str(exception))
#             continue
#
#         try:
#             # get the irradiation values
#             if hasattr(plant, 'metadata'):
#                 if plant.slug == "gupl2":
#                     irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
#                                                                                stream_name='EXTERNAL_IRRADIATION',
#                                                                                timestamp_in_data__gte=starttime,
#                                                                                timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
#                 else:
#                     irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
#                                                                                stream_name='IRRADIATION_2',
#                                                                                timestamp_in_data__gte=starttime,
#                                                                                timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
#                     if len(irradiation_data) == 0:
#                         irradiation_data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
#                                                                                    stream_name='EXTERNAL_IRRADIATION',
#                                                                                    timestamp_in_data__gte=starttime,
#                                                                                    timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
#                 try:
#                     idf = pd.DataFrame(irradiation_data[:], columns=['irradiance','timestamp'])
#                     idf["irradiance"] = idf["irradiance"].astype(float)
#                     idf['timestamp'] = idf['timestamp'].apply(lambda x: x.replace(second=0, microsecond=0))
#                     idf['average_irradiance'] = (idf["irradiance"] + idf["irradiance"].shift(+1))/2.0
#                     idf = idf.set_index('timestamp')
#                     idf = idf.between_time(start_time='00:00', end_time='13:30')
#                     idf = idf.reset_index()
#                     idf['delta'] = idf['timestamp'] - idf['timestamp'].shift(+1)
#                     idf['delta'] = idf['delta'] / np.timedelta64(1, 'h')
#                     idf = idf[idf['delta'] < 0.6]
#                     idf['values'] = idf['average_irradiance'] * idf['delta']
#                     print starttime, endtime, idf['values'].sum()
#                     data[str(starttime)]['IRRADIATION_2'] = idf['values'].sum()
#                 except Exception as exception:
#                     starttime = endtime
#                     print str(exception)
#                     continue
#         except Exception as exception:
#             starttime = endtime
#             print(str(exception))
#             continue
#
#         starttime = endtime
#         print starttime, endtime, starttime < endtime
#
#     return data
#
