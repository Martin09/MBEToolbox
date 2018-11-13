# -*- coding: utf-8 -*-
"""
Some functions that help in MBE growth
"""
# TODO: implement the Sb cell commands!
from datetime import datetime
from time import sleep, clock
import numpy as np

from MBE_Tools import ServerConnection
from Virtual_MBE.virtual_mbe_server_client import Connect

def ts_print(string):
    """
    DEPRECATED! USED THE MBERECIPE.self.ts_print FUNCTION!!!!!

    Print a certain string with a timestamp

    :param string: string you want to print
    :type string: str
    :return: None
    """
    print_string = "{}: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), string)

    # Print with a timestamp
    print(print_string)


class MBERecipe:
    """
    Helper class for MBE growths that takes care of communicating with the MBE server. It acts as the interface between
    a user's recipe and the MBE server.
    """

    def __init__(self, virtual_server=False, scriptname=None, stdby_at_exit=True):
        self.virtual_server = virtual_server
        if not self.virtual_server:
            self.conn = ServerConnection("10.18.7.24", "55001", "xxa")
        else:
            # make a debugging server connection
            self.conn = Connect('localhost', 9999)
            self.conn.send_command('#reset_virt_mbe')

        if scriptname:
            self.log_fn = scriptname[:-3] + '.log'
        else:
            self.log_fn = None

        self.recipeStarted = False
        # TODO: turn the manip_offset value into a function which depends on temp (and calibrate it for various holders)
        self.manip_offset = 110  # Used to be 110 before 01/05/2017, before arm crash?
        self.timer_start_time = 0
        self.stdby_at_exit = stdby_at_exit

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Makes sure that the connection is closed and number of recipes is decremented upon exiting the script

        :return: None
        """
        if self.recipeStarted:
            self.ts_print('Exiting cleanly...')
            if self.stdby_at_exit:
                self.set_stdby()
            self.decrement_recipes_running()  # Decrement number of recipes flag
            self.conn.close()  # Close MBE server connection

    def ts_print(self, string):
        """
        Print a certain string with a timestamp to console AND log file

        :param string: string you want to print
        :type string: str
        :return: None
        """
        print_string = "{}: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), string)

        # Print with a timestamp
        print(print_string)

        # Output it to the file if it exists
        if self.log_fn:
            with open(self.log_fn, 'a') as out_file:
                out_file.write(print_string + "\n")

    def start_recipe(self):
        """
        Run just before starting a recipe. Increments number of running recipes and sets recipe running flag to true.

        :return: None
        """
        self.recipeStarted = True
        self.increment_recipes_running()

    def get_param(self, parameter):
        """
        Returns the value of a parameter from the MBE server.

        :param parameter: ID of the parameter that you want to know (ex: 'MBE.P', 'Shutter.Al', or 'Ga.PV')
        :type parameter: string
        :return: value of the parameter, as a string
        :rtype: str
        """

        return self.conn.send_command("Get {}".format(parameter))

    def set_param(self, parameter, value, delay=0.1):
        """
        Set a parameter in the MBE, read it back to verify that its state has been set properly

        :param parameter: what parameter you want to set
        :type parameter: str
        :param value: what value should it get
        :type value: bool, str, int, float
        :param delay: time to wait before trying to read the parameter (to check if it was set properly)
        :type value: int, float
        :return: None, returns once the parameter has been set properly
        """
        MAX_TEMPS = {'manip.pv.tsp': 850,
                     'in.pv.tsp': 830,
                     'ga.pv.tsp': 1020,
                     'al.pv.tsp': 1120}
        if parameter.lower() in MAX_TEMPS.keys():
            if float(value) > MAX_TEMPS[parameter.lower()]:
                self.ts_print('Tried setting {} to {}, but maximum is {}. Set to max.'.format(parameter, value,
                                                                                              MAX_TEMPS[
                                                                                                  parameter.lower()]))
                value = MAX_TEMPS[parameter.lower()]

        MAX_TRIES = 10
        tries = 1
        while True:
            self.conn.send_command("Set {} {}".format(parameter, value))

            sleep(delay)
            if parameter.lower() == 'manip.rs.rpm':
                srv_reply = self.conn.send_command("Get Manip.RS")
            elif parameter.lower() == 'ascracker.valve.op':
                sleep(1)  # Give time for As valve to open respond
                srv_reply = self.conn.send_command('Get AsCracker.Valve')
            elif parameter.lower() == 'sbcracker.valve.op':
                sleep(1)  # Give time for Sb valve to respond
                srv_reply = self.conn.send_command('Get SbCracker.Valve')
            else:
                srv_reply = self.conn.send_command("Get {}".format(parameter))

            if isinstance(value, bool):
                set_properly = srv_reply.lower() == str(value).lower()  # Convert bool to string and do the comparison
            elif isinstance(value, str):
                set_properly = value.lower() == srv_reply.lower()  # Do direct string comparison
                if (value.lower() == 'auto') and (
                        srv_reply.lower() == 'pid'):  # Quick and dirty fix for problem when running virtual MBE server host
                    set_properly = True  # TODO: fix this hack properly on the side of the MBE server
            elif isinstance(value, int) or isinstance(value, float):
                set_properly = abs(float(value) - float(srv_reply)) <= 0.1  # Convert to float and do comparison
            else:
                raise Exception("Unknown parameter type {}".format(type(value)))

            if set_properly:
                return
            elif not set_properly and tries >= MAX_TRIES:
                raise Exception("Error! Could not set {} to {}, got {}".format(parameter, value, srv_reply))
            else:
                sleep(1)  # Pause 1 second
                tries += 1

    def shutter(self, shutter_names, openbools):
        """
        Open or close specific shutters in the MBE, double checks the shutter state after sending the value

        :param shutter_names: list of names of shutters to be manipulated
        :type shutter_names: str, list of str
        :param openbools: list of boolean values of shutter states (true = open, false = closed)
        :type openbools: bool, list of bool
        :return: return once shutters have been set
        """
        if not type(shutter_names) == list:
            shutter_names = [shutter_names]
        if not type(openbools) == list:
            openbools = [openbools]

        if not len(shutter_names) == len(openbools):
            raise Exception("Error, expected lists with the same length!")

        for shutter_name, openbool in zip(shutter_names, openbools):
            # Add check to make sure shutter is one of the valid shutters
            if openbool:
                value = "Open"
            elif not openbool:
                value = "Close"
            else:
                raise Exception("Error! Shutter boolean undefined!")
            self.conn.send_command("{} {}".format(value, shutter_name))
            sleep(0.1)
            srv_reply = self.conn.send_command("Get Shutter.{}".format(shutter_name))

            if value.lower() == 'close':
                value = 'closed'
            if not srv_reply.lower() == value.lower():
                raise Exception("Error! Could not {} shutter {}".format(value, shutter_name))

    def timer_start(self):
        """
        Starts the clock-based timer. Later use timer_wait to wait rest of amount of time since start_timer was called.

        :return: None
        """
        self.ts_print("Starting timer.")
        if self.virtual_server:
            self.timer_start_time = float(self.conn.send_command('Get time'))
        else:
            self.timer_start_time = clock()

    def timer_wait(self, seconds):
        """
        Waits a specified amount of time since start_timer was called. Therefore if start_timer is called at t=0 and
        then a beam flux calibration is performed until t=60+/-10. If we then call sleep(40), it will finish at t~100.
        But if we instead call timer_wait(100) it will finish exactly at t=100, independent of how long the beam flux
        calibration took.

        :param seconds: Number of seconds to wait.
        :return: Returns None once the timer is up.
        """

        if self.virtual_server:
            now = float(self.conn.send_command('Get time'))
        else:
            now = clock()

        self.ts_print(
            "Waiting {} seconds, of which {:.2f}s already elapsed.".format(seconds, now - self.timer_start_time))

        if self.virtual_server:
            self.conn.send_command('Wait {}'.format(now - (self.timer_start_time + seconds)))
        else:
            while clock() < (self.timer_start_time + seconds):
                sleep(1)
        self.ts_print("Timer is up!")
        return

    def as_capping(self, capping_time=30, t_capping=10, post_anneal=True):
        """
        Performs an arsenic capping step on the samples (usually done after growth)

        :type post_anneal: bool
        :param post_anneal: If true, heats sample to 100 after the As capping to remove excess arsenic (for safety)
        :param t_capping: temperature of arsenic capping
        :param capping_time: the duration of the As capping step (in minutes)
        :type capping_time: float, int
        :return: None, return after capping is done
        """
        capping_time_sec = 60 * capping_time

        # Wait for temperature to drop
        self.ts_print("Setting manip temperature to {} and waiting...".format(t_capping))
        self.set_param("Manip.PV.TSP", t_capping)
        self.wait_to_reach_temp(t_capping, error=2, timeout_on=False)

        # Begin the As capping
        self.ts_print("Temperature reached, opening As valve and shutter")
        self.set_param("AsCracker.Valve.OP", 100)
        self.shutter("As", True)
        self.ts_print("Waiting capping time: {:.2f} min".format(capping_time))
        self.waiting(capping_time_sec)
        self.ts_print("Closing As valve and shutter")
        self.shutter("As", False)
        self.set_param("AsCracker.Valve.OP", 0)
        self.set_param("Manip.RS.RPM", 0)

        if post_anneal:
            # Wait one hour to pump out, before heating up to 100C for short period
            self.waiting(60 * 60)  # 1 hour wait
            self.set_param("Manip.PV.Rate", 10)
            self.set_param("Manip.PV.TSP", 100)
            self.wait_to_reach_temp(100, error=2)
            self.waiting(60 * 5)  # 5 min anneal
            self.set_param("Manip.PV.Rate", 0)
            self.set_param("Manip.PV.TSP", 20)

    def take_pyro_reading(self, datapts=40):
        """
        Measures and averages multiple pyrometer readings, returning the average and error

        :param datapts: Number of datapoints to measure (spaced 1.5s apart)
        :type datapts: int
        :return: Average pyrometer temperature, variance of pyrometer temperature
        """
        self.shutter("Pyrometer", True)
        pyrotemps = []
        if self.virtual_server:
            pyrotemps.append(self.conn.send_command("Get Pyrometer.T"))  # Get pyrotemp from virtual server once
            self.waiting(datapts * 1.5)  # Wait the same amount of time it would take to do the real measurement
        else:
            for i in range(datapts):
                sleep(1.5)
                pyrotemps.append(self.conn.send_command("Get Pyrometer.T"))

        self.shutter("Pyrometer", False)

        pyrotemps = np.array(pyrotemps).astype(np.float)
        avg_pyro_temp = pyrotemps.mean()
        avg_pryo_temp_err = pyrotemps.var()
        return avg_pyro_temp, avg_pryo_temp_err

    def get_manip_offset(self, datapts=40):
        """
        Takes a pyromater measurement, compares it to manipulator temperature to get offset between the two

        :param datapts: number of pyrometer measurements to take
        :type datapts: int
        :return: manipulator to pyrometer offset
        :rtype: float
        """
        self.ts_print("Taking pyrometer reading")
        pyrotemp, pyroerr = self.take_pyro_reading(datapts)
        self.ts_print('Pyrotemp reads {}'.format(pyrotemp))
        self.manip_offset = float(self.conn.send_command("Get Manip.PV")) - pyrotemp
        return self.manip_offset

    def converge_to_temp(self, desired_temp, iterations=2, datapoints=30):
        """
        Converges with the pyrometer to a specific desired temperature

        :param desired_temp: Pyrometer temperature that you want to set your sample to
        :type desired_temp: float
        :param iterations: Number of iterations performed for temperature convergence
        :type iterations: int
        :param datapoints: Number of datapoints to take with the pyrometer at each iteration
        :type datapoints: int
        :return: None, returns once it has converged to the desired temperature
        """
        # TODO: Accelerate this somehow when debugging
        self.ts_print("Converging with pyrometer to {}".format(desired_temp))
        for i in range(iterations):
            self.manip_offset = self.get_manip_offset(datapts=datapoints)
            new_manip_temp = desired_temp + self.manip_offset
            self.ts_print("Manip temp modified to {}".format(new_manip_temp))
            self.set_param("Manip.PV.TSP", new_manip_temp)
            self.waiting(60)

    def read_pressures(self, delay=1, n=20, error=0.02, max_t=60):
        """
        Reads the pressures of the BFM and MBE, returning the mean values from all n measurements of each
        :param max_t: maximum acquisition time before returning (in seconds)
        :param error: percent error of reading desired as exit criteria
        :param delay: delay between successive measurements (in seconds)
        :param n: number of measurements to take (statistics)
        :return: returns the mean of both pressures in the format (BFM_pressure, MBE_pressure)
        """

        start_time = clock()

        ps_bfm = []
        ps_mbe = []
        # Read the BFM and MBE pressures repeatedly until have n data points and the error is small enough
        while True:
            ps_bfm.append(float(self.get_param("BFM.P")))
            ps_mbe.append(float(self.get_param("MBE.P")))

            # If have acquired more datapoints than required, remove oldest point
            if len(ps_bfm) > n:
                ps_bfm = ps_bfm[1:]
                ps_mbe = ps_mbe[1:]

            # If have full dataset (n), perform statistics + see if we have enough precision to exit the loop
            if len(ps_bfm) == n:
                p_bfm = np.mean(ps_bfm)
                p_bfm_std = np.std(ps_bfm)
                # Precision achieved
                if (p_bfm_std / p_bfm) < error:
                    self.ts_print('Precision reached! Error = +/-{:.2f}%'.format(p_bfm_std / p_bfm * 100))
                    break
                # Timeout condition
                if clock() > (start_time + max_t):
                    self.ts_print('Timeout reached! Error = +/-{:.2f}%'.format(p_bfm_std / p_bfm * 100))
                    break

            sleep(delay)

        p_mbe = np.mean(ps_mbe)
        p_mbe_std = np.std(ps_mbe)

        self.ts_print('BFM={}+/-{}, MBE={}+/-{}'.format(p_bfm, p_bfm_std, p_mbe, p_mbe_std))

        return p_bfm, p_mbe, p_bfm_std, p_mbe_std

    def bfm(self, insert=False):
        """
        Manipulate the beam flux monitor (BFM). Either insert or retract it fully.
        :return: Returns once operation is finished
        """
        if insert:
            if float(self.conn.send_command("Get BFM.LT")) >= 122:
                return
            self.ts_print("Moving BFM in")
            self.conn.send_command("Set BFM.LT.IN")
        else:
            if float(self.conn.send_command("Get BFM.LT")) == 0:
                return
            self.ts_print("Moving BFM out")
            self.conn.send_command("Set BFM.LT.OUT")

        self.waiting(30)  # Wait 30 sec to move BFM in

        if insert:
            if not float(self.conn.send_command("Get BFM.LT")) >= 122:
                raise Exception(
                    "Error, could not insert BFM! Current value is {}".format(self.conn.send_command("Get BFM.LT")))
            else:
                self.ts_print("BFM inserted")
        else:
            if not float(self.conn.send_command("Get BFM.LT")) == 0:
                raise Exception(
                    "Error, could not remove BFM! Current value is {}".format(self.conn.send_command("Get BFM.LT")))
            else:
                self.ts_print("BFM retracted")

    def converge_with_bfm(self, p_desired, calib_As, iterations=3, datapoints=30, withdraw_bfm=True):
        """
        Converges with the BFM to a desired As flux. Only As supported right now.

        Use in recipe like: mbe.converge_with_bfm(2.5E-6,calib_As)

        :param withdraw: Whether or not to withdraw BFM at end of function (for if you want to do more measurements)
        :param p_desired: The desired pressure that you want to reach
        :param calib_As: Arsenic calibration structure that you want to use to converge
        :param iterations: Number of iterations performed for pressure convergence
        :param datapoints: Number of datapoints to take with the BFM at each iteration
        :return: The optimized As opening value
        """
        self.ts_print("Converging with BFM to {}".format(p_desired))
        f_interp = calib_As.get_interpolator()
        self.bfm(insert=True)
        offset = 0

        # Modify the interpolator using the measured bfm pressure and move to next iteration
        def f_interp_new(interp, p, _offset):
            return float(interp(p + _offset))

        self.set_param("AsCracker.Valve.OP", f_interp_new(f_interp, p_desired, offset))

        for i in range(iterations):
            self.waiting(30)
            self.ts_print("Measuring BFM pressure")
            p_bfm, _ = self.read_pressures(delay=1.0, n=datapoints, error=0.02)
            offset += p_desired - p_bfm
            optimized_as_opening = f_interp_new(f_interp, p_desired, offset)
            self.set_param("AsCracker.Valve.OP", optimized_as_opening)
            self.ts_print("Adjusting calibration curve by {:.2e}".format((p_desired - p_bfm)))
            self.ts_print("Set As valve to {:.2f}".format(f_interp_new(f_interp, p_desired, offset)))

        if withdraw_bfm:
            self.bfm(insert=False)

        return optimized_as_opening

    def wait_to_reach_temp(self, temp=None, PID='Manip', error=1, n=10, timeout_on=True):
        """
        Wait until mbe manipulator or one of the cells reaches a certain temperature

        :param temp: temperature you are waiting to reach
        :type temp: float, int
        :param error: error within which +/- the temperature should be reached
        :type error: float, int
        :return: None, returns once temperature has been reached
        """
        # TODO: make temp input optional, if none is provided simply waits until temp reaches the TSP
        if self.virtual_server:
            start_time = float(self.conn.send_command('Get time'))
        else:
            start_time = clock()

        # If no temp was passed to the function, wait until current setpoint is reached
        if not temp:
            temp = float(self.get_param("{:s}.PV.TSP".format(PID)))

        self.ts_print("Waiting to reach {:s} temperature of {:.2f}".format(PID, temp))
        if not timeout_on:
            self.ts_print("Note: Timeout condition is off.".format(PID, temp))

        t_current = float(self.get_param("{:s}.PV".format(PID)))
        t_tsp = float(self.get_param("{:s}.PV.TSP".format(PID)))

        # Have already passed the temperature that we want to reach
        if (t_tsp <= t_current <= temp) or (t_tsp >= t_current >= temp):
            self.ts_print('Temp reached! Current T = {:.2f}'.format(t_current))
            return

        t_rate = float(self.get_param("{:s}.PV.Rate".format(PID)))
        est_time = abs(t_current - temp) / t_rate * 60.0 - 3
        self.waiting(int(est_time))

        max_t = est_time * 10.

        latest_temps = []
        while True:
            if self.virtual_server:
                self.waiting(1, verbose=False)
            else:
                sleep(1)
            latest_temps.append(float(self.get_param("{:s}.PV".format(PID))))

            if len(latest_temps) > n:
                latest_temps = latest_temps[1:]

            if len(latest_temps) == n:
                t_current = np.mean(latest_temps)
                t_current_std = np.std(latest_temps)
                if abs(t_current - temp) < error and t_current_std < (error / 2.):
                    self.ts_print('Temp reached! Current T = {:.2f}+/-{:.2f}'.format(t_current, t_current_std))
                    return

                # Timeout condition
                if self.virtual_server:
                    now = float(self.conn.send_command('Get time'))
                else:
                    now = clock()
                if timeout_on and now > (start_time + max_t):
                    self.ts_print('Timeout reached! Current T = {:.2f}+/-{:.2f}'.format(t_current, t_current_std))
                    break

    def waiting(self, wait_time, verbose=True):
        """
        Waits a certain amount of time before continuing, gets rounded down to nearest second. TIP: can use instead the
        timer_start and timer_wait functions for more robust timing (in some cases).

        :param time: time in seconds that you want to wait
        :type time: float, int
        :return: None, once timer is up
        """
        # TODO: Add a shorter wait during debugging mode of a recipe

        if verbose:
            self.ts_print("Waiting {}s".format(wait_time))
        if self.virtual_server:
            self.conn.send_command('Wait {}'.format(wait_time))
        else:  # Normal recipe
            for i in xrange(int(round(wait_time))):
                sleep(1.0)

            # for _ in trange(0, int(round(wait_time)), desc='Waiting', ascii=True):
            # for _ in range(0, int(round(wait_time))):
            #     sleep(1 - time() % 1)  # sleep until a whole second boundary

    def check_stdby(self):
        """
        Checks that the MBE cells are at their standby temperatures, if not returns False
        """
        # TODO: implement a check to see which cells are used in the current recipe, only checking those specific cells
        # TODO: add check for the cryopump gatevalves, make sure they are both open before starting growth
        stdby = True
        # Check is all sources are in standby
        stdby_chk_dict = {
            "Manip.PV": (195, 205),  # (min, max) temps
            "In.PV": (510, 520),
            "Ga.PV": (545, 555),
            # "Al.PV": (745, 755), ****************************
            "As.PV": (360, 410),
            "AsCracker.PV": (595, 1005),
            # "Sb.PV": (245, 255),  # Double check this! ****************************
            # "SbCracker.PV": (795, 805),  # Double check this! ****************************
            "SUKO.OP": (0, 40),
            "SUSI.OP": (0, 11)}
        for param, val in stdby_chk_dict.iteritems():
            value = float(self.get_param(param))
            if not (val[0] < value < val[1]):
                self.ts_print(
                    'Check Standby Failed: condition {} < {} < {} not fulfilled'.format(val[0], param, val[1]))
                stdby = False

        # Check if all shutters are closed
        shutters = ['In', 'Ga', 'As', 'Al', 'Sb', 'SUSI', 'SUKO']
        for shutter in shutters:
            if not (self.get_param("Shutter.{}".format(shutter)).lower() == "closed"):
                self.ts_print('Check Standby Failed: {} Shutter Open'.format(shutter))
                stdby = False
        return stdby

    def set_stdby(self):
        """
        Closes all MBE shutters and sets all the cells to their standby temperatures (and currents). Ignores cells that
        are below their standby temperatures (therefore ignoring cells that have been cooled down)

        :return: None
        """
        # Close all shutters
        shutters = ['In', 'Ga', 'As', 'Al', 'Sb', 'SUSI', 'SUKO', 'Viewport', 'Pyrometer']
        self.shutter(shutters, [False] * len(shutters))

        # Close Arsenic/Antimony Valves
        self.set_param("AsCracker.Valve.OP", 0)
        try:
            self.set_param("SbCracker.Valve.OP", 0)
        except:
            print("ERROR, COULDN'T CLOSE SB VALVE!")

        # Stop substrate rotation
        self.set_param("Manip.RS.RPM", 0)

        # Ramp down all PID cells to standby values (ignore cold cells)
        stdby_set_dict = {
            "Manip": {"PV.TSP": 200, "PV.Rate": 100},
            "In": {"PV.TSP": 515, "PV.Rate": 15},
            "Ga": {"PV.TSP": 550, "PV.Rate": 40},
            "Al": {"PV.TSP": 750, "PV.Rate": 10},
            "Sb": {"PV.TSP": 400, "PV.Rate": 5}}
        for key, value in stdby_set_dict.iteritems():
            if float(self.get_param("{}.PV".format(key))) <= value["PV.TSP"]:  # Don't ramps up cold cells or manip
                continue
            self.set_param("{}.Mode".format(key), "Auto")
            self.set_param("{}.PV.Rate".format(key), value["PV.Rate"])
            self.set_param("{}.PV.TSP".format(key), value["PV.TSP"])

        # Ramp down all Manual doping cells to standby values)
        stdby_set_doping_dict = {
            "SUKO": {"OP.TSP": 10, "OP.Rate": 2},
            "SUSI": {"OP.TSP": 10, "OP.Rate": 2}}
        for key, value in stdby_set_doping_dict.iteritems():
            self.set_param("{}.Mode".format(key), "Manual")
            self.set_param("{}.OP.Rate".format(key), value["OP.Rate"])
            self.set_param("{}.OP.TSP".format(key), value["OP.TSP"])

        # Retract BFM
        self.bfm(insert=False)

    def reinit_cells(self, cell):
        """
        Just re-initializes all the parameters in each Eurotherm, seems to solve the problem of having NaN values read
        from the Eurotherms
        :param cell:
        :return:
        """
        cells = ['Ga', 'As', 'Sb', 'SUSI', 'SUKO', 'SbCracker', 'SbCond', 'AsCracker']  # Removed In and Al
        cells = [cell]
        for cell in [cells[0]]:
            pv = float(self.get_param("{}.PV".format(cell)))
            op = float(self.get_param("{}.OP".format(cell)))

            self.set_param("{}.PV.rate".format(cell), 0.1)
            self.set_param("{}.OP.rate".format(cell), 0.1)

            self.set_param("{}.Mode".format(cell), "Manual")
            self.set_param("{}.OP.TSP".format(cell), op)

            self.set_param("{}.Mode".format(cell), "Auto")
            self.set_param("{}.PV.TSP".format(cell), pv)

    def get_recipes_running(self):
        """
        Gets the number of recipes currently running

        :return: Number of recipes running
        :rtype: int
        """
        return int(self.conn.send_command("get this.recipesrunning"))

    def increment_recipes_running(self):
        """
        Increase the recipe counter in the MBE server

        :return: None
        """
        prev = self.get_recipes_running()
        self.conn.send_command("set this.recipesrunning inc")
        curr = self.get_recipes_running()
        if not curr == prev + 1:
            raise Exception("Could not increase the recipes running flag!")

    def decrement_recipes_running(self):
        """
        Decrease the recipe counter in the MBE server

        :return: None
        """
        prev = self.get_recipes_running()
        self.conn.send_command("set this.recipesrunning dec")
        curr = self.get_recipes_running()
        if not curr == prev - 1:
            raise Exception("Could not decrease the recipes running flag!")

    def plot_log(self, filename=None):
        """
        When running a virtual mbe session, sends the command to the mbe server to save and plot the virtual log file

        :return: None
        """
        self.conn.send_command('#plot_log {:s}'.format(filename))

    def starting_growth_prompt(self):
        if self.virtual_server:
            grow = raw_input('Starting a VIRTUAL growth! Are you sure? (y/n):  ')
        else:
            grow = raw_input('Starting a REAL growth! Are you sure? (y/n):  ')

        if not grow.lower() == 'y':
            self.ts_print('Exiting.')
            exit()
        else:
            self.ts_print('Starting growth.')
            return True


if __name__ == '__main__':
    mbe = MBERecipe(scriptname='test.py')
    from mbe_calibration import Calibration

    calib_Sb = Calibration("Sb")
    # calib_As = Calibration("As")
    # calib_Ga = Calibration("Ga")
    # calib_Al = Calibration("Al")
    # calib_In = Calibration("In")

    # mbe.decrement_recipes_running()
    pass