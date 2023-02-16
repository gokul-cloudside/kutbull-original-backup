
from django.db import models
from solarrms.models import SolarPlant
from dataglen.models import Sensor
from django.contrib.auth.models import User
try:
    from django.utils import timezone
except ImportError:
    from datetime import datetime as timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
import collections


TASK_FREQUENCY = [('1', 'DAILY'),
                  ('7', 'WEEKLY'),
                  ('30', 'MONTHLY')]

TASK_RECURRING = [('1', '1'),
                  ('2', '2'),
                  ('3', '3')]

TASK_TIME = [(str(i), str(i)) for i in range(6, 20)]

COMPLETION_TRACKING = [('AJB', 'AJB'),
                       ('INVERTER', 'INVERTER'),
                       ('ENERGY METER', 'ENERGY_METER'),
                       ('DATA_LOGGER', 'DATA_LOGGER'),
                       ('PLANT', 'PLANT'),
                       ('ALL', 'ALL')]

# (name, frequency, recurring, time, associated_devices)
TASKS_LIST = [""]

TASK_STATUS = [('SCHEDULED', 'SCHEDULED'),
               ('RESCHEDULED', 'RESCHEDULED'),
               ('OPEN', 'OPEN'),
               ('CLOSED', 'CLOSED'),
               ('LOCKED', 'LOCKED')]

DATES = [(str(x), str(x)) for x in range(31)]


class Tasks(models.Model):
    name = models.CharField(max_length=500, null=False, blank=False)
    frequency = models.CharField(choices=TASK_FREQUENCY, max_length=50, null=False, blank=False)
    recurring = models.CharField(choices=TASK_RECURRING, max_length=50, null=False, blank=False)
    time = models.CharField(choices=TASK_TIME, max_length=50, null=False, blank=False)
    associated_devices = models.CharField(choices=COMPLETION_TRACKING, max_length=50, null=False, blank=False)

    @staticmethod
    def serialize():
        tasks = collections.OrderedDict()
        for task in Tasks.objects.all().order_by('id'):
            if task.name not in tasks.keys():
                tasks[task.name] = {"frequency": [], "recurring": [], "time": [], "enabled": False, "id":task.id}
            if task.frequency not in tasks[task.name]["frequency"]:
                tasks[task.name]["frequency"].append(task.frequency)
            if task.recurring not in tasks[task.name]["recurring"]:
                tasks[task.name]["recurring"].append(task.recurring)
            if task.time not in tasks[task.name]["time"]:
                tasks[task.name]["time"].append(task.time)

        return tasks

    @staticmethod
    def validate(preferences):
        tasks = []
        for task in preferences.keys():
            task_name = task
            enabled_frequency = preferences[task]["enabled_frequency"]
            enabled_recurring = preferences[task]["enabled_recurring"]
            enabled_time = preferences[task]["enabled_time"]
            try:
                t = Tasks.objects.get(name=task_name, frequency=enabled_frequency,
                                      recurring=enabled_recurring, time=enabled_time)
                tasks.append(t)
            except Tasks.DoesNotExist:
                raise ValidationError("No such combination of task is allowed: " + ":".join([task_name,
                                                                                             enabled_frequency,
                                                                                             enabled_recurring,
                                                                                             enabled_time]))
        return tasks

    def __unicode__(self):
        return ",".join([str(self.name), str(self.frequency), str(self.recurring), str(self.time)])

    class Meta:
        unique_together=(("name", "frequency", "recurring", "time", "associated_devices"))


class Preferences(models.Model):
    plant = models.ForeignKey(SolarPlant,
                              related_name="o_and_m_preferences",
                              related_query_name="o_and_m_preferences")
    ed = models.CharField(choices=DATES, max_length=2,
                                           null=False, blank=False, default='30')
    sd = models.CharField(choices=DATES, max_length=2,
                                           null=False, blank=False, default='1')
    alert_date = models.CharField(choices=DATES, max_length=2,
                                  null=False, blank=False, default='22')
    associated_tasks = models.ManyToManyField(Tasks)

    def __unicode__(self):
        return self.plant.name

    def serialize(self):
        tasks = Tasks.serialize()
        try:
            for task in self.associated_tasks.all():
                tasks[task.name]["enabled"] = True
                tasks[task.name]["enabled_frequency"] = task.frequency
                tasks[task.name]["enabled_recurring"] = task.recurring
                tasks[task.name]["enabled_time"] = task.time
                tasks[task.name]["id"] = task.id
            return tasks
        except Exception as exc:
            return {}

    # {"task_name": {"enabled_frequency": "", "enabled_recurring": "", "enabled_time": ""}
    def update(self, preferences):
        try:
            validated_tasks = Tasks.validate(preferences)
        except ValidationError as exc:
            raise ValidationError(str(exc))

        if validated_tasks:
            # drop all existing associated_tasks
            for t in self.associated_tasks.all():
                self.associated_tasks.remove(t)
            # add new tasks
            for t in validated_tasks:
                self.associated_tasks.add(t)


class Cycle(models.Model):
    preferences = models.ForeignKey(Preferences,
                                    related_name="o_and_m_cycles",
                                    related_query_name="o_and_m_cycles")
    start_date = models.DateTimeField(null=False, blank=False)
    end_date = models.DateTimeField(null=False, blank=False)
    alert_date = models.DateTimeField(null=True, blank=True)
    isActive = models.BooleanField(default=False)

    class Meta:
        unique_together=(("preferences", "start_date", "end_date"))

    def __unicode__(self):
        return self.preferences.plant.name + "_" + \
               str(self.start_date)

    def update_status(self):
        current_time = timezone.now()
        for task in self.tasks.all():
            task.update_status(current_time)

    def tasks_summary(self):
        preferences = self.preferences.serialize()
        for task_name in preferences.keys():
            try:
                if preferences[task_name]["enabled"] is False:
                    preferences.pop(task_name)
                else:
                    preferences[task_name]["completed_tasks"] = 0
                    preferences[task_name]["pending_tasks"] = 0
                    preferences[task_name]["task_range"] = "No summary on tasks"
                    open_task = self.tasks.get(task=Tasks.objects.get(name=task_name,
                                                                      frequency=preferences[task_name]["enabled_frequency"],
                                                                      recurring=preferences[task_name]["enabled_recurring"],
                                                                      time=preferences[task_name]["enabled_time"]), status="OPEN")
                    id, completed, pending, open_date, closing_date, \
                    status, time, task_range, assigned_to = open_task.completion_summary()
                    preferences[task_name]["completed_tasks"] = completed
                    preferences[task_name]["pending_tasks"] = pending
                    preferences[task_name]["task_range"] = task_range
            except:
                continue
        return preferences

    def completion_summary(self, task_name):
        summary = collections.OrderedDict()

        for t in TASK_TIME:
            summary[t[0]] = collections.OrderedDict()

        for task in self.tasks.filter(task__in=Tasks.objects.filter(name=task_name)):
            task_summary = task.completion_summary()
            if task_summary is not None:
                id, completed, pending, open_date, closing_date, status, time, task_range, assigned_to = task_summary
                # check if we've a key for this time and task range
                if task_range not in summary[time].keys():
                    summary[time][task_range] = []

                # append this task
                summary[time][task_range].append({"time": time,
                                                  "completed_tasks": completed,
                                                  "pending_tasks": pending,
                                                  "open_date": open_date,
                                                  "closing_date": closing_date,
                                                  "scheduled": task_range,
                                                  "status": status,
                                                  "assigned_to": assigned_to.first_name,
                                                  "id": id})
        tableData = []
        headers_keys = collections.OrderedDict()
        headers = [{"key": "time", "header": ""}]
        for time in summary.keys():
            info = {"time": time}
            for task_range in summary[time].keys():
                info[task_range] = summary[time][task_range]
                if task_range not in headers_keys.keys():
                    headers_keys[task_range] = {}
                    headers.append({"header": task_range, "key": task_range})
            tableData.append(info)

        return tableData, headers


class TaskItem(models.Model):
    cycle = models.ForeignKey(Cycle, related_name="cycles", related_query_name="cycles")
    task = models.ForeignKey(Tasks, related_name="tasks", related_query_name="tasks")
    title = models.TextField(max_length=500, null=True, blank=True)
    scheduled_start_date = models.DateTimeField(blank=False, null=False)
    scheduled_closing_date = models.DateTimeField(blank=False, null=False)
    assigned_to = models.ForeignKey(User, related_name="users", related_query_name="users")
    status = models.CharField(choices=TASK_STATUS, max_length=20, blank=False, null=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(blank=True, null=True)
    time = models.CharField(choices=TASK_TIME, max_length=50, null=False, blank=False)
    is_custom = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together=(("cycle", "task", "scheduled_start_date", "scheduled_closing_date"))

    def __unicode__(self):
        return ",".join([self.task.name, str(self.scheduled_start_date), str(self.status)])

    def save(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        if not self.is_custom:
            self.title = self.task.name
            self.description = self.task.name
        super(TaskItem, self).save(*args, **kwargs)

    def associations_summary(self):
        data = collections.OrderedDict()
        for task_association in self.task_associations.all():
            data[task_association.sensor.name] = task_association.serialize()
        return data

    def update_status(self, current_time):
        if self.status == "SCHEDULED" and current_time.date() == self.scheduled_start_date:
            self.status = "OPEN"
            self.save()
        elif self.status == "OPEN" and current_time.date() == self.scheduled_closing_date:
            self.status = "LOCKED"
            self.save()

    def task_range(self):
        try:
            return self.scheduled_start_date.strftime("%b %d") + "-" + \
                   str(self.scheduled_closing_date.day) + ", " + str(self.scheduled_start_date.year)
        except:
            raise ValidationError("something wrong with the task")

    def close_association(self, task_association_id):
        try:
            assert(self.scheduled_start_date <= timezone.now() <= self.scheduled_closing_date and self.status == "OPEN")
            association = self.task_associations.get(id=task_association_id)
            association.close()
            if self.open_associations() == 0:
                self.status = 'CLOSED'
                self.closed_at = timezone.now()
                self.save()
            return True
        except AssertionError:
            raise ValidationError("This task cannot be marked completed at this point.")
        except Sensor.DoesNotExist:
            raise ValidationError("This sensor does not exist")
        except ValidationError as exc:
            raise ValidationError(str(exc))
        except:
            return False

    def completion_summary(self):
        completed = len(self.task_associations.filter(active=False))
        pending = len(self.task_associations.filter(active=True))
        try:
            return self.id, completed, pending, str(self.scheduled_start_date), str(self.scheduled_closing_date), \
                   self.status, self.time, self.task_range(), self.assigned_to
        except:
            return None

    def open_associations(self):
        return len(self.task_associations.filter(active=True))


class TaskAssociation(models.Model):
    task_item = models.ForeignKey(TaskItem, related_name="task_associations", related_query_name="task_associations")
    sensor = models.ForeignKey(Sensor, related_name="sensors", related_query_name="sensors")
    active = models.BinaryField(blank=False, null=False, default=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    def serialize(self):
        return {"device": self.sensor.name, "active": str(self.active), "id": self.id,
                "opened_at": str(self.opened_at), "closed_at": str(self.closed_at), "sensor_key": self.sensor.sourceKey}

    def close(self, closed_at=None):
        if closed_at is None:
            closed_at = timezone.now()
        if self.task_item.status == "OPEN" and bool(self.active) is True:
            self.active = False
            self.closed_at = closed_at
            self.save()
        else:
            raise ValidationError("The task for this association has already been closed or locked, "
                                  "this association cannot be updated.")

    def __unicode__(self):
        return "_".join([self.sensor.name, str(self.opened_at), str(self.active), self.task_item.__unicode__()])

