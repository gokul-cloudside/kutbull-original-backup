from django.contrib import admin
from dataglen.models import Sensor, Field, SensorGroup

admin.site.register(Sensor)
admin.site.register(Field)
admin.site.register(SensorGroup)