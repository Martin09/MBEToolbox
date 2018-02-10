"""
***NEEDS WORK TO GET SB WORKING!***
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = True

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")
    calib_Sb = Calibration("As")  # NEED TO CHANGE THIS TO AN SB CALIBRATION!!!

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
        T_Ga = calib_Ga.calc_setpoint_gr(1.0)  # 1.0 A/s growth rate
        T_In = calib_In.calc_setpoint_gr(0.2)  # 0.2 A/s growth rate
        # T_Des_Anneal = 600  # Desired pyrometer temperature for anneal
        # T_Des_GaAs = 630  # Desired pyrometer temperature for GaAs growth
        # T_Des_InAs = 535  # Desired pyrometer temperature for InAs growth
        T_Des_Anneal_Manip = 705  # Desired manip temperature (pyro is broken)
        T_Des_GaAs_Manip = 750  # Desired manip temperature (pyro is broken)
        T_Des_InAs_Manip = 650  # Desired manip temperature for InAs growth
        T_Des_GaSb_Manip = 515  # Desired manip temperature for GaSb growth
        p_as_gaas = 4E-6  # Desired As pressure for GaAs growth
        p_as_inas = 1E-5  # Desired As pressure for InAs growth
        p_sb_gasb = 1E-5  # Desired Sb pressure for GaSb growth
        # NOT SURE ABOUT THIS PRESSURE RIGHT NOW!!
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        sb_valve_gasb = calib_Sb.calc_setpoint(p_sb_gasb)
        t_anneal = 10 * 60  # 10 minutes
        t_growth_gaas = 60 * 60  # 30 minutes
        t_growth_inas = 300
        t_growth_gasb = 300

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", 7)

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
        # mbe.set_param("Manip.PV.TSP", T_Des_Anneal + mbe.manip_offset)  # Anneal temperature
        mbe.set_param("Manip.PV.TSP", T_Des_Anneal_Manip)  # Anneal temperature
        ts_print("Ramping up Ga and In sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        mbe.set_param("In.PV.Rate", 15)
        mbe.set_param("In.OP.Rate", 0)
        mbe.set_param("In.PV.TSP", T_In)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        # mbe.wait_to_reach_temp(T_Des_Anneal + mbe.manip_offset, error=1)
        mbe.wait_to_reach_temp(T_Des_Anneal_Manip)
        mbe.timer_start()
        # mbe.converge_to_temp(T_Des_Anneal)  # Takes about 4min
        mbe.timer_wait(t_anneal)

        ##############################################################################
        # GaAs Membrane
        #############################################################################
        # Go to growth conditions
        # ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs + mbe.manip_offset))
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)
        # Wait until growth temperature is reached
        # mbe.wait_to_reach_temp(T_Des_GaAs + mbe.manip_offset, error=1)
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip)
        # mbe.converge_to_temp(T_Des_GaAs)  # Takes about 4min

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas)  # Wait Growth Time
        mbe.shutter("Ga", False)

        ##############################################################################
        # InAs Nanowire
        ##############################################################################

        # Go to InAs growth temp
        # ts_print("Going to InAs growth conditions, setting manip to {}".format(T_Des_InAs + mbe.manip_offset))
        ts_print("Going to InAs growth conditions, setting manip to {}".format(T_Des_InAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        # mbe.set_param("Manip.PV.TSP", T_Des_InAs + mbe.manip_offset)
        # mbe.wait_to_reach_temp(T_Des_InAs + mbe.manip_offset, error=1)
        mbe.set_param("Manip.PV.TSP", T_Des_InAs_Manip)
        mbe.wait_to_reach_temp(T_Des_InAs_Manip, error=1)

        # Set As flux, let it open during final temperature convergence
        mbe.set_param("AsCracker.Valve.OP", as_valve_inas)

        # mbe.converge_to_temp(T_Des_InAs)  # Takes about 4min

        # Start InAs Growth
        ts_print("Opening In shutter and waiting growth time")
        mbe.shutter("In", True)
        mbe.waiting(t_growth_inas)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)

        ##############################################################################
        # GaSb Passivation Shell
        ##############################################################################

        # Go to GaSb growth temp
        # ts_print("Going to GaSb growth conditions, setting manip to {}".format(T_Des_GaSb + mbe.manip_offset))
        ts_print("Going to GaSb growth conditions, setting manip to {}".format(T_Des_GaSb_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        # mbe.set_param("Manip.PV.TSP", T_Des_GsSb + mbe.manip_offset)
        # mbe.wait_to_reach_temp(T_Des_GaSb + mbe.manip_offset, error=1)
        mbe.set_param("Manip.PV.TSP", T_Des_GaSb_Manip)
        mbe.wait_to_reach_temp(T_Des_GaSb_Manip, error=1)

        # Close As and set Sb flux, let it open during final temperature convergence
        # THIS IS NOT GOING TO WORK!
        mbe.set_param("SbCracker.Valve.OP", sb_valve_gasb)
        mbe.set_param("AsCracker.Valve.OP", 0)
        mbe.shutter("Sb", True)
        mbe.shutter("As", False)

        # mbe.converge_to_temp(T_Des_GaSb)  # Takes about 4min

        # Start GaSb Growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gasb)  # Wait Growth Time
        ts_print("Closing Ga shutter")
        mbe.shutter("Ga", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.wait_to_reach_temp(200, error=3)
        ts_print("Temperature reached 200, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)
        mbe.set_param("SbCracker.Valve.OP", 0)  # THIS IS NOT GOING TO WORK!

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
