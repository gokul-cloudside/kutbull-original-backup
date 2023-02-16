import datetime
import collections
from rest_framework import serializers
from solarrms.models import SolarPlant
from eventsframework.utils import get_both_type_of_events
from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from dashboards.mixins import ProfileDataInAPIs
from solarrms.solarutils import filter_solar_plants
from django.core.exceptions import ObjectDoesNotExist
from eventsframework.models import Company, MaintenanceContract
from organizations.models import OrganizationUser, Organization, OrganizationOwner
from django.contrib.auth.models import User
from eventsframework.models import WEEKDAYS, SLA
from solarrms.api_views import update_tz
from dateutil import parser

import logging
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class EventDetailViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, plant_slug=None, **kwargs):
        """
        calander view from this api
        :param request:
        :param plant_slug:
        :return:
        """
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            # get request query params
            try:
                post_data = request.data
                plant_slug = post_data["plant_slug"]
                open_close = post_data["open_close"]
            except:
                return Response("Please provide plant_slug and open_close",
                                status=status.HTTP_400_BAD_REQUEST)
            starttime = None
            endtime = None
            try:
                if "starttime" in post_data:
                    starttime = post_data["starttime"]
                    starttime = datetime.datetime.strptime(starttime, "%d/%m/%Y")
                    starttime = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
                if "endtime" in post_data:
                    endtime = post_data["endtime"]
                    endtime = datetime.datetime.strptime(endtime, "%d/%m/%Y")
                    endtime = endtime.replace(hour=23, minute=59, second=59, microsecond=59)
            except:
                return Response("Please provide proper start, end time",
                                status=status.HTTP_400_BAD_REQUEST)

            # filter out plants
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            all_plants = []
            try:
                for plant_instance in plants:
                    if plant_instance.slug in plant_slug or len(plant_slug) == 0:
                        all_plants.append(plant_instance.slug)
                if all_plants is None:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except ObjectDoesNotExist:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            result_dict = get_both_type_of_events(all_plants, starttime, endtime, open_close)
            return Response(data=result_dict, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompanySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(label='id', read_only=True)
    class Meta:
        model = Company
        fields = ('id', 'name','logo', 'registered_name', 'registered_office_address','cin_number','email','tel_number',
                  'website_address', 'tax_details_primary','tax_details_secondary')

    def create(self, validated_data):
        data = self.context['request']._data

        data['dgclient_user'] = self.context['request'].user
        try:
            out = Company.add_new_solar_company(**data)
        except Exception as e:
            return Response("Invalid Parameters to Create a New Company.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return out


class CompanyView(ProfileDataInAPIs, viewsets.ModelViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CompanySerializer

    def get_queryset(self):
        try:
            user_role = self.request.user.role
            user_client = self.request.user.role.dg_client
        except Exception as exception:
            logger.debug(str(exception))
            return Response("Login To Proceed", status=status.HTTP_401_UNAUTHORIZED)

        logger.debug("reached in request")
        logger.debug(self.request.user.email)
        #if not user_role.enable_preference_edit:
        #    return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
        if user_role.role == "OM_VENDOR_ADMIN":
            org_owner = OrganizationOwner.objects.filter(organization_user__user=self.request.user)[0]
            org = org_owner.organization
            company = org.dataglengroup.company
            return Company.objects.filter(id=company.id)

        return Company.objects.filter(groupClient=user_client)


class FieldTechnicianView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'ft_id'

    def list(self, request, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            user_role = user.role
            # [0] because it is assumed that user has only on organization which is new maintainance company
            # org = user.organizations_organization.all()[0]
            org_owner = OrganizationOwner.objects.filter(organization_user__user=user)[0]
            org = org_owner.organization

            company = org.dataglengroup.company
            checking_id = company.owner.organization_user.user.id
            if not checking_id == user.id or not user_role.role == 'OM_VENDOR_ADMIN':
                return Response("Not Authorized to change", status=status.HTTP_401_UNAUTHORIZED)

            all_fts = OrganizationUser.objects.filter(organization=org).values('user__id','user__first_name',
                                                                               'user__last_name','user__email',
                                                                               'user__role__phone_number',
                                                                               'user__role__account_suspended').\
                exclude(user__role__role='OM_VENDOR_ADMIN')

            for ft in all_fts:
                ft['ft_id'] = ft.pop('user__id')
                ft['first_name'] = ft.pop('user__first_name')
                ft['last_name'] = ft.pop('user__last_name')
                ft['email'] = ft.pop('user__email')
                ft['phone_number'] = ft.pop('user__role__phone_number')
                ft['account_suspended'] = ft.pop('user__role__account_suspended')

            return Response(all_fts, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list FieldTechnicianView : %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, ft_id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            user_role = user.role
            # [0] because it is assumed that user has only on organization which is new maintainance company
            # org = user.organizations_organization.all()[0]
            org_owner = OrganizationOwner.objects.filter(organization_user__user=user)[0]
            org = org_owner.organization
            company = org.dataglengroup.company
            checking_id = company.owner.organization_user.user.id
            if not checking_id == user.id or not user_role.role == 'OM_VENDOR_ADMIN':
                return Response("Not Authorized to change", status=status.HTTP_401_UNAUTHORIZED)

            ft_user = User.objects.get(id=ft_id)
            checking_ft_in_organization = OrganizationUser.objects.filter(organization=org, user=ft_user)

            if checking_ft_in_organization:
                payload = {}
                payload['ft_id'] = ft_user.id
                payload['first_name'] = ft_user.first_name
                payload['last_name'] = ft_user.last_name
                payload['phone_number'] = ft_user.role.phone_number
                payload['email'] = ft_user.email
                payload['account_suspended'] = ft_user.role.account_suspended
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list FieldTechnicianView : %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, id=None, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            user_role = user.role
            # [0] because it is assumed that user has only on organization which is new maintainance company
            # org = user.organizations_organization.all()[0]
            org_owner = OrganizationOwner.objects.filter(organization_user__user=user)[0]
            org = org_owner.organization
            company = org.dataglengroup.company
            checking_id = company.owner.organization_user.user.id
            if not checking_id == user.id or not user_role.role == 'OM_VENDOR_ADMIN':
                return Response("Not Authorized to change", status=status.HTTP_401_UNAUTHORIZED)
            payload = self.request.data
            result = company.add_site_technician(payload['email'], payload['first_name'],
                                                 payload['last_name'], payload['email'], payload['phone_number'])
            if result:
                return Response(data="DONE %s" % result, status=status.HTTP_200_OK)
            else:
                return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as exception:
            logger.debug("Error in list FieldTechnicianView : %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, ft_id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            user = self.request.user
            user_role = user.role
            # [0] because it is assumed that user has only on organization which is new maintainance company
            # org = user.organizations_organization.all()[0]
            org_owner = OrganizationOwner.objects.filter(organization_user__user=user)[0]
            org = org_owner.organization
            company = org.dataglengroup.company
            checking_id = company.owner.organization_user.user.id
            if not checking_id == user.id or not user_role.role == 'OM_VENDOR_ADMIN':
                return Response("Not Authorized to change", status=status.HTTP_401_UNAUTHORIZED)

            ft_user = User.objects.get(id=ft_id)
            checking_ft_in_organization = OrganizationUser.objects.filter(organization=org, user=ft_user)

            if not checking_ft_in_organization:
                return Response("Field Technician not found", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            payload = self.request.data
            response_text = ""
            if 'delete_ft' in payload and int(payload['delete_ft']) == int(ft_id):
                result  = company.delete_site_technician(ft_user)
                return Response("Field Tech deleted. %s" % result, status=status.HTTP_200_OK)
            elif 'account_suspended' in payload:
                flag1 = ""
                if payload['account_suspended'] == True:
                    flag1 = "disabled"
                    # result = Company.disable_site_technician(user)
                    ft_user.role.account_suspended = True
                    ft_user.role.save()
                else:
                    flag1 = "enabled"
                    ft_user.role.account_suspended = False
                    ft_user.role.save()
                    # result = Company.enable_site_technician(user)
                response_text = "Field Tech accound %s" % flag1

            else:
                if 'first_name' in payload:
                    ft_user.first_name = payload['first_name']
                    response_text = "first name,"
                if 'last_name' in payload:
                    ft_user.last_name = payload['last_name']
                    response_text = response_text + "last name,"
                if 'phone_number' in payload:
                    ft_user.role.phone_number = payload['phone_number']
                    ft_user.role.save()
                    response_text = response_text + "phone number,"
                if 'email' in payload:
                    ft_user.email = payload['email']
                    response_text = response_text + "email,"
            ft_user.save()
            if response_text == "":
                response_text = "Nothing is"
            return Response("%s changed" % response_text, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in FieldTechnicianView: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class MaintenanceContractView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def list(self, request, id=None, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            dg_client = self.request.user.role.dg_client
            all_maintenance_companies = Company.objects.filter(groupClient=dg_client).values('id', 'name')
            all_maintenance_companies_ids = []
            for company in all_maintenance_companies:
                all_maintenance_companies_ids.append(company['id'])

            maintenance_contracts = MaintenanceContract.objects.filter(company_id__in=all_maintenance_companies_ids)
            contracts_list = []
            for contract in maintenance_contracts:
                contracts = {}
                contracts['id'] = contract.id
                contracts['name'] = contract.name
                contracts['company'] = contract.company.name
                contracts['start_time'] = contract.start_time
                contracts['end_time'] = contract.end_time
                contracts['phone_number'] = contract.phone_number
                contracts['fax_number'] = contract.fax_number
                contracts['email'] = contract.email
                contracts['comments'] = contract.comments
                contracts['plants'] = contract.plants.all().values_list('name', flat=True)
                contracts_list.append(contracts)

            all_available_plants = SolarPlant.objects.filter(groupClient=dg_client).values('id', 'name')

            master_payload = {}
            master_payload['all_contracts'] = contracts_list
            master_payload['all_plants'] = all_available_plants
            master_payload['all_maintenance_companies'] = all_maintenance_companies
            return Response(data=master_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list MaintenanceContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, id=None, **kwargs):
        """

        :param request:
        :param id:
        :param kwargs:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            dg_client = self.request.user.role.dg_client
            all_maintenance_companies = Company.objects.filter(groupClient=dg_client).values('id', 'name')
            all_maintenance_companies_ids = []
            for company in all_maintenance_companies:
                all_maintenance_companies_ids.append(company['id'])

            maintenance_contracts_ids = MaintenanceContract.objects.filter(
                company_id__in=all_maintenance_companies_ids).values_list('id', flat=True)
            if int(id) in maintenance_contracts_ids:
                contract = MaintenanceContract.objects.get(id=int(id))
            else:
                return Response("wrong contract id", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            this_contract = {}
            this_contract['id'] = contract.id
            this_contract['name'] = contract.name
            this_contract['company'] = contract.company.name
            this_contract['start_time'] = contract.start_time
            this_contract['end_time'] = contract.end_time
            this_contract['phone_number'] = contract.phone_number
            this_contract['fax_number'] = contract.fax_number
            this_contract['email'] = contract.email
            this_contract['comments'] = contract.comments
            this_contract['plants'] = contract.plants.all().values_list('name', flat=True)
            this_contract['SLA'] = contract.slas.all().values('id', 'priority', 'from_state__name', 'to_state__name', 'time',
                                 'consider_closed_hours', 'consider_closed_days')
            # this_contract['operational_hours'] = contract.openinghours_set.all().values('weekday','from_hour','to_hour')
            operational_hours = contract.openinghours_set.all().values('weekday','from_hour','to_hour')
            weekdays = {}
            for day in WEEKDAYS:
                weekdays[day[0]] = {}
                weekdays[day[0]] = day[1].title()

            for oph in operational_hours:
                oph['weekday'] = weekdays[oph.pop('weekday')]

            this_contract['operational_hours'] = operational_hours

            all_available_plants = SolarPlant.objects.filter(groupClient=dg_client).values('id', 'name')

            master_payload = {}
            master_payload['all_contracts'] = this_contract
            master_payload['all_plants'] = all_available_plants
            master_payload['all_maintenance_companies'] = all_maintenance_companies
            return Response(data=master_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list MaintenanceContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, id=None, **kwargs):
        """

        :param request:
        :param kwargs:
        :param id:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            dg_client = self.request.user.role.dg_client
            all_maintenance_companies = Company.objects.filter(groupClient=dg_client).values('id', 'name')
            all_maintenance_companies_ids = []
            for company in all_maintenance_companies:
                all_maintenance_companies_ids.append(company['id'])

            maintenance_contracts_ids = MaintenanceContract.objects.filter(
                company_id__in=all_maintenance_companies_ids).values_list('id', flat=True)
            if int(id) in maintenance_contracts_ids:
                contract = MaintenanceContract.objects.get(id=int(id))
            else:
                return Response("wrong contract id", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            payload = self.request.data

            if "name" in payload:
                contract.name = payload['name']
            if "start_time" in payload:
                contract.start_time = payload['start_time']
            if "end_time" in payload:
                contract.end_time = payload['end_time']
            if "phone_number" in payload:
                contract.phone_number = payload['phone_number']
            if "fax_number" in payload:
                contract.fax_number = payload['fax_number']
            if "email" in payload:
                contract.email = payload['email']
            if "comments" in payload:
                contract.comments = payload['comments']
            # if "plants" in payload:
            #     contract.name = payload['name']
            weekdays = {}
            for day in WEEKDAYS:
                weekdays[day[0]] = {}
                weekdays[day[0]] = day[1].title()
            if "operational_hours" in payload:
                days_list = payload["operational_hours"]
                for day in days_list:
                    if day['weekday'] in weekdays.values():
                        weekday_index = weekdays.keys()[weekdays.values().index('Monday')]
                        opening_hours_obj = contract.openinghours_set.get(weekday=weekday_index)
                        from_hour = parser.parse(day['from_hour'])
                        to_hour = parser.parse(day['to_hour'])
                        opening_hours_obj.from_hour = from_hour.time()
                        opening_hours_obj.to_hour = to_hour.time()
                        opening_hours_obj.save()
                    else:
                        logger.debug("Unknown day in updating Operational Hours")
            if "SLA" in payload:
                list_of_slas =  payload['SLA']
                for sla_single_state in list_of_slas:
                    id = sla_single_state['id']
                    try:
                        sla_obj = SLA.objects.get(id=id)
                    except Exception as exception:
                        return Response("SLA not found %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    if 'consider_closed_hours' in sla_single_state:
                        if type(sla_single_state['consider_closed_hours'])== bool:
                            sla_obj.consider_closed_hours = sla_single_state['consider_closed_hours']
                        else:
                            logger.debug("not bool")
                    if 'consider_closed_days' in sla_single_state:
                        if type(sla_single_state['consider_closed_hours'])== bool:
                            sla_obj.consider_closed_days = sla_single_state['consider_closed_days']
                        else:
                            logger.debug("not bool")

                    if 'time' in sla_single_state:
                        logger.debug(sla_single_state['time'])
                        sla_obj.time = datetime.timedelta(seconds=int(float(sla_single_state['time'])))
                    sla_obj.save()

            if "plants" in payload:
                new_plants_ids = payload["plants"]
                all_available_plants_ids = SolarPlant.objects.filter(groupClient=dg_client).values_list('id',flat=True)
                if not set(new_plants_ids).issubset(all_available_plants_ids):
                    return Response("INTERNAL_SERVER_ERROR: plant not found",
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                current_plants_ids = contract.plants.all().values_list('id', flat=True)
                to_remove_ids = set(current_plants_ids) - set(new_plants_ids)
                to_add_ids = set(new_plants_ids) - set(current_plants_ids)

                for plant_id in to_add_ids:
                    plant = SolarPlant.objects.get(id=plant_id)
                    contract.plants.add(plant)
                for plant_id in to_remove_ids:
                    plant = SolarPlant.objects.get(id=plant_id)
                    contract.plants.remove(plant)

            contract.save()

            return Response(data="Contract Updated", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list Maintenance Contract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, id=None, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:

            user = self.request.user
            user_role = self.request.user.role
            if not user_role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            payload = self.request.data
            company_id = payload.pop('company')
            new_plants_ids = payload.pop('plants')
            all_maintenance_companies = set(
                Company.objects.filter(groupClient=user_role.dg_client).values_list('id', flat=True))
            if company_id in all_maintenance_companies:
                company = Company.objects.get(id=company_id)
            else:
                return Response("INTERNAL_SERVER_ERROR: Company not found",
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                logger.debug("no company found")

            all_available_plants_ids = SolarPlant.objects.filter(groupClient=user_role.dg_client).values_list('id',flat=True)
            if set(new_plants_ids).issubset(all_available_plants_ids):
                pass
            else:
                return Response("INTERNAL_SERVER_ERROR: plant not found",
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                logger.debug("fail")
            start_time = payload.pop('start_time')
            end_time = payload.pop('end_time')
            plant = SolarPlant.objects.get(id=new_plants_ids[0])
            try:
                st = parser.parse(start_time)
                et = parser.parse(end_time)
                start_time = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                end_time = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("please specify start and end time in correct format",
                                status=status.HTTP_400_BAD_REQUEST)
            m = MaintenanceContract.objects.create(company=company, start_time=start_time, end_time=end_time, **payload)
            for plant_id in new_plants_ids:
                plant = SolarPlant.objects.get(id=plant_id)
                m.plants.add(plant)

            return Response(data="Contract Created", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list MaintenanceContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
