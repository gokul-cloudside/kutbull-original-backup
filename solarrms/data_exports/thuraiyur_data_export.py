from solarmonitoring.models import Inverter, SolarPlant, Feeder


def get_solar_plant(name):
    try:
        return SolarPlant.objects.get(name=name)
    except:
        return None


def add_feeders(solar_plant, file_name):
    lines = open(file_name).readlines()
    for line in lines:
        info = line.split(";")
        if info[-1] == "R":
            slave_id = info[3]
            name = info[1]
            print slave_id, name

if __name__ == "__main__":
    print "hello"
    solar_plant = get_solar_plant("APEX20MW_10")
    print solar_plant
    add_feeders(solar_plant, "/Users/sunilghai/Desktop/data/inverter_config.csv")

