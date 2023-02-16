
from solarrms.models import SolarPlant

PLANT_SLUG = "sterling"
DELTA = {'AC_VOLTAGE_R': (0.1, 'V'),
         'CURRENT_R': (.01,'A'),
         'ACTIVE_POWER': (.001,'KW'),
         'AC_FREQUENCY_R': (.01,'Hz'),
         'APPARENT_POWER_R': (.001,'KW'),
         'AC_VOLTAGE_Y': (0.1, 'V'),
         'CURRENT_Y': (.01,'A'),
         'AC_FREQUENCY_Y': (.01,'Hz'),
         'APPARENT_POWER_Y': (.001,'KW'),
         'AC_VOLTAGE_B': (0.1, 'V'),
         'CURRENT_B': (.01,'A'),
         'AC_FREQUENCY_B': (.01,'Hz'),
         'APPARENT_POWER_B': (.001,'KW'),
         'DC_POWER': (.001,'KW'),
         'DAILY_YIELD': (.01,'KWH'),
         'TOTAL_YIELD': (.01,'KWH')}

METADATA = {'IRRADIATION': (.001, 'KWm2'),
            'EXTERNAL_IRRADIATION': (.001, 'KWm2'),
            'ENERGY_METER_DATA': (.001, 'KWH')}

if __name__ == '__main__':
    plant = SolarPlant.objects.get(slug=PLANT_SLUG)
    for inverter in plant.independent_inverter_units.all():
        for stream in inverter.fields.all():
            if stream.name in DELTA.keys():
                stream.isActive = True
                stream.multiplicationFactor = DELTA[stream.name][0]
                stream.streamDataUnit = DELTA[stream.name][1]
                stream.save()
            else:
                stream.isActive = False
                stream.save()
    if hasattr(plant, 'metadata'):
        for stream in plant.metadata.fields.all():
            if stream.name in METADATA.keys():
                stream.isActive = True
                stream.multiplicationFactor = METADATA[stream.name][0]
                stream.streamDataUnit = METADATA[stream.name][1]
                stream.save()
            else:
                stream.isActive = False
                stream.save()
