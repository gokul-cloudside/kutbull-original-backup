from django.utils import timezone
from solarrms.solarutils import get_expected_energy, get_portfolio_predicted_energy_values_timeseries, get_predicted_energy_values_timeseries
from solarrms.models import PredictionData, PlantSummaryDetails, PlantCompleteValues
import numpy as np
import datetime
from helpdesk.models import Ticket
import json
import pytz
from solarrms2.generation.generation import generation
from solarrms2.alerts.alerts import gateway
import collections


def get_energy_prediction_data(starttime, endtime, plant):
    try:
        predicted_energy_value = 0.0
        predicted_values = PredictionData.objects.filter(timestamp_type='BASED_ON_START_TIME_SLOT',
                                                         count_time_period=900,
                                                         identifier=str(plant.slug),
                                                         stream_name='plant_energy',
                                                         model_name ='STATISTICAL_LATEST',
                                                         ts__gte=starttime,
                                                         ts__lte=endtime)
        for predicted_value in predicted_values:
            if float(predicted_value.value)>0:
                predicted_energy_value += float(predicted_value.value)
        return predicted_energy_value
    except Exception as exception:
        print("Error in getting predicted energy values : " + str(exception))

# get smb comparison details
def smb_comparison(*args, **kwargs):
    try:
        pass
    except Exception as exception:
        print str(exception)


# get predicted energy
# def predicted_energy(*args, **kwargs):
#     try:
#         plants_group=kwargs.pop('plants_group', None)
#         plant=kwargs.pop('plant', None)
#         starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
#         endtime=kwargs.pop('endtime',timezone.now())
#         predicted = 0.0
#         if plants_group is not None:
#             for plant in plants_group:
#                 predicted_energy_values = get_expected_energy(str(plant.slug), 'PLANT', starttime, endtime)
#                 if len(predicted_energy_values)>0:
#                     predicted += float(predicted_energy_values[0])
#         elif plant is not None:
#             predicted_energy_values = get_expected_energy(str(plant.slug), 'PLANT', starttime, endtime)
#             if len(predicted_energy_values)>0:
#                 predicted += float(predicted_energy_values[0])
#         return predicted
#     except Exception as exception:
#         print str(exception)

def predicted_energy(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',starttime+datetime.timedelta(days=1))
        predicted = 0.0
        predicted_list = []
        if plants_group is not None:
            for plant in plants_group:
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                predicted_list.append(predicted_energy_value)
            if len(predicted_list)>0:
                predicted = np.sum(predicted_list)
        elif plant is not None:
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            predicted_list.append(predicted_energy_value)
            if len(predicted_list)>0:
                predicted = np.sum(predicted_list)
        return predicted
    except Exception as exception:
        print str(exception)


def predicted_energy_tomorrow(*args, **kwargs):
    try:
        plants_group = kwargs.pop('plants_group', None)
        plant = kwargs.pop('plant', None)
        starttime = kwargs.pop('starttime', timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        starttime = starttime + datetime.timedelta(days=1)
        endtime = kwargs.pop('endtime', starttime + datetime.timedelta(days=1))
        predicted = 0.0
        predicted_list = []
        if plants_group is not None:
            for plant in plants_group:
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                predicted_list.append(predicted_energy_value)
            if len(predicted_list) > 0:
                predicted = np.sum(predicted_list)
        elif plant is not None:
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            predicted_list.append(predicted_energy_value)
            if len(predicted_list) > 0:
                predicted = np.sum(predicted_list)
        return predicted
    except Exception as exception:
        print str(exception)


# get inverter comparison details
def inverter_comparison(*args, **kwargs):
    try:
        pass
    except Exception as exception:
        print str(exception)

# get cleaning details
def cleaning(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        meter=kwargs.pop('meter', None)
        inverter=kwargs.pop('inverter', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        inverters_cleaning_list = []
        inverter_details = []
        final_result = {}
        if plants_group is not None:
            for plant in plants_group:
                errors = []
                plant_panel_cleaning_details = {}
                plant_result = {}
                plant_result['plant_name'] = str(plant.name)
                plant_result['plant_slug'] = str(plant.slug)
                panel_cleaning_details = Ticket.get_plant_live_ops_summary(plant, ['PANEL_CLEANING'])
                if len(panel_cleaning_details)>0:
                    try:
                        inverters_cleaning_list.extend(panel_cleaning_details['PANEL_CLEANING']['details'].keys())
                    except:
                        pass
                    try:
                        if len(panel_cleaning_details['PANEL_CLEANING'])>0:
                            plant_panel_cleaning_details['ticket_id'] = int(panel_cleaning_details['PANEL_CLEANING']['ticket_id'])
                            plant_panel_cleaning_details['devices'] = ",".join(panel_cleaning_details['PANEL_CLEANING']['details'].keys())
                            plant_panel_cleaning_details['event_type'] = 'PANEL_CLEANING'
                            if len(plant_panel_cleaning_details)>0:
                                errors.append(plant_panel_cleaning_details)
                    except:
                        pass
                    plant_result["errors"] = errors
                    inverter_details.append(plant_result)
        elif plant is not None:
            errors = []
            plant_panel_cleaning_details = {}
            plant_result = {}
            plant_result['plant_name'] = str(plant.name)
            plant_result['plant_slug'] = str(plant.slug)
            panel_cleaning_details = Ticket.get_plant_live_ops_summary(plant, ['PANEL_CLEANING'])
            if len(panel_cleaning_details)>0:
                try:
                    inverters_cleaning_list.extend(panel_cleaning_details['PANEL_CLEANING']['details'].keys())
                except:
                    pass
                try:
                    if len(panel_cleaning_details['PANEL_CLEANING'])>0:
                        plant_panel_cleaning_details['ticket_id'] = int(panel_cleaning_details['PANEL_CLEANING']['ticket_id'])
                        plant_panel_cleaning_details['devices'] = ",".join(panel_cleaning_details['PANEL_CLEANING']['details'].keys())
                        plant_panel_cleaning_details['event_type'] = 'PANEL_CLEANING'
                        if len(plant_panel_cleaning_details)>0:
                            errors.append(plant_panel_cleaning_details)
                except:
                    pass
                plant_result["errors"] = errors
                inverter_details.append(plant_result)

        final_result['error_details'] = inverter_details
        final_result['inverters_required_cleaning'] = len(inverters_cleaning_list)
        return final_result
    except Exception as exception:
        print str(exception)


# get mppt comparison details
def mppt_comparison(*args, **kwargs):
    try:
        pass
    except Exception as exception:
        print str(exception)


# get time series predicted energy at portfolio and plant level

# def predicted_timeseries(*args, **kwargs):
#     try:
#         final_result = {}
#         plants_group=kwargs.pop('plants_group', None)
#         plant=kwargs.pop('plant', None)
#         starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
#         endtime=kwargs.pop('endtime',starttime+datetime.timedelta(days=1))
#         if plants_group is not None:
#             for model in ['STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL']:
#                 final_result[model]= json.loads(get_portfolio_predicted_energy_values_timeseries(starttime, endtime-datetime.timedelta(minutes=15), plants_group, model, 900, False))
#         elif plant is not None:
#             for model in ['STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL']:
#                 final_result[model] = json.loads(get_predicted_energy_values_timeseries(starttime, endtime-datetime.timedelta(minutes=15), plant, model, 900, False))
#         return final_result
#     except Exception as exception:
#         print str(exception)

def predicted_timeseries(*args, **kwargs):
    try:
        final_result = {}
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        starttime=kwargs.pop('starttime', timezone.now())
        try:
            try:
                if plant is None:
                    plant = plants_group[0]
                    local_timezone = plant.metadata.plantmetasource.dataTimezone
                else:
                    local_timezone = plant.metadata.plantmetasource.dataTimezone

            except:
                local_timezone = "Asia/Kolkata"
            if starttime.tzinfo is None:
                tz = pytz.utc
                starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(local_timezone))
            starttime = starttime.replace(hour=6, minute=0, second=0, microsecond=0)
        except Exception as exception:
            print str(exception)
            starttime = starttime
        endtime=kwargs.pop('endtime',starttime+datetime.timedelta(hours=13))
        if plants_group is not None:
            for model in ['STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL']:
                final_result[model]= json.loads(get_portfolio_predicted_energy_values_timeseries(starttime, endtime-datetime.timedelta(minutes=15), plants_group, model, 900, False))
        elif plant is not None:
            for model in ['STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL']:
                final_result[model] = json.loads(get_predicted_energy_values_timeseries(starttime, endtime-datetime.timedelta(minutes=15), plant, model, 900, False))
        return final_result
    except Exception as exception:
        print str(exception)


def get_new_plant_summary_specific_date_widgets(starttime, endtime, plant):
    try:
        final_values = collections.OrderedDict()
        while endtime>starttime:
            plant_values = {}
            plant_values['generation'] = 0.0
            plant_values['performance_ratio'] = 0.0
            plant_values['cuf'] = 0.0
            plant_values['specific_yield'] = 0.0
            plant_values['dc_loss'] = 0.0
            plant_values['conversion_loss'] = 0.0
            plant_values['ac_loss'] = 0.0
            plant_values['grid_availability'] = 0.0
            plant_values['equipment_availability'] = 0.0
            plant_values['insolation'] = 0.0
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=86400,
                                                                      identifier=str(plant.slug),
                                                                      ts=starttime)

            if len(plant_summary_values)>0:
                value = plant_summary_values[0]
                plant_values['generation'] = value.generation
                plant_values['plant_co2'] = float(plant_values['generation'])*0.7 if value.generation else 0.0
                plant_values['generation'] = plant_values['generation'] if value.generation else 0.0
                plant_values['performance_ratio'] = "{0:.2f}".format(float(value.performance_ratio)) if value.performance_ratio else 0.0
                plant_values['cuf'] = "{0:.2f}".format(float(value.cuf)) if value.cuf else 0.0
                plant_values['specific_yield'] = "{0:.2f}".format(float(value.specific_yield)) if value.specific_yield else 0.0
                plant_values['dc_loss'] = value.dc_loss if value.dc_loss else None
                plant_values['conversion_loss'] = value.conversion_loss if value.conversion_loss else None
                plant_values['ac_loss'] = value.ac_loss if value.ac_loss else None
                plant_values['grid_availability'] = "{0:.2f}".format(float(value.grid_availability)) if value.grid_availability else 100.0
                plant_values['equipment_availability'] = "{0:.2f}".format(float(value.equipment_availability)) if value.equipment_availability else 100.0
                plant_values['insolation'] = "{0:.2f}".format(float(value.average_irradiation)) if value.average_irradiation else 0.0
                plant_values['timestamp'] = str(value.ts)
            final_values[str(starttime.date())] = plant_values
            starttime = starttime+datetime.timedelta(days=1)
        return final_values
    except Exception as exception:
        print(str(exception))
        return {}


def analytics_dashboard(*args, **kwargs):
    try:
        final_result = {}
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        endtime=kwargs.pop('endtime',timezone.now()+datetime.timedelta(days=1))
        starttime=kwargs.pop('starttime', None)
        if plant is None and plants_group is not None:
            plant = plants_group[0]
        if endtime.tzinfo is None:
            endtime = pytz.utc.localize(endtime)
        endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        endtime = endtime.replace(hour=0, minute=0, second=0, microsecond=0)
        if starttime is None:
            starttime = endtime - datetime.timedelta(days=7)
        else:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
        if plants_group is not None:
            for plant in plants_group:
                final_result[str(plant.slug)] = get_new_plant_summary_specific_date_widgets(starttime, endtime, plant)
        elif plant is not None:
            final_result[str(plant.slug)] = get_new_plant_summary_specific_date_widgets(starttime, endtime, plant)
        return final_result
    except Exception as exception:
        print(str(exception))
        return {}


def prediction_deviation(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',starttime+datetime.timedelta(days=1))
        deviation_list = []

        try:
            starttime_prediction = starttime
            starttime_prediction = starttime_prediction.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            endtime_prediction = timezone.now().astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime_prediction = starttime_prediction.astimezone(pytz.timezone("Asia/Kolkata"))
            endtime_prediction = timezone.now().astimezone(pytz.timezone("Asia/Kolkata"))

        starttime_prediction  = starttime_prediction.replace(hour=6, minute=0, second=0, microsecond=0)
        duration_hours = ((endtime_prediction-datetime.timedelta(minutes=15)) - starttime_prediction).total_seconds()/3600
        final_duration_hours = min(duration_hours, 12)
        predicted_energy_list = []
        actual_energy_list = []
        capacity_list = []

        if plants_group is not None:
            for plant in plants_group:
                #gateway_alerts = gateway(plant=plant, starttime=starttime, endtime=endtime)
                actual_generation = generation(plant=plant, starttime=starttime, endtime=endtime-datetime.timedelta(minutes=15))
                predicted_generation = predicted_energy(plant=plant, starttime=starttime, endtime=timezone.now()-datetime.timedelta(minutes=15))
                #if gateway_alerts['gateways_disconnected'] == 0 and gateway_alerts['gateways_powered_off'] == 0:
                predicted_energy_list.append(predicted_generation)
                actual_energy_list.append(actual_generation)
                capacity_list.append(plant.capacity)
            total_predicted_generation = np.sum(predicted_energy_list)
            total_actual_generation = np.sum(actual_energy_list)
            total_capacity = np.sum(capacity_list)
            deviation = abs(((float(total_predicted_generation)-float(total_actual_generation))/(float(total_capacity)*final_duration_hours))*100)
            return deviation
        elif plant is not None:
            #gateway_alerts = gateway(plant=plant, starttime=starttime, endtime=endtime)
            actual_generation = generation(plant=plant, starttime=starttime, endtime=endtime-datetime.timedelta(minutes=15))
            predicted_generation = predicted_energy(plant=plant, starttime=starttime, endtime=timezone.now()-datetime.timedelta(minutes=15))
            #if gateway_alerts['gateways_disconnected'] == 0 and gateway_alerts['gateways_powered_off'] == 0:
            predicted_energy_list.append(predicted_generation)
            actual_energy_list.append(actual_generation)
            capacity_list.append(plant.capacity)
            total_predicted_generation = np.sum(predicted_energy_list)
            total_actual_generation = np.sum(actual_energy_list)
            total_capacity = np.sum(capacity_list)
            deviation = abs(((float(total_predicted_generation)-float(total_actual_generation))/(float(total_capacity)*final_duration_hours))*100)
            return deviation

    except Exception as exception:
        print(str(exception))
        return "NA"


def predicted_energy_till_time(*args, **kwargs):
    try:
        plants_group = kwargs.pop('plants_group', None)
        plant = kwargs.pop('plant', None)
        starttime = kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime = starttime.replace(hour=23, minute=59, second=59, microsecond=999999)
        if starttime.date() == timezone.now().date():
            endtime = kwargs.pop('endtime', timezone.now())
        predicted = 0.0
        predicted_list = []
        if plants_group is not None:
            for plant in plants_group:
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                predicted_list.append(predicted_energy_value)
            if len(predicted_list)>0:
                predicted = np.sum(predicted_list)
        elif plant is not None:
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            predicted_list.append(predicted_energy_value)
            if len(predicted_list)>0:
                predicted = np.sum(predicted_list)
        return predicted
    except Exception as exception:
        print str(exception)

