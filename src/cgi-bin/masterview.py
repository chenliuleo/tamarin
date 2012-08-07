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
        
            tamarin.printHeader("Modified: " + form.getfirst('submission'))
            modifySubmission(form.getfirst('submission'), 
                             form.getfirst('grade'), form.getfirst('verify'),
                             form.getfirst('comment'))
            core_view.displaySubmission(form.getfirst('submission'), 
                                          master=True)
    
        elif 'submission' in form:
            # view a single specific submission (without modify, caught above)
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
        else:
            tamarin.printHeader('Masterview: No valid option submitted')
            raise TamarinError('BAD_SUBMITTED_FORM')          

    except TamarinError as err:
        tamarin.printError(err)
    except:
        tamarin.printError('UNHANDLED_ERROR')
    finally:
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
</div>
<br>

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
