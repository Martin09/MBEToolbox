"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    grow = raw_input('Starting a growth! Are you sure? (y/n):  ')
    if not (grow.lower() == 'y'):
        print('Exiting...')
        exit()
    else:
        print('Starting growth!')

    with MBERecipe(virtual_server=run_virtual_server) as mbe:
        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        mbe.set_param("Manip.RS.RPM", 7)

        # Uncapped GaAsOx from substrate manually

        # Ramp down manipulator, close As valve when it reaches 300
        mbe.wait_to_reach_temp(300, error=3, timeout_on=False)
        ts_print("Temperature reached 300, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        # Cap the sample with arsenic
        mbe.as_capping(capping_time=60)  # Before unloading sample, heat it to 100 degrees for ~5min

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log()
