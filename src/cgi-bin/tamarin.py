##
## tamarin.py
## Part of Tamarin, by Zach Tomaszewski.  
## Created 06 Jun 2008.
##
## This is the core code of Tamarin shared by most of the cgi-bin files.
## All configuration details are in this file. 
## 
## For an overview of the system as a whole, see the documentation at:
## http://code.google.com/p/tamarin/
##

import cgi
import datetime   # for determining submission lateness, etc
import glob       # to check for file existence
import os.path    # for checking file existence and joining paths
import re         # to compare/process timestamps, etc
import shutil     # for actually moving files around
import sys        # for crash/error reporting
import traceback  # for crash/error reporting

##
## CONFIGURATION Globals
##

## ---FOLDERS----
## Defines the locations and directory structure that Tamarin uses.
## Do not include any path separators (such as /) in the folder names.
## 

# Where the Tamarin .html and .css files are located.
# This is specified relative to the web server's htdocs root.
# Leave empty to use htdocs root.
# 
HTML_ROOT = 'tamarin'

# Where the .py cgi scripts are located 
# (If changed, also update any saved generated .html files, such as 
#  upload.html)
#  
CGI_ROOT = 'cgi-bin'

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
# that assigment.  Assignment folder format is: A##-YYYYMMDD-HHMM  
# That is, the assignment name followed by the due date and time.
# Can optionally include a -# at end, were # is a total score value
# for that assignment (as an integer of 1 or more digits).
# Can also optinally include a -ext at the end, where ext is the
# type extension required for submitted work.
# 
GRADED_ROOT = os.path.join(TAMARIN_ROOT, 'graded')

#Where a subfolder for each assignment (in format of [A-Z]\d\d\w?)
# holds the necessary grader and any extra files need for 
# grading that assignment.  
# Every assignment folder must contain at least one file.
# Any files that should be present for every grading session can
# be placed in the GRADERS_ROOT directory itself. 
# 
GRADERS_ROOT = os.path.join(TAMARIN_ROOT, 'graders')

# When using the strip tool offered through masterview.py,
# where to dump the files after stipping off the timestamps.
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
GRADEPIPE_OUT = os.path.join(STATUS_ROOT, 'gradepipe.output')

# The command needed to spawn the gradepipe (relative to CGI_ROOT) 
# as a separate process.  Used in submit.py. 
# 
# On Unix: './gradepipe.py' (or the full path)
# 
# On Windows: "python gradepipe.py" or "pythonw gradepipe.py"
#             (preferably, with full path to python)
#             
GRADEPIPE_CMD = 'pythonw ./gradepipe.py'

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

# The default total number of points each assignment is worth (though
# this can then be overridden by particular assignments in their 
# directory name).
# 
ASSIGNMENT_TOTAL = 5

# The default submission type (as a string) for submitted files.
# Can be overridden by particular assignments in their directory name.
# 
ASSIGNMENT_TYPE = "java"

# Default extension of grader files.  (There is no danger of overwriting 
# submitted .txt files because a grader output file always has at least 
# "-" appended to the filename.  However, you may want to use "grd" if
# you are grading a lot of txt files so you can easily differentiate the
# two in directory listings.)
# 
GRADER_OUTPUT_FILE_EXT = "txt"

# The collection of late policies for this class. See LatePolicy documentation 
# (far below) for details of policy formats and how they are applied.  
#
# This variable is a dictionary of policies that are applied to each
# assignment based on the longest match with the given assignment name.  
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
# determined by the timestamp of the last submission.
# 
LATE_POLICY = {
# Examples.  Uncomment to activate:
#    '': ':',  #global, allows late submissions at no penalty
#    'A': ('+2d:-10%', '+5d:-30%'),  #for only 'A..'-named assignments
#    'A01': '+5d:-0',
}

# The maximum number of times a student may resubmit an submission per
# assignment.  -1 means unlimited and 0 means no resubmissions.
#  
MAX_RESUBMISSIONS = -1

# Number of points to take off of the final submission for each 
# resubmission made.  Value may be either a number or a string.  If a string,
# it must be in the form of a number, optionally followed by % or $.  As for
# late policies, % means subtract the given percentage of the assignment total
# and $ means subtract the given percentage of the student's final score for
# each resubmission.  Unlike late policy specifiers, number value may be 
# floating point. 
# 
RESUBMISSION_PENALTY = 0.1

# Whether students may resubmit at any time they could turn in an original
# submission.  Set to False to allow resubmissions only before the assignment
# deadline.
#
ALLOW_LATE_RESUBMISSIONS = True

# If True, will accept resubmissions even after a human has verified the grade
# of a previous submission.  Use this if you (the human) want to keep grading 
# submissions until the student is satisfied with their grade; set to False if
# you only want to personally grade each assignment once for each student.
#
RESUMBIT_AFTER_HUMAN = False




# How to handle submissions/assignments with different file extensions.
# That is, how should each extension be processed.
# For each extension, specify:
# [compile command,
#  compile output file ext (replaces the original extension),
#  grade command, 
#  binary file type?, 
#  require init capital in filename?
#  display as code (using PRE without word wrap)?]
# If an extension does not need to be compiled or graded, put None for that
# command.  The following strings in the command will be replaced accordingly:
#   $F - the submitted file
#   $A - the assignment name for the submitted file
#   $C - whether the assignment compiled successfully (1 or 0; GRADE_CMD only)
# For security purposes, the full path to the command should be given.
# 
COMPILE_CMD = 0; 
COMPILED_EXT = 1; #Used to see if compilation was successful by producing such a file
                  #If set to None, no compiler output to stdout is assumed to mean success
                  #If set to '', the produced file has no extension
GRADE_CMD = 2; 
IS_BINARY = 3; 
REQ_INITIAL_CAP = 4; 
DISPLAY_AS_CODE = 5;
EXT_HANDLERS = {
 'java': ['javac $F',
          'class',
          'java $AGrader $F $C',
          False, True, True],
 'txt':  [None, 
          None, 
          'java $AGrader $F $C', 
          False, False, False],
 'zip':  [None, None, None, 
          True, False, False],
}

# Occasionally a weird submission or poorly written grader will cause
# problems that cause the grader to crash with an error message.
# This message will get logged in the status/grader.output file, and 
# more info will be in the particular grade results file, only in a 
# -.txt file (that is, no grade as part of the name).  However, in the 
# past, the actual submitted file would be just left in the SUBMITTED 
# directory (since it was not successfully graded). While possibly handy 
# for offline grading, this means Tamarin tries to grade the bad 
# submission each time a new submission comes in.  Set this variable to
# True if you want such a problem submission file to just be moved into 
# the graded directory with an ERR grade.
# 
MOVE_PROBLEM_FILES_INTO_GRADED_DIR = True





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

# Whether masterview.py links should open in a new window
# 
MASTER_LINKS_OPEN_NEW_WINDOW = True

# TamarinGrader.java marks all of its output lines with a prepend 
# string ("## " by default).  Set this variable to the same prepend 
# string if you want to turn on grader output highlighting.  
# Specifically, if this variable contains anything, all lines starting
# with the given string will be wrapped by a 
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
# The remainder of the code in this file are essential Tamarin classes and
# functions used across all tamarin components.
# 


##
## PROGRAM CONSTANTS 
## (Do not touch these as a user or admin!)
##

# The date of the last edit of this version 
# (shown in the footers of generated pages)
# 
TAMARIN_VERSION = '29 May 2012'

# The regex for an assignment name.
# Formed by a capital letter, a 2-digit number, and an optional 
# lowercase letter. (See class Assignment for the corresponding 
# directory format.) 
# 
ASSIGNMENT_RE = r"([A-Z]\d\d[a-z]?)"

# A filename extension, including the initial dot.  The extension
# may include multiple dots, such as for .tar.gz
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

# The regex for a student submission after it has been submitted:
# basically, as UPLOADED_RE, but with YYYYMMDD-HHMM timestamp added.
# 
SUBMITTED_RE = r"^(\w+)" + ASSIGNMENT_RE + r"-(\d{8}-\d{4})" + EXTENSION_RE

# The regex for a grade, which is either C, NC, ERR, or an integer
# or decimal number.  Grading errors usually produce a file with 
# only a - or -ERR.  * (0 or more) is used to match the - case.
# 
GRADE_RE = r"([NCER\d\.]*)"

# The regex for an assignment after it has been graded:
# basically, as SUBMITTED_RE, but with grading outcome added.
# Requires a '-' after the timestamp, and then a grade.
# After grading outcome, may include an optional -H, -C, or -HC
# for human-verified or comment.
# 
GRADED_RE = (r"^(\w+)" + ASSIGNMENT_RE + r"-(\d{8}-\d{4})-" + 
             GRADE_RE + r"(-[HC]+)?" + EXTENSION_RE)

# Status Codes (inspired by HTTP, but specific to Tamarin)
# stored as dictionary of tuples: {'KEY': (CODE, Message), 'KEY2': ...}
# 
# 
STATUS = {
    # (In retrospect, I'm not sure if this was a useful design choice 
    # or not. Originally, Tamarin did not use TamarinErrors or exception
    # handling.  Now that it does, having all error descriptions in one
    # place might still be useful... maybe for I18N?)

    #100s: Successful idempotent or informational requests only. 
    #      No change to grade/system state.  
    #      (These status messages usually replaced by returned info.)
    'OK': 
        (100, "Information request completed successfully."),
    'SUBMISSION_LATE': 
        (101, "Request successful, although assignment is late."),

    #200s: Change successfully completed, affecting grade/system state.
    'DONE': 
        (200, "Process completed successfully and system state "
        "has been updated."),

    #300s: User's request accepted successfully, 
    #      but for some (server-side) reason the next step cannot be 
    #      completed (right now).
    'ASSIGNMENT_COMPILE_FAILED': 
        (311, "The submitted assignment did not compile successfully "
        "on its own."),
    'GRADING_METHOD_UNDEFINED': 
        (312, "The grading of this submission has been skipped because "
        "there is neither a compile nor grading command defined for "
        "its file type in EXT_HANDLERS."),

    #400s: Error due to bad user input; could not proceed.
    #authentication problems:
    'INVALID_USERNAME': 
        (401, "Could not authenticate user: invalid username given."),
        # INVALID_USERNAME can also occur if the password file is mangled or
        # USER_FILE_DELIM doesn't match what's actually used in the file.
    'INVALID_PASSWORD': 
        (402, "Could not authenticate user: invalid password given."),

    #filename problems  
    'NO_FILE_UPLOADED': 
        (410, "You did not successfully upload a file."),
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
        #This ensures that, once the file is in the system, we won't have 
        #name-matching failures on case-sensitive OSs.
    'NO_INITIAL_CAP': 
        (416, "Your filename does not begin with a capital letter."),
    'BAD_FILENAME': 
        (417, "Your filename is invalid in some way that Tamarin could not "
        "clearly identify."),
    'NO_SUCH_ASSIGNMENT': 
        (418, "Tamarin does not know anything about the assignment you "
        "specified and so cannot grade or otherwise display information "
        "about it. Please check that you specified the correct assignment "
        "number, including any required lowercase letters (such as A07a "
        "rather than only A07)."),
        #NOTE: This error can also result from a missing "-date-time" format 
        #on the assignment dir on server.
    'WRONG_EXTENSION': 
        (419, "Your file's type/extension does not match the one required "
        "by this assignment."),

    #file content problems
    'EMPTY_FILE': 
        (431, "The file you uploaded is empty."),
    'BINARY_FILE': 
        (432, "Your file is not plain text, but instead contains "
        "non-standard characters."),
#TODO: details: what encoding was expected?

    #submission context problems
    'SUBMISSION_TOO_LATE': 
        (441, "Tamarin cannot accept your submission because the final "
        "cut-off date for this assignment has already passed."),
    'NO_UPLOADED_FILE': 
        (442, "There is no uploaded file that corresponds to the given "
        "username and assignment.  View your submissions it see if your "
        "file was already successfully submitted.  If it was not, please "
        "try submitting again."),
    'PREVIOUS_SUBMISSION_VERIFIED': 
        (443, "You may not resubmit this assignment because a previous "
        "submission has already been verified/graded by a human."),

    #500s: Error due to something wrong on server-side; 
    #      could not proceed.
    'UNHANDLED_ERROR': 
        (500, "Sorry, but something unexpected just happened and "
        "Tamarin crashed."),
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
        "server for this assignment does not contain the due date/time "
        "in the correct format."),    
    'DUPLICATED_ASSIGNMENTS': 
        (506, "There is more than one assignment directory defined on the "
        "Tamarin server for this assignment."),
        
'UNHANDLED_FILE_EXTENSION': (507,
"There is no EXT_HANDLER defined to handle the file type/extension required by "\
"this assignment, thus Tamarin doesn't know how to compile or grade this "\
"kind of file."),

    #510s: general file problems with things other than the grader files
'GRADING_ERROR': (510,
"Something unexpected happened while trying to grade. "\
"Either files could not be copied or the grader could not be started "\
"(probably due to permissions problems or failure to fork a process)."),
'NO_SUBMITTED_FILE': (511,
"Filename submitted for grading could not be found."),
'BAD_GRADE_FILENAME': (512, 
"Filename given for grading didn't match the proper format."),
'NO_RESULTS_FILE': (516,
"Could not open the output grading results file (probably due to "\
"a permissions problem or GRADED (sub)directory problems). "),
'UNPREPABLE_GRADEZONE': (517,
"Could not copy files into gradezone."),
'COULD_NOT_STORE_RESULTS': (518,
"Could not move either the submitted file or the text file of graded results "\
"into the GRADED (sub)directory."),

    #520s: problems with the grader
'NO_GRADER_DIR': (524,
"There is no grader directory established for this assignment."),
'NO_GRADER_FILES': (525,
"There is a grader directory established for this assignment, "\
"but it is empty."),
'GRADER_FAILED': (528, 
"The grader produced some stderr output to Tamarin "\
"but failed to actually provide a grade."),
'NO_GRADER_OUTPUT': (529, 
"The grader failed to produce any stderr report back to Tamarin."),

    #540s: view problems 
    #      (though some actually come from GradedFile constructor)
'COULD_NOT_READ': (541,
 "Could not read one of the files required to produce this view."),
'MULTIPLE_GRADER_RESULTS': (542, 
 "Just found multiple grader output files (instead of only one) "\
 "associated with this graded file."),
'NO_GRADER_RESULTS': (543, 
 "Found no grader output file for this (supposedly) graded file."),
}



##
## CLASSES
##

class TamarinError(Exception):
    """
    Represents some sort of error status code, usually in the 400s or 500s.
    See STATUS for more.
    """

    def __init__(self, key, details=None):
        """
        The first argument given should be a legal STATUS key for the 
        specific error.  Additional details may also be given as an 
        extra argument.
        
        If key is not valid, it may be treated as a special error message
        instead.
        
        Arguments may later be retrieved either as Exception args or 
        instance variables.
        """
        Exception.__init__(self, key, details)
        self.key = key
        self.details = details
    

class LatePolicy:
    """
    A policy that specifies grade changes based on a submission's timestamp.
    
    Each such policy covers a specific timespan (range) either before or 
    after the assignment's deadline.  (Most ranges will be after the deadline, 
    but it is possible to specify a preceding time range in order to implement
    bonus points for early submission.)  Each timespan corresponds to a 
    single rule that specifies how a final grade should be modified for 
    submissions submitted during that timespan.  See __init__ for details of 
    how to specify policies, including the format for a timespan range and the 
    corresponding rule.  
    
    An assignment may have more than one LatePolicy.  This allows for both
    a "negative" bonus point late policy for early submission as well as a
    late policy.  It is also useful for different policies depending on the
    degree of lateness.  (For example, 2 points off for the first 2 days late
    and then 5 points off for up to 5 days late.) If more than one overlapping
    timespan is specified by 2 or more policies, the rule of the shortest 
    (ie, closest to the deadline) applicable timespan is applied.  
    
    If an assignment is submitted after the deadline and after the last 
    post-deadline span, it will not be accepted by Tamarin.  
    The submission is too late.
    
    Once in the system, an assignment timestamped before the first pre-deadline
    span (if any) is treated as having a timestamp of the start of that span.
    Similarly, those timestamped after the last post-deadline span are treated
    as if submitted at the final cutoff time.  For example, if an instructor 
    manually uploads a submission timestamped after the final cutoff date, 
    the longest span late policy will still be applied to that submission.
    
    """
    
    def __init__(self, policy='0m:'):
        """
        Constructs a LatePolicy according to the given policy string.  
                
        Each policy should be a string in the form of: 'range:rule'
        
        A range has the following format: [+|-][[#d][#h][#m]|timestamp]
        
        That is, the range may optionally begin with either + or -.  
        If the sign is omitted, + is assumed.  
        
        The sign may then be followed by a span specified in days, 
        hours, and minutes.  This span is relative to the assignment deadline,
        either earlier (if sign is -) or later (if sign is +).  A particular
        unit may be omitted if unused; it will be assumed to be 0.  If more 
        than 23 hours or 59 minutes are specified, the correponding overflow 
        into days and hours will be calculated.
        
        As an alternative to specifying a relative span, a specific timestamp
        may be given.  (The sign is ignored in this case.)  
        
        If neither span nor timestamp is given, the end of the span is 
        treated as year 0 for a - sign or year 9999 for a positive sign.
        (Since LatePolicies usually apply across multiple assignments, 
        specific timestamps are rare.  However, they can be handy to specify
        a final cutoff date for all assignments--such as the last day of the
        course.)
        
        The range is then separated from the associated rule by a colon (:).
        
        The rule is of the form: [+|-|=][#[%|$]][/[#d][#h][#m]]

        That is, the rule may begin with a sign: +, -, or =.  If omitted,
        = is assumed.  The sign specifies whether the grade should be 
        increased by (+), decreased (-) by, or set equal to (=) the following
        value. 
        
        The sign is followed (optionally) by an integer value, which 
        may be appended by either % or $.  (A missing value is treated
        as 0.)  Without a modifier, the value is treated as a raw point 
        modifer.  If appended with a %, this is a percentage of the 
        assignment's total possible score.  If appended with a $, 
        it is a percentage of the submission's actual score.
        
        Optionally, the modifier may be followed by a / and relative span.
        At least one value--whether day, hour, or minutes--must be given
        after a /.  When such a span is given, the modifier is applied for 
        each span that the assignment is late.  For example, /1d means apply
        the modifier for each day.  Such as span does nothing if applied to 
        an = modifier.  If this rule is associated with an -timespan ("bonus 
        policy"), it is applied for each full span. Otherwise, it is applied 
        for each partial span.
                
        Examples:
        +5d:-1/1d - For up to 5 days after the deadline, submissions suffer 
        a penaly of 1 point off for each (partial) day.
        
        +48h:-10% - For 2 days after the deadline, any submission loses 10% 
        of the assignment total.  (So, for a 5 point assignment, this would 
        be -1 point.)  Equivalent to '2d:-10%' (if relying on the assumed 
        + sign on the timespan.).
        
        -3d:+5$/1d - An example of an "early bonus" policy, this grants a 
        cumulative bonus of 5 percent of the submission's score for each full 
        day early.
        
        20121221-1200:40$ - Using a timestamp to define the span, anything 
        submitted after the deadline but before noon on 21 Dec 2012 will 
        receive 40% of the score it would otherwise have received.  
        (:=40$ or :-60$ would also have been equivalent rules, since = is 
        assumed on rules without a sign.)
        
        1d: - Anything submitted for up to 1 day past the deadline is worth 0.
        
        Given only the policies above, any submissions later than the deadline
        plus the given late period timespan would be refused by Tamarin.
        
        :10% - Anything submitted after the deadline, no matter how late or 
        how bad, is given 10% of the total possible assignment value.  
        
        : - Anything submitted after the dealine is accepted but is worth 0.
        
        0m: - Since anything after the deadline would also be after this 
        policy, this refuses any late work.  This is the default LatePolicy.
        
        """

#can take a seq of  str or LatePolicy.  
#If more than 1, builds a LatePolicy of them all
# isLate()
# isTooLate()
# getGrade(timestamp, score, total)
# getLateOffset()
#
# Cascading policies based on assignment name matches!  And a global default.

    
class Assignment:
    """
    Represents an assignment folder, as found in the GRADED_ROOT directory.

    Thus, an Assignment instance includes the assignment's due date, 
    total point value, submission type, etc. If the total point value 
    or type is not defined explicitly by the directory name itself, 
    ASSIGNMENT_TOTAL or ASSIGNMENT_TYPE is used instead. 
    """
    def __init__(self, assignment):
        """
        Given the assignment name in the form of ASSIGNMENT_RE, loads
        the details of the assignment as an object.  Details include:

        * name -- short general name, of the form A##a
        * path -- the complete path to the assignment directory
        * dir  -- just the directory name
        * due  -- when the assignment is due (in Tamarin timestamp format)
        * maxScore -- the max score or total value of this assignment
        * type -- the required SubmissionType for submissions

        If the given assignment name is not of the correct format, throws an
        AssertionError.

        If the given assignment does not exist, throws a TamarinError
        with one of the following keys: 'NO_SUCH_ASSIGNMENT',
        'DUPLICATED_ASSIGNMENTS', or 'BAD_ASSIGNMENT_DIR_FORMAT'.
        """
        assert re.match(ASSIGNMENT_RE, assignment), \
            'Bad assignment format given.'
        assignDir = glob.glob(os.path.join(GRADED_ROOT, assignment + '-*'))
        if not assignDir:
            raise TamarinError('NO_SUCH_ASSIGNMENT', assignment)
        elif len(assignDir) > 1:
            #more than one matching directory found
            raise TamarinError('DUPLICATED_ASSIGNMENTS', assignment)

        #load object (part 1/2)
        self.name = assignment
        self.path = assignDir[0]
        self.dir = os.path.basename(self.path)
        
        #get details from dir name
        assignmentFormat = assignment + r"-(\d{8}-\d{4})(-(\d+))?(-(\w+))?$"
        match = re.match(assignmentFormat, self.dir)
        if not match: 
            raise TamarinError('BAD_ASSIGNMENT_DIR_FORMAT', self.dir)

        #load object (part 2/2)
        self.due = match.group(1)      
        if match.group(3):
            self.maxScore = int(match.group(3))
        else:
            self.maxScore = ASSIGNMENT_TOTAL
        if match.group(5):
            self.type = str(match.group(5))
        else:
            self.type = ASSIGNMENT_TYPE

    def __str__(self):
        """ Returns just the short name of this assignment """
        return str(self.name)

'''
    def isLate(self, submittedTime=None, comments=False):
        """
        Determine whether the submittedTime (in the format of 'YYYYMMDD-HHMM')
        occurs before this assignment's deadline.  If submittedtime is None,
        uses the current time as submittedTime.

        Returns 'OK' if the submit time is before deadline, 
        'SUBMISSION_LATE' if the the submit time is after the timestamp but
          before deadline + LATE_PERIOD
        'SUBMISSION_TOO_LATE' if the submit time is after deadline + LATE_PERIOD.

        If comments is True, will print an HTML comment containing the deadline
        and submit (current) time.
        """
    deadline = convertTimestampToTime(self.due)
    cutoff = deadline + datetime.timedelta(days=LATE_PERIOD)
    if not submittedTime:
      now = datetime.datetime.now()
    else:
      now = convertTimestampToTime(submittedTime)

    #print comments if requested
    if comments:
      print('<!--Current submit time: ' + now.isoformat(' ') + '-->')
      print('<!--Deadline: ' + deadline.isoformat(' ') + '-->')

    #results of time comparison
    if now < deadline: 
      return 'OK'
    elif now < cutoff:
      return 'SUBMISSION_LATE'
    else:
      return 'SUBMISSION_TOO_LATE'


class SubmittedFile:
  """
  Represents a file in SUBMITTED_ROOT that has completed its validation by submit.py
  and has been timestamped.
  
  Details include:
  * filename - the basename of the file
  * path - the full path of the file
  * username  - Username of the file's author
  * assignment - the name of the assignment this file was submitted for
               (not a full Assignment object)
  * timestamp - when the file was submitted
  * fileExt - the file extension
  * originalFilename - the filename without a timestamp
  
  If the virtual parameter is given, don't actually check that the file exists.
  """
  def __init__(self, filename, virtual=False):
    """
    If the given filename is not of the correct format, throws a
    TamarinStatusError('BAD_GRADE_FILENAME').

    If the given file does not exist in SUBMITTED, throws a 
    TamarinStatusError('NO_SUBMITTED_FILE').
    """
    #confirm format of filename
    fileMatch = re.match(SUBMITTED_RE, filename)
    if not fileMatch:
      raise TamarinStatusError('BAD_GRADE_FILENAME')
    self.filename = filename
    
    #check that file really exists.
    self.path = os.path.join(SUBMITTED_ROOT, filename)
    if not virtual and not os.path.exists(self.path):
      raise TamarinStatusError('NO_SUBMITTED_FILE')
    
    #load details from above match
    self.username = fileMatch.group(1).lower()
    self.assignment = fileMatch.group(2)
    self.timestamp = fileMatch.group(3)
    self.fileExt = fileMatch.group(4)
    self.originalFilename = fileMatch.group(1) + fileMatch.group(2) + '.' + \
                            fileMatch.group(4)

class GradedFile(SubmittedFile):
  """
  Represents a file in a GRADED_ROOT subdirector that has completed the grading process.
  
  Details are the same as for a SubmittedFile, plus:
  
  * graderPath - the full path to the grader output file
  * graderFilename - just the base name of the grader output file
  * grade - the grade from the grader file (or ERR if it can't be found)
  * humanVerified - the grade has been verified by a human
  
  If the virtual parameter is given, don't actually check that the file exists.
  Virtual will also supress reading the corresponding grade report, and so the
  instance will lack these attributes.
  """
  def __init__(self, filename, virtual=False):
    """
    Throws the same exceptions as a SubmittedFile.  
    May also throw exceptions to do with the assignment's directory not existing
    either.
    """
    #less superclass initialize everything
    SubmittedFile.__init__(self, filename, True)
    #now reset path variable
    assign = Assignment(self.assignment)
    self.path = os.path.join(GRADED_ROOT, assign.dir, filename)
    if not virtual and not os.path.exists(self.path):
      raise TamarinStatusError('NO_SUBMITTED_FILE')

    #add new details
    if not virtual:
      #add grader file details
      self.graderPath = self.path.replace("." + self.fileExt, 
                                          "-*." + GRADER_OUTPUT_FILE_EXT)
      gradeglob = glob.glob(self.graderPath)
      if not gradeglob:
        raise TamarinStatusError('NO_GRADER_RESULTS')
      elif len(gradeglob) > 1:
       raise TamarinStatusError('MULTIPLE_GRADER_RESULTS')
      else:
        self.graderPath = gradeglob[0]
      self.graderFilename = os.path.basename(self.graderPath)

      #try to pull grade from filename
      found = re.match(GRADED_RE, self.graderFilename)
      try:
        self.grade = float(found.group(4))
      except ValueError:
        self.grade = str(found.group(4))
        if not self.grade:
          self.grade = 'ERR' #empty string, as on a grader failure
      except:
        self.grade = 'ERR'  
      self.humanVerified = bool(found.group(5))



class SubmissionType:

    def __init__(self):
        self.fileExt
        self.processes  GradingProcess[]
        self.latePolicy
        
'''        
##
## FUNCTIONS
##

## Authentication

def loadUserFile():
    """
    Loads user details from file specified in USERS_FILE.
    
    Returns a dictionary, keyed by username, where each value is a list of 
    all the other fields in the file: password, section, last, first.
    
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

'''
def getUserDetails(username):
  #Future: Should probably make this a User class to be consistent
  """
  Returns the all the supplemental fields in the USER_FILE for the given user
  (that is, everthing after the username and password fields)
  or returns 'NO_USERS_FILE' or 'INVALID_USERNAME' instead.
  """
  users = loadUserFile()
  username = username.lower()
  if users == 'NO_USERS_FILE':
    return users
  elif username not in users:
    return 'INVALID_USERNAME'
  else:
    return users[username][1:]  #skip password; no need to be passing those around

def getUsers():
  """
  Returns a list of all usernames, or 'NO_USER_FILE' if there's an error.
  Note that in other places (such as displaycore.py) Tamarin expects usernames to
  be all lowercase.  (When they can occur as part of filenames, they can be lowercase
  or titlecase.)
  """
  users = loadUserFile()
  if users == 'NO_USERS_FILE':
    return users
  else:
    return users.keys()

'''  

## HTML printing    

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
<link rel="stylesheet" href=""" + '"' + HTML_ROOT + '/tamarin.css" ' + \
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
(&copy;2008 by Z. Tomaszewski)
</td>
<td align="center">
""" + '<a href="' + HTML_ROOT + '/index.html">Home</a>' + """
</td>
<td align="right" width="33%">
Version: """ + TAMARIN_VERSION + """
</td>
</tr>
</TABLE>

</body>
</html>
    """)

def printError(error, html=True):
    """
    Prints both Tamarin status code messages or other kinds of error mesgs.
    Error should be a TamarinError object or a string message.
    If you want a full traceback, send in 'UNHANDLED_ERRROR'.
   
    Can print in HTML with user-friendly messages, or not.
    """
    if not isinstance(error, TamarinError):
        if isinstance(error, str):
            error = TamarinError(error)
        else:
            error = TamarinError(type(error).__name__, str(error))
    if html:
        print('<div class="error">')
        print('<p class="error">')
        if error.key in STATUS:    
            #use standard error message format
            print('<b>Tamarin Error ' + str(STATUS[error.key][0]) + ':</b> ')
            print(STATUS[error.key][1])
            print('<small>')
            if error.details:
                print(error.args)
            else:
                print('(' + error.key + ')')
            print('</small></p>')

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

    else:
        #non-html version    
        print()
        if error in STATUS:
            print("ERROR " + str(STATUS[error.key][0]) + " (" + error.args + "): ")
            print(STATUS[error.key][1])
        else:
            print("Nonstandard Error: ")
            print(error.key)


## Other printing

def tprint(file, string, screen=True):
    """
    Primitive T (tee) printing.
    
    Prints the given string to both the given file and to stdout.  
    Adds a line break to file so output matches same as stdout when 
    using default print.

    If file=None, won't really print to file.  
    If screen=False, won't really print to screen.
    """
    
    #when input comes back from java or javac on Windows, it has 0D0A (\r\n)
    #line endings.  When writing this, python replaces the \n with the Windows
    #line ending, but this gives 0D0D0A (\r\r\n), which can mangle display in
    #browsers of <pre> content (comes out double-spaced).  
    #Hence, this fix here before writing any string:
    string = string.replace(chr(0x0D), '')
    
    if file:
        file.write(str(string))
        file.write('\n') #outputs 0D0A on Windows; os.linesep outputs as 0D0D0A
    if screen:
        print(str(string))


## Time and Assignment Processing

def convertTimeToTimestamp(time):
    """
    Converts the given datetime object to a string in the Tamarin timestamp
    format of YYYYMMDD-HHMM
    """
    stamp = str(time.year) 
    stamp += str(time.month).zfill(2) + str(time.day).zfill(2)
    stamp += '-' + str(time.hour).zfill(2) + str(time.minute).zfill(2)
    return stamp  


def convertTimestampToTime(timestamp):
    """
    Returns the given Tamarin timestamps converted to a datetime object.
    """
    match = re.match(r"(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)$", timestamp)
    assert match, 'Bad deadline timestamp format: ' + str(timestamp)

    #convert matches to ints and label
    elements = [int(g) for g in match.groups()]
    year, month, day, hour, minute = elements     

    #return new datetime object
    return datetime.datetime(year, month, day, hour, minute)
    

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

