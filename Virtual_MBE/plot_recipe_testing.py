"""
Helper function for easily trying new ways to plot the virtual log file recipe
"""

import matplotlib
import pandas as pd

from Virtual_MBE.virtual_mbe_server_host import VirtualMBE

matplotlib.rc('legend', fontsize=10, handlelength=2)

if __name__ == '__main__':
    print('Loading file.')

    df = pd.read_csv('virtual_log_file.csv.zip', compression='gzip')  # With compression
    # df = pd.read_csv('virtual_log_file_small.csv')  # Without compression

    print('Plotting data.')
    mbe = VirtualMBE()
    mbe.plot_recipe(data_frame=df)

    df.drop()