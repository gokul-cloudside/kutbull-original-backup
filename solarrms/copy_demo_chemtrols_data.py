from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource, AJB, EnergyMeter
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from monitoring.views import write_a_data_write_ttl

def copy_chemtrols_demo_data():
    try:
        print("chemtrols demo data copy cronjob started")

        until_time = datetime.utcnow()
        from_time = until_time - timedelta(minutes=45)

        from_inverters = ['Tx1Rcx2pLprGlJU','Im8bHsxN959Wb3D']
        to_inverters = ['8Dvet8ZJVYzJpDH','Ip3cWISwmiBNUvA']
        from_ajbs=['db2e11BzDN9cHd0','FkCgoRqZUarqZQt','elfbjmZTp5X0zMW','IPadC9JBwMLaTzq','vu3mJeE8agWsOEM','rZfiEgs80Wkmshe','58cpGnnwQIfwKow','n6xnLd2C3aCETm7','qcftwGm64VYMSlk','ImgwMVtxWAJ3zP0','rHI4TvIXmB8eUmK','XHLkzl6iq9Y0Td2']
        to_ajbs=['BYZFbkJRLzonWp9','IBM3VAEbovHuS6S','iXyrB2LHTfGoacd','SHQwyJ7n9LIGiiK','fvqhkqiGR7LXG04','y06rR4j5oxIgTVO','abdi9gtQ2sWciUK','gfGN0U9KhsIQA5h','aDZGGoSamAFGbKF','kuxp5gij6RPvd39','lg1KHY52Sbb4CoT','v7GzSNwManAANQ4']
        from_meters=['4P3UkzZtBoMjrqA']
        to_meters=['CiNaZwMqaFRegLb']
        from_gateway = ['NXu8an6Mb4EwTQl']
        to_gateway = ['E0UOQF2NIrOeJfl']
        from_meta = ['1IYcvMYjyx8pwP5']
        to_meta = ['iY8lAUNhBK4R3eg']


        # copy Gateway data
        for i in range(len(from_gateway)):
            from_gateway_source = GatewaySource.objects.get(sourceKey=from_gateway[i])
            to_gateway_source = GatewaySource.objects.get(sourceKey=to_gateway[i])

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
        for i in range(len(from_meta)):
            from_meta_source = PlantMetaSource.objects.get(sourceKey=from_meta[i])
            to_meta_source = PlantMetaSource.objects.get(sourceKey=to_meta[i])

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

        # copy AJB data
        for i in range(len(from_ajbs)):
            from_ajb = AJB.objects.get(sourceKey=from_ajbs[i])
            to_ajb = AJB.objects.get(sourceKey=to_ajbs[i])
            for field in from_ajb.fields.all():
                data_records = ValidDataStorageByStream.objects.filter(source_key=from_ajb.sourceKey,
                                                                       stream_name=field.name,
                                                                       timestamp_in_data__gte=from_time,
                                                                       timestamp_in_data__lte=until_time)
                print len(data_records)
                for record in data_records:
                    write_a_data_write_ttl(to_ajb.user.id, to_ajb.sourceKey,
                                       	   to_ajb.timeoutInterval,
                                           True, until_time)
                    ValidDataStorageByStream.objects.create(source_key=to_ajb.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            timestamp_in_data=record.timestamp_in_data)



        # copy Energy Meter data
        for i in range(len(from_meters)):
            from_meter = EnergyMeter.objects.get(sourceKey=from_meters[i])
            to_meter = EnergyMeter.objects.get(sourceKey=to_meters[i])
            for field in from_meter.fields.all():
                data_records = ValidDataStorageByStream.objects.filter(source_key=from_meter.sourceKey,
                                                                       stream_name=field.name,
                                                                       timestamp_in_data__gte=from_time,
                                                                       timestamp_in_data__lte=until_time)
                print len(data_records)
                for record in data_records:
                    write_a_data_write_ttl(to_meter.user.id, to_meter.sourceKey,
                                       	   to_meter.timeoutInterval,
                                           True, until_time)
                    ValidDataStorageByStream.objects.create(source_key=to_meter.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            timestamp_in_data=record.timestamp_in_data)

        print("chemtrols demo data copy cronjob completed!")
    except Exception as exception:
        print(str(exception))