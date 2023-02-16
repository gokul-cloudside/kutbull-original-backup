from solarrms2.models import EnergyContract
from django.db.models import Q

# Create your views here.
def get_ppa_price(plants, starttime, endtime):
    """

    :param plants:
    :param starttime:
    :param endtime:
    :return:
    """
    try:
        existing_contracts = EnergyContract.objects.filter(Q(start_date__gte=starttime.date(),
                                                            end_date__lte=starttime.date(),
                                                            plant__slug__in=plants) |
                                                          Q(start_date__gte=endtime.date(),
                                                            end_date__lte=endtime.date(),
                                                            plant__slug__in=plants) |
                                                          Q(start_date__gte=starttime.date(),
                                                            end_date__lte=endtime.date(),
                                                            plant__slug__in=plants) |
                                                          Q(start_date__lte=starttime.date(),
                                                            end_date__gte=endtime.date(),
                                                            plant__slug__in=plants)).values('plant__slug',
                                                                                            'ppa_price',
                                                                                            'start_date',
                                                                                            'end_date')
        contracts = {}
        for ec in existing_contracts:
            plant_slug = ec.pop('plant__slug')
            if plant_slug not in contracts:
                contracts["%s" % plant_slug] = []
            contracts["%s" % plant_slug].append(ec)
        return contracts
    except Exception as exc:
        return {}

