from events.models import EventsByTime, EventsConfig, EventsByError, Events, UserEventAlertsPreferences, AlertManagement
from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource
from dataglen.models import ValidDataStorageByStream, Sensor
import datetime
from django.core.exceptions import ObjectDoesNotExist
import pytz
from monitoring.models import SourceMonitoring
from cassandra.cqlengine.query import BatchQuery
from django.core.mail import send_mail

def events_write(request_arrival_time, identifier , event_name):
    try:
        print("inside events write")
        batch_query = BatchQuery()
        EventsByTime.batch(batch_query).create(identifier=identifier,
                                               insertion_time=request_arrival_time,
                                               event_name=event_name,
                                               event_time=request_arrival_time)

        EventsByError.batch(batch_query).create(identifier=identifier,
                                                event_name=event_name,
                                                insertion_time=request_arrival_time,
                                                event_time=request_arrival_time)

        batch_query.execute()
        sendAlerts(identifier, request_arrival_time, event_name, request_arrival_time)

    except Exception as exception:
        print(str(exception))

def sendAlerts(identifier,
               request_arrival_time,
               event_name, event_time):
    try:
        event = Events.objects.get(event_name=event_name)
        active_alerts = UserEventAlertsPreferences.objects.filter(identifier=identifier,
                                                                  event=event,
                                                                  alert_active=True)

        for alert in active_alerts:
            print("inside for")
            email = alert.email_id
            alert_interval = alert.alert_interval
            last_alert_time = AlertManagement.objects.filter(identifier=identifier,
                                                             event=event,
                                                             email_id=email).order_by("-alert_time")
            if len(last_alert_time) > 0:
                if last_alert_time[0].alert_time + datetime.timedelta(minutes=alert_interval) < request_arrival_time:
                    print("inside if")
                    try:
                        new_alert = AlertManagement(identifier=identifier,
                                                    alert_time=request_arrival_time,
                                                    event_time=event_time,
                                                    event=event,
                                                    email_id=email)
                        new_alert.save()

                        send_mail(event_name + ' event occurred on dataglen.com for source ' + identifier,
                                  event.description, 'admin@dataglen.com',
                                  [email], fail_silently=False)
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
                                                email_id=email)
                    new_alert.save()
                    try:
                        send_mail(event_name + ' event occurred on dataglen.com for source ' + identifier,
                                event.description, 'admin@dataglen.com',
                                [email], fail_silently=False)
                    except:
                        print("Error in sending email")
                except Exception as exception:
                    print("Error in saving new alerts" + str(exception))
    except Exception as exception:
        print(str(exception))


def events_check():
    print("Events cron job started - %s",datetime.datetime.now())

    try:
        # Get the source keys from EventsConfig table on which events check should be done.
        event_sources = EventsConfig.objects.all()
        if(len(event_sources)==0):
            print("No source found in the config table")

        # Iterate for all the sources found in the config table
        for event_source in event_sources:
            # Get the current time
            current_time = datetime.datetime.now()
            try:
                sensor = Sensor.objects.get(sourceKey=event_source.source_key.sourceKey)
            except Sensor.DoesNotExist:
                print("Sensor not found")

            # Get the current time in required format for source.
            try:
                tz = pytz.timezone(sensor.dataTimezone)
            except:
                print("error in converting current time to source timezone")
            if current_time.tzinfo is None:
                current_time = tz.localize(current_time)

            # get a time 5 minutes before the current time
            initial_time = current_time - datetime.timedelta(minutes=5)

            # Check if the data is present for the source in last 5 minutes
            event_source_data = SourceMonitoring.objects.filter(source_key=event_source.source_key.sourceKey)

            if (len(event_source_data)>0):
                # Data is coming
                if (str(event_source.condition_type) == 'DATA_STARTED'):
                    event_type = str(event_source.event_type)

                    # Check for the last entry made in the EventsByTime table
                    events_entry = EventsByTime.objects.filter(identifier=event_source.source_key.sourceKey).limit(1).values_list('insertion_time')
                    
                    if (len(events_entry) > 0):
                        #if the last entry was for DATA_STARTED
                        if (str(events_entry[0].event_name) == 'NETWORK_UP'):
                            # No need to log an event
                            pass
                        else:
                            # Log an event for above event_type
                            events_write(current_time, event_source.source_key.sourceKey, event_source.event_type)
                            print(event_type + " event logged for: " + str(event_source.source_key.sourceKey))
                else:
                    pass                
            else:
                #Data is not coming
                if (str(event_source.condition_type) == 'NO_DATA'):
                    event_type = str(event_source.event_type)
                    #Log an event for above event_type
                    events_write(current_time, event_source.source_key.sourceKey, event_source.event_type)
                    print(event_type + " event logged for: " + str(event_source.source_key.sourceKey))
                else:
                    pass

    except Exception as exception:
    	print(str(exception))
