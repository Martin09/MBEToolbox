import threading
from unittest import TestCase

from virtual_mbe_server_client import Connect

from Virtual_MBE.virtual_mbe_server_host import VirtualMBE, VirtualMBEServer, MBERequestHandler


class TestMBEDebugServer(TestCase):
    """
    Testing class for the whole virtual mbe server
    """

    def setUp(self):
        """
        Creates a thread for the virtual mbe server, run the server in this thread during the testing
        """
        HOST, PORT = "localhost", 9964
        self.server = VirtualMBEServer((HOST, PORT), MBERequestHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.client = Connect(HOST, PORT)

    def test_server(self):
        """
        Runs the various tests to test that the MBE server is working properly
        """
        # Testing set, floats
        result = self.client.send_command('Set Manip.PV 393.2\n')
        self.assertEqual(result, "OK.")
        # Testing get, floats
        result = self.client.send_command('Get Manip.PV\n')
        self.assertAlmostEqual(float(result), 393.2)

        # Testing pyrometer temperature
        result = self.client.send_command('Get Pyrometer.T')
        self.assertAlmostEqual(float(result), 283.2)

        # Testing set, bools
        result = self.client.send_command('Set Shutter.Al True\n')
        self.assertEqual(result, "OK.")
        # Testing get, bools
        result = self.client.send_command('Get Shutter.Al\n')
        self.assertEqual(result.lower(), 'true')

        # Testing set, strings
        result = self.client.send_command('Set Al.Mode Manual\n')
        self.assertEqual(result, "OK.")
        # Testing get, strings
        result = self.client.send_command('Get Al.Mode\n')
        self.assertEqual(result, 'manual')

        # Testing shutter opening
        result = self.client.send_command('Open Pyrometer')
        self.assertEqual(result, "OK.")
        result = self.client.send_command('Get Shutter.Pyrometer')
        self.assertEqual(result, 'open')

        # Testing shutter closing
        result = self.client.send_command('Close Pyrometer')
        self.assertEqual(result, "OK.")
        result = self.client.send_command('Get Shutter.Pyrometer')
        self.assertEqual(result, 'closed')

        # Testing recipe increment
        result = self.client.send_command('Set this.recipesrunning inc')
        self.assertEqual(result, "OK.")
        result = self.client.send_command('Get this.recipesrunning')
        self.assertEqual(int(result), 1)

        # Testing recipe decrement
        result = self.client.send_command('Set this.recipesrunning dec')
        self.assertEqual(result, "OK.")
        result = self.client.send_command('Get this.recipesrunning')
        self.assertEqual(int(result), 0)

        # Testing waiting
        result = self.client.send_command('Wait 60')
        self.assertEqual(result, "OK.")
        result = self.client.send_command('Get time')
        self.assertEqual(int(result), 60)

    def tearDown(self):
        """
        After testing is finished, shut down the server running in the thread
        """
        self.server.shutdown()
        self.server.server_close()


class TestVirtualMBE(TestCase):
    """
    Testing class for just the virtual mbe by itself (without the server)
    """

    def test_initialize(self):
        with VirtualMBE() as mbe:
            self.assertEqual(mbe.variables['manip.pv'], 200)
            for name in mbe.shutters:
                self.assertEqual(mbe.variables['shutter.' + name], 'closed')

    def test_set(self):
        with VirtualMBE() as mbe:
            self.assertTrue(mbe.set_param('Manip.PV.TSP', 210))
            self.assertEqual(mbe.variables['manip.pv.tsp'], 210)
            self.assertTrue(mbe.set_param('AsCracker.Valve.OP', 99))
            self.assertEqual(mbe.get_param('AsCracker.Valve.OP'), 99)
            self.assertFalse(mbe.set_param('bloop', 220))
            self.assertTrue(mbe.set_param('Shutter.Al', 'Open'))
            self.assertEqual(mbe.variables['shutter.al'], 'open')

    def test_set_strings(self):
        with VirtualMBE() as mbe:
            self.assertTrue(mbe.set_param('Manip.PV.TSP', '210'))
            self.assertEqual(mbe.variables['manip.pv.tsp'], 210)
            self.assertTrue(mbe.set_param('Manip.Mode', 'Manual'))
            self.assertEqual(mbe.variables['manip.mode'], 'manual')
            # Try some weird stuff
            self.assertFalse(mbe.set_param('Manip.Mode', 'pancakes'))
            self.assertFalse(mbe.set_param('Shutter.Al', 'gorilla'))
            self.assertFalse(mbe.set_param('this.recipesrunning', 'apricot'))

    def test_get(self):
        with VirtualMBE() as mbe:
            mbe.variables['manip.pv.tsp'] = 123
            self.assertEqual(mbe.get_param('Manip.PV.TSP'), 123)
            mbe.variables['ga.pv.tsp'] = 456
            self.assertEqual(mbe.get_param('Ga.PV.TSP'), 456)
            mbe.variables['shutter.pyrometer'] = 'open'
            self.assertEqual(mbe.get_param('Shutter.Pyrometer'), 'open')
            self.assertEqual(mbe.get_param('Pyrometer.T'), 90)

    def test_waiting(self):
        with VirtualMBE() as mbe:
            mbe.variables['time'] = 0
            mbe.wait(60)  # Wait 60 seconds
            self.assertEqual(mbe.get_param('Time'), 60)

    def test_do_timestep(self):
        with VirtualMBE() as mbe:
            mbe.timeStep = 1
            mbe.set_param('Manip.PV.Rate', 10)
            mbe.set_param('Manip.PV', 200)
            mbe.set_param('Manip.PV.TSP', 300)
            mbe.wait(60)
            self.assertAlmostEqual(mbe.get_param('Manip.PV'), 210)

            mbe.set_param('Ga.PV.Rate', 10)
            mbe.set_param('Ga.PV', 650)
            mbe.set_param('Ga.PV.TSP', 550)
            mbe.wait(60)
            self.assertAlmostEqual(mbe.get_param('Ga.PV'), 640)

            mbe.set_param('SUKO.OP.Rate', 2)
            mbe.set_param('SUKO.OP', 10)
            mbe.set_param('SUKO.OP.TSP', 20)
            mbe.wait(60)
            self.assertAlmostEqual(mbe.get_param('SUKO.OP'), 12)
