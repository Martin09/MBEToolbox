"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))  # Add parent directory to path
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

# Mod-doped nanomembrane growth for APT
# Growing doped regions in shell-growth regime (lower temp, high As pressure)
# Just a test to see if we can nail the desired height of the NMs (400nm)
# Ideas is then to see what width we get, if its in our desired range or not...
# Once we figure this out, then will add the doping steps and other markers within the NM growth step.
###########################
thickness_almarker1 = 20
thickness_markerspacer = 10
thickness_dop = 10  # 10nm thick doped layer
thickness_barrier = 10  # 5nm thick barrier
thickness_algaas_shell = 10
thickness_gaas_shell = 100
rate_ga = 1.0  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
rate_ga_shell = 1.0  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
rate_al_shell = 0.3  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
p_as_gaas = 4.0E-6  # Torr - Will calculate valve opening from this based on latest BFM calibrations
p_as_shell = 1.0E-5  # Torr - Will calculate valve opening from this based on latest BFM calibrations
###########################

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")
    calib_Al = Calibration("Al")

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
        T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)
        T_Ga_Shell = calib_Ga.calc_setpoint_gr(rate_ga_shell)
        T_Al_Shell = calib_Al.calc_setpoint_gr(rate_al_shell)
        T_Des_Anneal_Manip = 760  # Desired manip temperature (pyro is broken)
        T_Des_GaAs_Manip = 750  # Desired manip temperature (pyro is broken)
        T_Des_Shell_Manip = 450  # Desired manip temperature (since not using pyro)
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        as_valve_shell = calib_As.calc_setpoint(p_as_shell)
        t_anneal = 10 * 60  # 30 minutes
        t_growth_gaas = 30 * 60  # 30 minutes
        t_shell_growth = 1000  # seconds

        growth_rate_nanomembranes = 300.0 / 30.0 / 60.0  # ~300nm/30min/60sec
        t_growth_almarker = thickness_almarker1 / growth_rate_nanomembranes  # Assume Al doesn't add much to growth rate
        # t_growth_markerspacer = thickness_markerspacer / growth_rate_nanomembranes
        # Si_current = 30  # 30A
        #
        # GR_algaas_shell = (rate_ga_shell + rate_al_shell) / 2.  # Shell grows at 1/2 rate of a 2D layer (?)
        # t_growth_algaas = thickness_algaas_shell * 10. / GR_algaas_shell  # sec
        #
        # GR_gaas_shell = rate_ga_shell / 2.  # A/s - Shell grows at 1/2 rate of a 2D layer (?)
        # t_growth_dop = thickness_dop * 10. / GR_gaas_shell
        # t_growth_barrier = thickness_barrier * 10. / GR_gaas_shell
        # t_growth_gaas_shell = thickness_gaas_shell * 10. / GR_gaas_shell  # sec

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
        mbe.waiting(60 * 3)  # Wait 3min
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
        ts_print("Ramping up Al source")
        mbe.set_param("Al.PV.Rate", 20)
        mbe.set_param("Al.OP.Rate", 0)
        mbe.set_param("Al.PV.TSP", T_Al_Shell)
        # ts_print("Ramping up SUSI cell")
        # mbe.set_param("SUSI.Mode", "Manual")
        # mbe.set_param("SUSI.OP.Rate", 2)
        # mbe.set_param("SUSI.OP.TSP", Si_current)

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
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)
        # Wait until growth temperature is reached
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip)

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas - t_growth_almarker)
        mbe.shutter("Al", True)
        mbe.waiting(t_growth_almarker)
        mbe.shutter("Al", False)
        mbe.shutter("Ga", False)

        ##############################################################################
        # Shell Growth Starts
        #############################################################################
        # Set shell growth conditions
        ts_print("Going to shell growth conditions, setting manip to {}".format(T_Des_Shell_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_Shell_Manip)
        mbe.set_param("Ga.PV.TSP", T_Ga_Shell)
        mbe.set_param("Al.PV.TSP", T_Al_Shell)

        # Wait for manipulator and cell temperatures
        mbe.wait_to_reach_temp(T_Des_Shell_Manip, error=1)
        mbe.wait_to_reach_temp(T_Ga_Shell, PID='Ga', error=1)
        mbe.wait_to_reach_temp(T_Al_Shell, PID='Al', error=1)

        # Set As flux
        mbe.set_param("AsCracker.Valve.OP", as_valve_shell)

        # mbe.waiting(t_growth_almarker)
        # mbe.shutter("SUSI", True)
        # mbe.waiting(t_growth_dop)  # Wait doped layer growth time
        # mbe.shutter("SUSI", False)
        # mbe.waiting(t_growth_barrier)  # Wait barrier growth time
        # mbe.shutter("Ga", False)

        ##############################################################################
        # GaAs + AlGaAs + GaAs Shell
        ##############################################################################
        # Start AlGaAs Growth
        ts_print("Opening Ga shutter")
        mbe.shutter("Ga", True)
        mbe.waiting(t_shell_growth/3.)  # Wait Growth Time
        ts_print("Opening Al shutter")
        mbe.shutter("Al", True)
        mbe.waiting(t_shell_growth/3.)  # Wait Growth Time
        ts_print("Closing Al shutter")
        mbe.shutter("Al", False)
        mbe.waiting(t_shell_growth/3.)  # Wait Growth Time
        ts_print("Closing Al shutter")
        mbe.shutter("Ga", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("Al.PV.TSP", 750)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        # mbe.set_param("SUSI.OP.TSP", 10)
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