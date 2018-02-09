"""
Small script that I will use to try and understand how the MBE_Tools helper script works for loading log files
"""

from MBE_Tools import LogFile

if __name__ == "__main__":
    print('Loading log file.')
    logfile = LogFile('Log_160216.log')
    print('Log file loaded.')
