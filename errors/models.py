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


class ErrorField(models.Model):
    # associated sensor
    source = models.ForeignKey(Sensor,
                               to_field='sourceKey',
                               related_name = "errorfields",
                               related_query_name="errorfield",
                               help_text="Key of the source this stream belongs to")

    # field name
    name = models.CharField(max_length=128, blank=False, help_text="Name of the error stream, should be unique for this source")
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

    # multiplication factor
    multiplicationFactor = models.FloatField(default=1.0, blank=False, help_text="Multiplication factor for this stream, applicable only for numerical streams. Defaults to one.")

    isActive = models.BooleanField(default=True, blank=False, help_text="If this data stream is active and accepting data.")

    type = models.CharField(max_length=10, blank=False, default='error')

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = (("source", "name"), ("source", "streamPositionInCSV"),)


# store action parameters by stream
class ErrorStorageByStream(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    stream_name = columns.Text(partition_key=True, primary_key=True)
    timestamp_in_data = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    stream_value = columns.Text()
    insertion_time = columns.DateTime()
    updated_time = columns.DateTime()
    raw_value = columns.Text()
    multiplication_factor = columns.Float()