#!python

##
## tamarin.py
## Part of Tamarin, by Zach Tomaszewski.  Created 06 Jun 2008.
##
## This is the core code of the Tamarin. 
## See README.txt for more of an overview of the system as a whole.
##

import cgi
import traceback  #for crash/error reporting
import sys        #same
import glob       #to check for file existance
import datetime   #for determining submission lateness, etc
import re         #to compare/process timestamps, etc

#used in multiple other tamarin modules:
import os.path         #for checking on file existance
import shutil          #for actually moving files around


##
## CONFIGURATION Globals
##

## ROOTS
## Root values should all begin with a /, but not end with one.

#Where the Tamarin .html and .css files are located, 
# specified relative to the webserver's htdocs root.
HTML_ROOT = '/tamarin'

#where the .py cgi scripts are located 
# (If changed, update upload.html too.)
CGI_ROOT = '/cgi-bin'

#Where Tamarin stores its config files and (usually) the parent
# directory of all the storage directories.
# For security purposes, should not be under the webserver's htdocs
# folder so that these files cannot be served by the httpd.
# Can be either absolute or relative to CGI_ROOT.
TAMARIN_ROOT = '../tamarin'

#The directories where submissions are stored at various points
# through the grading process.
UPLOADED_ROOT = TAMARIN_ROOT + '/uploaded'
SUBMITTED_ROOT = TAMARIN_ROOT + '/submitted'

#A directory for each assignment must be created manually 
# within GRADED_ROOT so that Tamarin knows it can accept submissions 
# for that assigment.
# Assignment folders format: A##-YYYYMMDD-HHMM  
# That is, the assignment name followed by the due date and time.
# Can optionally include a -# at end, were # is a total score value
# for that assignment (as an integer of 1 or more digits).
# Can also optinally include a -ext at the end, where ext is the file
# type extension required for submitted work.
GRADED_ROOT = TAMARIN_ROOT + '/graded'

#Where assignments are temporarily located during actual grading.
GRADEZONE_ROOT = TAMARIN_ROOT + '/gradezone'

#Where a subfolder for each assignment (in format of A\d\d\w?)
# holds the necessary grader and any extra files need for 
# grading that assignment.  
#Every assignment folder must contain at least one file.
#Any files that should be present for every grading session can
# be placed in the GRADERS_ROOT directory itself. 
GRADERS_ROOT = TAMARIN_ROOT + '/graders'

#When using the strip tool offered through masterview.py,
# where to dump the files after stipping off the timestamps.
STRIPPED_ROOT = TAMARIN_ROOT + '/stripped'

#Where to dump various files created as Tamarin runs to indicate
# its status.
STATUS_ROOT = TAMARIN_ROOT + '/status'

## USERS
## List of student account details

#Location of a plain text file containing 
# username, password, section, lastname, and firstname fields.
# Usernames must be all lowercase and at least 2 characters long.
USER_FILE = TAMARIN_ROOT + '/users.txt' 

#delimter used between fields in USER_FILE
USER_FILE_DELIM = '|'   


## GRADING

#Location (and name) of the file that indicates an instance of
# the gradepipe is up and running.
GRADEPIPE_ACTIVE = STATUS_ROOT + '/gradepipe.pid'

#Location (and name) of the file that indicates that the gradepipe
# is disabled.  (It will not be started again while this file exists.)
GRADEPIPE_DISABLED = STATUS_ROOT + '/gradepipe.off'

#The command needed to spawn the gradepipe (relative to CGI_ROOT) 
# as a separate process.  Used in submit.py. 
# On Unix: './gradepipe.py' (or the full path)
# On Windows: "python gradepipe.py" or "pythonw gradepipe.py"
#             (preferably, with full path to python)
GRADEPIPE_CMD = 'pythonw ./gradepipe.py'

#The webserver spawns a separate process to run gradepipe.py.
# However, on Apache, the parent web server process won't end due to how Apache
# deals with file descriptors: the spawned process inherits stdout, stdin,
# etc from its parent process, and so that parent process persists until they
# are closed. Therefore, all streams need to be redirected so gradepipe.py 
# will detatch cleanly.  
# (XXX: This fix works under Linux, but not under Windows.)
GRADEPIPE_IN = STATUS_ROOT + '/null.txt'
GRADEPIPE_OUT = STATUS_ROOT + '/gradepipe.output'

#The address given in 5?? error messages for users to send a heads-up to
ADMIN_EMAIL = 'admin@email.NOTSET'

#You can modify an assignment after it's graded, using the master view.
#When you do, you can append a comment to the graded file.  This is the
#description of such a comment
TA_COMMENT = 'Comment from TA:'

#The default total number of points each assignment is worth
# (but can be overriden by particular assignments in their directory name).
ASSIGNMENT_TOTAL = 5

#The number of days for which late assignments will be accepted (at penalty)
LATE_PERIOD = 2

#Number of points to deduct for a late submission
LATE_PENALTY = 1

#Number of point to take off of a very late submission.
# This is in addition  to the late penalty
VERY_LATE_PENALTY = 1

#Number of points to take off of the final submission for each resubmission made
RESUBMISSION_PENALTY = 0.1

#If True, will accept new work no matter how late it is (though it will be labeled as
# very late).
SUBMIT_VERY_LATE = False

#If True, will accept REsubmitted work no matter how late it is 
# (though it will still be labeled as such).
# Thus, even if SUBMIT_VERY_LATE is False, it is possible to allow resubmissions after
# the cut-off.  Or, if SUBMIT_VERY_LATE is True but RESUBMIT_VERY_LATE is False,
# students can submit very late work only if they have turned in nothing for that 
# assignment so far.
RESUBMIT_VERY_LATE = False

#If True, will accept resubmissions even after a human has verified the grade
# of a previous submission.  Use this if you (the human) want to keep grading 
# submissions until the student is satisfied with their grade; set to False if
# you only want to personally grade each assignment once for each student.
RESUMBIT_AFTER_HUMAN = False

#How very late work should be labelled (can include HTML)
# (Used in upload.py even if the work is not accepted)
VERY_LATE_LABEL = "<b>very late</b>"

#Though an unverified grade is already marked with a CSS style, 
# this label can also be appended immediately after any grade 
# that has not yet been verified by a human.
UNVERIFIED_GRADE_LABEL = " (tentative)"

#As above, but this is used in list view of AssignmentSubmissions and when
# displaying submissions
SHORT_UNVERIFIED_GRADE_LABEL = '<span class="unverified"><i>?</i></span>'

#Whether masterview.py links should open in a new window
MASTER_LINKS_OPEN_NEW_WINDOW = True

#The Java TamarinGrader marks all of its output lines with a prepend
# string ("## " by default).  Set this variable to the same prepend
# string if you want to turn on grader output highlighting. Specifically,
# if this variable contains anything, all lines starting with the given
# string will be wrapped by a <span class="graderOutputLine"> tag when 
# displayed by displaycore.py.
HIGHLIGHT_PREFIX = '## '

#If HIGHLIGHT_PREFIX is set, then will also check for the following
# elements within each line.  Elements must be found within [brackets].
# Wraps each in a span of class="grader+element".  So, for example, if
# a list element is PASS, any [PASS] found in a grader ouptut line
# would be replaced with [<span class="graderPASS">PASS</span>].
HIGHLIGHT_ELEMENTS = ['PASS', 'FAIL', 'PART', 'EXTRA']


## GRADERS

#The default file extension (without preceding .) that submitted files must have
# (but can be overridden by particular assignments in their directory name)
ASSIGNMENT_FILE_EXT = "java"

#Default extension of grader files.  (There is no danger of overwriting 
# submitted .txt files because the grader output file always has at least 
# "-" appended to the filename.  However, you may want to use "grd" if
# you are grading a lot of txt files to you can easily differentiate the
# two in directory listings.)
GRADER_OUTPUT_FILE_EXT = "txt"

#How to handle submissions/assignments with different file extensions.
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
MOVE_PROBLEM_FILES_INTO_GRADED_DIR = True

##
## STATIC Globals (don't touch these as an user/admin)
##

#The date of the last edit of this version (shown in footers of generated pages)
TAMARIN_VERSION = '10 Apr 2012'

#The regex that matches what a submission's filename should look like when uploaded:
# a username of 1 or more chars, the assignment number (A, followed by two digits, and
# an optional lowercase letter), and the file extension.
UPLOADED_RE =  r"^(\w+)(A\d\d[a-z]?)\.(\w+)$"
#The regex for an assignment after it has been submitted:
# basically, as UPLOADED_RE, but with timestamp added
SUBMITTED_RE = r"^(\w+)(A\d\d[a-z]?)-(\d{8}-\d{4})\.(\w+)$"
#The regex for an assignment after it has been graded:
# basically, as SUBMITTED_RE, but with grade added
# Will even catch failed grading files
GRADED_RE = r"^(\w+)(A\d\d[a-z]?)-(\d{8}-\d{4})-([NCER\d\.]*)(-H)?\.(\w+)$"


#Status Codes (inspired by HTTP, but specific to Tamarin)
#stored as dictionary: {'KEY': [CODE, Message], 'KEY2': ...}
STATUS = {
  #100s: Successful idempotent or informational requests only. 
  #      No change to grade/system state.  
  #      (These status messages usually replaced by returned info.)
  'OK': [100, "Information request completed successfully."],
  'SUBMISSION_LATE': [101, "Request successful, although assignment is late."],

  #200s: Change successfully completed, affecting grade/system state.
  'DONE': [200, "Process completed successfully"
    "and system state has been updated."],

  #300s: User's request accepted successfully, 
  #      but for some (server-side) reason the next step cannot be 
  #      completed (right now).
  'ASSIGNMENT_COMPILE_FAILED': [311,
    "The submitted assignment did not compile successfully on its own. "],
  'GRADING_METHOD_UNDEFINED': [312,
    "The grading of this submission has been skipped because there is neither "\
    "a compile nor grading command defined for its file type in EXT_HANDLERS."],

  #400s: Error due to bad user input; could not proceed.
  #authentication problems:
  'INVALID_USERNAME': [401,
    "Could not authenticate user: invalid username given."],
    #INVALID_USERNAME can also occur if the password file is mangled or
    # USER_FILE_DELIM doesn't match what's actually used in the file.
  'INVALID_PASSWORD': [402,
    "Could not authenticate user: invalid password given."],

  #filename problems  
  'NO_FILE_UPLOADED': [410,
    "You did not successfully upload a file."],
  'INVALID_CHARS': [411, 
    "Your filename contains invalid characters.  It should only contain letters, "
    "numbers, and/or a dot (.)." ],
  'BAD_EXTENSION': [412, 
    "Your filename does not end with exactly one file extension "
    "(such as <code>.java</code> or <code>.txt</code>)."],
    #note that file submission processing currently assumes only one . in a filename
  'BAD_ASSIGNMENT': [413, 
    "Your class name does not end with the assignment number in the form of A##" 
    " or A##c."],
  'NO_INITIAL_CAP': [414, 
    "Your file name does not begin with a capital letter."],
  'NO_USER_NAME': [415, 
    "Your file name does not begin with a username before the <code>A##</code>."],
  'USERNAME_NOT_LOWERCASE': [416,
    "The username portion of your file name is not lowercased. "
    "While the first letter may be capitalized, "
    "the rest of your username should be all lowercase letters."],
    #This ensures that, once the file is in the system, we won't have 
    #name-matching failures on case-sensitive OSs.
  'BAD_FILENAME': [417, 
    "Your filename is invalid in some way that Tamarin could clearly identify."],
  'NO_SUCH_ASSIGNMENT': [418,
    "Tamarin does not know anything about the assignment you specified "
    "and so cannot grade or otherwise display information about it. "
    "Please check that you specified the correct assignment number, "
    "including any required lowercase letters (such as A07a rather than only A07)."],
    #this error can also result from a missing "-date-time" format 
    #on the assignment dir on server
  'WRONG_EXTENSION': [419,
    "Your file's type/extension does not match the one required by this assignment."],
  
  #file content problems
  'EMPTY_FILE': [431,
    "The file you uploaded is empty."],
  'BINARY_FILE': [432,
    "Your file is not plain text, but instead contains non-standard characters."],
    
  #submission context problems
  'SUBMISSION_TOO_LATE': [441,
    "Tamarin cannot accept your submission because the final cut-off date "\
    "for this assignment has already passed."],
  'NO_UPLOADED_FILE': [442,
    "There is no uploaded file that corresponds to the given username and "\
    "assignment."],
  'PREVIOUS_SUBMISSION_VERIFIED': [443,
    "You may not resubmit this assignment because a previous submission has "\
    "already been verified/graded by a human."],

  #500s: Error due to something wrong on server-side; 
  #      could not proceed.
  'UNHANDLED_ERROR': [500,
    "Sorry, but something unexpected just happened and Tamarin crashed."],
  'BAD_SUBMITTED_FORM': [501,
    "Your submitted information is missing certain required details "\
    "or is improperly formatted, "\
    "probably due to an error in the form you just submitted."],
  'NO_USERS_FILE': [502,
    "Could not authenticate user: USERS file is missing or unopenable."],
  'BAD_ASSIGNMENT_DIR_FORMAT': [503,
    "The name of the assignment directory on the Tamarin server for this assignment "\
    "does not contain the due date/time in the proper format."],
  'DUPLICATED_ASSIGNMENTS': [504,
    "There is more than one assignment directory defined on the Tamarin server "\
    "for this assignment."],
  'UNHANDLED_FILE_EXTENSION': [505,
    "There is no EXT_HANDLER defined to handle the file type/extension required by "\
    "this assignment, thus Tamarin doesn't know how to compile or grade this "\
    "kind of file."],
    
    
  #grading problems (due to bad system state, hence 500 status)
  #510s: general file problems with things other than the actual grader files
  'GRADING_ERROR': [510,
    "Something unexpected happened while trying to grade. "\
    "Either files could not be copied or the grader could not be started "\
    "(probably due to permissions problems or failure to fork a process)."],
  'NO_SUBMITTED_FILE': [511,
    "Filename submitted for grading could not be found."],
  'BAD_GRADE_FILENAME': [512, 
    "Filename given for grading didn't match the proper format."],
  'NO_RESULTS_FILE': [516,
    "Could not open the output grading results file (probably due to "\
    "a permissions problem or GRADED (sub)directory problems). "],
  'UNPREPABLE_GRADEZONE': [517,
    "Could not copy files into gradezone."],
  'COULD_NOT_STORE_RESULTS': [518,
    "Could not move either the submitted file or the text file of graded results "\
    "into the GRADED (sub)directory."],  
  #520s: problems with the grader
  'NO_GRADER_DIR': [524,
    "There is no grader directory established for this assignment."],
  'NO_GRADER_FILES': [525,
    "There is a grader directory established for this assignment, "\
    "but it is empty."],
  'GRADER_FAILED': [528, 
    "The grader produced some stderr output to Tamarin "\
    "but failed to actually provide a grade."],
  'NO_GRADER_OUTPUT': [529, 
    "The grader failed to produce any stderr report back to Tamarin."],
        
   #540s: view problems (though some actually come from GradedFile constructor)
   'COULD_NOT_READ': [541,
     "Could not read one of the files required to produce this view."],
   'MULTIPLE_GRADER_RESULTS': [542, 
     "Just found multiple grader output files (instead of only one) "\
     "associated with this graded file."],
   'NO_GRADER_RESULTS': [543, 
     "Found no grader output file for this (supposedly) graded file."],
}


##
## CLASSES
##

class TamarinStatusError(Exception):
  """
  Represents some sort of error status code, usually in the 400s or 500s.

  Contains the status key (defined globally, above) of the specific error
  and (optionally) additional information.  (Note that, because Tamarin was
  originally written without using this exception, not all error statuses are
  reported by this mechanism.)
  """
  def __init__(self, status, details=None):
    Exception.__init__(self, status)
    self.details = details
    

class Assignment:
  """
  Represents an assignment folder, as found in the GRADED_ROOT directory.
  Thus, an Assignment instance includes the assignment's due date, 
  point value, allowed file extension, etc. (If the total score is not defined
  explicitly by the directory name itself, ASSIGNMENT_TOTAL is used instead.) 
  """
  def __init__(self, assignment):
    """
    Given the assignment name in the form of "A##" or "A##[a-z]", loads
    the details of the assignment as an object.  Details include:
    
    * name -- short general name, of the form A##
    * path -- the complete path to the assignment directory
    * dir  -- just the directory name
    * due  -- when the assignment is due (in Tamarin timestamp format)
    * maxScore -- the max score or total value of this assignment
    * fileExt -- the required file extension for submissions (without .)
    
    If the given assignment name is not of the correct format, throws an
    AssertionError.
    
    If the given assignment does not exist, throws a TamarinStatusError
    with one of the following statuses: 'NO_SUCH_ASSIGNMENT',
    'DUPLICATED_ASSIGNMENTS', or 'BAD_ASSIGNMENT_DIR_FORMAT'.
    """
    assert re.match(r"A\d\d\w?$", assignment), 'Bad assignment format given.'
    assignDir = glob.glob(os.path.join(GRADED_ROOT, assignment + '-*'))
    if not assignDir:
      raise TamarinStatusError('NO_SUCH_ASSIGNMENT', assignment)
    elif len(assignDir) > 1:
      #more than one matching directory found
      raise TamarinStatusError('DUPLICATED_ASSIGNMENTS', assignment)
    else:
      #get details
      assignmentFormat = assignment + r"-(\d{8}-\d{4})(-(\d+))?(-(\w+))?$"
      match = re.search(assignmentFormat, assignDir[0])
      if not match: 
        raise TamarinStatusError('BAD_ASSIGNMENT_DIR_FORMAT', assignDir[0])

      #load object
      self.name = assignment
      self.path = assignDir[0]
      self.dir = os.path.basename(self.path)
      self.due = match.group(1)      
      if match.group(3):
        self.maxScore = int(match.group(3))
      else:
        self.maxScore = ASSIGNMENT_TOTAL
      if match.group(5):
        self.fileExt = str(match.group(5))
      else:
        self.fileExt = ASSIGNMENT_FILE_EXT

  def __str__(self):
    """ Returns just the short name of this assignment """
    return str(self.name)

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
      print '<!--Current submit time: ' + now.isoformat(' ') + '-->'
      print '<!--Deadline: ' + deadline.isoformat(' ') + '-->'

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
        

##
## FUNCTIONS
##

## Authentication

def loadUserFile():
  """
  Loads user details from file specified in USERS.
  
  Returns a dictionary, keyed by username, where each value is a list of 
  all the other fields in the file.
  
  Otherwise returns 'NO_USERS_FILE' if the USERS file does not exist 
  or cannot be opened.
  """
  try: 
    userDict = {}
    filein = open(USER_FILE)
    for line in filein:
      fields = line.strip().split(USER_FILE_DELIM)
      userDict[fields[0]] = fields[1:]
    filein.close()
    return userDict
  
  except IOError:
    return 'NO_USERS_FILE'
    
  
def authenticate(username, password):
  """
  Returns 'OK' if the given username and password are valid,
  as determined by examing the files specified in USERS file.
  
  Otherwise returns 'NO_USERS_FILE', 'INVALID_USERNAME', or 'INVALID_PASSWORD'
  """
  users = loadUserFile()
  username = username.lower()
  if users == 'NO_USERS_FILE':
    return users
  elif username not in users:
    return 'INVALID_USERNAME'
  elif users[username][0] != password:
    return 'INVALID_PASSWORD'
  else:
    return 'OK'

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
  

## HTML printing    

def printHeader(title='Tamarin Results'):
  """
  Prints the necessary content type header and then the HTML page header
  (with the given title).
  """
  #print header
  print "Content-Type: text/html"
  print
  #print HTML
  print """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
<meta name="author" content="Generated by Tamarin (by Z. Tomaszewski)">
<title>""" + title + """</title>
<link rel="stylesheet" href=""" + '"' + HTML_ROOT + '/tamarin.css" ' + """type="text/css">
</head>

<body>
  """

def printFooter():
  """
  Prints the page footers
  """
  print """
<!-- ===========footer============== -->
<TABLE width="100%" border="0" class="footer" id="bottom">
<tr><td align="left" width="33%">Tamarin (&copy;2008 by Z. Tomaszewski)</td>
<td align="center">""" + \
'<a href="' + HTML_ROOT + '/index.html">Home</a></td>' + """
<td align="right" width="33%">Last Edited: """ + TAMARIN_VERSION + """<br>
</td></tr>
</TABLE>

</body>
</html>  
  """

def printError(error, html=True):
  """
  Prints both Tamarin status code messages or other kinds of error messages.
  
  Can print in HTML with user-friendly messages, or not.
  """
  if html:
    print '<div class="error">'
    print '<p class="error">'
    if error in STATUS:    
      #use standard error message format
      print '<b>Tamarin Error ' + str(STATUS[error][0]) + ':</b> '
      print STATUS[error][1] + ' <small>(' + error + ')</small></p>'

      if STATUS[error][0] >= 500: 
        #sys-config problems, so let users know who to contacts
        if error == 'UNHANDLED_ERROR':
          #add message and traceback
          print '<pre class="error">'
          traceback.print_exc(None, sys.stdout)  #no limit, prints to stdout
          print '</pre>'

        print '<p>There seems to be a problem with the Tamarin server or '\
          'its configuration.  You may want to try what you were doing again. '\
          'However, if this same problem perists, please copy and paste '\
          'the complete error message above (including any Traceback information) '\
          'and email it to ' 
        if ADMIN_EMAIL:
          print ADMIN_EMAIL
        else: 
          print 'your Tamarin administrator [<i>email address unknown</i>]'
        print 'so that the problem can be fixed.  '
        print 'Thanks, and sorry for the inconvenience.</p>'

    else:
      print '<b>Nonstandard Tamarin Error:</b> ' + str(error) + '</p>'

    print '</div>'

  #non-html version    
  else:
    print
    if error in STATUS:
      print "ERROR " + str(STATUS[error][0]),
      print "(" + error + "):"
      print STATUS[error][1]
    else:
      print "Nonstandard Error: "
      print error


## Other printing

def tprint(file, string, screen=True):
  """
  Primitive T (tee) printing: prints the given string to both the given file
  and to stdout.  Adds a line break to file so output matches same as stdout
  when using default print.
  
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
    file.write(string)
    file.write('\n')  #comes out as 0D0A on Windows; os.linesep comes out as 0D0D0A
  if screen:
    print str(string)


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
  elements = []
  for g in match.groups():
     elements.append(int(g))
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
  submitted.sort(None, key=lambda x: re.search(r"\d{8}-\d{4}", x).group())
  return submitted



  
  
  
