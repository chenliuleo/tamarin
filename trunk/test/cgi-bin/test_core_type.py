"""
Tests the utility functions found in tamarin.py.

Author: Zach Tomaszewski
Created: Jul 02, 2012
"""

import unittest
import sys

import test
sys.path.append(test.SRC_CGI)
import tamarin
from core_type import TamarinError, LatePolicy, Assignment
    
class LatePolicyTest(test.TamarinTestCase):
    """ Tests LatePolicy. """

    def testGoodSpans(self):
        """ Various policies -> correct timespan endpoint. """
        deadline = '20140101-0000'
        tests = {
            ':': '99991231-2359',
            '+:': '99991231-2359',
            '-:': '00000101-0000',
            '20120606-1305:': '20120606-1305',
            '-20120606-1305:': '20120606-1305',
            '5d:': '20140106-0000',
            '-2d:': '20131230-0000',
            '36h65m:': '20140102-1305',
        }
        for policy, endpoint in tests.items():
            late = LatePolicy(policy, deadline)
            self.assertEqual(late.end, endpoint)
    
    def testBadPolicies(self):
        """ Various incorrect policies -> appropriate error. """
        deadline = '20140101-0000'
        tests = {
            '3h4d:': 'INVALID_LATE_POLICY',
            '0d:': 'INVALID_LATE_POLICY.*Parsable',
            ':=': 'INVALID_LATE_POLICY',            
        }
        for policy, error in tests.items():
            self.assertRaisesRegex(tamarin.TamarinError, error, 
                                   LatePolicy, policy, deadline)

    def testGradeAdjustment(self):
        """ Grade adjusts properly based on various rules. """
        deadline = '20140101-0000'
        score = 30
        total = 50
        tests = {
            (':', '20140102-0000'): 0,
            (':-20', '20140102-0000'): -20,  #one day late
            (':-40', '20140102-0000'): -40,  #not capped at 0
            (':-50%', '20140102-0000'): -25,
            (':-50$', '20140102-0000'): -15,
            (':-10$/1d', '20140102-0000'): -3,
            (':-10$/1d', '20140101-2359'): -3,
            (':-10$/1d', '20140102-0001'): -6,
            (':-10$/48h', '20140103-0000'): -3,
            (':-10$/1d24h', '20140103-0000'): -3,
            (':-10$/1d23h60m', '20140103-0000'): -3,
            (':-10$/1d', '20140103-0000'): -6,
            (':-10$/1d', '20140103-0001'): -9,
            ('-:+10$/1d', '20131231-2300'): 0,  #early
            ('-:+10$/1d', '20131231-0000'): +3,
            ('-:+10$/1d', '20131230-2300'): +3,
            ('-:+10$/1d', '20131230-0000'): +6,
            ('+5d:-1/1d', '20140104-0000'): -3,
            ('+5d:-1/1d', '20140108-0000'): -5, #capped at end of policy
            ('-5d:+1/1d', '20131230-0000'): +2,
            ('-5d:+1/1d', '20131223-0000'): +5,
        }
        for (policy, timestamp), gradeAdj in tests.items():
            late = LatePolicy(policy, deadline)
            self.assertEqual(late.getGradeAdjustment(score, total, timestamp), 
                             gradeAdj)
        
        late = LatePolicy('+:-10$/1d', deadline)  #$ to % on non-numeric
        self.assertEqual(late.getGradeAdjustment('ERR', 100, '20140105-0000'), 
                             -40)

class AssignmentTest(test.TamarinTestCase):
    """ Tests Assignment. """

    def testAssignment(self):
        """ Creating an Assignment instance -> works/fails appropriately. """        
        self.assertIsInstance(Assignment('A01'), Assignment)
        self.assertRaisesRegex(TamarinError, 'NO_SUCH_ASSIGNMENT',
                               Assignment, 'A54')
        #[FORMAT and DUPLICATE tested manually.]

    def testLateOffset(self):
        """ Makes sure offsets from A01's deadline are correct. """
        # vs: A01-20380119-0314
        tests = {
            '20380119-0314': '-0d 0h 00m',
            '20380119-0315': '+0d 0h 01m',
            '20380118-0211': '-1d 1h 03m',
            '20380119-0414': '+0d 1h 00m',            
        }
        for stamp, offset in tests.items():
            a = Assignment('A01')
            self.assertEqual(a.getLateOffset(stamp), offset)
            
    def testGetPolicy(self):
        a = Assignment('A01')
        a.due = '20140615-0000'
        early1 = LatePolicy('-3d:+10', a.due)
        early2 = LatePolicy('-1d:+5', a.due)
        late1 = LatePolicy('+1d:-15', a.due)
        late2 = LatePolicy('+2d:-30', a.due)
        tests = {
            ('20140614-0000', None): None,  #no polices
            ('20140616-0000', None): None,
            ('20140614-1200', (late1, late2)): None,  #early
            ('20140614-1200', (late2,)): None,
            ('20140614-1200', (early1,)): early1,
            ('20140614-1200', (early1, early2, late1)): early2,
            ('20140610-1200', (early1, early2, late1)): early1,
            ('20140615-1200', (early1, early2)): None, #late
            ('20140615-1200', (early1,)): None,
            ('20140615-1200', (early1, late1)): late1,
            ('20140616-1200', (early1, late1)): late1,
            ('20140616-1200', (early1, late1, late2)): late2,
            ('20140619-1200', (early1, late1, late2)): late2,
        }
        for (timestamp, policies), expected in tests.items():
            a.policies = list(policies) if policies else None
            self.assertEqual(a.getPolicy(timestamp), expected)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    