
## tamarin.py

"""
This is the core code of Tamarin shared by most of the cgi-bin files.
All configuration details are in this file.
 
For an overview of the system as a whole, see the documentation at:
http://code.google.com/p/tamarin/

Part of Tamarin, by Zach Tomaszewski.  
Created: 06 Jun 2008.
"""

import datetime   # for determining submission lateness, etc
import glob       # to check for file existence
import os.path    # for checking file existence and joining paths
import re         # to compare/process timestamps, etc
import sys        # for crash/error reporting
import traceback  # for crash/error reporting

##
## CONFIGURATION Globals
##

## ---FOLDERS----
## Defines the locations and directory structure that Tamarin uses.
## 

# Directory here the Tamarin .html and .css files are located.
# This is a URL specified relative to the web server's htdocs root, so 
# it should start with a '/'.  It must end with a '/'. 
# Just leave it as '/' to use the htdocs/ root. 
# 
HTML_URL = '/'

# Directory where the .py cgi scripts are located.  Again, this is a relative
# URL, so it should start with a / and must end with a /.
# (If changed, also update any saved generated .html files, such as 
#  upload.html)
#  
CGI_URL = '/cgi-bin/'

## It is recommended that you don't use any (non-normalized) literal 
## path separators (such as /) in the remaining ROOT paths.

# Where Tamarin stores its config files and (usually) the parent
# directory of all the storage directories.
# For security purposes, this should not be under the web server's
# htdocs folder so that these files cannot be served by the httpd.
# Can be either absolute or relative from CGI_ROOT.
# 
TAMARIN_ROOT = os.path.normpath('../tamarin')

# The directories where submissions are stored at various points
# through the grading process.
# 
UPLOADED_ROOT =  os.path.join(TAMARIN_ROOT, 'uploaded')
SUBMITTED_ROOT = os.path.join(TAMARIN_ROOT, 'submitted')

# Where assignments are temporarily located during actual grading.
#
GRADEZONE_ROOT = os.path.join(TAMARIN_ROOT, 'gradezone')

# Where assignment directories are created. 
# A directory for each assignment must be created manually within
# GRADED_ROOT so that Tamarin knows it can accept submissions for
# that assignment.  Assignment folder format is: A##-YYYYMMDD-HHMM  
# That is, the assignment name followed by the due date and time.
# Can optionally include a -# at end, were # is a total score value
# for that assignment (as an integer of 1 or more digits).
# Can also optionally include a -ext at the end, where ext is the
# name of the type extension required for submitted work.
# 
GRADED_ROOT = os.path.join(TAMARIN_ROOT, 'graded')

# Where a subfolder for each assignment (in format of [A-Z]\d\d\w?)
# holds the necessary grader and any extra files need for 
# grading that assignment.  
# Every assignment folder must contain at least one file.
# Any files that should be present for every grading session can
# be placed in the GRADERS_ROOT directory itself. 
# 
GRADERS_ROOT = os.path.join(TAMARIN_ROOT, 'graders')

# When using the strip tool offered through masterview.py,
# where to dump the files after stripping off the timestamps.
# 
STRIPPED_ROOT = os.path.join(TAMARIN_ROOT, 'stripped')

# Where to dump various files created as Tamarin runs to indicate
# its status.  (See FILES section below.)
STATUS_ROOT = os.path.join(TAMARIN_ROOT, 'status')


## ---FILES----
## Defines the location and name of special files used to control
## and record Tamarin's status. 
## 

# Location and name of the file that indicates an instance of
# the gradepipe is up and running.
# 
GRADEPIPE_ACTIVE = os.path.join(STATUS_ROOT, 'gradepipe.pid')

# Location and name of the file that indicates that the gradepipe
# is disabled.  (It will not be started again while this file exists.)
# 
GRADEPIPE_DISABLED =os.path.join(STATUS_ROOT, 'gradepipe.off')

# The webserver spawns a separate process to run gradepipe.py.
# However, on Apache, the parent web server process won't end due to 
# how Apache deals with file descriptors: the spawned process inherits
# stdout, stdin, etc from its parent process, and so that parent 
# process persists until they are closed. Therefore, all streams need 
# to be redirected so gradepipe.py will detatch cleanly.
#   
# XXX: This fix works under Linux, but not under Windows.
# 
GRADEPIPE_IN = os.path.join(STATUS_ROOT, 'null.txt')
GRADEPIPE_OUT = os.path.join(STATUS_ROOT, 'gradepipe.log')

# The command needed to spawn the gradepipe (relative to CGI_ROOT) 
# as a separate process.  Used in submit.py.  Remember to use Python 3. 
# 
# On Unix: './gradepipe.py' (or the full path)
# 
# On Windows: "python gradepipe.py" or "pythonw gradepipe.py"
#             (preferably, with full path to python)
#             
GRADEPIPE_CMD = 'python3 ./gradepipe.py'

# Location of a plain text file containing 
# username, password, section, lastname, and firstname fields.
# Usernames will be treated as all lowercase and at least 2 characters long.
# Any line in the file that starts with a # will be treated as a
# comment and ignored.
# 
USERS_FILE = os.path.join(TAMARIN_ROOT, 'users.txt')

# Delimter used between fields in USER_FILE
# 
USERS_FILE_DELIM = '|'   


## ---COURSE DETAILS---

# The address given in 5?? error messages for users to send a heads-up.
# May leave as '' and the error message will still make sense.
# 
ADMIN_EMAIL = ''

# Using masterview.py, you can append a comment to a graded submission.  
# This is the description of such a comment
# 
TA_COMMENT = 'Comment from TA:'

# The number of decimal points after the decimal point to which to round
# all grades for any source (grader, human override, late policy change, 
# etc). For example, 0 means integer grades only, 1 means 0.1 points
# are possible, and -1 means all grades will be rounded to the nearest 10
# points.  (Note that rounding follows the rules of Python's round() 
# function, which rounds .5s to the nearest even value and may occasionally 
# round "incorrectly" due to inherent floating point imprecision.  If such
# .5 cases are important to you, you may want to increase your precision to
# include them.)
#    
GRADE_PRECISION = 2

# The default total number of points each assignment is worth.
# This can then be overridden by particular assignments in their 
# directory name.
# 
ASSIGNMENT_TOTAL = 5

# The default submission type (as a string) for submitted files.
# Can be overridden by particular assignments in their directory name.
# 
ASSIGNMENT_TYPE = "java"

# Default extension of grader output files.  (There is no danger of 
# overwriting submitted .txt files because a grader output file always has
# at least "-" appended to the filename.  However, you may want to use 
# "grd" as an extension instead if you are grading a lot of txt files so 
# you can easily differentiate the two in directory listings.)
# 
GRADER_OUTPUT_FILE_EXT = "txt"

# The collection of late policies for this course. See Tamarin documentation 
# (or the LatePolicy class in core_type) for details of policy formats
# and how they are applied.  
#
# This variable is a dictionary of policies that are applied to each
# assignment based on the longest single match with the given assignment name.  
# For example, for an assignment 'A01a', any policies found would match in 
# the following order: 'A01a', 'A01', 'A0', 'A', ''.  Only the first match is
# applied, though the corresponding value may be a list or tuple of policies.
#
# Generally, only one global ('') policy is needed.  However, different late 
# policies for different assignment types, such as 'L' or 'E' for labs and 
# exercises might be handy.  And occasionally a special case might be needed
# for a particular assignment.
# 
# If no matching policy can be found, such as when LATE_POLICY is None or 
# empty, any late submissions will be refused.
#
# If resubmissions are allowed, overall lateness for an assignment is 
# determined by the timestamp of the last submission by the student for
# that assignment.
# 
LATE_POLICIES = {
# Examples.  Uncomment to activate:
#    '': ':',  #global, allows late submissions at no penalty
#    'A': ('+2d:-10%', '+5d:-30%'),  #for only 'A..'-named assignments
#    'A01': '+5d:-0',
}

# Number of points to take off of the final submission for each 
# resubmission made.  Should be a negative value.  Can be floating point.
# 
RESUBMISSION_PENALTY = -0.1

# Whether students may resubmit at any time that they could turn in an 
# original submission.  Set to False to allow resubmissions only before 
# the assignment deadline.
#
MAY_RESUBMIT_LATE = True

# If True, will accept resubmissions even after a human has verified the grade
# of a previous submission.  Use this if you (the human) want to keep grading 
# submissions until the student is satisfied with their grade; set to False if
# you only want to personally grade each assignment once for each student.
#
MAY_RESUMBIT_AFTER_HUMAN = False

from core_type import SubmissionType
from core_grade import CopyGrader
from core_grade import JavaCompiler, JavaGrader
# The mapping of submission type names to SubmissionType objects.  The name
# of each assignment directory may specify the submission type for that
# assignment.  If it does not, the default ASSIGNMENT_TYPE is used.
# 
# As a reminder, the SubmissionType constructor takes the following parameters:
# fileExt - required
# encoding - (default: 'utf-8')
# preformatted - (default: True)
# initialCap - (default: False)
# processes - (default: [])
#
SUBMISSION_TYPES = {
    'java': SubmissionType('java', 
                initialCap=True,
                processes=[
                    # may need to fill in full paths to javac and java
                    CopyGrader(),
                    JavaCompiler(javacPath='javac', required=False),
                    CopyGrader(),
                    JavaGrader(javaPath='java')
                ]),
    'txt':  SubmissionType('txt', preformatted=False),                    
}

# Occasionally a weird submission or poorly written grader will cause
# problems that cause the grader to crash with an error message.
# This message will get logged in the status/grader output file, and 
# more info may be in the particular grade results file with an ERR grade.
# Normally, the problem file will then be moved into the graded directory too
# so that it doesn't take up space (and get repeated graded) in the submit
# queue. However, if you're debugging or offline-grading, it's often nice to 
# have such problem files stay in the SUBMITTED folder instead so you don't 
# have to keep moving them back while tweaking the grader.  (Default: False)
#
# There are a couple serious problems where files get left in SUBMITTED
# even when this is True.
# 
LEAVE_PROBLEM_FILES_IN_SUBMITTED = True #False



## ---OUTPUT CONTROLS----
## 

# Though an unverified grade is already marked with a CSS style, 
# this label can also be appended immediately after any grade 
# that has not yet been verified by a human.
# 
UNVERIFIED_GRADE_LABEL = " (tentative)"

# As above, but this is used in list view of AssignmentSubmissions and
# when displaying submissions
# 
SHORT_UNVERIFIED_GRADE_LABEL = '<span class="unverified"><i>?</i></span>'

# Added after a submission when listed.
# 
HUMAN_COMMENT_LABEL = " + comment"

# Whether masterview.py links should open in a new window
# 
MASTER_LINKS_OPEN_NEW_WINDOW = False

# TamarinGrader.java marks all of its output lines with a prepend 
# string ("## " by default).  Set this variable to the same prepend 
# string if you want to turn on grader output highlighting.  
# Specifically, if this variable contains anything, all lines starting
# with the given string (regardless of Process source) will be wrapped by a 
# <span class="graderOutputLine"> tag when displayed by displaycore.py, 
# which then allows for CSS formatting.
# 
HIGHLIGHT_PREFIX = '## '

# If HIGHLIGHT_PREFIX is set, then will also check for the following
# elements within each line.  Elements must be found within [brackets].
# Wraps each in a span of class="grader+element".  So, for example, if
# a list element is PASS, any [PASS] found in a grader ouptut line
# would be replaced with [<span class="graderPASS">PASS</span>].
# Again, this allows for colorization and other CSS formating.
# 
HIGHLIGHT_ELEMENTS = ['PASS', 'FAIL', 'PART', 'EXTRA']


## --- END OF CONFIGURATION SETTINGS ---
#
# The remainder of the code in this file are essential Tamarin constants and
# functions used across all Tamarin components
# 


##
## PROGRAM CONSTANTS 
## (Do not touch these as a user or admin!)
##

# The date of the last edit of this Tamarin version 
# (shown in the footers of generated pages)
# 
TAMARIN_VERSION = '29 May 2012'

# The regex for an assignment name.
# Formed by a capital letter, a 2-digit number, and an optional 
# lowercase letter. (See class Assignment for the corresponding 
# directory format.) 
# 
ASSIGNMENT_RE = r"([A-Z]\d\d[a-z]?)"

# A filename extension, including the initial dot.  
# The extension may include multiple dots, such as for .tar.gz
# Nothing may follow the end of the extension.
# 
EXTENSION_RE = r"\.([\w.]+)$"

# The regex that matches what a submission's filename should look like
# when uploaded: 
# * a username (1 or more chars: letter, digit, or _), 
# * the assignment name (one capital letter, followed by two digits, 
#   and an optional lowercase letter), 
# * the file extension (1 or more chars).
# 
UPLOADED_RE =  r"^(\w+)" + ASSIGNMENT_RE + EXTENSION_RE

# A Tamarin timestamp, of the form YYYYMMDD-HHMM.
# 
TIMESTAMP_RE = r"(\d{8}-\d{4})"

# The regex for a student submission after it has been submitted:
# basically, as UPLOADED_RE, but a -timestamp inserted before the extension.
# 
SUBMITTED_RE = r"^(\w+)" + ASSIGNMENT_RE + '-' + TIMESTAMP_RE + EXTENSION_RE

# The regex for a grade, which is either OK, X, ERR, or an integer
# or decimal number.  Grading errors sometimes produce a file with 
# only a -, so * (0 or more) is used to match this case.  However,
# that means if used alone to look for a valid grade NOT part of a
# filename, you'll want to use GRADE_RE + '$'.
# 
GRADE_RE = r"([\d\.]*|ERR|OK|X)"

# The regex for an assignment after it has been graded:
# basically, as SUBMITTED_RE, but with grading outcome added.
# Requires a '-' after the timestamp, and then a grade.
# After grading outcome, may include an optional -H, -C, or -HC
# for human-verified or comment.
# 
GRADED_RE = (r"^(\w+)" + ASSIGNMENT_RE + '-' + TIMESTAMP_RE + '-' + 
             GRADE_RE + r"(-[HC]+)?" + EXTENSION_RE)

# When the standard GradeFile process grades a file, it posts the final
# grade into the output surrounded by these two TAG contents.  These are then
# important to other Tamarin components, such as core_view and masterview,
# when it comes to highlighting the grade as a link or updating it when
# changed by a human overseer.  End tag must start with a <.
#
GRADE_START_TAG = '<p class="grade"><b>Grade:</b> ' 
GRADE_END_TAG = '</p>'


# Status Codes (inspired by HTTP, but specific to Tamarin)
# stored as dictionary of tuples: {'KEY': (CODE, Message), 'KEY2': ...}
# 
STATUS = {
    # (In retrospect, I'm not sure if this was a useful design choice 
    # or not. Originally, Tamarin did not use TamarinErrors or exception
    # handling.  Now that it does, having all error descriptions in one
    # place might still be useful... maybe for I18N?)

    ## 100s: Successful idempotent or informational requests only. 
    ##  No change to grade/system state.  
    ## (These status messages usually replaced by returned info.)
    'OK': 
        (100, "Information request completed successfully."),
    'SUBMISSION_LATE': 
        (101, "Request successful, although assignment is late."),

    ## 200s: Change successfully completed, affecting grade/system state.
    'DONE': 
        (200, "Process completed successfully and system state "
        "has been updated."),

    ## 300s: User's request accepted successfully, 
    ## but for some (server-side) reason the next step cannot be 
    ## completed (right now).
    'ASSIGNMENT_COMPILE_FAILED': 
        (311, "The submitted assignment did not compile successfully "
        "on its own."),
    'GRADING_METHOD_UNDEFINED': 
        (312, "The grading of this submission has been skipped because "
        "there is neither a compile nor grading command defined for "
        "its file type in EXT_HANDLERS."),

    ## 400s: Error due to bad user input; could not proceed.
    # Authentication problems:
    'INVALID_USERNAME': 
        (401, "Could not authenticate user: invalid username given."),
        # INVALID_USERNAME can also occur if the password file is mangled or
        # USER_FILE_DELIM doesn't match what's actually used in the file.
    'INVALID_PASSWORD': 
        (402, "Could not authenticate user: invalid password given."),

    # General filename problems 
    'INVALID_CHARS': 
        (411, "Your filename contains invalid characters.  It should only "
        "contain simple ASCII letters, numbers, and/or a dot (.)." ),
    'BAD_EXTENSION': 
        (412, "Your filename does not end with exactly one file extension "
        "(such as <code>.java</code> or <code>.txt</code>)."),
        # note that file submission processing currently assumes only 
        # one . in a filename.
    'BAD_ASSIGNMENT': 
        (413, "Your filename does not end with the assignment name in "
        "the form of A## or A##c.  The assignment name must contain "
        "one capital letter followed by two digits (and possibly one " 
        "lowercase letter, depending on the assignment)."),
    'NO_USER_NAME': 
        (414, "Your filename does not begin with a username before "
        "the <code>A##</code> assignment name."),
    'USERNAME_NOT_LOWERCASE': 
        (415,  "The username portion of your file name is not lowercased. "
        "While the first letter may be capitalized, the rest of your "
        "username must be all lowercase letters."),
        # This ensures that, once the file is in the system, we won't have 
        # name-matching failures on case-sensitive OSs.
    'BAD_FILENAME': 
        (418, "Your filename is invalid in some way that Tamarin could not "
        "clearly identify."),
    'NO_SUCH_ASSIGNMENT': 
        (419, "Tamarin does not know anything about the assignment you "
        "specified and so cannot grade or otherwise display information "
        "about it. Please check that you specified the correct assignment "
        "number, including any required lowercase letters (such as A07a "
        "rather than only A07)."),
        # NOTE: This error can also result from a missing "-date-time" format 
        # on the assignment dir on server.

    # General file (contents) problems  
    'NO_FILE_UPLOADED': 
        (420, "You did not successfully upload a file."),
    'EMPTY_FILE': 
        (421, "The file you uploaded is empty."),
    
    # Assignment's type-specific filename checks 
    'WRONG_EXTENSION': 
        (430, "Your file's type/extension does not match the one required "
        "by this assignment."),
    'NO_INITIAL_CAP': 
        (431, "Your filename does not begin with a capital letter."),
    'BINARY_FILE': 
        (432, "Your file is not plain text but instead contains "
        "non-standard characters."),

    # Submission context problems
    'NO_UPLOADED_FILE': 
        (441, "There is no uploaded file that corresponds to the given "
        "username and assignment.  View your submissions it see if your "
        "file was already successfully submitted.  If it was not, please "
        "try submitting again."),
    'SUBMISSION_TOO_LATE': 
        (442, "Tamarin cannot accept your submission because the final "
        "cut-off date for this assignment has already passed."),
    'RESUBMISSION_LATE':
        (443, "The deadline for this assignment has passed, and "
         "Tamarin is currently configured to prohibit late resubmissions. "
         "You will be graded based on the file(s) you already submitted "
         "for this assignment."),
    'PREVIOUS_SUBMISSION_VERIFIED': 
        (444, "You may not resubmit this assignment because a previous "
        "submission has already been verified/graded by a human."),

    ## 500s: Error due to something wrong on server-side; could not proceed.
    'UNHANDLED_ERROR': 
        (500, "Sorry, but something unexpected just happened and "
        "Tamarin crashed."),
          
    # 50?s: Configuration problems         
    'BAD_SUBMITTED_FORM': 
        (501, "Your submitted information is missing certain required "
        "details or is improperly formatted, probably due to an error "
        "in the form you just submitted."),
    'NO_USERS_FILE': 
        (502, "Could not authenticate user: USERS file is missing or "
        "unopenable."),
    'MALFORMED_USERS_FILE': 
        (503, "Could not authenticate user: USERS file was openable, "
         "but its contents are not formatted properly."),
                    
    'BAD_ASSIGNMENT_DIR_FORMAT': 
        (505, "The name of the assignment directory on the Tamarin "
        "server for this assignment does not match the required format."),    
    'DUPLICATED_ASSIGNMENTS': 
        (506, "There is more than one assignment directory defined on the "
        "Tamarin server for this assignment."),        
    'UNDEFINED_TYPE': 
        (507, "There is no type defined in SUBMISSION_TYPES to handle "
         "the type specified by this assignment.  Therefore, Tamarin "
         "does not know how to compile or grade submissions for this "
         "assignment."),
    'INVALID_LATE_POLICY':
        (508, "One of the late policies specified is not in the correct "
         "format and could not be parsed."),
    'DUPLICATE_LATE_POLICY':
        (509, "More than one late policy covers the exact same span of time. "
         "While policy spans may overlap, idential spans create an ambiguity "
         "as to which late policy rule should be applied for that period."),
          

    # 510s: general file problems with things other than the grader 
    # processes or grader output file
    'GRADING_ERROR': 
        (510, "Something unexpected happened while trying to grade."),
    'NO_SUBMITTED_FILE': 
        (511, "Filename submitted for grading could not be found."),
    'BAD_GRADE_FILENAME': 
        (512, "Filename given for grading does not match the required "
         "format."),
    'NO_RESULTS_FILE': 
        (516, "Could not open the output grading results file (probably due "
         "to a permissions problem or a GRADED (sub)directory problem)."),
    'UNPREPABLE_GRADEZONE': 
        (517, "Could either not clear or not copy files into gradezone."),
        

    #520s: problems with a grader processes
    'GRADER_CRASH':
        (520, "A grading process just crashed unexpectedly with an " 
        "unanticipated error. See the Tamarin grading log for more "
        "information."),
    'COULD_NOT_STORE_RESULTS': 
        (521, "Could not write either the submitted file or the grader "
         "results file into the GRADED (sub)directory."),
    'INVALID_GRADE_FORMAT':
        (522, "A grading process or verifying human has returned a grade that "
         "does not match the allowed GRADE_RE format."),
    'INVALID_PROCESS_CONFIGURATION':
        (523, "A grading process has been incorrectly configured "
         "and so cannot run. The Tamarin grading log may have more "
         "information."),
    'GRADER_ERROR':
        (524, "A grading process has encountered a known error." 
         "See the Tamarin grading log for more information."),

    # 540s: view problems 
    # (though some actually come from GradedFile constructor)
'COULD_NOT_READ': 
        (541, "Could not read one of the files required to produce "
         "this view."),
    'NO_GRADER_RESULTS': 
        (542, "Found no grader output file for this (supposedly) "
         "graded file."),
    'MULTIPLE_GRADER_RESULTS': 
        (543, "Found multiple grader output files (instead of only one) "
         "associated with this graded file."),          
}


##
## FUNCTIONS
##

## ---Users and Authentication---

from core_type import TamarinError

def loadUserFile():
    """
    Loads user details from file specified in USERS_FILE.
    
    Returns a dictionary, keyed by username, where each value is a list of 
    all the other fields in the file: password, section, last, first.
    Lowercases all usernames.
    
    Otherwise raises a TamarinError('NO_USERS_FILE') if the USERS file does
    not exist or cannot be opened or a TamarinError('MALFORMED_USER_FILE')
    
    """
    try: 
        users = {}
        with open(USERS_FILE, 'r') as filein:
            i = 0
            for line in filein:
                i += 1
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  #skip comments or blank lines
                fields = [x.strip() for x in line.split(USERS_FILE_DELIM)]
                if len(fields) != 5:
                    raise TamarinError('MALFORMED_USER_FILE',
                        "Wrong number of data fields on line " + str(i) + ".")
                elif fields[0] in users:
                    raise TamarinError('MALFORMED_USER_FILE',
                        "User " + fields[0] + " is redefined on line " + \
                        str(i) + ".")
                users[fields[0].lower()] = fields[1:]
        return users
    
    except IOError:
        raise TamarinError('NO_USERS_FILE')

  
def authenticate(username, password):
    """
    Returns True if the given username and password are valid,
    as determined by examing the files specified in USERS file.
    
    Otherwise raises a TamarinError with one of the following keys:
    'NO_USERS_FILE', 'MALFORMED_USERS_FILE', 'INVALID_USERNAME', 
    or 'INVALID_PASSWORD'
    """
    users = loadUserFile()  #may raise TamarinError
    username = username.lower()
    if username not in users:
        raise TamarinError('INVALID_USERNAME')
    elif users[username][0] != password:
        raise TamarinError('INVALID_PASSWORD')
    else:
        return True

def getUsers():
    """
    Returns a sorted list of all usernames from USERS_FILE or throws a 
    TamarinError.  
    """
    return sorted(loadUserFile().keys())

def getUserDetails(username):
    """
    Returns all the supplemental fields in the USER_FILE for the given user.
    That is, everthing after the username and password fields: a list of
    [section, lastname, firstname].
    
    May throw 'NO_USERS_FILE' or 'INVALID_USERNAME' TamarinErrors.
    """
    users = loadUserFile()
    username = username.lower()
    return users[username.lower()][1:]


## --Printing---

def printHeader(title='Tamarin Results'):
    """
    Prints the necessary content type header and then the HTML page 
    header with the given title.
    """
    #print header
    print("Content-Type: text/html")
    print()
    #print HTML
    print("""\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
<meta name="author" content="Generated by Tamarin (by Z. Tomaszewski)">
<title>""" + title + """</title>
<link rel="stylesheet" href=""" + '"' + HTML_URL + 'tamarin.css" ' + \
"""type="text/css">
</head>

<body>
    """)

def printFooter():
    """
    Prints the page footers
    """
    print("""
<!-- ===========footer============== -->
<TABLE width="100%" border="0" class="footer" id="bottom">
<tr>
<td align="left" width="33%">
<a href="http://code.google.com/p/tamarin/">Tamarin</a> 
(&copy;2008-2012 by Z. Tomaszewski)
</td>
<td align="center">
""" + '<a href="' + HTML_URL + 'index.html">Home</a>' + """
</td>
<td align="right" width="33%">
Version: """ + TAMARIN_VERSION + """
</td>
</tr>
</TABLE>

</body>
</html>
    """)

def printError(error):
    """
    Prints both Tamarin status code messages or other kinds of error mesgs.
    Error should be a TamarinError object or a string message.
    If you want a full traceback, send in 'UNHANDLED_ERRROR'.

    """
    if not isinstance(error, TamarinError):
        if isinstance(error, str):
            error = TamarinError(error)
        else:
            error = TamarinError(type(error).__name__, str(error))
    print('<div class="error">')
    print('<p class="error">')
    if error.key in STATUS:    
        #use standard error message format
        print('<b>Tamarin Error ' + str(STATUS[error.key][0]) + ':</b> ')
        print(STATUS[error.key][1])
        print('<small>(' + error.key, end='')
        if error.details:
            print(': ' + error.details, end='')
        print(')</small></p>')

        if STATUS[error.key][0] >= 500: 
            #sys-config problems, so also let users know who to contacts
            if error.key == 'UNHANDLED_ERROR':
                #add message and traceback
                print('<pre class="error">')
                traceback.print_exc(file=sys.stdout)
                print('</pre>')

            print('<p>There seems to be a problem with the Tamarin '
                'server or its configuration.  You may want to try what '
                'you were doing again. However, if this same problem '
                'perists, please copy and paste the complete error '
                'message above (including any Traceback information) '
                'and email it to ')
            if ADMIN_EMAIL:
                print(ADMIN_EMAIL)
            else: 
                print('your Tamarin administrator '
                      '[<i>email address unknown</i>]')
            print(' so that the problem can be fixed. ')
            print('Thanks, and sorry for the inconvenience.</p>')
    else:
        #not in STATUS
        print('<b>Nonstandard Tamarin Error:</b> ')
        print(error.key, end='')
        print((": " + error.details) if error.details else '')
        print('</p>')
    print('</div>')


## ---Utility---

def convertTimeToTimestamp(time=None):
    """
    Converts the given datetime object to a string in the Tamarin timestamp
    format of YYYYMMDD-HHMM.  If not given, uses current time.
    """
    if not time:
        time = datetime.datetime.now()
    stamp = str(time.year) 
    stamp += str(time.month).zfill(2) + str(time.day).zfill(2)
    stamp += '-' + str(time.hour).zfill(2) + str(time.minute).zfill(2)
    return stamp  

def convertTimestampToTime(timestamp=None):
    """
    Returns the given Tamarin timestamps converted to a datetime object.
    """
    if not timestamp:
        timestamp = convertTimeToTimestamp()
    match = re.match(r"(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)$", timestamp)
    assert match, 'Bad deadline timestamp format: ' + str(timestamp)

    #convert matches to ints and label
    elements = [int(g) for g in match.groups()]
    year, month, day, hour, minute = elements     

    #return new datetime object
    return datetime.datetime(year, month, day, hour, minute)


def getAssignments():
    """
    Returns a sorted list of assignment names, pulled from GRADED_ROOT.
    """
    assignments = glob.glob(os.path.join(GRADED_ROOT, '*'))
    assignments = [re.match(ASSIGNMENT_RE, os.path.basename(a)).group(1) 
                           for a in assignments]
    assignments.sort()
    return assignments        
    
def getSubmissions(user=None, assignment=None, 
                   graded=True, submitted=True):
    """
    Returns a list of filename paths for the given combo of user and 
    assignment, which should both be strings.  Either may be None.
    For example, if user is not specified, returns all files for the given 
    assignment.  If both are None, returns all submitted files for all 
    assignments.  
    
    If submitted is False, will exclude files in SUBMITTED_ROOT.
    If graded is False, will exclude files found under GRADED_ROOT.
    Thus, set these to False if you want to filter out certain files.
    If both are False, no files will be found.
    
    Username does not need to be all lowercase.
    
    Returned filenames may point to files either in SUBMITTED_ROOT or in 
    a GRADED_ROOT subdirectory.  Files are sorted by timestamp.
    """
    # Future: 
    # asObjects=False, which would encapsulate as SubmittedFile and GradedFile?
    # if no user or assignment, sort into assignment-user-timestamp order?
    #
    from core_type import Assignment
    if not assignment:
        assignments = getAssignments()
    else:
        assignments = [assignment]

    files = []
    for a in assignments:
        assignment = Assignment(a)
        if user:
            # support username having either upper or lowercase first letter
            user = user.lower()
            globFilename = '[' + user[0] + user[0].upper() + ']' + user[1:]            
        else:
            # grab all users
            globFilename = '*'
        globFilename += assignment.name + '-*.' + assignment.type.fileExt
        
        # get graded files 
        if graded:
            afiles = glob.glob(os.path.join(assignment.path, globFilename))
            if assignment.type.fileExt == GRADER_OUTPUT_FILE_EXT:
                # need to drop grader output files from files list
                afiles = [f for f in afiles 
                            if re.match(SUBMITTED_RE, os.path.basename(f))]
            files.extend(afiles)
        
        # add any ungraded submitted files
        if submitted:
            sfiles = glob.glob(os.path.join(SUBMITTED_ROOT, globFilename))
            files.extend(sfiles)
    
    # sort using timestamp as the key  
    files.sort(key=lambda x: 
                re.match(SUBMITTED_RE, os.path.basename(x)).group(3))
    return files
                
def getSubmittedFilenames(only=None):
    """
    Returns a list of those files in SUBMITTED, sorted by timestamp.
    Includes the full pathname to the files.  If only is specified,
    will return only those files containing that string.
    """
    if only:
        submitted = glob.glob(os.path.join(SUBMITTED_ROOT, '*' + only + '*'))
    else:
        submitted = glob.glob(os.path.join(SUBMITTED_ROOT, '*'))
    #sort using timestamp as the key
    submitted.sort(key=lambda x: re.search(r"\d{8}-\d{4}", x).group())
    return submitted
