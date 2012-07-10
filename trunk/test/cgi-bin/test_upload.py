"""
Tests upload.py.

Author: Zach Tomaszewski
Created: Jun 2, 2012
"""
import unittest
import os
import os.path
import sys

import cgifactory
import test

sys.path.append(test.SRC_CGI)
import tamarin
import upload

class UploadTest(test.TamarinTestCase):
    
    def setUp(self):
        self.filenames = {'file': 'JohndoeA01.java'}
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
        
    def testEmptyFile(self):
        """ No file contents -> EMPTY_FILE. """
        self.fields['file'] = ''
        form = cgifactory.post(filenames=self.filenames, **self.fields)
        response = self.query(upload.main, form)
        #print(response)      
        self.assertIn('EMPTY_FILE', response)
        
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
            'JohnDoeA01.txt': 'USERNAME_NOT_LOWERCASE',
        
            'JohndoeA01.txt': 'WRONG_EXTENSION',
            'johndoeA01.java': 'NO_INITIAL_CAP'
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
    
    def testUndefinedType(self):
        dir = 'A92-21121212-1212-quark'
        try:
            os.mkdir(os.path.join(tamarin.GRADED_ROOT, dir))
            self.filenames['file'] = 'JohndoeA92.java'
            form = cgifactory.post(filenames=self.filenames, **self.fields)
            response = self.query(upload.main, form)
            #print(response)      
            self.assertIn('UNDEFINED_TYPE', response)            
        finally:
            os.rmdir(os.path.join(tamarin.GRADED_ROOT, dir))
            
    def testBinaryFile(self):
        """ Binary data on a plain text assignment -> BINARY_FILE. """
        self.fields['file'] = chr(0xB0)  #fine for UTF-8, but not ascii
        tamarin.SUBMISSION_TYPES['java'].encoding = 'ascii'
        try:
            form = cgifactory.post(filenames=self.filenames, **self.fields)
            response = self.query(upload.main, form)
            #print(response)      
            self.assertIn('BINARY_FILE', response)
        finally:
            tamarin.SUBMISSION_TYPES['java'].encoding = 'utf-8'
    
    def testValidSubmission(self):
        """ A valid submission -> successfully processed. """
        outputPath = os.path.join(tamarin.UPLOADED_ROOT, 
                                  self.filenames['file'])
        try:
            form = cgifactory.post(filenames=self.filenames, **self.fields)
            response = self.query(upload.main, form)
            print(response)      
            self.assertIn('<input type="submit"', response)
            self.assertTrue(os.path.exists(outputPath), outputPath)
        finally:
            #clean up
            if os.path.exists(outputPath):
                os.remove(outputPath)      
    
    # To test manually:
    # * Lateness
    # * Uploading with already submitted, graded, and/or verified    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    