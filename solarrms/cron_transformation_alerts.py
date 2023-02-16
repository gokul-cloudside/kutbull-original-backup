from solarrms.models import SolarPlant
from dataglen.models import Sensor
from dashboards.models import DataglenClient
from monitoring.models import SourceMonitoring

asun_gateway_devices = {
                        'asun':['abkaG9EB5XOCuny','eS8QjqdxBRxvi3C'],
                        'grps':['hHNSfWAi6aLvnXP'],
                        'msjs':['ojTi1KezoznjBcG'],
                        'slsdav':['5Z5LIMgO2PXegiM']
                        }

asun_heartbeat_devices = {
                          'asun':['wqCSIySp0TrpvKK'],
                          'grps':['vZ6iOgnOG3foBdL'],
                          'msjs':['xW3Bj4fGnwRK1O8'],
                          'slsdav':['NFpcEvNUiYwOq1Y']
                         }

def check_asun_transformation():
    try:
        client = DataglenClient.objects.get(slug='asun-solar')
        plants = SolarPlant.objects.filter(groupClient=client)
        for plant in plants:
            try:
                plant_slug = str(plant.slug)
                plant_gateway_sources = asun_gateway_devices[plant_slug]
                for source in plant_gateway_sources:
                    print ""
            except Exception as exception:
                print str(exception)
                continue
    except Exception as exception:
        print str(exception)