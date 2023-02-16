from solarrms.models import PlantCompleteValues
from django.utils import timezone
from django.conf import settings
import pytz

# get the Windspeed data
def windspeed(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        wind_speed = 0.0
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            wind_speed = value[0].windspeed
        return wind_speed if wind_speed > 0.0 else 0.0
    except Exception as exception:
        print(str(exception))
        return 0.0


# get the module temperature
def module_temperature(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        module_temperature = 0.0
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            module_temperature = value[0].module_temperature
        return module_temperature if module_temperature > 0.0 else 0.0
    except Exception as exception:
        print(str(exception))
        return 0.0

# get the ambient temperature
def ambient_temperature(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        ambient_temperature = 0.0
        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
        if len(value)>0:
            ambient_temperature = value[0].ambient_temperature
        return ambient_temperature if ambient_temperature > 0.0 else 0.0
    except Exception as exception:
        print(str(exception))
        return 0.0
