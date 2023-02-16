from django.db import models
from solarrms.models import SolarPlant, SolarGroup
from dataglen.models import Sensor

TICKETS_STATUS = [('OPEN','OPEN'),
                  ('CLOSED','CLOSED'),
                  ('ACKNOWLEDGED','ACKNOWLEDGED'),
                  ('RESOLVED','RESOLVED')]

EVENT_TYPE = [('POWER_OFF', 'POWER_OFF'),
              ('GATEWAY_DISCONNECTED', 'GATEWAY_DISCONNECTED'),
              ('INVERTERS_DISCONNECTED', 'INVERTERS_DISCONNECTED'),
              ('AJBS_DISCONNECTED', 'AJBS_DISCONNECTED'),
              ('INVERTERS_NOT_GENERATING', 'INVERTERS_NOT_GENERATING'),
              ('INVERTERS_ALARMS', 'INVERTERS_ALARMS'),
              ('AJB_STRING_CURRENT_ZERO_ALARM', 'AJB_STRING_CURRENT_ZERO_ALARM')]

PRIORITY = [('CRITICAL','CRITICAL'),
            ('HIGH','HIGH'),
            ('LOW', 'LOW'),
            ('NORMAL', 'NORMAL'),
            ('UNKNOWN', 'UNKNOWN')]

DEVICE_TYPE = [('INVERTER', 'INVERTER'),
               ('AJB' ,'AJB'),
               ('ENERGY_METER', 'ENERGY_METER')]

ENERGY_LOSS_CAUSE = [('GRID_NOT_AVAILABLE','GRID_UNAVAILABILITY'),
                     ('INVERTERS_NOT_GENERATING', 'INVERTERS_NOT_GENERATING'),
                     ('INVERTERS_INTERNAL_ALARMS', 'INVERTERS_INTERNAL_ALARMS'),
                     ('SOILING_LOSS','SOILING_LOSS'),
                     ('INVERTER_UNDERPERFORMING','INVERTER_UNDERPERFORMING'),
                     ('STRING_UNDERPERFORMING', 'STRING_UNDERPERFORMING')]


class Ticket(models.Model):
    plant = models.ForeignKey(SolarPlant,
                              related_name="tickets",
                              related_query_name="ticket",
                              to_field='slug',
                              help_text="Tickets associated with a plant")
    group = models.ForeignKey(SolarGroup, blank=True, null=True)
    created = models.DateTimeField(blank=False, null=False)
    associated_devices = models.ManyToManyField(Sensor, to='sourceKey', related_name="tickets")
    title = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=300, blank=False, null=False)
    status = models.CharField(choices=TICKETS_STATUS, max_length=50, blank=False, null=False)
    last_updated = models.DateTimeField(blank=False, null=False)
    closed = models.DateTimeField(blank=False, null=False)
    priority = models.CharField(choices=PRIORITY, max_length=50, blank=False, null=False)
    event_type = models.CharField(choices=EVENT_TYPE, max_length=50, blank=False, null=False)
    energy_loss = models.FloatField(blank=False, null=False)
    energy_loss_cause = models.CharField(choices=ENERGY_LOSS_CAUSE, max_length=50, blank=False, null=False)


class DeviceImpacted(models.Model):
    ticket = models.ForeignKey(Ticket,
                               related_name="associations",
                               related_query_name="associate",
                               to_field="title")
    identifier = models.CharField(max_length=50, blank=False, null=False)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE, blank=False, null=False)
    # stream name to store further details
    stream_name = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=300, blank=False, null=False)
    active = models.BooleanField(default=True, blank=False, null=False)
    created = models.DateTimeField(blank=False, null=False)
    closed = models.DateTimeField(blank=False, null=False)
    event_type = models.CharField(choices=EVENT_TYPE, max_length=50, blank=False, null=False)
    energy_loss = models.FloatField(blank=False, null=False)
    energy_loss_cause = models.CharField(choices=ENERGY_LOSS_CAUSE, max_length=50, blank=False, null=False)

'''def Q(plant, st, et, <ENERGY_LOSS_CAUSE>)
def Q(plant, inverters_down, ticket_status)

Tickets flow
Event triggering on close

class TicketHistory(models.Model):'''



