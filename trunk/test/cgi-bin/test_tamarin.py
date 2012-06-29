"""
Tests the utility functions found in tamarin.py.

Created: May 30, 2012
Author: Zach Tomaszewski
"""

import unittest
import sys
import io
import shutil

import cgifactory
import test

sys.path.append(test.SRC_CGI)
import tamarin
from tamarin import TamarinError
from tamarin import printFooter, printHeader, authenticate

class TamarinTest(test.TamarinTestCase):

    def setUp(self):
        """ Save all normal output to memory buffer for tests. """
        sys.stdout = io.StringIO()
        
    def tearDown(self):
        """ Reset output stream. """
        sys.stdout.close()
        sys.stdout = sys.__stdout__ 

    def testPrintPage(self):
        """ printHeader and printFooter work. """
        printHeader()
        print("<p>Hello World.</p>")
        printFooter()
        #print(sys.stdout.getvalue(), file=sys.__stdout__)
        
        output = sys.stdout.getvalue()
        self.assertIn('<html>', output)
        self.assertIn('</html>', output)
        self.assertIn('Hello', output)
        
    def testAuthenticate(self):
        """ Check of user -> True or 'INVALID' error, depending. """
        self.assertTrue(authenticate('johndoe', 'password'))
        self.assertRaisesRegex(TamarinError, 'INVALID_USERNAME',
                               authenticate, 'johndo', 'password')
        self.assertRaisesRegex(TamarinError, 'INVALID_PASSWORD',
                               authenticate, 'johndoe', 'letmein')

    def testAuthenticateNoUsersFile(self):
        """ If USERS_FILE is unopenable -> NO_USERS_FILE. """
        bak = tamarin.USERS_FILE + '.bak'
        try:
            shutil.move(tamarin.USERS_FILE, bak)
            self.assertRaisesRegex(TamarinError, 'NO_USERS_FILE',
                               authenticate, 'johndoe', 'password')
        finally:
            shutil.move(bak, tamarin.USERS_FILE)        
        #[Contents processing and MALFORMED_USERS_FILE tested manually.]

    def testAssignment(self):
        """ Creating an Assignment instance -> works/fails appropriately. """
        self.assertIsInstance(tamarin.Assignment('A01'), tamarin.Assignment)
        self.assertRaisesRegex(TamarinError, 'NO_SUCH_ASSIGNMENT',
                               tamarin.Assignment, 'A54')
        #[FORMAT and DUPLICATE tested manually.]
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    