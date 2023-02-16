import sys, logging, dateutil
from solarrms.models import InverterStatusMappings, streams_mappings

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

#Inverters

plant_solar_fields = ['TOTAL_OPERATIONAL_HOURS',
 'DAILY_YIELD',
 'CURRENT_R',
 'CURRENT_Y',
 'CURRENT_B',
 'AC_VOLTAGE_R',
 'AC_VOLTAGE_Y',
 'AC_VOLTAGE_B',
 'AC_FREQUENCY',
 'APPARENT_POWER',
 'ACTIVE_POWER',
 'REACTIVE_POWER',
 'DC_CURRENT',
 'DC_VOLTAGE',
 'DC_POWER',
 'TOTAL_YIELD']

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
							 'TOTAL_YIELD': 'kWh',
							 'AC_FREQUENCY': 'Hz',
							 'APPARENT_POWER': 'VA',
							 'REACTIVE_POWER': 'VAr',
							 'DC_CURRENT': 'A',
							 'DC_VOLTAGE': 'V'}

plant_solar_fields_mf = {'ACTIVE_POWER': 0.01,
 'AC_FREQUENCY': 0.01,
 'AC_VOLTAGE_B': 0.1,
 'AC_VOLTAGE_R': 0.1,
 'AC_VOLTAGE_Y': 0.1,
 'APPARENT_POWER': 0.01,
 'CURRENT_B': 0.01,
 'CURRENT_R': 0.01,
 'CURRENT_Y': 0.01,
 'DAILY_YIELD': 0.01,
 'DC_CURRENT': 0.01,
 'DC_POWER': 0.1,
 'DC_VOLTAGE': 1.0,
 'REACTIVE_POWER': 0.01,
 'TOTAL_OPERATIONAL_HOURS': 1.0,
 'TOTAL_YIELD': 1.0}


def set_mf_for_ingeteam_inverter(plant, inverter):
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

