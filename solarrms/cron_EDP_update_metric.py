from django.conf import settings
from solarrms.models import SolarPlant
from solarrms.past_date_calculation import historic_values_recalculation
import datetime
from django.utils import timezone
from dashboards.models import DataglenClient

start_date = "2017-01-01 00:00:00"

def compute_EDP_metrics():
    try:
        print("EDP Compute metric cron job started: "+str(timezone.now()))
        #current_time = timezone.now()
        current_time = datetime.datetime.now()
        endtime = (current_time+datetime.timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
        starttime = endtime - datetime.timedelta(days=7)
        #starttime = starttime.replace(hour=0,minute=0,second=0,microsecond=0)
        print(str(endtime))
        print(str(starttime))
        #starttime = datetime.datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
        #endtime = datetime.datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')
        #plant_list = ['faro','santarem','seia','castelo']
        #client = DataglenClient.objects.get(slug='edp')
        plants = SolarPlant.objects.all()
        for plant in plants:
            try:
                #plant = SolarPlant.objects.get(slug=plant_name)
                if str(plant.slug) == 'pavagada':
                    pass
                else:
                    historic_values_recalculation(starttime, endtime, plant)
                    print("calculations done for plant: "+plant.slug)
            except:
                continue

    except Exception as ex:
        print("Exception in compute_EDP_metrics: "+str(ex))