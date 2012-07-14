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

    def createFile(self, dir, name, contents):
        """ Puts given contents into a file with given name in given dir. """
        with open(os.path.join(dir, name), 'w') as file:
            file.write(contents) 

    def testDefault(self):
        """ No args given -> login form. """
        form = cgifactory.post()
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('View Submissions', response)
        self.assertNotIn('Tamarin Error', response)

    def testEmptyView(self):
        """ Login -> view of no assignments. """
        form = cgifactory.post(**self.fields)
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('John Doe', response)
        self.assertIn('Not yet submitted', response)
        self.assertNotIn('Tamarin Error', response)

    def testSubmittedOnly(self):
        """ Login -> view includes a submitted-only file. """
        self.createFile(tamarin.SUBMITTED_ROOT, 
                        'JohndoeA01-20200606-1200.java', "submitted content")
        form = cgifactory.post(**self.fields)
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('John Doe', response)
        self.assertIn('Not yet graded', response)
        self.assertNotIn('Tamarin Error', response)

    def testSubmittedOnlyView(self):
        """ View of single submitted file -> displays content. """
        self.createFile(tamarin.SUBMITTED_ROOT, 
                        'JohndoeA01-20200606-1200.java', "submitted content")
        form = cgifactory.post(submission='JohndoeA01-20200606-1200.java',
                               **self.fields)
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('submitted content', response)
        self.assertNotIn('Tamarin Error', response)
        
    def testGraded(self):
        """ Login -> view includes a graded file. """
        self.createFile(Assignment('A01').path, 
                        'JohndoeA01-20200606-1300.java', "graded content")
        self.createFile(Assignment('A01').path, 
                        'JohndoeA01-20200606-1300-3-H.txt', "grader output")
        form = cgifactory.post(**self.fields)
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('John Doe', response)
        self.assertIn('<b>Grade:</b> 3', response)
        self.assertNotIn('Tamarin Error', response)

    def testGraded(self):
        """ View of single graded file -> displays content. """
        self.createFile(Assignment('A01').path, 
                        'JohndoeA01-20200606-1300.java', "graded content")
        self.createFile(Assignment('A01').path, 
                        'JohndoeA01-20200606-1300-3-H.txt', 
                        '<div class="grader">grader output</div>')
        form = cgifactory.post(submission='JohndoeA01-20200606-1300.java',
                               **self.fields)
        response = self.query(view.main, form)
        #print(response)
        self.assertIn('graded content', response)
        self.assertIn('grader output', response)
        self.assertNotIn('Tamarin Error', response)
            

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
    