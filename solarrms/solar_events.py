from events.models import EventsByTime, EventsConfig, EventsByError, Events, UserEventAlertsPreferences, AlertManagement
from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource, PerformanceRatioTable, \
    InverterErrorCodes, AJB
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

from IPython.display import display, HTML
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from solarrms.api_views import fix_generation_units

EMAIL_TITLE = "DataGlen Solar RMS Alert for "
SIGNOFF_STRING = "\n--\nDataGlen Solar RMS"
FROM_EMAIL = 'alerts@dataglen.com'

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

# method to create inverter off ticket
def create_inverter_off_ticket(plant, inverters_INVERTER_OFF_ticket, current_time):
    print("inside inverter off ticket")
    if len(inverters_INVERTER_OFF_ticket) == 0:
        pass
    else:
        associations_dict = {}
        for inverter in inverters_INVERTER_OFF_ticket:
            associations_dict[inverter.sourceKey] = ['INVERTER_OFF', '-1', inverter.name, current_time]
        try:
            priority = 2
            due_date = current_time + datetime.timedelta(hours=2)
            #user = plant.owner.organization_user.user
            create_ticket(plant=plant, priority=priority, due_date=due_date,
                          ticket_name="Inverter off at " + str(plant.location),
                          ticket_description = 'Inverter Off event has occurred at : ' + str(plant.location),
                          associations_dict = associations_dict,
                          open_comment='Ticket created automatically based on the inverter off alerts.')
        except Exception as exception:
            print("Error in creating ticket for Inverter off at : " + str(plant.name) + " : " + str(exception))

# method to create AJB off ticket
def create_ajb_off_ticket(plant, ajbs_AJB_OFF_ticket, current_time):
    print("inside ajb off ticket")
    if len(ajbs_AJB_OFF_ticket) == 0:
        pass
    else:
        associations_dict = {}
        for ajb in ajbs_AJB_OFF_ticket:
            associations_dict[ajb.sourceKey] = ['AJB_OFF', '-1', ajb.name, current_time]
        try:
            priority = 2
            due_date = current_time + datetime.timedelta(hours=2)
            #user = plant.owner.organization_user.user
            create_ticket(plant=plant, priority=priority, due_date=due_date,
                          ticket_name="AJB off at " + str(plant.location),
                          ticket_description = 'AJB Off event has occurred at : ' + str(plant.location),
                          associations_dict = associations_dict,
                          open_comment='Ticket created automatically based on the ajb off alerts.')
        except Exception as exception:
            print("Error in creating ticket for Ajb off at : " + str(plant.name) + " : " + str(exception))

# method to create network down ticket
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
        due_date = current_time + datetime.timedelta(hours=2)
        #user = plant.owner.organization_user.user
        try:
            create_ticket(plant=plant, priority=priority, due_date=due_date,
                          ticket_name="Network down at " + str(plant.location),
                          ticket_description = 'Network down event has occurred at : ' + str(plant.location),
                          associations_dict = associations_dict,
                          open_comment='Ticket created automatically based on the network down alerts.')
        except Exception as exception:
            print("Error in creating NETWORK_DOWN ticket for : " + str(gateway.sourceKey) + " : " + str(exception))


# method to update network down ticket
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

# method to update inverter off ticket
def update_inverter_off_ticket(plant, inverters_INVERTER_ON_ticket, current_time):
    ticket = None
    if len(inverters_INVERTER_ON_ticket) == 0:
        pass
    else:
        ticket_associations = []
        for inverter in inverters_INVERTER_ON_ticket:
            print(inverter.sourceKey)
            ticket_association = TicketAssociation.objects.filter(identifier=inverter.sourceKey,
                                                                   event_name='INVERTER_OFF',
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
            print("Error in closing the inverter off ticket for : " + str(plant.name) + " : " + str(exception))

# method to update AJB off ticket
def update_ajb_off_ticket(plant, ajbs_AJB_ON_ticket, current_time):
    ticket = None
    if len(ajbs_AJB_ON_ticket) == 0:
        pass
    else:
        ticket_associations = []
        for ajb in ajbs_AJB_ON_ticket:
            print(ajb.sourceKey)
            ticket_association = TicketAssociation.objects.filter(identifier=ajb.sourceKey,
                                                                   event_name='AJB_OFF',
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
            print("Error in closing the ajb off ticket for : " + str(plant.name) + " : " + str(exception))


# method to create ticket for inverter alarms
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
            due_date = current_time + datetime.timedelta(hours=5)
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


# Method to log an event
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
    except Exception as exception:
        print("Error in saving events: " + str(exception))


# Method to log network up and down events
def solar_network_events_check(plant):
    try:
        isNetworkDown = False
        if plant.isOperational:
            gateway_sources = GatewaySource.objects.filter(plant=plant)
            for gateway in gateway_sources:
                try:
                    tz = pytz.timezone(gateway.dataTimezone)
                except:
                    print("error in converting current time to source timezone")
                try:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(gateway.dataTimezone))
                except Exception as exc:
                    current_time = timezone.now()

                # Check if the heartbeat is received from the gateway sources
                if gateway.isMonitored:
                    gateway_data = SourceMonitoring.objects.filter(source_key=gateway.sourceKey)
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
                        else:
                            # Log an event for NETWORK_UP
                            events_write(current_time.replace(second=0, microsecond=0),current_time.replace(second=0, microsecond=0), gateway.sourceKey, "NETWORK_UP", "-1")
                            print("NETWORK_UP" + " event logged for: " + str(gateway.sourceKey))
                    else:
                        #Network is down
                        #Log an event for NETWORK_DOWN if the last event logged for this source was NETWORK_UP
                        #In this case no need to check for INVERTER_ON, INVERTER_OFF events
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
        return isNetworkDown
    except Exception as exception:
        print('Error in checking the network events for plant : ' + str(plant.name) + " : " + str(exception))

# method to log inverter on and off events
def solar_inverter_events_check(plant, isNetworkDown):
    try:
        if not isNetworkDown:
            inverters = IndependentInverter.objects.filter(plant=plant)
            for inverter in inverters:
                if inverter.isMonitored:
                    # Get the current time in inverter timezone
                    try:
                        tz = pytz.timezone(inverter.dataTimezone)
                    except:
                        print("error in converting current time to source timezone")
                    try:
                        current_time = timezone.now()
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
                            #if the last entry was for INVERTER_ON
                            isInverterUp = True
                            if (str(inverter_events_entry[0].event_name) == 'INVERTER_ON'):
                                # No need to log an event
                                pass
                            else:
                                # Log an event for INVERTER_ON
                                events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0),inverter.sourceKey, "INVERTER_ON", "-1")
                                print("INVERTER_ON" + " event logged for: " + str(inverter.sourceKey))
                        else:
                             # Log an event for INVERTER_ON
                            events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), inverter.sourceKey, "INVERTER_ON", "-1")
                            print("INVERTER_ON" + " event logged for: " + str(inverter.sourceKey))
                    # Log an event for INVERTER_OFF if the last event logged for inverter was INVERTER_ON
                    else:
                        # Check for the last entry made in the EventsByTime table for inverter
                        inverter_events_entry = EventsByTime.objects.filter(identifier=inverter.sourceKey).limit(1)

                        if (len(inverter_events_entry) > 0):
                            #if the last entry was for INVERTER_OFF
                            if (str(inverter_events_entry[0].event_name) == 'INVERTER_OFF'):
                                # No need to log an event
                                pass
                            else:
                                # Log an event for INVERTER_OFF
                                events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), inverter.sourceKey, "INVERTER_OFF", "-1")
                                print("INVERTER_OFF" + " event logged for: " + str(inverter.sourceKey))
                                # TODO: create a ticket for inverter off for this inverter

                        else:
                            # Log an event for INVERTER_OFF
                            events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), inverter.sourceKey, "INVERTER_OFF", "-1")
                            print("INVERTER_OFF" + " event logged for: " + str(inverter.sourceKey))
    except Exception as exception:
        print("Error in checking inverter events for plant : " + str(plant.name) + " : " + str(exception))

# method to log AJB on and off events
def solar_ajb_events_check(plant, isNetworkDown):
    try:
        ajbs = AJB.objects.filter(plant=plant)
        if not isNetworkDown:
            for ajb in ajbs:
                if ajb.isMonitored:
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
                            #if the last entry was for AJB_ON
                            if (str(ajb_events_entry[0].event_name) == 'AJB_ON'):
                                # No need to log an event
                                pass
                            else:
                                # Log an event for AJB_ON
                                events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0),ajb.sourceKey, "AJB_ON", "-1")
                                print("AJB_ON" + " event logged for: " + str(ajb.sourceKey))
                        else:
                             # Log an event for AJB_ON
                            events_write(current_time.replace(second=0,microsecond=0), current_time.replace(second=0, microsecond=0), ajb.sourceKey, "AJB_ON", "-1")
                            print("AJB_ON" + " event logged for: " + str(ajb.sourceKey))
                    # Log an event for AJB_OFF if the last event logged for ajb was AJB_ON
                    else:
                        # Check for the last entry made in the EventsByTime table for inverter
                        ajb_events_entry = EventsByTime.objects.filter(identifier=ajb.sourceKey).limit(1)

                        if (len(ajb_events_entry) > 0):
                            #if the last entry was for AJB_OFF
                            if (str(ajb_events_entry[0].event_name) == 'AJB_OFF'):
                                # No need to log an event
                                pass
                            else:
                                # Log an event for AJB_OFF
                                events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), ajb.sourceKey, "AJB_OFF", "-1")
                                print("AJB_OFF" + " event logged for: " + str(ajb.sourceKey))
                        else:
                            # Log an event for AJB_OFF
                            events_write(current_time.replace(second=0, microsecond=0), current_time.replace(second=0, microsecond=0), ajb.sourceKey, "AJB_OFF", "-1")
                            print("AJB_OFF" + " event logged for: " + str(ajb.sourceKey))
    except Exception as exception:
        print("Error in checking the AJB events for plant : " + str(plant.name) + " : " + str(exception))

# method to send the email and sms alerts
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
                if str(event_type) is 'ERROR':
                    html_content = '<body style="background-color:red;"> <h1><center> DataGlen Solar RMS notification </center></h1></body></br>'
                elif str(event_type) is 'INFO':
                    html_content = '<body style="background-color:yellow;"> <h1><center> DataGlen Solar RMS notification </center></h1></body></br>'
                else:
                    html_content = ''
                email_subject = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant_location)
                html_content += 'Hi,<br><br> ' + str(event_name) +' event has occurred at ' + str(plant_location) + ' for following sources: <br><br>'+ str(event_sources_str)
                html_content += '<br><br> Thank You, <br> Team DataGlen <br>'
                html_content += '<body style="background-color:powderblue;" align="right"><h5>Connect with us </h5><a href="https://twitter.com/dataglen">Twitter</a> <a href="https://www.linkedin.com/company/dataglen">LinkedIn</a> <a href="https://www.facebook.com/dataglen/">Facebook</body>'
                text_content = ''
                try:
                    if email!='':
                        msg = EmailMultiAlternatives(email_subject, text_content, FROM_EMAIL, [email])
                        msg.attach_alternative(html_content, "text/html")
                        msg.send()
                except:
                    print("Error in sending email")
                try:
                    if phone!='':
                        send_solutions_infini_sms(phone,sms_message)
                except Exception as exception:
                    print("Error in sending sms" + str(exception))

            except Exception as exception:
                print("Error in saving new alerts" + str(exception))

    except Exception as exception:
        print(str(exception))

# method to read network events
def solar_network_events_read(plant):
    try:
        gateways = GatewaySource.objects.filter(plant=plant)
        gateways_NETWORK_DOWN = []
        gateways_NETWORK_DOWN_ticket = []
        gateways_NETWORK_UP = []
        gateways_NETWORK_UP_ticket = []
        for gateway in gateways:
            try:
                tz = pytz.timezone(gateway.dataTimezone)
            except:
                print("error in converting current time to source timezone")
            try:
                current_time = timezone.now()
                # astimezone does the conversion and updates the tzinfo part
                current_time = current_time.astimezone(pytz.timezone(gateway.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            if  current_time.minute < EVENTS_UPDATE_INTERVAL_MINUTES:
                initial_time = current_time.replace(second=0, microsecond=0, minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES+60, hour=current_time.hour-1)
            else:
                initial_time = current_time.replace(second=0, microsecond=0, minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES)
            gateway_events = EventsByTime.objects.filter(identifier=gateway.sourceKey, insertion_time__gt=initial_time).limit(1)
            if len(gateway_events):
                if gateway_events[0].event_name == "NETWORK_DOWN":
                    gateways_NETWORK_DOWN.append(gateway.name)
                    gateways_NETWORK_DOWN_ticket.append(gateway)
                elif gateway_events[0].event_name == "NETWORK_UP":
                    gateways_NETWORK_UP.append(gateway.name)
                    gateways_NETWORK_UP_ticket.append(gateway)
        if len(gateways_NETWORK_DOWN)>0:
            create_network_down_ticket(plant=plant, gateways_NETWORK_DOWN_ticket=gateways_NETWORK_DOWN_ticket, current_time=current_time)
            sendAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,event_name="NETWORK_DOWN",request_arrival_time=current_time,event_sources=gateways_NETWORK_DOWN,event_time=current_time)
            print("NETWORK_DOWN event notification sent")
        if len(gateways_NETWORK_UP)>0:
            update_network_down_ticket(plant=plant, gateways_NETWORK_UP_ticket = gateways_NETWORK_UP_ticket, current_time=current_time)
            sendAlertsWithoutCheck(event_type='INFO',identifier=plant.slug,event_name="NETWORK_UP",request_arrival_time=current_time,event_sources=gateways_NETWORK_UP,event_time=current_time)
            print("NETWORK_UP event notification sent")
    except Exception as exception:
        print("Error in reading the network events for plant : " + str(plant.name) + " : " + str(exception))


# method to read inverter events
def solar_inverter_events_read(plant):
    try:
        inverters_INVERTER_OFF =[]
        inverters_INVERTER_ON = []
        inverters_INVERTER_OFF_ticket = []
        inverters_INVERTER_ON_ticket = []
        inverters = IndependentInverter.objects.filter(plant=plant)
        for inverter in inverters:
            try:
                tz = pytz.timezone(inverter.dataTimezone)
            except:
                print("error in converting current time to source timezone")
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            initial_time = current_time.replace(minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES, second=0, microsecond=0)
            inverter_events = EventsByTime.objects.filter(identifier=inverter.sourceKey, insertion_time__gt=initial_time).limit(1)
            if len(inverter_events) > 0:
                if inverter_events[0].event_name == "INVERTER_OFF":
                    inverters_INVERTER_OFF.append(inverter.name)
                    inverters_INVERTER_OFF_ticket.append(inverter)
                elif inverter_events[0].event_name == "INVERTER_ON":
                    inverters_INVERTER_ON.append(inverter.name)
                    inverters_INVERTER_ON_ticket.append(inverter)
        if len(inverters_INVERTER_OFF)>0:
            create_inverter_off_ticket(plant=plant, inverters_INVERTER_OFF_ticket=inverters_INVERTER_OFF_ticket, current_time=current_time)
            sendAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,event_name="INVERTER_OFF",request_arrival_time=current_time,event_sources=inverters_INVERTER_OFF,event_time=current_time)
            print("INVERTER_OFF event notification sent")
        if len(inverters_INVERTER_ON)>0:
            update_inverter_off_ticket(plant=plant, inverters_INVERTER_ON_ticket=inverters_INVERTER_ON_ticket, current_time=current_time)
            sendAlertsWithoutCheck(event_type='INFO',identifier=plant.slug,event_name="INVERTER_ON",request_arrival_time=current_time,event_sources=inverters_INVERTER_ON,event_time=current_time)
            print("INVERTER_ON notification sent")
    except Exception as exception:
        print("Error in reading the inverter events for plant : " + str(plant.name) + " : " + str(exception))

# method to read AJB events
def solar_ajb_events_read(plant):
    try:
        ajbs_AJB_OFF =[]
        ajbs_AJB_ON = []
        ajbs_AJB_OFF_ticket = []
        ajbs_AJB_ON_ticket = []
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

            initial_time = current_time.replace(minute=current_time.minute-EVENTS_UPDATE_INTERVAL_MINUTES, second=0, microsecond=0)
            ajb_events = EventsByTime.objects.filter(identifier=ajb.sourceKey, insertion_time__gt=initial_time).limit(1)
            if len(ajb_events) > 0:
                if ajb_events[0].event_name == "AJB_OFF":
                    ajbs_AJB_OFF.append(ajb.name)
                    ajbs_AJB_OFF_ticket.append(ajb)
                elif ajb_events[0].event_name == "AJB_ON":
                    ajbs_AJB_ON.append(ajb.name)
                    ajbs_AJB_ON_ticket.append(ajb)

        if len(ajbs_AJB_OFF)>0:
            create_ajb_off_ticket(plant=plant, ajbs_AJB_OFF_ticket=ajbs_AJB_OFF_ticket, current_time=current_time)
            sendAlertsWithoutCheck(event_type='ERROR',identifier=plant.slug,event_name="AJB_OFF",request_arrival_time=current_time,event_sources=ajbs_AJB_OFF,event_time=current_time)
            print("AJB_OFF event notification sent")
        if len(ajbs_AJB_ON)>0:
            update_ajb_off_ticket(plant=plant, ajbs_AJB_ON_ticket=ajbs_AJB_ON_ticket, current_time=current_time)
            sendAlertsWithoutCheck(event_type='INFO',identifier=plant.slug,event_name="AJB_ON",request_arrival_time=current_time,event_sources=ajbs_AJB_ON,event_time=current_time)
            print("AJB_ON notification sent")
    except Exception as exception:
        print("Error in reading the ajb events for plant : " + str(plant.name) + " : " + str(exception))

# method to send inverter error alert
def sendInverterErrorAlertsWithoutCheck(event_type, identifier,
                                        request_arrival_time,
                                        event_name):
    try:
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
                html_content = 'Hi,<br> Following errors have occurred for inverters at ' + str(plant.location) + ':<br><br>'
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
                            except:
                                print("error in converting time to inverter timezone")
                            inverter_error_value = []
                            event_time = value[x].event_time
                            event_time = update_tz(event_time, inverter.dataTimezone)
                            event_time = event_time.replace(tzinfo=pytz.utc).astimezone(tz)
                            inverter_error_value.append(str(event_time))
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
                html_content = html_content + '<br><br> Thank You, <br> Team DataGlen'

                try:
                    if email!='':
                        subject, from_email, to = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant_location) , FROM_EMAIL, email
                        text_content = ''
                        html_content = html_content
                        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                        msg.attach_alternative(html_content, "text/html")
                        msg.send()
                except Exception as exception:
                    print("Error in sending email" + str(exception))
                try:
                    if phone!='':
                        send_solutions_infini_sms(phone,sms_message)
                except Exception as exception:
                    print("Error in sending sms" + str(exception))
    except Exception as exception:
        print(str(exception))

# method to check inverter errors (inverter alarms)
def check_inverter_errors(plant):
    # get all the inverters of plant
    print("Inverter Errors check started! for plant: " + str(plant.name))
    try:
        inverters = IndependentInverter.objects.filter(plant=plant)
    except Exception as exception:
        print("Error in getting the inverters of the plant: " + str(exception))
    current_time = timezone.now()
    try:
        for inverter in inverters:
            try:
                tz = pytz.timezone(inverter.dataTimezone)
            except:
                print("error in converting time to inverter timezone")
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


def send_detailed_report(plant, email):
    try:
        value = None
        plant_meta_source = plant.metadata.plantmetasource
        values = PlantCompleteValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                    count_time_period=86400,
                                                    identifier=plant_meta_source.sourceKey).limit(1)
        if len(values)>0:
            value = values[0]

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
                              "font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;"
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
                                  "font-family: 'Helvetica Neue', Helvetica, Arial, 'Lucida Grande', sans-serif;"
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
                                                    "<table width='100%' cellpadding='0' cellspacing='0'>"
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
                                                                "<h2 style='font-family: 'Helvetica Neue', Helvetica, Arial, 'Lucida Grande', sans-serif; color: #1a2c3f; line-height: 1.2em; font-weight: 800 !important; font-size: 16px !important; margin: 20px 0 5px; text-align: center;'>Today's Performance Report</h2>"
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
                                                                    "Grid Availability"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + (str("{0:.2f}".format(100.0 - value.grid_unavailability)) + " %" if value else "0 %") + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Equipment Availability"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + (str("{0:.2f}".format(100.0 - value.equipment_unavailability)) + " %" if value else "0 %") + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "DC Loss"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(fix_generation_units(float(value.dc_loss)) if value else str(fix_generation_units(0.0))) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Conversion Loss"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(fix_generation_units(float(value.conversion_loss)) if value else str(fix_generation_units(0.0))) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Cable Loss"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(fix_generation_units(float(value.ac_loss)) if value else str(fix_generation_units(0.0))) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Open Tickets"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(value.open_tickets if value else str(0)) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Closed Tickets"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(value.closed_tickets if value else str(0)) + \
                                                                ("</td>"
                                                                "</tr>"
                                                                "<tr>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>"
                                                                    "Unacknowledged Tickets"
                                                                "</td>"
                                                                "<td style='vertical-align:top;padding-left: 100px;padding-right: 50px;background-color: white;' valign='top'>") + str(value.unacknowledged_tickets if value else str(0)) + \
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


# method to send report at end of the day
def send_report(plant, event_name):
    try:
       plant_meta_source = plant.metadata.plantmetasource
       request_arrival_time = timezone.now()
       if plant.isOperational:
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

                    initial_time = request_arrival_time.replace(hour=0,minute=0,second=0)
                    current_time = request_arrival_time.replace(hour=23,minute=59,second=59)
                    try:
                        if plant_meta_source.energy_meter_installed:
                            print("inside energy meter")
                            todays_energy = get_energy_meter_values(initial_time,current_time,plant_meta_source.plant,'DAY')
                        else:
                            todays_energy = get_aggregated_energy(initial_time,current_time,plant_meta_source.plant,'DAY')
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

                    active_alerts = UserEventAlertsPreferences.objects.filter(identifier=plant.slug,
                                                                              event=event,
                                                                              alert_active=True)
                    for alert in active_alerts:
                        print("inside for")
                        email = alert.email_id
                        phone = alert.phone_no
                        plant_location = plant.location
                        plant_name = plant.name
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

                        try:
                            if email!='':
                                send_detailed_report(plant, email)
                        except Exception as exception:
                            print("Error in sending detailed report for the plant : " + str(plant.name) + " " + str(exception))
                        sms_message = 'Hi,\nDaily Performance Report of your plant at '+ str(plant_location)+':\nEnergy Generation : '+ str(today_energy_value) + str(' kWh') + ' ,\nPerformance Ratio : ' + str(performance_ratio_value) + ' ,\nThank you'
                        try:
                            if phone!='':
                                send_solutions_infini_sms(phone,sms_message)
                        except Exception as exception:
                            print("Error in sending sms" + str(exception))
    except Exception as exception:
        print("Error in sending the daily report for plant : " + str(plant.name) + " " + str(exception))


def solar_events_check():
    print("Events cron job started: " + str(datetime.datetime.now()))
    try:
        # get the solar plants
        try:
            plants = SolarPlant.objects.all()
        except ObjectDoesNotExist:
            print("No solar plant found.")
        # iterate for all the plants
        for plant in plants:
            print("For plant: ", plant.slug)
            isNetworkDown = solar_network_events_check(plant)
            solar_network_events_read(plant)
            solar_inverter_events_check(plant, isNetworkDown)
            solar_inverter_events_read(plant)
            solar_ajb_events_check(plant, isNetworkDown)
            solar_ajb_events_read(plant)
            check_inverter_errors(plant)
            send_report(plant, 'DAILY_REPORT')
        print("Cron job completed!")

    except Exception as exception:
        print(str(exception))