from django.utils import timezone
import pytz
from django.conf import settings
from solarrms.models import PlantCompleteValues, PlantSummaryDetails
import numpy as np

# grid availability

def grid(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        current = kwargs.pop('current',True)
        grid_availability_list=[]
        grid_availability_dict = {}
        grid_availability = ""
        if current is True:
            if plants_group is not None:
                for plant in plants_group:
                    try:
                        starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    except:
                        starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        grid_availability_list.append(100-(value[0].grid_unavailability))
                try:
                    grid_availability = str(round(np.mean(grid_availability_list),2)) + " %"
                except:
                    grid_availability = "100 %"
            elif plant is not None:
                try:
                    starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except:
                    starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    grid_availability = str(round(100-(value[0].grid_unavailability),2)) + " %"
            return grid_availability
        else:
            if plants_group is not None:
                for plant in plants_group:
                    try:
                        starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    except:
                        starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=str(plant.slug),
                                                               ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        grid_availability_list.append(value[0].grid_availability)
                        grid_availability_dict[str(plant.slug)] = str(value[0].grid_availability) + " %"
                    else:
                        grid_availability_dict[str(plant.slug)] = "100.0 %"
                try:
                    grid_availability = str(round(np.mean(grid_availability_list),2)) + " %"
                except:
                    grid_availability = "100 %"
            elif plant is not None:
                try:
                    starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except:
                    starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=str(plant.slug),
                                                           ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    grid_availability = str(round(value[0].grid_availability,2)) + " %"
            if split is True:
                grid_availability_dict['TOTAL'] = grid_availability
                return grid_availability_dict
            else:
                return grid_availability
    except Exception as exception:
        print str(exception)


# equipment availability

def equipment(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        current = kwargs.pop('current',True)
        equipment_availability_dict = {}
        equipment_availability_list=[]
        equipment_availability = ""
        if current is True:
            if plants_group is not None:
                for plant in plants_group:
                    try:
                        starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    except:
                        starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        equipment_availability_list.append(100-(value[0].equipment_unavailability))
                try:
                    equipment_availability = str(round(np.mean(equipment_availability_list),2)) + " %"
                except:
                    equipment_availability = "100 %"
            elif plant is not None:
                try:
                    starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except:
                    starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=plant.metadata.plantmetasource.sourceKey,
                                                           ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    equipment_availability = str(round(100-(value[0].equipment_unavailability),2)) + " %"
            return equipment_availability
        else:
            if plants_group is not None:
                for plant in plants_group:
                    try:
                        starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    except:
                        starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=str(plant.slug),
                                                               ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        equipment_availability_list.append(value[0].equipment_availability)
                        equipment_availability_dict[str(plant.slug)] = str(value[0].equipment_availability) + " %"
                    else:
                        equipment_availability_dict[str(plant.slug)] = "100.0 %"
                try:
                    equipment_availability = str(round(np.mean(equipment_availability_list),2)) + " %"
                except:
                    equipment_availability = "100 %"
            elif plant is not None:
                try:
                    starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except:
                    starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
                value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=str(plant.slug),
                                                           ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    equipment_availability = str(round(value[0].equipment_availability,2)) + " %"
            if split is True:
                equipment_availability_dict['TOTAL'] = equipment_availability
                return equipment_availability_dict
            else:
                return equipment_availability
    except Exception as exception:
        print str(exception)

