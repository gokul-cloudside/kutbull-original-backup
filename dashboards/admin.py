from django.contrib import admin
from .models import DataglenClient, DataglenGroup, Dashboard


admin.site.register(Dashboard)
admin.site.register(DataglenClient)
admin.site.register(DataglenGroup)
