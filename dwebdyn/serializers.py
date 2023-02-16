from rest_framework import serializers

class DataEntrySolarPlantSerializer(serializers.Serializer):
    name=serializers.CharField()
    location=serializers.CharField()
    city=serializers.CharField()
    ac_capacity=serializers.FloatField()
    dc_capacity=serializers.FloatField()
    lat=serializers.FloatField()
    long=serializers.FloatField()
    elevation=serializers.FloatField(required=False)
    evacuation_point=serializers.FloatField(required=False)
    intermediate_client=serializers.CharField(required=False, allow_null=True, allow_blank=True)

class DataEntryModuleSerializer(serializers.Serializer):
    panel_capacity=serializers.FloatField(help_text="Capacity of panels")
    panel_efficiency=serializers.FloatField(help_text="Panel efficiency")
    panel_area=serializers.FloatField(help_text="Area of panels")
    panel_manufacturer=serializers.CharField(help_text="Panel manufacturer")
    model_number=serializers.CharField(required=False, help_text="model number of panels")
    panel_technology=serializers.CharField(required=False, help_text="technology used in panels, like polyctystalline, monocrystalline etc.")
    total_number_of_panels=serializers.IntegerField(help_text="total number of panels")

class DataEntryGroupSerializer(serializers.Serializer):
    name=serializers.CharField()
    data_logger_device_id=serializers.CharField()
    panel_numbers=serializers.IntegerField()
    panel_area=serializers.FloatField()
    tilt_angle=serializers.FloatField()
    type=serializers.CharField(required=False)
    azimuth=serializers.CharField(required=False)

class StringsPerMpptSerializer(serializers.Serializer):
    mppt_name = serializers.CharField(required=False)
    tilt_angle = serializers.CharField(required=False)
    number_of_strings = serializers.CharField(required=False)

class ModulesPerStringSerializer(serializers.Serializer):
    mppt_name = serializers.CharField(required=False)
    string_name = serializers.CharField(required=False)
    number_of_modules = serializers.CharField(required=False)

class DataEntryInverterSerializer(serializers.Serializer):
    name=serializers.CharField(required=False)
    device=serializers.CharField(required=False)
    manufacturer=serializers.CharField()
    model_number=serializers.CharField()
    capacity=serializers.FloatField(required=False)
    number_of_mppts=serializers.IntegerField(required=False)
    strings_per_mppt=StringsPerMpptSerializer(required=False, many=True)
    # modules_per_string=ModulesPerStringSerializer(required=False, many=True)
    modules_per_string=serializers.ListField(required=False)
    connected_dc_capacity=serializers.FloatField(required=False)
    serial_number=serializers.CharField(required=False)
    modbus_address=serializers.CharField()

class DataEntryWeatherStation(serializers.Serializer):
    manufacturer=serializers.CharField()
    model_number=serializers.CharField()
    group_name=serializers.CharField()
    tilt_angle=serializers.FloatField()

# class DataEntryEnergyMeter(serializers.Serializer):
#     manufacturer=serializers.CharField()
#     model_number=serializers.CharField()
#     group_name=serializers.CharField()

class PlantDataEntrySerializer(serializers.Serializer):
    plant_details = DataEntrySolarPlantSerializer(required=True, many=False)
    module_details = DataEntryModuleSerializer(required=True, many=False)
    # group_details=DataEntryGroupSerializer(required=True, many=True)
    # inverter_details=DataEntryInverterSerializer(required=True, many=True)
    # weather_station=DataEntryWeatherStation(required=False, many=False)
    # energy_meter=DataEntryEnergyMeter(required=False, many=False)

class DeviceDataEntrySerializer(serializers.Serializer):
    group_details=DataEntryGroupSerializer(required=True, many=True)
    inverters=DataEntryInverterSerializer(required=False, many=True)
    modbus=DataEntryInverterSerializer(required=False, many=True)
    #weather_station=DataEntryWeatherStation(required=False, many=False)
    #energy_meter=DataEntryEnergyMeter(required=False, many=False)
