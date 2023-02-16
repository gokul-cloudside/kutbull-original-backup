from oandmmanager.models import Preferences, Tasks, TaskItem, TaskAssociation, Cycle
from solarrms.models import SolarPlant
import datetime
from django.utils import timezone
import pytz

# method to create and close cycle, task items and association based on the preferences.

def create_and_close_o_and_m_task():
    try:
        current_time = timezone.now()
        plants = SolarPlant.objects.filter(slug='rswm')
        for plant in plants:
            print "checking preferences for plant : " + str(plant.slug)
            try:
                try:
                    current_time = current_time.astimezone(plant.metadata.plantmetasource.dataTimezone)
                except Exception as exception:
                    print str(exception)
                    current_time = timezone.now()
                preferences = plant.o_and_m_preferences.all()
                try:
                    plant_owner = plant.groupClient.dataglenclient.owner.organization_user.user
                except:
                    plant_owner = None
                if len(preferences)>0:
                    preference = preferences[0]
                    cycle_start_day = preference.sd
                    cycle_end_day = preference.ed

                    alert_date = preference.alert_date
                    associated_tasks = preference.associated_tasks.all()
                    o_m_cycles = preference.o_and_m_cycles.all().filter(isActive=True)

                    # close the cycle and change the status of all the associated tasks.
                    if len(o_m_cycles)>0:
                        print "inside cycle"
                        cycle = o_m_cycles[0]
                        task_items = cycle.tasks.all()

                        if cycle.end_date.day == current_time.day:
                            print "inside close"
                            for task_item in task_items:
                                if task_item.status in ['SCHEDULED', 'OPEN']:
                                    task_item.status = 'LOCKED'
                                    task_item.save()
                            cycle.isActive = False
                            cycle.save()

                        else:
                            print "else"
                            for task_item in task_items:
                                if current_time.day > task_item.scheduled_closing_date.day:
                                    print "inside if"
                                    if task_item.status in ['SCHEDULED', 'OPEN']:
                                        task_item.status = 'LOCKED'
                                        task_item.save()
                                elif current_time.day == task_item.scheduled_start_date.day:
                                    print "inside elif"
                                    if task_item.status == 'SCHEDULED':
                                        task_item.status = 'OPEN'
                                        task_item.save()
                                else:
                                    print "else 2"
                                    pass

                    o_m_cycles = preference.o_and_m_cycles.all().filter(isActive=True)

                    # create new cycle and task items
                    if len(o_m_cycles)==0:
                        if current_time.day == int(cycle_start_day) and len(o_m_cycles)==0:
                            new_cycle = Cycle.objects.create(preferences=preference,
                                                             start_date=current_time,
                                                             end_date=current_time.replace(day=int(cycle_end_day)),
                                                             alert_date=current_time.replace(day=int(alert_date))
                                                             )
                            new_cycle.save()
                            for task in associated_tasks:
                                task_frequency = int(task.frequency)
                                for i in range(int(cycle_start_day)-1, int(cycle_end_day), task_frequency):
                                    try:
                                        scheduled_start_date=new_cycle.start_date+datetime.timedelta(days=i)
                                        scheduled_end_date = scheduled_start_date+datetime.timedelta(days=task_frequency-1)
                                        if scheduled_end_date>current_time.replace(day=int(cycle_end_day)):
                                            scheduled_end_date = scheduled_end_date.replace(day=int(cycle_end_day))
                                        task_item = TaskItem.objects.create(cycle=new_cycle,
                                                                            task=task,
                                                                            scheduled_start_date=scheduled_start_date,
                                                                            scheduled_closing_date=scheduled_end_date,
                                                                            status='SCHEDULED',
                                                                            assigned_to=plant_owner,
                                                                            time=current_time.hour
                                                                            )
                                        task_item.save()
                                        if task.associated_devices=='AJB':
                                            devices = plant.ajb_units.all()
                                        elif task.associated_devices=='INVERTER':
                                            devices=plant.independent_inverter_units.all()
                                        elif task.associated_devices=='ENERGY_METER':
                                            devices=plant.energy_meters.all()
                                        else:
                                            devices=[]
                                        for device in devices:
                                            task_association = TaskAssociation.objects.create(task_item=task_item,
                                                                                              sensor=device,
                                                                                              active=True,
                                                                                              opened_at=current_time)
                                            task_association.save()
                                    except Exception as exception:
                                        print str(exception)
                                        continue
            except:
                continue
    except Exception as exception:
        print str(exception)