from django.utils import timezone
import pytz
from django.conf import settings
from solarrms.models import PlantCompleteValues, SpecificYieldTable, PlantSummaryDetails
from solarrms2.generation.generation import international_plant

# get PR value
def pr(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        current = kwargs.pop('current',True)
        pr_list = []
        pr_value = 0.0
        pr_dict = {}
        try:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    value = PlantCompleteValues.objects.filter(
                        timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                        identifier=group.varchar_id,
                        ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                    pr_dict["%s" % group.varchar_id] = 0.0
                    try:
                        if len(value) > 0 and 0.0 < float(value[0].pr) <= 1.0:
                            pr_list.append(value[0].pr)
                            pr_dict["%s" % group.varchar_id] = value[0].pr
                    except:
                        pr_dict["%s" % group.varchar_id] = 0.0
                        pr_list.append(0.0)
                try:
                    pr_value = sum(pr_list) / len(pr_list) if len(pr_list) > 0 else 0.0
                except:
                    pr_value = 0.0
            elif group is not None:
                value = PlantCompleteValues.objects.filter(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=group.varchar_id,
                    ts=starttime.replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value) > 0:
                    pr_value = value[0].pr
            if group_count:
                pr_dict['TOTAL'] = pr_value
                return pr_dict
            else:
                return pr_value
        else:
            if current:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0 and 0.0<float(value[0].pr)<=1.0:
                            pr_list.append(value[0].pr)
                            pr_dict[str(plant.slug)] = value[0].pr
                        else:
                            pr_dict[str(plant.slug)] = value[0].pr
                    try:
                        pr_value = sum(pr_list)/len(pr_list)
                    except:
                        pr_value = 0.0
                elif plant is not None:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        pr_value = value[0].pr
                if split is True:
                    pr_dict['TOTAL'] = pr_value
                    return pr_dict
                else:
                    return pr_value
            else:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=str(plant.slug),
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0 and 0.0<float(value[0].performance_ratio)<=1.0:
                            pr_list.append(value[0].performance_ratio)
                            pr_dict[str(plant.slug)] = value[0].performance_ratio
                        else:
                            pr_dict[str(plant.slug)] = value[0].performance_ratio
                    try:
                        pr_value = sum(pr_list)/len(pr_list)
                    except:
                        pr_value = 0.0
                elif plant is not None:
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=str(plant.slug),
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        pr_value = value[0].performance_ratio
                if split is True:
                    pr_dict['TOTAL'] = pr_value
                    return pr_dict
                else:
                    return pr_value
    except Exception as exception:
        print str(exception)

# get CUFvalue
def cuf(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        current = kwargs.pop('current',True)
        split = kwargs.pop('split', None)
        cuf_list = []
        cuf_value = 0.0
        cuf_dict = {}
        try:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    cuf_dict["%s" % group.varchar_id] = 0.0
                    try:
                        if len(value)>0 and 0.0<float(value[0].cuf)<=1.0:
                            cuf_list.append(value[0].cuf)
                            cuf_dict["%s" % group.varchar_id] = value[0].cuf
                    except:
                        cuf_dict["%s" % group.varchar_id] = 0.0
                        cuf_list.append(0.0)
                try:
                    cuf_value = sum(cuf_list) / len(cuf_list) if len(cuf_list) > 0 else 0.0
                except:
                    cuf_value = 0.0
            elif group is not None:
                value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=group.varchar_id,
                                                           ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    cuf_value = value[0].cuf
            if group_count:
                cuf_dict['TOTAL'] = cuf_value
                return cuf_dict
            else:
                return cuf_value
        else:
            if current:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0 and 0.0<float(value[0].cuf)<=1.0:
                            cuf_list.append(value[0].cuf)
                            cuf_dict[str(plant.slug)] = value[0].cuf
                        else:
                            cuf_dict[str(plant.slug)] = value[0].cuf
                    try:
                        cuf_value = sum(cuf_list)/len(cuf_list)
                    except:
                        cuf_value = 0.0
                elif plant is not None:
                    value = PlantCompleteValues.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        cuf_value = value[0].cuf
                if split is True:
                    cuf_dict['TOTAL'] = cuf_value
                    return cuf_dict
                else:
                    return cuf_value
            else:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=str(plant.slug),
                                                                   ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0 and 0.0<float(value[0].cuf)<=1.0:
                            cuf_list.append(value[0].cuf)
                            cuf_dict[str(plant.slug)] = value[0].cuf
                        else:
                            cuf_dict[str(plant.slug)] = value[0].cuf
                    try:
                        cuf_value = sum(cuf_list)/len(cuf_list)
                    except:
                        cuf_value = 0.0
                elif plant is not None:
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=str(plant.slug),
                                                               ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        cuf_value = value[0].cuf
                if split is True:
                    cuf_dict['TOTAL'] = cuf_value
                    return cuf_dict
                else:
                    return cuf_value
    except Exception as exception:
        print str(exception)

# get Specific Yield
def sy(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        current = kwargs.pop('current',True)
        split = kwargs.pop('split', None)
        specific_yield_list = []
        specific_yield_value = 0.0
        specific_yield_dict = {}
        try:
            starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except:
            if international_plant(plant, plants_group) is False:
                starttime = starttime.astimezone(pytz.timezone("Asia/Kolkata"))
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    value = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=group.varchar_id,
                                                               ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    specific_yield_dict["%s" % group.varchar_id] = 0.0
                    try:
                        specific_yield_list.append(value[0].specific_yield)
                        specific_yield_dict["%s" % group.varchar_id] = value[0].specific_yield
                    except:
                        specific_yield_dict["%s" % group.varchar_id] = 0.0
                        specific_yield_list.append(0.0)
                try:
                    specific_yield_value = sum(specific_yield_list) / len(specific_yield_list) if len(specific_yield_list) > 0 else 0.0
                except:
                    specific_yield_value = 0.0
            elif group is not None:
                value = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                           count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                           identifier=group.varchar_id,
                                                           ts=starttime.astimezone(pytz.timezone(group.plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                if len(value)>0:
                    specific_yield_value = value[0].specific_yield
            if group_count:
                specific_yield_dict['TOTAL'] = specific_yield_value
                return specific_yield_dict
            else:
                return specific_yield_value
        else:
            if current:
                if plants_group is not None:
                    for plant in plants_group:
                        value = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                  identifier=plant.metadata.plantmetasource.sourceKey,
                                                                  ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0:
                            specific_yield_list.append(value[0].specific_yield)
                            specific_yield_dict[str(plant.slug)] = value[0].specific_yield
                    try:
                        specific_yield_value = sum(specific_yield_list)/len(specific_yield_list)
                    except:
                        specific_yield_value = 0.0
                elif plant is not None:
                    value = SpecificYieldTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                  identifier=plant.metadata.plantmetasource.sourceKey,
                                                                  ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        specific_yield_value = value[0].specific_yield
                if split is True:
                    specific_yield_dict['TOTAL'] = specific_yield_value
                    return specific_yield_dict
                else:
                    return specific_yield_value
            else:
                if plants_group is not None:
                    for plant in plants_group:
                        value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                  identifier=str(plant.slug),
                                                                  ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                        if len(value)>0:
                            specific_yield_list.append(value[0].specific_yield)
                            specific_yield_dict[str(plant.slug)] = value[0].specific_yield
                    try:
                        specific_yield_value = sum(specific_yield_list)/len(specific_yield_list)
                    except:
                        specific_yield_value = 0.0
                elif plant is not None:
                    value = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                  identifier=str(plant.slug),
                                                                  ts=starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone)).replace(hour=0, minute=0, second=0, microsecond=0))
                    if len(value)>0:
                        specific_yield_value = value[0].specific_yield
                if split is True:
                    specific_yield_dict['TOTAL'] = specific_yield_value
                    return specific_yield_dict
                else:
                    return specific_yield_value
    except Exception as exception:
        print str(exception)