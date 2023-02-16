from solarrms.api_views import PVSystInfo
from django.utils import timezone
import numpy as np

# get details of PVSYST specific yield
def sy(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        total_pv_sys_sy_list = []
        total_pvsyst_sy = 0
        if plants_group is not None:
            for plant in plants_group:
                if len(plant.pvsyst_info.all())>0:
                    try:
                        current_month = starttime.month if starttime else endtime.minute
                        date = starttime if starttime else endtime
                    except:
                        return 0
                    pv_sys_info_sy = PVSystInfo.objects.filter(plant=plant,
                                                   parameterName='SPECIFIC_PRODUCTION',
                                                   timePeriodType='MONTH',
                                                   timePeriodDay=0,
                                                   timePeriodYear=date.year,
                                                   timePeriodValue=current_month)
                    if len(pv_sys_info_sy)==0:
                        pv_sys_info_sy = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='SPECIFIC_PRODUCTION',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=0,
                                                                   timePeriodValue=current_month)
                    if len(pv_sys_info_sy)> 0 and pv_sys_info_sy[0].parameterValue is not None:
                        pvsyst_sy = float(pv_sys_info_sy[0].parameterValue)
                        total_pv_sys_sy_list.append(pvsyst_sy)
            total_pvsyst_sy = np.mean(total_pv_sys_sy_list) if len(total_pv_sys_sy_list)>0 else 0.0
        elif plant is not None:
            if len(plant.pvsyst_info.all())>0:
                try:
                    current_month = starttime.month if starttime else endtime.minute
                    date = starttime if starttime else endtime
                except:
                    return 0
                pv_sys_info_sy = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='SPECIFIC_PRODUCTION',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=date.year,
                                                           timePeriodValue=current_month)
                if len(pv_sys_info_sy)==0:
                    pv_sys_info_sy = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='SPECIFIC_PRODUCTION',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)
                if len(pv_sys_info_sy)> 0 and pv_sys_info_sy[0].parameterValue is not None:
                    pvsyst_sy = float(pv_sys_info_sy[0].parameterValue)
                total_pvsyst_sy = pvsyst_sy
        return total_pvsyst_sy
    except Exception as exception:
        print str(exception)


# get details of PVSYST PR
def pr(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        total_pv_sys_pr_list = []
        total_pvsyst_pr = 0
        if plants_group is not None:
            for plant in plants_group:
                if len(plant.pvsyst_info.all())>0:
                    try:
                        current_month = starttime.month if starttime else endtime.minute
                        date = starttime if starttime else endtime
                    except:
                        return 0
                    pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                   parameterName='PERFORMANCE_RATIO',
                                                   timePeriodType='MONTH',
                                                   timePeriodDay=0,
                                                   timePeriodYear=date.year,
                                                   timePeriodValue=current_month)
                    if len(pv_sys_info_pr)==0:
                        pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='PERFORMANCE_RATIO',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=0,
                                                                   timePeriodValue=current_month)
                    if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
                        pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
                        total_pv_sys_pr_list.append(pvsyst_pr)
            total_pvsyst_pr = np.mean(total_pv_sys_pr_list) if len(total_pv_sys_pr_list) >0 else 0.0
        elif plant is not None:
            if len(plant.pvsyst_info.all())>0:
                try:
                    current_month = starttime.month if starttime else endtime.minute
                    date = starttime if starttime else endtime
                except:
                    return 0
                pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                           parameterName='PERFORMANCE_RATIO',
                                                           timePeriodType='MONTH',
                                                           timePeriodDay=0,
                                                           timePeriodYear=date.year,
                                                           timePeriodValue=current_month)
                if len(pv_sys_info_pr)==0:
                    pv_sys_info_pr = PVSystInfo.objects.filter(plant=plant,
                                                               parameterName='PERFORMANCE_RATIO',
                                                               timePeriodType='MONTH',
                                                               timePeriodDay=0,
                                                               timePeriodYear=0,
                                                               timePeriodValue=current_month)
                if len(pv_sys_info_pr)> 0 and pv_sys_info_pr[0].parameterValue is not None:
                    pvsyst_pr = float(pv_sys_info_pr[0].parameterValue)
                total_pvsyst_pr = pvsyst_pr
        return total_pvsyst_pr
    except Exception as exception:
        print str(exception)


# get details of PVSYST CUF
def cuf(*args, **kwargs):
    try:
        pass
    except Exception as exception:
        print str(exception)


# get details of PVSYST generation
def generation(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        total_pvsyst_generation = 0
        if plants_group is not None:
            for plant in plants_group:
                if len(plant.pvsyst_info.all())>0:
                    try:
                        current_month = starttime.month if starttime else endtime.minute
                        date = starttime if starttime else endtime
                    except:
                        return 0
                    pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                       parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                       timePeriodType='MONTH',
                                                                       timePeriodDay=0,
                                                                       timePeriodYear=date.year,
                                                                       timePeriodValue=current_month)
                    if len(pv_sys_info_generation)==0:
                        pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                           parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                           timePeriodType='MONTH',
                                                                           timePeriodDay=0,
                                                                           timePeriodYear=0,
                                                                           timePeriodValue=current_month)
                    plant_capacity = plant.capacity
                    if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
                        pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
                        total_pvsyst_generation += pvsyst_generation
        elif plant is not None:
            if len(plant.pvsyst_info.all())>0:
                try:
                    current_month = starttime.month if starttime else endtime.minute
                    date = starttime if starttime else endtime
                except:
                    return 0
                pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                   parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                   timePeriodType='MONTH',
                                                                   timePeriodDay=0,
                                                                   timePeriodYear=date.year,
                                                                   timePeriodValue=current_month)
                if len(pv_sys_info_generation)==0:
                    pv_sys_info_generation = PVSystInfo.objects.filter(plant=plant,
                                                                       parameterName='NORMALISED_ENERGY_PER_DAY',
                                                                       timePeriodType='MONTH',
                                                                       timePeriodDay=0,
                                                                       timePeriodYear=0,
                                                                       timePeriodValue=current_month)
                plant_capacity = plant.capacity
                if len(pv_sys_info_generation)> 0 and pv_sys_info_generation[0].parameterValue is not None:
                    total_pvsyst_generation = float(pv_sys_info_generation[0].parameterValue) * plant_capacity
        return total_pvsyst_generation
    except Exception as exception:
        print str(exception)