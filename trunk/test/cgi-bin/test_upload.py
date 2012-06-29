"""
Created on Jun 2, 2012

@author: Zach Tomaszewski
"""
import unittest
import sys
import cgifactory
import test

sys.path.append(test.SRC_CGI)
import upload

class UploadTest(test.TamarinTestCase):
    
    def setUp(self):
        self.filenames = {'file': 'JohndoeA01.txt'}
        self.fields = {'pass': 'password', 'file': 'short file contents here'}

    def testDefault(self):
        """ No arguments -> print an input form."""
        form = cgifactory.get()
        response = self.query(upload.main, form)
        #print(response)
        self.assertIn('<form', response)
        
    def testBadForm(self):
        """ Required form fields are missing -> bad form message. """
        #only a password
        form = cgifactory.get(**{'pass': 'only'})
        response = self.query(upload.main, form)
        #print(response)
        self.assertIn('BAD_SUBMITTED_FORM', response)
        
    def testMissingFilename(self):
        """ Submitted file contents but not name -> NO_FILE. """
        form = cgifactory.post(**self.fields)
        response = self.query(upload.main, form)
        #print(response)      
        self.assertIn('NO_FILE_UPLOADED', response)
        
    def testBadFilename(self):
        """ Filename is malformed -> appropriate error. """
        tests = {
            'Johndoe?A01.txt': 'INVALID_CHARS', 
            'JohndoeA01': 'BAD_EXTENSION',
            'JohndoeA01.': 'BAD_EXTENSION',
            'Johndoea01.txt': 'BAD_ASSIGNMENT',
            'JohndoeA1.txt': 'BAD_ASSIGNMENT',
            'JohndoeA01bc.txt': 'BAD_ASSIGNMENT',
            'A01.txt': 'NO_USER_NAME', 
            'JohnDoeA01.txt': 'USERNAME_NOT_LOWERCASE'
        }
        for name, error in tests.items():
            self.filenames['file'] = name
            form = cgifactory.post(filenames=self.filenames, **self.fields)
            response = self.query(upload.main, form)
            #print(response)      
            self.assertIn(error, response)
                    
    def testGoodFilenames(self):
        """ Certain complex filenames -> accepted. """
        self.assertTrue(upload.checkFilename('JohndoeX01.txt'), 
                        "Accepts non-A caps.")
        self.assertTrue(upload.checkFilename('JohndoeA01.tar.gz'), 
                        "Accepts long/multiple extensions.")
    
    def testValidSubmission(self):
        """ A valid submission -> successfully processed. """
        # FIXME: implement
        pass
    
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    