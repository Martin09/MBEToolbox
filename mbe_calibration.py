# TODO: repurpose this to also include RHEED calibration files
# use both last RHEED calibration and latest BFM calibration to get the proper calibration
# TODO: Add a warning if the fits are bad (R2 < 0.98?)

import ntpath
from datetime import datetime
from glob import glob

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d  # , Akima1DInterpolator
from scipy import optimize, log10

matplotlib.style.use('ggplot')


class Calibration:
    """
    Class for reading MBE flux calibration files
    """

    def __init__(self, material, filename=None, rheed_filename=None, plot=False):
        """
        Initialize the calibration

        :param material: Name of material you are interested in (ex: 'Ga', 'As', etc.)
        :type material: str
        :param filename: Filename of the desired calibration file to use, if none uses the latest calibration
        :type filename: str
        :param plot: whether or not you want to plot the calibration curve (note: need to close graph before script will continue)
        :type plot: bool
        """
        print('Fetching calibration data for {}'.format(material))
        self.mat = material
        # Set the name of the x-axis data
        if self.mat == 'As':
            self.x_col = 'AsOpening'
        else:
            self.x_col = '{:s}Temp'.format(self.mat)
        self.spline_interp_inv = None
        if filename is None:
            filepath = self.get_latest_file(directory='//MBESERVER/Documents/Calibrations_D1/')
        else:
            filepath = '//MBESERVER/Documents/Calibrations_D1/' + filename
        self.directory, self.filename = ntpath.split(filepath)
        self.bfm_data = self.read_bfm_file(filepath)
        self.spline_interp = self.make_interpolator(self.bfm_data)
        self.bfm_plt_axis = None
        self.rheed_data = None

        if plot:
            self.bfm_plt_axis = self.plot_bfm_data(self.bfm_data, self.filename)

        if not self.mat.lower() == 'as':  # If its not arsenic, fetch the latest rheed calibration
            self.rheed_data = self.get_rheed_data(rheed_filename)

    def get_rheed_data(self, fn_rheed=None):
        """
        Gets the RHEED data from the rheed vs bfm folder
        :param fn_rheed: filename of the rheed file we want
        :return: rheed calibration dataframe
        """
        if fn_rheed:
            rheed_data = self.read_rheed_file(fn_rheed)
        else:
            rheed_path = self.get_latest_file(
                directory='//MBESERVER/Documents/Calibrations_D1/Martin/RHEED_vs_BFM/' + self.mat)
        return self.read_rheed_file(rheed_path)

    def read_bfm_file(self, filename):
        """
        Reads the bfm calibration data
        :param filename: filename of the bfm calibration we want
        :return: bfm calibration dataframe
        """
        print('Fetching BFM calibration file: {}'.format(filename))
        bfm_data = self.read_file(filename)
        bfm_data.columns = [self.x_col, 'BFM.P', 'MBE.P']  # Rename dataframe columns
        return bfm_data

    def read_rheed_file(self, filename):
        """
        Reads the rheed calibration data
        :param filename: filename of the rheed calibration we want
        :return: rheed calibration dataframe
        """
        print('Fetching RHEED calibration file: {}'.format(filename))
        rheed_data = self.read_file(filename)
        rheed_data.columns = ['BFM.P', 'Rate (A/s)']  # Rename dataframe columns
        return rheed_data

    def read_file(self, filename):
        """
        Read in the calibration file (bfm or rheed)

        :param filename: the filename to read in
        :type filename: str
        :return: data from the calibration file
        :rtype: Pandas dataframe
        """

        data = pd.read_csv(filename, delimiter='\t', header=None, comment='#')  # First try with no headers
        if any(isinstance(cell, str) for cell in data.loc[0]):  # If there is a header
            data = pd.read_csv(filename, delimiter='\t', header=0)  # Import it properly
        data = data.iloc[:, 0:3]  # Remove the standard deviation columns (5 and 6), if they exist
        return data

    def get_latest_file(self, directory='CalibrationFiles/'):
        """
        Get latest calibration file. Automatically pulls up latest file from the given directory

        :param directory: the directory where the calibration files are
        :type directory: str
        :return: full name and location of the latest calibration file
        :rtype: str
        """
        files = glob('{:s}/*_{:s}.txt'.format(directory, self.mat))  # Get all the relevant files in the directory

        files = [list(ntpath.split(filename)) for filename in
                 files]  # Split the paths into directory name and file name

        # Initialize search for the latest file
        latestfile = files[0]
        file_naming_format1 = '%Y-%m-%d_%H-%M-%S_{:s}.txt'.format(self.mat)
        file_naming_format2 = '%Y-%m-%d_{:s}.txt'.format(self.mat)  # No time values

        try:
            latest = datetime.strptime(latestfile[1], file_naming_format1)
        except:  # Probably doesn't have time values
            latest = datetime.strptime(latestfile[1], file_naming_format2)

        # Loop over all files, extract the latest file
        for pathname, filename in files:
            try:
                curr = datetime.strptime(filename, file_naming_format1)
                if curr > latest:
                    latestfile = [pathname, filename]
                    latest = datetime.strptime(latestfile[1], file_naming_format1)
            except:  # Probably doesn't have time values
                curr = datetime.strptime(filename, file_naming_format2)
                if curr > latest:
                    latestfile = [pathname, filename]
                    latest = datetime.strptime(latestfile[1], file_naming_format2)

        return latestfile[0] + '/' + latestfile[1]

    def make_interpolator(self, data):
        """
        Makes the interpolator that is used to then interpolate the data

        :param data: the data to be interpolated
        :type data:
        :return: spline interpolation function, y = f(x)
        :rtype: func
        """
        if self.mat.lower() == 'as':
            # Average the data points so there is only one y value per x value
            spl_data = data.groupby(by=self.x_col).mean().reset_index()
            spl_x = np.array(spl_data[self.x_col])
            spl_y = np.array(spl_data['BFM.P'])

            # Create interpolation function
            # spl = Akima1DInterpolator(spl_y, spl_x)
            bfm_model = interp1d(spl_y, spl_x, kind='linear')
        else:
            # TODO: Test this!
            #### BELOW IS FOR FITTING A POWER LAW FUNCTION, USE FOR THE BFM VS CELL TEMP DATA (EXCL. AS)
            logx = log10(self.bfm_data['BFM.P'])
            logy = log10(self.bfm_data[self.x_col])

            powerlaw = lambda x, amp, index: amp * (x ** index)
            # define our (line) fitting function
            fitfunc = lambda p, x: p[0] + p[1] * x
            errfunc = lambda p, x, y: (y - fitfunc(p, x))
            pinit = [1.0, -1.0]
            out = optimize.leastsq(errfunc, pinit, args=(logx, logy), full_output=1)

            pfinal = out[0]
            covar = out[1]

            index = pfinal[1]
            amp = 10.0 ** pfinal[0]

            powerlaw = lambda x, amp, index: amp * (x ** index)
            bfm_model = lambda x: powerlaw(x, amp, index)

        return bfm_model

    def calc_setpoint(self, desired_flux):
        """
        Given the desired material flux, will output the proper setpoint from the latest calibration file

        :param desired_flux: Flux (pressure in mBar) that you want to calculate the setpoint
        :type desired_flux: float
        :return: Ideal setpoint in the range of the calibration file (0-100% for As, temperature for other cells)
        :rtype: float
        """

        # TODO: add input checking to make sure the desired_flux is within some reasonable range

        if self.mat.lower() == 'as':  # Be careful about going outside the calibration range
            calib_max = self.bfm_data['BFM.P'].max()
            calib_min = self.bfm_data['BFM.P'].min()
            # TODO: Add the possibility to extrapolate outside fitting range?
            if desired_flux >= self.bfm_data['BFM.P'].max():
                # raise ValueError('The desired flux is outside of the calibration range!')
                print(
                    "Warning, the desired flux of {:.2e} is outside of the calibration range({:.2e} to {:.2e}). Using "
                    "highest value!".format(desired_flux, calib_min, calib_max))
                return float(self.spline_interp(calib_max))
            elif desired_flux <= self.bfm_data['BFM.P'].min():
                # raise ValueError('The desired flux ({}) is outside of the calibration range!'.format(desired_flux))
                print(
                    "Warning, the desired flux of {:.2e} is outside of the calibration range({:.2e} to {:.2e}). Using "
                    "lowest value!".format(desired_flux, calib_min, calib_max))
                return float(self.spline_interp(calib_min))

        opening = self.spline_interp(desired_flux)
        return float(opening)

    def calc_setpoint_gr(self, desired_gr):
        """
        Given the desired material growth rate (A/s), will output the proper cell setpoint from the latest RHEED and BFM calibration files
        :param desired_gr: Desired growth rate for GaAs, InAs, AlAs etc.
        :return: Setpoint to use (either cell temperature or As opening)
        """
        # TODO: add input checking to make sure the desired_gr is within some reasonable range
        if self.mat.lower() == 'as':
            return ValueError('Arsenic calibration cannot use GR setpoint!')

        x = self.rheed_data['Rate (A/s)']
        y = self.rheed_data['BFM.P']
        p = np.polyfit(x, y, 1)

        bfm_pressure = np.polyval(p, desired_gr)

        # TODO: Add limit testing!!! If returns value outside the allowed temperature range, raise an exception


        return self.calc_setpoint(bfm_pressure)

    def get_interpolator(self):
        """
        Getter function to get the interpolator function of the calibration
        :return: Interpolator function
        """
        return self.spline_interp

    def plot_bfm_data(self, data, title):
        """
        Plots the calibration data

        :param title: title of the plot
        :type title: str
        :param data: data to be plotted
        :type data: Pandas dataframe
        :return: axis handle
        :rtype: axis handle
        """
        # Plot the data
        xlim = None
        ylim = None
        # ylim = [-1E-7, max(data['BFM.P']) * 1.05]
        xrange = max(self.bfm_data[self.x_col]) - min(self.bfm_data[self.x_col])
        yrange = max(self.bfm_data['BFM.P']) - min(self.bfm_data['BFM.P'])
        ylim = [min(self.bfm_data['BFM.P']) - yrange * 0.05, max(self.bfm_data['BFM.P']) + yrange * 0.05]
        xlim = [min(self.bfm_data[self.x_col]) - xrange * 0.05, max(self.bfm_data[self.x_col]) + xrange * 0.05]

        ax = data.plot(x=self.x_col, y='BFM.P', style='.-', grid=True, logy=False, xlim=xlim, ylim=ylim)
        if self.mat == 'As':
            ax.set_xlabel('As Opening %')
        else:
            ax.set_xlabel('{:s} Temp (deg C)'.format(self.mat))
        ax.set_ylabel('Pressure')
        ax.set_title(title)

        # Plot the interpolated function
        y_interp = np.linspace(min(self.bfm_data["BFM.P"]) * 1.01, max(self.bfm_data["BFM.P"]) * 0.99, 101)
        x_interp = self.spline_interp(y_interp)
        ax.plot(x_interp, y_interp, label='Model')
        ax.legend(loc='best')

        plt.show()
        return ax


if __name__ == '__main__':
    # fn = None
    fn = '2017-07-03_09-45-00_As.txt'
    # fn = 'CalibrationFiles/2016-08-16_22-59-32_Ga.txt'
    calib = Calibration('As', plot=True)
    calib2 = Calibration('In', plot=True)

    print calib.calc_setpoint(4E-6)
    print calib2.calc_setpoint_gr(0.2)
