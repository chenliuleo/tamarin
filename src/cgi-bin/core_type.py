
## core_type.py

"""
The definition of core classes used by Tamarin.

Part of Tamarin, by Zach Tomaszewski.  
Created: 30 Jun 2012.
"""

import datetime
import glob
import math
import os.path
import re


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


class SubmissionType:
    
    # Future considerations:
    # * More than one possible file ext, such as for html and htm?
    # * More than one submission type per assignment?
    # * Currently check at upload: initial cap.  Convert to an UploadCheck
    #   system similar to Process system, where can run multiple checks
    #   based only on filename and filecontents before accepting upload?
    #   Warn or Refuse.
    #   Examples: warn about useing "package" declaration in code, ...? 
    
    """
    Determines how Tamarin processes submissions of the given type.
    
    Each Assignment has an single associated SubmissionType, as determined by
    the SUBMISSION_TYPES global.  Each SubmissionType contains the following
    details:

    * fileExt  - the required file extension, such 'java' or 'txt' or 'zip'
    * encoding - If specified, all submissions must be plain text of the given
                 encoding.  ('utf-8' is the default.  However, if your compiler
                 doesn't support "Unicode" source code files or if you want to
                 be strictly traditional, 'ascii' works well.)  If set to None,
                 submissions are assumed to be a binary file and so are not 
                 displayed by Tamarin.
    * preformatted - If True, displays text in <PRE> tag, appropriate for code.
                     Otherwise, allows for line-wrapping, better for text.
    * initialCap - Whether filename must start with an initial capital letter.
    * processes - an ordered list of Process objects that determine how each
                  submission is processed for grading purposes.  If list is
                  None or empty, does nothing except take the submission.   
    """
    def __init__(self, fileExt, encoding='UTF-8', preformatted=True,
                 initialCap=False, processes=[]):
        self.fileExt = fileExt
        self.encoding = encoding
        self.preformatted = preformatted
        self.initialCap = initialCap        
        self.processes = processes

        
class Process:
    pass        


class LatePolicy:
    """
    A policy that specifies grade changes based on a submission's timestamp.
    
    Each policy covers a specific timespan (range).  One end of the span is
    the assignment's deadline.  Most ranges will then extend to after the 
    deadline, but it is possible to specify a preceding time range in order 
    to implement bonus points for early submission.  Each timespan corresponds
    to a single rule that specifies how a final grade should be modified for 
    submissions submitted during that timespan.  See __init__ for details of 
    how to specify policies, including the format for a timespan range and the 
    corresponding rule.  
    
    An assignment may have more than one LatePolicy.  This allows for both
    a "negative" bonus point late policy for early submission as well as a
    late policy.  It is also useful for different policies depending on the
    degree of lateness.  (For example, 2 points off for the first 2 days late
    and then 5 points off for up to 5 days late would require 2 separate 
    policies.) If a submission falls within more than one overlapping timespan
    specified by 2 or more policies, the rule of the shortest (ie, closest to 
    the deadline) applicable timespan is applied.  It is an error to give an 
    assignment more that one LatePolicy covering the exact same timespan.  
    
    If an assignment is submitted after the deadline and after the last 
    post-deadline span (if any), it will not be accepted by Tamarin.  
    The submission is too late.
    
    Once in the system, an assignment timestamped before the first pre-deadline
    span (if any) is treated as having a timestamp of the start of that span.
    Similarly, those timestamped after the last post-deadline span are treated
    as if submitted at the final cutoff time.  For example, if an instructor 
    manually uploads a submission timestamped after the final cutoff date, 
    the longest span late policy will still be applied to that submission.
    
    LatePolicies have no effect on letter grades, such as ERR, OK, or X.
    
    """
    def __init__(self, policy, deadline):
        """
        Constructs a LatePolicy according to the given policy string.

        The deadline should be in Tamarin timestamp format.  
                
        Each policy should be a string in the form of: 'range:rule'
        
        A range has the following format: [+|-][[#d][#h][#m]|timestamp]
        
        That is, the range may optionally begin with either + or -.  
        If the sign is omitted, + is assumed.  
        
        The sign may then be followed by a span specified in days, 
        hours, and minutes.  This span is relative to the assignment deadline,
        either earlier (if sign is -) or later (if sign is +).  A particular
        unit may be omitted if unused; it will be assumed to be 0.  If more 
        than 23 hours or 59 minutes are specified, the corresponding overflow 
        into days and hours will be calculated.  At least one unit must be
        given though: d for day, h for hours, or m for minutes.  If more
        than one is used, they must be in that order.
        
        As an alternative to specifying a relative span, a specific timestamp
        may be given. The sign is ignored in these cases. (Since LatePolicies 
        usually apply across multiple assignments, specific timestamps are 
        rare.  However, they can be handy to specify a final cutoff date for 
        all assignments--such as the last day of the course.)  
        
        It is an error to have a 0 length span, either because the relative
        span is of size 0 or if the timestamp given is equal to the deadline.
        
        If neither span nor timestamp is given, the end of the span is 
        treated as year 0 for a - sign or year 9999 for a positive sign.
                
        The range is then separated from the associated rule by a colon (:).
        
        The rule is of the form: [+|-|=][#[%|$]][/[#d][#h][#m]]

        That is, the rule may begin with a sign: +, -, or =.  If omitted,
        = is assumed.  The sign specifies whether the grade should be 
        increased by (+), decreased (-) by, or set equal to (=) the following
        value. 
        
        The sign is followed by an integer value, which may be appended by 
        either % or $.  Without a modifier, the value is treated as a raw 
        point modifier.  If appended with a %, this is a percentage of the 
        assignment's total possible score.  If appended with a $, 
        it is a percentage of the submission's actual score.  (If the actual
        score to be modified is not numeric, will default to % instead.)
        
        Optionally, the modifier may be followed by a / and relative span.
        At least one value--whether day, hour, or minutes--must be given
        after a /.  When such a span is given, the modifier is applied for 
        each span that the assignment is late.  For example, /1d means apply
        the modifier for each day.  Such as span does nothing if applied to 
        an = modifier.  If this rule is associated with a -timespan ("bonus 
        policy"), it is applied for each full span. Otherwise, it is applied 
        for each partial span.
        
        The rule may be omitted.  In this case, the submission is marked late
        (or early), but no grade change is applied.
                
        Examples:
        +5d:-1/1d - For up to 5 days after the deadline, submissions suffer 
        a penalty of 1 point off for each (partial) day.
        
        +48h:-10% - For 2 days after the deadline, any submission loses 10% 
        of the assignment total.  (So, for a 5 point assignment, this would 
        be -1 point.)  Equivalent to '2d:-10%' (if relying on the assumed 
        + sign on the timespan).
        
        -3d:+5$/1d - An example of an "early bonus" policy, this grants a 
        cumulative bonus of 5 percent of the submission's score for each full 
        day early.
        
        20121221-1200:40$ - Using a timestamp to define the span, anything 
        submitted after the deadline but before noon on 21 Dec 2012 will 
        receive 40% of the score it would otherwise have received.  
        (:=40$ or :-60$ would also have been equivalent rules, since = is 
        assumed on rules without a sign.)
        
        1d: - Anything submitted for up to 1 day past the deadline is marked
        as late but its grade is unaffected.
        
        Given only the policies above, any submissions later than the deadline
        plus the given late period timespan would be refused by Tamarin.
        
        +:10% - Anything submitted after the deadline, no matter how late or 
        how bad, is given 10% of the total possible assignment value.  
        
        : - Anything submitted after the deadline is late but still accepted.
        
        """
        import tamarin
        self.raw = policy
        self.deadline = deadline
        assert re.match(r'\d{8}-\d{4}', self.deadline)
                
        span_re = r'(\+|-)?((\d{8}-\d{4})|((\d+d)?(\d+h)?(\d+m)?))'
        rule_re = r'(\+|-|=)?(\d*)([%$])?(/(\d+d)?(\d+h)?(\d+m)?)?'
        parsed = re.match(span_re + ':' + rule_re, policy)
        if not parsed:
            raise TamarinError('INVALID_LATE_POLICY', policy)

        (self.span_sign, unused_offset, self.span_timestamp, 
         relative, self.span_day, self.span_hour, self.span_minute,
         self.rule_sign, self.rule_value, self.rule_unit, 
         self.rule_repeater, 
         self.rule_day, self.rule_hour, self.rule_minute) = parsed.groups()
        
        #apply defaults and constrains
        if not self.span_sign:
            self.span_sign = '+'
        
        if self.span_timestamp:
            self.end = self.span_timestamp
        elif relative:
            day = hour = minute = 0
            sign = -1 if self.span_sign == '-' else 1           
            if self.span_day:
                day = int(self.span_day[:-1]) * sign
            if self.span_hour:
                hour = int(self.span_hour[:-1]) * sign
            if self.span_minute:
                minute = int(self.span_minute[:-1]) * sign
            endDate = tamarin.convertTimestampToTime(deadline)            
            shift = datetime.timedelta(days=day, hours=hour, minutes=minute)
            self.end = tamarin.convertTimeToTimestamp(endDate + shift)
        else:
            if self.span_sign == '-':
                self.end = '00000101-0000'
            else: 
                self.end = '99991231-2359'
        
        if self.end == self.deadline:
            raise TamarinError('INVALID_LATE_POLICY', 
                               "Parsable, but deadline == endpoint.")

        if self.rule_sign or self.rule_value or self.rule_unit or \
                self.rule_repeater:
            #some part of a rule given, so lets see if it's all valid
            if not self.rule_sign:
                self.rule_sign = '='
            if not self.rule_value:
                raise TamarinError('INVALID_LATE_POLICY', 
                                   "No grade change value given.")
            self.rule_value = int(self.rule_value)
            if self.rule_repeater and not self.rule_day and \
                    not self.rule_hour and not self.rule_minute:
                raise TamarinError('INVALID_LATE_POLICY', 
                                   "Empty /modifier given: " + self.raw)
            
    def getGradeAdjustment(self, score, total, timestamp, allowNeg=True):
        """
        Given the submission's score, assignment total, and timestamp,
        returns the adjustment based on this policy. Respects 
        tamarin.GRADE_PRECISION.  
        
        Normally, returns the adjustment even if this is a penalty greater than
        the score itself.  If allowNeg is False, any computed penalty is 
        capped at -score.
        
        Remember, if passed a non-numeric score, any $ rules will convert to
        % instead.  This way, a numeric value can always be returned.  
                
        """
        import tamarin
        if self.span_sign == '+':
            assert self.deadline < timestamp
            timestamp = min(timestamp, self.end)
            timespan = (tamarin.convertTimestampToTime(timestamp) -
                        tamarin.convertTimestampToTime(self.deadline)) 
        else:
            assert timestamp <= self.deadline
            timestamp = max(timestamp, self.end)
            timespan = (tamarin.convertTimestampToTime(self.deadline) -
                        tamarin.convertTimestampToTime(timestamp)) 

        if not self.rule_sign:
            #no rule, which means do nothing to the grade
            return 0 
            
        if not self.rule_unit:
            modifier = self.rule_value 
        elif self.rule_unit == '$' and \
                (isinstance(score, int) or isinstance(score, float)):
            modifier = (self.rule_value * score) / 100
        else:   # self.rule_unit == '%', or '$' with non-numeric 
            modifier = (self.rule_value * total) / 100
                    
        if self.rule_sign == '-':
            modifier *= -1
        
        times = 1
        if self.rule_repeater and not self.rule_sign == '=':
            days = int(self.rule_day[:-1]) if self.rule_day else 0
            hours = int(self.rule_hour[:-1]) if self.rule_hour else 0
            minutes = int(self.rule_minute[:-1]) if self.rule_minute else 0
            repeater = datetime.timedelta(days=days, hours=hours, 
                                        minutes=minutes)
            times = timespan / repeater
            if self.span_sign == '+':
                times = math.ceil(times)  #include any partial repeater span
            else:
                times = math.floor(times) #only complete repeater span
            
        gradeAdj = round(modifier * times, tamarin.GRADE_PRECISION)        
        if not allowNeg and score + gradeAdj < 0:
            gradeAdj = -score
        return gradeAdj
    
    def isEarlyPolicy(self):
        """ 
        An early policy is one that covers a span before the deadline.
        Returns False if this policy covers a span after the deadline.
        """
        return self.end < self.deadline

    def __str__(self):
        """ Returns the original late policy format string. """
        return self.raw

    def __repr__(self):
        """ Shows the original late policy format string and deadline. """
        return ''.join((self.__class__.__name__, 
                       "('", self.raw, "', '", self.deadline, "')")) 

    
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
        * policies -- a sorted list of LatePolicies 

        If the given assignment name is not of the correct format, throws an
        AssertionError.

        If the given assignment does not exist, throws a TamarinError
        with one of the following keys: 'NO_SUCH_ASSIGNMENT',
        'DUPLICATED_ASSIGNMENTS', 'BAD_ASSIGNMENT_DIR_FORMAT', or
        'UNHANDLED_TYPE'.
        """
        import tamarin
        assert re.match(tamarin.ASSIGNMENT_RE, assignment), \
            'Bad assignment format given.'
        assignDir = glob.glob(os.path.join(tamarin.GRADED_ROOT, 
                                           assignment + '-*'))
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
            self.maxScore = tamarin.ASSIGNMENT_TOTAL
        if match.group(5):
            typeName = str(match.group(5))
        else:
            typeName = tamarin.ASSIGNMENT_TYPE
        if typeName in tamarin.SUBMISSION_TYPES:
            self.type = tamarin.SUBMISSION_TYPES[typeName]
        else:
            raise TamarinError('UNDEFINED_TYPE', typeName)
        
        # load late polices: longest of all possible key matches
        possible = [key for key in tamarin.LATE_POLICIES.keys() \
                        if self.name.startswith(key)]
        if possible:
            key = sorted(possible, key=len)[-1]
            if not tamarin.LATE_POLICIES[key]:
                # corresponding key has no policy value
                self.policies = None
            elif isinstance(tamarin.LATE_POLICIES[key], str):
                # key corresponds to a single policy, so put in list
                self.policies = [LatePolicy(tamarin.LATE_POLICIES[key], 
                                            self.due)]
            else:
                # multiple policies, so convert and sort for later
                self.policies = [LatePolicy(p, self.due) for p in \
                                    tamarin.LATE_POLICIES[key]]
                self.policies.sort(key=lambda policy: policy.end)                
        else:
            self.policies = None

    def __str__(self):
        """ Returns just the short name of this assignment """
        return str(self.name)
    
    def getLateOffset(self, submittedTimestamp=None):
        """
        Returns a string in the format of '+#d #h #m' showing the lateness of
        the given Tamarin timestamp.
        
        If a timestamp is not given, will use the current time instead.
        If the given timestamp is before this assignment's deadline, will
        return a negative offset showing how early the submission is.
        """
        # convert to datetimes
        import tamarin
        submitted = tamarin.convertTimestampToTime(submittedTimestamp)
        deadline = tamarin.convertTimestampToTime(self.due)
        # to avoid dealing with negative timedeltas (which are weird)
        if submitted <= deadline:
            offset = deadline - submitted
            sign = '-'
        else:
            offset = submitted - deadline
            sign = '+'
        hours = offset.seconds // 3600
        minutes = (offset.seconds // 60) - (hours * 60)
        return '{0}{1}d {2}h {3:02}m'.format(sign, offset.days, hours, minutes)

    def getPolicy(self, submittedTimestamp=None):
        """
        Returns the appropriate policy associated with this assignment based
        on the given timestamp.  If no timestamp is given, uses the current
        time.  May return None if this assignment has no late policies, or if
        the given timestamp is before the deadline but there is no early 
        submission policy.
        """
        import tamarin
        if not submittedTimestamp:
            # use current time
            submittedTimestamp = tamarin.convertTimeToTimestamp()        
        timestamp = submittedTimestamp 

        if not self.policies:
            return None
        elif self.isLate(timestamp):
            if self.policies[-1].isEarlyPolicy():
                # only have early policies, though, so none apply
                return None
            else:
                # find last late policy that applies (even if past last one)
                for policy in self.policies:
                    if not policy.isEarlyPolicy() and timestamp <= policy.end:
                        break
                return policy                
        else:
            if not self.policies[0].isEarlyPolicy():
                # submission is early, but only have late policies
                return None
            else:
                #find closest-to-deadline early policy that applies (or first)
                for policy in reversed(self.policies):
                    if policy.isEarlyPolicy() and timestamp >= policy.end:
                        break
                return policy

    def isLate(self, submittedTimestamp=None):
        """
        Determines whether the submittedTimestamp (in 'YYYYMMDD-HHMM' format)
        occurs before this assignment's deadline.  If submittedTimestamp is 
        None, uses the current time.
        """
        import tamarin
        if not submittedTimestamp:
            # use current time
            submittedTimestamp = tamarin.convertTimeToTimestamp()
        # nice thing about Tamarin timestamps is they also compare properly 
        return submittedTimestamp > self.due
    
    def isTooLate(self, submittedTimestamp=None):
        """
        Determines whether the submittedTimestamp (in 'YYYYMMDD-HHMM' format)
        occurs after this assignment's deadline AND after all late policies.  
        If submittedTimestamp is None, uses the current time.
        """
        import tamarin
        if not submittedTimestamp:
            # use current time
            submittedTimestamp = tamarin.convertTimeToTimestamp()
        if self.policies:
            # just look at last one (already sorted)
            return submittedTimestamp <= self.policies[-1].end
        else:
            return self.isLate()
        

class SubmittedFile:
    """
    Represents a file in SUBMITTED_ROOT that has completed its validation by 
    submit.py and has been timestamped.
    
    Details include:
    * filename   - the basename of the file
    * path       - the full path of the file (including the filename)
    * username   - username of the file's author/submitter
    * assignment - the name of the assignment this file was submitted for
                   (as str, not Assignment object)
    * timestamp  - when the file was submitted, as a Tamarin timestamp
    * fileExt    - the file extension
    * originalFilename - the uploaded filename without the added embedded 
                         timestamp
    
    """
    def __init__(self, filename, virtualFile=False):
        """
        Constructs a SubmittedFile for the given filename.  
        
        If the given filename is not of the correct format, throws a
        TamarinError('BAD_GRADE_FILENAME').
        
        If the virtualFile parameter is True, does not check that the file
        exists. Otherwise, if the given file does not exist in SUBMITTED_ROOT, 
        throws a TamarinError('NO_SUBMITTED_FILE').
        
        """
        import tamarin
        #confirm format of filename        
        fileMatch = re.match(tamarin.SUBMITTED_RE, filename)
        if not fileMatch:
            raise TamarinError('BAD_GRADE_FILENAME', filename)
        self.filename = filename
    
        #check that file really exists.
        self.path = os.path.join(tamarin.SUBMITTED_ROOT, filename)
        if not virtualFile and not os.path.exists(self.path):
            raise TamarinError('NO_SUBMITTED_FILE', filename)
    
        #load details from above match
        self.username = fileMatch.group(1).lower()
        self.assignment = fileMatch.group(2)
        self.timestamp = fileMatch.group(3)
        self.fileExt = fileMatch.group(4)
        self.originalFilename = fileMatch.group(1) + fileMatch.group(2) + \
                                    '.' + fileMatch.group(4)


class GradedFile(SubmittedFile):
    """
    Represents a file in a GRADED_ROOT subdirectory that has completed the 
    grading process.
    
    Details are the same as for a SubmittedFile, plus:
    
    * assign - the Assignment object for the str in self.assignment
    * graderOutputPath - the full path to the grader output file
    * graderOutputFilename - just the base name of the grader output file
    * grade - the grade from the grader file (or ERR if it can't be found)
    * humanVerified - the grade has been verified by a human
    * humanComment - whether a human has appended a comment to the output file
    
    """
    def __init__(self, filename, virtualFile=False):
        """
        Constructs a new GradeFile for the given file.
        
        Throws the same TamarinErrors as a SubmittedFile.  
        May also throw any of the errors from the Assignment constructor.
        
        If the virtualFile parameter is True, doesn't actually check that 
        the file exists.  Will also skip reading the corresponding grade 
        report, and so the instance will lack the grade, verified, and 
        comment values.

        """
        import tamarin
        #let superclass initialize everything
        super().__init__(filename, virtualFile=True)
        #now reset path variable
        self.assign = Assignment(self.assignment)
        self.path = os.path.join(self.assign.path, filename)
        if not virtualFile: 
            if not os.path.exists(self.path):
                raise TamarinError('NO_SUBMITTED_FILE', filename)

            #add new details            
            self.graderOutputPath = self.path.replace("." + self.fileExt, 
                                        "-*." + tamarin.GRADER_OUTPUT_FILE_EXT)
            gradedGlob = glob.glob(self.graderOutputPath)
            if not gradedGlob:
                raise TamarinError('NO_GRADER_RESULTS', filename)
            elif len(gradedGlob) > 1:
                raise TamarinError('MULTIPLE_GRADER_RESULTS', filename)
            self.graderOutputPath = gradedGlob[0]
            self.graderOutputFilename = os.path.basename(self.graderOutputPath)

            # pull grade from filename
            found = re.match(tamarin.GRADED_RE, self.graderOutputFilename)
            try:
                self.grade = float(found.group(4))
            except ValueError:
                self.grade = str(found.group(4))
                if not self.grade:
                    self.grade = 'ERR' #empty string, as on a grader failure

            # human verified or comments?
            human = found.group(5)
            if human:
                self.humanVerified = 'H' in human
                self.humanComment = 'C' in human
            else:
                self.humanVerified = False
                self.humanComment = False                
                
    def getLateOffset(self):
        """ As per Assignment.getLateOffset for this submission. """
        self.assign.getLateOffset(self.timestamp)
    
    def getLateGradeAdjustment(self):
        """
        Returns the penalty or bonus due to the LatePolicy associated
        with this assignment.  See LatePolicy.getGradeAdjustment.
        Does not cap the late penalty (may be more than score itself).
        Returns 0 if there is no late policy (as when isTooLate).
        """
        policy = Assignment(self.assignment).getPolicy(self.timestamp)
        if not policy:
            return 0
        else:
            return policy.getGradeAdjustment(self.grade, 
                                             self.assignment.maxScore,
                                             self.timestamp)
    
    def getResubmissionGradeAdjustment(self, submissionCount=None):
        """
        Returns the penalty due to additional submissions for this assignment.

        Penalty can be more than can be covered by the grade itself. 
        Returns the penalty even for non-numeric grades. Does not consider 
        tamarin.MAX_RESUBMISSIONS, so extra manual uploads could lead to 
        higher penalties than normally allowed. 
        
        The submissionCount is a performance boost.  If the number of 
        submissions (including this one) is given here, will be used instead
        of polling the file system to (re)collect the same data. 
        
        """
        import tamarin
        if not submissionCount:
            # need to count the files here
            files = tamarin.getSubmissions(user=self.username, 
                                           assignment=self.assignment)
            submissionCount = len(files)            

        if submissionCount <= 1:
            return 0
        else:            
            adj = (len(files) - 1) * tamarin.RESUBMISSION_PENALTY
            return round(adj, tamarin.GRADE_PRECISION)
            
    def getAdjustedGrade(self, submissionCount=None):
        """ 
        Returns this file's grade after adjustments for lateness or 
        resubmissions.  See getLateGradedAjustment and 
        getResubmissionGradeAdjustment.  Normalizes grade based on 
        tamarin.GRADE_PRECISION.
        
        Non-numeric grades cannot be updated, and so these are returned
        unchanged.  Also, does not allow for negative grades, so will 
        return 0 instead if cumulative penalties are more than the grade.
        
        For the raw score returned by the grader, use self.grade directly.
                
        """
        import tamarin
        if isinstance(self.grade, str):
            return self.grade
        adjGrade = self.grade
        adjGrade += self.getLateGradeAdjustment() 
        adjGrade += self.getResubmissionGradeAdjustment(submissionCount)
        adjGrade = round(adjGrade, tamarin.GRADE_PRECISION)
        if adjGrade < 0:
            adjGrade = 0
        return adjGrade
    
    def isLate(self):
        """ As per Assignment.isLate for this submission. """
        self.assign.isLate(self.timestamp)

    def isTooLate(self):
        """ As per Assignment.isTooLate for this submission. """
        self.assign.isTooLate(self.timestamp)
    
    