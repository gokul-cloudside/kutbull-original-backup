from django.conf import settings
from dataglen.models import ValidDataStorageByStream
from solarrms.models import PredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from django.utils import timezone
from solarrms.solarutils import get_minutes_aggregated_energy
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import sys
import pytz
import pandas as pd

def run_test1():
        print(" test - %s", datetime.now())
