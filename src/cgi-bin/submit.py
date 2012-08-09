#!python3

## submit.py 

"""
Given an previously uploaded file, processes that file as a submission.  

Should be given the name of a file already saved in UPLOADED_ROOT.
Will then timestamp the file and move it into SUBMITTED_ROOT.
If grading is then possible, it will go ahead and start the grading pipeline.

If anything goes wrong along the way, reports to what happened to user.

Part of Tamarin, by Zach Tomaszewski.  
Created: 01 Aug 2008.
"""

import cgi
import os
import re
import shutil
import subprocess

import tamarin
from core_type import TamarinError

def main(form=None):
    if not form:
        form = cgi.FieldStorage()
    tamarin.printHeader("Submission and Grading Results")
    print('<h2>Submission and Grading Results</h2>')
    try: 
        print('<p>')

        # check that submitted form was correct with all needed details
        if 'uploaded' not in form:
            raise TamarinError('BAD_SUBMITTED_FORM', "Missing uploaded field.")
        
        # validate filename format, printing username and assignment
        filename = form.getfirst('uploaded')
        match = re.match(tamarin.UPLOADED_RE, filename)
        if not match:
            raise TamarinError('BAD_SUBMITTED_FORM', "Wrong filename format.")
              
        print('<b>Username:</b> ' +  match.group(1) + '<br>')
        print('<b>Assignment:</b> ' + match.group(2) + '<br>')
    
        # check that uploaded file really exists
        uploadedFilename = os.path.join(tamarin.UPLOADED_ROOT, filename)
        if not os.path.exists(uploadedFilename):
            raise TamarinError('NO_UPLOADED_FILE')
    
        # create submitted filename and move uploaded file to submitted folder
        currentStamp = tamarin.convertTimeToTimestamp()
        submittedFilename = filename.replace('.', '-' + currentStamp + '.', 1)
        submittedFilename = os.path.join(tamarin.SUBMITTED_ROOT, 
                                         submittedFilename)
        shutil.move(uploadedFilename, submittedFilename)
        print('<b>File submitted at:</b> ' + currentStamp + '<br>')
        # Yay!  Submission is successful, and user is DONE
        print('<i>--Submission completed successfully--</i>')
        print('</p>')

        # now start grading...
        # (In future, might have option to grade in real time.  For now, 
        #  just start the grade pipe and print results.)
        startGradePipe()      
    
    except TamarinError as err:
        tamarin.printError(err)
        print('<p>')
        print("Due to the above error, your file was <i>not</i> successfully "
            "submitted. You may want to try again or else contact your " 
            "Tamarin administrator ")
        if tamarin.ADMIN_EMAIL:
            print("(" + tamarin.ADMIN_EMAIL + ")")
        print(" with the details of the error you encountered.")
        print('</p>')   
    except:
        tamarin.printError('UNHANDLED_ERROR')
    finally: 
        tamarin.printFooter()


def startGradePipe(printStatus=True):
    """
    If not already running, spawns a new instance of the grade pipe as a
    separate process. (See gradepipe.py for more.)
    
    Returns True if the gradepipe was actually started; False if not 
    (usually because it's already running or because it's been disabled.)
    
    If printStatus=True, prints a message concerning the initial state 
    of the grade pipe (ie, already running or whether it was just started).
    """
    active = False
    if printStatus:
        print('<p><b>Grading:</b>')
  
    if os.path.exists(tamarin.GRADEPIPE_DISABLED):
        if printStatus:
            print('Queued.</p>')
            print('<p>The grade pipe is currently disabled. '
                  'Your submission has been added to the end of grading '
                  'queue, to be compiled and/or graded once the grade pipe '
                  'is activated again.</p>')

    elif os.path.exists(tamarin.GRADEPIPE_ACTIVE):
        # gradepipe already running
        if printStatus:
            print('Queued.</p>')
            print('<p>The grade pipe is already running, grading earlier '
                  'submissions than yours.  Your submission has been ' 
                  'added to the end of grading queue. </p>')
    
    else:
        # gradepipe not running yet, so start it up.
        # First, make sure the redirected input file exists
        open(tamarin.GRADEPIPE_IN, 'w').close()
        # Spawn the gradepipe, redirecting in/out to get a clean separation
        # End of process will close the files.
        # NOTE: If you get a crash complaining about this line (probably
        # only the last "stderr" line of which is printed in the error 
        # message), check that your GRADEPIPE_CMD is valid.
        subprocess.Popen(tamarin.GRADEPIPE_CMD.split(), 
                         stdin=open(tamarin.GRADEPIPE_IN), 
                         stdout=open(tamarin.GRADEPIPE_OUT, 'w'), 
                         stderr=open(tamarin.GRADEPIPE_OUT, 'w'))
        active = True
        if printStatus:
            print('Started.</p>')
            print('<p>The grade pipe has been started in order to grade '
                  'your submission, which is at the front of the grading '
                  'queue.</p>')
    
    if printStatus:
        print('<p>See <a href="' + tamarin.CGI_URL + 'status.py">status</a> ' +
              'for more on the current state of the submitted/grading ' 
              'queue.</p>')
        
    return active


if __name__ == "__main__":
    #running as a script (rather than as imported module)
    main()
