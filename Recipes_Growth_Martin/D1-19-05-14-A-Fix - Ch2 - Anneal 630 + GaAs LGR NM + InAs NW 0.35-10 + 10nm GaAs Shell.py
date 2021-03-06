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
# D1-19-05-10-D: Added 2nm shell after InAs growth

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
    calib_Ga = Calibration("Ga", rheed_filename="2017-06-30_Ga.txt")
    calib_As = Calibration("As")

    with MBERecipe(virtual_server=run_virtual_server) as mbe:
        # Prompt user if they are sure
        mbe.starting_growth_prompt()

        # Increment number of recipes flag and set recipes running to true
        ts_print("Setting variables")

        # Define growth parameters
        # T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_Ga = 870  # Ga temp
        ##################### TEMPORARY OVERRIDE BECAUSE OUR LAST RHEED ONLY HAD 2 POINTS
        T_In = calib_In.calc_setpoint_gr(rate_in)  # In temp
        T_Anneal_Manip = 770  # Desired manip temperature (pyro is broken)
        T_GaAs_Manip = 770  # Desired manip temperature (pyro is broken)
        T_InAs_Manip = 660  # Desired manip temperature for InAs growth
        T_GaAs_Shell_Manip = 660  # Desired manip temperature for GaAs shell growth
        p_as_gaas = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas)  # Desired As pressure for GaAs growth
        as_valve_gaas = calib_As.calc_setpoint(p_as_gaas)
        p_as_inas = calib_In.calc_p_arsenic(rate_in, ftr_inas)  # Desired As pressure for InAs growth
        as_valve_inas = calib_As.calc_setpoint(p_as_inas)
        p_as_gaas_shell = calib_Ga.calc_p_arsenic(rate_ga, ftr_gaas_shell)  # Desired As pressure for GaAs shell growth
        as_valve_gaas_shell = calib_As.calc_setpoint(p_as_gaas_shell)
        t_anneal = 10 * 60  # 10 minutes
        thickness_gaas = 100  # nm
        t_growth_gaas = thickness_gaas * 10 / rate_ga  # Always grow the same thickness of material
        thickness_inas = 63  # nm
        t_growth_inas = thickness_inas * 10 / rate_in  # Always grow the same thickness of material
        thickness_gaas_shell = 10  # nm
        t_growth_gaas_shell = thickness_gaas_shell * 10 / rate_ga


        ##############################################################################
        # InAs Nanowire
        ##############################################################################

        mbe.waiting(1200)  # Wait Growth Time
        ts_print("Closing In shutter")
        mbe.shutter("In", False)

        ##############################################################################
        # GaAs Passivation Layer
        ##############################################################################
        # Go to GaAs shell growth temp
        ts_print("Going to GaAs shell growth conditions, setting manip to {}".format(T_GaAs_Shell_Manip))
        mbe.set_param("Manip.PV.Rate", 30)

        mbe.set_param("Manip.PV.TSP", T_GaAs_Shell_Manip)
        mbe.wait_to_reach_temp(T_GaAs_Shell_Manip, error=1)

        # Set As flux
        mbe.set_param("AsCracker.Valve.OP", as_valve_gaas_shell)
        mbe.waiting(30)  # Wait for cracker valve to open

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas_shell)  # Wait Growth Time
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

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
