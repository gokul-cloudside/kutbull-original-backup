import sys, logging, dateutil
from solarrms.models import InverterStatusMappings

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

plant_solar_fields = ['ACTIVE_POWER',
 'REACTIVE_POWER',
 'TOTAL_YIELD',
 'AC_VOLTAGE_R',
 'AC_VOLTAGE_Y',
 'AC_VOLTAGE_B',
 'CURRENT_R',
 'CURRENT_Y',
 'CURRENT_B',
 'AC_FREQUENCY',
 'POWER_FACTOR',
 'INSIDE_TEMPERATURE',
 'MPPT1_DC_POWER',
 'MPPT2_DC_POWER',
 'MPPT3_DC_POWER',
 'SOLAR_STATUS',
 'DC_POWER',
 'DAILY_YIELD',
 'DAILY_SCADA_ENERGY_DAY_1']

#Inverters
plant_solar_fields_units = {'ACTIVE_POWER': 'kW',
 'AC_FREQUENCY': 'Hz',
 'AC_VOLTAGE_B': 'V',
 'AC_VOLTAGE_R': 'V',
 'AC_VOLTAGE_Y': 'V',
 'CURRENT_B': 'A',
 'CURRENT_R': 'A',
 'CURRENT_Y': 'A',
 'DAILY_SCADA_ENERGY_DAY_1': 'kWh',
 'DAILY_YIELD': 'kWh',
 'DC_POWER': 'kW',
 'INSIDE_TEMPERATURE': 'C',
 'MPPT1_DC_POWER': 'kW',
 'MPPT2_DC_POWER': 'kW',
 'MPPT3_DC_POWER': 'kW',
 'POWER_FACTOR': 'None',
 'REACTIVE_POWER': 'Var',
 'SOLAR_STATUS': 'None',
 'TOTAL_YIELD': 'kWh'}

plant_solar_fields_mf = {'ACTIVE_POWER': 0.001,
 'AC_FREQUENCY': 0.01,
 'AC_VOLTAGE_B': 0.1,
 'AC_VOLTAGE_R': 0.1,
 'AC_VOLTAGE_Y': 0.1,
 'CURRENT_B': 0.1,
 'CURRENT_R': 0.1,
 'CURRENT_Y': 0.1,
 'DAILY_SCADA_ENERGY_DAY_1': 0.01,
 'DAILY_YIELD': 0.001,
 'DC_POWER': 0.001,
 'INSIDE_TEMPERATURE': 0.1,
 'MPPT1_DC_POWER': 0.001,
 'MPPT2_DC_POWER': 0.001,
 'MPPT3_DC_POWER': 0.001,
 'POWER_FACTOR': 0.001,
 'REACTIVE_POWER': 0.001,
 'SOLAR_STATUS': 1,
 'TOTAL_YIELD': 0.01}


HUAWEI_INVERTER_STATUS_MAPPINGS = [(0.0, 'Idle: Initializing', True),
                                   (1.0, 'Idle: ISO Detecting', True),
                                   (2.0, 'Idle: Irradiation Detecting', True),
                                   (3.0, 'Idle: Grid Detecting', True),
                                   (256.0, 'Starting', True),
                                   (512.0, 'On-grid', True),
                                   (513.0, 'On-grid:Limited', True),
                                   (768.0, 'Shutdown: Abnormal', False),
                                   (769.0, 'Shutdown: Forced', False),
                                   (1025.0, 'Grid Dispatch: cos?-P Curve', True),
                                   (1026.0, 'Grid Dispatch: Q-U Curve', True),
                                   (1280.0, 'Checking completed', True),
                                   (1281.0, 'Checking', True),
                                   (1536.0, 'Inspecting', True),
                                   (40960.0, 'Idle: No Irradiation', True)]

def set_mf_for_huawei_inverter(plant, inverter):
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


def set_huawei_inverter_error_codes(plant):
	try:
		for value in HUAWEI_INVERTER_STATUS_MAPPINGS:
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

