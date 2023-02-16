from solarrms.models import SolarPlant, PlantCompleteValues
from django.conf import settings
from monitoring.views import get_user_data_monitoring_status
from django.utils import timezone
import pytz
from solarrms.cron_solar_events import check_network_for_virtual_gateways
import logging
from solarrms.api_views import get_energy_prediction_data, fix_generation_units, fix_capacity_units, fix_co2_savings
from solarrms.settings import LAST_CAPACITY_DAYS
from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from dashboards.utils import is_owner
from solarrms.solarutils import filter_solar_plants
from dashboards.mixins import ProfileDataInAPIs
from solarrms.mobile_app.utils import get_client_owner_status_data_mobile_ceo, \
    get_final_non_client_owner_plant_status_data_mobile_ceo, get_client_owner_status_data_mobile_OandM_Manager,\
    get_final_non_client_owner_plant_status_data_mobile_OandM_Manager, select_plant_for_client_roles, \
    select_plant_for_clients_client_roles, get_plant_status_mobile_api
from dateutil import parser

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

class V1_Mobile_Client_Summary_CEO_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            profile_data = self.get_profile_data()
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)
            logger.debug(solar_plants)
        except Exception as exc:
            logger.debug(str(exc))
            return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

        try:
            role = str(self.request.user.role.role)
        except:
            role = 'CEO'

        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                owner=True
                solar_plants = SolarPlant.objects.filter(groupClient=user_client)
                client=user_client
        except Exception as exception:
            logger.debug(str(exception))
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)

        if str(role.upper()) in ['CEO', 'CLIENT_CEO']:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone('Asia/Kolkata'))
            if owner:
                try:
                    final_values = get_client_owner_status_data_mobile_ceo(client, current_time, solar_plants, role)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                try:
                    return Response(data=final_values, status=status.HTTP_200_OK)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                try:
                    final_values = get_final_non_client_owner_plant_status_data_mobile_ceo(solar_plants, current_time, role)
                    try:
                        return Response(data=final_values, status=status.HTTP_200_OK)
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response("You are not authorized to view this page", status=status.HTTP_403_FORBIDDEN)



class V1_Mobile_Client_Summary_OandM_Manager_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            profile_data = self.get_profile_data()
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)
            logger.debug(solar_plants)
        except Exception as exc:
            logger.debug(str(exc))
            return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

        try:
            role = str(self.request.user.role.role)
        except:
            role = 'O&M_MANAGER'

        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                owner=True
                solar_plants = SolarPlant.objects.filter(groupClient=user_client)
                client=user_client
        except Exception as exception:
            logger.debug(str(exception))
            owner, client = is_owner(self.request.user)
            solar_plants = filter_solar_plants(profile_data)

        current_time = timezone.now()
        current_time = current_time.astimezone(pytz.timezone('Asia/Kolkata'))
        if owner:
            try:
                final_values = get_client_owner_status_data_mobile_OandM_Manager(client, current_time, solar_plants, role)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            try:
                return Response(data=final_values, status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                final_values = get_final_non_client_owner_plant_status_data_mobile_OandM_Manager(solar_plants, current_time, role)
                try:
                    return Response(data=final_values, status=status.HTTP_200_OK)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class V1_Mobile_Select_Plant_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            profile_data = self.get_profile_data()
            solar_plants = filter_solar_plants(profile_data)
            logger.debug(solar_plants)
        except Exception as exc:
            logger.debug(str(exc))
            return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

        try:
            role = str(self.request.user.role.role)
        except:
            role = 'O&M_MANAGER'

        try:
            user_role = self.request.user.role.role
            user_client = self.request.user.role.dg_client
            if str(user_role) == 'CEO':
                solar_plants = SolarPlant.objects.filter(groupClient=user_client)
        except Exception as exception:
            logger.debug(str(exception))
            solar_plants = filter_solar_plants(profile_data)

        current_time = timezone.now()
        current_time = current_time.astimezone(pytz.timezone('Asia/Kolkata'))

        if str(role.upper()) in ['CEO','O&M_MANAGER', 'SITE_ENGINEER']:
            try:
                final_values = select_plant_for_client_roles(solar_plants, current_time, role)
                try:
                    return Response(data=final_values, status=status.HTTP_200_OK)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif str(role.upper()) in ['CLIENT_CEO','CLIENT_O&M_MANAGER', 'CLIENT_SITE_ENGINEER']:
            try:
                final_values = select_plant_for_clients_client_roles(solar_plants, current_time, role)
                try:
                    return Response(data=final_values, status=status.HTTP_200_OK)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            return Response("You are not authorized to view this page", status=status.HTTP_403_FORBIDDEN)


class V1_Mobile_Plant_Summary_View(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            try:
                profile_data = self.get_profile_data()
                solar_plants = filter_solar_plants(profile_data)
                logger.debug(solar_plants)
            except Exception as exc:
                logger.debug(str(exc))
                return Response("INVALID_CLIENT" ,status=status.HTTP_400_BAD_REQUEST)

            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    owner=True
                    solar_plants = SolarPlant.objects.filter(groupClient=user_client)
                    client=user_client
            except Exception as exception:
                logger.debug(str(exception))
                owner, client = is_owner(self.request.user)
                solar_plants = filter_solar_plants(profile_data)

            try:
                plant_slug = self.request.query_params.get("plant_slug", None)
            except:
                return Response("Please specify plant slug", status=status.HTTP_400_BAD_REQUEST)

            if plant_slug is None:
                return Response("Please specify plant slug", status=status.HTTP_400_BAD_REQUEST)

            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)

            if plant not in solar_plants:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)

            try:
                role = str(self.request.user.role.role)
            except:
                role = 'O&M_MANAGER'

            combined = self.request.query_params.get('combined', 'FALSE')
            if str(combined).upper() == 'TRUE':
                combined = True
            else:
                combined = False
            date = self.request.query_params.get('date',None)
            if date:
                try:
                    tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
                except:
                    tz = pytz.timezone("UTC")
                date = parser.parse(date)
                if date.tzinfo is None:
                    date = tz.localize(date)
                    date = date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                date = timezone.now()
                date = date.astimezone(pytz.timezone('Asia/Kolkata'))
            try:
                final_values = get_plant_status_mobile_api(plant, date, role, combined)
                return Response(data=final_values, status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)