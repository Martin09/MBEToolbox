"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    grow = raw_input('Starting a growth! Are you sure? (y/n):  ')
    if not (grow.lower() == 'y'):
        print('Exiting...')
        exit()
    else:
        print('Starting growth!')

    calib_In = Calibration("In", filename='2017-03-05_13-10-54_In.txt')
    calib_Ga = Calibration("Ga", filename='2017-03-05_11-28-33_Ga.txt')
    calib_As = Calibration("As", filename='2017-03-05_10-04-40_As.txt')

    with MBERecipe(virtual_server=run_virtual_server) as mbe:
        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

        # mbe.waiting(60*5)  # wait 60a before starting the recipe

        ts_print("Setting variables")
        # Define growth parameters
        T_Ga = calib_Ga.calc_setpoint(2.4E-7)
        T_In = calib_In.calc_setpoint(7.0E-8)  # roughly ?? A/s
        T_Des_Anneal = 650  # Desired pyrometer temperature for anneal
        T_Des_GaAs = 630  # Desired pyrometer temperature for GaAs growth
        T_Des_InAs = 540  # Desired pyrometer temperature for InAs growth
        p_as = 4E-6  # Desired As pressure for GaAs growth
        As_Valve = calib_As.calc_setpoint(p_as)
        As_Valve_InAs = 100  # calib_As.calc_setpoint(9.5E-6)  # 100% opening
        Growth_Time = 30 * 60  # 30 minutes
        Growth_Time_InAs = 100  # 100 seconds (2nm)
        Si_current = 40  # 40A = 2.1E20 cm-3

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", 7)

        # Check pressure before ramping up anything, make sure As valve is working
        ts_print("Opening arsenic cracker valve and shutter")
        mbe.set_param("AsCracker.Valve.OP", As_Valve)
        mbe.shutter("As", True)
        mbe.waiting(60 * 3)  # Wait 3min
        ts_print("Checking pressure")
        if float(mbe.get_param("MBE.P")) < 1e-8:  # Make sure As valve opened properly
            mbe.set_param("Manip.PV.TSP", 200)
            mbe.set_param("Manip.PV.Rate", 100)
            raise Exception("Pressure still below 1e-8 after opening As. Something is wrong, aborting!")

        # Converge with BFM to desired As pressure
        mbe.converge_with_bfm(p_as, calib_As)  # Takes about 5 min

        ts_print("Pressure looks good.")
        ts_print("Ramping to degassing temperature")
        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", T_Des_Anneal + mbe.manip_offset)  # Anneal temperature
        ts_print("Ramping up Ga and In sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        mbe.set_param("In.PV.Rate", 15)
        mbe.set_param("In.OP.Rate", 0)
        mbe.set_param("In.PV.TSP", T_In)
        ts_print("Ramping up SUSI cell")
        mbe.set_param("SUSI.Mode", "Manual")
        mbe.set_param("SUSI.OP.Rate", 2)
        mbe.set_param("SUSI.OP.TSP", Si_current)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        mbe.wait_to_reach_temp(T_Des_Anneal + mbe.manip_offset, error=1)
        mbe.timer_start()
        mbe.converge_to_temp(T_Des_Anneal)  # Takes about 4min
        # mbe.waiting(60 * 26)  # Wait 26min (total about 30min)
        mbe.timer_wait(60 * 30)  # Wait 30min during anneal

        ##############################################################################
        # GaAs Membrane
        #############################################################################
        # Go to growth conditions
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Des_GaAs + mbe.manip_offset))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_GaAs + mbe.manip_offset)
        # Wait until growth temperature is reached
        mbe.wait_to_reach_temp(T_Des_GaAs + mbe.manip_offset, error=1)
        mbe.converge_to_temp(T_Des_GaAs)  # Takes about 4min

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(Growth_Time)  # Wait Growth Time
        mbe.shutter("Ga", False)

        # Ramp down Ga
        ts_print("Ramping down Ga")
        mbe.set_param("Ga.PV.TSP", 550)

        ##############################################################################
        # InAs Nanowire
        ##############################################################################

        # Go to InAs growth temp
        ts_print("Going to InAs growth conditions, setting manip to {}".format(T_Des_InAs + mbe.manip_offset))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Des_InAs + mbe.manip_offset)
        mbe.wait_to_reach_temp(T_Des_InAs + mbe.manip_offset, error=1)

        # Set As flux, let it open during final temperature convergence
        mbe.set_param("AsCracker.Valve.OP", As_Valve_InAs)

        mbe.converge_to_temp(T_Des_InAs)  # Takes about 4min

        # Start InAs Growth
        ts_print("Opening In shutter and waiting growth time")
        mbe.shutter("In", True)
        mbe.shutter("SUSI", True)
        mbe.waiting(Growth_Time_InAs)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)
        mbe.shutter("SUSI", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down In and Manipulator")
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.set_param("SUSI.OP.TSP", 10)
        mbe.wait_to_reach_temp(300, error=3)
        ts_print("Temperature reached 300, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        # Cap the sample with arsenic
        # mbe.as_capping(capping_time=40)  # Before unloading sample, heat it to 100 degrees for ~5min

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log()
