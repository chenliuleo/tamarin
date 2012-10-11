
## core_grade.py

"""
Defines gradepipe grading processes.

Contains the Process class, which defines a single step to be executed
during a gradepipe session.  This superclass defines the interface for all
other specific processes to implement.

Also contains all specific processes implemented so far.

Part of Tamarin, by Zach Tomaszewski.  
Created: 14 Jul 2012.
"""

import datetime
import glob
import html
import logging
import re
import os
import shutil
import subprocess
import zipfile

# can't import tamarin here due to circular dependency; imported in methods
#from core_type import TamarinErrror 

class Process:
    """
    A Process simplifies the work of executing a step in the grading flow.
    It is possible to execute Python code or invoke an external tool.
    Any Process subclass has access to a common logger.
    
    See method documentation for further details.  Also, see GradeFile for
    an example of how the variables and methods of a Process are often used.
          
    """
    def __init__(self, required=True, displayName=None):
        """
        Initializes this Process.  Subclasses may add additional required
        parameters, but should always invoke this superclass constructor. 
        
        Sets up these public instance variables:
        * required (from parameter)
        * name (name of the constructing subclass)
        * displayName (from parameter, if given; else name)
        * grade (None)
        * output (None)
        * logger
        
        self.required (taken from the parameter) specifies whether this 
        process must pass its run before carrying on to the next one in the 
        current grading sequence. That is, if this process fails to pass its
        run, should this abort the rest of the grading sequence for this 
        submitted file? 
        
        self.grade is the grade resulting from the run of this process.  
        The value must match the format of tamarin.GRADE_RE, which means 
        a float or 'OK' or 'X' (or 'ERR').  If left as None, grading 
        is not relevant to this process.  (For example, the process might
        be only informational or simply involve copying files around in
        preparation for another process.) 
        
        self.output is any content that should be displayed to the student
        in the generated grader output file.  
        
        self.name is the most-specific class name of this Process.
        
        self.displayName is a longer or more coherent name shown in grader 
        output to the student.  Defaults to self.name if not given.
        
        self.logger is the logger specific to the particular Process class
        and can be used to record information that would be useful in 
        debugging or when monitoring the process.  See the Python logging
        module for more information.  Logged data does NOT go into output
        passed on to the student.  
        
        """
        self.required = required
        self.name = type(self).__name__
        self.displayName = displayName if displayName else self.name
        self.grade = None
        self.output = None
        self.logger = logging.getLogger('Process.' + self.name)

    def run(self, args):
        """
        Executes this Process.
        
        Passes in a dict as args.  This dictionary is shared by all Processes
        in a grading sequence, so every Process should document what keys it
        requires and what changes it might make.  This mechanism allows 
        different processes to recording important information (such as 
        return codes, etc.) for other later processes to access.  To avoid
        unexpected name clashes, every Process should prefix its class name 
        to any keys it uses.  For example, if a GradeFile process wants to add
        a 'filename key, it should instead add 'GradeFile.filename'. 
            
        This method should then return either True or False.  If True, the
        run sufficiently accomplished its goals.  If False, the run failed to 
        achieve what was required of either it or the submitted work.  
        For example, a Compile process would return False if the files did 
        not actually compile.
        
        For errors in the process itself, an exception--preferably a
        TamarinError--should be thrown.
        
        The difference between a run failure (returning False) and an error
        (throwing an exception) is that failure will still result in grade
        and output being reported to the student.  Also, if the process was not
        required, the gradepipe will try to continue with the next Process.  
        On the other hand, an error means the Process itself crashed, which 
        will halt the gradepipe for the current file and be reported as a 
        Tamarin-level error.
        
        This run(args) method must be overridden in any implementing subclass.
        """
        pass


class GradePipe(Process):
    """
    Not intended for direct use by Tamarin users or admins.
    Thus, it should not be included in the process list for a SubmissionType.
        
    GradePipe is something of a "meta process".  It is normally started 
    when gradepipe.py is executed.               
    
    """
    def __init__(self, required=True, fileControlled=True, 
                 logLevel='INFO', gradeOnly=None):
        """
        If fileControlled is True, this GradePipe will respect the files
        set in tamarin.py on whether or not it should run.  That is, it
        will abort if another GrapePipe is running (tamarin.GRADEPIPE_ACTIVE)
        or disabled (tamarin.GRADEPIPE_DISABLED).  If False, it will always
        run.
        
        logLevel controls the level of logging.  Should be one of the 
        standard levels from Python's logging module.  'DEBUG' is basically
        'verbose' mode. 
        
        If gradeOnly is given, will grade only those submitted files 
        whose basenames includes the given substring.
        
        """
        super().__init__(required)
        self.fileControlled = fileControlled
        self.logLevel = logLevel
        self.gradeOnly = gradeOnly
    
    def run(self, args=None):
        """
        Grades all files in tamarin.SUBMITTED_ROOT.
        
        Will abort with False if fileControlled and a file state indicates
        it should not run.  
        
        If running, sets up logging for all sub-processes.  Will then loop
        through all submitted files, running GradeFile on each one, and return
        True.
        """
        import tamarin
        
        if not args:
            args = dict()
                
        # set up top-level Process logger in order to capture all logging
        topLogger = logging.getLogger('Process')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt='{name}-{levelname}: {message}', 
                                      style='{')
        handler.setFormatter(formatter)
        topLogger.addHandler(handler)
        topLogger.setLevel(self.logLevel)
        
        # make sure we should even run.
        if self.fileControlled:            
            if os.path.exists(tamarin.GRADEPIPE_DISABLED):
                self.logger.warn("GRADEPIPE_DISABLED file exists. Quitting...")
                return False
            elif os.path.exists(tamarin.GRADEPIPE_ACTIVE):
                self.logger.warn("GRADEPIPE_ACTIVE file exits. Quitting...")
                return False
            
        # dump PID into file
        try:
            self.logger.info("Started at %s.", datetime.datetime.now())
            with open(tamarin.GRADEPIPE_ACTIVE, 'w') as outfile:
                outfile.write(str(os.getpid()))
            self.logger.debug("Wrote PID %d to ACTIVE file.", os.getpid())
        except IOError:
            self.logger.exception("Could not dump PID to file.")    
            return False

        # grading loop
        try:
            #loop over submitted files as long as there are more to grade
            gradedCount = 0
            failedCount = 0
            badFiles = []
            gf = GradeFile()

            while True:
                # get most recent list 
                submitted = tamarin.getSubmittedFilenames(self.gradeOnly)
                submitted = [f for f in submitted if f not in badFiles]

                if not submitted: 
                    break
                        
                success = gf.run(args, os.path.basename(submitted[0]))
                if success:
                    gradedCount += 1
                else:
                    failedCount += 1
                    if tamarin.LEAVE_PROBLEM_FILES_IN_SUBMITTED:
                        badFiles.append(submitted[0])
    
            # done looping
            self.logger.info("%d of %d files successfully graded.", 
                             gradedCount, gradedCount + failedCount)
        except:
            self.logger.exception("Crashed unexpectedly!")

        # cleanup PID file 
        try:
            os.remove(tamarin.GRADEPIPE_ACTIVE)
            self.logger.debug("Removed PID %d's ACTIVE file.", os.getpid())      
        except:
            self.logger.exception("Could not clean up ACTIVE/PID file.")
        
        self.logger.info("Stopped at %s", datetime.datetime.now())
        return True    


class GradeFile(Process):
    """
    Not intended for direct use by Tamarin users or admins.
    Thus, it should not be included in the process list for a SubmissionType.
        
    GradeFile deals with the task of grading a single submitted file.  It sets
    up the gradezone, calls the appropriate processes for that file type, 
    records the results into a grader output file, and them moves the file
    into the graded directory (depending on the value of 
    tamarin.LEAVE_PROBLEM_FILES_IN_SUBMITTED).                
    
    """    
    def __init__(self, required=False):
        """
        Failing to grade one file doesn't mean we can't try the next one.
        """
        super().__init__(required)

    def run(self, args, filenameInSubmitted=None):
        """
        Grades the given submitted file.
        
        The given filename must be located in SUBMITTED_ROOT.  If this 
        convenience argument is omitted, will look in 
        args['GradeFile.filenameInSubmitted'] instead.  If that is missing too,
        will raise a ValueError. 
        
        args must be a valid dictionary, though it can be empty.  The passed
        args value will be unaffected.  That is, each GradeFile subprocess
        will receive a fresh/reset copy of the passed args.  
        
        Sets the following args fields:
        * GradeFile.filenameInSubmitted - timestamped filename in SUBMITTED
        * GradeFile.filename - name of original submission, now GRADEZONE
        * GradeFile.name - everything up to first .
        * GradeFile.ext - everything after first .
        * GradeFile.path - full path to file's GRADEZONE location
        * GradeFile.username - username as appears in filename
        * GradeFile.user - username, but all lowercase
        * GradeFile.assignment - for which this file was submitted
        
        Clears the gradezone and copies the submitted file (under its 
        original, non-timestamped name) into the zone.  Then opens a grader 
        output file and runs all process appropriate for that assignment's 
        type.  

        The grader output file starts with <div class="grader">.
        
        Then, for each process, records any grade or output if either is not 
        None. If recording, the process gets its own <div class="graderName">
        section were Name is the process's class name.  
        
        The grade will then be recorded as 
        <p><span class="displayName">display name:</span> grade</p>.
        If there is no grade, the rest of the line still gets printed
        in order to identify the output. 
        
        Any output will then follow.  If the first character is a '<',
        it is assumed that the output is appropriately HTML-formatted. 
        If not, it will be HTML-escaped and displayed in a <pre> format.  
        In this case, it is recommended to keep lines to fewer than 80 
        chars long.  
        
        Finally, the current process's div will be closed with a </div>.  
        
        Whether a process's run passes or fails does not affect output.
        It simply determines whether or not the next process should be 
        invoked.  So, if a Process is going to fail and wants the student
        to know why, it should document it somehow in its self.output.
        
        After running all processes, the overall grade is stored in a 
        'GRADE_START_TAG grade GRADE_END_TAG' line (without the spaces).  
        If any grade is 'ERR', the final grade is 'ERR'.  Otherwise, if at 
        least one grade was a number, the grade is the sum of all numerical 
        grades.  If none were numbers, the grade is 'OK', unless there was 
        at least one 'X'.  This means the grade is 'OK' if there were no 
        processes that returned a grade.
        
        Finally, the grader output file ends with another </div>. 
         
        """
        import tamarin
        from core_type import TamarinError, Assignment, SubmittedFile   
        
        args = dict(args)  # don't want to mangle version passed to each run 
                
        # check args
        if 'GradeFile.filenameInSubmitted' not in args:
            args['GradeFile.filenameInSubmitted'] = filenameInSubmitted
        if not args['GradeFile.filenameInSubmitted']:
            raise ValueError("'GradeFile.filenameInSubmitted' not provided.")
        fInS = args['GradeFile.filenameInSubmitted']

        try: 
            # check filename exists and grab details
            self.logger.debug("%s - started grading...", fInS)
            submitted = SubmittedFile(fInS)
            assignment = Assignment(submitted.assignment)
            processes = assignment.type.processes

            # save details into args for other sub-processes to use
            fn = submitted.originalFilename
            args['GradeFile.filename'] = fn
            args['GradeFile.name'] = fn.split('.', 1)[0]
            args['GradeFile.ext'] = fn.split('.', 1)[1]
            args['GradeFile.username'] = submitted.username
            args['GradeFile.user'] = submitted.username.lower()
            args['GradeFile.assignment'] =  submitted.assignment
            args['GradeFile.path'] = os.path.join(tamarin.GRADEZONE_ROOT, fn)
            
            # sanity check (for manually uploaded files)
            if args['GradeFile.ext'] != assignment.type.fileExt:
                raise TamarinError('GRADING_ERROR', 
                                   "File's extension does not match that " 
                                   "required by " + assignment.name)
            
            # copy file into a clean gradezone
            try:
                self.clearGradeZone()
                shutil.copy(submitted.path, args['GradeFile.path'])
                self.logger.debug("%s copied into a clean gradezone.", fn)
            except:
                raise TamarinError('UNPREPABLE_GRADEZONE')
            
            # open a grader output file
            try:
                # first, delete any old grader files for this submission
                outName = submitted.filename.replace("." + submitted.fileExt, 
                                        "-*." + tamarin.GRADER_OUTPUT_FILE_EXT)
                outName = os.path.join(assignment.path, outName)
                for file in glob.glob(outName):
                    os.remove(file)
                    
                outName = outName.replace('-*.', '-.')  # grade-less form
                graderOut = open(outName, 'w')
                print('<div class="grader">', file=graderOut)
            except:
                self.logger.exception("Could not rm old or write new results.")
                raise TamarinError('COULD_NOT_STORE_RESULTS', outName)

            grades = []
            passed = True
            try:              
                # run all processes on the submission                
                for p in processes:
                    success = p.run(args)                    
                    if p.grade or p.output:
                        print('<div class="' + p.name + '">', file=graderOut)
                        print('<p><span class="displayName">' + p.displayName +
                              ':</span>', end='', file=graderOut)
                            
                        # save grade summary
                        if p.grade:
                            if not re.match(tamarin.GRADE_RE + '$', 
                                            str(p.grade)):
                                raise TamarinError('INVALID_GRADE_FORMAT',
                                                   p.name + ' => "' + 
                                                   p.grade + '"')
                            try:
                                # convert p.grade to number it really is
                                p.grade = round(float(p.grade), 
                                                tamarin.GRADE_PRECISION)
                            except ValueError:
                                pass  # p.grade wasn't a number, so nevermind
                            grades.append(p.grade)
                            
                            #print color-coded non-numeric grades
                            if isinstance(p.grade, str):
                                g = '<span class="'
                                g += 'success' if p.grade == 'OK' else 'fail'
                                g += '">' + p.grade + '</span>' 
                            else:
                                g = str(p.grade)
                            print(' ' + g, end='', file=graderOut)
                        
                        print('</p>', file=graderOut)    
                            
                        # save any output
                        if p.output:
                            if p.output[0] == '<':
                                # already formatted
                                print(p.output, file=graderOut)
                            else:
                                print('<pre>\n' + html.escape(p.output, 
                                                            quote=False) + 
                                      '</pre>', file=graderOut)
                        print('</div>', file=graderOut)
                        
                    if not success and p.required:
                        self.logger.warn("%s required but failed, so "
                                          "aborting grading run", p.name)
                        passed = False
                        break
                
                # process grades now that we have them all
                if any(map(lambda x: x == 'ERR', grades)):
                    grade = 'ERR' 
                elif any(map(lambda x: isinstance(x, float), grades)):
                    grade = 0
                    for g in grades:
                        if isinstance(g, float):
                            grade += g
                else:
                    grade = 'X' if 'X' in grades else 'OK'
                                
            except TamarinError as err:
                self.logger.error("%r", err)
                grade = 'ERR'
                passed = False
                # Future: send this through printError on way to file?
                print('<pre>' + repr(err) + '</pre>', file=graderOut)
            except:
                self.logger.exception('A grading process just crashed!')
                grade = 'ERR'
                passed = False
                print('<pre>TamarinError: GRADING_CRASH.</pre>', 
                      file=graderOut)
            finally:
                print(tamarin.GRADE_START_TAG + str(grade) + 
                      tamarin.GRADE_END_TAG, file=graderOut)
                print('</div>', file=graderOut)
                graderOut.close()

            # done grading this file (whether successful or not)
            if isinstance(grade, float):
                grade = round(grade, tamarin.GRADE_PRECISION)
            
            # save results
            try:                
                newName = outName.replace('-.', '-' + str(grade) + '.')
                shutil.move(outName, newName)
                
                if passed or not tamarin.LEAVE_PROBLEM_FILES_IN_SUBMITTED:
                    newLoc = os.path.join(assignment.path, submitted.filename)
                    shutil.move(submitted.path, newLoc)  
            except:
                self.logger.exception("Could not rename/move final results.")
                raise TamarinError('COULD_NOT_STORE_RESULTS', outName)

            # SUCCESS!
            self.logger.info("%s -> %s", fInS, grade)
            return passed

        except TamarinError as err:
            self.logger.error("%r", err)
            return False
        except:
            self.logger.exception("Unexpected crash!")
            return False
       
    def clearGradeZone(self):
        """ Recursively deletes all files and directories in the GRADEZONE. """
        from tamarin import GRADEZONE_ROOT
        zoneFiles = glob.glob(GRADEZONE_ROOT + '/*')
        for zf in zoneFiles:
            #remove both directories and files
            if os.path.isdir(zf):
                shutil.rmtree(zf)
            else:
                os.remove(zf)


class CopyGrader(Process):
    """ 
    Copies the grader files for this assignment into the GRADEZONE. 
    
    It is recommended that grader files be pre-compiled and copied after
    compiling the submission.  This way, the submission cannot overwrite
    the grader files.  If the submission needs some of the grader files
    in order to compile, then copy the graders, compile the submission,
    and copy the graders again (to be sure you still have the original
    versions).
    """
    
    def __init__(self, required=True, 
                 displayName="Copying grader files into gradezone",
                 rootGrader=True, assignmentGrader=True):
        """
        If rootGrader is True, will copy any files found in GRADERS_ROOT
        into the gradezone.  If there aren't any files there, the run will 
        fail. Copies files only, not directories.
        
        If assignmentGrader=True, will copy any files found in GRADERS_ROOT/X,
        where X is the assignment name.  If the folder is not there or is
        empty, the run will fail.  Will copy whole directories trees if 
        present.  Since any assignment copying always happens seconds, it is
        possible to overwrite any default rootGrader files with 
        assignment-specific versions.
        
        It is an error to set both rootGrader and assignmentGrader to False,
        since then there's nothing to copy.  This will result in an exception
        when running.
        """
        super().__init__(required=required, displayName=displayName)
        self.rootGrader = rootGrader
        self.assignmentGrader = assignmentGrader
        
    def run(self, args):
        """
        If rootGrader, copies that first.  If assignmentGrader, requires 
        args['GradeFile.assignment'] for the assignment name.  Will copy
        those graders too.
        
        See __init__ for more docs.
        """
        import tamarin
        from core_type import TamarinError
            
        if not self.rootGrader and not self.assignmentGrader:
            self.logger.error("Both rootGrader and assignmentGrader are "
                              "False.")
            raise TamarinError('INVALID_PROCESS_CONFIGURATION', self.name)
        
        if self.rootGrader:
            try:
                graderFiles = glob.glob(os.path.join(tamarin.GRADERS_ROOT,'*'))
                # files only; no dirs
                graderFiles = [gf for gf in graderFiles if os.path.isfile(gf)]
                if not graderFiles:
                    self.logger.error("No rootGrader files to copy.")
                    raise TamarinError('GRADER_ERROR', self.name)
                for gf in graderFiles:
                        shutil.copy(gf, tamarin.GRADEZONE_ROOT)
                self.logger.debug("Copied %d root grader file(s) "
                                  "into gradezone.", len(graderFiles))
            except TamarinError:
                raise
            except:
                self.logger.exception('Could not copy rootGrader files')
                raise TamarinError('GRADER_CRASH', self.name)

        if self.assignmentGrader:
            try:
                assignLoc = os.path.join(tamarin.GRADERS_ROOT, 
                                         args['GradeFile.assignment'])
                if not os.path.exists(assignLoc):
                    self.logger.error('No GRADERS/%s location to copy from.', 
                                      args['GradeFile.assignment'])
                    raise TamarinError('GRADER_ERROR', self.name)
                
                graderFiles = glob.glob(os.path.join(assignLoc,'*'))
                if not graderFiles:
                    self.logger.error("No assignmentGrader files to copy.")
                    raise TamarinError('GRADER_ERROR', self.name)
                for gf in graderFiles:
                    #do a recursive copy of any directories
                    if os.path.isdir(gf):
                        # remove anything already there so copy will succeed; 
                        # ignore errors if not there
                        shutil.rmtree(os.path.join(tamarin.GRADEZONE_ROOT, 
                                                   os.path.basename(gf)), True)
                        shutil.copytree(gf,os.path.join(tamarin.GRADEZONE_ROOT,
                                                   os.path.basename(gf)), True)
                    else:
                        shutil.copy(gf, tamarin.GRADEZONE_ROOT)
                self.logger.debug("Copied %d assignment grader file(s) "
                                  "into gradezone.", len(graderFiles))
            except TamarinError:
                raise
            except:
                self.logger.exception('Could not copy assignmentGrader files')
                raise TamarinError('GRADER_CRASH', self.name)
        
        return True

class DisplayFiles(Process):
    """
    Displays the contents of the given glob of text files.
    
    A text file submission is automatically shown by Tamarin, so this process 
    is only necessary when you want to show the contents of unzipped files.
    Will search gradezone for the given list of file globs, displaying each
    file found using a "preformatted" display format.
    
    Adds (as a list) the set of actual filenames (relative to GRADEZONE)
    to args['DisplayFiles.filenames'] 
    
    """
    # FUTURE: Loop through SUBMISSION_TYPEs to look at file exts to determine
    # formatting?  Neither looking at type keys or looping through possible
    # duplicates is entirely satisfactory.
    #
    # FUTURE: Flag for recursive file printing.
    #    
    def __init__(self, *globs, required=False, displayName="Displaying files"):
        super().__init__(required, displayName)
        self.grade = 'OK'
        self.globs = globs
        
    def run(self, args):
        """ 
        Adds each glob-matching file name to output.
        If at least one found, grade is OK (returns True), 
        else X (returns False: no files displayed).
        """
        import tamarin
        files = set()
        self.output = ''
        
        for g in self.globs:
            batch = glob.glob(os.path.join(tamarin.GRADEZONE_ROOT, g))
            for file in batch:
                self.output += '<div class="file">\n'
                fn = file.replace(tamarin.GRADEZONE_ROOT, '.')
                files.add(fn)
                self.output += '<h4>' + fn + '</h4>\n'
                with open(file, 'r') as filein:
                    content = filein.read()
                    content = html.escape(content, quote=False)
                    self.output += '<pre>' + content + '</pre>\n</div>\n'
        
        # record results
        args['DisplayFiles.filenames'] = list(files)
        self.logger.debug("Displayed " + str(len(files)) + " files from " + 
                          str(self.globs))
        if len(files) == 0:
            self.grade = 'X'
            self.output = None
        return len(files) > 0
        

class JavaCompiler(Process):
    """ 
    Compiles the submitted file using javac. 
    """
    
    def __init__(self, javacPath, required=True, displayName="Compiled",
                 grade='OK', all=False):
        """
        Requires the path to the javac compiler.  If all is True, compiles
        all .java files currently in gradezone (top level only).
        """
        super().__init__(required, displayName)
        self.javac = javacPath
        self.grade = grade
        self.all = all
    
    def run(self, args):
        """
        Compiles the file named in args['GradeFile.file'].  It is assumed
        that this will be a .java file.
        
        Returns True and leaves self.grade as set in the constructor 
        if the file compiled.  Otherwise, sets self.grade to 0 if it was a 
        number or to 'X' if it wasn't and returns False.
        
        Also sets 'JavaCompiler.compiled' to True or False.
        """
        # Future: Allow a compile *.java somehow?  
        # And maybe support packages someday?
        import tamarin
        from core_type import TamarinError
        if self.all:
            cmd = self.javac + ' ' + '*.java'
        else:
            cmd = self.javac + ' ' + args['GradeFile.filename']
        try:
            compiler = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.STDOUT,
                                        cwd=tamarin.GRADEZONE_ROOT,
                                        universal_newlines=True,
                                        shell=True) # to expand *.java on linux
            #only need stdout of (stdout, stderr)
            self.output = compiler.communicate()[0]  # may just be warnings
        except:
            self.logger.exception("Couldn't spawn javac process")
            raise TamarinError('GRADER_ERROR', self.name)

        if self.all:
            javas = glob.glob(os.path.join(tamarin.GRADEZONE_ROOT, '*.java'))
            args['JavaCompiler.compiled'] = True
            for file in javas:
                # XXX: Breaks if have a different non-public class in .java
                if not os.path.exists(file.replace('.java', '.class')):
                    args['JavaCompiler.compiled'] = False
                    self.grade = 'X' if isinstance(self.grade, str) else 0 
                    self.logger.debug("%s did not compile", 
                                      os.path.basename(file))
                    return False
            return True        
        else:
            compiled = args['GradeFile.filename'].replace('.java', '.class')
            if os.path.exists(os.path.join(tamarin.GRADEZONE_ROOT, compiled)):
                self.logger.debug("Compiled %s", args['GradeFile.filename'])
                args['JavaCompiler.compiled'] = True
                return True

        # did not compile    
        self.grade = 'X' if isinstance(self.grade, str) else 0 
        self.logger.debug("%s did not compile", args['GradeFile.filename'])
        args['JavaCompiler.compiled'] = False
        return False


class JavaGrader(Process):
    """ 
    Invokes the assignment-specific TamaringGrader.java-based grader.
    Assumes the grader is already compiled and named XXGrader.class,
    where XX is the assignment name.  The grader will also need the
    .class files generated by TamarinGrader.java. (These can often
    be stored in the GRADERS_ROOT directory.)
    """
    
    def __init__(self, javaPath, required=True, displayName="Tamarin grader"):
        """
        Requires the path to the java executable.
        """
        super().__init__(required, displayName)
        self.java = javaPath
        
    def run(self, args):
        """
        Requires args['GradeFile.filename'], args['GradeFile.assignment'],
        and args['JavaCompiler.compiled'].  
        """
        import tamarin
        from core_type import TamarinError
        
        self.logger.debug("Grading %s with %sGrader", 
                          args['GradeFile.filename'], 
                          args['GradeFile.assignment'])
        graderName = args['GradeFile.assignment'] + 'Grader'
        if not os.path.exists(os.path.join(tamarin.GRADEZONE_ROOT, 
                                           graderName + '.class')):
            raise TamarinError('GRADER_ERROR', 
                               graderName + ".class is not in the gradezone.")
        try:            
            compiled = 1 if args['JavaCompiler.compiled'] else 0
            subfile = args['GradeFile.filename']
            cmd = (self.java, graderName, subfile, str(compiled))
            grader = subprocess.Popen(cmd, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      cwd=tamarin.GRADEZONE_ROOT,
                                      universal_newlines=True)
            (self.output, stderr) = grader.communicate()
        except:
            self.logger.exception("Couldn't spawn Java grader process")
            raise TamarinError('GRADER_ERROR', self.name)
          
        #make sure grader returned something
        try:
            self.grade = float(stderr)
            return True
        except ValueError:
            if self.output:
                self.output += '\n\n'
            else:
                self.output = ''
            self.output += 'GRADER_ERROR: The Tamarin grader did not '
            self.output += 'return a valid grade on stderr.\n'
            self.output += 'Instead, its dying words were: \n'
            self.output += str(stderr) + '\n'
            self.grade = 'ERR'
            return False

class Unzip(Process):
    """
    Unzips the file specified by args['GradeFile.path'] in the gradezone.
    """
    
    def __init__(self, required=False, displayName="Unzipping files"):
        super().__init__(required, displayName)
        self.grade = 'OK'
        
    def run(self, args):
        """
        Unzips the file. Is careful to prevent any absolute paths or symlinks 
        that would allow for  extraction of files to outside the gradezone.  
        If any of such files exist, they are reported to stdout and simply 
        skipped.  If any files are skipped or if no files are unzipped, will
        return False as per a failure.  However, this process is not required
        by default, so grading will likely try to continue.
    
        Prints a list of all unzipped and skipped files. Also stores that list 
        of extracted files into args['Unzip.extracted'].
        """
        import tamarin
        zf = zipfile.ZipFile(args['GradeFile.path'], 'r')
        if not zf.namelist():
            self.output = '[No files found in zipped archive.]\n'
            self.grade = 'X'
        else:
            self.output = ''
        safe = self.validMembers(zf.namelist())
        try:
            zf.extractall(path=tamarin.GRADEZONE_ROOT, members=safe)
            args['Unzip.extracted'] = safe
            self.logger.debug('Unzipped ' + str(len(safe)) + ' of ' +
                                        str(len(zf.namelist())) + ' files')
        except IOError as e:
            self.output += ('...\nABORTING: Could not correctly extract '
                            'one of the files.\n')
            self.output += ('This is probably due to the zipped file '
                'being corrupted or containing a symlink.\n')
            self.logger.warn('Unzip ' + args['GradeFile.filename'] + ' aborted'
                             ' with: ' + str(e))
            self.logger.debug('If GRADZONE permissions are correct, error is '
                              'likely due to a symlink/error in zip file.')
            self.grade = 'X'
            return False
        finally:
            zf.close()
        # problem/False if no files or if we skipped on
        if len(safe) == 0 or len(safe) != len(zf.namelist()):
            self.grade = 'X'
            return False
        else:
            return True
        

    def validMembers(self, members):
        # thanks in part to: http://stackoverflow.com/questions/10060069/
        safe = []
        base = os.path.realpath(os.path.abspath('.'))
        for m in members:
            self.output += m
            extracting = os.path.join(base, m)
            extracting = os.path.realpath(os.path.abspath(extracting))
            if not extracting.startswith(base):
                #would extract to other dir
                self.output += ' [SKIPPED: Would extract to outside of ' +\
                    'gradezone.]\n'
            else:
                self.output += '\n'
                safe.append(m)
        return safe


class VerifyMainFile(Process):
    """
    Verifies--usually after an Unzip--that a given main file exists in the
    gradezone.  If it does exit, replaces args['GradeFile.filename'] with the
    new name.  Note that this leaves all other GradeFile arguments untouched!
    
    The nameTemplate can include any '{$Something.other}', for which replacment
    values will be pulled from args when run.  Most commonly useful will 
    probably be ${GradeFile.user}, etc.  (A special version of string.Template 
    is used to include dots in the identifiers, excluding the first character.)
    
    """
    
    def __init__(self, nameTemplate, required=True, 
                 displayName="Verifying main file"):
        super().__init__(required, displayName)
        self.grade = 'OK'
        self.name = nameTemplate
        
    def run(self, args): 
        import tamarin
        import string
        
        class Temp(string.Template):
            idpattern = '[_a-z][_a-z0-9.]*'
        template = Temp(self.name)
        
        try:
            mainfile = template.substitute(args)
        except KeyError as e:
            self.logger.error("While producing template: %s", e)
            raise
        
        if os.path.exists(os.path.join(tamarin.GRADEZONE_ROOT, mainfile)):
            self.logger.info("Found %s", mainfile)
            args['GradeFile.filename'] = mainfile
            self.grade = 'OK'
            return True
        else:
            self.logger.warn("Did not find %s", mainfile)
            self.output = "Did not find required main file: " + mainfile 
            self.grade = 'X'
            return False
        