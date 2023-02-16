from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from dashboards.mixins import ProfileDataInAPIs
import sys, logging, dateutil
from solarrms.models import SolarPlant, SolarGroup, IndependentInverter, PlantMetaSource, WeatherStation, EnergyMeter, \
    SolarMetrics, PVSystInfo
from dwebdyn.utils import add_plant_parameters, create_plant_user, create_plant_owner, add_solar_groups, \
    add_independent_inverters, add_independent_inverters_for_delremo, create_plant_meta_source, add_energy_meter, add_weather_station, add_plant_gateway_source, \
    add_solar_metrics, add_plant_features_enabled, add_queue, add_plant_virtual_gateway, add_webdyn_gateway, \
    add_webdyn_inverters_device, add_webdyn_modbus_inverter_device, add_webdyn_modbus_energy_meter_device, \
    add_webdyn_io_devices, get_request_json_for_ftp_post_call
from dwebdyn.serializers import  PlantDataEntrySerializer, DeviceDataEntrySerializer
import json
import requests
from solarrms.settings import DGC_FTP_CLIENT_MAPPING
from dashboards.utils import is_owner
from dwebdyn.models import WebdynClient, WebdynGateway, InvertersDevice, ModbusDevice, IODevice
from dwebdyn.inverter_delta_template import set_delta_inverter_error_codes
from dwebdyn.inverter_huawei_template import set_huawei_inverter_error_codes
from dwebdyn.inverter_microlyte_template import set_microlyte_inverter_error_codes
from dwebdyn.inverter_sungrow_template import set_sungrow_inverter_error_codes
from dwebdyn.inverter_solis_template import set_solis_inverter_error_codes
from dwebdyn.inverter_waaree_template import set_waaree_inverter_error_codes

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

FTP_SERVER_ADDRESS = 'http://ftp.dataglen.com/'
#FTP_SERVER_ADDRESS = 'http://127.0.0.1:8000/'
FTP_DEVICES_ADDRESS = 'provisioning/devices/'
FTP_ADD_ADDRESS = 'provisioning/add/'
FTP_SMA_IM_ADDRESS = 'provisioning/smaim/'
FTP_SMA_WB_ADDRESS = 'provisioning/smawb/'
WEBDYN_FTP_API_KEY = '2fab9ff946d235aa55f43911a4150ed1596b4ff3'
token = 'Token ' + WEBDYN_FTP_API_KEY
auth_header = {'Authorization ': token, 'content-type': 'application/json'}

class CreatePlantsView(ProfileDataInAPIs, viewsets.ViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request):
        try:
            try:
                owner, client = is_owner(self.request.user)
                if owner:
                    dataglen_client = client.dataglenclient
                else:
                    dataglen_client = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient
            except Exception as exception:
                logger.debug(str(exception))
                return Response("You do not have access rights to create a new plant.", status=status.HTTP_403_FORBIDDEN)
            try:
                dataglen_client_owner = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient.owner.organization_user.user
            except Exception as exception:
                try:
                    dataglen_client_owner = self.request.user.organizations_organization.all()[1].dataglengroup.groupClient.owner.organization_user.user
                except:
                    logger.debug(str(exception))
                    return Response("You do not have access rights to create a new plant.", status=status.HTTP_403_FORBIDDEN)
            try:
                payload = self.request.data
                # create the plant
                try:
                    serializer = PlantDataEntrySerializer(data=request.data)
                    if serializer.is_valid():
                        plant = add_plant_parameters(dataglen_client, payload['plant_details'])
                        logger.debug(plant)
                        client_user = create_plant_user(dataglen_client_owner, plant)
                        client_owner = create_plant_owner(client_user, plant)
                        plant_user = create_plant_user(self.request.user, plant)
                        plant_meta = create_plant_meta_source(dataglen_client_owner, plant, payload['module_details'])
                        virtual_gateway_source = add_plant_virtual_gateway(plant, dataglen_client_owner)
                        gateway_source = add_plant_gateway_source(plant, dataglen_client_owner)
                        solar_metrics = add_solar_metrics(plant,dataglen_client_owner)
                        features_enabled = add_plant_features_enabled(plant)
                        queue = add_queue(plant)
                        response = {}
                        response["plant_slug"] = str(plant.slug)
                        try:
                            response["plant_gateway_key"] = str(plant.gateway.all()[0].sourceKey)
                            response["plant_virtual_gateway_key"] = str(plant.virtual_gateway_units.all()[0].sourceKey)
                            response["plant_metadata_key"] = str(plant.metadata.plantmetasource.sourceKey)
                        except:
                            pass

                        return Response(response, status=status.HTTP_201_CREATED)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("Please correct the plant details", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
        except Exception as exception:
            logger.debug(str(exception))


def create_devices_on_ftp(client_slug, device_id, device_type):
    try:
        # get the request json
        request_json = get_request_json_for_ftp_post_call(client_slug, device_id)
        logger.debug(request_json)
        logger.debug(device_type)
        if device_type == 'WEBDYN':
            actual_url = FTP_SERVER_ADDRESS + FTP_ADD_ADDRESS
        elif device_type == 'SMA_IM':
            actual_url = FTP_SERVER_ADDRESS + FTP_SMA_IM_ADDRESS
        elif device_type == 'SMA_WB':
            actual_url = FTP_SERVER_ADDRESS + FTP_SMA_WB_ADDRESS
        else:
            return "Invalid device type"
        #actual_url = actual_url + "?clientslug=" + client_slug + "&deviceid=" + device_id
        logger.debug(actual_url)
        params = {}
        params['clientslug'] = client_slug
        params['deviceid'] = device_id
        response = requests.post(url=actual_url, json=request_json, params=params)
        logger.debug(response.content)
        return response
    except Exception as exception:
        logger.debug(str(exception))



class CreateDelRemoPlantInvertersView(ProfileDataInAPIs, viewsets.ViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request):
        try:
            try:
                owner, client = is_owner(self.request.user)
                if owner:
                    dataglen_client = client.dataglenclient
                else:
                    dataglen_client = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient
            except Exception as exception:
                logger.debug(str(exception))
                return Response("You do not have access rights to create a new plant.", status=status.HTTP_403_FORBIDDEN)
            try:
                dataglen_client_owner = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient.owner.organization_user.user
            except Exception as exception:
                try:
                    dataglen_client_owner = self.request.user.organizations_organization.all()[1].dataglengroup.groupClient.owner.organization_user.user
                except:
                    logger.debug(str(exception))
                    return Response("You do not have access rights to create a new plant.", status=status.HTTP_403_FORBIDDEN)
            try:
                try:
                    payload = self.request.data
                    logger.debug(payload)
                    logger.debug(type(payload["inverters"]))
                    logger.debug(len(payload["inverters"]))
                except:
                    logger.exception("Error parsing payload")

                try:
                    plant_slug = self.request.data["plant_slug"]
                    plant = SolarPlant.objects.get(slug=plant_slug)
                except:
                    return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)
                independent_inverters = []
                try:
                    if len(payload["inverters"]) > 0:
                        for i in range(len(payload["inverters"])):
                            independent_inverter = add_independent_inverters_for_delremo(plant, dataglen_client_owner, payload['inverters'][i])
                            if independent_inverter is not None:
                                independent_inverters.append(independent_inverter)
                        return Response(independent_inverters, status=status.HTTP_201_CREATED)
                    else:
                        return Response("No inverters added", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.exception("while adding a new delremo inverter")
                    logger.debug(str(exception))
                    return Response("Bad request", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
        except Exception as exception:
            logger.debug(str(exception))

class CreatePlantDevicesView(ProfileDataInAPIs, viewsets.ViewSet):

        authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
        permission_classes = (permissions.IsAuthenticated,)

        def create(self, request):
            try:
                try:
                    owner, client = is_owner(self.request.user)
                    if owner:
                        dataglen_client = client.dataglenclient
                    else:
                        dataglen_client = self.request.user.organizations_organization.all()[
                            0].dataglengroup.groupClient
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("You do not have access rights to create a new plant.",
                                    status=status.HTTP_403_FORBIDDEN)
                try:
                    dataglen_client_owner = self.request.user.organizations_organization.all()[
                        0].dataglengroup.groupClient.owner.organization_user.user
                except Exception as exception:
                    try:
                        dataglen_client_owner = self.request.user.organizations_organization.all()[
                            1].dataglengroup.groupClient.owner.organization_user.user
                    except:
                        logger.debug(str(exception))
                        return Response("You do not have access rights to create a new plant.",
                                        status=status.HTTP_403_FORBIDDEN)
                try:
                    payload = self.request.data
                    plant_slug = self.request.query_params.get("plant_slug", None)
                    try:
                        plant = SolarPlant.objects.get(slug=plant_slug)
                    except:
                        return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)

                    device_type = self.request.query_params.get("device_type", None)

                    if device_type is None:
                        return Response("Please specify a device type to add", status=status.HTTP_400_BAD_REQUEST)

                    if str(device_type).upper() not in ['WEBDYN', 'SMA_IM', 'SMA_WB']:
                        return Response("Invalid device type", status=status.HTTP_400_BAD_REQUEST)

                    try:
                        serializer = DeviceDataEntrySerializer(data=request.data)
                        if serializer.is_valid():
                            try:
                                webdyn_client_slug = DGC_FTP_CLIENT_MAPPING[str(dataglen_client.slug)]
                                webdyn_client = WebdynClient.objects.get(slug=webdyn_client_slug)
                            except Exception as exception:
                                logger.debug(str(exception))
                                return Response("Webdyn client Not found. Please contact the system administrator",
                                                status=status.HTTP_400_BAD_REQUEST)

                            # add group
                            groups = add_solar_groups(plant, dataglen_client_owner, dataglen_client,
                                                      payload['group_details'])
                            if groups:
                                group = groups[0]
                                # add WebdynGateway
                                webdyn_gateway = add_webdyn_gateway(plant, group, webdyn_client)

                            # add inverters devices
                            independent_inverters = []
                            webdyn_inverter_devices = []
                            if len(payload["inverters"]) > 0:
                                for i in range(len(payload["inverters"])):
                                    independent_inverter = add_independent_inverters(plant, dataglen_client_owner,
                                                                                     payload['inverters'][i], group)
                                    independent_inverters.append(independent_inverter)
                                    # add the inverter details to InvertersDevice model
                                    if str(device_type).upper() == 'WEBDYN':
                                        webdyn_inverter_device = webdyn_inverter_device = add_webdyn_inverters_device(
                                            webdyn_gateway, independent_inverter)
                                    elif str(device_type).upper() == 'SMA_IM':
                                        webdyn_inverter_device = webdyn_inverter_device = add_webdyn_inverters_device(
                                            webdyn_gateway, independent_inverter, fields_template="SMAIM_INVERTER")
                                    elif str(device_type).upper() == 'SMA_WB':
                                        webdyn_inverter_device = webdyn_inverter_device = add_webdyn_inverters_device(
                                            webdyn_gateway, independent_inverter, fields_template="SMA_WEB_BOX")

                                    webdyn_inverter_devices.append(webdyn_inverter_device)

                                try:
                                    inv_manufacturer = payload['inverters'][0]['manufacturer']
                                    logger.debug(inv_manufacturer)
                                    if str(inv_manufacturer).upper().startswith("DELTA"):
                                        set_delta_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for delta inverters.")
                                    elif str(inv_manufacturer).upper().startswith("SUNGROW"):
                                        set_sungrow_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for sungrow inverters.")
                                    elif str(inv_manufacturer).upper().startswith("MODBUS_MICROLYTE"):
                                        set_microlyte_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for microlyte inverters.")
                                    elif str(inv_manufacturer).upper().startswith("MODBUS_INV_HUAWEI_33K_SUN2000"):
                                        set_huawei_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for microlyte inverters.")
                                    elif str(inv_manufacturer).upper().startswith("SOLIS"):
                                        set_solis_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for solis inverters.")
                                    elif str(inv_manufacturer).upper().startswith("WAAREE"):
                                        set_waaree_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for waaree inverters.")

                                    else:
                                        pass
                                except Exception as exception:
                                    logger.debug("Error in adding inverter status mappings : " + str(exception))
                                    pass

                            # add modbus devices
                            modbus_independent_inverters = []
                            webdyn_modbus_inverter_devices = []
                            webdyn_modbus_energy_meters = []
                            if len(payload["modbus"]) > 0:
                                for i in range(len(payload["modbus"])):
                                    if (payload["modbus"][i]["device"]).upper() == "INVERTER":
                                        independent_inverter = add_independent_inverters(plant,
                                                                                         dataglen_client_owner,
                                                                                         payload['modbus'][i],
                                                                                         group)
                                        modbus_independent_inverters.append(independent_inverter)
                                        # add inverter details to ModbusDevice
                                        # str(device_type).upper() not in ['WEBDYN', 'SMA_IM', 'SMA_WB']
                                        webdyn_modbus_inverter = add_webdyn_modbus_inverter_device(webdyn_gateway,
                                                                                                   independent_inverter)
                                        webdyn_modbus_inverter_devices.append(webdyn_modbus_inverter)
                                    elif (payload["modbus"][i]["device"]).upper() == "ENERGY_METER":
                                        energy_meter = add_energy_meter(plant, dataglen_client_owner,
                                                                        payload['modbus'][i], group)
                                        webdyn_modbus_energy_meters.append(energy_meter)
                                        # add meter details to ModbusDevice
                                        webdyn_modbus_energy_meter = add_webdyn_modbus_energy_meter_device(
                                            webdyn_gateway, energy_meter)
                                        webdyn_modbus_energy_meters.append(webdyn_modbus_energy_meter)

                                try:
                                    inv_manufacturer = payload['modbus'][0]['manufacturer']
                                    logger.debug(inv_manufacturer)
                                    if str(inv_manufacturer).upper().startswith("DELTA"):
                                        set_delta_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for delta inverters.")
                                    elif str(inv_manufacturer).upper().startswith("SUNGROW"):
                                        set_sungrow_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for sungrow inverters.")
                                    elif str(inv_manufacturer).upper().startswith("MODBUS_MICROLYTE"):
                                        set_microlyte_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for microlyte inverters.")
                                    elif str(inv_manufacturer).upper().startswith("MODBUS_INV_HUAWEI_33K_SUN2000"):
                                        set_huawei_inverter_error_codes(plant)
                                        logger.debug("multiplication factor set for microlyte inverters.")
                                    else:
                                        pass
                                except Exception as exception:
                                    logger.debug("Error in adding inverter status mappings : " + str(exception))
                                    pass

                            # add io devices
                            plant_meta = plant.metadata.plantmetasource
                            io_devices = []
                            if len(payload["io"]) > 0:
                                for i in range(len(payload["io"])):
                                    io_device = add_webdyn_io_devices(webdyn_gateway, plant_meta, payload["io"][i])
                                    io_devices.append(io_device)

                            # make a post call on FTP server to add devices
                            logger.debug(webdyn_client_slug)
                            logger.debug(webdyn_gateway.device_id)
                            logger.debug(device_type)
                            ftp_response = create_devices_on_ftp(client_slug=webdyn_client_slug,
                                                                 device_id=webdyn_gateway.device_id,
                                                                 device_type=device_type)
                            # logger.debug(ftp_response.content)
                            logger.debug(ftp_response.status_code)
                            return Response("Devices added for the plant.", status=status.HTTP_201_CREATED)
                        else:
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("Please correct the plant details", status=status.HTTP_400_BAD_REQUEST)
                except Exception as exception:
                    logger.debug(str(exception))
            except Exception as exception:
                logger.debug(str(exception))



# This API is to get the details of the devices from FTP
class FTPDetailsView(ProfileDataInAPIs, viewsets.ViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            try:
                owner, client = is_owner(self.request.user)
                if owner:
                    dataglen_client = client
                else:
                    dataglen_client = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient
            except Exception as exception:
                logger.debug(str(exception))
                return Response("You do not have access rights to create a new plant.", status=status.HTTP_403_FORBIDDEN)
            client_slug= dataglen_client.slug
            webdyn_device_id = self.request.query_params.get("deviceid", None)
            if webdyn_device_id == None:
                return Response("Please provide the device id.", status=status.HTTP_400_BAD_REQUEST)

            # make an API call to the FTP server and get the details.
            actual_url = FTP_SERVER_ADDRESS + FTP_DEVICES_ADDRESS
            params = {}
            params['clientslug'] = DGC_FTP_CLIENT_MAPPING[str(client_slug)]
            params['deviceid'] = webdyn_device_id
            response = requests.get(actual_url, params=params)
            return Response(json.loads(response.content), status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


