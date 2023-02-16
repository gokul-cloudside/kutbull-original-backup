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
import pytz
from django.utils import timezone
MAC_REGEX_PATTERN = "[0-9a-fA-F]{2}([-:])[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$"

class Sensor(models.Model):
    # user associated with this sensor
    user = models.ForeignKey(User, related_name = "data_source", related_query_name="data_source")
    # name of the sensor (this with user name must be unique)
    name = models.CharField(max_length=128, blank=False, help_text="Name of the source, it should be unique")
    # name of the sensor (this with user name must be unique)
    UID = models.CharField(max_length=128, blank=True, default=None, null=True, help_text="If UID is specified, it should be unique across the entire platform.")
    # reporting time interval
    dataReportingInterval = models.IntegerField(blank=True, null=True, help_text="Data reporting interval (in seconds)")
    # data format the sensor uses
    dataFormat = models.CharField(max_length=10,
                                  choices=settings.DATAGLEN['DATA_FORMATS'],
                                  blank=False, help_text="The format in which this source sends data records")
    # sensor active
    isActive = models.BooleanField(default=False, blank=False, help_text="Data will be accepted only if this parameter is True")
    # monitoring enabled
    isMonitored = models.BooleanField(default=False, blank=False, help_text="This source will be monitored only if this parameter is True")
    # second after which the sensor is declared "disconnected"
    timeoutInterval = models.IntegerField(default=2700, blank=False, help_text="If there is no data for these many seconds, a notification will be raised")
    # timezone
    dataTimezone = models.CharField(max_length=100,
                                    choices=settings.TIMEZONE_CHOICES,
                                    default='Asia/Kolkata', blank=False, help_text="Source timezone")

    # optional fields

    # sensor mac address, regex validator
    sourceMacAddress = models.CharField(max_length=17, validators=[RegexValidator(regex=MAC_REGEX_PATTERN)],
                                        blank=True, null=True, help_text="Source hardware identifier")
    # sensor key # TODO blank=True has been done for DRF. Update it.
    sourceKey = models.CharField(unique=True, max_length=43,
                                 blank=True, help_text="Unique sensor key, a read only field",
                                 db_index=True)
    # return message with a 200 OK
    textMessageWithHTTP200 = models.TextField(default=None, blank=True, null=True, help_text="Text message to be accompanied with HTTP 200 OK")
    # failed message with 400
    textMessageWithError = models.TextField(default=None, blank=True, null=True, help_text="Text message to be accompanied with an error")
    # data key name
    csvDataKeyName = models.CharField(max_length=128, default=None, blank=True, null=True, help_text="Key name that holds comma separated data (applicable only if source dataFormat is CSV)")

    # if it's a template. templates can't store data
    isTemplate = models.BooleanField(blank=False, default=False)
    # template name
    templateName = models.CharField(max_length=128, default=False, blank=False, null=False)
    # if the actuation is enabled on this sensor
    actuationEnabled = models.BooleanField(blank=False, default=False, help_text="If this source has actuation features enabled. Keep it unchecked if unsure.")

    # owner details
    manager_email = models.EmailField(blank=True, help_text="Email address of the person who manages this source")
    manager_name = models.CharField(blank=True, max_length=128, help_text="Name of the person who manages this source")
    manager_phone = models.CharField(blank=True, max_length=15, help_text="Phone number of the person who manages this source")
    def __unicode__(self):
        return self.name + "_" + self.sourceKey

    def save(self, *args, **kwargs):
        if self.pk:
            super(Sensor, self).save(*args, **kwargs)
        else:
            # generate the key
            # It needs to be imported here, otherwise creates a circular error!
            from dataglen.misc import generate_hash_key
            self.sourceKey = generate_hash_key()
            super(Sensor, self).save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse('dataglen:source-detail', kwargs={'source_key': self.sourceKey})

    def get_last_write_ts(self, field_names=None, first_ts=False):
        latest_ts = None
        if field_names is None:
            active_fields = self.fields.filter(isActive=True)
        else:
            active_fields = self.fields.filter(isActive=True, name__in=field_names)

        for field in active_fields:
            if first_ts:
                data_point = ValidDataStorageByStream.objects.filter(source_key = self.sourceKey,
                                                                     stream_name = field.name).limit(96*7).values_list('timestamp_in_data', flat=True).order_by('timestamp_in_data')
                if len(data_point) > 0 and (latest_ts is None or latest_ts > data_point[-1]):
                    latest_ts = data_point[-1]

            else:
                data_point = ValidDataStorageByStream.objects.filter(source_key = self.sourceKey,
                                                                     stream_name = field.name).limit(1).values_list('timestamp_in_data', flat=True).order_by('-timestamp_in_data')
                if len(data_point) > 0 and (latest_ts is None or latest_ts < data_point[-1]):
                    latest_ts = data_point[-1]
        if latest_ts:
            return latest_ts.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(self.dataTimezone))
        else:
            return None

    class Meta:
        order_with_respect_to = 'user'
        #unique_together=(("user", "name"), )


class Field(models.Model):
    # associated sensor
    source = models.ForeignKey(Sensor,
                               related_name = "fields",
                               related_query_name="field",
                               to_field='sourceKey',
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

    # multiplication factor
    multiplicationFactor = models.FloatField(default=1.0, blank=False, help_text="Multiplication factor for this stream, applicable only for numerical streams. Defaults to one.")
    # Date format, needed for Timestamp values

    isActive = models.BooleanField(default=True, blank=False, help_text="If this data stream is active and accepting data.")

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = (("source", "name"), ("source", "streamPositionInCSV"),)


# store valid data points by stream
class ValidDataStorageByStream(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    stream_name = columns.Text(partition_key=True, primary_key=True)
    timestamp_in_data = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    stream_value = columns.Text()
    insertion_time = columns.DateTime()
    raw_value = columns.Text()
    multiplication_factor = columns.Float()


# store invalid data by source
class InvalidDataStorageBySource(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    data = columns.Text()
    error = columns.Text(index=True)
    comments = columns.Map(columns.Text, columns.Text)

# create Django Rest Framework tokens
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

class SensorGroup(models.Model):
    slug = models.SlugField(max_length=50)
    name = models.CharField(max_length=128, blank=False)
    user = models.ForeignKey(User, related_name = "group_data_source", related_query_name="group_data_source")
    groupSensors = models.ManyToManyField(Sensor, blank=True, null=True, related_name="sensor_groups")
    displayName = models.CharField(max_length=128, blank=False)
    isActive = models.BooleanField(default=False, blank=False)
    def get_sensors(self):
        return self.groupSensors.all()

    def __unicode__(self):
        return "_".join([self.name, str(self.user.username)])

