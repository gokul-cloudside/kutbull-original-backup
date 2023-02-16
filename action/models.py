from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.core.urlresolvers import reverse

from dataglen.models import Sensor, Field


# Create your models here.

# store action parameters by stream
class ActionsStorageByStream(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    acknowledgement = columns.Integer(partition_key=True, primary_key=True,default=0)
    stream_name = columns.Text(partition_key=False, primary_key=True)
    stream_value = columns.Text()
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    comments = columns.Text()


class ActionField(models.Model):
    # associated sensor
    source = models.ForeignKey(Sensor,
                               to_field='sourceKey',
                               related_name = "actionfields",
                               related_query_name="actionfield",
                               help_text="Key of the source this stream belongs to")

    # field name
    name = models.CharField(max_length=128, blank=False, help_text="Name of the data stream, should be unique for this source")
    # field type TODO extend the support of other data types later. Allow nested fields also?
    streamDataType = models.CharField(max_length=20, choices=settings.DATAGLEN['DATA_TYPES'],
                                      blank=False,
                                      help_text="Type of the data this stream reports")

    streamDateTimeFormat = models.CharField(max_length=20,
                                            blank=True,
                                            help_text="DateTime field values should be reported in ISO 8601 formats. You can specify custom formats here.")

    # field position in the sensor
    streamPositionInCSV = models.IntegerField(null=True,
                                              blank=True,
                                              help_text="Applicable only if source dataFormat is CSV, should be unique")
    # data units
    streamDataUnit = models.CharField(max_length=20, null=True, blank=True, help_text="Data Unit")
    # Date format, needed for Timestamp values
    type = models.CharField(max_length=10, blank=False, default='action')

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = (("source", "name"), ("source", "streamPositionInCSV"),)


# class ConfigField(Field):
