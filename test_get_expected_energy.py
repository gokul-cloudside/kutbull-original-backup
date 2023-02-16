#!/usr/bin/python

import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()

from dataglen.models import Sensor, Field
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from django.contrib.auth.models import User
from django.conf import settings
from dataglen.models import ValidDataStorageByStream
from solarrms.models import PredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_energy, get_expected_energy
from solarrms.cron_statistical_generation_prediction import getPredictionDataEnergy
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import sys
import pytz
import pandas as pd
import numpy as np

start_time_str = "2017-03-12 05:30:00"
end_time_str = "2017-03-12 06:30:00"
identifier = "yerangiligi"
identifier_type = "PLANT"

print "starting test for get_expected_energy"
try:
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
    expected_energy  = get_expected_energy(identifier, identifier_type, start_time, end_time)
    print (expected_energy)
except Exception as ex:
    print(str(ex))