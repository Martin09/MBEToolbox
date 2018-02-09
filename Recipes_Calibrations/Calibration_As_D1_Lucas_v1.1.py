"""
Performs a flux calibration of the As cell
"""
from recipe_helper import MBERecipe, ts_print
from time import strftime

# Script takes about 3min per value, would like to keep the total calibration to around 30 min, so 10 values

# Short calibration
# values = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
# Long calibration
# values = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]
values = [10, 20, 25, 30, 33, 35, 36, 38, 40, 60, 70, 80, 85, 100]
# Randomized order to help eliminate memory fyrom prev measurements,
# but small openings after large openings are not meaningful... so don't use this
# values = [30, 80, 25, 50, 35, 15, 100, 45, 5, 70, 40, 10, 90, 20, 60, 0]

t_stabilize = 30
t_shutter_stabilize = 30

#################################
# Modify this for each material
#################################
mat = "As"
standby_value = 0
#################################

filename = r"\\MBESERVER\Documents\Calibrations_D1" + "\\" + strftime("%Y-%m-%d_%H-%M-%S_" + mat + ".txt")

# If running the script locally:
if __name__ == '__main__':
    grow = raw_input('Starting a growth! Are you sure? (y/n):  ')
    if not (grow.lower() == 'y'):
        print('Exiting...')
        exit()
    else:
        print('Starting growth!')

    with MBERecipe(virtual_server=False) as mbe:
        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        # Insert bfm
        mbe.bfm(True)

        # Write the file headers
        f = open(filename, "a")
        f.write("{:s}\tBFM.P\tMBE.P\n".format(mat))
        f.close()

        # Loop over all the values to calibrate
        for value in values:
            ts_print("Ramping to {}".format(value))
            mbe.set_param("AsCracker.Valve.OP", value)

            ts_print("Waiting {:.0f}s to stabilize".format(t_stabilize))
            mbe.waiting(t_stabilize)

            ts_print("Opening shutter and making measurement")
            mbe.shutter(mat, True)  # Open shutter

            pressure, background = mbe.read_pressures(n=30, error=0.01)
            f = open(filename, "a")
            f.write("{:.0f}\t{:.6E}\t{:.6E}\n".format(value, pressure, background))
            f.close()
            ts_print("Pressure: " + str(pressure) + " (stored to file)")

            mbe.shutter(mat, False)  # Close shutter

        mbe.set_stdby()  # Set MBE to standby conditions

    ts_print("Recipe Done.")
