"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

# Nanowire growth as test for photodetector arrays
# Recipe from Martin Friedl


###########################
Rate_In = 0.2  # A/s
five_three_ratio = 110
###########################

run_virtual_server = False

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    # calib_Ga = Calibration("Ga", rheed_filename="2017-06-30_Ga.txt")
    calib_As = Calibration("As")

    with MBERecipe(virtual_server=run_virtual_server) as mbe:

        ts_print("Setting variables")

        # Define growth parameters
        # T_Ga = calib_Ga.calc_setpoint_gr(1.0)  # 1.0 A/s growth rate
        ###################
        T_Ga = 931  # UGLY TEMPORARY FIX UNTIL WE DO A PROPER RHEED!
        ###################
        T_In = calib_In.calc_setpoint_gr(Rate_In)  # 0.2 A/s growth rate
        # Using Tr2 holder!
        T_Des_Anneal_Manip = 780  # 780  # Desired manip temperature (pyro is broken)
        T_Des_GaAs_Manip = 780  # 780  # Desired manip temperature (pyro is broken)
        T_Des_InAs_Manip = 660  # 640  # Desired manip temperature for InAs growth
        p_as_gaas = 4E-6  # Desired As pressure for GaAs growth
        p_as_inas = calib_In.calc_p_arsenic(Rate_In, five_three_ratio)  # Desired As pressure for InAs growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        t_anneal = 10 * 60  # 30 minutes  ############CHANGED
        t_growth_gaas = 30 * 60  # 30 minutes
        # thickness_inas = 4  # nm
        # t_growth_inas = thickness_inas * 10 / Rate_In  # Always grow the same thickness of material

        print("T_Ga: {:.0f} deg C".format(T_Ga))
        # print("T_In: {:.0f} deg C".format(T_In))
        print("p_as_gaas: {:.2e} Torr".format(p_as_gaas))
        # print("p_as_inas: {:.2e} Torr".format(p_as_inas))
        print("as_valve_gaas: {:.2f}%".format(as_valve_gaas))
        # print("as_valve_inas: {:.2f}%".format(as_valve_inas))
        # print("t_growth_inas: {:.2f}s".format(t_growth_inas))

        # Prompt user if they are sure
        mbe.starting_growth_prompt()

        # Check that no other recipes are already running
        if not mbe.get_recipes_running() == 0:
            raise Exception("At least one recipe is running!")

        # Increment number of recipes flag and set recipes running to true
        mbe.start_recipe()

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
        # mbe.set_param("Manip.PV.TSP", T_Des_Anneal + mbe.manip_offset)  # Anneal temperature
        mbe.set_param("Manip.PV.TSP", T_Des_Anneal_Manip)  # Anneal temperature
        ts_print("Ramping up Ga and In sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        # mbe.set_param("In.PV.Rate", 15)
        # mbe.set_param("In.OP.Rate", 0)
        # mbe.set_param("In.PV.TSP", T_In)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        mbe.wait_to_reach_temp(T_Des_Anneal_Manip)
        mbe.waiting(t_anneal)  # Wait Growth Time

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

        ts_print("Ramping down Ga")
        mbe.set_param("Ga.PV.TSP", 550)

        # ##############################################################################
        # # InAs Nanowire
        # ##############################################################################
        #
        # # Go to InAs growth temp
        # ts_print("Going to InAs growth conditions, setting manip to {}".format(T_Des_InAs_Manip))
        # mbe.set_param("Manip.PV.Rate", 30)
        # mbe.set_param("Manip.PV.TSP", T_Des_InAs_Manip)
        # mbe.wait_to_reach_temp(T_Des_InAs_Manip, error=1)
        #
        # # Set As flux
        # mbe.set_param("AsCracker.Valve.OP", as_valve_inas)
        # mbe.waiting(30)  # Wait for cracker valve to open
        #
        #
        # # Start InAs Growth
        # ts_print("Opening In shutter and waiting growth time")
        # mbe.shutter("In", True)
        # mbe.waiting(t_growth_inas)  # Wait Growth Time
        # ts_print("Closing In shutter")
        # mbe.shutter("In", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.set_param("SUSI.OP.TSP", 10)
        mbe.wait_to_reach_temp(200, error=3)
        ts_print("Temperature reached 200, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        # Cap the sample with arsenic
        # mbe.as_capping()  # Before unloading sample, heat it to 100 degrees for ~5min

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
