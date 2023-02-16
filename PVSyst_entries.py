import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()

from dataglen.models import Sensor, Field
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB, PVSystInfo
from django.contrib.auth.models import User


plant = SolarPlant.objects.get(slug='waaneep')
print(str(plant))

PR_values =[(1,0.8),(2,0.795), (3,0.78),(4,0.78), (5,0.775),(6,0.785),(7,0.79),(8,0.795),(9,0.795),(10,0.78),(11,0.79),(12,0.795)]
normalised_values =[(1,4.6),(2,5.1),(3,5.4),(4,5.2),(5,5.25),(6,4.3),(7,3.3),(8,3.25),(9,3.75),(10,4.6),(11,4.65),(12,4.45)]

normalised_year =(0,4.2)

for (key,value) in PR_values:
    PVSystInfo.objects.create(plant=plant,parameterName="PERFORMANCE_RATIO",timePeriodType="MONTH",timePeriodValue=key ,parameterValue=value)

for (key,value) in normalised_values:
    PVSystInfo.objects.create(plant=plant,parameterName="NORMALISED_ENERGY_PER_DAY",timePeriodType="MONTH",timePeriodValue=key ,parameterValue=value,unit="kWh/kWp/day")
