from dashboards.models import DataglenClient
from solarrms.models import SolarPlant, Feeder, IndependentInverter, AJB
from dateutil import parser
import requests, json

SERVER = 'http://dev.dataglen.com'
TOKEN = 'e9eeb4a597a0f86ad8e3fc7444310cee22c32646'

MAPPINGS = [('DC_INPUT_VOLTAGE', 'DC Link Voltage'),
            ('DC_INPUT_CURRENT', 'DC Current'),
            ('DC_INPUT_POWER', 'DC Power'),
            ('ACTIVE_POWER', 'Active Power'),
            ('APPARENT_POWER', 'Apparent Power'),
                ('REACTIVE_POWER', 'FLOAT'),
            ('ACTIVE_ENERGY', 'Active Energy'),
                ('POWER_FACTOR', 'FLOAT'),
            ('OUTPUT_FREQUENCY', 'Frequency'),
                ('OUTPUT_VOLTAGE', 'FLOAT'),
            ('APPARENT_POWER_Y', 'Apparent Power Y_PH'),
            ('APPARENT_POWER_B', 'Apparent Power B_PH'),
            ('APPARENT_POWER_R', 'Apparent Power R_PH'),
            ('ACTIVE_POWER_Y', 'Active Power Y_PH'),
            ('ACTIVE_POWER_B', 'Active Power B_PH'),
            ('ACTIVE_POWER_R', 'Active Power R_PH'),
                ('REACTIVE_POWER_Y', 'FLOAT'),
                ('REACTIVE_POWER_B', 'FLOAT'),
                ('REACTIVE_POWER_R', 'FLOAT'),
            ('CURRENT_Y', 'Current Y_PH'),
            ('CURRENT_B', 'Current B_PH'),
            ('CURRENT_R', 'Current R_PH'),
            ('HEAT_SINK_TEMPERATURE', 'Heat Sink Temperature'),
            ('INSIDE_TEMPERATURE', 'Inside Temperature'),
            ('CURRENT_ERROR', 'Current Error'),
            ('POWER_SUPPLY_VOLTAGE', 'Power Supply Voltage'),
            ('POWER_SUPPLY_CURRENT', 'Power Supply Current'),
            ('POWER_SUPPLY_VOLTAGE_Y', 'Power Supply Voltage Y_PH'),
            ('POWER_SUPPLY_VOLTAGE_B', 'Power Supply Voltage B_PH'),
            ('POWER_SUPPLY_VOLTAGE_R', 'Power Supply Voltage R_PH'),
            ('SOLAR_STATUS', 'Solar Status'),
            ('DIGITAL_INPUT', 'Digital Inputs'),
                ('CONVERTER_TEMPERATURE', 'FLOAT'),
                ('CUBICLE_TEMPERATURE', 'FLOAT')]


def get_the_client(name):
    try:
        client = DataglenClient.objects.get(name="APEX Spinning Mills")
        return client
    except:
        return None


def get_solar_plant(client, name):
    for group in client.dataglen_groups.all():
        if group.name == name:
            return group.solarplant


def dequote(s):
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        return s[1:-1]
    return s


def load_feeders(client, plant, filename):
    lines = open(filename).readlines()
    for line in lines:
        params = [dequote(param) for param in line.strip().split(";")]
        if params[-1] == "R":
            try:
                feeder = Feeder(user=client.owner.organization_user.user, plant=plant,
                                name=params[3], displayName=params[1],
                                dataFormat='JSON')
                feeder.save()
                print "Feeder saved", params[1]
            except Exception as exc:
                print "Error saving feeder instance", exc
                continue


def load_inverters(client, plant, filename):
    lines = open(filename).readlines()
    for line in lines:
        params = [dequote(param) for param in line.strip().split(";")]
        if params[-1] == "I":
            try:
                inverter = IndependentInverter(user=client.owner.organization_user.user, plant=plant,
                                               manufacturer = 'Unknown',
                                               name=params[3], displayName=params[1],
                                               dataFormat='JSON')
                inverter.save()
                print "inverter saved", params[1]
            except Exception as exc:
                print "Error saving inverter instance", exc
                continue


def return_field(name):
    for entry in MAPPINGS:
        if entry[1] == name:
            return entry[0]


def load_feeder_and_inverter_data(feeders, inverters, data_files):
    for filename in data_files:
        print filename
        lines = open(filename).readlines()
        indexes = range(5, 109, 4)

        for i in range(1, len(lines)):#line in lines[1:]:
            line = lines[i]
            params = [dequote(param) for param in line.strip().split(";")]
            # always use a list like this for now. using json.dumps with a single datapoint w/o a list will fail.
            data = []
            try:
                # find an inverter instance
                try:
                    source = inverters.get(name=params[1])
                    # prepare a datapoint
                    data_point = {}
                    for index in indexes:
                        data_point[return_field(params[index])] = float(float(params[index+1])*float(params[index+2]))
                except IndependentInverter.DoesNotExist:
                    try:
                        source = feeders.get(name=params[1])
                        # prepare a datapoint
                        data_point = {}
                        for index in indexes:
                            data_point[params[index]] = float(float(params[index+1])*float(params[index+2]))
                    except:
                        print "NO INVERTER/FEEDER with this ID"
                        print params

                ts = parser.parse(params[-1])
                data_point['TIMESTAMP'] = str(ts)

                # append to the list
                data.append(data_point)
                if source.isActive is False or source.isMonitored is False:
                    source.isActive = True
                    source.isMonitored = True
                    source.save()

                # send to the server
                response = requests.post(url = SERVER + "/api/sources/" + source.sourceKey + "/data/",
                                         json = data,
                                         headers = {'Authorization': 'Token ' + TOKEN})
                #print filename, i, len(lines)

                # print only if there's an error
                if response.status_code != 200:
                    print data_point
                    print SERVER + "/api/sources/" + source.sourceKey + "/data/"
                    print response.text
            # catch other errors
            except Exception as E:
                # print the error
                print E
                print params


def run():
    apex = get_the_client("APEX Spinning Mills")
    inverter_data_files = ['/Users/sunilghai/Desktop/data/inverter_data_1.csv',
                           '/Users/sunilghai/Desktop/data/inverter_data_2.csv',
                           '/Users/sunilghai/Desktop/data/inverter_data_3.csv',
                           '/Users/sunilghai/Desktop/data/inverter_data_4.csv']
    if apex:
        print apex
        plant = get_solar_plant(apex, "Thuraiyur Plant")
        if plant:
            print plant
            #load_feeders(apex, plant, "/Users/sunilghai/Desktop/data/inverter_config.csv")
            #load_inverters(apex, plant, "/Users/sunilghai/Desktop/data/inverter_config.csv")
            feeders = plant.feeder_units.all()
            inverters = plant.independent_inverter_units.all()
            load_feeder_and_inverter_data(feeders, inverters, inverter_data_files)
