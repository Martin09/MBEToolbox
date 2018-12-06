from recipe_helper import MBERecipe, ts_print
from mbe_calibration import Calibration

"""
Any time the valved cracker needs to be cooled to room temperature, follow
this procedure:
    1. Ramp the bulk evaporator to room temperature using a ramp rate of 5C/min.
    2. Wait until the bulk evaporator temperature has dropped 100C from the operating temperature
    3. Open the valve at least 100 mil.
    4. Ramp the cracking zone and conductance zone to room temperature using a ramp rate of 20C/min
    
"Any time the cracking zone or the conductance
zone temperature is adjusted, the valve must be partially open.
The crucible is made of PBN and the drive mechanism for the
valve is made of tantalum and molybdenum. These materials
have different rates of the thermal expansion, which could cause
jamming or breakage of the needle or crucible."
"""

if __name__ == '__main__':
    with MBERecipe(virtual_server=False) as mbe:
        T_stdby_sb_tank = 380
        T_stdby_sb_cond = 600
        T_stdby_sb_cracker = 700

        if not T_stdby_sb_cracker > T_stdby_sb_cond:
            ValueError("Cracker temp must always be greater than conductance temp!")

        T_curr_sb_tank = float(mbe.get_param("Sb.PV"))

        mbe.set_param("Sb.Mode", "Auto")
        mbe.set_param("Sb.PV.Rate", 5)
        mbe.set_param("Sb.OP.Rate", 0)
        mbe.set_param("Sb.PV.TSP", T_stdby_sb_tank)

        # Wait until tank temp has dropped by 100 degrees before opening Sb valve and cooling cracker
        if (T_curr_sb_tank - 100) < T_stdby_sb_tank:
            mbe.wait_to_reach_temp(T_stdby_sb_tank, PID='Sb')
        else:
            mbe.wait_to_reach_temp(T_curr_sb_tank - 100, PID='Sb')

        mbe.set_param("SbCracker.Valve.OP", 33)  # Open antimony valve

        mbe.set_param("SbCond.Mode", "Auto")
        mbe.set_param("SbCond.PV.Rate", 20)
        mbe.set_param("SbCond.OP.Rate", 0)

        mbe.set_param("SbCracker.Mode", "Auto")
        mbe.set_param("SbCracker.PV.Rate", 20)
        mbe.set_param("SbCracker.OP.Rate", 0)

        T_curr_sb_cracker = float(mbe.get_param("SbCracker.PV"))
        T_curr_sb_cond = float(mbe.get_param("SbCond.PV"))

        # Iterate and drop temperature in 50 degree increments to avoid cracker temp dropping faster than cond tube
        while True:
            if T_curr_sb_cond - T_stdby_sb_cond < 50:
                mbe.set_param("SbCond.PV.TSP", T_stdby_sb_cond)
            else:
                mbe.set_param("SbCond.PV.TSP", T_curr_sb_cond - 50)

            if T_curr_sb_cracker - T_stdby_sb_cracker < 50:
                mbe.set_param("SbCracker.PV.TSP", T_stdby_sb_cracker)
            else:
                mbe.set_param("SbCracker.PV.TSP", T_curr_sb_cracker - 50)

            mbe.wait_to_reach_temp(PID='SbCond')
            mbe.wait_to_reach_temp(PID='SbCracker')

            T_curr_sb_cracker = float(mbe.get_param("SbCracker.PV"))
            T_curr_sb_cond = float(mbe.get_param("SbCond.PV"))

            if T_curr_sb_cond==T_stdby_sb_cond and T_curr_sb_cracker==T_stdby_sb_cracker:
                break

        mbe.set_param("SbCracker.Valve.OP", 0)  # Close antimony valve
