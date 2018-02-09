import socket
from time import sleep


class Connect(object):
    """
    Creates a TCP server client connection: allows you to communicate with a TCP server.
    """

    def __init__(self, HOST, PORT, verbose=False):
        """
        Initializes the object with proper host id and port

        :param HOST: ip address of the host server
        :type HOST: str
        :param PORT: port of the host server to communicate over
        :type PORT: int
        :param verbose: if true then prints the send and receive data to the console for debugging
        :type verbose: bool
        """
        self.HOST, self.PORT = HOST, PORT
        self.verbose = verbose

    def connect(self):
        """
        Creates the socket connection to the server

        :return: socket object over which we can communicate
        :rtype: socket
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.verbose:
            print('connecting to host')
        sock.connect((self.HOST, self.PORT))
        return sock

    def send_command(self, command):
        """
        Sends a command to the server by first initializing the socket, sending the command, getting the response and
        then closing the socket

        :param command: command to be sent to the server
        :type command: str
        :return: response from the server
        :rtype: str
        """
        sock = self.connect()  # Create the socket connection
        if self.verbose:
            print('sending: ' + command)
        sock.sendall(command)  # Send command over the connection
        sleep(0.1)
        data = sock.recv(1024).strip()  # Read the response
        if self.verbose:
            print('received: ' + data)
        sock.close()  # Close socket after getting the response
        return data

    def close(self):
        """
        No need to do anything when closing the connection since the socket is closed after each sent command

        :return: None
        """
        return


# For testing purposes
if __name__ == '__main__':
    conn = Connect('localhost', 9999)
    conn.send_command('Set Manip.PV.TSP 155')
    conn.send_command('Get Manip.PV.TSP')
