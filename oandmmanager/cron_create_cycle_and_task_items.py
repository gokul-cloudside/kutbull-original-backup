import calendar
import sys
from django.utils import timezone
from datetime import timedelta
from solarrms.models import SolarPlant
from dgusers.models import UserRole
from oandmmanager.models import Preferences, Cycle, TaskItem, TaskAssociation
from django.db import transaction


MONTHLY_TASK = {1:'DAILY', 7:'WEEKLY', 30:'MONTHLY', }
OTHER_TASK = {90:'3M', 180:'6M', 365:'12M'}
ASSOCIATED_DEVICES = {'AJB', 'INVERTER' 'ENERGY_METER', 'DATA_LOGGER', 'PLANT'}
# when quaterly task will created
QUATERLY_MONTHS = (1, 4, 7, 10)
# when halfyearly task will created
HALFYEAR_MONTHS = (1, 7)
# when yearly task will created
YEARLY_MONTHS = (1,)
#alert date
ALERT_DAY = 22
#task start time
TASK_START_TIME = 8
#task gap
TASK_GAP = 15
#assign to
SITE_ENGINEER = "SITE_ENGINEER"
# dgclient
DG_CLINET = ("demo@dataglen.com", "dhananjay.nandedkar@cleanmaxsolar.com", "dataglen@edp.com")


def get_month_start_and_end_datetime(dt_current):
    """

    :param dt_month:
    :param dt_year:
    :param dt_current:
    :return:
    """
    _, last_day_of_month = calendar.monthrange(dt_current.year, dt_current.month)
    month_sd = dt_current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_ed = dt_current.replace(day=last_day_of_month, hour=23, minute=59, second=59, microsecond=59)
    return month_sd, month_ed, last_day_of_month


def get_associated_devices_for_task(plant, task_associated_devices):
    """

    :param plant:
    :return:
    """
    source_keys = []
    if task_associated_devices == "ALL":
        task_associated_devices = ASSOCIATED_DEVICES
    else:
        task_associated_devices = set([task_associated_devices])
    for device in task_associated_devices:
        if device == "AJB":
            ajb_sourcekey = list(plant.ajb_units.all().values_list('id', flat=True))
            if ajb_sourcekey:
                source_keys.extend(ajb_sourcekey)
        if device == "INVERTER":
            inverter_sourcekey = list(plant.independent_inverter_units.all().values_list('id', flat=True))
            if inverter_sourcekey:
                source_keys.extend(inverter_sourcekey)
        if device == "ENERGY_METER":
            meter_sourcekey = list(plant.energy_meters.all().values_list('id', flat=True))
            if meter_sourcekey:
                source_keys.extend(meter_sourcekey)
        if device == "PLANT":
            source_keys.extend(list(plant.metadata.plantmetasource.sensor_ptr_id))
        if device == "DATA_LOGGER":
            #Todo data logger source keys
            source_keys.extend(list(plant.metadata.plantmetasource.sensor_ptr_id))
    return set(source_keys)


def _define_task_cycle(current_date_time):
    """

    :return:
    """
    all_plants = set(SolarPlant.objects.filter(organization_ptr__users__email__in=DG_CLINET)
                     .values_list('id', flat=True))
    # Todo: optimise code use prefetch_related
    all_plant_preferences = Preferences.objects.filter(plant_id__in=all_plants)
    for plant_preference in all_plant_preferences:
        # start create cycle for current month also
        start_date, end_date, last_day_of_month = get_month_start_and_end_datetime(current_date_time)
        cycle_per_month = create_cycle_for_month(plant_preference.id, start_date, end_date)
        # end create cycle for current month also
        # start create cycle for next month also
        n_start_date, n_end_date, n_last_day_of_month = \
            get_month_start_and_end_datetime(end_date + timedelta(days=1))
        cycle_per_month_next = create_cycle_for_month(plant_preference.id, n_start_date, n_end_date)
        # end create cycle for next month also
        plant = plant_preference.plant
        user_role = UserRole.objects.filter(dg_client__slug=plant.groupClient.dataglenclient.slug, role=SITE_ENGINEER)
        if not user_role:
            continue
        user = user_role[0].user
        preference_tasks = plant_preference.associated_tasks.all().exclude(name="CUSTOM_TASK")
        for preference_task in preference_tasks:
            # condition is only for creating
            if int(preference_task.frequency) in MONTHLY_TASK:
                create_taskitem_association_for_monthly(cycle_per_month, preference_task, plant, start_date,
                                                        last_day_of_month, current_date_time, user)
            if int(preference_task.frequency) in OTHER_TASK:
                create_taskitem_association_for_others(cycle_per_month, preference_task, plant, start_date,
                                                        current_date_time, user)
        _update_taskitem(cycle_per_month, current_date_time)


def create_taskitem_association_for_others(cycle_per_month, preference_task, plant, start_date, current_date_time, user):

    """    
    :param cycle_per_month:
    :param preference_task:
    :param frequency:
    :param plant:
    :param start_date:
    :param end_date:
    :param last_day_of_month:
    :return:
    """
    task_item = None
    if start_date.date() < current_date_time.date():
        return
    task_associated_device = preference_task.associated_devices
    if task_associated_device in ASSOCIATED_DEVICES:
        return
    if current_date_time.month in QUATERLY_MONTHS:
        task_item, created = TaskItem.objects.get_or_create(cycle=cycle_per_month.id, task=preference_task.id,
                                scheduled_start_date=start_date,
                                scheduled_closing_date=start_date+timedelta(days=TASK_GAP),
                                assigned_to=user)
        if created:
            task_item.status = "SCHEDULED"
            task_item.time = TASK_START_TIME
            task_item.save()

    if current_date_time.month in HALFYEAR_MONTHS:
        task_item, created = TaskItem.objects.get_or_create(cycle=cycle_per_month.id,task=preference_task.id,
                                        scheduled_start_date=start_date,
                                        scheduled_closing_date=start_date+timedelta(days=TASK_GAP),
                                        assigned_to=user)
        if created:
            task_item.status = "SCHEDULED"
            task_item.time = TASK_START_TIME
            task_item.save()

    if current_date_time.month in YEARLY_MONTHS:
        task_item, created = TaskItem.objects.get_or_create(cycle=cycle_per_month.id,task=preference_task.id,
                                        scheduled_start_date=start_date,
                                        scheduled_closing_date=start_date+timedelta(days=TASK_GAP),
                                        assigned_to=user)
        if created:
            task_item.status = "SCHEDULED"
            task_item.time = TASK_START_TIME
            task_item.save()

    all_task_items = []
    if task_item:
        source_keys = get_associated_devices_for_task(plant, task_associated_device)
        for sourcekey in source_keys:
            all_task_items.append(TaskAssociation(task_item_id=task_item.id,
                                                  sensor=sourcekey,
                                                  active=True,
                                                  opened_at=start_date))
        TaskAssociation.objects.bulk_create(all_task_items)



def create_taskitem_association_for_monthly(cycle_per_month, preference_task, plant, start_date, last_day_of_month, current_date_time, user):
    """

    :param cycle_per_month:
    :param preference_task:
    :param frequency:
    :param plant:
    :param start_date:
    :param end_date:
    :param last_day_of_month:
    :return:
    """
    # total number of days 28 days on feb
    frequency = int(preference_task.frequency)
    recurring = int(preference_task.recurring)
    total_number_of_days = 30 if last_day_of_month in (28, 29) else last_day_of_month
    task_count = total_number_of_days // frequency
    start_date_i = start_date
    for i in range(task_count):
        close_date_i = start_date_i + timedelta(days=frequency)
        # if daily then it return frequency else recurring
        recurring_task_count = recurring if frequency > 1 else frequency
        start_date_j = start_date_i
        for j in range(recurring_task_count):
            scheduled_closing_date_divisor = 1
            if preference_task.frequency == total_number_of_days:
                scheduled_closing_date_divisor = 2
            end_date_j = start_date_j + timedelta(days=(frequency // recurring) // scheduled_closing_date_divisor)
            if start_date_j.date() < current_date_time.date():
                start_date_j = end_date_j
                continue

            # if task.associated_device are not under ASSOCIATED_DEVICES continue
            task_associated_device = preference_task.associated_devices
            if task_associated_device in ASSOCIATED_DEVICES:
                start_date_j = end_date_j
                continue
            source_keys = get_associated_devices_for_task(plant, task_associated_device)

            # if a plant don't have meter or any other device don't create the task
            if not source_keys:
                continue

            task_item, created = TaskItem.objects.get_or_create(cycle_id=cycle_per_month.id,
                                                                task_id=preference_task.id,
                                                                scheduled_start_date=start_date_j,
                                                                scheduled_closing_date=end_date_j-timedelta(seconds=1),
                                                                assigned_to=user)
            if created:
                task_item.time = TASK_START_TIME
                task_item.status = "SCHEDULED"
                task_item.save()
            else:
                continue
            all_task_items = list()
            for sourcekey in source_keys:
                # Adding current_date_time to opened_at the taskitem.
                all_task_items.append(TaskAssociation(task_item_id=task_item.id,
                                                      sensor_id=sourcekey,
                                                      active=True,
                                                      opened_at=start_date_j))
            TaskAssociation.objects.bulk_create(all_task_items)
            start_date_j = end_date_j
        start_date_i = close_date_i


def create_cycle_for_month(plant_preference_id, start_date, end_date):
    """

    :return:
    """
    #Todo : add alert_date here
    alert_date = start_date + timedelta(days=ALERT_DAY)
    try:
        cycle_obj = Cycle.objects.get(preferences_id=plant_preference_id,
                                                     start_date__gte=start_date,
                                                     end_date__lte=end_date)
    except Cycle.DoesNotExist:
        cycle_obj = Cycle.objects.create(preferences_id=plant_preference_id, start_date=start_date,
                             end_date=end_date, alert_date=alert_date, isActive = False)
        print "cycle created for this month %s" % plant_preference_id
    return cycle_obj


def _update_taskitem(cycle_per_month, current_date_time):
    """

    :return:
    """
    task_item_all = TaskItem.objects.filter(cycle=cycle_per_month).select_related('cycle', 'task')
    open_tasks = []
    scheduled_tasks = []
    for task_item in task_item_all:
        if task_item.status == "SCHEDULED" and current_date_time >= task_item.scheduled_start_date and current_date_time <= task_item.scheduled_closing_date:
            scheduled_tasks.append(task_item.id)
        if task_item.status == "OPEN" and current_date_time >= task_item.scheduled_closing_date:
            open_tasks.append(task_item.id)

    if open_tasks:
        TaskItem.objects.filter(id__in=open_tasks).update(status="LOCKED")
        TaskAssociation.objects.filter(task_item_id__in=open_tasks).update(active=False)
    if scheduled_tasks:
        TaskItem.objects.filter(id__in=scheduled_tasks).update(status="OPEN")
        TaskAssociation.objects.filter(task_item_id__in=scheduled_tasks).update(active=True)


def create_update_task_and_cycle():
    """

    :return:
    """
    try:
        with transaction.atomic():
            current_date_time = timezone.now()
            _define_task_cycle(current_date_time)
    except:
        import traceback
        print "%s" % traceback.format_exc()
        print "%s" % sys.exc_info()[0]