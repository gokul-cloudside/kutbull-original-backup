import sys
import os
import django
import configparser
from django.utils import timezone
import datetime
import pytz
import requests
import json
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from solarrms.models import SolarPlant, IndependentInverter
from errors.models import ErrorStorageByStream, ErrorField
from dataglen.models import Sensor
from django.utils import timezone
import datetime

try:
    plant_read = SolarPlant.objects.filter(slug='ranergy')
    inverters = IndependentInverter.objects.filter(plant=plant_read)
    initial_time = timezone.now()
    start_time = initial_time - datetime.timedelta(days=2)
    end_time = initial_time + datetime.timedelta(days=800)
    print("started")
    for inverter in inverters:
        source_key = inverter.sourceKey
        source= Sensor.objects.filter(sourceKey=source_key)
        fields = ErrorField.objects.filter(source=source)
        for field in fields:
            records = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                          stream_name=field.name,
                                                          timestamp_in_data__gte=start_time,
                                                          timestamp_in_data__lte=end_time)
            print("no. of records ", str(len(records)))
            for record in records:
                new_record = ErrorStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                 stream_name=field.name,
                                                                 timestamp_in_data=record.timestamp_in_data)
                new_record.delete()
    print("completed")
except Exception as exception:
	print(str(exception))