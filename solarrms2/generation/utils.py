from dataglen.models import ValidDataStorageByStream
from solarrms.settings import PLANT_POWER_STREAM, ENERGY_METER_STREAM_UNITS,\
    ENERGY_METER_STREAM_UNIT_FACTOR, ENERGY_CALCULATION_STREAMS, INVERTER_ENERGY_FIELD, \
    INVERTER_POWER_FIELD, INVERTER_TOTAL_ENERGY_FIELD, VALID_ENERGY_CALCULATION_DELTA_MINUTES, \
    PLANT_ENERGY_STREAM
import math, numpy as np, pandas as pd
import multiprocessing as mp
import time
import multiprocessing.pool
from django.contrib.auth.models import User
from dataglen.models import ValidDataStorageByStream, InvalidDataStorageBySource
from monitoring.models import SourceMonitoring
from django.utils import timezone
from kutbill.settings import HOST_IP

class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)


class Pool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess


# device
def a((key, stream)):
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.query import dict_factory
    from cassandra.cqlengine import connection
    from cassandra.cqlengine import models

    auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
    cassandra_cluster = Cluster([HOST_IP],
                                auth_provider=auth_provider, protocol_version=3)

    cassandra_session = cassandra_cluster.connect()
    cassandra_session.row_factory = dict_factory
    connection.set_session(cassandra_session)
    models.DEFAULT_KEYSPACE = 'dataglen_data'
    data = ValidDataStorageByStream.objects.all()
    return len(data)


def a2(x):
    time.sleep(1)
    return x*x*x

# plant
def b(x_list):
    pool = Pool(processes=(mp.cpu_count() - 1))
    results = pool.map(a, x_list)
    pool.close()
    pool.join()
    return results

def d(x_list):
    pool = Pool(processes=(mp.cpu_count() - 1))
    results = pool.map(a2, x_list)
    pool.close()
    pool.join()
    return results


# client
def c(list_of_x_lists):
    pool = Pool(processes=(mp.cpu_count() - 1))
    results = pool.map(b, list_of_x_lists)
    pool.close()
    pool.join()
    return results

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

def get_inverter_power((binning_interval, inverter_key, stream, starttime, endtime)):
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.query import dict_factory
    from cassandra.cqlengine import connection
    from cassandra.cqlengine import models

    t1 = timezone.now()
    auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
    cassandra_cluster = Cluster([HOST_IP],
                                auth_provider=auth_provider, protocol_version=3)

    cassandra_session = cassandra_cluster.connect()
    cassandra_session.row_factory = dict_factory
    connection.set_session(cassandra_session)
    models.DEFAULT_KEYSPACE = 'dataglen_data'
    t2 = timezone.now()

    timestamps = []
    values = []
    try:
        inverter_data = ValidDataStorageByStream.objects.filter(source_key=inverter_key,
                                                                stream_name=stream,
                                                                timestamp_in_data__gt=starttime,
                                                                timestamp_in_data__lte=endtime).limit(0).order_by(
            'timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
        if binning_interval:
            for data_point in inverter_data:
                timestamps.append(data_point[1].replace(minute=data_point[1].minute - data_point[1].minute % (
                int(binning_interval) / 60),
                second=0,
                microsecond=0))
                values.append(float(data_point[0]))
        else:
            for data_point in inverter_data:
                timestamps.append(data_point[1].replace(second=0, microsecond=0))
                values.append(float(data_point[0]))
    except Exception as exc:
        print str(exc)

    from django import db
    db.connections.close_all()

    return (inverter_key, values, timestamps)


def get_plant_power_new(starttime, endtime, plant, pandas_df=False, energy=False, split=False, meter_energy=True):
    t1 = timezone.now()
    if (split is False) and hasattr(plant, 'metadata') and plant.metadata.sending_aggregated_power:
        data = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.sourceKey,
                                                       stream_name=PLANT_POWER_STREAM,
                                                       timestamp_in_data__gt=starttime,
                                                       timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

        values = [{'power': entry[0], 'timestamp':entry[1].replace(second=0, microsecond=0)} for entry in data]
        return values

    elif hasattr(plant, 'metadata') and plant.metadata.meter_power and (energy is False):
        df = pd.DataFrame()
        meter = plant.energy_meters.all()[0]
        data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                       stream_name='WATT_TOTAL',
                                                       timestamp_in_data__gt=starttime,
                                                       timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')

        sum = []
        timestamps = []
        for data_point in data:
            sum.append(float(data_point[0]))
            timestamps.append(data_point[1].replace(second=0, microsecond=0))
        df['sum'] = sum
        df['timestamp'] = timestamps
        if pandas_df:
            return df
        else:
            timestamps = df['timestamp'].tolist()
            power_data = df.sum(axis=1)
            values = []
            stream_name = 'power'
            for i in range(df.shape[0]):
                values.append({stream_name: power_data.values[i],
                               'timestamp': timestamps[i].to_datetime()})
            return values


    elif len(plant.energy_meters.all()) > 0 and energy and meter_energy:
        df_list = []
        order = ['timestamp']
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

        for meter in plant.energy_meters.all().filter(isActive=True).filter(energy_calculation=True):
            try:
                meter_data = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                     stream_name=stream,
                                                                     timestamp_in_data__gt=starttime,
                                                                     timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value', 'timestamp_in_data')
                timestamps = []
                values = []
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
                #logger.debug(str(exc))
                continue
        try:
            if len(df_list) >= 2:
                results = df_list[0]
                for i in range(1, len(df_list)):
                    results = results.merge(df_list[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                    updated_results = results
                    results = updated_results
            else:
                results = df_list[0]

            sorted_results = results.sort(['timestamp'])
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
        args = []
        print  timezone.now()
        for inverter in plant.independent_inverter_units.all().filter(isActive=True):
            args.append((plant.metadata.plantmetasource.binning_interval, inverter.sourceKey, stream, starttime, endtime))
        pool = mp.Pool(processes=(mp.cpu_count()-1))
        results = pool.map(get_inverter_power, args)
        pool.close()
        pool.join()
        df_result  = pd.DataFrame()
        print timezone.now()
        for entry in results:
            df_temp = pd.DataFrame()
            try:
                # df_list.append(pd.DataFrame({entry[0].name: entry[1],
                #                          'timestamp': pd.to_datetime(entry[2])}))
                # order.append(entry[0].name)
                # print order
                df_temp['timestamp'] = entry[2]
                df_temp[entry[0]] = entry[1]
                if df_result.empty:
                    df_result = df_temp
                else:
                    df_result = df_result.merge(df_temp, on='timestamp', how='outer')
            except Exception as exc:
                print str(exc)
                continue
        t2 = timezone.now()
        print t2-t1
        return df_result

        # try:
        #     if len(df_list) >= 2:
        #         results = df_list[0]
        #         for i in range(1, len(df_list)):
        #             results = results.merge(df_list[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
        #             updated_results = results
        #             results = updated_results
        #     elif len(df_list)>0:
        #         results = df_list[0]
        #     else:
        #         pass
        #
        #     sorted_results = results.sort(['timestamp'])
        #     results = sorted_results
        #     results = results.ffill(limit=1)
        #
        #     # if pandas_df, sum up the value and send back as more operations might be pending
        #     if pandas_df:
        #         results["sum"] = results.sum(axis=1)
        #         return results
        #
        #     # otherwise, prepare the final result
        #     timestamps = results['timestamp'].tolist()
        #     power_data = results.sum(axis=1)
        #     values = []
        #     # stream name
        #     stream_name = 'power'
        #     if energy:
        #         stream_name = 'energy'
        #     for i in range(results.shape[0]):
        #         values.append({stream_name: power_data.values[i],
        #                        'timestamp': timestamps[i].to_datetime()})
        #     return values
        #
        # except Exception as exc:
        #     #comments = generate_exception_comments(sys._getframe().f_code.co_name)
        #     #logger.debug(comments)
        #     print str(exc)
        #     return []

# def get client_power(client, starttime, endtime)
#
# def power_feature(client, plant, inverter, startime, endtime, aggregation, scope):
#     if scope == "inverter":
#         get_inverter_power
#     elif scope == "plant":
#         get_plant_power()


