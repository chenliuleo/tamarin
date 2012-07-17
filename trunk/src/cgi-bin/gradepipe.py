#!python3

## gradepipe.py 

"""
Grades submitted assignments, one at a time, until the submit queue 
is empty.  See core_grade.GradePipe for more.

In order to conserve resources, dumps its PID into the GRADEPIPE_ACTIVE
file.  If this file exists, gradepipe is assumed to already be running.
(Note that may have been terminated externally/abnormally during its last
run, though.)

If the GRADEPIPE_ACTIVE exists, just adds new submissions to the SUBMITTED
folder, and they'll get graded by the already running gradepipe.

Gradepipe is usually started by submit.py in response to an assignment
submission.  However, it will also work started directly by running this
module as a script, which is handy for quick offline grading or debugging.

Gradepipe uses a logger to print out the details of what it's doing to stdout.
To change the default log level of INFO, you can pass one of the following 
as a cmd line argument: debug, info, warning, error, critical.  The last value
given will be used.

Additionally, you can pass any other string as a command line argument
and the gradepipe will only grade files containing that string.

Part of Tamarin, by Zach Tomaszewski.  
Created: 12 Aug 2008.
"""
import sys

import core_grade

def main():
    """
    Processes command line arguments and starts the gradepipe if appropriate.
    """
    logLevel = 'DEBUG';
    gradeOnly = None;

    #process command line args (skipping name of script)
    for arg in sys.argv[1:]:
        if arg.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            logLevel = arg.upper()
        else:
            gradeOnly = arg  #takes only last one   
    core_grade.GradePipe(logLevel=logLevel, gradeOnly=gradeOnly).run()
    

if __name__ == "__main__":
    #running as a script (rather than as imported module)
    main() #call main

