import sys
import os
import django
import configparser
from django.utils import timezone
import datetime
import pytz
import requests
import json
#sys.path.append("/Dataglen/template-integration/kutbill-django")
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from django.db import IntegrityError
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from dataglen.models import ValidDataStorageByStream,Field, Sensor
from dashboards.models import DataglenClient
from dashboards.models import Dashboard
from organizations.models import OrganizationOwner
from organizations.models import OrganizationUser
from solarrms.models import SolarPlant, IndependentInverter, GatewaySource, PlantMetaSource
from django.core.mail import send_mail
from client_creation_script import create_dataglen_client
from rest_framework.authtoken.models import Token

#CONFIG_FILE = "plant_creation.cfg"

plant_read = SolarPlant.objects.filter(slug='ranergy')
inverters = IndependentInverter.objects.filter(plant=plant_read)
current_time = timezone.now()
initial_time = current_time.replace(hour=0,minute=30,second=0,microsecond=0)#start time UTC 0:30
#initial_time = initial_time + datetime.timedelta(hours=-5)
end_time = current_time.replace(hour=1,minute=0,second=0,microsecond=0)#nd time UTC 1:00
#end_time = end_time + datetime.timedelta(hours=-5)
print("initial time: ", initial_time)
print("end time", end_time)
'''
for inverter in inverters:
        source_key = inverter.sourceKey
        source= Sensor.objects.filter(sourceKey=source_key)
        fields = Field.objects.filter(source=source)
        print("for inverter: ", source_key)
        for field in fields:
            print("for field: ", field.name)
            records = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                              stream_name=field.name,
                                                              timestamp_in_data__gte=initial_time,
                                                              timestamp_in_data__lte=end_time)
            print("no. of records ", str(len(records)))
            for record in records:
                new_record = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                              stream_name=field.name,
                                                                    timestamp_in_data=record.timestamp_in_data)
                new_record.delete()
            records = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                              stream_name=field.name,
                                                              timestamp_in_data__gte=initial_time,
                                                              timestamp_in_data__lte=end_time)
            print("AFTER no. of records ", str(len(records)))
'''
