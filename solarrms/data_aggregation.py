from solarrms.models import SolarPlant, SolarField
from dataglen.models import Field, ValidDataStorageByStream
import pandas as pd
from solarrms.solar_reports import DEFAULT_STREAM_UNIT
from dataglen.models import Sensor
import datetime
from solarrms.settings import IRRADIATION_UNITS, IRRADIATION_UNITS_FACTOR
import numpy as np
import logging

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

# get the average value in the specified period for a given streams of any source

def get_average_value_specified_interval(starttime, endtime, source, streams_list, aggregator, aggregation_period):
    try:
        df_final = pd.DataFrame()
        final_values = {}
        for stream_name in streams_list:
            try:
                df_list_stream = []
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
                                                                      timestamp_in_data__lte = endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                if stream.streamDataType not in ['FLOAT']:
                    continue
                else:
                    values = [item[0] for item in source_data]
                    timestamps = [item[1].replace(second=0, microsecond=0) for item in source_data]

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
                        df_new = pd.merge(df_final, results_stream_temp, on='timestamp', how='outer')
                        df_final = df_new
            except:
                continue

        if aggregator == 'MINUTE':
            aggregation = str(aggregation_period) + 'Min'
        elif aggregator == 'DAY':
            aggregation = str(aggregation_period) + 'D'
        elif aggregator == 'MONTH':
            aggregation = str(aggregation_period) + 'M'
        else:
            aggregation = '60Min'

        if not df_final.empty:
            final_stream_values = {}
            df_final = df_final.set_index('timestamp')
            column_names = df_final.columns.values.tolist()
            grouped_mean = df_final.astype(float).groupby(pd.TimeGrouper(aggregation))
            mean_grouped_values = grouped_mean.mean()
            for column in column_names:
                data = []
                for key, value in mean_grouped_values[column].iteritems():
                    try:
                        data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'mean_value': value})
                    except:
                        data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': value})
                final_stream_values[str(column).split("#")[1]] = data
            final_values[str(source.name)] = final_stream_values
        return final_values
    except Exception as exception:
        print str(exception)
        return {}

# get the minimum value in the specified period for a given streams of any source

def get_minimum_value_specified_interval(starttime, endtime, source, streams_list, aggregator, aggregation_period):
    try:
        df_final = pd.DataFrame()
        final_values = {}
        for stream_name in streams_list:
            try:
                df_list_stream = []
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
                                                                      timestamp_in_data__lte = endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                if stream.streamDataType not in ['FLOAT']:
                    continue
                else:
                    values = [item[0] for item in source_data]
                    timestamps = [item[1].replace(second=0, microsecond=0) for item in source_data]

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
                        df_new = pd.merge(df_final, results_stream_temp, on='timestamp', how='outer')
                        df_final = df_new
            except:
                continue

        if aggregator == 'MINUTE':
            aggregation = str(aggregation_period) + 'Min'
        elif aggregator == 'DAY':
            aggregation = str(aggregation_period) + 'D'
        elif aggregator == 'MONTH':
            aggregation = str(aggregation_period) + 'M'
        else:
            aggregation = '60Min'

        if not df_final.empty:
            final_stream_values = {}
            df_final = df_final.set_index('timestamp')
            column_names = df_final.columns.values.tolist()
            grouped_min = df_final.groupby(pd.TimeGrouper(aggregation))
            min_grouped_values = grouped_min.min()
            for column in column_names:
                data = []
                for key, value in min_grouped_values[column].iteritems():
                    try:
                        data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'min_value': value})
                    except:
                        data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': value})
                final_stream_values[str(column).split("#")[1]] = data
            final_values[source.name] = final_stream_values
        return final_values
    except Exception as exception:
        print str(exception)
        return {}


# get the maximum value in the specified period for a given streams of any source

def get_maximum_value_specified_interval(starttime, endtime, source, streams_list, aggregator, aggregation_period):
    try:
        df_final = pd.DataFrame()
        final_values = {}
        for stream_name in streams_list:
            try:
                df_list_stream = []
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
                                                                      timestamp_in_data__lte = endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                if stream.streamDataType not in ['FLOAT']:
                    continue
                else:
                    values = [item[0] for item in source_data]
                    timestamps = [item[1].replace(second=0, microsecond=0) for item in source_data]

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
                        df_new = pd.merge(df_final, results_stream_temp, on='timestamp', how='outer')
                        df_final = df_new
            except:
                continue

        if aggregator == 'MINUTE':
            aggregation = str(aggregation_period) + 'Min'
        elif aggregator == 'DAY':
            aggregation = str(aggregation_period) + 'D'
        elif aggregator == 'MONTH':
            aggregation = str(aggregation_period) + 'M'
        else:
            aggregation = '60Min'

        if not df_final.empty:
            final_stream_values = {}
            df_final = df_final.set_index('timestamp')
            column_names = df_final.columns.values.tolist()
            grouped_max = df_final.groupby(pd.TimeGrouper(aggregation))
            max_grouped_values = grouped_max.max()
            for column in column_names:
                data = []
                for key, value in max_grouped_values[column].iteritems():
                    try:
                        data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'max_value': value})
                    except:
                        data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': value})
                final_stream_values[str(column).split("#")[1]] = data
            final_values[source.name] = final_stream_values
        return final_values
    except Exception as exception:
        print str(exception)
        return {}

def get_multiple_sources_multiple_streams_data_merge_pandas_aggregation(starttime, endtime, sources_stream_association,
                                                                        delta, plant, aggregator, aggregation_period,
                                                                        aggregation_type='mean'):
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
                                                                              timestamp_in_data__lte = endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')


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
                                df_new = pd.merge(df_final, results_stream_temp, on='timestamp', how='outer')
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
                    filling_timestamp.append(df_missing.iloc[index]['timestamp']- datetime.timedelta(minutes=((df_missing.iloc[index]['ts'] / np.timedelta64(1, 'm'))/2)))
                except Exception as exception:
                    print str(exception)
                    continue

            df_filling['timestamp'] = filling_timestamp
            df_final = df_final.merge(df_filling, on='timestamp', how='outer')
            df_final = df_final.sort('timestamp')
            df_final = df_final.where(pd.notnull(df_final), None)

            df_energy = pd.DataFrame()
            df_final_energy = pd.DataFrame()
            column_names = df_final.columns.values.tolist()
            for column in column_names:
                if str(column).endswith("Wh"):
                    df_energy[column] = df_final[column]
            df_energy['timestamp'] = df_final['timestamp']

            df_energy_columns = df_energy.columns.values.tolist()

            for column in df_energy_columns:
                if column != 'timestamp':
                    df_final_energy[column] = df_energy[column].astype(float).diff()
            df_final_energy['timestamp'] = df_energy['timestamp']
            df_final_temp = pd.DataFrame()
            energy_column_names = df_final_energy.columns.values.tolist()
            column_names = df_final.columns.values.tolist()
            for column in column_names:
                if column not in energy_column_names:
                    df_final_temp[column] = df_final[column]
            df_final_temp['timestamp'] = df_final['timestamp']

            #df_final = df_final_temp.merge(df_final_energy, on='timestamp', how='outer')

            # aggregation period
            if aggregator == 'MINUTE':
                aggregation = str(aggregation_period) + 'Min'
            elif aggregator == 'DAY':
                aggregation = str(aggregation_period) + 'D'
            elif aggregator == 'MONTH':
                aggregation = str(aggregation_period) + 'M'
            else:
                aggregation = '1D'

            #df_final = df_final.set_index('timestamp')
            df_final_temp = df_final_temp.set_index('timestamp')
            df_final_energy = df_final_energy.set_index('timestamp')

            del(df_final['ts'])
            del(df_final_temp['ts'])

            if not df_final_temp.empty:
                df_final_temp = df_final_temp.astype(float).groupby(pd.TimeGrouper(aggregation))
            if not df_final_energy.empty:
                df_final_energy = df_final_energy.astype(float).groupby(pd.TimeGrouper(aggregation))

            # aggregation type
            if aggregation_type == 'min':
                df_final_temp = df_final_temp.min()
                df_final_energy = df_final_energy.min()
            elif aggregation_type == 'max':
                df_final_temp = df_final_temp.max()
                df_final_energy = df_final_energy.max()
            else:
                df_final_temp = df_final_temp.mean()
                df_final_energy = df_final_energy.sum()

            df_final_temp = df_final_temp.reset_index()
            df_final_energy = df_final_energy.reset_index()
            if not df_final_temp.empty and not df_final_energy.empty:
                df_final = df_final_temp.merge(df_final_energy, on='timestamp',how='outer')
            elif not df_final_temp.empty:
                df_final = df_final_temp
            else:
                df_final = df_final_energy
            column_names = df_final.columns.values.tolist()
            timestamp_list = df_final['timestamp'].tolist()
            timestamp_list = [x.strftime("%Y-%m-%dT%H:%M:%SZ") for x in timestamp_list]
            # print "before", timestamp_list
            # try:
            #     timestamp_list = [pd.to_datetime(x).tz_localize(plant.metadata.plantmetasource.dataTimezone).tz_convert('UTC').strftime("%Y-%m-%dT%H:%M:%SZ") for x in timestamp_list]
            # except:
            #     timestamp_list = [pd.to_datetime(x).tz_convert(plant.metadata.plantmetasource.dataTimezone).strftime("%Y-%m-%dT%H:%M:%SZ") for x in timestamp_list]
            # print "after", timestamp_list
            for column in column_names:
                if column != 'ts':
                    try:
                        df_column_list_values = df_final[column].tolist()
                        df_column_list_values_without_nan = [x if not np.isnan(x) else None for x in df_column_list_values]
                        name = column.split('#')
                        device_name = name[0]
                        stream_name = name[1]
                        stream_unit = name[2]
                        stream_dict = {}
                        stream_dict_list = []
                        stream_dict['x'] = timestamp_list
                        stream_dict['y'] = df_column_list_values_without_nan
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


EXCLUDE_STREAMS = ['LIVE', 'AGGREGATED', 'TIMESTAMP', 'AGGREGATED_START_TIME', 'AGGREGATED_END_TIME', 'AGGREGATED_COUNT']
def get_single_device_multiple_streams_data_aggregated(starttime, endtime, plant, source, streams_list,
                                                       aggregator, aggregation_period, aggregation_type='mean'):
    try:
        df_results_stream = pd.DataFrame()
        for stream in streams_list:
            df_list_stream = []
            if stream not in EXCLUDE_STREAMS:
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
                    if stream_object.streamDataType != 'STRING':
                        values_stream.append(float(data_point[0]))
                    else:
                        values_stream.append(data_point[0])
                try:
                    stream_unit = str(stream_object.streamDataUnit) if (stream_object and stream_object.streamDataUnit) else DEFAULT_STREAM_UNIT[str(stream_object.name)]
                except:
                    stream_unit = "NA"
                df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),
                                                    str(stream_display_name)+'('+str(stream_unit)+')': values_stream}))

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
            df_energy = pd.DataFrame()
            df_final_energy = pd.DataFrame()
            column_names = df_results_stream.columns.values.tolist()
            for column in column_names:
                if str(column).endswith('Wh)'):
                    df_energy[column] = df_results_stream[column]

            df_energy['timestamp'] = df_results_stream['timestamp']
            df_energy_columns = df_energy.columns.values.tolist()

            for column in df_energy_columns:
                if column != 'timestamp':
                    df_final_energy[column] = df_energy[column].astype(float).diff()
            df_final_energy['timestamp'] = df_energy['timestamp']

            df_results_stream_temp = pd.DataFrame()
            energy_column_names = df_final_energy.columns.values.tolist()
            column_names = df_results_stream.columns.values.tolist()

            df_results_stream_temp['timestamp'] = df_results_stream['timestamp']
            for column in column_names:
                if column not in energy_column_names:
                    df_results_stream_temp[column] = df_results_stream[column]

            # aggregation period
            if aggregator == 'MINUTE':
                aggregation = str(aggregation_period) + 'Min'
            elif aggregator == 'DAY':
                aggregation = str(aggregation_period) + 'D'
            elif aggregator == 'MONTH':
                aggregation = str(aggregation_period) + 'M'
            else:
                aggregation = '1D'

            df_results_stream_temp = df_results_stream_temp.set_index('timestamp')
            df_final_energy = df_final_energy.set_index('timestamp')

            if not df_results_stream_temp.empty:
                df_results_stream_temp = df_results_stream_temp.astype(float).groupby(pd.TimeGrouper(aggregation))
            if not df_final_energy.empty:
                df_final_energy = df_final_energy.astype(float).groupby(pd.TimeGrouper(aggregation))

            # aggregation type
            if aggregation_type == 'min':
                df_results_stream_temp = df_results_stream_temp.min()
                df_final_energy = df_final_energy.min()
            elif aggregation_type == 'max':
                df_results_stream_temp = df_results_stream_temp.max()
                df_final_energy = df_final_energy.max()
            else:
                df_results_stream_temp = df_results_stream_temp.mean()
                df_final_energy = df_final_energy.sum()

            df_results_stream_temp = df_results_stream_temp.reset_index()
            df_final_energy = df_final_energy.reset_index()
            if not df_results_stream_temp.empty and not df_final_energy.empty:
                df_results_stream = df_results_stream_temp.merge(df_final_energy, on='timestamp',how='outer')
            elif not df_results_stream_temp.empty:
                df_results_stream = df_results_stream_temp
            else:
                df_results_stream = df_final_energy

            df_results_stream = df_results_stream.sort('timestamp')
            final_timestamp = df_results_stream['timestamp']
            df_results_stream.drop(labels=['timestamp'], axis=1,inplace = True)
            df_results_stream.insert(0, 'Timestamp', final_timestamp)
            df_results_stream.index = np.arange(1, len(df_results_stream) + 1)
        return df_results_stream
    except Exception as exception:
        print(str(exception))
        return df_results_stream


# made by Upendra Jan2018
# Used when for single Single Stream Name on multiple SourceKeys
# for example: "ACTIVE_POWER":["3klk15PkzALckD5","BzrHE4UdAk0uHPn"]

EXCLUDE_STREAMS = ['LIVE', 'AGGREGATED', 'TIMESTAMP', 'AGGREGATED_START_TIME', 'AGGREGATED_END_TIME',
                   'AGGREGATED_COUNT']
def get_single_stream_multiple_sources_data_aggregated(starttime, endtime, plant, sources_list, stream,
                                                         aggregator, aggregation_period, aggregation_type='mean'):
    try:
        df_results_stream = pd.DataFrame()
        for source in sources_list:
            df_list_stream = []
            if stream not in EXCLUDE_STREAMS:
                try:
                    stream_object = SolarField.objects.get(source=source, displayName=stream)
                    stream = stream_object.name
                    stream_display_name = str(stream_object.displayName)
                except:
                    stream_object = Field.objects.get(source=source, name=stream)
                    stream = stream
                    stream_display_name = stream
                stream_values = ValidDataStorageByStream.objects.filter(source_key=source,
                                                                        stream_name=stream,
                                                                        timestamp_in_data__gte=starttime,
                                                                        timestamp_in_data__lte=endtime
                                                                        ).limit(0).order_by(
                    'timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                values_stream = []
                timestamp_stream = []
                for data_point in stream_values:
                    timestamp_stream.append(data_point[1].replace(second=0, microsecond=0))
                    if stream_object.streamDataType != 'STRING':
                        values_stream.append(float(data_point[0]))
                    else:
                        values_stream.append(data_point[0])
                try:
                    stream_unit = str(stream_object.streamDataUnit) if (
                    stream_object and stream_object.streamDataUnit) else DEFAULT_STREAM_UNIT[str(stream_object.name)]
                except:
                    stream_unit = "NA"
                # df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),
                #                                    str(stream_display_name)+'('+str(stream_unit)+')': values_stream}))
                s = Sensor.objects.get(sourceKey=source)
                df_list_stream.append(pd.DataFrame({'timestamp': pd.to_datetime(timestamp_stream),
                                                    s.name: values_stream}))

                if len(df_list_stream) > 0:
                    results_stream_temp = df_list_stream[0]
                    for i in range(1, len(df_list_stream)):
                        results_stream_temp = results_stream_temp.merge(df_list_stream[i].drop_duplicates('timestamp'),
                                                                        how='outer', on='timestamp')
                    if df_results_stream.empty:
                        df_results_stream = results_stream_temp
                    else:
                        df_new = pd.merge(df_results_stream, results_stream_temp.drop_duplicates('timestamp'),
                                          on='timestamp', how='outer')
                        df_results_stream = df_new

        if not df_results_stream.empty:
            df_energy = pd.DataFrame()
            df_final_energy = pd.DataFrame()
            column_names = df_results_stream.columns.values.tolist()
            for column in column_names:
                if str(column).endswith('Wh)'):
                    df_energy[column] = df_results_stream[column]

            df_energy['timestamp'] = df_results_stream['timestamp']
            df_energy_columns = df_energy.columns.values.tolist()

            for column in df_energy_columns:
                if column != 'timestamp':
                    df_final_energy[column] = df_energy[column].astype(float).diff()
            df_final_energy['timestamp'] = df_energy['timestamp']

            df_results_stream_temp = pd.DataFrame()
            energy_column_names = df_final_energy.columns.values.tolist()
            column_names = df_results_stream.columns.values.tolist()

            df_results_stream_temp['timestamp'] = df_results_stream['timestamp']
            for column in column_names:
                if column not in energy_column_names:
                    df_results_stream_temp[column] = df_results_stream[column]

            # aggregation period
            if aggregator == 'MINUTE':
                aggregation = str(aggregation_period) + 'Min'
            elif aggregator == 'DAY':
                aggregation = str(aggregation_period) + 'D'
            elif aggregator == 'MONTH':
                aggregation = str(aggregation_period) + 'M'
            else:
                aggregation = '1D'

            df_results_stream_temp = df_results_stream_temp.set_index('timestamp')
            df_final_energy = df_final_energy.set_index('timestamp')

            if not df_results_stream_temp.empty:
                df_results_stream_temp = df_results_stream_temp.astype(float).groupby(pd.TimeGrouper(aggregation))
            if not df_final_energy.empty:
                df_final_energy = df_final_energy.astype(float).groupby(pd.TimeGrouper(aggregation))

            # aggregation type
            if aggregation_type == 'min':
                df_results_stream_temp = df_results_stream_temp.min()
                df_final_energy = df_final_energy.min()
            elif aggregation_type == 'max':
                df_results_stream_temp = df_results_stream_temp.max()
                df_final_energy = df_final_energy.max()
            else:
                df_results_stream_temp = df_results_stream_temp.mean()
                df_final_energy = df_final_energy.sum()

            df_results_stream_temp = df_results_stream_temp.reset_index()
            df_final_energy = df_final_energy.reset_index()
            if not df_results_stream_temp.empty and not df_final_energy.empty:
                df_results_stream = df_results_stream_temp.merge(df_final_energy, on='timestamp', how='outer')
            elif not df_results_stream_temp.empty:
                df_results_stream = df_results_stream_temp
            else:
                df_results_stream = df_final_energy

            df_results_stream = df_results_stream.sort_values('timestamp')
            final_timestamp = df_results_stream['timestamp']
            df_results_stream.drop(labels=['timestamp'], axis=1, inplace=True)
            df_results_stream.insert(0, 'Timestamp', final_timestamp)
            df_results_stream.index = np.arange(1, len(df_results_stream) + 1)
        return df_results_stream
    except Exception as exception:
        print(str(exception))
        return df_results_stream


