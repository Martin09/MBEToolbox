"""
Trying to find the optimal way to store the data of virtual mbe log file
"""

import gzip, pickle
import pandas as pd

if __name__ == '__main__':
    print('Loading file.')

    # # Load a raw pickle file without compression
    # with file('virtual_log_file.p', 'rb') as f:
    #     data_array = pickle.load(f)

    # Load a gzipped pickle file
    with gzip.GzipFile('virtual_log_file.pgz', 'rb') as f:
        data_array = pickle.load(f)

    print('File loaded')

    one_array = data_array[0]
    for key, value in one_array.iteritems():
        one_array[key] = [value]

    df = pd.DataFrame()
    df = df.from_dict(one_array)