from rest_framework import viewsets
from rest_framework import authentication, permissions
from oandmmanager.models import Preferences, Tasks, TaskItem, TaskAssociation, Cycle
from rest_framework.response import Response
from rest_framework import status
import logging
import datetime
from solarrms.models import SolarPlant
from solarrms.solarutils import filter_solar_plants
from dashboards.mixins import ProfileDataInAPIs
from dateutil import parser
from dataglen.models import Sensor
from django.utils import timezone
from dashboards.models import OrganizationUser

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class OandMPreferencesView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'preference_id'

    def list(self, request, plant_slug=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            preferences = Preferences.objects.filter(plant=plant)
            result = {}
            final_result = []
            for preference in preferences:
                try:
                    result["data"] = preference.serialize()
                    result["data"].pop('CUSTOM_TASK')
                    result["preference_id"] = preference.id
                    final_result.append(result)
                except:
                    continue
            return Response(data=final_result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, plant_slug=None, preference_id=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            try:
                preference = Preferences.objects.get(plant=plant, id=preference_id)
            except:
                return Response("Invalid Preference Id", status=status.HTTP_400_BAD_REQUEST)
            try:
                result= preference.serialize()
            except:
                return Response("Invalid Preference Id", status=status.HTTP_400_BAD_REQUEST)
            return Response(data=result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, plant_slug=None ,preference_id=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            try:
                plant_preference = Preferences.objects.get(plant=plant, id=preference_id)
            except:
                return Response("Invalid Preference Id", status=status.HTTP_400_BAD_REQUEST)
            slugs = self.request.query_params.get("slugs", None)
            if slugs is not None:
                try:
                    slugs = slugs.split(',')
                except:
                    return Response("Please specify comma separated slugs", status=status.HTTP_400_BAD_REQUEST)
            data = self.request.data
            for key in data.keys():
                for k in data[key].keys():
                    try:
                        if k=='enabled' and data[key][k].upper()=='FALSE':
                            data[key][k] = False
                        elif k=='enabled' and data[key][k].upper()=='TRUE':
                            data['key'][k] = True
                        else:
                            pass
                    except:
                        continue
            if slugs is not None:
                for slug in slugs:
                    try:
                        plant = SolarPlant.objects.get(slug=slug)
                        preference = Preferences.objects.get(plant=plant)
                        preference.update(data)
                    except:
                        return Response("Preference not found or multiple preferences set for the plant " + str(plant.name), status=status.HTTP_400_BAD_REQUEST)
            try:
                plant_preference.update(data)
            except:
                return Response("Invalid Format", status=status.HTTP_400_BAD_REQUEST)
            return Response("Preferences updated successfully", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OandMTasksListView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'task_id'

    def create(self, request, plant_slug=None, **kwargs):
        """
        only create custom task
        :param request:
        :param plant_slug:
        :param kwargs:
        :return:
        """
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            payload = self.request.data
            try:
                user_id = payload['user_id']
                from_date = parser.parse(payload['from_date'])
                to_date = parser.parse(payload['to_date'])
                cycle_id = payload['cycle_id']
                task_title = payload['title']
                description = payload['description']
                if to_date <= from_date:
                    raise Exception("to_date < from_date")
                associated_devices = set(
                    Sensor.objects.filter(sourceKey__in=payload['associated_devices']).values_list('id', flat=True))
                user_id = OrganizationUser.objects.get(id=user_id).user_id
            except:
                return Response(
                    "Please specify user_id, associated devices, from date, to date, cycle_id, title, description in request body",
                    status=status.HTTP_400_BAD_REQUEST)
            try:
                cycle_obj = Cycle.objects.get(id=cycle_id)
                custom_task_id = cycle_obj.preferences.associated_tasks.get(name='CUSTOM_TASK').id
            except:
                return Response("Perference for custom task not found", status=status.HTTP_400_BAD_REQUEST)
            task_item, created = TaskItem.objects.get_or_create(cycle_id=cycle_id,
                                                                task_id=custom_task_id,
                                                                scheduled_start_date=from_date,
                                                                scheduled_closing_date=to_date,
                                                                assigned_to_id=user_id,
                                                                is_custom=True)
            current_date = timezone.now().date()
            if not created:
                return Response("There is already a custom task with same from date and to date",\
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                task_item.title = task_title
                # open a task if it is current date task
                task_item.status = "OPEN" if current_date == from_date.date() else "SCHEDULED"
                task_item.description = description
                task_item.save()

            all_task_items = []
            for sourcekey in associated_devices:
                all_task_items.append(TaskAssociation(task_item_id=task_item.id,
                                                      sensor_id=sourcekey,
                                                      active=True))
            TaskAssociation.objects.bulk_create(all_task_items)
            return Response("Custom Task created successfully", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def list(self, request, plant_slug=None):
        """
        calander view from this api
        :param request:
        :param plant_slug:
        :return:
        """
        try:
            user = request.user
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)

            try:
                starttime = request.query_params["startTime"]
                endtime = request.query_params["endTime"]
                #st = parser.parse(starttime)
                #et = parser.parse(endtime)
                st = datetime.datetime.strptime(starttime, "%d/%m/%Y")
                et = datetime.datetime.strptime(endtime, "%d/%m/%Y")
                st = st.replace(hour=0, minute=0, second=0, microsecond=0)
                et = et.replace(hour=23, minute=59, second=59, microsecond=59)
            except:
                return Response("Please provide proper start, end time", status=status.HTTP_400_BAD_REQUEST)

            task_item = TaskItem.objects.filter(cycle__start_date__gte=st, cycle__end_date__lte=et,
                                                cycle__preferences__plant_id=plant.id).\
                select_related('task', 'assigned_to')
            if not task_item:
                return Response("No Cycle create for this month", status=status.HTTP_200_OK)

            if user.role.role in ('SITE_ENGINEER', 'CLIENT_SITE_ENGINEER'):
                task_item = task_item.filter(assigned_to_id=request.user_id)

            tasks_data = []
            for task_i in task_item:
                task_item_dict = dict()
                task_item_dict["task_id"] = "%s" % task_i.task_id
                task_item_dict["item_id"] = "%s" % task_i.id
                task_item_dict["title"] = "%s" % task_i.title
                task_item_dict["assigned_to"] = "%s %s" % (task_i.assigned_to.first_name,
                                                           task_i.assigned_to.last_name)
                task_item_dict["start"] = "%s" % task_i.scheduled_start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                task_item_dict["end"] = "%s" % task_i.scheduled_closing_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                task_item_dict["status"] = "%s" % task_i.status
                task_item_dict["pending_tasks"] = len(tuple(task_i.task_associations.filter(active=True)
                                                            .values_list('id', flat=True)))
                task_item_dict["completed_tasks"] = len(tuple(task_i.task_associations.filter(active=False)
                                                              .values_list('id', flat=True)))
                task_item_dict["is_custom"] = task_i.is_custom
                task_item_dict["cycle_id"] = task_i.cycle_id
                task_item_dict["description"] = task_i.description
                tasks_data.append(task_item_dict)
            return Response(data=tasks_data, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, plant_slug=None, task_id=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            preferences = Preferences.objects.filter(plant=plant)
            try:
                preference = preferences[0]
            except:
                return Response("No preference is set for this plant", status=status.HTTP_400_BAD_REQUEST)
            cycles = preference.o_and_m_cycles.all()
            try:
                task = Tasks.objects.get(id=task_id)
            except:
                return Response("Invalid Task Id", status=status.HTTP_400_BAD_REQUEST)

            final_result = []
            for cycle in cycles:
                try:
                    result = {}
                    result['table_data'] = cycle.completion_summary(task.name)[0]
                    result['header'] = cycle.completion_summary(task.name)[1]
                    final_result.append(result)
                except:
                    continue
            return Response(data=final_result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OandMTaskItemView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'item_id'

    def retrieve(self, request, plant_slug=None, item_id=None):
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            try:
                task_item = TaskItem.objects.get(id=item_id)
            except:
                return Response("Invalid Task Item Id", status=status.HTTP_400_BAD_REQUEST)
            final_result = task_item.associations_summary()
            return Response(data=final_result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, plant_slug=None, item_id=None):
        """

        :param request:
        :param plant_slug:
        :param item_id:
        :return:
        """
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            try:
                task_item = TaskItem.objects.get(id=item_id)
                assert (task_item.scheduled_start_date <= timezone.now() <= task_item.scheduled_closing_date)
            except:
                return Response("Invalid Task Item Id or Task is Locked", status=status.HTTP_400_BAD_REQUEST)
            data = self.request.data
            logger.debug(data)
            close_association = []
            open_association = []
            for key in data:
                if data['%s' % key].upper() == "TRUE":
                    open_association.append(key)
                if data['%s' % key].upper() == "FALSE":
                    close_association.append(key)
            if close_association:
                TaskAssociation.objects.filter(task_item_id=item_id, id__in=close_association).\
                    update(closed_at=timezone.now(), active=False)
            if open_association:
                TaskAssociation.objects.filter(task_item_id=item_id, id__in=open_association).\
                    update(closed_at=None, active=True)
            if task_item.open_associations() > 0:
                task_item.status = 'OPEN'
                task_item.closed_at = None
                task_item.save()
            else:
                task_item.status = 'CLOSED'
                task_item.closed_at = timezone.now()
                task_item.save()
            return Response("Tasks updated", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, plant_slug=None, item_id=None):
        """

        :param request:
        :param plant_slug:
        :param item_id:
        :return:
        """
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
                profile_data = self.get_profile_data()
                logger.debug(profile_data)
                solar_plants = filter_solar_plants(profile_data)
                if plant not in solar_plants:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            try:
                task_item = TaskItem.objects.get(id=item_id)
                task_item.delete()
            except:
                return Response("Invalid Task Item Id", status=status.HTTP_400_BAD_REQUEST)
            return Response("Task deleted successfully ", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)



