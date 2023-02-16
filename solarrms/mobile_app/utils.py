from solarrms.models import PlantCompleteValues, SolarPlant, SpecificYieldTable
from django.conf import settings
from monitoring.views import get_user_data_monitoring_status
from django.utils import timezone
import pytz
from solarrms.cron_solar_events import check_network_for_virtual_gateways
import logging
#from solarrms.api_views import get_energy_prediction_data, fix_generation_units, fix_capacity_units, fix_co2_savings
from solarrms.settings import LAST_CAPACITY_DAYS
from dashboards.models import DataglenClient
from helpdesk.models import Ticket
import numpy as np
from solarrms.solar_plants_groups import k_means_groups
from solarrms.api_views import fix_generation_units, fix_capacity_units, fix_co2_savings
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import get_power_irradiation_mobile
import datetime
from solarrms.models import KWHPerMeterSquare
import json
from solarrms2.analytics.analytics import get_energy_prediction_data, prediction_deviation

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


# Method to get client parameters from plants which are not computed using cronjob at client level for CEO.
def get_client_owner_plant_status_ceo(plant, current_time, final_values_temp):
    try:
        if plant.commissioned_date and ((current_time.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
            final_values_temp['total_capacity_past_month'].append(plant.capacity)
        plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
        if len(plant_network_details)>0:
            final_values_temp['plants_disconnected'].append(str(plant.slug))
            # try:
            #     final_values_temp['gateways_disconnected'].extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
            # except:
            #     pass
            # try:
            #     final_values_temp['gateways_powered_off'].extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
            # except:
            #     pass
        starttime = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        endtime = current_time
        if str(plant.slug) not in final_values_temp['plants_disconnected']:
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            final_values_temp['predicted_energy'].append(float(predicted_energy_value))
            try:
                value_plant = PlantCompleteValues.objects.filter(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=plant.metadata.plantmetasource.sourceKey,
                    ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value_plant) > 0:
                    final_values_temp['total_energy_for_network_up_plants'].append(value_plant[0].plant_generation_today)
                    final_values_temp['total_capacity_for_network_up_plants'].append(value_plant[0].capacity)
            except Exception as exception:
                logger.debug(str(exception))
        return final_values_temp
    except Exception as exception:
        logger.debug(str(exception))
        return final_values_temp

# Method to get client parameters which are computed using cronjob at client level for CEO.
def get_client_owner_status_data_mobile_ceo(client, current_time, solar_plants, role):
    try:
        value_client = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                          identifier=client.slug,
                                                          ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
        final_values = {}
        final_values_temp = {}
        final_values_temp['total_capacity_past_month'] = []
        final_values_temp['plants_disconnected'] = []
        # final_values_temp['gateways_disconnected'] = []
        # final_values_temp['gateways_powered_off'] = []
        final_values_temp['predicted_energy'] = []
        final_values_temp['total_energy_for_network_up_plants'] = []
        final_values_temp['total_capacity_for_network_up_plants'] = []

        if len(value_client)>0:
            final_values['client_name'] = str(value_client[0].name)
            final_values['client_logo'] = str(client.dataglenclient.clientMobileLogo) if client.dataglenclient and client.dataglenclient.clientMobileLogo else ""
            final_values["total_capacity"] = fix_capacity_units(float(value_client[0].capacity))
            final_values["total_energy"] = fix_generation_units(float(value_client[0].total_generation))
            final_values["energy_today"] = float(value_client[0].plant_generation_today)
            final_values['total_diesel'] = "{0:.1f} L".format(float(final_values['energy_today'])/4.0)
            final_values["energy_today"] = fix_generation_units(float(final_values["energy_today"]))
            final_values["total_co2"] = fix_co2_savings(float(value_client[0].co2_savings))
            final_values["total_active_power"] = round(float(value_client[0].active_power),2)
        for plant in solar_plants:
            final_values_temp = get_client_owner_plant_status_ceo(plant, current_time, final_values_temp)
        final_values["total_capacity_past_month"] = fix_capacity_units(np.sum(final_values_temp["total_capacity_past_month"]) if len(final_values_temp["total_capacity_past_month"])>0 else 0.0)
        final_values["total_plants"] = len(solar_plants)
        final_values["total_connected_plants"] = len(solar_plants) - len(final_values_temp["plants_disconnected"])
        final_values["total_disconnected_plants"] = len(final_values_temp["plants_disconnected"])
        final_values['total_unmonitored_plants'] = 0
        # final_values["gateways_disconnected"] = len(final_values_temp["gateways_disconnected"])
        # final_values["gateways_powered_off"] = len(final_values_temp["gateways_powered_off"])
        if str(role).upper() == 'CEO':
            final_values['know_more'] = True
            try:
                final_values['prediction_deviation'] = prediction_deviation(plants_group=solar_plants)
                final_values['prediction_deviation'] = round(float(final_values['prediction_deviation']),2)
            except Exception as exception:
                print str(exception)
                final_values['prediction_deviation'] = 0.0
            # final_values['know_more'] = True
            # prediction_starttime = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            # duration_hours = (current_time - prediction_starttime).total_seconds() / 3600
            # final_duration_hours = min(duration_hours, 12)
            # predicted_energy_till_time = np.sum(final_values_temp["predicted_energy"]) if len(final_values_temp["predicted_energy"])>0 else 0.0
            # total_energy_for_network_up_plants = np.sum(final_values_temp["total_energy_for_network_up_plants"]) if len(final_values_temp["total_energy_for_network_up_plants"])>0 else 0.0
            # total_capacity_for_network_up_plants = np.sum(final_values_temp["total_capacity_for_network_up_plants"]) if len(final_values_temp["total_capacity_for_network_up_plants"])>0 else 0.0
            # try:
            #     final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time)-float(total_energy_for_network_up_plants))/(float(total_capacity_for_network_up_plants)*final_duration_hours))*100)
            #     final_values['prediction_deviation'] = round(float(final_values['prediction_deviation']),2)
            # except Exception as exception:
            #     logger.debug(str(exception))
            #     final_values['prediction_deviation'] = 0.0
        else:
            final_values['know_more'] = False
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return final_values


# Method to get plant parameters for non client owners CEO
def get_non_client_owner_plant_status_data_mobile_ceo(plant, current_time, final_values):
    try:
        plant_value = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            final_values["total_capacity"].append(float(value[0].capacity))
            final_values["total_energy"].append(float(value[0].total_generation))
            final_values["energy_today"].append(float(value[0].plant_generation_today))
            final_values["total_co2"].append(float(value[0].co2_savings))
            final_values["total_active_power"].append(float(value[0].active_power))
            if plant.commissioned_date and ((current_time.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
                final_values['total_capacity_past_month'].append(plant.capacity)
            plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
            if len(plant_network_details)>0:
                final_values['plants_disconnected'].append(str(plant.slug))
                # try:
                #     final_values['gateways_disconnected'].extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                # except:
                #     pass
                # try:
                #     final_values['gateways_powered_off'].extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                # except:
                #     pass
            starttime = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            endtime = current_time
            if str(plant.slug) not in final_values['plants_disconnected']:
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                final_values['predicted_energy'].append(float(predicted_energy_value))
                try:
                    value_plant = PlantCompleteValues.objects.filter(
                        timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                        identifier=plant.metadata.plantmetasource.sourceKey,
                        ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value_plant) > 0:
                        final_values['total_energy_for_network_up_plants'].append(
                            value_plant[0].plant_generation_today)
                        final_values['total_capacity_for_network_up_plants'].append(value_plant[0].capacity)
                except Exception as exception:
                    logger.debug(str(exception))
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return final_values


# Method to get the final values at client level for non client owners CEO
def get_final_non_client_owner_plant_status_data_mobile_ceo(solar_plants, current_time, role):
    try:
        final_values = {}
        final_values["total_capacity"] = []
        final_values["total_energy"] = []
        final_values["energy_today"] = []
        final_values["total_co2"] = []
        final_values["total_active_power"] = []
        final_values["total_capacity_past_month"] = []
        #final_values["today_predicted_energy_value_till_time"] = []
        final_values['plants_disconnected'] = []
        # final_values['gateways_disconnected'] = []
        # final_values['gateways_powered_off'] = []
        final_values['predicted_energy'] = []
        final_values['total_energy_for_network_up_plants'] = []
        final_values['total_capacity_for_network_up_plants'] = []
        for plant in solar_plants:
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            final_values =  get_non_client_owner_plant_status_data_mobile_ceo(plant, current_time, final_values)

        final_values['client_name'] = plant.groupClient.name if plant.groupClient else plant.name
        if str(role).upper().startswith("CLIENT"):
            try:
                final_values['client_logo'] = plant.dataglengroup.groupMobileLogo if plant.dataglengroup and plant.dataglengroup.groupMobileLogo else plant.groupClient.dataglenclient.clientMobileLogo
            except:
                final_values['client_logo'] = ""
        else:
            try:
                final_values['client_logo'] = str(
                    plant.groupClient.dataglenclient.clientMobileLogo) if plant.groupClient.dataglenclient and plant.groupClient.dataglenclient.clientMobileLogo else ""
            except:
                final_values['client_logo'] = ""
        final_values["total_capacity"] = fix_capacity_units(np.sum(final_values["total_capacity"]) if len(final_values["total_capacity"])>0 else 0.0)
        final_values["total_energy"] = fix_generation_units(np.sum(final_values["total_energy"]) if len(final_values["total_energy"])>0 else 0.0)
        final_values["energy_today"] = np.sum(final_values["energy_today"]) if len(final_values["energy_today"])>0 else 0.0
        final_values['total_diesel'] = "{0:.1f} L".format(float(final_values['energy_today'])/4.0)
        final_values["energy_today"] = fix_generation_units(float(final_values["energy_today"]))
        final_values["total_co2"] = fix_co2_savings(np.sum(final_values["total_co2"]) if len(final_values["total_co2"])>0 else 0.0)
        final_values["total_active_power"] = np.sum(final_values["total_active_power"]) if len(final_values["total_active_power"])>0 else 0.0
        final_values["total_active_power"] = round(float(final_values["total_active_power"]),2)
        final_values["total_capacity_past_month"] = fix_capacity_units(np.sum(final_values["total_capacity_past_month"]) if len(final_values["total_capacity_past_month"])>0 else 0.0)
        final_values["total_plants"] = len(solar_plants)
        final_values["total_connected_plants"] = len(solar_plants) - len(final_values["plants_disconnected"])
        final_values["total_disconnected_plants"] = len(final_values["plants_disconnected"])
        final_values['total_unmonitored_plants'] = 0
        # final_values["gateways_disconnected"] = len(final_values["gateways_disconnected"])
        # final_values["gateways_powered_off"] = len(final_values["gateways_powered_off"])
        if str(role).upper() == 'CEO':
            final_values['know_more'] = True
            # prediction_starttime = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            # duration_hours = (current_time - prediction_starttime).total_seconds() / 3600
            # final_duration_hours = min(duration_hours, 12)
            # predicted_energy_till_time = np.sum(final_values["predicted_energy"]) if len(final_values["predicted_energy"])>0 else 0.0
            # total_energy_for_network_up_plants = np.sum(final_values["total_energy_for_network_up_plants"]) if len(final_values["total_energy_for_network_up_plants"])>0 else 0.0
            # total_capacity_for_network_up_plants = np.sum(final_values["total_capacity_for_network_up_plants"]) if len(final_values["total_capacity_for_network_up_plants"])>0 else 0.0
            # try:
            #     final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time)-float(total_energy_for_network_up_plants))/(float(total_capacity_for_network_up_plants)*final_duration_hours))*100)
            # except Exception as exception:
            #     logger.debug(str(exception))
            #     final_values['prediction_deviation'] = 0.0
            try:
                final_values['prediction_deviation'] = prediction_deviation(plants_group=solar_plants)
                final_values['prediction_deviation'] = round(float(final_values['prediction_deviation']),2)
            except Exception as exception:
                print str(exception)
                final_values['prediction_deviation'] = 0.0
        else:
            final_values['know_more'] = False
        final_values.pop('plants_disconnected', None)
        final_values.pop('predicted_energy', None)
        final_values.pop('total_capacity_for_network_up_plants', None)
        final_values.pop('total_energy_for_network_up_plants', None)
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return final_values


# Method to get client parameters from plants which are not computed using cronjob at client level for CEO.
def get_client_owner_plant_status_OandM_Manager(plant, current_time, final_values_temp):
    try:
        if plant.commissioned_date and ((current_time.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
            final_values_temp['total_capacity_past_month'].append(plant.capacity)
        plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
        if len(plant_network_details)>0:
            final_values_temp['plants_disconnected'].append(str(plant.slug))
            # try:
            #     final_values_temp['gateways_disconnected'].extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
            # except:
            #     pass
            # try:
            #     final_values_temp['gateways_powered_off'].extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
            # except:
            #     pass
        starttime = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        endtime = current_time
        if str(plant.slug) not in final_values_temp['plants_disconnected']:
            predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
            final_values_temp['predicted_energy'].append(float(predicted_energy_value))
            try:
                value_plant = PlantCompleteValues.objects.filter(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=plant.metadata.plantmetasource.sourceKey,
                    ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value_plant) > 0:
                    final_values_temp['total_energy_for_network_up_plants'].append(
                        value_plant[0].plant_generation_today)
                    final_values_temp['total_capacity_for_network_up_plants'].append(value_plant[0].capacity)
            except Exception as exception:
                logger.debug(str(exception))
        specific_yield_value = SpecificYieldTable.objects.filter(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
            identifier=plant.metadata.plantmetasource.sourceKey).limit(1)
        if len(specific_yield_value)>0:
            final_values_temp['specific_yield'].append(float(specific_yield_value[0].specific_yield))
        return final_values_temp
    except Exception as exception:
        logger.debug(str(exception))
        return final_values_temp

# Method to get client parameters which are computed using cronjob at client level for O & M Manager.
def get_client_owner_status_data_mobile_OandM_Manager(client, current_time, solar_plants,role):
    try:
        value_client = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                          identifier=client.slug,
                                                          ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
        final_values = {}
        final_values_temp = {}
        final_values_temp['total_capacity_past_month'] = []
        final_values_temp['plants_disconnected'] = []
        # final_values_temp['gateways_disconnected'] = []
        # final_values_temp['gateways_powered_off'] = []
        final_values_temp['predicted_energy'] = []
        final_values_temp['total_energy_for_network_up_plants'] = []
        final_values_temp['total_capacity_for_network_up_plants'] = []
        final_values_temp['specific_yield'] = []
        plant_slugs = []
        if len(value_client)>0:
            final_values['client_name'] = str(value_client[0].name)
            if final_values['client_name'] == "Jackson":
                final_values['client_name'] = "Jakson Solar"
            final_values['client_logo'] = str(client.dataglenclient.clientMobileLogo) if client.dataglenclient and client.dataglenclient.clientMobileLogo else ""
            final_values["total_capacity"] = fix_capacity_units(float(value_client[0].capacity))
            final_values["total_energy"] = fix_generation_units(float(value_client[0].total_generation))
            final_values["energy_today"] = float(value_client[0].plant_generation_today)
            #final_values['total_diesel'] = "{0:.1f} L".format(float(final_values['energy_today'])/4.0)
            final_values["energy_today"] = fix_generation_units(float(value_client[0].plant_generation_today))
            #final_values["total_co2"] = fix_co2_savings(float(value_client[0].co2_savings))
            final_values["total_active_power"] = round(float(value_client[0].active_power),2)
            final_values['average_pr'] = "{0:.2f}".format(value_client[0].pr*100) + " %" if value_client[0].pr else "0.0 %"
            final_values['average_cuf'] = "{0:.2f}".format(value_client[0].cuf*100) + " %" if value_client[0].cuf else "0.0 %"
        for plant in solar_plants:
            final_values_temp = get_client_owner_plant_status_OandM_Manager(plant, current_time, final_values_temp)
            plant_slugs.append(str(plant.slug))
        final_values["total_capacity_past_month"] = np.sum(final_values_temp["total_capacity_past_month"]) if len(final_values_temp["total_capacity_past_month"])>0 else 0.0
        final_values["total_capacity_past_month"] = fix_capacity_units(final_values["total_capacity_past_month"])
        final_values["total_plants"] = len(solar_plants)
        final_values["total_connected_plants"] = len(solar_plants) - len(final_values_temp["plants_disconnected"])
        final_values["total_disconnected_plants"] = len(final_values_temp["plants_disconnected"])
        final_values['total_unmonitored_plants'] = 0
        final_values['specific_yield'] = "{0:.2f}".format(np.average(final_values_temp['specific_yield'])) if len(final_values_temp['specific_yield'])>0 else 0.0
        # final_values["gateways_disconnected"] = len(final_values_temp["gateways_disconnected"])
        # final_values["gateways_powered_off"] = len(final_values_temp["gateways_powered_off"])
        if str(role).upper() in ['CEO','O&M_MANAGER']:
            final_values['know_more'] = True
            final_values['tickets_tab'] = True
            # prediction_starttime = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            # duration_hours = (current_time - prediction_starttime).total_seconds() / 3600
            # final_duration_hours = min(duration_hours, 12)
            # predicted_energy_till_time = np.sum(final_values_temp["predicted_energy"]) if len(final_values_temp["predicted_energy"])>0 else 0.0
            # total_energy_for_network_up_plants = np.sum(final_values_temp["total_energy_for_network_up_plants"]) if len(final_values_temp["total_energy_for_network_up_plants"])>0 else 0.0
            # total_capacity_for_network_up_plants = np.sum(final_values_temp["total_capacity_for_network_up_plants"]) if len(final_values_temp["total_capacity_for_network_up_plants"])>0 else 0.0
            # try:
            #     final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time)-float(total_energy_for_network_up_plants))/(float(total_capacity_for_network_up_plants)*final_duration_hours))*100)
            # except Exception as exception:
            #     logger.debug(str(exception))
            #     final_values['prediction_deviation'] = 0.0
            try:
                final_values['prediction_deviation'] = prediction_deviation(plants_group=solar_plants)
                final_values['prediction_deviation'] = round(float(final_values['prediction_deviation']),2)
            except Exception as exception:
                print str(exception)
                final_values['prediction_deviation'] = 0.0
        else:
            final_values['know_more'] = False
            final_values['tickets_tab'] = False
        no_of_groups = len(solar_plants) if len(solar_plants) < 5 else 5
        plant_groups = k_means_groups(plant_slugs, no_of_groups, True)
        try:
            energy_groups = select_plant_ceo_details(solar_plants, current_time, role, groups=True)
            final_values['energy_groups'] = energy_groups['groups']
        except:
            final_values['energy_groups'] = []
        groups = []
        if len(plant_groups)>0:
            for key in plant_groups.keys():
                try:
                    plant_group = {}
                    plant_group['group_name'] = plant_groups[key]['group_name']
                    plant_group['lat'] = plant_groups[key]['lat']
                    plant_group['long'] = plant_groups[key]['long']
                    plant_group['tickets_summary'] = plant_groups[key]['tickets_summary']
                    groups.append(plant_group)
                except:
                    continue
        final_values['groups'] = groups
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return final_values

# Method to get plant parameters for non client owners O & M Managers
def get_non_client_owner_plant_status_data_mobile_OandM_Manager(plant, current_time, final_values):
    try:
        plant_value = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            final_values["total_capacity"].append(float(value[0].capacity))
            final_values["total_energy"].append(float(value[0].total_generation))
            final_values["energy_today"].append(float(value[0].plant_generation_today))
            final_values["total_co2"].append(float(value[0].co2_savings))
            final_values["total_active_power"].append(float(value[0].active_power))
            if plant.commissioned_date and ((current_time.date() - plant.commissioned_date).total_seconds()/(86400) < float(LAST_CAPACITY_DAYS)):
                final_values['total_capacity_past_month'].append(plant.capacity)
            plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
            if len(plant_network_details)>0:
                final_values['plants_disconnected'].append(str(plant.slug))
                # try:
                #     final_values['gateways_disconnected'].extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                # except:
                #     pass
                # try:
                #     final_values['gateways_powered_off'].extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                # except:
                #     pass
            try:
                value_plant = PlantCompleteValues.objects.filter(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=plant.metadata.plantmetasource.sourceKey,
                    ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value_plant)>0:
                    if float(value_plant[0].pr) <=1:
                        final_values['average_pr'].append(float(value_plant[0].pr))
                    final_values['average_cuf'].append(float(value_plant[0].cuf))
            except Exception as exception:
                logger.debug(str(exception))
            specific_yield_value = SpecificYieldTable.objects.filter(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
            identifier=plant.metadata.plantmetasource.sourceKey).limit(1)
        if len(specific_yield_value)>0:
            final_values['specific_yield'].append(float(specific_yield_value[0].specific_yield))
            starttime = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            endtime = current_time
            if str(plant.slug) not in final_values['plants_disconnected']:
                predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                final_values['predicted_energy'].append(float(predicted_energy_value))
                if len(value_plant) > 0:
                    final_values['total_energy_for_network_up_plants'].append(
                        value_plant[0].plant_generation_today)
                    final_values['total_capacity_for_network_up_plants'].append(value_plant[0].capacity)
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return final_values

# Method to get the final values at client level for non client owners O & M Managers
def get_final_non_client_owner_plant_status_data_mobile_OandM_Manager(solar_plants, current_time,role):
    try:
        final_values = {}
        final_values["total_capacity"] = []
        final_values["total_energy"] = []
        final_values["energy_today"] = []
        final_values["total_co2"] = []
        final_values["total_active_power"] = []
        final_values["total_capacity_past_month"] = []
        #final_values["today_predicted_energy_value_till_time"] = []
        final_values['plants_disconnected'] = []
        # final_values['gateways_disconnected'] = []
        # final_values['gateways_powered_off'] = []
        final_values['predicted_energy'] = []
        final_values['total_energy_for_network_up_plants'] = []
        final_values['total_capacity_for_network_up_plants'] = []
        final_values['specific_yield'] = []
        final_values['average_pr'] = []
        final_values['average_cuf'] = []
        plant_slugs = []
        for plant in solar_plants:
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            final_values =  get_non_client_owner_plant_status_data_mobile_OandM_Manager(plant, current_time, final_values)
            plant_slugs.append(str(plant.slug))
            if str(role).upper().startswith("CLIENT"):
                try:
                    final_values['client_logo'] = plant.dataglengroup.groupMobileLogo if plant.dataglengroup and plant.dataglengroup.groupMobileLogo else plant.groupClient.dataglenclient.clientMobileLogo
                except:
                    final_values['client_logo'] = ""
            else:
                try:
                    final_values['client_logo'] = str(
                        plant.groupClient.dataglenclient.clientMobileLogo) if plant.groupClient.dataglenclient and plant.groupClient.dataglenclient.clientMobileLogo else ""
                except:
                    final_values['client_logo'] = ""

        final_values['client_name'] = plant.groupClient.name if plant.groupClient else plant.name
        final_values["total_capacity"] = fix_capacity_units(np.sum(final_values["total_capacity"]) if len(final_values["total_capacity"])>0 else 0.0)
        final_values["total_energy"] = fix_generation_units(np.sum(final_values["total_energy"]) if len(final_values["total_energy"])>0 else 0.0)
        final_values["energy_today"] = np.sum(final_values["energy_today"]) if len(final_values["energy_today"])>0 else 0.0
        #final_values['total_diesel'] = "{0:.1f} L".format(float(final_values['energy_today'])/4.0)
        final_values["energy_today"] = fix_generation_units(float(final_values["energy_today"]))
        #final_values["total_co2"] = fix_co2_savings(np.sum(final_values["total_co2"]) if len(final_values["total_co2"])>0 else 0.0)
        final_values["total_active_power"] = np.sum(final_values["total_active_power"]) if len(final_values["total_active_power"])>0 else 0.0
        final_values["total_active_power"] = round(float(final_values["total_active_power"]),2)
        final_values["total_capacity_past_month"] = fix_capacity_units(np.sum(final_values["total_capacity_past_month"]) if len(final_values["total_capacity_past_month"])>0 else 0.0)
        final_values["total_plants"] = len(solar_plants)
        final_values["total_connected_plants"] = len(solar_plants) - len(final_values["plants_disconnected"])
        final_values["total_disconnected_plants"] = len(final_values["plants_disconnected"])
        final_values['total_unmonitored_plants'] = 0
        final_values['specific_yield'] = "{0:.2f}".format(np.average(final_values['specific_yield'])) if len(final_values['specific_yield'])>0 else 0.0
        final_values['average_pr'] = "{0:.2f}".format(np.average(final_values['average_pr'])*100) + " %" if len(final_values['average_pr'])>0 else "0.0 %"
        final_values['average_cuf'] = "{0:.2f}".format(np.average(final_values['average_cuf'])*100) + " %" if len(final_values['average_cuf'])>0 else "0.0 %"
        # final_values["gateways_disconnected"] = len(final_values["gateways_disconnected"])
        # final_values["gateways_powered_off"] = len(final_values["gateways_powered_off"])
        if str(role).upper() in ['CEO','O&M_MANAGER']:
            final_values['know_more'] = True
            final_values['tickets_tab'] = True
            # prediction_starttime = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            # duration_hours = (current_time - prediction_starttime).total_seconds() / 3600
            # final_duration_hours = min(duration_hours, 12)
            # predicted_energy_till_time = np.sum(final_values["predicted_energy"]) if len(
            #     final_values["predicted_energy"]) > 0 else 0.0
            # total_energy_for_network_up_plants = np.sum(final_values["total_energy_for_network_up_plants"]) if len(
            #     final_values["total_energy_for_network_up_plants"]) > 0 else 0.0
            # total_capacity_for_network_up_plants = np.sum(final_values["total_capacity_for_network_up_plants"]) if len(
            #     final_values["total_capacity_for_network_up_plants"]) > 0 else 0.0
            # try:
            #     final_values['prediction_deviation'] = abs(((float(predicted_energy_till_time) - float(
            #         total_energy_for_network_up_plants)) / (float(
            #         total_capacity_for_network_up_plants) * final_duration_hours)) * 100)
            # except Exception as exception:
            #     logger.debug(str(exception))
            #     final_values['prediction_deviation'] = 0.0
            try:
                final_values['prediction_deviation'] = prediction_deviation(plants_group=solar_plants)
                final_values['prediction_deviation'] = round(float(final_values['prediction_deviation']),2)
            except Exception as exception:
                print str(exception)
                final_values['prediction_deviation'] = 0.0
        else:
            final_values['know_more'] = False
            final_values['tickets_tab'] = False
        final_values.pop('plants_disconnected', None)
        final_values.pop('predicted_energy', None)
        final_values.pop('total_capacity_for_network_up_plants', None)
        final_values.pop('total_energy_for_network_up_plants', None)
        final_values.pop('total_co2', None)

        try:
            energy_groups = select_plant_ceo_details(solar_plants, current_time, role, groups=True)
            final_values['energy_groups'] = energy_groups['groups']
        except:
            final_values['energy_groups'] = []


        no_of_groups = len(solar_plants) if len(solar_plants) < 5 else 5
        plant_groups = k_means_groups(plant_slugs, no_of_groups, True)
        groups = []
        if len(plant_groups)>0:
            for key in plant_groups.keys():
                try:
                    plant_group = {}
                    plant_group['group_name'] = plant_groups[key]['group_name']
                    plant_group['lat'] = plant_groups[key]['lat']
                    plant_group['long'] = plant_groups[key]['long']
                    plant_group['tickets_summary'] = plant_groups[key]['tickets_summary']
                    groups.append(plant_group)
                except:
                    continue
        final_values['groups'] = groups
        #final_values["today_predicted_energy_value_till_time"] = np.sum(final_values["today_predicted_energy_value_till_time"]) if len(final_values["today_predicted_energy_value_till_time"])>0 else 0.0
        return final_values
    except Exception as exception:
        logger.debug(str(exception))
        return final_values


# Method to get individual plant generation details
def individual_plant_generation_details(plant, current_time, generation_details):
    try:
        generation_detail = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
        generation_detail['plant_name'] = str(plant.name)
        generation_detail['plant_slug'] = str(plant.slug)
        generation_detail['plant_capacity'] = fix_capacity_units(float(plant.capacity))
        if len(value)>0:
            generation_detail['generation'] = fix_generation_units(float(value[0].plant_generation_today)) if value[0].plant_generation_today else '0.0 kWh'
            generation_detail['power'] = "{0:.2f}".format(float(value[0].active_power)) if value[0].active_power else 0.0
        else:
            generation_detail['generation'] = '0.0 kWh'
            generation_detail['power'] = '0.0'
        generation_details.append(generation_detail)
        return generation_details
    except Exception as exception:
        print str(exception)

# Method to get individual group plant generation details
def individual_group_plant_generation_details(plant, current_time, plant_group):
    try:
        plant_group['group_plants_capacity'].append(float(plant.capacity))
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            plant_group['group_plants_generation'].append(float(value[0].plant_generation_today))
            plant_group['group_plants_power'].append(float(value[0].active_power))
        return plant_group
    except Exception as exception:
        print str(exception)

# Method to get select a plant details based on generation
def select_plant_ceo_details(solar_plants, current_time, role, groups=False):
    try:
        final_values = {}
        plant_slugs = []
        generation_details = []
        for plant in solar_plants:
            plant_slugs.append(str(plant.slug))
            generation_details = individual_plant_generation_details(plant, current_time, generation_details)
        final_values['generation_details'] = generation_details

        if groups:
            no_of_groups = len(solar_plants) if len(solar_plants) < 5 else 5
            plant_groups = k_means_groups(plant_slugs, no_of_groups, True)
            groups = []
            if len(plant_groups)>0:
                for key in plant_groups.keys():
                    try:
                        plant_group = {}
                        plant_group['group_name'] = plant_groups[key]['group_name']
                        plant_group['lat'] = plant_groups[key]['lat']
                        plant_group['long'] = plant_groups[key]['long']
                        group_plants = plant_groups[key]['plants']
                        plant_group['group_plants_generation'] = []
                        plant_group['group_plants_power'] = []
                        plant_group['group_plants_capacity'] = []
                        for plant in group_plants:
                            plant_group = individual_group_plant_generation_details(plant, current_time, plant_group)
                        plant_group['generation'] = fix_generation_units(np.sum(plant_group["group_plants_generation"]) if len(plant_group["group_plants_generation"])>0 else 0.0)
                        plant_group['power'] = "{0:.2f}".format(np.sum(plant_group["group_plants_power"])) if len(plant_group["group_plants_power"])>0 else 0.0
                        plant_group['group_capacity'] = fix_capacity_units(np.sum(plant_group["group_plants_capacity"]) if len(plant_group["group_plants_capacity"])>0 else '0.0 kW')
                        plant_group.pop('group_plants_generation', None)
                        plant_group.pop('group_plants_power', None)
                        plant_group.pop('group_plants_capacity', None)
                        groups.append(plant_group)
                    except:
                        continue

            final_values['groups'] = groups
        return final_values
    except Exception as exception:
        print str(exception)

# Method to get individual plant ticket details
def individual_plant_ticket_details(plant, current_time, ticket_details):
    try:
        ticket_detail = Ticket.get_plant_live_priority_summary(plant)
        ticket_detail['plant_name'] = str(plant.name)
        ticket_detail['plant_slug'] = str(plant.slug)
        ticket_details.append(ticket_detail)
        return ticket_details
    except Exception as exception:
        print str(exception)

# Method to get select a plant details based on tickets
def select_plant_for_OandM_details(solar_plants, current_time, role, groups=False):
    try:
        final_values = {}
        plant_slugs = []
        ticket_details = []
        for plant in solar_plants:
            plant_slugs.append(str(plant.slug))
            ticket_details = individual_plant_ticket_details(plant, current_time, ticket_details)
        final_values['ticket_details'] = ticket_details
        if groups:
            no_of_groups = len(solar_plants) if len(solar_plants) < 5 else 5
            plant_groups = k_means_groups(plant_slugs, no_of_groups, True)
            groups = []
            if len(plant_groups)>0:
                for key in plant_groups.keys():
                    try:
                        plant_group = {}
                        plant_group['group_name'] = plant_groups[key]['group_name']
                        plant_group['lat'] = plant_groups[key]['lat']
                        plant_group['long'] = plant_groups[key]['long']
                        plant_group['tickets_summary'] = plant_groups[key]['tickets_summary']
                        groups.append(plant_group)
                    except:
                        continue
            final_values['groups'] = groups
        return final_values
    except Exception as exception:
        print str(exception)

# Method to get select a plant details for client's roles (CEO, O&M Manager, Site Engineer)
def select_plant_for_client_roles(solar_plants, current_time, role):
    try:
        final_values = {}
        o_and_m_details = select_plant_for_OandM_details(solar_plants, current_time, role, groups=True)
        if o_and_m_details:
            final_values.update(o_and_m_details)
        ceo_details= select_plant_ceo_details(solar_plants, current_time, role, groups=False)
        final_values.update(ceo_details)
        final_values['tickets'] = True
        final_values['generation'] = True
        return final_values
    except Exception as exception:
        print str(exception)

# Method to get select a plant details for client's client's roles (Client CEO, Client O&M Manager, Client Site Engineer)
def select_plant_for_clients_client_roles(solar_plants, current_time, role):
    try:
        final_values = {}
        ceo_details = select_plant_ceo_details(solar_plants, current_time, role, groups=True)
        final_values.update(ceo_details)
        final_values['tickets'] = False
        final_values['generation'] = True
        return final_values
    except Exception as exception:
        print str(exception)

# Method to get plant level details for mobile APP
def get_plant_status_mobile_api(plant, date, role, combined=False):
    try:
        plant_values = {}
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=date.replace(hour=0, minute=0, second=0, microsecond=0))

        plant_values['plant_name'] = str(plant.name)
        plant_values['plant_location'] = str(plant.location)
        if str(role).upper().startswith("CLIENT"):
            try:
                logo = plant.dataglengroup.groupMobileLogo if plant.dataglengroup and plant.dataglengroup.groupMobileLogo else plant.groupClient.clientLogo
            except:
                logo = ""
        else:
            try:
                logo = str(
                    plant.groupClient.dataglenclient.clientMobileLogo) if plant.groupClient.dataglenclient and plant.groupClient.dataglenclient.clientMobileLogo else ""
            except:
                logo = ""
        plant_values['plant_logo'] = logo
        plant_values['plant_capacity'] = float(plant.capacity) if plant.capacity else 0.0
        plant_values['latitude'] = plant.latitude
        plant_values['longitude'] = plant.longitude
        plant_values['total_energy'] = '0.0 kWh'
        plant_values['energy_today'] = '0.0 kWh'
        plant_values['performance_ratio'] = 0.0
        plant_values['cuf'] = 0.0
        plant_values['module_temperature'] = 0.0
        plant_values['ambient_temperature'] = 0.0
        plant_values['current_power'] = 0.0
        if len(value)>0:
            value = value[0]
            plant_values['total_energy'] = fix_generation_units(float(value.total_generation)) if value.total_generation else '0.0 kWh'
            plant_values['energy_today'] = float(value.plant_generation_today) if value.plant_generation_today else 0.0
            plant_values['performance_ratio'] = "{0:.2f}".format(value.pr * 100) + " %" if value.pr else '0.0 %'
            plant_values['cuf'] = "{0:.2f}".format(value.cuf*100) + " %" if value.cuf else '0.0 %'
            plant_values['module_temperature'] = "{0:.2f}".format(value.module_temperature) if value.module_temperature else '0.0'
            plant_values['ambient_temperature'] = "{0:.2f}".format(value.ambient_temperature) if value.ambient_temperature else '0.0'
            plant_values['irradiation'] = "{0:.2f}".format(value.irradiation) if value.irradiation else '0.0'
            plant_values['current_power'] = "{0:.2f}".format(value.active_power) if value.active_power else '0.0'
        specific_yield_value = SpecificYieldTable.objects.filter(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
            identifier=plant.metadata.plantmetasource.sourceKey,
            ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
        plant_values['specific_yield'] = "{0:.2f}".format(float(specific_yield_value[0].specific_yield)) if len(specific_yield_value)>0 else 0.0
        plant_values['inverters'] = len(plant.independent_inverter_units.all())
        try:
            plant_values['energy_meters'] = 1 if plant.metadata.energy_meter_installed or plant.metadata.sending_aggregated_power else len(plant.energy_meters.all())
        except:
            plant_values['energy_meters'] = 0
        weather_station_count = 0
        irradiation_value = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.plantmetasource.sourceKey,
                                                                    stream_name='IRRADIATION').limit(1)
        if len(irradiation_value)>0:
            weather_station_count = 1
        else:
            irradiation_value = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.plantmetasource.sourceKey,
                                                                       stream_name='EXTERNAL_IRRADIATION').limit(1)
            if len(irradiation_value)>0:
                weather_station_count = 1

        try:
            past_kwh_per_meter_square_values = KWHPerMeterSquare.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                identifier=plant.metadata.plantmetasource.sourceKey,
                                                                                ts=date.replace(hour=0, minute=0, second=0, microsecond=0))
            plant_values['kwh_value'] = str("{0:.2f}".format(float(past_kwh_per_meter_square_values[0].value))) + " kWh/m2"
        except Exception as exception:
            print(str(exception))
            pass

        weather_station_count = len(plant.weather_stations.all()) if len(plant.weather_stations.all())>0 else weather_station_count
        plant_values['other_devices'] = len(plant.ajb_units.all()) + len(plant.transformers.all()) + int(weather_station_count)

        plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
        if len(plant_network_details)>0:
            plant_values['plant_connection_status'] = 'disconnected'
        else:
            plant_values['plant_connection_status'] = 'connected'
        try:
            plant_values['gateways_disconnected'] = len(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
        except:
            plant_values['gateways_disconnected'] = 0
            pass
        try:
            plant_values['gateways_powered_off'] = len(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
        except:
            plant_values['gateways_powered_off'] = 0
            pass

        if str(role).upper() in ['CEO', 'O&M_MANAGER']:
            plant_values['know_more'] = True
            starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
            endtime = date
            endtime_today = endtime.replace(hour=23, minute=0, second=0, microsecond=0)
            #Total today's predicted energy value
            total_predicted_energy_value = get_energy_prediction_data(starttime, endtime_today, plant)
            try:
                plant_values['predicted_energy_value'] = fix_generation_units(total_predicted_energy_value)
            except:
                plant_values['predicted_energy_value'] = None
            if plant_values['plant_connection_status'] == 'connected':
                # predicted_energy_value = get_energy_prediction_data(starttime, endtime, plant)
                # prediction_starttime = date.replace(hour=6, minute=0, second=0, microsecond=0)
                # duration_hours = (date - prediction_starttime).total_seconds() / 3600
                # final_duration_hours = min(duration_hours, 12)
                # try:
                #     plant_values['prediction_deviation'] = abs(((float(predicted_energy_value)-float(plant_values['energy_today']))/(float(plant_values['plant_capacity'])*final_duration_hours))*100)
                #     plant_values['prediction_deviation'] = "{0:.2f}".format(float(plant_values['prediction_deviation'])) + ' %'
                # except:
                #     plant_values['prediction_deviation'] = None
                try:
                    plant_values['prediction_deviation'] = prediction_deviation(plant=plant)
                    plant_values['prediction_deviation'] = round(float(plant_values['prediction_deviation']),2)
                except Exception as exception:
                    print str(exception)
                    plant_values['prediction_deviation'] = 0.0
        else:
            plant_values['know_more'] = False
        plant_values['plant_capacity'] = fix_capacity_units(float(plant.capacity)) if plant.capacity else '0.0 kW'
        plant_values['energy_today'] = fix_generation_units(float(value.plant_generation_today)) if value.plant_generation_today else '0.0 kWh'
        plant_values['ambient_temperature'] = str(plant_values['ambient_temperature']) + ' C'
        plant_values['module_temperature'] = str(plant_values['module_temperature']) + ' C'
        plant_values['irradiation'] = plant_values['kwh_value'] #str(plant_values['irradiation']) + ' kWh/m2'
        if combined:
            starttime = date.replace(hour=0, minute=0, second=0, microsecond=0)
            endtime = starttime + datetime.timedelta(days=1)
            power_values = get_power_irradiation_mobile(starttime, endtime, plant)
            plant_values['power_values'] = json.loads(power_values)
        return plant_values
    except Exception as exception:
        print str(exception)
        return plant_values
