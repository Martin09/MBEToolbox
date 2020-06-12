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

    def __init__(self, material, filename=None, rheed_filename=None, plot=False, bfm_correction=None):
        """
        Initialize the calibration

        :param material: Name of material you are interested in (ex: 'Ga', 'As', etc.)
        :type material: str
        :param filename: Filename of the desired calibration file to use, if none uses the latest calibration
        :type filename: str
        :param plot: whether or not you want to plot the calibration curve (note: need to close graph before script will continue)
        :type plot: bool
        :param bfm_correction: function which takes the current bfm pressures and outputs a corrected pressure
        :type bfm_correction: function
        """
        print('Fetching calibration data for {}'.format(material))
        self.mat = material
        # Set the name of the x-axis data
        if self.mat == 'As':
            self.x_col = 'AsOpening'
        elif self.mat == 'Sb':
            self.x_col = 'SbOpening'
        else:
            self.x_col = '{:s}Temp'.format(self.mat)
        self.spline_interp_inv = None

        calib_path = '//MBESERVER/Documents/Calibrations_D1/'
        if not ntpath.exists(calib_path):  # if calibration files on server are not available
            calib_path = '../Calibration_Data/BFM_vs_CellT/'  # use local calibration files

        if filename is None:
            filepath = self.get_latest_file(directory=calib_path)
        else:
            filepath = calib_path + filename
        self.directory, self.filename = ntpath.split(filepath)
        self.bfm_data = self.read_bfm_file(filepath)

        if bfm_correction is not None:
            try:
                self.bfm_data['BFM.P'] = [bfm_correction(dat) for dat in self.bfm_data['BFM.P']]
            except:
                print('Error, could not apply BFM correction!')
                raise

        self.spline_interp = self.make_interpolator(self.bfm_data)
        self.bfm_plt_axis = None
        self.rheed_data = None

        self.lattice_const_dict = {"ga": 5.6532, "al": 5.6605, "in": 6.0583}  # GaAs/AlAs/InAs in Angstrom
        self.lattice_const = self.lattice_const_dict.get(material.lower())

        if plot:
            self.bfm_plt_axis = self.plot_bfm_data(self.bfm_data, self.filename)

        # If its not arsenic or antimony, fetch the latest rheed calibration
        if not (self.mat.lower() == 'as' or self.mat.lower() == 'sb'):
            self.rheed_data = self.get_rheed_data(rheed_filename)

    def get_rheed_data(self, fn_rheed=None):
        """
        Gets the RHEED data from the rheed vs bfm folder
        :param fn_rheed: filename of the rheed file we want
        :return: rheed calibration dataframe
        """
        bfm_path = '//MBESERVER/Documents/Calibrations_D1/Martin/RHEED_vs_BFM/'
        if not ntpath.exists(bfm_path):  # if calibration files on server are not available
            bfm_path = '../Calibration_Data/RHEED_vs_BFM/'  # use local calibration files

        if fn_rheed:
            rheed_path = bfm_path + self.mat + "/" + fn_rheed
        else:
            rheed_path = self.get_latest_file(directory=bfm_path + self.mat)
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
        self.rheed_filename = filename
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

    def get_latest_file(self, directory='Calibration_Data/'):
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
        file_naming_format1 = '%Y-%m-%d_%H-%M-%S'
        file_naming_format2 = '%Y-%m-%d'  # No time values

        try:

            latest = datetime.strptime('_'.join(latestfile[1].split('_')[:2]), file_naming_format1)
        except:  # Probably doesn't have time values
            latest = datetime.strptime('_'.join(latestfile[1].split('_')[:1]), file_naming_format2)

        # Loop over all files, extract the latest file
        for pathname, filename in files:
            try:
                curr = datetime.strptime('_'.join(filename.split('_')[:2]), file_naming_format1)
                if curr > latest:
                    latestfile = [pathname, filename]
                    latest = datetime.strptime('_'.join(filename.split('_')[:2]), file_naming_format1)
            except:  # Probably doesn't have time values
                curr = datetime.strptime('_'.join(filename.split('_')[:1]), file_naming_format2)
                if curr > latest:
                    latestfile = [pathname, filename]
                    latest = datetime.strptime('_'.join(filename.split('_')[:1]), file_naming_format2)

        return latestfile[0] + '/' + latestfile[1]

    def make_interpolator(self, data):
        """
        Makes the interpolator that is used to then interpolate the data

        :param data: the data to be interpolated
        :type data:
        :return: spline interpolation function, y = f(x)
        :rtype: func
        """
        if self.mat.lower() == 'as' or self.mat.lower() == 'sb':
            # Average the data points so there is only one y value per x value
            spl_data = data.groupby(by=self.x_col).mean().reset_index()
            spl_x = np.array(spl_data[self.x_col])
            spl_y = np.array(spl_data['BFM.P'])

            # Create interpolation function
            # spl = Akima1DInterpolator(spl_y, spl_x)
            bfm_model = interp1d(spl_y, spl_x, kind='linear')
        else:
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

        if self.mat.lower() == 'as' or self.mat.lower() == 'sb':  # Be careful about going outside the calibration range
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
        if self.mat.lower() == 'sb':
            return ValueError('Antimony calibration cannot use GR setpoint!')

        x = self.rheed_data['Rate (A/s)']
        y = self.rheed_data['BFM.P']
        p = np.polyfit(x, y, 1)

        bfm_pressure = np.polyval(p, desired_gr)

        # TODO: Add limit testing!!! If returns value outside the allowed temperature range, raise an exception

        return self.calc_setpoint(bfm_pressure)

    def calc_p_arsenic(self, group3_gr, desired_53ratio):
        """
        Given the desired V/III ratio and the group III growth rate, returns the required As pressure
        :param group3_gr: growth rate in A/s of the group III material
        :param desired_53ratio: desired V/III ratio
        :return: required pressure in Torr of the As cell
        """
        if self.mat.lower() == 'as':
            return ValueError('Arsenic calibration cannot use GR setpoint!')
        if self.mat.lower() == 'sb':
            return ValueError('Antimony calibration cannot use GR setpoint!')

        return self.calc_bfm_p(group3_gr) * desired_53ratio

    def calc_bfm_p(self, group3_gr):
        """
        Given the group III growth rate, returns the interpolated BFM pressure of the cell
        :param group3_gr: group three desired growth rate
        :return: pressure of the cell at the desired growth rate
        """

        x = self.rheed_data['Rate (A/s)']
        y = self.rheed_data['BFM.P']
        p = np.polyfit(x, y, 1)

        return np.polyval(p, group3_gr)

    def conv_gr_to_af(self, group3_gr):
        """
        Converts the group III growth rate into atomic flux in atoms/m2/s.
        NOTE: assumes an FCC crystal and that the calibration was done on a 100 substrate!
        :param group3_gr: growth rate in A/s to be converted to atomic flux
        :return: atomic flux in atoms/m2/s
        """
        if not self.lattice_const:
            return ValueError("This material doesn't have a defined lattice constant!")

        ml_gr = group3_gr / (self.lattice_const / 2.)  # Convert to monolayer growth rate ML/s
        return 2. / (self.lattice_const * 1E-10) ** 2. * ml_gr

    # TODO: get the atomic flux calculations working for As as well
    def conv_af_to_gr(self, atomic_flux):
        """
        Converts the atomic flux in atoms/m2/s into group III growth rate
        NOTE: assumes an FCC crystal and that the calibration was done on a 100 substrate!
        :param atomic_flux: atomic flux in atoms/m2/s
        :return: growth rate in A/s
        """
        if not self.lattice_const:
            return ValueError("This material doesn't have a defined lattice constant!")

        ml_gr = atomic_flux / 2. * (self.lattice_const * 1E-10) ** 2.
        return ml_gr * (self.lattice_const / 2.)  # Convert to angstrom growth rate (A/s)

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
        if self.mat == 'As' or self.mat == 'Sb':
            ax.set_xlabel(self.mat + ' Opening %')
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
    calib = Calibration('Ga', plot=True)
    calib1 = Calibration('Sb', plot=True)
    calib2 = Calibration('In', plot=True)

    # print calib.calc_setpoint(4E-6)
    print calib.calc_setpoint_gr(0.3)
