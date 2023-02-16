import sys
import os
import django
import configparser
import requests
import json
#sys.path.append("/Dataglen/template-integration/kutbill-django")
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from django.db import IntegrityError
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from dashboards.models import DataglenClient
from dashboards.models import Dashboard
from organizations.models import OrganizationOwner
from organizations.models import OrganizationUser
from solarrms.models import SolarPlant, IndependentInverter, GatewaySource, PlantMetaSource, AJB, EnergyMeter, Transformer, \
    WeatherStation, SolarMetrics, SolarGroup, PlantFeaturesEnable
from django.core.mail import send_mail
from client_creation_script import create_dataglen_client
from rest_framework.authtoken.models import Token
import ast
from helpdesk.models import Queue

CONFIG_FILE = "plant_creation.cfg"


class PlantCreation(object):
    inverter_key_list = []
    def get_config_parameters(self):
        config_dict = {}
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            config_dict['USER_NAME'] = config['USER']['NAME']
            config_dict['CLIENT_SLUG'] = config['CLIENT']['SLUG']
            config_dict['PLANT_NAME'] = config['PLANT']['NAME']
            config_dict['PLANT_SLUG'] = config['PLANT']['SLUG']
            config_dict['PLANT_ACTIVE'] = config['PLANT']['IS_ACTIVE']
            config_dict['PLANT_CAPACITY'] = config['PLANT']['CAPACITY']
            config_dict['PLANT_LOCATION'] = config['PLANT']['LOCATION']
            config_dict['PLANT_OPENWEATHER'] = config['PLANT']['OPENWEATHER']
            config_dict['PLANT_OPERATIONAL'] = config['PLANT']['ISOPERATIONAL']
            config_dict['PLANT_LATITUDE'] = config['PLANT']['LATITUDE']
            config_dict['PLANT_LONGITUDE'] = config['PLANT']['LONGITUDE']
            config_dict['PLANT_EVACUATION_POINT'] = config['PLANT']['EVACUATION_POINT']
            config_dict['PLANT_WEBDYN_DEVICE_ID'] = config['PLANT']['WEBDYN_DEVICE_ID']
            config_dict['INVERTER_COUNT'] = config['INVERTER']['COUNT']
            config_dict['DATA_FORMAT'] = config['INVERTER']['DATA_FORMAT']
            config_dict['MANUFACTURER'] = config['INVERTER']['MANUFACTURER']
            config_dict['INVERTER_MODEL'] = config['INVERTER']['MODEL']
            config_dict['INVERTER_TIME_OUT_INTERVAL'] = config['INVERTER']['TIME_OUT_INTERVAL']
            config_dict['DATA_REPORTING_INTERVAL'] = config['INVERTER']['REPORTING_INTERVAL']
            config_dict['SOURCE_NAME'] = config['GATEWAY']['SOURCE_NAME']
            config_dict['SOURCE_ACTIVE'] = config['GATEWAY']['IS_ACTIVE']
            config_dict['SOURCE_MONITORED'] = config['GATEWAY']['IS_MONITORED']
            config_dict['SOURCE_DATAFORMAT'] = config['GATEWAY']['DATAFORMAT']
            config_dict['SERVER_URL'] = config['API']['SERVER_URL']
            config_dict['SOURCE_URL'] = config['API']['SOURCE_URL']
            config_dict['STREAM_HEARTBEAT'] = config['GATEWAY']['HEARTBEAT']
            config_dict['STREAM_TIESTAMP'] = config['GATEWAY']['TIMESTAMP']
            config_dict['GATEWAYSOURCE_NAME'] = config['GATEWAYSOURCE']['NAME']
            config_dict['GATEWAYSOURCE_ISACTIVE'] = config['GATEWAYSOURCE']['ISACTIVE']
            config_dict['GATEWAYSOURCE_ISMONITORED'] = config['GATEWAYSOURCE']['ISMONITORED']
            config_dict['GATEWAYSOURCE_DATAFORMAT'] = config['GATEWAYSOURCE']['DATAFORMAT']
            config_dict['GATEWAYSOURCE_ISVIRTUAL'] = config['GATEWAYSOURCE']['ISVIRTUAL']
            config_dict['PLANTMETA_NAME'] = config['PLANT_META']['NAME']
            config_dict['PLANTMETA_ISACTIVE'] = config['PLANT_META']['ISACTIVE']
            config_dict['PLANTMETA_ISMONITORED'] = config['PLANT_META']['ISMONITORED']
            config_dict['PLANTMETA_DATAFORMAT'] = config['PLANT_META']['DATAFORMAT']
            config_dict['PLANTMETA_SENDING_AGGREGATED_POWER'] = config['PLANT_META']['SENDING_AGGREGATED_POWER']
            config_dict['PLANTMETA_SENDING_AGGREGATED_ENERGY'] = config['PLANT_META']['SENDING_AGGREGATED_ENERGY']
            config_dict['PLANTMETA_ENERGY_METER_INSTALLED'] = config['PLANT_META']['ENERGY_METER_INSTALLED']
            config_dict['PLANTMETA_PV_PANEL_AREA'] = config['PLANT_META']['PV_PANEL_AREA']
            config_dict['PLANT_META_PV_PANEL_EFFICIENCY'] = config['PLANT_META']['PV_PANEL_EFFICIENCY']
            config_dict['PLANT_META_OPERATIONS_START_TIME'] = config['PLANT_META']['OPERATIONS_START_TIME']
            config_dict['PLANT_META_OPERATIONS_END_TIME'] = config['PLANT_META']['OPERATIONS_END_TIME']
            config_dict['PLANT_META_CALCULATE_HOURLY_PR'] = config['PLANT_META']['CALCULATE_HOURLY_PR']
            config_dict['PLANT_META_REPORTING_INTERVAL'] = config['PLANT_META']['REPORTING_INTERVAL']
            config_dict['INVERTER_CAPACITY'] = config['INVERTER']['CAPACITY']
            config_dict['INVERTER_ORIENTATION'] = config['INVERTER']['ORIENTATION']
            config_dict['AJB_ADD'] = config['AJB']['ADD']
            config_dict['AJB_COUNT'] = config['AJB']['COUNT']
            config_dict['AJB_MANUFACTURER'] = config['AJB']['MANUFACTURER']
            config_dict['AJB_DATA_REPORTING_INTERVAL'] = config['AJB']['REPORTING_INTERVAL']

            config_dict['ENERGY_METER_ADD'] = config['ENERGY_METER']['ADD']
            config_dict['ENERGY_METER_COUNT'] = config['ENERGY_METER']['COUNT']
            config_dict['ENERGY_METER_DATA_FORMAT'] = config['ENERGY_METER']['DATA_FORMAT']
            config_dict['ENERGY_METER_MANUFACTURER'] = config['ENERGY_METER']['MANUFACTURER']
            config_dict['ENERGY_METER_DATA_REPORTING_INTERVAL'] = config['ENERGY_METER']['REPORTING_INTERVAL']
            config_dict['ENERGY_METER_TIME_OUT_INTERVAL'] = config['ENERGY_METER']['TIME_OUT_INTERVAL']

            config_dict['TRANSFORMER_ADD'] = config['TRANSFORMER']['ADD']
            config_dict['TRANSFORMER_COUNT'] = config['TRANSFORMER']['COUNT']
            config_dict['TRANSFORMER_DATA_FORMAT'] = config['TRANSFORMER']['DATA_FORMAT']
            config_dict['TRANSFORMER_MANUFACTURER'] = config['TRANSFORMER']['MANUFACTURER']
            config_dict['TRANSFORMER_DATA_REPORTING_INTERVAL'] = config['TRANSFORMER']['REPORTING_INTERVAL']
            config_dict['TRANSFORMER_TIME_OUT_INTERVAL'] = config['TRANSFORMER']['TIME_OUT_INTERVAL']

            config_dict['WEATHER_STATION_ADD'] = config['WEATHER_STATION']['ADD']
            config_dict['WEATHER_STATION_COUNT'] = config['WEATHER_STATION']['COUNT']
            config_dict['WEATHER_STATION_DATA_FORMAT'] = config['WEATHER_STATION']['DATA_FORMAT']
            config_dict['WEATHER_STATION_MANUFACTURER'] = config['WEATHER_STATION']['MANUFACTURER']
            config_dict['WEATHER_STATION_MODEL'] = config['WEATHER_STATION']['MODEL']
            config_dict['WEATHER_STATION_DATA_REPORTING_INTERVAL'] = config['WEATHER_STATION']['REPORTING_INTERVAL']
            config_dict['WEATHER_STATION_TIME_OUT_INTERVAL'] = config['WEATHER_STATION']['TIME_OUT_INTERVAL']

            config_dict['SOLAR_METRICS_COUNT'] = config['SOLAR_METRICS']['COUNT']
            config_dict['SOLAR_METRICS_DATA_FORMAT'] = config['SOLAR_METRICS']['DATA_FORMAT']
            config_dict['SOLAR_METRICS_DATA_REPORTING_INTERVAL'] = config['SOLAR_METRICS']['REPORTING_INTERVAL']
            config_dict['SOLAR_METRICS_TIME_OUT_INTERVAL'] = config['SOLAR_METRICS']['TIME_OUT_INTERVAL']

            config_dict['GROUP_ADD'] = config['GROUP']['ADD']
            config_dict['GROUP_NAME'] = config['GROUP']['NAME']
            config_dict['GROUP_TYPE'] = config['GROUP']['TYPE']
            config_dict['GROUP_ROOF_TYPE'] = config['GROUP']['ROOF_TYPE']
            config_dict['GROUP_TILT_ANGLE'] = config['GROUP']['TILT_ANGLE']
            config_dict['GROUP_LATITUDE'] = config['GROUP']['LATITUDE']
            config_dict['GROUP_LONGITUDE'] = config['GROUP']['LONGITUDE']
            config_dict['GROUP_AZIMUTH'] = config['GROUP']['AZIMUTH']
            config_dict['GROUP_PANEL_MANUFACTURER'] = config['GROUP']['PANEL_MANUFACTURER']
            config_dict['GROUP_PANEL_CAPACITY'] = config['GROUP']['PANEL_CAPACITY']
            config_dict['GROUP_PANEL_NUMBERS'] = config['GROUP']['PANEL_NUMBERS']
            config_dict['GROUP_PV_PANEL_AREA'] = config['GROUP']['PV_PANEL_AREA']
            config_dict['GROUP_PV_PANEL_EFFICIENCY'] = config['GROUP']['PV_PANEL_EFFICIENCY']

        except configparser.Error:
            config_dict = None
        return config_dict

    def __init__(self):

        self.config_dict = self.get_config_parameters()
        if not self.config_dict:
            sys.exit()


    def get_user(self):
    	try:
    		try:
    			user = User.objects.get(username=self.config_dict['USER_NAME'])
    			return user
    		except Exception as exception:
    			print(str(exception))

    	except IntegrityError as exception:
    		print(str(exception))
    	except Exception as exception:
    		print(str(exception))


    def get_client(self):
    	try:
    		try:
    			client = DataglenClient.objects.get(slug=self.config_dict["CLIENT_SLUG"])
    			return client
    		except Exception as exception:
    			print(str(exception))

    	except IntegrityError as exception:
    		print(str(exception))
    	except Exception as exception:
    		print(str(exception))

    def add_plant(self, client):
    	try:
            evacuation_point = self.config_dict['PLANT_EVACUATION_POINT'] if self.config_dict['PLANT_EVACUATION_POINT'] else None
            webdyn_device_id = self.config_dict['PLANT_WEBDYN_DEVICE_ID'] if self.config_dict['PLANT_WEBDYN_DEVICE_ID'] else None
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
                                              evacuation_point= evacuation_point,
                                              webdyn_device_id=webdyn_device_id)
            plant.save()
            new_slug = str(plant.slug).replace("-","")
            plant.slug = new_slug
            plant.save()
    	    print ("plant created")
    	    return plant
    	except IntegrityError as exception:
    		print(str(exception))
    	except Exception as exception:
    		print(str(exception))

    def create_plant_user(self,user,plant):
        try:
            organization_user = OrganizationUser.objects.get(user=user,
                                                             organization=plant)
            return organization_user
        except:
            try:
                organization_user = OrganizationUser.objects.create(user=user,
                                                                    organization=plant,
                                                                    is_admin=True)
                organization_user.save()
                print("Plant User Created")
                return organization_user
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))


    def create_plant_owner(self,plant,organization_user):
        try:
            organization_owner = OrganizationOwner.objects.get(organization=plant,
    														   organization_user=organization_user)
            return organization_owner
        except:
            try:
                organization_owner = OrganizationOwner.objects.create(organization=plant,
                                                                      organization_user=organization_user)
                organization_owner.save()
                print("Plant Owner Created")
                return organization_owner
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))

    # use below commented method for plants where inverter names are symmetrical (like Inverter_1, Inverter_2)
    def add_inverters(self,plant,user):
        try:
            source_keys = []
            for count in range(int(self.config_dict['INVERTER_COUNT'])):
            	name = str(plant.slug).upper() + '_Inverter_' + str(count+1)
            	inverter = IndependentInverter.objects.create(name=name,
            												  user=user,
            												  dataFormat=self.config_dict['DATA_FORMAT'],
            												  plant=plant,
            												  displayName=name,
            												  manufacturer=self.config_dict['MANUFACTURER'],
                                                              model = self.config_dict['INVERTER_MODEL'],
                                                              isActive=True,
                                                              isMonitored=True,
                                                              dataReportingInterval=self.config_dict['DATA_REPORTING_INTERVAL'],
                                                              timeoutInterval = self.config_dict['INVERTER_TIME_OUT_INTERVAL'],
                                                              total_capacity = self.config_dict['INVERTER_CAPACITY'],
                                                              actual_capacity = self.config_dict['INVERTER_CAPACITY'],
                                                              orientation = self.config_dict['INVERTER_ORIENTATION'])
            	inverter.save()
                print("inverter",count+1,"created")
                source_keys.append(inverter.name + " : " + inverter.sourceKey)
                #source_keys.append(inverter.sourceKey)
            inverter_key_list = source_keys
            print("Details of inverters")
            for i in range(len(source_keys)):
            	print (source_keys[i])
            return inverter_key_list
    	except IntegrityError as exception:
    		print(str(exception))
    	except Exception as exception:
    		print(str(exception))

    # specific add inverters method for waaneep, for other plants where inverter names are symmetrical, uncomment above method and use that.
    # def add_inverters(self,plant,user):
    #     try:
    #         source_keys = []
    #         for i in range(7):
    #             for count in range(4):
    #                 name = 'PVCS' + str(i+1) + str('.') + 'INV' + str(count+1)
    #                 inverter = IndependentInverter.objects.create(name=name,
    #                                                               user=user,
    #                                                               dataFormat=self.config_dict['DATA_FORMAT'],
    #                                                               plant=plant,
    #                                                               displayName=name,
    #                                                               manufacturer=self.config_dict['MANUFACTURER'],
    #                                                               model = self.config_dict['INVERTER_MODEL'],
    #                                                               isActive=True,
    #                                                               isMonitored=True,
    #                                                               dataReportingInterval=self.config_dict['DATA_REPORTING_INTERVAL'],
    #                                                               total_capacity = self.config_dict['INVERTER_CAPACITY'],
    #                                                               actual_capacity = self.config_dict['INVERTER_CAPACITY'],
    #                                                               orientation = self.config_dict['INVERTER_ORIENTATION'])
    #                 inverter.save()
    #                 print("inverter",count+1,"created")
    #                 source_keys.append(inverter.name + " : " + inverter.sourceKey)
    #         # for i in range(8):
    #         #     for count in range(4):
    #         #         name = 'NIOSOL_Inverter_' + str(i+1) + str('.') + str(count+1)
    #         #         inverter = IndependentInverter.objects.create(name=name,
    #         #                                                       user=user,
    #         #                                                       dataFormat=self.config_dict['DATA_FORMAT'],
    #         #                                                       plant=plant,
    #         #                                                       displayName=name,
    #         #                                                       manufacturer=self.config_dict['MANUFACTURER'],
    #         #                                                       model = self.config_dict['INVERTER_MODEL'],
    #         #                                                       isActive=True,
    #         #                                                       isMonitored=True,
    #         #                                                       dataReportingInterval=self.config_dict['DATA_REPORTING_INTERVAL'],
    #         #                                                       total_capacity = self.config_dict['INVERTER_CAPACITY'],
    #         #                                                       actual_capacity = self.config_dict['INVERTER_CAPACITY'],
    #         #                                                       orientation = self.config_dict['INVERTER_ORIENTATION'])
    #         #         inverter.save()
    #         #         print("inverter",count+1,"created")
    #         #         source_keys.append(inverter.name + " : " + inverter.sourceKey)
    #                 #source_keys.append(inverter.sourceKey)
    #         inverter_key_list = source_keys
    #         print("Details of inverters")
    #         for i in range(len(source_keys)):
    #         	print (source_keys[i])
    #         return inverter_key_list
    # 	except IntegrityError as exception:
    # 		print(str(exception))
    # 	except Exception as exception:
    # 		print(str(exception))

    # def add_ajb(self, plant, user):
    #     ajb_source_keys = []
    #     if self.config_dict['AJB_ADD']:
    #         try:
    #             inverters = IndependentInverter.objects.filter(plant=plant)
    #             for inverter in inverters:
    #                 inverter_name = str(inverter.name)
    #                 #inverter_name_split = inverter_name.split('_',3)
    #                 for count in range(int(self.config_dict['AJB_COUNT'])):
    #                     #ajb_name = str(inverter_name_split[0]) + '_SMB_'+ str(inverter_name_split[2])+ '.' + str(count+1)
    #                     ajb_name = inverter_name+('_SMB')+str(count+1)
    #                     ajb = AJB.objects.create(user=user,
    #                                              name= ajb_name,
    #         									 plant=plant,
    #                                              independent_inverter = inverter,
    #         									 displayName=ajb_name,
    #         									 manufacturer=self.config_dict['AJB_MANUFACTURER'],
    #                                              isActive=True,
    #                                              isMonitored=True,
    #                                              dataReportingInterval=self.config_dict['AJB_DATA_REPORTING_INTERVAL'])
    #                     ajb.save()
    #                     print(ajb_name,"created")
    #                     ajb_source_keys.append(ajb.name + " : " + ajb.sourceKey)
    #             return ajb_source_keys
    #         except Exception as exception:
    #             print(str(exception))
    #     else:
    #         return ajb_source_keys

    #use below commented method to create ajbs where inverter names are symmetrical
    def add_ajb(self, plant, user):
        ajb_source_keys = []
        print self.config_dict['AJB_ADD']
        if self.config_dict['AJB_ADD'] == 'True':
            print "inside ajb create"
            try:
                inverters = IndependentInverter.objects.filter(plant=plant)
                for inverter in inverters:
                    inverter_name = str(inverter.name)
                    inverter_name_split = inverter_name.split('_',2)
                    for count in range(int(self.config_dict['AJB_COUNT'])):
                        #ajb_name = 'SMB_'+ str(inverter_name_split[0])+ '_' + str(inverter_name_split[1]) + '.' +str(count+1)
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
                        ajb.save()
                        print(ajb_name,"created")
                        ajb_source_keys.append(ajb.name + " : " + ajb.sourceKey)
                return ajb_source_keys
            except Exception as exception:
                print(str(exception))
        else:
            return ajb_source_keys


    def get_auth_token(self, user):
        try:
            token = Token.objects.get(user=user)
            api_token = token
            return token
        except IntegrityError as exception:
            print(str(exception))
        except Exception as exception:
            print(str(exception))

    """
    def add_gateway_source(self,token):
        try:
            url = self.config_dict['SERVER_URL'] + self.config_dict['SOURCE_URL']
            print(url)
            api_token = 'Token ' + str(token)
            post_body = {
                              "name": self.config_dict['SOURCE_NAME'],
                              "dataFormat": self.config_dict['SOURCE_DATAFORMAT'],
                              "isActive": self.config_dict['SOURCE_ACTIVE'],
                              "isMonitored": self.config_dict['SOURCE_MONITORED'],
                        }
            length = sys.getsizeof(post_body)
            auth_header = {'Authorization': api_token, 'content-length': length, 'content-type': 'application/json'}
            response = requests.post(url , data = json.dumps(post_body) , headers = auth_header)
            resp_dict = json.loads(response.content)
            key = resp_dict['sourceKey']
            print('Gateway source created')
            print(response.content)
            return key
        except IntegrityError as exception:
            print(str(exception))
        except Exception as exception:
            print(str(exception))

    def add_gateway_streams(self,token,key):
        try:
            url = self.config_dict['SERVER_URL'] + self.config_dict['SOURCE_URL'] + key + '/streams/'
            print(url)
            api_token = 'Token ' + str(token)
            post_body_heartbeat = {
                                    "name": self.config_dict['STREAM_HEARTBEAT'],
                                    "streamDataType": "BOOLEAN"
                                  }
            post_body_timestamp = {
                                    "name": self.config_dict['STREAM_TIESTAMP'],
                                    "streamDataType": "TIMESTAMP"
                                  }
            length_heartbeat = sys.getsizeof(post_body_heartbeat)
            length_timestamp = sys.getsizeof(post_body_timestamp)
            auth_header_heartbeat = {'Authorization': api_token, 'content-length': length_heartbeat, 'content-type': 'application/json'}
            auth_header_timestamp = {'Authorization': api_token, 'content-length': length_timestamp, 'content-type': 'application/json'}
            response_heartbeat = requests.post(url , data = json.dumps(post_body_heartbeat) , headers = auth_header_heartbeat)
            print("HEARTBEAT stream created for Gateway source")
            print(response_heartbeat.content)
            response_timestamp = requests.post(url , data = json.dumps(post_body_timestamp) , headers = auth_header_timestamp)
            print("TIMESTAMP stream created for Gateway source")
            print(response_timestamp.content)
        except IntegrityError as exception:
            print(str(exception))
        except Exception as exception:
            print(str(exception))
    """

    def add_plant_gateway_source(self,plant,user):
        try:
            gateway_source = GatewaySource.objects.create(plant=plant,
                                                          user=user,
                                                          name=self.config_dict['GATEWAYSOURCE_NAME'],
                                                          isActive=self.config_dict['GATEWAYSOURCE_ISACTIVE'],
                                                          isMonitored=self.config_dict['GATEWAYSOURCE_ISMONITORED'],
                                                          dataFormat=self.config_dict['GATEWAYSOURCE_DATAFORMAT'],
                                                          isVirtual=self.config_dict['GATEWAYSOURCE_ISVIRTUAL']
                                                          )
            gateway_source.save()
            gateway_source_key = gateway_source.sourceKey
            print("gateway source created")
            return gateway_source_key
        except Exception as exception:
            print(str(exception))

    def add_plant_meta_source(self,plant,user):
        try:
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
            plant_meta_source.save()
            print("Plant meta source created.")
            return plant_meta_source.sourceKey
        except Exception as exception:
            print(str(exception))

    def add_energy_meters(self, plant,user):
        try:
            energy_meter_source_keys = []
            if self.config_dict['ENERGY_METER_ADD'] == 'True':
                for count in range(int(self.config_dict['ENERGY_METER_COUNT'])):
                    name = str(plant.slug).upper() + "_Energy_Meter_" + str(count+1)
                    energy_meter = EnergyMeter.objects.create(name=name,
                                                                  user=user,
                                                                  dataFormat=self.config_dict['ENERGY_METER_DATA_FORMAT'],
                                                                  plant=plant,
                                                                  displayName=name,
                                                                  manufacturer=self.config_dict['ENERGY_METER_MANUFACTURER'],
                                                                  isActive=True,
                                                                  isMonitored=True,
                                                                  dataReportingInterval=self.config_dict['ENERGY_METER_DATA_REPORTING_INTERVAL'],
                                                                  timeoutInterval = self.config_dict['ENERGY_METER_TIME_OUT_INTERVAL'])
                    energy_meter.save()
                    print("energy meter",count+1,"created")
                    energy_meter_source_keys.append(energy_meter.name + " : " + energy_meter.sourceKey)

            print("Details of energy meters")
            for i in range(len(energy_meter_source_keys)):
            	print (energy_meter_source_keys[i])
            return energy_meter_source_keys
        except Exception as exception:
            print(str(exception))

    def add_transformers(self, plant,user):
        try:
            transformer_source_keys = []
            if self.config_dict['TRANSFORMER_ADD'] == 'True':
                for count in range(int(self.config_dict['TRANSFORMER_COUNT'])):
                    name = 'Transformer_' + str(count+1)
                    transformer = Transformer.objects.create(name=name,
                                                              user=user,
                                                              dataFormat=self.config_dict['TRANSFORMER_DATA_FORMAT'],
                                                              plant=plant,
                                                              displayName=name,
                                                              manufacturer=self.config_dict['TRANSFORMER_MANUFACTURER'],
                                                              isActive=True,
                                                              isMonitored=True,
                                                              dataReportingInterval=self.config_dict['TRANSFORMER_DATA_REPORTING_INTERVAL'],
                                                              timeoutInterval = self.config_dict['TRANSFORMER_TIME_OUT_INTERVAL'])
                    transformer.save()
                    print("transformer",count+1,"created")
                    transformer_source_keys.append(transformer.name + " : " + transformer.sourceKey)

            print("Details of transformers")
            for i in range(len(transformer_source_keys)):
            	print (transformer_source_keys[i])
            return transformer_source_keys
        except Exception as exception:
            print(str(exception))

    def add_weather_stations(self, plant,user):
        try:
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
                    weather_station.save()
                    print("weather station",count+1,"created")
                    weather_station_source_keys.append(weather_station.name + " : " + weather_station.sourceKey)

            print("Details of weather stations")
            for i in range(len(weather_station_source_keys)):
            	print (weather_station_source_keys[i])
            return weather_station_source_keys
        except Exception as exception:
            print(str(exception))

    def add_solar_metrics(self, plant,user):
        try:
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
            solar_metric.save()
            print("solar metric created")
            solar_metrics_source_keys.append(solar_metric.name + " : " + solar_metric.sourceKey)

            print("Details of solar metrics")
            for i in range(len(solar_metrics_source_keys)):
            	print (solar_metrics_source_keys[i])
            return solar_metrics_source_keys
        except Exception as exception:
            print(str(exception))

    def add_solar_groups(self, plant, user):
        try:
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
                    group.save()
                    solar_groups_slug.append(group.name + " : " + group.slug)
            print("Details of solar groups")
            for i in range(len(solar_groups_slug)):
            	print (solar_groups_slug[i])
            return solar_groups_slug
        except Exception as exception:
            print str(exception)

    def add_plant_features_enabled(self, plant):
        try:
            features_enabled = PlantFeaturesEnable.objects.create(plant=plant,
                                                                  solar_metrics=True,
                                                                  economic_benefits=False,
                                                                  analytics=False,
                                                                  alerts=False
                                                                  )
            features_enabled.save()
            print("Features enabled instance created")
            return features_enabled
        except Exception as exception:
            print(str(exception))

    def email_send(self, plant, key_list, ajb_key_list, desc, gateway_source_key, plant_meta_source_key):
        email = ['nishant@dataglen.com']
        subject = 'New Plant Created : ' + str(plant.slug)
        description = desc + '\n\nA new Plant has been created on dataglen.com with following details \n\nPlant Name ' + self.config_dict["PLANT_NAME"] + '\n'+'Plant Slug: ' + self.config_dict["PLANT_SLUG"] + '\n\n' + 'Inverter Details: \n'+ '\n'.join(key_list) + '\n\nAJB Details: \n'+ '\n'.join(ajb_key_list) + '\n\nGateway Source Details:\n' + self.config_dict["GATEWAYSOURCE_NAME"] + " : " + gateway_source_key + "\n\nPlant Meta Source Details:\n" + self.config_dict["PLANTMETA_NAME"] + " : " + plant_meta_source_key + '\n\n\n' + 'Best Wishes,\n' + 'Team Dataglen'
        try:
            send_mail(subject,description,'admin@dataglen.com',email,fail_silently=False)
            print("email sent")
        except Exception as exception:
            print(str(exception))


    def add_queue(self, plant):
        try:
            queue = Queue.objects.create(plant=plant,
                                         title=str(plant.slug),
                                         slug=str(plant.slug)
                                         )
            queue.save()
            print("Queue created")
            return queue
        except Exception as exception:
            print(str(exception))


if __name__ == "__main__":
    desc = create_dataglen_client(False)
    plantCreation = PlantCreation()
    client = plantCreation.get_client()
    plant = plantCreation.add_plant(client)
    user = plantCreation.get_user()
    plant_user = plantCreation.create_plant_user(user,plant)
    plant_owner = plantCreation.create_plant_owner(plant,plant_user)
    key_list = plantCreation.add_inverters(plant,user)
    ajb_key_list = plantCreation.add_ajb(plant, user)
    token = plantCreation.get_auth_token(user)
    #key = plantCreation.add_gateway_source(token)
    #plantCreation.add_gateway_streams(token,key)
    gateway_source_key = plantCreation.add_plant_gateway_source(plant, user)
    plant_meta_source_key = plantCreation.add_plant_meta_source(plant, user)
    energy_meters = plantCreation.add_energy_meters(plant, user)
    #transformers = plantCreation.add_transformers(plant, user)
    #weather_stations = plantCreation.add_weather_stations(plant, user)
    solar_metrics = plantCreation.add_solar_metrics(plant, user)
    features_enabled = plantCreation.add_plant_features_enabled(plant)
    queue = plantCreation.add_queue(plant)
    #solar_groups = plantCreation.add_solar_groups(plant, user)
    plantCreation.email_send(plant, key_list, ajb_key_list, desc, gateway_source_key, plant_meta_source_key)

