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
#Chip substrate ID : 800002879885
#Same growth with D1-19-10-02-C we only test the NW growth on different substrate chip. Substrate could be problematic.
#Repetition of D1-19-10-09-B
###########################
rate_ga = 1.0  # A/s
ftr_gaas = 25  # five three ratio
rate_in = 0.2  # A/s
ftr_inas = 62  # five three ratio
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In")
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")

    with MBERecipe(virtual_server=run_virtual_server) as mbe:

        ts_print("Setting variables")
        # Define growth parameters
        T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        #T_Ga = 931  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_In = calib_In.calc_setpoint_gr(rate_in)  # In temp

        T_Anneal_Manip = 810  # Desired manip temperature (pyro is broken)
        T_GaAs_Manip = 800  # Desired manip temperature (pyro is broken)
        T_InAs_Manip = 700  # Desired manip temperature for InAs growth
        p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
        p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        t_anneal = 10 * 60  # 10 minutes
        growth_rate_nanomembranes = 300.0 / 30.0 / 60.0  # ~300nm/30min/60sec
        t_growth_gaas = 30 * 60  # 30 minutes
        thickness_inas = 8  # nm
        t_growth_inas = thickness_inas * 10 / rate_in  # Always grow the same thickness of material

        print("T_Ga: {:.0f} deg C".format(T_Ga))
        print("T_In: {:.0f} deg C".format(T_In))
        print("p_as_gaas: {:.2e} Torr".format(p_as_gaas))
        print("p_as_inas: {:.2e} Torr".format(p_as_inas))
        print("as_valve_gaas: {:.2f}%".format(as_valve_gaas))
        print("as_valve_inas: {:.2f}%".format(as_valve_inas))
        print("t_growth_inas: {:.2f}s".format(t_growth_inas))


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
        ts_print("Ramping up Ga source")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        mbe.set_param("In.PV.Rate", 15)
        mbe.set_param("In.OP.Rate", 0)
        mbe.set_param("In.PV.TSP", T_In)


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
        mbe.waiting(t_growth_gaas)  # Wait Growth Time
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
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
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
