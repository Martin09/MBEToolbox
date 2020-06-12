"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False

# Combination of the optimized InGaAs NW recipe yielding 50/50 Ga/In ratio in wires with modulation doping
# Combined recipe D1-17-09-03-B (mod doping) with growth parameters from D1-18-09-21-C (In @ 0.2 A/s, FTR of 100).
# Modified from D1-18-12-11-B, added shell growth from D1-19-05-07-A, changed marker from Al to In
# 05-B: Removed shell growth to see how NWs are growing
# 07-A: Decreased temperature by 20 degrees during InAs growth
# 09-A: Added APT shell step
# 02-C: Added 10 nm of blocking GaAs blocking layer after InAs and InGaAs layers

###########################
rate_ga = 1.0  # A/s
ftr_gaas = 25  # five three ratio
rate_in = 0.2  # A/s
ftr_inas = 110  # five three ratio
t_growth_shell = 1000  # seconds
rate_ga_shell = 1.0  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
rate_in_shell = 0.2  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibrations
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga", rheed_filename="2017-06-30_Ga.txt")
    calib_As = Calibration("As")

    with MBERecipe(virtual_server=run_virtual_server) as mbe:

        ts_print("Setting variables")
        # Define growth parameters
        # T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_Ga = 931  # Ga temp
        T_Ga_Shell = 931  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_In = calib_In.calc_setpoint_gr(rate_in)  # In temp
        T_In_Shell = calib_In.calc_setpoint_gr(rate_in_shell)  # In temp
        T_Anneal_Manip = 760  # Desired manip temperature (pyro is broken)
        T_GaAs_Manip = 750  # Desired manip temperature (pyro is broken)
        T_InAs_Manip = 640  # Desired manip temperature for InAs growth
        T_Shell_Manip = 550  # 200 deg lower than GaAs NM growth
        T_Shell_Manip_blockinglayer=450
        p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
        p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
        p_as_shell = 1.0E-5  # Desire d As pressure for GaAs shell growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        as_valve_shell = calib_As.calc_setpoint(p_as_shell)
        t_anneal = 10 * 60  # 10 minutes
        growth_rate_nanomembranes = 300.0 / 30.0 / 60.0  # ~300nm/30min/60sec
        thickness_dop = 6  # 6nm thick doped layer
        thickness_barrier = 2  # 2nm thick barrier
        t_growth_gaas = 30 * 60  # 30 minutes
        t_growth_dop = thickness_dop / growth_rate_nanomembranes
        t_growth_barrier = thickness_barrier / growth_rate_nanomembranes
        thickness_inas = 4  # nm
        t_growth_inas = thickness_inas * 10 / rate_in  # Always grow the same thickness of material
        Si_current = 40  # 40A
        thickness_blocking_gaas = 10 #10 nm blocking layer before and after InGaAs growth
        t_block_gaas=thickness_blocking_gaas * 10 / rate_ga

        print("T_Ga: {:.0f} deg C".format(T_Ga))
        print("T_In: {:.0f} deg C".format(T_In))
        print("T_In_Shell: {:.0f} deg C".format(T_In_Shell))
        print("p_as_gaas: {:.2e} Torr".format(p_as_gaas))
        print("p_as_inas: {:.2e} Torr".format(p_as_inas))
        print("p_as_shell: {:.2e} Torr".format(p_as_shell))
        print("as_valve_gaas: {:.2f}%".format(as_valve_gaas))
        print("as_valve_inas: {:.2f}%".format(as_valve_inas))
        print("as_valve_shell: {:.2f}%".format(as_valve_shell))
        print("t_growth_dop: {:.2f}s".format(t_growth_dop))
        print("t_growth_inas: {:.2f}s".format(t_growth_inas))
        print("t_growth_shell: {:.2f}s".format(t_growth_shell))
        print("t_block_gaas: {: .2f}s" .format(t_block_gaas))

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
        mbe.waiting(60 * 3)  # Wait 2min
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

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas - t_growth_dop - t_growth_barrier)  # Wait Growth Time
        mbe.shutter("SUSI", True)
        mbe.waiting(t_growth_dop)  # Wait doped layer growth time
        mbe.shutter("SUSI", False)
        mbe.waiting(t_growth_barrier)  # Wait barrier growth time
        mbe.shutter("Ga", False)


        ##############################################################################
        # InAs Nanowire
        ##############################################################################

        # Go to InAs growth temp
        ts_print("Going to InAs growth conditions, setting manip to {}".format(T_InAs_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_InAs_Manip)
        mbe.wait_to_reach_temp(T_InAs_Manip, error=1)

        # Set As flux, let it open during final temperature convergence
        mbe.set_param("AsCracker.Valve.OP", as_valve_inas)

        # Start InAs Growth
        ts_print("Opening In shutter and waiting growth time")
        mbe.shutter("In", True)
        mbe.waiting(t_growth_inas)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)

        ts_print("Close As valve a bit during cool-down")
        mbe.set_param("AsCracker.Valve.OP", as_valve_gaas)

        ##############################################################################
        # Shell Growth Starts
        #############################################################################
        #Setting up conditions for shell growth

        ts_print("Setting shell growth conditions")

        mbe.set_param("Ga.PV.TSP", T_Ga_Shell)
        mbe.set_param("In.PV.TSP", T_In_Shell)
        mbe.set_param("AsCracker.Valve.OP", as_valve_shell)

        mbe.wait_to_reach_temp(T_Ga_Shell, PID='Ga', error=1)
        mbe.wait_to_reach_temp(T_In_Shell, PID='In', error=1)

        # Set the conditions for first blocking layer
        ts_print("Going to blocking layer GaAs growth conditions, setting manip to {}".format(T_Shell_Manip_blockinglayer))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Shell_Manip_blockinglayer)

        mbe.wait_to_reach_temp(T_Shell_Manip_blockinglayer, error=1)

        ts_print("Opening Ga shutter")
        mbe.shutter("Ga", True)
        mbe.waiting(t_block_gaas)  # Wait Growth Time
        ts_print("Closing Ga shutter")
        mbe.shutter("Ga", False)


        # Set shell growth conditions
        ts_print("Going to shell growth conditions, setting manip to {}".format(T_Shell_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Shell_Manip)

        mbe.wait_to_reach_temp(T_Shell_Manip, error=1)


        # Start InGaAs Growth
        ts_print("Opening Ga shutter")
        mbe.shutter("Ga", True)
        mbe.waiting((t_growth_shell / 3)-t_block_gaas)  # Wait Growth Time
        ts_print("Opening In shutter")
        mbe.shutter("In", True)
        mbe.waiting(t_growth_shell / 3.)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)
        ts_print("Closing Ga shutter")
        mbe.shutter("Ga", False)

        # Set the conditions for second blocking layer
        ts_print("Going to shell growth conditions, setting manip to {}".format(T_Shell_Manip_blockinglayer))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Shell_Manip_blockinglayer)


        mbe.wait_to_reach_temp(T_Shell_Manip_blockinglayer, error=1)


        ts_print("Opening Ga shutter")
        mbe.shutter("Ga", True)
        mbe.waiting(t_block_gaas)  # Wait Growth Time
        ts_print("Closing Ga shutter")
        mbe.shutter("Ga", False)

        #Continuing GaAs shell growth
        ts_print("Going to blocking layer GaAs growth conditions, setting manip to {}".format(T_Shell_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Shell_Manip)
        mbe.wait_to_reach_temp(T_Shell_Manip, error=1)

        ts_print("Opening Ga shutter")
        mbe.shutter("Ga", True)
        mbe.waiting((t_growth_shell / 3)-t_block_gaas)  # Wait Growth Time
        ts_print("Closing Ga shutter")
        mbe.shutter("Ga", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.set_param("SUSI.OP.TSP", 10)
        mbe.wait_to_reach_temp(200, error=3)
        ts_print("Temperature reached 200, closing As valve and  shutter")
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
