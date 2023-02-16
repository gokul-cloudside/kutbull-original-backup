from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from solarrms.models import VirtualGateway
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
from django.db import transaction, IntegrityError

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

FTP_SERVER_ADDRESS = 'http://ftp.dataglen.com/'
FTP_CM_SERVER_ADDRESS = 'http://cmftp.dataglen.com/'
FTP_DEVICES_ADDRESS = 'provisioning/devices/'
FTP_ADD_ADDRESS = 'provisioning/add/'
FTP_SMA_IM_ADDRESS = 'provisioning/smaim/'
FTP_SMA_WB_ADDRESS = 'provisioning/smawb/'
WEBDYN_FTP_API_KEY = '2fab9ff946d235aa55f43911a4150ed1596b4ff3'
token = 'Token ' + WEBDYN_FTP_API_KEY
auth_header = {'Authorization ': token, 'content-type': 'application/json'}


def clean_data(data):
    return str(data.encode('utf-8'))


def prepare_ftp_json(client_slug,
                     device_id,
                     solar_plant,
                     solar_group,
                     heartbeat_sk,
                     metadata_sk,
                     independent_inverters,
                     modbus_independent_inverters,
                     modbus_energy_meters,
                     io_devices):
    try:
        ftp_json = {}
        gateway_details = {}
        inverters_details = []
        modbus_details = []
        io_details = []

        # get all basic parameters
        gateway_details["client_slug"] = client_slug
        gateway_details["device_id"] = str(device_id)
        gateway_details["active"] = str(True).upper()
        gateway_details["installed_location"] = clean_data(solar_plant.location)
        gateway_details["heartbeat_source_key"] = heartbeat_sk
        gateway_details["metadata_source_key"] = metadata_sk
        ftp_json["gateway_details"] = gateway_details
        # get inverter level details

        # Inverter protocol
        for inverter in independent_inverters:
            inverter_dict = {}
            inverter_dict["identifier"] = inverter.serial_number
            inverter_dict["source_key"] = str(inverter.sourceKey)
            inverter_dict["active"] = str(True).upper()
            inverters_details.append(inverter_dict)
        ftp_json["inverters"] = inverters_details

        # Modbus inverters
        for device in modbus_independent_inverters:
            modbus_dict = {}
            modbus_dict["modbus_address"] = device.modbus_address
            modbus_dict["source_key"] = str(device.sourceKey)
            modbus_dict["active"] = str(True).upper()
            modbus_details.append(modbus_dict)

        # Modbus meters
        for meter in modbus_energy_meters:
            modbus_dict = {}
            modbus_dict["modbus_address"] = meter.modbus_address
            modbus_dict["source_key"] = str(meter.sourceKey)
            modbus_dict["active"] = str(True).upper()
            modbus_details.append(modbus_dict)
        ftp_json["modbus"] = modbus_details

        # IO Devices
        for io_device in io_devices:
            io_dict = {}
            io_dict["input_id"] = int(io_device['input_id'])
            io_dict["stream_name"] = clean_data(io_device['stream'])
            io_dict["source_key"] = str(solar_plant.metadata.sourceKey)
            io_dict["manufacturer"] = clean_data(io_device['manufacturer'])
            io_dict["output_range"] = clean_data(io_device['output_range'])
            io_dict["lower_bound"] = clean_data(io_device['lower_bound'])
            io_dict["upper_bound"] = clean_data(io_device['upper_bound'])
            io_dict["multiplicationFactor"] = str(1)
            io_dict["active"] = clean_data("True").upper()
            io_details.append(io_dict)
        ftp_json["io"] = io_details

        return ftp_json
    except Exception as exception:
        logger.debug("Error in making the request json for ftp post call : " + str(exception))
        return None


def commission_device(client_slug, device_id, json_data):
    try:
        actual_url = None
        if client_slug != "hcleanmax":
            actual_url = FTP_SERVER_ADDRESS + FTP_ADD_ADDRESS
        elif client_slug == "hcleanmax":
            actual_url = FTP_CM_SERVER_ADDRESS + FTP_ADD_ADDRESS
        logger.debug(actual_url)

        if actual_url:
            params = {}
            params['clientslug'] = client_slug
            params['deviceid'] = device_id
            # TODO check for the response code here and throw a proper error if needed
            response = requests.post(url=actual_url, json=json_data, params=params)
            logger.debug(response.content)
            if response.status_code != 201:
                return False
            else:
                return True
        else:
            return False
    except Exception as exception:
        logger.debug(str(exception))
        return False


class CreatePlantDevicesViewVersion2(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request):
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

        # 2. Start data parsing
        try:
            payload = self.request.data
            try:
                logger.debug(payload)
            except:
                pass

            plant_slug = self.request.query_params.get("plant_slug", None)
            try:
                plant = SolarPlant.objects.get(slug=plant_slug)
            except:
                return Response("INVALID_PLANT_SLUG", status=status.HTTP_400_BAD_REQUEST)

            device_type = self.request.query_params.get("device_type", None)

            if device_type is None or str(device_type).upper() not in ['WEBDYN', 'SMA_IM', 'SMA_WB']:
                return Response("Please specify a valid device type to add", status=status.HTTP_400_BAD_REQUEST)

            try:
                serializer = DeviceDataEntrySerializer(data=request.data)
                if serializer.is_valid():
                    try:
                        # a. get the client slug on ftp
                        if str(dataglen_client.slug) in DGC_FTP_CLIENT_MAPPING.keys():
                            webdyn_client_slug = DGC_FTP_CLIENT_MAPPING[str(dataglen_client.slug)]
                        else:
                            webdyn_client_slug = str(dataglen_client.slug)

                        ftp_response = False
                        with transaction.atomic():
                            # b. add a group (returns a list though)
                            groups = add_solar_groups(plant, dataglen_client_owner, dataglen_client,
                                                      payload['group_details'])

                            if len(groups) > 0:
                                # this group is the key now!
                                group = groups[0]
                                heartbeat_source_key = group.groupGatewaySources.all()[0].sourceKey
                                metadata_source_key = VirtualGateway.objects.filter(plant=plant,
                                                                                    solar_group=group)[0].sourceKey
                            else:
                                raise IntegrityError("There was an error while creating a new group. Please "
                                                     "contact the DataGlen team with the Device ID")

                            # c. add inverters, if available
                            independent_inverters = []
                            if len(payload["inverters"]) > 0:
                                for i in range(len(payload["inverters"])):
                                    independent_inverter = add_independent_inverters(plant,
                                                                                     dataglen_client_owner,
                                                                                     payload['inverters'][i],
                                                                                     group)
                                    if independent_inverter is None:
                                        raise IntegrityError("Error while adding an inverter device. Please "
                                                             "contact the DataGlen team with the Device ID")
                                    independent_inverters.append(independent_inverter)

                            # d. add modbus inverters, meters TODO : AJB and Weather station handling here
                            modbus_independent_inverters = []
                            modbus_energy_meters = []
                            if len(payload["modbus"]) > 0:
                                for i in range(len(payload["modbus"])):
                                    if (payload["modbus"][i]["device"]).upper() == "INVERTER":
                                        independent_inverter = add_independent_inverters(plant,
                                                                                         dataglen_client_owner,
                                                                                         payload['modbus'][i],
                                                                                         group)
                                        if independent_inverter is None:
                                            raise IntegrityError("Error while adding an inverter device. Please "
                                                                 "contact the DataGlen team with the Device ID")
                                        modbus_independent_inverters.append(independent_inverter)

                                    elif (payload["modbus"][i]["device"]).upper() == "ENERGY_METER":
                                        energy_meter = add_energy_meter(plant, dataglen_client_owner,
                                                                        payload['modbus'][i], group)
                                        if energy_meter is None:
                                            raise IntegrityError("Error while adding an energy meter device. Please "
                                                                 "contact the DataGlen team with the Device ID")

                                        modbus_energy_meters.append(energy_meter)

                            # e. add io devices
                            plant_meta = plant.metadata.plantmetasource
                            io_devices = []
                            if len(payload["io"]) > 0:
                                for i in range(len(payload["io"])):
                                    io_devices.append(payload["io"][i])

                            # f. set error code
                            # try:
                            #    inv_manufacturer = payload['modbus'][0]['manufacturer']
                            #    logger.debug(inv_manufacturer)
                            #    if str(inv_manufacturer).upper().startswith("DELTA"):
                            #        set_delta_inverter_error_codes(plant)
                            #        logger.debug("multiplication factor set for delta inverters.")
                            #    elif str(inv_manufacturer).upper().startswith("SUNGROW"):
                            #        set_sungrow_inverter_error_codes(plant)
                            #        logger.debug("multiplication factor set for sungrow inverters.")
                            #    elif str(inv_manufacturer).upper().startswith("MODBUS_MICROLYTE"):
                            #        set_microlyte_inverter_error_codes(plant)
                            #        logger.debug("multiplication factor set for microlyte inverters.")
                            #    elif str(inv_manufacturer).upper().startswith("MODBUS_INV_HUAWEI_33K_SUN2000"):
                            #        set_huawei_inverter_error_codes(plant)
                            #        logger.debug("multiplication factor set for microlyte inverters.")
                            #    else:
                            #        pass
                            # except Exception as exception:
                            #    logger.debug("Error in adding inverter status mappings : " + str(exception))
                            #    pass

                            # g. prepare a json for ftp
                            json_data = prepare_ftp_json(client_slug=webdyn_client_slug,
                                                         device_id=group.data_logger_device_id,
                                                         solar_plant=plant,
                                                         solar_group=group,
                                                         heartbeat_sk=heartbeat_source_key,
                                                         metadata_sk=metadata_source_key,
                                                         independent_inverters=independent_inverters,
                                                         modbus_independent_inverters=modbus_independent_inverters,
                                                         modbus_energy_meters=modbus_energy_meters,
                                                         io_devices=io_devices)
                            if json_data is None:
                                raise IntegrityError("Error while preparing content for FTP server. "
                                                     "Please contact the DataGlen team with the Device ID")

                            # g. create a device
                            ftp_response = commission_device(client_slug=webdyn_client_slug,
                                                             device_id=group.data_logger_device_id,
                                                             json_data=json_data)
                            if ftp_response is False:
                                raise IntegrityError("Error while creating a new device on the FTP server. "
                                                     "Please contact the DataGlen team with the Device ID")

                        # TODO check for the status code here
                        if ftp_response:
                            return Response("Devices added for the plant.", status=status.HTTP_201_CREATED)
                        else:
                            return Response("Devices not added.", status=status.HTTP_400_BAD_REQUEST)
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("Device not added : " + str(exception), status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("Please correct the plant details", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))


class FTPDetailsViewV2(ProfileDataInAPIs, viewsets.ViewSet):
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
            if str(client_slug) == "hcleanmax":
                actual_url = FTP_CM_SERVER_ADDRESS + FTP_DEVICES_ADDRESS
            else:
                actual_url = FTP_SERVER_ADDRESS + FTP_DEVICES_ADDRESS

            params = {}
            if str(client_slug) in DGC_FTP_CLIENT_MAPPING.keys():
                params['clientslug'] = DGC_FTP_CLIENT_MAPPING[str(client_slug)]
            else:
                params['clientslug'] = str(client_slug)

            params['deviceid'] = webdyn_device_id
            response = requests.get(actual_url, params=params)
            return Response(json.loads(response.content), status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR_" + str(exception), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


