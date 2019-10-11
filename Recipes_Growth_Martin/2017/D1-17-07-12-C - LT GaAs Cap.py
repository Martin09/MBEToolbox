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

        ts_print("Setting variables")
        # Define growth parameters
        T_Ga = calib_Ga.calc_setpoint_gr(1.0)  # 1.0 A/s growth rate
        T_In = calib_In.calc_setpoint_gr(0.2)  # 0.2 A/s growth rate
        # T_Des_Anneal = 600  # Desired pyrometer temperature for anneal
        # T_Des_GaAs = 630  # Desired pyrometer temperature for GaAs growth
        # T_Des_InAs = 535  # Desired pyrometer temperature for InAs growth
        T_Des_LTGaAs_Manip = 400  # Desired manip temperature for low temperature GaAs growth
        p_as_ltgaas = 8E-6  # Desired As pressure for LT GaAs
        as_valve_ltgaas = calib_As.calc_setpoint(p_as_ltgaas)
        t_anneal = 10 * 60  # 10 minutes
        t_growth_inas = 200  # 200 seconds (4nm)

        # Shell growth rate = 1.0 A/s / 2 = 0.5 A/s (geometric effects)
        # 20nm / 0.5A/s = 400s total growth time
        # 400s - 20s = 380s total GaAs growth time (20s InGaAs growth)
        # 380s / 2 = 190s
        t_growth_ltgaas_half = 190  # 190 sec
        t_growth_ingaas_marker = 10  # 10 sec

        # Check that MBE parameters are in standby mode
        ts_print("Checking standby conditions")
        if not (mbe.check_stdby()):
            raise Exception('MBE standby conditions not met, growth aborted!')

        # Start substrate rotation
        ts_print("Starting substrate rotation")
        mbe.set_param("Manip.RS.RPM", 7)

        ts_print("Ramping to growth temperature")
        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        # mbe.set_param("Manip.PV.TSP", T_Des_Anneal + mbe.manip_offset)  # Anneal temperature
        mbe.set_param("Manip.PV.TSP", T_Des_LTGaAs_Manip)  # Anneal temperature
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
        # mbe.wait_to_reach_temp(T_Des_LTGaAs_Manip + mbe.manip_offset, error=1)
        mbe.wait_to_reach_temp(T_Des_LTGaAs_Manip)
        mbe.timer_start()
        # mbe.converge_to_temp(T_Des_LTGaAs_Manip)  # Takes about 4min
        mbe.timer_wait(t_anneal)

        ##############################################################################
        # Low Temp GaAs Cap
        ##############################################################################

        # Set As flux, let it open during temperature convergence
        mbe.set_param("AsCracker.Valve.OP", as_valve_ltgaas)

        # Go to low temperature GaAs growth temp
        # ts_print("Going to InAs growth conditions, setting manip to {}".format(T_Des_InAs + mbe.manip_offset))
        ts_print("Going to low temp GaAs growth conditions, setting manip to {}".format(T_Des_LTGaAs_Manip))
        mbe.set_param("Manip.PV.Rate", 50)
        # mbe.set_param("Manip.PV.TSP", T_Des_InAs + mbe.manip_offset)
        # mbe.wait_to_reach_temp(T_Des_InAs + mbe.manip_offset, error=1)
        mbe.set_param("Manip.PV.TSP", T_Des_LTGaAs_Manip)
        mbe.wait_to_reach_temp(T_Des_LTGaAs_Manip)
        mbe.wait_to_reach_temp(T_In, 'In')
        mbe.wait_to_reach_temp(T_Ga, 'Ga')

        mbe.waiting(5 * 60)  # Wait five minutes to stabilize temperature and pressure

        ts_print("Checking pressure")
        if float(mbe.get_param("MBE.P")) < 1e-8:  # Make sure As valve opened properly
            mbe.set_param("Manip.PV.TSP", 200)
            mbe.set_param("Manip.PV.Rate", 100)
            raise Exception(
                "Pressure still below 1e-8 after opening As. Something is wrong, check As valve, shutter and tank temperature!")
        ts_print("Pressure looks good.")

        # Grow first half of LT shell
        mbe.shutter("Ga", True)
        mbe.waiting(t_growth_ltgaas_half)

        # Grow the InGaAs insertion half way through the shell
        mbe.shutter("In", True)
        mbe.waiting(t_growth_ingaas_marker)
        mbe.shutter("In", False)

        # Grow second half of LT shell
        mbe.waiting(t_growth_ltgaas_half)
        mbe.shutter("Ga", False)

        ##############################################################################
        # Cool Down Cells
        ##############################################################################
        ts_print("Ramping down Manipulator")
        mbe.set_param("Ga.PV.TSP", 550)
        mbe.set_param("In.PV.TSP", 515)
        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.PV.TSP", 200)
        mbe.wait_to_reach_temp(200, error=3)
        ts_print("Temperature reached 200, closing As valve and shutter")
        mbe.shutter("As", False)
        mbe.set_param("AsCracker.Valve.OP", 0)

        # Cap the sample with arsenic
        # mbe.as_capping(capping_time=30)  # Before unloading sample, heat it to 100 degrees for ~5min

        ts_print("Stopping substrate rotation")
        mbe.set_param("Manip.RS.RPM", 0)

        mbe.set_stdby()  # Set cells to standby conditions just in case we forgot something in the code
        mbe.waiting(60 * 10)

    ts_print("Recipe Done.")

    if mbe.virtual_server:
        ts_print("Plotting the log file")
        mbe.plot_log(filename=__file__.split('/')[-1].split(' ')[0])
