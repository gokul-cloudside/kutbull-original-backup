import sys, json, requests
import time
# Define some parameters

SAMPLE_DATA = "49.96,220.970,0.092,0.037,0.000,0.024,5.371,5.372,0.017,89.021,02:38:00:04/05/15,18FE349F5C6E,BPlug_Radiostudio,608\r\n" \
              "asd,221.005,0.008,0.037,0.000,0.024,5.299,5.299,0.001,89.916,18:16:15:15/04/15,18FE349F5C6E,BPlug_Radiostudio,610\r\n"

DATA = "49.96,221.005,0.008,0.037,0.000,0.024,5.299,5.299,0.001,89.916,17:16:14:15/04/15,18FE349F5C6E,BPlug_Radiostudio,610\r\n"

NEW_DATA = "33.87,64.27,53.78,0,0,1007.63,63,-0.19,-0.19,14.02,1.68,16:35:07:07/04/15,18FE349B4CFF,BSense_RadioStudio,3\r\n"

R_DATA = u'50.11,235.607,0.088,0.033,0.000,0.027,6.276,6.276,0.000,89.962,13:16:51:24/06/15,18FE349B4C67,RSBplug_16,452\r\n' \
         u'50.10,235.683,0.202,0.033,0.000,0.027,6.369,6.373,0.032,88.186,13:16:52:24/06/15,18FE349B4C67,RSBplug_16,453\r\n' \
         u'50.10,235.704,0.144,0.033,0.000,0.027,6.429,6.430,0.022,88.718,13:16:53:24/06/15,18FE349B4C67,RSBplug_16,454\r\n' \
         u'50.10,235.754,0.126,0.033,0.000,0.026,6.206,6.207,0.020,88.833,13:16:54:24/06/15,18FE349B4C67,RSBplug_16,455\r\n' \
         u'50.11,235.432,0.083,0.033,0.000,0.026,6.009,6.010,0.014,89.206,13:16:55:24/06/15,18FE349B4C67,RSBplug_16,456\r\n' \
         u'50.11,235.580,0.013,0.033,0.000,0.026,6.116,6.116,0.002,89.874,13:16:56:24/06/15,18FE349B4C67,RSBplug_16,457\r\n' \
         u'50.09,235.703,0.017,0.033,0.000,0.026,6.134,6.134,0.003,89.845,13:16:57:24/06/15,18FE349B4C67,RSBplug_16,458\r\n' \
         u'50.11,235.580,0.013,0.033,0.000,0.026,6.116,6.116,0.002,89.874,13:16:58:24/06/15,18FE349B4C67,RSBplug_16,457\r\n' \
         u'50.11,235.580,0.013,0.033,0.000,0.026,6.116,6.116,0.002,89.874,13:16:59:24/06/15,18FE349B4C67,RSBplug_16,457\r\n' \
         u'50.11,235.580,0.013,0.033,0.000,0.026,6.116,6.116,0.002,89.874,13:17:00:24/06/15,18FE349B4C67,RSBplug_16,457\r\n'

RE_DATA = u'50.01,219.782,0.199,0.003,0.000,0.024,5.266,5.270,0.038,87.833,13:55:05:12/05/15,18FE34A04171,RSBplug_13,48\r\n' \
          u'49.99,219.731,0.021,0.003,0.000,0.023,5.014,5.014,0.004,89.761,13:55:07:12/05/15,18FE34A04171,RSBplug_13,49\r\n' \
          u'50.10,234.742,0.276,0.000,0.000,0.023,5.479,5.486,0.050,87.117,00:00:11:00/01/00,18FE34A04171,RSBplug_13,1\r\n' \
          u'50.11,234.809,0.046,0.000,0.000,0.022,5.105,6.039,0.034,88.050,00:00:14:00/01/00,18FE34A04171,RSBplug_13,2\r\n' \
          u'50.09,234.628,0.098,0.000,0.000,0.021,5.014,5.015,0.019,88.885,00:00:16:00/01/00,18FE34A04171,RSBplug_13,3\r\n' \
          u'50.07,234.821,0.034,0.000,0.000,0.021,4.948,4.948,0.007,89.605,00:00:22:00/01/00,18FE34A04171,RSBplug_13,4\r\n' \
          u'50.10,234.826,0.017,0.000,0.000,0.022,5.054,5.054,0.003,89.809,13:26:14:13/05/15,18FE34A04171,RSBplug_13,5\r\n' \
          u'50.09,234.698,0.068,0.000,0.000,0.021,5.033,5.034,0.014,89.221,13:26:16:13/05/15,18FE34A04171,RSBplug_13,6\r\n'
E = u'0.00,0.00,0.00,77.75,0.00,49.85,0.00,0.00,0.00,233.24,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.46,0.37,0.00,0.00,0.00,0,2111882,101,19:28:42:13/05/15,18FE34A03EAE,BSendRS_SriramDesk,3307\r\n'

SENSOR_NAME = "TEST"
FORMAT = "CSV" # One of XM/JS/CSV


RS_DATA = u'50.03,222.926,0.075,0.041,0.000,0.036,8.106,8.107,0.009,89.471,16:02:37:00/05/15,18FE349DF87D,BPlugRS_Induction,24\r\n' \
          u'50.03,223.087,0.029,0.042,0.000,0.037,8.220,8.220,0.022,88.744,16:02:47:00/05/15,18FE349DF87D,BPlugRS_Induction,25\r\n' \
          u'50.02,222.910,0.140,0.042,0.000,0.037,8.318,8.319,0.017,89.036,16:02:57:00/05/15,18FE349DF87D,BPlugRS_Induction,26\r\n' \
          u'50.01,222.810,0.130,0.043,0.000,0.036,8.092,8.093,0.016,89.077,16:03:07:00/05/15,18FE349DF87D,BPlugRS_Induction,27\r\n' \
          u'50.03,222.993,0.177,0.043,0.000,0.038,8.415,8.417,0.021,88.797,16:03:17:00/05/15,18FE349DF87D,BPlugRS_Induction,28\r\n' \
          u'50.04,222.507,0.109,0.044,0.000,0.036,7.983,7.983,0.014,89.216,16:03:27:00/05/15,18FE349DF87D,BPlugRS_Induction,29\r\n' \
          u'50.03,222.568,0.245,0.044,0.000,0.037,8.255,8.258,0.030,88.298,16:03:37:00/05/15,18FE349DF87D,BPlugRS_Induction,30\r\n' \
          u'50.04,222.579,0.146,0.044,0.000,0.037,8.343,8.345,0.018,88.995,16:03:47:00/05/15,18FE349DF87D,BPlugRS_Induction,31\r\n'

SINGLE_LINE = u'50.11,235.607,0.088,0.033,0.000,0.027,6.276,6.276,0.000,89.962,13:16:51:24/06/15,18FE349B4C67,RSBplug_16,452\r\n'

KEY = "eYtL2qLVQQ5dufH"
BASE_URL = "http://dev.dataglen.com"



print BASE_URL + "/api/sources/" + KEY + "/"




response = requests.post(BASE_URL + "/api/sources/" + KEY + "/data/",
                        headers = {"Authorization": "Token 31543fd69cad4cfb254f5f8847d9b788330bf40b"},
                        data = {'datapoint': SINGLE_LINE},
                        )
print "DATA_ADDED", response.status_code, response.text

sys.exit()
jPlug_Fields = [
    ("Frequency", "FLOAT", 1, "H", ""),
    ("Voltage", "FLOAT", 2, "V", ""),
    ("ActivePower", "FLOAT", 3, "W", ""),
    ("Energy", "FLOAT", 4, "Wh", ""),
    ("Cost", "FLOAT", 5, "", ""),
    ("Current", "FLOAT", 6, "A", ""),
    ("ReactivePower", "FLOAT", 7, "W", ""),
    ("ApparentPower", "FLOAT", 8, "VA", ""),
    ("PowerFactor", "FLOAT", 9, "", ""),
    ("PhaseAngle", "FLOAT", 10, "", ""),
    ("Timestamp", "TIMESTAMP", 11, "", "%H:%M:%S:%d/%m/%y"),
    ("MACAddress", "STRING", 12, "", ""),
    ("Appliance", "STRING", 13, "", ""),
    ("Checksum", "STRING", 14, "", ""),
]

for field in jPlug_Fields:
    response = requests.post(BASE_URL + "/api/sources/" + KEY + "/streams/",
                            headers = {"Authorization": "Token 31543fd69cad4cfb254f5f8847d9b788330bf40b"},
                            data = {'sourceKey': KEY,
                                      'name': field[0],
                                      'streamDataType': field[1],
                                      'streamPositionInCSV': field[2],
                                      'streamDataUnit': field[3],
                                      'streamDateTimeFormat': field[4]
                            })
    print field[0], response.status_code, response.text

print "FIELDS_ADDED."

response = requests.post(BASE_URL + "/api/sources/" + KEY + "/",
                        headers = {"Authorization": "Token a70186b9cff2e5cffc5605e2478077b3a42e1993"},
                        data = {'timeoutInterval': 900},
                        )
print response.status_code, response.text
sys.exit()

response = requests.post(BASE_URL + "/dataglen/upload/" + KEY + "/",
                        data = {'datapoint': SINGLE_LINE},
                        )
print response.status_code, response.text

fd = open("error.html", "w")
fd.write(response.text)
fd.close()



sys.exit()


sys.exit()


i = 0
KEY = "UGpUUJkYbmEEDm6"
response = unirest.post(BASE_URL + "/api/sources/" + KEY + "/data/",
                        headers = {"Authorization": "Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc"},
                        params = {'datapoint': SINGLE_LINE},
                        )
print response.code, response.body

sys.exit()

response = unirest.post(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'name': 'RadioStudio_InverterIn',
                                  'format': "JSON", # data format as JSON
                                  'frequency': 100, # data reporting interval in seconds
                                  'timezone': 'Asia/Kolkata' # sensor timezone
                        })

if response.code == 201:
    print "Call succeeded"
    print response.body
else:
    print "Call failed", response.body, response.code

sys.exit()





response = unirest.post(BASE_URL + "/dataglen/sensors/",
                        headers={'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'},
                        )
print response.code
print response.body
sys.exit()


response = unirest.get(BASE_URL + "/dataglen/data/",
                      params = {"start": "2014-01-01",
                                "end": "2016-01-01",
                                "key": KEY})
print response.code
print response.body
sys.exit()

response = unirest.post(BASE_URL + "/dataglen/upload/" + KEY + "/",
                        params = {'datapoint': SINGLE_LINE},
                        )
print response.code
print response.body
sys.exit()




response = unirest.post("http://dataglen.com/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'name': 'test_sensor',
                                  'dataFormat': "JSON", # data format as JSON
                                  'dataReportingInterval': 100, # data reporting interval in seconds
                                  'dataTimezone': 'Asia/Kolkata' # sensor timezone
                        })

if response.code == 201:
    print "Call succeeded"
else:
    print "Call failed", response.body, response.code

sys.exit()





bSense_Fields = [
    ("Temperature", "FLOAT", 1, "", ""),
    ("LinearRelativeHumidity", "FLOAT", 2, "", ""),
    ("TemperatureCompensatedRH", "FLOAT", 3, "", ""),

    ("MotionSensorConnectionStatus", "FLOAT", 4, "", ""),
    ("MotionDetectionStatus", "FLOAT", 5, "", ""),
    ("BarometricPressure", "FLOAT", 6, "", ""),
    ("AmbientLight", "FLOAT", 7, "", ""),

    ("AccelerometerXaxis", "FLOAT", 8, "", ""),
    ("AccelerometerYaxis", "FLOAT", 9, "", ""),
    ("AccelerometerZaxis", "FLOAT", 10, "", ""),

    ("SoundLevel", "FLOAT", 11, "", ""),
    ("Timestamp", "TIMESTAMP", 12, "", "%H:%M:%S:%d/%m/%y"),

    ("MACAddress", "STRING", 13, "", ""),
    ("Appliance", "STRING", 14, "", ""),
    ("DataCount", "INTEGER", 15, "", ""),
]


jPlug_Fields = [
    ("Frequency", "FLOAT", 1, "H", ""),
    ("Voltage", "FLOAT", 2, "V", ""),
    ("ActivePower", "FLOAT", 3, "W", ""),
    ("Energy", "FLOAT", 4, "Wh", ""),
    ("Cost", "FLOAT", 5, "", ""),
    ("Current", "FLOAT", 6, "A", ""),
    ("ReactivePower", "FLOAT", 7, "W", ""),
    ("ApparentPower", "FLOAT", 8, "VA", ""),
    ("PowerFactor", "FLOAT", 9, "", ""),
    ("PhaseAngle", "FLOAT", 10, "", ""),
    ("Timestamp", "TIMESTAMP", 11, "", "%H:%M:%S:%d/%m/%y"),
    ("MACAddress", "STRING", 12, "", ""),
    ("Appliance", "STRING", 13, "", ""),
    ("Checksum", "STRING", 14, "", ""),
]

for field in jPlug_Fields:
    response = unirest.post(BASE_URL + "/dataglen/fields/",
                            auth=(USER, PASSWD),
                            params = {'sourceKey': KEY,
                                      'name': field[0],
                                      'streamDataType': field[1],
                                      'streamPositionInCSV': field[2],
                                      'streamDataUnit': field[3],
                                      'date_format': field[4]
                            })
    print field[0], response.code, response.body

print "FIELDS_ADDED."

sys.exit()

for field in jPlug_Fields:
    response = unirest.delete(BASE_URL + "/dataglen/fields/",
                            auth=(USER, PASSWD),
                            params = {'sourceKey': KEY,
                                      'name': field[0]
                                      })

    print field[0], "DELETE", response.code, response.body

sys.exit()

# Add fields now
mSend_Fields = [
    ("ApparentPowerTotal", "FLOAT", 1, "VA", ""),
    ("ActivePowerTotal", "FLOAT", 2, "W", ""),
    ("AveragePowerFactor", "FLOAT", 3, "PF", ""),
    ("AverageVoltage", "FLOAT", 4, "V", ""),
    ("AverageCurrent", "FLOAT", 5, "A", ""),
    ("AverageFrequency", "FLOAT", 6, "H", ""),
    # Phase 1
    ("ApparentPower_Phase1", "FLOAT", 7, "VA", ""),
    ("ActivePower_Phase1", "FLOAT", 8, "W", ""),
    ("PowerFactor_Phase1", "FLOAT", 9, "PF", ""),
    ("Voltage_Phase1ToNeutral", "FLOAT", 10, "V", ""),
    ("Ampere1Phase1", "FLOAT", 11, "A", ""),
    # Phase 2
    ("ApparentPower_Phase2", "FLOAT", 12, "VA", ""),
    ("ActivePower_Phase2", "FLOAT", 13, "W", ""),
    ("PowerFactor_Phase2", "FLOAT", 14, "PF", ""),
    ("Voltage_Phase2ToNeutral", "FLOAT", 15, "V", ""),
    ("Ampere_Phase2", "FLOAT", 16, "A", ""),
    # Phase 3
    ("ApparentPower_Phase3", "FLOAT", 17, "VA", ""),
    ("ActivePower_Phase3", "FLOAT", 18, "W", ""),
    ("PowerFactor_Phase3", "FLOAT", 19, "PF", ""),
    ("Voltage_Phase3ToNeutral", "FLOAT", 20, "V", ""),
    ("Ampere_Phase3", "FLOAT", 21, "A", ""),
    # rest of the fields
    ("ForwardApparentEnergy", "FLOAT", 22, "VAH", ""),
    ("ForwardActiveEnergy", "FLOAT", 23, "WH", ""),
    ("PresentDemand", "FLOAT", 24, "", ""),
    ("RisingDemand", "FLOAT", 25, "", ""),
    ("MaximumDemand", "FLOAT", 26, "", ""),
    ("MaximumDemandOccurence", "INTEGER", 27, "", ""),
    ("OnHours", "INTEGER", 28, "", ""),
    ("PowerInterruptions", "INTEGER", 29, "", ""),

    ("TimeStamp", "TIMESTAMP", 31, "", "%H:%M:%S:%d/%m/%y"),
    ("MACADDRESS", "STRING", 32, "", ""),
    ("mSendName", "STRING", 33, "", ""),
    ("DataCount", "INTEGER", 34, "", "")]

for field in jPlug_Fields:
    response = unirest.post(BASE_URL + "/dataglen/fields/",
                            auth=(USER, PASSWD),
                            params = {'sourceKey': KEY,
                                      'name': field[0],
                                      'streamDataType': field[1],
                                      'streamPositionInCSV': field[2],
                                      'streamDataUnit': field[3],
                                      'date_format': field[4]
                            })
    print field[0], response.code, response.body

print "FIELDS_ADDED."
sys.exit()
# Activate the sensor
response = unirest.patch(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                                  'isActive': True,
                        })

print "SENSOR ACTIVATED", response.code, response.body


# get a list of sensors
response = unirest.get(BASE_URL + "/dataglen/sensors/",
                       auth=auth_params)

# data write
response = unirest.post(BASE_URL + "/dataglen/upload/" + KEY + "/",
                        params = {'datapoint': SAMPLE_DATA},
                        )
print response.code
print response.body
sys.exit()
response = unirest.get(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD))
print "GET ALL", response.code
response = unirest.patch(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': 'VtoVwIBs8sKaADd',
                                  'isActive': False,
                        })

response = unirest.delete(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': "Tm7NR7jyjMKCg9x",
                        })
print "DELETE SENSOR", response.code, response.body

sys.exit()


response = unirest.patch(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'csvDataKeyName': 'datapoint'
                        })

if response.code == 201:
    print "SENSOR ADDED", response.code
    print response.body
else:
    print "CALL FAILED", response.body, response.code

sys.exit()


response = unirest.get(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY})

print response.code
print response.body

sys.exit()

response = unirest.post(BASE_URL + "/dataglen/upload/" + KEY + "/",
                        params = {'datapoint': SAMPLE_DATA},
                        )
print response.code
print response.body
sys.exit()

response = unirest.patch(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                                  'csvDataKeyName': 'datapoint'
                        })

if response.code == 201:
    print "SENSOR ADDED", response.code
    print response.body
else:
    print "CALL FAILED", response.body, response.code

sys.exit()



response = unirest.get(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY})

print "SENSOR_DETAILS", response.code
print response.body

sys.exit()





response = unirest.post(BASE_URL + "/dataglen/upload/VtoVwIBs8sKaADd/",
                        params={'datapoint':DATA})


# get sensor details
response = unirest.get(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY})

print "SENSOR_DETAILS", response.code
print response.body

response = unirest.post(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'name': "test_sensor_2",
                                  'dataFormat': "CSV",
                                  'dataReportingInterval': 10
                        })

if response.code == 201:
    print "SENSOR ADDED", response.code
    print response.body
else:
    print "CALL FAILED", response.body, response.code

sys.exit()

response = unirest.get(BASE_URL + "/dataglen/fields/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                        })

print "FIELDS GET", response.code, response.body

sys.exit()
# data write
response = unirest.post(BASE_URL + "/dataglen/upload/" + KEY + "/",
                        params = {'datapoint': NEW_DATA},
                        )

print "Data: "
print response.code
print response.body

sys.exit()



