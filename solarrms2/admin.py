from django.contrib import admin

# Register your models here.
from solarrms2.models import EnergyOffTaker, EnergyContract, SolarEventsPriorityMapping,\
    BankAccount, BillingEntity

admin.site.register(EnergyOffTaker)
admin.site.register(EnergyContract)
admin.site.register(SolarEventsPriorityMapping)
admin.site.register(BankAccount)
admin.site.register(BillingEntity)