"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False

# Toggles the shutter of the MBE open and closed to help find an oscillating RHEED spot

# If running the script locally:
if __name__ == '__main__':

    with MBERecipe(virtual_server=run_virtual_server, stdby_at_exit=False) as mbe:
        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        # Define parameters
        n_repetitions = 200
        t_open = 8  # seconds
        t_close = 8  # seconds

        while n_repetitions:
            mbe.shutter("Ga", True)
            mbe.waiting(t_open)
            mbe.shutter("Ga", False)
            mbe.waiting(t_open)
