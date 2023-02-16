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
from solarrms.models import PredictionData, SolarPlant, IndependentInverter, PlantMetaSource,NewPredictionData
from datetime import datetime, timedelta
from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_energy
from solarrms.cron_statistical_generation_prediction import getPredictionDataEnergy
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import sys
import pytz
import pandas as pd
import numpy as np
from solarrms.cron_stat_generation_prediction_new import save_actual_energy_generation_for_inverters

BOUNDS_ON_CAPACITY = 0.15

solar_plants = SolarPlant.objects.all()
for plant in solar_plants:
    records = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                              count_time_period=900,identifier=plant.slug,
                                                              stream_name ='plant_energy', model_name='STATISTICAL_DAY_AHEAD',
                                                              )
    for record in records:
               record.lower_bound = record.value - BOUNDS_ON_CAPACITY*plant.capacity/4
               record.upper_bound = record.value + BOUNDS_ON_CAPACITY*plant.capacity/4
               record.save()
    records = PredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                              count_time_period=900,identifier=plant.slug,
                                                              stream_name ='plant_energy', model_name='STATISTICAL_LATEST',
                                                              )
    for record in records:
               record.lower_bound = record.value - BOUNDS_ON_CAPACITY*plant.capacity/4
               record.upper_bound = record.value + BOUNDS_ON_CAPACITY*plant.capacity/4
               record.save()

    records = NewPredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                              count_time_period=900,identifier_type='plant',identifier=plant.slug,plant_slug=plant.slug,
                                                              stream_name ='plant_energy', model_name='STATISTICAL_DAY_AHEAD')
    for record in records:
               record.lower_bound = record.value - BOUNDS_ON_CAPACITY*plant.capacity/4
               record.upper_bound = record.value + BOUNDS_ON_CAPACITY*plant.capacity/4
               record.save()

    records = NewPredictionData.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
                                                              count_time_period=900,identifier_type='plant',identifier=plant.slug,plant_slug=plant.slug,
                                                              stream_name ='plant_energy', model_name='STATISTICAL_LATEST')
    for record in records:
               record.lower_bound = record.value - BOUNDS_ON_CAPACITY*plant.capacity/4
               record.upper_bound = record.value + BOUNDS_ON_CAPACITY*plant.capacity/4
               record.save()