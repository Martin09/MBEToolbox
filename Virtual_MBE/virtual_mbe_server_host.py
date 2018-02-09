"""
Server to debug python mbe growth recipes. A virtual emulation of the MBE.
"""

import SocketServer, gzip, copy
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import cPickle as pickle
import ntpath

from SocketServer import TCPServer
import matplotlib

matplotlib.rc('legend', fontsize=10, handlelength=2)


class VirtualMBEServer(TCPServer):
    """
    A virtual MBE server which contains the request handler and the virtual mbe
    """

    def __init__(self, server_address, handler_class):
        TCPServer.__init__(self, server_address, handler_class)
        self.mbe = VirtualMBE()

    def init_mbe(self):
        """
        Reset the mbe to the default values (reset the mbe)

        :return: True if it was successfully reset
        """
        self.mbe = VirtualMBE()
        return True

    def __del__(self):
        self.shutdown()


class MBERequestHandler(SocketServer.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        """
        Handle a request made to the server. When a client sends some data this function gets called to handle it. The
        function reads the request, processes it, generates a reply and sends back the reply

        :return: The reply of the server to the client.
        :rtype: str
        """
        # self.request is the TCP socket connected to the client
        data = self.request.recv(1024).strip()
        print("{} wrote: {}".format(self.client_address[0], data))
        reply = self.process_command(data)
        # just send back the same data, but upper-cased
        self.request.sendall(str(reply))

    def process_command(self, command):
        """
        Processes commands sent to the server from the clients

        :param command: command that was sent to the server
        :return: None
        """
        words = command.split(" ")

        if '#reset_virt_mbe' in command:
            if self.server.init_mbe():
                return 'OK.'
            else:
                return 'Error!'
        elif '#plot_log' in command:
            fn = words[1] if len(words) > 1 else None
            if self.server.mbe.plot_recipe(filename=fn):
                return 'OK.'
            else:
                return 'Error!'

        words = [word.lower() for word in words]  # put them in lowercase

        if len(words) < 2:
            return "Error!"
            # raise Exception("Expected more than one word!")

        if words[0] == "get":
            if not len(words) == 2:
                return "Error!"
                # raise Exception("Expected two words in GET command, got {}: '{}'".format(len(words), command))
            else:
                value = self.server.mbe.get_param(words[1])
                reply = value
        elif words[0] == "set":
            if len(words) == 3:
                if self.server.mbe.set_param(words[1], words[2]):
                    reply = "OK."
                else:
                    reply = "Error!"
            # If its a BFM command
            elif len(words) == 2 and (words[1].lower() == 'bfm.lt.in') or (words[1].lower() == 'bfm.lt.out'):
                if self.server.mbe.set_param(words[1], None):
                    reply = "OK."
                else:
                    reply = "Error!"
            else:
                return "Error!"
                # raise Exception("Expected three words in SET command, got {}: '{}'".format(len(words), command))

        elif words[0] == 'wait':
            if not len(words) == 2:
                return "Error!"
            else:
                if self.server.mbe.wait(float(words[1])):
                    reply = "OK."
                else:
                    reply = "Error!"

        elif words[0] in ['open', 'close']:  # Shutter manipulation
            if not len(words) == 2:
                return "Error!"
            else:
                if words[0] == 'close':
                    words[0] = 'closed'  # small difference in the way shutters are stored: "closed" or "open"
                if self.server.mbe.set_param('shutter.' + words[1], words[0]):
                    reply = "OK."
                else:
                    reply = "Error!"
        else:
            return "Error!"
            # raise Exception("Unknown command {}".format(word[0]))

        return reply


# TODO: add the option to initialize the virtual MBE parameters with the current parameters of the real MBE
class VirtualMBE:
    """
    A virtual MBE object that emulates the parameters of the real MBE. Including most of the variables and has many
    helper functions to manipulate these variables.
    """

    def __init__(self):
        """
        Initializes all parameters of the virtual MBE

        :param return: None
        """
        self.timeStep = 1
        # Initialize MBE variables
        self.dataArray = []
        self.shutters = ['in', 'ga', 'as', 'al', 'sb', 'susi', 'suko', 'pyrometer']
        self.controllers = ['manip', 'in', 'ga', 'as', 'al', 'sb', 'susi', 'suko', 'ascracker', 'sbcracker']

        self.variables = {'time': 0, 'manip.rs.rpm': 0,
                          'mbe.p': 1E-7, 'this.recipesrunning': 0,
                          'manip.pv': 200, 'manip.pv.rate': 0, 'manip.pv.tsp': 200,
                          'manip.op': 0.0, 'manip.op.rate': 0, 'manip.mode': 'pid',
                          'ga.pv': 550, 'ga.pv.rate': 0, 'ga.pv.tsp': 550,
                          'ga.op': 0.0, 'ga.op.rate': 0, 'ga.op.tsp': 0, 'ga.mode': 'pid',
                          'in.pv': 515, 'in.pv.rate': 0, 'in.pv.tsp': 515,
                          'in.op': 0.0, 'in.op.rate': 0, 'in.op.tsp': 0, 'in.mode': 'pid',
                          'as.pv': 375, 'as.pv.rate': 0, 'as.pv.tsp': 375,
                          'as.op': 0.0, 'as.op.rate': 0, 'as.op.tsp': 0, 'as.mode': 'pid',
                          'sb.pv': 250, 'sb.pv.rate': 0, 'sb.pv.tsp': 250,
                          'sb.op': 0.0, 'sb.op.rate': 0, 'sb.op.tsp': 0, 'sb.mode': 'pid',
                          'al.pv': 750, 'al.pv.rate': 0, 'al.pv.tsp': 750,
                          'al.op': 0.0, 'al.op.rate': 0, 'al.op.tsp': 0, 'al.mode': 'pid',
                          'ascracker.pv': 600, 'ascracker.pv.rate': 2, 'ascracker.pv.tsp': 600,
                          'ascracker.op': 0.0, 'ascracker.op.rate': 0, 'ascracker.op.tsp': 0, 'ascracker.mode': 'pid',
                          'ascracker.valve.op': 0,
                          'sbcracker.pv': 800, 'sbcracker.pv.rate': 10, 'sbcracker.op.tsp': 0, 'sbcracker.pv.tsp': 800,
                          'sbcracker.op': 0.0, 'sbcracker.op.rate': 0, 'sbcracker.mode': 'pid',
                          'sbcond.pv': 800, 'sbcond.pv.rate': 10, 'sbcond.op.tsp': 0, 'sbcond.pv.tsp': 800,
                          'sbcond.op': 0.0, 'sbcond.op.rate': 0, 'sbcond.mode': 'pid',
                          'suko.pv': 0, 'suko.pv.rate': 0, 'suko.pv.tsp': 0,
                          'suko.op': 10, 'suko.op.rate': 0.5, 'suko.op.tsp': 10, 'suko.mode': 'manual',
                          'susi.pv': 0, 'susi.pv.rate': 0, 'susi.pv.tsp': 0,
                          'susi.op': 10, 'susi.op.rate': 0.5, 'susi.op.tsp': 10, 'susi.mode': 'manual',
                          'shutter.in': 'closed', 'shutter.ga': 'closed', 'shutter.as': 'closed',
                          'shutter.al': 'closed', 'shutter.sb': 'closed', 'shutter.susi': 'closed',
                          'shutter.suko': 'closed', 'shutter.pyrometer': 'closed',
                          'pyrometer.t': 0, 'bfm.lt': 0}

    def set_param(self, parameter, value):
        """
        Set a parameter of the virtual MBE to a specific value

        :param parameter: parameter in the variables dictionary that you would like to set
        :type parameter: str
        :param value: value that you would like to set to the parameter
        :type value: str
        :return: True if it was able to set the value, false otherwise
        """
        parameter = parameter.lower()  # Make the input string all lowercase, case does not matter
        # If its the BFM, there is no value
        if parameter == 'bfm.lt.out':
            self.variables['bfm.lt'] = 0
            return True
        elif parameter == 'bfm.lt.in':
            self.variables['bfm.lt'] = 124
            return True

        if parameter not in self.variables.iterkeys():  # Check if parameter exists
            return False

        try:  # Try to first convert value string into a float
            value = float(value)
            self.variables[parameter] = value
            return True
        except ValueError:  # If there is an error, it is not a float, continue
            pass

        value = value.lower()  # It is a string, so make it lowercase since case does not matter

        if value in ("true", "false"):  # Is it a boolean string?
            value = value == 'true'
            self.variables[parameter] = value
            return True

        # If it is not a boolean value it must simply be a string... check if it is a specific string:
        if 'this.recipesrunning' in parameter:
            if value == 'inc':
                self.variables[parameter] += 1
                return True
            elif value == 'dec':
                if self.variables[parameter] == 0:
                    return True
                self.variables[parameter] -= 1
                return True
            else:
                return False
        elif 'shutter' in parameter:
            if value in ['open', 'closed']:
                self.variables[parameter] = value
                return True
            else:
                return False
        elif 'mode' in parameter:
            if value in ['pid', 'manual']:
                self.variables[parameter] = value
                return True
            else:
                return False

        # If it is another string then just set it (assume it is correct, maybe should add some more checks here later)
        self.variables[parameter] = value
        return True

    def get_param(self, parameter):
        """
        Get a certain parameter of the MBE

        :param parameter: Parameter that you would like to know.
        :type parameter: str
        :return: the value of the parameter requested, can be one of many types depending on the parameter
        :rtype: int, float, bool, str
        """
        if parameter.lower() == 'manip.rs':
            parameter = 'manip.rs.rpm'
        elif parameter.lower() == 'ascracker.valve':
            parameter = 'ascracker.valve.op'

        if parameter.lower() not in self.variables.iterkeys():
            return False
        if parameter.lower() == 'pyrometer.t':
            return self.variables['manip.pv'] - 110  # Rough estimate what the pyrometer should read
        return self.variables[parameter.lower()]

    def do_timestep(self):
        """
        Evolve the parameters of the MBE by one timestep (one second). Depending on the ramp rate and setpoint of the
        cells, calculates the values of the parameters one second into the future and sets them.

        :return: Nothing
        """
        for what in self.controllers:  # Loops over eurotherm controllers (growth cells, doping cells, manipulator etc.)
            if self.variables[what + '.mode'] == 'pid':  # Do different stuff depending on the cell mode setting
                pv_or_op = 'pv'
            elif self.variables[what + '.mode'] == 'manual':
                pv_or_op = 'op'
            else:
                raise Exception('Unrecognised control mode {}'.format(self.variable[what + '.mode']))
            # Calculate the new value
            difference = self.variables[what + '.' + pv_or_op + '.tsp'] - self.variables[what + '.' + pv_or_op]
            if np.abs(difference) > 0:  # It is ramping up/down
                increment = self.timeStep * self.variables[what + '.' + pv_or_op + '.rate'] / 60.0 * np.sign(
                    difference)
                if np.abs(increment) < np.abs(difference):  # Setpoint not reached
                    self.variables[what + '.' + pv_or_op] += increment
                else:  # Setpoint reached
                    self.variables[what + '.' + pv_or_op] = self.variables[what + '.' + pv_or_op + '.tsp']
        self.variables['time'] += 1  # Increment the time variable to indicate we have moved ahead in time by 1
        # Save data to array which we can then graph (acts like our log file)
        self.dataArray.append(copy.deepcopy(self.variables))

    def wait(self, seconds):
        """
        Tells virtual MBE to wait specific amount of time during which the parameters keep ramping up/down

        :param seconds: number of seconds to wait for. If float, gets rounded down to nearest second.
        :type seconds: float, int
        :return: True if wait was successful, false otherwise
        :rtype: bool
        """
        if seconds < 0:
            return False
        for sec in range(int(seconds)):
            self.do_timestep()
        return True

    def plot_recipe(self, data_frame=None, show=False, filename=None):
        """
        Plot the log file so that it can be analyzed. It both saves the pandas dataframe log to a gzipped csv file
        called 'virtual_log_file.csv.zip' and outputs a png of the plot called 'virtual_log_file.png'

        :param data_frame: if you want to process a specific data_frame other than the current one
        :type data_frame: pandas DataFrame
        :param show: show the plot in a figure before saving to png
        :type show: bool
        :return: True if it was successful
        :rtype: bool
        """

        if filename:
            savename = ntpath.basename(filename).split('.')[0]
        else:
            savename = 'virtual_log_file'

        if not self.dataArray and data_frame is None:  # If the array is empty
            print('Error: data_array is empty, need to run the simulation first!')
            return False
        elif not self.dataArray and data_frame is not None:
            df = data_frame
        else:
            data_array = self.dataArray
            df = pd.DataFrame()
            df = df.from_dict(data_array)

        fig = plt.figure()
        ax1 = plt.subplot(311)
        ax2 = plt.subplot(312, sharex=ax1)
        ax3 = plt.subplot(313, sharex=ax1)

        df['time_in_min'] = df['time'] / 60.0

        # It is nice to save the files as compressed csv files because the file size is quite small when zipped and, if
        # the user wants, they can simply unzip the file and look at it in detail in a common csv format
        df.to_csv('{:s}.csv.zip'.format(savename), compression='gzip')

        df1 = df.filter(regex=".pv$")
        df1['time_in_min'] = df1.index / 60.0
        goodcols = [col for col in df1.columns.tolist() if
                    not any(x in col for x in ['cracker', 'cond', 'susi', 'suko'])]
        df1 = df1[goodcols]
        df2 = df.filter(regex='(^su..\.op$)|(valve.op)')
        df2['time_in_min'] = df1.index / 60.0
        df3 = df.filter(regex="^shutter.")
        for i, col in enumerate(df3.columns):
            df3[col] = df3[col] == 'open'
            df3[col] = df3[col].apply(int) * (.9 + (i / 20.))
        df3['time_in_min'] = df3.index / 60.0

        colors1 = plt.cm.gist_rainbow(np.linspace(0, 1, 6))
        colors2 = plt.cm.gist_rainbow(np.linspace(0, 1, 4))
        colors3 = plt.cm.gist_rainbow(np.linspace(0, 1, 8))
        df1.plot(x='time_in_min', ax=ax1, grid=True, ylim=[190, 1200], color=colors1)
        try:
            df2.plot.area(x='time_in_min', ax=ax2, grid=True, ylim=[0, 100], stacked=False, sharex=True, color=colors2)
            df3.plot.area(x='time_in_min', ax=ax3, grid=True, ylim=[-0.1, 1.3], stacked=False, sharex=True,
                          color=colors3)
        except AttributeError:  # If installation doesn't have latest version of pandas don't use "area" attribute
            print('Warning: Detected old version of pandas, update for prettier plots!')
            df2.plot(x='time_in_min', ax=ax2, grid=True, ylim=[0, 100], sharex=True, color=colors2)
            df3.plot(x='time_in_min', ax=ax3, grid=True, ylim=[-0.1, 1.3], sharex=True, color=colors3)

        ax1.set_ylabel('Temperature ($^\circ$C)')
        ax2.set_ylabel('Power/Opening (%)')
        ax3.set_xlabel('Time (min)')
        ax3.set_ylabel('Shutter Opening')

        for ax in [ax1, ax2, ax3]:  # Formatting the legend size and location
            # Shrink current axis by 20%
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

            # Put a legend to the right of the current axis
            ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        fig.set_size_inches(11.69, 8.27)  # A4 size landscape output
        fig.savefig('{:s}.png'.format(savename), dpi=600)  # Save the plot as PNG file
        if show:
            plt.show()
        else:
            plt.close()
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.dataArray
        return

    def __del__(self):
        del self.dataArray
        return


# For testing purposes and running the MBE server
if __name__ == "__main__":
    HOST, PORT = "localhost", 9999
    # Create the server, binding to localhost on port 9999
    server = VirtualMBEServer((HOST, PORT), MBERequestHandler)

    # Activate the server; this will keep running until you interrupt the program with Ctrl-C
    print("Starting server.")
    server.serve_forever()
