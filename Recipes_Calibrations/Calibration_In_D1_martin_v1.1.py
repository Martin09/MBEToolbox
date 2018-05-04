"""
Performs a flux calibration of the Ga cell
"""
from recipe_helper import MBERecipe, ts_print
from time import strftime
import numpy as np

# Script takes about 3min per value, would like to keep the total calibration to around 30 min, so 10 values

# Short calibration
values = np.linspace(830, 770, 7)
# Long calibration
# values = np.linspace(830, 770, 13)

t_stabilize = 300  # 5 minutes

#################################
# Modify this for each material
#################################
mat = "In"
ramp_rate = 20  # degrees/min
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
        f.write("{:s}\tBFM.P\tMBE.P\tBFM.P_STD\tMBE.P_STD\n".format(mat))
        f.close()

        # Loop over all the values to calibrate
        for i, value in enumerate(values):
            ts_print("Ramping to {}".format(value))
            mbe.set_param(mat + ".PV.Rate", ramp_rate)
            mbe.set_param(mat + ".OP.Rate", 0)
            mbe.set_param(mat + ".PV.TSP", value)

            mbe.wait_to_reach_temp(value, PID=mat)

            if i == 0:
                ts_print("Stabilizing at first point".format(t_stabilize))
                mbe.waiting(3 * 60)

            mbe.waiting(t_stabilize)

            ts_print("Opening shutter and making measurement")
            mbe.shutter(mat, True)  # Open shutter

            pressure, background, p_std, b_std = mbe.read_pressures(max_t=60, n=30, error=0.01)
            f = open(filename, "a")
            f.write("{:.0f}\t{:.6E}\t{:.6E}\t{:.6E}\t{:.6E}\n".format(value, pressure, background, p_std, b_std))
            f.close()
            ts_print("Pressure: " + str(pressure) + " (stored to file)")

            mbe.shutter(mat, False)  # Close shutter

        mbe.set_stdby()  # Set MBE to standby conditions

    ts_print("Recipe Done.")
