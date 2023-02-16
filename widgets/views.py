import re
from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from django.utils import timezone
from widgets.models import Widget
from solarrms.solarutils import filter_solar_plants
from django.core.exceptions import ObjectDoesNotExist
from dashboards.mixins import ProfileDataInAPIs, ProfileDataInSolarAPIs
from dashboards.views import is_owner
from solarrms.api_views import update_tz
from dateutil import parser
from django.conf import settings

import logging
logger = logging.getLogger('widgets.models')
logger.setLevel(logging.DEBUG)

import multiprocessing as mp
import time
import multiprocessing.pool
from django.contrib.auth.models import User
import logging
from solarrms.models import *

logger = logging.getLogger('widgets.models')
logger.setLevel(logging.DEBUG)

SPLIT_TRUE_WIDGETS = [10, 31, 30]

class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)


class Pool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess


def get_widget_data((widget_id, plants_slugs, user_id, date, group_call, solar_groups)):
    # restart django's connection with mysql
    from django.db import connection
    if connection.connection:
        connection.connection.close()
    connection.connection = None

    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.query import dict_factory
    from cassandra.cqlengine import connection
    from cassandra.cqlengine import models

    auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
    cassandra_cluster = Cluster(settings.HOST_IP,
                                auth_provider=auth_provider, protocol_version=3)

    cassandra_session = cassandra_cluster.connect()
    cassandra_session.row_factory = dict_factory
    connection.set_session(cassandra_session)
    models.DEFAULT_KEYSPACE = 'dataglen_data'

    user = User.objects.get(id=user_id)
    solar_plants = list(SolarPlant.objects.filter(slug__in=plants_slugs))
    solar_groups = SolarGroup.objects.filter(id__in=solar_groups)
    group_call = group_call

    try:
        t2 = timezone.now()
        widget = Widget.objects.get(widget_id=widget_id)
        if int(widget.widget_id) in SPLIT_TRUE_WIDGETS:
            if date:
                current = True if date.date() == timezone.now().date() else False
                widget_result = widget.__getdata__(user, plants_group=solar_plants, split=True, starttime=date,
                                                   current=current, group_call=group_call, solar_groups=solar_groups)
            else:
                widget_result = widget.__getdata__(user, plants_group=solar_plants, split=True,
                                                   group_call=group_call, solar_groups=solar_groups)
        else:
            widget_result = widget.__getdata__(user, plants_group=solar_plants,
                                               group_call=group_call, solar_groups=solar_groups)
        t3 = timezone.now()

        from django import db
        db.connections.close_all()
        #logger.debug(";".join([";", str(widget_id),"WIDGET", str(widget), "START TIME", str(t2), "END TIME", str(t3), "RUN TIME", str(t3-t2), "\n"]))
        return {widget_id: widget_result}

    except Exception as exception:
        logger.exception(str(exception))
        return {}


class WidgetViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            t1 = timezone.now()
            user = self.request.user
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            result = {}
            widgets = self.request.query_params.get("widgets", None)
            date = self.request.query_params.get("date", None)
            # get group level details
            group = self.request.query_params.get("group", None)
            solar_groups = None
            group_call = False
            if group:
                try:
                    if group == "all":
                        solar_groups = plant.solar_groups.all()
                    else:
                        group = SolarGroup.objects.get(plant_id=plant.id,
                                                       id=int(re.sub("\D", "", group)))
                    group_call = True
                except SolarGroup.DoesNotExist:
                    logger.debug("solar_group not exist")
            if date:
                try:
                    date = parser.parse(date)
                    if user.role.dg_client.id == 1013:
                        # ausnet
                        date = update_tz(date, "Australia/Melbourne")
                    else:
                        date = update_tz(date, "UTC")
                except:
                    date = date
            # logger.debug(widgets)
            # logger.debug(group_call)
            # logger.debug(solar_groups)
            # logger.debug(group)
            if widgets is None:
                return Response("Please specify atleast one widget id", status=status.HTTP_400_BAD_REQUEST)
            else:
                widgets = widgets.split(",")
            t2 = timezone.now()
            # logger.debug("FIRST HALF ##########: " + str(t2 - t1))
            # logger.debug(date)
            for widget_id in widgets:
                try:
                    try:
                        widget = Widget.objects.get(widget_id=widget_id)
                    except:
                        return Response("Invalid widget id", status=status.HTTP_400_BAD_REQUEST)
                    if date is not None:
                        current = True if date.date() == timezone.now().date() else False
                        widget_result = widget.__getdata__(user, plant=plant, starttime=date, current=current,
                                                           group=group, solar_groups=solar_groups,
                                                           group_call=group_call)
                    else:
                        widget_result = widget.__getdata__(user, plant=plant, group=group,
                                                           solar_groups= solar_groups ,group_call=group_call)
                    result.update({widget_id:widget_result})
                except Exception as exception:
                    logger.debug(str(exception))
                    continue
            t3 = timezone.now()
            # logger.debug("SECOND HALF ##########: " + str(t3 - t2))

            return Response(data=result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientWidgetViewSet(ProfileDataInSolarAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            # logger.debug("#########NEW RUN#########")
            t1 = timezone.now()
            # logger.debug("START: " + str(t1))
            # get group level details
            group = self.request.query_params.get("group", None)
            solar_groups = None
            group_call = False
            all_group_ids = []
            try:
                tt1 = timezone.now()
                profile_data = self.get_profile_data()
                tt2 = timezone.now()
                #logger.debug("profile data: " + str(tt2 -tt1))

                try:
                    solar_plants = profile_data['solar_plants']#filter_solar_plants(profile_data)
                except:
                    pass

                try:
                    user_role = self.request.user.role.role
                    user_client = self.request.user.role.dg_client
                    if str(user_role) == 'CEO':
                        solar_plants = SolarPlant.objects.filter(groupClient=user_client)
                except Exception as exception:
                    logger.debug(str(exception))
                    solar_plants = profile_data['solar_plants']

                try:
                    solar_plants = sorted(solar_plants, key=lambda x: x.id)
                except:
                    solar_plants = solar_plants

                if group and group == "all":
                    try:
                        all_plant_ids = list()
                        for plant in solar_plants:
                            all_plant_ids.append(plant.id)
                        solar_groups = SolarGroup.objects.filter(plant_id__in=all_plant_ids)
                        group_call = True
                        all_group_ids = solar_groups.values_list('id', flat=True)
                    except SolarGroup.DoesNotExist:
                        logger.debug("solar_group not exist")
                user = self.request.user
                tt3 = timezone.now()
                #logger.debug("filter_solar_plants: " + str(tt3 -tt2))
                #logger.debug(solar_plants)
                date = self.request.query_params.get("date", None)
                if date:
                    try:
                        date = parser.parse(date)
                        # if user.role.dg_client.id == 1013:
                        #     # ausnet
                        #     date = update_tz(date, "Australia/Melbourne")
                        # else:
                        date = update_tz(date, "UTC")
                    except:
                        date = date
                widgets = self.request.query_params.get("widgets", None)
                if widgets is None:
                    return Response("Please specify atleast one widget id", status=status.HTTP_400_BAD_REQUEST)
                else:
                    widgets = widgets.split(",")
            except Exception as exc:
                logger.debug(str(exc))
                return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

            if len(solar_plants) >= 25:
                t2 = timezone.now()
                #logger.debug("BEFORE POOL: " + str(t2-t1))

                #pool = Pool(processes=(mp.cpu_count() - 1))
                pool = Pool(processes = len(widgets))
                slugs = [plant.slug for plant in solar_plants]
                #logger.debug(slugs)
                args = []
                for widget in widgets:
                    args.append((widget, slugs, user.id, date, group_call, all_group_ids))
                t3 = timezone.now()
                #logger.debug("BEFORE MAP: " + str(t3-t2))
                results = pool.map(get_widget_data, args)
                pool.close()
                pool.join()
                t4 = timezone.now()
                #logger.debug("BEFORE RETURN: " + str(t4-t3))
                try:
                    return Response(data=reduce(lambda r, d: r.update(d) or r, results, {}), status=status.HTTP_200_OK)
                except:
                    return Response(data=results, status=status.HTTP_200_OK)
            else:
                results = {}
                for widget_id in widgets:
                    try:
                        try:
                            widget = Widget.objects.get(widget_id=widget_id)
                        except:
                            return Response("Invalid widget id", status=status.HTTP_400_BAD_REQUEST)

                        if int(widget.widget_id) in SPLIT_TRUE_WIDGETS:
                            if date:
                                current = True if date.date() == timezone.now().date() else False
                                widget_result = widget.__getdata__(user, plants_group=solar_plants, starttime=date,
                                                                   split=True, current=current,
                                                                   solar_groups= solar_groups, group_call=group_call)
                            else:
                                widget_result = widget.__getdata__(user, plants_group=solar_plants, split=True,
                                                                   solar_groups=solar_groups, group_call=group_call)
                        else:
                            widget_result = widget.__getdata__(user, plants_group=solar_plants,
                                                               solar_groups= solar_groups ,group_call=group_call)

                        results.update({widget_id: widget_result})
                    except Exception as exception:
                        logger.debug(str(exception))
                        continue
                return Response(data=results, status=status.HTTP_200_OK)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
