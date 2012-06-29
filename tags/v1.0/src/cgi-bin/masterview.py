#!python

##
## masterview.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 15 Sep 2008.
##
## Allows the administrator to view submitted assignments and change
## grades or add comments through the web interface.
##
## BEWARE: Secure access to this script!
##

from tamarin import *
import displaycore
import submit

def main():
  form = cgi.FieldStorage()
  if not form:
    displayForm()
  else:
    try:
      result = 'OK'
      #modifying a submission
      if 'modify' in form:
        if ('submission' not in form) or ('grade' not in form):
          #may have a comment too, but that can be blank
          printHeader()
          result = 'BAD_SUBMITTED_FORM'
        
        if result == 'OK':
          printHeader("Modified: " + form.getfirst('submission'))
          result = appendComment(form.getfirst('submission'), form.getfirst('comment'),\
                        form.getfirst('grade'), form.getfirst('verify'))
          if result == 'OK':
            result = displaycore.displaySubmission(form.getfirst('submission'), master=True)          
    
      elif 'submission' in form:
        #wants to see a specific submission
        printHeader('Master view: ' + form.getfirst('submission'))
        print '<br>'
        result = displaycore.modifySubmission(form.getfirst('submission'))
       
      elif 'user' in form:
        printHeader('Master view: ' + form.getfirst('user'))
        result = displaycore.displayUser(form.getfirst('user'),
                                          assignment=form.getfirst('assignment'),
                                          brief=form.getfirst('brief'), 
                                          master=True)
      
      elif 'assignment' in form:
        #and without user, or would have been caught above
        printHeader('Master view: ' + form.getfirst('assignment'))
        result = displaycore.displayAssignment(form.getfirst('assignment'), 
                                               form.getfirst('brief'), 
                                               master=True)
                                          
      elif 'strip' in form: 
        printHeader('Master view: stripping ' + form.getfirst('strip'))
        result = stripFiles(form.getfirst('strip'), form.getfirst('only'))

      elif 'verifyAll' in form: 
        printHeader('Master view: verifying' + form.getfirst('verifyAll'))
        result = markAllAsVerified(form.getfirst('verifyAll'))
        
      elif 'startGrader' in form:
        printHeader('Master view: Start Grading Pipeline')
        started = submit.startGradePipe(printStatus=False)
        if started:
          print '<p><br>Grading pipeline started.'
        else:
          print '<p><br>Grader pipeline <b>not</b> started.'
          print 'This is either because it is disabled or is already running.'
        print '<p>See <a href="' + CGI_ROOT + '/status.py">status</a> '\
              'for more.</p>'
        
      else:
        printHeader()
        print '<p><br>You did not select a valid option.</p>'
          
    except:
      result = 'UNHANDLED_ERROR'

    if result != 'OK':
      printError(result)
    
    printFooter()


def displayForm():
  """
  Displays the masterview form.
  """
  printHeader('Tamarin: Masterview')

  #get user list
  users = getUsers()
  users.sort()

  #get assignment list
  assignments = glob.glob(os.path.join(GRADED_ROOT, 'A*'))
  assignments.sort()
  for i in range(len(assignments)):
    assign = re.search(r"(A\d\d\w?)-\d{8}-\d{4}", assignments[i])
    if not assign:
      result = 'BAD_ASSIGNMENT_DIR_FORMAT'
      break  #so that we only print one error message
    assignments[i] = assign.group(1) #grab short form of A
    
  print """
<h2>Masterview</h2>  
<div class="masterview">
<h3>Views</h3>
<form action="/cgi-bin/masterview.py" method="get">
Assignment: 
  """
  print '<select name="assignment">'
  for a in assignments:
    print '<option>' + a + '</option>'
  print '</select>'
  
  print """
<select name="brief">
<option value="1" selected>Brief</option>
<option value="">Full</option>
</select>
<input type="submit" value="View">
</form>

<form action="/cgi-bin/masterview.py" method="get">
User:
<select name="user"><option></option>
  """
  for u in users:
    print '<option>' + u + '</option>'
  print '</select>'
  
  print '<select name="assignment"><option value="">(All assignments)</option>'
  for a in assignments:
    print '<option>' + a + '</option>'
  print '</select>'
  
  print """
<select name="brief">
<option value="1" selected>Brief</option>
<option value="">Full</option>
</select>
<input type="submit" value="View">
</form>
</div>
<br>
<div class="masterview">
<h3>Tools</h3>
<form action="/cgi-bin/masterview.py" method="get">
<h4>Mark as human-verified</h4>
<p>Mark all graded files in: 
  """
  print '<select name="verifyAll"><option></option>'
  for a in assignments:
    print '<option>' + a + '</option>'
  print '</select>'
  
  print """
<input type="submit" value="Verify"></p>
</form>

<form action="/cgi-bin/masterview.py" method="post" enctype="multipart/form-data">
<h4>Start Grader</h4>
<p>
Normally, each submission is graded as it comes in.  However, when multiple Tamarin 
instances share the same pipeline, a submission may temporarily go ungraded if
it is submitted while the pipeline is currently grading submissions for another 
Tamarin instance.  Though this submission will automatically be graded next time 
another student in the same instance submits a file, you may want it graded right now.
<p>
If this should happen--the pipeline is OFF but submissions are
still sitting in the grading queue, as shown by 
"""
  print '<a href="' + CGI_ROOT + '/status.py">status</a>--'
  print """
you can:
<input type="hidden" name="startGrader" value="1">
<p>
<input type="submit" value="Start Grader">
</p>
</form>

<form action="/cgi-bin/masterview.py" method="get">
<h4>Strip timestamps from filenames</h4>
  """
  print '<p>From assignment/directory: '
  print '<select name="strip"><option>submitted</option>'
  for a in assignments:
    print '<option>' + a + '</option>'
  print '</select>'
  print '&nbsp; (copying into ' + STRIPPED_ROOT + ')'
  print '<p>Strip only files with names containing (blank for all):'
  print '<input type="text" name="only">'
  print """
<p><input type="submit" value="Strip"></p>
</form>
</div>
  """
  printFooter()


def appendComment(filename, comment, newGrade, verified):
  """
  Appends the given comment to the grader file for filename and changes
  its grade to newGrade.  If verfied, adds "-H" to filename; otherwise, 
  removes it.  Comment can be None.
  """
  #get the grader file
  try:
    result = 'OK'
    toEdit = GradedFile(filename)
    
    #modify the file
    if result == 'OK':
      #read in
      inFile = open(toEdit.graderPath, 'r')
      contents = ""
      for line in inFile:
        if '<p><b>Grade:</b>' in line:
          #replace this line with new grade, prepending comment first
          if comment:
            contents += '<div class="comment"><p><b>' + TA_COMMENT + '</b><br>\n'
            #preserve raw formatting.  And we don't know where it came from, so std-ize
            comment = comment.replace('\r\n', '\n');
            comment = comment.replace('\r', '\n');
            contents += comment.replace('\n', '<br>\n')
            contents += '\n</p></div>\n'
          contents += '<p><b>Grade:</b> ' + newGrade + '</p>\n'
        else:
          contents += line
      inFile.close()
      
      #dump file contents back into grader file
      outFile = open(toEdit.graderPath, 'w')
      outFile.write(contents)
      outFile.close()
      
      #now rename the grader file
      match = re.match(GRADED_RE, toEdit.graderFilename)
      assert match, "Grader filename malformed in masterview.appendComment."
      if toEdit.humanVerified:
        #want to ground grade in larger expression so we don't accidently
        #change A number or part of timestamp if grade is an integer
        oldGrade = match.group(4) + "-H."
      else:
        oldGrade = match.group(4) + "."
      
      #add verification -H, if necessary
      newGrade = str(newGrade)
      if verified:
        newGrade += "-H"
      newGrade += "."
      
      newGraderPath = toEdit.graderPath.replace(oldGrade, newGrade)
      
      shutil.move(toEdit.graderPath, newGraderPath)
      
  except TamarinStatusError, tse:
    result = tse.args[0]
  except EnvironmentError:
    #possible IO problems
    result = 'COULD_NOT_READ'
  
  return result


def markAllAsVerified(assignName, silent=False):
  """
  Marks all graded files in the given assignment directory as human-verified.
  
  If silent is True, won't print any feedback.
  
  Returns status.
  """
  result = 'OK'
  try:
    assign = Assignment(assignName)
    files = glob.glob(os.path.join(assign.path, '*.' + GRADER_OUTPUT_FILE_EXT))
    
    toMark = []
    for f in files:
      match = re.match(GRADED_RE, os.path.basename(f))
      if match and not match.group(5):
        #has no -H yet
        toMark.append(f)
    
    if not silent:
      print '<br><p class="strip">Found ' + str(len(files)) + ' grader output files;'
      print str(len(toMark)) + ' of them need to be marked.'
      print '<p class="strip"><b>Marked as human verified:</b><br>'

    toMark.sort()
    for m in toMark:
      match = re.match(GRADED_RE, os.path.basename(m))
      assert match, "Bad graded filename format: " + os.path.basename(m)
      newF = os.path.join(assign.path, match.group(1) + match.group(2) + '-' +
                          match.group(3) + '-' + match.group(4) + '-H.' +
                          match.group(6))
      shutil.move(m, newF)

      if not silent: 
        print os.path.basename(m) + ' &nbsp; ==&gt; &nbsp; ' + \
              os.path.basename(newF) + '<br>'
    
    if not silent:
      print '</p><p class="strip"><b>Done.</b></p>'
         
  except TamarinStatusError, tse:  
    result = tse.args[0]
  except AssertionError:
    result = 'BAD_SUBMITTED_FORM'
  return result
  

def stripFiles(directory, only=None):
  """
  Goes through the given directory (which must either be an assignment of the form A##
  or 'submitted'), copying each .java file into STRIPPED_ROOT, removing the timestamps
  from the names.  Copies in order of timestamp, so later submissions will overwrite earlier
  ones and you'll be left with the latest version.
  
  If only is set, will only strip/copy files with names (but not extensions) 
  containing that string.
  
  Returns returns status (including 'BAD_SUBMITTED_FORM' if input is incorrectly formatted).
  """
  result = 'OK'

  #check input and figure out which full directory to process
  match = re.match(r"A\d\d\w?$", directory)
  if match:
    assign = Assignment(match.group())
    toStrip = assign.path
  elif directory == 'submitted':
    toStrip = SUBMITTED_ROOT
  else:
    result = 'BAD_SUBMITTED_FORM'

  if result == 'OK':
    #get file glob of files to strip, and sort
    if (only):
      files = glob.glob(os.path.join(toStrip, '*' + only + '*.java'))
    else:   
      files = glob.glob(os.path.join(toStrip, '*.java'))
    if not files:
      print '<br><p>No files to strip in ' + directory + '</p>'
    else:
      files.sort(None, key=lambda x: re.search(SUBMITTED_RE, os.path.basename(x)).group(3))

      #copy files
      print '<br><p class="strip"><b>Stripping:</b><br>'
      for f in files:
        match = re.match(SUBMITTED_RE, os.path.basename(f))
        assert match, "Bad file format in stripFiles"
        newF = os.path.join(STRIPPED_ROOT, match.group(1) + match.group(2) + 
                            "." + match.group(4))
        print 'Copying ' + os.path.basename(f) + ' ==&gt; ' + os.path.basename(newF), 
        if os.path.exists(newF):
          #file already exists
          print '<i>(overwite)</i>'
        shutil.copy(f, newF)
        print '<br>'
      print '</p><p class="strip"><b>Done.</b></p>'

  return result


if __name__ == "__main__":
  #running as a script (rather than as imported module)
  main() #call main
  
