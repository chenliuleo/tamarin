#!python3

## status.py 

"""
Prints various details about Tamarin's status: current time, 
state of the grading queue, etc.

Part of Tamarin, by Zach Tomaszewski.  
Created: 28 Aug 2008.
"""

import datetime
import glob
import os

import tamarin

def main():
    """
    Displays current time, grading method, gradepipe status, number of
    uploaded (but unsubmitted files), and the submitted queue.
    """
    tamarin.printHeader("Tamarin Status")
    try: 
        print('<h2>Tamarin Status</h2>')
    
        # current time 
        # (Printed in two different formats as a way for users 
        # to learn how to make sense of Tamarin timestamp format)
        print('<p><b>Current System Time:</b> ')
        now = datetime.datetime.now()
        print(tamarin.convertTimeToTimestamp(now))
        print('&nbsp; (<i>' + now.isoformat(' ') + '</i>)')
        print('</p>')
    
        # uploaded file count
        print('<p><b>Uploaded (but not submitted) file count:</b> ')
        uploaded = glob.glob(os.path.join(tamarin.UPLOADED_ROOT, '*'))
        print(len(uploaded))
        
        # grade pipe status      
        print('<p><b>Gradepipe:</b> ')
        if os.path.exists(tamarin.GRADEPIPE_ACTIVE):
            print('<small>RUNNING</small>')
        else:
            print('<small>OFF</small>')
        if os.path.exists(tamarin.GRADEPIPE_DISABLED):
            print(' <small>(DISABLED)</small>')    
        print('</p>')
        
        # grading queue contents
        print('<p><b>Submitted (but not yet graded) queue:</b> ')
        submitted = tamarin.getSubmittedFilenames()
        if len(submitted) == 0:
            print('[empty]')
        else:
            print('<br>')
            for s in submitted:
                print('<span class="gradequeue">' + os.path.basename(s) + 
                      '</span><br>')
        print('</p>')

    except:
        tamarin.printError('UNHANDLED_ERROR')
    finally: 
        tamarin.printFooter()


if __name__ == "__main__":
    #running as a script (rather than as imported module)
    main() #call main
