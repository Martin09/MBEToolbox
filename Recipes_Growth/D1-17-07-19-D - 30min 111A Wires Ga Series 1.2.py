"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As", filename='2017-07-03_09-45-00_As.txt')

    with MBERecipe(virtual_server=run_virtual_server) as mbe:
        # Prompt user if they are sure
        mbe.starting_growth_prompt()

        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        # mbe.waiting(60)  # wait 60 minutes for As tank temp to stabilize at 378 again!!!

        mbe.ts_print("Setting variables")
        # Define growth parameters
        Ga_flux_gr = 1.2  # Normally ~1.0 A/s
        T_Ga = calib_Ga.calc_setpoint_gr(Ga_flux_gr)
        # T_In = calib_In.calc_setpoint(1.0E-7)
        # T_Des_Anneal = 600  # Desired pyrometer temperature for anneal
        # T_Des_GaAs = 630  # Desired pyrometer temperature for GaAs growth
        T_Des_Anneal_Manip = 750  # Desired manip temperature (pyro is broken)
        T_Des_GaAs_Manip = 750  # Desired manip temperature (pyro is broken)
        # T_Des_InAs = 535  # Desired pyrometer temperature for InAs growth
        p_as_gaas = 4E-6  # Desired As pressure for GaAs growth, 4E-6 originally
        # p_as_inas = 8E-6  # Desired As pressure for InAs growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        # as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        t_anneal = 10 * 60  # 10 minutes
        t_growth_gaas = 30 * 60 / Ga_flux_gr  # Normalize time to deposit same amount of material as for 1A/s for 30min
        # t_growth_inas = 200  # 200 seconds (4nm)
        # Si_current = 0  # 0A

        # Check that MBE parameters are in standby mode
        mbe.ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        mbe.ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", 7)

        # Check pressure before ramping up anything, make sure As valve is working
        mbe.ts_print("Opening arsenic cracker valve and shutter")
        mbe.set_param("AsCracker.Valve.OP", as_valve_gaas)
        mbe.shutter("As", True)
        mbe.waiting(60 * 3)  # Wait 3min
        mbe.ts_print("Checking pressure")
        if float(mbe.get_param("MBE.P")) < 1e-8:  # Make sure As valve opened properly
            mbe.set_param("Manip.PV.TSP", 200)
            mbe.set_param("Manip.PV.Rate", 100)
            raise Exception("Pressure still below 1e-8 after opening As. Something is wrong, aborting!")
        mbe.ts_print("Pressure looks good.")

        mbe.ts_print("Ramping to degassing temperature")
        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        # mbe.set_param("Manip.PV.TSP", T_Des_Anneal + mbe.manip_offset)  # Anneal temperature
        mbe.set_param("Manip.PV.TSP", T_Des_Anneal_Manip)  # Anneal temperature
        mbe.ts_print("Ramping up Ga and In sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        # mbe.set_param("In.PV.Rate", 15)
        # mbe.set_param("In.OP.Rate", 0)
        # mbe.set_param("In.PV.TSP", T_In)
        # mbe.ts_print("Ramping up SUSI cell",fn=log_fn)
        # mbe.set_param("SUSI.Mode", "Manual")
        # mbe.set_param("SUSI.OP.Rate", 2)
        # mbe.set_param("SUSI.OP.TSP", Si_current)

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
        # mbe.ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs + mbe.manip_offset),fn=log_fn)
        mbe.ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs_Manip)
        # Wait until growth temperature is reached
        # mbe.wait_to_reach_temp(T_Des_GaAs + mbe.manip_offset, error=1)
        mbe.wait_to_reach_temp(T_Des_GaAs_Manip)
        # mbe.converge_to_temp(T_Des_GaAs)  # Takes about 4min

        # Open Ga shutter and start growth
        mbe.ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas)  # Wait Growth Time
        mbe.shutter("Ga", False)

        # Ramp down Ga
        mbe.ts_print("Ramping down Ga")
        mbe.set_param("Ga.PV.TSP", 550)

        # ##############################################################################
        # # InAs Nanowire
        # ##############################################################################
        #
        # # Go to InAs growth temp
        # mbe.ts_print("Going to InAs growth conditions, setting manip to {}".format(T_Des_InAs + mbe.manip_offset),fn=log_fn)
        # mbe.set_param("Manip.PV.Rate", 30)
        # mbe.set_param("Manip.PV.TSP", T_Des_InAs + mbe.manip_offset)
        # mbe.wait_to_reach_temp(T_Des_InAs + mbe.manip_offset, error=1)
        #
        # # Set As flux, let it open during final temperature convergence
        # mbe.set_param("AsCracker.Valve.OP", as_valve_inas)
        #
        # mbe.converge_to_temp(T_Des_InAs)  # Takes about 4min
        #
        # # Start InAs Growth
        # mbe.ts_print("Opening In shutter and waiting growth time",fn=log_fn)
        # mbe.shutter("In", True)
        # mbe.shutter("SUSI", True)
        # mbe.waiting(t_growth_inas)  # Wait Growth Time
        # mbe.ts_print("Closing In shutter",fn=log_fn)
        # mbe.shutter("In", False)
        # mbe.shutter("SUSI", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        mbe.ts_print("Ramping down Manipulator")
        # mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.set_param("SUSI.OP.TSP", 10)
        mbe.wait_to_reach_temp(200, error=3)
        mbe.ts_print("Temperature reached 200, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        # Cap the sample with arsenic
        # mbe.as_capping(capping_time=30)  # Before unloading sample, heat it to 100 degrees for ~5min

        mbe.ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

        mbe.ts_print("Recipe Done.")

        if mbe.virtual_server:
            ts_print("Plotting the log file")
            mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])

