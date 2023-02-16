from django.db import models
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model

# Create your models here.


class JPlug_Data_Table(Model):
    premise = columns.Text(max_length=100, primary_key=True, partition_key=True)
    load = columns.Text(max_length=100, primary_key=True, index=True,  partition_key=True)
    sample_time = columns.DateTime(primary_key=True, partition_key=False, index=True, clustering_order="desc")
    active = columns.Float(default=0)
    apparent = columns.Float(default=0)
    cost = columns.Float(default=0)
    current = columns.Float(default=0)
    energy = columns.Float(default=0)
    frequency = columns.Float(default=0)
    insertion_time = columns.DateTime()
    mac = columns.Text(max_length=17)
    angle = columns.Float(default=0)
    power_factor = columns.Float(default=0)
    reactive = columns.Float(default=0)
    voltage = columns.Float(default=0)


class JPlug_Status_Table(Model):
    premise = columns.Text(max_length=100, primary_key=True)
    load = columns.Text(max_length=100, primary_key=True, index=True)
    mac = columns.Text(max_length=17)
    is_monitoring = columns.Boolean(default=False)
    caretaker = columns.Text(max_length=100)
    email = columns.Text(max_length=200)
    phone = columns.Text(max_length=20)
    alarms = columns.Integer(default=0)
    sampling_interval = columns.Integer(default=0)


class JPlug_Energy_Data_Table(Model):
    premise = columns.Text(max_length=100, primary_key=True, partition_key=True)
    load = columns.Text(max_length=100, primary_key=True, partition_key=False, index=True)
    label_time = columns.DateTime(clustering_order='desc', index=True, primary_key=True, partition_key=False)
    computed_time = columns.DateTime()
    energy = columns.Float(default=0)


class JPlug_Hourly_Energy_Data_Table(Model):
    premise = columns.Text(max_length=100, primary_key=True, partition_key=True)
    load = columns.Text(max_length=100, primary_key=True, partition_key=True, index=True)
    label_time = columns.DateTime(clustering_order='desc', index=True, primary_key=True, partition_key=False)
    computed_time = columns.DateTime()
    energy = columns.Float(default=0)


class JPlug_Daily_Energy_Data_Table(Model):
    premise = columns.Text(max_length=100, primary_key=True, partition_key=True)
    load = columns.Text(max_length=100, primary_key=True, partition_key=True, index=True)
    label_time = columns.DateTime(clustering_order='desc', index=True, primary_key=True, partition_key=False)
    computed_time = columns.DateTime()
    energy = columns.Float(default=0)

