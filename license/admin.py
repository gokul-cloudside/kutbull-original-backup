from django.contrib import admin
from license.models import License, Installation

# Register your models here.
class InstallationInline(admin.TabularInline):
    model = Installation

class LicenseAdmin(admin.ModelAdmin):
    model = License
    # inlines = [InstallationInline]
    search_fields = ['license_key', 'installation_key']

admin.site.register(License, LicenseAdmin)
admin.site.register(Installation)

