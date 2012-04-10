#!python

##
## submit.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 01 Aug 2008.
##
## Given an uploaded file, submit.py then takes that uploaded
## file as a submission.  
##
## If grading is then possible, it will go ahead
## and start the grading process by launching the appropriate grading system.
##
## If anything goes wrong along the way, reports to what happened to user.
##

from tamarin import *
import subprocess     #for spawning a separate gradepipe process


def main():
  printHeader("Submission and Grading Results")
  try: 
    print '<h2>Submission and Grading Results</h2>'
    form = cgi.FieldStorage()
    result = 'OK'
    late = False
    print '<p>'

    #check that submitted form was correct with all needed details
    if ('uploaded' not in form):
      result = 'BAD_SUBMITTED_FORM'

    #grab and print username and assignment (validating filename format)
    if result == 'OK':
      filename = form.getfirst('uploaded')
      match = re.match(UPLOADED_RE, filename)
      if not match:
        result = 'BAD_SUBMITTED_FORM'

      if result == 'OK':      
        print '<b>Username:</b> ' +  match.group(1) + '<br>'
        print '<b>Assignment:</b> ' + match.group(2) + '<br>'
    
    #SUBMIT
    #check that uploaded file exists
    if result == 'OK':
      uploadedFilename = os.path.join(UPLOADED_ROOT, filename)
      if not os.path.exists(uploadedFilename):
        result = 'NO_UPLOADED_FILE'
    
    #create submitted filename and move uploaded file to submitted location
    if result == 'OK':
      currentStamp = convertTimeToTimestamp(datetime.datetime.now())
      submittedFilename = filename.replace('.', '-' + currentStamp + '.')
      submittedFilename = os.path.join(SUBMITTED_ROOT, submittedFilename)
      shutil.move(uploadedFilename, submittedFilename)
      print '<b>File submitted at:</b> ' + currentStamp + '<br>'
      #YAY!  Submission is successful, and user is DONE
      print '<i>--Submission completed successfully--</i>'
      print '</p>'
      result = 'DONE'

    #now start grading
    if result == 'DONE':
      #In future, might be able to grade in real time (at least as option).
      #For now, just start the grade pipe (and print results).
      startGradePipe()      
    
    if result != 'DONE':
      #Encountered an error along the way above, so report it now
      printError(result)
      print '<p>'
      print 'Due to the above error, your file was <i>not</i> succesfully submitted.'
      print 'You may want to try again '
      print 'or else contact ' + ADMIN_EMAIL + ' about the error you encountered.'
      print '</p>'   

  except:
    printError('UNHANDLED_ERROR')
  finally: 
    printFooter()


def startGradePipe(printStatus=True):
  """
  If not already running, spawns a new instance of the grade pipe.  
  (See gradepipe.py for more.)
  
  Returns True if the gradepipe was actually started; False if not 
  (usually because it's already running or because it's been disabled.)
  
  If printStatus=True, prints a message concerning the initial state 
  of the grade pipe (ie, already running or whether it was just started).
  """
  active = False
  if printStatus:
    print '<p><b>Grading:</b> '
  
  if os.path.exists(GRADEPIPE_DISABLED):
    if printStatus:
      print 'Queued.</p>'
      print '<p>The grade pipe is currently disabled. '\
        'Your submission has been added to the end of grading queue, '\
        'to be compiled and/or graded once the grade pipe is activated again.</p>'  

  elif os.path.exists(GRADEPIPE_ACTIVE):
    #gradepipe already running
    if printStatus:
      print 'Queued.</p>'
      print '<p>The grade pipe is already running, grading earlier '\
        'submissions than yours.  Your submission has been added to the '\
        'end of grading queue. </p>'
  
  else:
    #gradepipe not running yet, so start it up.
    #first, make sure the redirected input file exists
    open(GRADEPIPE_IN, 'w').close()
    #spawn the gradepipe, redirecting in/out to get a clean separation
    subprocess.Popen(GRADEPIPE_CMD.split(), 
                     stdin=open(GRADEPIPE_IN), 
                     stdout=open(GRADEPIPE_OUT, 'w'), 
                     stderr=open(GRADEPIPE_OUT, 'w'))
    #let end of process close the files                     
    active = True

    if printStatus:
      print 'Started.</p>'
      print '<p>The grade pipe has been started in order to grade '\
        'your submission, which is at the front of the grading queue.</p>'
    
  if printStatus:
    print '<p>See <a href="' + CGI_ROOT + '/status.py">status</a> '\
      'for more on the current state of the submitted/grading queue.</p>'

  return active



if __name__ == "__main__":
  #running as a script (rather than as imported module)
  main() #call main
