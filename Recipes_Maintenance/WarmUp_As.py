"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = True

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

        ts_print("Setting variables")
        # Define growth parameters
        as_valve_warmup = 30
        t_cracker = 600  # Degrees C
        t_cracker_rate = 5  # Degrees C per minute
        t_as_tank = 395  # Degrees C
        t_as_tank_rate = 5  # Degrees C per minute

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code

        ts_print("Opening arsenic cracker valve")
        mbe.set_param("AsCracker.Valve.OP", as_valve_warmup)

        ts_print("Ramping up As cracker to {} C at a rate of {} C/min".format(t_cracker, t_cracker_rate))
        mbe.set_param("AsCracker.PV.Rate", t_cracker_rate)
        mbe.set_param("AsCracker.PV.TSP", t_cracker)

        ts_print("Ramping up As tank to {} C at a rate of {} C/min".format(t_as_tank, t_as_tank_rate))
        mbe.set_param("As.PV.Rate", t_as_tank_rate)
        mbe.set_param("As.PV.TSP", t_as_tank)

        ts_print("Closing arsenic cracker valve")
        mbe.set_param("AsCracker.Valve.OP", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
