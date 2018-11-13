import sys, os

sys.path.insert(1, os.path.join(sys.path[0], '..'))  # Add parent directory to path

from recipe_helper import MBERecipe, ts_print
from datetime import datetime, timedelta
from time import sleep
import numpy as np

"""
This script is meant to protect the As and Sb valves during emergency cool-down events such as power/cooling water cuts.
The As/Sb valves always need to be open when changing the cracker temperature to avoid damaging them. Currently nothing
ensures that they open during an emergency cool-down. This script monitors the cracker temps and opens the valves to 30%
in case it detects a significant change in temperature of the cracker.
"""

cracker_tolerance = 20  # [degrees] Allow crackers temps to fluctuate +/- this amount without intervention


def cool_down(mbe, cell):
    if cell.lower() not in ["as", "sb"]:
        raise ValueError("Need to specify either 'As' or 'Sb' to cool down")

    cn = "As" if cell.lower() == "as" else "Sb"  # Cell Name

    ts_print("Opening the " + cn + " valve to 30%. Cooling it down...")

    T_stdby_tank = 50
    T_stdby_cond = 50
    T_stdby_cracker = 50

    mbe.set_param(cn + "Cracker.Valve.OP", 33)  # Open cracker valve

    mbe.set_param(cn + ".Mode", "Auto")
    mbe.set_param(cn + ".PV.Rate", 5)
    mbe.set_param(cn + ".OP.Rate", 0)
    mbe.set_param(cn + ".PV.TSP", T_stdby_tank)

    mbe.set_param(cn + "Cracker.Mode", "Auto")
    mbe.set_param(cn + "Cracker.PV.Rate", 20)
    mbe.set_param(cn + "Cracker.OP.Rate", 0)
    mbe.set_param(cn + "Cracker.PV.TSP", T_stdby_cracker)

    if cn == "Sb":
        mbe.set_param("SbCond.Mode", "Auto")
        mbe.set_param("SbCond.PV.Rate", 20)
        mbe.set_param("SbCond.OP.Rate", 0)
        mbe.set_param("SbCond.PV.TSP", T_stdby_cond)


if __name__ == "__main__":

    with MBERecipe(virtual_server=False, stdby_at_exit=False)as mbe:

        ref_temp_AsCracker = float(mbe.get_param("AsCracker.PV"))
        ref_temp_SbCracker = float(mbe.get_param("SbCracker.PV"))

        ref_time_As = datetime.now()
        ref_time_Sb = datetime.now()

        while True:

            # Pull latest data about the As/Sb cells
            temp_AsCracker = float(mbe.get_param("AsCracker.PV"))
            valve_As = float(mbe.get_param("AsCracker.Valve"))
            temp_SbCracker = float(mbe.get_param("SbCracker.PV"))
            valve_Sb = float(mbe.get_param("SbCracker.Valve"))
            currTime = datetime.now()

            # Calc temp difference since last check
            temp_diff_As = ref_temp_AsCracker - temp_AsCracker
            temp_diff_Sb = ref_temp_SbCracker - temp_SbCracker

            # Calc time difference since last check
            time_diff_As = (currTime - ref_time_As).total_seconds()
            time_diff_Sb = (currTime - ref_time_Sb).total_seconds()

            if valve_As >= 30:  # Valve is safe
                ref_time_As = currTime
                ref_temp_AsCracker = temp_AsCracker
                valve_safe_As = True
                ts_print("As valve open, valve is safe.")
            else:  # Valve is potentially in danger
                if np.abs(temp_diff_As) < cracker_tolerance:  # Temperature is within tolerance, no problems
                    ref_time_As = currTime
                    ts_print("As valve closed, temp within specified limits (temp is {:.0f}C).".format(temp_AsCracker))
                else:  # Temperature is outside of tolerance, might need to intervene
                    ts_print("As valve closed, temp outside of limits (temp is {:.0f}C)!!!".format(
                        temp_AsCracker))  # Intervene only if less than 10min has passes since last check and if temperature diff is below 100
                    # if temp diff is above 100, its better not to move the Sb valve. Heat it up again and open it later
                    if temp_diff_As < 60 * 10 and np.abs(temp_diff_As) < 100:
                        cool_down(mbe, "As")
                        pass

            if valve_Sb >= 30:  # Valve is safe
                ref_time_Sb = currTime
                ref_temp_SbCracker = temp_SbCracker
                valve_safe_Sb = True
                ts_print("Sb valve open, valve is safe.")
            else:  # Valve is potentially in danger
                if np.abs(temp_diff_Sb) < cracker_tolerance:  # Temperature is within tolerance, no problems
                    ref_time_Sb = currTime
                    ts_print("Sb valve closed, temp within specified limits (temp is {:.0f}C).".format(temp_SbCracker))
                else:  # Temperature is outside of tolerance, might need to intervene
                    ts_print("Sb valve closed, temp outside of limits (temp is {:.0f}C)!!!".format(temp_SbCracker))
                    # Intervene only if less than 10min has passes since last check and if temperature diff is below 100
                    # if temp diff is above 100, its better not to move the Sb valve. Heat it up again and open it later
                    if temp_diff_Sb < 60 * 10 and np.abs(temp_diff_Sb) < 100:
                        cool_down(mbe, "Sb")
                        pass

            ts_print("Sleeping for 10s...")
            sleep(10)
