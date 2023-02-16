''' PLANT METADATA '''
METADATA_STREAMS = [('TOTAL_PLANT_ENERGY', 'FLOAT'),
                    ('DAILY_PLANT_ENERGY', 'FLOAT'),
                    ('PLANT_ACTIVE_POWER', 'FLOAT'),
                    ('AMBIENT_TEMPERATURE', 'FLOAT'),
                    ('HIGHEST_AMBIENT_TEMPERATURE', 'FLOAT'),
                    ('IRRADIATION', 'FLOAT'),
                    ('MODULE_TEMPERATURE', 'FLOAT'),
                    ('EXTERNAL_IRRADIATION', 'FLOAT'),
                    ('ENERGY_METER_DATA', 'FLOAT'),
                    ('FREQUENCY', 'FLOAT'),
                    ('WINDSPEED', 'FLOAT'),
                    ('IRRADIATION_2', 'FLOAT'),
                    ('IRRADIATION_3', 'FLOAT'),
                    ('IRRADIATION_4', 'FLOAT'),
                    ('AMBIENT_TEMPERATURE_2', 'FLOAT'),
                    ('AMBIENT_TEMPERATURE_3', 'FLOAT'),
                    ('AMBIENT_TEMPERATURE_4', 'FLOAT'),
                    ('MODULE_TEMPERATURE_2', 'FLOAT'),
                    ('MODULE_TEMPERATURE_3', 'FLOAT'),
                    ('MODULE_TEMPERATURE_4', 'FLOAT'),
                    ('WINDSPEED_2', 'FLOAT'),
                    ('WINDSPEED_3', 'FLOAT'),
                    ('WINDSPEED_4', 'FLOAT'),
                    ('WIND_DIRECTION', 'FLOAT'),
                    ('WIND_DIRECTION_2', 'FLOAT'),
                    ('WIND_DIRECTION_3', 'FLOAT'),
                    ('WIND_DIRECTION_4', 'FLOAT')]

PLANT_POWER_STREAM = 'PLANT_ACTIVE_POWER'
PLANT_TOTAL_ENERGY_STREAM = 'TOTAL_PLANT_ENERGY'
PLANT_ENERGY_STREAM = 'DAILY_PLANT_ENERGY'

METADATA_STATUS_PARAMETERS = [('LIVE', 'BOOLEAN'),
                              ('AGGREGATED', 'BOOLEAN')]

METADATA_INPUT_PATAMETERS = [('TIMESTAMP', 'TIMESTAMP'),
                             ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                             ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                             ('AGGREGATED_COUNT', 'FLOAT')]

'''WEATHER STATION PARAMETERS'''
WEATHER_STATION_STREAMS = [('AMBIENT_TEMPERATURE', 'FLOAT'),
                           ('HIGHEST_AMBIENT_TEMPERATURE', 'FLOAT'),
                           ('MODULE_TEMPERATURE', 'FLOAT'),
                           ('IRRADIATION', 'FLOAT'),
                           ('EXTERNAL_IRRADIATION', 'FLOAT'),
                           ('WINDSPEED', 'FLOAT'),
                           ('WIND_DIRECTION', 'FLOAT'),
                           ('RAINFALL', 'FLOAT')]

WEATHER_STATION_STATUS_PARAMETERS = [('LIVE', 'BOOLEAN'),
                                     ('AGGREGATED', 'BOOLEAN')]

WEATHER_STATION_INPUT_PATAMETERS = [('TIMESTAMP', 'TIMESTAMP'),
                                    ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                                    ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                                    ('AGGREGATED_COUNT', 'FLOAT')]


'''SOLAR METRICS PARAMETERS'''
SOLAR_METRICS_STREAMS = [('PR', 'FLOAT'),
                         ('CUF', 'FLOAT'),
                         ('SPECIFIC_YIELD', 'FLOAT')]

SOLAR_METRICS_STATUS_PARAMETERS = [('LIVE', 'BOOLEAN'),
                                   ('AGGREGATED', 'BOOLEAN')]

SOLAR_METRICS_INPUT_PATAMETERS = [('TIMESTAMP', 'TIMESTAMP'),
                                  ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                                  ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                                  ('AGGREGATED_COUNT', 'FLOAT')]

'''GATEWAY PARAMETERS'''

GATEWAY_STREAMS = [('HEARTBEAT', 'BOOLEAN')]
GATEWAY_INPUT_PATAMETERS = [('TIMESTAMP', 'TIMESTAMP')]


''' INVERTER PARAMETERS '''
FIELD_CHOICES = (('INPUT', 'INPUT'),
                 ('OUTPUT', 'OUTPUT'),
                 ('STATUS', 'STATUS'),
                 ('ERROR', 'ERROR'))

INPUT_PARAMETERS = [('DC_VOLTAGE', 'FLOAT'),
                    ('DC_CURRENT', 'FLOAT'),
                    ('DC_POWER', 'FLOAT'),
                    ('CONVERTER_VOLTAGE', 'FLOAT'),
                    ('TIMESTAMP', 'TIMESTAMP'),
                    ('INVERTER_TIMESTAMP', 'TIMESTAMP'),
                    ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                    ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                    ('AGGREGATED_COUNT', 'FLOAT')]

MPPT_INPUT_PARAMETERS = [('MPPT1_DC_VOLTAGE','FLOAT'),
                         ('MPPT1_DC_CURRENT','FLOAT'),
                         ('MPPT1_DC_POWER','FLOAT'),
                         ('MPPT2_DC_VOLTAGE','FLOAT'),
                         ('MPPT2_DC_CURRENT','FLOAT'),
                         ('MPPT2_DC_POWER','FLOAT'),
                         ('MPPT3_DC_VOLTAGE','FLOAT'),
                         ('MPPT3_DC_CURRENT','FLOAT'),
                         ('MPPT3_DC_POWER','FLOAT'),
                         ('MPPT4_DC_VOLTAGE','FLOAT'),
                         ('MPPT4_DC_CURRENT','FLOAT'),
                         ('MPPT4_DC_POWER','FLOAT'),
                         ('MPPT5_DC_VOLTAGE','FLOAT'),
                         ('MPPT5_DC_CURRENT','FLOAT'),
                         ('MPPT5_DC_POWER','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_1','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_2','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_3','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_4','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_5','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_6','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_7','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_8','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_9','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_10','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_11','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_12','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_13','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_14','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_15','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_16','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_17','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_18','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_19','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_20','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_21','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_22','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_23','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_24','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_25','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_26','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_27','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_28','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_29','FLOAT'),
                         ('DAILY_SCADA_ENERGY_DAY_30','FLOAT')]

OUTPUT_PARAMETERS = [('ACTIVE_POWER', 'FLOAT'),
                     ('APPARENT_POWER', 'FLOAT'),
                     ('REACTIVE_POWER', 'FLOAT'),

                     ('ACTIVE_ENERGY', 'FLOAT'),
                     ('TOTAL_YIELD', 'FLOAT'),
                      ('DAILY_YIELD', 'FLOAT'),

                     ('PHASE_ANGLE', 'FLOAT'),
                     ('POWER_FACTOR', 'FLOAT'),

                     ('AC_FREQUENCY', 'FLOAT'),
                     ('AC_VOLTAGE', 'FLOAT'),
                     #phases R-L1, Y-L2, B-L3
                     ('AC_VOLTAGE_R', 'FLOAT'),
                     ('AC_VOLTAGE_Y', 'FLOAT'),
                     ('AC_VOLTAGE_B', 'FLOAT'),
                     ('INVERTER_LOADING', 'FLOAT'),

                     ('APPARENT_POWER_R', 'FLOAT'),
                     ('APPARENT_POWER_Y', 'FLOAT'),
                     ('APPARENT_POWER_B', 'FLOAT'),

                     ('AC_FREQUENCY_R', 'FLOAT'),
                     ('AC_FREQUENCY_Y', 'FLOAT'),
                     ('AC_FREQUENCY_B', 'FLOAT'),

                     ('ACTIVE_POWER_R', 'FLOAT'),
                     ('ACTIVE_POWER_Y', 'FLOAT'),
                     ('ACTIVE_POWER_B', 'FLOAT'),

                     ('REACTIVE_POWER_R', 'FLOAT'),
                     ('REACTIVE_POWER_Y', 'FLOAT'),
                     ('REACTIVE_POWER_B', 'FLOAT'),

                     ('CURRENT_R', 'FLOAT'),
                     ('CURRENT_Y', 'FLOAT'),
                     ('CURRENT_B', 'FLOAT'),
                     ('CURRENT', 'FLOAT'),
                     ('TOTAL_OPERATIONAL_HOURS', 'FLOAT'),
                     ('DAILY_OPERATIONAL_HOURS', 'FLOAT')
                     ]


STATUS_PARAMETERS = [('HEAT_SINK_TEMPERATURE', 'FLOAT'),
                     ('INSIDE_TEMPERATURE', 'FLOAT'),
                     ('CURRENT_ERROR', 'FLOAT'),
                     ('CURRENT_COMPLETE_ERROR', 'FLOAT'),
                     ('POWER_SUPPLY_VOLTAGE', 'FLOAT'),
                     ('POWER_SUPPLY_CURRENT', 'FLOAT'),
                     ('POWER_SUPPLY_VOLTAGE_Y', 'FLOAT'),
                     ('POWER_SUPPLY_VOLTAGE_B', 'FLOAT'),
                     ('POWER_SUPPLY_VOLTAGE_R', 'FLOAT'),
                     ('SOLAR_STATUS', 'FLOAT'),
                     ('SOLAR_STATUS_MESSAGE', 'FLOAT'),
                     ('SOLAR_STATUS_DESCRIPTION', 'STRING'),
                     ('OPERATING_TIME', 'FLOAT'),
                     ('FEEDIN_TIME', 'FLOAT'),

                     ('FAULT_LOW', 'STRING'),
                     ('FAULT_HIGH', 'STRING'),

                     ('DIGITAL_INPUT', 'FLOAT'),
                     ('CONVERTER_TEMPERATURE', 'FLOAT'),
                     ('CUBICLE_TEMPERATURE', 'FLOAT'),

                     ('AGGREGATED', 'BOOLEAN'),
                     ('LIVE', 'BOOLEAN')]

VIRTUAL_GATEWAY_INPUT_PARAMETERS = [('POWER_ON', 'BOOLEAN'),
                                    ('GPRS_SIGNAL_STRENGTH', 'FLOAT'),
                                    ('REBOOT_TIMESTAMP', 'TIMESTAMP'),
                                    ('TIMESTAMP', 'TIMESTAMP')]

VIRTUAL_GATEWAY_OUTPUT_PARAMETERS = []

VIRTUAL_GATEWAY_STATUS_PARAMETERS = []

VIRTUAL_GATEWAY_ERROR_FIELDS = []

INVERTER_CHART_FIELDS = ['DC_POWER', 'ACTIVE_POWER', 'AC_FREQUENCY', 'INSIDE_TEMPERATURE']

INVERTER_CHART_LEN = 30

INVERTER_POWER_FIELD = 'ACTIVE_POWER'
INVERTER_ENERGY_FIELD = 'DAILY_YIELD'
INVERTER_TOTAL_ENERGY_FIELD = 'TOTAL_YIELD'

INVERTER_VALID_LAST_ENTRY_MINUTES = 20
VALID_ENERGY_CALCULATION_DELTA_MINUTES = 3
VALID_ENERGY_CALCULATION_DELTA_MINUTES_DOMINICUS = 6
AGGREGATOR_CHOICES = ["HOUR", "DAY", "WEEK", "FIVE_MINUTES", "MONTH"]

'''FEEDER PARAMETERS'''
FEEDER_PARAMETERS = [('R_PH Voltage', 'FLOAT'),
                     ('Y_PH Voltage', 'FLOAT'),
                     ('B_PH Voltage', 'FLOAT'),
                     ('R_PH Current', 'FLOAT'),
                     ('Y_PH Current', 'FLOAT'),
                     ('B_PH Current', 'FLOAT'),
                     ('R_PH Active Power', 'FLOAT'),
                     ('Y_PH Active Power', 'FLOAT'),
                     ('B_PH Active Power', 'FLOAT'),
                     ('R_PH Apparent Power', 'FLOAT'),
                     ('Y_PH Apparent Power', 'FLOAT'),
                     ('B_PH Apparent Power', 'FLOAT'),
                     ('R_PH Reactive Power', 'FLOAT'),
                     ('Y_PH Reactive Power', 'FLOAT'),
                     ('B_PH Reactive Power', 'FLOAT'),
                     ('R_PH Power Factor', 'FLOAT'),
                     ('Y_PH Power Factor', 'FLOAT'),
                     ('B_PH Power Factor', 'FLOAT'),
                     ('Total Current', 'FLOAT'),
                     ('Total Active Power', 'FLOAT'),
                     ('Total Apparent Power', 'FLOAT'),
                     ('Total Reactive Power', 'FLOAT'),
                     ('Average PF', 'FLOAT'),
                     ('Frequency', 'FLOAT'),
                     ('Total Active Energy', 'FLOAT'),
                     ('Total Reactive Energ', 'FLOAT'),
                     ('TIMESTAMP', 'TIMESTAMP'),
                     ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                     ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                     ('AGGREGATED_COUNT', 'FLOAT')]


'''AJB PARAMS'''
STRINGS = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7',
           'S8', 'S9', 'S10', 'S11', 'S12', 'S13', 'S14',
           'S15', 'S16', 'S17', 'S18', 'S19', 'S20', 'S21',
           'S22', 'S23', 'S24', 'S25']

TEMPERATURE_SENSORS = ['TEMP1', 'TEMP2', 'TEMP3']

OTHERS = [('VOLTAGE', 'FLOAT'),
          ('CURRENT', 'FLOAT'),
          ('POWER', 'FLOAT'),
          ('TIMESTAMP', 'TIMESTAMP'),
          ('AGGREGATED_START_TIME', 'TIMESTAMP'),
          ('AGGREGATED_END_TIME', 'TIMESTAMP'),
          ('AGGREGATED_COUNT', 'FLOAT'),
          ('LIVE', 'BOOLEAN'),
          ('AGGREGATED', 'BOOLEAN'),
          ('DI_STATUS_1', 'FLOAT'),
          ('DI_STATUS_2', 'FLOAT'),
          ('DI_STATUS_3', 'FLOAT'),
          ('DI_STATUS_4', 'FLOAT'),
          ('DI_STATUS_5', 'FLOAT'),
          ('DO_STATUS_1', 'FLOAT'),
          ('DO_STATUS_2', 'FLOAT'),
          ('DI_STATUS_1_DESCRIPTION', 'STRING'),
          ('DI_STATUS_2_DESCRIPTION', 'STRING'),
          ('DI_STATUS_3_DESCRIPTION', 'STRING'),
          ('DI_STATUS_4_DESCRIPTION', 'STRING'),
          ('DI_STATUS_5_DESCRIPTION', 'STRING'),
          ('DO_STATUS_1_DESCRIPTION', 'STRING'),
          ('DO_STATUS_2_DESCRIPTION', 'STRING')]

PLANT_DEFAULT_TIMEZONE = 'Asia/Kolkata'
PLANT_DEFAULT_START_TIME = '06:30:00'
PLANT_DEFAULT_END_TIME = '18:30:00'

INVERTER_ERROR_FIELDS = [('ERROR_CODE', 'FLOAT'),
                        ('ERROR_DESCRIPTION', 'STRING'),
                        ('ERROR_TIMESTAMP','TIMESTAMP'),
                        ('ERROR_CONDITION','FLOAT'),
                        ('ACTIVE_ALARMS','FLOAT'),
                        ('LIVE','BOOLEAN'),
                        ('AGGREGATED','BOOLEAN'),
                        ('ERROR_MODBUS_READ', 'FLOAT')]

AJB_ERROR_FIELDS = [('ERROR_CODE', 'FLOAT'),
                    ('ERROR_DESCRIPTION', 'STRING'),
                    ('ERROR_TIMESTAMP','TIMESTAMP'),
                    ('ERROR_CONDITION','FLOAT'),
                    ('ACTIVE_ALARMS','FLOAT'),
                    ('LIVE','BOOLEAN'),
                    ('AGGREGATED','BOOLEAN'),
                    ('ERROR_MODBUS_READ', 'FLOAT')]

PLANT_META_ERROR_FIELDS = [('ERROR_MODBUS_READ', 'FLOAT'),
                           ('ERROR_TIMESTAMP','TIMESTAMP'),
                           ('LIVE','BOOLEAN'),
                           ('AGGREGATED','BOOLEAN')]

ENERGY_METER_STREAMS = [('WATT_TOTAL', 'FLOAT'),
                        ('WATTS_R_PHASE', 'FLOAT'),
                        ('WATTS_Y_PHASE', 'FLOAT'),
                        ('WATTS_B_PHASE', 'FLOAT'),
                        ('VAR_TOTAL', 'FLOAT'),
                        ('VAR_R_PHASE', 'FLOAT'),
                        ('VAR_Y_PHASE', 'FLOAT'),
                        ('VAR_B_PHASE', 'FLOAT'),
                        ('PF_AVG', 'FLOAT'),
                        ('PF_R_PHASE', 'FLOAT'),
                        ('PF_Y_PHASE', 'FLOAT'),
                        ('PF_B_PHASE', 'FLOAT'),
                        ('VA_TOTAL', 'FLOAT'),
                        ('VA_R_PHASE', 'FLOAT'),
                        ('VA_Y_PHASE', 'FLOAT'),
                        ('VA_B_PHASE', 'FLOAT'),
                        ('VLL_AVG', 'FLOAT'),
                        ('VRY_PHASE', 'FLOAT'),
                        ('VYB_PHASE', 'FLOAT'),
                        ('VBR_PHASE', 'FLOAT'),
                        ('VLN_AVG', 'FLOAT'),
                        ('VR_PHASE', 'FLOAT'),
                        ('VY_PHASE', 'FLOAT'),
                        ('VB_PHASE', 'FLOAT'),
                        ('CURRENT_TOTAL', 'FLOAT'),
                        ('C_R_PHASE', 'FLOAT'),
                        ('C_Y_PHASE', 'FLOAT'),
                        ('C_B_PHASE', 'FLOAT'),
                        ('Frequency', 'FLOAT'),
                        ('Wh_RECEIVED', 'FLOAT'),
                        ('VAh_RECEIVED', 'FLOAT'),
                        ('VARh_IMPEDENCE_RECEIVED', 'FLOAT'),
                        ('VARh_CAPACITANCE_RECEIVED', 'FLOAT'),
                        ('Wh_DELIVERED', 'FLOAT'),
                        ('VAh_DELIVERED', 'FLOAT'),
                        ('VARh_IMPEDENCE_DELIVERED', 'FLOAT'),
                        ('VARh_CAPACITANCE_DELIVERED', 'FLOAT')]

ENERGY_METER_ERROR_STREAMS = [('ERROR_MODBUS_READ', 'FLOAT'),
                              ('ERROR_TIMESTAMP','TIMESTAMP'),
                              ('LIVE','BOOLEAN'),
                              ('AGGREGATED','BOOLEAN')]

TRANSFORMER_STREAMS = [('VOLTAGE', 'FLOAT'),
                       ('CURRENT', 'FLOAT'),
                       ('PF', 'FLOAT'),
                       ('HZ', 'FLOAT'),
                       ('KWH_I', 'FLOAT'),
                       ('KWH_E', 'FLOAT'),
                       ('TIMESTAMP','TIMESTAMP'),
                       ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                       ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                       ('AGGREGATED_COUNT', 'FLOAT')]

TRANSFORMER_ERROR_STREAMS = [('ERROR_MODBUS_READ', 'FLOAT'),
                             ('ERROR_TIMESTAMP','TIMESTAMP'),
                             ('LIVE','BOOLEAN'),
                             ('AGGREGATED','BOOLEAN')]

WEBDYN_PLANTS_SLUG = ['growels','hospital','iesschool','portuserbuilding','rrkabel','raheja','uran','solarpump','stmaryschool','unipatch','waareedemo', 'platina']
PLANTS_SLUG_FIVE_MINUTES_INTERVAL_DATA = ['dominicus']

ENERGY_CALCULATION_STREAMS = {'waaneep':'KWH',
                              'dominicus':'kWhT(I)',
                              'yerangiligi':'Wh_RECEIVED',
                              'gsi':'Wh_RECEIVED',
                              'hyderabadhouse':'Wh_RECEIVED',
                              'rashtrapatibhawanauditorium':'Wh_RECEIVED',
                              'sardarpatelbhawan':'Wh_RECEIVED',
                              'nizampalace':'Wh_RECEIVED',
                              'airportmetrodepot':'Wh_RECEIVED',
                              'rashtrapatibhawangarage': 'Wh_RECEIVED',
                              'oldjnuclubbuilding': 'Wh_RECEIVED',
                              'oldjnulibraryandclubbuilding':'Wh_RECEIVED',
                              'hacgocomplex':'Wh_RECEIVED',
                              'rbl':'Wh_DELIVERED',
                              'ranetrw':'Wh_RECEIVED',
                              'gmr': 'Wh_RECEIVED',
                              'thunganivillage':'Wh_RECEIVED',
                              'shramsaktibhawan':'Wh_RECEIVED',
                              'unipatch':'Wh_RECEIVED',
                              'rrkabel':'Wh_RECEIVED',
                              'uran':'Wh_RECEIVED',
                              'councilhouse':'Wh_RECEIVED',
                              'mohanestate':'Wh_RECEIVED',
                              'goipresssantragachi':'Wh_RECEIVED',
                              'gisochurchlane':'Wh_RECEIVED',
                              'dgcis':'Wh_RECEIVED',
                              'goiformstoretemplestreet':'Wh_RECEIVED',
                              'ezcc':'Wh_RECEIVED',
                              'gupl': 'Wh_RECEIVED',
                              'ranergy':'Wh_RECEIVED',
                              'lohia':'Wh_FINAL',
                              'pavagada':'Wh_DELIVERED',
                              'demochemtrols':'Wh_RECEIVED',
                              'evps':'Wh_DELIVERED',
                              'dlfsarojninagar':'Wh_RECEIVED',
                              'vjti':'Wh_RECEIVED',
                              'bajajmotors':'Wh_RECEIVED',
                              'khaitanpublicschool': 'Wh_RECEIVED',
                              'airportdepot2': 'Wh_RECEIVED',
                              'ecopark': 'Wh_RECEIVED',
                              'govindpuri': 'Wh_RECEIVED',
                              'oldfaridabad': 'Wh_RECEIVED',
                              'jaivinsacademy': 'Wh_RECEIVED',
                              'ponnitapes': 'Wh_RECEIVED',
                              'demoh': 'Wh_RECEIVED',
                              'shiningsunpower':'Wh_DELIVERED',
                              'jppl1': 'DAILY_ENERGY',
                              'jppl2': 'DAILY_ENERGY',
                              'jppllalitpur': 'Wh_DELIVERED',
                              'omya': 'Wh_RECEIVED',
                              'pavagadastarkraft': 'Wh_DELIVERED',
                              'lovelyres': 'Wh_RECEIVED',
                              'jeevanjoty': 'Wh_RECEIVED',
                              'ioclkadapa3mwp': 'Wh_RECEIVED',
                              'instaproducts':'Wh_DELIVERED',
                              'adpacklimited':'Wh_DELIVERED',
                              'alkemmandwa': 'Wh_DELIVERED',
                              'velammaledtrust': 'Wh_DELIVERED',
                              'bajajautoltd': 'Wh_DELIVERED',
                              'sedam145mw': 'Wh_DELIVERED',
                              'kmch': 'Wh_RECEIVED'}

TOTAL_ENERGY_CALCULATION_STREAMS = {'jppl1': 'Wh_DELIVERED',
                                    'jppl2': 'Wh_DELIVERED'}

ENERGY_METER_STREAM_UNITS = {'waaneep' : 'MWH',
                             'yerangiligi': 'MWH',
                             'gsi':'W',
                             'nizampalace':'W',
                             'thunganivillage':'MWH',
                             'lohia': 'MWH',
                             'demochemtrols': 'MWH',
                             'shiningsunpower':'MWH'}

ENERGY_METER_STREAM_UNIT_FACTOR = {'MWH' : 1000,
                                   'W': 0.001}


IRRADIATION_UNITS = {"airportmetrodepot":"W/m2"}

IRRADIATION_UNITS_FACTOR = {"W/m2":1000}

TOTAL_OPERATIONAL_HOURS_UNITS = {'asun': 'hour',
                                 'councilhouse': 'hour',
                                 'demochemtrols':'hour',
                                 'dgcis': 'hour',
                                 'ezcc': 'hour',
                                 'gmhssec45c': 'hour',
                                 'grps': 'hour',
                                 'gsi': 'hour',
                                 'hacgocomplex': 'hour',
                                 'hyderabadhouse': 'hour',
                                 'ivorysoap': 'hour',
                                 'jsecsite1': 'hour',
                                 'jsecsite2': 'hour',
                                 'lohia': 'hour',
                                 'nappino100kw': 'hour',
                                 'nappino50kw': 'hour',
                                 'nizampalace': 'hour',
                                 'oldjnuclubbuilding': 'hour',
                                 'oldjnulibraryandclubbuilding': 'hour',
                                 'rashtrapatibhawanauditorium': 'hour',
                                 'rashtrapatibhawangarage': 'hour',
                                 'rdil': 'hour',
                                 'sardarpatelbhawan': 'hour',
                                 'shramsaktibhawan': 'hour',
                                 'sonablw': 'hour',
                                 'thunganivillage': 'hour',
                                 'yerangiligi': 'hour'}

TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION  = {'hour': 1,
                                             'minute': 60,
                                             'second': 3600}

LAST_CAPACITY_DAYS = 28


# left side DataglenClient/Organization Slug
# right side FTP Webdyn Client slug
DGC_FTP_CLIENT_MAPPING = {'chemtrols-solar':'chemtrols',
                          'harsha-abakus-solar':'harshaabakus',
                          'hero-future-energies':'heroenergies',
                          'renew-power':'renewdg',
                          'sterlingandwilson':'sterling',
                          'test':'test',
                          'demo-solar-organization': 'renewdg2',
                          'amp-solar': 'ampsolar',
                          'asun-solar':'asun',
                          'sri-power': 'sripower',
                          'gensol':'gensol',
                          'sanjeevani-solar':'micromax',
                          'waaree-energies-ltd':'waaree',
                          'winnerspitch':'winnerspitch',
                          'sandhare-ecogreen':'secogreen',
                          'concept-powertech':'conceptp',
                          'vibgyor-energy':'vibgyor',
                          'tata-power': 'tpower',
                          'suryaday':'suryaday',
                          'opower':'opower',
                          'topzon':'topzon',
                          'solfreedom':'solfreedom',
                          'tecso-global':'tecso',
                          'galileo-solar':'gsolar',
                          'cleanmax-solar':'cleanmax',
                          'highground':'highground',
                          'ellumesolar':'ellumesolar',
                          'erigeronenergy':'erigeronenergy',
                          'sunpureenergy':'sunpureenergy',
                          'rays-power-infra': 'rayspower',
                          'sunfront': 'sunfront',
                          'comfonomics': 'environomics',
                          'tmtl-eicher': 'eicher',
                          'panasian': 'panasian',
                          'evpv': 'evpv',
                          'soltek': 'soltechenergy',
                          'proinso': 'proinso',
                          'swelect-systems': 'swelect',
                          'rockford-solar': 'rockford-solar',
                          'paerenewables': 'paerenewables',
                          'mytrahenergy': 'mytrahenergy',
                          'greenaltsol': 'greenaltsol',
                          'khotari-solar': 'ksolar',
                          'jackson': 'jackson',
                          'thermax': 'thermax',
                          'atria': 'atria',
                          'bluebird': 'bluebird'}

INVERTERS_COMPARISON_STANDARD_DEVIATION = 2
INVERTERS_COMPARISON_PERCENTAGE = 10
MPPTS_COMPARISON_STANDARD_DEVIATION = 2
MPPTS_COMPARISON_PERCENTAGE = 10
AJBS_COMPARISON_STANDARD_DEVIATION = 2
AJBS_COMPARISON_PERCENTAGE = 10

''' PLANT WMS '''
WMS_STREAMS =  [('IRRADIATION', 'FLOAT'),
                ('IRRADIATION_2', 'FLOAT'),
                ('IRRADIATION_3', 'FLOAT'),
                ('IRRADIATION_4', 'FLOAT'),
                ('AMBIENT_TEMPERATURE', 'FLOAT'),
                ('AMBIENT_TEMPERATURE_2', 'FLOAT'),
                ('AMBIENT_TEMPERATURE_3', 'FLOAT'),
                ('AMBIENT_TEMPERATURE_4', 'FLOAT'),
                ('MODULE_TEMPERATURE', 'FLOAT'),
                ('MODULE_TEMPERATURE_2', 'FLOAT'),
                ('MODULE_TEMPERATURE_3', 'FLOAT'),
                ('MODULE_TEMPERATURE_4', 'FLOAT'),
                ('WINDSPEED', 'FLOAT'),
                ('WINDSPEED_2', 'FLOAT'),
                ('WINDSPEED_3', 'FLOAT'),
                ('WINDSPEED_4', 'FLOAT'),
                ('WIND_DIRECTION', 'FLOAT'),
                ('WIND_DIRECTION_2', 'FLOAT'),
                ('WIND_DIRECTION_3', 'FLOAT'),
                ('WIND_DIRECTION_4', 'FLOAT')]

WMS_STATUS_PARAMETERS = [('LIVE', 'BOOLEAN'),
                              ('AGGREGATED', 'BOOLEAN')]

WMS_INPUT_PARAMETERS = [('TIMESTAMP', 'TIMESTAMP'),
                             ('AGGREGATED_START_TIME', 'TIMESTAMP'),
                             ('AGGREGATED_END_TIME', 'TIMESTAMP'),
                             ('AGGREGATED_COUNT', 'FLOAT')]
