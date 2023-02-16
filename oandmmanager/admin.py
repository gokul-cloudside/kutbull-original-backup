from django.contrib import admin
from oandmmanager.models import Tasks, Preferences, TaskItem, TaskAssociation, Cycle

admin.site.register(Tasks)
admin.site.register(Preferences)
admin.site.register(TaskItem)
admin.site.register(TaskAssociation)
admin.site.register(Cycle)
