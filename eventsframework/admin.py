from django.contrib import admin
from .models import Company, MaintenanceContract, Event, ContractState, ServiceRequest,\
ServiceRequestState, SLA, OpeningHours, ClosingRules
# Register your models here.


class ContractStateInline(admin.TabularInline):
    model = ContractState


class SLAInline(admin.TabularInline):
    model = SLA


class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours


class ClosingHoursInline(admin.TabularInline):
    model = ClosingRules


admin.site.register(Company)


class MaintenanceContractAdmin(admin.ModelAdmin):
    model = MaintenanceContract
    inlines = [ContractStateInline, SLAInline, OpeningHoursInline, ClosingHoursInline]

admin.site.register(MaintenanceContract, MaintenanceContractAdmin)

admin.site.register(Event)
admin.site.register(ServiceRequest)
admin.site.register(ServiceRequestState)
