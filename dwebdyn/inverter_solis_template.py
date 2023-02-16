import sys, logging, dateutil
from solarrms.models import InverterStatusMappings, streams_mappings

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

#Inverters

plant_solar_fields = ['ACTIVE_POWER', 'AC_FREQUENCY', 'AC_VOLTAGE_B', 'AC_VOLTAGE_R', 'AC_VOLTAGE_Y',
					  'APPARENT_POWER', 'CURRENT_B', 'CURRENT_R', 'CURRENT_Y', 'DAILY_SCADA_ENERGY_DAY_1',
					  'DAILY_YIELD', 'DC_POWER', 'DIGITAL_INPUT', 'HEAT_SINK_TEMPERATURE', 'MPPT1_DC_CURRENT',
					  'MPPT1_DC_VOLTAGE', 'MPPT2_DC_CURRENT', 'MPPT2_DC_VOLTAGE', 'MPPT3_DC_CURRENT',
					  'MPPT3_DC_VOLTAGE', 'MPPT4_DC_CURRENT', 'MPPT4_DC_VOLTAGE', 'POWER_FACTOR',
					  'REACTIVE_POWER', 'SOLAR_STATUS', 'TOTAL_YIELD']


plant_solar_fields_units = {'ACTIVE_POWER': 'kW', 'AC_FREQUENCY': 'H', 'AC_VOLTAGE_B': 'V',
							'AC_VOLTAGE_R': 'V', 'AC_VOLTAGE_Y': 'V', 'APPARENT_POWER': 'VA',
							'CURRENT_B': 'A', 'CURRENT_R': 'A', 'CURRENT_Y': 'A',
							'DAILY_SCADA_ENERGY_DAY_1': 'kWh', 'DAILY_YIELD': 'kWh',
							'DC_POWER': 'kW', 'DIGITAL_INPUT': 'NA',
							'HEAT_SINK_TEMPERATURE': 'C', 'MPPT1_DC_CURRENT': 'A',
							'MPPT1_DC_VOLTAGE': 'V', 'MPPT2_DC_CURRENT': 'A', 'MPPT2_DC_VOLTAGE': 'V',
							'MPPT3_DC_CURRENT': 'A', 'MPPT3_DC_VOLTAGE': 'V', 'MPPT4_DC_CURRENT': 'A',
							'MPPT4_DC_VOLTAGE': 'V', 'POWER_FACTOR': 'NA', 'REACTIVE_POWER': 'Var',
							'SOLAR_STATUS': 'NA', 'TOTAL_YIELD': 'kWh'}


plant_solar_fields_mf = {'ACTIVE_POWER': 0.001, 'AC_FREQUENCY': 0.01, 'AC_VOLTAGE_B': 0.1,
						 'AC_VOLTAGE_R': 0.1, 'AC_VOLTAGE_Y': 0.1, 'APPARENT_POWER': 1.0,
						 'CURRENT_B': 0.1, 'CURRENT_R': 0.1, 'CURRENT_Y': 0.1,
						 'DAILY_SCADA_ENERGY_DAY_1': 1.0, 'DAILY_YIELD': 1.0,
						 'DC_POWER': 0.001, 'DIGITAL_INPUT': 1.0, 'HEAT_SINK_TEMPERATURE': 0.1,
						 'MPPT1_DC_CURRENT': 0.1, 'MPPT1_DC_VOLTAGE': 0.1, 'MPPT2_DC_CURRENT': 0.1,
						 'MPPT2_DC_VOLTAGE': 0.1, 'MPPT3_DC_CURRENT': 0.1, 'MPPT3_DC_VOLTAGE': 0.1,
						 'MPPT4_DC_CURRENT': 0.1, 'MPPT4_DC_VOLTAGE': 0.1, 'POWER_FACTOR': 1.0,
						 'REACTIVE_POWER': 1.0, 'SOLAR_STATUS': 1.0, 'TOTAL_YIELD': 1.0}


def set_mf_for_solis_inverter(plant, inverter):
	from solarrms.models import streams_mappings
	try:
		fields = inverter.fields.all()
		for field in fields:
			if str(field.name) in plant_solar_fields:
				field.streamDataUnit = plant_solar_fields_units[field.name]
				field.multiplicationFactor = plant_solar_fields_mf[field.name]
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
		print exception
		logger.debug(str(exception))


#Plant Meta

plant_meta_solar_fields = ['IRRADIATION','MODULE_TEMPERATURE','AMBIENT_TEMPERATURE']

plant_meta_solar_fields_units = {'IRRADIATION':'kWh/m^2','MODULE_TEMPERATURE':'C','AMBIENT_TEMPERATURE':'C'}

plant_meta_solar_fields_mf = {'IRRADIATION':0.001,'MODULE_TEMPERATURE':1.0,'AMBIENT_TEMPERATURE':1.0}


SOLIS_INVERTER_STATUS_MAPPINGS = [(0, 'Waiting', True),
								  (1, 'Operation OK', True),
								  (2, 'Low Sunlight', True),
								  (3, 'At the Initializing', False),
								  (4100, 'Control Stop', False),
								  (4112, 'Grid Over Voltage', False),
								  (4113, 'Grid Under Voltage', False),
								  (4114, 'Grid Over Frequency', False),
								  (4115, 'Grid Under Frequency', False),
								  (4116, 'Grid Impedance Over', False),
								  (4117, 'No Grid', False), (4118, 'Grid Unbalance', False),
								  (4119, 'Grid Frequency Fluctuation', False), (4120, 'Grid Over Current', False),
								  (4121, 'Grid Current Tracking Fault', False), (4128, 'DC Over Voltage', False),
								  (4129, 'DC Bus Over Voltage', False), (4130, 'DC Bus Unbalance', False),
								  (4131, 'DC Bus Under Voltage', False), (4132, 'DC Bus Unbalance 2', False),
								  (4133, 'DC(Channel A ) Over Current', False),
								  (4134, 'DC(Channel B ) Over Current', False), (4135, 'DC Over Current', False), (4144, 'The Grid Interference Protection', False), (4145, 'The DSP Initial Protection', False), (4146, 'Temperature Protection', False), (4147, 'Ground Fault', False), (4148, 'Leakage Current Protection', False), (4149, 'Relay Protection', False), (4150, 'DSP_B Protection', False), (4151, 'DC Injection Protection', False), (4152, '12V Under Voltage Faulty', False), (4153, 'Leakage Current Check Protection', False), (4160, 'AFCI Check Fault', False), (4161, 'AFCI Fault', False), (4162, 'DSP Chip SRAM Fault', False), (4163, 'DSP Chip FLASH Fault', False), (4164, 'DSP Chip PC Pointer Fault', False), (4165, 'DSP Chip Register Fault', False), (4166, 'The Grid Interference 02 Protection', False), (4167, 'The Grid Current Sampling Error', False), (4168, 'IGBT Over Current', False)]



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


def set_solis_inverter_error_codes(plant):
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