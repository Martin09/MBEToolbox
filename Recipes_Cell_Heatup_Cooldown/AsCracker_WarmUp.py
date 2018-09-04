from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

T_as_cracker_final = 950
T_as_cracker_degas = 1200
t_degas = 60*60*1 # degas for 1 hour

if __name__ == '__main__':
    with MBERecipe(virtual_server=True) as mbe:

        mbe.set_param("AsCracker.Mode", "Auto")
        mbe.set_param("AsCracker.PV.Rate", 10)
        mbe.set_param("AsCracker.OP.Rate", 0)

        mbe.set_param("AsCracker.Valve.OP", 30)
        mbe.set_param("AsCracker.PV.TSP", T_as_cracker_degas)
        mbe.wait_to_reach_temp(T_as_cracker_degas, PID='AsCracker')
        mbe.set_param("AsCracker.Valve.OP", 0)

        mbe.waiting(t_degas)

        mbe.set_param("AsCracker.Valve.OP", 30)
        mbe.set_param("AsCracker.PV.TSP", T_as_cracker_final)
        mbe.wait_to_reach_temp(T_as_cracker_final, PID='AsCracker')
        mbe.set_param("AsCracker.Valve.OP", 0)
