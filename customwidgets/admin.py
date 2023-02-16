from django.contrib import admin
from .models import WidgetInstance, FilePath, UserConfiguration

admin.site.register(WidgetInstance)
admin.site.register(FilePath)
admin.site.register(UserConfiguration)