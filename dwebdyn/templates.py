
DEVICE_TYPES = [('INV', 'INV'), ('MODBUS', 'MODBUS'), ('IO, IO')]


# TODO NOTE : EACH MANUFACTURER SHOULD HAVE A STANDARD DEF FILE BASED ON WHICH A TEMPLATE IS DEFINED
# TODO ADDING A NEW MANUFACTURER - DEF FILE - TEMPLATE will be manual for now


# inverters manufacturers
INVERTERS_MANUFACTURERS = [
    ('DELTA', 'DELTA'),
    ('SUNGROW', 'SUNGROW'),
    ('SMA', 'SMA'),
    ('SMA_WR10TL09', 'SMA_WR10TL09'),
    ('SMA_WR10TL11', 'SMA_WR10TL11'),
    ('SMA_WR10TL12', 'SMA_WR10TL12'),
    ('SMA_WR7KRP04', 'SMA_WR7KRP04'),
    ('SMA_WR7KRP07', 'SMA_WR7KRP07'),
    ('SMA_WR7KRP12', 'SMA_WR7KRP12'),
    ('Kaco: Powador', 'Kaco: Powador'),
    ('Kaco: Powador: Extended', 'Kaco: Powador: Extended'),
    ('WD008C1B_INV_WRHM6Y95', 'WD008C1B_INV_WRHM6Y95'),
    ('REFUSOL', 'REFUSOL')
]

# devices templates - fields to be picked up
INV_TEMPLATES = {
    'DELTA': {
        'DATA': {26: 'AC_VOLTAGE_R', 27:'CURRENT_R', 28:'ACTIVE_POWER', 29:'AC_FREQUENCY_R', 35:'APPARENT_POWER_R',
                 43:'AC_VOLTAGE_Y', 44: 'CURRENT_Y', 45: 'ACTIVE_POWER', 46: 'AC_FREQUENCY_Y', 52: 'APPARENT_POWER_Y',
                 60: 'AC_VOLTAGE_B', 61: 'CURRENT_B', 62: 'ACTIVE_POWER', 63: 'AC_FREQUENCY_B', 69: 'APPARENT_POWER_B',
                 130: 'DC_POWER', 147: 'DC_POWER', 194: 'DAILY_YIELD', 196: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'SUNGROW': {},
    'Kaco: Powador': {
        'DATA': {2: 'SOLAR_STATUS', 3:'DC_VOLTAGE', 4:'DC_CURRENT', 5:'AC_VOLTAGE_R', 6:'CURRENT_R', 7:'AC_VOLTAGE_Y',
                 8: 'CURRENT_Y', 9:'AC_VOLTAGE_B', 10:'CURRENT_B',
                 11: 'DC_POWER', 12:'ACTIVE_POWER', 15:'DAILY_YIELD'},
        'ERRORS': [2]
    },
    'Kaco: Powador: Extended': {
        'DATA': {2: 'SOLAR_STATUS', 3:'DC_VOLTAGE', 4:'DC_CURRENT', 9:'AC_VOLTAGE_R', 10:'CURRENT_R', 11:'AC_VOLTAGE_Y',
                 12: 'CURRENT_Y', 13:'AC_VOLTAGE_B', 14:'CURRENT_B',
                 15: 'DC_POWER', 16:'ACTIVE_POWER', 19:'DAILY_YIELD'},
        'ERRORS': [2]
    },
    'REFUSOL': {
        'DATA': {3: 'AC_VOLTAGE_R', 7:'CURRENT_R', 1:'ACTIVE_POWER', 10:'AC_FREQUENCY_R',
                 4:'AC_VOLTAGE_Y', 8: 'CURRENT_Y', 11: 'AC_FREQUENCY_Y', 5: 'AC_VOLTAGE_B', 9: 'CURRENT_B',
                 12: 'AC_FREQUENCY_B', 13: 'DC_POWER', 14:'DC_VOLTAGE', 15:'DC_CURRENT',
                 20: 'DAILY_YIELD', 21: 'TOTAL_YIELD', 22: 'TOTAL_OPERATIONAL_HOURS'},
        'ERRORS': []
    },

    'SMA_WR10TL09': {
        'DATA': {72: 'ACTIVE_POWER', 82: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'SMA_WR10TL11': {
        'DATA': {72: 'ACTIVE_POWER', 82: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'SMA_WR10TL12': {
        'DATA': {73: 'ACTIVE_POWER', 82: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'SMA_WR7KRP04': {
        'DATA': {86: 'ACTIVE_POWER', 99: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'SMA_WR7KRP07': {
        'DATA': {91: 'ACTIVE_POWER', 104: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'SMA_WR7KRP12': {
        'DATA': {107: 'ACTIVE_POWER', 120: 'TOTAL_YIELD'},
        'ERRORS': []
    },

    'SMA': {
        'DATA': {110: 'ACTIVE_POWER', 113: 'TOTAL_YIELD'},
        'ERRORS': []
    },
    'WD008C1B_INV_WRHM6Y95' : {
        'DATA': {190: 'ACTIVE_POWER', 224: 'TOTAL_YIELD', 191: 'ACTIVE_POWER_R', 192: 'ACTIVE_POWER_Y', 193: 'ACTIVE_POWER_B',
                 194: 'AC_VOLTAGE_R', 195: 'AC_VOLTAGE_Y',196: 'AC_VOLTAGE_B',
                 197: 'CURRENT_R',198: 'CURRENT_Y',199: 'CURRENT_B',
                 202: 'APPARENT_POWER_R', 203: 'APPARENT_POWER_Y', 204: 'APPARENT_POWER_B',
                 206: 'REACTIVE_POWER_R', 207: 'REACTIVE_POWER_Y', 208: 'REACTIVE_POWER_B',
                 212: 'HEAT_SINK_TEMPERATURE', 243: 'SOLAR_STATUS'},
        'ERRORS': []
    }
}

INV_DEF_FILES = {
    'SMA': '/var/www/dwebdyn/DEF/INV/WD008A47_INV_WRHM6Y94.ini',
    'KACO: POWADOR': '/var/www/dwebdyn/DEF/INV/WD008D94_INV_50kH3P.ini',
    'Kaco: Powador: Extended': '/var/www/dwebdyn/DEF/INV/WD008D94_INV_50kH3P.ini',
}

# TODO NOTE : EACH MANUFACTURER SHOULD HAVE A STANDARD DEF FILE BASED ON WHICH A TEMPLATE IS DEFINED
# TODO ADDING A NEW MANUFACTURER - DEF FILE - TEMPLATE will be manual for now

MODBUS_MANUFACTURERS = [
    ('DELTA', 'DELTA'),
    ('SUNGROW', 'SUNGROW'),
    ('SECURE_ELITE_440_446', 'Secure_Elite_440_446'),
    ('SECURE_ELITE_440_443', 'Secure_Elite_440_443'),
    ('SCHNEIDER_EM6436', 'Schneider_EM6436'),
    ('SCHNEIDER_EM6430', 'Schneider_EM6430'),
    ('SCHNEIDER_EM6400', 'Schneider_EM6400'),
    ('HENSEL', 'Hensel'),
    ('MODBUS_SATEC', 'Modbus_Satec'),
    ('ABB', 'ABB'),
    ('ELMEASURE', 'Elmeasure'),
    ('SMA', 'SMA'),
    ('MODBUS_PYRANOMETER', 'MODBUS_Pyranometer'),
    ('WMS', 'WMS'),
    ('LNT', 'LNT'),
    ('MODBUS_MICROLYTE', 'MODBUS_Microlyte'),
    ('RAYCHEM_SCB','Raychem_SCB'),
    ('IDSITE_SCHNEIDER_CONEXT_CORE_XC','IDSITE_SCHNEIDER_CONEXT_CORE_XC'),
    ('SCB_MS', 'SCB_MS'),
    ('TRINITY_MFM', 'TRINITY_MFM'),
    ('MODBUS_INV_HUAWEI_33K_SUN2000', 'MODBUS_INV_HUAWEI_33k_SUN2000'),
    ('STP_25', 'STP_25'),
    ('SMA_STP_60_IM', 'SMA_STP_60_IM'),
    ('MODBUS_IRRADIANCE', 'Modbus_Irradiance'),
    ('STP_25_KMRL_WORKSHOP', 'STP_25_KMRL_WORKSHOP'),
    ('WAAREE', 'WAAREE'),
    ('ZEVERSOLAR', 'Zeversolar'),
    ('TATA', 'Tata')

]

MODBUS_Name_Aliases = {
    'micromex_inv' : 'MODBUS_MICROLYTE',
    'huawei_1': 'MODBUS_INV_HUAWEI_33K_SUN2000'
}

MODBUS_DEF_FILES = {
    'DELTA':'/var/www/dwebdyn/DEF/MODBUS/MODBUS_DELTA.ini',
    'SUNGROW':'/var/www/dwebdyn/DEF/MODBUS/MODBUS_INV_SUNGROW_50KTL_M.ini',
    'SECURE_ELITE_440_446':'/var/www/dwebdyn/DEF/MODBUS/Secure_Elite_440_446.ini',
    'SECURE_ELITE_440_443':'/var/www/dwebdyn/DEF/MODBUS/Secure_Elite_440_443.ini',
    'SCHNEIDER_EM6436':'/var/www/dwebdyn/DEF/MODBUS/Schneider_EM6436.ini',
    'SCHNEIDER_EM6430':'/var/www/dwebdyn/DEF/MODBUS/Schneider_EM6436.ini',
    'SCHNEIDER_EM6400':'/var/www/dwebdyn/DEF/MODBUS/Schneider_EM6436.ini',
    'HENSEL':'/var/www/dwebdyn/DEF/MODBUS/Hensel_SCB.ini',
    'ABB':'/var/www/dwebdyn/DEF/MODBUS/Modbus_INV_ABB_1MW.ini',
    'ELMEASURE':'/var/www/dwebdyn/DEF/MODBUS/Test_Elmeasure.ini',
    'SMA': '/var/www/dwebdyn/DEF/MODBUS/STP_25.ini',
    'MODBUS_MICROLYTE': '/var/www/dwebdyn/DEF/MODBUS/MODBUS_Microlyte.ini',
    'RAYCHEM_SCB': '/var/www/dwebdyn/DEF/MODBUS/Raychem.ini',
    'SCB_MS': '/var/www/dwebdyn/DEF/MODBUS/SCB_MS.ini',
    'IDSITE_SCHNEIDER_CONEXT_CORE_XC': '',
    'TRINITY_MFM': '/var/www/dwebdyn/DEF/MODBUS/Trinity_MFM.ini',
    'MODBUS_INV_HUAWEI_33K_SUN2000': '/var/www/dwebdyn/DEF/MODBUS/MODBUS_INV_HUAWEI_33k_SUN2000.ini',
    'STP_25': '/var/www/dwebdyn/DEF/MODBUS/STP_25.ini',
    'SMA_STP_60_IM': '/var/www/dwebdyn/DEF/MODBUS/STP_25.ini',
    'MODBUS_SATEC': '/var/www/dwebdyn/DEF/MODBUS/Test_Elmeasure.ini',
    'MODBUS_IRRADIANCE': '/var/www/dwebdyn/DEF/MODBUS/Modbus_Irradiance.ini',
    'STP_25_KMRL_WORKSHOP': '/var/www/dwebdyn/DEF/MODBUS/STP_25.ini',
    'WAAREE': '/var/www/dwebdyn/DEF/MODBUS/Modbus_Waaree.ini',
    'ZEVERSOLAR': '/var/www/dwebdyn/DEF/MODBUS/Modbus_Waaree.ini',
    'TATA': '/var/www/dwebdyn/DEF/MODBUS/Modbus_Waaree.ini'

}

MODBUS_TEMPLATES = {
    'DELTA': {
            'DATA': {
                15: 'SOLAR_STATUS', 18: 'ACTIVE_POWER', 19: 'AC_VOLTAGE_R',
                20: 'CURRENT_R', 21: 'ACTIVE_POWER_R', 22: 'AC_FREQUENCY_R',
                23: 'AC_VOLTAGE_Y', 24: 'CURRENT_Y', 25: 'ACTIVE_POWER_Y',
                26: 'AC_FREQUENCY_Y', 27: 'AC_VOLTAGE_B', 28: 'CURRENT_B',
                29: 'ACTIVE_POWER_B', 30: 'AC_FREQUENCY_B', 31: 'DC_POWER',
                32: 'MPPT1_DC_VOLTAGE', 33: 'MPPT1_DC_CURRENT', 34: 'MPPT1_DC_POWER',
                35: 'MPPT2_DC_VOLTAGE', 36: 'MPPT2_DC_CURRENT', 37: 'MPPT2_DC_POWER',
                38: 'DAILY_YIELD', 39: 'TOTAL_OPERATIONAL_HOURS', 40: 'TOTAL_YIELD',
                44: 'HEAT_SINK_TEMPERATURE'
             },
             # status values in strings which mean an error
            'SOLAR_STATUS_ERRORS' : [4.0],
             # main field to read and upload in case of an error
            'ERROR_FIELD' : [52],
             # other errors to log
            'OTHER_ERRORS': [51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]
    },
    'ZEVERSOLAR': {
            'DATA': {
                1: 'DAILY_YIELD', 2: 'TOTAL_YIELD',
                3: 'MPPT1_DC_VOLTAGE', 4: 'MPPT1_DC_CURRENT',
                5: 'MPPT2_DC_VOLTAGE', 6: 'MPPT2_DC_CURRENT',
                7: 'MPPT3_DC_VOLTAGE', 8: 'MPPT3_DC_CURRENT',
                9: 'AC_VOLTAGE_R', 10: 'CURRENT_R',
                11: 'AC_VOLTAGE_Y', 12: 'CURRENT_Y',
                13: 'AC_VOLTAGE_B', 14: 'CURRENT_B', 15: 'AC_FREQUENCY',
                18: 'SOLAR_STATUS', 16: 'ACTIVE_POWER'
             },
             # status values in strings which mean an error
            'SOLAR_STATUS_ERRORS' : [],
             # main field to read and upload in case of an error
            'ERROR_FIELD' : [],
             # other errors to log
            'OTHER_ERRORS': []
    },
    'TATA': {
            'DATA': {
                1: 'AC_VOLTAGE', 2: 'CURRENT', 3: 'AC_FREQUENCY', 4: 'ACTIVE_POWER',
                5: 'REACTIVE_POWER', 6: 'MPPT1_DC_VOLTAGE', 7: 'MPPT1_DC_CURRENT', 8: 'MPPT1_DC_POWER',
                10: 'TOTAL_YIELD', 11: 'SOLAR_STATUS', 12: 'HEAT_SINK_TEMPERATURE', 13: 'CUBICLE_TEMPERATURE'

            },
             # status values in strings which mean an error
            'SOLAR_STATUS_ERRORS' : [],
             # main field to read and upload in case of an error
            'ERROR_FIELD' : [],
             # other errors to log
            'OTHER_ERRORS': []
    },
    'WAAREE' : {
            'DATA': {1:'MPPT1_DC_VOLTAGE',2:'MPPT2_DC_VOLTAGE',
                     3: 'MPPT1_DC_CURRENT', 4:'MPPT2_DC_CURRENT',
                     17: 'DAILY_YIELD', 18: 'TOTAL_YIELD', 14: 'ACTIVE_POWER',
                     5: 'AC_VOLTAGE_R', 6: 'AC_VOLTAGE_Y', 7:'AC_VOLTAGE_B',
                     8: 'CURRENT_R', 9:'CURRENT_Y', 10: 'CURRENT_B',
                     16:'HEAT_SINK_TEMPERATURE',15:'SOLAR_STATUS',
                     11: 'AC_FREQUENCY_R', 12: 'AC_FREQUENCY_Y', 13: 'AC_FREQUENCY_B'},
            # status values in strings which mean an error
            'SOLAR_STATUS_ERRORS': [],
            # main field to read and upload in case of an error
            'ERROR_FIELD': [],
            # other errors to log
            'OTHER_ERRORS': []

    },
    'SMA_STP_60_IM': {
            'DATA': {
                3: 'CURRENT', 4: 'CURRENT_R', 5: 'CURRENT_Y', 6: 'CURRENT_B',
                # 8: '', 9: '', 10: '',
                11: 'AC_VOLTAGE_R', 12: 'AC_VOLTAGE_Y', 13: 'AC_VOLTAGE_B',
                15: 'ACTIVE_POWER', 17: 'AC_FREQUENCY', 19: 'APPARENT_POWER', 20: 'REACTIVE_POWER',
                23: 'POWER_FACTOR', 25: 'TOTAL_YIELD', 27: 'DC_CURRENT', 29: 'DC_VOLTAGE', 31: 'DC_POWER',
                38: 'SOLAR_STATUS',
            },
            # status values in strings which mean an error
            'SOLAR_STATUS_ERRORS': [],
            # main field to read and upload in case of an error
            'ERROR_FIELD': [],
            # other errors to log
            'OTHER_ERRORS': []
    },
    'SUNGROW': {
            'DATA' : {
                4: 'DAILY_YIELD', 5: 'TOTAL_YIELD', 6: 'MPPT1_DC_VOLTAGE', 7: 'MPPT1_DC_CURRENT',
                8: 'MPPT2_DC_VOLTAGE', 9: 'MPPT2_DC_CURRENT', 10: 'MPPT3_DC_VOLTAGE',
                11: 'MPPT3_DC_CURRENT', 12: 'DC_POWER',
                13: 'AC_VOLTAGE_R', 14: 'AC_VOLTAGE_Y',
                15: 'AC_VOLTAGE_B', 16: 'CURRENT_R', 17: 'CURRENT_Y',
                18: 'CURRENT_B', 19: 'ACTIVE_POWER', 20: 'AC_FREQUENCY',
                21: 'MPPT4_DC_VOLTAGE', 22: 'MPPT4_DC_CURRENT', 23: 'SOLAR_STATUS',
                24: 'TOTAL_OPERATIONAL_HOURS'
            },
            'SOLAR_STATUS_ERRORS': [32768, 4608, 4864, 5120, 5376, 9472, 5376, 9472, 5632, 13824,
                                    21760, 33024, 33280, 37120],
            'ERROR_FIELD': [31],
            'OTHER_ERRORS': []
    },
    'SECURE_ELITE_440_446': {
            'DATA': {
                1 : 'VR_PHASE', 2 : 'VY_PHASE', 3 : 'VB_PHASE', 4 : 'VLN_AVG', 5 : 'VRY_PHASE',
                6 : 'VYB_PHASE', 7 : 'VBR_PHASE', 8 : 'C_R_PHASE', 9 : 'C_Y_PHASE', 10 : 'C_B_PHASE',
                11 : 'CURRENT_TOTAL', 12 : 'PF_R_PHASE', 13 : 'PF_Y_PHASE', 14 : 'PF_B_PHASE', 15 : 'PF_AVG',
                16 : 'WATTS_R_PHASE', 17 : 'WATTS_Y_PHASE', 18 : 'WATTS_B_PHASE',
                19 : 'WATT_TOTAL', 20 : 'VAR_R_PHASE', 21 : 'VAR_Y_PHASE',
                22 : 'VAR_B_PHASE', 23 : 'VAR_TOTAL', 24 : 'VA_R_PHASE', 25 : 'VA_Y_PHASE',
                26 : 'VA_B_PHASE', 27 : 'VA_TOTAL', 28 : 'Frequency', 29 : 'Wh_RECEIVED', 30 : 'Wh_DELIVERED',
                31 : 'VAh_DELIVERED', 32 : 'VARh_IMPEDENCE_RECEIVED', 33 : 'VARh_IMPEDENCE_DELIVERED',
            },
            'ERRORS': []},
    'SECURE_ELITE_440_443': {
            'DATA': {
                1: 'Frequency', 2: 'Wh_RECEIVED', 4: 'WATT_TOTAL',
                5: 'VR_PHASE', 6: 'VY_PHASE', 7: 'VB_PHASE',
                8: 'VLN_AVG', 9: 'VRY_PHASE', 10: 'VYB_PHASE', 11: 'VBR_PHASE',
                12: 'C_R_PHASE', 13: 'C_Y_PHASE', 14: 'C_B_PHASE',
                15: 'CURRENT_TOTAL', 16: 'PF_AVG'
            },
            'ERRORS': []},
    'SCHNEIDER_EM6436': {
            'DATA': {
                1: 'Wh_RECEIVED', 2: 'WATT_TOTAL', 3 : 'VR_PHASE', 4 : 'VY_PHASE', 5 : 'VB_PHASE', 7: 'Frequency',
                8: 'VRY_PHASE', 9: 'VYB_PHASE', 10: 'VBR_PHASE', 11: 'PF_AVG',
                12: 'C_R_PHASE', 13: 'C_Y_PHASE', 14: 'C_B_PHASE',
                15 : 'PF_R_PHASE', 16 : 'PF_Y_PHASE', 17 : 'PF_B_PHASE'
            },
            'ERRORS': []},
    'SCHNEIDER_EM6430': {
            'DATA': {
                1: 'Wh_RECEIVED',
                2: 'WATT_TOTAL'
            },
            'ERRORS': []},
    'SCHNEIDER_EM6400': {
            'DATA': {
                1: 'Wh_RECEIVED',
                2: 'WATT_TOTAL'
            },
            'ERRORS': []},
    'TRINITY_MFM': {
            'DATA': {
                2: 'WATT_TOTAL',
                4: 'PF_AVG',
                5: 'Wh_RECEIVED',
                6: 'Frequency',
                7: 'VRY_PHASE', 8: 'VYB_PHASE', 9: 'VBR_PHASE',
                10 : 'VR_PHASE', 11 : 'VY_PHASE', 12 : 'VB_PHASE',
                13: 'C_R_PHASE', 14: 'C_Y_PHASE', 15: 'C_B_PHASE',
            },
            'ERRORS': []},
    'HENSEL': {
        'DATA' : {
            1 : 'S1', 2 : 'S2', 3 : 'S3', 4 : 'S4', 5 : 'S5', 6 : 'S6', 7 : 'S7', 8 : 'S8',
            9 : 'S9', 10 : 'S10', 11 : 'S11', 12 : 'S12', 13 : 'S13', 14 : 'S14', 15 : 'S15',
            16 : 'S16', 17 : 'S17', 18 : 'S18', 19 : 'S19', 20 : 'S20', 21 : 'S21', 22 : 'S22',
            23 : 'S23', 24 : 'S24', 25 : 'VOLTAGE', 26 : 'TEMP2', 27 : 'TEMP3', 28 : 'TEMP1',
            29 : 'DI_STATUS_1', 30 : 'DI_STATUS_2', 31 : 'DI_STATUS_3', 32 : 'DI_STATUS_4',
            33 : 'DI_STATUS_5', 34 : 'DO_STATUS_1', 35 : 'DO_STATUS_2',
        },
        'ERRORS' : []
    },
    'MODBUS_SATEC' : {
        'DATA' : {1: 'VR_PHASE', 2: 'VY_PHASE', 3: 'VB_PHASE', 4: 'C_R_PHASE', 5: 'C_Y_PHASE', 6: 'C_B_PHASE',
                  7: 'WATTS_R_PHASE', 8: 'WATTS_Y_PHASE', 9: 'WATTS_B_PHASE', 10: 'VAR_R_PHASE', 11: 'VAR_Y_PHASE', 12: 'VAR_B_PHASE',
                  13: 'VA_R_PHASE', 14: 'VA_Y_PHASE', 15: 'VA_B_PHASE', 16: 'PF_R_PHASE', 17: 'PF_Y_PHASE', 18: 'PF_B_PHASE',
                  31: 'VRY_PHASE', 32: 'VYB_PHASE', 33: 'VBR_PHASE', 34: 'WATT_TOTAL', 35: 'VAR_TOTAL', 36: 'VA_TOTAL', 37: 'PF_AVG',
                  38: 'Wh_RECEIVED', 39: 'Wh_DELIVERED', 42: 'VAh_RECEIVED', 43: 'VAh_DELIVERED', 44: 'Frequency'},
        'ERRORS': {},
    },
    'ABB': {
        'DATA' : {
            1 : 'AC_VOLTAGE_R', 2 : 'AC_VOLTAGE_Y', 3 : 'AC_VOLTAGE_B', 4 : 'CURRENT_R',
            5 : 'CURRENT_Y', 6 : 'CURRENT_B', 7 : 'ACTIVE_POWER', 8 : 'AC_POWER_PERCENT',
            9 : 'AC_FREQUENCY', 10 : 'POWER_FACTOR', 11 : 'REACTIVE_POWER', 12: 'GRID_IMPEDENCE',
            13: 'INSULATION_IMPEDENCE', 14: 'DC_VOLTAGE', 15 : 'DC_CURRENT',
            16 : 'DC_POWER', 17 : 'INSIDE_TEMPERATURE', 18 : 'SOLAR_STATUS', 19 : 'INVERTER_FAILURE',
            20 : 'ALARM_ACTIVE', 22 : 'TOTAL_OPERATIONAL_HOURS', 23 : 'TOTAL_YIELD',
        },
        'ERRORS' : []
    },
    'ELMEASURE': {
        'DATA' : {
            1 : 'WATT_TOTAL', 2 : 'WATTS_R_PHASE', 3 : 'WATTS_Y_PHASE', 4 : 'WATTS_B_PHASE',
            5 : 'VAR_TOTAL', 6 : 'VAR_R_PHASE', 7 : 'VAR_Y_PHASE', 8 : 'VAR_B_PHASE', 9 : 'PF_AVG',
            10 : 'PF_R_PHASE', 11 : 'PF_Y_PHASE', 12 : 'PF_B_PHASE', 13 : 'VA_TOTAL', 14 : 'VA_R_PHASE',
            15 : 'VA_Y_PHASE', 16 : 'VA_B_PHASE', 17 : 'VLL_AVG', 18 : 'VRY_PHASE', 19 : 'VYB_PHASE',
            20 : 'VBR_PHASE', 21 : 'VLN_AVG', 22 : 'VR_PHASE', 23 : 'VY_PHASE', 24 : 'VB_PHASE',
            25 : 'CURRENT_TOTAL', 26 : 'C_R_PHASE', 27 : 'C_Y_PHASE', 28 : 'C_B_PHASE', 29 : 'Frequency',
            30 : 'Wh_RECEIVED', 31 : 'VAh_RECEIVED', 32 : 'VARh_IMPEDENCE_RECEIVED', 33 : 'VARh_CAPACITANCE_RECEIVED',
            34 : 'Wh_DELIVERED', 35 : 'VAh_DELIVERED', 36 : 'VARh_IMPEDENCE_DELIVERED', 37 : 'VARh_CAPACITANCE_DELIVERED'
        },
        'ERRORS' : []
    },
    'SMA': {
        'DATA': {3:'CURRENT',4:'CURRENT_R',5:'CURRENT_B',6:'CURRENT_Y',11:'AC_VOLTAGE_R',
                 12: 'AC_VOLTAGE_B',13:'AC_VOLTAGE_Y',15:'ACTIVE_POWER',17:'AC_FREQUENCY',
                 19: 'APPARENT_POWER',21:'REACTIVE_POWER',23:'POWER_FACTOR',25:'TOTAL_YIELD',27:'DC_CURRENT',
                 29: 'DC_VOLTAGE',31:'DC_POWER',34:'HEAT_SINK_TEMPERATURE',38:'SOLAR_STATUS'},
        'ERRORS': []
    },
    'MODBUS_PYRANOMETER': {
        'DATA': {6: 'IRRADIATION'},
        'ERRORS': []
    },
    'MODBUS_IRRADIANCE' : {
        'DATA': {5: 'IRRADIATION'},
        'ERRORS' : []
    },
    'WMS': {
        'DATA' : {
            1: 'WINDSPEED_RAW',
            2: 'WIND_DIRECTION_RAW',
            3: 'AMBIENT_TEMPERATURE_RAW',
            4: 'MODULE_TEMPERATURE2_RAW',
            5: 'MODULE_TEMPERATURE_RAW',
            6: 'MODULE_TEMPERATURE3_RAW',
            7: 'MODULE_TEMPERATURE4_RAW'
        },
        'ERRORS': []
    },
    'LNT': {
        'DATA': {
            22: 'WATT_TOTAL',
            25: 'Frequency',
            26: 'Wh_RECEIVED'
        },
        'ERRORS': [

        ]
    },
    'MODBUS_MICROLYTE' : {
        'DATA' : {6: 'ACTIVE_POWER', 7: 'DC_POWER', 8: 'TOTAL_YIELD',
                  #9: 'ENERGY_CURRENT_MONTH', 10:'ENERGY_PREVIOUS_MONTH',
                  11: 'DAILY_YIELD',
                  #12:'ENERGY_YESTERDAY',
                  13: 'MPPT1_DC_VOLTAGE', 14: 'MPPT1_DC_CURRENT', 15: 'MPPT2_DC_VOLTAGE',
                  16: 'MPPT2_DC_CURRENT', 17: 'MPPT3_DC_VOLTAGE', 18: 'MPPT3_DC_CURRENT',
                  19: 'MPPT4_DC_VOLTAGE', 20: 'MPPT4_DC_CURRENT', 21: 'AC_VOLTAGE_R',
                  22: 'AC_VOLTAGE_Y', 23: 'AC_VOLTAGE_B', 24: 'CURRENT_R', 25: 'CURRENT_Y',
                  26: 'CURRENT_B', 27: 'AC_FREQUENCY', 28: 'SOLAR_STATUS'},
        # status values in strings which mean an error
        'SOLAR_STATUS_ERRORS': [4100, 4112, 4113, 4114, 4115, 4116, 4117, 4118, 4119, 4120,
                                4121, 4128, 4129, 4130, 4131, 4132, 4133, 4134, 4135, 4144,
                                4145, 4146, 4147, 4148, 4149, 4150, 4151, 4152, 4153, 4160,
                                4161, 4162, 4163, 4164, 4165, 4166, 4167, 4168],
        # main field to read and upload in case of an error
        'ERROR_FIELD': [28],
        # other errors to log
        'OTHER_ERRORS': []
    },
    'RAYCHEM_SCB': {
        'DATA': {1: 'DI_STATUS_1', 2: 'DI_STATUS_2', 3: 'DI_STATUS_3', 4: 'S1', 5: 'S2', 6: 'S3', 7: 'S4', 8: 'S5',
                 9: 'S6', 10: 'S7', 11: 'S8', 12: 'S9', 13: 'S10', 14: 'S11', 15: 'S12', 16: 'S13', 17: 'S14',
                 18: 'S15', 19: 'S16', 20: 'S17', 21: 'S18', 22: 'S19', 23: 'S20', 24: 'S21',  25: 'S22',  26: 'S23',
                 27: 'S24', 28: 'CURRENT', 29: 'VOLTAGE', 30: 'POWER', 31: 'TEMP1', 32: 'TEMP2'},
        # status values in strings which mean an error
        'SOLAR_STATUS_ERRORS': [],
        # main field to read and upload in case of an error
        'ERROR_FIELD': [],
        # other errors to log
        'OTHER_ERRORS': []

    },
    'SCB_MS': {
        'DATA': {1: 'CURRENT', 2: 'VOLTAGE', 7: 'POWER', 10: 'S1', 11: 'S2', 12: 'S3', 13: 'S4', 14: 'S5',
                 15: 'S6', 16: 'S7', 17: 'S8', 18: 'S9', 19: 'S10', 20: 'S11', 21: 'S12', 22: 'S13', 23: 'S14',
                 24: 'S15', 25: 'S16', 26: 'S17', 27: 'S18', 28: 'S19', 29: 'S20', 30: 'S21',  31: 'S22',  32: 'S23',
                 33: 'S24', 8: 'TEMP1', 9: 'TEMP2'},
        # status values in strings which mean an error
        'SOLAR_STATUS_ERRORS': [],
        # main field to read and upload in case of an error
        'ERROR_FIELD': [],
        # other errors to log
        'OTHER_ERRORS': []

    },
    'IDSITE_SCHNEIDER_CONEXT_CORE_XC':{
        'DATA': {1:'AC_FREQUENCY', 2:'TOTAL_YIELD', 3:'DAILY_YIELD', 5:'HEAT_SINK_TEMPERATURE', 8:'CURRENT',
                 9:'APPARENT_POWER', 10:'REACTIVE_POWER', 11:'AC_VOLTAGE_R', 12:'AC_VOLTAGE_Y', 13:'AC_VOLTAGE_B',
                 14:'CURRENT_R', 15: 'CURRENT_Y', 16:'CURRENT_B', 17:'ACTIVE_POWER',
                 19:'DC_CURRENT', 20:'DC_POWER'},
        # status values in strings which mean an error
        'SOLAR_STATUS_ERRORS': [],
        # main field to read and upload in case of an error
        'ERROR_FIELD': [],
        # other errors to log
        'OTHER_ERRORS': []
    },
    'MODBUS_INV_HUAWEI_33K_SUN2000' : {
        'DATA' : {1 : 'ACTIVE_POWER', 2 : 'REACTIVE_POWER', 3 : 'TOTAL_YIELD',
                  4 : 'AC_VOLTAGE_R', 5 : 'AC_VOLTAGE_Y', 6 : 'AC_VOLTAGE_B',
                  7 : 'CURRENT_R', 8 : 'CURRENT_Y', 9 : 'CURRENT_B',
                  10 : 'AC_FREQUENCY', 11 : 'POWER_FACTOR', 12 : 'INSIDE_TEMPERATURE', 16 : 'SOLAR_STATUS'},
        'SOLAR_STATUS_ERRORS':  [],
        'ERROR_FIELD': [],
        'OTHER_ERRORS': []
    },
    'STP_25' : {
        'DATA': {
            2: 'ACTIVE_POWER', 1: 'TOTAL_YIELD'
        },
        'SOLAR_STATUS_ERRORS': [],
        'ERROR_FIELD': [],
        'OTHER_ERRORS': []
    },
    'STP_25_KMRL_WORKSHOP': {
        'DATA': {
            3: 'ACTIVE_POWER', 1: 'TOTAL_YIELD',
            4: 'CURRENT_R', 5: 'CURRENT_Y', 6: 'CURRENT_B',
            7: 'AC_VOLTAGE_R', 8: 'AC_VOLTAGE_Y', 9: 'AC_VOLTAGE_B',
        },
        'SOLAR_STATUS_ERRORS': [],
        'ERROR_FIELD': [],
        'OTHER_ERRORS': []
    }

}

IO_CHOICES = [(1,1),
              (2,2),
              (3,3),
              (4,4),
              (5,5),
              (6,6),
              (7,7),
              (8,8)]

WRITE_LATENCY_MINS = 5
