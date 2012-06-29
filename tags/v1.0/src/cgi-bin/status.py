#!python

##
## status.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 28 Aug 2008.
##
## Prints various details about Tamarin's status: current time, 
## state of the grading queue, etc.
##

from tamarin import *


def main():
  """
  Displays current time, grading method, gradepipe status, number of
  uploaded (but unsubmitted files), and the submitted queue.
  """
  printHeader("Tamarin Status")
  try: 
    print '<h2>Tamarin Status</h2>'
    
    print '<p><b>Current System Time:</b> '
    now = datetime.datetime.now()
    print convertTimeToTimestamp(now),
    print '&nbsp; (<i>' + now.isoformat(' ') + '</i>)'
    print '</p>'
    
    print '<p><b>Uploaded (but not submitted) file count:</b> '
    uploaded = glob.glob(os.path.join(UPLOADED_ROOT, '*'))
    print len(uploaded)

    ##TODO: put grading method here later
    print '<p><b>Gradepipe:</b> '
    if os.path.exists(GRADEPIPE_ACTIVE):
      print '<small>RUNNING</small>'
    else:
      print '<small>OFF</small>'
    if os.path.exists(GRADEPIPE_DISABLED):
      print ' <small>(DISABLED)</small>'    
    print '</p>'
        
    print '<p><b>Submitted (but not yet graded) queue:</b> '
    submitted = getSubmittedFilenames()
    if len(submitted) == 0:
      print '[empty]'
    else:
      print '<br>'
      for s in submitted:
        print '<span class="gradequeue">' + os.path.basename(s) + '</span><br>'
    print '</p>'
      
  except:
    printError('UNHANDLED_ERROR')
  finally: 
    printFooter()


if __name__ == "__main__":
  #running as a script (rather than as imported module)
  main() #call main
  
  