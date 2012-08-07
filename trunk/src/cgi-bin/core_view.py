
## core_view.py 

"""
A library of functions for constructing different views of graded 
Tamarin data and files.  The display functions output HTML code but 
do not construct complete HTML pages by themselves.

Many of these functions include a "master" parameter. This will make 
the displayed Grade for each submission (if shown in that view) a link
that will allow the viewer to add a comment and modify the grade.  
This is intended for use in masterview.py and so is False by default.

See view.py and masterview.py for more.

Part of Tamarin, by Zach Tomaszewski.  
Created: 10 Sep 2008.
"""

import html
import os
import re

import tamarin
from core_type import TamarinError, SubmittedFile, GradedFile, Assignment

def displaySubmission(filename, master=False):
    """
    Displays a single submitted file and its corresponding grader output.
    
    Filename means a UsernameA##-########-####.ext filename, which will 
    correspond to a SubmittedFile or GradedFile.
    If master is True, grade is a link to a modify/comment form.
    
    Raises a TamarinError if the given file cannot be displayed.
    """
    # most likely to be graded, so check that first
    try:
        submittedFile = GradedFile(filename)
    except TamarinError as err:
        if err.key == 'NO_SUBMITTED_FILE':
            # file not graded yet, so try submitted instead
            submittedFile = SubmittedFile(filename)
        else:
            # some more serious error, so let it carry on
            raise err
    
    print('<div class="submission">')
    print('<h4>' + filename + '</h4>')
    assignment = Assignment(submittedFile.assignment)

    #how should we print this code?
    usePre = assignment.type.preformatted
    #print code
    codefile = open(submittedFile.path, 'r')
    if usePre:
        print('<pre class="code">')
    else:
        print('<div class="code">')
    
    if not assignment.type.encoding:
        #can't display the contents (binary)
        print('[ binary file format (' + submittedFile.fileExt + '): '
              'cannot display contents here ]')
    else:
        for line in codefile:
            #replace angle brackets and such
            line = html.escape(line)
            #if as text, need a little line-break formatting
            if not usePre:
                line = line.replace("\n", "<br>\n")
            print(line, end='')  #since still have \n in line itself
    
    if usePre:
        print('</pre>')
    else:
        print('</div>')
    codefile.close()

    if isinstance(submittedFile, GradedFile):
        #a graded file
        with open(submittedFile.graderOutputPath, 'r') as gradeFile:
            for line in gradeFile:                
                
                #grab grade line and mark tentative and/or convert to link
                if tamarin.GRADE_START_TAG in line:
                    match = re.match(tamarin.GRADE_START_TAG + 
                                     r"\s*([^<]+)\s*" + tamarin.GRADE_END_TAG, 
                                     line)
                    line = tamarin.GRADE_START_TAG  # reconstruct the line
                    if master:
                        #make this a link to modifying the grade             
                        line += '<a href="masterview.py?submission=' + \
                                filename + '#append"'
                        if tamarin.MASTER_LINKS_OPEN_NEW_WINDOW:
                            line += ' target="_blank"'
                        line += '>'
                    
                    line += match.group(1)  #grade
                    if not submittedFile.humanVerified:
                        line += tamarin.SHORT_UNVERIFIED_GRADE_LABEL

                    if master:
                        #end link
                        line += '</a>'
                    line += tamarin.GRADE_END_TAG + '\n' #end line
        
                #markup any grader output lines
                if tamarin.HIGHLIGHT_PREFIX and \
                        line.startswith(tamarin.HIGHLIGHT_PREFIX):
                    #</span> comes after line break, which is slightly annoying
                    line = '<span class="graderOutputLine">' + line + '</span>'
                    for elem in tamarin.HIGHLIGHT_ELEMENTS:
                        line = line.replace('[' + elem + ']', 
                                            '[<span class="grader' + elem +
                                               '">' + elem + '</span>]')
        
                print(line, end='')
            #end for, then...
            gradeFile.close()
    else:
        #only a submitted file
        print('<div class="grader">')
        print('<p><i>Submitted, but not yet graded.</i></p>')
        print('</div>')
    print('</div>')    

def displayAssignmentSubmissions(user, assignmentName, 
                                 brief=False, master=False):
    """
    Displays all the submissions the user made for this assignment.
    
    In brief mode, this will just be a list of files, including the grade
    for each one.  Each listing will be a button (or link, if in master mode)
    to the appropriate submission view.
    
    If in full mode (that is, brief=False), will show each submission expanded 
    within this view.
    
    At the top off all submissions, will include a header listing the 
    assignment and the final grade based on last submission and late policy
    adjustments.
    """
    assignment = Assignment(assignmentName)
    files = tamarin.getSubmissions(user=user, assignment=assignmentName)
    
    # calculate final grade and status for this assignment
    # (Assuming that even ungraded and grader-error submissions count as
    # submissions, we only need the grade of the last submission to have an 
    # accurate final grade.)
    grade = '<i>Not yet submitted.</i>'
    reason = None

    if files:
        lastSubmit = files[-1]
        if tamarin.SUBMITTED_ROOT in lastSubmit:
            grade = '<i>Not yet graded.</i>'
            lastFile = SubmittedFile(os.path.basename(lastSubmit))
        else:
            lastFile = GradedFile(os.path.basename(lastSubmit))
            grade = lastFile.getAdjustedGrade(len(files))
            lateness = lastFile.getLateGradeAdjustment()
            resubmits = lastFile.getResubmissionGradeAdjustment(len(files))
            
            if lateness or resubmits:
                # explain grade calcs
                reason = '[= ' + lastFile.grade
                if lateness:
                    reason += ' ' + str(lateness)
                    reason += ' (' + lastFile.getLateOffset() + ')'
                if resubmits:
                    reason += ' ' + str(resubmits)
                    reason += ' (' + str(len(files) - 1) + ' resubmits)'
                reason += ']'
            elif lastFile.isLate():
                # just a little informational timestamping
                reason = '<small>' + lastFile.getLateOffset() + '</small>'
            
            # mark grade if not verified yet
            if not lastFile.humanVerified:
                grade = '<span class="unverified">' + str(grade) + \
                        tamarin.UNVERIFIED_GRADE_LABEL + '</span>'
    else:
        #no files submitted at all yet
        if assignment.isTooLate():
            #can't submit, so grade goes to 0
            grade = 0
            reason = '<i>Too late to submit.</i>'

    # print submission list header, starting with assignment grade
    print('<div class="submissionList">')
    print('<div class="assignment">')
    print('<table class="assignment"><tr><td class="assignment">')
    print('<b>' + assignment.name + '</b> &nbsp;')
    print('<small>(Due: ' + assignment.due + '. ')
    print('Total: ' + str(assignment.maxScore) + ' points.)</small></td>')
    print('<td class="grade"><b>Grade:</b> ' + str(grade) + '</td>')
    if reason:
        print('<td class="reason">' + reason + '</td>')
    print('</tr></table>')

    #list contents
    if files and brief:
        print('<ul>')
    for f in files:
        if brief:
            if master:
                print('<li><a href="masterview.py?submission=' + 
                      os.path.basename(f) + '"', end='')
                if tamarin.MASTER_LINKS_OPEN_NEW_WINDOW:
                    print(' target="_blank"', end='')
                print('>' + os.path.basename(f) + '</a>', end=' ') 
            else:
                print('<li><input type="submit" name="submission" value="' + 
                      os.path.basename(f) + '">', end=' ')
            if tamarin.SUBMITTED_ROOT in f:
                print('&nbsp; [<i>Not yet graded.</i>]')
            else:
                graded = GradedFile(os.path.basename(f))
                shortGrade = str(graded.grade)
                if not graded.humanVerified:
                    shortGrade += tamarin.SHORT_UNVERIFIED_GRADE_LABEL
                if graded.humanComment:
                    shortGrade += tamarin.HUMAN_COMMENT_LABEL
                print('&nbsp; [' + shortGrade + ']')
        else:
            displaySubmission(os.path.basename(f), master)
          
    #list footer
    if files and brief:
        print('</ul>')
    print('</div></div>')
            
def displayUser(user, assignment=None, brief=True, master=False):
    """
    Displays the work of the given user.  
    
    If the name of the assignment is specified, it displays only that 
    assignment. Otherwise, displays an assignmentSubmissions view for every 
    assignment for this user. In other words, shows all the work this user 
    has submitted (or not).
    
    A brief assignmentSubmissions view is on by default for this function.
    
    """
    #get assignment list
    if assignment:
        assignment = Assignment(assignment)
        assignments = [assignment.name]
    else:
        assignments = tamarin.getAssignments()
    
    #print user table
    details = tamarin.getUserDetails(user)
    print('<div class="user">')
    print('<table class="user"><tr>')
    print('<td class="user"><b>' + user.lower() + '</b>')
    print('&nbsp; <small>(' + str(details[2]) + ' ' + str(details[1]) + 
          ')</small></td>')
    print('<td class="section">Section: ' + str(details[0]) + '</td>')
    print('</tr></table>')
      
    for assign in assignments:
        displayAssignmentSubmissions(user, assign, brief, master)      
    print('</div>')
 
def displayAssignment(assignment, brief=False, master=False):
    """
    Displays the assignment submission lists for every user
    for the given assignment.  (This is basically the "grading" view.)
    """
    # Future: add section filtering?
    users = tamarin.getUsers()
    for u in users:
        displayUser(u, assignment, brief, master)  

def modifySubmission(filename):
    """
    Extends displaySubmission to append a form for the master to append 
    a comment and/or change the grade. Sends these change to appendComment 
    (in masterview.py), which deals with the actual hassle of storing 
    the changes.
    """
    #doesn't need to be master, since don't need grade link
    displaySubmission(filename)
    submittedFile = GradedFile(filename)
    print('<form class="modify" action="masterview.py#bottom" method="post">')
    print('<input type="hidden" name="submission" value="' + filename + '">')
    print('<p id="append"><b>Comment to append:</b></p>')
    print('<textarea name="comment" rows="4" cols="80"></textarea><br>')
    print('<p><b>New grade:</b>')
    print('<input type="text" name="grade" size="6"',) 
    print('value="' + str(submittedFile.grade) + '">')
    print('&nbsp; <b>Human verified:</b> ')
    print('<input type="checkbox" name="verify" checked> &nbsp;')
    print('<input type="submit" name="modify" value="Modify">')
    print('</p></form>')

