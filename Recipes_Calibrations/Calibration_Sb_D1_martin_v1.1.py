"""
Performs a flux calibration of the As cell
"""
from recipe_helper import MBERecipe, ts_print
from time import strftime

# Script takes about 3min per value, would like to keep the total calibration to around 30 min, so 10 values

# Very short calibration
# values = [0, 20, 40, 60, 80, 100]
# Short calibration
values = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
# Long calibration
# values = [10, 15, 20, 25, , 30, 35, 40, 45, 50, 52, 60, 80, 100]

t_stabilize = 30
t_shutter_stabilize = 30

#################################
# Modify this for each material
#################################
mat = "Sb"
T_Sb = 450
#################################

filename = r"\\MBESERVER\Documents\Calibrations_D1" + "\\" + strftime("%Y-%m-%d_%H-%M-%S_T" + T_Sb + "_" + mat + ".txt")

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

        # Ramp up the Sb cell to the desired temperature
        if mat.lower() == "sb":
            mbe.set_param("Sb.PV.Rate", 5)
            mbe.set_param("Sb.OP.Rate", 0)
            mbe.set_param("Sb.PV.TSP", T_Sb)
            mbe.wait_to_reach_temp(PID="Sb")
            mbe.waiting(60 * 10)  # Stabilize for 10 min

        # Insert bfm
        mbe.bfm(True)

        # Write the file headers
        f = open(filename, "a")
        f.write("{:s}\tBFM.P\tMBE.P\tBFM.P_STD\tMBE.P_STD\n".format(mat))
        f.close()

        # Loop over all the values to calibrate
        for value in values:
            ts_print("Ramping to {}".format(value))
            mbe.set_param("SbCracker.Valve.OP", value)

            ts_print("Waiting {:.0f}s to stabilize".format(t_stabilize))
            mbe.waiting(t_stabilize)

            ts_print("Opening shutter and making measurement")
            mbe.shutter(mat, True)  # Open shutter

            pressure, background, p_std, b_std = mbe.read_pressures(max_t=30, n=10, error=0.01)
            f = open(filename, "a")
            f.write("{:.0f}\t{:.6E}\t{:.6E}\t{:.6E}\t{:.6E}\n".format(value, pressure, background, p_std, b_std))
            f.close()
            ts_print("Pressure: " + str(pressure) + " (stored to file)")

            mbe.shutter(mat, False)  # Close shutter

        mbe.set_stdby()  # Set MBE to standby conditions

    ts_print("Recipe Done.")
