import unirest, sys, json

# Define some parameters
BASE_URL = "http://dataglen.com"

SAMPLE_DATA = "49.96,220.970,0.092,0.037,0.000,0.024,5.371,5.372,0.017,89.021,02:38:00:04/05/15,18FE349F5C6E,BPlug_Radiostudio,608\r\n" \
       "49.98,220.818,0.117,0.037,0.000,0.025,5.439,5.440,0.021,88.772,18:16:13:15/04/15,18FE349F5C6E,BPlug_Radiostudio,609\r\n" \
       "49.96,221.005,0.008,0.037,0.000,0.024,5.299,5.299,0.001,89.916,18:16:15:15/04/15,18FE349F5C6E,BPlug_Radiostudio,610\r\n"
#DATA = "49.96,221.005,0.008,0.037,0.000,0.024,5.299,5.299,0.001,89.916,17:16:14:15/04/15,18FE349F5C6E,BPlug_Radiostudio,610\r\n"
DATA = "Test data for invalid records"

NEW_DATA = "33.87,64.27,53.78,0,0,1007.63,63,-0.19,-0.19,14.02,1.68,16:35:07:07/04/15,18FE349B4CFF,BSense_RadioStudio,3\r\n"

SENSOR_NAME = "TEST"
USER = 'root'
PASSWD = 'root@dg'
FORMAT = "CSV" # One of XM/JS/CSV
KEY = "Cd8rjfk2vY9cICN"

'''
    SENSOR_GET
'''

response = unirest.post(BASE_URL + "/dataglen/fields/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                                  'name': "Frequency",
                                  'streamPositionInCSV': 2,
                                  'streamDataType': "FLOAT"
                        })

print response.code, response.body
sys.exit()

response = unirest.get(BASE_URL + "/dataglen/fields/",
                        auth=(USER, PASSWD),
                        params = {'ky': KEY,
                        })


response = unirest.post(BASE_URL + "/dataglen/fields/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                                  'name': "check3",
                                  "position": 2,
                                  "type": "INTEGER"
                        })
print response.code, response.body
sys.exit()



response = unirest.get(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD))
print response.code



if response.code == 201:
    print "SENSOR ADDED", response.code
    KEY = response.body["key"]
    print KEY
else:
    print "CALL FAILED", response.body, response.code

sys.exit()

response = unirest.delete(BASE_URL + "/dataglen/fields/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                                  'name': "cehck"
                        })

print response.code, response.body
sys.exit()

response = unirest.post(BASE_URL + "/dataglen/upload/VtoVwIBs8sKaADd/",
                        params={'datapoint':DATA})


# get sensor details
response = unirest.get(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY})

print "SENSOR_DETAILS", response.code
print response.body


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

    ("Time", "TIME", 30, "", "%H:%M:%S"),
    ("Date", "DATE", 31, "", "%d/%m/%y"),

    ("MACADDRESS", "STRING", 32, "", ""),
    ("mSendName", "STRING", 33, "", ""),
    ("DataCount", "INTEGER", 34, "", "")]

for field in bSense_Fields:
    response = unirest.post(BASE_URL + "/dataglen/fields/",
                            auth=(USER, PASSWD),
                            params = {'sourceKey': KEY,
                                      'name': field[0],
                                      'streamDataType': field[1],
                                      'streamPositionInCSV': field[2],
                                      'streamDataUnit': field[3],
                                      'date_format': field[4]
                            })
    print field[0], response.code

print "FIELDS_ADDED."
# Activate the sensor
response = unirest.patch(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                                  'isActive': True,
                        })

print "SENSOR ACTIVATED", response.code

# data write
response = unirest.post(BASE_URL + "/dataglen/upload/" + KEY + "/",
                        params = {'datapoint': NEW_DATA},
                        )

print "Data added: "
print response.code
print response.body

sys.exit()

response = unirest.get(BASE_URL + "/dataglen/fields/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                        })

print "FIELDS GET", response.code

for field in jPlug_Fields:
    response = unirest.delete(BASE_URL + "/dataglen/fields/",
                            auth=(USER, PASSWD),
                            params = {'sourceKey': KEY,
                                      'name': field[0]
                                      })

    print field[0], "DELETE", response.code

sys.exit()
response = unirest.delete(BASE_URL + "/dataglen/sensors/",
                        auth=(USER, PASSWD),
                        params = {'sourceKey': KEY,
                        })
print "DELETE SENSOR", response.code

sys.exit()


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
