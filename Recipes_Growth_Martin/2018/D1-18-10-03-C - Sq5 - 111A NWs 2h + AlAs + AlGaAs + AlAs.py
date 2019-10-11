"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False
use_pyro = False

# Indium/III-V ratio series
###########################
rate_ga = 1.0  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
rate_ga_shell = 0.568  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
rate_al_shell = 0.284  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
p_as_gaas = 4.0E-6  # Torr - Will calculate valve opening from this based on latest BFM calibrations
p_as_shell = 1.2E-5  # Torr - Will calculate valve opening from this based on latest BFM calibrations
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_Ga = Calibration("Ga")
    calib_Al = Calibration("Al")
    calib_As = Calibration("As")

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
        # T_Des_Anneal = 610  # Desired pyrometer temperature for anneal - Unused since pyro isn't being used
        # T_Des_GaAs = 630  # Desired pyrometer temperature for GaAs growth - Unused since pyro isn't being used
        # T_Des_Shell = 460 # Desired pyrometer temperature for AlGaAs growth - Unused since pyro isn't being used
        T_Des_Anneal_Manip = 750  # Desired manip temperature (since not using pyro)
        T_Des_GaAs_Manip = 750  # Desired manip temperature (since not using pyro)
        T_Des_Shell_Manip = 530  # Desired manip temperature (since not using pyro)
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        as_valve_shell = calib_As.calc_setpoint(p_as_shell)
        t_anneal = 10 * 60  # 10 minutes
        t_growth_gaas = 2 * 60 * 60  # 60 minutes

        thickness_alas_shell_1 = 10  # nm
        GR_alas_shell = rate_al_shell / 4.  # Shell grows at 1/4 rate of a 2D layer (for vert. NWs)
        t_growth_alas_1 = thickness_alas_shell_1 * 10. / GR_alas_shell  # sec

        thickness_algaas_shell = 50  # nm
        GR_algaas_shell = (rate_ga_shell + rate_al_shell) / 4.  # Shell grows at 1/4 rate of a 2D layer (for vert. NWs)
        t_growth_algaas = thickness_algaas_shell * 10. / GR_algaas_shell  # sec

        thickness_alas_shell_2 = 30  # nm
        GR_alas_shell = rate_al_shell / 4.  # Shell grows at 1/4 rate of a 2D layer (for vert. NWs)
        t_growth_alas_2 = thickness_alas_shell_2 * 10. / GR_alas_shell  # sec

        thickness_gaas_shell = 20  # nm, normally 5 nm but we want to be safe and covered on the bottom of the NWs
        GR_gaas_shell = rate_ga_shell / 4.  # A/s - Shell grows at 1/4 rate of a 2D layer (for vert. NWs)
        t_growth_gaas_shell = thickness_gaas_shell * 10. / GR_gaas_shell  # sec

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", -7)  # use negative rotation because manip has some problems turning positively

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

        # # Want to save the BFM so don't use it to converge
        # # Converge with BFM to desired InAs growth As pressure, save the correct As opening for use later
        # ts_print("Converging with BFM for As pressure in InAs growth, saving it for later")
        # as_valve_inas = mbe.converge_with_bfm(p_as_inas, calib_As, withdraw_bfm=False)  # Takes about 5 min

        # Converge with BFM to desired GaAs growth As pressure
        # ts_print("Converging with BFM for As pressure in GaAs growth")
        # as_valve_gaas = mbe.converge_with_bfm(p_as_gaas, calib_As)  # Takes about 5 min

        ts_print("Ramping to degassing temperature")
        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", T_Des_Anneal_Manip)  # Anneal temperature
        ts_print("Ramping up Ga and Al sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        mbe.set_param("Al.PV.Rate", 20)
        mbe.set_param("Al.OP.Rate", 0)
        mbe.set_param("Al.PV.TSP", T_Al_Shell)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        mbe.wait_to_reach_temp(T_Des_Anneal_Manip, error=1)
        mbe.timer_start()
        if use_pyro:
            mbe.converge_to_temp(T_Des_Anneal)  # Takes about 4min
        mbe.timer_wait(t_anneal)

        ##############################################################################
        # GaAs NW
        #############################################################################
        # Go to NW growth conditions
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)

        # Wait for manipulator and cell temperatures
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip, error=1)
        mbe.wait_to_reach_temp(T_Ga, PID='Ga', error=1)

        if use_pyro:
            mbe.converge_to_temp(T_Des_GaAs)  # Takes about 4min

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas)  # Wait Growth Time
        mbe.shutter("Ga", False)

        ##############################################################################
        # AlAs Shell
        ##############################################################################
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

        if use_pyro:
            mbe.converge_to_temp(T_Des_Shell)  # Takes about 4min

        mbe.shutter("Al", True)
        mbe.waiting(t_growth_alas_1)  # Wait Growth Time
        mbe.shutter("Al", False)

        ##############################################################################
        # AlGaAs Shell
        ##############################################################################

        # Start AlGaAs Growth
        ts_print("Opening Ga+Al shutters and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.shutter("Al", True)
        mbe.waiting(t_growth_algaas)  # Wait Growth Time
        ts_print("Closing Al shutters")
        mbe.shutter("Al", False)
        mbe.shutter("Ga", False)

        ##############################################################################
        # AlAs Shell
        ##############################################################################
        mbe.shutter("Al", True)
        mbe.waiting(t_growth_alas_2)  # Wait Growth Time
        mbe.shutter("Al", False)

        # Ramp down aluminum
        mbe.set_param("Al.PV.TSP", 750)

        ##############################################################################
        # GaAs Shell
        ##############################################################################
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas_shell)  # Wait Growth Time
        mbe.shutter("Ga", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        # Ramp down manipulator and cells
        ts_print("Ramping down cells")
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.set_param("Ga.PV.TSP", 650)
        mbe.wait_to_reach_temp(200, error=3)

        # Close As once sample is cool
        ts_print("Temperature reached 200, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        # Cap the sample with arsenic
        # mbe.as_capping(capping_time=30)  # Before unloading sample, heat it to 100 degrees for ~5min

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
