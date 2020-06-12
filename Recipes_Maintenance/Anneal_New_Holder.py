from recipe_helper import MBERecipe, ts_print
from time import sleep
from mbe_calibration import Calibration

"""
Recipe used to anneal a new holder in the MBE chamber. 
Note: only anneal the holder in the growth chamber after a thorough anneal in the degassing chamber!
"""
if __name__ == '__main__':
    with MBERecipe(virtual_server=False, stdby_at_exit=False) as mbe:

        init_temp = 200
        final_temp = 900

        anneal_time = 60 * 60 * 2  # 2 hours annealing time

        temps = range(init_temp, final_temp, 20)
        temps.append(final_temp)

        mbe.set_param("Manip.PV.Rate", 20)
        mbe.set_param("Manip.OP.Rate", 0)

        for incr_temp in temps:

            while float(mbe.get_param("MBE.P")) > 5E-8:  # If pressure is too high, wait for it to go down a bit
                sleep(1)

            mbe.set_param("Manip.PV.TSP", incr_temp)  # Perform incremental temperature step
            mbe.wait_to_reach_temp(incr_temp)

        mbe.waiting(anneal_time)

        mbe.set_param("Manip.PV.Rate", 100)
        mbe.set_param("Manip.OP.Rate", 0)
        mbe.set_param("Manip.PV.TSP", 200)  # Initial temperature
        mbe.wait_to_reach_temp(200)

        mbe.set_stdby()
