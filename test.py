
from confluent_kafka import Producer
import json

p = Producer({'bootstrap.servers': 'localhost:9092'})
print("p is None %s" %str(p) )
#some_data_source=['s1','s2','s3']
some_data_source=[{'s1':1},{'s1':2},{'s1':3}]
for data in some_data_source:
    #p.produce('mytopic', data.encode('utf-8'))
     p.produce('newtopic',json.dumps(data))
p.flush()

#for saving actual energy data for old dates again
from solarrms.models import PredictionData,NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from django.conf import settings
from solarrms.cron_stat_generation_prediction_new import run_generation_prediction_adjustments, run_old_generation_prediction_adjustment
from django.utils import timezone
import pytz

plant = SolarPlant.objects.get(slug='gupl')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
start_time = timezone.now()
tz = pytz.timezone(plant_meta_source.dataTimezone)
start_time = start_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
start_time = start_time - timedelta(days=10)
start_time = start_time.replace(hour=0,minute=0,second=0,microsecond=0)
end_time = start_time + timedelta(days=10)

PREDICTION_TIMEPERIOD_SPECIFIED = 60*15
#update actual energy for all hours starting from 6:00am
#TODO: update for all earlier hours of that day
dt_current_time_UTC = timezone.now()
dict_energy = get_minutes_aggregated_energy(start_time, end_time, plant_meta_source.plant, 'MINUTE', PREDICTION_TIMEPERIOD_SPECIFIED/60, split=False, meter_energy=True)
if dict_energy:
    for i in range(0,len(dict_energy)):
        print dict_energy[i]['energy']
        print dict_energy[i]['timestamp']
        pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                        identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'ACTUAL',
                                        ts = dict_energy[i]['timestamp'],value = dict_energy[i]['energy'],
                                        lower_bound = dict_energy[i]['energy'], upper_bound=dict_energy[i]['energy'],update_at = dt_current_time_UTC)
        pd_obj.save()
        pd_obj = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=PREDICTION_TIMEPERIOD_SPECIFIED,
                                           identifier_type = 'plant',plant_slug=plant_meta_source.plant.slug, identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'ACTUAL',
                                           ts = dict_energy[i]['timestamp'],value = dict_energy[i]['energy'],
                                           lower_bound = dict_energy[i]['energy'], upper_bound=dict_energy[i]['energy'],update_at = dt_current_time_UTC)
        pd_obj.save()


#for running day-ahead forecasting for old data
from solarrms.models import PredictionData,NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from django.conf import settings
from solarrms.cron_stat_generation_prediction_new import run_generation_prediction_adjustments, run_old_generation_prediction_adjustment,compute_day_ahead_statistical_prediction
from django.utils import timezone
import pytz
#start_time = timezone.now()
plant = SolarPlant.objects.get(slug='gupl')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
tz = pytz.timezone(plant_meta_source.dataTimezone)
#start_time = start_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
#start_time = start_time - timedelta(days=60)
#start_time = start_time.replace(hour=0,minute=0,second=0,microsecond=0)
start_time = datetime.strptime("2017-10-01T00:00:00", "%Y-%m-%dT%H:%M:%S")#put one day in advance than we need to compute
start_time = tz.localize(start_time)
#end_time = start_time + timedelta(days=60)
end_time = datetime.strptime("2017-12-31T23:45:00", "%Y-%m-%dT%H:%M:%S")
end_time = tz.localize(end_time)
current_time = start_time
while current_time <= end_time:
    compute_day_ahead_statistical_prediction(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
    print("Hourly prediction completed")
    compute_day_ahead_statistical_prediction(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
    print("15 min prediction completed")
    current_time = current_time + timedelta(days=1)


#for running adjustments on old data
from solarrms.models import PredictionData,NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from django.conf import settings
from solarrms.cron_stat_generation_prediction_new import run_generation_prediction_adjustments, run_old_generation_prediction_adjustment,compute_day_ahead_statistical_prediction,run_generation_prediction_adjustments_update
from django.utils import timezone
import pytz
start_time = timezone.now()
plant = SolarPlant.objects.get(slug='gupl')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
tz = pytz.timezone(plant_meta_source.dataTimezone)
start_time = datetime.strptime("2017-10-01T00:00:00", "%Y-%m-%dT%H:%M:%S")#put one day in advance than we need to compute
start_time = tz.localize(start_time)
#start_time = start_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
#start_time = start_time - timedelta(days=40)
#start_time = start_time.replace(hour=0,minute=0,second=0,microsecond=0)
#end_time = start_time + timedelta(days=40)
end_time = datetime.strptime("2017-12-31T23:45:00", "%Y-%m-%dT%H:%M:%S")
end_time = tz.localize(end_time)
OPERATIONS_END_TIME = 20
OPERATIONS_START_TIME = 6

current_time = start_time
while current_time <= end_time:
    if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
        run_generation_prediction_adjustments_update(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
        run_generation_prediction_adjustments_update(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
    current_time = current_time + timedelta(minutes=15)


#for running MAPE adjustments on old data
from solarrms.models import PredictionData,NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from django.conf import settings
from solarrms.cron_stat_generation_prediction_new import run_generation_prediction_adjustments, run_old_generation_prediction_adjustment,compute_day_ahead_statistical_prediction,run_generation_prediction_adjustments_update
from django.utils import timezone
import pytz
start_time = timezone.now()
plant = SolarPlant.objects.get(slug='gupl')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
tz = pytz.timezone(plant_meta_source.dataTimezone)
start_time = datetime.strptime("2017-10-01T00:00:00", "%Y-%m-%dT%H:%M:%S")#put one day in advance than we need to compute
start_time = tz.localize(start_time)
#start_time = start_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
#start_time = start_time - timedelta(days=40)
#start_time = start_time.replace(hour=0,minute=0,second=0,microsecond=0)
#end_time = start_time + timedelta(days=40)
end_time = datetime.strptime("2017-12-31T23:45:00", "%Y-%m-%dT%H:%M:%S")
end_time = tz.localize(end_time)
OPERATIONS_END_TIME = 20
OPERATIONS_START_TIME = 6

current_time = start_time
while current_time <= end_time:
    if current_time.hour>= OPERATIONS_START_TIME and current_time.hour < OPERATIONS_END_TIME:
        run_generation_prediction_adjustments_update(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.HOUR)
        run_generation_prediction_adjustments_update(plant_meta_source,current_time,settings.DATA_COUNT_PERIODS.FIFTEEN_MINUTUES)
    current_time = current_time + timedelta(minutes=15)



#set a adjustment model values to day ahead prediction first
from solarrms.models import PredictionData,NewPredictionData, SolarPlant, IndependentInverter, PlantMetaSource
from datetime import datetime, timedelta
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from solarrms.solarutils import get_minutes_aggregated_energy
from django.conf import settings
from solarrms.cron_stat_generation_prediction_new import run_generation_prediction_adjustments, run_old_generation_prediction_adjustment,compute_day_ahead_statistical_prediction,run_generation_prediction_adjustments_update
from django.utils import timezone
import pytz
start_time = timezone.now()
plant = SolarPlant.objects.get(slug='gupl')
plant_meta_source = PlantMetaSource.objects.get(plant=plant)
tz = pytz.timezone(plant_meta_source.dataTimezone)
start_time = datetime.strptime("2017-10-01T00:00:00", "%Y-%m-%dT%H:%M:%S")#put one day in advance than we need to compute
start_time = tz.localize(start_time)
end_time = datetime.strptime("2017-12-31T23:45:00", "%Y-%m-%dT%H:%M:%S")
end_time = tz.localize(end_time)
OPERATIONS_END_TIME = 20
OPERATIONS_START_TIME = 6
PREDICTION_TIMEPERIOD_SPECIFIED =900
energyData = PredictionData.objects.filter(
            timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,
            count_time_period = PREDICTION_TIMEPERIOD_SPECIFIED,
            identifier = plant.slug,
            stream_name = 'plant_energy',
            model_name = 'STATISTICAL_DAY_AHEAD',
            ts__gte=start_time,
            ts__lt=end_time)
for i in range(0,len(energyData)):

    adjusted_value = energyData[i]['value'] #+ (adjustments * plant_meta_source.plant.capacity*PREDICTION_TIMEPERIOD_SPECIFIED)/(3600*100)
    pd_obj = PredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=900,
                            identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MAPE',
                            ts = energyData[i]['ts'],value = energyData[i]['value'],
                            lower_bound = energyData[i]['lower_bound'],
                            upper_bound=energyData[i]['upper_bound'],
                            update_at = start_time)
    pd_obj.save()
    pd_obj_new = NewPredictionData(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_START_TIME_SLOT,count_time_period=900,identifier_type='plant',plant_slug=plant_meta_source.plant.slug,
                                   identifier=plant_meta_source.plant.slug, stream_name = 'plant_energy', model_name = 'STATISTICAL_LATEST_MAPE',
                                   ts = energyData[i]['ts'],value = energyData[i]['value'],
                                   lower_bound = energyData[i]['lower_bound'],
                                   upper_bound=energyData[i]['upper_bound'],
                                   update_at = start_time)
    pd_obj_new.save()


from solarrms.cron_cleaning_schedule_new_test import cleaning_schedule
cleaning_schedule()