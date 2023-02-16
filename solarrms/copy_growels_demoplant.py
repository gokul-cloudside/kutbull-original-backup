from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from monitoring.views import write_a_data_write_ttl

def copy_growels_data():
    try:
        print("growels data copy cronjob started")

        until_time = datetime.utcnow()
        from_time = until_time - timedelta(minutes=20)

        from_inverters = ['kA0OloSSR4p4BC4','ZckEZtxOJqPaKeB','rgIUvgevMA5xbu4','7AArjELGfUFcaQi','RuQGSE3TbJQammG','fQ4QNa22dWd2OK7']
        to_inverters = ['P3QCtnQHjwgmFlG','4QPFSKObCyArVHE','PqfAUZf1wVTD7IL','0vdhSWFU1WzJG6j','CJCxQbKpKrKZd86','9a6iguPJafcm8Ch']
        from_gateway = 'h1wlfGUzSeMquh7'
        to_gateway = 'thCgPW96cuJKWx8'
        from_meta = 'M2ckTQWK0TmGGse'
        to_meta = 'ilHpRI9xIAKtXLu'

        # copy Gateway data
        from_gateway_source = GatewaySource.objects.get(sourceKey=from_gateway)
        to_gateway_source = GatewaySource.objects.get(sourceKey=to_gateway)

        for field in from_gateway_source.fields.all():
            data_records = ValidDataStorageByStream.objects.filter(source_key=from_gateway_source.sourceKey,
                                                                   stream_name=field.name,
                                                                   timestamp_in_data__gte=from_time,
                                                                   timestamp_in_data__lte=until_time)
            print len(data_records)
            for record in data_records:
                write_a_data_write_ttl(to_gateway_source.user.id, to_gateway_source.sourceKey,
                                       to_gateway_source.timeoutInterval,
                                       True, until_time)
                ValidDataStorageByStream.objects.create(source_key=to_gateway_source.sourceKey,
                                                        stream_name=field.name,
                                                        stream_value=record.stream_value,
                                                        timestamp_in_data=record.timestamp_in_data)

        # copy Inverters data
        for i in range(len(from_inverters)):
            from_inverter = IndependentInverter.objects.get(sourceKey=from_inverters[i])
            to_inverter = IndependentInverter.objects.get(sourceKey=to_inverters[i])
            for field in from_inverter.fields.all():
                data_records = ValidDataStorageByStream.objects.filter(source_key=from_inverter.sourceKey,
                                                                       stream_name=field.name,
                                                                       timestamp_in_data__gte=from_time,
                                                                       timestamp_in_data__lte=until_time)
                print len(data_records)
                for record in data_records:
                    write_a_data_write_ttl(to_inverter.user.id, to_inverter.sourceKey,
                                       	   to_inverter.timeoutInterval,
                                           True, until_time)
                    ValidDataStorageByStream.objects.create(source_key=to_inverter.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            timestamp_in_data=record.timestamp_in_data)

        # copy plant meta source data
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
                ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                        stream_name=field.name,
                                                        stream_value=record.stream_value,
                                                        timestamp_in_data=record.timestamp_in_data)
        print("growels data copy cronjob completed!")
    except Exception as exception:
        print(str(exception))