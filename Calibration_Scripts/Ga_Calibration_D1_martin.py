import atexit
from datetime import datetime
from time import strftime, sleep

import numpy as np
from MBE_Tools import ServerConnection

# Script takes about 3min per value, would like to keep the total calibration to around 30 min, so 10 values
# TODO: Andres recommends to go from higher temperature to lower temperatures during calibration, says its more stable...?


# Short calibration
# values = np.linspace(960, 900, 7)
# Long calibration
values = np.linspace(960, 900, 13)

t_stabilize = 6 * 60  # 6 minutes
t_shutter_stabilize = 1 * 60  # 1 minute

#################################
# Modify this for each material
#################################
mat = "Ga"
standby_value = 550
#################################

# filename=r"C:\Users\epfl\Calibrations\2013-04-08_As_Flux1.txt"
filename = r"\\MBESERVER\Documents\Calibrations_D1" + "\\" + strftime("%Y-%m-%d_%H-%M-%S_" + mat + ".txt")


@atexit.register  # Terminate script cleanly, even when interrupted early
def exit_cleanly():
    """
    Is called at the end of the script or if there is an interrupt. Cleans up the connection etc. to exit cleanly.
    :return: Nothing
    """

    #    if not recipeStarted:
    #        connection.close()
    #        return
    ts_print('Exiting cleanly...')
    # Close shutter
    connection.sendCommand("Close " + mat)
    # Decrement number of recipes flag
    connection.sendCommand("set this.recipesrunning dec")
    connection.close()


def ts_print(string):
    """
    Adds a timestamp to printed output
    :param string: string you want to print
    :return: nothing
    """
    # Print with a timestamp
    print("{}: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), string))


def waiting(time):
    """
    Waits the specified amount of time
    :param time: time to wait
    :return: nothing
    """
    ts_print("Waiting {}s".format(time))
    for i in xrange(int(round(time))):
        sleep(1.0)


def read_pressures(delay=1.2, n=50):
    """
    Reads the pressures of the BFM and MBE, returning the mean values from all n measurements of each
    :param delay: delay between successive measurements (in seconds)
    :param n: number of measurements to take (statistics)
    :return: returns the mean of both pressures in the format (BFM_pressure, MBE_pressure)
    """
    ps_bfm = []
    ps_mbe = []
    # Read the BFM and MBE pressures repeatedly
    for i in range(n):
        ps_bfm.append(float(connection.sendCommand("Get BFM.P")))
        ps_mbe.append(float(connection.sendCommand("Get MBE.P")))
        sleep(delay)
    # Perform statistics on the read values
    p_bfm = np.mean(ps_bfm)
    p_bfm_std = np.std(ps_bfm)

    p_mbe = np.mean(ps_mbe)
    p_mbe_std = np.std(ps_mbe)

    print('BFM={}+/-{}, MBE={}+/-{}'.format(p_bfm, p_bfm_std, p_mbe, p_mbe_std))

    return p_bfm, p_mbe


def ramp_to(setpoint, material, error=0.1):
    """
    Ramps the desired material to the setpoint
    :param setpoint: setpoint you want to reach
    :param material: material to ramp (ex: 'As', 'Ga', 'Manip')
    :param error: returns once the actual temperature reaches the setpoint +/- this error
    :return: returns true once it reaches the setpoint
    """
    if material == "As":
        connection.sendCommand("Set AsCracker.Valve.OP {:.0f}".format(setpoint))
    else:
        connection.sendCommand("Set " + material + ".PV.TSP {:.0f}".format(setpoint))

    while True:
        sleep(1)
        if material == "As":
            current = float(connection.getValue("AsCracker.Valve"))
        else:
            current = float(connection.getValue(material + ".PV"))
        if abs(current - setpoint) <= error:
            return True


# If running the script locally:
if __name__ == '__main__':

    grow = raw_input('Starting a recipe! Are you sure? (y/n):  ')
    if not (grow.lower() == 'y'):
        print('Exiting...')
        sleep(1)
        exit()
    else:
        print('Starting recipe!')

    connection = ServerConnection("10.18.7.24", "55001", "xxa")

    if not connection.sendCommand("get this.recipesrunning") == "0":
        raise Exception("At least one recipe is running!")

    connection.sendCommand("set this.recipesrunning inc")
    ts_print("Moving BFM in")
    connection.sendCommand("Set BFM.LT.IN")
    waiting(30)  # Wait 30 sec to move BFM in
    recipeStarted = True

    # Write the file headers    
    f = open(filename, "a")
    f.write("{:s}\tBFM.P\tMBE.P\n".format(mat))
    f.close()

    # Loop over all the values to calibrate
    for value in values:
        ts_print("Ramping to {}".format(value))
        ramp_to(value, mat)

        ts_print("Waiting to stabilize")
        waiting(t_stabilize)

        connection.sendCommand("Open " + mat)
        ts_print("Opened shutter")
        waiting(t_shutter_stabilize)

        pressure, background = read_pressures()
        f = open(filename, "a")
        f.write("{:.0f}\t{:.6E}\t{:.6E}\n".format(value, pressure, background))
        f.close()
        ts_print("Pressure: " + str(pressure) + " (stored to file)")

        connection.sendCommand("Close " + mat)
        ts_print("Closed shutter")

    # Go to standby conditions
    if mat == "As":
        connection.sendCommand("Set AsCracker.valve.OP %d" % standby_value)
    else:
        connection.sendCommand("Set " + mat + ".PV.TSP %d" % standby_value)

    # Remove the BFM and tidy up
    connection.sendCommand("Set BFM.LT.OUT")
    connection.sendCommand("set this.recipesrunning dec")
    connection.close()
    recipeStarted = False
    ts_print("Done")
