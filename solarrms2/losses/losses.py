from django.utils import timezone
import pytz
from django.conf import settings
from solarrms.models import PlantCompleteValues
from solarrms.models import PredictedValues
from datetime import timedelta

#DC Loss
def dc(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        dc_loss_list = []
        dc_loss = 0.0
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))

        if plants_group is not None:
            for plant in plants_group:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0 and float(value[0].dc_loss)>0:
                    dc_loss_list.append(float(value[0].dc_loss))
            try:
                dc_loss = sum(dc_loss_list)/len(dc_loss_list)
            except:
                dc_loss = 0.0
        elif plant is not None:
            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
            if len(value)>0 and float(value[0].dc_loss)>0:
                dc_loss = float(value[0].dc_loss)
        return dc_loss
    except Exception as exception:
        print str(exception)
        return 0.0

# Conversion Loss
def conversion(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        conversion_loss_list = []
        conversion_loss = 0.0
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))

        if plants_group is not None:
            for plant in plants_group:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=plant.metadata.plantmetasource.sourceKey,
                                                           ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0 and float(value[0].conversion_loss)>0:
                    conversion_loss_list.append(float(value[0].conversion_loss))
            try:
                conversion_loss = sum(conversion_loss_list)/len(conversion_loss_list)
            except:
                conversion_loss = 0.0
        elif plant is not None:
            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
            if len(value)>0 and float(value[0].conversion_loss)>0:
                conversion_loss = float(value[0].conversion_loss)
        return conversion_loss
    except Exception as exception:
        print str(exception)
        return 0.0

# AC Loss
def ac(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        ac_loss_list = []
        ac_loss = 0.0
        try:
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))

        if plants_group is not None:
            for plant in plants_group:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                   ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0 and float(value[0].ac_loss)>0:
                    ac_loss_list.append(float(value[0].ac_loss))
            try:
                ac_loss = sum(ac_loss_list)/len(ac_loss_list)
            except:
                ac_loss = 0.0
        elif plant is not None:
            value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
            if len(value)>0 and float(value[0].ac_loss)>0:
                ac_loss = float(value[0].ac_loss)
        return ac_loss
    except Exception as exception:
        print str(exception)
        return 0.0


# Soiling Loss
def soiling(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now().replace(hour=23, minute=59, second=59, microsecond=59))
        starttime -= timedelta(days=1)
        endtime -= timedelta(days=1)
        soiling_loss = 0.0
        try:
            #starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            starttime = starttime.replace(tzinfo=None)
            starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone('UTC'))
        except:
            tz = pytz.timezone("Asia/Kolkata")
            starttime = starttime.replace(tzinfo=None)
            starttime = tz.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone('UTC'))
        if plant is not None:
            all_inverters = plant.independent_inverter_units.all().values_list('name', flat=True)
            for inverter in all_inverters:
                identifier = "%s-%s" % (plant, inverter)
                value = PredictedValues.objects.filter(timestamp_type='BASED_ON_TIMESTAMP_IN_DATA',
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=identifier,
                                                       stream_name='cleaning',
                                                       ts=starttime)
                if len(value) > 0 and float(value[0].losses) > 0:
                    soiling_loss += float(value[0].losses)
        return soiling_loss
    except Exception as exception:
        print str(exception)
        return 0.0
