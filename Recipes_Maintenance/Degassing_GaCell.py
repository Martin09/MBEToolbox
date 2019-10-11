"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration
from time import sleep

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':

    with MBERecipe(virtual_server=False, stdby_at_exit=False) as mbe:
        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        start_OP = 0  # Percent
        max_OP = 10  # Percent
        incr_OP = 0.3  # Percent
        max_temp = 150  # Degrees C
        max_pressure = 1E-6  # Torr

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.OP.TSP", start_OP)

        while True:

            while float(mbe.get_param("MBE.P")) > max_pressure:
                sleep(1)

            if float(mbe.get_param("Ga.PV")) >= max_temp:
                break
            if float(mbe.get_param("Ga.OP")) >= max_OP:
                break

            curr_OP = float(mbe.get_param("Ga.OP"))
            mbe.set_param("Ga.OP.TSP", curr_OP + incr_OP)

            sleep(60 * 10)  # Wait 10 minutes


        ts_print("Recipe Done.")

