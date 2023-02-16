import logging
from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from dashboards.mixins import ProfileDataInAPIs
from organizations.models import OrganizationUser, Organization
from solarrms.models import SolarPlant, SolarGroup, NewPredictionData, PredictionData, CleaningTrigger, AJB
from django.contrib.auth.models import User
from dgusers.models import UserRole, SOLAR_USER_ROLE
from solarrms.models import IndependentInverter, EnergyMeter, MPPT, PanelsString
from organizations.exceptions import OwnershipRequired
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.contrib.auth import authenticate
from solarrms.solarutils import filter_solar_plants
from features.models import UserSolarPlantWidgetsConfig, FeatureOrder, UserTableWidgetsConfig, RoleAccess
from features.settings import FEATURE_DETAILS
from features.models import CONFIG_SCOPE
import datetime
from django.utils import timezone
from dataglen.data_views import data_write
from django.conf import settings
from dateutil import parser
from solarrms.api_views import update_tz
from solarrms.views import PDFReportSummary, GenerateElectricityBill
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)
from openpyxl.writer.excel import save_virtual_workbook


class EditUserPreferences(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'user_id'

    def list(self, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user_role = self.request.user.role
            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED_BAD_REQUEST)
            owner_user_id = user_role.dg_client.owner.organization_user.user_id
            organization_set = set(Organization.objects.filter(users=owner_user_id).values_list('id', flat=True))
            solar_plant_org = SolarPlant.objects.filter(organization_ptr__in=organization_set). \
                values('organization_ptr', 'id', 'name')
            solar_plant_dict = {}
            for solar_plant in solar_plant_org:
                if not solar_plant.get('organization_ptr', None):
                    continue
                organization_ptr = solar_plant.pop('organization_ptr')
                solar_plant_dict[organization_ptr] = solar_plant
            users_all = list(OrganizationUser.objects.filter(organization_id__in=organization_set).values(
                'organization_id', 'user_id', 'user__role__role', 'user__role__daily_report',
                'user__role__sms', 'user__email', 'user__role__phone_number', 'user__role__account_suspended',
                'user__first_name', \
                'user__last_name', 'user__last_login', 'user__date_joined').exclude(user__role__role='CEO'))
            user_plant_dict = {}
            for usr in users_all:
                if not usr['user_id'] in user_plant_dict:
                    user_plant_dict[usr['user_id']] = {"role": usr['user__role__role'],
                                                       "daily_report": usr['user__role__daily_report'],
                                                       "sms": usr['user__role__sms'],
                                                       "email_id": usr['user__email'],
                                                       "phone_no": usr['user__role__phone_number'],
                                                       "user_disabled": usr['user__role__account_suspended'],
                                                       "first_name": usr['user__first_name'],
                                                       "last_name": usr['user__last_name'],
                                                       "last_login": usr['user__last_login'],
                                                       "date_joined": usr['user__date_joined'],
                                                       "plants":[]}

                if not solar_plant_dict.get(usr['organization_id'], None):
                    continue
                else:
                    user_plant_dict[usr['user_id']]['plants'].append(solar_plant_dict[usr['organization_id']])
            #user for which plants are not assigned
            all_user_no_plants = UserRole.objects.filter(dg_client=user_role.dg_client).\
                                                     exclude(user__id__in=user_plant_dict).exclude(role='CEO').\
                values('user_id', 'user__role__role', 'user__role__daily_report',
                'user__role__sms', 'user__email', 'user__role__phone_number', 'user__role__account_suspended',
                'user__first_name',
                'user__last_name', 'user__last_login', 'user__date_joined')
            for usr in all_user_no_plants:
                user_plant_dict[usr['user_id']] = {"role": usr['user__role__role'],
                                                   "daily_report": usr['user__role__daily_report'],
                                                   "sms": usr['user__role__sms'],
                                                   "email_id": usr['user__email'],
                                                   "phone_no": usr['user__role__phone_number'],
                                                   "user_disabled": usr['user__role__account_suspended'],
                                                   "first_name": usr['user__first_name'],
                                                   "last_name": usr['user__last_name'],
                                                   "last_login": usr['user__last_login'],
                                                   "date_joined": usr['user__date_joined'],
                                                   "plants":[]}
            #all plants
            plants = SolarPlant.objects.filter(organization_ptr__in=organization_set).values('id', 'name')
            master_dict_user_preferences = {}
            master_dict_user_preferences['user_details_dict'] = user_plant_dict
            master_dict_user_preferences['list_of_all_plants'] = plants
            return Response(data=master_dict_user_preferences, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list edituserpreferences: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, user_id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user_role = self.request.user.role
            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            owner_user_id = user_role.dg_client.owner.organization_user.user_id
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response("User does not exist", status=status.HTTP_400_BAD_REQUEST)
            # get all org of owner user
            organization_set = Organization.objects.filter(users=owner_user_id)
            # get all user of this owner user
            """users_all = set(OrganizationUser.objects.filter(
                organization_id__in=set(organization_set.values_list('id', flat=True))).values_list('user_id', flat=True))"""
            users_all = UserRole.objects.filter(dg_client=user_role.dg_client).values_list('user_id', flat=True)
            if not int(user_id) in users_all:
                return Response("User not belong to same organization", status=status.HTTP_401_UNAUTHORIZED)
            # filter other organization of requested user_id
            organization_set = set(organization_set.filter(users=user_id).values_list('id', flat=True))
            solar_plant_org = dict(SolarPlant.objects.filter(organization_ptr__in=organization_set). \
                                   values_list('id', 'name'))
            user_plant_dict = {}
            user_plant_dict[user.id] = {"role": user.role.role,
                                        "daily_report": user.role.daily_report,
                                        "sms": user.role.sms,
                                        "email_id": user.email,
                                        "phone_no": user.role.phone_number,
                                        "user_disabled": user.role.account_suspended,
                                        "first_name": user.first_name,
                                        "last_name": user.last_name,
                                        "last_login": user.last_login,
                                        "date_joined": user.date_joined,
                                        "plants": solar_plant_org}
            return Response(data=user_plant_dict, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in retrieve edituserpreferences: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, user_id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user_role = self.request.user.role
            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            with transaction.atomic():
                payload = self.request.data
                user = User.objects.get(id=user_id)
                user_role = UserRole.objects.get(user_id=user_id)
                organization_list = set(
                    user.organizations_organizationuser.all().values_list('organization_id', flat=True))
                """users_all = OrganizationUser.objects.filter(organization_id__in=organization_list). \
                    values_list('user_id', flat=True)"""
                users_all = UserRole.objects.filter(dg_client=user_role.dg_client).values_list('user_id', flat=True)
                accessible_roles = set([item[0] for item in SOLAR_USER_ROLE])
                if user.id in users_all:
                    dict_changes = payload
                    update_data_dict_key = set(dict_changes.keys())
                    logger.debug("List of elements to change")
                    if 'first_name' in update_data_dict_key:
                        user.first_name = dict_changes['first_name']
                    if 'last_name' in update_data_dict_key:
                        user.last_name = dict_changes['last_name']
                    if 'email_id' in update_data_dict_key:
                        user.email = dict_changes['email_id']
                    if 'phone_no' in update_data_dict_key:
                        user_role.phone_number = int(dict_changes['phone_no'])
                    if 'user_disabled' in update_data_dict_key:
                        user_role.account_suspended = int(dict_changes['user_disabled'])

                    if 'role' in update_data_dict_key and (str(dict_changes['role']).upper() in accessible_roles):
                        user_role.role = str(dict_changes['role']).upper()
                    if 'daily_report' in update_data_dict_key:
                        user_role.daily_report = dict_changes['daily_report']
                    if 'sms' in update_data_dict_key:
                        user_role.sms = dict_changes['sms']
                    if 'plants' in update_data_dict_key:
                        current_plants_obj = SolarPlant.objects.filter(organization_ptr__in=organization_list)
                        current_plants = current_plants_obj.values_list('id', flat=True)
                        new_plants_list = dict_changes['plants']
                        # from front end it will it will come with all the plant_ids
                        if new_plants_list:
                            to_delete_plants = set(current_plants) - set(new_plants_list)
                            logger.debug("To delete plants %s" % to_delete_plants)
                            to_add_plants = set(new_plants_list) - set(current_plants)
                            logger.debug("To add Plants %s" % to_add_plants)
                            if to_delete_plants:
                                user.organizations_organizationuser.filter(organization_id__in=to_delete_plants). \
                                    delete()
                            for add_plant in SolarPlant.objects.filter(id__in=to_add_plants):
                                user.organizations_organizationuser.create(organization_id=add_plant.id)
                        else:
                            logger.debug("New Plants List Should be a List")
                    user.save()
                    user_role.save()
                else:
                    logger.debug("User email is not present %s" % user_id)
                return Response('User preferences changed!', status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in getting device details of User with user id %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EditPlantPreferences(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'plant_id'

    def list(self, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user_role = self.request.user.role
            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            owner_user_id = user_role.dg_client.owner.organization_user.user_id
            organization_set = set(Organization.objects.filter(users=owner_user_id).values_list('id', flat=True))
            plants = SolarPlant.objects.filter(organization_ptr__in=organization_set)
            """users_all_list = list(OrganizationUser.objects.filter(organization_id__in=organization_set) \
                                  .values('user_id', 'user__email').exclude(user__role__role='CEO'))"""
            users_all_list = UserRole.objects.filter(dg_client=user_role.dg_client).\
                values('user_id', 'user__email').exclude(user__role__role='CEO')
            dict_users_all_list = {}
            for item in users_all_list:
                dict_users_all_list[item['user_id']] = item
            users_all = dict_users_all_list.values()
            plant_detail_dict = {}
            all_tags = []
            for plant in plants:
                all_plant_users = plant.organization_users.all().exclude(user__role__role='CEO'). \
                    values('user__email', 'user__first_name', 'user__last_name', 'user__role__phone_number', 'user_id')

                all_groups_of_a_plant = plant.solar_groups.all()
                groups_data = {}
                for group in all_groups_of_a_plant:

                    inv_list = group.groupIndependentInverters.all()
                    inv_data = {}

                    for inverter in inv_list:
                        inv_data[inverter.id] = {'dc_capacity': inverter.actual_capacity,
                                                 'name': inverter.name,
                                                 'model': inverter.model,
                                                 'serial_number': inverter.serial_number}
                    sensors_list = group.groupIOSensors.all()
                    print "inverters are done"
                    sensor_data = {}
                    for sensor in sensors_list:
                        if sensor.stream_type in sensor_data:
                            sensor_data[sensor.stream_type].append({'sensor_id': sensor.id, \
                                                                    'sensor_name': sensor.solar_field.displayName})
                        else:
                            sensor_data[sensor.stream_type] = [{'sensor_id': sensor.id, \
                                                                'sensor_name': sensor.solar_field.displayName}]
                    groups_data[group.id] = {'roof_name': group.name, 'datalogger_id': group.data_logger_device_id, \
                                            'inverters_list': inv_data, 'sensors_list': sensor_data}
                data = {}
                for item in all_plant_users:
                    key = item.pop('user_id')
                    item['email_id'] = item.pop('user__email')
                    item['first_name'] = item.pop('user__first_name')
                    item['last_name'] = item.pop('user__last_name')
                    item['phone_no'] = item.pop('user__role__phone_number')
                    data[key] = item
                all_plant_users = data
                plant_current_tags = set(plant.tags.values_list('name', flat=True))
                all_tags = all_tags + list(plant_current_tags)
                plant_detail_dict[int(plant.id)] = {'plant_name': plant.name,
                                                    'plant_capacity': plant.capacity,
                                                    'plant_location': plant.location,
                                                    'plant_longitude': plant.longitude,
                                                    'plant_latitude': plant.latitude,
                                                    'plant_elevation': plant.elevation,
                                                    'plant_tags': plant_current_tags,
                                                    'user_basic_info': all_plant_users,
                                                    'all_groups_data': groups_data}
                # get inverter details
                inverters = plant.independent_inverter_units.all(). \
                    values('actual_capacity', 'name', 'manufacturer', 'model', 'orientation', 'serial_number', \
                           'tilt_angle', 'total_capacity', 'id')
                inverter_details = {}
                no_of_inverters = 0
                for inverter in inverters:
                    inverter_details["%s" % inverter['id']] = {'dc_capacity': inverter['actual_capacity'],
                                                               'name': inverter['name'],
                                                               'manufacturer': inverter['manufacturer'],
                                                               'model': inverter['model'],
                                                               'orientation': inverter['orientation'],
                                                               'serial_number': inverter['serial_number'],
                                                               'tilt_angle': inverter['tilt_angle'],
                                                               'ac_capacity': inverter['total_capacity']}
                    no_of_inverters += 1
                plant_detail_dict[int(plant.id)]['inverter_details'] = inverter_details
                plant_detail_dict[int(plant.id)]['no_of_inverters'] = no_of_inverters
                # get meter details
                energy_meters = plant.energy_meters.all().values('name', 'manufacturer', 'model', 'id')
                energy_meter_details = {}
                for meter in energy_meters:
                    energy_meter_details["%s" % meter['id']] = {
                        'name': meter['name'],
                        'manufacturer': meter['manufacturer'],
                        'model': meter['model']
                    }
                plant_detail_dict[int(plant.id)]['energy_meter_details'] = energy_meter_details
            master_dict_plant_preferences = {}
            master_dict_plant_preferences['plant_details_dict'] = plant_detail_dict
            master_dict_plant_preferences['list_of_all_users'] = users_all
            master_dict_plant_preferences['all_available_tags'] = list(set(all_tags))

            return Response(data=master_dict_plant_preferences, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in retrieve editplantpreference :%s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def retrieve(self, request, plant_id=None, **kwargs):
        """
        :param request:
        :param plant_id:
        :param kwargs:
        :return:
        """
        try:
            try:
                plant_id = int(plant_id)
            except:
                Response("Wrong Query Parameter. Should be Integer", status=status.HTTP_400_BAD_REQUEST)

            user_role = self.request.user.role
            owner_user_id = user_role.dg_client.owner.organization_user.user_id
            organization_set = set(Organization.objects.filter(users=owner_user_id).values_list('id', flat=True))
            plants_list = set(SolarPlant.objects.filter(organization_ptr__in=organization_set).values_list('id', flat=True))

            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            if not plant_id in plants_list:
                return Response("User not authorised to change this plant details. Plant not in Client's plants list.",
                                status=status.HTTP_401_UNAUTHORIZED)
            try:
                plant = SolarPlant.objects.get(id=plant_id)
            except SolarPlant.DoesNotExist:
                return Response("Plant does not exist", status=status.HTTP_400_BAD_REQUEST)
            plant_detail_dict = {}
            all_plant_users = plant.organization_users.all().exclude(user__role__role='CEO'). \
                values('user__email', 'user__first_name', 'user__last_name', 'user__role__phone_number', 'user_id')
            data = {}
            for item in all_plant_users:
                key = item.pop('user_id')
                item['email_id'] = item.pop('user__email')
                item['first_name'] = item.pop('user__first_name')
                item['last_name'] = item.pop('user__last_name')
                item['phone_no'] = item.pop('user__role__phone_number')
                data[key] = item
            all_plant_users = data
            plant_current_tags = set(plant.tags.values_list('name', flat=True))
            plant_detail_dict[int(plant.id)] = {'plant_name': plant.name, 'plant_capacity': plant.capacity,
                                                'plant_location': plant.location, 'plant_longitude': plant.longitude,
                                                'plant_latitude': plant.latitude,
                                                'plant_elevation': plant.elevation,
                                                'plant_tags': plant_current_tags,
                                                'user_basic_info': all_plant_users}
            # get inverter details
            inverters = plant.independent_inverter_units.all()
            inverter_details = {}
            no_of_inverters = 0
            for inverter in inverters:
                mppt_dict = {}
                all_mppts = inverter.mppt_units.all()
                for mppt in all_mppts:

                    all_strings = mppt.panels_strings.all()
                    strings_dict = {}
                    for string in all_strings:
                        panels_make = "%s %s" % (plant.metadata.panel_manufacturer, plant.metadata.model_number)
                        strings_dict[string.id] = {'name': string.name,
                                                   'no_of_panels_per_string': string.number_of_panels,
                                                   'panels_make': panels_make,
                                                   'orientation': string.orientation,
                                                   'tilt_angle': string.tilt_angle}
                    mppt_dict[mppt.id] = {'mppt_name': mppt.name,
                                          'mppt_total_strings': mppt.strings_per_mppt,
                                          'mppt_total_panels': mppt.total_panels(),
                                          'strings_details': strings_dict}

                inverter_details[inverter.id] = {'inverter_group_or_roof_name': inverter.solar_groups.all()[0].name if inverter.solar_groups.all() else "" ,
                                                 'inverter_group_or_roof_id': inverter.solar_groups.all()[0].id if inverter.solar_groups.all() else "" ,
                                                 'dc_capacity': inverter.actual_capacity,
                                                 'name': inverter.name,
                                                 'manufacturer': inverter.manufacturer,
                                                 'model': inverter.model,
                                                 'orientation': inverter.orientation,
                                                 'serial_number': inverter.serial_number,
                                                 'tilt_angle': inverter.tilt_angle,
                                                 'ac_capacity': inverter.total_capacity,
                                                 'mppt_details': mppt_dict}

                no_of_inverters += 1
            plant_detail_dict[int(plant.id)]['inverter_details'] = inverter_details
            plant_detail_dict[int(plant.id)]['no_of_inverters'] = no_of_inverters
            # get meter details
            energy_meters = plant.energy_meters.all().values('name', 'manufacturer', 'model', 'id')
            energy_meter_details = {}
            for meter in energy_meters:
                energy_meter_details["%s" % meter['id']] = {
                    'name': meter['name'],
                    'manufacturer': meter['manufacturer'],
                    'model': meter['model']
                }
            plant_detail_dict[int(plant.id)]['energy_meter_details'] = energy_meter_details
            plant_list_of_all_groups_or_roofs = plant.solar_groups.all().values('id', 'name')
            plants_combined_dict = {'plant_details_dict' : plant_detail_dict, \
                                    'plants_list_of_all_groups_or_roofs' : plant_list_of_all_groups_or_roofs}

            return Response(data=plants_combined_dict, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in retrieve edit plant preference :%s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, plant_id=None, **kwargs):
        """
        :param request:
        :param plant_id:
        :param kwargs:
        :return:
        """
        try:
            user_role = self.request.user.role
            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            owner_user_id = user_role.dg_client.owner.organization_user.user_id
            organization_set = set(Organization.objects.filter(users=owner_user_id).values_list('id', flat=True))
            plants_list = set(
                SolarPlant.objects.filter(organization_ptr__in=organization_set).values_list('id', flat=True))
            if not int(plant_id) in plants_list:
                return Response("User not authorised to change this plant details", status=status.HTTP_401_UNAUTHORIZED)
            payload = self.request.data
            if not payload:
                return Response("No Payload Found", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            flag = ""
            with transaction.atomic():
                plant_id = int(plant_id)
                plant = SolarPlant.objects.get(id=int(plant_id))
                plant_meta_data = set(payload.keys()) - set(['inverter_details', 'user_basic_info', \
                                                             'energy_meter_details','user_basic_info','plant_tagging',\
                                                             'group_renaming'])

                if plant_meta_data:
                    logger.debug("Changing plant metadata")
                    plant_data_to_change = set(payload.keys())
                    # logger.debug(plant_data_to_change)
                    if 'plant_name' in plant_data_to_change:
                        plant.name = payload['plant_name']
                    if 'plant_capacity' in plant_data_to_change:
                        plant.capacity = payload['plant_capacity']
                    if 'plant_location' in plant_data_to_change:
                        plant.location = payload['plant_location']
                    if 'plant_longitude' in plant_data_to_change:
                        plant.longitude = payload['plant_longitude']
                    if 'plant_latitude' in plant_data_to_change:
                        plant.latitude = payload['plant_latitude']
                    if 'plant_elevation' in plant_data_to_change:
                        plant.elevation = payload['plant_elevation']
                    plant.save()
                    flag = "Plant metadata saved"
                    logger.debug("Plant metadata saved")
                else:
                    logger.debug("Plant Meta Data not changed")
                # inverter update
                if "inverter_details" in payload:
                    logger.debug("Changing inverter metadata")
                    inverter_id = payload['inverter_details'].keys()[0]
                    inverter_data_to_change = set(payload['inverter_details'][inverter_id])
                    # logger.debug(inverter_data_to_change)
                    if inverter_id:
                        inverter_payload = payload['inverter_details'][inverter_id]
                        inverters_in_plant = plant.independent_inverter_units.all()
                        inverter = IndependentInverter.objects.get(id=int(inverter_id))
                        # Creating a tuple just to save a query
                        if inverter in inverters_in_plant:
                            if 'dc_capacity' in inverter_data_to_change:
                                inverter.actual_capacity = inverter_payload['dc_capacity']
                            if 'name' in inverter_data_to_change:
                                inverter.name = inverter_payload['name']
                            if 'manufacturer' in inverter_data_to_change:
                                inverter.manufacturer = inverter_payload['manufacturer']
                            if 'model' in inverter_data_to_change:
                                inverter.model = inverter_payload['model']
                            if 'orientation' in inverter_data_to_change:
                                inverter.orientation = inverter_payload['orientation']
                            if 'serial_number' in inverter_data_to_change:
                                inverter.serial_number = inverter_payload['serial_number']
                            if 'tilt_angle' in inverter_data_to_change:
                                inverter.tilt_angle = inverter_payload['tilt_angle']
                            if 'ac_capacity' in inverter_data_to_change:
                                inverter.total_capacity = inverter_payload['ac_capacity']
                            if 'mppt_details' in inverter_data_to_change:
                                logger.debug("Changing mppt details")
                                all_mppts_in_inverter = inverter.mppt_units.all()
                                if "new_mppt_details" in inverter_payload['mppt_details'].keys():
                                    logger.debug("Adding new mppt")
                                    new_mppt_details_dict = inverter_payload['mppt_details']['new_mppt_details']
                                    mppt_name = new_mppt_details_dict['mppt_name']
                                    strings_per_mppt = new_mppt_details_dict['strings_per_mppt']
                                    modules_per_string = new_mppt_details_dict['modules_per_string']
                                    mppt_already_exists = all_mppts_in_inverter.filter(name = mppt_name)
                                    if len(mppt_already_exists)>0:
                                        logger.debug('mppt already exists ')
                                        raise Exception("MPPT Name already exists. Please Specify Different Name")
                                    else:
                                        logger.debug("MPPT not present. Creating New MPPT")
                                        mppt = MPPT.objects.create(plant=plant,
                                                                   user=self.request.user,
                                                                   independent_inverter=inverter,
                                                                   name=mppt_name,
                                                                   isActive=True,
                                                                   isMonitored=True,
                                                                   dataFormat='JSON',
                                                                   strings_per_mppt=strings_per_mppt,
                                                                   modules_per_string=modules_per_string)
                                        if mppt:
                                            current_number_of_mppts = inverter.number_of_mppts
					    if current_number_of_mppts:
                                                inverter.number_of_mppts = current_number_of_mppts + 1
					    else:
						inverter.number_of_mppts = 1
                                            panel_string = []
                                            for i in range(strings_per_mppt):
                                                panel_string.append(PanelsString(name="String_No_%s" % i, mppt_id=mppt.id,\
                                                                                 number_of_panels=modules_per_string))
                                            PanelsString.objects.bulk_create(panel_string)
                                elif "delete_mppt" in inverter_payload['mppt_details'].keys():
                                    logger.debug("About to delete mppt ------------------")
                                    mppt_id_to_delete = inverter_payload['mppt_details']['delete_mppt']
                                    MPPT.objects.get(id = mppt_id_to_delete).delete()
                                    current_number_of_mppts = inverter.number_of_mppts
                                    inverter.number_of_mppts = current_number_of_mppts - 1
                                    logger.debug("Deleted MPPT with ID : %s" % mppt_id_to_delete)
                                else:
                                    mppt_id_to_change = inverter_payload['mppt_details'].keys()[0]
                                    mppt_data_to_change = inverter_payload['mppt_details'][mppt_id_to_change]

                                    mppt_obj = MPPT.objects.get(id=int(mppt_id_to_change))

                                    if mppt_obj in all_mppts_in_inverter:
                                        logger.debug("Changing of mppt is allowed")
                                        if 'mppt_name' in mppt_data_to_change:
                                            mppt_obj.name = mppt_data_to_change['mppt_name']
                                            mppt_obj.save()

                                        elif 'add_new_string' in mppt_data_to_change:
                                            logger.debug("Adding string to mppt")
                                            all_strings = mppt_obj.panels_strings.all()

                                            new_string_dict = mppt_data_to_change['add_new_string']
                                            string_name = new_string_dict['name']
                                            number_of_panels = new_string_dict['no_of_panels_per_string']
                                            string_orientation = new_string_dict['orientation']
                                            tilt_angle = new_string_dict['tilt_angle']

                                            string_check = all_strings.filter(name = string_name)
                                            if len(string_check) > 0 :
                                                raise Exception("String Name already Exists. Choose Different String Name")
                                            else:
                                                panel_string = PanelsString.objects.create(name = string_name,
                                                                                           mppt=mppt_obj,
                                                                                           number_of_panels=number_of_panels,
                                                                                           orientation = string_orientation,
                                                                                           tilt_angle = tilt_angle)
                                                # panel_string.save()

                                        elif 'delete_string' in mppt_data_to_change:
                                            logger.debug("Deleting string from mppt")
                                            delete_string_id = mppt_data_to_change['delete_string']

                                            PanelsString.objects.get(id = delete_string_id).delete()
                                            logger.debug("String Deleted successfully, id =  %s" % delete_string_id)

                                        elif 'strings_details' in mppt_data_to_change:
                                            logger.debug("changing string details")
                                            string_id_to_change = mppt_data_to_change['strings_details'].keys()[0]
                                            string_data_to_change = mppt_data_to_change['strings_details'][
                                                string_id_to_change]
                                            all_mppt_strings = mppt_obj.panels_strings.all()
                                            string_obj = PanelsString.objects.get(id=string_id_to_change)

                                            if string_obj in all_mppt_strings:
                                                logger.debug("change string allowed")

                                                if 'name' in string_data_to_change:
                                                    string_obj.name = string_data_to_change['name']
                                                if 'tilt_angle' in string_data_to_change:
                                                    string_obj.tilt_angle = string_data_to_change['tilt_angle']
                                                if 'orientation' in string_data_to_change:
                                                    string_obj.orientation = string_data_to_change['orientation']
                                                if 'no_of_panels_per_string' in string_data_to_change:
                                                    string_obj.number_of_panels = string_data_to_change['no_of_panels_per_string']

                                                string_obj.save()
                                                logger.debug("string saved %s" % string_id_to_change)
                            inverter.save()
                            flag = flag + "Inverter Details Changed"
                        else:
                            logger.debug("User is not allowed to change this inverter details %s" \
                                         % inverter.name)
                else:
                    logger.debug("Inverter details not changed")
                # meter update
                if "energy_meter_details" in payload:
                    logger.debug("Changing energy_meter_details metadata")
                    meter_id = payload['energy_meter_details'].keys()[0]
                    meter_data_to_change = payload['energy_meter_details'][meter_id]
                    # logger.debug(meter_data_to_change)
                    if meter_id:
                        meter_payload = payload['energy_meter_details'][meter_id]
                        meters_in_plant = plant.energy_meters.all()
                        meter = EnergyMeter.objects.get(id=int(meter_id))
                        if meter in meters_in_plant:
                            if 'name' in meter_data_to_change:
                                meter.name = meter_payload['name']
                            if 'manufacturer' in meter_data_to_change:
                                meter.manufacturer = meter_payload['manufacturer']
                            if 'model' in meter_data_to_change:
                                meter.model = meter_payload['model']
                            meter.save()
                        else:
                            logger.debug("Meter not in Plants Meter list : %" % meter.name)
                        flag = flag + "Energy Meter Data Changed"
                else:
                    logger.debug("key energy meter not found in payload")
                # userinfo update
                if "user_basic_info" in payload:
                    logger.debug("Changing users in plant preferences %s " % plant.name)
                    list_of_user_ids = payload['user_basic_info']
                    current_users = plant.organization_users.all().exclude(user__role__role='CEO')
                    if list_of_user_ids:
                        list_of_current_users = []
                        for or_user in current_users:
                            user = or_user.user
                            list_of_current_users.append(user)
                        list_of_final_users = []
                        for user_id in list_of_user_ids:
                            final_user = User.objects.get(id=user_id)
                            list_of_final_users.append(final_user)
                        to_delete_users = set(list_of_current_users) - set(list_of_final_users)
                        to_add_users = set(list_of_final_users) - set(list_of_current_users)
                        for del_user in to_delete_users:
                            del_organizationuser = current_users.get(user_id=del_user.id,
                                                                     organization_id=plant.organization_ptr_id)
                            del_organizationuser.delete()
                        for add_user in to_add_users:
                            if str(user_role).upper().startswith("CLIENT"):
                                admin = False
                            else:
                                admin = True
                            plant_ = SolarPlant.objects.filter(id=plant_id)
                            if plant_:
                                plant = plant_[0]
                            organization_user = OrganizationUser.objects.create(user=add_user,
                                                                                organization=plant,
                                                                                is_admin=admin)
                            organization_user.save()
                    else:
                        logger.debug("Deleting all users for plant %s" % plant.name)
                        for current_user in current_users:
                            current_user.delete()
                    flag = flag + "User basic info changed!"
                else:
                    logger.debug("key user_basic_info not found in payload")
                if "group_renaming" in payload:
                    # logger.debug("Altering groups")
                    all_group_ids_for_this_plant = plant.solar_groups.all().values_list('id', flat=True)
                    group_payload = payload['group_renaming']

                    if group_payload:
                        group_id = group_payload.keys()[0]
                        if int(group_id) in all_group_ids_for_this_plant:
                            try:
                                group_obj = SolarGroup.objects.get(id = int(group_id))
                            except SolarGroup.DoesNotExist:
                                logger.debug("SolarGroup Doesnt exists")
                                raise Exception("Solar group doesnt exist")
                            group_data = group_payload[group_id]
                            if "roof_name" in group_data:
                                group_obj.name = group_data['roof_name']
                                group_obj.displayName = group_data['roof_name']
                            if "datalogger_id" in group_data:
                                group_obj.data_logger_device_id = group_data['datalogger_id']
                            group_obj.save()
                        else:
                            raise Exception("GroupId does not belong to the Plant. Wrong Group ID")
                    flag = flag + "Group Renaming Done"
                elif "group_creation" in payload:
                    logger.debug("Adding New Group ++++++++++++   +   ++++++++++++")
                    create_group_payload = payload['group_creation']
                    group_name = create_group_payload['group_name'].strip()
                    data_logger_device_id = create_group_payload['datalogger_id'].strip() if 'datalogger_id' in create_group_payload else ''
                    if group_name:
                        SolarGroup.objects.create(name=group_name, plant=plant, displayName=group_name,
                                                  data_logger_device_id=data_logger_device_id, user=self.request.user)
                    else:
                        raise Exception("Please provide valid group name")
                    flag = flag + "Group Created"
                elif "delete_group" in payload:
                    logger.debug("Deleting Existing Group -----------------")
                    delete_group_id = payload['delete_group']
                    all_group_ids_for_this_plant = plant.solar_groups.all().values_list('id', flat=True)
                    if delete_group_id in all_group_ids_for_this_plant:
                        try:
                            group_obj = SolarGroup.objects.get(id=int(delete_group_id))
                            group_obj.delete()
                            logger.debug("Group Deleted with ID :%s " % delete_group_id)
                        except SolarGroup.DoesNotExist:
                            logger.debug("SolarGroup Doesnt exists")
                            raise Exception("Solar group doesnt exist")
                    flag = flag + "Group Deleted"
                elif "add_inverter_to_a_group" in payload:
                    logger.debug("Adding inverter to a group")
                    add_inverter_payload = payload['add_inverter_to_a_group']
                    group_key = add_inverter_payload.keys()[0]
                    inverter_id = add_inverter_payload[group_key]
                    # Check if inverter exists and belongs to plant
                    try:
                        inverter_to_add = plant.independent_inverter_units.all().get(id=int(inverter_id))
                    except Exception as exception:
                        logger.debug("Inverter Not found")
                        raise Exception("Invalid Inverter ID")
                    # Check if group exists and belongs to the plant
                    try:
                        group_obj = plant.solar_groups.get(id=int(group_key))
                    except SolarGroup.DoesNotExist:
                        logger.debug("SolarGroup Doesnt exists")
                        raise Exception("Solar group doesnt exist")
                    # Now check weather inverter already has any associations with group
                    existing_groups_for_inverter = inverter_to_add.solar_groups.all()
                    # if inverter is already member of a group then remove it from that group or remove group from inverter
                    if len(existing_groups_for_inverter)>0:
                        for gr in existing_groups_for_inverter:
                            inverter_to_add.solar_groups.remove(gr)
                    # as now inverter does not belong to any group now its ready to add
                    group_obj.groupIndependentInverters.add(inverter_to_add)
                    flag = flag + "Inverter Added to group"
                elif "remove_inverter_from_a_group" in payload:
                    logger.debug("Removing inverter from a group")
                    remove_inverter_payload = payload['remove_inverter_from_a_group']
                    group_key = remove_inverter_payload.keys()[0]
                    inverter_id_to_remove = int(remove_inverter_payload[group_key])

                    all_plant_inverters = set(plant.independent_inverter_units.all().values_list('id',flat=True))
                    all_plant_groups = list(plant.solar_groups.all().values_list('id',flat=True))
                    if int(group_key) in all_plant_groups and inverter_id_to_remove in all_plant_inverters:
                        try:
                            group_obj = SolarGroup.objects.get(id=int(group_key))
                            inverter_obj_to_remove = IndependentInverter.objects.get(id=inverter_id_to_remove)
                            group_obj.groupIndependentInverters.remove(inverter_obj_to_remove)
                            logger.debug("inverter removed from a group")

                        except SolarGroup.DoesNotExist:
                            logger.debug("SolarGroup Doesnt exists")
                            raise Exception("Solar group doesnt exist")
                        except IndependentInverter.DoesNotExist:
                            raise Exception("inverter id not found")
                    flag = flag + "Inverter removed from Group"

                elif "alter_inverter_group_association" in payload:
                    logger.debug("Altering inverter group assocciation +++++_--------*****/////")
                    alter_i_g_payload = payload['alter_inverter_group_association']
                    inverter_key = alter_i_g_payload.keys()[0]

                    remove_inverter_from_this_group_key = int(alter_i_g_payload[inverter_key]['from'])
                    add_inverter_to_this_group_key = int(alter_i_g_payload[inverter_key]['to'])


                    all_plant_inverters = set(plant.independent_inverter_units.all().values_list('id', flat=True))

                    all_plant_groups = list(plant.solar_groups.all().values_list('id', flat=True))
                    if int(remove_inverter_from_this_group_key) in all_plant_groups and int(inverter_key) in all_plant_inverters:
                        try:
                            inverter_obj = IndependentInverter.objects.get(id=inverter_key)

                            remove_inverter_from_this_group_obj = SolarGroup.objects.get(id=int(remove_inverter_from_this_group_key))
                            remove_inverter_from_this_group_obj.groupIndependentInverters.remove(inverter_obj)

                            add_inverter_to_this_group_obj = SolarGroup.objects.get(id=int(add_inverter_to_this_group_key))
                            add_inverter_to_this_group_obj.groupIndependentInverters.add(inverter_obj)

                            logger.debug("inverter removed from a group")
                        except SolarGroup.DoesNotExist:
                            logger.debug("SolarGroup Doesnt exists")
                            raise Exception("Solar group doesnt exist")
                        except IndependentInverter.DoesNotExist:
                            raise Exception("inverter id not found")
                    flag = flag + "Inverter is shifted to different group"

                if "plant_tagging" in payload:
                    logger.debug("Changing plant tags")
                    new_tags_list = payload['plant_tagging']
                    plant.add_or_update_or_clear_tags(new_tags_list)
                    flag = flag + "Plant's Tagging is Modified! "

                if flag == "":
                    return Response("Looks like nothing is modified.", status=status.HTTP_200_OK)
                return Response("Modified successfully! %s" % flag, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in Partial_update : " + str(exception))
            return Response("INTERNAL_SERVER_ERROR : %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EditUserProfile(ProfileDataInAPIs, viewsets.ViewSet):
    """
       This is to Edit Single User Profile
    """
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'user_id'

    def list(self, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            user_details = {'id':user.id, 'first_name': user.first_name, 'last_name':user.last_name,
                            'phone_number': user.role.phone_number, 'email': user.email}
            return Response(data=user_details, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list edit user: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, user_id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            user_details = {'id':user.id, 'first_name': user.first_name, 'last_name':user.last_name,
                            'phone_no': user.role.phone_number, 'email_id': user.email}
            return Response(data=user_details, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list edit user: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, user_id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            payload = self.request.data
            with transaction.atomic():
                changes = ""
                update_data_dict_key = payload
                if 'first_name' in update_data_dict_key:
                    user.first_name = update_data_dict_key['first_name']
                    changes = changes + "First Name, "
                if 'last_name' in update_data_dict_key:
                    user.last_name = update_data_dict_key['last_name']
                    changes = changes + "Last Name, "

                if 'email_id' in update_data_dict_key:
                    user.email = update_data_dict_key['email_id']
                    changes = changes + "Email, "

                if 'phone_no' in update_data_dict_key:
                    user.role.phone_number = update_data_dict_key['phone_no']
                    user.role.save()
                    changes = changes + "Phone No, "

                if 'old_password' in update_data_dict_key and 'new_password' in update_data_dict_key\
                        and 'new_password1' in update_data_dict_key:
                    user = authenticate(username=user.username, password=payload['old_password'])
                    if user:
                        if not payload['new_password'] == payload['new_password1']:
                            return Response("Password, confirm password should match!",
                                            status=status.HTTP_400_BAD_REQUEST)
                        if payload['old_password'] == payload['new_password']:
                            return Response("Current, new password are same!",
                                            status=status.HTTP_400_BAD_REQUEST)
                        user.set_password(payload['new_password'].strip())
                        changes = changes + "Password, "
                    else:
                        return Response("Current password is wrong!", status=status.HTTP_400_BAD_REQUEST)

                user.save()
                if changes == "":
                    return Response('Nothing is changed', status=status.HTTP_200_OK)
                else:
                    return Response('User Details changed! %s' % changes, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in getting device details of User with user id %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSolarPlantWigetsConfigView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def list(self, request, id=None,**kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
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
            results = UserSolarPlantWidgetsConfig.objects.filter(user=self.request.user)
            payload={}
            for result in results:
                payload[result.id]={}
                payload[result.id]['config_name'] = result.config_name
                payload[result.id]['plants'] = result.plants.all().values('name','slug')

            master_payload = {}
            master_payload['configs']= payload
            plants_meta = request.query_params.get("plants_meta")
            if plants_meta:
                logger.debug("Sending More Details")
                list_plant_meta = []

                for plant in plants:
                    plant_meta = {}
                    plant_meta['name'] = plant.name
                    plant_meta['slug'] = plant.slug
                    plant_meta['location'] = plant.location
                    plant_meta['roof_names'] = plant.solar_groups.all().values_list('name',flat=True) if plant.solar_groups.all() else []
                    plant_meta['tags'] = plant.tags.values_list('name',flat=True) if plant.tags else []
                    list_plant_meta.append(plant_meta)
                master_payload['plants_extra_info'] = list_plant_meta
            return Response(data=master_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list UserSolarPlantWigetsConfigView: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            payload = {}
            context = self.get_profile_data(**kwargs)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                uwpwc =  UserSolarPlantWidgetsConfig.objects.get(id=int(id))
            except UserSolarPlantWidgetsConfig.DoesNotExist:
                return Response("UserSolarPlantWidgetsConfig does not exist", status=status.HTTP_200_OK)
            payload['id'] = uwpwc.id
            payload['config_name'] = uwpwc.config_name
            payload['plants'] = uwpwc.plants.all().values('name', 'slug')
            return Response(data=payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list UserSolarPlantWigetsConfig: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR: in retrieve",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, id=None, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            return_payload = {}
            payload = self.request.data
            context = self.get_profile_data(**kwargs)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            try:
                current_upws = UserSolarPlantWidgetsConfig.objects.get(id=int(id))
                all_plants = current_upws.plants.all().values_list('slug', flat=True)
            except UserSolarPlantWidgetsConfig.DoesNotExist:
                return Response("UserSolarPlantWidgetsConfig does not exist", status=status.HTTP_200_OK)
            with transaction.atomic():
                if 'delete' in payload:
                    try:
                        UserSolarPlantWidgetsConfig.objects.get(id=int(payload['delete'])).delete()
                    except Exception:
                        return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_400_BAD_REQUEST)
                if 'plants' in payload:
                    new_plant_slugs = payload['plants']
                    to_delete = set(all_plants)-set(new_plant_slugs)
                    to_add = set(new_plant_slugs)-set(all_plants)
                    for plant in plants:
                        if plant.slug in to_delete:
                            current_upws.plants.remove(plant)
                        if plant.slug in to_add:
                            current_upws.plants.add(plant)
            results = UserSolarPlantWidgetsConfig.objects.filter(user=self.request.user)
            for result in results:
                return_payload[result.id] = {}
                return_payload[result.id]['config_name'] = result.config_name
                return_payload[result.id]['plants'] = result.plants.all().values('name', 'slug')
            return Response(data=return_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list plant widget config: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            return_payload = {}
            context = self.get_profile_data(**kwargs)
            user = self.request.user
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            plant_slugs = []
            for plant in plants:
                plant_slugs.append(plant.slug)
            try:
                payload = self.request.data
                new_plant_slugs = payload['plants']
            except:
                return Response("Please specify plant slugs in request body",
                                status=status.HTTP_400_BAD_REQUEST)
            if not set(new_plant_slugs).issubset(set(plant_slugs)):
                return Response("INTERNAL_SERVER_ERROR: Invalid Plant in list",
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                with transaction.atomic():
                    upw_obj = UserSolarPlantWidgetsConfig.objects.create(user=user,
                                                                 config_name=payload['config_name'])
                    all_plants = SolarPlant.objects.filter(slug__in=new_plant_slugs)
                    for plant in all_plants:
                        upw_obj.plants.add(plant)
                results = UserSolarPlantWidgetsConfig.objects.filter(user=self.request.user)
                for result in results:
                    return_payload[result.id] = {}
                    return_payload[result.id]['config_name'] = result.config_name
                    return_payload[result.id]['plants'] = result.plants.all().values('name', 'slug')
            except Exception as exc:
                return Response("INTERNAL_SERVER_ERROR %s" % exc, status=status.HTTP_400_BAD_REQUEST)
            return Response(return_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list user solar plant widget: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserTableWidgetsConfigView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'


    def list(self, request, id=None,**kwargs):

        """
        :param request:
        :param kwargs:
        :return:
        """
        try:
            config_scope = request.query_params.get("config_scope")
            valid_scopes = []
            for scope in CONFIG_SCOPE:
                valid_scopes = valid_scopes + list(scope)

            if not config_scope in valid_scopes:
                return Response("Please Specify Valid Query Parameter !!", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            user = self.request.user
            payload_to_send = {}
            accessible_features = RoleAccess.objects.get(role=user.role.role,
                                                         dg_client=user.role.dg_client)

            try:
                config = UserTableWidgetsConfig.objects.get(user=user, config_scope=config_scope)
            except Exception as e:
                logger.debug("couldnt find config, sending default config")
                # data_key_name is type of feature
                all_columns = accessible_features.features.all().filter(include_table=True).values('id', 'name', 'data_key_name')

                enabled_features_list = []
                all_features_list = []
                payload_to_send = {}
                elist = {'ENERGY_GENERATION':1, 'CURRENT_POWER':2, 'SY':3,'CUF':4}
                enable_order_id = 0
                for col in all_columns:
                    if col['name'] in elist:
                        enabled_features = {}
                        enabled_features['feature_id'] = col['id']
                        enabled_features['feature_name'] = col['name']
                        enabled_features['text'] = FEATURE_DETAILS["%s" % col['name']]['text']
                        enabled_features['type'] = col['data_key_name']
                        enabled_features['order_number'] = enable_order_id + 1
                        enable_order_id = enable_order_id + 1
                        enabled_features_list.append(enabled_features)
                    else:
                        all_features = {}
                        all_features['feature_id'] = col['id']
                        all_features['feature_name'] = col['name']
                        all_features['text'] = FEATURE_DETAILS["%s" % col['name']]['text']
                        all_features['type'] = col['data_key_name']
                        all_features_list.append(all_features)


                payload_to_send['enabled_features'] = enabled_features_list
                payload_to_send['available_columns_to_add'] = all_features_list
                return Response(data=payload_to_send, status=status.HTTP_200_OK)

            all_columns = accessible_features.features.all().filter(include_table=True).values('name','id')
            all_available_columns = {}
            for col in all_columns:
                all_available_columns[col['name']] = col['id']
            assigned_columns = []

            fixed_features = FeatureOrder.objects.filter(user_table_widgets=config, is_fixed=True).values(
                'order_number', 'features__name', 'features__id', 'features__data_key_name')
            for fixed_feature in fixed_features:
                assigned_columns.append(fixed_feature['features__name'])
                fixed_feature['feature_id'] = fixed_feature.pop('features__id')
                fixed_feature['feature_name'] = fixed_feature.pop('features__name')
                fixed_feature['text'] = FEATURE_DETAILS["%s" % fixed_feature['feature_name']]['text']
                fixed_feature['type'] = fixed_feature.pop('features__data_key_name')
            temp_dict = {}
            ordered_fixed_features = []
            for item in fixed_features:
                temp_dict[item['order_number']] = item
            for key in sorted(temp_dict.keys()):
                ordered_fixed_features.append(temp_dict[key])
            payload_to_send['fixed_features'] = ordered_fixed_features

            enabled_features = FeatureOrder.objects.filter(user_table_widgets=config, is_fixed=False) \
                .values('order_number', 'features__name', 'features__id', 'features__data_key_name')

            for enabled_feature in enabled_features:
                assigned_columns.append(enabled_feature['features__name'])
                enabled_feature['feature_id'] = enabled_feature.pop('features__id')
                enabled_feature['feature_name'] = enabled_feature.pop('features__name')
                enabled_feature['text'] = FEATURE_DETAILS["%s" % enabled_feature['feature_name']]['text']
                enabled_feature['type'] = enabled_feature.pop('features__data_key_name')
            temp_dict = {}
            ordered_enabled_features = []
            for item in enabled_features:
                temp_dict[item['order_number']] = item
            for key in sorted(temp_dict.keys()):
                ordered_enabled_features.append(temp_dict[key])
            payload_to_send['enabled_features'] = ordered_enabled_features

            remaining_columns = set(all_available_columns.keys()) - set(assigned_columns)

            list_of_remaining_columns = []
            for column in remaining_columns:
                dict_remaining_columns = {}
                dict_remaining_columns['feature_id'] = all_available_columns[column]
                dict_remaining_columns['feature_name'] = column
                dict_remaining_columns['text'] = FEATURE_DETAILS[column]['text']
                dict_remaining_columns['type'] = FEATURE_DETAILS[column]['type']
                list_of_remaining_columns.append(dict_remaining_columns)

            payload_to_send['available_columns_to_add'] = list_of_remaining_columns
            return Response(data=payload_to_send, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list UserTableWIdgetConfig: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def create(self, request, id=None, **kwargs):
            """"

            :param request:
            :param id:
            :param kwargs:
            :return:
            """
            try:

                config_scope = request.query_params.get("config_scope")
                valid_scopes = []
                for scope in CONFIG_SCOPE:
                    valid_scopes = valid_scopes + list(scope)

                if not config_scope in valid_scopes:
                    return Response("Please Specify Valid Query Parameter !!", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                user = self.request.user

                try:
                    config, flag = UserTableWidgetsConfig.objects.get_or_create(user=user, config_scope=config_scope)
                except Exception as e:
                    logger.debug("couldnt find config")
                    return Response("No config found !!", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                payload = self.request.data
                new_fixed_features = payload['new_fixed_features'] if 'new_fixed_features' in payload else 'none'
                new_enabled_features = payload['new_enabled_features'] if 'new_enabled_features' in payload else 'none'

                if not new_fixed_features == 'none':

                    if flag == False:
                        fixed_features = FeatureOrder.objects.filter(user_table_widgets=config, is_fixed=True)
                        if fixed_features:
                            fixed_features.delete()

                    # if not set(new_fixed_features)-set(fixed_features):
                    # Currently for testing keep it true. but in final prod remove below line and uncomment above line
                    # Just checking if list is empty so that it deletes all features
                    if True:
                        order_number = 0
                        new_fixed_features_to_add = []
                        for feature_id in new_fixed_features:
                            new_fixed_features_to_add.append(FeatureOrder(user_table_widgets_id=config.id, is_fixed=True,
                                                                            features_id=feature_id,
                                                                            order_number=order_number + 1))
                            order_number = order_number + 1
                        FeatureOrder.objects.bulk_create(new_fixed_features_to_add)
                        logger.debug("fixed features updated")

                # Now time for enabled feature reordering and adding or deleting all in one go
                if not new_enabled_features == 'none':
                    new_enabled_features_to_add = []
                    if flag == False:
                        enabled_features = FeatureOrder.objects.filter(user_table_widgets=config, is_fixed=False)
                        enabled_features.delete()
                    if not new_enabled_features == []:
                        order_number=0
                        for feature_id in new_enabled_features:
                            new_enabled_features_to_add.append(FeatureOrder(user_table_widgets_id=config.id, is_fixed=False,
                                                                            features_id=feature_id,order_number=order_number+1))
                            order_number = order_number + 1
                        FeatureOrder.objects.bulk_create(new_enabled_features_to_add)
                    logger.debug("enabled features updated")

                return self.list(request, id=None, **kwargs)
                return Response(data="Done", status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug("Error in list UserTableWIdgetConfig: %s" % exception)
                return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlantGroupView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
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
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(plant)
            if plant not in plants:
                return Response("Invalid plant slug", status=status.HTTP_400_BAD_REQUEST)
            groups = SolarGroup.objects.filter(plant=plant)
            all_groups = []
            for group in groups:
                group_data = {}
                group_data['id'] = group.varchar_id
                group_data['name'] = group.name
                group_data['latitude'] = group.latitude
                group_data['longitude'] = group.longitude
                group_data['roof_type'] = group.roof_type
                group_data['group_type'] = group.roof_type
                group_data['displayName'] = group.displayName
                all_groups.append(group_data)
            return Response(data=all_groups, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in getting device details of plant : " +str(plant.slug)+ str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DataglenClientView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'client_id'

    def list(self, request, id=None,**kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            client = self.request.user.role.dg_client
            payload={}
            payload['id'] = client.id
            payload['name'] = client.name
            payload['clientWebsite'] = client.clientWebsite
            payload['clientDomain'] = client.clientDomain
            payload['clientContactAddress'] = client.clientContactAddress

            return Response(data=payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list dataglenclient: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, id=None, **kwargs):
        """
        :param request:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            client = self.request.user.role.dg_client
            payload={}
            payload['id']=client.id
            payload['name'] = client.name
            payload['clientWebsite'] = client.clientWebsite
            payload['clientDomain'] = client.clientDomain
            payload['clientContactAddress'] = client.clientContactAddress

            return Response(data=payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list dataglenclient: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def partial_update(self, request, id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            try:
                payload = self.request.data
            except:
                return Response("Please specify payload in request body", status=status.HTTP_400_BAD_REQUEST)

            dgc = user.role.dg_client
            if "clientWebsite" in payload:
                dgc.clientWebsite = payload["clientWebsite"]
            if "clientContactAddress" in payload:
                dgc.clientContactAddress = payload["clientContactAddress"]
            if "name" in payload:
                dgc.name = payload["name"]
            if "clientDomain" in payload:
                dgc.clientDomain = payload["clientDomain"]
            dgc.save()

            return Response(data="DONE", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list plant widget config: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConnectionTest(viewsets.ViewSet):
    # renderer_classes = (XMLRenderer, JSONRenderer,)

    def list(self, request,**kwargs):
        logger.debug("Request Received %s" % request.__dict__)
        return Response(data = "ok", status=status.HTTP_200_OK)

class GetCurrentTime(ProfileDataInAPIs, viewsets.ViewSet):

    def list(self,request):
        return Response(data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status=status.HTTP_200_OK)


class DataTransferKaco(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.BasicAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'inverter_serial_no'

    def list(self, request, inverter_serial_no=None, **kwargs):

        try:
            return Response(data='get', status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list dataglenclient: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, inverter_serial_no=None, **kwargs):

        try:
            payload = self.request.data
            file_path = '/var/tmp/monthly_report/incoming_data.csv'
            file = open(file_path, 'a')
            file.write(str(payload))
            file.write(',')
            #
            # request_arrival_time = timezone.now()
            # source_key='pEhfVzRn0qzJkHF'
            #
            # resp = data_write(request,request_arrival_time,source_key,settings.RESPONSE_TYPES.DRF)
            # return resp
            return Response(data='Written to file', status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list dataglenclient: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class V2_NewPredictionDataViewSet(viewsets.ViewSet):
    """
    Used for MSR Demo plant for posting prediction data
    """
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, plant_slug=None, **kwargs):
        """

        :param request: request parameter including post and data
        :param plant_slug: plan_slug from solarplant
        :param kwargs:
        :return:
        """
        model_name_values = ('STATISTICAL_DAY_AHEAD', 'STATISTICAL_LATEST', 'ACTUAL_VALUE', 'ACTUAL', 'LSTM')
        timestamp_types_values = tuple(value for key, value in settings.TIMESTAMP_TYPES.__dict__.items()
                                             if not key.startswith('__') and not callable(key))
        count_time_period_values = tuple(value for key, value in settings.DATA_COUNT_PERIODS.__dict__.items()
                                             if not key.startswith('__') and not callable(key))
        try:
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            t_post_data = request.data
            # check if post_data is a dictionary
            payload = [t_post_data] if isinstance(t_post_data, dict) else t_post_data

            for post_data in payload:
                logger.debug(post_data)
                if "timestamp_type" and "count_time_period" and "identifier_type" and "identifier"\
                        and "model_name" and "ts" and "stream_name" not in post_data:
                    return Response("Please specify timestamp_type, count_time_period, identifier_type,\
                     model_name, ts, stream_name in the request payload",\
                                    status=status.HTTP_400_BAD_REQUEST)

                if post_data['ts']:
                    try:
                        ts = parser.parse(post_data['ts'])
                        ts = update_tz(ts, "UTC")
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("Please provide valid timestamp", status=status.HTTP_400_BAD_REQUEST)
                else:
                    ts = timezone.now()

                if post_data['timestamp_type'] not in timestamp_types_values:
                    return Response("Please provide valid timestamp_type", status=status.HTTP_400_BAD_REQUEST)

                if int(post_data['count_time_period']) not in count_time_period_values:
                    return Response("Please provide valid count_time_period", status=status.HTTP_400_BAD_REQUEST)

                if post_data['identifier_type'] not in ('plant', 'source'):
                    return Response("Please provide valid identifier_type", status=status.HTTP_400_BAD_REQUEST)

                if post_data['model_name'] not in model_name_values:
                    return Response("Please provide valid model_name", status=status.HTTP_400_BAD_REQUEST)
                try:
                    NewPredictionData.objects.create(timestamp_type="%s" %post_data['timestamp_type'],
                                                     count_time_period=int(post_data['count_time_period']),
                                                     identifier_type="%s" %post_data['identifier_type'],
                                                     plant_slug="%s" %plant.slug,
                                                     identifier="%s" %post_data['identifier'],
                                                     stream_name="%s" %post_data['stream_name'],
                                                     model_name="%s" %post_data['model_name'], ts=ts,
                                                     value=float(post_data['value']),
                                                     upper_bound=float(post_data['upper_bound']),
                                                     lower_bound=float(post_data['lower_bound']))

                    PredictionData.objects.create(
                        timestamp_type="%s" %post_data['timestamp_type'],
                        count_time_period=int(post_data['count_time_period']),
                        identifier=plant.slug,
                        stream_name="%s" %post_data['stream_name'],
                        model_name="%s" %post_data['model_name'],
                        ts=ts,
                        value=float(post_data['value']),
                        lower_bound=float(post_data['lower_bound']),
                        upper_bound=float(post_data['upper_bound']),
                        update_at=timezone.now())


                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("value, upper_bound, lower_bound should be float", status=status.HTTP_400_BAD_REQUEST)
            return Response("NewPredictionData entry created successful", status=status.HTTP_201_CREATED)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GECleaningTrigger(ProfileDataInAPIs, viewsets.ViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        """

        :param request:
        :param id:
        :param kwargs:
        :return:
        """
        string_name = ('S1', 'S10', 'S11', 'S12', 'S13', 'S14', 'S15', 'S16', 'S17',
                       'S18', 'S19', 'S2', 'S20', 'S21', 'S22', 'S23', 'S24', 'S25',
                       'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9')
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

        channel = request.query_params.get('channel')
        """if channel not in ('ui', 'em'):
            return Response("invalid channel", status=status.HTTP_400_BAD_REQUEST)"""
        all_ajbs = plant.ajb_units.all()
        all_ajbs_id = all_ajbs.values_list('id', flat=True)
        response = {}
        if channel == 'ui':
            open_trigger = CleaningTrigger.objects.filter(present_state__in=('open', 'in_process'),
                                            ajb_id__in=all_ajbs_id).values_list('ajb__sourceKey', 'string_name')
            all_open_trigger = {}
            for trg,st in open_trigger:
                if trg in all_open_trigger:
                    all_open_trigger[trg].append(st)
                else:
                    all_open_trigger[trg] = [st]
            all_string_name = {}
            for ajb in all_ajbs:
                stream_names = ajb.fields.filter(isActive=True, name__in=string_name).values_list('name', flat=True)
                stream_exists = all_open_trigger.get(ajb.sourceKey, None)
                for stname in stream_names:
                    if stream_exists and stname in stream_exists:
                        continue
                    all_string_name['%s+%s' %(ajb.sourceKey, stname)] = "%s (%s)" %(ajb.name, stname)
            response['ui'] = all_string_name

        if channel == 'em':
            all_triggers = CleaningTrigger.objects.filter(present_state__in=('open', 'in_process'),
                                                          ajb_id__in=all_ajbs_id)
            all_triggers_list = []
            for trg in all_triggers:
                all_triggers_list.append({'ajb': trg.ajb.sourceKey, 'string_name': trg.string_name,
                                   'trigger_type': trg.trigger_type, 'present_state': trg.present_state,
                                   'submitted_at': trg.submitted_at, 'accepted_at': trg.accepted_at,
                                   'finished_at': trg.finished_at, 'submitted_by': trg.submitted_by.email})
            response['em'] = all_triggers_list

        startdate = request.query_params.get('startdate')
        enddate = request.query_params.get('enddate')
        if startdate and enddate:
            try:
                startdate = datetime.datetime.strptime(startdate, "%d-%m-%Y")
                enddate = datetime.datetime.strptime(enddate, "%d-%m-%Y")
            except Exception as exception:
                logger.debug(str(exception))
            all_triggers = CleaningTrigger.objects.filter(submitted_at__gte=startdate,
                                                          submitted_at__lte=enddate,
                                                          ajb__in=all_ajbs_id)
            all_triggers_list = []
            for trg in all_triggers:
                all_triggers_list.append({'ajb': trg.ajb.sourceKey, 'string_name': trg.string_name,
                                          'trigger_type': trg.trigger_type, 'present_state': trg.present_state,
                                          'submitted_at': trg.submitted_at, 'accepted_at': trg.accepted_at,
                                          'finished_at': trg.finished_at, 'submitted_by': trg.submitted_by.email})
                response['triggers'] = all_triggers_list
        return Response(data=response, status=status.HTTP_200_OK)

    def create(self, request, plant_slug=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        from solarrms.models import CLEANING_PRESENT_STATE, TRIGGER_TYPE
        try:
            payload = self.request.data
            user = request.user
            sourceKey, string_name = payload['sourceKey_string'].split("+")
            try:
                ajb = AJB.objects.get(sourceKey=sourceKey)
            except:
                return Response(data="wrong ajb id", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            trigger_type = payload['trigger_type']
            present_state = payload.get('present_state', 'open')

            if trigger_type in dict(TRIGGER_TYPE).keys() and present_state in dict(CLEANING_PRESENT_STATE).keys():
                print "ok"
            else:
                return Response(
                    data="trigger_type(['cool','cleaning']) or present_state(['finished', 'open', 'in_process']) is wrong",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            channel = request.query_params.get("channel", "")
            if channel == 'em':
                try:
                    ct = CleaningTrigger.objects.filter(ajb=ajb, string_name=string_name,
                                                     trigger_type=payload['trigger_type'],
                                                     present_state__in=('open', 'in_process'))
                    if len(ct) == 0:
                        raise Exception
                except:
                    return Response(data="CleaningTrigger object not found",
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                #print "change cleaning present state to in process"

                if present_state == "in_process":
                    if ct[0].present_state == "open":
                        ct.update(present_state="in_process", accepted_at=datetime.datetime.now())
                        return Response(data="data saved", status=status.HTTP_200_OK)
                    else:
                        return Response("present state is not open. Cannot change state",
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                if present_state == "finished":
                    if ct[0].present_state == "in_process":
                        ct.update(present_state="finished", finished_at=datetime.datetime.now())
                        return Response(data="data saved", status=status.HTTP_200_OK)
                    else:
                        return Response("present state is not in process. Cannot change state",
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if channel == 'ui':
                CleaningTrigger.objects.create(ajb=ajb, string_name=string_name, trigger_type=trigger_type,
                                               present_state='open', submitted_by=user)

            return Response(data="DONE", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error : %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from features.models import CustomReportFormat
from .views import feature_dynamic_pdf_ids_mapping
from django.db.models import Sum
class CustomReportFormatView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'format_id'

    def list(self, request, format_id=None,**kwargs):
        """
        Returns
        1: all Formats
        2: custom_features of each format
        example:

         "1": {
        "is_default": false,
        "users_list": [],
        "custom_format_name": "CustomFormat1",
        "role": "CEO",
        "custom_features": [
            {
                "feature_chart_type": null,
                "feature_type": null,
                "feature_columns": null,
                "custom_feature_id": 8,
                "feature_order": 1,
                "feature_title": "pr",
                "feature_description": null,
                "feature_unit": null
            }
        ]

        3: default_features_for_all_roles
        :param request:
        :param format_id:
        :param kwargs:
        :return:

        4: all_users with their roles
        url:
            http://127.0.0.1:8000/api/v1/solar/custom_report_format/
        """
        try:
            payload={}
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            client = self.request.user.role.dg_client
            all_customised_format = CustomReportFormat.objects.filter(dg_client=client)
            all_customised_format_list = []
            for format in all_customised_format:
                users_list = format.user.all().values('id','email')
                for usr in users_list:
                    usr['user_id'] = usr.pop('id')
                custom_features = format.custom_features.all().\
                    values('feature_title','feature_description','feature_columns', \
                            'feature_chart_type','feature_unit', 'feature_type','feature_order','features__id')
                for item in custom_features:
                    item['feature_id'] = item.pop('features__id')
                single_format = {'custom_format_name': format.name,'is_default':format.role_default, 'role': format.role,'custom_features': custom_features,'users_list':users_list, 'custom_format_id':format.id}
                all_customised_format_list.append(single_format)
            payload['all_customised_format_list'] = all_customised_format_list
            all_role_accesses = client.access_definitions.all()
            pdf_features = feature_dynamic_pdf_ids_mapping.values()
            default_feature_set_all_roles = {}
            role_users_dict = {}
            for role_access in all_role_accesses:
                user_features = []
                user_features_obj_list = RoleAccess.objects.get(role=role_access.role,
                                                                dg_client=self.request.user.role.dg_client).features.all()
                for feature_obj in user_features_obj_list:
                    user_features.append({"feature_id": feature_obj.id,"feature_name":str(feature_obj)})

                # single_role_all_features_list = role_access.features.all().values_list('name', flat=True)
                feature_set_per_role = []
                for single_feature in user_features:
                    if single_feature['feature_name'] in pdf_features:
                        # print "this feature exists " , single_feature['feature_name']
                        feature_set_per_role.append(single_feature)
                    else:
                        pass
                        # print single_feature['feature_name'], " is not there in pdf_features "
                role_users_dict[role_access.role] = UserRole.objects.filter(dg_client=client,role=role_access.role).values('user_id', 'user__email')

                default_feature_set_all_roles[role_access.role] = feature_set_per_role
            payload['default_features_for_all_roles'] = default_feature_set_all_roles
            # all_users = UserRole.objects.filter(dg_client=client).values('user_id', 'user__email', 'role')
            # payload['all_users']= all_users
            payload['roles_and_users'] = role_users_dict
            return Response(data=payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list : %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Just a placeholder
    def retrieve(self, request, format_id=None, **kwargs):
        """
        :param request:
        :param kwargs:
        :return:
        """
        try:
            payload="all is well %s " % format_id
            return Response(data=payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in retrieve: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def partial_update(self, request, format_id=None, **kwargs):
        """
        This will modify an existing Custom Format
        1. Add or remove user
        2. Make the custom_format as default format for particular role
        3. Add or remove custom features in a format

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            client = user.role.dg_client
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            try:
                payload = self.request.data
            except Exception as exception:
                logger.debug("Payload problems in customreportformatview partial update %s" % exception)
                return Response("Please specify payload in request body", status=status.HTTP_400_BAD_REQUEST)

            try:
                c_format = CustomReportFormat.objects.get(id=format_id)
            except Exception as exception:
                logger.debug("No format found in customreportformat %s" % exception)
                return Response("format is not found", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if 'users_list' in payload:
                all_users = UserRole.objects.filter(dg_client=client, role=c_format.role).values_list('user_id',flat=True)
                new_users_list = payload['users_list']
                if set(new_users_list).issubset(set(all_users)):
                    # Firstly remove the old user to custom format associations
                    for id in new_users_list:
                        mod_user = User.objects.get(id=id)
                        all_formats_per_user = mod_user.custom_report.all()
                        for cf in all_formats_per_user:
                            mod_user.custom_report.remove(cf)
                    # Now add or remove users from a particular custom format
                    current_users_list = c_format.user.all().values_list('id',flat=True)
                    to_delete_users = set(current_users_list)-set(new_users_list)
                    to_add_users = set(new_users_list) - set(current_users_list)
                    for user_id_r in to_delete_users:
                        try:
                            c_format.user.remove(User.objects.get(id=user_id_r))
                        except Exception as exception:
                            logger.debug("couldnt remove user %s" % exception)
                    for user_id_a in to_add_users:
                        try:
                            c_format.user.add(User.objects.get(id=user_id_a))
                        except Exception as exception:
                            logger.debug("couldnt add user %s" % exception)
                    return Response(data="User modification done", status=status.HTTP_202_ACCEPTED)
                else:
                    return Response(data="Unauthorised User ids", status=status.HTTP_401_UNAUTHORIZED)

            if 'make_default_for_role' in payload:
                try:
                    default_format = CustomReportFormat.objects.get(dg_client=client, role=c_format.role, role_default=True)
                    default_format.role_default = False
                    default_format.save()
                except Exception as exception:
                    pass
                if payload['make_default_for_role'] == True or payload['make_default_for_role'] == False:
                    c_format.role_default = payload['make_default_for_role']
                    c_format.save()
            if 'custom_features' in payload:
                feature_dict = payload['custom_features']
                print c_format.update_custom_format(feature_dict)
            else:
                print "nothing changed"
            if 'name' in payload:
                c_format.name = payload['name']
                c_format.save()


            return Response(data="DONE", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in partial update: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        url:
            http://127.0.0.1:8000/api/v1/solar/custom_report_format/
        """
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            try:
                payload = self.request.data
            except Exception as exc:
                logger.debug("Payload problems %s" %exc)
                return Response("Please specify payload in request body: %s" % exc, status=status.HTTP_400_BAD_REQUEST)

            dg_client = user.role.dg_client
            # Create New Format
            # Check if name and role is provided to create new custom report format. then check if new features provided with that
            # with transaction.atomic():
            if set(["name","role"]).issubset(set(payload.keys())) and payload["list_of_new_feature_dict"]:
                check_if_similar_report_format_exists = CustomReportFormat.objects.filter(name=payload['name'], dg_client=dg_client,role=payload['role'])
                if len(check_if_similar_report_format_exists):
                    return Response(data="Custom Report Format with this name already exists. Choose different Name", status=status.HTTP_409_CONFLICT)
                c_format = CustomReportFormat.objects.create(name=payload['name'], dg_client=dg_client, role=payload['role'])
                updation_reply = c_format.update_custom_format(payload["list_of_new_feature_dict"])
                if 'make_default_for_role' in payload:
                    try:
                        default_format = CustomReportFormat.objects.get(dg_client=dg_client, role=c_format.role,
                                                                        role_default=True)
                        default_format.role_default = False
                        default_format.save()
                    except Exception as exception:
                        logger.debug("No default format found. No worries")
                        pass
                    c_format.role_default = True
                    c_format.save()
                if updation_reply == True:
                    return Response(data="DONE", status=status.HTTP_201_CREATED)
                else:
                    return Response(data="Something went wrong %s" % updation_reply, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                print "list of new feature dict does not exist"

            return Response(data="DONE", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list plant widget config: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
class OneDayPDFReport(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                plant = SolarPlant.objects.get(slug=plant_slug, groupClient=user_client)
                if str(user_role) != 'CEO':
                    # verify_if_user_has_plant_access
                    if not (plant.users.get(id=self.request.user.id)):
                        logger.debug("Not Authorised for this plant slug %s"%plant_slug)
                        return Response("Not Authorised for this plant slug %s"%plant_slug,\
                                        status=status.HTTP_401_UNAUTHORIZED)

            except Exception as exception:
                logger.debug("Something went wrong slug = %s , >>%s" % (plant_slug,exception))
                return Response("Something went wrong slug = %s" % plant_slug,
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            st = request.query_params["st"]
            pdfs = PDFReportSummary()
            file_name = pdfs.get_pdf_content(st, plant,self.request.user)
            with open('%s' %file_name, 'rb') as pdf:
                file_name=file_name.split('/')[-1]
                response = HttpResponse(pdf.read(), content_type='application/force-download')
                response['Content-Disposition'] = 'inline;filename=%s' %(file_name)
                return response
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from solarrms.views import PDFReportSummaryMonthly
class MonthlyPDFReport(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                plant = SolarPlant.objects.get(slug=plant_slug, groupClient=user_client)
                if str(user_role) != 'CEO':
                    # verify_if_user_has_plant_access
                    if not (plant.users.get(id=self.request.user.id)):
                        logger.debug("Not Authorised for this plant slug %s"%plant_slug)
                        return Response("Not Authorised for this plant slug %s"%plant_slug,\
                                        status=status.HTTP_401_UNAUTHORIZED)

            except Exception as exception:
                logger.debug("Something went wrong slug = %s , >>%s" % (plant_slug,exception))
                return Response("Something went wrong slug = %s" % plant_slug,
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            st = request.query_params["st"]
            pdfs = PDFReportSummaryMonthly()
            file_name = pdfs.get_pdf_content(st, plant,self.request.user)
            with open('%s' %file_name, 'rb') as pdf:
                file_name=file_name.split('/')[-1]
                response = HttpResponse(pdf.read(), content_type='application/force-download')
                response['Content-Disposition'] = 'inline;filename=%s' %(file_name)
                return response
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from .pvsyst_reports import cron_send_pvsyst_report_cleanmax
from django.http import StreamingHttpResponse
from dateutil import parser
class PVSystAchievementReportDownload(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'client_id'

    def list(self, request, id=None,**kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        # return Response(data="make a post request",
        #                 status=status.HTTP_200_OK)
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            client = self.request.user.role.dg_client
            startdate = self.request.query_params.get('startdate')
            enddate = self.request.query_params.get('enddate')
            startdate = parser.parse(startdate)
            enddate = parser.parse(enddate)
            # recepient_email = self.request.query_params.get('recepient_email')
            workbook = cron_send_pvsyst_report_cleanmax(startdate, enddate, user)
            # cron_send_pvsyst_report_cleanmax(st, et, user, recepient_email=None)
            # pandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
            try:
                # pandasWriter.save()
                # sio.seek(0)
                # workbook = sio.getvalue()
		response = HttpResponse(content=save_virtual_workbook(workbook), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                #response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')

                response['Content-Disposition'] = 'attachment; filename=' + "PVSyst Achievement.xls"
                return response
            except Exception as exception:
                return Response("BAD_REQUEST %s " % exception, status=status.HTTP_400_BAD_REQUEST)

            return Response(data="this is client, starttime, endtime, %s %s %s" % (client.name,startdate,enddate), status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list pvsyst achievement: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            try:
                payload = self.request.data
                if not payload:
                    return Response("Please specify payload in request body. Its looking empty", status=status.HTTP_400_BAD_REQUEST)
                if type(payload) != list:
                    return Response("Payload should be list", status=status.HTTP_400_BAD_REQUEST)
                all_plants_accessible = SolarPlant.objects.filter(groupClient=user.role.dg_client).values_list('slug',flat=True)
                if not set(payload).issubset(all_plants_accessible):
                    return Response("Invalid Plant Slugs. Unauthorised",
                                    status=status.HTTP_400_BAD_REQUEST)


            except Exception as exc:
                logger.debug("Payload problems %s" %exc)
                return Response("Please specify payload in request body: %s" % exc, status=status.HTTP_400_BAD_REQUEST)

            # client = user.role.dg_client
            startdate = self.request.query_params.get('startdate')
            enddate = self.request.query_params.get('enddate')
            startdate = parser.parse(startdate)
            enddate = parser.parse(enddate)
            plant_slugs = payload
            workbook = cron_send_pvsyst_report_cleanmax(startdate, enddate, user, plant_slugs)
            try:
                response = HttpResponse(content=save_virtual_workbook(workbook),
                                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                response['Content-Disposition'] = 'attachment; filename=' + "PVSyst Achievement.xls"
                return response
            except Exception as exception:
                return Response("BAD_REQUEST %s " % exception, status=status.HTTP_400_BAD_REQUEST)

            return Response(data="this is client, starttime, endtime, %s %s %s" % (client.name, startdate, enddate),
                        status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in post pvsyst: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MonthlyGenerationBill(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, plant_slug=None, **kwargs):
        try:
            # for now we are not applying any checks for authentication as if he is master user he will be having all access
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug,groupClient=user.role.dg_client)
            except Exception as exception:
                logger.debug("Invalid Plant Slug entered in monthlygenerationbill %s" %exception)
                return Response("Invalid Plant Slug")

            st = request.query_params["st"]
            et = request.query_params["et"]
            pdfs = GenerateElectricityBill()
            file_name = pdfs.get_pdf_content(st,et,plant)
            # file_name = "/home/upendra/PycharmProjects/kutbill_staging/kutbill-django/solarrms/daily.pdf"
            with open('%s' %file_name, 'rb') as pdf:
                file_name=file_name.split('/')[-1]
                response = HttpResponse(pdf.read(), content_type='application/force-download')
                response['Content-Disposition'] = 'inline;filename=%s' %(file_name)
                return response
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR in MonthlyGenerationBill %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# This is exclusively to be used by obu
class AllPlantsDetails1(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, **kwargs):
        try:
            user = self.request.user
            if not user.email ==  "adminobu@dataglen.com":
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            import collections
            import pandas as pd
            f = pd.DataFrame(columns=["slug", "name", "capacity", "location", "latitude", "longitude", "client", \
                                      "commissioned_date", "inverters", "isOperational"]
                             )
            plants = SolarPlant.objects.all()
            for plant in plants:
                logger.debug("Fetching Data for plant == == %s", plant.slug)
                invs = plant.independent_inverter_units.all()
                models = []
                for i in invs:
                    models.append(i.manufacturer + "-" + i.model)
                inverters_dict = collections.Counter(models)
                no_of_inverters = ''
                for key in inverters_dict:
                    no_of_inverters = no_of_inverters + str(inverters_dict[key]) + " - " + key + " "

                d = {"slug": plant.slug, "name": plant.name, "capacity": plant.capacity, "location": plant.location,
                     "latitude": plant.latitude, \
                     "longitude": plant.longitude, "client": plant.groupClient.name,
                     "commissioned_date": str(plant.commissioned_date), \
                     "inverters": no_of_inverters, "isOperational": plant.isOperational}
                f = f.append(d, ignore_index=True)
            file_name = "/var/tmp/monthly_report/obu_all_plants_data.csv"
            f.to_csv(file_name)
            with open('%s' % file_name, 'rb') as csv_file:
                response = HttpResponse(csv_file, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename=data.csv'
                return response
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR in %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# This is exclusively to be used by obu
class AllPlantsDetails(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, **kwargs):
        try:
            user = self.request.user
            if not user.email ==  "adminobu@dataglen.com":
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            import collections
            import pandas as pd
            f = pd.DataFrame(columns=["slug", "name", "capacity", "location", "latitude", "longitude", "client", \
                                      "commissioned_date", "inverters", "isOperational"]
                             )
            plants = SolarPlant.objects.all()
            for plant in plants:
                logger.debug("Fetching Data for plant == == %s", plant.slug)
                invs = plant.independent_inverter_units.all()
                models = []
                for i in invs:
                    models.append(i.manufacturer + "-" + i.model)
                inverters_dict = collections.Counter(models)
                no_of_inverters = ''
                for key in inverters_dict:
                    no_of_inverters = no_of_inverters + str(inverters_dict[key]) + " - " + key + " "

                d = {"slug": plant.slug, "name": (plant.name).replace(","," "), "capacity": plant.capacity, "location": (plant.location).replace(","," "),
                     "latitude": plant.latitude, \
                     "longitude": plant.longitude, "client": plant.groupClient.name,
                     "commissioned_date": str(plant.commissioned_date), \
                     "inverters": no_of_inverters, "isOperational": plant.isOperational}
                f = f.append(d, ignore_index=True)
            file_name = "/var/tmp/monthly_report/obu_all_plants_data.csv"
            f.to_csv(file_name)
            with open('%s' % file_name, 'rb') as csv_file:
                response = HttpResponse(csv_file, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename=data.csv'
                return response
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR in %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


