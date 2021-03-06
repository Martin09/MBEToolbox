"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False
use_pyro = False

# Low GR growth, starting with conditions that I am used to (T=630, P_As=4E-6) and just decreasing Ga rate to 0.3 A/s
# Try InAs with copenhagen growth conditions, no Sb though
# Cracker is at 950
# 09-04-B - Lowered manip temperature of both GaAs and InAs steps by 20 degrees.
# 10-04-B - Increased temps by 40 degrees because growing on the Ch1 holder. Cracker is only at 600.
# 10-18-A - Added pause after Ga shutter close to check that it is indeed closed.
# 12-12-B - Repeating of growth from 18-10-20-D to check conditions with new calibration files/conversion function
# 12-14-B - Same recipe, just now using As2 instead of As4
###########################
rate_ga = 0.3  # A/s
ftr_gaas = 80  # five three ratio
rate_in = 0.35  # A/s
ftr_inas = 10  # five three ratio
###########################

# If running the script locally:
if __name__ == '__main__':
    # Conversion function used to convert from pressures read by new BFM to the old BFM (changed mid-Oct 2018)
    conv_func_As = lambda old_P: 0.861 * old_P + 1.37E-7
    calib_As = Calibration("As", bfm_correction=conv_func_As, filename="2018-12-14_11-14-22_TCrck950_As.txt")
    conv_func_GroupIII = lambda old_P: 0.621 * old_P + 4.58E-10
    calib_In = Calibration("In", bfm_correction=conv_func_GroupIII, filename="2018-10-30_16-50-59_In.txt",
                           rheed_filename="2017-06-30_In.txt")
    calib_Ga = Calibration("Ga", bfm_correction=conv_func_GroupIII, filename="2018-10-30_14-36-43_Ga.txt",
                           rheed_filename="2017-06-30_Ga.txt")

    ts_print("Setting variables")
    # --- Cell growth parameters --- #
    T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
    T_In = calib_In.calc_setpoint_gr(rate_in)  # In temp
    # --- Manipulator temperatures --- #
    T_Anneal_Manip = 800  # Desired manip temperature (pyro is broken)
    T_GaAs_Manip = 770  # Desired manip temperature (pyro is broken)
    T_InAs_Manip = 660  # Desired manip temperature for InAs growth
    # --- Group V pressures --- #
    p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
    p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
    p_as_anneal = p_as_gaas  # Try to reduce this later
    # --- Group V valve openings --- #
    as_valve_anneal = calib_As.calc_setpoint(p_as_anneal)
    as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
    as_valve_inas = calib_As.calc_setpoint(p_as_inas)
    # --- Timing --- #
    t_anneal = 10 * 60  # 30 minutes
    thickness_gaas = 100  # nm
    t_growth_gaas = thickness_gaas * 10 / rate_ga  # Always grow the same thickness of material
    thickness_inas = 63  # nm
    t_growth_inas = thickness_inas * 10 / rate_in  # Always grow the same thickness of material

    print("T_Ga: {:.0f} deg C".format(T_Ga))
    print("T_In: {:.0f} deg C".format(T_In))
    print("p_as_anneal: {:.2e} Torr".format(p_as_anneal))
    print("p_as_gaas: {:.2e} Torr".format(p_as_gaas))
    print("p_as_inas: {:.2e} Torr".format(p_as_inas))
    print("as_valve_anneal: {:.2f}%".format(as_valve_anneal))
    print("as_valve_gaas: {:.2f}%".format(as_valve_gaas))
    print("as_valve_inas: {:.2f}%".format(as_valve_inas))
    print("t_growth_gaas: {:.2f}s".format(t_growth_gaas))
    print("t_growth_inas: {:.2f}s".format(t_growth_inas))

    with MBERecipe(virtual_server=run_virtual_server) as mbe:
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
        mbe.set_param("AsCracker.Valve.OP", as_valve_anneal)
        mbe.shutter("As", True)
        mbe.waiting(60 * 1)  # Wait 1min
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
        mbe.waiting(10)  # Wait for cracker valve to open

        # Start InAs Growth
        ts_print("Opening In shutter and waiting growth time")
        mbe.shutter("In", True)
        mbe.waiting(t_growth_inas)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)

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

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
