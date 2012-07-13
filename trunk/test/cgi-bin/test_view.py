"""
Tests view.py.

Author: Zach Tomaszewski
Created: Jun 2, 2012
"""
import unittest
import glob
import os
import sys

import cgifactory
import test

sys.path.append(test.SRC_CGI)
import tamarin
from core_type import Assignment
import view

class ViewTest(test.TamarinTestCase):
    
    def setUp(self):
        self.fields = {'user': 'johndoe', 'pass': 'password'}
            
    def tearDown(self):
        """ Clean any stub files dropped during test. """
        files = glob.glob(os.path.join(Assignment('A01').path, '*'))
        files.extend(glob.glob(os.path.join(tamarin.SUBMITTED_ROOT, '*')))
        for file in files:
            os.remove(file)

    def createFile(dir, name, contents):
        """ Puts given contents into a file with given name in given dir. """
        with open(os.path.join(dir, name)) as file:
            file.write(contents) 

    def testDefault(self):
        """ No args given -> login form. """
        form = cgifactory.post()
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('View Submissions', response)                

    def testEmptyView(self):
        """ Login -> view of no assignments. """
        form = cgifactory.post(**self.fields)
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('John Doe', response)
        self.assertIn('Not yet submitted', response)

      

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    