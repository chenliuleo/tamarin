#!python3

## masterview.py 

"""
BEWARE: Secure access to this script!

Allows the administrator to view submitted assignments, change grades,  
add comments, and perform other common grading tasks through the web 
interface.

Part of Tamarin, by Zach Tomaszewski.  
Created: 15 Sep 2008.
"""

import cgi
import glob
import html
import os
import re
import shutil

import tamarin
from core_type import TamarinError, Assignment, GradedFile
import core_view
import submit


def main(form=None):
    if not form:
        form = cgi.FieldStorage()
    try:
        if not form:
            tamarin.printHeader('Tamarin Masterview')
            displayForm()
        
        elif 'modify' in form:
            # modify a submission's grade
            if 'submission' not in form or 'grade' not in form:
                # may have a comment too, but that can be blank
                tamarin.printHeader('Masterview: Modify error')
                raise TamarinError('BAD_SUBMITTED_FORM')        
            
            tamarin.printHeader("Masterview: Modified " + 
                                form.getfirst('submission'))
            modifySubmission(form.getfirst('submission'), 
                             form.getfirst('grade'), form.getfirst('verify'),
                             form.getfirst('comment'))
            core_view.displaySubmission(form.getfirst('submission'), 
                                        master=True)
        elif 'deleteComment' in form:
            # delete a comment from a submission
            if 'submission' not in form:
                tamarin.printHeader('Masterview: Delete comment error')
                raise TamarinError('BAD_SUBMITTED_FORM')
            
            tamarin.printHeader('Masterview: Deleted comment #' + 
                                form.getfirst('deleteComment'))
            deleteComment(form.getfirst('submission'), 
                          form.getfirst('deleteComment'))
            print('<br>')
            core_view.displaySubmission(form.getfirst('submission'), 
                                        master=True)
    
        elif 'submission' in form:
            # view a single specific submission 
            # (without modify or deleteComment, caught above)            
            tamarin.printHeader('Masterview: ' + form.getfirst('submission'))
            print('<br>')
            core_view.modifySubmission(form.getfirst('submission'))
       
        elif 'user' in form:
            # view all of a user's submissions
            tamarin.printHeader('Masterview: ' + form.getfirst('user'))
            core_view.displayUser(form.getfirst('user'),
                                  assignment=form.getfirst('assignment'),
                                  brief=form.getfirst('brief'), 
                                  master=True)
      
        elif 'assignment' in form:
            # without user given, or would have been caught above
            tamarin.printHeader('Masterview: ' + form.getfirst('assignment'))
            core_view.displayAssignment(form.getfirst('assignment'), 
                                        form.getfirst('brief'), 
                                        master=True)
                                          
        elif 'strip' in form: 
            tamarin.printHeader('Masterview: Stripping ' + 
                                form.getfirst('strip'))
            stripFiles(form.getfirst('strip'), form.getfirst('only'))

        elif 'verifyAll' in form: 
            tamarin.printHeader('Masterview: Verifying ' + 
                                form.getfirst('verifyAll'))
            markAllAsVerified(form.getfirst('verifyAll'))
        
        elif 'startGrader' in form:
            tamarin.printHeader('Masterview: Start grading pipeline')
            started = submit.startGradePipe(printStatus=False)
            if started:
                print('<p><br>Grading pipeline started.</p>')
            else:
                print('<p><br>Grader pipeline <b>not</b> started.')
                print('This is either because it is disabled or is already '
                      'running.')
                print('<p>See <a href="' + tamarin.CGI_URL + 
                      'status.py">status</a> ' + 'for more.</p>')
        elif 'gradesheet' in form:
                print("Content-Type: text/plain")
                print()
                displayGradeSheet(form.getfirst('comma'))
        else:
            tamarin.printHeader('Masterview: No valid option submitted')
            raise TamarinError('BAD_SUBMITTED_FORM')          

    except TamarinError as err:
        tamarin.printError(err)
    except:
        tamarin.printError('UNHANDLED_ERROR')
    finally:
        if not (form and 'gradesheet' in form):
            tamarin.printFooter()


def displayForm():
    """
    Displays the initial/default masterview form.  Does not include header
    or footers.
    """
    #get sorted user and assignment lists
    users = tamarin.getUsers()
    assignments = tamarin.getAssignments()
        
    print("""<h2>Masterview</h2>  
<div class="masterview">
<h3>Views</h3>
    """)
    print('<form action="' + tamarin.CGI_URL + 'masterview.py" method="get">')
    print('Assignment: <select name="assignment">')
    for a in assignments:
        print('<option>' + a + '</option>')
    print('</select>')
  
    print("""
<select name="brief">
<option value="1" selected>Brief</option>
<option value="">Full</option>
</select>
<input type="submit" value="View">
</form>
    """)
    print('<form action="' + tamarin.CGI_URL + 'masterview.py" method="get">')
    print('User: <select name="user"><option></option>')
    for u in users:
        print('<option>' + u + '</option>')
    print('</select>')
  
    print('<select name="assignment">')
    print('<option value="">(All assignments)</option>')
    for a in assignments:
        print('<option>' + a + '</option>')
    print('</select>')
    print("""
<select name="brief">
<option value="1" selected>Brief</option>
<option value="">Full</option>
</select>
<input type="submit" value="View">
</form>

<h4>Grade sheet view</h4>
    """)
    print('<form action="' + tamarin.CGI_URL + 'masterview.py" method="get">')
    print("""
<p>
Produces a tab-separated plain-text view of adjusted Tamarin scores for all 
users across all assignments.  This can easily be copy-and-pasted into a 
spreadsheet program.  
<p>
<input type="hidden" name="gradesheet" value="1">
<input type="checkbox" name="comma"> 
Use commas instead of tabs and suppress username-column padding.
<p>
<input type="submit" value="Generate"
title="You may need to paste into a text editor first and then copy again 
from there before your spreadsheet will accept it correctly.">
</p>
</form>
</div>

<div class="masterview">
<h3>Tools</h3>
<h4>Mark as human-verified</h4>
    """)
    print('<form action="' + tamarin.CGI_URL + 'masterview.py" method="get">')
    print('<p>Mark all graded files in:')
    print('<select name="verifyAll"><option></option>')
    for a in assignments:
        print('<option>' + a + '</option>')
    print('</select>')
  
    print('<input type="submit" value="Verify"></p>')
    print('</form>')

    print('<h4>Start grader</h4>')
    print('<form action="' + tamarin.CGI_URL + 'masterview.py"', end=' ')
    print('method="post" enctype="multipart/form-data">')
    print("""<p>
If the pipeline is OFF but submissions are still sitting in the grading queue, 
as shown by 
    """)
    print('<a href="' + tamarin.CGI_URL + 'status.py">status</a>,')
    print("""you can:
<input type="hidden" name="startGrader" value="1">
<p>
<input type="submit" value="Start Grader">
</p>
</form>
    """)

    print('<h4>Strip timestamps from filenames</h4>')
    print('<form action="' + tamarin.CGI_URL + 'masterview.py" method="get">')
    print('<p>From assignment/directory: ')
    print('<select name="strip"><option>submitted</option>')
    for a in assignments:
        print('<option>' + a + '</option>')
    print('</select>')
    print('&nbsp; (copying into ' + tamarin.STRIPPED_ROOT + ')')
    print('<p>Strip only files with names containing (blank for all):')
    print('<input type="text" name="only">')
    print('<p><input type="submit" value="Strip"></p>')
    print('</form>')
    print('</div>')


def displayGradeSheet(comma=False):
    """
    Produces a grade sheet view for all users and assignments.
    
    Rows correspond to users, sorted by username.  Rows contain the Tamarin 
    adjusted scores for each assignment followed by the total adjusted score. 
    
    By default, uses tabs as delimiters, with the user column padded to 14 
    characters to maintain a readable format even when faced with slightly 
    longer usernames.  If comma is True, just uses commas and no padding. 

    Unverified grades (and any totals depending on them) are marked
    with an appended ?. 
    
    Missing/unsubmitted grades are left blank.  Submitted but ungraded
    submissions are ignored (so blank if no other submissions for that 
    assignment).
    
    The total score is the sum of all numeric values, ignoring any 
    OK, X, or ERR grades.  If there are no numeric values, the total
    is ERR, X, or OK (in that order) if such a value is a component grade.
    Otherwise, the total is blank.  If at least one score is 
    tentative (unverified), the total is also tentative.

    """
    users = tamarin.getUsers()
    delim = ',' if comma else '\t'
    
    # build data structure 
    sheet = dict()
    for user in users:
        sheet[user] = {}  # scores keyed by assignment name
    
    # now process each assignment
    assignments = tamarin.getAssignments()  # already sorted
    for assign in assignments:
        subs = tamarin.getSubmissions(assignment=assign, submitted=False)
        # overwrite until last sub for each user, keyed by lower username
        submissions = {}
        for sub in subs:
            sub = os.path.basename(sub)
            usr = re.match(r"(\w+)" + assign, sub).group(1).lower()
            submissions[usr] = sub
        
        for user in users:
            if user in submissions:
                sub = GradedFile(submissions[user])
                grd = sub.getAdjustedGrade()

                # add to total grade list: (grade, verified?)
                if 'Total' not in sheet[user]:
                    sheet[user]['Total'] = [grd, True]
                elif isinstance(grd, float) or isinstance(grd, int):
                    # grd is a number, so overwrite/adds to whatever is there
                    if isinstance(sheet[user]['Total'][0], str):
                        sheet[user]['Total'][0] = grd
                    else:
                        sheet[user]['Total'][0] += grd
                else:
                    # grd is a string, so maybe replace any str or else ignore
                    if isinstance(sheet[user]['Total'][0], str):
                        if sheet[user]['Total'][0] == 'OK':
                            sheet[user]['Total'][0] = grd
                        elif sheet[user]['Total'][0] == 'X' and grd != 'OK':
                            sheet[user]['Total'][0] = grd
                        else:
                            pass  # grade is already ERR
                    else:
                        pass  # grade is a number, so ignore this string grd

                grd = str(grd)
                if not sub.humanVerified:
                    grd += '?'
                    sheet[user]['Total'][1] = False
                sheet[user][assign] = grd 
            else:
                sheet[user][assign] = ''  # blank
            
    # print details    
    # header
    print(',' if comma else '{:14}\t'.format(' '), end='')
    for assign in assignments:
        print(assign + delim, end='')
    print('Total')

    for user in users:
        print(user + ',' if comma else '{:14}\t'.format(user), end='')
        for assign in assignments:
            print(sheet[user][assign] + delim, end='')
        # print final total
        if 'Total' in sheet[user]:
            if isinstance(sheet[user]['Total'][0], float):
                sheet[user]['Total'][0] = round(sheet[user]['Total'][0], 
                                                tamarin.GRADE_PRECISION)
            print(sheet[user]['Total'][0], end='')
            if not sheet[user]['Total'][1]:
                print('?', end='')
        print('')
        

def deleteComment(submission, commentID):
    """
    Removes the comment with the given ID from the grader file for submission.
    Submission is a filename.  If the commentID cannot be found, raises a
    TamarinError('BAD_SUBMITTED_FORM').
    """
    sub = GradedFile(submission)

    with open(sub.graderOutputPath , 'r') as filein:
        contents = ""
        otherComments = False
        deleting = False
        deleted = False
        
        for line in filein:
            if '<div class="comment"' in line:
                thisId = int(re.search(r'id="comment(\d+)"', line).group(1))
                if str(thisId) == commentID:
                    # delete all lines of this comment until end tag
                    deleting = True
                else:
                    otherComments = True
            
            if not deleting:
                contents += line
                
            if deleting and '</div><!--comment' + str(commentID) in line:
                deleting = False
                deleted = True

    if not deleted:
        raise TamarinError('BAD_SUBMITTED_FORM', 
                           "Could not deleteComment=" + str(commentID))
                                 
    # dump file contents back into grader file
    with open(sub.graderOutputPath, 'w') as fileout:
        fileout.write(contents)
    
    if not otherComments:    
        # deleted last comment, so need to update filename
        sub.humanComment = False
        sub.update()    


def modifySubmission(submission, newGrade, verified, comment=None):
    """
    Modifies the grading status of the given submission.
    
    Takes a filename of the submission file.  Will change it's grade to
    newGrade.  If verified, adds "-H" to the grader filename; otherwise, 
    removes it.  If a comment is given, appends the comment to the grader file.
    
    Throws a TamarinError('INVALID_GRADE_FORMAT') if the passed newGrade is
    invalid.  If valid, will still round it to match tamarin.GRADE_PRECISION
    first.
    
    """
    sub = GradedFile(submission)
        
    # sanity checks and prep for any changes
    if newGrade != sub.grade:
        if not re.match(tamarin.GRADE_RE + '$', newGrade):
            raise TamarinError('INVALID_GRADE_FORMAT', html.escape(newGrade))
        try:
            newGrade = float(newGrade)
            newGrade = round(newGrade, tamarin.GRADE_PRECISION)
        except ValueError:
            pass  # fine, leave as a valid string

        # update object representation
        sub.grade = newGrade

    sub.humanVerified = verified

    if comment:
        sub.humanComment = True
        # preserve raw formatting.  
        # and we don't know where it came from, so standardize line-endings
        comment = comment.replace('\r\n', '\n');
        comment = comment.replace('\r', '\n');            
        comment = comment.replace('\n', '<br>\n')
        
    # now ready to update file contents
    with open(sub.graderOutputPath , 'r') as filein:
        contents = ""
        lastId = 0
        for line in filein:
            if '<div class="comment"' in line:
                # record ID of last comment seen in file
                # (see also: core_view.displaySubmission)
                lastId = int(re.search(r'id="comment(\d+)"', line).group(1))
            
            if tamarin.GRADE_START_TAG in line:
                if comment:
                    # insert latest comment before this line
                    lastId += 1
                    contents += '<div class="comment" id="comment' + \
                                str(lastId) + '">\n'
                    contents += '<p><b>' + tamarin.TA_COMMENT + '</b><br>\n'
                    contents += comment
                    contents += '\n</p>\n</div><!--comment' + str(lastId) + \
                                '-->\n'
                
                # replace line with current (possibly updated) grade
                contents += tamarin.GRADE_START_TAG + str(sub.grade) + \
                            tamarin.GRADE_END_TAG + '\n'
            else:
                contents += line
  
    # dump file contents back into grader file
    with open(sub.graderOutputPath, 'w') as fileout:
        fileout.write(contents)
        
    # now rename the grader output file if any changes were made
    sub.update()
    

def markAllAsVerified(assignName, silent=False):
    """
    Marks all graded files in the given assignment directory as human-verified.
    
    If silent is True, won't print any feedback.
    """
    files = tamarin.getSubmissions(assignment=assignName, submitted=False)
    files.sort()

    if not silent:
        print('<p class="strip"><b>Marking these files as human '
              'verified:</b><br>')
  
    marked = 0
    for f in files:
        # convert to GradedFile objects
        gf = GradedFile(os.path.basename(f))
        if not gf.humanVerified:
            if not silent: 
                print(gf.graderOutputFilename + ' &nbsp; ==&gt; &nbsp; ', 
                      end='')
            gf.humanVerified = True
            gf.update()
            marked += 1
            if not silent:
                print(gf.graderOutputFilename + '<br>')

    if not silent:
        print('<p class="strip">Marked ' + str(marked) + ' of ' + 
              str(len(files)) + ' submissions for ' + assignName +
              ' as human-verified.</p>')
        print('<p class="strip"><b>Done.</b></p>')

  
def stripFiles(directory, only=None):
    """
    Strips Tamarin timestamps from submission files in the given directory.
    
    Goes through the given directory (which must either be an assignment name 
    of the short A##a form or 'submitted'), copying each submitted file into 
    STRIPPED_ROOT, removing the Tamarin-appended timestamps from the names.  
    Copies in order of timestamp, so later submissions will overwrite earlier
    ones and you'll be left with the latest version for each user.
    
    If only is set, will only strip/copy files with names (but not extensions) 
    containing that string.
    
    If directory is an assignment, strips only files that match that 
    assignment type's file extension.  Also ignores all files that don't match 
    SUBMITTED_RE, which avoids any grader output file conflicts.
    
    Throws TamarinError on problems, including 'BAD_SUBMITTED_FORM' if input
    is incorrectly formatted.
    """
    #check input and figure out which full directory to process
    match = re.match(tamarin.ASSIGNMENT_RE + '$', directory)
    if match:
        assign = Assignment(directory)
        toStrip = assign.path
        ext = assign.type.fileExt
    elif directory == 'submitted':
        toStrip = tamarin.SUBMITTED_ROOT
        ext = '*'
    else:
        raise TamarinError('BAD_SUBMITTED_FORM', 
                           'Given strip directory is invalid: ' + directory) 

    #get file glob of files to strip
    if only:
        files = glob.glob(os.path.join(toStrip, '*' + only + '*.' + ext))
    else:   
        files = glob.glob(os.path.join(toStrip, '*.' + ext))
    
    if not files:
        print('<p class="strip">No files to strip in ' + directory, end='')
        if only:
            print(" that contain the substring '" + only + "'", end='')
        print('.</p>')
    else:
        # filter out any non-submitted files (such as .txt grader outputs)
        files = [f for f in files if re.match(tamarin.SUBMITTED_RE, 
                                              os.path.basename(f))]
        # sort by timestamp
        files.sort(key=lambda x: re.match(tamarin.SUBMITTED_RE, 
                                          os.path.basename(x)).group(3))
        #copy files
        print('<p class="strip"><b>Stripping:</b><br>')
        for f in files:
            match = re.match(tamarin.SUBMITTED_RE, os.path.basename(f))
            newF = os.path.join(tamarin.STRIPPED_ROOT, 
                                match.group(1) + match.group(2) + "." + 
                                match.group(4))
            print('Copying ' + os.path.basename(f) + ' ==&gt; ' + 
                  os.path.basename(newF), end='') 
            if os.path.exists(newF):
                #file already exists
                print(' <i>(overwite)</i>', end='')
            shutil.copy(f, newF)
            print('<br>')
        print('</p><p class="strip"><b>Done.</b></p>')


if __name__ == "__main__":
    #running as a script (rather than as imported module)
    main() #call main
