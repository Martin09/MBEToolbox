"""
Example of a growth recipe for nanomembranes.
Requires the new MBE_Toolbox
"""

from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

# Second Nanomembrane on Si growth for Nick
# Trying MEE by cycling Ga shutter open and closed (1 s open, 1 s closed)
###########################
rate_ga = 0.33  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
p_as_gaas = 8E-6  # Torr - Will calculate valve opening from this based on latest BFM calibrations
###########################

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    #calib_Ga = Calibration("Ga", filename="2018-08-31_13-51-50_Ga.txt", rheed_filename="2017-06-30_Ga.txt")
    calib_As = Calibration("As", filename="2019-03-18_13-47-28_TCrck599_As.txt")

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
        T_Ga = 888  # (BEP = 1E-7)
        T_Des_Anneal_Manip = 850  # Desired manip temperature (pyro is broken)
        T_Des_GaAs_Manip = 750  # Desired manip temperature (pyro is broken)
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        t_anneal = 30 * 60  # 30 minutes
        t_growth_gaas = 60 * 60  # 60 minutes
        t_cycle_open = 1 #MEE cycle with Ga shutter open for 1 second at a time
        t_cycle_closed = 1 #MEE cycle with Ga shutter closed for 1 second at a time

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", -7)

        ts_print("Ramping to degassing temperature")
        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", T_Des_Anneal_Manip)  # Anneal temperature
        ts_print("Ramping up Ga source")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        mbe.wait_to_reach_temp(T_Des_Anneal_Manip)
        mbe.waiting(t_anneal)

        ##############################################################################
        # Start Growth
        ##############################################################################
        # Go to growth conditions
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip)
        mbe.wait_to_reach_temp(T_Ga, PID='Ga', error=1)
        ts_print("Opening arsenic cracker valve and shutter")
        mbe.set_param("AsCracker.Valve.OP", as_valve_gaas)
        mbe.shutter("As", True)
        ts_print("Starting Ga shutter cycling")


        for x in range(1, t_growth_gaas): #only use if valve open time is 1 sec
            mbe.shutter("Ga", True)
            mbe.waiting(t_cycle_open)
            mbe.shutter("Ga", False)
            mbe.waiting(t_cycle_closed)


        mbe.shutter("Ga", False) #shutter should already be closed

        # Ramp down Ga
        ts_print("Growth finished")
        ts_print("Ramping down Ga")
        mbe.set_param("Ga.PV.TSP", 550)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down manip and cells")
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.wait_to_reach_temp(200, error=3)
        ts_print("Temperature reached 200, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
