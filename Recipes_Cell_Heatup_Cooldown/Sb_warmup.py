from SbValveControl import SbValve
from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

if __name__ == '__main__':
    with MBERecipe(virtual_server=False) as mbe:
        T_Manip = 300  # Heat up manipulator a bit during warm-up
        T_sb_tank = 300
        T_sb_cond = 300
        T_sb_cracker = 300

        valve = SbValve(COM=2)
        valve.setPV(30)  # Crack open antimony valve to 30% opening (100 mil)

        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", T_Manip)  # Manip temperature

        mbe.set_param("Sb.Mode", "Auto")
        mbe.set_param("Sb.PV.Rate", 5)
        mbe.set_param("Sb.OP.Rate", 0)
        mbe.set_param("Sb.PV.TSP", T_sb_tank)

        mbe.set_param("SbCond.Mode", "Auto")
        mbe.set_param("SbCond.PV.Rate", 10)
        mbe.set_param("SbCond.OP.Rate", 0)
        mbe.set_param("SbCond.PV.TSP", T_sb_cond)

        mbe.set_param("SbCracker.Mode", "Auto")
        mbe.set_param("SbCracker.PV.Rate", 10)
        mbe.set_param("SbCracker.OP.Rate", 0)
        mbe.set_param("SbCracker.PV.TSP", T_sb_cracker)

        mbe.wait_to_reach_temp(T_sb_tank, PID='Sb')
        mbe.wait_to_reach_temp(T_sb_cond, PID='SbCond')
        mbe.wait_to_reach_temp(T_sb_cracker, PID='SbCracker')

        valve.setPV(0)  # Close antimony valve again after warm-up

        mbe.set_param("Manip.PV.Rate", 50)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", 200)  # Manip temperature
