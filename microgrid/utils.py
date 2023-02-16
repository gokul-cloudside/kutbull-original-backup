from microgrid.models import *
from django.db import transaction
import sys


def setup_new_plant(plant, load_voltage=12):
    # create a charge controller
    try:
        user = plant.organization_users.all()[0].user
        with transaction.atomic():
            primary_cc = ChargeController.objects.create(plant=plant, user=user, name=plant.slug + " Primary_CC",
                                                         dataReportingInterval=300, dataFormat="JSON", isActive=True,
                                                         isMonitored=True, timeoutInterval=2700, is_master=True,
                                                         dataTimezone="Asia/Kolkata")
            print "Primary CC key/template name: %s/%s with fields:" % (primary_cc.sourceKey, primary_cc.templateName)
            for field in primary_cc.fields.all():
                print "\t", field.name

            secondary_cc = ChargeController.objects.create(plant=plant, user=user, name=plant.slug + " Secondary_CC",
                                                           dataReportingInterval=300, dataFormat="JSON", isActive=True,
                                                           isMonitored=True, timeoutInterval=2700, is_master=False)

            print "Secondary CC key/template name: %s/%s with fields:" % (secondary_cc.sourceKey, secondary_cc.templateName)
            for field in secondary_cc.fields.filter():
                print "\t", field.name

            panel_set_two_panels = PanelSet.objects.create(plant=plant, user=user, name=plant.slug + " Two Panels Set",
                                                           charge_controller= primary_cc,
                                                           dataReportingInterval=300, dataFormat="JSON", isActive=True,
                                                           isMonitored=True, timeoutInterval=2700,
                                                           manufacturer="Solar-Apps", model="Solar-Apps",
                                                           orientation="NORTH", total_capacity=330, actual_capacity=330,
                                                           no_of_panels=2)
            print "Panel set with two panels source key/template name: %s/%s connected to primary CC" % (panel_set_two_panels.sourceKey, panel_set_two_panels.templateName)
            for field in panel_set_two_panels.fields.filter(isActive=True):
                print "\t", field.name

            load = ConnectedLoad.objects.create(plant=plant, user=user, name=plant.slug + " Connected Load",
                                                charge_controller=primary_cc,
                                                dataReportingInterval=300, dataFormat="JSON", isActive=True,
                                                isMonitored=True, timeoutInterval=2700, manufacturer="Solar-Apps",
                                                model="Solar-Apps", orientation="NORTH", total_capacity=330,
                                                actual_capacity=330, load_voltage=load_voltage)
            print "Load with source key/template name: %s/%s connected to primary CC" % (load.sourceKey, load.templateName)
            for field in load.fields.filter(isActive=True):
                print "\t", field.name

            panel_set_one_panel = PanelSet.objects.create(plant=plant, user=user, name=plant.slug + " Single Panel",
                                                          charge_controller=secondary_cc,
                                                          dataReportingInterval=300, dataFormat="JSON", isActive=True,
                                                          isMonitored=True, timeoutInterval=2700,
                                                          manufacturer="Solar-Apps", model="Solar-Apps",
                                                          orientation="NORTH", total_capacity=330, actual_capacity=330,
                                                          no_of_panels=1)
            print "Panel set with one panel source key/template name: %s/%s connected to secondary CC" % (panel_set_one_panel.sourceKey, panel_set_one_panel.templateName)
            for field in panel_set_one_panel.fields.filter(isActive=True):
                print "\t", field.name

            battery = Battery.objects.create(plant=plant, user=user, name=plant.slug + " Battery", dataReportingInterval=300,
                                             dataFormat="JSON", isActive=True, isMonitored=True, timeoutInterval=2700,
                                             manufacturer="Solar-Apps", model="Solar-Apps", orientation="NORTH",
                                             total_capacity=330, actual_capacity=330, controllable=False)
            battery.charge_controller.add(primary_cc)
            battery.charge_controller.add(secondary_cc)
            print "Battery source key/template name: %s/%s connected to both primary and secondary CC" % (panel_set_one_panel.sourceKey, panel_set_one_panel.templateName)
            for field in panel_set_one_panel.fields.filter(isActive=True):
                print "\t", field.name
    except:
        import traceback
        print "%s" % traceback.format_exc()
        print "%s" % sys.exc_info()[0]

import sys
import os
import django
import configparser
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from django.contrib.auth.models import User
from dashboards.models import DataglenClient
from organizations.models import OrganizationOwner
from organizations.models import OrganizationUser
from solarrms.models import SolarPlant, IndependentInverter, GatewaySource, PlantMetaSource, AJB, EnergyMeter, Transformer, \
    WeatherStation, SolarMetrics, SolarGroup, PlantFeaturesEnable
from django.core.mail import send_mail
from client_creation_script_v2 import create_dataglen_client
from rest_framework.authtoken.models import Token
import ast
from helpdesk.models import Queue
from django.db import transaction

__version__ = '2.0'
CONFIG_FILE = "plant_creation.cfg"


class PlantCreation(object):
    inverter_key_list = []

    def __init__(self, plant_name, plant_slug):
        """
        read config parameters
        """

        self.config_dict = self.get_config_parameters(plant_name, plant_slug)
        if not self.config_dict:
            sys.exit()


    def get_config_parameters(self, plant_name, plant_slug):
        """
        get config parameter from .cfg file
        :return:
        """

        config_dict = {}
        # config = configparser.ConfigParser()
        # config.read(CONFIG_FILE)
        config_dict['USER_NAME'] = "sharat@solar-apps.com" #config['USER']['NAME']
        config_dict['CLIENT_SLUG'] = "solar-apps" #config['CLIENT']['SLUG']
        config_dict['PLANT_NAME'] = plant_name #config['PLANT']['NAME']
        config_dict['PLANT_SLUG'] = plant_slug #config['PLANT']['SLUG']
        config_dict['PLANT_ACTIVE'] = True #config['PLANT']['IS_ACTIVE']
        config_dict['PLANT_CAPACITY'] = 1 #config['PLANT']['CAPACITY']
        config_dict['PLANT_LOCATION'] = "Philippines" #config['PLANT']['LOCATION']
        config_dict['PLANT_OPENWEATHER'] = "philippines" #config['PLANT']['OPENWEATHER']
        config_dict['PLANT_OPERATIONAL'] = True #config['PLANT']['ISOPERATIONAL']
        config_dict['PLANT_LATITUDE'] = 12.8797 #config['PLANT']['LATITUDE']
        config_dict['PLANT_LONGITUDE'] = 121.7740 #config['PLANT']['LONGITUDE']
        config_dict['PLANT_EVACUATION_POINT'] = "" #config['PLANT']['EVACUATION_POINT']
        config_dict['PLANT_WEBDYN_DEVICE_ID'] = "" #config['PLANT']['WEBDYN_DEVICE_ID']
        # config_dict['INVERTER_COUNT'] = config['INVERTER']['COUNT']
        # config_dict['DATA_FORMAT'] = config['INVERTER']['DATA_FORMAT']
        # config_dict['MANUFACTURER'] = config['INVERTER']['MANUFACTURER']
        # config_dict['INVERTER_MODEL'] = config['INVERTER']['MODEL']
        # config_dict['INVERTER_TIME_OUT_INTERVAL'] = config['INVERTER']['TIME_OUT_INTERVAL']
        # config_dict['DATA_REPORTING_INTERVAL'] = config['INVERTER']['REPORTING_INTERVAL']
        # config_dict['SOURCE_NAME'] = config['GATEWAY']['SOURCE_NAME']
        # config_dict['SOURCE_ACTIVE'] = config['GATEWAY']['IS_ACTIVE']
        # config_dict['SOURCE_MONITORED'] = config['GATEWAY']['IS_MONITORED']
        # config_dict['SOURCE_DATAFORMAT'] = config['GATEWAY']['DATAFORMAT']
        # config_dict['SERVER_URL'] = config['API']['SERVER_URL']
        # config_dict['SOURCE_URL'] = config['API']['SOURCE_URL']
        # config_dict['STREAM_HEARTBEAT'] = config['GATEWAY']['HEARTBEAT']
        # config_dict['STREAM_TIESTAMP'] = config['GATEWAY']['TIMESTAMP']
        config_dict['GATEWAYSOURCE_NAME'] = plant_name + "_GATEWAYSOURCE" #config['GATEWAYSOURCE']['NAME']
        config_dict['GATEWAYSOURCE_ISACTIVE'] = True #config['GATEWAYSOURCE']['ISACTIVE']
        config_dict['GATEWAYSOURCE_ISMONITORED'] = True #config['GATEWAYSOURCE']['ISMONITORED']
        config_dict['GATEWAYSOURCE_DATAFORMAT'] = "JSON" #config['GATEWAYSOURCE']['DATAFORMAT']
        config_dict['GATEWAYSOURCE_ISVIRTUAL'] = True #config['GATEWAYSOURCE']['ISVIRTUAL']
        config_dict['PLANTMETA_NAME'] = plant_name + "_PLANTMETA" #config['PLANT_META']['NAME']
        config_dict['PLANTMETA_ISACTIVE'] = True #config['PLANT_META']['ISACTIVE']
        config_dict['PLANTMETA_ISMONITORED'] = True #config['PLANT_META']['ISMONITORED']
        config_dict['PLANTMETA_DATAFORMAT'] = "JSON" #config['PLANT_META']['DATAFORMAT']
        config_dict['PLANTMETA_SENDING_AGGREGATED_POWER'] = False #config['PLANT_META']['SENDING_AGGREGATED_POWER']
        config_dict['PLANTMETA_SENDING_AGGREGATED_ENERGY'] = False #config['PLANT_META']['SENDING_AGGREGATED_ENERGY']
        config_dict['PLANTMETA_ENERGY_METER_INSTALLED'] = False #config['PLANT_META']['ENERGY_METER_INSTALLED']
        config_dict['PLANTMETA_PV_PANEL_AREA'] = 222 #config['PLANT_META']['PV_PANEL_AREA']
        config_dict['PLANT_META_PV_PANEL_EFFICIENCY'] = 0.16 #config['PLANT_META']['PV_PANEL_EFFICIENCY']
        config_dict['PLANT_META_OPERATIONS_START_TIME'] = "06:00" #config['PLANT_META']['OPERATIONS_START_TIME']
        config_dict['PLANT_META_OPERATIONS_END_TIME'] = "20:00" #config['PLANT_META']['OPERATIONS_END_TIME']
        config_dict['PLANT_META_CALCULATE_HOURLY_PR'] = False #config['PLANT_META']['CALCULATE_HOURLY_PR']
        config_dict['PLANT_META_REPORTING_INTERVAL'] = 300 #config['PLANT_META']['REPORTING_INTERVAL']
        # config_dict['INVERTER_CAPACITY'] = config['INVERTER']['CAPACITY']
        # config_dict['INVERTER_ORIENTATION'] = config['INVERTER']['ORIENTATION']
        # config_dict['AJB_ADD'] = config['AJB']['ADD']
        # config_dict['AJB_COUNT'] = config['AJB']['COUNT']
        # config_dict['AJB_MANUFACTURER'] = config['AJB']['MANUFACTURER']
        # config_dict['AJB_DATA_REPORTING_INTERVAL'] = config['AJB']['REPORTING_INTERVAL']
        #
        # config_dict['ENERGY_METER_ADD'] = config['ENERGY_METER']['ADD']
        # config_dict['ENERGY_METER_COUNT'] = config['ENERGY_METER']['COUNT']
        # config_dict['ENERGY_METER_DATA_FORMAT'] = config['ENERGY_METER']['DATA_FORMAT']
        # config_dict['ENERGY_METER_MANUFACTURER'] = config['ENERGY_METER']['MANUFACTURER']
        # config_dict['ENERGY_METER_DATA_REPORTING_INTERVAL'] = config['ENERGY_METER']['REPORTING_INTERVAL']
        # config_dict['ENERGY_METER_TIME_OUT_INTERVAL'] = config['ENERGY_METER']['TIME_OUT_INTERVAL']
        #
        # config_dict['TRANSFORMER_ADD'] = config['TRANSFORMER']['ADD']
        # config_dict['TRANSFORMER_COUNT'] = config['TRANSFORMER']['COUNT']
        # config_dict['TRANSFORMER_DATA_FORMAT'] = config['TRANSFORMER']['DATA_FORMAT']
        # config_dict['TRANSFORMER_MANUFACTURER'] = config['TRANSFORMER']['MANUFACTURER']
        # config_dict['TRANSFORMER_DATA_REPORTING_INTERVAL'] = config['TRANSFORMER']['REPORTING_INTERVAL']
        # config_dict['TRANSFORMER_TIME_OUT_INTERVAL'] = config['TRANSFORMER']['TIME_OUT_INTERVAL']
        #
        # config_dict['WEATHER_STATION_ADD'] = config['WEATHER_STATION']['ADD']
        # config_dict['WEATHER_STATION_COUNT'] = config['WEATHER_STATION']['COUNT']
        # config_dict['WEATHER_STATION_DATA_FORMAT'] = config['WEATHER_STATION']['DATA_FORMAT']
        # config_dict['WEATHER_STATION_MANUFACTURER'] = config['WEATHER_STATION']['MANUFACTURER']
        # config_dict['WEATHER_STATION_MODEL'] = config['WEATHER_STATION']['MODEL']
        # config_dict['WEATHER_STATION_DATA_REPORTING_INTERVAL'] = config['WEATHER_STATION']['REPORTING_INTERVAL']
        # config_dict['WEATHER_STATION_TIME_OUT_INTERVAL'] = config['WEATHER_STATION']['TIME_OUT_INTERVAL']
        #
        # config_dict['SOLAR_METRICS_COUNT'] = config['SOLAR_METRICS']['COUNT']
        # config_dict['SOLAR_METRICS_DATA_FORMAT'] = config['SOLAR_METRICS']['DATA_FORMAT']
        # config_dict['SOLAR_METRICS_DATA_REPORTING_INTERVAL'] = config['SOLAR_METRICS']['REPORTING_INTERVAL']
        # config_dict['SOLAR_METRICS_TIME_OUT_INTERVAL'] = config['SOLAR_METRICS']['TIME_OUT_INTERVAL']
        #
        # config_dict['GROUP_ADD'] = config['GROUP']['ADD']
        # config_dict['GROUP_NAME'] = config['GROUP']['NAME']
        # config_dict['GROUP_TYPE'] = config['GROUP']['TYPE']
        # config_dict['GROUP_ROOF_TYPE'] = config['GROUP']['ROOF_TYPE']
        # config_dict['GROUP_TILT_ANGLE'] = config['GROUP']['TILT_ANGLE']
        # config_dict['GROUP_LATITUDE'] = config['GROUP']['LATITUDE']
        # config_dict['GROUP_LONGITUDE'] = config['GROUP']['LONGITUDE']
        # config_dict['GROUP_AZIMUTH'] = config['GROUP']['AZIMUTH']
        # config_dict['GROUP_PANEL_MANUFACTURER'] = config['GROUP']['PANEL_MANUFACTURER']
        # config_dict['GROUP_PANEL_CAPACITY'] = config['GROUP']['PANEL_CAPACITY']
        # config_dict['GROUP_PANEL_NUMBERS'] = config['GROUP']['PANEL_NUMBERS']
        # config_dict['GROUP_PV_PANEL_AREA'] = config['GROUP']['PV_PANEL_AREA']
        # config_dict['GROUP_PV_PANEL_EFFICIENCY'] = config['GROUP']['PV_PANEL_EFFICIENCY']
        return config_dict

    def get_user(self):
        """

        :return:
        """

        user = User.objects.get(username=self.config_dict['USER_NAME'])
        return user

    def get_client(self):
        """

        :return:
        """

        client = DataglenClient.objects.get(slug=self.config_dict["CLIENT_SLUG"])
        return client

    def add_plant(self, client):
        """

        :param client:
        :return:
        """

        evacuation_point = self.config_dict['PLANT_EVACUATION_POINT'] if self.config_dict[
            'PLANT_EVACUATION_POINT'] else None
        webdyn_device_id = self.config_dict['PLANT_WEBDYN_DEVICE_ID'] if self.config_dict[
            'PLANT_WEBDYN_DEVICE_ID'] else None
        plant = SolarPlant.objects.create(name=self.config_dict['PLANT_NAME'],
                                          slug=self.config_dict['PLANT_SLUG'],
                                          groupClient=client,
                                          is_active=self.config_dict['PLANT_ACTIVE'],
                                          capacity=self.config_dict['PLANT_CAPACITY'],
                                          location=self.config_dict['PLANT_LOCATION'],
                                          openweather=self.config_dict['PLANT_OPENWEATHER'],
                                          isOperational=self.config_dict['PLANT_OPERATIONAL'],
                                          latitude=self.config_dict['PLANT_LATITUDE'],
                                          longitude=self.config_dict['PLANT_LONGITUDE'],
                                          evacuation_point=evacuation_point,
                                          webdyn_device_id=webdyn_device_id)
        new_slug = str(plant.slug).replace("-", "")
        plant.slug = new_slug
        plant.save()
        print "plant created"
        return plant

    def create_plant_user(self,user,plant):
        """

        :param user:
        :param plant:
        :return:
        """

        organization_user, created = OrganizationUser.objects.get_or_create(user=user, organization=plant)
        if created:
            print "Plant User Created"
        print "Plant User is %s" % organization_user
        return organization_user

    def create_plant_owner(self,plant,organization_user):
        """

        :param plant:
        :param organization_user:
        :return:
        """

        organization_owner, created = OrganizationOwner.objects.get_or_create(organization=plant,
                                                                     organization_user=organization_user)
        if created:
            print "Plant Owner Created"
        print "Plant Owner is %s" % organization_owner
        return organization_owner


    def add_inverters(self,plant,user):
        """
        use below commented method for plants where inverter names are
        symmetrical (like Inverter_1, Inverter_2)
        :param plant:
        :param user:
        :return:
        """

        source_keys = []
        for count in range(int(self.config_dict['INVERTER_COUNT'])):
            name = str(plant.slug).upper() + '_Inverter_' + str(count+1)
            inverter = IndependentInverter.objects.create(name=name, user=user,
                                                          dataFormat=self.config_dict['DATA_FORMAT'], plant=plant,
                                                          displayName=name,
                                                          manufacturer=self.config_dict['MANUFACTURER'],
                                                          model=self.config_dict['INVERTER_MODEL'], isActive=True,
                                                          isMonitored=True, dataReportingInterval=self.config_dict[
                    'DATA_REPORTING_INTERVAL'], timeoutInterval=self.config_dict['INVERTER_TIME_OUT_INTERVAL'],
                                                          total_capacity=self.config_dict['INVERTER_CAPACITY'],
                                                          actual_capacity=self.config_dict['INVERTER_CAPACITY'],
                                                          orientation=self.config_dict['INVERTER_ORIENTATION'])
            print "inverter %s created" % (count+1)
            source_keys.append(inverter.name + " : " + inverter.sourceKey)
        inverter_key_list = source_keys
        print "Details of inverters"
        for i in range(len(source_keys)):
            print "%s" % source_keys[i]
        return inverter_key_list

    def add_ajb(self, plant, user):
        """

        :param plant:
        :param user:
        :return:
        """
        ajb_source_keys = []
        print "AJB_ADD %s" % self.config_dict['AJB_ADD']
        if self.config_dict['AJB_ADD'] == 'True':
            print "inside ajb create"
            inverters = IndependentInverter.objects.filter(plant=plant)
            for inverter in inverters:
                inverter_name = str(inverter.name)
                inverter_name_split = inverter_name.split('_',2)
                for count in range(int(self.config_dict['AJB_COUNT'])):
                    ajb_name = str(plant.slug).upper() + '_SMB_'+ str(inverter_name_split[2])+ '.' +str(count+1)
                    ajb = AJB.objects.create(user=user,
                                             name= ajb_name,
                                             plant=plant,
                                             independent_inverter = inverter,
                                             displayName=ajb_name,
                                             manufacturer=self.config_dict['AJB_MANUFACTURER'],
                                             isActive=True,
                                             isMonitored=True,
                                             dataReportingInterval=self.config_dict['AJB_DATA_REPORTING_INTERVAL'])
                    print "%s created" % ajb_name
                    ajb_source_keys.append(ajb.name + " : " + ajb.sourceKey)
            return ajb_source_keys
        else:
            return ajb_source_keys

    def get_auth_token(self, user):
        """

        :param user:
        :return:
        """
        token = Token.objects.get(user=user)
        print "get auth token %s" % token
        return token

    def add_plant_gateway_source(self,plant,user):
        """

        :param plant:
        :param user:
        :return:
        """
        gateway_source = GatewaySource.objects.create(plant=plant, user=user,
                                                      name=self.config_dict['GATEWAYSOURCE_NAME'],
                                                      isActive=self.config_dict['GATEWAYSOURCE_ISACTIVE'],
                                                      isMonitored=self.config_dict['GATEWAYSOURCE_ISMONITORED'],
                                                      dataFormat=self.config_dict['GATEWAYSOURCE_DATAFORMAT'],
                                                      isVirtual=self.config_dict['GATEWAYSOURCE_ISVIRTUAL']
                                                      )
        gateway_source_key = gateway_source.sourceKey
        print "gateway source created %s" % gateway_source_key
        return gateway_source_key

    def add_plant_meta_source(self,plant,user):
        """

        :param plant:
        :param user:
        :return:
        """

        plant_meta_source = PlantMetaSource.objects.create(plant=plant,
                                                           user=user,
                                                           name=self.config_dict['PLANTMETA_NAME'],
                                                           isActive=self.config_dict['PLANTMETA_ISACTIVE'],
                                                           isMonitored=self.config_dict['PLANTMETA_ISMONITORED'],
                                                           dataFormat=self.config_dict['PLANTMETA_DATAFORMAT'],
                                                           sending_aggregated_power=self.config_dict['PLANTMETA_SENDING_AGGREGATED_POWER'],
                                                           sending_aggregated_energy=self.config_dict['PLANTMETA_SENDING_AGGREGATED_ENERGY'],
                                                           energy_meter_installed=self.config_dict['PLANTMETA_ENERGY_METER_INSTALLED'],
                                                           PV_panel_area=self.config_dict['PLANTMETA_PV_PANEL_AREA'],
                                                           PV_panel_efficiency=self.config_dict['PLANT_META_PV_PANEL_EFFICIENCY'],
                                                           operations_start_time=self.config_dict['PLANT_META_OPERATIONS_START_TIME'],
                                                           operations_end_time=self.config_dict['PLANT_META_OPERATIONS_END_TIME'],
                                                           calculate_hourly_pr=self.config_dict['PLANT_META_CALCULATE_HOURLY_PR'],
                                                           dataReportingInterval=self.config_dict['PLANT_META_REPORTING_INTERVAL'])
        print "Plant meta source created."
        return plant_meta_source.sourceKey

    def add_energy_meters(self, plant,user):
        """

        :param plant:
        :param user:
        :return:
        """
        energy_meter_source_keys = []
        if self.config_dict['ENERGY_METER_ADD'] == 'True':
            for count in range(int(self.config_dict['ENERGY_METER_COUNT'])):
                name = str(plant.slug).upper() + "_Energy_Meter_" + str(count+1)
                energy_meter = EnergyMeter.objects.create(name=name, user=user,
                                                          dataFormat=self.config_dict['ENERGY_METER_DATA_FORMAT'],
                                                          plant=plant, displayName=name,
                                                          manufacturer=self.config_dict['ENERGY_METER_MANUFACTURER'],
                                                          isActive=True, isMonitored=True,
                                                          dataReportingInterval=self.config_dict[
                                                              'ENERGY_METER_DATA_REPORTING_INTERVAL'],
                                                          timeoutInterval=self.config_dict[
                                                              'ENERGY_METER_TIME_OUT_INTERVAL'])
                print "energy meter %s created" % (count+1)
                energy_meter_source_keys.append(energy_meter.name + " : " + energy_meter.sourceKey)
        print "Details of energy meters"
        for i in range(len(energy_meter_source_keys)):
            print "%s" % energy_meter_source_keys[i]
        return energy_meter_source_keys

    def add_weather_stations(self, plant,user):
        """

        :param plant:
        :param user:
        :return:
        """
        weather_station_source_keys = []
        if self.config_dict['WEATHER_STATION_ADD'] == 'True':
            for count in range(int(self.config_dict['WEATHER_STATION_COUNT'])):
                name = 'Weather_Station_' + str(count+1)
                weather_station = WeatherStation.objects.create(name=name,
                                                                user=user,
                                                                dataFormat=self.config_dict['WEATHER_STATION_DATA_FORMAT'],
                                                                plant=plant,
                                                                displayName=name,
                                                                manufacturer=self.config_dict['WEATHER_STATION_MANUFACTURER'],
                                                                model = self.config_dict['WEATHER_STATION_MODEL'],
                                                                isActive=True,
                                                                isMonitored=True,
                                                                dataReportingInterval=self.config_dict['WEATHER_STATION_DATA_REPORTING_INTERVAL'],
                                                                timeoutInterval = self.config_dict['WEATHER_STATION_TIME_OUT_INTERVAL'])
                print "weather station %s created" % count+1,
                weather_station_source_keys.append(weather_station.name + " : " + weather_station.sourceKey)
        print "Details of weather stations"
        for i in range(len(weather_station_source_keys)):
            print "%s" % weather_station_source_keys[i]
        return weather_station_source_keys

    def add_solar_metrics(self, plant,user):
        """

        :param plant:
        :param user:
        :return:
        """
        solar_metrics_source_keys = []
        name = str(plant.slug).upper() + '_SOLAR_METRICS'
        solar_metric = SolarMetrics.objects.create(name=name,
                                                   user=user,
                                                   dataFormat=self.config_dict['SOLAR_METRICS_DATA_FORMAT'],
                                                   plant=plant,
                                                   displayName=name,
                                                   isActive=True,
                                                   isMonitored=True,
                                                   dataReportingInterval=self.config_dict['SOLAR_METRICS_DATA_REPORTING_INTERVAL'],
                                                   timeoutInterval = self.config_dict['SOLAR_METRICS_TIME_OUT_INTERVAL'])
        print "solar metric created"
        solar_metrics_source_keys.append(solar_metric.name + " : " + solar_metric.sourceKey)
        print "Details of solar metrics"
        for i in range(len(solar_metrics_source_keys)):
            print "%s" % solar_metrics_source_keys[i]
        return solar_metrics_source_keys

    def add_solar_groups(self, plant, user):
        """

        :param plant:
        :param user:
        :return:
        """
        solar_groups_slug = []
        plant_slug= str(plant.slug)
        if self.config_dict['GROUP_ADD'] == 'True':
            group_names = ast.literal_eval(self.config_dict['GROUP_NAME'])
            for i in range(len(group_names)):
                group_name = group_names[i]
                group_slug = plant_slug + '_' + str(group_name).lower()
                group = SolarGroup.objects.create(slug=group_slug,
                                                  name=group_name,
                                                  user=user,
                                                  displayName=group_name,
                                                  isActive=True,
                                                  plant=plant,
                                                  group_type=self.config_dict['GROUP_TYPE'],
                                                  roof_type=self.config_dict['GROUP_ROOF_TYPE'],
                                                  tilt_angle=self.config_dict['GROUP_TILT_ANGLE'],
                                                  latitude=self.config_dict['GROUP_LATITUDE'],
                                                  longitude=self.config_dict['GROUP_LONGITUDE'],
                                                  azimuth=self.config_dict['GROUP_AZIMUTH'],
                                                  panel_manufacturer=self.config_dict['GROUP_PANEL_MANUFACTURER'],
                                                  panel_capacity=self.config_dict['GROUP_PANEL_CAPACITY'],
                                                  no_of_panels=self.config_dict['GROUP_PANEL_NUMBERS'],
                                                  PV_panel_area=self.config_dict['GROUP_PV_PANEL_AREA'],
                                                  PV_panel_efficiency=self.config_dict['GROUP_PV_PANEL_EFFICIENCY']
                                                  )
                solar_groups_slug.append(group.name + " : " + group.slug)
        print "Details of solar groups"
        for i in range(len(solar_groups_slug)):
            print "%s" % solar_groups_slug[i]
        return solar_groups_slug

    def add_plant_features_enabled(self, plant):
        """

        :param plant:
        :return:
        """
        features_enabled = PlantFeaturesEnable.objects.create(plant=plant, solar_metrics=True,
                                                              economic_benefits=False,
                                                              analytics=False, alerts=False)
        print "Features enabled instance created %s" % features_enabled
        return features_enabled

    def email_send(self, plant, key_list, ajb_key_list, desc, gateway_source_key, plant_meta_source_key):
        """

        :param plant:
        :param key_list:
        :param ajb_key_list:
        :param desc:
        :param gateway_source_key:
        :param plant_meta_source_key:
        :return:
        """
        email = ['nishant@dataglen.com', 'lavanya@dataglen.com']
        subject = 'New Plant Created : ' + str(plant.slug)
        description = str(desc) + '\n\nA new Plant has been created on dataglen.com with following details \n\nPlant Name ' + str(self.config_dict["PLANT_NAME"]) + '\n'+'Plant Slug: ' + str(self.config_dict["PLANT_SLUG"]) + '\n\n' + 'Inverter Details: \n'+ '\n'.join(key_list) + '\n\nAJB Details: \n'+ '\n'.join(ajb_key_list) + '\n\nGateway Source Details:\n' + str(self.config_dict["GATEWAYSOURCE_NAME"]) + " : " + str(gateway_source_key) + "\n\nPlant Meta Source Details:\n" + str(self.config_dict["PLANTMETA_NAME"]) + " : " + str(plant_meta_source_key) + '\n\n\n' + 'Best Wishes,\n' + 'Team Dataglen'
        send_mail(subject, description, 'admin@dataglen.com', email, fail_silently=False)
        print "email sent"

    def add_queue(self, plant):
        """

        :param plant:
        :return:
        """
        queue = Queue.objects.create(plant=plant, title=str(plant.slug), slug=str(plant.slug))
        print "Queue created %s" % queue
        return queue


def create_new_plants():
    names = ["SUEIC", "INFANTA", "BALER", "BAGUIO", "TUGUEGARAO", "APARRI", "BASCO",
             "DACT", "VIRAC", "CATARMAN", "MASBATE", "SAN JOSE", "CUYO", "PTC. PRINCESA",
             "QUEZON", "ROKAS", "ILOILO", "MACTAN", "SURIGAO", "GUINAN", "DUMAGUETE",
             "BUTUAN", "DIPLOLOG", "LAGUINDINGAN", "MOLUGAN", "MALAYBALAY", "HINATUAN",
             "ZAMECANGA", "COTABATO", "DAVAO", "TAMPAKAN"]
    try:
        with transaction.atomic():
            for name in names:
                # desc = create_dataglen_client(False)
                plantCreation = PlantCreation(name, name.lower())
                client = plantCreation.get_client()
                plant = plantCreation.add_plant(client)
                user = plantCreation.get_user()
                plant_user = plantCreation.create_plant_user(user,plant)
                plant_owner = plantCreation.create_plant_owner(plant,plant_user)
                # key_list = plantCreation.add_inverters(plant,user)
                # ajb_key_list = plantCreation.add_ajb(plant, user)
                token = plantCreation.get_auth_token(user)
                gateway_source_key = plantCreation.add_plant_gateway_source(plant, user)
                plant_meta_source_key = plantCreation.add_plant_meta_source(plant, user)
                # energy_meters = plantCreation.add_energy_meters(plant, user)
                # solar_metrics = plantCreation.add_solar_metrics(plant, user)
                features_enabled = plantCreation.add_plant_features_enabled(plant)
                queue = plantCreation.add_queue(plant)
                # plantCreation.email_send(plant, key_list, ajb_key_list, desc, gateway_source_key, plant_meta_source_key)
                setup_new_plant(plant)
    except:
        import traceback
        print "%s" % traceback.format_exc()
        print "%s" % sys.exc_info()[0]