"""
Example of a growth recipe for nanomembranes with InAs nanowires on top.
Requires the new MBE_Toolbox
"""
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

run_virtual_server = False
use_pyro = False

# AlAs/GaAs superlattice growth on top of a doped 100 substrate for isolation of surface impurities and back gating.
###########################
rate_ga = 0.5  # A/s
rate_al = 0.5  # A/s
ftr = 150  # five three ratio
n_superlattice = 10  # Superlattice repetitions
###########################

# If running the script locally:
if __name__ == '__main__':
    calib_Ga = Calibration("Ga")
    calib_As = Calibration("As")
    calib_Al = Calibration("Al")

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
        T_Ga = calib_Ga.calc_setpoint_gr(rate_ga)  # Ga temp
        T_Al = calib_Al.calc_setpoint_gr(rate_al)  # Ga temp
        T_Anneal_Manip = 750  # Desired manip temperature (pyro is broken)
        T_Growth_Manip = 700  # Desired manip temperature (pyro is broken)
        p_as = calib_Ga.calc_p_arsenic(rate_ga, ftr)  # Desired As pressure for GaAs growth
        as_valve = calib_As.calc_setpoint(p_as)
        t_anneal = 10 * 60  # 10 minutes
        thickness_gaas1 = 20  # nm
        t_growth_gaas1 = thickness_gaas1 * 10 / rate_ga  # Always grow the same thickness of material
        thickness_sl_gaas = 2  # nm
        t_growth_sl_gaas = thickness_sl_gaas * 10 / rate_ga  # Always grow the same thickness of material
        thickness_sl_alas = 2  # nm
        t_growth_sl_alas = thickness_sl_alas * 10 / rate_al  # Always grow the same thickness of material
        thickness_alas = 10  # nm
        t_growth_alas = thickness_alas * 10 / rate_al  # Always grow the same thickness of material
        thickness_gaas2 = 30  # nm
        t_growth_gaas2 = thickness_gaas2 * 10 / rate_ga  # Always grow the same thickness of material

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", -7)

        # Check pressure before ramping up anything, make sure As valve is working
        ts_print("Opening arsenic cracker valve and shutter")
        mbe.set_param("AsCracker.Valve.OP", as_valve)
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
        ts_print("Ramping up Ga and In sources")
        mbe.set_param("Ga.PV.Rate", 40)
        mbe.set_param("Ga.OP.Rate", 0)
        mbe.set_param("Ga.PV.TSP", T_Ga)
        mbe.set_param("Al.PV.Rate", 20)
        mbe.set_param("Al.OP.Rate", 0)
        mbe.set_param("Al.PV.TSP", T_Al)

        ##############################################################################
        # Anneal sample
        ##############################################################################
        mbe.wait_to_reach_temp(T_Anneal_Manip)
        mbe.waiting(t_anneal)

        #############################################################################
        # GaAs Buffer Layer 1
        #############################################################################
        # Go to growth conditions
        ts_print("Going to GaAs growth conditions, setting manip to {}".format(T_Growth_Manip))
        mbe.set_param("Manip.PV.Rate", 30)
        mbe.set_param("Manip.PV.TSP", T_Growth_Manip)
        # Wait until growth temperature is reached
        mbe.wait_to_reach_temp(T_Growth_Manip)

        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas1)  # Wait Growth Time
        mbe.shutter("Ga", False)

        mbe.waiting(10)  # Pause 10 seconds

        #############################################################################
        # AlAs Superlattice
        #############################################################################

        for i in range(1, n_superlattice):
            mbe.shutter("Al", True)
            mbe.waiting(t_growth_sl_alas)  # Wait Growth Time
            mbe.shutter("Al", False)
            mbe.waiting(1)  # Pause 1 second
            mbe.shutter("Ga", True)
            mbe.waiting(t_growth_sl_gaas)  # Wait Growth Time
            mbe.shutter("Ga", False)

        mbe.waiting(10)  # Pause 10 seconds

        #############################################################################
        # AlAs Buffer Layer
        #############################################################################
        # Open Al shutter and start growth
        ts_print("Opening Al shutter and waiting growth time")
        mbe.shutter("Al", True)
        mbe.waiting(t_growth_alas)  # Wait Growth Time
        mbe.shutter("Al", False)

        mbe.waiting(10)  # Pause 10 seconds

        #############################################################################
        # GaAs Buffer Layer 2
        #############################################################################
        # Open Ga shutter and start growth
        ts_print("Opening Ga shutter and waiting growth time")
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_gaas2)  # Wait Growth Time
        mbe.shutter("Ga", False)

        mbe.waiting(10)  # Pause 10 seconds

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("Al.PV.TSP", 750)
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