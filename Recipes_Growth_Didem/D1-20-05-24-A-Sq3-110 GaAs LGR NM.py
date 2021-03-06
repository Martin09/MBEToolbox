"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""


from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False
use_pyro = False
run_growth ={'Annealing':True,
             'GaAs_Membrane_Growth':True,
             'InAs_NW_Growth':False,
             'GaAs_passivation_layer':False}


# Chip ID:

###########################
rate_ga = 0.15  # A/s
ftr_gaas = 110  # five three ratio
rate_in = 0.35  # A/s
ftr_inas = 10  # five three ratio
rate_ga_shell = 1.0  # A/s - Will calculate cell temp from this based on latest RHEED/BFM calibration
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_In = Calibration("In", rheed_filename="2017-06-30_In.txt")
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")

    with MBERecipe(virtual_server=run_virtual_server) as mbe:

        ts_print("Setting variables")

        # Define growth parameters
        T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        # T_Ga = 877  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_Ga_Shell = 931  # Ga temp
        T_In = calib_In.calc_setpoint_gr(rate_in)  # In temp
        T_Anneal_Manip = 730  # Desired manip temperature (pyro is broken)
        T_GaAs_Manip = 730  # Desired manip temperature (pyro is broken)
        T_InAs_Manip = 660  # Desired manip temperature for InAs growth
        T_GaAs_Shell_Manip = 480  # Desired manip temperature for GaAs

        p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        p_as_shell = 1.0E-5   # Desired As pressure for GaAs shell growth
        as_valve_shell = calib_As.calc_setpoint(p_as_shell)
        t_anneal = 10 * 60  # 10 minutes
        thickness_gaas = 100  # nm
        t_growth_gaas = thickness_gaas * 10 / rate_ga  # Always grow the same thickness of material
        thickness_shell = 10  # nm
        t_growth_shell = thickness_shell * 10 / rate_ga_shell
        thickness_inas = 63  # nm
        t_growth_inas = thickness_inas * 10 / rate_in  # Always grow the same thickness of material

        print("T_Ga: {:.0f} deg C".format(T_Ga))
        #print("T_In: {:.0f} deg C".format(T_In))
        #print("T_GaAs_Shell_Manip: {:.0f} deg C".format(T_GaAs_Shell_Manip))
        print("p_as_gaas: {:.2e} Torr".format(p_as_gaas))
        #print("p_as_inas: {:.2e} Torr".format(p_as_inas))
        #print("p_as_shell: {:.2e} Torr".format(p_as_shell))
        print("as_valve_gaas: {:.2f}%".format(as_valve_gaas))
        #print("as_valve_inas: {:.2f}%".format(as_valve_inas))
        #print("as_valve_gaas_shell: {:.2f}%".format(as_valve_shell))
        #print("t_growth_inas: {:.2f}s".format(t_growth_inas))
        #print("t_growth_shell: {:.2f}s".format(t_growth_shell))

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
        ts_print("Ramping up Ga sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        #mbe.set_param("In.PV.Rate", 15)
        #mbe.set_param("In.OP.Rate", 0)
        #mbe.set_param("In.PV.TSP", T_In)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        if run_growth['Annealing']:
            mbe.wait_to_reach_temp(T_Anneal_Manip)
            mbe.timer_start()
            if use_pyro:
                mbe.converge_to_temp(T_Anneal_Manip)  # Takes about 4min
            mbe.timer_wait(t_anneal)

        ##############################################################################
        # GaAs Membrane
        #############################################################################
        # Go to growth conditions
        if run_growth['GaAs_Membrane_Growth']:
            ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_GaAs_Manip))
            mbe.set_param("Manip.PV.Rate", 30)
            mbe.set_param("Manip.PV.TSP", T_GaAs_Manip)
            # Wait until growth temperature is reached
            mbe.wait_to_reach_temp(T_GaAs_Manip)
            if use_pyro:
                mbe.converge_to_temp(T_GaAs_Manip)  # Takes about 4min

            # Open Ga shutter and start growth
            ts_print("Opening Ga shutter and waiting growth time")
            mbe.shutter("Ga", True)
            mbe.waiting(t_growth_gaas)  # Wait Growth Time
            mbe.shutter("Ga", False)


            mbe.waiting(30)  # Wait to check if shutter closed properly

        # ##############################################################################
        # # InAs Nanowire
        # ##############################################################################

        # # Go to InAs growth temp
        if run_growth['InAs_NW_Growth']:
            ts_print("Going to InAs growth conditions, setting manip to {}".format(T_InAs_Manip))
            mbe.set_param("Manip.PV.Rate", 30)

            mbe.set_param("Manip.PV.TSP", T_InAs_Manip)
            mbe.wait_to_reach_temp(T_InAs_Manip, error=1)
            #
            # # Set As flux
            mbe.set_param("AsCracker.Valve.OP", as_valve_inas)
            mbe.waiting(30)  # Wait for cracker valve to open
            #
            # if use_pyro:
            #     mbe.converge_to_temp(T_InAs_Manip)  # Takes about 4min
            #
            # # Start InAs Growth
            ts_print("Opening In shutter and waiting growth time")
            mbe.shutter("In", True)
            mbe.waiting(t_growth_inas)  # Wait Growth Time
            ts_print("Closing In shutter")
            mbe.shutter("In", False)

        # ##############################################################################
        # # GaAs Passivation Layer
        # ##############################################################################
        # # Go to GaAs shell growth temp
        if run_growth['GaAs_passivation_layer']:
            ts_print("Going to GaAs shell growth conditions, setting manip to {}".format(T_GaAs_Shell_Manip))


            mbe.set_param("Ga.PV.TSP", T_Ga_Shell)
            mbe.wait_to_reach_temp(T_Ga_Shell, PID='Ga', error=1)

            mbe.set_param("Manip.PV.Rate", 30)
            mbe.set_param("Manip.PV.TSP", T_GaAs_Shell_Manip)
            mbe.wait_to_reach_temp(T_GaAs_Shell_Manip, error=1)
            #
            # # Set As flux
            mbe.set_param("AsCracker.Valve.OP", as_valve_shell)
            mbe.waiting(30)  # Wait for cracker valve to open
            #
            # # Open Ga shutter and start growth
            ts_print("Opening Ga shutter and waiting growth time")
            mbe.shutter("Ga", True)
            mbe.waiting(t_growth_shell)  # Wait Growth Time
            mbe.shutter("Ga", False)


        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        mbe.set_param("AsCracker.Valve.OP", 40)  # Set moderate As flux for cool-down
        ts_print("Ramping down Manipulator")
        mbe.set_param("Ga.PV.TSP", 550)
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

    ##############################################################################
    # Saving the recipe parameters
    ##############################################################################
    ts_print('Plotting Recipe Parameter')
    fname = __file__.split('/')[-1].split(' ')[0]
    file = open('Recipes_text_files/' + fname + '.txt', 'w')
    if run_growth['Annealing']:
        file.write("Parameters used for Annealing\n")
        file.write("T_Anneal: {:.0f} deg C \n".format(T_Anneal_Manip))
        file.write("Time for annealing: {:.1f}s\n\n".format(t_anneal))

    if run_growth['GaAs_Membrane_Growth']:
        file.write("Parameters used for GaAs membrane growth\n")
        file.write("T manipulator during GaAs: {:.0f} Torr\n".format(T_GaAs_Manip))
        file.write("rate_ga_for gaas: {:.1f} Torr\n".format(rate_ga))
        file.write("T_Ga during GaAs membrane growth: {:.0f} deg C\n".format(T_Ga))
        file.write("p_as_gaas: {:.2e} Torr\n".format(p_as_gaas))
        file.write("as_valve_gaas: {:.2f}%\n".format(as_valve_gaas))
        file.write("t_growth_gaas: {:.1f}s\n\n".format(t_growth_gaas))

    if run_growth['InAs_NW_Growth']:
        file.write("Parameters used for InAs NW growth\n")
        file.write("T manipulator during InAs: {:.0f} Torr\n".format(T_InAs_Manip))
        file.write("rate_in_for inas: {:.1f} Torr\n".format(rate_in))
        file.write("T_In during InAs membrane growth:{:.0f} deg C\n".format(T_In))
        file.write("p_as_inas: {:.2e} Torr\n".format(p_as_inas))
        file.write("as_valve_inas: {:.2f}%\n".format(as_valve_inas))
        file.write("t_growth_inas: {:.1f}s \n\n".format(t_growth_inas))

    if run_growth['GaAs_passivation_layer']:
        file.write("Parameters used for GaAs passivation layer growth\n")
        file.write("T manipulator during GaAs shell growth: {:.0f} deg C\n".format(T_GaAs_Shell_Manip))
        file.write("T_Ga during GaAs passivation layer: {:.0f} Torr\n".format(T_Ga_Shell))
        file.write("p_as_gaas: {:.2e} Torr\n".format(p_as_shell))
        file.write("as_valve_gaas: {:.2f}%\n".format(as_valve_shell))
        file.write("t_growth_gaas: {:.1f}s\n".format(t_growth_shell))
        file.write("thickness_gaas_shell: {:.0f}s\n\n".format(thickness_shell))

    file.write("BFM files used are:\n")
    file.write(calib_In.filename + "\n")
    file.write(calib_Ga.filename + "\n")
    file.write(calib_As.filename + "\n\n")

    file.write("RHEED files used are:\n")
    file.write(calib_In.rheed_filename.split('/')[-1] + "\n")
    file.write(calib_Ga.rheed_filename.split('/')[-1] + "\n")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
