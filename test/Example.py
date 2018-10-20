"""
Test template for unittests.

Use this example class to build new test classes for unit tests.
"""
from unittest import TestCase


class Example(TestCase):
    """ Example test for test framework. """

    def setUp(self):
        """ Test setup. """
        self.x = 5
        self.y = 5

    def tearDown(self):
        """ Test teardown. """
        pass

    def test_compare_x_y(self):
        """ Compares x with y.

        Expected result x equals y.
        """
        self.assert_(self.x == self.y)

