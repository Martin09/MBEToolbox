"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False
use_pyro = False

# Grows GaAs buffer followed by AlGaAs superlattice and finally a last buffer
###########################
T_Ga = 960  # Ga temp
T_Al = 1040  # Al temp
T_Manip = 750  # Temperature for substrate de-oxidation
p_as = 5E-6  # Torr
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")
    calib_Al = Calibration("Al")

    as_valve = calib_As.calc_setpoint(p_as)

    with MBERecipe(virtual_server=run_virtual_server, stdby_at_exit=False) as mbe:
        # Prompt user if they are sure
        mbe.starting_growth_prompt()

        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()
        ts_print("Setting variables")

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", -7)

        # Check pressure before ramping up anything, make sure As valve is working
        ts_print("Opening arsenic cracker valve and shutter")
        mbe.set_param("AsCracker.Valve.OP", as_valve)
        mbe.shutter("As", True)
        mbe.waiting(60 * 3)  # Wait 3min
        ts_print("Checking pressure")
        if float(mbe.get_param("MBE.P")) < 1e-8:  # Make sure As valve opened properly
            mbe.set_param("Manip.PV.TSP", 200)
            mbe.set_param("Manip.PV.Rate", 100)
            raise Exception(
                "Pressure <1e-8 after opening As. Something wrong, check As valve, shutter and tank temperature!")
        ts_print("Pressure looks good.")

        ts_print("Ramping to degassing temperature")
        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", T_Manip)  # Anneal temperature
        ts_print("Ramping up Ga and Al sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        mbe.set_param("Al.PV.Rate", 20)
        mbe.set_param("Al.OP.Rate", 0)
        mbe.set_param("Al.PV.TSP", T_Al)

        ##############################################################################
        # Wait to reach set temp
        ##############################################################################
        mbe.wait_to_reach_temp(T_Manip)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
