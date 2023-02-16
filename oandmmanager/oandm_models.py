
from django.db import models
from solarrms.models import SolarPlant
from solarrms.models import IndependentInverter, AJB
from dataglen.models import Sensor
try:
    from django.utils import timezone
except ImportError:
    from datetime import datetime as timezone
from django.core.exceptions import ValidationError

TASK_FREQUENCY = [(1, 'DAILY'),
                  (7, 'WEEKLY'),
                  (30, 'MONTHLY'),
                  (15, 'TWICE A MONTH'),
                  (10,  'THRICE A MONTH'),
                  (4, 'BI-WEEKLY')]


COMPLETION_TRACKING = [('AJB', 'AJB'),
                       ('INVERTER', 'INVERTER'),
                       ('ENERGY METER', 'ENERGY_METER')]


TASK_STATUS = [('SCHEDULED', 'SCHEDULED'),
               ('OPEN', 'OPEN'),
               ('CLOSED', 'CLOSED'),
               ('LOCKED', 'LOCKED')]

DATES = [(x, str(x)) for x in range(31)]


class TasksList(models.Model):
    name = models.CharField(max_length=50, null=False, blank=False, primary_key=True)
    frequency = models.CharField(choices=TASK_FREQUENCY, max_length=50, null=False, blank=False, primary_key=True)
    associated_devices = models.CharField(choices=COMPLETION_TRACKING, max_length=50, null=False, blank=False, primary_key=True)


class OandMPrefrences(models.Model):
    plant = models.ForeignKey(SolarPlant,
                              related_name="o_and_m_preferences",
                              related_query_name="o_and_m_preferences")
    cycle_start_date = models.CharField(choices=DATES, max_length=2,
                                        null=False, blank=False)
    cycle_end_date = models.CharField(choices=DATES, max_length=2,
                                      null=False, blank=False)
    alert_date = models.CharField(choices=DATES, max_length=2,
                                  null=False, blank=False)
    associated_tasks = models.ManyToManyField(TasksList)


class TaskItem(models.Model):
    task = models.ForeignKey(TasksList, related_name="tasks", related_query_name="tasks")
    scheduled_start_date = models.DateTimeField(blank=False, null=False)
    scheduled_closing_date = models.DateTimeField(blank=False, null=False)
    status = models.CharField(choices=TASK_STATUS, max_length=20, blank=False, null=False)
    closed_at = models.DateTimeField(blank=False, null=False)
    last_updated = models.DateTimeField(blank=False, null=False)


class TaskAssociation(models.Model):
    task_item = models.ForeignKey(TasksList, related_name="associations", related_query_name="associations")
    sensor = models.ForeignKey(Sensor, related_name="task_associations",
                               related_query_name="task_associations")
    active = models.BinaryField(blank=False, null=False, default=False)
    opened_at = models.DateTimeField(blank=False, null=False)
    closed_at = models.DateTimeField(blank=False, null=False)

    def close(self, closed_at):
        if closed_at is None:
            closed_at = timezone.now()
        if self.task_item.status == "OPEN" and self.active is True:
            self.active = False
            self.closed_at = closed_at
        else:
            raise ValidationError("The task for this association has already been closed or locked, "
                                  "this association cannot be updated.")