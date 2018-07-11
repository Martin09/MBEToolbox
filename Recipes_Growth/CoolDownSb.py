"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
import sys, os
sys.path.insert(1, os.path.join(sys.path[0], '..'))  # Add parent directory to path
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

sb_stdby = 250
sbcracker_stbdy = 300
sbcond_stbdy = 300

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':

    with MBERecipe(virtual_server=run_virtual_server) as mbe:
        # Prompt user if they are sure
        mbe.starting_growth_prompt()

        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        mbe.set_param("SbCracker.Valve.OP", 30)  # Crack open Sb valve during cool down
        ts_print("Sb cracker opened to {}%".format(mbe.get_param("SbCracker.Valve.OP")))

        mbe.set_param("SbCracker.PV.Rate", 10)
        mbe.set_param("SbCracker.PV.TSP", sbcracker_stbdy)
        mbe.set_param("SbCond.PV.Rate", 10)
        mbe.set_param("SbCond.PV.TSP", sbcond_stbdy)
        mbe.set_param("Sb.PV.Rate", 5)
        mbe.set_param("Sb.PV.TSP", sb_stdby)

        # Testing
        mbe.wait_to_reach_temp(795, PID='SbCracker', error=3)
        ts_print("SbCracker Reached 795")
        mbe.wait_to_reach_temp(790, PID='SbCond', error=3)
        ts_print("SbCond Reached 790")
        mbe.wait_to_reach_temp(490, PID='Sb', error=3)
        ts_print("Sb Reached 490")

        mbe.wait_to_reach_temp(sbcracker_stbdy, PID='SbCracker', error=1)
        mbe.wait_to_reach_temp(sbcond_stbdy, PID='SbCond', error=1)
        mbe.wait_to_reach_temp(sb_stdby, PID='Sb', error=1)

        mbe.set_param("SbCracker.Valve.OP", 0)  # Close Sb valve again after cool down
        ts_print("Sb cracker closed. Current value {}%".format(mbe.get_param("SbCracker.Valve.OP")))

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
