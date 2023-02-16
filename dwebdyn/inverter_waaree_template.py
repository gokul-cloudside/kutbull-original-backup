import sys, logging, dateutil
from solarrms.models import InverterStatusMappings, streams_mappings

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

#Inverters

plant_solar_fields = ['MPPT1_DC_VOLTAGE',
 'MPPT2_DC_VOLTAGE',
 'MPPT1_DC_CURRENT',
 'MPPT2_DC_CURRENT',
 'AC_VOLTAGE_R',
 'AC_VOLTAGE_Y',
 'AC_VOLTAGE_B',
 'CURRENT_R',
 'CURRENT_Y',
 'CURRENT_B',
 'AC_FREQUENCY_R',
 'AC_FREQUENCY_Y',
 'AC_FREQUENCY_B',
 'ACTIVE_POWER',
 'SOLAR_STATUS',
 'HEAT_SINK_TEMPERATURE',
 'DAILY_YIELD',
 'TOTAL_YIELD']



plant_solar_fields_units = {'ACTIVE_POWER': 'kW', 'AC_FREQUENCY': 'Hz',
							'AC_FREQUENCY_R': 'Hz', 'AC_FREQUENCY_Y': 'Hz', 'AC_FREQUENCY_B': 'Hz',
							'AC_VOLTAGE_B': 'V',
							'AC_VOLTAGE_R': 'V', 'AC_VOLTAGE_Y': 'V', 'APPARENT_POWER': 'VA',
							'CURRENT_B': 'A', 'CURRENT_R': 'A', 'CURRENT_Y': 'A',
							'DAILY_SCADA_ENERGY_DAY_1': 'kWh', 'DAILY_YIELD': 'kWh',
							'DC_POWER': 'kW', 'DIGITAL_INPUT': 'NA',
							'HEAT_SINK_TEMPERATURE': 'C', 'MPPT1_DC_CURRENT': 'A',
							'MPPT1_DC_VOLTAGE': 'V', 'MPPT2_DC_CURRENT': 'A', 'MPPT2_DC_VOLTAGE': 'V',
							'MPPT3_DC_CURRENT': 'A', 'MPPT3_DC_VOLTAGE': 'V', 'MPPT4_DC_CURRENT': 'A',
							'MPPT4_DC_VOLTAGE': 'V', 'POWER_FACTOR': 'NA', 'REACTIVE_POWER': 'Var',
							'SOLAR_STATUS': 'NA', 'TOTAL_YIELD': 'kWh'}


plant_solar_fields_mf = {u'ACTIVE_POWER': 0.001,
 u'AC_FREQUENCY_B': 0.01,
 u'AC_FREQUENCY_R': 0.01,
 u'AC_FREQUENCY_Y': 0.01,
 u'AC_VOLTAGE_B': 0.1,
 u'AC_VOLTAGE_R': 0.1,
 u'AC_VOLTAGE_Y': 0.1,
 u'CURRENT_B': 1.0,
 u'CURRENT_R': 1.0,
 u'CURRENT_Y': 1.0,
 u'DAILY_YIELD': 0.1,
 u'HEAT_SINK_TEMPERATURE': 1.0,
 u'MPPT1_DC_CURRENT': 0.1,
 u'MPPT1_DC_VOLTAGE': 0.1,
 u'MPPT2_DC_CURRENT': 0.1,
 u'MPPT2_DC_VOLTAGE': 0.1,
 u'SOLAR_STATUS': 1.0,
 u'TOTAL_YIELD': 0.1}

def set_mf_for_waaree_inverter(plant, inverter):
	try:
		fields = inverter.fields.all()
		for field in fields:
			if str(field.name) in plant_solar_fields:
				field.streamDataUnit = plant_solar_fields_units[field.name]
				field.multiplicationFactor = plant_solar_fields_mf[field.name]
				if "SOLEX" in inverter.manufacturer and "YIELD" in field.name:
					field.multiplicationFactor = plant_solar_fields_mf[field.name] * 0.01
				field.isActive = True
			else:
				field.isActive = False

			if str(field.name).startswith("DAILY_SCADA_ENERGY_DAY"):
				field.isActive = False

			field.save()

			solar_field = field.solarfield
			solar_field.displayName = streams_mappings.get("%s" % field.name, "%s" % field.name)
			solar_field.save()
	except Exception as exception:
		logger.debug(str(exception))



#Plant Meta

plant_meta_solar_fields = ['IRRADIATION','MODULE_TEMPERATURE','AMBIENT_TEMPERATURE']

plant_meta_solar_fields_units = {'IRRADIATION':'kWh/m^2','MODULE_TEMPERATURE':'C','AMBIENT_TEMPERATURE':'C'}

plant_meta_solar_fields_mf = {'IRRADIATION':0.001,'MODULE_TEMPERATURE':1.0,'AMBIENT_TEMPERATURE':1.0}


SOLIS_INVERTER_STATUS_MAPPINGS = [(0, 'Wait Mode', False),
								  (1, 'Normal Mode', True),
								  (2, 'Fault Mode', False),
								  (3, 'Normal Mode - SOLEX', True)]


def set_mf_for_plant_meta(plant):
	try:
		plant_meta = plant.metadata.plantmetasource
		fields = plant_meta.fields.all()
		for field in fields:
			if str(field.name) in plant_meta_solar_fields:
				field.streamDataUnit = plant_meta_solar_fields_units[field.name]
				field.multiplicationFactor = plant_meta_solar_fields_mf[field.name]
			else:
				field.isActive = False
			field.save()
	except Exception as exception:
		logger.debug(str(exception))


def set_waaree_inverter_error_codes(plant):
	try:
		for value in SOLIS_INVERTER_STATUS_MAPPINGS:
			try:
				mapping = InverterStatusMappings.objects.create(plant=plant,
																stream_name='SOLAR_STATUS',
																status_code=float(value[0]),
																status_description=str(value[1]),
																description_stream_name='SOLAR_STATUS_DESCRIPTION',
																generating=value[2])
				mapping.save()
			except:
				continue
	except Exception as exception:
		logger.debug(str(exception))