#########################################################################################
# Imports
import os


#########################################################################################
# Variables..
ENERGY_OUTPUT_FOLDER = "/usr/local/lib/BONSAI_N/ENERGY/"
POWER_OUTPUT_FOLDER = "/usr/local/lib/BONSAI_N/POWER/"
EDGEML_DIR = "/var/www/EdgeML_TF"

#########################################################################################
# FUnctions

# Function1
# this function runs the TENSOR FLOW Code
# Output would be BONSAI numpy arrays on the appropriate output folders.
def bonsai_trainer(energy=True):
    # assign the proper output folder based on unit
    if energy:
        OUTPUT_FOLDER = ENERGY_OUTPUT_FOLDER
    else:
        OUTPUT_FOLDER = POWER_OUTPUT_FOLDER

    # Calls the edgeml code for training.
    plant_directory = [OUTPUT_FOLDER.rstrip("/") + "/" + directory + "/bonsai/" for directory in
                       os.listdir(OUTPUT_FOLDER) if
                       os.path.isdir(OUTPUT_FOLDER + directory)]
    print(plant_directory)

    for plant in plant_directory:
        print("\n\n")
        print("---------------------------------------------------")
        print("Currently Working for plant >>> : ", plant)

        slots = [directory for directory in os.listdir(plant) if os.path.isdir(plant + directory)]
        print(slots)

        for slot in slots:
            print("-------------------------------------------------")
            print("Currently working for slot >>> : ", slot)
            print(plant + slot)

            # pass the right parameters for PREDICTION REVISION. Below parms were decided in microsoft
            # TODO add Gridsearch to this code in future.
            print(os.system(
                "python " + EDGEML_DIR.rstrip("/") + "/tf/examples/bonsai_example.py -dir "
                + plant + slot + " -e 500 -d 4 -p 10 -b 32 -s 0.1 -lr 0.05 -rW 0.00001 -rZ 0.000001"))


# Main Function.
if __name__ == '__main__':
    # trainer for energy..
    bonsai_trainer(energy=True)
    # trainer for power..
    bonsai_trainer(energy=False)

###########################################################################################