from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_energy, get_plant_power, get_power_irradiation
from dataglen.models import ValidDataStorageByStream
from solarrms.models import IndependentInverter, PlantCompleteValues, KWHPerMeterSquare, PlantSummaryDetails, SolarField
import pytz
from django.conf import settings
import numpy as np
import datetime
import copy
import ast
import json
import random
import collections
from datetime import timedelta
from solarrms.solargrouputils import get_group_power_irradiation
from solarrms2.models import EnergyContract
INTL_SLUGS = ["instaproducts", 'beaconsfield', 'ausnetdemosite', 'benalla', 'collingwood', 'leongatha',
                      'lilydale', 'rowville', 'seymour', 'thomastown', 'traralgon', 'wodonga', 'yarraville']

def international_plant(plant, plants_groups):
    if plant is not None and plant.slug in INTL_SLUGS:
        return True
    if plants_groups is not None:
        for plant in plants_groups:
            if plant.slug in INTL_SLUGS:
                return True

    return False


unit_conversion = {'GWh' : 1000000,
                   'MWh' : 1000,
                   'kWh' : 1}

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
        return 0.0

# get today's generation for client, plant, inverters, meters based on the scope
# For client, pass all the plants, for which the user has access under plants_group as a list of plants.
# def generation(*args, **kwargs):
#     try:
#         plants_group=kwargs.pop('plants_group', None)
#         plant=kwargs.pop('plant', None)
#         meter=kwargs.pop('meter', None)
#         inverter=kwargs.pop('inverter', None)
#         starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
#         endtime=kwargs.pop('endtime',timezone.now())
#         energy_value = 0.0
#         if plants_group is not None:
#             for plant in plants_group:
#                 plant_energy_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, False, True)
#                 if len(plant_energy_dict)>0:
#                     energy_value += float(plant_energy_dict[len(plant_energy_dict)-1]['energy'])
#         elif plant is not None and meter is not None:
#             meter_energy_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, True, True)
#             if len(meter_energy_dict)>0:
#                 energy_value = meter_energy_dict[str(meter.name)][len(meter_energy_dict[str(meter.name)])-1]['energy']
#         elif plant is not None and inverter is not None:
#             inverter_energy_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, True, False)
#             if len(inverter_energy_dict)>0:
#                 energy_value = inverter_energy_dict[str(inverter.name)][len(inverter_energy_dict[str(inverter.name)])-1]['energy']
#         elif plant is not None:
#             plant_energy_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, False, True)
#             if len(plant_energy_dict)>0:
#                 energy_value += float(plant_energy_dict[len(plant_energy_dict)-1]['energy'])
#         return energy_value
#     except Exception as exception:
#         print str(exception)
#         return 0.0


def generation(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        meter=kwargs.pop('meter', None)
        inverter=kwargs.pop('inverter', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split=kwargs.pop('split', None)
        current = kwargs.pop('current',True)
        energy_value = 0.0
        energy_value_list = []
        energy_value_dict = {}
        try:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        # group call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    energy_value_dict["%s" % group.varchar_id] = 0.0
                    try:
                        energy_value_list.append(value[0].plant_generation_today)
                        energy_value_dict["%s" % group.varchar_id] = value[0].plant_generation_today
                    except:
                        energy_value_dict["%s" % group.varchar_id] = 0.0
                        energy_value_list.append(0.0)
                try:
                    energy_value += sum(energy_value_list)
                except:
                    energy_value += 0.0
            elif group is not None:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    energy_value = value[0].energy_value
            if group_count:
                energy_value_dict['TOTAL'] = energy_value
                return energy_value_dict
            else:
                return energy_value
        else:
            if current is True:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0:
                            energy_value_list.append(float(value[0].plant_generation_today))
                            energy_value_dict[str(plant.slug)] = float(value[0].plant_generation_today)
                        else:
                            energy_value_dict[str(plant.slug)] = 0.0

                    if len(energy_value_list)>0:
                        energy_value = np.sum(energy_value_list)
                elif plant is not None and meter is not None:
                    meter_energy_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, True, True)
                    if len(meter_energy_dict)>0:
                        energy_value = meter_energy_dict[str(meter.name)][len(meter_energy_dict[str(meter.name)])-1]['energy']
                elif plant is not None and inverter is not None:
                    inverter_energy_dict = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, True, False)
                    if len(inverter_energy_dict)>0:
                        energy_value = inverter_energy_dict[str(inverter.name)][len(inverter_energy_dict[str(inverter.name)])-1]['energy']
                elif plant is not None:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        energy_value_list.append(float(value[0].plant_generation_today))
                    if len(energy_value_list)>0:
                        energy_value = np.sum(energy_value_list)
                if split:
                    energy_value_dict['TOTAL'] = energy_value
                    return energy_value_dict
                else:
                    return energy_value
            else:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=str(plant.slug),
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0:
                            energy_value_list.append(float(value[0].generation))
                            energy_value_dict[str(plant.slug)] = float(value[0].generation)
                        else:
                            energy_value_dict[str(plant.slug)] = 0.0

                    if len(energy_value_list)>0:
                        energy_value = np.sum(energy_value_list)
                elif plant is not None:
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=str(plant.slug),
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        energy_value_list.append(float(value[0].generation))
                    if len(energy_value_list)>0:
                        energy_value = np.sum(energy_value_list)
                if split:
                    energy_value_dict['TOTAL'] = energy_value
                    return energy_value_dict
                else:
                    return energy_value
    except Exception as exception:
        print str(exception)
        return 0.0


# get current power based on the scope
def power_chart(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        try:
            if starttime.tzinfo is None:
                tz = pytz.utc
                starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            starttime = starttime.replace(hour=5, minute=0, second=0, microsecond=0)
        except Exception as exception:
            print str(exception)
            starttime = starttime
        endtime=kwargs.pop('endtime',starttime+datetime.timedelta(hours=15))
        power_values = get_power_irradiation(starttime, endtime, plant)
        return json.loads(power_values)
    except Exception as exception:
        print str(exception)


# get total energy generated by plant till date
# def total_energy(*args, **kwargs):
#     try:
#         total_plant_energy = 0.0
#         plants_group=kwargs.pop('plants_group', None)
#         plant=kwargs.pop('plant', None)
#         if plants_group is not None:
#             for plant in plants_group:
#                 plant_energy = calculate_total_plant_generation(plant)
#                 total_plant_energy += plant_energy
#         elif plant is not None:
#             total_plant_energy = calculate_total_plant_generation(plant)
#         return total_plant_energy
#     except Exception as exception:
#         print str(exception)
#         return 0.0

def total_energy(*args, **kwargs):
    try:
        total_plant_energy = 0.0
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        energy_value_list = []
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        if plants_group is not None:
            for plant in plants_group:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=plant.metadata.plantmetasource.sourceKey,
                                                           ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    energy_value_list.append(float(value[0].total_generation))
                if len(energy_value_list)>0:
                    total_plant_energy = np.sum(energy_value_list)
        elif plant is not None:
            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=plant.metadata.plantmetasource.sourceKey,
                                                           ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
            if len(value)>0:
                energy_value_list.append(float(value[0].total_generation))
            if len(energy_value_list)>0:
                total_plant_energy = np.sum(energy_value_list)
        return total_plant_energy
    except Exception as exception:
        print str(exception)
        return 0.0


# weekly energy chart
def weekly_energy(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        weekly_generation = []
        if plants_group is not None:
            for plant in plants_group:
                try:
                    starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except Exception as exception:
                    print str(exception)
                    if international_plant(plant, plants_group) is False:
                        starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))

                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=plant.metadata.plantmetasource.sourceKey,
                                                           ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    plant_past_generation = ast.literal_eval(value[0].past_generations)
                    if len(weekly_generation) == 0 and len(plant_past_generation)==7:
                        weekly_generation = copy.deepcopy(plant_past_generation)
                        for i in range (len (weekly_generation)):
                            weekly_generation[i]['energy'] = float (
                                str (weekly_generation[i]['energy']).split (' ')[0]) * float (
                                unit_conversion[str (weekly_generation[i]['energy']).split (' ')[1]])

                    else:
                        for i in range(len(weekly_generation)):
                            try:
                                weekly_generation[i]['energy'] = float(str(weekly_generation[i]['energy']))+ \
                                    float(str(plant_past_generation[i]['energy']).split(' ')[0])*float(unit_conversion[str(plant_past_generation[i]['energy']).split(' ')[1]])
                            except Exception as exception:
                                continue
            # if len(plants_group)==1:
            #     for i in range(len(weekly_generation)):
            #         weekly_generation[i]['energy'] = float(str(weekly_generation[i]['energy']).split(' ')[0])*float(unit_conversion[str(weekly_generation[i]['energy']).split(' ')[1]])
        elif plant is not None:
            try:
                starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exception:
                print str(exception)
                if international_plant(plant, plants_group) is False:
                    starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=plant.metadata.plantmetasource.sourceKey,
                                                           ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
            if len(value)>0:
                plant_past_generation = ast.literal_eval(value[0].past_generations)
            if len(weekly_generation) == 0:
                        weekly_generation = copy.deepcopy(plant_past_generation)
            for i in range(len(weekly_generation)):
                    weekly_generation[i]['energy'] = float(str(weekly_generation[i]['energy']).split(' ')[0])*float(unit_conversion[str(weekly_generation[i]['energy']).split(' ')[1]])
        try:
            for i in range(len(weekly_generation)):
                weekly_generation[i]['timestamp'] = datetime.datetime.strptime(str(weekly_generation[i]['timestamp']),'%Y-%m-%d %H:%M:%S')
                weekly_generation[i]['timestamp'] = weekly_generation[i]['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ')
        except:
            pass
        return weekly_generation
    except Exception as exception:
        print str(exception)


def total_power(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        active_power_list = []
        active_power = 0.0
        active_power_dict = {}
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    active_power_dict["%s" % group.varchar_id] = 0.0
                    try:
                        active_power_list.append(value[0].active_power)
                        active_power_dict["%s" % group.varchar_id] = value[0].active_power
                    except:
                        active_power_dict["%s" % group.varchar_id] = 0.0
                        active_power_list.append(0.0)
                try:
                    active_power += sum(active_power_list)
                except:
                    active_power += 0.0
            elif group is not None:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    active_power = value[0].active_power
            if group_count:
                active_power_dict['TOTAL'] = active_power
                return active_power_dict
            else:
                return active_power
        else:
            if plants_group is not None:
                for plant in plants_group:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        active_power_list.append(value[0].active_power)
                        active_power_dict[str(plant.slug)] = value[0].active_power
                    else:
                        active_power_dict[str(plant.slug)] = 0.0
                try:
                    active_power = sum(active_power_list)
                except:
                    active_power = 0.0
            elif plant is not None:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    active_power = value[0].active_power
            if split is True:
                active_power_dict['TOTAL'] = active_power
                return active_power_dict
            else:
                return active_power
    except Exception as exception:
        print (str(exception))

def insolation(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        current = kwargs.pop('current',True)
        insolation_list = []
        insolation_dict = {}
        insolation = 0.0
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        if current is True:
            if plants_group is not None:
                for plant in plants_group:
                    value = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                             identifier=plant.metadata.plantmetasource.sourceKey,
                                                             ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        insolation_list.append(value[0].value)
                        insolation_dict[str(plant.slug)] = value[0].value
                    else:
                        insolation_dict[str(plant.slug)] = 0.0
                try:
                    insolation = sum(insolation_list)
                except:
                    insolation = 0.0
            elif plant is not None:
                value = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                         identifier=plant.metadata.plantmetasource.sourceKey,
                                                         ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    insolation = value[0].value
            if split is True:
                insolation_dict['TOTAL'] = insolation
                return insolation_dict
            else:
                return insolation
        else:
            if plants_group is not None:
                for plant in plants_group:
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=str(plant.slug),
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        insolation_list.append(value[0].average_irradiation)
                        insolation_dict[str(plant.slug)] = value[0].average_irradiation
                    else:
                        insolation_dict[str(plant.slug)] = 0.0
                try:
                    insolation = np.mean(insolation_list)
                except:
                    insolation = 0.0
            elif plant is not None:
                value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=str(plant.slug),
                                                           ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    insolation = value[0].average_irradiation
            if split is True:
                insolation_dict['TOTAL'] = insolation
                return insolation_dict
            else:
                return insolation
    except Exception as exception:
        print str(exception)


def peak_power(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        try:
            power_values, peak_power = get_power_irradiation(starttime, endtime, plant, True)
        except:
            peak_power = 0.0
        return peak_power
    except Exception as exception:
        print str(exception)

ENERGY_METER_POWER_STREAM_UNIT_FACTOR = {'MW': 1000,
                                         'W': 0.001}

def meter_power(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        meters = plant.energy_meters.all().filter(energy_calculation=True)
        if len(meters)==0:
            return "NA"
        else:
            power = 0.0
            for meter in meters:
                values = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                 stream_name='WATT_TOTAL',
                                                                 timestamp_in_data__lte=datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                 timestamp_in_data__gte=datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=meter.timeoutInterval)).limit(1)
                stream = SolarField.objects.get(source=meter, name='WATT_TOTAL')
                stream_data_unit = stream.streamDataUnit
                if len(values)>0:
                    if stream_data_unit:
                        try:
                            power += float(values[0].stream_value)*float(ENERGY_METER_POWER_STREAM_UNIT_FACTOR[stream_data_unit])
                        except:
                            power += float(values[0].stream_value)
                    power += float(values[0].stream_value)
            return power
    except Exception as exception:
        print str(exception)


def meter_energy(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        meters = plant.energy_meters.all().filter(energy_calculation=True)
        if len(meters)==0:
            return "NA"
        else:
            energy_values = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, False, True, False)
            try:
                energy = energy_values[len(energy_values)-1]['energy']
            except:
                energy = 0.0
            return energy
    except Exception as exception:
        print str(exception)


def inverter_energy(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        inverters = plant.independent_inverter_units.all()
        meters=plant.energy_meters.all()
        energy_value_list = []

        if len(inverters)==0:
            return "NA"
        elif len(meters)==0:
            try:
                starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except:
                if international_plant(plant, None) is False:
                    starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))

            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
            if len(value)>0:
                return float(value[0].plant_generation_today)
            else:
                return 0.0

        else:
            energy_values = get_minutes_aggregated_energy(starttime, endtime, plant, 'DAY', 1, False, False, False)
            try:
                energy = energy_values[len(energy_values)-1]['energy']
            except:
                energy = 0.0
            return energy
    except Exception as exception:
        print str(exception)


def inverter_power(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        inverters = plant.independent_inverter_units.all()
        if len(inverters)==0:
            return "NA"
        else:
            power = 0.0
            for inverter in inverters:
                values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                 stream_name='ACTIVE_POWER',
                                                                 timestamp_in_data__lte=datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                 timestamp_in_data__gte=datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=inverter.timeoutInterval)).limit(1)
                if len(values)>0:
                        power += float(values[0].stream_value)
            return power
    except Exception as exception:
        print str(exception)



def ajb_power(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        ajbs = plant.ajb_units.all()
        if len(ajbs)==0:
            return "NA"
        else:
            power = 0.0
            for ajb in ajbs:
                values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                 stream_name='POWER',
                                                                 timestamp_in_data__lte=datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=120),
                                                                 timestamp_in_data__gte=datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(seconds=ajb.timeoutInterval)).limit(1)
                if len(values)>0:
                        power += float(values[0].stream_value)
            return power
    except Exception as exception:
        print str(exception)

# PPA Pricing
def ppa_pricing(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        split = kwargs.pop('split', None)
        ppa_pricing_dict = {}

        if plants_group is not None:
            for plant in plants_group:
                ppa_pricing_value = "--"
                plant_contract_details = plant.contract_details.all()
                if len(plant_contract_details)>0:
                    contract_detail = plant_contract_details[0]
                    if contract_detail.ppa_pricing:
                        ppa_pricing_value = contract_detail.ppa_pricing
                    else:
                        ppa_pricing_value = "--"
                ppa_pricing_dict[str(plant.slug)] = ppa_pricing_value
        elif plant is not None:
            ppa_pricing_value = "--"
            plant_contract_details = plant.contract_details.all()
            if len(plant_contract_details)>0:
                contract_detail = plant_contract_details[0]
                if contract_detail.ppa_pricing:
                    ppa_pricing_value = contract_detail.ppa_pricing
                else:
                    ppa_pricing_value = "--"
        if split is True:
            return ppa_pricing_dict
        else:
            return ppa_pricing_value
    except Exception as exception:
        print str(exception)


def group_power_chart(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plant=kwargs.pop('plant', None)
        solar_group = kwargs.pop('group', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        try:
            if starttime.tzinfo is None:
                tz = pytz.utc
                starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            starttime = starttime.replace(hour=5, minute=0, second=0, microsecond=0)
        except Exception as exception:
            print str(exception)
            starttime = starttime
        endtime=kwargs.pop('endtime',starttime+datetime.timedelta(hours=15))
        power_values = get_group_power_irradiation(starttime, endtime, solar_group, plant)
        return json.loads(power_values)
    except Exception as exception:
        print str(exception)


def current_irradiance(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        irradiance_list = []
        irradiance_value = 0.0
        irradiance_dict = {}
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    irradiance_dict["%s" % group.varchar_id] = 0.0
                    if len(value) > 0:
                        irradiance_list.append(value[0].irradiation)
                        irradiance_dict["%s" % group.varchar_id] = value[0].irradiation
                    else:
                        irradiance_dict["%s" % group.varchar_id] = 0.0
                try:
                    irradiance_value = sum(irradiance_list)/len(irradiance_list)
                except:
                    irradiance_value = 0.0
            elif group is not None:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value) > 0:
                    irradiance_value = value[0].irradiation
            if group_count:
                irradiance_dict['TOTAL'] = irradiance_value
                return irradiance_dict
            else:
                return irradiance_value
        else:
            if plants_group is not None:
                for plant in plants_group:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value) > 0:
                        irradiance_list.append(value[0].irradiation)
                        irradiance_dict["%s" % plant.slug] = value[0].irradiation
                    else:
                        irradiance_dict["%s" % plant.slug] = 0.0
                try:
                    irradiance_value = sum(irradiance_list)/len(irradiance_list)
                except:
                    irradiance_value = 0.0
            elif plant is not None:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    irradiance_value = value[0].irradiation
            if split is True:
                irradiance_dict['TOTAL'] = irradiance_value
                return irradiance_dict
            else:
                return irradiance_value
    except Exception as exception:
        print (str(exception))


def daily_generation(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        revenue = {}
        generation = collections.OrderedDict()
        generation_dict = {}
        try:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        if plants_group is not None:
            for plant in plants_group:
                ppa_pricing = 0
                try:
                    energy_contact = EnergyContract.objects.get(start_date__lte=starttime,
                                                                end_date__gte=starttime, plant=plant)
                    ppa_pricing = energy_contact.ppa_price
                except:
                    ppa_pricing = 0
                value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=str(plant.slug),
                                                           ts__gte=starttime.replace(hour=0, minute=0, second=0, microsecond=0),
                                                           ts__lte=endtime.replace(hour=0, minute=0, second=0, microsecond=0)).order_by('ts')
                #print "%s-%s" % (plant.slug, ppa_pricing)
                for val in value:
                    ts_val = val.ts
                    ts_val = ts_val.strftime('%Y-%m-%dT%H:%M:%SZ')
                    if "%s" % ts_val in generation:
                        generation["%s" % ts_val] += val.generation if val.generation else 0.0
                        revenue["%s" % ts_val] += val.generation * ppa_pricing if val.generation else 0.0
                    else:
                        generation["%s" % ts_val] = val.generation if val.generation else 0.0
                        revenue["%s" % ts_val] = val.generation * ppa_pricing if val.generation else 0.0
        elif plant is not None:
            ppa_pricing = 0
            try:
                energy_contact = EnergyContract.objects.get(start_date__lte=starttime,
                                                            end_date__gte=starttime, plant=plant)
                ppa_pricing = energy_contact.ppa_price
            except:
                ppa_pricing = 0
            value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=str(plant.slug),
                                                       ts__gte=starttime.replace(hour=0, minute=0, second=0, microsecond=0),
                                                       ts__lte=endtime.replace(hour=0, minute=0, second=0, microsecond=0)).order_by('ts')
            #print "%s-%s" % (plant.slug, ppa_pricing)
            for val in value:
                ts_val = val.ts
                ts_val = ts_val.strftime('%Y-%m-%dT%H:%M:%SZ')
                if "%s" % ts_val in generation:
                    generation["%s" % ts_val] += val.generation if val.generation else 0.0
                    revenue["%s" % ts_val] += val.generation * ppa_pricing if val.generation else 0.0
                else:
                    generation["%s" % ts_val] = val.generation if val.generation else 0.0
                    revenue["%s" % ts_val] = val.generation * ppa_pricing if val.generation else 0.0
        generation_dict['GENERATION'] = map(lambda k: {'timestamp': k, 'generation': generation[k]}, generation)
        generation_dict['TOTAL'] = sum(generation.values())
        generation_dict['CO2'] = generation_dict['TOTAL'] * 0.7
        generation_dict['REVENUE'] = sum(revenue.values())
        return generation_dict
    except Exception as exception:
        print str(exception)
        return 0.0


def monthly_generation(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        revenue = {}
        generation = collections.OrderedDict()
        generation_dict = {}
        try:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        if plants_group is not None:
            for plant in plants_group:
                ppa_pricing = 0
                try:
                    energy_contact = EnergyContract.objects.get(start_date__lte=starttime,
                                                                end_date__gte=starttime, plant=plant)
                    ppa_pricing = energy_contact.ppa_price
                except:
                    ppa_pricing = 0
                value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                           identifier=str(plant.slug),
                                                           ts__gte=starttime.replace(hour=0, minute=0, second=0, microsecond=0),
                                                           ts__lte=endtime.replace(hour=0, minute=0, second=0, microsecond=0)).order_by('ts')
                for val in value:
                    ts_val = val.ts
                    ts_val = ts_val.strftime('%Y-%m-%dT%H:%M:%SZ')
                    if "%s" % ts_val in generation:
                        generation["%s" % ts_val] += val.generation if val.generation else 0.0
                        revenue["%s" % ts_val] += val.generation * ppa_pricing if val.generation else 0.0
                    else:
                        generation["%s" % ts_val] = val.generation if val.generation else 0.0
                        revenue["%s" % ts_val] = val.generation * ppa_pricing if val.generation else 0.0
        elif plant is not None:
            value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                       identifier=str(plant.slug),
                                                       ts__gte=starttime.replace(hour=0, minute=0, second=0, microsecond=0),
                                                       ts__lte=endtime.replace(hour=0, minute=0, second=0, microsecond=0)).order_by('ts')
            ppa_pricing = 0
            try:
                energy_contact = EnergyContract.objects.get(start_date__lte=starttime,
                                                            end_date__gte=starttime, plant=plant)
                ppa_pricing = energy_contact.ppa_price
            except:
                ppa_pricing = 0
            for val in value:
                ts_val = val.ts
                ts_val = ts_val.strftime('%Y-%m-%dT%H:%M:%SZ')
                if "%s" % ts_val in generation:
                    generation["%s" % ts_val] += val.generation if val.generation else 0.0
                    revenue["%s" % ts_val] += val.generation * ppa_pricing if val.generation else 0.0
                else:
                    generation["%s" % ts_val] = val.generation if val.generation else 0.0
                    revenue["%s" % ts_val] = val.generation * ppa_pricing if val.generation else 0.0
        generation_dict['GENERATION'] = map(lambda k: {'timestamp': k, 'generation': generation[k]}, generation)
        generation_dict['TOTAL'] = sum(generation.values())
        generation_dict['CO2'] = generation_dict['TOTAL'] * 0.7
        generation_dict['REVENUE'] = sum(revenue.values())
        return generation_dict
    except Exception as exception:
        print str(exception)
        return 0.0


def daily_revenue(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        revenue = 0.0
        try:
            tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            starttime = starttime.replace(tzinfo=None)
            starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone('UTC'))
        except:
            tz = pytz.timezone("Asia/Kolkata")
            starttime = starttime.replace(tzinfo=None)
            starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone('UTC'))
        if plants_group is not None:
            for plant in plants_group:
                ppa_pricing = 0
                try:
                    energy_contact = EnergyContract.objects.get(start_date__lte=starttime,
                                                                end_date__gte=starttime, plant=plant)
                    ppa_pricing = energy_contact.ppa_price
                except:
                    ppa_pricing = 0
                value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=str(plant.slug),
                                                           ts=starttime)
                if len(value) > 0:
                    revenue += value[0].generation * ppa_pricing if value[0].generation else 0.0
        elif plant is not None:
            ppa_pricing = 0
            try:
                energy_contact = EnergyContract.objects.get(start_date__lte=starttime,
                                                            end_date__gte=starttime, plant=plant)
                ppa_pricing = energy_contact.ppa_price
            except:
                ppa_pricing = 0
            value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=str(plant.slug),
                                                       ts=starttime)
            if len(value) > 0:
                revenue += value[0].generation * ppa_pricing if value[0].generation else 0.0
        return revenue
    except Exception as exception:
        print str(exception)
        return 0.0