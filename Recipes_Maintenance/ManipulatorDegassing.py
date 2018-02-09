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

        mbe.set_param("Manip.PV.Rate", 20)
        mbe.set_param("Manip.PV.TSP", 400)
        mbe.wait_to_reach_temp(400, error=2)
        mbe.waiting(60 * 30)  # 30 min anneal
        mbe.set_param("Manip.PV.Rate", 0)
        mbe.set_param("Manip.PV.TSP", 200)
        ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log()
