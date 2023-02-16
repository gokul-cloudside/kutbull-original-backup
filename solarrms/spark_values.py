from solarrms.models import SolarPlant, IndependentInverter, PlantEquipmentData, PlantAggregatedInfo, \
    InverterErrorCodes, InverterStatusMappings, SolarField
from solarrms.api_views import sorted_nicely
import pytz
from datetime import datetime, timedelta
import ast
from monitoring.views import get_user_data_monitoring_status
from errors.models import ErrorStorageByStream
from dataglen.models import ValidDataStorageByStream
from solarrms.api_views import update_tz
from django.utils import timezone
from solarrms.solar_reports import DEFAULT_STREAM_UNIT
import dateutil
import logging

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

EXCLUDE_VISUALIZATION_STREAMS = ['LIVE', 'AGGREGATED', 'AGGREGATED_START_TIME', 'AGGREGATED_END_TIME', 'AGGREGATED_COUNT','TIMESTAMP']

def get_inverter_sld_parameters_new_spark(plant, inverter_name):
    try:
        result = []
        inverter = IndependentInverter.objects.get(plant=plant, name=inverter_name)
        fields = SolarField.objects.filter(source=inverter, isActive=True)
        inverter_fields = []
        for field in fields:
            inverter_fields.append(str(field.name))
        inverter_fields = sorted_nicely(inverter_fields)
        inverters_data_dict = PlantEquipmentData.objects.filter(identifier=str(plant.slug),
                                                                stream_name='INVERTER_LIVE_DICT',
                                                                window_st_ts__gte=datetime.now(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)) - timedelta(seconds=inverter.timeoutInterval),
                                                                window_st_ts__lte=datetime.now(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)) - timedelta(seconds=120)).limit(1)
        try:
            inverters_data_dict = ast.literal_eval(inverters_data_dict[0].stream_value)
        except:
            inverters_data_dict = {}
        try:
            inverter_values = inverters_data_dict[str(inverter.sourceKey)]
        except:
            inverter_values = {}
        for name in inverter_fields:
            field = SolarField.objects.get(source=inverter, name=name)
            if str(field.name) not in EXCLUDE_VISUALIZATION_STREAMS:
                try:
                    value = inverter_values[name]
                except:
                    value = "NA"

                try:
                    name = str(field.displayName) if field.displayName else str(field.name)
                    stream_name = str(field.name)
                    stream = SolarField.objects.get(source=inverter, name=stream_name)
                    stream_unit = str(stream.streamDataUnit) if (stream and stream.streamDataUnit) else DEFAULT_STREAM_UNIT[stream_name]
                except Exception as exception:
                    logger.debug(str(exception))
                    stream_unit = "NA"

                value_result = {}
                if value is not "NA" and stream_unit is not "NA":
                    value_result['name'] = name
                    try:
                        value_result['value'] = str(round(float(value),2)) + " " + str(stream_unit)
                    except:
                        value_result['value'] = "NA"
                elif value is not "NA" and stream_unit is "NA":
                    value_result['name'] = name
                    value_result['value'] = str(value)
                else:
                    value_result['name'] = name
                    value_result['value'] = "NA"
                result.append(value_result)
        return result
    except Exception as exception:
        logger.debug(str(exception))
        return []

def get_inverters_live_status_spark(plant, inverters, inverters_generation):
    try:
        inverters_keys = [inverter.sourceKey for inverter in inverters]
        stats = get_user_data_monitoring_status(IndependentInverter.objects.filter(sourceKey__in=inverters_keys))
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
        else:
            active_alive_valid = None
            active_dead = None
        logger.debug("before")
        inverters_data = []
        inverters_data_dict = PlantEquipmentData.objects.filter(identifier=str(plant.slug),
                                                                stream_name='INVERTER_LIVE_DICT',
                                                                window_st_ts__gte=datetime.now(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)) - timedelta(seconds=inverter.timeoutInterval),
                                                                window_st_ts__lte=datetime.now(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)) - timedelta(seconds=120)).limit(1)
        try:
            inverters_data_dict = ast.literal_eval(inverters_data_dict[0].stream_value)
        except:
            inverters_data_dict = {}
        logger.debug("inverters_data_dict")
        logger.debug(inverters_data_dict)
        for inverter in inverters:
            try:
                entry = inverters_data_dict[str(inverter.sourceKey)]
            except:
                entry = {}
            try:
                today_generation = inverters_generation[str(inverter.sourceKey)]
            except:
                today_generation = 0.0
            data = {}
            try:
                last_power = entry['ACTIVE_POWER']
            except:
                last_power = 0.0
            try:
                last_total_yield=entry['TOTAL_YIELD']
            except:
                last_total_yield = 0.0
            try:
                inside_temperature=entry['INSIDE_TEMPERATURE']
            except:
                inside_temperature = 0.0

            alarm_active = False

            try:
                try:
                    current_solar_status=float(entry['SOLAR_STATUS'])
                except:
                    current_solar_status = "NA"
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

            if inverter.sourceKey in active_alive_valid and alarm_active:
                connected = "alarms"
            elif inverter.sourceKey in active_alive_valid:
                connected = "connected"
            elif inverter.sourceKey in active_dead:
                connected = "disconnected"
            else:
                connected = "unknown"

            last_three_errors = []
            try:
                inverter_errors = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name='ERROR_CODE').limit(3)
                for i in range(len(inverter_errors)):
                    error_values = {}
                    try :
                        error_description = InverterErrorCodes.objects.get(manufacturer=inverter.manufacturer,
                                                                           model=inverter.model,
                                                                           error_code = float(inverter_errors[i].stream_value)).error_description
                    except:
                        error_description = None


                    error_code = inverter_errors[i].stream_value
                    if inverter.plant.slug == "thuraiyur":# or inverter.plant.slug == "palladam":
                        error_code = hex(int(float(error_code)))

                    if error_description is not None:
                        error_values['error_code'] = str(error_code) + ": " + error_description
                    else:
                        error_values['error_code'] = str(error_code)

                    error_values['timestamp'] = (inverter_errors[i].timestamp_in_data).strftime('%Y-%m-%dT%H:%M:%SZ')
                    last_three_errors.append(error_values)
            except Exception as exc:
                logger.debug(exc)
                last_three_errors = []
            latest_inverter_status = []
            status_values = {}
            try:
                status_description = InverterStatusMappings.objects.get(plant=plant, stream_name='SOLAR_STATUS',
                                                                        status_code=current_solar_status)
                status_values['status'] = status_description.status_description
            except:
                status_values['status'] = current_solar_status
            try:
                status_time = entry['TIMESTAMP']
                status_time = dateutil.parser.parse(status_time)
                status_time = status_time.astimezone(pytz.timezone('UTC')).strftime('%Y-%m-%dT%H:%M:%SZ')
                status_values['timestamp'] = status_time
            except:
                try:
                    status_values['timestamp'] = entry['TIMESTAMP']
                except:
                    status_values['timestamp'] = "NA"
            latest_inverter_status.append(status_values)

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
                logger.debug(str(exc))
                last_timestamp = "NA"
            data['name'] = inverter.name
            data['generation'] = today_generation
            data['power'] = last_power
            data['connected'] = connected
            data['key'] = inverter.sourceKey
            data['orientation'] = inverter.orientation
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
        return inverters_data
    except Exception as exception:
        logger.debug(str(exception))
        return {}

def get_plant_live_data_status_spark(plant, current_time, fill_inverters=True, inverter_name=None):
    try:
        t1 = timezone.now()
        result = {}
        if inverter_name:
            inverters = plant.independent_inverter_units.all().filter(isActive=True).filter(name=inverter_name)
        else:
            inverters = plant.independent_inverter_units.all().filter(isActive=True).order_by('id')
        inverters_name = []
        for inverter in inverters:
            inverters_name.append(str(inverter.name))
        inverters_name = sorted_nicely(inverters_name)
        inverters = []
        for name in inverters_name:
            inverter = IndependentInverter.objects.get(plant=plant, name=name)
            inverters.append(inverter)
        inverters_data = []
        if inverter_name:
            result['dc_sld'] = get_inverter_sld_parameters_new_spark(plant, inverter_name)
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
                logger.debug(str(exc))
                last_timestamp = "NA"
            result['last_timestamp'] = last_timestamp
            return result

        sts = datetime.now(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0,
                                                                 second=0, microsecond=0)
        ets = sts+timedelta(hours=24)

        inverters_generation = PlantEquipmentData.objects.filter(identifier=str(plant.slug),
                                                                 stream_name='INVERTER_LIVE_ENERGY',
                                                                 window_st_ts__gte=sts).limit(1)

        try:
            inverters_generation = ast.literal_eval(inverters_generation[0].stream_value)
            logger.debug(inverters_generation)
        except:
            inverters_generation = {}

        solar_groups_name = plant.solar_groups.all()
        if len(solar_groups_name) == 0:
            result['solar_groups'] = []
            result['total_group_number'] = 0
        else:
            solar_group_list = []
            for i in range(len(solar_groups_name)):
                solar_group_list.append(str(solar_groups_name[i].name))

            result['solar_groups'] = solar_group_list
            result['total_group_number'] = len(solar_groups_name)
        inverters_data = get_inverters_live_status_spark(plant, inverters, inverters_generation)
        result['inverters'] = inverters_data
        logger.debug((timezone.now() - t1).total_seconds())
        return result
    except Exception as exception:
        logger.debug(str(exception))