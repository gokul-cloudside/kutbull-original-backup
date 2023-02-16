from django.contrib import admin
from dwebdyn.models import WebdynClient, WebdynGateway, InvertersDevice, ModbusDevice, IODevice

# Register your models here.
admin.site.register(WebdynClient)
admin.site.register(WebdynGateway)
admin.site.register(InvertersDevice)
admin.site.register(ModbusDevice)
admin.site.register(IODevice)
