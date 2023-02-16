import sys, logging, dateutil
from solarrms.models import InverterStatusMappings

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

plant_solar_fields = ['DAILY_YIELD','TOTAL_YIELD','DC_POWER','AC_VOLTAGE_R','AC_VOLTAGE_Y','AC_VOLTAGE_B','CURRENT_R',
'CURRENT_Y','CURRENT_B','ACTIVE_POWER','AC_FREQUENCY_R','SOLAR_STATUS','MPPT1_DC_VOLTAGE','MPPT2_DC_VOLTAGE','MPPT2_DC_VOLTAGE',
'MPPT2_DC_VOLTAGE','MPPT1_DC_CURRENT','MPPT2_DC_CURRENT','MPPT3_DC_CURRENT','MPPT4_DC_CURRENT']

#Inverters
plant_solar_fields_units = {'DAILY_YIELD':'kWh','TOTAL_YIELD':'kWh','DC_POWER':'kW','AC_VOLTAGE_R':'V','AC_VOLTAGE_Y':'V','AC_VOLTAGE_B':'V',
'CURRENT_R':'A','CURRENT_Y':'A','CURRENT_B':'A','ACTIVE_POWER':'kW','AC_FREQUENCY_R':'Hz','SOLAR_STATUS':'','MPPT1_DC_VOLTAGE':'V',
'MPPT2_DC_VOLTAGE':'V','MPPT3_DC_VOLTAGE':'V','MPPT4_DC_VOLTAGE':'V','MPPT1_DC_CURRENT':'A','MPPT2_DC_CURRENT':'A','MPPT3_DC_CURRENT':'A',
'MPPT4_DC_CURRENT':'A'}

plant_solar_fields_mf = {'DAILY_YIELD':1,'TOTAL_YIELD':1,'DC_POWER':0.001,'AC_VOLTAGE_R':0.1,'AC_VOLTAGE_Y':0.1,'AC_VOLTAGE_B':0.1,'CURRENT_R':0.1,
'CURRENT_Y':0.1,'CURRENT_B':0.1,'ACTIVE_POWER':0.001,'AC_FREQUENCY_R':0.1,'SOLAR_STATUS':1,'MPPT1_DC_VOLTAGE':0.1,'MPPT2_DC_VOLTAGE':0.1,'MPPT3_DC_VOLTAGE':0.1,
'MPPT4_DC_VOLTAGE':0.1,'MPPT1_DC_CURRENT':0.1,'MPPT2_DC_CURRENT':0.1,'MPPT3_DC_CURRENT':0.1,'MPPT4_DC_CURRENT':0.1}


SUNGROW_INVERTER_STATUS_MAPPINGS = [(0.0, 'Run', True),
								    (21760.0, 'Stop due to fault', False),
									(33024.0, 'Derating', True),
									(4608.0, 'Initial Stand-by', True),
									(4864.0, 'Key stop', True),
									(5120.0, 'Stand-by', True),
									(5376.0, 'Emergency Stop', True),
									(5632.0, 'Start-up', True),
									(9472.0, 'Communicate abnormal', False),
									(13824.0, 'Upgrade failure', False),
									(32768.0, 'Stop', True),
									(33280.0, 'Power limitation from external commands', True),
									(37120.0, 'Warning', True),
									(65535.0, 'Undefined', True)]



def set_mf_for_sungrow_inverter(plant, inverter):
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


def set_sungrow_inverter_error_codes(plant):
	try:
		for value in SUNGROW_INVERTER_STATUS_MAPPINGS:
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

