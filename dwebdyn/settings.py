UPLOAD_INV = True
UPLOAD_MODBUS = True
UPLOAD_IO = True
UPLOAD_ALARMS = True
UPLOAD_ERRORS = True
UPLOAD_LOG = True

# API ERROR CODES
class STATUS_CODES():
    SUCCESSFUL_DATA_REQUEST = 200
    SUCCESSFUL_REQUEST = 201
    BAD_REQUEST = 400
    UNAUTHENTICATED_REQUEST = 401
    DUPLICATE_REQUEST = 409
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    CONNECTION_FAILURE = -1

HEARTBEAT_MINUTES = 30

INVERTER_TYPES = {
    "0": "SMA: SMA Net",
    "1": "PowerOne: Aurora",
    "2": "Schneider Electric: SunEzy",
    "3": "Kaco: Powador",
    "4": "Ingeteam",
    "5": "LTI",
    "6": "Fronius",
    "7": "Schneider: ConextCom",
    "8": "Danfoss: ComLynx",
    "9": "PowerOne: (Manual addressing)",
    "10": "Siemens: PVM/Refusol",
    "11": "DiehlAko: Platinum",
    "12": "SMA CENTRAUX: Modbus TCP",
    "13": "SOCOMEC: SunSysHome",
    "14": "SOCOMEC: SunSysPro",
    "15": "reserved",
    "16": "Ingeteam: Modbus TCP",
    "17": "SolarMax: MaxComm",
    "19": "DELTA",
}

NEW_GATEWAY_CHECK_MINUTES = 15
NEW_DATA_CHECK_MINUTES = 5