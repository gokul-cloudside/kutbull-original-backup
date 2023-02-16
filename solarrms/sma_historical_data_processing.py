from solarrms.tasks import write_inverter_energy
from solarrms.models import SolarPlant, IndependentInverter
from dataglen.models import ValidDataStorageByStream
import pytz

PLANT_SLUG = 'uran'
USER_ID = 43

plant = SolarPlant.objects.get(slug=PLANT_SLUG)
inverters = plant.independent_inverter_units.all()

from solarrms.models import EnergyGenerationTable,PlantPowerTable

ctp = [60*5,60*60,60*60*24,60*60*24*7,60*60*24*7*4]


def delete_records():
    try:
        for i in range(len(ctp)):
            plants_energy = EnergyGenerationTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                 count_time_period=ctp[i],
                                                                 identifier=str(USER_ID) + '_' + PLANT_SLUG)
            plants_energy.delete()
    except Exception as exception:
        print("Error occurred while deleting the records from energy table: "+ str(exception))

    try:
        plants_power = PlantPowerTable.objects.filter(plant_slug=PLANT_SLUG)
        for power in plants_power:
            power.delete()
    except Exception as exception:
        print("Error occurred while deleting the records from power table: "+ str(exception))

# data = ValidDataStorageByStream.objects.filter(source_key=pm.sourceKey, stream_name=PLANT_POWER_STREAM, timestamp_in_data__gte=ts).order_by('timestamp_in_data')
# for i in range(len(data)):
#     ts = pytz.UTC.localize(data[i].timestamp_in_data).astimezone(ist)
#     write_plant_energy(42, pm.sourceKey, ts, 1)

fd = open('invalidrecords.txt', 'w')
for inverter in inverters:
    print "staring to process a new inverter"
    data = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey, stream_name='ACTIVE_POWER').limit(0).order_by('timestamp_in_data')
    for datapoint in data:
        timestamp_in_data = datapoint.timestamp_in_data
        tz = pytz.timezone(str(inverter.dataTimezone))
        # localize only adds tzinfo and does not change the dt value
        print inverter.sourceKey
        utc = pytz.timezone('UTC')
        timestamp_in_data = utc.localize(timestamp_in_data)
        timestamp_in_data = timestamp_in_data.astimezone(tz)
        print timestamp_in_data
        print "----"
        write_inverter_energy(USER_ID, inverter.sourceKey, timestamp_in_data, 1)
        #if timestamp_in_data.hour <= 5:
        #    print timestamp_in_data.hour
        #    print ",".join([inverter.sourceKey, str(timestamp_in_data), str(datapoint.stream_value), "\n"])
        #    fd.write(",".join([inverter.sourceKey, str(timestamp_in_data), str(datapoint.stream_value), "\n"]))
        #    continue
        write_inverter_energy(USER_ID, inverter.sourceKey, timestamp_in_data, 1)
fd.close()