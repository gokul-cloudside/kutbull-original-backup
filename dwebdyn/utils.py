from solarrms.models import SolarPlant, SolarGroup, SolarMetrics, IndependentInverter, PlantMetaSource, \
    EnergyMeter, WeatherStation, GatewaySource, PlantFeaturesEnable, VirtualGateway, MPPT, PanelsString
from django.db import IntegrityError
from django.contrib.auth.models import User
from organizations.models import OrganizationUser, OrganizationOwner
from helpdesk.models import Queue
from dwebdyn.models import WebdynGateway, InvertersDevice, ModbusDevice, IODevice, WebdynClient
from dwebdyn.inverter_delta_template import  set_mf_for_plant_meta,set_mf_for_delta_inverter
from dwebdyn.inverter_sungrow_template import set_mf_for_sungrow_inverter
from dwebdyn.inverter_microlyte_template import set_mf_for_microlyte_inverter
from dwebdyn.inverter_huawei_template import set_mf_for_huawei_inverter
from dwebdyn.inverter_ingeteam_template import set_mf_for_ingeteam_inverter
from dwebdyn.inverter_solis_template import set_mf_for_solis_inverter
from dwebdyn.inverter_waaree_template import set_mf_for_waaree_inverter

import sys, logging, dateutil

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

# Add a new plant
def add_plant_parameters(client, params):
    try:
        try:
            elevation = params['elevation']
        except:
            elevation = None
        try:
            evacuation_point = params['evacuation_point']
        except:
            evacuation_point = None
        try:
            intermediate_client = params['intermediate_client']
        except:
            intermediate_client = None
        plant = SolarPlant.objects.create(name=params['name'],
                                          groupClient=client,
                                          is_active=True,
                                          capacity=params['dc_capacity'],
                                          ac_capacity=params['ac_capacity'],
                                          location=params['location'],
                                          openweather=params['city'],
                                          isOperational=True,
                                          latitude=params['lat'],
                                          longitude=params['long'],
                                          elevation=elevation,
                                          evacuation_point=evacuation_point,
                                          intermediate_client=intermediate_client)
        plant.save()
        plant_slug = plant.slug
        plant.slug = plant_slug.replace("-","")
        plant.save()
        return plant
    except IntegrityError as exception:
        logger.debug(str(exception))
    except Exception as exception:
        logger.debug(str(exception))

# create organization user of plant
def create_plant_user(user,plant):
    try:
        organization_user = OrganizationUser.objects.get(user=user,
                                                         organization=plant)
        return organization_user
    except:
        try:
            organization_user = OrganizationUser.objects.create(user=user,
                                                                organization=plant)
            organization_user.save()
            logger.debug("Plant User Created")
            return organization_user
        except IntegrityError as exception:
            logger.debug(str(exception))
        except Exception as exception:
            logger.debug(str(exception))

# create organization owner of plant
def create_plant_owner(organization_user,plant):
    try:
        organization_owner = OrganizationOwner.objects.get(organization=plant,
                                                           organization_user=organization_user)
        return organization_owner
    except:
        try:
            organization_owner = OrganizationOwner.objects.create(organization=plant,
                                                                  organization_user=organization_user)
            organization_owner.save()
            logger.debug("Plant Owner Created")
            return organization_owner
        except IntegrityError as exception:
            logger.debug(str(exception))
        except Exception as exception:
            logger.debug(str(exception))

# add plant meta source
def create_plant_meta_source(user, plant, meta_details):
    try:
        try:
            model_number = meta_details['model_number']
        except:
            model_number = None
        try:
            panel_technology=meta_details['panel_technology']
        except:
            panel_technology = None
        plant_meta_source = PlantMetaSource.objects.create(plant=plant,
                                                           user=user,
                                                           name=str(plant.slug).upper().replace(" ","_")+"_Plant_Meta",
                                                           isActive=True,
                                                           isMonitored=True,
                                                           dataFormat='JSON',
                                                           sending_aggregated_power=False,
                                                           sending_aggregated_energy=False,
                                                           energy_meter_installed=False,
                                                           inverters_sending_daily_generation=False,
                                                           inverters_sending_total_generation=True,
                                                           PV_panel_area=meta_details['panel_area'],
                                                           PV_panel_efficiency=float(meta_details['panel_efficiency'])/100.0,
                                                           calculate_hourly_pr=False,
                                                           dataReportingInterval=900,
                                                           panel_capacity=meta_details['panel_capacity'],
                                                           model_number=model_number,
                                                           panel_technology=panel_technology,
                                                           panel_manufacturer=meta_details['panel_manufacturer'],
                                                           no_of_panels=meta_details['total_number_of_panels'],
                                                           operations_start_time="06:00:00",
                                                           operations_end_time="20:30:00")
        plant_meta_source.save()
        logger.debug("Plant meta source created.")
        set_mf_for_plant_meta(plant)
        logger.debug("multiplication factor set for plant meta.")
        return plant_meta_source
    except Exception as exception:
        logger.debug(str(exception))

# add solar groups
def add_solar_groups(plant, user, client, group_details):
    try:
        groups = []
        for i in range(len(group_details)):
            try:
                try:
                    azimuth=group_detail['azimuth']
                except:
                    azimuth=None
                try:
                    group_type=group_detail['type']
                except:
                    group_type = None
                group_detail = group_details[i]
                group_slug = str(plant.slug) + '_' + str(group_detail['name']).replace(" ","_").lower()
                group = SolarGroup.objects.create(slug=group_slug,
                                                  name=group_detail['name'].replace(" ","_"),
                                                  user=user,
                                                  displayName=group_detail['name'],
                                                  isActive=True,
                                                  plant=plant,
                                                  tilt_angle=group_detail['tilt_angle'],
                                                  group_type=group_type,
                                                  azimuth=azimuth,
                                                  no_of_panels=group_detail['panel_numbers'],
                                                  PV_panel_area=group_detail['panel_area'],
                                                  data_logger_device_id=group_detail['data_logger_device_id'])
                group.save()
                add_group_gateway_source(plant, group, user)
                add_group_virtual_gateway(plant, group, user)
                groups.append(group)
            except Exception as exception:
                logger.debug(str(exception))
                raise ValueError("Error creating a new group")
        return groups
    except Exception as exception:
        logger.debug(str(exception))
        raise ValueError("Error creating a new group")


multiplication_factors = {
    'ACTIVE_POWER_B': '0.001',
    'ACTIVE_POWER_R': '0.001',
    'ACTIVE_POWER_Y': '0.001',
    'ACTIVE_POWER': '0.001',
    'AC_FREQUENCY_B': '1',
    'AC_FREQUENCY_R': '1',
    'AC_FREQUENCY_Y': '1',
    'AC_VOLTAGE_B': '1',
    'AC_VOLTAGE_R': '1',
    'AC_VOLTAGE_Y': '1',
    'AMBIENT_TEMPERATURE': '1',
    'CURRENT_B': '1',
    'CURRENT_R': '1',
    'CURRENT_Y': '1',
    'DAILY_YIELD': '1',
    'TOTAL_YIELD': '1',
    'IRRADIATION': '0.001',
    'MODULE_TEMPERATURE': '1',
    'MPPT1_DC_CURRENT': '1',
    'MPPT1_DC_POWER': '0.001',
    'MPPT1_DC_VOLTAGE': '1',
    'MPPT2_DC_CURRENT': '1',
    'MPPT2_DC_POWER': '0.001',
    'MPPT2_DC_VOLTAGE': '1',
}

mappings = {'ACTIVE_POWER_B': ('AC Power3', 'W3'),
 'ACTIVE_POWER_R': ('AC Power1', 'W1'),
 'ACTIVE_POWER_Y': ('AC Power2', 'W2'),
 'ACTIVE_POWER': ('Total Power', 'W'),
 'AC_FREQUENCY_B': ('AC Frequency Phase3', 'F3'),
 'AC_FREQUENCY_R': ('AC Frequency Phase1', 'F1'),
 'AC_FREQUENCY_Y': ('AC Frequency Phase2', 'F2'),
 'AC_VOLTAGE_B': ('AC Voltage Phase3', 'V3'),
 'AC_VOLTAGE_R': ('AC Voltage Phase1', 'V1'),
 'AC_VOLTAGE_Y': ('AC Voltage Phase2', 'V2'),
 'AMBIENT_TEMPERATURE': ('Ambient Temperature', 'Ambient Temperature'),
 'CURRENT_B': ('AC Current Phase3', 'I3'),
 'CURRENT_R': ('AC Current Phase1', 'I1'),
 'CURRENT_Y': ('AC Current Phase2', 'I2'),
 'DAILY_YIELD': ('Daily Energy', 'Yield'),
 'TOTAL_YIELD': ('Total Energy', 'Yield'),
 'IRRADIATION': ('Irradiance', 'Irradiance'),
 'MODULE_TEMPERATURE': ('Module Temperature', 'Module Temperature'),
 'MPPT1_DC_CURRENT': ('DC Current1', 'DCI1'),
 'MPPT1_DC_POWER': ('DC Power1', 'DCW1'),
 'MPPT1_DC_VOLTAGE': ('DC Voltage1', 'DCV1'),
 'MPPT2_DC_CURRENT': ('DC Current2', 'DCI2'),
 'MPPT2_DC_POWER': ('DC Power2', 'DCW2'),
 'MPPT2_DC_VOLTAGE': ('DC Voltage2', 'DCV2')}


def add_independent_inverters_for_delremo(plant, user, inverter_detail):
    capacity = 5
    try:
        inverter_model = inverter_detail["model_number"]
        for i in range(10,101,10):
            if str(i) in inverter_model:
                capacity = i
                break
    except:
        pass

    logger.debug(capacity)
    logger.debug(inverter_detail)
    logger.debug(inverter_detail['name'])
    try:
        inverter = IndependentInverter.objects.create(
            name=inverter_detail['name'],
            user=user,
            dataFormat='JSON',
            plant=plant,
            displayName=inverter_detail['name'],
            serial_number=inverter_detail['name'],
            model=inverter_detail['model_number'],
            modbus_address=str(inverter_detail['rs485id']),
            isActive=True,
            isMonitored=True,
            manufacturer="DELTA - DELREMO",
            dataReportingInterval=900,
            timeoutInterval=2700,
            total_capacity=capacity,
            actual_capacity=capacity,
            orientation='SOUTH'
            )
        inverter.save()

        for field in inverter.fields.all():
            if field.name in multiplication_factors.keys():
                sf = field.solarfield
                sf.displayName = mappings[field.name][0]
                sf.save()
                field.multiplicationFactor = multiplication_factors[field.name]
                field.isActive = True
                field.save()
            else:
                field.isActive = False
                field.save()
        inverter_detail['source_key'] = inverter.sourceKey
        return inverter_detail

    except Exception as exception:
        logger.exception("While adding delremo inverter")
        logger.debug(str(exception))
        return None


def copy_mfs(fs, ts):
    for field in fs.fields.filter(isActive=True):
        try:
            tf = ts.fields.get(name = field.name)
            tf.multiplicationFactor = field.multiplicationFactor
            tf.isActive = True
            tf.save()
            sf = tf.solarfield
            sf.displayName = field.solarfield.displayName
            sf.save()
        except Exception as exc:
            print field, ts, exc


# add inverters
def add_independent_inverters(plant, user, inverter_detail, group=None):
    try:
        try:
            number_of_mppts=inverter_detail['number_of_mppts']
        except:
            number_of_mppts = 0
        try:
            strings_per_mppt = inverter_detail['strings_per_mppt']
        except:
            strings_per_mppt = []
        try:
            modules_per_string = inverter_detail['modules_per_string']
        except:
            modules_per_string = []
        inverter = IndependentInverter.objects.create(name="Inverter-" + str(plant.independent_inverter_units.all().count() + 1),
                                                      user=user,
                                                      dataFormat='JSON',
                                                      plant=plant,
                                                      displayName=inverter_detail['name'],
                                                      manufacturer=inverter_detail['manufacturer'],
                                                      model = inverter_detail['model_number'],
                                                      isActive=True,
                                                      isMonitored=True,
                                                      dataReportingInterval=900,
                                                      timeoutInterval = 2700,
                                                      total_capacity = inverter_detail['capacity'],
                                                      actual_capacity = inverter_detail['connected_dc_capacity'],
                                                      orientation = 'SOUTH',
                                                      number_of_mppts=number_of_mppts,
                                                      # strings_per_mppt=strings_per_mppt,
                                                      # modules_per_string=modules_per_string,
                                                      serial_number=str(inverter_detail['serial_number']),
                                                      modbus_address=str(inverter_detail['modbus_address']))
        inverter.save()
        if group:
            group.groupIndependentInverters.add(inverter)
            group.save()
        for i in range(int(number_of_mppts)):
            try:
                add_mppt(plant, user, inverter, strings_per_mppt[i]['number_of_strings'], modules_per_string[i],\
                         strings_per_mppt[i]['tilt_angle'], i)
            except Exception as exception:
                logger.debug(str(exception))
                continue
        # set multiplication factor for inverter
        if str(inverter.manufacturer).upper().startswith("DELTA") or "DELTA" in str(inverter.manufacturer).upper():
            set_mf_for_delta_inverter(plant, inverter)
            logger.debug("multiplication factor set for delta inverters.")
        elif str(inverter.manufacturer).upper().startswith("SUNGROW") or "SUNGROW" in str(inverter.manufacturer).upper():
            set_mf_for_sungrow_inverter(plant, inverter)
            logger.debug("multiplication factor set for sungrow inverters.")
        elif str(inverter.manufacturer).upper().startswith("MODBUS_MICROLYTE") or "MICROLYTE" in str(inverter.manufacturer).upper():
            set_mf_for_microlyte_inverter(plant, inverter)
            logger.debug("multiplication factor set for microlyte inverters.")
        elif str(inverter.manufacturer).upper().startswith("MODBUS_INV_HUAWEI_33K_SUN2000") or "HUAWEI" in str(inverter.manufacturer).upper():
            set_mf_for_huawei_inverter(plant, inverter)
            logger.debug("multiplication factor set for microlyte inverters.")
        elif str(inverter.manufacturer).upper().startswith("INGETEAM") or "INGETEAM" in str(inverter.manufacturer).upper():
            set_mf_for_ingeteam_inverter(plant, inverter)
            logger.debug("multiplication factor set for ingeteam inverters.")
        elif str(inverter.manufacturer).upper().startswith("SOLIS") or "SOLIS" in str(inverter.manufacturer).upper():
            set_mf_for_solis_inverter(plant, inverter)
            logger.debug("multiplication factor set for solis inverters.")
        elif str(inverter.manufacturer).upper().startswith("WAAREE") or "WARREE" in str(inverter.manufacturer).upper():
            set_mf_for_waaree_inverter(plant, inverter)
            logger.debug("multiplication factor set for waaree inverters.")
        else:
            from_invs = IndependentInverter.objects.filter(manufacturer=inverter.manufacturer)
            if len(from_invs) == 0:
                pass
            else:
                fs = from_invs[0]
                copy_mfs(fs, inverter)
            pass
        return inverter
    except Exception as exception:
        logger.debug(str(exception))
        return None

# add energy meters
def add_energy_meter(plant, user, meter_details, group):
    try:
        meter = EnergyMeter.objects.create(name="EnergyMeter-" + str(plant.energy_meters.all().count() + 1),
                                           user=user,
                                           dataFormat='JSON',
                                           plant=plant,
                                           displayName=str(plant.name).replace(" ","_")+"_Energy_Meter",
                                           manufacturer=meter_details['manufacturer'],
                                           model=meter_details['model_number'],
                                           isActive=True,
                                           isMonitored=True,
                                           dataReportingInterval=900,
                                           timeoutInterval = 2700,
                                           modbus_address=str(meter_details['modbus_address']))
        meter.save()
        group.groupEnergyMeters.add(meter)
        group.save()
        return meter
    except Exception as exception:
        logger.debug(str(exception))


# add Weather Station
def add_weather_station(plant, user, weather_station_details):
    try:
        group_slug = str(plant.slug) + '_' + str(weather_station_details['group_name']).replace(" ","_").lower()
        try:
            group = SolarGroup.objects.get(slug=group_slug)
        except Exception as exception:
            logger.debug(str(exception))
        weather_station = WeatherStation.objects.create(name=str(plant.name).replace(" ","_")+"_Weather_Station",
                                                         user=user,
                                                         dataFormat='JSON',
                                                         plant=plant,
                                                         displayName=str(plant.name).replace(" ","_")+"_Weather_Station",
                                                         manufacturer=weather_station_details['manufacturer'],
                                                         model=weather_station_details['model_number'],
                                                         isActive=True,
                                                         isMonitored=True,
                                                         dataReportingInterval=900,
                                                         timeoutInterval = 2700)
        weather_station.save()
        weather_station.solar_groups.add(group)
        return weather_station
    except Exception as exception:
        logger.debug(str(exception))

def add_plant_gateway_source(plant, user):
    try:
        gateway_source = GatewaySource.objects.create(plant=plant,
                                                      user=user,
                                                      name=str(plant.name).replace(" ","_")+"_Gateway",
                                                      isActive=True,
                                                      isMonitored=True,
                                                      dataFormat='JSON',
                                                      isVirtual=True,
                                                      timeoutInterval = 2700
                                                      )
        gateway_source.save()
        logger.debug("gateway source created")
        return gateway_source
    except Exception as exception:
        logger.debug(str(exception))

def add_solar_metrics(plant,user):
    try:
        solar_metrics = []
        solar_metric = SolarMetrics.objects.create(name=str(plant.name).replace(" ","_")+"_SOLAR_METRICS",
                                                   user=user,
                                                   dataFormat='JSON',
                                                   plant=plant,
                                                   displayName=str(plant.name).replace(" ","_")+"_SOLAR_METRICS",
                                                   isActive=True,
                                                   isMonitored=True,
                                                   dataReportingInterval=900,
                                                   timeoutInterval = 2700)
        solar_metric.save()
        solar_metrics.append(solar_metric)

        solar_groups=plant.solar_groups.all()
        for i in range(len(solar_groups)):
            group_solar_metric = SolarMetrics.objects.create(name=str(solar_groups[i].name).replace(" ","_")+"_SOLAR_METRICS",
                                                             user=user,
                                                             dataFormat='JSON',
                                                             plant=plant,
                                                             displayName=str(solar_groups[i].name).replace(" ","_")+"_SOLAR_METRICS",
                                                             isActive=True,
                                                             isMonitored=True,
                                                             dataReportingInterval=900,
                                                             timeoutInterval = 2700)
            group_solar_metric.save()
            solar_metrics.append(group_solar_metric)
        return solar_metrics
    except Exception as exception:
        logger.debug(str(exception))

def add_plant_features_enabled(plant):
    try:
        features_enabled = PlantFeaturesEnable.objects.create(plant=plant,
                                                              solar_metrics=True,
                                                              economic_benefits=False,
                                                              analytics=False,
                                                              alerts=False
                                                              )
        features_enabled.save()
        logger.debug("Features enabled instance created")
        return features_enabled
    except Exception as exception:
        logger.debug(str(exception))

def add_queue(plant):
    try:
        queue = Queue.objects.create(plant=plant,
                                     title=str(plant.slug),
                                     slug=str(plant.slug)
                                     )
        queue.save()
        logger.debug("Queue created")
        return queue
    except Exception as exception:
        logger.debug(str(exception))

def add_group_gateway_source(plant, group, user):
    try:
        group_gateway_source = GatewaySource.objects.create(plant=plant,
                                                            user=user,
                                                            name=str(group.slug).upper().replace(" ","_")+"_GATEWAY_SOURCE",
                                                            isActive=True,
                                                            isMonitored=True,
                                                            dataFormat='JSON',
                                                            isVirtual=True,
                                                            timeoutInterval = 2700)
        group_gateway_source.save()
        group.groupGatewaySources.add(group_gateway_source)
        return group_gateway_source
    except Exception as exception:
        logger.debug(str(exception))

def add_group_virtual_gateway(plant, group, user):
    try:
        group_virtual_gateway = VirtualGateway.objects.create(plant=plant,
                                                              solar_group=group,
                                                              user=user,
                                                              name=str(plant.slug).upper().replace(" ","_")+ "_" +str(group.name).replace(" ","_")+ "_WEBDYN_GATEWAY",
                                                              isActive=True,
                                                              isMonitored=True,
                                                              dataFormat='JSON',
                                                              manufacturer='WEBDYN',
                                                              displayName=str(plant.slug).upper().replace(" ","_")+ "_" +str(group.name).replace(" ","_")+ "_WEBDYN_GATEWAY",
                                                              timeoutInterval = 2700
                                                              )
        group_virtual_gateway.save()
        return group_virtual_gateway
    except Exception as exception:
        logger.debug(str(exception))

def add_plant_virtual_gateway(plant, user):
    try:
       group_virtual_gateway = VirtualGateway.objects.create(plant=plant,
                                                             user=user,
                                                             name=str(plant.slug).upper().replace(" ","_")+ "_WEBDYN_GATEWAY",
                                                             isActive=True,
                                                             isMonitored=True,
                                                             dataFormat='JSON',
                                                             manufacturer='WEBDYN',
                                                             displayName=str(plant.slug).upper().replace(" ","_")+"_WEBDYN_GATEWAY",
                                                             timeoutInterval = 2700
                                                             )
       group_virtual_gateway.save()
       logger.debug("virtual gateway source created")
       return group_virtual_gateway
    except Exception as exception:
        logger.debug(str(exception))

def add_mppt(plant, user, inverter, strings_per_mppt, modules_per_string, tilt_angle, count):
    try:
        mppt = MPPT.objects.create(plant=plant,
                                   user=user,
                                   independent_inverter=inverter,
                                   name=str(inverter.name).replace(" ","_")+"_MPPT"+str(count+1),
                                   isActive=True,
                                   isMonitored=True,
                                   dataFormat='JSON',
                                   strings_per_mppt=strings_per_mppt,
                                   modules_per_string=modules_per_string[0]['number_of_modules'])
        mppt.save()
        no_of_strings = strings_per_mppt
        for j in range(int(no_of_strings)):
            number_of_panels=modules_per_string[j]['number_of_modules']
            tilt_angle=tilt_angle
            panel_string = PanelsString.objects.create(mppt=mppt, number_of_panels=number_of_panels,
                                                       tilt_angle=tilt_angle)
            panel_string.save()
    except Exception as exception:
        logger.debug("Error in creating mppt objects : " + str(exception))

def add_webdyn_gateway(plant, group, webdyn_client):
    try:
        group_gateway = group.groupGatewaySources.all()
        if len(group_gateway)>0:
            heartbeat_source_key = group_gateway[0].sourceKey
        else:
           heartbeat_source_key = None
        try:
            virtual_gateway = VirtualGateway.objects.filter(plant=plant, solar_group=group)
            metadata_source_key = str(virtual_gateway[0].sourceKey)
        except:
            metadata_source_key = None
        webdyn_gateway = WebdynGateway.objects.create(client=webdyn_client,
                                                      device_id=group.data_logger_device_id,
                                                      active=True,
                                                      installed_location=str(plant.location),
                                                      heartbeat_source_key=heartbeat_source_key,
                                                      metadata_source_key=metadata_source_key)
        webdyn_gateway.save()
        return webdyn_gateway
    except Exception as exception:
        logger.debug("Error in saving webdyn gateway : " + str(exception))

def add_webdyn_inverters_device(gateway_device, inverter, fields_template = None):
    if fields_template is None:
        fields_template = str(inverter.manufacturer)

    try:
        inverter_device = InvertersDevice.objects.create(gateway_device=gateway_device,
                                                         identifier=str(inverter.serial_number),
                                                         fields_template=str(fields_template),
                                                         source_key=str(inverter.sourceKey),
                                                         active=True)
        inverter_device.save()
        return inverter_device
    except Exception as exception:
        logger.debug("Error in saving inverters devices : " + str(exception))

def add_webdyn_modbus_inverter_device(gateway_device, inverter):
    try:
        inverter_device = ModbusDevice.objects.create(gateway_device=gateway_device,
                                                      modbus_address=str(inverter.modbus_address),
                                                      fields_template=str(inverter.manufacturer),
                                                      source_key=str(inverter.sourceKey),
                                                      active=True)
        inverter_device.save()
        return inverter_device
    except Exception as exception:
        logger.debug("Error in saving inverters devices : " + str(exception))

def add_webdyn_modbus_energy_meter_device(gateway_device, energy_meter):
    try:
        energy_meter_device = ModbusDevice.objects.create(gateway_device=gateway_device,
                                                             modbus_address=str(energy_meter.modbus_address),
                                                             fields_template=str(energy_meter.manufacturer),
                                                             source_key=str(energy_meter.sourceKey),
                                                             active=True)
        energy_meter_device.save()
        return energy_meter_device
    except Exception as exception:
        logger.debug("Error in saving inverters devices : " + str(exception))

def add_webdyn_io_devices(gateway_device, meta_source, io_details):
    try:
        io_device = IODevice.objects.create(gateway_device=gateway_device,
                                            input_id=io_details['input_id'],
                                            stream_name=io_details['stream'],
                                            source_key=meta_source.sourceKey,
                                            manufacturer=io_details['manufacturer'],
                                            output_range=io_details['output_range'],
                                            lower_bound=io_details['lower_bound'],
                                            upper_bound=io_details['upper_bound'],
                                            active=True)
        io_device.save()
        return io_device
    except Exception as exception:
        logger.debug("Error in daving IO details : " + str(exception))

def get_request_json_for_ftp_post_call(client_slug, device_id):
    try:
        webdyn_client = WebdynClient.objects.get(slug=client_slug)
        webdyn_devices = WebdynGateway.objects.filter(client=webdyn_client, device_id=device_id)
        if len(webdyn_devices)>0:
            webdyn_device = webdyn_devices[0]
        ftp_json = {}
        gateway_details = {}
        inverters_details = []
        modbus_details = []
        io_details = []
        gateway_details["client_slug"]=client_slug
        gateway_details["device_id"]=str(webdyn_device.device_id)
        gateway_details["active"]=str(True).upper()
        gateway_details["installed_location"]=str(webdyn_device.installed_location.encode('utf-8'))
        gateway_details["heartbeat_source_key"]=str(webdyn_device.heartbeat_source_key)
        gateway_details["metadata_source_key"]=str(webdyn_device.metadata_source_key)
        ftp_json["gateway_details"] = gateway_details
        inverter_devices = webdyn_device.inverter_devices.all()
        for inverter in inverter_devices:
            inverter_dict = {}
            inverter_dict["identifier"] = str(inverter.identifier)
            inverter_dict["fields_template"] = str(inverter.fields_template)
            inverter_dict["source_key"] = str(inverter.source_key)
            inverter_dict["active"] = str(inverter.active).upper()
            inverters_details.append(inverter_dict)
        ftp_json["inverters"] = inverters_details
        modbus_devices = webdyn_device.modbus_devices.all()
        for device in modbus_devices:
            modbus_dict = {}
            modbus_dict["modbus_address"] = str(device.modbus_address)
            modbus_dict["fields_template"] = str(device.fields_template)
            modbus_dict["source_key"] = str(device.source_key)
            modbus_dict["active"] = str(device.active).upper()
            modbus_details.append(modbus_dict)
        ftp_json["modbus"] = modbus_details
        io_devices = webdyn_device.io_devices.all()
        for io_device in io_devices:
            io_dict = {}
            io_dict["input_id"] = int(io_device.input_id)
            io_dict["stream_name"] = str(io_device.stream_name)
            io_dict["source_key"] = str(io_device.source_key)
            io_dict["manufacturer"] = str(io_device.manufacturer.encode('utf-8'))
            io_dict["output_range"] = str(io_device.output_range)
            io_dict["lower_bound"] = str(io_device.lower_bound)
            io_dict["upper_bound"] = str(io_device.upper_bound)
            io_dict["multiplicationFactor"] = io_device.multiplicationFactor
            io_dict["active"] = str(io_device.active).upper()
            io_details.append(io_dict)
        ftp_json["io"] = io_details
        return ftp_json
    except Exception as exception:
        logger.debug("Error in making the request json for ftp post call : "+ str(exception))
