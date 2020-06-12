"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False
use_pyro = False

# D1-19-05-07-B: First test of InAs NW growth on new substrate 000045672829
# D1-19-05-10-C: Same as 05-08-A, control sample, no GaAs shell
# D1-19-05-28-F: ARPES chip, only GaAs growth. In stuck to dummy Si wafer. So decreaased temps by 30 to 740 manip.
# D1-19-05-30-C: ARPES chip. Same as 28-F but reduced anneal/growth temp further by 20 degrees.
# D1-19-06-01-A: ARPES chip. First chip from second wafer just finished yesterday.
# D1-19-07-05-A: 2nm SL chip. First test growth from MOVPE SL chip for back gating. Removing doping commands.
# D1-19-07-09-A: 2nm SL chip. Removed InAs growth step to check GaAs buffer growth.
# D1-19-07-15-B: 2nm SL chip. Double GaAs thickness, added InAs growth back in.
# D1-19-07-17-B: 2nm SL chip. Increased InAs growth temp by 20 deg. [got InAs on top!]
# D1-19-07-18-C: 2nm SL chip. Decreased GaAs growth time, increased InAs growth time. Same temp.

###########################
rate_ga = 0.3  # A/s
ftr_gaas = 80  # five three ratio
rate_in = 0.35  # A/s
ftr_inas = 10  # five three ratio
ftr_gaas_shell = 200  # five three ratio
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")

    with MBERecipe(virtual_server=run_virtual_server) as mbe:

        ts_print("Setting variables")
        # Define growth parameters
        # T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_Ga = 877  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_In = calib_In.calc_setpoint_gr(rate_in)  # In temp
        # Set 735 to get 625-630 in IR camera
        T_Anneal_Manip = 715  # Desired manip temperature (pyro is broken)
        T_GaAs_Manip = 695  # Desired manip temperature (pyro is broken)
        T_InAs_Manip = 635  # Desired manip temperature for InAs growth
        p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        t_anneal = 10 * 60  # 10 minutes
        thickness_gaas = 140  # nm
        t_growth_gaas = thickness_gaas * 10 / rate_ga  # Always grow the same thickness of material
        thickness_inas = 100  # nm
        t_growth_inas = thickness_inas * 10 / rate_in  # Always grow the same thickness of material
        # si_current = 0  # 40A

        print("T_Ga: {:.0f} deg C".format(T_Ga))
        print("T_In: {:.0f} deg C".format(T_In))
        print("p_as_gaas: {:.2e} Torr".format(p_as_gaas))
        print("p_as_inas: {:.2e} Torr".format(p_as_inas))
        print("as_valve_gaas: {:.2f}%".format(as_valve_gaas))
        print("as_valve_inas: {:.2f}%".format(as_valve_inas))
        print("t_growth_inas: {:.2f}s".format(t_growth_inas))
        # print("si_current: {:.0f}A".format(si_current))

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
        mbe.set_param("Manip.PV.TSP", T_Anneal_Manip)  # Anneal temperature
        ts_print("Ramping up Ga")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        ts_print("Ramping up In")
        mbe.set_param("In.PV.Rate", 15)
        mbe.set_param("In.OP.Rate", 0)
        mbe.set_param("In.PV.TSP", T_In)
        # ts_print("Ramping up SUSI cell")
        # mbe.set_param("SUSI.Mode", "Manual")
        # mbe.set_param("SUSI.OP.Rate", 2)
        # mbe.set_param("SUSI.OP.TSP", si_current)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        mbe.wait_to_reach_temp(T_Anneal_Manip)
        mbe.waiting(t_anneal)

        ##############################################################################
        # GaAs Membrane
        #############################################################################
        # Go to growth conditions
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_GaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_GaAs_Manip)
        # Wait until growth temperature is reached
        mbe.wait_to_reach_temp(T_GaAs_Manip)
        if use_pyro:
            mbe.converge_to_temp(T_GaAs_Manip)  # Takes about 4min

        # Open Ga shutter and start growth
        ts_print("Opening Ga + SUSI shutters and waiting growth time")
        # mbe.shutter("SUSI", True)
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas)  # Wait Growth Time
        mbe.shutter("Ga", False)
        # mbe.shutter("SUSI", False)

        ts_print("Ramping down Ga")
        mbe.set_param("Ga.PV.TSP", 550)

        ##############################################################################
        # InAs Nanowire
        ##############################################################################

        # Go to InAs growth temp
        ts_print("Going to InAs growth conditions, setting manip to {}".format(T_InAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)

        mbe.set_param("Manip.PV.TSP", T_InAs_Manip)
        mbe.wait_to_reach_temp(T_InAs_Manip, error=1)

        # Set As flux
        mbe.set_param("AsCracker.Valve.OP", as_valve_inas)
        mbe.waiting(30)  # Wait for cracker valve to open

        # Start InAs Growth
        ts_print("Opening In shutter and waiting growth time")
        mbe.shutter("In", True)
        mbe.waiting(t_growth_inas)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        mbe.set_param("AsCracker.Valve.OP", 40)  # Set moderate As flux for cool-down
        ts_print("Ramping down Manipulator")
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("SUSI.OP.TSP", 10)
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
