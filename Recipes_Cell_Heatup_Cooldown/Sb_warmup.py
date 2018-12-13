from recipe_helper import MBERecipe, ts_print
from time import sleep
from mbe_calibration import Calibration

"""
"Always heat the cracking zone and conductance zone first and cool them last
to prevent condensation in the conductance tube. The bulk evaporator
should always be heated last."

"Any time the cracking zone or the conductance
zone temperature is adjusted, the valve must be partially open.
The crucible is made of PBN and the drive mechanism for the
valve is made of tantalum and molybdenum. These materials
have different rates of the thermal expansion, which could cause
jamming or breakage of the needle or crucible."
"""
if __name__ == '__main__':
    with MBERecipe(virtual_server=False, stdby_at_exit=False) as mbe:
        T_sb_tank = 380
        T_sb_cond = 750
        T_sb_cracker = 800

        sb_cond_init_temp = int(float(mbe.get_param("SbCond.PV")))
        sb_cracker_init_temp = int(float(mbe.get_param("SbCracker.PV")))

        sb_cond_temps = range(sb_cond_init_temp, T_sb_cond, 20)
        sb_cond_temps.append(T_sb_cond)
        sb_cracker_temps = range(sb_cracker_init_temp, T_sb_cracker, 20)
        sb_cracker_temps.append(T_sb_cracker)

        mbe.set_param("SbCracker.Valve.OP", 33)  # Open antimony valve
        # mbe.set_param("SbCracker.Valve.OP", 100)  # Open antimony valve

        mbe.set_param("SbCond.Mode", "Auto")
        mbe.set_param("SbCond.PV.Rate", 10)
        mbe.set_param("SbCond.OP.Rate", 0)

        mbe.set_param("SbCracker.Mode", "Auto")
        mbe.set_param("SbCracker.PV.Rate", 10)
        mbe.set_param("SbCracker.OP.Rate", 0)

        for i in range(max([len(sb_cond_temps), len(sb_cracker_temps)])):

            while float(mbe.get_param("MBE.P")) > 1E-7:
                sleep(1)

            if not i > len(sb_cond_temps) - 1:
                mbe.set_param("SbCond.PV.TSP", sb_cond_temps[i])
            if not i > len(sb_cracker_temps) - 1:
                mbe.set_param("SbCracker.PV.TSP", sb_cracker_temps[i])

            mbe.wait_to_reach_temp(PID='SbCond')
            mbe.wait_to_reach_temp(PID='SbCracker')

        mbe.set_param("SbCracker.Valve.OP", 0)  # Close antimony valve

        mbe.set_param("Sb.Mode", "Auto")
        mbe.set_param("Sb.PV.Rate", 5)
        mbe.set_param("Sb.OP.Rate", 0)
        mbe.set_param("Sb.PV.TSP", T_sb_tank)

        mbe.wait_to_reach_temp(T_sb_tank, PID='Sb')


