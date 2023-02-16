from django.contrib import admin
from .models import Events, EventsConfig,AlertManagement,UserEventAlertsPreferences
# Register your models here.

admin.site.register(Events)
admin.site.register(EventsConfig)
admin.site.register(AlertManagement)
admin.site.register(UserEventAlertsPreferences)