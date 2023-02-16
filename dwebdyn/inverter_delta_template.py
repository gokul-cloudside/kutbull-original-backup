import sys, logging, dateutil
from solarrms.models import InverterStatusMappings, streams_mappings

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

#Inverters

plant_solar_fields = ['ACTIVE_POWER', 'ACTIVE_POWER_R', 'ACTIVE_POWER_Y', 'ACTIVE_POWER_B', 'AC_FREQUENCY_B', 'AC_FREQUENCY_R',
					  'AC_FREQUENCY_Y', 'AC_VOLTAGE_B', 'AC_VOLTAGE_R', 'AC_VOLTAGE_Y', 'APPARENT_POWER_B','APPARENT_POWER_R',
					  'APPARENT_POWER_Y', 'CURRENT_B', 'CURRENT_R', 'CURRENT_Y', 'DAILY_YIELD', 'DC_POWER', 'TOTAL_YIELD',
					  'HEAT_SINK_TEMPERATURE', 'MPPT1_DC_CURRENT', 'MPPT1_DC_POWER', 'MPPT1_DC_VOLTAGE',
					  'MPPT2_DC_CURRENT', 'MPPT2_DC_POWER', 'MPPT2_DC_VOLTAGE', 'SOLAR_STATUS',
					  'TOTAL_OPERATIONAL_HOURS',
					  'DAILY_SCADA_ENERGY_DAY_1', 'DAILY_SCADA_ENERGY_DAY_2', 'DAILY_SCADA_ENERGY_DAY_3',
					  'DAILY_SCADA_ENERGY_DAY_4', 'DAILY_SCADA_ENERGY_DAY_5', 'DAILY_SCADA_ENERGY_DAY_6',
					  'DAILY_SCADA_ENERGY_DAY_7', 'DAILY_SCADA_ENERGY_DAY_8', 'DAILY_SCADA_ENERGY_DAY_9',
					  'DAILY_SCADA_ENERGY_DAY_10', 'DAILY_SCADA_ENERGY_DAY_11', 'DAILY_SCADA_ENERGY_DAY_12',
					  'DAILY_SCADA_ENERGY_DAY_13', 'DAILY_SCADA_ENERGY_DAY_14', 'DAILY_SCADA_ENERGY_DAY_15',
					  'DAILY_SCADA_ENERGY_DAY_16', 'DAILY_SCADA_ENERGY_DAY_17', 'DAILY_SCADA_ENERGY_DAY_18',
					  'DAILY_SCADA_ENERGY_DAY_19', 'DAILY_SCADA_ENERGY_DAY_20', 'DAILY_SCADA_ENERGY_DAY_21',
					  'DAILY_SCADA_ENERGY_DAY_22', 'DAILY_SCADA_ENERGY_DAY_23', 'DAILY_SCADA_ENERGY_DAY_24',
					  'DAILY_SCADA_ENERGY_DAY_25', 'DAILY_SCADA_ENERGY_DAY_26', 'DAILY_SCADA_ENERGY_DAY_27',
					  'DAILY_SCADA_ENERGY_DAY_28', 'DAILY_SCADA_ENERGY_DAY_29', 'DAILY_SCADA_ENERGY_DAY_30']

plant_solar_fields_units = {'ACTIVE_POWER': 'kW',
							 'ACTIVE_POWER_B': 'kW',
							 'ACTIVE_POWER_R': 'kW',
							 'ACTIVE_POWER_Y': 'kW',
							 'AC_FREQUENCY_B': 'Hz',
							 'AC_FREQUENCY_R': 'Hz',
							 'AC_FREQUENCY_Y': 'Hz',
							 'AC_VOLTAGE_B': 'V',
							 'AC_VOLTAGE_R': 'V',
							 'AC_VOLTAGE_Y': 'V',
							 'APPARENT_POWER_B': 'kW',
							 'APPARENT_POWER_R': 'kW',
							 'APPARENT_POWER_Y': 'kW',
							 'CURRENT_B': 'A',
							 'CURRENT_R': 'A',
							 'CURRENT_Y': 'A',
							 'HEAT_SINK_TEMPERATURE': 'C',
							 'MPPT1_DC_CURRENT': 'A',
							 'MPPT1_DC_POWER': 'kW',
							 'MPPT1_DC_VOLTAGE': 'V',
							 'MPPT2_DC_CURRENT': 'A',
							 'MPPT2_DC_POWER': 'kW',
							 'MPPT2_DC_VOLTAGE': 'V',
							 'SOLAR_STATUS': 'NA',
							 'TOTAL_OPERATIONAL_HOURS': 'H',
							 'DAILY_SCADA_ENERGY_DAY_1': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_10': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_11': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_12': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_13': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_14': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_15': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_16': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_17': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_18': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_19': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_2': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_20': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_21': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_22': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_23': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_24': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_25': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_26': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_27': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_28': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_29': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_3': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_30': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_4': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_5': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_6': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_7': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_8': 'kWh',
							 'DAILY_SCADA_ENERGY_DAY_9': 'kWh',
							 'DAILY_YIELD': 'kWh',
							 'DC_POWER': 'kW',
							 'TOTAL_YIELD': 'kWh'}

plant_solar_fields_mf = {'ACTIVE_POWER': 0.001,
 'ACTIVE_POWER_B': 0.001,
 'ACTIVE_POWER_R': 0.001,
 'ACTIVE_POWER_Y': 0.001,
 'AC_FREQUENCY_B': 0.01,
 'AC_FREQUENCY_R': 0.01,
 'AC_FREQUENCY_Y': 0.01,
 'AC_VOLTAGE_B': 0.1,
 'AC_VOLTAGE_R': 0.1,
 'AC_VOLTAGE_Y': 0.1,
 'APPARENT_POWER_B': 0.001,
 'APPARENT_POWER_R': 0.001,
 'APPARENT_POWER_Y': 0.001,
 'CURRENT_B': 0.01,
 'CURRENT_R': 0.01,
 'CURRENT_Y': 0.01,
 'HEAT_SINK_TEMPERATURE': 1,
 'SOLAR_STATUS' : 1,
 'TOTAL_OPERATIONAL_HOURS': 1,
 'MPPT1_DC_CURRENT': 0.001,
 'MPPT1_DC_POWER': 0.001,
 'MPPT1_DC_VOLTAGE': 0.1,
 'MPPT2_DC_CURRENT': 0.001,
 'MPPT2_DC_POWER': 0.001,
 'MPPT2_DC_VOLTAGE': 0.1,
 'DAILY_SCADA_ENERGY_DAY_1': 0.001,
 'DAILY_SCADA_ENERGY_DAY_10': 0.001,
 'DAILY_SCADA_ENERGY_DAY_11': 0.001,
 'DAILY_SCADA_ENERGY_DAY_12': 0.001,
 'DAILY_SCADA_ENERGY_DAY_13': 0.001,
 'DAILY_SCADA_ENERGY_DAY_14': 0.001,
 'DAILY_SCADA_ENERGY_DAY_15': 0.001,
 'DAILY_SCADA_ENERGY_DAY_16': 0.001,
 'DAILY_SCADA_ENERGY_DAY_17': 0.001,
 'DAILY_SCADA_ENERGY_DAY_18': 0.001,
 'DAILY_SCADA_ENERGY_DAY_19': 0.001,
 'DAILY_SCADA_ENERGY_DAY_2': 0.001,
 'DAILY_SCADA_ENERGY_DAY_20': 0.001,
 'DAILY_SCADA_ENERGY_DAY_21': 0.001,
 'DAILY_SCADA_ENERGY_DAY_22': 0.001,
 'DAILY_SCADA_ENERGY_DAY_23': 0.001,
 'DAILY_SCADA_ENERGY_DAY_24': 0.001,
 'DAILY_SCADA_ENERGY_DAY_25': 0.001,
 'DAILY_SCADA_ENERGY_DAY_26': 0.001,
 'DAILY_SCADA_ENERGY_DAY_27': 0.001,
 'DAILY_SCADA_ENERGY_DAY_28': 0.001,
 'DAILY_SCADA_ENERGY_DAY_29': 0.001,
 'DAILY_SCADA_ENERGY_DAY_3': 0.001,
 'DAILY_SCADA_ENERGY_DAY_30': 0.001,
 'DAILY_SCADA_ENERGY_DAY_4': 0.001,
 'DAILY_SCADA_ENERGY_DAY_5': 0.001,
 'DAILY_SCADA_ENERGY_DAY_6': 0.001,
 'DAILY_SCADA_ENERGY_DAY_7': 0.001,
 'DAILY_SCADA_ENERGY_DAY_8': 0.001,
 'DAILY_SCADA_ENERGY_DAY_9': 0.001,
 'DAILY_YIELD': 0.001,
 'DC_POWER': 0.001,
 'TOTAL_YIELD': 0.01}

def set_mf_for_delta_inverter(plant, inverter):
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


DELTA_INVERTER_STATUS_MAPPINGS = [(0.0, 'Grid Tie - Standby', False),
								  (1.0, 'Grid Tie - System count down', False),
								  (2.0, 'Grid Tie - Operation', True),
								  (3.0, 'Grid Tie - No DC', False),
								  (4.0, 'Grid Tie - Alarm', False)]



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


def set_delta_inverter_error_codes(plant):
	try:
		for value in DELTA_INVERTER_STATUS_MAPPINGS:
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