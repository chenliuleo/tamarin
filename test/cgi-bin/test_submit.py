"""
Tests upload.py.

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
import submit

class UploadTest(test.TamarinTestCase):
    
    @classmethod
    def setUpClass(cls):
        """ Turn off gradepipe. """
        open(tamarin.GRADEPIPE_DISABLED, 'w').close()
        
    @classmethod
    def tearDownClass(cls):
        """ Turn gradepipe back on and clear out any/all submitted files. """
        os.remove(tamarin.GRADEPIPE_DISABLED)
        submitted = glob.glob(os.path.join(tamarin.SUBMITTED_ROOT, "*"))
        for file in submitted:
            os.remove(file)
                
    def setUp(self):
        self.file = 'JohndoeA01.java'
        self.testFile = os.path.join(tamarin.UPLOADED_ROOT, self.file)
        with open(self.testFile, 'w') as f:
            f.write("file contents here")        
        
    def tearDown(self):
        if os.path.exists(self.testFile):
            os.remove(self.testFile)
        
    def testBadForm(self):
        """ Required form fields are missing -> bad form message. """
        form = cgifactory.get(upload=self.file)  #should be uploaded=
        response = self.query(submit.main, form)
        #print(response)
        self.assertIn('BAD_SUBMITTED_FORM', response)
        
    def testBadContext(self):
        """ Various context problems -> appropriate message. """
        tests = {
            'A01': 'BAD_SUBMITTED_FORM',
            'JohndoeA99.java': 'NO_UPLOADED_FILE',
        }
        for file, error in tests.items():
            form = cgifactory.get(uploaded=file) 
            response = self.query(submit.main, form)
            #print(response)
            self.assertIn(error, response)

    def testGoodSubmission(self):
        """ Required form fields are missing -> bad form message. """
        #only a password
        form = cgifactory.get(uploaded=self.file) 
        response = self.query(submit.main, form)
        #print(response)
        self.assertIn("Submission completed successfully", response)
        self.assertIn("disabled", response)  # gradepipe was really off?
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    