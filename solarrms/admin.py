from django.contrib import admin
from .models import SolarPlant, Feeder, Inverter, AJB, SolarField, IndependentInverter, PlantMetaSource,\
    GatewaySource, InverterErrorCodes, EnergyMeter, SolarErrorField, SolarGroup, PVSystInfo, Transformer,\
    WeatherStation, SolarMetrics, GatewaySource, InverterErrorCodes, EnergyMeter, SolarErrorField, SolarGroup,\
    PVSystInfo, Transformer, VirtualGateway, PlantContractDetails, PlantFeaturesEnable, ClientContentsEnable, MPPT,\
    InverterStatusMappings, AJBStatusMappings, MeterStatusMappings, TransformerStatusMappings,\
    AggregatedIndependentInverter, PVWatt, IOSensorField

admin.site.register(SolarPlant)
admin.site.register(Feeder)
admin.site.register(Inverter)
admin.site.register(PlantMetaSource)
admin.site.register(AJB)
admin.site.register(SolarField)
admin.site.register(IndependentInverter)
admin.site.register(GatewaySource)
admin.site.register(InverterErrorCodes)
admin.site.register(EnergyMeter)
admin.site.register(SolarErrorField)
admin.site.register(SolarGroup)
admin.site.register(PVSystInfo)
admin.site.register(Transformer)
admin.site.register(WeatherStation)
admin.site.register(SolarMetrics)
admin.site.register(VirtualGateway)
admin.site.register(PlantContractDetails)
admin.site.register(PlantFeaturesEnable)
admin.site.register(ClientContentsEnable)
admin.site.register(MPPT)
admin.site.register(InverterStatusMappings)
admin.site.register(AJBStatusMappings)
admin.site.register(MeterStatusMappings)
admin.site.register(TransformerStatusMappings)
admin.site.register(AggregatedIndependentInverter)
admin.site.register(PVWatt)
admin.site.register(IOSensorField)
