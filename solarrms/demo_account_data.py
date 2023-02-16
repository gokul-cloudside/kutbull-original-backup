from solarrms.models import SolarPlant
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from monitoring.views import write_a_data_write_ttl

def copy_data():
    from_plant = "unisun"
    to_plant = "bangalore"

    from_time = datetime.utcnow() - timedelta(minutes=10)
    until_time = from_time + timedelta(minutes=10)

    from_inverters = SolarPlant.objects.get(slug=from_plant).independent_inverter_units.all()
    to_inverters = SolarPlant.objects.get(slug=to_plant).independent_inverter_units.all()

    for i in range(2):
        from_streams = from_inverters[i].fields.all()
        to_streams = to_inverters[i].fields.all()
        for j in range(len(from_streams)):
            ts = to_streams[j]
            ts.isActive = from_streams[j].isActive
            ts.save()

    for i in range(len(from_inverters)):
        inverter = from_inverters[i]
        for field in inverter.fields.all():
            data_records = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                   stream_name=field.name,
                                                                   timestamp_in_data__gte=from_time,
                                                                   timestamp_in_data__lte=until_time)
            for record in data_records:
                write_a_data_write_ttl(to_inverters[i].user.id, to_inverters[i].sourceKey,
                                       to_inverters[i].timeoutInterval,
                                       True, until_time)
                ValidDataStorageByStream.objects.create(source_key=to_inverters[i].sourceKey,
                                                        stream_name=field.name,
                                                        stream_value=record.stream_value,
                                                        timestamp_in_data=record.timestamp_in_data)
