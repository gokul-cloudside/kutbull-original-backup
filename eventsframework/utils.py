import datetime
from django.conf import settings
from eventsframework.models import OpeningHours, ClosingRules, MaintenanceContract
from django.core.exceptions import ImproperlyConfigured

from compat import get_model
import random
import datetime
from solarrms.models import VirtualGateway, GatewaySource, SolarGroup, IndependentInverter
from helpdesk.models import TicketAssociation, Ticket
from django.db.models import Sum, Count
from oandmmanager.models import TaskItem
from django.db.models import Q



ALL_EVENTS = {'CORRECTIVE_EVENT': ['GATEWAY_POWER_OFF', 'GATEWAY_DISCONNECTED', 'INVERTERS_DISCONNECTED',
                                   'INVERTERS_ALARMS'],
              'PREDICTIVE_EVENT': ['PANEL_CLEANING']}

SEVERITY = {'HIGH': ['INVERTERS_ALARMS'], 'LOW': ['SCHEDULED_TASK', 'CUSTOM_TASK'],
            'MEDIUM':['INVERTERS_DISCONNECTED'],
            'COMMUNICATION_ERROR': ['GATEWAY_DISCONNECTED', 'GATEWAY_POWER_OFF']}

def get_now():
    """
    Allows to access global request and read a timestamp from query.
    """
    return datetime.datetime.now()


def get_closing_rule_for_now(contract):
    """
    Returns QuerySet of ClosingRules that are currently valid
    """
    now = get_now()

    return ClosingRules.objects.filter(contract=contract,
                                       start__lte=now, end__gte=now)


def has_closing_rule_for_now(location):
    """
    Does the company have closing rules to evaluate?
    """
    cr = get_closing_rule_for_now(location)
    return cr.count()


def is_open(contract, now=None):
    """
    Is the company currently open? Pass "now" to test with a specific
    timestamp. Can be used stand-alone or as a helper.
    """
    if now is None:
        now = get_now()

    if has_closing_rule_for_now(contract):
        return False

    now_time = datetime.time(now.hour, now.minute, now.second)

    ohs = OpeningHours.objects.filter(contract=contract)

    for oh in ohs:
        is_open = False
        # start and end is on the same day
        if (oh.weekday == now.isoweekday() and
                oh.from_hour <= now_time and
                now_time <= oh.to_hour):
            is_open = oh

        # start and end are not on the same day and we test on the start day
        if (oh.weekday == now.isoweekday() and
                oh.from_hour <= now_time and
                ((oh.to_hour < oh.from_hour) and
                    (now_time < datetime.time(23, 59, 59)))):
            is_open = oh

        # start and end are not on the same day and we test on the end day
        if (oh.weekday == (now.isoweekday() - 1) % 7 and
                oh.from_hour >= now_time and
                oh.to_hour >= now_time and
                oh.to_hour < oh.from_hour):
            is_open = oh
            # print " 'Special' case after midnight", oh

        if is_open is not False:
            return oh
    return False


def next_time_open(contract):
    """
    Returns the next possible opening hours object, or (False, None)
    if location is currently open or there is no such object
    I.e. when is the company open for the next time?
    """
    if not is_open(contract):
        now = get_now()
        now_time = datetime.time(now.hour, now.minute, now.second)
        found_opening_hours = False
        for i in range(8):
            l_weekday = (now.isoweekday() + i) % 7
            ohs = OpeningHours.objects.filter(contract=contract,
                                              weekday=l_weekday
                                              ).order_by('weekday',
                                                         'from_hour')

            if ohs.count():
                for oh in ohs:
                    future_now = now + datetime.timedelta(days=i)
                    # same day issue
                    tmp_now = datetime.datetime(future_now.year,
                                                future_now.month,
                                                future_now.day,
                                                oh.from_hour.hour,
                                                oh.from_hour.minute,
                                                oh.from_hour.second)
                    if tmp_now < now:
                        tmp_now = now  # be sure to set the bound correctly...
                    if is_open(contract, now=tmp_now):
                        found_opening_hours = oh
                        break
                if found_opening_hours is not False:
                    return found_opening_hours, tmp_now
    return False, None

def get_both_type_of_events(all_plants, starttime, endtime, open_close):
    """

    :param all_plants:
    :param starttime:
    :return:
    """
    ticket_details = get_event_tickets(all_plants, starttime, endtime, open_close)
    oandm_task_details = get_event_oandmanager_tasks(all_plants, starttime)
    result_dict = []
    result_dict.extend(ticket_details.values())
    result_dict.extend(oandm_task_details.values())
    return result_dict


def get_event_oandmanager_tasks(all_plants, starttime):
    """

    :param all_plants:
    :param starttime:
    :return:
    """
    if not starttime:
        starttime = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    starttime -= datetime.timedelta(days=1)
    all_taskitems = TaskItem.objects.filter(cycle__preferences__plant__slug__in=all_plants,
                                            scheduled_closing_date__gte=starttime,
                                            scheduled_start_date__gte=starttime,
                                            status__in=('OPEN', 'LOCKED')).\
        order_by('scheduled_closing_date')
    result_ticket_dict = {}
    CONTENT_TYPE_ID = 125
    for taskitem in all_taskitems:
        result_ticket_dict[taskitem.id] = {}
        result_ticket_dict[taskitem.id]['plant_name'] = taskitem.cycle.preferences.plant.name
        result_ticket_dict[taskitem.id]['event_type'] = "SCHEDULED_TASK" if taskitem.is_custom else "CUSTOM_TASK"
        result_ticket_dict[taskitem.id]['scheduled_start_date'] = taskitem.scheduled_start_date
        result_ticket_dict[taskitem.id]['scheduled_closing_date'] = taskitem.scheduled_closing_date
        result_ticket_dict[taskitem.id]['impact_component'] = list(taskitem.task_associations.filter(active=True).
                                                                   values_list('sensor__name', flat=True))
        result_ticket_dict[taskitem.id]['event_base_type'] = 'PREVENTIVE_EVENT'
        result_ticket_dict[taskitem.id]['latitude'] = taskitem.cycle.preferences.plant.latitude
        result_ticket_dict[taskitem.id]['longitude'] = taskitem.cycle.preferences.plant.longitude
        result_ticket_dict[taskitem.id]['losses'] = random.randrange(1,40)
        result_ticket_dict[taskitem.id]['impact'] = "--"
        result_ticket_dict[taskitem.id]['id'] = taskitem.id

        # content type id
        result_ticket_dict[taskitem.id]['ct'] = CONTENT_TYPE_ID
        result_ticket_dict[taskitem.id]['severity'] = 'LOW'

    return result_ticket_dict


def get_event_tickets(all_plants, starttime, endtime, open_close):
    """

    :param all_plants:
    :param starttime:
    :return:
    """
    # all tickets not just open , ticket__status=Ticket.OPEN_STATUS
    EVENT_TYPE = ALL_EVENTS['CORRECTIVE_EVENT'] + ALL_EVENTS["PREDICTIVE_EVENT"]
    all_ticket_association = TicketAssociation.objects.filter(ticket__queue__plant__slug__in=all_plants,
                                                                event_type__in=EVENT_TYPE).\
        select_related('ticket__queue', 'ticket__queue__plant').order_by('id')
    if open_close == "OPEN":
        all_ticket_association = all_ticket_association.filter(active=True)
    elif open_close == "CLOSE":
        all_ticket_association = all_ticket_association.filter(active=False)
    elif open_close == "BOTH":
        all_ticket_association = all_ticket_association
    else:
        return {}
    if starttime and endtime:
        all_ticket_association = all_ticket_association.filter(created__gte=starttime, created__lte=endtime)

    result_ticket_dict = {}
    CONTENT_TYPE_ID = 53
    for ticket_associate in all_ticket_association:
        detail_association = {}
        if not ticket_associate.ticket_id in result_ticket_dict:
            result_ticket_dict[ticket_associate.ticket_id] = {}
            result_ticket_dict[ticket_associate.ticket_id]['impact_capacity'] = 0.0
            result_ticket_dict[ticket_associate.ticket_id]['impact_component'] = []
            result_ticket_dict[ticket_associate.ticket_id]['alarm'] = {}
            result_ticket_dict[ticket_associate.ticket_id]['details'] = []
        result_ticket_dict[ticket_associate.ticket_id]['plant_name'] = ticket_associate.ticket.queue.plant.name
        result_ticket_dict[ticket_associate.ticket_id]['latitude'] = ticket_associate.ticket.queue.plant.latitude
        result_ticket_dict[ticket_associate.ticket_id]['longitude'] = ticket_associate.ticket.queue.plant.longitude
        result_ticket_dict[ticket_associate.ticket_id]['event_type'] = ticket_associate.ticket.event_type
        result_ticket_dict[ticket_associate.ticket_id]['tk_created_at'] = ticket_associate.ticket.created
        result_ticket_dict[ticket_associate.ticket_id]['tk_modified'] = ticket_associate.ticket.modified
        result_ticket_dict[ticket_associate.ticket_id]['ta_created'] = ticket_associate.created
        result_ticket_dict[ticket_associate.ticket_id]['ta_updated'] = ticket_associate.updated
        result_ticket_dict[ticket_associate.ticket_id]['losses'] = random.randrange(1,40)
        result_ticket_dict[ticket_associate.ticket_id]['id'] = ticket_associate.ticket_id
        # content type id
        result_ticket_dict[ticket_associate.ticket_id]['ct'] = CONTENT_TYPE_ID
        # detail association
        detail_association = {}
        detail_association['ta_id'] = ticket_associate.id
        detail_association['ta_created'] = ticket_associate.created
        detail_association['ta_updated'] = ticket_associate.updated
        detail_association['ta_active'] = ticket_associate.active
        detail_association['ta_closed'] = ticket_associate.closed

        if 'GATEWAY_POWER_OFF' == result_ticket_dict[ticket_associate.ticket_id]['event_type']:
            result_ticket_dict[ticket_associate.ticket_id]['severity'] = 'COMMUNICATION_ERROR'
            result_ticket_dict[ticket_associate.ticket_id]['event_base_type'] = 'CORRECTIVE_EVENT'
            capacity = 0.0
            try:
                virtual_gateway = VirtualGateway.objects.get(sourceKey=ticket_associate.identifier)
            except VirtualGateway.DoesNotExist:
                continue
            if not virtual_gateway.solar_group_id:
                continue
            capacity_t = virtual_gateway.solar_group.groupIndependentInverters.all(). \
                aggregate(actual_capacity=Sum('actual_capacity'))
            result_ticket_dict[ticket_associate.ticket_id]['impact_capacity'] += \
                capacity_t['actual_capacity'] if capacity_t['actual_capacity'] else 0.0
            virtual_gateway_name = virtual_gateway.name
            result_ticket_dict[ticket_associate.ticket_id]['impact_component'].append(virtual_gateway_name)
            # detail about ticket association
            detail_association['ta_component'] = virtual_gateway_name
            result_ticket_dict[ticket_associate.ticket_id]['details'].append(detail_association)
            continue

        if 'GATEWAY_DISCONNECTED' == result_ticket_dict[ticket_associate.ticket_id]['event_type']:
            result_ticket_dict[ticket_associate.ticket_id]['severity'] = 'COMMUNICATION_ERROR'
            result_ticket_dict[ticket_associate.ticket_id]['event_base_type'] = 'CORRECTIVE_EVENT'
            capacity = 0.0
            try:
                gateway_source = GatewaySource.objects.get(sourceKey=ticket_associate.identifier)
            except GatewaySource.DoesNotExist:
                continue
            for group in SolarGroup.objects.filter(groupGatewaySources=gateway_source.id):
                capacity_t = group.groupIndependentInverters.all(). \
                    aggregate(actual_capacity=Sum('actual_capacity'))
                capacity += capacity_t['actual_capacity'] if capacity_t['actual_capacity'] else 0.0
            gateway_source_name = gateway_source.name
            result_ticket_dict[ticket_associate.ticket_id]['impact_capacity'] += capacity
            result_ticket_dict[ticket_associate.ticket_id]['impact_component'].append("%s" % gateway_source_name)
            # detail about ticket association
            detail_association['ta_component'] = gateway_source_name
            result_ticket_dict[ticket_associate.ticket_id]['details'].append(detail_association)
            continue

        if 'INVERTERS_DISCONNECTED' == result_ticket_dict[ticket_associate.ticket_id]['event_type']:
            result_ticket_dict[ticket_associate.ticket_id]['severity'] = 'MEDIUM'
            result_ticket_dict[ticket_associate.ticket_id]['event_base_type'] = 'CORRECTIVE_EVENT'
            try:
                inveters = IndependentInverter.objects.get(sourceKey=ticket_associate.identifier)
            except IndependentInverter.DoesNotExist:
                continue
            result_ticket_dict[ticket_associate.ticket_id]['impact_capacity'] += inveters.actual_capacity
            inverter_name = inveters.name
            result_ticket_dict[ticket_associate.ticket_id]['impact_component'].append("%s" % inveters.name)
            # detail about ticket association
            detail_association['ta_component'] = inverter_name
            result_ticket_dict[ticket_associate.ticket_id]['details'].append(detail_association)
            continue

        if 'INVERTERS_ALARMS' == result_ticket_dict[ticket_associate.ticket_id]['event_type']:
            result_ticket_dict[ticket_associate.ticket_id]['severity'] = 'HIGH'
            result_ticket_dict[ticket_associate.ticket_id]['event_base_type'] = 'CORRECTIVE_EVENT'
            try:
                inveters = IndependentInverter.objects.get(sourceKey=ticket_associate.identifier)
            except IndependentInverter.DoesNotExist:
                continue
            result_ticket_dict[ticket_associate.ticket_id]['impact_capacity'] += inveters.total_capacity
            inverter_name = inveters.name
            result_ticket_dict[ticket_associate.ticket_id]['impact_component'].append("%s" % inverter_name)
            if not "%s" % inverter_name in result_ticket_dict[ticket_associate.ticket_id]['alarm']:
                result_ticket_dict[ticket_associate.ticket_id]['alarm']["%s" % inverter_name] = {}

            detail_association['ta_component'] = inverter_name
            # get alarm details
            detail_association['ta_component_alarm'] = []
            alarm = {}
            try:
                alarm_assiociation = ticket_associate.alarms.all().order_by('-created')
                for ala in alarm_assiociation:
                    alarm_1 = {}
                    alarm_1['alarm_code'] = ala.alarm_code
                    alarm_1['alarm_description'] = ala.alarm_description
                    alarm_1['device_status_description'] = ala.device_status_description
                    alarm_1['device_status_number'] = ala.device_status_number
                    alarm_1['created'] = ala.created
                    alarm_1['updated'] = ala.updated
                    alarm_1['closed'] = ala.closed
                    alarm_1['inverter_name'] = inverter_name
                    detail_association['ta_component_alarm'].append(alarm_1)
                    alarm = alarm_1
            except:
                alarm = {}

            result_ticket_dict[ticket_associate.ticket_id]['alarm']["%s" % inveters.name] = alarm
            result_ticket_dict[ticket_associate.ticket_id]['details'].append(detail_association)

        if 'PANEL_CLEANING' == result_ticket_dict[ticket_associate.ticket_id]['event_type']:
            result_ticket_dict[ticket_associate.ticket_id]['severity'] = 'LOW'
            result_ticket_dict[ticket_associate.ticket_id]['event_base_type'] = 'PREDICTIVE_EVENT'
            try:
                cleaning = ticket_associate.performance_associations.all().order_by('-created')[0]
                inveters = IndependentInverter.objects.get(name=cleaning.identifier,
                                                           plant=ticket_associate.ticket.queue.plant)
                cleaning_capacity = -1 * cleaning.residual if cleaning.residual < 0 else cleaning.residual
            except Exception:
                cleaning_capacity = 0.0
            result_ticket_dict[ticket_associate.ticket_id]['impact_capacity'] += cleaning_capacity
            result_ticket_dict[ticket_associate.ticket_id]['impact_component'].append("%s" % inveters.name)
            continue

    return result_ticket_dict
