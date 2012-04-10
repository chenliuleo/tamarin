#!python

##
## gradepipe.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 12 Aug 2008.
##
## Grades submitted assignments, one at a time, until the submit queue 
## is empty.
##
## In order to conserve resources, dumps its PID into the GRADEPIPE_ACTIVE
## file.  If this file does not exist, gradepipe is not already running.
## (Note that it may still be disabled/turned off, or may have been terminated 
## externally/abnormally during its last run.)
##
## If the GRADEPIPE_ACTIVE exists, just adds new submissions to the SUBMITTED
## folder, and they'll get graded by the already running gradepipe.
##
## Gradepipe is usually started by submit.py in response to an assignment
## submission.  However, it will also work started directly, which is
## handy for quick offline grading.
##
## Usually gradepipe prints out the details of what it's doing to stdout.
## However, if you want it to run silently (except for really big errors),
## give it 'silent' as a command line argument
##
## Additionally, you can give it any string as a command line argument
## and it will only grade files containing that string. 
##

from tamarin import *
import gradecore        #part of tamarin

import os               #in order to grab PID


def main():
  verbose = True;
  gradeOnly = None;

  #process command line args (skipping name of script)
  for arg in sys.argv[1:]:
    if arg == 'silent':
      verbose = False  #turn off verbose output
    else:
      gradeOnly = arg  #takes only last one 
  
  
  if os.path.exists(GRADEPIPE_ACTIVE):
    #already running, so quit
    if verbose:
      print "Another instance is already running, so quitting..."
    return  
  
  #STARTUP
  try: 
    if verbose:
      print "Gradepipe started. ",

    #first, dump PID into file
    outfile = open(GRADEPIPE_ACTIVE, 'w')
    outfile.write(str(os.getpid()))
    outfile.close()
    if verbose:
      print "(PID dumped to file)"
       
  except:
    print "ERROR: Could not start (could not dump PID to file)."
    traceback.print_exc(None, sys.stdout)
    return
    
  #GRADING LOOP
  try:    
    #loop over submitted files as long as there are more to grade
    # and we're capable of grading them (no errors)
    gradedCount = 0
    badfiles = []
    submitted = getSubmittedFilenames(gradeOnly)
    while submitted:
      #remove any badfiles from refreshed/full submitted list
      while submitted and submitted[0] in badfiles:
        submitted.remove(submitted[0])

      if not submitted: 
        #empty after removing bad files
        break
        
      #pass next file to gradecore (which will remove the file from SUBMITTED dir)
      verbosity = gradecore.CONSOLE if verbose else gradecore.SILENT
      if verbose:
        print
      result = gradecore.grade(os.path.basename(submitted[0]), verbosity)
      if result == 'DONE':
        gradedCount += 1
      else:
        badfiles.append(submitted[0])

      submitted = getSubmittedFilenames(gradeOnly)
    
    #done looping
    if verbose:
      print
      print str(gradedCount) + " files graded"
      if badfiles:
        print str(len(badfiles)) + " files could not be graded."
    
  except:
    print
    print "Gradepipe CRASHED unexpectedly!"
    print
    traceback.print_exc(None, sys.stdout)
    #and now try to clean up anyway
     
  #CLEAN UP 
  try:
    if verbose:
      print
      print "Gradepipe stopped. ",

    #remove PID file
    os.remove(GRADEPIPE_ACTIVE)
    if verbose:
      print "(PID file removed)"
      
  except:
    print "WARNING: Could not clean up PID file."
  
  if verbose:
    print "Gradepipe DONE."
    
    

if __name__ == "__main__":
  #running as a script (rather than as imported module)
  main() #call main

