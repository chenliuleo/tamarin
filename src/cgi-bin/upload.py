#!python

##
## upload.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 06 Jun 2008.
##
## If given no arguments, will display the upload form.
##
## Otherwise, validates an uploaded source code file, checking that it has a 
## valid file name, valid ASCII contents, isn't too large, etc.
##
## If anything is wrong, it will produce a page explaining what's wrong.
##
## If all is correct, it will confirm that the user wants to submit this 
## uploaded file for grading.
##

import re
from tamarin import *


def main():
  """
  Determine which mode to run in: are we displaying the upload page, or processing
  a submission, or was there an error?
  """
  form = cgi.FieldStorage()
  if not form:
    displayUploadForm()
  elif ('file' in form) and ('pass' in form):
    validateUploadedFile(form)
  else:
    #XXX: You'll get this error if a binary file is uploaded and
    #  Tamarin is running on Windows because, for some reason, the
    #  pass field is then not submitted correctly.
    printHeader('File Upload Error')
    printError('BAD_SUBMITTED_FORM')
    print form;
    printFooter()


def displayUploadForm():
  """
  Displays the form to be used to upload a file.
  """
  printHeader('File Upload')
  print """
<h2>File Upload</h2>  
<form class="html" action="/cgi-bin/upload.py" method="post" enctype="multipart/form-data">
<table>
<tr><td>File (<code><i>Username</i>A##.<i>ext</i></code>):</td><td><input type="file" name="file"></td></tr>
<tr><td>Your password:</td><td><input type="password" name="pass"></td></tr>
<tr><td colspan="2" style="text-align: center;"><input type="submit" value="Upload this file for grading"></td></tr>
</table>
</form>
  """
  printFooter()


def validateUploadedFile(form):
  """
  Processes a file upload.  On an error, reports what went wrong to user.
  Otherwise confirms that the user wants to grade the uploaded file.
  """
  printHeader("File Upload Results")
  try: 
    print '<h2>File Upload Results</h2>'
    result = 'OK'
    late = False
    print '<p>'

    if result == 'OK':
      #get filename and check that file was properly uploaded
      filename = form['file'].filename
      if not filename:
        result = 'NO_FILE_UPLOADED'
      else:
        print '<!--Original filename: ' + filename + '-->'
        filename = stripFilename(filename)
        print '<b>Filename:</b> ' + filename + '<br>'
        filecontents = form.getfirst('file')
    
    #validate filename
    if result == 'OK':
      result = checkFilename(filename)

    #authenticate user
    if result == 'OK':
      #assumes we ran checkFilename, so match will succeed
      match = re.match(UPLOADED_RE, filename)
      assert match
      username = match.group(1)
      username = username.lower()
      assignmentName = match.group(2)
      extension = match.group(3)
      password = form.getfirst('pass')

      print '<b>Username:</b> ' + username + '<br>'
      print '<b>Password:</b>',
      if password: 
        print '*' * len(password) + '<br>'
      else:
        print '[missing]<br>'
      
      result = authenticate(username, password)
    
    #validate assignment
    if result == 'OK':  
      print '<b>Assignment:</b> ' + assignmentName
      try:
        assignment = Assignment(assignmentName)
      except TamarinStatusError, tse:
        result = tse.args[0]

    #confirm extension and initial cap    
    if result == 'OK':  
      #sanity/config check that we'll be able to handle this assignment's submissions
      if assignment.fileExt not in EXT_HANDLERS.keys():
        result = 'UNHANDLED_FILE_EXTENSION'

      #right extension?
      if result == 'OK':
        if extension != assignment.fileExt:
          print '<br><b>Extension:</b> .' + str(extension) + \
                ' (but expected .' + assignment.fileExt + ')'
          result = 'WRONG_EXTENSION'
      
      #initial cap, if required?
      if result == 'OK':
        if EXT_HANDLERS[assignment.fileExt][REQ_INITIAL_CAP] and \
           not re.match(r"^[A-Z]", filename):
          result = 'NO_INITIAL_CAP'
    
    #see if already submitted or graded a submission for this assignment
    # (info grabbed here since needed to determine what to accept late; 
    #  but also used further below for warnings)
    if result == 'OK':
      #check submitted first, reusing filename (without extension) from above
      wildFilename = filename.replace('.', '*.')
      alreadySubmitted = glob.glob(os.path.join(SUBMITTED_ROOT, wildFilename))
      #and now graded
      alreadyGraded = glob.glob(os.path.join(assignment.path, wildFilename))
      #but not all files in graded == a graded submission file if submitted
      #ext is same as grader output file ext, so remove grader output files
      for ag in alreadyGraded[:]: 
        if re.match(GRADED_RE, os.path.basename(ag)):              
          alreadyGraded.remove(ag)   
    
    #determine lateness
    if result == 'OK':
      result = assignment.isLate(comments=True) #add some timestamps in HTML

      if result == 'SUBMISSION_LATE':
        print ' (<i>late</i>)',
        late = True
        result = 'OK'
      elif result == 'SUBMISSION_TOO_LATE':
        print ' (' + VERY_LATE_LABEL + ')',
        late = True
        if SUBMIT_VERY_LATE and not alreadySubmitted and not alreadyGraded:
          #can submit and haven't done so yet
          result = 'OK'
        elif RESUBMIT_VERY_LATE and (alreadySubmitted or alreadyGraded):
          #can resubmit and have already submitted something
          result = 'OK'     
      print '<br>'
      
    #as a kind of lateness: has a human already verified a previous submission?
    if result == 'OK':
      if not RESUMBIT_AFTER_HUMAN and alreadyGraded:
        #check if graded has also been verified
        result = 'OK'
        try:
          for f in alreadyGraded: 
            gradedF = GradedFile(os.path.basename(f))
            if gradedF.humanVerified:
              #oops for student: already verified
              result = 'PREVIOUS_SUBMISSION_VERIFIED'
              break
        except TamarinStatusError, tse:
          result = tse.args[0]

    #grab file contents
    if result == 'OK':
      if not filecontents:
        result = 'EMPTY_FILE'
        
    #check that file contents are plain text (if necessary)
    if result == 'OK':
      if assignment.fileExt and not EXT_HANDLERS[assignment.fileExt][IS_BINARY]:
        try:
          filecontents.decode()
        except UnicodeError:
          #sometimes it's not just a file format problem, but a copy-and-paste thing
          # where a couple odd characters (like quotes and such) come from a word
          # processor.  So this will help students track down where their bad chars are
          # in this case.
          lineCount = 1
          charCount = 1
          for char in filecontents: 
            if ord(char) > 128:
              print "<br><b>First non-ASCII character:</b>: ",
              print "line " + str(lineCount) + ", char " + str(charCount) + "<br>"
              break
            elif char == '\n':  
              #Note: line count only correct for Unix and Windows; not old Mac, etc
              lineCount += 1
              charCount = 1
            else:
              charCount += 1
          result = 'BINARY_FILE'

    print '</p>'
    
    #files often uploaded in binary form from various OSs, so adjust line-endings
    if result == 'OK' and not EXT_HANDLERS[assignment.fileExt][IS_BINARY]:
      filecontents = filecontents.replace('\r\n', '\r')
      filecontents = filecontents.replace('\r', '\n')  #yet \n comes out as 0D0A on Windows

    #display file
    if result == 'OK' or result == 'BINARY_FILE':
      print '<p><b>Uploaded Code:</b></p>'
      print '<pre class="code">'
      if EXT_HANDLERS[assignment.fileExt][IS_BINARY]:
        print '[ <i>binary file format: cannot display contents here</i> ]'
      else:
        #need to prevent disappearing code due to tests looking like html tags
        filedisplay = filecontents.replace('&', '&amp;');
        filedisplay = filedisplay.replace('>', '&gt;');
        filedisplay = filedisplay.replace('<', '&lt;');
        print filedisplay
      print '</pre>'    
      
    #Done, so write file and give submit button
    if result == 'OK':
      #write file (could result in an error, handled as an UNHANDLED_ERROR below)
      uploadedFilename = os.path.join(UPLOADED_ROOT, filename)
      overwrite = glob.glob(uploadedFilename)  #see if file already exists
      outfile = open(uploadedFilename, 'w')
      outfile.write(filecontents)
      outfile.close()

      #give success message
      print '<p>'
      print 'Your code (as shown above) has been uploaded to Tamarin. '
      if overwrite: 
        print '(Doing so overwrote a previously uploaded '\
          'but unsubmitted file of the same name).  '
      print '<i>It has not yet been submitted.</i> '

    #warn if already submitted (and/or graded) this assignment
    if result == 'OK':
      if alreadySubmitted or alreadyGraded:
        print '<p><b><i>Warning:</i></b> You already have '
        if alreadySubmitted:
          print str(len(alreadySubmitted)) + ' file(s) submitted '\
            '(but not yet graded) '
          if alreadyGraded:
            print 'and '
        if alreadyGraded:
          print str(len(alreadyGraded)) + ' file(s) graded '
        print 'for this ' + str(assignment) + ' assignment. '
        submitCount = len(alreadySubmitted) + len(alreadyGraded)
        print 'If you submit this uploaded file, it will be a (resubmission * ' + \
              str(submitCount) + '), and so its final score will be reduced ' + \
              'by -' + str(submitCount * RESUBMISSION_PENALTY) + '.</p>'                                      

    #provide submit button
    if result == 'OK':
      print '<p>If you are ready to officially submit this uploaded file for '\
        'grading, click the button below. </p>'
      print ''
      print '<form action="' + CGI_ROOT + '/submit.py" method="post" class="html">'
      print '<input type="hidden" name="uploaded" value="' + filename + '">'
      print '<input type="submit" value="Submit this file" class="centered">'
      print '</form>'  
    
    if result != 'OK':
      #Encountered an error along the way above, so report it now
      printError(result)
      print '<p>'
      print 'Due to the above error, your uploaded file was not saved. ' \
        'Please <a href="' + CGI_ROOT + '/upload.py">return to '\
        'the upload page</a> and try again.'
      print '</p>'   
     
  except:
    printError('UNHANDLED_ERROR')
  finally: 
    printFooter()


def stripFilename(name):
  """
  A bit of a hack needed for IE7 and other browsers that provide the full path
  rather than just the filename of an uploaded file.
  
  Returns the stripped filename.
  """
  match = re.search(r"([^\\/]+)$", name) #grab the stuff at the end after all slashes
  return match.group(1)


def checkFilename(name):
  """"
  Determines whether name is syntactically correct (eg. UsernameA##.java)
  
  Returns 'OK' if so.  
  Otherwise returns: 
  'INVALID_CHARS', 'BAD_EXTENSION', 'BAD_ASSIGNMENT', 'NO_USER_NAME',
  'USERNAME_NOT_LOWERCASE', or 'BAD_FILENAME'
  
  """
  #Checks all these things one step at a time to give user the most feedback 
  #about exactly what's wrong.
  if (re.search(r"[^\w\.]", name)):
    #contains something other than letter, digit, _, or .
    return 'INVALID_CHARS'
  elif (not re.match(r"\w*\.\w+$", name)):
    #doesn't end in some sort of file extension
    return 'BAD_EXTENSION'
  elif (not re.match(r"\w*A\d\d[a-z]?\.\w+$", name)):
    #filename doesn't end with A##a format
    return 'BAD_ASSIGNMENT'
  elif (not re.match(r"\w+A\d\d[a-z]?\.\w+$", name)):
    #filename doesn't include a class or username before the assignment designator
    return 'NO_USER_NAME'
  elif (not re.match(r"\w[a-z0-9_]+A\d\d[a-z]?\.\w+$", name)):
    #filename doesn't include any lowercase letters in username
    return 'USERNAME_NOT_LOWERCASE'
  elif (not re.match(UPLOADED_RE, name)):
    #sanity check (almost certainly unnecessary at this point, but...)
    return 'BAD_FILENAME'
  else:
    return 'OK'
    


if __name__ == "__main__":
  #running as a script (rather than as imported module)
  main() #call main
