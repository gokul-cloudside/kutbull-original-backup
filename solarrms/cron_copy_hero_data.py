from solarrms.models import SolarPlant
from dataglen.models import ValidDataStorageByStream
from django.utils import timezone
import datetime
from monitoring.views import write_a_data_write_ttl

plant_slug_mapppings = {'centralcustom':'demo100',
                        'gmhs':'demo101',
                        'adminblockbbmb':'demo102',
                        'bhu':'demo103',
                        'ait82kw':'demo104',
                        'computerblockbbmb':'demo105',
                        'hirschvogelcomponents':'demok',
                        'councilhouse':'demoh'}


endtime = timezone.now()
starttime = endtime - datetime.timedelta(minutes=60)

def copy_data():
    try:
        for key in plant_slug_mapppings.keys():
            try:
                from_plant = SolarPlant.objects.get(slug=key)
                from_inverters = from_plant.independent_inverter_units.all()
                from_energy_meters = from_plant.energy_meters.all()
                from_ajbs = from_plant.ajb_units.all()
                from_meta = from_plant.metadata.plantmetasource
                from_gateways = from_plant.gateway.all()
                to_plant = SolarPlant.objects.get(slug=plant_slug_mapppings[key])
                to_inverters = to_plant.independent_inverter_units.all()
                to_energy_meters = to_plant.energy_meters.all()
                to_ajbs = to_plant.ajb_units.all()
                to_meta = to_plant.metadata.plantmetasource
                to_gateways = to_plant.gateway.all()

                print "copying for plant : " + str(to_plant.slug)
                # copy inverters data
                for i in range(len(from_inverters)):
                    try:
                        fields = from_inverters[i].fields.all().filter(isActive=True)
                        for field in fields:
                            try:
                                values = ValidDataStorageByStream.objects.filter(source_key=from_inverters[i].sourceKey,
                                                                                 stream_name=str(field.name),
                                                                                 timestamp_in_data__gte=starttime,
                                                                                 timestamp_in_data__lte=endtime)
                                for value in values:
                                    write_a_data_write_ttl(to_inverters[i].user.id, to_inverters[i].sourceKey,
                                                           to_inverters[i].timeoutInterval,
                                                           True, endtime)
                                    ValidDataStorageByStream.objects.create(source_key=to_inverters[i].sourceKey,
                                                                            stream_name=str(field.name),
                                                                            stream_value=value.stream_value,
                                                                            raw_value=value.raw_value,
                                                                            timestamp_in_data=value.timestamp_in_data)
                            except:
                                continue
                    except Exception as exception:
                        print("Exception in copying inverters data : " + str(exception))
                        continue

                # copy energy meters data
                for i in range(len(from_energy_meters)):
                    try:
                        fields = from_energy_meters[i].fields.all().filter(isActive=True)
                        for field in fields:
                            try:
                                values = ValidDataStorageByStream.objects.filter(source_key=from_energy_meters[i].sourceKey,
                                                                                 stream_name=str(field.name),
                                                                                 timestamp_in_data__gte=starttime,
                                                                                 timestamp_in_data__lte=endtime)
                                for value in values:
                                    write_a_data_write_ttl(to_energy_meters[i].user.id, to_energy_meters[i].sourceKey,
                                                           to_energy_meters[i].timeoutInterval,
                                                           True, endtime)
                                    ValidDataStorageByStream.objects.create(source_key=to_energy_meters[i].sourceKey,
                                                                            stream_name=str(field.name),
                                                                            stream_value=value.stream_value,
                                                                            raw_value=value.raw_value,
                                                                            timestamp_in_data=value.timestamp_in_data)
                            except:
                                continue
                    except Exception as exception:
                        print str("Exception in copying meters data : " +str(exception))

                # copy ajbs data
                for i in range(len(from_ajbs)):
                    try:
                        fields = from_ajbs[i].fields.all().filter(isActive=True)
                        for field in fields:
                            try:
                                values = ValidDataStorageByStream.objects.filter(source_key=from_ajbs[i].sourceKey,
                                                                                 stream_name=str(field.name),
                                                                                 timestamp_in_data__gte=starttime,
                                                                                 timestamp_in_data__lte=endtime)
                                for value in values:
                                    write_a_data_write_ttl(to_ajbs[i].user.id, to_ajbs[i].sourceKey,
                                                           to_ajbs[i].timeoutInterval,
                                                           True, endtime)
                                    ValidDataStorageByStream.objects.create(source_key=to_ajbs[i].sourceKey,
                                                                            stream_name=str(field.name),
                                                                            raw_value=value.raw_value,
                                                                            stream_value=value.stream_value,
                                                                            timestamp_in_data=value.timestamp_in_data)
                            except:
                                continue
                    except Exception as exception:
                        print str("Exception in copying ajb data : " + str(exception))

                # copy gateways data
                for i in range(len(from_gateways)):
                    try:
                        fields = from_gateways[i].fields.all().filter(isActive=True)
                        for field in fields:
                            try:
                                values = ValidDataStorageByStream.objects.filter(source_key=from_gateways[i].sourceKey,
                                                                                 stream_name=str(field.name),
                                                                                 timestamp_in_data__gte=starttime,
                                                                                 timestamp_in_data__lte=endtime)
                                for value in values:
                                    write_a_data_write_ttl(to_gateways[i].user.id, to_gateways[i].sourceKey,
                                                           to_gateways[i].timeoutInterval,
                                                           True, endtime)
                                    ValidDataStorageByStream.objects.create(source_key=to_gateways[i].sourceKey,
                                                                            stream_name=str(field.name),
                                                                            raw_value=value.raw_value,
                                                                            stream_value=value.stream_value,
                                                                            timestamp_in_data=value.timestamp_in_data)
                            except:
                                continue
                    except Exception as exception:
                        print str("Exception in copying gateway data : " + str(exception))

                # copy plant meta data
                fields = from_meta.fields.all().filter(isActive=True)
                for field in fields:
                    try:
                        values = ValidDataStorageByStream.objects.filter(source_key=from_meta.sourceKey,
                                                                         stream_name=str(field.name),
                                                                         timestamp_in_data__gte=starttime,
                                                                         timestamp_in_data__lte=endtime)
                        for value in values:
                            write_a_data_write_ttl(to_meta.user.id, to_meta.sourceKey,
                                                   to_meta.timeoutInterval,
                                                   True, endtime)
                            ValidDataStorageByStream.objects.create(source_key=to_meta.sourceKey,
                                                                    stream_name=str(field.name),
                                                                    raw_value=value.raw_value,
                                                                    stream_value=value.stream_value,
                                                                    timestamp_in_data=value.timestamp_in_data)
                    except:
                        continue
            except Exception as exception:
                print str(exception)
                continue
    except Exception as exception:
        print str(exception)