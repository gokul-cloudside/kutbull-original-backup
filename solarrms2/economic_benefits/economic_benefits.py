from django.utils import timezone
from solarrms2.generation.generation import generation

# get details of CO2 saved
def co2(*args, **kwargs):
    try:
        # plants_group=kwargs.pop('plants_group', None)
        # plant=kwargs.pop('plant', None)
        # meter=kwargs.pop('meter', None)
        # inverter=kwargs.pop('inverter', None)
        # starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        # endtime=kwargs.pop('endtime',timezone.now())
        # print plant
        # if plants_group is not None:
        #     energy = generation(plants_group=plants_group, starttime=starttime, endtime=endtime)
        # elif plant is not None:
        #     energy = generation(plant=plant, starttime=starttime, endtime=endtime)
        # else:
        #     energy = 0
        # return energy*0.7
        return 0.7
    except Exception as exception:
        print str(exception)


# get details of homes powered
def homes_powered(*args, **kwargs):
    try:
        # plants_group=kwargs.pop('plants_group', None)
        # plant=kwargs.pop('plant', None)
        # meter=kwargs.pop('meter', None)
        # inverter=kwargs.pop('inverter', None)
        # starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        # endtime=kwargs.pop('endtime',timezone.now())
        # if plants_group is not None:
        #     energy = generation(plants_group=plants_group, starttime=starttime, endtime=endtime)
        # elif plant is not None:
        #     energy = generation(plant=plant, starttime=starttime, endtime=endtime)
        # else:
        #     energy = 0
        # return int(energy/3)
        return 3
    except Exception as exception:
        print str(exception)


# get details of trees planted
def trees_planted(*args, **kwargs):
    try:
        # plants_group=kwargs.pop('plants_group', None)
        # plant=kwargs.pop('plant', None)
        # meter=kwargs.pop('meter', None)
        # inverter=kwargs.pop('inverter', None)
        # starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        # endtime=kwargs.pop('endtime',timezone.now())
        # if plants_group is not None:
        #     energy = generation(plants_group=plants_group, starttime=starttime, endtime=endtime)
        # elif plant is not None:
        #     energy = generation(plant=plant, starttime=starttime, endtime=endtime)
        # else:
        #     energy = 0
        # return int(energy/10)
        return 10
    except Exception as exception:
        print str(exception)