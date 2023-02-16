from events.models import EventsByTime, EventsConfig, EventsByError, Events, UserEventAlertsPreferences, AlertManagement
from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource, PerformanceRatioTable, \
    InverterErrorCodes, AJB
import datetime
import pytz
from monitoring.models import SourceMonitoring
from django.utils import timezone
from dataglen.models import ValidDataStorageByStream
import numpy as np
from cassandra.cqlengine.query import BatchQuery
from tabulate import tabulate
from django.core.mail import EmailMultiAlternatives
from kutbill.settings import STRING_EVENTS_UPDATE_INTERVAL_MINUTES, ACTIVE_DEVIATION_NUMBER
from helpdesk.dg_functions import create_ticket

EMAIL_TITLE = "DataGlen Solar RMS Alert for "
FROM_EMAIL = 'alerts@dataglen.com'

# method to update tz
def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt

# method to check if the network is up
def check_network(plant):
    try:
        network_up = False
        gateway_sources = GatewaySource.objects.filter(plant=plant)
        for gateway in gateway_sources:
            if gateway.isMonitored:
                gateway_data = SourceMonitoring.objects.filter(source_key=gateway.sourceKey)
                if (len(gateway_data) > 0):
                    network_up = True
        return network_up
    except Exception as exception:
        print("Error in getting the network details : " + str(exception))

# method to write events into cassandra database
def string_events_write(request_arrival_time, event_time, identifier , event_name, event_code, event_details):
    try:
        print("inside events write")
        batch_query = BatchQuery()
        EventsByTime.batch(batch_query).create(identifier=identifier,
                                               insertion_time=request_arrival_time,
                                               event_name=event_name,
                                               event_time=event_time,
                                               event_code=event_code,
                                               event_details=event_details)

        EventsByError.batch(batch_query).create(identifier=identifier,
                                                event_name=event_name,
                                                insertion_time=request_arrival_time,
                                                event_time=event_time,
                                                event_code=event_code,
                                                event_details=event_details)

        batch_query.execute()
    except Exception as exception:
        print("Error in saving events: " + str(exception))

# method to the the values of strings
def check_string_values(plant, inverter):
    try:
        print("inside string check")
        ajb_up = []
        ajbs = inverter.ajb_units.all()
        #print(ajbs)
        for ajb in ajbs:
            ajb_monitoring = SourceMonitoring.objects.filter(source_key=ajb.sourceKey)
            if len(ajb_monitoring) > 0:
                ajb_up.append(ajb)

        # Get the mean of all the strings of ajbs which are up
        for ajb in ajb_up:
            ajb_strings = ajb.fields.all().filter(isActive=True)
            string_names = []
            for string in ajb_strings:
                if str(string.name).startswith('S'):
                    string_names.append(str(string.name))
            current_time = timezone.now()
            current_time = update_tz(current_time, inverter.dataTimezone)
            initial_time = current_time - datetime.timedelta(minutes=STRING_EVENTS_UPDATE_INTERVAL_MINUTES)
            string_values_dict = {}
            for name in string_names:
                individual_string_values_list = []
                stream_data = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                      stream_name=name,
                                                                      timestamp_in_data__gte=initial_time,
                                                                      timestamp_in_data__lte=current_time
                                                                      ).values_list('stream_value')
                if stream_data:
                    for index in range(len(stream_data)):
                        try:
                            individual_string_values_list.append(float(stream_data[index][0]))
                        except:
                            pass
                    string_values_dict[name] = np.mean(individual_string_values_list)

            string_values_list = list(string_values_dict.values())
            # get the standard deviation of values
            values_standard_deviation = np.std(string_values_list)
            # get the mean of values
            values_mean = np.mean(string_values_list)
            for key in string_values_dict.keys():
                event_detail = {}
                event_detail[key] = string_values_dict[key]
                event_detail['mean'] = values_mean
                if string_values_dict[key] < values_mean-ACTIVE_DEVIATION_NUMBER*values_standard_deviation:
                    #log an event for low string error
                    string_events_write(request_arrival_time=current_time.replace(second=0, microsecond=0),
                                        event_time=current_time.replace(second=0, microsecond=0), identifier=str(ajb.sourceKey)+"_ajb",
                                        event_name='STRING_ERROR_LOW', event_code=str(key), event_details=str(event_detail))
                elif string_values_dict[key] > values_mean+ACTIVE_DEVIATION_NUMBER*values_standard_deviation:
                    # log an event for high string error
                    string_events_write(request_arrival_time=current_time.replace(second=0, microsecond=0),
                                        event_time=current_time.replace(second=0, microsecond=0), identifier=str(ajb.sourceKey)+"_ajb",
                                        event_name='STRING_ERROR_HIGH', event_code=str(key), event_details=str(event_detail))
                else:
                    pass
            print(values_standard_deviation)
            print(values_mean)
    except Exception as exception:
        print(str(exception))

def check_string_events():
    plants = SolarPlant.objects.all()
    for plant in plants:
        if plant.isOperational:
            print("for plant : " + str(plant.slug))
            if not check_network(plant=plant):
                pass
            else:
                inverters = IndependentInverter.objects.filter(plant=plant)
                for inverter in inverters:
                    check_string_values(plant=plant, inverter=inverter)

                read_string_events(plant, 'STRING_ERROR', 'ERROR')


def read_string_events(plant, event_name, event_type):
    try:
        print("inside read events")
        inverters = IndependentInverter.objects.filter(plant=plant)
        current_time = timezone.now()
        html_content = 'Hi,<br> Following errors have occurred for SMB\'s at ' + str(plant.location) + ':<br><br>'
        flag = False
        high_ajbs = []
        low_ajbs = []
        for inverter in inverters:
            try:
                tz = pytz.timezone(inverter.dataTimezone)
            except:
                print("error in converting time to inverter timezone")
            current_time = update_tz(current_time, inverter.dataTimezone)
            initial_time = current_time - datetime.timedelta(minutes=STRING_EVENTS_UPDATE_INTERVAL_MINUTES)
            ajbs = AJB.objects.filter(plant=plant, independent_inverter=inverter)
            for ajb in ajbs:
                flag_high = False
                flag_low = False
                high_errors = []
                low_errors = []
                string_error_values_table_high = []
                string_error_values_table_low = []
                string_high_errors = EventsByError.objects.filter(identifier=str(ajb.sourceKey)+"_ajb",
                                                                  event_name='STRING_ERROR_HIGH',
                                                                  insertion_time__gt=initial_time)
                if len(string_high_errors)> 0:
                    for value in string_high_errors:
                        high_errors.append(value)
                    flag_high=True

                high_ajbs.extend(high_errors)

                print(high_ajbs)

                string_low_errors = EventsByError.objects.filter(identifier=str(ajb.sourceKey)+"_ajb",
                                                                 event_name='STRING_ERROR_LOW',
                                                                 insertion_time__gt=initial_time)
                if len(string_low_errors)> 0:
                    for value in string_low_errors:
                        low_errors.append(value)
                    flag_low=True

                low_ajbs.extend(low_errors)
                print(low_ajbs)

                """
                if flag:
                    sendStringErrorAlerts(plant=plant, identifier=plant.slug, ajb = ajb, event_name='STRING_ERROR',
                                          request_arrival_time=current_time,event_sources_high=high_errors,
                                          event_sources_low=low_errors ,event_time=current_time, event_type='ERROR')
                """
                if flag_high or flag_low:
                    html_content = html_content + '<b><u>'+str(ajb.name) + '</b></u>:<br>'
                    flag = True
                if flag_high:
                    html_content = html_content + '<b><u>'+str("STRING_ERROR_HIGH") + '</b></u>:<br>'
                    for value in high_errors:
                        string_error_values = []
                        event_time = update_tz(value.event_time, inverter.dataTimezone)
                        event_time = event_time.replace(tzinfo=pytz.utc).astimezone(tz)
                        string_error_values.append(str(event_time))
                        string_error_values.append(str(value.event_code))
                        string_error_values.append(str(value.event_details))
                        string_error_values_table_high.append(string_error_values)
                    string_error_values_table_high = tabulate(string_error_values_table_high, headers=['Timestamp','String', 'Values'], tablefmt='html')
                    html_content = html_content + string_error_values_table_high
                if flag_low:
                    html_content = html_content + '<b><u>'+str("STRING_ERROR_LOW") + '</b></u>:<br>'
                    for value in low_errors:
                        string_error_values = []
                        event_time = update_tz(value.event_time, inverter.dataTimezone)
                        event_time = event_time.replace(tzinfo=pytz.utc).astimezone(tz)
                        string_error_values.append(str(event_time))
                        string_error_values.append(str(value.event_code))
                        string_error_values.append(str(value.event_details))
                        string_error_values_table_low.append(string_error_values)
                    string_error_values_table_low = tabulate(string_error_values_table_low, headers=['Timestamp','String', 'Values'], tablefmt='html')
                    html_content = html_content + string_error_values_table_low
        html_content = html_content + '<br><br> Thank You, <br> Team DataGlen'

        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=plant.slug,
                                                                  event=event,
                                                                  alert_active=True)
        if flag:
            create_string_anomaly_ticket(plant, high_ajbs, low_ajbs)
            for alert in active_alerts:
                print("inside for")
                email = alert.email_id
                phone = alert.phone_no
                try:
                    new_alert = AlertManagement(identifier=plant.slug,
                                                alert_time=current_time,
                                                event_time=current_time,
                                                event=event,
                                                email_id=email,
                                                phone_no=phone)

                    new_alert.save()
                except Exception as exception:
                    print("Error in saving alert: " + str(exception))

                try:
                    if email!='':
                        subject, from_email, to = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant.location) , FROM_EMAIL, email
                        text_content = ''
                        html_content = html_content
                        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                        msg.attach_alternative(html_content, "text/html")
                        msg.send()
                except Exception as exception:
                    print("Error in sending email" + str(exception))

    except Exception as exception:
        print(str(exception))

def create_string_anomaly_ticket(plant, high_ajbs, low_ajbs):
    try:
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            current_time = timezone.now()
        high_associations_dict = {}
        low_associations_dict = {}
        # create string high ticket
        for value in high_ajbs:
            source_key = str(value.identifier).split("_")[0]
            event_description = str(value.event_details)
            print("source_key" + source_key)
            try:
                ajb = AJB.objects.get(sourceKey=source_key)
            except:
                continue
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(ajb.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            high_associations_dict[ajb.sourceKey] = ['STRING_HIGH_ERROR', '-3', ajb.name, current_time, event_description]
        priority = 1
        due_date = current_time + datetime.timedelta(hours=2)
        print high_associations_dict
        if len(high_associations_dict) > 0:
            try:
                create_ticket(plant=plant, priority=priority, due_date=due_date,
                              ticket_name="STRING_HIGH_ERROR occurred for strings " + " at " + str(plant.location),
                              ticket_description = 'High string value anomaly occurred for strings at ' + str(plant.location),
                              associations_dict = high_associations_dict,
                              open_comment='Ticket created automatically based on the STRING_ERROR alert.')
            except Exception as exception:
                print("Error in creating ticket for plant : " + str(plant.slug) + " - " + str(exception))

        # create string low ticket
        for value in low_ajbs:
            source_key = str(value.identifier).split("_")[0]
            event_description = str(value.event_details)
            try:
                ajb = AJB.objects.get(sourceKey=source_key)
            except:
                continue
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(ajb.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            low_associations_dict[ajb.sourceKey] = ['STRING_LOW_ERROR', '-4', ajb.name, current_time, event_description]
        print low_associations_dict
        if len(low_associations_dict) > 0:
            try:
                create_ticket(plant=plant, priority=priority, due_date=due_date,
                              ticket_name="STRING_LOW_ERROR occurred for strings " + " at " + str(plant.location),
                              ticket_description = 'Low string value anomaly occurred for strings at ' + str(plant.location),
                              associations_dict = low_associations_dict,
                              open_comment='Ticket created automatically based on the STRING_ERROR alert.')
            except Exception as exception:
                print("Error in creating ticket for plant : " + str(plant.slug) + " - " + str(exception))
    except Exception as exception:
        print("Error in creating string anomaly ticket : " + str(exception))

'''
def sendStringErrorAlerts(plant, identifier, event_name, ajb , request_arrival_time, event_sources_high, event_sources_low, event_time, event_type):
    try:
        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=identifier,
                                                                  event=event,
                                                                  alert_active=True)
        string_error_values_table_high = []
        string_error_values_table_low = []
        html_content = 'Hi,<br> Following errors have occurred for SMB - ' + str(ajb.name) + ' at ' + str(plant.location) + ':<br><br>'
        if len(event_sources_high) > 0:
            html_content = html_content + '<b><u>'+str("STRING_ERROR_HIGH") + '</b></u>:<br>'
            for value in event_sources_high:
                string_error_values = []
                string_error_values.append(str(event_time))
                string_error_values.append(str(value.event_code))
                string_error_values.append(str(value.event_details))
                string_error_values_table_high.append(string_error_values)
            string_error_values_table_high = tabulate(string_error_values_table_high, headers=['Timestamp','String', 'Values'], tablefmt='html')
            html_content = html_content + string_error_values_table_high

        if len(event_sources_low) > 0:
            html_content = html_content + '<br><b><u>'+str("STRING_ERROR_LOW") + '</b></u>:<br>'
            for value in event_sources_low:
                string_error_values = []
                string_error_values.append(str(event_time))
                string_error_values.append(str(value.event_code))
                string_error_values.append(str(value.event_details))
                string_error_values_table_low.append(string_error_values)
            string_error_values_table_low = tabulate(string_error_values_table_low, headers=['Timestamp','String', 'Values'], tablefmt='html')
            html_content = html_content + string_error_values_table_low
        html_content = html_content + '<br><br> Thank You, <br> Team DataGlen'

        for alert in active_alerts:
            print("inside for")
            email = alert.email_id
            phone = alert.phone_no
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

            try:
                if email!='':
                    subject, from_email, to = '[' + str(event_type) + '] ' + EMAIL_TITLE + str(event_name) + ' at ' + str(plant.location) , FROM_EMAIL, email
                    text_content = ''
                    html_content = html_content
                    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
            except Exception as exception:
                print("Error in sending email" + str(exception))
    except Exception as exception:
        print(str(exception))'''
