
"""
Core helper code for all Tamarin unit-tests.

Includes a superclass for all Tamarin-based unit tests.
If run as a program, runs the full suite of all unit tests.

Author: Zach Tomaszewski
Created: 23 Jun 2012
"""

import unittest
import io
import sys
import cgi
import os
import os.path

#the relative path of the true src/cgi-bin files to be tested 
SRC_CGI = os.path.normpath('../../src/cgi-bin/')

class TamarinTestCase(unittest.TestCase):
    
    def __init__(self, arg):
        super().__init__(arg)
        os.chdir(SRC_CGI)
    
    def query(self, fn, cgi):
        """
        Returns the output from the given fn based on the given CGI query.
        
        Requires a function that takes a CGI object (only) and a 
        valid CGI object argument to pass to it.  Redirects the called
        function's stdout output and returns it as a string.
        """
        sys.stdout = io.StringIO()
        fn(cgi)
        output = sys.stdout.getvalue()
        sys.stdout.close()
        sys.stdout = sys.__stdout__ 
        return output


if __name__ == "__main__":
    unittest.main(argv=['', 'discover'])
        