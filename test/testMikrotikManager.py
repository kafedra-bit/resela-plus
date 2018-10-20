"""
Test for the MikrotikManager
"""
import os
from unittest import TestCase
from resela.backend.managers.MikrotikManager import MikrotikManager
from resela.app import app_init


class TestMikrotikManager(TestCase):
    """ Test class for the mikrotik manager. """

    @classmethod
    def setUpClass(cls):
        # Initialize Resela's Flask app.
        os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
        app_init()

    def setUp(self):
        """ Test setup. """
        self.vlan = 69
        self.cidr = '10.1.4.64/28'

    def tearDown(self):
        """ Test teardown. """
        pass

    def test_static_cidr(self):
        """ Compares cidr with vlan 69 cidr

        Expected result cidr equals self.cidr
        """
        cidr = MikrotikManager.get_cidr_for_subnet(self.vlan)
        self.assertEqual(cidr, self.cidr)

    def test_static_vpn_addresses(self):
        """ Compares local with gateway and remote with vpn user of vlan 69.

        Expected result local equals 10.1.4.65 and remote equals 10.1.4.78
        """
        local, remote = MikrotikManager.vpn_addresses_vlan(self.cidr)
        self.assertEqual(local, '10.1.4.65')
        self.assertEqual(remote, '10.1.4.78')

