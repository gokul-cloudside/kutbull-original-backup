from django.db import models
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from dataglen.models import Sensor


class EventsByTime(Model):
    identifier = columns.Text(partition_key=True, primary_key=True)
    # time at which event was logged into table.
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # type of event occurred(network error/inverter off etc.)
    event_name = columns.Text(partition_key=False, primary_key=True)
    #code of the event
    event_code = columns.Text(partition_key=False, primary_key=True, default='-1')
    # time at which event occurred.
    event_time = columns.DateTime()
    #event_details
    event_details = columns.Text(partition_key=False, primary_key=False)

class EventsConfig(models.Model):
    source_key = models.ForeignKey(Sensor,
                               related_name = "eventsConfig",
                               related_query_name="eventsConfig",
                               to_field='sourceKey',
                               help_text="The source key of the source")
    stream_name = models.CharField(max_length=128, blank=False, help_text="The stream name (or ALL) for which the event needs to be configured")
    condition_type = models.CharField(max_length=128, blank=False, help_text="The condition_type for this event. It could be NO_DATA, DATA_STARTED etc.")
    condition_operator = models.CharField(max_length=30, blank=False, help_text="Operator on the stream condition. It would be ? when not applicable.")
    condition_value = models.CharField(max_length=128, blank=False, help_text="Value of the condition that need to be checked. It could be an absolute value or AVG, SUM, 2SD etc.")
    event_type = models.CharField(max_length=128, blank=False, help_text="The type of the event that should be raised. It could be NETWORK_DOWN etc.")

    def __unicode__(self):
        return "_".join([self.source_key.sourceKey , self.stream_name , self.condition_type , self.condition_operator , self.condition_value])

    class Meta:
        unique_together = (("source_key", "stream_name", "condition_type","condition_operator","condition_value" ),)



class EventsByError(Model):
    identifier = columns.Text(partition_key=True, primary_key=True)
    # type of event occurred(network error/inverter off etc.)
    event_name = columns.Text(partition_key=True, primary_key=True)
    # time at which event was logged into table.
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    #code of the event
    event_code = columns.Text(partition_key=False, primary_key=True, default='-1')
    # time at which event occurred.
    event_time = columns.DateTime()
    #event_details
    event_details = columns.Text(partition_key=False, primary_key=False)

class Events(models.Model):
    # name of the event
    event_name = models.CharField(max_length=128, blank=False, help_text="The name of the event, should be unique")
    # category of the event(Gateway/Data Driven)
    # TODO must be a choice field, and list down the categories we accept events for
    event_category = models.CharField(max_length=128, blank=False, help_text="The source of the event generation, "
                                                                             "such as data, gateway etc.")
    # Entity to which the event is applicable to(Plant/Inverter/Source)
    # TODO should it a choice field, and list down the options that are valid and we accept the events for
    applicable_to = models.CharField(max_length=128, blank=True, help_text="The entity to which this event is "
                                                                           "applicable, such as Inverter, "
                                                                           "Source, SolarPlant etc.")

    description = models.CharField(max_length=200, blank=False)

    def __unicode__(self):
        return self.event_name

    class Meta:
        unique_together = (("event_name", "event_category", "applicable_to"),)


class UserEventAlertsPreferences(models.Model):
    event = models.ForeignKey(Events, related_name='preferences', related_query_name='preference',
                              help_text="An event with which the alert preference is related with.")
    identifier = models.CharField(max_length=128, blank=False,
                                  help_text="Unique identifier of the entity (sourceKey, plant_slug)")
    alert_active = models.BooleanField(default=False, blank=False,
                                       help_text="Alerts for this event will be sent if this parameter is selected.")
    email_id = models.EmailField(max_length=128, blank=True,
                                 help_text="Email address to which alerts will be sent")
    phone_no = models.CharField(max_length=13, blank=True, default='',
                                help_text="Phone number to which alerts will be sent")
    alert_interval = models.IntegerField(blank=False, default = 180,
                                         help_text="Time interval after which the alert should be sent again.")

    def __unicode__(self):
        return "_".join([self.identifier , self.event.event_name , self.email_id, self.phone_no])

    class Meta:
        unique_together = (("event", "identifier",
                            "email_id", "phone_no"),)


class AlertManagement(models.Model):
    event = models.ForeignKey(Events, related_name='alerts',
                                      related_query_name='alert',
                                      help_text="The event for which the alert will be sent")
    identifier = models.CharField(max_length=128, blank=False,
                                  help_text="The unique identifier of the entity (plant_slug, sourceKey etc.)")
    alert_time = models.DateTimeField(max_length=128, blank=False,
                                      help_text="The time at which the alert was sent")
    event_time = models.DateTimeField(max_length=128, blank=False, help_text="The time at which event occurred")
    email_id = models.EmailField(max_length=128, blank=True, help_text="An Email address to which the alert will be sent")
    phone_no = models.CharField(max_length=13, blank=True,
                                help_text="Phone number to which alerts will be sent")
    event_code = models.CharField(max_length=100, blank=False,default="-1", help_text="Code of the event occurred.")
    def __unicode__(self):
        return self.identifier

    class Meta:
        unique_together = (("identifier", "alert_time","email_id","event_code"),)


class EventsByTimeTemp(Model):
    identifier = columns.Text(partition_key=True, primary_key=True)
    # time at which event was logged into table.
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # type of event occurred(network error/inverter off etc.)
    event_name = columns.Text(partition_key=False, primary_key=True)
    # time at which event occurred.
    event_time = columns.DateTime()

class EventsByErrorTemp(Model):
    identifier = columns.Text(partition_key=True, primary_key=True)
    # type of event occurred(network error/inverter off etc.)
    event_name = columns.Text(partition_key=True, primary_key=True)
    # time at which event was logged into table.
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    #code of the event
    event_time = columns.DateTime()