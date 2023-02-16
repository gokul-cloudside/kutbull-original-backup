import datetime
import logging
import subprocess
import requests
import email
import imaplib
import re

from solarrms.models import SolarPlant, InverterStatusMappings, IndependentInverter, AJB, InverterErrorCodes
from dataglen.models import ValidDataStorageByStream
from monitoring.models import SourceMonitoring
from errors.models import ErrorStorageByStream
from django.utils import timezone
from helpdesk.models import Ticket, Queue
from helpdesk.dg_functions import create_ticket, update_ticket
from ftplib import FTP
from django.conf import settings
from celery import shared_task
from django.db import transaction
from django.contrib.auth.models import User

logger = logging.getLogger('helpdesk.models')
logger.setLevel(logging.DEBUG)


DISABLE_NEW_TICKET_FOR_PLANTS = ('koyophase2', 'kbilphase2')


class IRRADIATION_VALUES():
    DATA_NOT_AVAILABLE = 0
    IRRADIATION_PRESENT = 1
    IRRADIATION_ZERO = 2
    IRRADIATION_LOW = 3


def check_cassandra_up_time():
    try:
        up_time= 4000
        output = subprocess.check_output(['nodetool', 'info'])
        lines = output.split("\n")
        for line in lines:
            if "Uptime" in line:
                up_time = line.split(":")[1].strip()
        return int(up_time)
    except Exception as exception:
        print str(exception)
        return 0


def check_cassandra_up_time_new():
    """
    return cassandra up time
    :return:
    """
    try:
        up_time= 4000
        process = subprocess.Popen("ssh -p 2732 %s nodetool info" % (settings.HOST_IP[0]), shell=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, stderr = process.communicate()
        lines = output.split("\n")
        for line in lines:
            if "Uptime" in line:
                up_time = line.split(":")[1].strip()
        return int(up_time)
    except Exception as exception:
        print str(exception)
        return 0


def check_ftp_status():
    try:
        conn = FTP('ftp.dataglen.com')
    except Exception as exception:
        print str(exception)
        return False


def check_dgc_up():
    try:
        URL = "http://dataglen.com/api/sources/"
        authorization_token = "Token 6b2205a9280cfe806fd50e18542f35778cda0c18"
        auth_header = {'Authorization ': authorization_token}
        response = requests.get(URL, headers=auth_header, params={})
        if response.status_code != 500:
            return True
        else:
            return False
    except Exception as exception:
        print str(exception)
        return False


def check_ftp_up():
    return True
    """
    #sample api call to check ftp is up
    :return:
    """
    try:

        URL = "http://ftp.dataglen.com/provisioning/devices/?clientslug=chemtrols&deviceid=WD0084C00"
        authorization_token = "Token 2fab9ff946d235aa55f43911a4150ed1596b4ff3"
        auth_header = {'Authorization ': authorization_token}
        response = requests.get(URL, headers=auth_header)
        if response.status_code != 500:
            return True
        else:
            return False
    except Exception as exception:
        print str(exception)
        return False


# data related events
# use below method to check the power off of gateway for individual groups
def check_gateway_power_off(plant, group, request_arrival_time):
    '''
    :param group: Each group should have only a single virtual gateway theoretically,
    that is why we only check for the first only
    :return:
    '''
    try:
        try:
            virtual_gateway = group.group_virtual_gateway_units.all()[0]
        except:
            virtual_gateway = None
        if virtual_gateway:
            power_on_values = ValidDataStorageByStream.objects.filter(source_key=virtual_gateway.sourceKey,
                                                                      stream_name='POWER_ON').limit(1)
            if len(power_on_values)>0 and float(power_on_values[0].stream_value) == 0:
                return True
        return False
    except Exception as exception:
        print(str(exception))
        return False


# use below method to check the power off of gateway where there are no groups
def check_gateway_power_off_for_plant(plant, request_arrival_time):
    '''

    :param plant: This should only be called for a plant which have a single gateway
    :param request_arrival_time:
    :return:
    '''
    try:
        try:
            virtual_gateway = plant.virtual_gateway_units.all()[0]
        except:
            virtual_gateway = None
        if virtual_gateway:
            power_on_values = ValidDataStorageByStream.objects.filter(source_key=virtual_gateway.sourceKey,
                                                                      stream_name='POWER_ON').limit(1)
            if len(power_on_values)>0 and float(power_on_values[0].stream_value) == 0:
                return True
        return False
    except Exception as exception:
        print(str(exception))
        return False


# use below method to check the connectivity of virtual gateways individually
def check_gateway_disconnected(plant, group, request_arrival_time):
    try:
        try:
            gateway_source = group.groupGatewaySources.all()[0]
        except:
            gateway_source = None
        if gateway_source:
            gateway_data = SourceMonitoring.objects.filter(source_key=gateway_source.sourceKey)
            if len(gateway_data)>0:
                return False
        return True
    except Exception as exception:
        print str(exception)
        return False


# use below method to check the connectivity of gateway(plant) for DG gateways
def check_plant_disconnected(plant, request_arrival_time):
    try:
        try:
            gateway_source = plant.gateway.all()[0]
        except:
            gateway_source = None
        if gateway_source:
            gateway_data = SourceMonitoring.objects.filter(source_key=gateway_source.sourceKey)
            if len(gateway_data)>0:
                return False
        return True
    except Exception as exception:
        print str(exception)
        return False


def check_inverters_disconnected_for_group(plant, group, request_arrival_time):
    '''
    Returns a list of disconnected inverters
    :param plant:
    :param group:
    :param request_arrival_time:
    :return:
    '''
    try:
        inverters_disconnected = []
        if group:
            inverters = group.groupIndependentInverters.all()
            for inverter in inverters:
                inverter_data = SourceMonitoring.objects.filter(source_key=inverter.sourceKey)
                if len(inverter_data) == 0:
                    inverters_disconnected.append(inverter.sourceKey)
        return inverters_disconnected
    except Exception as exception:
        print(str(exception))
        return []


def check_ajbs_disconnected_for_group(plant, group, request_arrival_time):
    try:
        ajbs_disconnected = []
        if group:
            ajbs = group.groupAJBs.all()
            for ajb in ajbs:
                ajb_data = SourceMonitoring.objects.filter(source_key=ajb.sourceKey)
                if len(ajb_data) == 0:
                    ajbs_disconnected.append(ajb.sourceKey)
        return ajbs_disconnected
    except Exception as exception:
        print(str(exception))
        return []


def check_inverters_disconnected_for_plant(plant, request_arrival_time):
    try:
        inverters_disconnected = []
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            inverter_data = SourceMonitoring.objects.filter(source_key=inverter.sourceKey)
            if len(inverter_data) == 0:
                inverters_disconnected.append(inverter.sourceKey)
        return inverters_disconnected
    except Exception as exception:
        print(str(exception))
        return []


def check_ajbs_disconnected_for_plant(plant, request_arrival_time):
    try:
        ajbs_disconnected = []
        ajbs = plant.ajb_units.all()
        for ajb in ajbs:
            ajb_data = SourceMonitoring.objects.filter(source_key=ajb.sourceKey)
            if len(ajb_data) == 0:
                ajbs_disconnected.append(ajb.sourceKey)
        return ajbs_disconnected
    except Exception as exception:
        print(str(exception))
        return []


def check_inverters_dual_status_for_plant(plant, request_arrival_time):
    try:
        inverters_not_generating = []
        inverters_not_generating_status_dict = {}
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            inverter_status_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                             stream_name='SOLAR_STATUS',
                                                                             timestamp_in_data__lte=request_arrival_time,
                                                                             timestamp_in_data__gte=request_arrival_time-datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)
            if len(inverter_status_values) and len(plant.solar_status.all())>0:
                inverter_status = inverter_status_values[0].stream_value
                try:
                    inverter_status_mapping = InverterStatusMappings.objects.get(plant=plant, stream_name='SOLAR_STATUS',status_code=float(inverter_status))
                    if inverter_status_mapping.dual_status:
                        inverters_not_generating.append(inverter.sourceKey)
                        inverters_not_generating_status_dict[str(inverter.sourceKey)] = inverter_status
                except Exception as exception:
                    print str(exception)
                    continue
        return inverters_not_generating, inverters_not_generating_status_dict
    except Exception as exception:
        print(str(exception))


def check_inverters_not_generating_for_plant(plant, request_arrival_time):
    try:
        inverters_not_generating = []
        inverters_not_generating_status_dict = {}
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            inverter_status_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                             stream_name='SOLAR_STATUS',
                                                                             timestamp_in_data__lte=request_arrival_time,
                                                                             timestamp_in_data__gte=request_arrival_time-datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)
            if len(inverter_status_values) and len(plant.solar_status.all())>0:
                inverter_status = inverter_status_values[0].stream_value
                try:
                    inverter_status_mapping = InverterStatusMappings.objects.get(plant=plant, stream_name='SOLAR_STATUS',status_code=float(inverter_status))
                    if not inverter_status_mapping.generating:
                        inverters_not_generating.append(inverter.sourceKey)
                        inverters_not_generating_status_dict[str(inverter.sourceKey)] = inverter_status
                except Exception as exception:
                    print str(exception)
                    continue
        return inverters_not_generating, inverters_not_generating_status_dict
    except Exception as exception:
        print(str(exception))


def check_inverters_not_generating_for_group(plant, group, request_arrival_time):
    try:
        inverters_not_generating = []
        inverters_not_generating_status_dict = {}
        if group:
            inverters = group.groupIndependentInverters.all()
        for inverter in inverters:
            inverter_status_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                             stream_name='SOLAR_STATUS',
                                                                             timestamp_in_data__lte=request_arrival_time,
                                                                             timestamp_in_data__gte=request_arrival_time - datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)
            if len(inverter_status_values) and len(plant.solar_status.all()) > 0:
                inverter_status = inverter_status_values[0].stream_value
                try:
                    inverter_status_mapping = InverterStatusMappings.objects.get(plant=plant,
                                                                                 stream_name='SOLAR_STATUS',
                                                                                 status_code=float(inverter_status))
                    if not inverter_status_mapping.generating:
                        inverters_not_generating.append(inverter.sourceKey)
                        inverters_not_generating_status_dict[str(inverter.sourceKey)] = inverter_status
                except Exception as exception:
                    print str(exception)
                    continue
        return inverters_not_generating, inverters_not_generating_status_dict
    except Exception as exception:
        print(str(exception))


def check_inverters_grid_down(plant, request_arrival_time, group=None):
    try:
        inverters_grid_down = []
        inverters_grid_down_status_dict = {}
        inverter_grid_down_alarms = {}

        # get the list of inverters
        if group:
            inverters = group.groupIndependentInverters.all()
        else :
            inverters = plant.independent_inverter_units.all()

        # iterate through the inverters
        for inverter in inverters:
            # check for solar status - if it's already in the grid_down state, no alarm is required,
            # otherwise, check for alarms
            inverter_status_values = ValidDataStorageByStream.objects.filter(
                source_key=inverter.sourceKey, stream_name='SOLAR_STATUS', timestamp_in_data__lte=request_arrival_time,
                timestamp_in_data__gte=request_arrival_time - datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)

            # if there is a solar status value
            if len(inverter_status_values) and len(plant.solar_status.all()) > 0:
                inverter_status = inverter_status_values[0].stream_value
                try:
                    inverter_status_mapping = InverterStatusMappings.objects.get(plant=plant,
                                                                                 stream_name='SOLAR_STATUS',
                                                                                 status_code=float(inverter_status))

                    # if it is grid down, we will not check for alarm yet
                    if inverter_status_mapping.grid_down:
                        inverters_grid_down.append(inverter.sourceKey)
                        inverters_grid_down_status_dict[str(inverter.sourceKey)] = inverter_status

                    # if it's in a non-generating status, check if there is a alarm with a grid down status
                    elif not inverter_status_mapping.generating:
                        alarms = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                     stream_name='ERROR_CODE',
                                                                     timestamp_in_data__lte=request_arrival_time,
                                                                     timestamp_in_data__gt=request_arrival_time - datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)
                        if len(alarms) == 1:
                            alarm = alarms[0]
                            individual_inverter_alarms = []
                            inv_error_code = InverterErrorCodes.objects.filter(
                                manufacturer__in=[inverter.manufacturer.upper(),
                                                  inverter.manufacturer,
                                                  inverter.manufacturer.title()], error_code=alarm.stream_value)
                            if len(inv_error_code) > 0 and inv_error_code[0].grid_down:
                                inverters_grid_down_status_dict[str(inverter.sourceKey)] = inverter_status
                                inverters_grid_down.append(inverter.sourceKey)
                                individual_inverter_alarms.append(alarm.stream_value)
                                inverter_grid_down_alarms[inverter.sourceKey] = {'alarm_codes': individual_inverter_alarms}
                except Exception as exception:
                    # print str(exception)
                    continue

        # return all the three values
        try:
            if len(inverters_grid_down) > 0 :
                from helpdesk.utils import send_infini_sms_internal
                # send_infini_sms_internal(9741313083, ",".join([str(inverters_grid_down_status_dict),
                #                                                str(inverter_grid_down_alarms),
                #                                                str(plant),
                #                                                str(plant.get_client().name),
                #                                                str(request_arrival_time)]))
            # return inverters_grid_down, inverters_grid_down_status_dict, inverter_grid_down_alarms
            return
        except:
            return
    except Exception as exception:
        logger.debug(str(exception))


def check_inverters_alarms_for_plant(plant, request_arrival_time, inverters_list=None):
    try:
        inverter_alarms = {}
        if inverters_list is None:
            inverters = plant.independent_inverter_units.all()
        else:
            inverters = []
            for source_key in inverters_list:
                inverter = IndependentInverter.objects.get(sourceKey=source_key)
                inverters.append(inverter)
        for inverter in inverters:
            individual_inverter_alarms = []
            alarms = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                         stream_name='ERROR_CODE',
                                                         timestamp_in_data__lte=request_arrival_time,
                                                         timestamp_in_data__gt=request_arrival_time-datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)
            if len(alarms)>0:
                for i in range(len(alarms)):
                    individual_inverter_alarms.append(alarms[i].stream_value)
                if len(individual_inverter_alarms) > 0:
                    alarms_dict={}
                    alarms_dict['alarm_codes'] = individual_inverter_alarms
                    inverter_alarms[inverter.sourceKey] = alarms_dict
        return inverter_alarms
    except Exception as exception:
        print(str(exception))


def check_inverters_alarms_for_group(plant, group, request_arrival_time, inverters_list=None):
    try:
        inverter_alarms = {}
        if inverters_list is None:
            inverters = group.groupIndependentInverters.all()
        else:
            inverters = []
            for source_key in inverters_list:
                inverter = IndependentInverter.objects.get(sourceKey=source_key)
                inverters.append(inverter)
        for inverter in inverters:
            individual_inverter_alarms = []
            alarms = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                         stream_name='ERROR_CODE',
                                                         timestamp_in_data__lte=request_arrival_time,
                                                         timestamp_in_data__gt=request_arrival_time-datetime.timedelta(seconds=inverter.timeoutInterval)).limit(1)
            if len(alarms) > 0:
                for i in range(len(alarms)):
                    individual_inverter_alarms.append(alarms[i].stream_value)
                if len(individual_inverter_alarms) > 0:
                    alarms_dict = {}
                    alarms_dict['alarm_codes'] = individual_inverter_alarms
                    inverter_alarms[inverter.sourceKey] = alarms_dict
        return inverter_alarms
    except Exception as exception:
        print(str(exception))


def check_ajbs_current_zero_for_plant(plant, request_arrival_time, ajbs_list=None):
    try:
        zero_current_ajbs_list = []
        final_zero_current_alarms_dict = {}
        ajbs_current_zero_alarms = {}
        if ajbs_list is None:
            ajbs = plant.ajb_units.all()
        else:
            ajbs = []
            for source_key in ajbs_list:
                ajb = AJB.objects.get(sourceKey=source_key)
                ajbs.append(ajb)
        for ajb in ajbs:
            individual_ajb_current_zero_alarms = []
            alarms = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                             stream_name='CURRENT_ZERO_STREAM',
                                                             timestamp_in_data__lte=request_arrival_time,
                                                             timestamp_in_data__gt=request_arrival_time-datetime.timedelta(seconds=ajb.timeoutInterval)).limit(1)
            if len(alarms)>0:
                for i in range(len(alarms)):
                    try:
                        values = str(alarms[i].stream_value).split(",")
                        values_list = ['S'+str(value) for value in values]
                        individual_ajb_current_zero_alarms.extend(values_list)
                    except:
                        pass
                if len(individual_ajb_current_zero_alarms) > 0:
                    alarms_dict={}
                    alarms_dict['alarm_codes'] = individual_ajb_current_zero_alarms
                    ajbs_current_zero_alarms[ajb.sourceKey] = alarms_dict
        for key in ajbs_current_zero_alarms.keys():
            zero_current_ajbs_list.append(str(key))
            ajb_zero_current_dict = {}
            ajb_zero_current_dict['solar_status'] = "-1.0"
            ajb_zero_current_dict['alarm_codes'] = ajbs_current_zero_alarms[key]['alarm_codes']
            final_zero_current_alarms_dict[key] = ajb_zero_current_dict
        return zero_current_ajbs_list, final_zero_current_alarms_dict
    except Exception as exception:
        print(str(exception))


def create_power_off_ticket(plant, priority, due_date):
    try:
        ticket_name = "Gateway Powered off at : " + str(plant.location)
        ticket_description = "The data logger at the site has been powered off, please check the power " \
                             "supply. The generation data will not be collected until the device's power " \
                             "supply is back."
        event_type = "GATEWAY_POWER_OFF"
        open_comment = "This ticket has been generated by the system based on a power off signal from the device."
        new_power_off_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                            ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return  new_power_off_ticket
    except Exception as exception:
        print(str(exception))


def create_gateway_disconnected_ticket(plant, priority, due_date):
    try:
        ticket_name = "Gateway disconnected at : " + str(plant.location)
        ticket_description = "All connected devices to this data logger have stopped sending data, please check " \
                             "the availability and status of an internet connection (pre-paid SIM balance, " \
                             "post-paid bill status, LAN/Wi-Fi  etc.) at the site."
        event_type = "GATEWAY_DISCONNECTED"
        open_comment = "Ticket created automatically based on the gateway disconnected alerts."
        new_gateway_disconnected_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                        ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_gateway_disconnected_ticket
    except Exception as exception:
        print(str(exception))


def create_inverters_disconnected_ticket(plant, priority, due_date):
    try:
        ticket_name = "Inverters disconnected at : " + str(plant.location)
        ticket_description = "This inverter has stopped sending data while an internet connection at the site is " \
                             "available. Please check communication interfaces and operational status of the inverter."
        event_type = "INVERTERS_DISCONNECTED"
        open_comment = "Ticket created automatically based on the inverters disconnected alerts."
        new_inverters_disconnected_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                          ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_inverters_disconnected_ticket
    except Exception as exception:
        print(str(exception))


def create_ajbs_disconnected_ticket(plant, priority, due_date):
    try:
        ticket_name = "AJBs disconnected at : " + str(plant.location)
        ticket_description = "AJBs disconnected event occurred at : " + str(plant.location)
        event_type = "AJBS_DISCONNECTED"
        open_comment = "Ticket created automatically based on the ajbs disconnected alerts."
        new_ajbs_disconnected_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                     ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_ajbs_disconnected_ticket
    except Exception as exception:
        print(str(exception))


def create_inverters_alarms_ticket(plant, priority, due_date):
    try:
        ticket_name = "Inverters raised alarms at : " + str(plant.location)
        ticket_description = "This inverter has raised alarms as per the details below, please address them as soon as possible."
        event_type = "INVERTERS_ALARMS"
        open_comment = "Tickets created automatically based on the inverter alarms"
        new_inverters_alarms_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                    ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_inverters_alarms_ticket
    except Exception as exception:
        print(str(exception))


def create_ajb_string_current_zero_ticket(plant, priority, due_date):
    try:
        ticket_name = "String zero Error at : " + str(plant.location)
        ticket_description = "Certain strings are sending zero current values at : " + str(plant.location)
        event_type = "AJB_STRING_CURRENT_ZERO_ALARM"
        open_comment = "Tickets created automatically based on the string values"
        new_inverters_alarms_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                    ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_inverters_alarms_ticket
    except Exception as exception:
        print(str(exception))


def create_inverters_not_generating_ticket(plant, priority, due_date):
    try:
        ticket_name = "Inverters not generating at : " + str(plant.location)
        ticket_description = "Inverters not generating event occurred at : " + str(plant.location)
        event_type = "INVERTERS_NOT_GENERATING"
        open_comment = "Ticket created automatically based on the inverters status."
        new_inverters_not_generating_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                           ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_inverters_not_generating_ticket
    except Exception as exception:
        print(str(exception))


def close_ticket(plant, ticket, request_arrival_time):
    try:
        comment = "Ticket closed automatically based on updated data"
        new_status = Ticket.CLOSED_STATUS
        try:
            user = plant.owner.organization_user.user
        except:
            user = None
        update_ticket(plant=plant, ticket_id=ticket.id, followup_user=user, comment=comment, new_status=new_status, title=ticket.title)
    except Exception as exception:
        print(str(exception))


def check_irradiation_data(starttime, endtime, plant):
    try:
        values = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.plantmetasource.sourceKey,
                                                         stream_name='IRRADIATION',
                                                         timestamp_in_data__gte=starttime,
                                                         timestamp_in_data__lte=endtime)
        if len(values) == 0:
            values = ValidDataStorageByStream.objects.filter(source_key=plant.metadata.plantmetasource.sourceKey,
                                                             stream_name='EXTERNAL_IRRADIATION',
                                                             timestamp_in_data__gte=starttime,
                                                             timestamp_in_data__lte=endtime)

        if len(values) == 0:
            return IRRADIATION_VALUES.DATA_NOT_AVAILABLE
        else:
            value = values[0].stream_value
            if float(value) > (0.05*4):
                # if irradiance is more than 200
                return IRRADIATION_VALUES.IRRADIATION_PRESENT
            elif 0 < float(value) < (0.05*4):
                # if irradiance is between 0 and 200
                return IRRADIATION_VALUES.IRRADIATION_LOW
            elif float(value) == 0.0:
                # if irradiance is zero
                return IRRADIATION_VALUES.IRRADIATION_ZERO
            else:
                # faulty sensor
                return IRRADIATION_VALUES.DATA_NOT_AVAILABLE
    except Exception as exception:
        print(str(exception))
        return IRRADIATION_VALUES.DATA_NOT_AVAILABLE


def check_tickets_for_a_plant(plant, run_id="Not defined"):
    with transaction.atomic():
        # get plant's queue and acquire a lock with select_for_update()
        try:
            logger.debug(",".join(["looking for a queue for plant", plant.slug, run_id]))
            queue = Queue.objects.select_for_update().get(plant=plant)
        except Exception as exception:
            print ("Queue does not exist for plant : " + str(plant.slug))
            logger.debug(",".join(["a queue does not exist for this plant",
                                   str(plant.slug), str(exception)]))
            return

        # start the run now, no other process will be able to take a queue until this part returns
        try:
            print("checking for plant : " + str(plant.slug))
            logger.debug(",".join(["ID_LOG: Checkinf for plant",
                                   plant.slug, run_id]))
            if plant.isOperational:
                logger.debug(",".join(["ID_LOG: Plant operational, checking further",
                                       plant.slug, run_id]))
                try:
                    plant_gateway_source = plant.gateway.all()[0]
                except:
                    plant_gateway_source = None
                if plant_gateway_source.isMonitored:
                    logger.debug(",".join(["ID_LOG: Gateway active, checking further",
                                           plant.slug, str(plant_gateway_source.name), run_id]))
                    final_gateway_power_off_list = []
                    final_gateway_disconnected_list = []
                    final_inverters_disconnected_list = []
                    final_ajbs_disconnected_list = []
                    final_inverter_alarms = {}
                    final_inverters_grid_down_list = []
                    final_inverters_not_generating_list = []
                    final_inverters_not_generating_status_dict = {}

                    # Following if condition is for virtual gateways (webdyn plants)
                    if plant_gateway_source and plant_gateway_source.isVirtual:
                        # go through each group
                        groups = plant.solar_groups.all()
                        # If multiple gateways are installed at a single plant
                        if len(groups) > 0:
                            # parse through groups
                            for group in groups:
                                logger.debug(",".join(["ID_LOG: Group found, checking further", plant.slug,
                                                       str(group.name), run_id]))
                                try:
                                    check_inverters_grid_down(plant, timezone.now(), group)
                                except:
                                    pass
                                gateway_power_off_list = []
                                gateway_disconnected_list = []
                                inverters_disconnected_list = []
                                ajbs_disconnected_list = []
                                inverters_grid_down_list = []
                                inverters_not_generating_list = []
                                inverter_alarms_dict = {}

                                # returns a list of inverters that have a grid down/not generation status
                                # returns True if the group's first virtual gateway is powered off
                                group_gateway_power_off = check_gateway_power_off(plant, group,
                                                                                  timezone.now())
                                if group_gateway_power_off:
                                    # this gateway is powered off
                                    if len(group.group_virtual_gateway_units.all()) > 0:
                                        virtual_gateway = group.group_virtual_gateway_units.all()[0]
                                        # holds the source key of the switched off gateway
                                        gateway_power_off_list.append(virtual_gateway.sourceKey)

                                # if the gateway is not powered off, check for gateway disconnected
                                if len(gateway_power_off_list) == 0:
                                    # returns the status of a group's connectivity status
                                    # (group.groupGatewaySources.all()[0])
                                    group_gateway_disconnected = check_gateway_disconnected(plant, group,
                                                                                            timezone.now())
                                    if group_gateway_disconnected:
                                        if len(group.groupGatewaySources.all()) > 0:
                                            gateway_source = group.groupGatewaySources.all()[0]
                                            # holds the key of the gateway disconnected
                                            gateway_disconnected_list.append(gateway_source.sourceKey)

                                # if the gateway is not disconnected or powered off,
                                # check for inverters disconnected

                                # TODO Not checking these cases when there is a gateway powered off/disconn,
                                # will close earlier tickets (if any) related to inverters/ajbs disconnected
                                if len(gateway_power_off_list) == 0 and len(gateway_disconnected_list) == 0:
                                    # returns a list of disconnected inverters with this group
                                    group_inverters_disconnected = check_inverters_disconnected_for_group(
                                        plant, group, timezone.now())
                                    inverters_disconnected_list.extend(group_inverters_disconnected)

                                # if the gateway is not disconnected or powered off,
                                # check for ajbs disconnected
                                if len(gateway_power_off_list) == 0 and len(gateway_disconnected_list) == 0:
                                    group_ajbs_disconnected = check_ajbs_disconnected_for_group(plant, group,
                                                                                                timezone.now())
                                    ajbs_disconnected_list.extend(group_ajbs_disconnected)

                                # If the gateway is not disconnected or powered off,
                                # check for inverters not generating

                                # TODO Not checking these cases when there is a gateway powered off/disconn.,
                                # will close earlier tickets (if any) related to inverters alarms
                                if len(gateway_power_off_list) == 0 and len(gateway_disconnected_list) == 0:
                                    # returns SOLAR_STATUS within TTL having generating param not set
                                    inverters_not_generating, inverters_status_dict = \
                                        check_inverters_not_generating_for_group(plant, group, timezone.now())
                                    inverters_not_generating_list.extend(inverters_not_generating)

                                # If the gateway is not disconnected or powered off, check for inverter alarms
                                if len(gateway_power_off_list) == 0 and len(gateway_disconnected_list) == 0:
                                    # returns inverters that have raised alarms within TTL,
                                    # and alarms values as required by Tickets models
                                    group_inverter_alarms = check_inverters_alarms_for_group(
                                        plant, group, timezone.now(), inverters_not_generating_list)
                                    inverter_alarms_dict.update(group_inverter_alarms)

                                # update the final lists of gateways, inverters and AJBs status
                                # for disconnected and powered off nodes
                                final_gateway_power_off_list.extend(gateway_power_off_list)
                                final_gateway_disconnected_list.extend(gateway_disconnected_list)
                                final_inverters_disconnected_list.extend(inverters_disconnected_list)
                                final_ajbs_disconnected_list.extend(ajbs_disconnected_list)

                                if len(gateway_power_off_list) == 0 and len(gateway_disconnected_list) == 0:
                                    final_inverter_alarms.update(inverter_alarms_dict)
                                    final_inverters_not_generating_status_dict.update(inverters_status_dict)
                                    final_inverters_not_generating_list.extend(inverters_not_generating_list)
                            # group loop ends


                            # alarms_disabled needs to be parsed in the Tickets functions to tell if
                            # alarm value is present in the association
                            alarms_disabled = False

                            # prepare the final argument that needs to be passed
                            if len(final_inverters_not_generating_list) == 0:
                                # if there are no inverters with _not_genreating status
                                final_inverter_alarms = {}
                            else:
                                for sourceKey in final_inverters_not_generating_list:
                                    try:
                                        # this will mean that there is an entry in final_inverter_alarms with
                                        # the mentioned sourceKey, we are adding solar_status as well
                                        inverter_solar_status = final_inverters_not_generating_status_dict[sourceKey]
                                        final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                    except:
                                        try:
                                            # this will mean that there is NO entry in final_inverter_alarms
                                            # with the mentioned sourceKey, we are adding solar_status and
                                            # putting alarms_disabled to True even if this is true for at
                                            # least one source
                                            inverter_solar_status = final_inverters_not_generating_status_dict[sourceKey]
                                            final_inverter_alarms[sourceKey] = {}
                                            final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                            final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                            alarms_disabled = True
                                        except:
                                            # fallback, no solar_status or alarm code,
                                            # this should not happen though
                                            final_inverter_alarms[sourceKey]['solar_status'] = None
                                            final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                            alarms_disabled = True
                                        continue

                            '''
                            We have prepared dictionaries and data we need to manage tickets 
                            '''

                            closed_a_gateway_powered_off_ticket = False
                            closed_a_gateway_disconnected_ticket = False

                            # 1. Check if an open ticket exists for gateway power off for this plant
                            gateway_power_off_ticket = Ticket.objects.filter(queue=queue,
                                                                             event_type='GATEWAY_POWER_OFF',
                                                                             status=1)
                            if len(gateway_power_off_ticket) > 0:
                                # As a ticket exists already, update the associations. If the
                                # len(gateway_power_off_list) is zero, then the ticket will get closed.
                                gateway_power_off_ticket[0].update_ticket_associations(
                                    final_gateway_power_off_list)
                                if len(final_gateway_power_off_list) == 0:
                                    # close this ticket as all devices have been powered on
                                    close_ticket(plant=plant, ticket=gateway_power_off_ticket[0],
                                                 request_arrival_time=timezone.now())
                                    closed_a_gateway_powered_off_ticket = True
                                    # TODO a gateway powered off ticket has just been closed off, the
                                    # TODO next run should not be possible until the time we get everything back
                                    return
                            elif len(gateway_power_off_ticket) == 0 and len(final_gateway_power_off_list) > 0:
                                # create a new ticket for gateway power powered off
                                new_gateway_power_off_ticket = create_power_off_ticket(plant, priority=1,
                                                                                       due_date=None)
                                new_gateway_power_off_ticket.update_ticket_associations(
                                    final_gateway_power_off_list)
                            else:
                                pass

                            # 2. Check if an open ticket exists for gateway disconnected for this plant
                            gateway_disconnected_ticket = Ticket.objects.filter(
                                queue=queue, event_type='GATEWAY_DISCONNECTED', status=1)
                            if len(gateway_disconnected_ticket) > 0:
                                # As a tickets exists already, update the associations.
                                # if len(gateway_disconnected_ticket) is zero, then this ticket will get closed.
                                gateway_disconnected_ticket[0].update_ticket_associations(
                                    final_gateway_disconnected_list)
                                if len(final_gateway_disconnected_list) == 0:
                                    # all gateways are connected now
                                    close_ticket(plant=plant, ticket=gateway_disconnected_ticket[0],
                                                 request_arrival_time=timezone.now())
                                    closed_a_gateway_disconnected_ticket = True
                                    # TODO a gateway disconnected ticket has just been closed off, the
                                    # TODO next run should not be possible until the time we get everything back
                                    return
                            elif len(gateway_disconnected_ticket) == 0 and \
                                    len(final_gateway_disconnected_list) > 0:
                                # create a new ticket for gateway disconnected
                                new_gateway_disconnected_ticket = create_gateway_disconnected_ticket(
                                    plant, priority=2, due_date=None)
                                new_gateway_disconnected_ticket.update_ticket_associations(
                                    final_gateway_disconnected_list)
                            else:
                                pass

                            # 3. Check if an open ticket exists for disconnected inverters
                            inverters_disconnected_ticket = Ticket.objects.filter(
                                queue=queue, event_type='INVERTERS_DISCONNECTED', status=1)
                            if len(inverters_disconnected_ticket) > 0:
                                # A tickets exists already, update associations.
                                inverters_disconnected_ticket[0].update_ticket_associations(
                                    final_inverters_disconnected_list)
                                # If len(inverters_disconnected_ticket) is 0, close the ticket as well as
                                # all inverters are online now.
                                if len(final_inverters_disconnected_list) == 0:
                                    close_ticket(plant=plant, ticket=inverters_disconnected_ticket[0],
                                                 request_arrival_time=timezone.now())
                            elif len(inverters_disconnected_ticket) == 0 and \
                                    len(final_inverters_disconnected_list) > 0:
                                # create a new ticket for inverters disconnected
                                new_inverters_disconnected_ticket = create_inverters_disconnected_ticket(
                                    plant, priority=2, due_date=None)
                                new_inverters_disconnected_ticket.update_ticket_associations(
                                    final_inverters_disconnected_list)
                            else:
                                pass

                            # 4. check if an open ticket exists for ajbs disconnected
                            ajbs_disconnected_ticket = Ticket.objects.filter(
                                queue=queue, event_type='AJBS_DISCONNECTED', status=1)
                            if len(ajbs_disconnected_ticket) > 0:
                                # A tickets exists already, update associations.
                                ajbs_disconnected_ticket[0].update_ticket_associations(
                                    final_ajbs_disconnected_list)
                                # If len(inverters_disconnected_ticket) is zero, then close the ticket.
                                if len(final_ajbs_disconnected_list) == 0:
                                    close_ticket(plant=plant, ticket=ajbs_disconnected_ticket[0],
                                                 request_arrival_time=timezone.now())
                            elif len(ajbs_disconnected_ticket) == 0 and len(final_ajbs_disconnected_list) > 0:
                                # Create a new ticket for AJBs disconnected
                                new_ajbs_disconnected_ticket = create_ajbs_disconnected_ticket(
                                    plant, priority=2, due_date=None)
                                new_ajbs_disconnected_ticket.update_ticket_associations(
                                    final_ajbs_disconnected_list)
                            else:
                                pass

                            # check if an open ticket exists for inverter alarms
                            # inverters_alarms_ticket = Ticket.objects.filter(queue=queue, event_type='INVERTERS_ALARMS', status=1)
                            # if len(inverters_alarms_ticket)>0:
                            #     #Ticket exists already, update associations.
                            #     inverters_alarms_ticket[0].update_ticket_associations(identifiers_list = final_inverter_alarms.keys(), alarms_dict=final_inverter_alarms)
                            #     if len(final_inverter_alarms) == 0:
                            #         close_ticket(plant=plant, ticket=inverters_alarms_ticket[0], request_arrival_time=timezone.now())
                            # elif len(inverters_alarms_ticket) == 0 and len(final_inverter_alarms)>0:
                            #     #create new ticket for inverter alarms
                            #     new_inverters_alarms_ticket = create_inverters_alarms_ticket(plant, priority=2, due_date=None)
                            #     new_inverters_alarms_ticket.update_ticket_associations(identifiers_list = final_inverter_alarms.keys(), alarms_dict=final_inverter_alarms)
                            # else:
                            #     pass

                            # 5. Check for inverters alarms based on  solar status values of inverters and
                            # the actual alarms raised by inverters.
                            irradiation_status = check_irradiation_data(
                                timezone.now() - datetime.timedelta(minutes=40), timezone.now(), plant)

                            irradiation_values = irradiation_status is IRRADIATION_VALUES.IRRADIATION_PRESENT or \
                                                 irradiation_status is IRRADIATION_VALUES.DATA_NOT_AVAILABLE
                            # TODO create a ticket if there's an irradiation sensor installed
                            # (plant.metadata.plantmetasource.irradiation_data is True) and the function
                            # returns with a > 200 value, or if there's no irradiation sensor
                            # DO NOT create a ticket if there is an irradiation sensor installed and the irradiation
                            # value is 0
                            if (plant.metadata.plantmetasource.irradiation_data is True and irradiation_values is True) \
                                    or (plant.metadata.plantmetasource.irradiation_data is False):
                                print("inside Inverter Alarms check for multiple groups virtual plant")
                                inverters_not_generating_ticket = Ticket.objects.filter(
                                    queue=queue, event_type='INVERTERS_ALARMS', status=1)
                                if len(inverters_not_generating_ticket) > 0:
                                    # A ticket exists already, update its associations.
                                    inverters_not_generating_ticket[0].update_ticket_associations(
                                        final_inverters_not_generating_list, final_inverter_alarms,
                                        alarms_disabled=alarms_disabled)
                                    if len(final_inverters_not_generating_list) == 0:
                                        close_ticket(plant=plant, ticket=inverters_not_generating_ticket[0],
                                                     request_arrival_time=timezone.now())
                                elif len(inverters_not_generating_ticket) == 0 \
                                        and len(final_inverters_not_generating_list) > 0:
                                    # Create a new ticket for inverters alarms
                                    new_inverters_not_generating_ticket = create_inverters_alarms_ticket(
                                        plant, priority=1, due_date=None)
                                    new_inverters_not_generating_ticket.update_ticket_associations(
                                        final_inverters_not_generating_list, final_inverter_alarms,
                                        alarms_disabled=alarms_disabled)
                                else:
                                    pass

                            # 6. Check for string current zero values
                            if len(final_gateway_power_off_list) == 0 and len(final_gateway_disconnected_list) == 0:
                                # check for string's current zero values.
                                if (plant.metadata.plantmetasource.irradiation_data is True and irradiation_values is True) \
                                        or (plant.metadata.plantmetasource.irradiation_data is False):
                                    # check for AJB strings zero error
                                    print "checking for string current zero values"
                                    ajbs_string_zero_list, ajbs_string_zero_dict = check_ajbs_current_zero_for_plant(
                                        plant, timezone.now())
                                    string_current_zero_ticket = Ticket.objects.filter(
                                        queue=queue, event_type='AJB_STRING_CURRENT_ZERO_ALARM', status=1)
                                    if len(string_current_zero_ticket) > 0:
                                        # A ticket exists already, update its associations.
                                        string_current_zero_ticket[0].update_ticket_associations(
                                            ajbs_string_zero_list, ajbs_string_zero_dict)
                                        if len(ajbs_string_zero_list) == 0:
                                            close_ticket(plant=plant, ticket=string_current_zero_ticket[0],
                                                         request_arrival_time=timezone.now())
                                    elif len(string_current_zero_ticket) == 0 and len(ajbs_string_zero_list) > 0:
                                        # Create a new ticket for AJBs currentzero error
                                        new_ajb_current_zero_ticket = create_ajb_string_current_zero_ticket(
                                            plant, priority=1, due_date=None)
                                        new_ajb_current_zero_ticket.update_ticket_associations(
                                            ajbs_string_zero_list, ajbs_string_zero_dict)
                                    else:
                                        pass

                        # If there is only one gateway at the plant
                        else:
                            # check grid down for a plant
                            try:
                                check_inverters_grid_down(plant, timezone.now())
                            except:
                                pass

                            # check for gateway power off
                            plant_gateway_power_off = check_gateway_power_off_for_plant(plant, timezone.now())
                            if plant_gateway_power_off:
                                virtual_gateway = plant.virtual_gateway_units.all()[0]
                                final_gateway_power_off_list.append((virtual_gateway.sourceKey))

                            # check if an open ticket exists for gateway power off
                            gateway_power_off_ticket = Ticket.objects.filter(queue=queue, event_type='GATEWAY_POWER_OFF',
                                                                             status=1)
                            if len(gateway_power_off_ticket) > 0:
                                # Tickets exists already, update the associations.
                                gateway_power_off_ticket[0].update_ticket_associations(final_gateway_power_off_list)
                                if len(final_gateway_power_off_list) == 0:
                                    close_ticket(plant=plant, ticket=gateway_power_off_ticket[0],
                                                 request_arrival_time=timezone.now())
                                    return
                            elif len(gateway_power_off_ticket) == 0 and len(final_gateway_power_off_list) > 0:
                                # create new ticket for gateway disconnected
                                new_gateway_power_off_ticket = create_power_off_ticket(plant, priority=2, due_date=None)
                                new_gateway_power_off_ticket.update_ticket_associations(final_gateway_power_off_list)
                            else:
                                pass

                            # check for gateway disconnected
                            # This should be checked only when there is no gateway power off open ticket
                            if len(final_gateway_power_off_list) == 0:
                                plant_gateway_disconnected = check_plant_disconnected(plant, timezone.now())
                                if plant_gateway_disconnected:
                                    gateway_source = plant.gateway.all()[0]
                                    final_gateway_disconnected_list.append(gateway_source.sourceKey)

                                # check if an open ticket exists for gateway disconnected
                                gateway_disconnected_ticket = Ticket.objects.filter(queue=queue,
                                                                                    event_type='GATEWAY_DISCONNECTED',
                                                                                    status=1)
                                if len(gateway_disconnected_ticket) > 0:
                                    # Tickets exists already, update the associations.
                                    gateway_disconnected_ticket[0].update_ticket_associations(
                                        final_gateway_disconnected_list)
                                    if len(final_gateway_disconnected_list) == 0:
                                        close_ticket(plant=plant, ticket=gateway_disconnected_ticket[0],
                                                     request_arrival_time=timezone.now())
                                        return
                                elif len(gateway_disconnected_ticket) == 0 and len(final_gateway_disconnected_list) > 0:
                                    # create new ticket for gateway disconnected
                                    new_gateway_disconnected_ticket = create_gateway_disconnected_ticket(plant, priority=2,
                                                                                                         due_date=None)
                                    new_gateway_disconnected_ticket.update_ticket_associations(
                                        final_gateway_disconnected_list)
                                else:
                                    pass

                            # check for inverters disconnected
                            # This should be checked only when there is no gateway power off and gateway disconnected open ticket
                            if len(final_gateway_power_off_list) == 0 and len(final_gateway_disconnected_list) == 0:
                                final_inverters_disconnected_list = check_inverters_disconnected_for_plant(plant,
                                                                                                           timezone.now())
                                # check if an open ticket exists for inverters disconnected
                                inverters_disconnected_ticket = Ticket.objects.filter(queue=queue,
                                                                                      event_type='INVERTERS_DISCONNECTED',
                                                                                      status=1)

                                if len(inverters_disconnected_ticket) > 0:
                                    # Tickets exists already, update the associations.
                                    inverters_disconnected_ticket[0].update_ticket_associations(
                                        final_inverters_disconnected_list)
                                    if len(final_inverters_disconnected_list) == 0:
                                        close_ticket(plant=plant, ticket=inverters_disconnected_ticket[0],
                                                     request_arrival_time=timezone.now())
                                elif len(inverters_disconnected_ticket) == 0 and len(final_inverters_disconnected_list) > 0:
                                    # create new ticket for inverters disconnected
                                    new_inverters_disconnected_ticket = create_inverters_disconnected_ticket(plant,
                                                                                                             priority=2,
                                                                                                             due_date=None)
                                    new_inverters_disconnected_ticket.update_ticket_associations(
                                        final_inverters_disconnected_list)
                                else:
                                    pass

                            # check for ajbs disconnected
                            # This should be checked only when there is no gateway power off and gateway disconnected open ticket
                            if len(final_gateway_power_off_list) == 0 and len(final_gateway_disconnected_list) == 0:
                                final_ajbs_disconnected_list = check_ajbs_disconnected_for_plant(plant, timezone.now())
                                # check if an open ticket exists for inverters disconnected
                                ajbs_disconnected_ticket = Ticket.objects.filter(queue=queue,
                                                                                 event_type='AJBS_DISCONNECTED', status=1)

                                if len(ajbs_disconnected_ticket) > 0:
                                    # Ticket exists already, update the associations.
                                    ajbs_disconnected_ticket[0].update_ticket_associations(final_ajbs_disconnected_list)
                                    if len(final_ajbs_disconnected_list) == 0:
                                        close_ticket(plant=plant, ticket=ajbs_disconnected_ticket[0],
                                                     request_arrival_time=timezone.now())
                                elif len(ajbs_disconnected_ticket) == 0 and len(final_ajbs_disconnected_list) > 0:
                                    # create new ticket for inverters disconnected
                                    new_ajbs_disconnected_ticket = create_ajbs_disconnected_ticket(plant, priority=2,
                                                                                                   due_date=None)
                                    new_ajbs_disconnected_ticket.update_ticket_associations(final_ajbs_disconnected_list)
                                else:
                                    pass

                            # check for inverter errors
                            # This should be checked only when there is no gateway power off and gateway disconnected open ticket
                            # if len(final_gateway_power_off_list) == 0 and len(final_gateway_disconnected_list) == 0:
                            #     final_inverter_alarms = check_inverters_alarms_for_plant(plant, timezone.now())
                            #     #check if an open ticket exists for inverter alarms
                            #     inverters_alarms_ticket = Ticket.objects.filter(queue=queue, event_type='INVERTERS_ALARMS', status=1)
                            #     if len(inverters_alarms_ticket)>0:
                            #         #Ticket exists already, update the associations
                            #         inverters_alarms_ticket[0].update_ticket_associations(final_inverter_alarms.keys(), final_inverter_alarms)
                            #         if len(final_inverter_alarms) == 0:
                            #             close_ticket(plant=plant, ticket=inverters_alarms_ticket[0], request_arrival_time=timezone.now())
                            #     elif len(inverters_alarms_ticket) == 0 and len(final_inverter_alarms) >0:
                            #         # create new ticket for inverter alarms
                            #         new_inverters_alarms_ticket = create_inverters_alarms_ticket(plant, priority=1, due_date=None)
                            #         new_inverters_alarms_ticket.update_ticket_associations(final_inverter_alarms.keys(), final_inverter_alarms)
                            #     else:
                            #         pass

                            # check for inverters alarms based on the solar status values of inverters and the actual alarms raised by inverters.
                            if len(final_gateway_power_off_list) == 0 and len(final_gateway_disconnected_list) == 0:
                                final_inverters_not_generating_list, final_inverters_not_generating_status_dict = check_inverters_not_generating_for_plant(
                                    plant, timezone.now())
                                final_inverter_alarms = check_inverters_alarms_for_plant(plant, timezone.now(),
                                                                                         final_inverters_not_generating_list)

                                # add solar status in final_inverters alarms
                                # for key in final_inverter_alarms.keys():
                                #     try:
                                #         inverter_solar_status = final_inverters_not_generating_status_dict[key]
                                #         final_inverter_alarms[key]['status_code'] = inverter_solar_status
                                #     except:
                                #         final_inverter_alarms[key]['status_code'] = None
                                #         continue

                                alarms_disabled = False
                                if len(final_inverters_not_generating_list) == 0:
                                    final_inverter_alarms = {}
                                else:
                                    for sourceKey in final_inverters_not_generating_list:
                                        try:
                                            inverter_solar_status = final_inverters_not_generating_status_dict[sourceKey]
                                            final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                        except:
                                            try:
                                                inverter_solar_status = final_inverters_not_generating_status_dict[
                                                    sourceKey]
                                                final_inverter_alarms[sourceKey] = {}
                                                final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                                final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                                alarms_disabled = True
                                            except:
                                                final_inverter_alarms[sourceKey]['solar_status'] = None
                                                final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                                alarms_disabled = True
                                            continue

                                print "final_inverter_alarms"
                                print final_inverter_alarms
                                print "final_inverters_not_generating_list"
                                print final_inverters_not_generating_list
                                # check if an open ticket exists for inverters not generating
                                irradiation_status = check_irradiation_data(
                                    timezone.now() - datetime.timedelta(minutes=40), timezone.now(), plant)

                                irradiation_values = irradiation_status is IRRADIATION_VALUES.IRRADIATION_PRESENT or \
                                                     irradiation_status is IRRADIATION_VALUES.DATA_NOT_AVAILABLE

                                if (plant.metadata.plantmetasource.irradiation_data is True and irradiation_values is True) or (
                                    plant.metadata.plantmetasource.irradiation_data is False):
                                    print("Inverter Alarms check for single group virtual plant")
                                    inverters_not_generating_ticket = Ticket.objects.filter(queue=queue,
                                                                                            event_type='INVERTERS_ALARMS',
                                                                                            status=1)
                                    if len(inverters_not_generating_ticket) > 0:
                                        # Ticket already exists, update the associations
                                        inverters_not_generating_ticket[0].update_ticket_associations(
                                            final_inverters_not_generating_list, alarms_dict=final_inverter_alarms,
                                            alarms_disabled=alarms_disabled)
                                        if len(final_inverters_not_generating_list) == 0:
                                            close_ticket(plant=plant, ticket=inverters_not_generating_ticket[0],
                                                         request_arrival_time=timezone.now())
                                    elif len(inverters_not_generating_ticket) == 0 and len(
                                            final_inverters_not_generating_list) > 0:
                                        # create new ticket for inverters alarms
                                        new_inverters_not_generating_ticket = create_inverters_alarms_ticket(plant,
                                                                                                             priority=1,
                                                                                                             due_date=None)
                                        new_inverters_not_generating_ticket.update_ticket_associations(
                                            final_inverters_not_generating_list, alarms_dict=final_inverter_alarms,
                                            alarms_disabled=alarms_disabled)
                                    else:
                                        pass

                            if len(final_gateway_power_off_list) == 0 and len(final_gateway_disconnected_list) == 0:
                                # check for string's current zero values.
                                if (
                                        plant.metadata.plantmetasource.irradiation_data is True and irradiation_values is True) or (
                                        plant.metadata.plantmetasource.irradiation_data is False):
                                    # check for AJB strings zero error
                                    ajbs_string_zero_list, ajbs_string_zero_dict = check_ajbs_current_zero_for_plant(plant,
                                                                                                                     timezone.now())
                                    string_current_zero_ticket = Ticket.objects.filter(queue=queue,
                                                                                       event_type='AJB_STRING_CURRENT_ZERO_ALARM',
                                                                                       status=1)
                                    if len(string_current_zero_ticket) > 0:
                                        # Ticket exists already, update associations.
                                        string_current_zero_ticket[0].update_ticket_associations(ajbs_string_zero_list,
                                                                                                 ajbs_string_zero_dict)
                                        if len(ajbs_string_zero_list) == 0:
                                            close_ticket(plant=plant, ticket=string_current_zero_ticket[0],
                                                         request_arrival_time=timezone.now())
                                    elif len(string_current_zero_ticket) == 0 and len(ajbs_string_zero_list) > 0:
                                        # create new ticket for ajbs currentzero error
                                        new_ajb_current_zero_ticket = create_ajb_string_current_zero_ticket(plant,
                                                                                                            priority=1,
                                                                                                            due_date=None)
                                        new_ajb_current_zero_ticket.update_ticket_associations(ajbs_string_zero_list,
                                                                                               ajbs_string_zero_dict)
                                    else:
                                        pass


                    # Following else condition is for non virtual (soekris) gateways
                    else:
                        # check for gateway disconnected
                        plant_gateway_disconnected = check_plant_disconnected(plant, timezone.now())
                        if plant_gateway_disconnected:
                            gateway_source = plant.gateway.all()[0]
                            final_gateway_disconnected_list.append(gateway_source.sourceKey)
                        # check if an open ticket exists for gateway disconnected
                        gateway_disconnected_ticket = Ticket.objects.filter(queue=queue, event_type='GATEWAY_DISCONNECTED',
                                                                            status=1)
                        if len(gateway_disconnected_ticket) > 0:
                            # Tickets exists already, update the associations.
                            gateway_disconnected_ticket[0].update_ticket_associations(final_gateway_disconnected_list)
                            if len(final_gateway_disconnected_list) == 0:
                                close_ticket(plant=plant, ticket=gateway_disconnected_ticket[0],
                                             request_arrival_time=timezone.now())
                                return
                        elif len(gateway_disconnected_ticket) == 0 and len(final_gateway_disconnected_list) > 0:
                            # create new ticket for gateway disconnected
                            new_gateway_disconnected_ticket = create_gateway_disconnected_ticket(plant, priority=2,
                                                                                                 due_date=None)
                            new_gateway_disconnected_ticket.update_ticket_associations(final_gateway_disconnected_list)
                        else:
                            pass

                        # check for inverters disconnected
                        # This should be checked only when there is no gateway disconnected open ticket
                        if len(final_gateway_disconnected_list) == 0:
                            final_inverters_disconnected_list = check_inverters_disconnected_for_plant(plant,
                                                                                                       timezone.now())
                            # check if an open ticket exists for inverters disconnected
                            inverters_disconnected_ticket = Ticket.objects.filter(queue=queue,
                                                                                  event_type='INVERTERS_DISCONNECTED',
                                                                                  status=1)

                            if len(inverters_disconnected_ticket) > 0:
                                # Tickets exists already, update the associations.
                                inverters_disconnected_ticket[0].update_ticket_associations(
                                    final_inverters_disconnected_list)
                                if len(final_inverters_disconnected_list) == 0:
                                    close_ticket(plant=plant, ticket=inverters_disconnected_ticket[0],
                                                 request_arrival_time=timezone.now())
                            elif len(inverters_disconnected_ticket) == 0 and len(final_inverters_disconnected_list) > 0:
                                # create new ticket for inverters disconnected
                                new_inverters_disconnected_ticket = create_inverters_disconnected_ticket(plant, priority=2,
                                                                                                         due_date=None)
                                new_inverters_disconnected_ticket.update_ticket_associations(
                                    final_inverters_disconnected_list)
                            else:
                                pass

                        # check for ajbs disconnected
                        # This should be checked only when there is no gateway disconnected open ticket
                        if len(final_gateway_disconnected_list) == 0:
                            final_ajbs_disconnected_list = check_ajbs_disconnected_for_plant(plant, timezone.now())
                            # check if an open ticket exists for inverters disconnected
                            ajbs_disconnected_ticket = Ticket.objects.filter(queue=queue, event_type='AJBS_DISCONNECTED',
                                                                             status=1)

                            if len(ajbs_disconnected_ticket) > 0:
                                # Ticket exists already, update the associations.
                                ajbs_disconnected_ticket[0].update_ticket_associations(final_ajbs_disconnected_list)
                                if len(final_ajbs_disconnected_list) == 0:
                                    close_ticket(plant=plant, ticket=ajbs_disconnected_ticket[0],
                                                 request_arrival_time=timezone.now())
                            elif len(ajbs_disconnected_ticket) == 0 and len(final_ajbs_disconnected_list) > 0:
                                # create new ticket for inverters disconnected
                                new_ajbs_disconnected_ticket = create_ajbs_disconnected_ticket(plant, priority=2,
                                                                                               due_date=None)
                                new_ajbs_disconnected_ticket.update_ticket_associations(final_ajbs_disconnected_list)
                            else:
                                pass

                        # check for inverter errors
                        # This should be checked only when there is no gateway disconnected open ticket
                        # if len(final_gateway_disconnected_list) == 0:
                        #     final_inverter_alarms = check_inverters_alarms_for_plant(plant, timezone.now())
                        #     #check if an open ticket exists for inverter alarms
                        #     inverters_alarms_ticket = Ticket.objects.filter(queue=queue, event_type='INVERTERS_ALARMS', status=1)
                        #     if len(inverters_alarms_ticket)>0:
                        #         #Ticket exists already, update the associations
                        #         inverters_alarms_ticket[0].update_ticket_associations(final_inverter_alarms.keys(), final_inverter_alarms)
                        #         if len(final_inverter_alarms) == 0:
                        #             close_ticket(plant=plant, ticket=inverters_alarms_ticket[0], request_arrival_time=timezone.now())
                        #     elif len(inverters_alarms_ticket) == 0 and len(final_inverter_alarms) >0:
                        #         # create new ticket for inverter alarms
                        #         new_inverters_alarms_ticket = create_inverters_alarms_ticket(plant, priority=1, due_date=None)
                        #         new_inverters_alarms_ticket.update_ticket_associations(final_inverter_alarms.keys(), final_inverter_alarms)
                        #     else:
                        #         pass

                        # check for inverters alarms based on the solar status values of inverters and the actual alarms raised by inverters.
                        if len(final_gateway_disconnected_list) == 0:
                            final_inverters_not_generating_list, final_inverters_not_generating_status_dict = check_inverters_not_generating_for_plant(
                                plant, timezone.now())
                            final_inverter_alarms = check_inverters_alarms_for_plant(plant, timezone.now(),
                                                                                     final_inverters_not_generating_list)
                            final_inverters_not_generating_list_dual_status, final_inverters_not_generating_status_dict_dual_status = check_inverters_dual_status_for_plant(
                                plant, timezone.now())
                            # print final_inverters_not_generating_list_dual_status
                            # print final_inverters_not_generating_status_dict_dual_status
                            # add solar status in final_inverters alarms
                            # for key in final_inverter_alarms.keys():
                            #     try:
                            #         inverter_solar_status = final_inverters_not_generating_status_dict[key]
                            #         final_inverter_alarms[key]['status_code'] = inverter_solar_status
                            #     except:
                            #         final_inverter_alarms[key]['status_code'] = None
                            #         continue

                            # adding condition to handle the cases when inverters raise alarms under generating status
                            alarms_disabled = False
                            if len(final_inverter_alarms) > 0 and len(final_inverters_not_generating_list) == 0 and \
                                    len(final_inverters_not_generating_list_dual_status) > 0:
                                for sourceKey in final_inverters_not_generating_list_dual_status:
                                    try:
                                        inverter_solar_status = final_inverters_not_generating_status_dict_dual_status[
                                            sourceKey]
                                        final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                    except:
                                        try:
                                            inverter_solar_status = final_inverters_not_generating_status_dict_dual_status[
                                                sourceKey]
                                            final_inverter_alarms[sourceKey] = {}
                                            final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                            final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                            alarms_disabled = True
                                        except:
                                            final_inverter_alarms[sourceKey]['solar_status'] = None
                                            final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                            alarms_disabled = True
                                        continue
                                final_inverters_not_generating_list = final_inverters_not_generating_list_dual_status
                                print "inside dual solar status"
                                print "final_inverters_not_generating_list_dual_status"
                                print final_inverters_not_generating_list_dual_status
                                print "final_inverters_not_generating_list"
                                print final_inverters_not_generating_list

                            elif len(final_inverters_not_generating_list) == 0:
                                final_inverter_alarms = {}
                            else:
                                for sourceKey in final_inverters_not_generating_list:
                                    try:
                                        inverter_solar_status = final_inverters_not_generating_status_dict[sourceKey]
                                        final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                    except:
                                        try:
                                            inverter_solar_status = final_inverters_not_generating_status_dict[sourceKey]
                                            final_inverter_alarms[sourceKey] = {}
                                            final_inverter_alarms[sourceKey]['solar_status'] = inverter_solar_status
                                            final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                            alarms_disabled = True
                                        except:
                                            final_inverter_alarms[sourceKey]['solar_status'] = None
                                            final_inverter_alarms[sourceKey]['alarm_codes'] = []
                                            alarms_disabled = True
                                        continue


                            irradiation_status = check_irradiation_data(
                                timezone.now() - datetime.timedelta(minutes=40), timezone.now(), plant)

                            irradiation_values = irradiation_status is IRRADIATION_VALUES.IRRADIATION_PRESENT or \
                                                 irradiation_status is IRRADIATION_VALUES.DATA_NOT_AVAILABLE

                            if (plant.metadata.plantmetasource.irradiation_data is True and irradiation_values is True)\
                                    or (plant.metadata.plantmetasource.irradiation_data is False):
                                print("Inverter Alarms check for non virtual plants")
                                # check if an open ticket exists for inverters not generating
                                inverters_not_generating_ticket = Ticket.objects.filter(queue=queue,
                                                                                        event_type='INVERTERS_ALARMS',
                                                                                        status=1)
                                if len(inverters_not_generating_ticket) > 0:
                                    # Ticket already exists, update the associations
                                    inverters_not_generating_ticket[0].update_ticket_associations(
                                        final_inverters_not_generating_list, alarms_dict=final_inverter_alarms,
                                        alarms_disabled=alarms_disabled)
                                    if len(final_inverters_not_generating_list) == 0:
                                        close_ticket(plant=plant, ticket=inverters_not_generating_ticket[0],
                                                     request_arrival_time=timezone.now())
                                elif len(inverters_not_generating_ticket) == 0 and len(
                                        final_inverters_not_generating_list) > 0:
                                    # create new ticket for inverters alarms
                                    new_inverters_not_generating_ticket = create_inverters_alarms_ticket(plant, priority=1,
                                                                                                         due_date=None)
                                    new_inverters_not_generating_ticket.update_ticket_associations(
                                        final_inverters_not_generating_list, alarms_dict=final_inverter_alarms,
                                        alarms_disabled=alarms_disabled)
                                else:
                                    pass

                        # String current zero values
                        if len(final_gateway_disconnected_list) == 0:
                            # check for string's current zero values.
                            if (plant.metadata.plantmetasource.irradiation_data is True and irradiation_values is True) or (
                                    plant.metadata.plantmetasource.irradiation_data is False):
                                # check for AJB strings zero error
                                print "checking for string current zero values"
                                ajbs_string_zero_list, ajbs_string_zero_dict = check_ajbs_current_zero_for_plant(plant,
                                                                                                                 timezone.now())
                                print "ajbs_string_zero_list"
                                print ajbs_string_zero_list
                                print "ajbs_string_zero_dict"
                                print ajbs_string_zero_dict
                                string_current_zero_ticket = Ticket.objects.filter(queue=queue,
                                                                                   event_type='AJB_STRING_CURRENT_ZERO_ALARM',
                                                                                   status=1)
                                if len(string_current_zero_ticket) > 0:
                                    # Ticket exists already, update associations.
                                    string_current_zero_ticket[0].update_ticket_associations(ajbs_string_zero_list,
                                                                                             ajbs_string_zero_dict)
                                    if len(ajbs_string_zero_list) == 0:
                                        close_ticket(plant=plant, ticket=string_current_zero_ticket[0],
                                                     request_arrival_time=timezone.now())
                                elif len(string_current_zero_ticket) == 0 and len(ajbs_string_zero_list) > 0:
                                    # create new ticket for ajbs currentzero error
                                    new_ajb_current_zero_ticket = create_ajb_string_current_zero_ticket(plant, priority=1,
                                                                                                        due_date=None)
                                    new_ajb_current_zero_ticket.update_ticket_associations(ajbs_string_zero_list,
                                                                                           ajbs_string_zero_dict)
                                else:
                                    pass
        except Exception as exception:
            print(str(exception))


def new_solar_events_check(plant_id=None):
    import random
    t1 = timezone.now()
    run_id = str(random.randrange(1000000,
                                  2000000))
    try:
        logger.debug("Tickets cron job run at : " + str(timezone.now()) + " for plant id: " + str(plant_id))
        if plant_id:
            plants = SolarPlant.objects.filter(id = plant_id).exclude(slug__in=DISABLE_NEW_TICKET_FOR_PLANTS)
        else:
            plants = SolarPlant.objects.all().exclude(slug__in=DISABLE_NEW_TICKET_FOR_PLANTS)
        cassandra_up_time = 4000
        if not plant_id:
            cassandra_up_time = check_cassandra_up_time_new()
        dgc_up = check_dgc_up()
        ftp_up = check_ftp_up()
        if cassandra_up_time > 3600 and dgc_up is True and ftp_up is True:
            for plant in plants:
                logger.debug(",".join(["Checking for plant", plant.slug]))
                try:
                    check_tickets_for_a_plant(plant,
                                              run_id=str(run_id))
                except Exception as exc:
                    logger.debug(",".join(["error running a ticket run for plant", plant.slug, str(exc)]))
                    continue
    except Exception as exception:
        print(str(exception))
    logger.debug("ID_LOG: total run time: " + str(timezone.now() - t1))


@shared_task
def new_solar_events_check_for_a_plant(plant_id):
    # analyse_ticket.apply_async(args=[ticket.id], countdown=60*30)
    new_solar_events_check(plant_id)

# This reads unread messages from inbox of ge@dataglen.com. User sends email to the plant email ids. Plant slug is fetched from plant email
# to create ticket.
def custom_tickets_created_by_user_emails():
    EMAIL_ACCOUNT = 'ge@dataglen.com '
    PASSWORD = 'q>23=qJn'
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(EMAIL_ACCOUNT, PASSWORD)
    mail.list()
    mail.select('inbox')
    result, data = mail.uid('search', None, "UNSEEN")  # (ALL/UNSEEN)
    i = len(data[0].split())
    # iterate over unseen/ all emails i
    for x in range(i):
        latest_email_uid = data[0].split()[x]
        result, email_data = mail.uid('fetch', latest_email_uid, '(RFC822)')
        raw_email = email_data[0][1]
        raw_email_string = raw_email.decode('utf-8')
        email_message = email.message_from_string(raw_email_string)

        # Header Details
        date_tuple = email.utils.parsedate_tz(email_message['Date'])
        if date_tuple:
            local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            local_message_date = "%s" % (str(local_date.strftime("%a, %d %b %Y %H:%M:%S")))
        email_from = str(email.header.make_header(email.header.decode_header(email_message['From'])))
        email_to = str(email.header.make_header(email.header.decode_header(email_message['To'])))
        subject = str(email.header.make_header(email.header.decode_header(email_message['Subject'])))

        # Body details
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True)
                # print ("From: %s\nTo: %s\nDate: %s\nSubject: %s\n\nBody: \n\n%s" %(email_from, email_to,\
                # local_message_date, subject, body.decode('utf-8')))
                emailId = re.findall(r'[\w\.-]+@[\w\.-]+', email_to)[0]
                slug = emailId.split('@')[0]
                priority = 3
                due_date = timezone.now() + datetime.timedelta(days=7)
                ticket_name = subject
                ticket_description = body.decode('utf-8')
                event_type = ""
                open_comment = "sample comment"

                try:
                    plant = SolarPlant.objects.get(slug=slug)
                except Exception as e:
                    print("Solar Plant not found")
                    logger.debug("Solar Plant not found. Cannot Create ticket")

                try:
                    user = User.objects.get(email=email_from)
                except Exception as e:
                    logger.debug("user not found %s"% email_from)
                    user = None
                    open_comment = "Ticket is created by: %s" %email_from

                c = create_ticket(plant=plant, priority=priority, due_date=due_date,
                                  ticket_name=ticket_name, ticket_description=ticket_description, event_type=event_type,
                                  open_comment=open_comment, user=user, send_email=False)
                if c:
                    logger.debug("User has created custom ticket for plant slug == == %s" %slug)
                    logger.debug("Ticket id is : %s",c)
            else:
                continue