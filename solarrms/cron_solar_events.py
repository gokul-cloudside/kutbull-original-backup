from events.models import EventsByTime, EventsConfig, EventsByError, Events, UserEventAlertsPreferences, AlertManagement
from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource, PerformanceRatioTable, \
    InverterErrorCodes, AJB, EnergyMeter, Transformer
from dataglen.models import ValidDataStorageByStream
import datetime
from django.core.exceptions import ObjectDoesNotExist
import pytz
from monitoring.models import SourceMonitoring
from cassandra.cqlengine.query import BatchQuery
from django.core.mail import send_mail
from django.utils import timezone
from dataglen.models import Sensor
from .settings import PLANT_DEFAULT_END_TIME, PLANT_DEFAULT_START_TIME, PLANT_DEFAULT_TIMEZONE
from kutbill.settings import EVENTS_UPDATE_INTERVAL_MINUTES
from django.template import Context
from django.template.loader import render_to_string, get_template
from django.core.mail import EmailMessage
from utils.views import send_twilio_message, send_solutions_infini_sms
from solarrms.solarutils import get_aggregated_energy, get_energy_meter_values
from errors.models import ErrorStorageByStream
from tabulate import tabulate
from django.core.mail import EmailMultiAlternatives
from tabulate import tabulate
from helpdesk.dg_functions import create_ticket, update_ticket
from helpdesk.models import Ticket, Queue, TicketAssociation
from solarrms.models import PlantCompleteValues
from helpdesk.dg_functions import get_plant_tickets_date
import smtplib,email,email.encoders,email.mime.text,email.mime.base

from IPython.display import display, HTML
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#from solarrms.api_views import fix_generation_units
import calendar
EMAIL_TITLE    = "DataGlen Solar RMS Alert for "
#EMAIL_TITLE    = "DataGlen Alert for"
SIGNOFF_STRING = "\n--\nDataGlen Solar RMS"
FROM_ERROR_EMAIL = 'alerts@dataglen.com'
FROM_INFO_EMAIL = 'info@dataglen.com'
FROM_REPORT_EMAIL = 'reports@dataglen.com'

default_sla_l1 = {1: 15, 2: 60, 3: 120, 4: 180, 5: 360}

def fix_generation_units(generation):
    if generation > 100000000.0:
        return "{0:.2f} GWh".format(generation/1000000.0)
    if generation > 100000.0:
        return "{0:.2f} Mwh".format(generation/1000.0)
    else:
        return "{0:.2f} kWh".format(generation)

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

def create_inverter_disconnected_ticket(plant, inverters_INVERTER_DISCONNECTED_ticket, current_time):
    print("inside inverter disconnected ticket")
    if len(inverters_INVERTER_DISCONNECTED_ticket) == 0:
        pass
    else:
        associations_dict = {}
        for inverter in inverters_INVERTER_DISCONNECTED_ticket:
            associations_dict[inverter.sourceKey] = ['INVERTER_DISCONNECTED', '-1', inverter.name, current_time]
        try:
            priority = 2
            due_minutes = default_sla_l1[priority]
            due_date = current_time + datetime.timedelta(minutes=due_minutes)
            #user = plant.owner.organization_user.user
            create_ticket(plant=plant, priority=priority, due_date=due_date,
                          ticket_name="Inverter disconnected at " + str(plant.location),
                          ticket_description = 'Inverter disconnected event has occurred at : ' + str(plant.location),
                          associations_dict = associations_dict,
                          open_comment='Ticket created automatically based on the inverter disconnected alerts.')
        except Exception as exception:
            print("Error in creating ticket for Inverter disconnected at : " + str(plant.name) + " : " + str(exception))


def create_ajb_disconnected_ticket(plant, ajbs_AJB_DISCONNECTED_ticket, current_time):
    print("inside ajb disconnected ticket")
    if len(ajbs_AJB_DISCONNECTED_ticket) == 0:
        pass
    else:
        associations_dict = {}
        for ajb in ajbs_AJB_DISCONNECTED_ticket:
            associations_dict[ajb.sourceKey] = ['AJB_DISCONNECTED', '-1', ajb.name, current_time]
        try:
            priority = 2
            due_minutes = default_sla_l1[priority]
            due_date = current_time + datetime.timedelta(minutes=due_minutes)
            #user = plant.owner.organization_user.user
            create_ticket(plant=plant, priority=priority, due_date=due_date,
                          ticket_name="AJB disconnected at " + str(plant.location),
                          ticket_description = 'AJB Off event has occurred at : ' + str(plant.location),
                          associations_dict = associations_dict,
                          open_comment='Ticket created automatically based on the ajb disconnected alerts.')
        except Exception as exception:
            print("Error in creating ticket for Ajb disconnected at : " + str(plant.name) + " : " + str(exception))


def create_network_down_ticket(plant, gateways_NETWORK_DOWN_ticket, current_time):
    print("inside network down ticket")
    print(len(gateways_NETWORK_DOWN_ticket))
    if len(gateways_NETWORK_DOWN_ticket) == 0:
        pass
    else:
        associations_dict = {}
        for gateway in gateways_NETWORK_DOWN_ticket:
            associations_dict[gateway.sourceKey] = ['NETWORK_DOWN', '-1', gateway.name, current_time]
        priority = 1
        due_minutes = default_sla_l1[priority]
        due_date = current_time + datetime.timedelta(minutes=due_minutes)
        #user = plant.owner.organization_user.user
        try:
            create_ticket(plant=plant, priority=priority, due_date=due_date,
                          ticket_name="Network down at " + str(plant.location),
                          ticket_description = 'Network down event has occurred at : ' + str(plant.location),
                          associations_dict = associations_dict,
                          open_comment='Ticket created automatically based on the network down alerts.')
        except Exception as exception:
            print("Error in creating NETWORK_DOWN ticket for : " + str(gateway.sourceKey) + " : " + str(exception))


def update_network_down_ticket(plant, gateways_NETWORK_UP_ticket, current_time):
    print("inside update network down ticket")
    print(gateways_NETWORK_UP_ticket)
    ticket = None
    if len(gateways_NETWORK_UP_ticket) == 0:
        pass
    else:
        ticket_associations = []
        for gateway in gateways_NETWORK_UP_ticket:
            print(gateway.sourceKey)
            ticket_association = TicketAssociation.objects.filter(identifier=gateway.sourceKey,
                                                                   event_name='NETWORK_DOWN',
                                                                   event_code='-1',
                                                                   status=True)
            print(ticket_association)
            ticket_associations.extend(ticket_association)
            print(ticket_associations)
        print("ticket_associations " + str(ticket_associations))

        try:
            for association in ticket_associations:
                ticket = association.ticket
                association.status = False
                association.save()
                print("association.status : " + str(association.status))
        except Exception as exception:
            print("Error in updating the status of ticket association for : " + str(association.identifier_name) + " : " + str(exception))
        try:
            final_ticket_associations = TicketAssociation.objects.filter(ticket=ticket, status=True)
            print("final_ticket_associations : " + str(final_ticket_associations))
            if ticket and len(final_ticket_associations) == 0:
                user = plant.owner.organization_user.user
                update_ticket(plant = plant, ticket_id = ticket.id, followup_user = user,
                              comment = 'Ticket got closed automatically based on the alert',
                              new_status = Ticket.CLOSED_STATUS,
                              title = str(ticket.title) + " - Resolved at " + str(current_time))
        except Exception as exception:
            print("Error in closing the network down ticket for : " + str(plant.name) + " : " + str(exception))

def update_inverter_disconnected_ticket(plant, inverters_INVERTER_CONNECTED_ticket, current_time):
    ticket = None
    if len(inverters_INVERTER_CONNECTED_ticket) == 0:
        pass
    else:
        ticket_associations = []
        for inverter in inverters_INVERTER_CONNECTED_ticket:
            print(inverter.sourceKey)
            ticket_association = TicketAssociation.objects.filter(identifier=inverter.sourceKey,
                                                                   event_name='INVERTER_DISCONNECTED',
                                                                   event_code='-1',
                                                                   status=True)
            print(ticket_association)
            ticket_associations.extend(ticket_association)
            print(ticket_associations)
        print("ticket_associations " + str(ticket_associations))

        try:
            for association in ticket_associations:
                ticket = association.ticket
                association.status = False
                association.save()
                print("association.status : " + str(association.status))
                try:
                    final_ticket_associations = TicketAssociation.objects.filter(ticket=ticket, status=True)
                    print("final_ticket_associations : " + str(final_ticket_associations))
                    if ticket and len(final_ticket_associations) == 0:
                        user = plant.owner.organization_user.user
                        update_ticket(plant = plant, ticket_id = ticket.id, followup_user = user,
                                      comment = 'Ticket got closed automatically based on the alert',
                                      new_status = Ticket.CLOSED_STATUS,
                                      title = str(ticket.title) + " - Resolved at " + str(current_time))
                except Exception as exception:
                    print("Error in closing the inverter disconnected ticket for : " + str(plant.name) + " : " + str(exception))
        except Exception as exception:
            print("Error in updating the status of ticket association for : " + str(association.identifier_name) + " : " + str(exception))

def update_ajb_disconnected_ticket(plant, ajbs_AJB_CONNECTED_ticket, current_time):
    ticket = None
    if len(ajbs_AJB_CONNECTED_ticket) == 0:
        pass
    else:
        ticket_associations = []
        for ajb in ajbs_AJB_CONNECTED_ticket:
            print(ajb.sourceKey)
            ticket_association = TicketAssociation.objects.filter(identifier=ajb.sourceKey,
                                                                   event_name='AJB_DISCONNECTED',
                                                                   event_code='-1',
                                                                   status=True)
            print(ticket_association)
            ticket_associations.extend(ticket_association)
            print(ticket_associations)
        print("ticket_associations " + str(ticket_associations))

        try:
            for association in ticket_associations:
                ticket = association.ticket
                association.status = False
                association.save()
                print("association.status : " + str(association.status))
                try:
                    final_ticket_associations = TicketAssociation.objects.filter(ticket=ticket, status=True)
                    print("final_ticket_associations : " + str(final_ticket_associations))
                    if ticket and len(final_ticket_associations) == 0:
                        user = plant.owner.organization_user.user
                        update_ticket(plant = plant, ticket_id = ticket.id, followup_user = user,
                                      comment = 'Ticket got closed automatically based on the alert',
                                      new_status = Ticket.CLOSED_STATUS,
                                      title = str(ticket.title) + " - Resolved at " + str(current_time))
                except Exception as exception:
                    print("Error in closing the ajb disconnected ticket for : " + str(plant.name) + " : " + str(exception))
        except Exception as exception:
            print("Error in updating the status of ticket association for : " + str(association.identifier_name) + " : " + str(exception))


def create_inverter_error_ticket(plant, initial_time):
    print("inside inverter error ticket")
    inverters = IndependentInverter.objects.filter(plant=plant)
    for inverter in inverters:
        current_time = timezone.now()
        current_time = update_tz(current_time, inverter.dataTimezone)
        inverter_error_values = EventsByError.objects.filter(identifier=inverter.sourceKey,
                                                             event_name="INVERTER_ERROR",
                                                             insertion_time__gt=initial_time)
        for value in inverter_error_values:
            associations_dict = {}
            associations_dict[value.identifier] = ['INVERTER_ERROR', value.event_code, inverter.name, current_time]
            priority = 1
            due_minutes = default_sla_l1[priority]
            due_date = current_time + datetime.timedelta(minutes=due_minutes)
            #user = plant.owner.organization_user.user
            inverter_error = InverterErrorCodes.objects.get(manufacturer=inverter.manufacturer,
                                                            model=inverter.model,
                                                            error_code=value.event_code)
            try:
                create_ticket(plant=plant, priority=priority, due_date=due_date,
                              ticket_name="Inverter Error at " + str(plant.location) + " for: " + str(inverter.name) + "_" +str(value.event_code),
                              ticket_description="Inverter Error has occurred at : {0} for {1}\n{2} : {3}\n {4}".format(
                                  str(plant.location), str(inverter.name), str(value.event_code), str(inverter_error.error_description), str(inverter_error.notes)),
                              associations_dict = associations_dict,
                              open_comment='Ticket created automatically based on the inverter alarm.')
            except Exception as exception:
                print("Error in creating INVERTER_ERROR ticket for : {0} : {1}".format(str(inverter.sourceKey), str(exception)))


def events_write(request_arrival_time, event_time, identifier , event_name, event_code):
    try:
        print("inside events write")
        batch_query = BatchQuery()
        EventsByTime.batch(batch_query).create(identifier=identifier,
                                               insertion_time=request_arrival_time,
                                               event_name=event_name,
                                               event_time=event_time,
                                               event_code=event_code)

        EventsByError.batch(batch_query).create(identifier=identifier,
                                                event_name=event_name,
                                                insertion_time=request_arrival_time,
                                                event_time=event_time,
                                                event_code=event_code)

        batch_query.execute()
        #sendAlerts(identifier, request_arrival_time, event_name, request_arrival_time)

    except Exception as exception:
        print("Error in saving events: " + str(exception))

def events_read():
    print("Events read cron job started: ",str(datetime.datetime.now()))
    try:
        plants = SolarPlant.objects.all()
    except ObjectDoesNotExist:
        print("No solar plant found.")
        current_time = timezone.now()
    # iterate for all the plants
    for plant in plants:
        try:
            print("For plant: ", plant.slug)
            gateways = GatewaySource.objects.filter(plant=plant)
            gateways_NETWORK_DOWN = []
            gateways_NETWORK_DOWN_ticket = []
            gateways_NETWORK_UP = []
            gateways_NETWORK_UP_ticket = []
            for gateway in gateways:
                try:
                    tz = pytz.timezone(gateway.dataTimezone)
                    #print("tz" , tz)
                except:
                    print("error in converting current time to source timezone")
                try:
                    current_time = timezone.now()
                    # astimezone does the conversion and updates the tzinfo part
                    current_time = current_time.astimezone(pytz.timezone(gateway.dataTimezone))
                except Exception as exc:
                    current_time = timezone.now()
                # if  current_time.minute < EVENTS_UPDATE_INTERVAL_MINUTES:
                #     initial_time = current_time.replace(second=0, microsecond=0, minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES+60, hour=current_time.hour-1)
                # else:
                #     initial_time = current_time.replace(second=0, microsecond=0, minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES)
                initial_time = current_time - datetime.timedelta(minutes=EVENTS_UPDATE_INTERVAL_MINUTES)
                gateway_events = EventsByTime.objects.filter(identifier=gateway.sourceKey, insertion_time__gt=initial_time).limit(1)
                if len(gateway_events):
                    if gateway_events[0].event_name == "NETWORK_DOWN":
                        gateways_NETWORK_DOWN.append(gateway.name)
                        gateways_NETWORK_DOWN_ticket.append(gateway)
                    elif gateway_events[0].event_name == "NETWORK_UP":
                        gateways_NETWORK_UP.append(gateway.name)
                        gateways_NETWORK_UP_ticket.append(gateway)
            if len(gateways_NETWORK_DOWN)>0:
                #sendAlerts(identifier=plant.slug,event_name="NETWORK_DOWN",request_arrival_time=current_time,event_sources=gateways_NETWORK_DOWN,event_time=current_time)
                create_network_down_ticket(plant=plant, gateways_NETWORK_DOWN_ticket=gateways_NETWORK_DOWN_ticket, current_time=current_time)
                sendAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,event_name="NETWORK_DOWN",request_arrival_time=current_time,event_sources=gateways_NETWORK_DOWN,event_time=current_time)
                print("NETWORK_DOWN event notification sent")
            if len(gateways_NETWORK_UP)>0:
                #sendAlerts(identifier=plant.slug,event_name="NETWORK_UP",request_arrival_time=current_time,event_sources=gateways_NETWORK_UP,event_time=current_time)
                update_network_down_ticket(plant=plant, gateways_NETWORK_UP_ticket = gateways_NETWORK_UP_ticket, current_time=current_time)
                sendAlertsWithoutCheck(event_type='INFO',identifier=plant.slug,event_name="NETWORK_UP",request_arrival_time=current_time,event_sources=gateways_NETWORK_UP,event_time=current_time)
                print("NETWORK_UP event notification sent")
            inverters_INVERTER_DISCONNECTED =[]
            inverters_INVERTER_CONNECTED = []
            inverters_INVERTER_DISCONNECTED_ticket = []
            inverters_INVERTER_CONNECTED_ticket = []
            inverters = IndependentInverter.objects.filter(plant=plant)
            for inverter in inverters:
                try:
                    tz = pytz.timezone(inverter.dataTimezone)
                    #print("tz" , tz)
                except:
                    print("error in converting current time to source timezone")
                try:
                    current_time = timezone.now()
                    # astimezone does the conversion and updates the tzinfo part
                    current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))

                except Exception as exc:
                    current_time = timezone.now()
                #print("current_time", current_time)
                #initial_time = current_time.replace(minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES, second=0, microsecond=0)
                initial_time = current_time - datetime.timedelta(minutes=EVENTS_UPDATE_INTERVAL_MINUTES)
                #print("initial_time", initial_time)
                inverter_events = EventsByTime.objects.filter(identifier=inverter.sourceKey, insertion_time__gt=initial_time).limit(1)
                if len(inverter_events) > 0:
                    if inverter_events[0].event_name == "INVERTER_DISCONNECTED":
                        inverters_INVERTER_DISCONNECTED.append(inverter.name)
                        inverters_INVERTER_DISCONNECTED_ticket.append(inverter)
                    elif inverter_events[0].event_name == "INVERTER_CONNECTED":
                        inverters_INVERTER_CONNECTED.append(inverter.name)
                        inverters_INVERTER_CONNECTED_ticket.append(inverter)
            #TODO: change identifier to user_slug
            if len(inverters_INVERTER_DISCONNECTED)>0:
                #sendAlerts(identifier=plant.slug,event_name="INVERTER_DISCONNECTED",request_arrival_time=current_time,event_sources=inverters_INVERTER_DISCONNECTED,event_time=current_time)
                create_inverter_disconnected_ticket(plant=plant, inverters_INVERTER_DISCONNECTED_ticket=inverters_INVERTER_DISCONNECTED_ticket, current_time=current_time)
                sendAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,event_name="INVERTER_DISCONNECTED",request_arrival_time=current_time,event_sources=inverters_INVERTER_DISCONNECTED,event_time=current_time)
                print("INVERTER_DISCONNECTED event notification sent")
            if len(inverters_INVERTER_CONNECTED)>0:
                #sendAlerts(identifier=plant.slug,event_name="INVERTER_CONNECTED",request_arrival_time=current_time,event_sources=inverters_INVERTER_CONNECTED,event_time=current_time)
                update_inverter_disconnected_ticket(plant=plant, inverters_INVERTER_CONNECTED_ticket=inverters_INVERTER_CONNECTED_ticket, current_time=current_time)
                sendAlertsWithoutCheck(event_type='INFO',identifier=plant.slug,event_name="INVERTER_CONNECTED",request_arrival_time=current_time,event_sources=inverters_INVERTER_CONNECTED,event_time=current_time)
                print("INVERTER_CONNECTED notification sent")

            ajbs_AJB_DISCONNECTED =[]
            ajbs_AJB_CONNECTED = []
            ajbs_AJB_DISCONNECTED_ticket = []
            ajbs_AJB_CONNECTED_ticket = []
            ajbs = AJB.objects.filter(plant=plant)
            for ajb in ajbs:
                try:
                    tz = pytz.timezone(ajb.dataTimezone)
                except:
                    print("error in converting current time to source timezone")
                try:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(ajb.dataTimezone))
                except Exception as exc:
                    current_time = timezone.now()

                #initial_time = current_time.replace(minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES, second=0, microsecond=0)
                initial_time = current_time - datetime.timedelta(minutes=EVENTS_UPDATE_INTERVAL_MINUTES)
                ajb_events = EventsByTime.objects.filter(identifier=ajb.sourceKey, insertion_time__gt=initial_time).limit(1)
                if len(ajb_events) > 0:
                    if ajb_events[0].event_name == "AJB_DISCONNECTED":
                        ajbs_AJB_DISCONNECTED.append(ajb.name)
                        ajbs_AJB_DISCONNECTED_ticket.append(ajb)
                    elif ajb_events[0].event_name == "AJB_CONNECTED":
                        ajbs_AJB_CONNECTED.append(ajb.name)
                        ajbs_AJB_CONNECTED_ticket.append(ajb)

            if len(ajbs_AJB_DISCONNECTED)>0:
                create_ajb_disconnected_ticket(plant=plant, ajbs_AJB_DISCONNECTED_ticket=ajbs_AJB_DISCONNECTED_ticket, current_time=current_time)
                sendAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,event_name="AJB_DISCONNECTED",request_arrival_time=current_time,event_sources=ajbs_AJB_DISCONNECTED,event_time=current_time)
                print("AJB_DISCONNECTED event notification sent")
            if len(ajbs_AJB_CONNECTED)>0:
                update_ajb_disconnected_ticket(plant=plant, ajbs_AJB_CONNECTED_ticket=ajbs_AJB_CONNECTED_ticket, current_time=current_time)
                sendAlertsWithoutCheck(event_type='INFO',identifier=plant.slug,event_name="AJB_CONNECTED",request_arrival_time=current_time,event_sources=ajbs_AJB_CONNECTED,event_time=current_time)
                print("AJB_CONNECTED notification sent")

        except Exception as ex:
            print("ERROR: ",ex.message)

def sendAlertsWithoutCheck(event_type, identifier,
                           request_arrival_time,
                           event_name, event_time, event_sources):
    try:
        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=identifier,
                                                                  event=event,
                                                                  alert_active=True)

        for alert in active_alerts:
            print("inside for")
            email = alert.email_id
            phone = alert.phone_no
            plants = SolarPlant.objects.filter(slug=identifier)
            plant = plants[0]
            if len(plants)>0:
                plant_location = plants[0].location
            try:
                new_alert = AlertManagement(identifier=identifier,
                                            alert_time=request_arrival_time,
                                            event_time=event_time,
                                            event=event,
                                            email_id=email,
                                            phone_no=phone)

                new_alert.save()
                event_sources_str =''
                event_sources_sms =''
                j = 1
                for event_source in event_sources:
                    event_sources_str = event_sources_str+ str(j) + '. ' + str(event_source)+'<br>'
                    j += 1
                    event_sources_sms = event_sources_sms+ str(event_source)+', '

                sms_message = str(event_name) + ' event occurred at ' + str(plant_location) +' for:\n'+str(event_sources_sms)
                try:
                    if email!='':
                        if str(event_type) is 'ERROR':
                            send_error_alert(plant=plant, event_type=event_type, event_name=event_name, event_sources=event_sources_str, email=email)
                        elif str(event_type) is 'INFO':
                            send_error_info(plant=plant, event_type=event_type, event_name=event_name, event_sources=event_sources_str, email=email)
                        else:
                            send_error_alert(plant=plant, event_type=event_type, event_name=event_name, event_sources=event_sources_str, email=email)
                except Exception as exception:
                    print("Error in sendng email " + str(exception))
                try:
                    if phone!='':
                        #send_twilio_message(phone, sms_message)
                        send_solutions_infini_sms(phone,sms_message)
                except Exception as exception:
                    print("Error in sending sms" + str(exception))

            except Exception as exception:
                print("Error in saving new alerts" + str(exception))

    except Exception as exception:
        print(str(exception))

def send_report(request_arrival_time,
                event_name):
    try:
        plant_meta_sources = PlantMetaSource.objects.all()
        for plant_meta_source in plant_meta_sources:
            if plant_meta_source.plant.isOperational:
                print("plant is operational")
                if plant_meta_source.isMonitored:
                    print("plant is running in its operational time")
                    # do nothing
                    pass
                else:
                    print("plant is not running in its operational time")
                    try:
                        event = Events.objects.get(event_name=event_name)
                        print("event : " + str(event))
                    except Exception as exception:
                        print("No such event found : " + str(exception))
                    try:
                        tz = pytz.timezone(plant_meta_source.dataTimezone)
                        #print("tz" , tz)
                    except:
                        print("error in converting current time to source timezone")
                    try:
                        request_arrival_time = request_arrival_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
                    except Exception as exc:
                        print(str(exc))
                    report_time = request_arrival_time.replace(hour=0,minute=0,second=0,microsecond=0)
                    report_events = EventsByTime.objects.filter(event_name=event_name,identifier=plant_meta_source.sourceKey,insertion_time=report_time)
                    request_time = request_arrival_time.time()
                    operations_start_time = datetime.datetime.strptime(plant_meta_source.operations_start_time , '%H:%M:%S')
                    operations_start_time = operations_start_time + datetime.timedelta(minutes=EVENTS_UPDATE_INTERVAL_MINUTES)
                    operations_start_time = operations_start_time.time()
                    print("request_time: ", request_time)
                    print("operations_start_time: ", operations_start_time)
                    print("report events length : ", len(report_events))
                    if(len(report_events)>0 or request_time < operations_start_time):
                        print("inside if")
                        # The report has already been sent or the report time is after midnight and before operations_start_time of plant in the morning
                        # do nothing
                        pass
                    else:
                        print("inside else")
                        # log an event for DAILY_REPORT
                        try:
                            events_write(report_time, report_time, plant_meta_source.sourceKey, "DAILY_REPORT", "-1")
                        except Exception as exception:
                            print("Error in writting DAILY_REPORT event")
                        # get the energy value generated today
                        initial_time = request_arrival_time.replace(hour=0,minute=0,second=0)
                        current_time = request_arrival_time.replace(hour=23,minute=59,second=59)
                        #print("initial_time: ", initial_time)
                        #print("current_time: ", current_time)
                        try:
                            if plant_meta_source.energy_meter_installed:
                                print("inside energy meter")
                                todays_energy = get_energy_meter_values(initial_time,current_time,plant_meta_source.plant,'DAY')
                            else:
                                todays_energy = get_aggregated_energy(initial_time,current_time,plant_meta_source.plant,'DAY')
                            #todays_energy = get_aggregated_energy(initial_time,current_time,plant_meta_source.plant,'DAY')
                        except Exception as exception:
                            print("Error in getting todays energy value : " + str(exception))
                        print(todays_energy)
                        if todays_energy and len(todays_energy)>0:
                            energy_values = [item['energy'] for item in todays_energy]
                            if len(energy_values) > 0:
                                today_energy_value = energy_values[len(energy_values)-1]
                                today_energy_value = round(today_energy_value,3)
                            else:
                                today_energy_value = 0.0
                        else:
                            today_energy_value = 0.0
                        print('today\'s energy calculated from method: ', today_energy_value)

                        # get today's PR value
                        try:
                            performance_ratio = PerformanceRatioTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                     count_time_period=86400,
                                                                                     identifier=plant_meta_source.sourceKey,
                                                                                     ts=report_time)
                            if (len(performance_ratio)>0):
                                performance_ratio_value = performance_ratio[0].performance_ratio
                                performance_ratio_value = round(performance_ratio_value,3)
                            else:
                                performance_ratio_value = 0.0

                        except Exception as exception:
                            print("Error in getting the PR value : " + str(exception))

                        # send email for today's energy generation.
                        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=plant_meta_source.plant.slug,
                                                                                  event=event,
                                                                                  alert_active=True)

                        for alert in active_alerts:
                            print("inside for")
                            FROM_EMAIL = FROM_REPORT_EMAIL
                            email = alert.email_id
                            phone = alert.phone_no
                            plant_location = plant_meta_source.plant.location
                            plant_name = plant_meta_source.plant.name
                            try:
                                new_alert = AlertManagement(identifier=plant_meta_source.plant.slug,
                                                            alert_time=request_arrival_time,
                                                            event_time=request_arrival_time,
                                                            event=event,
                                                            email_id=email,
                                                            phone_no=phone)

                                new_alert.save()
                            except Exception as exception:
                                print("Error in saving new alert for daily report : " + str(exception))

                            # try:
                            #     html_content = '<body style="background-color:yellow;"> <h1><center> Today\'s Performance Report </center></h1></body></br>'
                            #     email_subject = '[INFO]' + ' Daily Performance Report for plant' + " at " + str(plant_location)
                            #     html_content += 'Hi,<br><br>This is a notification from DataGlen Solar RMS.<br>Today\'s Energy Generation : '+ str(today_energy_value) + str(' kWh') + '<br>Today\'s Performance Ratio : ' + str(performance_ratio_value)
                            #     html_content += '<br><br> Thank You, <br> Team DataGlen <br>'
                            #     html_content += '<body style="background-color:powderblue;" align="right"><h5>Connect with us </h5><a href="https://twitter.com/dataglen">Twitter</a> <a href="https://www.linkedin.com/company/dataglen">LinkedIn</a> <a href="https://www.facebook.com/dataglen/">Facebook</body>'
                            #     text_content = ''
                            #     if email!='':
                            #         # message_body =  'Hi,\nThis is a notification from DataGlen Solar RMS. \nToday\'s Energy Generation : '+ str(today_energy_value) + str(' kWh') + '\nToday\'s Performance Ratio : ' + str(performance_ratio_value) + '\n\nThank you,\nTeam DataGlen'
                            #         # send_mail(message_subject,
                            #         #     message_body,
                            #         #     FROM_EMAIL, [email], fail_silently=False)
                            #         msg = EmailMultiAlternatives(email_subject, text_content, FROM_EMAIL, [email])
                            #         msg.attach_alternative(html_content, "text/html")
                            #         msg.send()
                            # except Exception as exception:
                            #     print("Error in sending daily report email")
                            try:
                                if email != '':
                                    send_detailed_report(plant_meta_source.plant, email)
                            except Exception as exception:
                                print("Error in sending daily report for the plant - " + str(plant_meta_source.plant.slug) + ' : ' + str(exception))

                            sms_message = 'Hi,\nDaily Performance Report of your plant at '+ str(plant_location)+':\nEnergy Generation : '+ str(today_energy_value) + str(' kWh') + ' ,\nPerformance Ratio : ' + str(performance_ratio_value) + ' ,\nThank you'
                            try:
                                if phone!='':
                                    #send_twilio_message(phone, sms_message)
                                    send_solutions_infini_sms(phone,sms_message)
                            except Exception as exception:
                                print("Error in sending sms" + str(exception))

    except Exception as exception:
        print("Error in sending daily report: " + str(exception))

def sendAlerts(identifier,
               request_arrival_time,
               event_name, event_time, event_sources):
    try:
        FROM_EMAIL = FROM_ERROR_EMAIL
        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=identifier,
                                                                  event=event,
                                                                  alert_active=True)

        for alert in active_alerts:
            print("inside for")
            email = alert.email_id
            phone = alert.phone_no
            alert_interval = alert.alert_interval
            last_alert_time = AlertManagement.objects.filter(identifier=identifier,
                                                             event=event,
                                                             email_id=email).order_by("-alert_time")
            plants = SolarPlant.objects.filter(slug=identifier)
            plant_location = identifier
            if len(plants)>0:
                plant_location = plants[0].location
            print("last_alert_time",last_alert_time)
            if len(last_alert_time) > 0:
                if last_alert_time[0].alert_time + datetime.timedelta(minutes=alert_interval) < request_arrival_time:
                    print("inside if")
                    try:
                        new_alert = AlertManagement(identifier=identifier,
                                                    alert_time=request_arrival_time,
                                                    event_time=event_time,
                                                    event=event,
                                                    email_id=email,
                                                    phone_no=phone)#,
                                                    #event_sources=event_sources)
                        #TODO: add event sources in AlertManagement
                        new_alert.save()

                        event_sources_str =''
                        event_sources_sms =''
                        for event_source in event_sources:
                            event_sources_str = event_sources_str+ '-'+ str(event_source)+'\n'
                            event_sources_sms = event_sources_sms+ str(event_source)+', '

                        sms_message = str(event_name) + ' event occurred at ' + str(plant_location) +' for:\n'+str(event_sources_sms)
                        #event_sources_str = ", ".join(event_sources)
                        try:
                            if email!='':
                                send_mail(EMAIL_TITLE + str(event_name) + ' at ' + str(plant_location),
                                    str(event_name) + ' event occurred at ' + str(plant_location) +' for:\n'+str(event_sources_str) + SIGNOFF_STRING,
                                    FROM_EMAIL,
                                    [email], fail_silently=False)
                        except:
                            print("Error in sending email")
                        try:
                            if phone!='':
                                #send_twilio_message(phone, sms_message)
                                send_solutions_infini_sms(phone,sms_message)
                        except Exception as exception:
                            print("Error in sending sms" + str(exception))
                        '''
                        #send a mail with event specific template.

                        message = get_template('core/organization_invitation_email.html').render(Context(ctx))
                        msg = EmailMessage(INVITATION_EMAIL_SUBJECT , message, to=[form.cleaned_data['email']], from_email='alerts@dataglen.com')
                        msg.content_subtype = 'html'
                        msg.send()
                        '''

                    except Exception as exception:
                        print("Error in saving new alerts" + str(exception))
                else:
                    print("hello")
            else:
                print("inside else")
                try:
                    new_alert = AlertManagement(identifier=identifier,
                                                alert_time=request_arrival_time,
                                                event_time=event_time,
                                                event=event,
                                                email_id=email,
                                                phone_no=phone)
                    new_alert.save()
                    event_sources_str =''
                    event_sources_sms =''
                    for event_source in event_sources:
                        event_sources_str = event_sources_str+ '-'+ str(event_source)+'\n'
                        event_sources_sms = event_sources_sms+ str(event_source)+', '

                    sms_message = str(event_name) + ' event occurred at ' + str(plant_location) +' for:\n'+str(event_sources_sms)
                    try:
                        if email!='':
                            send_mail(EMAIL_TITLE + str(event_name) + ' at ' + str(plant_location),
                                str(event_name) + ' event occurred at ' + str(identifier) +' for:\n'+str(event_sources_str)+ SIGNOFF_STRING,
                                FROM_EMAIL,
                                [email], fail_silently=False)
                    except:
                        print("Error in sending email")

                    try:
                        if phone!='':
                            #send_twilio_message(phone, sms_message)
                            send_solutions_infini_sms(phone,sms_message)
                    except Exception as exception:
                        print("Error in sending sms" + str(exception))
                except Exception as exception:
                    print(str(exception))
    except Exception as exception:
        print(str(exception))


def check_network_for_virtual_gateways(plant):
    try:
        network_up = False
        inverters = plant.independent_inverter_units.all().filter(isMonitored=True)
        ajbs = plant.ajb_units.all().filter(isMonitored=True)
        plant_meta = plant.metadata.plantmetasource
        energy_meters = plant.energy_meters.all().filter(isMonitored=True)
        transformers = plant.transformers.all().filter(isMonitored=True)
        plant_meta_data = SourceMonitoring.objects.filter(source_key=plant_meta.sourceKey)
        if plant_meta.isMonitored and len(plant_meta_data)>0:
            network_up = True
            return network_up
        for meter in energy_meters:
            meter_data = SourceMonitoring.objects.filter(source_key=meter.sourceKey)
            if len(meter_data)>0:
                network_up = True
            return network_up
        for transformer in transformers:
            transformer_data = SourceMonitoring.objects.filter(source_key=transformer.sourceKey)
            if len(transformer_data)>0:
                network_up = True
            return network_up
        for inverter in inverters:
            inverter_data = SourceMonitoring.objects.filter(source_key=inverter.sourceKey)
            if len(inverter_data)>0:
                network_up = True
            return network_up
        for ajb in ajbs:
            ajb_data = SourceMonitoring.objects.filter(source_key=ajb.sourceKey)
            if len(ajb_data)>0:
                network_up = True
            return network_up
        return network_up
    except Exception as exception:
        print(str(exception))


def solar_events_check():
    print("Events cron job started: ",str(datetime.datetime.now()))

    try:
        # get the solar plants
        try:
            plants = SolarPlant.objects.all()
        except ObjectDoesNotExist:
            print("No solar plant found.")
        current_time = timezone.now()
        # iterate for all the plants
        for plant in plants:
            print("For plant: ", plant.slug)
            if plant.isOperational:
                # Get the inverters associated with the plants for which events should be logged
                inverters = IndependentInverter.objects.filter(plant=plant)
                ajbs = AJB.objects.filter(plant=plant)

                #Get the gateway sources
                try:
                    gateway_sources = GatewaySource.objects.filter(plant=plant)
                    isNetworkDown = False
                    for gateway in gateway_sources:
                        '''
                        #Get the plant meta source
                        try:
                            plant_meta_source = PlantMetaSource.objects.get(plant=plant)
                        except ObjectDoesNotExist:
                            print("No plant meta source found for the plant: " + plant.slug)
                        '''

                        # Get the current time in gateway timezone
                        try:
                            tz = pytz.timezone(gateway.dataTimezone)
                            print("plant operational, tz" , tz)
                        except:
                            print("error in converting current time to source timezone")
                        try:
                            current_time = timezone.now()
                            # astimezone does the conversion and updates the tzinfo part
                            current_time = current_time.astimezone(pytz.timezone(gateway.dataTimezone))
                        except Exception as exc:
                            current_time = timezone.now()

                        # Check if the heartbeat is received from the gateway sources
                        if gateway.isMonitored:
                            # If the gateway is not virtual
                            if not gateway.isVirtual:
                                gateway_data = SourceMonitoring.objects.filter(source_key=gateway.sourceKey)
                                print("gateway data len: " + str(len(gateway_data)))
                                if (len(gateway_data)>0):
                                    # Network is up
                                    # Check for the last entry made in the EventsByTime table
                                    events_entry = EventsByTime.objects.filter(identifier=gateway.sourceKey).limit(1)

                                    if (len(events_entry) > 0):
                                        #if the last entry was for NETWORK_UP
                                        if (str(events_entry[0].event_name) == 'NETWORK_UP'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for NETWORK_UP
                                            events_write(current_time.replace(second=0, microsecond=0),current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_UP", "-1")
                                            print("NETWORK_UP" + " event logged for: " + str(gateway.sourceKey))
                                            #TODO: close the ticket for network down for this plant
                                else:
                                    #Network is down
                                    #Log an event for NETWORK_DOWN if the last event logged for this source was NETWORK_UP
                                    #In this case no need to check for INVERTER_CONNECTED, INVERTER_DISCONNECTED events
                                    events_entry = EventsByTime.objects.filter(identifier=gateway.sourceKey).limit(1)
                                    if (len(events_entry) > 0):
                                        #if the last entry was for NETWORK_DOWN
                                        if (str(events_entry[0].event_name) == 'NETWORK_DOWN'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for NETWORK_DOWN
                                            events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_DOWN", "-1")
                                            print("NETWORK_DOWN" + " event logged for: " + str(gateway.sourceKey))
                                            #TODO: create a ticket for network down for this plant

                                    else:
                                        # Log an event for NETWORK_DOWN
                                        events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_DOWN", "-1")
                                        print("NETWORK_DOWN" + " event logged for: " + str(gateway.sourceKey))
                                    isNetworkDown = True
                            else:
                                gateway_data = check_network_for_virtual_gateways(plant)
                                print("network status of plant : " + str(plant.slug) + str(gateway_data))
                                if gateway_data:
                                    # Network is up
                                    # Check for the last entry made in the EventsByTime table
                                    events_entry = EventsByTime.objects.filter(identifier=gateway.sourceKey).limit(1)

                                    if (len(events_entry) > 0):
                                        #if the last entry was for NETWORK_UP
                                        if (str(events_entry[0].event_name) == 'NETWORK_UP'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for NETWORK_UP
                                            events_write(current_time.replace(second=0, microsecond=0),current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_UP", "-1")
                                            print("NETWORK_UP" + " event logged for: " + str(gateway.sourceKey))
                                            #TODO: close the ticket for network down for this plant
                                else:
                                    #Network is down
                                    #Log an event for NETWORK_DOWN if the last event logged for this source was NETWORK_UP
                                    #In this case no need to check for INVERTER_CONNECTED, INVERTER_DISCONNECTED events
                                    events_entry = EventsByTime.objects.filter(identifier=gateway.sourceKey).limit(1)
                                    if (len(events_entry) > 0):
                                        #if the last entry was for NETWORK_DOWN
                                        if (str(events_entry[0].event_name) == 'NETWORK_DOWN'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for NETWORK_DOWN
                                            events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_DOWN", "-1")
                                            print("NETWORK_DOWN" + " event logged for: " + str(gateway.sourceKey))
                                            #TODO: create a ticket for network down for this plant

                                    else:
                                        # Log an event for NETWORK_DOWN
                                        events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_DOWN", "-1")
                                        print("NETWORK_DOWN" + " event logged for: " + str(gateway.sourceKey))
                                    isNetworkDown = True
                except ObjectDoesNotExist:
                        print("No gateway source found for the plant: " + plant.slug)

                iInverterDown = 0
                if not isNetworkDown:
                        # Check for INVERTER_CONNECTED, INVERTER_DISCONNECTED events
                        for inverter in inverters:
                            if inverter.isMonitored:
                                # Get the current time in inverter timezone
                                try:
                                    tz = pytz.timezone(inverter.dataTimezone)
                                    #print("tz" , tz)
                                except:
                                    print("error in converting current time to source timezone")
                                try:
                                    current_time = timezone.now()
                                    # astimezone does the conversion and updates the tzinfo part
                                    current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))
                                except Exception as exc:
                                    current_time = timezone.now()

                                # Check if the data is present for the inverter in last 10 minutes
                                inverter_data = SourceMonitoring.objects.filter(source_key=inverter.sourceKey)
                                if (len(inverter_data)>0):
                                    # Inverter is up

                                    # Check for the last entry made in the EventsByTime table for inverter
                                    inverter_events_entry = EventsByTime.objects.filter(identifier=inverter.sourceKey).limit(1)

                                    if (len(inverter_events_entry) > 0):
                                        #if the last entry was for INVERTER_CONNECTED
                                        isInverterUp = True
                                        if str(inverter_events_entry[0].event_name) == 'INVERTER_CONNECTED' or str(inverter_events_entry[0].event_name) == 'INVERTER_ERROR':
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for INVERTER_CONNECTED
                                            events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0),inverter.sourceKey, "INVERTER_CONNECTED", "-1")
                                            print("INVERTER_CONNECTED" + " event logged for: " + str(inverter.sourceKey))
                                            # TODO: close the ticket that was created for inverter disconnected for this inverter
                                    else:
                                         # Log an event for INVERTER_CONNECTED
                                        events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), inverter.sourceKey, "INVERTER_CONNECTED", "-1")
                                        print("INVERTER_CONNECTED" + " event logged for: " + str(inverter.sourceKey))
                                # Log an event for INVERTER_DISCONNECTED if the last event logged for inverter was INVERTER_CONNECTED
                                else:
                                    # Check for the last entry made in the EventsByTime table for inverter
                                    inverter_events_entry = EventsByTime.objects.filter(identifier=inverter.sourceKey).limit(1)

                                    if (len(inverter_events_entry) > 0):
                                        #if the last entry was for INVERTER_DISCONNECTED
                                        if (str(inverter_events_entry[0].event_name) == 'INVERTER_DISCONNECTED'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for INVERTER_DISCONNECTED
                                            events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), inverter.sourceKey, "INVERTER_DISCONNECTED", "-1")
                                            print("INVERTER_DISCONNECTED" + " event logged for: " + str(inverter.sourceKey))
                                            # TODO: create a ticket for inverter disconnected for this inverter

                                    else:
                                        # Log an event for INVERTER_DISCONNECTED
                                        events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), inverter.sourceKey, "INVERTER_DISCONNECTED", "-1")
                                        print("INVERTER_DISCONNECTED" + " event logged for: " + str(inverter.sourceKey))
                                    iInverterDown+=1
                        # Check for AJB_CONNECTED, AJB_DISCONNECTED events
                        for ajb in ajbs:
                            if ajb.isMonitored:
                                # Get the current time in ajb timezone
                                try:
                                    tz = pytz.timezone(ajb.dataTimezone)
                                except:
                                    print("error in converting current time to source timezone")
                                try:
                                    current_time = timezone.now()
                                    current_time = current_time.astimezone(pytz.timezone(ajb.dataTimezone))
                                except Exception as exc:
                                    current_time = timezone.now()

                                # Check if the data is present for the ajb since time out interval
                                ajb_data = SourceMonitoring.objects.filter(source_key=ajb.sourceKey)
                                if (len(ajb_data)>0):
                                    # AJB is up
                                    # Check for the last entry made in the EventsByTime table for ajb
                                    ajb_events_entry = EventsByTime.objects.filter(identifier=ajb.sourceKey).limit(1)

                                    if (len(ajb_events_entry) > 0):
                                        #if the last entry was for AJB_CONNECTED
                                        if (str(ajb_events_entry[0].event_name) == 'AJB_CONNECTED'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for AJB_CONNECTED
                                            events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0),ajb.sourceKey, "AJB_CONNECTED", "-1")
                                            print("AJB_CONNECTED" + " event logged for: " + str(ajb.sourceKey))
                                    else:
                                         # Log an event for AJB_CONNECTED
                                        events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), ajb.sourceKey, "AJB_CONNECTED", "-1")
                                        print("AJB_CONNECTED" + " event logged for: " + str(ajb.sourceKey))
                                # Log an event for AJB_DISCONNECTED if the last event logged for ajb was AJB_CONNECTED
                                else:
                                    # Check for the last entry made in the EventsByTime table for inverter
                                    ajb_events_entry = EventsByTime.objects.filter(identifier=ajb.sourceKey).limit(1)

                                    if (len(ajb_events_entry) > 0):
                                        #if the last entry was for AJB_DISCONNECTED
                                        if (str(ajb_events_entry[0].event_name) == 'AJB_DISCONNECTED'):
                                            # No need to log an event
                                            pass
                                        else:
                                            # Log an event for AJB_DISCONNECTED
                                            events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), ajb.sourceKey, "AJB_DISCONNECTED", "-1")
                                            print("AJB_DISCONNECTED" + " event logged for: " + str(ajb.sourceKey))
                                    else:
                                        # Log an event for AJB_DISCONNECTED
                                        events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), ajb.sourceKey, "AJB_DISCONNECTED", "-1")
                                        print("AJB_DISCONNECTED" + " event logged for: " + str(ajb.sourceKey))

                        '''
                        if not isNetworkDown and iInverterDown!=0 and iInverterDown == len(inverters):
                            isNetworkDown = True
        '''
                check_inverter_errors(current_time,plant)
        events_read()
        send_report(current_time,"DAILY_REPORT")
        print("Cron job completed!")

    except Exception as exception:
        print(str(exception))


def solar_activate_monitoring():
    print("Activate monitoring cron job started", str(datetime.datetime.now()))
    current_time = timezone.now()
    try:
        plants = SolarPlant.objects.all()
    except ObjectDoesNotExist:
        print("No solar plant found.")
        # iterate for all the plants
    for plant in plants:
            print("For plant: ", plant.slug)
            if plant.isOperational:
                #Get plant meta source
                try:
                    plant_meta_sources = PlantMetaSource.objects.filter(plant=plant)
                    if len(plant_meta_sources)>0:
                        plant_meta_source = plant_meta_sources[0]
                        plant_operations_start_time_str = plant_meta_source.operations_start_time
                        plant_operations_end_time_str = plant_meta_source.operations_end_time
                        #GET timezon info from plant_meta_source
                        try:
                            plant_time_zone = plant_meta_source.dataTimezone

                        except:
                            print("error in converting current time to source timezone")
                    else:
                        plant_operations_start_time_str = PLANT_DEFAULT_START_TIME
                        plant_operations_end_time_str = PLANT_DEFAULT_END_TIME
                        plant_time_zone = PLANT_DEFAULT_TIMEZONE
                except ObjectDoesNotExist:
                    print("No Plant meta source found for plant" + str(plant))
                    plant_operations_start_time_str = PLANT_DEFAULT_START_TIME
                    plant_operations_end_time_str = PLANT_DEFAULT_END_TIME
                    plant_time_zone = PLANT_DEFAULT_TIMEZONE

                print("plant_operations_start_time_str", plant_operations_start_time_str)
                print("plant_operations_end_time_str" , plant_operations_end_time_str)
                print("plant_time_zone" , plant_time_zone)

                try:
                    # astimezone does the conversion and updates the tzinfo part
                        current_time = current_time.astimezone(pytz.timezone(plant_time_zone))
                except Exception as exc:
                        current_time = timezone.now()

                plant_operations_start_time = current_time
                plant_operations_end_time = current_time
                start_time = datetime.datetime.strptime(plant_operations_start_time_str,"%H:%M:%S")
                end_time =  datetime.datetime.strptime(plant_operations_end_time_str,"%H:%M:%S")

                plant_operations_start_time = plant_operations_start_time.replace(hour=start_time.hour, minute=start_time.minute)
                plant_operations_end_time = plant_operations_end_time.replace(hour=end_time.hour, minute=end_time.minute)
                print("plant_operations_start_time",plant_operations_start_time)
                print("plant_operations_end_time",plant_operations_end_time)

                isMonitored = True
                if current_time >= plant_operations_end_time:
                    isMonitored = False
                elif current_time >= plant_operations_start_time and current_time < plant_operations_end_time:
                    isMonitored = True
                else:
                    isMonitored = False

                print("isMonitoring for all the sources would be turned: ", isMonitored )

                # Get the inverters associated with the plants for which events should be logged
                try:
                    IndependentInverter.objects.filter(plant=plant).update(isMonitored = isMonitored)
                except:
                    print("Error while retrieving inverters for the plant: "+ str(plant))

                # Get the ajbs associated with the plant
                try:
                    AJB.objects.filter(plant=plant).update(isMonitored = isMonitored)
                except:
                    print("Error while retrieving ajbs for the plant: " + str(plant))

                #Get plant meta source for this plant
                PlantMetaSource.objects.filter(plant=plant).update(isMonitored = isMonitored)

                #Get gateway object for this plant
                try:
                   GatewaySource.objects.filter(plant=plant).update(isMonitored=isMonitored)
                except ObjectDoesNotExist:
                    print("No gateway source found for plant" + str(plant))

                # Get the energy meters of the plant
                try:
                    EnergyMeter.objects.filter(plant=plant).update(isMonitored = isMonitored)
                except:
                    print("Error while retrieving energy meters of the plant: "+ str(plant))

                # Get the transformers of the plant
                try:
                    Transformer.objects.filter(plant=plant).update(isMonitored = isMonitored)
                except:
                    print("Error while retrieving transformers of the plant: "+ str(plant))

    print("Completed cron job!" )

def sendInverterErrorAlertsWithoutCheck(event_type, identifier,
                                        request_arrival_time,
                                        event_name):
    try:
        FROM_EMAIL = FROM_ERROR_EMAIL
        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=identifier,
                                                                  event=event,
                                                                  alert_active=True)

        try:
            plant = SolarPlant.objects.get(slug=identifier)
        except Exception as exception:
            print("No plant found")
        inverters = IndependentInverter.objects.filter(plant=plant)
        inverter_errors = []
        for inverter in inverters:
            inverter_error = []
            inverter_error_values = EventsByError.objects.filter(identifier=inverter.sourceKey,
                                                                 event_name="INVERTER_ERROR",
                                                                 insertion_time__gt=request_arrival_time)
            for value in range(len(inverter_error_values)):
                inverter_error.append(inverter_error_values[value])
            if len(inverter_error) > 0:
                inverter_errors.append(inverter_error)
        print(inverter_errors)
        if len(inverter_errors) > 0:
            for alert in active_alerts:
                print("inside for")
                email = alert.email_id
                phone = alert.phone_no
                plants = SolarPlant.objects.filter(slug=identifier)
                if len(plants)>0:
                    plant_location = plants[0].location
                try:
                    new_alert = AlertManagement(identifier=identifier,
                                                alert_time=request_arrival_time,
                                                event_time=request_arrival_time,
                                                event=event,
                                                email_id=email,
                                                phone_no=phone)

                    new_alert.save()
                except Exception as exception:
                    print("Error in saving alert: " + str(exception))
                #html_content = 'Hi,<br> Following errors have occurred for inverters at ' + str(plant.location) + ':<br><br>'
                html_content = ""
                sms_message = 'INVERTER_ERROR event occurred at ' + str(plant.location) + ' for:\n'
                for value in inverter_errors:
                    inverter_error_values_table = []
                    for x in range(len(value)):
                        print(value[x].event_code)
                        try:
                            inverter = IndependentInverter.objects.get(sourceKey=value[x].identifier)
                            inverter_error = InverterErrorCodes.objects.get(manufacturer=inverter.manufacturer,
                                                                            model=inverter.model,
                                                                            error_code=value[x].event_code)
                            try:
                                tz = pytz.timezone(inverter.dataTimezone)
                                #print("tz" , tz)
                            except:
                                print("error in converting time to inverter timezone")
                            inverter_error_value = []
                            event_time = value[x].event_time
                            #print(event_time)
                            event_time = update_tz(event_time, inverter.dataTimezone)
                            event_time = event_time.replace(tzinfo=pytz.utc).astimezone(tz)
                            # print(event_time)
                            # event_time = tz.localize(value[x].event_time)
                            # print(event_time)
                            # event_time = event_time.astimezone(pytz.timezone(inverter.dataTimezone))
                            print(event_time)
                            inverter_error_value.append(str(event_time).split('.')[0])
                            inverter_error_value.append(str(inverter_error.error_code))
                            inverter_error_value.append(str(inverter_error.error_description))
                            inverter_error_value.append(str(inverter_error.default_severity))
                            inverter_error_value.append(str(inverter_error.notes))
                            inverter_error_values_table.append(inverter_error_value)
                            sms_message = sms_message + str(inverter.name) + ": " + str(inverter_error.error_description) + ', '
                        except Exception as exception:
                            print("Error in getting values from InverterErrorCodes table: " + str(exception))
                    inverter_error_values_table = tabulate(inverter_error_values_table, headers=['Timestamp','Error Code', 'Error Description', 'Severity', 'Notes'], tablefmt='html')
                    html_content = html_content + '<b><u>'+str(inverter.name) + '</b></u>:<br>' +  inverter_error_values_table + '<br>'
                #html_content = html_content + '<br><br> Thank You, <br> Team DataGlen'

                try:
                    if email!='':
                        # subject, from_email, to = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant_location) , FROM_EMAIL, email
                        # text_content = ''
                        # html_content = html_content
                        # msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                        # msg.attach_alternative(html_content, "text/html")
                        # msg.send()
                        send_inverter_error_alert(plant, 'ERROR', 'INVERTER_ERROR', html_content, email)
                except Exception as exception:
                    print("Error in sending email" + str(exception))
                try:
                    if phone!='':
                        send_solutions_infini_sms(phone,sms_message)
                except Exception as exception:
                    print("Error in sending sms" + str(exception))
    except Exception as exception:
        print(str(exception))


def check_inverter_errors(request_arrival_time,plant):
    # get all the inverters of plant
    print("Inverter Errors check started! for plant: " + str(plant.name))
    try:
        inverters = IndependentInverter.objects.filter(plant=plant)
    except Exception as exception:
        print("Error in getting the inverters of the plant: " + str(exception))
    current_time = request_arrival_time
    try:
        for inverter in inverters:
            try:
                tz = pytz.timezone(inverter.dataTimezone)
                #print("tz" , tz)
            except:
                print("error in converting time to inverter timezone")
            #current_time = tz.localize(current_time)
            current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))
            initial_time = current_time - datetime.timedelta(minutes=EVENTS_UPDATE_INTERVAL_MINUTES)
            # get the errors occurred in the last five minutes for the inverter
            try:
                inverter_errors = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name='ERROR_CODE',
                                                                      timestamp_in_data__gt=initial_time,
                                                                      timestamp_in_data__lte=current_time).values_list('stream_value','timestamp_in_data')
                if len(inverter_errors) > 0:
                    values = [item[0] for item in inverter_errors]
                    timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in inverter_errors]
                    for value in range(len(values)):
                        try:
                            event_time = tz.localize(datetime.datetime.strptime(timestamps[value],'%Y-%m-%dT%H:%M:%S' + '+05:30'))
                        except Exception as exception:
                            event_time = tz.localize(datetime.datetime.strptime(timestamps[value],'%Y-%m-%dT%H:%M:%S.%f' + '+05:30'))
                            pass
                        event_time = event_time.astimezone(pytz.timezone(inverter.dataTimezone))
                        events_write(request_arrival_time = current_time.replace(second=0, microsecond=0), event_time=event_time, identifier=inverter.sourceKey, event_name="INVERTER_ERROR", event_code=values[value])
            except Exception as exception:
                print("Error in fetching the errors for the inverter: " + str(inverter.name) + str(exception))
        create_inverter_error_ticket(plant=plant, initial_time=initial_time)
        sendInverterErrorAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,request_arrival_time=initial_time,event_name="INVERTER_ERROR")
    except Exception as exception:
        print(str(exception))



def send_detailed_report(plant,email):
    try:
        value = None
        plant_meta_source = plant.metadata.plantmetasource
        values = PlantCompleteValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                    count_time_period=86400,
                                                    identifier=plant_meta_source.sourceKey).limit(1)
        if len(values)>0:
            value = values[0]

        # get today's ticket details
        try:
            date = timezone.now()
            tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            if date.tzinfo is None:
                date = tz.localize(date)
            date = date.replace(hour=0, minute=0,second=0, microsecond=0)
        except Exception as exception:
            print("Error in getting todays date : " + str(exception))

        t_stats = get_plant_tickets_date(plant, date, date+datetime.timedelta(hours=24))
        if t_stats != -1:
            unacknowledged_tickets = len(t_stats['open_unassigned_tickets'])
            open_tickets = len(t_stats['open_assigned_tickets'])
            closed_tickets = len(t_stats['tickets_closed_resolved'])

        else:
            unacknowledged_tickets = 0
            open_tickets = 0
            closed_tickets = 0

        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = (  "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.0 Transitional//EN' 'http://www.w3.org/TR/REC-html40/loose.dtd'>"
                        "<html xmlns='http://www.w3.org/1999/xhtml'>"
                        "<head>"
                        "<meta name='viewport' content='width=device-width'>"
                        "<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>"
                        "<title>Actionable emails e.g. reset password</title>"
                        "<style>"
                         "{"
                              "margin: 0;"
                              "font-family: Verdana, Geneva, sans-serif;"
                              "box-sizing: border-box;"
                              "font-size: 14px;"
                            "}"
                            "img {"
                              "max-width: 100%;"
                            "}"
                            "body {"
                              "-webkit-font-smoothing: antialiased;"
                              "-webkit-text-size-adjust: none;"
                              "width: 100% !important;"
                              "height: 100%;"
                              "line-height: 1.6em;"
                                "}"
                                "table td {"
                                  "vertical-align: top;"
                                "}"
                                "body {"
                                  "background-color: #ecf0f5;"
                                  "color: #6c7b88"
                                "}"
                                ".body-wrap {"
                                  "background-color: #ecf0f5;"
                                  "width: 100%;"
                                "}"
                                ".container {"
                                  "display: block !important;"
                                  "max-width: 600px !important;"
                                  "margin: 0 auto !important;"
                                  "/* makes it centered */"
                                  "clear: both !important;"
                                "}"
                                ".content {"
                                  "max-width: 600px;"
                                  "margin: 0 auto;"
                                  "display: block;"
                                  "padding: 20px;"
                                "}"
                                ".main {"
                                  "background-color: #fff;"
                                  "border-bottom: 2px solid #d7d7d7;"
                                "}"
                                ".content-wrap {"
                                  "padding: 20px;"
                                "}"
                                ".content-block {"
                                  "padding: 0 0 20px;"
                                "}"
                                ".header {"
                                  "width: 100%;"
                                  "margin-bottom: 20px;"
                                "}"
                                ".footer {"
                                  "width: 100%;"
                                  "clear: both;"
                                  "color: #999;"
                                  "padding: 20px;"
                                "}"
                                ".footer p, .footer a, .footer td {"
                                  "color: #999;"
                                  "font-size: 12px;"
                                "}"
                                "h1, h2, h3 {"
                                  "font-family: Verdana, Geneva, sans-serif;"
                                  "color: #1a2c3f;"
                                  "margin: 30px 0 0;"
                                  "line-height: 1.2em;"
                                  "font-weight: 400;"
                                "}"
                                "h1 {"
                                  "font-size: 32px;"
                                  "font-weight: 500;"
                                "}"
                                "h2 {"
                                  "font-size: 24px;"
                                "}"
                                "h3 {"
                                  "font-size: 18px;"
                                "}"
                                "h4 {"
                                  "font-size: 14px;"
                                  "font-weight: 600;"
                                "}"

                                "p, ul, ol {"
                                  "margin-bottom: 10px;"
                                  "font-weight: normal;"
                                "}"
                                "p li, ul li, ol li {"
                                  "margin-left: 5px;"
                                  "list-style-position: inside;"
                                "}"
                                "a {"
                                  "color: #348eda;"
                                  "text-decoration: underline;"
                                "}"
                                ".btn-primary {"
                                  "text-decoration: none;"
                                  "color: #FFF;"
                                  "background-color: #42A5F5;"
                                  "border: solid #42A5F5;"
                                  "border-width: 10px 20px;"
                                  "line-height: 2em;"
                                  "font-weight: bold;"
                                  "text-align: center;"
                                  "cursor: pointer;"
                                  "display: inline-block;"
                                  "text-transform: capitalize;"
                                "}"
                                ".last {"
                                  "margin-bottom: 0;"
                                "}"
                                ".first {"
                                  "margin-top: 0;"
                                "}"
                                ".aligncenter {"
                                  "text-align: center;"
                                "}"
                                ".alignright {"
                                  "text-align: right;"
                                "}"
                                ".alignleft {"
                                  "text-align: left;"
                                "}"
                                ".clear {"
                                  "clear: both;"
                                "}"
                                ".alert {"
                                  "font-size: 16px;"
                                  "color: #fff;"
                                  "font-weight: 500;"
                                  "padding: 20px;"
                                  "text-align: center;"
                                "}"
                                ".alert a {"
                                  "color: #fff;"
                                  "text-decoration: none;"
                                  "font-weight: 500;"
                                  "font-size: 16px;"
                                "}"
                                ".alert.alert-warning {"
                                  "background-color: #FFA726;"
                                "}"
                                ".alert.alert-bad {"
                                  "background-color: #ef5350;"
                                "}"
                                ".alert.alert-good {"
                                  "background-color: #8BC34A;"
                                "}"
                                ".invoice {"
                                  "margin: 25px auto;"
                                  "text-align: left;"
                                  "width: 100%;"
                                "}"
                                ".invoice td {"
                                  "padding: 5px 0;"
                                "}"
                                ".invoice .invoice-items {"
                                  "width: 100%;"
                                "}"
                                ".invoice .invoice-items td {"
                                  "border-top: #eee 1px solid;"
                                "}"
                                ".invoice .invoice-items .total td {"
                                  "border-top: 2px solid #6c7b88;"
                                  "font-size: 18px;"
                                "}"
                                "@media only screen and (max-width: 640px) {"
                                  "body {"
                                    "padding: 0 !important;"
                                  "}"
                                  "h1, h2, h3, h4 {"
                                    "font-weight: 800 !important;"
                                    "margin: 20px 0 5px !important;"
                                  "}"
                                  "h1 {"
                                    "font-size: 22px !important;"
                                  "}"
                                  "h2 {"
                                    "font-size: 18px !important;"
                                  "}"
                                  "h3 {"
                                    "font-size: 16px !important;"
                                  "}"
                                  ".container {"
                                    "padding: 0 !important;"
                                    "width: 100% !important;"
                                  "}"
                                  ".content {"
                                    "padding: 0 !important;"
                                  "}"
                                  ".content-wrap {"
                                    "padding: 10px !important;"
                                  "}"
                                  ".invoice {"
                                    "width: 100% !important;"
                                  "}"
                                "}"
                        "</style>"
                        "</head>"
                        "<body itemscope itemtype='http://schema.org/EmailMessage' style='-webkit-font-smoothing: antialiased; -webkit-text-size-adjust: none; width: 100% !important; height: 100%; line-height: 1.6em; color: #6c7b88; background-color: #ecf0f5; padding: 0;' bgcolor='#ecf0f5'>"
                        "<table class='body-wrap' style='background-color: #ecf0f5; width: 100%;' bgcolor='#ecf0f5'>"
                            "<tr>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                                "<td class='container' width='600' style='vertical-align: top; display: block !important; max-width: 600px !important; clear: both !important; width: 100% !important; margin: 0 auto; padding: 0;' valign='top'>"
                                    "<div class='content' style='max-width: 600px; display: block; margin: 0 auto; padding: 0;'>"
                                        "<table class='main' width='100%' cellpadding='0' cellspacing='0' itemprop='action' itemscope itemtype='http://schema.org/ConfirmAction' style='background-color: #fff; border-bottom-color: #d7d7d7; border-bottom-width: 2px; border-bottom-style: solid;' bgcolor='#fff'>"
                                            "<tr>"
                                                "<td class='content-wrap' style='vertical-align: top; padding: 10px;' valign='top'>"
                                                    "<meta itemprop='name' content='Confirm Email'>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0' bgcolor='#BDE5F8'>"
                                                        "<tr>"
                                                            "<tb>"
                                                                "<td style='vertical-align: top;' valign='top'>") + dataglen_logo_html + \
                                                                ("</td>"
                                                                "<td style='vertical-align: top;' valign='top'>") + client_logo_html + \
                                                            ("</td>"
                                                            "</tb>"
                                                        "</tr>"
                                                    "</table>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0'>"
                                                        "<tr>"
                                                            "<td class='content-block' style='vertical-align: top; padding: 0 0 20px;' valign='top'>"
                                                                "<h2 style='font-family: Verdana, Geneva, sans-serif; color: #1a2c3f; line-height: 1.2em; font-weight: 800 !important; font-size: 16px !important; margin: 20px 0 5px; text-align: center;'>Today's Performance Report</h2>"
                                                            "</td>"
                                                        "</tr>"
                                                    "</table>"
                                                        "<table width='100%' cellpadding='2' cellspacing='2' bgcolor='#C0C0C0' padding-right='1' padding-left='1'>"
                                                            "<tb>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Total Generation"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(fix_generation_units(float(value.plant_generation_today))) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "PR"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + (str("{0:.2f}".format(value.pr*100)) + " %" if value else "0 %") + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "CUF"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + (str("{0:.2f}".format(value.cuf*100)) + " %" if value else "0 %") + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Open Tickets"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(open_tickets) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Closed Tickets"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(closed_tickets) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Unacknowledged Tickets"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(unacknowledged_tickets) + \
                                                                ("</td>"
                                                                "</tr>"
                                                            "</tb>"
                                                        "</table>"
                                                "</td>"
                                            "</tr>"
                                        "</table>"
                                        "<div class='footer' style='width: 100%; clear: both; color: #999; padding: 20px;'>"
                                            "<table width='100%'>"
                                                "<tr>"
                                                    "<td class='aligncenter content-block' style='vertical-align: top; color: #999; font-size: 12px; text-align: center; padding: 0 0 20px;' align='center' valign='top'><h3>Follow <a href='https://dataglen.com'>DataGlen</a> on</h3><a href='https://twitter.com/dataglen'>Twitter</a> <a href='https://www.linkedin.com/company/dataglen'>LinkedIn</a> <a href='https://www.facebook.com/dataglen/'>Facebook</a></td>"
                                                "</tr>"
                                            "</table>"
                                        "</div>"
                                    "</div>"
                                "</td>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                            "</tr>"
                        "</table>"
                        "</body>"
                        "</html>")

        report_account_email = 'alerts@dataglen.com'
        from_email = 'reports@dataglen.com'
        recipient = email
        subject = ' [INFO] Daily Performance Report for plant at ' + str(plant.location)

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))
        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()

    except Exception as exception:
        print("Error in sending daily report: " + str(exception))


def send_detailed_report_with_attachment(plant,recepient_email):
    try:
        value = None
        plant_meta_source = plant.metadata.plantmetasource
        values = PlantCompleteValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                    count_time_period=86400,
                                                    identifier=plant_meta_source.sourceKey).limit(1)
        if len(values)>0:
            value = values[0]

        # get today's ticket details
        try:
            date = timezone.now()
            tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            if date.tzinfo is None:
                date = tz.localize(date)
            date = date.replace(hour=0, minute=0,second=0, microsecond=0)
        except Exception as exception:
            print("Error in getting todays date : " + str(exception))

        t_stats = get_plant_tickets_date(plant, date, date+datetime.timedelta(hours=24))
        if t_stats != -1:
            unacknowledged_tickets = len(t_stats['open_unassigned_tickets'])
            open_tickets = len(t_stats['open_assigned_tickets'])
            closed_tickets = len(t_stats['tickets_closed_resolved'])

        else:
            unacknowledged_tickets = 0
            open_tickets = 0
            closed_tickets = 0

        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = "<!doctype html><html> <head> <meta name='viewport' content='width=device-width' /> <meta http-equiv='Content-Type' content='text/html; charset=UTF-8' /> <title>DataGlen Generation Report</title> <style> /* ------------------------------------- GLOBAL RESETS ------------------------------------- */ img { border: none; -ms-interpolation-mode: bicubic; max-width: 100%; } body { background-color: #f6f6f6; font-family: sans-serif; -webkit-font-smoothing: antialiased; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; } table { border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; } table td { font-family: sans-serif; font-size: 14px; vertical-align: top; } /* ------------------------------------- BODY & CONTAINER ------------------------------------- */ .body { background-color: #f6f6f6; width: 100%; } /* Set a max-width, and make it display as block so it will automatically stretch to that width, but will also shrink down on a phone or something */ .container { display: block; Margin: 0 auto !important; /* makes it centered */ max-width: 580px; padding: 10px; width: 580px; } /* This should also be a block element, so that it will fill 100% of the .container */ .content { box-sizing: border-box; display: block; Margin: 0 auto; max-width: 580px; padding: 10px; } /* ------------------------------------- HEADER, FOOTER, MAIN ------------------------------------- */ .main { background: #fff; border-radius: 3px; width: 100%; } .wrapper { box-sizing: border-box; padding: 20px; } .footer { clear: both; padding-top: 10px; text-align: center; width: 100%; } .footer td, .footer p, .footer span, .footer a { color: #999999; font-size: 12px; text-align: center; } /* ------------------------------------- TYPOGRAPHY ------------------------------------- */ h1, h2, h3, h4 { color: #000000; font-family: sans-serif; font-weight: 400; line-height: 1.4; margin: 0; Margin-bottom: 30px; } h1 { font-size: 35px; font-weight: 300; text-align: center; text-transform: capitalize; } p, ul, ol { font-family: sans-serif; font-size: 14px; font-weight: normal; margin: 0; Margin-bottom: 15px; } p li, ul li, ol li { list-style-position: inside; margin-left: 5px; } a { color: #3498db; text-decoration: underline; } /* ------------------------------------- BUTTONS ------------------------------------- */ .btn { box-sizing: border-box; width: 100%; } .btn > tbody > tr > td { padding-bottom: 15px; } .btn table { width: auto; } .btn table td { background-color: #ffffff; border-radius: 5px; text-align: center; } .btn a { background-color: #ffffff; border: solid 1px #3498db; border-radius: 5px; box-sizing: border-box; color: #3498db; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; margin: 0; padding: 12px 25px; text-decoration: none; text-transform: capitalize; } .btn-primary table td { background-color: #3498db; } .btn-primary a { background-color: #3498db; border-color: #3498db; color: #ffffff; } /* ------------------------------------- OTHER STYLES THAT MIGHT BE USEFUL ------------------------------------- */ .last { margin-bottom: 0; } .first { margin-top: 0; } .align-center { text-align: center; } .align-right { text-align: right; } .align-left { text-align: left; } .clear { clear: both; } .mt0 { margin-top: 0; } .mb0 { margin-bottom: 0; } .preheader { color: transparent; display: none; height: 0; max-height: 0; max-width: 0; opacity: 0; overflow: hidden; mso-hide: all; visibility: hidden; width: 0; } .powered-by a { text-decoration: none; } hr { border: 0; border-bottom: 1px solid #f6f6f6; Margin: 20px 0; } /* ------------------------------------- RESPONSIVE AND MOBILE FRIENDLY STYLES ------------------------------------- */ @media only screen and (max-width: 620px) { table[class=body] h1 { font-size: 28px !important; margin-bottom: 10px !important; } table[class=body] p, table[class=body] ul, table[class=body] ol, table[class=body] td, table[class=body] span, table[class=body] a { font-size: 16px !important; } table[class=body] .wrapper, table[class=body] .article { padding: 10px !important; } table[class=body] .content { padding: 0 !important; } table[class=body] .container { padding: 0 !important; width: 100% !important; } table[class=body] .main { border-left-width: 0 !important; border-radius: 0 !important; border-right-width: 0 !important; } table[class=body] .btn table { width: 100% !important; } table[class=body] .btn a { width: 100% !important; } table[class=body] .img-responsive { height: auto !important; max-width: 100% !important; width: auto !important; }} /* ------------------------------------- PRESERVE THESE STYLES IN THE HEAD ------------------------------------- */ @media all { .ExternalClass { width: 100%; } .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div { line-height: 100%; } .apple-link a { color: inherit !important; font-family: inherit !important; font-size: inherit !important; font-weight: inherit !important; line-height: inherit !important; text-decoration: none !important; } .btn-primary table td:hover { background-color: #34495e !important; } .btn-primary a:hover { background-color: #34495e !important; border-color: #34495e !important; } } </style> </head> <body class=''> <table border='0' cellpadding='0' cellspacing='0' class='body'> <tr> <td>&nbsp;</td> <td class='container'> <div class='content'> <!-- START CENTERED WHITE CONTAINER --> <span class='preheader'>Generation report for the current month.</span> <table class='main'> <tr> " +  client_logo_html + " <!-- put image here --> </tr> <!-- START MAIN CONTENT AREA --> <tr> <td class='wrapper'> <table border='0' cellpadding='0' cellspacing='0'> <tr> <td> <p>Hi there! </p> <p>We have attached generation performance report for your plant " + str(plant.name) + " " + str(plant.location) + " with this email. </p> <p>Please feel free to reach out to us if you have any queries.</p> <p>Thank you!</p> </td> </tr> </table> </td> </tr> <!-- END MAIN CONTENT AREA --> </table> <!-- START FOOTER --> <div class='footer'> <table border='0' cellpadding='0' cellspacing='0'> <tr> <td class='content-block'> <span class='apple-link'>DataGlen Technologies Private Limited, 2017</span> </td> </tr> </table> </div> <!-- END FOOTER --> <!-- END CENTERED WHITE CONTAINER --></div> </td> <td>&nbsp;</td> </tr> </table> </body></html>"

        report_account_email = 'alerts@dataglen.com'
        from_email = 'reports@dataglen.com'
        recipient = recepient_email
        subject = ' [DATAGLEN] Generation Report: ' + str(date.date())

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))

        current_time = timezone.now()
        starttime = current_time.replace(day=1)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        path = '/var/tmp/monthly_report/'
        fp = open(path+file_name , 'rb')
        file1=email.mime.base.MIMEBase('application','vnd.ms-excel')
        file1.set_payload(fp.read())
        fp.close()
        email.encoders.encode_base64(file1)
        file1.add_header('Content-Disposition','attachment;filename=' + file_name)

        msg.attach(file1)

        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()

    except Exception as exception:
        print("Error in sending daily report: " + str(exception))


def send_error_alert(plant,event_type, event_name, event_sources, email):
    try:
        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = (  "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.0 Transitional//EN' 'http://www.w3.org/TR/REC-html40/loose.dtd'>"
                        "<html xmlns='http://www.w3.org/1999/xhtml'>"
                        "<head>"
                        "<meta name='viewport' content='width=device-width'>"
                        "<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>"
                        "<title>Actionable emails e.g. reset password</title>"
                        "<style>"
                         "{"
                              "margin: 0;"
                              "font-family: Verdana, Geneva, sans-serif"
                              "box-sizing: border-box;"
                              "font-size: 14px;"
                            "}"
                            "img {"
                              "max-width: 100%;"
                            "}"
                            "body {"
                              "-webkit-font-smoothing: antialiased;"
                              "-webkit-text-size-adjust: none;"
                              "width: 100% !important;"
                              "height: 100%;"
                              "line-height: 1.6em;"
                                "}"
                                "table td {"
                                  "vertical-align: top;"
                                "}"
                                "body {"
                                  "background-color: #ecf0f5;"
                                  "color: #6c7b88"
                                "}"
                                ".body-wrap {"
                                  "background-color: #ecf0f5;"
                                  "width: 100%;"
                                "}"
                                ".container {"
                                  "display: block !important;"
                                  "max-width: 600px !important;"
                                  "margin: 0 auto !important;"
                                  "/* makes it centered */"
                                  "clear: both !important;"
                                "}"
                                ".content {"
                                  "max-width: 600px;"
                                  "margin: 0 auto;"
                                  "display: block;"
                                  "padding: 20px;"
                                "}"
                                ".main {"
                                  "background-color: #fff;"
                                  "border-bottom: 2px solid #d7d7d7;"
                                "}"
                                ".content-wrap {"
                                  "padding: 20px;"
                                "}"
                                ".content-block {"
                                  "padding: 0 0 20px;"
                                "}"
                                ".header {"
                                  "width: 100%;"
                                  "margin-bottom: 20px;"
                                "}"
                                ".footer {"
                                  "width: 100%;"
                                  "clear: both;"
                                  "color: #999;"
                                  "padding: 20px;"
                                "}"
                                ".footer p, .footer a, .footer td {"
                                  "color: #999;"
                                  "font-size: 12px;"
                                "}"
                                "h1, h2, h3 {"
                                  "font-family: Verdana, Geneva, sans-serif;"
                                  "color: #1a2c3f;"
                                  "margin: 30px 0 0;"
                                  "line-height: 1.2em;"
                                  "font-weight: 400;"
                                "}"
                                "h1 {"
                                  "font-size: 32px;"
                                  "font-weight: 500;"
                                "}"
                                "h2 {"
                                  "font-size: 24px;"
                                "}"
                                "h3 {"
                                  "font-size: 18px;"
                                "}"
                                "h4 {"
                                  "font-size: 14px;"
                                  "font-weight: 600;"
                                "}"

                                "p, ul, ol {"
                                  "margin-bottom: 10px;"
                                  "font-weight: normal;"
                                "}"
                                "p li, ul li, ol li {"
                                  "margin-left: 5px;"
                                  "list-style-position: inside;"
                                "}"
                                "a {"
                                  "color: #348eda;"
                                  "text-decoration: underline;"
                                "}"
                                ".btn-primary {"
                                  "text-decoration: none;"
                                  "color: #FFF;"
                                  "background-color: #42A5F5;"
                                  "border: solid #42A5F5;"
                                  "border-width: 10px 20px;"
                                  "line-height: 2em;"
                                  "font-weight: bold;"
                                  "text-align: center;"
                                  "cursor: pointer;"
                                  "display: inline-block;"
                                  "text-transform: capitalize;"
                                "}"
                                ".last {"
                                  "margin-bottom: 0;"
                                "}"
                                ".first {"
                                  "margin-top: 0;"
                                "}"
                                ".aligncenter {"
                                  "text-align: center;"
                                "}"
                                ".alignright {"
                                  "text-align: right;"
                                "}"
                                ".alignleft {"
                                  "text-align: left;"
                                "}"
                                ".clear {"
                                  "clear: both;"
                                "}"
                                ".alert {"
                                  "font-size: 16px;"
                                  "color: #fff;"
                                  "font-weight: 500;"
                                  "padding: 20px;"
                                  "text-align: center;"
                                "}"
                                ".alert a {"
                                  "color: #fff;"
                                  "text-decoration: none;"
                                  "font-weight: 500;"
                                  "font-size: 16px;"
                                "}"
                                ".alert.alert-warning {"
                                  "background-color: #FFA726;"
                                "}"
                                ".alert.alert-bad {"
                                  "background-color: #ef5350;"
                                "}"
                                ".alert.alert-good {"
                                  "background-color: #8BC34A;"
                                "}"
                                ".invoice {"
                                  "margin: 25px auto;"
                                  "text-align: left;"
                                  "width: 100%;"
                                "}"
                                ".invoice td {"
                                  "padding: 5px 0;"
                                "}"
                                ".invoice .invoice-items {"
                                  "width: 100%;"
                                "}"
                                ".invoice .invoice-items td {"
                                  "border-top: #eee 1px solid;"
                                "}"
                                ".invoice .invoice-items .total td {"
                                  "border-top: 2px solid #6c7b88;"
                                  "font-size: 18px;"
                                "}"
                                "@media only screen and (max-width: 640px) {"
                                  "body {"
                                    "padding: 0 !important;"
                                  "}"
                                  "h1, h2, h3, h4 {"
                                    "font-weight: 800 !important;"
                                    "margin: 20px 0 5px !important;"
                                  "}"
                                  "h1 {"
                                    "font-size: 22px !important;"
                                  "}"
                                  "h2 {"
                                    "font-size: 18px !important;"
                                  "}"
                                  "h3 {"
                                    "font-size: 16px !important;"
                                  "}"
                                  ".container {"
                                    "padding: 0 !important;"
                                    "width: 100% !important;"
                                  "}"
                                  ".content {"
                                    "padding: 0 !important;"
                                  "}"
                                  ".content-wrap {"
                                    "padding: 10px !important;"
                                  "}"
                                  ".invoice {"
                                    "width: 100% !important;"
                                  "}"
                                "}"
                        "</style>"
                        "</head>"
                        "<body itemscope itemtype='http://schema.org/EmailMessage' style='-webkit-font-smoothing: antialiased; -webkit-text-size-adjust: none; width: 100% !important; height: 100%; line-height: 1.6em; color: #6c7b88; background-color: #ecf0f5; padding: 0;' bgcolor='#ecf0f5'>"
                        "<table class='body-wrap' style='background-color: #ecf0f5; width: 100%;' bgcolor='#ecf0f5'>"
                            "<tr>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                                "<td class='container' width='600' style='vertical-align: top; display: block !important; max-width: 600px !important; clear: both !important; width: 100% !important; margin: 0 auto; padding: 0;' valign='top'>"
                                    "<div class='content' style='max-width: 600px; display: block; margin: 0 auto; padding: 0;'>"
                                        "<table class='main' width='100%' cellpadding='0' cellspacing='0' itemprop='action' itemscope itemtype='http://schema.org/ConfirmAction' style='background-color: #fff; border-bottom-color: #d7d7d7; border-bottom-width: 2px; border-bottom-style: solid;' bgcolor='#fff'>"
                                            "<tr>"
                                                "<td class='content-wrap' style='vertical-align: top; padding: 10px;' valign='top'>"
                                                    "<meta itemprop='name' content='Confirm Email'>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0' bgcolor='#D8000C'>"
                                                        "<tr>"
                                                            "<tb>"
                                                                "<td style='vertical-align: top;' valign='top'>") + dataglen_logo_html + \
                                                                ("</td>"
                                                                "<td style='vertical-align: top;' valign='top'>") + client_logo_html + \
                                                            ("</td>"
                                                            "</tb>"
                                                        "</tr>"
                                                    "</table>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0'>"
                                                        "<tr>"
                                                            "<td class='content-block' style='vertical-align: top; padding: 0 0 20px;' valign='top'>"
                                                                "<h2 style='font-family: Verdana, Geneva, sans-serif; color: #1a2c3f; line-height: 1.2em; font-weight: 800 !important; font-size: 16px !important; margin: 20px 0 5px; text-align: center;'>" + event_name +" event occurred at "+ str(plant.location) + " for the following sources: " + "</h2>"
                                                            "</td>"
                                                        "</tr>"
                                                    "</table>"
                                                        "<table align='center' cellpadding='2' cellspacing='2' bgcolor='#C0C0C0' padding-right='1' padding-left='1'>"
                                                            "<tb>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 100px;background-color: white;' valign='top'>" + \
                                                                    (event_sources) + \
                                                                "</td>"
                                                                "</tr>"
                                                            "</tb>"
                                                        "</table>"
                                                "</td>"
                                            "</tr>"
                                        "</table>"
                                        "<div class='footer' style='width: 100%; clear: both; color: #999; padding: 20px;'>"
                                            "<table width='100%'>"
                                                "<tr>"
                                                    "<td class='aligncenter content-block' style='vertical-align: top; color: #999; font-size: 12px; text-align: center; padding: 0 0 20px;' align='center' valign='top'><h3>Follow <a href='https://dataglen.com'>DataGlen</a> on</h3><a href='https://twitter.com/dataglen'>Twitter</a> <a href='https://www.linkedin.com/company/dataglen'>LinkedIn</a> <a href='https://www.facebook.com/dataglen/'>Facebook</a></td>"
                                                "</tr>"
                                            "</table>"
                                        "</div>"
                                    "</div>"
                                "</td>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                            "</tr>"
                        "</table>"
                        "</body>"
                        "</html>")

        report_account_email = 'alerts@dataglen.com'
        from_email = 'alerts@dataglen.com'
        recipient = email
        subject = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant.location)

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))
        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()
    except Exception as exception:
        print("Error in sending detailed alert for plant : " + str(plant.slug) + " " + str(exception))


def send_error_info(plant, event_type, event_name, event_sources, email):
    try:
        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = (  "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.0 Transitional//EN' 'http://www.w3.org/TR/REC-html40/loose.dtd'>"
                        "<html xmlns='http://www.w3.org/1999/xhtml'>"
                        "<head>"
                        "<meta name='viewport' content='width=device-width'>"
                        "<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>"
                        "<title>Actionable emails e.g. reset password</title>"
                        "<style>"
                         "{"
                              "margin: 0;"
                              "font-family: Verdana, Geneva, sans-serif;"
                              "box-sizing: border-box;"
                              "font-size: 14px;"
                            "}"
                            "img {"
                              "max-width: 100%;"
                            "}"
                            "body {"
                              "-webkit-font-smoothing: antialiased;"
                              "-webkit-text-size-adjust: none;"
                              "width: 100% !important;"
                              "height: 100%;"
                              "line-height: 1.6em;"
                                "}"
                                "table td {"
                                  "vertical-align: top;"
                                "}"
                                "body {"
                                  "background-color: #ecf0f5;"
                                  "color: #6c7b88"
                                "}"
                                ".body-wrap {"
                                  "background-color: #ecf0f5;"
                                  "width: 100%;"
                                "}"
                                ".container {"
                                  "display: block !important;"
                                  "max-width: 600px !important;"
                                  "margin: 0 auto !important;"
                                  "/* makes it centered */"
                                  "clear: both !important;"
                                "}"
                                ".content {"
                                  "max-width: 600px;"
                                  "margin: 0 auto;"
                                  "display: block;"
                                  "padding: 20px;"
                                "}"
                                ".main {"
                                  "background-color: #fff;"
                                  "border-bottom: 2px solid #d7d7d7;"
                                "}"
                                ".content-wrap {"
                                  "padding: 20px;"
                                "}"
                                ".content-block {"
                                  "padding: 0 0 20px;"
                                "}"
                                ".header {"
                                  "width: 100%;"
                                  "margin-bottom: 20px;"
                                "}"
                                ".footer {"
                                  "width: 100%;"
                                  "clear: both;"
                                  "color: #999;"
                                  "padding: 20px;"
                                "}"
                                ".footer p, .footer a, .footer td {"
                                  "color: #999;"
                                  "font-size: 12px;"
                                "}"
                                "h1, h2, h3 {"
                                  "font-family: Verdana, Geneva, sans-serif;"
                                  "color: #1a2c3f;"
                                  "margin: 30px 0 0;"
                                  "line-height: 1.2em;"
                                  "font-weight: 400;"
                                "}"
                                "h1 {"
                                  "font-size: 32px;"
                                  "font-weight: 500;"
                                "}"
                                "h2 {"
                                  "font-size: 24px;"
                                "}"
                                "h3 {"
                                  "font-size: 18px;"
                                "}"
                                "h4 {"
                                  "font-size: 14px;"
                                  "font-weight: 600;"
                                "}"

                                "p, ul, ol {"
                                  "margin-bottom: 10px;"
                                  "font-weight: normal;"
                                "}"
                                "p li, ul li, ol li {"
                                  "margin-left: 5px;"
                                  "list-style-position: inside;"
                                "}"
                                "a {"
                                  "color: #348eda;"
                                  "text-decoration: underline;"
                                "}"
                                ".btn-primary {"
                                  "text-decoration: none;"
                                  "color: #FFF;"
                                  "background-color: #42A5F5;"
                                  "border: solid #42A5F5;"
                                  "border-width: 10px 20px;"
                                  "line-height: 2em;"
                                  "font-weight: bold;"
                                  "text-align: center;"
                                  "cursor: pointer;"
                                  "display: inline-block;"
                                  "text-transform: capitalize;"
                                "}"
                                ".last {"
                                  "margin-bottom: 0;"
                                "}"
                                ".first {"
                                  "margin-top: 0;"
                                "}"
                                ".aligncenter {"
                                  "text-align: center;"
                                "}"
                                ".alignright {"
                                  "text-align: right;"
                                "}"
                                ".alignleft {"
                                  "text-align: left;"
                                "}"
                                ".clear {"
                                  "clear: both;"
                                "}"
                                ".alert {"
                                  "font-size: 16px;"
                                  "color: #fff;"
                                  "font-weight: 500;"
                                  "padding: 20px;"
                                  "text-align: center;"
                                "}"
                                ".alert a {"
                                  "color: #fff;"
                                  "text-decoration: none;"
                                  "font-weight: 500;"
                                  "font-size: 16px;"
                                "}"
                                ".alert.alert-warning {"
                                  "background-color: #FFA726;"
                                "}"
                                ".alert.alert-bad {"
                                  "background-color: #ef5350;"
                                "}"
                                ".alert.alert-good {"
                                  "background-color: #8BC34A;"
                                "}"
                                ".invoice {"
                                  "margin: 25px auto;"
                                  "text-align: left;"
                                  "width: 100%;"
                                "}"
                                ".invoice td {"
                                  "padding: 5px 0;"
                                "}"
                                ".invoice .invoice-items {"
                                  "width: 100%;"
                                "}"
                                ".invoice .invoice-items td {"
                                  "border-top: #eee 1px solid;"
                                "}"
                                ".invoice .invoice-items .total td {"
                                  "border-top: 2px solid #6c7b88;"
                                  "font-size: 18px;"
                                "}"
                                "@media only screen and (max-width: 640px) {"
                                  "body {"
                                    "padding: 0 !important;"
                                  "}"
                                  "h1, h2, h3, h4 {"
                                    "font-weight: 800 !important;"
                                    "margin: 20px 0 5px !important;"
                                  "}"
                                  "h1 {"
                                    "font-size: 22px !important;"
                                  "}"
                                  "h2 {"
                                    "font-size: 18px !important;"
                                  "}"
                                  "h3 {"
                                    "font-size: 16px !important;"
                                  "}"
                                  ".container {"
                                    "padding: 0 !important;"
                                    "width: 100% !important;"
                                  "}"
                                  ".content {"
                                    "padding: 0 !important;"
                                  "}"
                                  ".content-wrap {"
                                    "padding: 10px !important;"
                                  "}"
                                  ".invoice {"
                                    "width: 100% !important;"
                                  "}"
                                "}"
                        "</style>"
                        "</head>"
                        "<body itemscope itemtype='http://schema.org/EmailMessage' style='-webkit-font-smoothing: antialiased; -webkit-text-size-adjust: none; width: 100% !important; height: 100%; line-height: 1.6em; color: #6c7b88; background-color: #ecf0f5; padding: 0;' bgcolor='#ecf0f5'>"
                        "<table class='body-wrap' style='background-color: #ecf0f5; width: 100%;' bgcolor='#ecf0f5'>"
                            "<tr>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                                "<td class='container' width='600' style='vertical-align: top; display: block !important; max-width: 600px !important; clear: both !important; width: 100% !important; margin: 0 auto; padding: 0;' valign='top'>"
                                    "<div class='content' style='max-width: 600px; display: block; margin: 0 auto; padding: 0;'>"
                                        "<table class='main' width='100%' cellpadding='0' cellspacing='0' itemprop='action' itemscope itemtype='http://schema.org/ConfirmAction' style='background-color: #fff; border-bottom-color: #d7d7d7; border-bottom-width: 2px; border-bottom-style: solid;' bgcolor='#fff'>"
                                            "<tr>"
                                                "<td class='content-wrap' style='vertical-align: top; padding: 10px;' valign='top'>"
                                                    "<meta itemprop='name' content='Confirm Email'>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFF00'>"
                                                        "<tr>"
                                                            "<tb>"
                                                                "<td style='vertical-align: top;' valign='top'>") + dataglen_logo_html + \
                                                                ("</td>"
                                                                "<td style='vertical-align: top;' valign='top'>") + client_logo_html + \
                                                            ("</td>"
                                                            "</tb>"
                                                        "</tr>"
                                                    "</table>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0'>"
                                                        "<tr>"
                                                            "<td class='content-block' style='vertical-align: top; padding: 0 0 20px;' valign='top'>"
                                                                "<h2 style='font-family: Verdana, Geneva, sans-serif; color: #1a2c3f; line-height: 1.2em; font-weight: 800 !important; font-size: 16px !important; margin: 20px 0 5px; text-align: center;'>" + event_name +" event occurred at "+ str(plant.location) + " for the following sources: " + "</h2>"
                                                            "</td>"
                                                        "</tr>"
                                                    "</table>"
                                                        "<table align='center' cellpadding='2' cellspacing='2' bgcolor='#C0C0C0' padding-right='1' padding-left='1'>"
                                                            "<tb>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 100px;background-color: white;' valign='top'>" + \
                                                                    (event_sources) + \
                                                                "</td>"
                                                                "</tr>"
                                                            "</tb>"
                                                        "</table>"
                                                "</td>"
                                            "</tr>"
                                        "</table>"
                                        "<div class='footer' style='width: 100%; clear: both; color: #999; padding: 20px;'>"
                                            "<table width='100%'>"
                                                "<tr>"
                                                    "<td class='aligncenter content-block' style='vertical-align: top; color: #999; font-size: 12px; text-align: center; padding: 0 0 20px;' align='center' valign='top'><h3>Follow <a href='https://dataglen.com'>DataGlen</a> on</h3><a href='https://twitter.com/dataglen'>Twitter</a> <a href='https://www.linkedin.com/company/dataglen'>LinkedIn</a> <a href='https://www.facebook.com/dataglen/'>Facebook</a></td>"
                                                "</tr>"
                                            "</table>"
                                        "</div>"
                                    "</div>"
                                "</td>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                            "</tr>"
                        "</table>"
                        "</body>"
                        "</html>")

        report_account_email = 'alerts@dataglen.com'
        from_email = 'info@dataglen.com'
        recipient = email
        subject = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant.location)

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))
        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()
    except Exception as exception:
        print("Error in sending detailed alert for plant : " + str(plant.slug) + " " + str(exception))


def send_inverter_error_alert(plant,event_type, event_name, event_sources, email):
    try:
        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = (  "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.0 Transitional//EN' 'http://www.w3.org/TR/REC-html40/loose.dtd'>"
                        "<html xmlns='http://www.w3.org/1999/xhtml'>"
                        "<head>"
                        "<meta name='viewport' content='width=device-width'>"
                        "<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>"
                        "<title>Actionable emails e.g. reset password</title>"
                        "<style>"
                         "{"
                              "margin: 0;"
                              "font-family: Verdana, Geneva, sans-serif"
                              "box-sizing: border-box;"
                              "font-size: 14px;"
                            "}"
                            "img {"
                              "max-width: 100%;"
                            "}"
                            "body {"
                              "-webkit-font-smoothing: antialiased;"
                              "-webkit-text-size-adjust: none;"
                              "width: 100% !important;"
                              "height: 100%;"
                              "line-height: 1.6em;"
                                "}"
                                "table td {"
                                  "vertical-align: top;"
                                "}"
                                "body {"
                                  "background-color: #ecf0f5;"
                                  "color: #6c7b88"
                                "}"
                                ".body-wrap {"
                                  "background-color: #ecf0f5;"
                                  "width: 100%;"
                                "}"
                                ".container {"
                                  "display: block !important;"
                                  "max-width: 600px !important;"
                                  "margin: 0 auto !important;"
                                  "/* makes it centered */"
                                  "clear: both !important;"
                                "}"
                                ".content {"
                                  "max-width: 600px;"
                                  "margin: 0 auto;"
                                  "display: block;"
                                  "padding: 20px;"
                                "}"
                                ".main {"
                                  "background-color: #fff;"
                                  "border-bottom: 2px solid #d7d7d7;"
                                "}"
                                ".content-wrap {"
                                  "padding: 20px;"
                                "}"
                                ".content-block {"
                                  "padding: 0 0 20px;"
                                "}"
                                ".header {"
                                  "width: 100%;"
                                  "margin-bottom: 20px;"
                                "}"
                                ".footer {"
                                  "width: 100%;"
                                  "clear: both;"
                                  "color: #999;"
                                  "padding: 20px;"
                                "}"
                                ".footer p, .footer a, .footer td {"
                                  "color: #999;"
                                  "font-size: 12px;"
                                "}"
                                "h1, h2, h3 {"
                                  "font-family: Verdana, Geneva, sans-serif;"
                                  "color: #1a2c3f;"
                                  "margin: 30px 0 0;"
                                  "line-height: 1.2em;"
                                  "font-weight: 400;"
                                "}"
                                "h1 {"
                                  "font-size: 32px;"
                                  "font-weight: 500;"
                                "}"
                                "h2 {"
                                  "font-size: 24px;"
                                "}"
                                "h3 {"
                                  "font-size: 18px;"
                                "}"
                                "h4 {"
                                  "font-size: 14px;"
                                  "font-weight: 600;"
                                "}"

                                "p, ul, ol {"
                                  "margin-bottom: 10px;"
                                  "font-weight: normal;"
                                "}"
                                "p li, ul li, ol li {"
                                  "margin-left: 5px;"
                                  "list-style-position: inside;"
                                "}"
                                "a {"
                                  "color: #348eda;"
                                  "text-decoration: underline;"
                                "}"
                                ".btn-primary {"
                                  "text-decoration: none;"
                                  "color: #FFF;"
                                  "background-color: #42A5F5;"
                                  "border: solid #42A5F5;"
                                  "border-width: 10px 20px;"
                                  "line-height: 2em;"
                                  "font-weight: bold;"
                                  "text-align: center;"
                                  "cursor: pointer;"
                                  "display: inline-block;"
                                  "text-transform: capitalize;"
                                "}"
                                ".last {"
                                  "margin-bottom: 0;"
                                "}"
                                ".first {"
                                  "margin-top: 0;"
                                "}"
                                ".aligncenter {"
                                  "text-align: center;"
                                "}"
                                ".alignright {"
                                  "text-align: right;"
                                "}"
                                ".alignleft {"
                                  "text-align: left;"
                                "}"
                                ".clear {"
                                  "clear: both;"
                                "}"
                                ".alert {"
                                  "font-size: 16px;"
                                  "color: #fff;"
                                  "font-weight: 500;"
                                  "padding: 20px;"
                                  "text-align: center;"
                                "}"
                                ".alert a {"
                                  "color: #fff;"
                                  "text-decoration: none;"
                                  "font-weight: 500;"
                                  "font-size: 16px;"
                                "}"
                                ".alert.alert-warning {"
                                  "background-color: #FFA726;"
                                "}"
                                ".alert.alert-bad {"
                                  "background-color: #ef5350;"
                                "}"
                                ".alert.alert-good {"
                                  "background-color: #8BC34A;"
                                "}"
                                ".invoice {"
                                  "margin: 25px auto;"
                                  "text-align: left;"
                                  "width: 100%;"
                                "}"
                                ".invoice td {"
                                  "padding: 5px 0;"
                                "}"
                                ".invoice .invoice-items {"
                                  "width: 100%;"
                                "}"
                                ".invoice .invoice-items td {"
                                  "border-top: #eee 1px solid;"
                                "}"
                                ".invoice .invoice-items .total td {"
                                  "border-top: 2px solid #6c7b88;"
                                  "font-size: 18px;"
                                "}"
                                "@media only screen and (max-width: 640px) {"
                                  "body {"
                                    "padding: 0 !important;"
                                  "}"
                                  "h1, h2, h3, h4 {"
                                    "font-weight: 800 !important;"
                                    "margin: 20px 0 5px !important;"
                                  "}"
                                  "h1 {"
                                    "font-size: 22px !important;"
                                  "}"
                                  "h2 {"
                                    "font-size: 18px !important;"
                                  "}"
                                  "h3 {"
                                    "font-size: 16px !important;"
                                  "}"
                                  ".container {"
                                    "padding: 0 !important;"
                                    "width: 100% !important;"
                                  "}"
                                  ".content {"
                                    "padding: 0 !important;"
                                  "}"
                                  ".content-wrap {"
                                    "padding: 10px !important;"
                                  "}"
                                  ".invoice {"
                                    "width: 100% !important;"
                                  "}"
                                "}"
                        "</style>"
                        "</head>"
                        "<body itemscope itemtype='http://schema.org/EmailMessage' style='-webkit-font-smoothing: antialiased; -webkit-text-size-adjust: none; width: 100% !important; height: 100%; line-height: 1.6em; color: #6c7b88; background-color: #ecf0f5; padding: 0;' bgcolor='#ecf0f5'>"
                        "<table class='body-wrap' style='background-color: #ecf0f5; width: 100%;' bgcolor='#ecf0f5'>"
                            "<tr>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                                "<td class='container' width='600' style='vertical-align: top; display: block !important; max-width: 600px !important; clear: both !important; width: 100% !important; margin: 0 auto; padding: 0;' valign='top'>"
                                    "<div class='content' style='max-width: 600px; display: block; margin: 0 auto; padding: 0;'>"
                                        "<table class='main' width='100%' cellpadding='0' cellspacing='0' itemprop='action' itemscope itemtype='http://schema.org/ConfirmAction' style='background-color: #fff; border-bottom-color: #d7d7d7; border-bottom-width: 2px; border-bottom-style: solid;' bgcolor='#fff'>"
                                            "<tr>"
                                                "<td class='content-wrap' style='vertical-align: top; padding: 10px;' valign='top'>"
                                                    "<meta itemprop='name' content='Confirm Email'>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0' bgcolor='#D8000C'>"
                                                        "<tr>"
                                                            "<tb>"
                                                                "<td style='vertical-align: top;' valign='top'>") + dataglen_logo_html + \
                                                                ("</td>"
                                                                "<td style='vertical-align: top;' valign='top'>") + client_logo_html + \
                                                            ("</td>"
                                                            "</tb>"
                                                        "</tr>"
                                                    "</table>"
                                                    "<table width='100%' cellpadding='0' cellspacing='0'>"
                                                        "<tr>"
                                                            "<td class='content-block' style='vertical-align: top; padding: 0 0 20px;' valign='top'>"
                                                                "<h2 style='font-family: Verdana, Geneva, sans-serif; color: #1a2c3f; line-height: 1.2em; font-weight: 800 !important; font-size: 16px !important; margin: 20px 0 5px; text-align: center;'>" + event_name +" event occurred at "+ str(plant.location) + " for the following sources: " + "</h2>"
                                                            "</td>"
                                                        "</tr>"
                                                    "</table>"
                                                        "<table align='center' cellpadding='2' cellspacing='2' bgcolor='#C0C0C0' padding-right='1   ' padding-left='1'>"
                                                            "<tb>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 0px;padding-right: 0px;background-color: white;' valign='top'>" + \
                                                                    (event_sources) + \
                                                                "</td>"
                                                                "</tr>"
                                                            "</tb>"
                                                        "</table>"
                                                "</td>"
                                            "</tr>"
                                        "</table>"
                                        "<div class='footer' style='width: 100%; clear: both; color: #999; padding: 20px;'>"
                                            "<table width='100%'>"
                                                "<tr>"
                                                    "<td class='aligncenter content-block' style='vertical-align: top; color: #999; font-size: 12px; text-align: center; padding: 0 0 20px;' align='center' valign='top'><h3>Follow <a href='https://dataglen.com'>DataGlen</a> on</h3><a href='https://twitter.com/dataglen'>Twitter</a> <a href='https://www.linkedin.com/company/dataglen'>LinkedIn</a> <a href='https://www.facebook.com/dataglen/'>Facebook</a></td>"
                                                "</tr>"
                                            "</table>"
                                        "</div>"
                                    "</div>"
                                "</td>"
                                "<td style='vertical-align: top;' valign='top'></td>"
                            "</tr>"
                        "</table>"
                        "</body>"
                        "</html>")

        report_account_email = 'alerts@dataglen.com'
        from_email = 'alerts@dataglen.com'
        recipient = email
        subject = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant.location)

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))
        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()
    except Exception as exception:
        print("Error in sending detailed inverter error alert for plant : " + str(plant.slug) + " " + str(exception))
