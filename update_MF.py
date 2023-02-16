import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()

from dataglen.models import Sensor, Field
from solarrms.models import PlantMetaSource

meta_source = PlantMetaSource.objects.get(sourceKey="M2ckTQWK0TmGGse")
print(str(meta_source))
field = Field.objects.get(source=meta_source,name="IRRADIATION")
print(str(field))
field.multiplicationFactor=0.001
field.save()
