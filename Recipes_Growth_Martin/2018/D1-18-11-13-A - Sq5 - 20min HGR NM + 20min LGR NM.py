"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))  # Add parent directory to path
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

# Trying to grow a nanomembrane tall and then reduce its growth rate to encourage the formation of a flat top facet
# 11-13-A - Reverted to old calibration files and also trying again, last time Sb cracker outgassed all over the sample.
###########################
rate_ga = 1.0  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
rate_ga2 = 0.3  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
p_as_gaas = 4.0E-6  # Torr - Will calculate valve opening from this based on latest BFM calibrations
ftr_gaas2 = 80
###########################

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    calib_Ga = Calibration("Ga", filename="2018-08-31_13-51-50_Ga.txt", rheed_filename="2017-06-30_Ga.txt")
    calib_As = Calibration("As", filename="2018-10-02_17-45-23_As.txt")

    with MBERecipe(virtual_server=run_virtual_server, stdby_at_exit=True) as mbe:
        # Prompt user if they are sure
        mbe.starting_growth_prompt()

        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()
        ts_print("Setting variables")

        # Define growth parameters
        T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)
        T_Ga2 = calib_Ga.calc_setpoint_gr(rate_ga2)
        T_Des_Anneal_Manip = 760  # Desired manip temperature (pyro is broken)
        T_Des_GaAs_Manip = 750  # Desired manip temperature (pyro is broken)
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        p_as_gaas2 = calib_Ga.calc_p_arsenic(rate_ga2, ftr_gaas2)  # Desired As pressure for GaAs growth
        as_valve_gaas2 = calib_As.calc_setpoint(p_as_gaas2)
        t_anneal = 10 * 60  # 30 minutes
        t_growth_gaas1 = 20 * 60  # 30 minutes
        t_growth_gaas2 = 20 * 60  # 30 minutes

        Si_current = 30  # 30A

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", -7)

        # Check pressure before ramping up anything, make sure As valve is working
        ts_print("Opening arsenic cracker valve and shutter")
        mbe.set_param("AsCracker.Valve.OP", as_valve_gaas)
        mbe.shutter("As", True)
        mbe.waiting(60 * 1)  # Wait 3min
        ts_print("Checking pressure")
        if float(mbe.get_param("MBE.P")) < 1e-8:  # Make sure As valve opened properly
            mbe.set_param("Manip.PV.TSP", 200)
            mbe.set_param("Manip.PV.Rate", 100)
            raise Exception(
                "Pressure still below 1e-8 after opening As. Something is wrong, check As valve, shutter and tank temperature!")
        ts_print("Pressure looks good.")

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
        mbe.timer_start()
        mbe.timer_wait(t_anneal)

        ##############################################################################
        # GaAs Membrane
        #############################################################################
        # Go to growth conditions
        ts_print("Going to GaAs HGR conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)
        # Wait until growth temperature is reached
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip)

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas1)
        mbe.shutter("Ga", False)

        ##############################################################################
        # Shell Growth Starts
        #############################################################################
        # Set shell growth conditions
        ts_print("Going to GaAs LGR conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)
        mbe.set_param("Ga.PV.TSP", T_Ga2)

        # Set As flux
        mbe.set_param("AsCracker.Valve.OP", as_valve_gaas2)

        # Wait for manipulator and cell temperatures
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip, error=1)
        mbe.wait_to_reach_temp(T_Ga2, PID='Ga', error=1)

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas2)
        mbe.shutter("Ga", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
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
