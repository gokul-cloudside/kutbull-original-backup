

TASKS = [
    # ("", "1/7/30", "1/2/3", "8")
    ("Perform the cleaning of solar panels", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check if the fasteners on panels mounting structures are sealed and locked properly?", "30", "2", "8", ["INVERTER", "AJB"]),
    ("Check if the fixation of modules on the mounting structures are firm?", "30", "3", "8", ["INVERTER", "AJB"]),

    ("Inspect the conduits and junction boxes of module strings", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Inspect the conduits and junction boxes of module strings", "30", "2", "8", ["INVERTER", "AJB"]),

    ("Check if cable connections between panels strings and array junction boxes are secured?", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check if cable connections between panels strings and array junction boxes are secured?", "30", "2", "8", ["INVERTER", "AJB"]),

    ("Check if lids are closed for all array junction boxes and cables are tightly secured?", "30", "1", "8", ["AJB"]),
    ("Check if lids are closed for all array junction boxes and cables are tightly secured?", "30", "2", "8", ["AJB"]),

    ("Check if the fasteners on array junction boxes are sealed and locked?", "30", "1", "8", ["AJB"]),
    ("Check if the fasteners on array junction boxes are sealed and locked?", "30", "2", "8", ["AJB"]),

    ("Inspect modules for damages. Ensure there is no crack.", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Inspect modules for damages. Ensure there is no crack.", "30", "2", "8", ["INVERTER", "AJB"]),

    ("Check and record inverters generation manually", "1", "1", "8", ["INVERTER"]),
    ("Check and record inverters generation manually", "7", "1", "8", ["INVERTER"]),
    ("Check and record inverters generation manually", "30", "1", "8", ["INVERTER"]),

    ("Check if inverters connections and wire lugs fasteners are secured and locked?", "30", "1", "8", ["INVERTER"]),
    ("Check if inverters connections and wire lugs fasteners are secured and locked?", "30", "2", "8", ["INVERTER"]),

    ("Check if all power terminals of inverters are secured?", "30", "1", "8", ["INVERTER"]),
    ("Check if all power terminals of inverters are secured?", "30", "2", "8", ["INVERTER"]),

    ("Check all electrical wires, joints and terminal at the plant", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check the insulation of all the cables", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check if the color code used during installation exists?", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check if the insulation tape or heat sleeves used for joints are placed?", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check for physical damages to the AJB.", "30", "1", "8", ["AJB"]),
    ("Check for the holding of AJBs to the mounting structure.", "30", "1", "8", ["AJB"]),
    ("Check the status of fuse and fuse holders.","30", "1", "8", ["INVERTER", "AJB"]),
    ("Check for physical damages to the AC distribution board.", "30", "1", "8", ["ENERGY_METER"]),
    ("Check for the functionality of energy meters.", "30", "1", "8", ["ENERGY_METER"]),
    ("Check connections between the sensor, inverters and data logger units.", "30", "1", "8", ["DATA_LOGGER"]),
    ("Check all RJ 45/232/485 jacks between individual units and the data logger", "30", "1", "8", ["DATA_LOGGER"]),
    ("Check for physical damages to the data logger","30", "1", "8", ["DATA_LOGGER"]),

    ("Check all electrical wires, joints and terminal at the plant", "30", "2", "8", ["INVERTER", "AJB"]),
    ("Check the insulation of all the cables", "30", "2", "8", ["INVERTER", "AJB"]),
    ("Check if the color code used during installation exists?", "30", "2", "8", ["INVERTER", "AJB"]),
    ("Check if the insulation tape or heat sleeves used for joints are placed?", "30", "2", "8", ["INVERTER", "AJB"]),
    ("Check for physical damages to the AJB.", "30", "2", "8", ["AJB"]),
    ("Check for the holding of AJBs to the mounting structure.", "30", "2", "8", ["AJB"]),
    ("Check the status of fuse and fuse holders.","30", "2", "8", ["INVERTER", "AJB"]),
    ("Check for physical damages to the AC distribution board.", "30", "2", "8", ["PLANT"]),
    ("Check for the functionality of energy meters.", "30", "2", "8", ["ENERGY_METER"]),
    ("Check connections between the sensor, inverters and data logger units.", "30", "2", "8", ["DATA_LOGGER"]),
    ("Check all RJ 45/232/485 jacks between individual units and the data logger", "30", "2", "8", ["DATA_LOGGER"]),
    ("Check for physical damages to the data logger","30", "2", "8", ["DATA_LOGGER"]),

    ("Check for earthquake resistance", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Visually check for the earth connection at each mounting structure and to the earth electrode", "30", "1", "8", ["INVERTER", "AJB"]),
    ("Check for earthquake resistance", "30", "2", "8", ["INVERTER", "AJB"]),
    ("Visually check for the earth connection at each mounting structure and to the earth electrode", "30", "2", "8", ["INVERTER", "AJB"]),

    ("Clean the Solar PV area and inverter room area", "1", "1", "8", ["INVERTER"]),
    ("Inspect and clean all electrical equipment", "1", "1", "8", ["INVERTER", "AJB"]),
    ("Clean the Solar PV area and inverter room area", "7", "1", "8", ["INVERTER"]),
    ("Inspect and clean all electrical equipment", "7", "1", "8", ["INVERTER", "AJB"]),

    ("Inspect walkways and site access routes", "30", "1", "8", ["PLANT"]),
    ("Inspect leakages and pressure for water pipeline", "30", "1", "8", ["PLANT"]),
    ("Inspect walkways and site access routes", "30", "2", "8", ["PLANT"]),
    ("Inspect leakages and pressure for water pipeline", "30", "2", "8", ["PLANT"]),

    ("Inspect DC distribution board's current and voltage", "30", "1", "8", ["PLANT"]),
    ("Inspect AC distribution board's current and voltage", "30", "1", "8", ["PLANT"]),

    ("Inspect DC distribution board's current and voltage", "30", "2", "8", ["PLANT"]),
    ("Inspect AC distribution board's current and voltage", "30", "2", "8", ["PLANT"]),

    ("CUSTOM_TASK", "1", "1", "8", ["ALL"])
]

from .models import Tasks

def setup_tasks(delete=True):
    if delete:
        for task in Tasks.objects.all():
            task.delete()

    for task in TASKS:
        for ad in task[4]:
            print ad
            if ad == "AJB":
                continue
            tsk = Tasks.objects.create(name=task[0],
                                       frequency=task[1],
                                       recurring=task[2],
                                       time=task[3],
                                       associated_devices=ad)
            tsk.save()
