from multiprocessing import cpu_count
from solarrms.models import InverterStatusMappings, AJB, IndependentInverter, AJBStatusMappings
from monitoring.views import get_user_data_monitoring_status
from dataglen.models import ValidDataStorageByStream
from datetime import datetime, timedelta
from solarrms.models import InverterErrorCodes
from django.conf import settings

import logging, pytz
import multiprocessing.pool


INVERTER_LIM = 20
logger = logging.getLogger('widgets.models')
logger.setLevel(logging.DEBUG)

class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)


class Pool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess


def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

def get_ajbs_live_status((plant, ajbs)):
    try:
        print "Getting cassandra"
        # restart django's connection with mysql
        from django.db import connection
        try:
            if connection.connection:
                connection.connection.close()
            connection.connection = None
        except:
            pass

        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider
        from cassandra.query import dict_factory
        from cassandra.cqlengine import connection
        from cassandra.cqlengine import models

        auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
        cassandra_cluster = Cluster(settings.HOST_IP,
                                    auth_provider=auth_provider, protocol_version=3)

        cassandra_session = cassandra_cluster.connect()
        cassandra_session.row_factory = dict_factory
        connection.set_session(cassandra_session)
        models.DEFAULT_KEYSPACE = 'dataglen_data'

        result = {}

        # find the monitoring status of these ajbs
        ajb_keys =  [ajb.sourceKey for ajb in ajbs]
        stats = get_user_data_monitoring_status(AJB.objects.filter(sourceKey__in=ajb_keys))
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
        else:
            active_alive_valid = None
            active_dead = None

        ajb_data = []
        for ajb in ajbs:
            try:

                try:
                    timeout_interval = plant.metadata.plantmetasource.data_frequency if plant.metadata.plantmetasource and \
                                                                                        plant.metadata.plantmetasource.data_frequency \
                        else ajb.timeoutInterval
                except:
                    try:
                        timeout_interval = ajb.timeoutInterval
                    except:
                        timeout_interval = 2700

                data = {}

                # get the connection status
                # if active_alive_valid:
                if ajb.sourceKey in active_alive_valid:
                    connected = "connected"
                elif ajb.sourceKey in active_dead:
                    connected = "disconnected"
                else:
                    connected = "unknown"
                # else:
                #     connected = "unknown"

                if connected == "connected":
                    # get current power
                    try:
                        last_power = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                             stream_name='POWER',
                                                                             timestamp_in_data__lte=datetime.now(
                                                                                 pytz.timezone(
                                                                                     'Asia/Kolkata')) - timedelta(
                                                                                 seconds=120),
                                                                             timestamp_in_data__gte=datetime.now(
                                                                                 pytz.timezone(
                                                                                     'Asia/Kolkata')) - timedelta(
                                                                                 seconds=timeout_interval)).limit(1)
                        last_power = float("{0:.2f}".format(float(float(last_power[0].stream_value))))
                    except Exception as exc:
                        logger.exception("last_power")
                        logger.debug(str(exc))
                        last_power = 0.0
                        #connected = "disconnected"

                    # get current TOTAL CURRENT
                    try:
                        last_current = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                               stream_name='CURRENT',
                                                                               timestamp_in_data__lte=datetime.now(
                                                                                   pytz.timezone(
                                                                                       'Asia/Kolkata')) - timedelta(
                                                                                   seconds=120),
                                                                               timestamp_in_data__gte=datetime.now(
                                                                                   pytz.timezone(
                                                                                       'Asia/Kolkata')) - timedelta(
                                                                                   seconds=timeout_interval)).limit(1)
                        last_current = float("{0:.2f}".format(float(last_current[0].stream_value)))
                    except Exception as exc:
                        logger.exception("last_current")
                        logger.debug(exc)
                        last_current = 0.0
                        #connected = "disconnected"

                    # get current voltage
                    try:
                        last_voltage = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                               stream_name='VOLTAGE',
                                                                               timestamp_in_data__lte=datetime.now(
                                                                                   pytz.timezone(
                                                                                       'Asia/Kolkata')) - timedelta(
                                                                                   seconds=120),
                                                                               timestamp_in_data__gte=datetime.now(
                                                                                   pytz.timezone(
                                                                                       'Asia/Kolkata')) - timedelta(
                                                                                   seconds=timeout_interval)).limit(1)
                        last_voltage = float("{0:.2f}".format(float(last_voltage[0].stream_value)))
                    except Exception as exc:
                        logger.exception("last_voltage#" + str(ajb.name) + "#" + str(timeout_interval))
                        logger.debug(exc)
                        last_voltage = 0.0
                        #connected = "disconnected"
                else:
                    last_power = 0.0
                    last_current = 0.0
                    last_voltage = 0.0

                data['name'] = str(ajb.name)
                data['power'] = last_power
                data['current'] = last_current
                data['voltage'] = last_voltage
                data['connected'] = connected
                data['key'] = str(ajb.sourceKey)
                data['inverter_name'] = str(ajb.independent_inverter.name)

                if len(ajb.solar_groups.all()) != 0:
                    data['solar_group'] = str(ajb.solar_groups.all()[0].name)
                else:
                    data['solar_group'] = "NA"

                # get the ajb spd status
                latest_ajb_spd_status = []
                try:
                    ajb_spd_status = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                             stream_name='DI_STATUS_4').limit(1)
                    for i in range(len(ajb_spd_status)):
                        spd_status_values = {}
                        try:
                            ajb_spd_status_description = AJBStatusMappings.objects.get(plant=plant,
                                                                                       stream_name='DI_STATUS_4',
                                                                                       status_code=float(
                                                                                           ajb_spd_status[
                                                                                               i].stream_value))
                            spd_status_values['spd_status'] = ajb_spd_status_description.status_description
                        except:
                            spd_status_values['spd_status'] = ajb_spd_status[i].stream_value
                        spd_status_values['timestamp'] = ajb_spd_status[i].timestamp_in_data
                        latest_ajb_spd_status.append(spd_status_values)
                except Exception as exc:
                    logger.debug(exc)
                    latest_ajb_spd_status = []

                # get the ajb spd status
                latest_ajb_dc_isolator_status = []
                try:
                    ajb_dc_isolator_status = ValidDataStorageByStream.objects.filter(
                        source_key=ajb.sourceKey,
                        stream_name='DI_STATUS_3').limit(1)
                    for i in range(len(ajb_dc_isolator_status)):
                        dc_isolator_status_values = {}
                        try:
                            ajb_dc_isolator_status_description = AJBStatusMappings.objects.get(plant=plant,
                                                                                               stream_name='DI_STATUS_3',
                                                                                               status_code=float(
                                                                                                   ajb_dc_isolator_status[
                                                                                                       i].stream_value))
                            dc_isolator_status_values[
                                'dc_isolator_status'] = ajb_dc_isolator_status_description.status_description
                        except:
                            dc_isolator_status_values['dc_isolator_status'] = ajb_dc_isolator_status[
                                i].stream_value
                        dc_isolator_status_values['timestamp'] = ajb_dc_isolator_status[i].timestamp_in_data
                        latest_ajb_dc_isolator_status.append(dc_isolator_status_values)
                except Exception as exc:
                    logger.debug(exc)
                    latest_ajb_dc_isolator_status = []

                data['last_spd_status'] = latest_ajb_spd_status
                data['last_dc_isolator_status'] = latest_ajb_dc_isolator_status
                ajb_data.append(data)

            except Exception as exception:
                logger.debug(str(exception))
        result['ajbs'] = ajb_data

        from django import db
        db.connections.close_all()

        return ajb_data
    except Exception as exception:
        logger.debug(str(exception))
        return {}


def get_plant_live_ajb_status_mp(plant, ajbs_query_set):
    try:
        ajbs = [ajb for ajb in ajbs_query_set]
        n_ajbs = len(ajbs)
        n_cpu = cpu_count()
        args = []

        if n_ajbs > 20:
            ajbs_per_proc = (n_ajbs/(n_cpu-1)) + 1
            pool = Pool(processes=n_cpu-1)
            for i in range(n_cpu-1):
                args.append((plant, ajbs[i*ajbs_per_proc: (i+1)*ajbs_per_proc]))
        else:
            pool = Pool(processes=1)
            args.append((plant, ajbs))

        results = pool.map(get_ajbs_live_status, args)
        pool.close()
        pool.join()
        ajbs_status = [item for sublist in results for item in sublist]
        # close this connection in the main process to be on the safe side
        from django.db import connection
        try:
            if connection.connection:
                connection.connection.close()
            connection.connection = None
        except:
            pass
        return ajbs_status
    except:
        return []


def get_inverters_power_or_energy_data((plant, inverters, energy, starttime, endtime)):
    #logger.debug("starting a new process for get_inverters_power_or_energy_data : " + str(len(inverters)))
    # restart django's connection with mysql
    from django.db import connection
    try:
        if connection.connection:
            #logger.debug("closing mysql connection")
            connection.connection.close()
        connection.connection = None
    except:
        pass

    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.query import dict_factory
    from cassandra.cqlengine import connection
    from cassandra.cqlengine import models
    from solarrms.settings import INVERTER_ENERGY_FIELD, INVERTER_POWER_FIELD, \
        INVERTER_TOTAL_ENERGY_FIELD
    import pandas as pd

    auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
    cassandra_cluster = Cluster(settings.HOST_IP,
                                auth_provider=auth_provider, protocol_version=3)

    cassandra_session = cassandra_cluster.connect()
    cassandra_session.row_factory = dict_factory
    connection.set_session(cassandra_session)
    models.DEFAULT_KEYSPACE = 'dataglen_data'

    df_list = []
    if energy:
        if hasattr(plant, 'metadata') and plant.metadata.inverters_sending_daily_generation:
            stream = INVERTER_ENERGY_FIELD
        elif hasattr(plant, 'metadata') and plant.metadata.inverters_sending_total_generation:
            stream = INVERTER_TOTAL_ENERGY_FIELD
        else:
            return []
    else:
        stream = INVERTER_POWER_FIELD
    for inverter in inverters:
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
        except Exception as exc:
            logger.debug(exc)
            continue
    #logger.debug("stopping a new process for get_inverters_power_or_energy_data : " + str(len(inverters)))
    from django import db
    db.connections.close_all()

    return df_list

def get_inverters_power_or_energy_data_mp(plant, inverters, energy, starttime, endtime):
    try:
        #inverters = [inv for inv in inverters_query_set]
        n_inverters = len(inverters)
        n_cpu = cpu_count()
        args = []

        # limit the number of processes that comes up, so to avoid too many connections with cassandra
        # mp is already being used on the widgets and
        if n_inverters > INVERTER_LIM:
            n_procs = int(n_inverters/10)+1
            if n_procs >= n_cpu:
                inverters_per_proc = int(n_inverters/(n_cpu-1)) + 1
                n_procs = n_cpu-1
            else:
                inverters_per_proc = int(n_inverters / n_procs) + 1

            pool = Pool(processes=n_procs)
            for i in range(n_procs):
                args.append((plant, inverters[i*inverters_per_proc: (i+1)*inverters_per_proc], energy, starttime, endtime))
        else:
            pool = Pool(processes=1)
            args.append((plant, inverters, energy, starttime, endtime))

        results = pool.map(get_inverters_power_or_energy_data, args)
        pool.close()
        pool.join()
        #logger.debug(len(results))
        df_list = [item for sublist in results for item in sublist]
        # logger.debug("LIVEAPI HUA _ get_inverters_power_or_energy_data_mp: " + str(df_list))
        #logger.debug(len(df_list))
        # close this connection in the main process to be on the safe side
        from django.db import connection
        try:
            if connection.connection:
                connection.connection.close()
            connection.connection = None
        except:
            pass
        return df_list
    except Exception as exc:
        # logger.debug("LIVEAPI HUA _ get_inverters_power_or_energy_data_mp: " + str(exc))
        return []


def get_inverters_live_status((plant, inverters, inverters_generation, mobile_app)):
    try:
        #logger.debug("starting a new process for live inverters information : " + str(len(inverters)))
        # restart django's connection with mysql
        from django.db import connection
        try:
            if connection.connection:
                connection.connection.close()
            connection.connection = None
        except:
            pass

        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider
        from cassandra.query import dict_factory
        from cassandra.cqlengine import connection
        from cassandra.cqlengine import models

        auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
        cassandra_cluster = Cluster(settings.HOST_IP,
                                    auth_provider=auth_provider, protocol_version=3)

        cassandra_session = cassandra_cluster.connect()
        cassandra_session.row_factory = dict_factory
        connection.set_session(cassandra_session)
        models.DEFAULT_KEYSPACE = 'dataglen_data'

        results = {}
        inverters_keys = [inverter.sourceKey for inverter in inverters]
        # logger.debug(inverters_keys)
        stats = get_user_data_monitoring_status(IndependentInverter.objects.filter(sourceKey__in=inverters_keys))
        # logger.debug(stats)
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
        else:
            active_alive_valid = None
            active_dead = None

        inverters_data = []
        for inverter in inverters:
            try:
                data = {}

                # get the generation for today
                try:
                    today_generation = float(inverters_generation[0]['energy'][inverter.name])
                except:
                    today_generation = 0.0

                # get current power
                try:
                    try:
                        last_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                             stream_name='ACTIVE_POWER',
                                                                             timestamp_in_data__lte=datetime.now(
                                                                                 pytz.timezone(inverter.dataTimezone)) - timedelta(
                                                                                 seconds=120),
                                                                             timestamp_in_data__gte=datetime.now(
                                                                                 pytz.timezone(inverter.dataTimezone)) - timedelta(
                                                                                 seconds=inverter.timeoutInterval)).limit(1)
                        last_power = float(last_power[0].stream_value)
                    except:
                        last_power = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                             stream_name='ACTIVE_POWER',
                                                                             timestamp_in_data__lte=datetime.now(
                                                                                 pytz.timezone('Asia/Kolkata')) - timedelta(
                                                                                 seconds=120),
                                                                             timestamp_in_data__gte=datetime.now(
                                                                                 pytz.timezone('Asia/Kolkata')) - timedelta(
                                                                                 seconds=inverter.timeoutInterval)).limit(1)
                        last_power = float(last_power[0].stream_value)

                except Exception as exc:
                    #logger.debug(exc)
                    last_power = 0.0

                # get current total yield
                try:
                    last_total_yield = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                               stream_name='TOTAL_YIELD').limit(1)

                    last_total_yield = float(last_total_yield[0].stream_value)
                except Exception as exc:
                    #logger.debug(exc)
                    last_total_yield = 0.0

                # get inside temperature
                try:
                    inside_temperature = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                 stream_name='INSIDE_TEMPERATURE',
                                                                                 timestamp_in_data__lte=datetime.now(
                                                                                     pytz.timezone(
                                                                                         'Asia/Kolkata')) - timedelta(
                                                                                     seconds=120),
                                                                                 timestamp_in_data__gte=datetime.now(
                                                                                     pytz.timezone(
                                                                                         'Asia/Kolkata')) - timedelta(
                                                                                     seconds=inverter.timeoutInterval)).limit(
                        1)
                    inside_temperature = float(inside_temperature[0].stream_value)
                except Exception as exc:
                    #logger.debug(exc)
                    inside_temperature = 0.0

                # get last 3 inverter errors
                last_three_errors = []
                try:
                    #from errors.models import ErrorStorageByStream
                    from solarrms.api_views import ErrorStorageByStream
                    inverter_errors = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                          stream_name='ERROR_CODE').limit(3)
                    for i in range(len(inverter_errors)):
                        error_values = {}
                        try :
                            error_description = inverter.get_error_code_mapping(float(inverter_errors[i].stream_value))
                            # error_description = InverterErrorCodes.objects.get(manufacturer=inverter.manufacturer,
                            #                                                    model=inverter.model,
                            #                                                    error_code = float(inverter_errors[i].stream_value)).error_description
                        except:
                            error_description = None


                        error_code = inverter_errors[i].stream_value
                        if inverter.plant.slug == "thuraiyur":# or inverter.plant.slug == "palladam":
                            error_code = hex(int(float(error_code)))

                        if error_description is not None:
                            if mobile_app:
                                error_values['error_code'] = float(error_code)
                            else:
                                error_values['error_code'] = str(error_code) + ": " + error_description
                        else:
                            error_values['error_code'] = str(error_code)

                        error_values['timestamp'] = (inverter_errors[i].timestamp_in_data).strftime('%Y-%m-%dT%H:%M:%SZ')
                        last_three_errors.append(error_values)
                except Exception as exc:
                    logger.debug(exc)
                    last_three_errors = []

                alarm_active = False
                # get the current solar status value
                try:
                    current_solar_status = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                   stream_name='SOLAR_STATUS',
                                                                                   timestamp_in_data__lte=datetime.now(
                                                                                       pytz.timezone('Asia/Kolkata')),
                                                                                   timestamp_in_data__gte=datetime.now(
                                                                                       pytz.timezone(
                                                                                           'Asia/Kolkata')) - timedelta(
                                                                                       seconds=inverter.timeoutInterval)).limit(
                        1)
                    if len(current_solar_status) > 0:
                        current_solar_status = float(current_solar_status[0].stream_value)
                        try:
                            solar_status_mapping = InverterStatusMappings.objects.filter(plant=plant,
                                                                                         stream_name='SOLAR_STATUS',
                                                                                         status_code=current_solar_status)
                            if not solar_status_mapping[0].generating:
                                alarm_active = True
                        except:
                            alarm_active = False

                except:
                    alarm_active = False

                # get the connection status
                # if active_alive_valid:
                if inverter.sourceKey in active_alive_valid and alarm_active:
                    connected = "alarms"
                elif inverter.sourceKey in active_alive_valid:
                    connected = "connected"
                elif inverter.sourceKey in active_dead:
                    connected = "disconnected"
                else:
                    connected = "unknown"
                # else:
                #     connected = "unknown"
                # logger.debug(inverter)
                # logger.debug(connected)
                # get the inverter status
                latest_inverter_status = []
                try:
                    inverter_status = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                              stream_name='SOLAR_STATUS',
                                                                              timestamp_in_data__lte=datetime.now(
                                                                                  pytz.timezone('Asia/Kolkata')),
                                                                              timestamp_in_data__gte=datetime.now(
                                                                                  pytz.timezone(
                                                                                      'Asia/Kolkata')) - timedelta(
                                                                                  seconds=inverter.timeoutInterval)).limit(
                        1)
                    for i in range(len(inverter_status)):
                        status_values = {}
                        if mobile_app:
                            status_values['status'] = float(inverter_status[i].stream_value)
                        else:
                            try:
                                status_description = InverterStatusMappings.objects.get(plant=plant, stream_name='SOLAR_STATUS',
                                                                                        status_code=float(
                                                                                            inverter_status[i].stream_value))
                                status_values['status'] = status_description.status_description
                            except:
                                status_values['status'] = inverter_status[i].stream_value
                        status_values['timestamp'] = (inverter_status[i].timestamp_in_data).strftime('%Y-%m-%dT%H:%M:%SZ')
                        latest_inverter_status.append(status_values)
                except Exception as exc:
                    logger.debug(exc)
                    latest_inverter_status = []

                ajb_stats = get_user_data_monitoring_status(inverter.ajb_units.all().filter(isActive=True))
                if ajb_stats is not None:
                    active_alive_valid_ajb, active_alive_invalid_ajb, active_dead_ajb, deactivated_alive_ajb, deactivated_dead_ajb, unmonitored_ajb = ajb_stats
                else:
                    active_alive_valid_ajb = None
                    active_dead_ajb = None

                disconnected_ajbs = len(active_dead_ajb) + len(deactivated_alive_ajb)

                try:
                    last_timestamp_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                  stream_name='TOTAL_YIELD').limit(1)

                    if len(last_timestamp_data) == 0:
                        last_timestamp_data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                      stream_name='DAILY_YIELD').limit(1)

                    if len(last_timestamp_data) > 0:
                        last_timestamp = last_timestamp_data[0].timestamp_in_data
                        last_timestamp = update_tz(last_timestamp, plant.metadata.plantmetasource.dataTimezone).strftime(
                            '%Y-%m-%dT%H:%M:%SZ')
                    else:
                        last_timestamp = "NA"
                except Exception as exc:
                    print str(exc)
                    last_timestamp = "NA"

                # data for this inverter
                data['name'] = inverter.name
                if mobile_app:
                    data['generation'] = str(today_generation) + " kWh"
                else:
                    data['generation'] = today_generation
                data['power'] = last_power
                data['connected'] = connected
                data['key'] = inverter.sourceKey
                data['orientation'] = inverter.orientation
                if mobile_app:
                    data['capacity'] = str(inverter.actual_capacity) + ' kW'
                else:
                    data['capacity'] = inverter.actual_capacity
                if len(inverter.solar_groups.all()) != 0:
                    data['solar_group'] = str(inverter.solar_groups.all()[0].name)
                else:
                    data['solar_group'] = "NA"
                data['inside_temperature'] = str(inside_temperature) + ' C'
                data['total_yield'] = str(last_total_yield) + ' kWh'
                data['last_three_errors'] = last_three_errors
                data['last_inverter_status'] = latest_inverter_status
                data['total_ajbs'] = len(inverter.ajb_units.all())
                data['disconnected_ajbs'] = disconnected_ajbs
                data['last_timestamp'] = last_timestamp
                # populate in the inverters data list
                inverters_data.append(data)
            except Exception as exc:
                logger.debug(str(exc))
                continue

        from django import db
        db.connections.close_all()
        #logger.debug("ending the process for live inverters information : " + str(len(inverters_data)))
        return inverters_data

    except Exception as exc:
        logger.debug(exc)
        return {}


def get_plant_live_inverters_status_mp(plant, inverters_query_set, inverters_generation, mobile_app=True):
    try:
        inverters = [inv for inv in inverters_query_set]
        n_inverters = len(inverters)
        n_cpu = cpu_count()
        args = []

        if n_inverters > INVERTER_LIM:
            n_procs = int(n_inverters/10)+1
            if n_procs >= n_cpu:
                inverters_per_proc = int(n_inverters/(n_cpu-1)) + 1
                n_procs = n_cpu-1
            else:
                inverters_per_proc = int(n_inverters / n_procs) + 1

            pool = Pool(processes=n_procs)
            for i in range(n_procs):
                args.append((plant, inverters[i*inverters_per_proc: (i+1)*inverters_per_proc], inverters_generation, mobile_app))
        else:
            pool = Pool(processes=1)
            args.append((plant, inverters, inverters_generation, mobile_app))

        results = pool.map(get_inverters_live_status, args)
        pool.close()
        pool.join()
        #logger.debug(len(results))
        df_list = [item for sublist in results for item in sublist]
        #logger.debug(len(df_list))
        # close this connection in the main process to be on the safe side
        from django.db import connection
        try:
            if connection.connection:
                connection.connection.close()
            connection.connection = None
        except:
            pass
        return df_list
    except:
        return []


def generation_grouping((plant, devices, df, original_starttime, original_endtime, aggregation, local_timezone, meter_energy)):
    #logger.debug("starting a new process for energy aggregation information : " + str(len(devices)))
    # restart django's connection with mysql
    from django.db import connection
    try:
        if connection.connection:
            connection.connection.close()
        connection.connection = None
    except:
        pass

    # from cassandra.cluster import Cluster
    # from cassandra.auth import PlainTextAuthProvider
    # from cassandra.query import dict_factory
    # from cassandra.cqlengine import connection
    # from cassandra.cqlengine import models
    import pandas as pd
    import numpy as np
    import math

    # auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
    # cassandra_cluster = Cluster(settings.HOST_IP,
    #                             auth_provider=auth_provider, protocol_version=3)
    #
    # cassandra_session = cassandra_cluster.connect()
    # cassandra_session.row_factory = dict_factory
    # connection.set_session(cassandra_session)
    # models.DEFAULT_KEYSPACE = 'dataglen_data'

    final_values = {}
    for device in devices:
        try:
            df_device_new = pd.DataFrame()
            df_device_new['timestamp'] = df['timestamp']
            df_device_new[str(device.name)] = df[(device.name)]

            if plant.metadata.plantmetasource.energy_from_power is True:
                df_device = pd.DataFrame()
                df_device['ts'] = df['timestamp'].diff()
                df_device[str(device.name)] = df[(device.name)]
                df_device['timestamp'] = df_device_new['timestamp']
            else:
                df_device = (df_device_new.dropna(axis=0, how='any').diff(-1)) * -1
                df_device = df_device.rename(columns={'timestamp': 'ts'})
                df_device['timestamp'] = df_device_new['timestamp']
                df_device = df_device[df_device['timestamp'] >= original_starttime]
                df_device = df_device[df_device['timestamp'] <= original_endtime]

            if not meter_energy or len(plant.energy_meters.all()) == 0:
                device_capacity = device.total_capacity if device.total_capacity is not None else device.actual_capacity
                df_device = df_device[df_device[str(device.name)] > 0]
                df_device = df_device[
                    df_device[device.name] <= 1.5 * (device_capacity / 60) * (df_device['ts'] / np.timedelta64(1, 'm'))]
            try:
                df_device['timestamp'] = df_device['timestamp'].map(lambda x: x.tz_convert(local_timezone))
            except:
                df_device['timestamp'] = df_device['timestamp'].map(
                    lambda x: x.tz_localize('UTC').tz_convert(local_timezone))
            df_device = df_device.set_index('timestamp')
            data = []
            if not df_device.empty:
                grouped = df_device.groupby(pd.TimeGrouper(aggregation))
                energy = grouped.sum()
                for key, value in energy[device.name].iteritems():
                    try:
                        if not math.isnan(value):
                            data.append(
                                {'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': value})
                        else:
                            # data.append({'timestamp': pd.to_datetime(key).tz_localize('UTC').tz_convert('UTC'), 'energy': 0.0})
                            pass
                    except:
                        if not math.isnan(value):
                            data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': value})
                        else:
                            # data.append({'timestamp': pd.to_datetime(key).tz_convert('UTC'), 'energy': 0.0})
                            pass
                        continue
            final_values[device.name] = data
        except Exception as exception:
            print(str(exception))
            continue
    from django import db
    db.connections.close_all()
    #logger.debug("finishing a process for energy aggregation information : " + str(len(devices)))
    return final_values

def generation_grouping_mp(plant, devices, df, original_starttime, original_endtime, aggregation, local_timezone, meter_energy):
    try:
        n_devices = len(devices)
        n_cpu = cpu_count()
        args = []

        if n_devices > INVERTER_LIM:
            n_procs = int(n_devices/10)+1
            if n_procs >= n_cpu:
                devices_per_proc = int(n_devices/(n_cpu-1)) + 1
                n_procs = n_cpu-1
            else:
                devices_per_proc = int(n_devices/n_procs) + 1

            pool = Pool(processes=n_procs)
            for i in range(n_procs):
                args.append((plant, devices[i*devices_per_proc: (i+1)*devices_per_proc], df,
                             original_starttime, original_endtime, aggregation, local_timezone, meter_energy))
        else:
            pool = Pool(processes=1)
            args.append((plant, devices, df, original_starttime, original_endtime, aggregation, local_timezone, meter_energy))

        results = pool.map(generation_grouping, args)
        pool.close()
        pool.join()
        #logger.debug((results))
        final_data = {}
        for entry in results:
            for key in entry.keys():
                final_data[key] = entry[key]
        from django.db import connection
        try:
            if connection.connection:
                connection.connection.close()
            connection.connection = None
        except:
            pass
        return final_data
    except:
        return []
