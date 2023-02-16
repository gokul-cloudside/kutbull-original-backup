from django.db import models
from dashboards.models import DataglenGroup, DataglenClient
from dataglen.models import Sensor, Field, SensorGroup
from errors.models import ErrorField
from .settings import INPUT_PARAMETERS, OUTPUT_PARAMETERS, STATUS_PARAMETERS, FIELD_CHOICES, \
    FEEDER_PARAMETERS, STRINGS, TEMPERATURE_SENSORS, OTHERS, METADATA_STREAMS, METADATA_STATUS_PARAMETERS, \
    METADATA_INPUT_PATAMETERS,GATEWAY_STREAMS,GATEWAY_INPUT_PATAMETERS, INVERTER_ERROR_FIELDS, PLANT_META_ERROR_FIELDS, AJB_ERROR_FIELDS, \
    WEATHER_STATION_STREAMS, WEATHER_STATION_STATUS_PARAMETERS, WEATHER_STATION_INPUT_PATAMETERS, SOLAR_METRICS_STREAMS, SOLAR_METRICS_STATUS_PARAMETERS, \
    SOLAR_METRICS_INPUT_PATAMETERS,ENERGY_METER_STREAMS, ENERGY_METER_ERROR_STREAMS, TRANSFORMER_STREAMS, TRANSFORMER_ERROR_STREAMS, VIRTUAL_GATEWAY_INPUT_PARAMETERS, \
    VIRTUAL_GATEWAY_OUTPUT_PARAMETERS, VIRTUAL_GATEWAY_STATUS_PARAMETERS, VIRTUAL_GATEWAY_ERROR_FIELDS, MPPT_INPUT_PARAMETERS, WMS_INPUT_PARAMETERS, WMS_STATUS_PARAMETERS, WMS_STREAMS
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from django.conf import settings
from jsonfield import JSONField
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db import transaction
import logging
from tagging.models import Tag
from tagging.registry import register as tagging_register
from django.contrib.auth.models import User

streams_mappings = {u'ACTIVE_ENERGY': 'Active Energy',
 u'ACTIVE_POWER': 'AC Power',
 u'ACTIVE_POWER_B': 'AC Power B-Phase',
 u'ACTIVE_POWER_R': 'AC Power R-Phase',
 u'ACTIVE_POWER_Y': 'AC Power Y-Phase',
 u'AC_FREQUENCY': 'AC Frequency',
 u'AC_FREQUENCY_B': 'AC Frequency B-Phase',
 u'AC_FREQUENCY_R': 'AC Frequency R-Phase',
 u'AC_FREQUENCY_Y': 'AC Frequency Y-Phase',
 u'AC_VOLTAGE': 'AC Voltage',
 u'AC_VOLTAGE_B': 'AC Voltage B-Phase',
 u'AC_VOLTAGE_R': 'AC Voltage R-Phase',
 u'AC_VOLTAGE_Y': 'AC Voltage Y-Phase',
 u'AGGREGATED': 'AGGREGATED',
 u'AGGREGATED_COUNT': 'AGGREGATED_COUNT',
 u'AGGREGATED_END_TIME': 'AGGREGATED_END_TIME',
 u'AGGREGATED_START_TIME': 'AGGREGATED_START_TIME',
 u'APPARENT_POWER': 'Apparent Power',
 u'APPARENT_POWER_B': 'Apparent Power B-Phase',
 u'APPARENT_POWER_R': 'Apparent Power R-Phase',
 u'APPARENT_POWER_Y': 'Apparent Power Y-Phase',
 u'CONVERTER_TEMPERATURE': 'Converter Temperature',
 u'CONVERTER_VOLTAGE': 'Converter Voltage',
 u'CUBICLE_TEMPERATURE': 'Cubicle Temperature',
 u'CURRENT': 'AC Current',
 u'CURRENT_B': 'AC Current B-Phase',
 u'CURRENT_COMPLETE_ERROR': 'CURRENT_COMPLETE_ERROR',
 u'CURRENT_ERROR': 'CURRENT_ERROR',
 u'CURRENT_R': 'AC Current R-Phase',
 u'CURRENT_Y': 'AC Current Y-Phase',
 u'DAILY_OPERATIONAL_HOURS': 'Todays Operational Runtime',
 u'DAILY_SCADA_ENERGY_DAY_1': 'DAILY_SCADA_ENERGY_DAY_1',
 u'DAILY_SCADA_ENERGY_DAY_10': 'DAILY_SCADA_ENERGY_DAY_10',
 u'DAILY_SCADA_ENERGY_DAY_11': 'DAILY_SCADA_ENERGY_DAY_11',
 u'DAILY_SCADA_ENERGY_DAY_12': 'DAILY_SCADA_ENERGY_DAY_12',
 u'DAILY_SCADA_ENERGY_DAY_13': 'DAILY_SCADA_ENERGY_DAY_13',
 u'DAILY_SCADA_ENERGY_DAY_14': 'DAILY_SCADA_ENERGY_DAY_14',
 u'DAILY_SCADA_ENERGY_DAY_15': 'DAILY_SCADA_ENERGY_DAY_15',
 u'DAILY_SCADA_ENERGY_DAY_16': 'DAILY_SCADA_ENERGY_DAY_16',
 u'DAILY_SCADA_ENERGY_DAY_17': 'DAILY_SCADA_ENERGY_DAY_17',
 u'DAILY_SCADA_ENERGY_DAY_18': 'DAILY_SCADA_ENERGY_DAY_18',
 u'DAILY_SCADA_ENERGY_DAY_19': 'DAILY_SCADA_ENERGY_DAY_19',
 u'DAILY_SCADA_ENERGY_DAY_2': 'DAILY_SCADA_ENERGY_DAY_2',
 u'DAILY_SCADA_ENERGY_DAY_20': 'DAILY_SCADA_ENERGY_DAY_20',
 u'DAILY_SCADA_ENERGY_DAY_21': 'DAILY_SCADA_ENERGY_DAY_21',
 u'DAILY_SCADA_ENERGY_DAY_22': 'DAILY_SCADA_ENERGY_DAY_22',
 u'DAILY_SCADA_ENERGY_DAY_23': 'DAILY_SCADA_ENERGY_DAY_23',
 u'DAILY_SCADA_ENERGY_DAY_24': 'DAILY_SCADA_ENERGY_DAY_24',
 u'DAILY_SCADA_ENERGY_DAY_25': 'DAILY_SCADA_ENERGY_DAY_25',
 u'DAILY_SCADA_ENERGY_DAY_26': 'DAILY_SCADA_ENERGY_DAY_26',
 u'DAILY_SCADA_ENERGY_DAY_27': 'DAILY_SCADA_ENERGY_DAY_27',
 u'DAILY_SCADA_ENERGY_DAY_28': 'DAILY_SCADA_ENERGY_DAY_28',
 u'DAILY_SCADA_ENERGY_DAY_29': 'DAILY_SCADA_ENERGY_DAY_29',
 u'DAILY_SCADA_ENERGY_DAY_3': 'DAILY_SCADA_ENERGY_DAY_3',
 u'DAILY_SCADA_ENERGY_DAY_30': 'DAILY_SCADA_ENERGY_DAY_30',
 u'DAILY_SCADA_ENERGY_DAY_4': 'DAILY_SCADA_ENERGY_DAY_4',
 u'DAILY_SCADA_ENERGY_DAY_5': 'DAILY_SCADA_ENERGY_DAY_5',
 u'DAILY_SCADA_ENERGY_DAY_6': 'DAILY_SCADA_ENERGY_DAY_6',
 u'DAILY_SCADA_ENERGY_DAY_7': 'DAILY_SCADA_ENERGY_DAY_7',
 u'DAILY_SCADA_ENERGY_DAY_8': 'DAILY_SCADA_ENERGY_DAY_8',
 u'DAILY_SCADA_ENERGY_DAY_9': 'DAILY_SCADA_ENERGY_DAY_9',
 u'DAILY_YIELD': 'Todays Generation',
 u'DC_CURRENT': 'DC Current',
 u'DC_POWER': 'DC Power',
 u'DC_VOLTAGE': 'DC Voltage',
 u'DIGITAL_INPUT': 'DIGITAL_INPUT',
 u'FAULT_HIGH': 'FAULT_HIGH',
 u'FAULT_LOW': 'FAULT_LOW',
 u'FEEDIN_TIME': 'FEEDIN_TIME',
 u'HEAT_SINK_TEMPERATURE': 'Heat Sink Temperature',
 u'INSIDE_TEMPERATURE': 'Inside Temperature',
 u'INVERTER_LOADING': 'Inverter Loading',
 u'INVERTER_TIMESTAMP': 'Inverter Timestamp',
 u'IRRADIATION': 'Irradiation',
 u'MODULE_TEMPERATURE': 'Module Temperature',
 u'AMBIENT_TEMPERATURE': 'Ambient Temperature',
 u'WINDSPEED': 'Wind speed',
 u'WIND_DIRECTION': 'Wind Direction',
 u'LIVE': 'LIVE',
 u'MPPT1_DC_CURRENT': 'PV1 DC Current',
 u'MPPT1_DC_POWER': 'PV1 DC Power',
 u'MPPT1_DC_VOLTAGE': 'PV1 DC Voltage',
 u'MPPT2_DC_CURRENT': 'PV2 DC Current',
 u'MPPT2_DC_POWER': 'PV2 DC Power',
 u'MPPT2_DC_VOLTAGE': 'PV2 DC Voltage',
 u'MPPT3_DC_CURRENT': 'PV3 DC Current',
 u'MPPT3_DC_POWER': 'PV3 DC Power',
 u'MPPT3_DC_VOLTAGE': 'PV3 DC Voltage',
 u'MPPT4_DC_CURRENT': 'PV4 DC Current',
 u'MPPT4_DC_POWER': 'PV4 DC Power',
 u'MPPT4_DC_VOLTAGE': 'PV4 DC Voltage',
 u'MPPT5_DC_CURRENT': 'PV5 DC Current',
 u'MPPT5_DC_POWER': 'PV5 DC Power',
 u'MPPT5_DC_VOLTAGE': 'PV5 DC Voltage',
 u'OPERATING_TIME': 'Operating Time',
 u'PHASE_ANGLE': 'Phase Angle',
 u'POWER_FACTOR': 'Power Factor',
 u'POWER_SUPPLY_CURRENT': 'Power Supply Current',
 u'POWER_SUPPLY_VOLTAGE': 'Power Supply Voltage',
 u'POWER_SUPPLY_VOLTAGE_B': 'Power Supply Voltage B-Phase',
 u'POWER_SUPPLY_VOLTAGE_R': 'Power Supply Voltage R-Phase',
 u'POWER_SUPPLY_VOLTAGE_Y': 'Power Supply Voltage Y-Phase',
 u'REACTIVE_POWER': 'Reactive Power',
 u'REACTIVE_POWER_B': 'Reactive Power B-Phase',
 u'REACTIVE_POWER_R': 'Reactive Power R-Phase',
 u'REACTIVE_POWER_Y': 'Reactive Power Y-Phase',
 u'SOLAR_STATUS': 'Inverter Operational Status',
 u'SOLAR_STATUS_DESCRIPTION': 'Inverter Operational Status Description',
 u'SOLAR_STATUS_MESSAGE': 'Inverter Operational Status Message',
 u'TIMESTAMP': 'Timestamp',
 u'TOTAL_OPERATIONAL_HOURS': 'Total Operational Runime',
 u'TOTAL_YIELD': 'Total Generation',
 u'TEMPERATURE': 'TEMPERATURE',
 u'BATT_VOLTAGE': 'BATT_VOLTAGE',
 u'BATT_CURRENT': 'BATT_CURRENT',
 u'LOAD_CURRENT': 'LOAD_CURRENT'}

logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)

ORIENTATION_CHOICES = [('NORTH','NORTH'),
                       ('SOUTH','SOUTH'),
                       ('EAST','EAST'),
                       ('WEST','WEST'),
                       ('SOUTH-WEST','SOUTH-WEST'),
                       ('EAST-WEST','EAST-WEST')]

PVSYST_PARAMETERS =[ ('PRODUCED_ENERGY','PRODUCED_ENERGY'),
                     ('SPECIFIC_PRODUCTION', 'SPECIFIC_PRODUCTION'),
                     ('PERFORMANCE_RATIO' , 'PERFORMANCE_RATIO'),
                     ('NORMALISED_ENERGY_PER_DAY', 'NORMALISED_ENERGY_PER_DAY'),
                     ('TILT_ANGLE', 'TILT_ANGLE'),
                     ('GHI_IRRADIANCE','GHI_IRRADIANCE'),
                     ('IN_PLANE_IRRADIANCE','IN_PLANE_IRRADIANCE')]

PVSYST_TIME_PERIODS = [ ('MONTH', 'MONTH'),
                        ('YEAR', 'YEAR')]


AJB_STATUS_STREAMS_LIST = [('DI_STATUS_1', 'DI_STATUS_1'),
                           ('DI_STATUS_2', 'DI_STATUS_2'),
                           ('DI_STATUS_3', 'DI_STATUS_3'),
                           ('DI_STATUS_4', 'DI_STATUS_4'),
                           ('DI_STATUS_5', 'DI_STATUS_5'),
                           ('DO_STATUS_1', 'DO_STATUS_1'),
                           ('DO_STATUS_2', 'DO_STATUS_2')]

AJB_STATUS_STREAMS_DESCRIPTION_LIST = [('DI_STATUS_1_DESCRIPTION', 'DI_STATUS_1_DESCRIPTION'),
                                       ('DI_STATUS_2_DESCRIPTION', 'DI_STATUS_2_DESCRIPTION'),
                                       ('DI_STATUS_3_DESCRIPTION', 'DI_STATUS_3_DESCRIPTION'),
                                       ('DI_STATUS_4_DESCRIPTION', 'DI_STATUS_4_DESCRIPTION'),
                                       ('DI_STATUS_5_DESCRIPTION', 'DI_STATUS_5_DESCRIPTION'),
                                       ('DO_STATUS_1_DESCRIPTION', 'DO_STATUS_1_DESCRIPTION'),
                                       ('DO_STATUS_2_DESCRIPTION', 'DO_STATUS_2_DESCRIPTION')]

INVERTER_STATUS_STREAMS_LIST = [('SOLAR_STATUS','SOLAR_STATUS'),
                                ('INVERTER_FAILURE','INVERTER_FAILURE'),
                                ('ALARM_ACTIVE','ALARM_ACTIVE')]

INVERTER_STATUS_STREAMS_DESCRIPTION_LIST = [('SOLAR_STATUS_DESCRIPTION','SOLAR_STATUS_DESCRIPTION'),
                                            ('INVERTER_FAILURE_DESCRIPTION','INVERTER_FAILURE_DESCRIPTION'),
                                            ('ALARM_ACTIVE_DESCRIPTION','ALARM_ACTIVE_DESCRIPTION')]

METER_STATUS_STREAMS_LIST = [('CIRCUIT_BREAKER_STATUS1','CIRCUIT_BREAKER_STATUS1'),
                             ('CIRCUIT_BREAKER_STATUS2','CIRCUIT_BREAKER_STATUS2')]

METER_STATUS_STREAMS_DESCRIPTION_LIST = [('CIRCUIT_BREAKER_STATUS1_DESCRIPTION','CIRCUIT_BREAKER_STATUS1_DESCRIPTION'),
                                         ('CIRCUIT_BREAKER_STATUS2_DESCRIPTION','CIRCUIT_BREAKER_STATUS2_DESCRIPTION')]

TRANSFORMER_STATUS_STREAMS_LIST = [('OTI','OTI'),
                                   ('WTI','WTI')]

TRANSFORMER_STATUS_STREAMS_DESCRIPTION_LIST = [('OTI_DESCRIPTION','OTI_DESCRIPTION'),
                                               ('WTI_DESCRIPTION','WTI_DESCRIPTION')]


PVSYST_TIME_PERIOD_VALUES =[(0,' '),
                            ( 1 , 'JAN'),
                            ( 2 , 'FRB'),
                            ( 3 , 'MAR'),
                            ( 4, 'APR'),
                            ( 5, 'MAY'),
                            ( 6 , 'JUN'),
                            ( 7 , 'JUL'),
                            ( 8 , 'AUG'),
                            ( 9 , 'SEP'),
                            ( 10 , 'OCT'),
                            ( 11 , 'NOV'),
                            ( 12 , 'DEC')]

ENERGY_CALCULATION_DEVICES=[('PLANT_META','PLANT_META'),
                            ('INVERTER_ENERGY','INVERTER_ENERGY'),
                            ('INVERTER_POWER','INVERTER_POWER'),
                            ('ENERGY_METER','ENERGY_METER')]


ENERGY_CALCULATION_STREAMS = [('TOTAL_PLANT_ENERGY','TOTAL_PLANT_ENERGY'),
                              ('DAILY_PLANT_ENERGY','DAILY_PLANT_ENERGY'),
                              ('TOTAL_YIELD','TOTAL_YIELD'),
                              ('DAILY_YIELD','DAILY_YIELD'),
                              ('ACTIVE_POWER','ACTIVE_POWER'),
                              ('Wh_RECEIVED','Wh_RECEIVED'),
                              ('Wh_DELIVERED','Wh_DELIVERED'),
                              ('KWH','KWH'),
                              ('kWhT(I)','kWhT(I)'),
                              ('Wh_FINAL','Wh_FINAL')]

ENERGY_CALCULATION_STREAM_UNITS = [('kWh','kWh'),
                                   ('kW','kW'),
                                   ('MWH','MWH'),
                                   ('MW','MW'),
                                   ('Wh','Wh'),
                                   ('W','W')]

PLANT_TYPE = [('ROOFTOP','ROOFTOP'),
              ('UTILITY','UTILITY')]

INSTALLER_TYPE = [('EPC','EPC'),
                  ('IPP','IPP')]

GATEWAY_MANUFACTURERS = [('Webdyn','Webdyn'),
                         ('Soekris','Soekris'),
                         ('Atoll','Atoll'),
                         ('DelRemo','DelRemo'),
                         ('DataGlen','DataGlen')]

class SolarField(Field):
    displayName = models.CharField(max_length=100, blank=False)
    fieldType = models.CharField(max_length=20, choices=FIELD_CHOICES, blank=False)

    def update_display_name(self):
        if self.displayName == self.name:
            self.displayName = streams_mappings.get("%s" % self.name, "%s" % self.name)
            self.save()

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                stream_name = streams_mappings[str(self.name)]
                assert(stream_name != str(self.name))
                self.displayName = streams_mappings.get("%s" % self.name, "%s" % self.name)
            except:
                self.isActive = False
            if "IRRADIATION" in str(self.name):
                self.multiplicationFactor = 0.001
                self.streamDataUnit = "kW/m^2"
            elif "TEMPERATURE" in str(self.name):
                self.streamDataUnit = "C"
            elif "WINDSPEED" in str(self.name):
                self.streamDataUnit = "km/hr"

        super(SolarField, self).save(*args, **kwargs)

class SolarErrorField(ErrorField):
    displayName = models.CharField(max_length=100, blank=False)
    fieldType = models.CharField(max_length=20, choices=FIELD_CHOICES, blank=False)

# class InverterErrorField(ErrorField):
#     displayName = models.CharField(max_length=100, blank=False)
#     fieldType = models.CharField(max_length=20, choices=FIELD_CHOICES, blank=False)

# class AJBErrorField(ErrorField):
#     displayName = models.CharField(max_length=100, blank=False)
#     fieldType = models.CharField(max_length=20, choices=FIELD_CHOICES, blank=False)


def add_energy_meter_streams(energy_meter):
    for stream in ENERGY_METER_STREAMS:
        sf = SolarField(source=energy_meter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()
    for stream in METADATA_STATUS_PARAMETERS:
        sf = SolarField(source=energy_meter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()
    for stream in METADATA_INPUT_PATAMETERS:
        sf = SolarField(source=energy_meter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()
    for stream in ENERGY_METER_ERROR_STREAMS:
        ef = SolarErrorField(source=energy_meter, name=stream[0],
                            streamDataType=stream[1], displayName=stream[0], fieldType='ERROR')
        ef.save()

def add_transformers_streams(transformer):
    for stream in TRANSFORMER_STREAMS:
        sf = SolarField(source=transformer, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()
    for stream in METADATA_STATUS_PARAMETERS:
        sf = SolarField(source=transformer, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()
    for stream in TRANSFORMER_ERROR_STREAMS:
        ef = SolarErrorField(source=transformer, name=stream[0],
                            streamDataType=stream[1], displayName=stream[0], fieldType='ERROR')
        ef.save()

def add_metadata_streams(metasource):
    for stream in METADATA_STREAMS:
        try:
            sf = SolarField(source=metasource, name=stream[0],
                            streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
            sf.save()
            print sf
        except:
            continue

    for stream in METADATA_STATUS_PARAMETERS:
        try:
            sf = SolarField(source=metasource, name=stream[0],
                            streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
            sf.save()
        except:
            continue

    for stream in METADATA_INPUT_PATAMETERS:
        try:
            sf = SolarField(source=metasource, name=stream[0],
                            streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
            sf.save()
        except:
            continue

    for stream in PLANT_META_ERROR_FIELDS:
        try:
            ef = SolarErrorField(source=metasource, name=stream[0],
                                streamDataType=stream[1], displayName=stream[0], fieldType='ERROR')
            ef.save()
        except:
            continue


def add_inverter_streams(inverter):
    # add input parameters
    for stream in INPUT_PARAMETERS:
        sf = SolarField(source=inverter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()

    for stream in MPPT_INPUT_PARAMETERS:
        sf = SolarField(source=inverter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()

    for stream in OUTPUT_PARAMETERS:
        sf = SolarField(source=inverter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()

    for stream in STATUS_PARAMETERS:
        sf = SolarField(source=inverter, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()

    for stream in INVERTER_ERROR_FIELDS:
        ef = SolarErrorField(source=inverter, name=stream[0],
                                streamDataType=stream[1], displayName=stream[0], fieldType='ERROR')
        ef.save()

def add_weather_station_streams(weather_station):

    for stream in WEATHER_STATION_STREAMS:
        sf = SolarField(source=weather_station, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()

    for stream in WEATHER_STATION_STATUS_PARAMETERS:
        sf = SolarField(source=weather_station, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()

    for stream in WEATHER_STATION_INPUT_PATAMETERS:
        sf = SolarField(source=weather_station, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()

def add_solar_metrics_streams(solar_metrics):

    for stream in SOLAR_METRICS_STREAMS:
        sf = SolarField(source=solar_metrics, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()

    for stream in SOLAR_METRICS_STATUS_PARAMETERS:
        sf = SolarField(source=solar_metrics, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()

    for stream in SOLAR_METRICS_INPUT_PATAMETERS:
        sf = SolarField(source=solar_metrics, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()

def add_virtual_gateway_streams(virtual_gateway):
    # add input parameters
    for stream in VIRTUAL_GATEWAY_INPUT_PARAMETERS:
        sf = SolarField(source=virtual_gateway, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()

    for stream in VIRTUAL_GATEWAY_OUTPUT_PARAMETERS:
        sf = SolarField(source=virtual_gateway, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()

    for stream in VIRTUAL_GATEWAY_STATUS_PARAMETERS:
        sf = SolarField(source=virtual_gateway, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()

    for stream in VIRTUAL_GATEWAY_ERROR_FIELDS:
        ef = SolarErrorField(source=virtual_gateway, name=stream[0],
                                streamDataType=stream[1], displayName=stream[0], fieldType='ERROR')
        ef.save()


def add_gateway_streams(gateway):
    for stream in GATEWAY_STREAMS:
        sf = SolarField(source=gateway, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='OUTPUT')
        sf.save()
    for stream in GATEWAY_INPUT_PATAMETERS:
        sf = SolarField(source=gateway, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()


class SolarPlant(DataglenGroup):
    # in kW
    capacity = models.FloatField(blank=False, help_text="The capacity of the solar plant in KW")
    location = models.CharField(max_length=250, blank=False, help_text="The location of the plant (City, State)")

    # optional params
    latitude = models.FloatField(blank=True, null=True, help_text="The latitude coordinates of the plant location")
    longitude = models.FloatField(blank=True, null=True, help_text="The latitude coordinates of the plant location")

    commissioned_date = models.DateField(blank=True, null=True, help_text="The date the plant was commissioned")
    feed_in_tariff = models.FloatField(blank=True, null=True, help_text="The feed in tariff for solar energy")

    openweather = models.CharField(max_length=50, blank=False, default=None, help_text="The location to be sent to openweather for weather information")
    isOperational = models.BooleanField(blank=False, default=False, help_text="The boolean flag that indicates if the plant is operational at present.")

    # new plant parameters
    evacuation_point = models.FloatField(blank=True, null=True, help_text="The feed in tariff for solar energy")
    webdyn_device_id = models.CharField(max_length=100, blank=True, null=True, help_text="The gateway Id of webdyn")
    ac_capacity = models.FloatField(blank=True, null=True, help_text="The ac capacity of the solar plant in KW")
    elevation = models.FloatField(blank=True, null=True, help_text="The elevation of plant")
    intermediate_client = models.CharField(max_length=100, blank=True, null=True, help_text="Name of the intermediate client of the plant, apart from the main client.")

    def get_feeders(self):
        return self.feeder_units.all()

    def get_independent_inverters(self):
        return self.independent_inverter_units.all()

    def get_inverters(self):
        return self.inverter_units.all()

    def get_ajbs(self):
        return self.ajb_units.all()

    def save(self, *args, **kwargs):
        super(SolarPlant, self).save(*args, **kwargs)
        if self.id and len(self.o_and_m_preferences.all()) == 0:
            from oandmmanager.models import Preferences
            preference = Preferences.objects.create(plant=self)
            preference.save()

    def get_status_description_mapping(self, device_status_number):
        try:
            inverter_status_mapping = InverterStatusMappings.objects.get(plant=self,
                                                                         stream_name='SOLAR_STATUS',
                                                                         status_code=float(
                                                                             device_status_number))

            return inverter_status_mapping.status_description
        except:
            return None


    def add_or_update_or_clear_tags(self, tag_value):
        """

        :param flag:
        :param tag_value:
        :return:
        """
        if type(tag_value) is list:
            tag_value = ",".join(tag_value)
            Tag.objects.update_tags(self, "%s" % tag_value)
        elif type(tag_value) is str:
            Tag.objects.add_tag(self, '"%s"' % tag_value)
        elif tag_value is None:
            Tag.objects.update_tags(self, None)
        else:
            raise ValidationError("Not valid tag_value, Can only be list, str, None")

    def __unicode__(self):
        return self.slug


class Feeder(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="feeder_units")
    manufacturer = models.CharField(max_length=100, blank=False)
    displayName = models.CharField(max_length=100, blank=False)

    def get_inverters(self):
        return self.inverter_units.all()

    def save(self, *args, **kwargs):
        super(Feeder, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            for param in FEEDER_PARAMETERS:
                stream = SolarField(source=self, name=param[0], streamDataType=param[1],
                                    displayName=param[0], fieldType='INPUT')
                stream.save()


class EnergyMeter(Sensor):
    # strings are fields
    plant = models.ForeignKey(SolarPlant, related_name="energy_meters")
    manufacturer = models.CharField(max_length=100, blank=False)
    model = models.CharField(max_length=100, blank=True, null=True, help_text="Model of the weather Sensor")
    displayName = models.CharField(max_length=100, blank=False)
    modbus_address = models.CharField(max_length=100, blank=True, null=True, help_text="modbus address of inverter")
    energy_calculation = models.BooleanField(default=True, blank=False, null=False, help_text="whether this meter should be considered for energy calculation")

    def save(self, *args, **kwargs):
        self.templateName = settings.ENERGY_METER_TEMPLATE
        super(EnergyMeter, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_energy_meter_streams(self)

# Transformer Model
class Transformer(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="transformers")
    manufacturer = models.CharField(max_length=100, blank=False)
    displayName = models.CharField(max_length=100, blank=False)

    def save(self, *args, **kwargs):
        self.templateName = settings.TRANSFORMER_TEMPLATE
        super(Transformer, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_transformers_streams(self)

class IndependentInverter(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="independent_inverter_units")
    manufacturer = models.CharField(max_length=100, blank=False, help_text="Manufacturer name")
    model = models.CharField(max_length=100, blank=True, help_text="Model of the inverter")
    displayName = models.CharField(max_length=100, blank=False, help_text="The display name of the inverter end users")
    orientation = models.CharField(max_length=100, choices=ORIENTATION_CHOICES, blank=True, null=True, help_text="Direction of the inverter")
    total_capacity = models.FloatField(blank=True, null=True, help_text="Total capacity of the inverter")
    actual_capacity = models.FloatField(blank=True, null=True, help_text="Actual capacity of the inverter")
    energy_meter = models.ForeignKey(EnergyMeter, related_name="independent_inverter_units", blank=True, null=True)
    # new parameters
    no_of_strings = models.IntegerField(blank=True, null=True, help_text="No of strings for this inverter")
    string_capacity = models.FloatField(blank=True, null=True, help_text="capacity of every string")
    number_of_mppts = models.IntegerField(blank=True, null=True, help_text="No of mppt for this inverter")
    serial_number = models.CharField(max_length=100, blank=True, null=True,help_text="Manufacturer name")
    modbus_address = models.CharField(max_length=100, blank=True, null=True, help_text="modbus address of inverter")
    #tilt angle
    tilt_angle = models.FloatField(blank=True, null=True, help_text="Tilt Angle of inverter panels")
    compute_irradiance = models.BooleanField(blank=False, null=False, default=False, help_text='whether irradiace should be computed for this inverter using tilt angle')

    def clean(self):
        all_inverter = self.plant.independent_inverter_units.all()
        if self.pk:
            all_inverter = all_inverter.exclude(id=self.id)
        all_inverter_names = set(all_inverter.values_list('name', flat=True))
        if self.name in all_inverter_names:
            raise ValidationError("Duplicate inverter name of plant %s" % self.plant)

    def save(self, *args, **kwargs):
        self.clean()
        self.templateName = settings.INVERTER_TEMPLATE
        super(IndependentInverter, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_inverter_streams(self)

    def get_error_code_mapping(self, alarm_code):
        try:
            inv_error_codes = InverterErrorCodes.objects.filter(manufacturer__in=[self.manufacturer.upper(), self.manufacturer],
                                                                error_code=alarm_code)
            alarm_description = inv_error_codes[0].error_description
        except:
            alarm_description = "No error details available"
        return alarm_description


class MPPT(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="mppt_units")
    independent_inverter = models.ForeignKey(IndependentInverter, related_name="mppt_units", blank=True, null=True)
    order = models.IntegerField(blank=True, null=True, help_text="Order of the MPPT")

    def strings_per_mppt_function(self):
        return len(self.panels_strings.all())

    def total_panels(self):
        panels = 0
        for string in self.panels_strings.all():
            panels += string.number_of_panels
        return panels

    strings_per_mppt = models.IntegerField(blank=True, null=True, help_text="No of strings per mppt")
    modules_per_string = models.IntegerField(blank=True, null=True, help_text="No of modules per string")


class PanelsString(models.Model):
    name = models.CharField(blank=True, null=True, max_length=50, help_text="Name of the string")
    orientation = models.FloatField(blank=True, null=True, max_length=50, help_text="Orientation of the string")
    mppt = models.ForeignKey(MPPT, related_name="panels_strings")
    number_of_panels = models.IntegerField(blank=True, null=True, help_text="No of modules in this string")
    tilt_angle = models.FloatField(blank=True, null=True, help_text="Tilt angle of this string")


AIN = (1, 2, 3, 4, 5, 6, 7, 8)
AIN_OPTIONS = list(zip(AIN, AIN))

streams_types = ("IRRADIATION",
                 "AMBIENT_TEMPERATURE",
                 "MODULE_TEMPERATURE",
                 "WINDSPEED",
                 "WIND_DIRECTION")
streams_types_options = list(zip(streams_types, streams_types))



class PlantMetaSource(Sensor):
    plant = models.OneToOneField(SolarPlant, related_name="metadata")
    sending_aggregated_power = models.BooleanField(default=False)
    sending_aggregated_energy = models.BooleanField(default=False)
    energy_meter_installed = models.BooleanField(default=False)
    inverters_sending_daily_generation = models.BooleanField(default=True)
    inverters_sending_total_generation = models.BooleanField(default=False)
    meter_power = models.BooleanField(default=False)
    PV_panel_area = models.FloatField(blank=False, default=0, null=True, help_text="Total PV area of plant in m2")
    PV_panel_efficiency = models.FloatField(blank=True, default=0, null=True, help_text="Efficiency of the PV plant")

    panel_capacity=models.FloatField(null=True, blank=True, default=0, help_text="capacity of panel")
    panel_technology=models.CharField(max_length=100,null=True, blank=True, default=0, help_text="panel type Ex: monocrystalline, polycrystalline etc.")
    panel_manufacturer=models.CharField(max_length=100,null=True, blank=True, help_text="Manufacturer of panels")
    model_number=models.CharField(max_length=100, null=True, blank=True, help_text="model of panels")
    no_of_panels = models.IntegerField(null=True, blank=True, help_text="number of panels installed in the plant")
    ws_tilt_angle = models.FloatField(blank=True, null=True, help_text="Tilt Angle of Weather Station")

    operations_start_time = models.CharField(max_length=100, blank=False, default="06:30:00", help_text="Plant operations start time")
    operations_end_time = models.CharField(max_length=100, blank=False, default="18:30:00", help_text="Plant operations end time")
    calculate_hourly_pr = models.BooleanField(default=True, blank=False)
    tickets_enabled = models.BooleanField(blank=False, default=False)
    dc_loss_enabled = models.BooleanField(blank=False, default=False)
    conversion_loss_enabled = models.BooleanField(blank=False, default=True)
    ac_loss_enabled = models.BooleanField(blank=False, default=False)
    energy_from_power = models.BooleanField(blank=False, default=False)
    irradiation_data = models.BooleanField(blank=False, null=False, default=True, help_text="Are we getting the irradiation data")

    energy_calculation_device = models.CharField(max_length=100, blank=False, null=False, choices=ENERGY_CALCULATION_DEVICES, default='INVERTER_ENERGY', help_text='Device which should be used for energy calculation')
    energy_calculation_stream = models.CharField(max_length=100, blank=False, null=False, choices=ENERGY_CALCULATION_STREAMS, default='TOTAL_YIELD', help_text="Stream which should be used to get the data for energy calculation")
    energy_calculation_stream_unit = models.CharField(max_length=100, blank=False, null=False, choices=ENERGY_CALCULATION_STREAM_UNITS, default='kWH', help_text="Unit in which we are getting the data")

    # Adding this parameter for Apex AJB issue
    data_frequency = models.IntegerField(null=True, blank=True, help_text="Frequency at which we are getting the data")

    #plant type (ROOFTOP/UTILITY)
    plant_type = models.CharField(max_length=100, null=False, blank=False, default='ROOFTOP', choices=PLANT_TYPE, help_text="What kind of plant is it")

    #installer type (EPC/IPP)
    installer_type = models.CharField(max_length=100, null=False, blank=False, default='IPP', choices=INSTALLER_TYPE, help_text="What kind of installers are they")

    binning_interval = models.IntegerField(null=True, blank=True, help_text="binning interval in seconds.")
    gateway_manufacturer = models.CharField(max_length=50, null=False, blank=False, choices=GATEWAY_MANUFACTURERS, default='DataGlen', help_text="gateway provider")
    dsm_enabled = models.BooleanField(default=False, blank=False, null=False, help_text="Boolean parameter to determine if DSM tab should be enabled or not.")
    prediction_enabled = models.BooleanField(default=True, blank=False, null=False,
                                      help_text="Boolean parameter to determine if prediction needs to be run for this plant..")

    @transaction.atomic
    def add_sensor(self, group_name, device_id, ain_number, type, output_range,
                   lower_bound, upper_bound, tilt=None, orientation=None):
        try:
            # check for the type
            if type not in streams_types:
                raise ValidationError("A wrong type value passed")

            # find out if there's already a sensor with this AIN
            if len(self.io_sensors.filter(ain_number=ain_number,
                                          device_id=device_id)) > 0:
                print "inside validation error"
                raise ValidationError("A sensor with this AIN already exists")

            # find out existing mapping
            existing_sensors = self.io_sensors.filter(stream_type=type)

            # check if already have 4 sensors installed
            if len(existing_sensors) >= 4:
                raise ValidationError("Limit for the number of sensors for this type reached")

            # frame the associated stream name
            if len(existing_sensors) == 0:
                associated_stream_name = type
            else:
                associated_stream_name = type + "_" + str(len(existing_sensors) + 1)

            # get the associated stream
            stream = self.fields.get(name=associated_stream_name)
            # set it to True
            stream.isActive = True
            # save the stream
            stream.save()

            # update the displayName for solar_field
            sf = stream.solarfield
            sf.displayName = "-".join([group_name.replace("_", " ").title(),
                                       type.title(),
                                       str(device_id),
                                       "AIN",
                                       str(ain_number)])
            # save the solar stream
            sf.save()

            # save a new mapping for IOSensorField
            if tilt is not None and orientation is not None:
                mapping = IOSensorField.objects.create(plant_meta=self,
                                                       solar_field=sf,
                                                       device_id=device_id,
                                                       ain_number=ain_number,
                                                       stream_type=type,
                                                       tilt=tilt,
                                                       orientation=orientation,
                                                       output_range=output_range,
                                                       lower_bound=lower_bound,
                                                       upper_bound=upper_bound)
                mapping.save()
            # save a new mapping if there's no tilt/orientation
            else:
                mapping = IOSensorField.objects.create(plant_meta=self,
                                                       solar_field=sf,
                                                       device_id=device_id,
                                                       ain_number=ain_number,
                                                       stream_type=type,
                                                       output_range=output_range,
                                                       lower_bound=lower_bound,
                                                       upper_bound=upper_bound)
                mapping.save()

            # return this mapping to be stored in M2M solargroup
            return mapping
        except Exception as exc:
            raise ValidationError(str(exc))

    def save(self, *args, **kwargs):
        self.templateName = settings.PLANT_META_TEMPLATE
        super(PlantMetaSource, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_metadata_streams(self)


class IOSensorField(models.Model):
    plant_meta = models.ForeignKey(PlantMetaSource, related_name="io_sensors")
    # solar_field
    solar_field = models.ForeignKey(SolarField, related_name="sensor_field")
    # sensor device ID
    device_id = models.CharField(max_length=20, blank=False, null=False)
    # AIN number of the webdyn device
    ain_number = models.IntegerField(choices=AIN_OPTIONS, default=False, null=False)
    # associated stream type
    stream_type = models.CharField(choices=streams_types_options, max_length=50, default=False, null=False)
    # title angle, cannot be null if it's an irradiation sensor
    tilt = models.FloatField(blank=True, null=True, help_text="title angle")
    # orientation, cannot be null if it's an irradiation sensor
    orientation = models.FloatField(blank=True, null=True, help_text="sensor orientation")
    # output range, will be one of these two options always, will be there in the webdyn add request
    output_range = models.CharField(choices = [('4-20mA', '4-20mA'), ('0-10V', '0-10V')],
                                    max_length=20, blank=False, null=False,
                                    help_text="sensor range")
    # lower bound of the sensor, will be there in the webdyn add request
    lower_bound = models.FloatField(blank=False, null=False, help_text="lower bound")
    # upper bound of the sensor, will be there in the webdyn add request
    upper_bound = models.FloatField(blank=False, null=False, help_text="upper bound")


    def __unicode__(self):
        return ",".join([str(self.device_id),
                         str(self.ain_number),
                         str(self.stream_type),
                         str(self.solar_field.name)])

class GatewaySource(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="gateway")
    isVirtual =  models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.templateName = settings.GATEWAY_TEMPLATE
        if self.pk is None:
            self.timeoutInterval = 1800
        super(GatewaySource, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_gateway_streams(self)



# add any additional parameters in the models below as necessary
class Inverter(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="inverter_units")
    feeder = models.ForeignKey(Feeder, related_name="inverter_units")
    energy_meter = models.ForeignKey(EnergyMeter, related_name="inverter_units", blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=False)
    displayName = models.CharField(max_length=100, blank=False)

    def get_ajbs(self):
        return self.ajb_units.all()

    def save(self, *args, **kwargs):
        super(Inverter, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_inverter_streams(self)


# add any additional parameters in the models below as necessary
class AJB(Sensor):
    # strings are fields
    plant = models.ForeignKey(SolarPlant, related_name="ajb_units")
    inverter = models.ForeignKey(Inverter, related_name="ajb_units", blank=True, null=True)
    independent_inverter = models.ForeignKey(IndependentInverter, related_name="ajb_units", blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=False)
    displayName = models.CharField(max_length=100, blank=False)

    def save(self, *args, **kwargs):
        self.templateName = settings.AJB_TEMPLATE
        super(AJB, self).save(*args, **kwargs)
        # enforce the json format
        self.dataFormat = 'JSON'

        if len(self.fields.all()) == 0:
            strings = range(1, 26)
            temperatures = range(1, 4)
            # save the strings
            for string in STRINGS:
                field = SolarField(source=self, name=string, streamDataType="FLOAT",
                                   displayName=string, fieldType='INPUT')
                field.save()
            # save the temperature
            for temperature in TEMPERATURE_SENSORS:
                field = SolarField(source=self, name=temperature, streamDataType="FLOAT",
                                   displayName=temperature, fieldType='INPUT')
                field.save()

            for stream in OTHERS:
                field = SolarField(source=self, name=stream[0], streamDataType=stream[1],
                                   displayName=stream[0], fieldType='INPUT')
                field.save()

            for stream in AJB_ERROR_FIELDS:
                ef = SolarErrorField(source=self, name=stream[0],
                                    streamDataType=stream[1], displayName=stream[0], fieldType='ERROR')
                ef.save()



class SolarGroup(SensorGroup):
    groupAJBs = models.ManyToManyField(AJB, blank=True, null=True, related_name="solar_groups")
    groupInverters = models.ManyToManyField(Inverter, blank=True, null=True, related_name="solar_groups")
    groupIndependentInverters = models.ManyToManyField(IndependentInverter, blank=True, null=True, related_name="solar_groups")
    groupFeeders = models.ManyToManyField(Feeder, blank=True, null=True, related_name="solar_groups")
    groupEnergyMeters = models.ManyToManyField(EnergyMeter, blank=True, null=True, related_name="solar_groups")
    groupPlantMetaSources = models.ManyToManyField(PlantMetaSource, blank=True, null=True, related_name="solar_groups")
    groupGatewaySources = models.ManyToManyField(GatewaySource, blank=True, null=True, related_name="solar_groups")
    plant = models.ForeignKey(SolarPlant, related_name="solar_groups")
    groupIOSensors = models.ManyToManyField(IOSensorField, blank=True, null=True, related_name="solar_groups")
    # new parameters
    group_type = models.CharField(max_length=100, null=True, blank=True, help_text="Group type (Ex. Rooms/Roofs)")
    roof_type = models.CharField(max_length=100, null=True, blank=True, help_text="Roof Type")
    tilt_angle = models.FloatField(null=True, blank=True, help_text="Tilt angle")
    latitude = models.FloatField(blank=True, null=True, help_text="The latitude coordinates of the group/roof")
    longitude = models.FloatField(blank=True, null=True, help_text="The longitude coordinates of the group/roof")
    azimuth = models.CharField(max_length=100, null=True, blank=True, help_text="orientation of the panels")

    panel_manufacturer = models.CharField(max_length=100, null=True, blank=True, help_text="panel manufacturer")
    panel_capacity = models.FloatField(null=True, blank=True, help_text="capacity of the group")
    no_of_panels = models.IntegerField(null=True, blank=True, help_text="number of panels")
    PV_panel_area = models.FloatField(blank=False, default=0, null=True, help_text="Total PV area of group/roof in m2")
    PV_panel_efficiency = models.FloatField(blank=True, default=0, null=True, help_text="Efficiency of the PV plant")
    data_logger_device_id = models.CharField(max_length=100, blank=True, null=True, help_text="The gateway Id of data logger")

    def get_inverters(self):
        return self.groupInverters.all()
    def get_ajbs(self):
        return self.groupAJBs.all()
    def get_independent_inverters(self):
        return self.groupIndependentInverters.all()
    def get_feeders(self):
        return self.groupFeeders.all()
    def get_energy_meters(self):
        return self.groupEnergyMeters.all()
    def get_plant_meta_sources(self):
        return self.groupPlantMetaSources.all()
    def get_gateway_sources(self):
        return self.groupGatewaySources.all()

    @property
    def varchar_id(self):
        return "solar_group_%s" % self.id


class SolarSection(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False)
    plant = models.ForeignKey(SolarPlant, blank=False, null=False, related_name="solar_section")
    solar_groups = models.ManyToManyField(SolarGroup, blank=True, null=True, related_name="solar_section")

    def __unicode__(self):
        return self.name + "_" + self.plant.slug

class VirtualGateway(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="virtual_gateway_units")
    solar_group = models.ForeignKey(SolarGroup, related_name="group_virtual_gateway_units", blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=False)
    displayName = models.CharField(max_length=100, blank=False, help_text="The display name of the virtual gateway")

    def save(self, *args, **kwargs):
        self.templateName = settings.WEBDYN_TEMPLATE
        super(VirtualGateway, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_virtual_gateway_streams(self)


class EnergyGenerationTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/inverter_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # energy value
    energy = columns.Float()


class PlantPowerTable(Model):
    plant_slug = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # energy value
    power = columns.Float()


class PerformanceRatioTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    performance_ratio = columns.Float()
    # Average External Irradiation
    irradiation = columns.Float()
    #count of solar irradiation
    count = columns.Integer()
    #total sum of irradiation values
    sum_irradiation = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class PlantAggregatedInfo(Model):
    identifier = columns.Text(partition_key=True, primary_key=True)
    #plant slug
    stream_name = columns.Text(partition_key=True, primary_key=True)
    #ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # ts as a key
    window_st_ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    window_et_ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    stream_value = columns.Float()
    update_time = columns.DateTime()

class PlantEquipmentData(Model):
    identifier = columns.Text(partition_key=True, primary_key=True)
    stream_name = columns.Text(partition_key=True, primary_key=True)
    #plant slug
    #ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # ts as a key
    window_st_ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    window_et_ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    stream_value = columns.Text()
    update_time = columns.DateTime()


class PerformanceRatioTableSpark(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    performance_ratio = columns.Float()
    # Average External Irradiation
    irradiation = columns.Float()
    #count of solar irradiation
    count = columns.Integer()
    #total sum of irradiation values
    sum_irradiation = columns.Float()
    #last updated time
    updated_at = columns.DateTime()


class CUFTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    CUF = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class CUFTableSpark(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    CUF = columns.Float()
    #last updated time
    updated_at = columns.DateTime()


class PerformanceRatioTableTemp(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    performance_ratio = columns.Float()
    # Average External Irradiation
    irradiation = columns.Float()
    #count of solar irradiation
    count = columns.Integer()
    #total sum of irradiation values
    sum_irradiation = columns.Float()
    #last updated time
    updated_at = columns.DateTime()



class InverterErrorCodes(models.Model):
    # manufacturer of the inverter
    manufacturer = models.CharField(max_length=128, blank=False, help_text="Manufacturer of the inverter")
    #model of the inverter
    model = models.CharField(max_length=128, blank=False, help_text="Model of the inverter")
    # Error Codes
    error_code = models.FloatField(blank=False, help_text="Error Code")
    # Error Description
    error_description = models.CharField(max_length=256, blank=True, null=True, help_text="Error Description")
    #default severity
    default_severity = models.CharField(max_length=256, blank=True, null=True, help_text="Severity of the error")
    #special notes
    notes = models.CharField(max_length=256, blank=True, null=True, help_text="notes about the error")
    grid_down = models.BooleanField(default=False)

    def __unicode__(self):
        return "_".join([self.manufacturer, self.model, str(self.error_code)])

    class Meta:
        unique_together = (("manufacturer", "model", "error_code"),)

class InverterStatusMappings(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="solar_status")
    stream_name = models.CharField(choices=INVERTER_STATUS_STREAMS_LIST, max_length=100, blank=False, null=False)
    status_code = models.FloatField(blank=False, null=False)
    status_description = models.CharField(max_length=256, blank=False, null=False)
    description_stream_name = models.CharField(choices=INVERTER_STATUS_STREAMS_DESCRIPTION_LIST, max_length=100, blank=False, null=False)
    generating = models.BooleanField(default=False)
    dual_status = models.BooleanField(default=False)
    grid_down = models.BooleanField(default=False)

    def __unicode__(self):
        return "_".join([str(self.plant.slug), str(self.stream_name), str(self.status_code)])

    class Meta:
        unique_together = (("plant", "stream_name", "status_code"),)

class MeterStatusMappings(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="meter_status")
    stream_name = models.CharField(choices=METER_STATUS_STREAMS_LIST, max_length=100, blank=False, null=False)
    status_code = models.FloatField(blank=False, null=False)
    status_description = models.CharField(max_length=256, blank=False, null=False)
    description_stream_name = models.CharField(choices=METER_STATUS_STREAMS_DESCRIPTION_LIST, max_length=100, blank=False, null=False)

    def __unicode__(self):
        return "_".join([str(self.plant.slug), str(self.stream_name), str(self.status_code)])

    class Meta:
        unique_together = (("plant", "stream_name", "status_code"),)

class TransformerStatusMappings(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="transformer_status")
    stream_name = models.CharField(choices=TRANSFORMER_STATUS_STREAMS_LIST, max_length=100, blank=False, null=False)
    status_code = models.FloatField(blank=False, null=False)
    status_description = models.CharField(max_length=256, blank=False, null=False)
    description_stream_name = models.CharField(choices=TRANSFORMER_STATUS_STREAMS_DESCRIPTION_LIST, max_length=100, blank=False, null=False)

    def __unicode__(self):
        return "_".join([str(self.plant.slug), str(self.stream_name), str(self.status_code)])

    class Meta:
        unique_together = (("plant", "stream_name", "status_code"),)

class AJBStatusMappings(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="ajb_status")
    stream_name = models.CharField(choices=AJB_STATUS_STREAMS_LIST, max_length=100, blank=False, null=False)
    status_code = models.FloatField(blank=False, null=False)
    status_description = models.CharField(max_length=256, blank=False, null=False)
    description_stream_name = models.CharField(choices=AJB_STATUS_STREAMS_DESCRIPTION_LIST, max_length=100, blank=False, null=False)

    def __unicode__(self):
        return "_".join([str(self.plant.slug), str(self.stream_name), str(self.status_code)])

    class Meta:
        unique_together = (("plant", "stream_name",  "status_code"),)

class HistoricEnergyValues(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (DAy/MONTH/YEAR)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/inverter_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # energy value
    energy = columns.Float()

class HistoricEnergyValuesWithPrediction(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (DAy/MONTH/YEAR)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/inverter_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # energy value
    energy = columns.Float()
    # predicted energy value
    predicted_energy = columns.Float()
    # lower bound of prediction
    lower_bound = columns.Float()
    # upper bound of prediction
    upper_bound = columns.Float()

'''
class HistoricProcessedEnergyValues(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (DAy/MONTH/YEAR/HOUR/15 MIN)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/inverter_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # energy value
    energy = columns.Float()
    noisy = columns.Boolean()
    missing_autofilled = columns.Boolean()
    samples = columns.Integer()
    '''

class PVSystInfo(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="pvsyst_info")
    solar_group = models.ForeignKey(SolarGroup, blank=True, null=True, related_name="group_pvsyst")
    parameterName = models.CharField(max_length=100, choices=PVSYST_PARAMETERS, blank=True, null=True)
    timePeriodType = models.CharField(max_length=100, choices=PVSYST_TIME_PERIODS, blank=True, null=True, help_text="Time period for the parameter value such as MONTH/YEAR")
    timePeriodDay = models.IntegerField(default = 0, blank=True, null=True, help_text="Year for which the pvsyst value is specified.")
    timePeriodValue = models.IntegerField(choices=PVSYST_TIME_PERIOD_VALUES, blank=True, null=True, help_text="Time period value such specific month name")
    timePeriodYear = models.IntegerField(default = 0, blank=True, null=True, help_text="Year for which the pvsyst value is specified.")
    parameterValue = models.FloatField(blank=True, default=0, null=True, help_text="PVSyst parameter value")
    unit = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.plant.slug + "_" + self.parameterName + "_" + str(self.timePeriodType) + "_" + str(self.timePeriodDay) + "_" + str(self.timePeriodValue) + "_" + str(self.timePeriodYear)

    class Meta:
        unique_together = (("plant", "solar_group", "parameterName" , "timePeriodType", "timePeriodDay", "timePeriodValue", "timePeriodYear"),)


class WeatherStation(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="weather_stations")
    manufacturer = models.CharField(max_length=100, blank=True, null=True, help_text="Manufacturer name")
    model = models.CharField(max_length=100, blank=True, null=True, help_text="Model of the weather Sensor")
    displayName = models.CharField(max_length=100, blank=False, help_text="The display name of the weather sensor")
    solar_groups = models.ManyToManyField(SolarGroup, blank=True, null=True, related_name="weather_stations")

    def save(self, *args, **kwargs):
        self.templateName = settings.WEATHER_STATION_TEMPLATE
        super(WeatherStation, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_weather_station_streams(self)

class SolarMetrics(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="solar_metrics")
    displayName = models.CharField(max_length=100, blank=False, help_text="The display name of the solar metric")
    solar_group = models.ForeignKey(SolarGroup, blank=True, null=True, related_name="solar_metrics")

    def save(self, *args, **kwargs):
        self.templateName = settings.SOLAR_METRICS_TEMPLATE
        super(SolarMetrics, self).save(*args, **kwargs)
        if len(self.fields.all()) == 0:
            add_solar_metrics_streams(self)


class EnergyLossTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # dc energy from ajb
    dc_energy_ajb = columns.Float()
    # dc energy from inverters
    dc_energy_inverters = columns.Float()
    # ac energy of inverters from active power
    ac_energy_inverters_ap = columns.Float()
    # ac energy from inverters total yield
    ac_energy_inverters = columns.Float()
    # ac energy from meters
    ac_energy_meters = columns.Float()
    # dc energy loss
    dc_energy_loss = columns.Float()
    # conversion loss
    conversion_loss = columns.Float()
    # ac energy loss
    ac_energy_loss = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class EnergyLossTableNew(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # dc energy from ajb
    dc_energy_ajb = columns.Float()
    # dc energy from inverters taking common points of AJB DC Power and Inverter DC Power
    dc_energy_inverters_ajb = columns.Float()
    # dc energy from inverters taking common points of Inverter Active Power and DC Power
    dc_energy_inverters = columns.Float()
    # ac energy of inverters from active power
    ac_energy_inverters_ap = columns.Float()
    # ac energy from inverters total yield
    ac_energy_inverters = columns.Float()
    # ac energy from meters
    ac_energy_meters = columns.Float()
    # dc energy loss
    dc_energy_loss = columns.Float()
    # conversion loss
    conversion_loss = columns.Float()
    # ac energy loss
    ac_energy_loss = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class PlantDownTime(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # down time in minutes
    down_time = columns.Float()
    #last updated time
    updated_at = columns.DateTime()


class PlantCompleteValues(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (DAy/MONTH/YEAR)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/inverter_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    #plant name
    name = columns.Text()
    # plant capacity
    capacity = columns.Float()
    # plant location
    location = columns.Text()
    # latitude
    latitude = columns.Float()
    # longitude
    longitude = columns.Float()
    # performance ratio
    pr = columns.Float()
    #CUF
    cuf = columns.Float()
    #grid unavailability
    grid_unavailability = columns.Float()
    #equipment unavailability
    equipment_unavailability = columns.Float()
    #unacknowlwdged tickets
    unacknowledged_tickets = columns.Integer()
    #open tickets
    open_tickets = columns.Integer()
    #closed tickets
    closed_tickets = columns.Integer()
    #total generation
    total_generation = columns.Float()
    # today's generation
    plant_generation_today = columns.Float()
    #co2 savings
    co2_savings = columns.Float()
    # active power
    active_power = columns.Float()
    #irradiation
    irradiation = columns.Float()
    # inverters_connected
    connected_inverters = columns.Integer()
    # disconnected inverters
    disconnected_inverters = columns.Integer()
    # inverters sending invalid data
    invalid_inverters = columns.Integer()
    # connected smb's
    connected_smbs = columns.Integer()
    # disconnected smbs
    disconnected_smbs = columns.Integer()
    # inverters sending invalid data
    invalid_smbs = columns.Integer()
    # plant conection status
    status = columns.Text()
    # wind speed
    windspeed = columns.Float()
    # Ambient Temperature
    ambient_temperature = columns.Float()
    # Module Temperature
    module_temperature = columns.Float()
    # DC loss
    dc_loss = columns.Float()
    # Conversion loss
    conversion_loss = columns.Float()
    # AC loss
    ac_loss = columns.Float()
    #last updated time
    updated_at = columns.DateTime()
    # last 7 days generation
    past_generations = columns.Text()
    # last 7 days PR
    past_pr = columns.Text()
    #last 7 days cuf
    past_cuf = columns.Text()
    #last 7 days grid unavailability
    past_grid_unavailability = columns.Text()
    #last 7 days equipment unavailability
    past_equipment_unavailability = columns.Text()
    #last 7 days DC loss
    past_dc_loss = columns.Text()
    #last 7 dys conversion loss
    past_conversion_loss = columns.Text()
    #last 7 days AC loss
    past_ac_loss = columns.Text()


class PredictedValues(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # stream for which the value is predicted
    stream_name = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # predicted value
    predicted_value = columns.Float()
    # actual value
    actual_value = columns.Float()
    # actual - predicted. This gives mean of residuals across multiple days
    residual = columns.Float()
    # residual value which does not get updated, once the training data change.
    today_residual = columns.Float()
    #residual sum gives the sum of residuals across all hours of the day
    residual_sum = columns.Float()
    #cleaning losses per day computed w.r.t. a benchmark value of the cleaning day
    losses = columns.Float()
    # models name :e.g. STATISTICAL_DAY_AHEAD, STATISTICAL_LATEST, ACTUAL_VALUE regression, etc
    model_name = columns.Text()
    #last updated time
    updated_at = columns.DateTime()


class PredictionData(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # stream for which the value is predicted
    stream_name = columns.Text(partition_key=True, primary_key=True)
    # models name :e.g. STATISTICAL_DAY_AHEAD, STATISTICAL_LATEST, ACTUAL_VALUE regression, etc
    model_name = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # predicted value
    value = columns.Float()
    #prediction upper bound value
    upper_bound = columns.Float()
    lower_bound = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class NewPredictionData(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # Identifier type (PLANT/SOURCE)
    identifier_type = columns.Text(partition_key=True, primary_key=True)
    # Plant Slug
    plant_slug = columns.Text(partition_key=False, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=False, primary_key=True)
    # stream for which the value is predicted
    stream_name = columns.Text(partition_key=False, primary_key=True)
    # models name :e.g. STATISTICAL_DAY_AHEAD, STATISTICAL_LATEST, ACTUAL_VALUE regression, etc
    model_name = columns.Text(partition_key=False, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # predicted value
    value = columns.Float()
    #prediction upper bound value
    upper_bound = columns.Float()
    lower_bound = columns.Float()
    #last updated time
    updated_at = columns.DateTime()


class PlantSummaryDetails(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK/MONTHLY/YEARLY)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    #plant generation
    generation = columns.Float()
    #estimated generation
    estimated_generation = columns.Float()
    #curtailment loss (Estimated - Actual)
    curtailment_loss = columns.Float()
    #plant PR
    performance_ratio = columns.Float()
    #plant CUF
    cuf = columns.Float()
    #plant AC CUF
    ac_cuf = columns.Float()
    # specific yield
    specific_yield = columns.Float()
    # plant DC loss
    dc_loss = columns.Float()
    #plant conversion loss
    conversion_loss = columns.Float()
    #plant AC loss
    ac_loss = columns.Float()
    #grid availability
    grid_availability = columns.Float()
    #equipment availability
    equipment_availability = columns.Float()
    #average irradiation
    average_irradiation = columns.Float()
    # average inclined irradiation
    average_inclined_irradiation = columns.Float()
    # average module temperature
    average_module_temperature = columns.Float()
    # average ambient temperature
    average_ambient_temperature = columns.Float()
    # average wind speed
    average_wind_speed = columns.Float()
    #open tickets
    open_tickets = columns.Integer()
    #unacknowledged tickets
    unknowledged_tickets = columns.Integer()
    #closed tickets
    closed_tickets = columns.Integer()
    # maximum irradiation
    max_irradiance = columns.Float()
    # total generation from inverters
    inverter_generation = columns.Float()
    # estimated GHI
    estimated_ghi = columns.Float()
    #total cumulative energy
    total_cumulative_energy = columns.Float()
    # plant start time
    plant_start_time = columns.Text()
    # plant stop time
    plant_stop_time = columns.Text()
    # plant run time
    plant_run_time = columns.Text()
    #last updated time
    updated_at = columns.DateTime()

class PlantDeviceSummaryDetails(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK/MONTHLY/YEARLY)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    #plant generation
    generation = columns.Float()
    # estimated generation
    estimated_generation = columns.Float()
    #curtailment loss
    curtailment_loss = columns.Float()
    #plant PR
    performance_ratio = columns.Float()
    #plant CUF
    cuf = columns.Float()
    # specific yield
    specific_yield = columns.Float()
    # plant DC loss
    dc_loss = columns.Float()
    #plant conversion loss
    conversion_loss = columns.Float()
    #plant AC loss
    ac_loss = columns.Float()
    # total working hours
    total_working_hours = columns.Float()
    # maximum dc power of inverter
    max_dc_power = columns.Float()
    # maximum active power of inverter
    max_ac_power = columns.Float()
    #total cumulative energy
    total_cumulative_energy = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

# table to store max values at plant and inverter level
class MaxValuesTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK/MONTHLY/YEARLY)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # maximum irradiation
    max_irradiance = columns.Float()
    # inverters generation
    inverters_generation = columns.Float()
    # maximum dc power of inverter
    max_dc_power = columns.Float()
    # maximum active power of inverter
    max_ac_power = columns.Float()
    #last updated time
    updated_at = columns.DateTime()


class KWHPerMeterSquare(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    value = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class KWHPerMeterSquareSpark(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    value = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class AggregatedPlantParameters(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # average ambient temperature
    average_ambient_temperature = columns.Float()
    # average module temperature
    average_module_temperature = columns.Float()
    # average wind speed
    average_windspeed = columns.Float()
    # Inclined Irradiation
    inclined_irradiation = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class SpecificYieldTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    specific_yield = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class SpecificYieldTableSpark(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    specific_yield = columns.Float()
    #last updated time
    updated_at = columns.DateTime()

class PlantContractDetails(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="contract_details")
    contract_date = models.DateField(null=True, blank=True, help_text="Date on which the contract was awarded.")
    loi_date = models.DateField(null=True, blank=True, help_text="Date of LOI")
    ppa_date = models.DateField(null=True, blank=True, help_text="Date of PPA signing")
    commissioning_date = models.DateField(null=True, blank=True, help_text="Date of Commissioning")
    contract_number = models.CharField(max_length=100, null=True, blank=True, help_text="contract number")
    contract_release_date = models.DateField(null=True, blank=True, help_text="Date of Contract Release")
    current_utility_tariff = models.FloatField(null=True, blank=True, help_text="Current Utility Tariff")
    current_solar_tarrif = models.FloatField(null=True, blank=True, help_text="Current solar Tariff")
    differential_pricing = models.FloatField(null=True, blank=True, help_text="Differential Pricing")
    ppa_pricing = models.FloatField(blank=True, null=True, help_text="PPA price for showing economic benefits")
    pricing_model = models.CharField(max_length=100, blank=True, null=True, help_text="capex / opex")
    total_investment = models.FloatField(null=True, blank=True, help_text="Total investement in project")

    def __unicode__(self):
        return self.plant.slug


class PlantFeaturesEnable(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="features_enabled")
    solar_metrics = models.BooleanField(default=True, help_text="Boolean parameter to determine, if the solar metrics should be shown or not.")
    economic_benefits = models.BooleanField(default=False, help_text="Boolean parameter to determine, if the economic benefits should be shown or not.")
    analytics = models.BooleanField(default=False, help_text="Boolean parameter to determine, if analytics should be shown or not.")
    alerts = models.BooleanField(default=False, help_text="Boolean parameter to determine if the alarms/alerts should be shown or not")
    reports = models.BooleanField(default=True, help_text="Boolean parameter to determine if the reports should be shown or not")
    timeseries = models.BooleanField(default=True, help_text="Boolean parameter to determine if the timeseries data should be shown")

    def __unicode__(self):
        return self.plant.slug


class ClientContentsEnable(models.Model):
    client = models.ForeignKey(DataglenClient, related_name="contents_enabled")
    contents = JSONField()

    def __unicode__(self):
        return self.client.slug


# Model to store the weather data from third party API's
class WeatherData(Model):

    CURRENT = 'current'
    FUTURE = 'future'
    HOURLY = 'hourly'
    DAILY = 'daily'

    api_source = columns.Text(partition_key=True, primary_key=True)
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    identifier = columns.Text(partition_key=True, primary_key=True)
    prediction_type = columns.Text(default=CURRENT, partition_key=False, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True)
    city = columns.Text()
    latitude = columns.Float()
    longitude = columns.Float()
    sunrise = columns.DateTime()
    sunset = columns.DateTime()
    cloudcover = columns.Float()
    humidity = columns.Float()
    windspeed = columns.Float()
    precipMM = columns.Float()
    updated_at = columns.DateTime()
    chanceofrain = columns.Float()
    ghi = columns.Float()
    ghi_10 = columns.Float()
    ghi_90 = columns.Float()
    dni = columns.Float()
    dni_10 = columns.Float()
    dni_90 = columns.Float()
    dhi = columns.Float()
    air_temp = columns.Float()


#Temporary Model to copy the data of WeatherData model
class WeatherDataTemp(Model):
    api_source = columns.Text(partition_key=True, primary_key=True)
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    identifier = columns.Text(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True)
    city = columns.Text()
    latitude = columns.Float()
    longitude = columns.Float()
    sunrise = columns.DateTime()
    sunset = columns.DateTime()
    cloudcover = columns.Float()
    humidity = columns.Float()
    windspeed = columns.Float()
    precipMM = columns.Float()


class AggregatedIndependentInverter(Sensor):
    plant = models.ForeignKey(SolarPlant, related_name="aggregated_inverter_units", related_query_name="aggregated_inverter_units")
    aggregated_independent_inverters = models.ManyToManyField(IndependentInverter, blank=True, null=True, related_name="aggregated_inverter_units")


class ScadaDailyEnergyTable(Model):
    # settings.TIMESTAMP_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS (HOUR/DAILY/WEEK)
    count_time_period = columns.Integer(partition_key=True, primary_key=True)
    # Estimated/Actual
    energy_type = columns.Text(partition_key=True, primary_key=True)
    # plant_slug/plant_meta_key
    identifier = columns.Text(partition_key=True, primary_key=True)
    # ts as a key
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    # performance ratio
    energy = columns.Float()
    #last updated time
    updated_at = columns.DateTime()


def add_wms_streams(wmssource):
    for stream in WMS_STREAMS:
        if stream[0] in ["IRRADIATION", "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "WINDSPEED", "WIND_DIRECTION"]:
            active = False
        else:
            active = False
            # keep both False as of now, active = True
        sf = SolarField(source=wmssource, name=stream[0], isActive=active,
                        streamDataType=stream[1], displayName=stream[0].replace("_", " ").title(), fieldType='OUTPUT')
        sf.save()

    for stream in WMS_STATUS_PARAMETERS:
        sf = SolarField(source=wmssource, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='STATUS')
        sf.save()

    for stream in WMS_INPUT_PARAMETERS:
        sf = SolarField(source=wmssource, name=stream[0],
                        streamDataType=stream[1], displayName=stream[0], fieldType='INPUT')
        sf.save()


PVWATT_PARAMETERS = [('AC_ANNUAL','AC_ANNUAL'),
                     ('SOLRAD_ANNUAL', 'SOLRAD_ANNUAL'),
                     ('CAPACITY_FACTOR' , 'CAPACITY_FACTOR'),
                     ('AC_MONTHLY', 'AC_MONTHLY'),
                     ('DC_MONTHLY', 'DC_MONTHLY'),
                     ('SOLRAD_MONTHLY','SOLRAD_MONTHLY'),
                     ('POA_MONTHLY','POA_MONTHLY')]

PVWATT_TIME_PERIODS = [('MONTH', 'MONTH'),
                        ('YEAR', 'YEAR')]

PVWATT_TIME_PERIOD_VALUES = [(0,' '), (1, 'JAN'), (2, 'FRB'), (3, 'MAR'), (4, 'APR'), (5, 'MAY'), (6, 'JUN'),
                             (7, 'JUL'), (8, 'AUG'), (9, 'SEP'), (10, 'OCT'), (11, 'NOV'), (12, 'DEC')]


class PVWatt(models.Model):
    plant = models.ForeignKey(SolarPlant, related_name="pvwatt_plants")
    solar_group = models.ForeignKey(SolarGroup, blank=True, null=True, related_name="pvwatt_groups")
    parameter_name = models.CharField(max_length=100, choices=PVWATT_PARAMETERS, blank=True, null=True)
    time_period_type = models.CharField(max_length=100, choices=PVWATT_TIME_PERIODS, blank=True, null=True,
                                      help_text="Time period for the parameter value such as MONTH/YEAR")
    time_period_year_number = models.IntegerField(default = 0, blank=True, null=True,
                                        help_text="Year for which the pvwatt value is specified.")
    time_period_month_number = models.IntegerField(choices=PVWATT_TIME_PERIOD_VALUES, blank=True, null=True,
                                          help_text="Time period value such specific month name")
    parameter_value = models.FloatField(blank=True, default=0, null=True, help_text="pvwatt parameter value")
    unit = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return "%s_%s_%s_%s_%s" % \
               (self.plant.slug, self.parameter_name, self.time_period_type, self.time_period_year_number,
                self.time_period_month_number)

    class Meta:
        unique_together = (("plant", "solar_group", "parameter_name" , "time_period_type",
                            "time_period_year_number", "time_period_month_number"),)


CLEANING_PRESENT_STATE = (('open', 'OPEN'), ('in_process', 'IN PROCESS'), ('finished', 'FINISHED'))
TRIGGER_TYPE = (('cool', 'COOLING'), ('clean', 'CLEANING'))

class CleaningTrigger(models.Model):

    ajb = models.ForeignKey(AJB, related_name="ajb_trigger")
    string_name = models.CharField(max_length=100, null=False, blank=False)
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE, null=False, blank=False)
    present_state = models.CharField(max_length=20, choices=CLEANING_PRESENT_STATE, null=False, blank=False)
    submitted_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(User, related_name="trigger_submitted_by")

    def __unicode__(self):
        return "%s_%s_%s_%s_%s" %(self.ajb, self.string_name, self.trigger_type, self.present_state, self.submitted_by)


# register an Url model for tagging
tagging_register(SolarPlant)

# clients = DataglenClient.objects.all()
# data = []
# for client in clients:
#     for group in client.dataglen_groups.all():
#         if hasattr(group, "solarplant"):
#             plant = group.solarplant
#             latest_ts = None
#             last_ts = None
#             try:
#                 inv = plant.independent_inverter_units.all()[0]
#                 line = "#".join([str(client.name), str(plant.name),
#                                  str(plant.latitude), str(plant.longitude) ,
#                                  str(plant.capacity), str(plant.ac_capacity),
#                                  str(inv.get_last_write_ts(['ACTIVE_POWER'], True).date()),
#                                  str(inv.get_last_write_ts(['ACTIVE_POWER'], False).date()),
#                                  str(plant.independent_inverter_units.count()),
#                                  str(plant.independent_inverter_units.all()[0].manufacturer)])
#                 print line
#                 data.append(line)
#             except:
#                 continue
#

# clients = DataglenClient.objects.all()
# data = []
# for client in clients:
#     for group in client.dataglen_groups.all():
#         if hasattr(group, "solarplant"):
#             plant = group.solarplant
#             ts_last = None
#             try:
#                 pm = plant.metadata
#                 line = "#".join([str(client.name), str(plant.name), str(plant.latitude), str(plant.longitude),
#                                  str(plant.capacity), str(plant.ac_capacity),
#                                  str(pm.get_last_write_ts(['IRRADIATION'], True).date()),
#                                  str(pm.get_last_write_ts(['IRRADIATION'], False).date())])
#                 print line
#                 data.append(line)
#             except Exception as exc:
#                 continue
#
#
# import datetime, time
# from solarrms.models import *
# plant = SolarPlant.objects.get(slug="amitymumbai")
# fd = open("./cron_output.txt", "w")
# fd.close()
# while True:
#     data = PlantSummaryDetails.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
#                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
#                                               identifier=str(plant.slug)).limit(1)
#     for entry in data:
#         print ",".join([str(entry.ts), str(entry.generation), str(entry.inverter_generation)])
#         fd = open("./cron_output.txt", "a")
#         fd.write(",".join([str(entry.ts), str(entry.generation), str(entry.inverter_generation)]))
#         fd.write("\n")
#         fd.close()
#     time.sleep(15*60)

