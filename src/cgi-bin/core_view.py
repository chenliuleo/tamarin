#!python

##
## displaycore.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 10 Sep 2008.
##
## A library of functions for constructing different views of 
## graded Tamarin data and files.  The display functions 
## output HTML code but do not construct complete HTML pages 
## by themselves.
##
## Many of these functions include a "master" parameter.
## This will make the displayed Grade for each submission (if
## shown in that view) a link that will allow the viewer to 
## add a comment and modify the grade.  This is intended for 
## use in masterview.py and so is False by default.
##
## See view.py and masterview.py for more.
##

from tamarin import *

def displaySubmission(filename, master=False):
  """
  Displays a single submitted file and its corresponding grader output.
  
  Filename means the UsernameA##-########-####.ext filename.
  If master is True, grade is a link to a modify/comment form.
  
  Returns the result of displaying (should be 'OK')
  """
  result = 'OK'
  try:
    submittedFile = SubmittedFile(filename)
  except TamarinStatusError, tse:
    if tse.args[0] == 'NO_SUBMITTED_FILE':
      try:
        submittedFile = GradedFile(filename)
      except TamarinStatusError, tse2:
        result = tse2.args[0]
    else:
      result = tse.args[0]

  if result == 'OK':
    print '<div class="submission">'
    print '<h4>' + filename + '</h4>'
    
    #how should we print this code
    usePre = EXT_HANDLERS[Assignment(submittedFile.assignment).fileExt][DISPLAY_AS_CODE]
    #print code
    javafile = open(submittedFile.path, 'r')
    if usePre:
      print '<pre class="code">'
    else:
      print '<div class="code">'
    if EXT_HANDLERS[Assignment(submittedFile.assignment).fileExt][IS_BINARY]:
      #can't display the contents
      print '[ binary file format (' + submittedFile.fileExt + '): '
      print 'cannot display contents here ]'
    else:
      for line in javafile:
        #replace angle brackets
        line = line.replace('&', '&amp;')
        line = line.replace('<', '&lt;')
        line = line.replace('>', '&gt;')
        #if as text, need formatting
        if not usePre:
          line = line.replace("\n", "<br>\n")
        print line,
    if usePre:
      print '</pre>'
    else:
      print '</div>'
    javafile.close()

  if result == 'OK':
    #a graded file
    if isinstance(submittedFile, GradedFile):
      graderfile = open(submittedFile.graderPath, 'r')
      for line in graderfile:
        #grab grade line and tweak
        if '<p><b>Grade:</b>' in line:
          match = re.match(r"(<p><b>Grade:</b>)\s?([^<]+)(</p>)", line)
          line = match.group(1) + ' '
          if master:
            #make this a link to modifying the grade             
            line += '<a href="masterview.py?submission=' + filename + '#append"'
            if MASTER_LINKS_OPEN_NEW_WINDOW:
              line += ' target="_blank"'
            line += '>'

          line += match.group(2)
          if not submittedFile.humanVerified:
            line += SHORT_UNVERIFIED_GRADE_LABEL

          if master:
             #end link
             line += '</a>'
          line += match.group(3)
        
        #markup any grader output lines
        if HIGHLIGHT_PREFIX and line.startswith(HIGHLIGHT_PREFIX):
          #</span> comes after line break, which is slightly annoying
          line = '<span class="graderOutputLine">' + line + '</span>'
          for elem in HIGHLIGHT_ELEMENTS:
            line = line.replace('[' + elem + ']', 
                     '[<span class="grader' + elem + '">' + elem + '</span>]')
        
        sys.stdout.write(line)  #print without additional spaces
      graderfile.close()
      #add explanation of C and NC grades
      if submittedFile.grade == 'C' or submittedFile.grade == 'NC':
        print '<div class="grader"><p>'
        if submittedFile.grade == 'C':
          print '<i>Compiled OK; not yet graded.</i>'
        else:
          print '<i>Did not compile; not yet graded.</i>'        
        print '</p></div>'

    #only a submitted file
    else:
      print '<div class="grader">'
      print '<p><i>Submitted, but not yet graded.</i></p>'
      print '</div>'

    print '</div>'
  
  return result    
    

def displayAssignmentSubmissions(user, assignmentName, brief=False, master=False):
  """
  Displays all the submissions the user made for this assignment.
  
  If in brief mode, this will just be a list of files, including the grade
  for each one.  Each listing will be a button (or link, if in master mode)
  to the appropriate submission view.
  
  If in full mode (that is, not brief), will show each submission expanded within 
  this view.
  
  At the top off all submissions, will include a header listing the assignment
  and the final grade.
  
  Returns the status code (should be 'OK')
  """
  result = 'OK'
  
  assignment = Assignment(assignmentName)

  #first, support username having either upper or lowercase first letter
  user = user.lower()
  globFilename = '[' + user[0] + user[0].upper() + ']' + user[1:]
  globFilename += assignment.name + '-*.' + assignment.fileExt
  if result == 'OK':
    try:
      #get graded files for this user
      files = glob.glob(os.path.join(GRADED_ROOT, assignment.dir, globFilename))
      #add any ungraded submitted files
      files.extend(glob.glob(os.path.join(SUBMITTED_ROOT, globFilename))[:])

      #if grader files have same extension as submissions, need to drop grader files
      if assignment.fileExt == GRADER_OUTPUT_FILE_EXT:
        weededFiles = [];
        for f in files:
          if re.match(SUBMITTED_RE, os.path.basename(f)):
            weededFiles.append(f)
        files = weededFiles

      #sort using timestamp as the key  (note: timestamp in dir names too, so need base)
      files.sort(None, key=lambda x: re.match(SUBMITTED_RE, os.path.basename(x)).group(3))
    except:
      result = 'COULD_NOT_READ'
  
  if result == 'OK':
    #print the file list, according to mode, with grade or not 
    #list header
    print '<div class="submissionList">'
    
    #calculate final grade
    #(Assuming that even ungraded and grader-error submissions count as
    #  submissions, we only need the grade of the last submission to have an accurate
    #  final grade.)    
    grade = '<i>Not yet submitted.</i>'
    late = False
    resubmits = False
    pastDue = False
    
    if files:
      lastSubmit = files[-1]
      if SUBMITTED_ROOT in lastSubmit:
        grade = '<i>Not yet graded.</i>'
        lastSubmittedFile = SubmittedFile(os.path.basename(lastSubmit))
      else:
        lastSubmittedFile = GradedFile(os.path.basename(lastSubmit))
        grade = lastSubmittedFile.grade  #may be ERR

      lastGrade = grade
      lateStatus = assignment.isLate(lastSubmittedFile.timestamp)
      
      #compute lateness effect on grade      
      if lateStatus != 'OK':
        late = True
        if not isinstance(grade, str):
          grade -= LATE_PENALTY
          if lateStatus == 'SUBMISSION_TOO_LATE':
            grade -= VERY_LATE_PENALTY
          if grade < 0.00001:
            grade = 0.0

      #resubmit penalty
      if len(files) > 1:
        resubmits = True
        if not isinstance(grade, str):
          grade -= (len(files) - 1) * RESUBMISSION_PENALTY
          if grade < 0.00001:
            #handles both negative and floating point errors
            grade = 0.0
            
      #grade not verified yet
      if isinstance(lastSubmittedFile, GradedFile) and \
         not lastSubmittedFile.humanVerified and not isinstance(grade, str):
         grade = '<span class="unverified">' + str(grade) + \
                 UNVERIFIED_GRADE_LABEL + '</span>'
      
    else:
      #no files submitted at all yet
      lateStatus = assignment.isLate()
      late = (lateStatus != 'OK')
      #pastDue means no submissions yet, and now it's too late to get any in
      pastDue = (lateStatus == 'SUBMISSION_TOO_LATE') and not SUBMIT_VERY_LATE
      if pastDue:
        #can't submit, so grade goes to 0
        grade = 0

    print '<div class="assignment">'
    print '<table class="assignment"><tr><td class="assignment">'
    print '<b>' + assignment.name + '</b> &nbsp;'
    print '<small>(Due: ' + assignment.due + '. '
    print 'Total: ' + str(assignment.maxScore) + ' points.)</small></td>'
    print '<td class="grade"><b>Grade:</b> ' + str(grade) + '</td>'
    if late or resubmits:
      #need to explain why grade doesn't match last submit
      print '<td class="reason">[',
      if pastDue:
        #can't even submit, so explain why the grade is a 0
        print '<i>Too late to submit.</i>',
      else:
        #print explanation/late status (even if don't really have a full grade yet)
        if not isinstance(grade, str):
          print '= ' + str(lastGrade),
        if late:
          if lateStatus == 'SUBMISSION_LATE':
            print '-' + str(LATE_PENALTY),
            print '(late)',
          else:
            print '-' + str(LATE_PENALTY + VERY_LATE_PENALTY),
            print '(' + VERY_LATE_LABEL + ')'
        if resubmits:
          print ' - (' + str(RESUBMISSION_PENALTY) + ' * ' + \
                str(len(files) - 1) + ' resubmits)',
      print ']</td>'
    print '</tr></table>'
      
    #list contents
    if files and brief:
      print '<ul>'
    for f in files:
      if brief:
        if master:
          print '<li><a href="masterview.py?submission=' + os.path.basename(f) + '"',
          if MASTER_LINKS_OPEN_NEW_WINDOW:
            print 'target="_blank"',
          print '>' + os.path.basename(f) + '</a>', 
        else:
          print '<li><input type="submit" name="submission" value="' + \
                 os.path.basename(f) + '">'
        if SUBMITTED_ROOT in f:
          print '&nbsp; [<i>Not yet graded.</i>]'
        else:
          graded = GradedFile(os.path.basename(f))
          shortGrade = str(graded.grade)
          if not graded.humanVerified and not isinstance(graded.grade, str):
            shortGrade += SHORT_UNVERIFIED_GRADE_LABEL
          print '&nbsp; [' + shortGrade + ']'  #may be ERR
      else:
        displaySubmission(os.path.basename(f), master)
          
    #list footer
    if files and brief:
      print '</ul>'
    print '</div></div>'
      
  return result
  
  
def displayUser(user, assignment=None, brief=True, master=False):
  """
  Displays the work of the given user.  
  
  If assignment is not None, it displays only that assignment.  
  Otherwise, displays an assignmentSubmissions view for every assignment 
  for this user. In other words, shows all the work this user has submitted 
  (or not).
  
  A brief assignmentSubmissions view is on by default for this function.
  
  Returns the status code.
  """
  result = 'OK'
  #get assignment list
  if assignment:
    #single assignment only, so first verify it really exists
    try:
      assignment = Assignment(assignment)
    except TamarinStatusError, tse:
      result = tse.args[0]
    if result == 'OK':
      assignments = [os.path.join(GRADED_ROOT, assignment.dir)]
  else:
    #get a full list
    assignments = glob.glob(os.path.join(GRADED_ROOT, 'A*'))
    assignments.sort()
    
  if result == 'OK':
    #print user table
    details = getUserDetails(user)
    if not isinstance(details, list):
      #then it's an error code
      result = details
    else:
      print '<div class="user">'
      print '<table class="user"><tr><td class="user"><b>' + user.lower() + '</b>'
      print '&nbsp; <small>(' + str(details[2]) + ' ' + str(details[1]) + ')</small></td>'
      print '<td class="section">Section: ' + str(details[0]) + '</td></tr></table>'
      
      for a in assignments:
        assign = re.search(r"(A\d\d\w?)-\d{8}-\d{4}", a)
        if not assign:
          result = 'BAD_ASSIGNMENT_DIR_FORMAT'
          break  #so that we only print one error message
        assign = assign.group(1) #grab short form of A
        result = displayAssignmentSubmissions(user, assign, brief, master)
        if result != 'OK':
          printError(result) 
      
      print '</div>'
      
  return result


#add section filtering?
def displayAssignment(assignment, brief=False, master=False):
  """
  Displays the assignment submissions list for every user
  for the given assignment.  (This is basically the "grading" view.)
  """
  result = 'OK'
  users = getUsers()
  if users == 'NO_USER_FILE':
    result = users
  
  if result == 'OK':
    users.sort()
    for u in users:
      result = displayUser(u, assignment, brief, master)
  
  return result


def modifySubmission(filename):
  """
  As displaySubmission, this function then appends a form 
  for the master to append a comment and/or change the grade.  
  Sends these change to appendComment (in masterview.py), 
  which deals with the actual hassle of storing the changes.
  """
  #doesn't need to be master, since don't need grade line
  result = displaySubmission(filename)
  
  #need to get current grade, and then print comment form
  if result == 'OK':
    try:
      submittedFile = GradedFile(filename) 
      print '<form class="modify" action="masterview.py#bottom" method="post">'
      print '<input type="hidden" name="submission" value="' + filename + '">'
      print '<p id="append"><b>Comment to append:</b></p>'
      print '<textarea name="comment" rows="4" cols="80"></textarea><br>'
      print '<p><b>New grade:</b>'
      print '<input type="text" name="grade" size="6"', 
      print 'value="' + str(submittedFile.grade) + '">'
      print '&nbsp; <b>Human verified:</b> '
      print '<input type="checkbox" name="verify" checked> &nbsp;'
      print '<input type="submit" name="modify" value="Modify">'
      print '</p></form>'
  
    except TamarinStatusError:
      #do nothing--just not graded yet, so can't edit grade
      pass  
  return result

