import json
import random
from django.views.generic.base import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from solarrms.admin_forms import AddInverterForm, MultiplicationFactorForm, AddMeterForm,\
    AddAJBForm, AddClientAndPlantForm, AddSolarFieldFrom, AddPayloadErrorCheckFrom, ResetPassword
from django.core.exceptions import PermissionDenied
from solarrms.models import SolarGroup, SolarPlant, SolarField, IndependentInverter, EnergyMeter,\
    AJB, PlantMetaSource, GatewaySource, MPPT, VirtualGateway
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.db import transaction
from solarrms.admin_utils import define_client_subscription_plan, define_roles_access_for_client, send_email
from organizations.models import OrganizationOwner
from organizations.models import OrganizationUser
from dgusers.models import UserRole
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from rest_framework.authtoken.models import Token
from dashboards.models import DataglenClient, Dashboard
from dataglen.models import Sensor, Field
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe


class BaseTemplateView(TemplateView):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            raise PermissionDenied
        return super(BaseTemplateView, self).dispatch(request, *args, **kwargs)
        

class AdminInverterView(BaseTemplateView):
    template_name = 'admin/admin_inverter.html'

    def get(self, request, *args, **kwargs):
        form = AddInverterForm
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        solar_plant = post_data.get("solar_plant", None)
        solar_group = post_data.get("solar_group", None)
        total_capacity = float(post_data.get("total_capacity", 0))
        actual_capacity = float(post_data.get("actual_capacity", None))
        manufacturer = post_data.get("manufacturer", None)
        model = post_data.get("model", None)
        total_number_inverters = int(post_data.get("total_number_inverters", None))
        if solar_plant and total_capacity and actual_capacity and total_number_inverters > 0:
            solar_plant = SolarPlant.objects.get(id=solar_plant)
            if solar_group:
                solar_group = SolarGroup.objects.get(id=solar_group)
            user = solar_plant.metadata.plantmetasource.user
            inverter_instance = ""
            with transaction.atomic():
                # if solar group is present assign name of solar group to inverter
                if solar_group:
                    no_of_existing_inverters = len(solar_group.groupIndependentInverters.all())
                    inverter_name_prefix = "%s_Inverter_" % (solar_group.name)
                else:
                    # as solar group is not provided set inverter name as following
                    # check if inverters are aleady present, if present continue numbering from there...
                    no_of_existing_inverters = len(solar_plant.independent_inverter_units.all())
                    inverter_name_prefix = "%s_Inverter_" % (solar_plant.slug)
                for inv_i in range(0, total_number_inverters):
                    inverter_name = "%s_Inverter_%s" % (inverter_name_prefix, inv_i + no_of_existing_inverters + 1)
                    inverter = IndependentInverter.objects.create(plant=solar_plant,
                                                       name=inverter_name,
                                                       displayName=inverter_name,
                                                       total_capacity=total_capacity,
                                                       actual_capacity=actual_capacity,
                                                       manufacturer=manufacturer,
                                                       model=model,
                                                       user=user,
                                                       dataTimezone="%s" % solar_plant.metadata.plantmetasource.dataTimezone,
                                                       isActive=True,
                                                       isMonitored=True,
                                                       templateName='INVERTER_TEMPLATE',
                                                       timeoutInterval=2700,
                                                       dataReportingInterval=300,
                                                       dataFormat='JSON')
                    if solar_group:
                        solar_group.groupIndependentInverters.add(inverter)
                    inverter_instance += "%s, " % inverter
            message_data = "Success! %s" % inverter_instance
            messages.success(request, " %s" % message_data)
            return HttpResponseRedirect("")
        else:
            message_data = "Failed!"
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")


class AdminMeterView(BaseTemplateView):
    template_name = 'admin/admin_meter.html'

    def get(self, request, *args, **kwargs):
        form = AddMeterForm
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        solar_plant = post_data.get("solar_plant", None)
        solar_group = post_data.get("solar_group", None)
        manufacturer = post_data.get("manufacturer", None)
        model = post_data.get("model", None)
        energy_calculation = post_data.get("energy_calculation", False)
        total_number_meters = int(post_data.get("total_number_meter", None))
        if solar_plant and total_number_meters > 0:
            solar_plant = SolarPlant.objects.get(id=solar_plant)
            if solar_group:
                solar_group = SolarGroup.objects.get(id=solar_group)
            user = solar_plant.metadata.plantmetasource.user
            meter_instance = ""
            with transaction.atomic():
                for meter_i in range(0, total_number_meters):
                    inveter_name = "%s_Energy_Meter_%s" % (solar_plant.slug, meter_i+1)
                    meter = EnergyMeter.objects.create(plant=solar_plant,
                                                       name=inveter_name,
                                                       displayName=inveter_name,
                                                       manufacturer=manufacturer,
                                                       dataReportingInterval=300,
                                                       model=model,
                                                       user=user,
                                                       dataTimezone="%s" % solar_plant.metadata.plantmetasource.dataTimezone,
                                                       isActive=True,
                                                       isMonitored=True,
                                                       dataFormat='JSON',
                                                       templateName='ENERGY_METER_TEMPLATE',
                                                       timeoutInterval=2700,
                                                       energy_calculation=energy_calculation)
                    if solar_group:
                        solar_group.groupEnergyMeters.add(meter)
                    meter_instance += "%s, " % meter
            message_data = "Success! %s" % meter_instance
            messages.success(request, " %s" % message_data)
            return HttpResponseRedirect("")
        else:
            message_data = "Failed!"
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")


class AdminSetMultiplicationFactorView(BaseTemplateView):
    template_name = 'admin/admin_set_multiplication_factor.html'

    def get(self, request, *args, **kwargs):
        form = MultiplicationFactorForm
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        if 'source_key' in post_data and 'source_streams' in post_data:
            source_keys = post_data.getlist("source_key", None)
            source_streams = post_data.getlist("source_streams", None)
            multiplication_factor = post_data.get("multiplication_factor", None)
            stream_data_type = post_data.get("stream_data_type", None)
            change_display_name = post_data.get("change_display_name", None)

            if '_setmf' in post_data:
                solar_fields = Field.objects.filter(source__sourceKey__in=source_keys, name__in=source_streams)
                solar_fields.update(multiplicationFactor=multiplication_factor)
                message_data = "Success! MF set"
                messages.success(request, " %s" % message_data)
                return HttpResponseRedirect("")
            elif '_deactive' in post_data:
                solar_fields = Field.objects.filter(source__sourceKey__in=source_keys, name__in=source_streams)
                solar_fields.update(isActive=False)
                message_data = "Success! Stream Deactive"
                messages.success(request, " %s" % message_data)
                return HttpResponseRedirect("")

            elif '_active' in post_data:
                solar_fields = Field.objects.filter(source__sourceKey__in=source_keys, name__in=source_streams)
                solar_fields.update(isActive=True)
                message_data = "Success! Stream Active"
                messages.success(request, " %s" % message_data)
                return HttpResponseRedirect("")

            elif '_changedt' in post_data:
                solar_fields = Field.objects.filter(source__sourceKey__in=source_keys, name__in=source_streams)
                solar_fields.update(streamDataType=stream_data_type)
                message_data = "Success! Set DataType"
                messages.success(request, " %s" % message_data)
                return HttpResponseRedirect("")

            elif '_changedn' in post_data:
                solar_fields = SolarField.objects.filter(source__sourceKey__in=source_keys, name__in=source_streams)
                solar_fields.update(displayName=change_display_name)
                message_data = "Success! Set Display Name"
                messages.success(request, " %s" % message_data)
                return HttpResponseRedirect("")
            
            else:
                message_data = "Noting to change"
                messages.error(request, " %s" % message_data)
                return HttpResponseRedirect("")

        else:
            message_data = "Source Stream Can't be None!"
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")


def get_solar_plant(request):
    """

    :param request:
    :return:
    """
    if request.method == "POST" and request.is_ajax():
        all_plants = SolarPlant.objects.all().values('id', 'name')
        solar_plants = []
        for solar_plant in all_plants:
            solar_plants.append({'id': solar_plant['id'], 'name': solar_plant['name']})
        response = json.dumps(solar_plants)
        return HttpResponse(response, content_type="application/json")
    return HttpResponseNotAllowed(['GET'])


def get_solar_group_for_plant_admin(request):
    """

    :return:
    """
    if request.method == "POST" and request.is_ajax():
        response = ""
        plant_id = int(request.POST.get("plant_id", None))
        plant_groups = []
        if plant_id:
            all_solar_groups = SolarGroup.objects.filter(plant_id=plant_id).values('id', 'name')
            for solar_group in all_solar_groups:
                plant_groups.append({'id': solar_group['id'], 'name': solar_group['name']})
            response = json.dumps(plant_groups)
            return HttpResponse(response, content_type="application/json")
        else:
            return HttpResponse(response, content_type="application/json")
    return HttpResponseNotAllowed(['GET'])


def get_source_for_plant_group_admin(request):
    """

    :return:
    """
    if request.method == "POST" and request.is_ajax():
        response = ""
        plant_id = int(request.POST.get("plant_id", None))
        devices = request.POST.get("devices", None)
        #group_id = int(request.POST.get("group_id", None))
        source_key = []
        if plant_id:
            plant = SolarPlant.objects.get(id=plant_id)
            #group = SolarGroup.objects.filter(id=group_id)
            if 'inverter' in devices:
                inverters = plant.independent_inverter_units.all()
                for source in inverters.values('sourceKey', 'name'):
                    source_key.append({'sourceKey': source['sourceKey'], 'name': source['name']})
            if 'meter' in devices:
                meters = plant.energy_meters.all()
                for source in meters.values('sourceKey', 'name'):
                    source_key.append({'sourceKey': source['sourceKey'], 'name': source['name']})
            if 'abj' in devices:
                ajbs = plant.ajb_units.all()
                for source in ajbs.values('sourceKey', 'name'):
                    source_key.append({'sourceKey': source['sourceKey'], 'name': source['name']})
            if 'mppt' in devices:
                mppts = plant.mppt_units.all()
                for source in mppts.values('sourceKey', 'name'):
                    source_key.append({'sourceKey': source['sourceKey'], 'name': source['name']})
            if 'plantmeta' in devices:
                source_key.append({'sourceKey': plant.metadata.plantmetasource.sourceKey,
                                   'name': plant.metadata.plantmetasource.name})
            if 'gateway' in devices:
                gateway = plant.gateway.all()
                for source in gateway.values('sourceKey', 'name'):
                    source_key.append({'sourceKey': source['sourceKey'], 'name': source['name']})
            if 'virtual' in devices:
                virtual = plant.virtual_gateway_units.all()
                for source in virtual.values('sourceKey', 'name'):
                    source_key.append({'sourceKey': source['sourceKey'], 'name': source['name']})
            response = json.dumps(source_key)
            return HttpResponse(response, content_type="application/json")
        else:
            return HttpResponse(response, content_type="application/json")
    return HttpResponseNotAllowed(['GET'])


def get_stream_for_sources_admin(request):
    """

    :return:
    """
    if request.method == "POST" and request.is_ajax():
        response = ""
        source_keys = request.POST.getlist("sourcekeys[]", None)
        solar_fields = []
        all_stream_name = SolarField.objects.filter(source__sourceKey__in=source_keys).\
                                       values('name', 'displayName', 'isActive',
                                              'multiplicationFactor', 'streamDataType')
        for stream_name in all_stream_name:
            stream_name_details = "%s, %s, %s, %s, %s" % (stream_name['name'],
                                                          stream_name['displayName'],
                                                          stream_name['isActive'],
                                                          stream_name['multiplicationFactor'],
                                                          stream_name['streamDataType'])
            solar_fields.append({'stream_name': stream_name['name'],
                                 'stream_name_details': stream_name_details})
        response = json.dumps(solar_fields)
        return HttpResponse(response, content_type="application/json")
    return HttpResponseNotAllowed(['GET'])


class AdminAJBView(BaseTemplateView):
    template_name = 'admin/admin_ajb.html'

    def get(self, request, *args, **kwargs):
        form = AddAJBForm
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        solar_plant = post_data.get("solar_plant", None)
        solar_group = post_data.get("solar_group", None)
        display_name = post_data.get("display_name", None)
        manufacturer = post_data.get("manufacturer", None)
        total_number_abjs = int(post_data.get("total_number_abjs", None))
        inverters = post_data.get("inverters", None)
        if solar_plant and total_number_abjs > 0:
            solar_plant = SolarPlant.objects.get(id=solar_plant)
            if solar_group:
                solar_group = SolarGroup.objects.get(id=solar_group)
            if inverters:
                inverters = IndependentInverter.objects.get(sourceKey=inverters)
            user = solar_plant.metadata.plantmetasource.user
            abj_instance = ""
            with transaction.atomic():
                for inv_i in range(0, total_number_abjs):
                    if not inverters:
                        ajb_name = "%s_AJB_%s" % (solar_plant.slug, inv_i+1)
                    else:
                        ajb_name = "%s_%s_AJB_%s" % (solar_plant.slug, inverters.name, inv_i+1) 
                    ajb = AJB.objects.create(plant=solar_plant,
                                                       name=ajb_name,
                                                       displayName=ajb_name,
                                                       manufacturer=manufacturer,
                                                       user=user,
                                                       dataTimezone="%s" % solar_plant.metadata.plantmetasource.dataTimezone,
                                                       isActive=True,
                                                       isMonitored=True,
                                                       templateName='AJB_TEMPLATE',
                                                       timeoutInterval=2700,
                                                       dataReportingInterval=300,
                                                       independent_inverter=inverters,
                                                       dataFormat='JSON')
                    if solar_group:
                        solar_group.groupAJBs.add(ajb)
                    abj_instance += "%s, " % ajb
            message_data = "Success! %s" % abj_instance
            messages.success(request, " %s" % message_data)
            return HttpResponseRedirect("")
        else:
            message_data = "Failed!"
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")


class AdminAddClientAndPlantView(BaseTemplateView):
    template_name = 'admin/admin_add_client_and_plant.html'

    def get(self, request, *args, **kwargs):
        form = AddClientAndPlantForm
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        config_dict = {}

        config_dict['USER_NAME'] = post_data.get("email_as_user_name", None)
        config_dict['PASSWORD'] = post_data.get("password", None)
        config_dict['EMAIL'] = post_data.get("email_as_user_name", None)
        config_dict['FIRST_NAME'] =  post_data.get("first_name", None)
        config_dict['LAST_NAME'] = post_data.get("last_name", None)

        config_dict['CLIENT_NAME'] = post_data.get("client_name", None)
        config_dict['CLIENT_ACTIVE'] = post_data.get("is_active", True)
        config_dict['CLIENT_SLUG'] = post_data.get("client_slug", None)
        config_dict['CLIENT_WEBSITE'] = post_data.get("client_website", None)
        config_dict['CLIENT_DASHBOARD'] = "SOLAR"
        config_dict['CLIENT_CAN_CREATE_GROUPS'] = post_data.get("can_create_groups", True)

        random_number = random.randint(1, 9999)
        new_plant_name = "DemoPlant_%s" % random_number

        with transaction.atomic():
            # desc, client, user, token = create_dataglen_client(config_dict, False)
            # user = clientCreation.add_user()
            user = User.objects.filter(username=config_dict["USER_NAME"])
            if not user:
                user = User.objects.create_user(config_dict["USER_NAME"],
                                                config_dict["EMAIL"],
                                                config_dict["PASSWORD"],
                                                first_name=config_dict["FIRST_NAME"],
                                                last_name=config_dict["LAST_NAME"])
                user.save()
                print "New user created"

            # clientCreation.add_email(user)
            email_address, created = EmailAddress.objects.get_or_create(user=user,
                                                                        email=config_dict["EMAIL"],
                                                                        verified=True,
                                                                        primary=True)
            if created:
                print "Email address added"


            # client = clientCreation.add_client()
            try:
                client = DataglenClient.objects.get(slug=config_dict["CLIENT_SLUG"])
            except ObjectDoesNotExist:
                print "dataglen client not found"
                dashboard = Dashboard.objects.get(name=config_dict["CLIENT_DASHBOARD"])
                client = DataglenClient.objects.create(name=config_dict["CLIENT_NAME"],
                                                       is_active=config_dict["CLIENT_ACTIVE"],
                                                       slug=config_dict["CLIENT_SLUG"],
                                                       clientWebsite=config_dict["CLIENT_WEBSITE"],
                                                       clientDashboard=dashboard,
                                                       canCreateGroups=config_dict["CLIENT_CAN_CREATE_GROUPS"])
                print "Client Created"

            ur = UserRole.objects.create(user=user, role="CEO", dg_client=client)

            # organization_user = clientCreation.create_organization_user(user, client)
            organization_user, created = OrganizationUser.objects.get_or_create(user=user, organization=client)
            if created:
                print "Organization User Created"

            # organization_owner = clientCreation.create_organization_owner(client, organization_user)
            organization_owner, created = OrganizationOwner.objects.get_or_create(organization=client, \
                                                                                  organization_user=organization_user)
            if created:
                print "Organization Owner Created"

            # token = clientCreation.get_auth_token(user)
            token = Token.objects.get(user=user)

            # email_content = clientCreation.email_send(token, send_email)
            desc = 'A new Client has been created on dataglen.com with following details \n\nClient Name ' + str(
                config_dict["CLIENT_NAME"]) + '\n' + 'User Name: ' + str(
                config_dict["USER_NAME"]) + '\n' + 'Email: ' + str(
                config_dict["EMAIL"]) + '\n' + 'Password: ' + str(
                config_dict["PASSWORD"]) + '\n' + 'Dashboard: ' + str(
                config_dict['CLIENT_DASHBOARD']) + '\n' + 'API-KEY: ' + str(token.key)

            # plantCreation = PlantCreation(config_dict)
            # plant = plantCreation.add_plant(client)
            plant = SolarPlant.objects.create(name=new_plant_name,
                                              groupClient=client,
                                              is_active=True,
                                              capacity=10,
                                              location="Bangalore",
                                              openweather="blr",
                                              isOperational=True)
            print "plant created: ", plant.slug
            # plant_user = plantCreation.create_plant_user(user, plant)
            organization_user, created = OrganizationUser.objects.get_or_create(user=user, organization=plant)
            if created:
                print
                "Plant User Created"
            print "Plant User is %s" % organization_user
            # plant_owner = plantCreation.create_plant_owner(plant, plant_user)
            organization_owner, created = OrganizationOwner.objects.get_or_create(organization=plant,
                                                                                  organization_user=organization_user)
            if created:
                print "Plant Owner Created"
            print "Plant Owner is %s" % organization_owner

            # token = plantCreation.get_auth_token(user)
            print "got auth token %s" % token
            # plant_meta_source_key = plantCreation.add_plant_meta_source(plant, user)
            plant_meta_source = PlantMetaSource.objects.create(plant=plant,
                                                               user=user,
                                                               name="PlantMeta_%s" % plant.slug,
                                                               isActive=True,
                                                               isMonitored=True,
                                                               dataFormat='JSON',
                                                               sending_aggregated_power=False,
                                                               sending_aggregated_energy=False,
                                                               energy_meter_installed=False,
                                                               PV_panel_area=0,
                                                               PV_panel_efficiency=0,
                                                               operations_start_time="0",
                                                               operations_end_time="0",
                                                               calculate_hourly_pr=False)
            print "Plant meta source created.", plant_meta_source.sourceKey
            # solar_metrics = plantCreation.add_solar_metrics(plant, user)
            # features_enabled = plantCreation.add_plant_features_enabled(plant)
            # queue = plantCreation.add_queue(plant)
            # should get called only once
            define_client_subscription_plan(client)
            define_roles_access_for_client(client)
            send_email(plant, desc, plant_meta_source.name, plant_meta_source.sourceKey)

        message_data = "Success! %s" % post_data
        messages.success(request, " %s" % message_data)
        return HttpResponseRedirect("")


class AdminSolarFieldView(BaseTemplateView):
    template_name = 'admin/admin_solar_field.html'

    def get(self, request, *args, **kwargs):
        form = AddSolarFieldFrom
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        source_keys = post_data.getlist("source_key", None)
        stream_name = post_data.get("stream_name", None)
        stream_display_name = post_data.get("stream_display_name", None)
        multiplication_factor = post_data.get("multiplication_factor", None)
        if source_keys and stream_name:
            solar_field_instance = ""
            with transaction.atomic():
                for source_key in source_keys:
                    source = Sensor.objects.get(sourceKey=source_key)
                    solar_field = SolarField.objects.create(source=source,
                                                             name=stream_name,
                                                             displayName=stream_display_name,
                                                             isActive=True,
                                                             streamDataType="FLOAT",
                                                             multiplicationFactor=multiplication_factor)
                    solar_field_instance += "%s" % solar_field
            message_data = "Success! %s" % solar_field_instance
            messages.success(request, " %s" % message_data)
            return HttpResponseRedirect("")
        else:
            message_data = "Failed!"
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")


class AdminPayloadErrorCheckView(BaseTemplateView):
    template_name = 'admin/admin_payload_error_check.html'

    def get(self, request, *args, **kwargs):
        form = AddPayloadErrorCheckFrom
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        source_key = post_data.getlist("source_key", None)
        source_key_string = post_data.get("source_key_string", None)
        data_write_payload = post_data.get("data_write_payload", None)
        if (source_key or source_key_string) and data_write_payload:
            data_write_payload = json.loads(data_write_payload)
            sourcekey = source_key if source_key else source_key_string
            message_data = "Payload Check List! <br /><br />"
            # check source key is active, is monitored, datatype json
            sensor = Sensor.objects.get(sourceKey=sourcekey)
            message_data += "Source Details <br />"
            message_data += "Active:- %s <br /> Monitored:- %s <br /> " \
                           "Template:- %s <br /> DataTimezone:- %s <br /> DataFormat:- %s <br />" % (
                            sensor.isActive,
                            sensor.isMonitored,
                            sensor.templateName,
                            sensor.dataTimezone,
                            sensor.dataFormat)
            # find is there any new stream_name
            all_fields = set(sensor.fields.all().values_list('name', flat=True))
            stream_name_set = set(data_write_payload.keys())
            extra_stream_in_payload = stream_name_set - all_fields
            if extra_stream_in_payload:
                message_data += "<br />"
                message_data += "Extra Stream_name :- "
                for stream_name in extra_stream_in_payload:
                    message_data += "%s, " % stream_name
            # check if any stream_name is set to false
            inactive_stream_name = set(sensor.fields.filter(isActive=False, name__in=stream_name_set).
                                        values_list('name', flat=True))
            if inactive_stream_name:
                message_data += "<br /><br />"
                message_data += "InActive Stream_name :- "
                for stream_name in inactive_stream_name:
                    message_data += "%s, " % stream_name
            # check if any streamDataType is set to false
            notfloat_stream_name = set(sensor.fields.filter(name__in=stream_name_set).
                                       exclude(streamDataType='FLOAT').values_list('name', flat=True))
            if notfloat_stream_name:
                message_data += "<br /><br />"
                message_data += "Not Float Stream_name :- "
                for stream_name in notfloat_stream_name:
                    message_data += "%s, " % stream_name
            # get plant and device details
            message_data += "<br /><br />"
            if sensor.templateName == "INVERTER_TEMPLATE":
                inv = IndependentInverter.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % inv.plant
            elif sensor.templateName == "AJB_TEMPLATE":
                ajb = AJB.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % ajb.plant
            elif sensor.templateName == "ENERGY_METER_TEMPLATE":
                meter = EnergyMeter.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % meter.plant
            elif sensor.templateName == "GATEWAY_TEMPLATE":
                gateway = GatewaySource.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % gateway.plant
            elif sensor.templateName == "PLANT_META_TEMPLATE":
                plantmeta = PlantMetaSource.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % plantmeta.plant
            elif sensor.templateName == "WEBDYN_TEMPLATE":
                vgateway = VirtualGateway.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % vgateway.plant
            else:
                mppt = MPPT.objects.get(sensor_ptr=sensor.id)
                message_data += "Plant :- %s" % mppt.plant
            messages.success(request, mark_safe(message_data))
            return HttpResponseRedirect("")
        else:
            message_data = "Failed!"
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")

class AdminResetPasswordView(BaseTemplateView):
    template_name = 'admin/admin_reset_password.html'

    def get(self, request, *args, **kwargs):
        form = ResetPassword
        return self.render_to_response({'form':form, 'user':request.user})

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        email = post_data.get("email", None)
        new_password = post_data.get("new_password", None)
        confirm_password = post_data.get("confirm_password", None)
        try:
            user = User.objects.get(email=email, is_superuser=False, is_staff=False)
        except:
            user = None
        if user and new_password and confirm_password:
            if new_password != confirm_password:
                message_data = "new password and confirm password should be same!"
                messages.error(request, " %s" % message_data)
                return HttpResponseRedirect("")
            user.set_password(new_password)
            user.save()
            message_data = "Success! Password Changed for email %s" % email
            messages.success(request, " %s" % message_data)
            return HttpResponseRedirect("")
        else:
            message_data = "Failed! User with this email not found %s" % email
            messages.error(request, " %s" % message_data)
            return HttpResponseRedirect("")

