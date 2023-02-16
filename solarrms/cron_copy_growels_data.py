from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from monitoring.views import write_a_data_write_ttl
from django.utils import timezone


def copy_growels_data():
    try:
        print("growels data copy cronjob started")
        from_plant = "growels"
        to_plant = "raheja"
        until_time = timezone.now()
        from_time = until_time - timedelta(minutes=20)
        from_meta = 'M2ckTQWK0TmGGse'
        to_meta = 'IvJntXuz6ohWxDQ'
        from_meta_source = PlantMetaSource.objects.get(sourceKey=from_meta)
        to_meta_source = PlantMetaSource.objects.get(sourceKey=to_meta)

        for field in from_meta_source.fields.all():
            data_records = ValidDataStorageByStream.objects.filter(source_key=from_meta_source.sourceKey,
                                                                   stream_name=field.name,
                                                                   timestamp_in_data__gte=from_time,
                                                                   timestamp_in_data__lte=until_time)
            print len(data_records)
            for record in data_records:
                write_a_data_write_ttl(to_meta_source.user.id, to_meta_source.sourceKey,
                                       to_meta_source.timeoutInterval,
                                       True, until_time)
                if record.timestamp_in_data.minute == 15:
                    time_stamp1 = record.timestamp_in_data.replace(minute=10)
                    time_stamp2 = record.timestamp_in_data.replace(minute=20)
                    ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                            stream_name=field.name,
                                                            timestamp_in_data=time_stamp1,
                                                            insertion_time=record.insertion_time,
                                                            multiplication_factor=record.multiplication_factor,
                                                            raw_value = record.raw_value,
                                                            stream_value=record.stream_value
                                                            )
                    ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                            stream_name=field.name,
                                                            timestamp_in_data=time_stamp2,
                                                            insertion_time=record.insertion_time,
                                                            multiplication_factor=record.multiplication_factor,
                                                            raw_value = record.raw_value,
                                                            stream_value=record.stream_value)
                elif record.timestamp_in_data.minute == 45:
                    time_stamp1 = record.timestamp_in_data.replace(minute=40)
                    time_stamp2 = record.timestamp_in_data.replace(minute=50)
                    ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                            stream_name=field.name,
                                                            timestamp_in_data=time_stamp1,
                                                            insertion_time=record.insertion_time,
                                                            multiplication_factor=record.multiplication_factor,
                                                            raw_value = record.raw_value,
                                                            stream_value=record.stream_value)
                    ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                            stream_name=field.name,
                                                            timestamp_in_data=time_stamp2,
                                                            insertion_time=record.insertion_time,
                                                            multiplication_factor=record.multiplication_factor,
                                                            raw_value = record.raw_value,
                                                            stream_value=record.stream_value)
                else:
                    ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                            stream_name=field.name,
                                                            timestamp_in_data=record.timestamp_in_data,
                                                            insertion_time=record.insertion_time,
                                                            multiplication_factor=record.multiplication_factor,
                                                            raw_value = record.raw_value,
                                                            stream_value=record.stream_value)
        print("growels data copy cronjob completed!")
    except Exception as exception:
        print(str(exception))