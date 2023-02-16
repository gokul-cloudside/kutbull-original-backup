__author__ = 'sunilghai'

from solarrms.tasks import write_inverter_energy
from solarrms.models import SolarPlant, IndependentInverter
from dataglen.models import ValidDataStorageByStream

PLANT_SLUG = 'palladam'
USER_ID = 96

plant = SolarPlant.objects.get(slug=PLANT_SLUG)
inverters = plant.independent_inverter_units.all()

for inverter in inverters:
    print "staring to process a new inverter"
    data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey, stream_name='ACTIVE_POWER').order_by('timestamp_in_data')
    print inverter.sourceKey, len(data)
    for datapoint in data:
        print datapoint.timestamp_in_data
        write_inverter_energy(USER_ID, inverter.sourceKey, datapoint.timestamp_in_data, 1)
