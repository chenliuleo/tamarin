
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
import logging
import re
import os
import shutil

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
        in the generated grader output file.  It will be displayed in a 
        preformatted format to preserve any formatting.  It is recommended
        to keep lines to fewer than 80 chars long.
        
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
                elif tamarin.LEAVE_PROBLEM_FILES_IN_SUBMITTED:
                    badFiles.append(submitted[0])
    
            # done looping
            self.logger.info("%d of %d files successfully graded.", 
                             gradedCount, gradedCount + len(badFiles))
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
        * GradeFile.user - all lowercase
        * GradeFile.assignment - for which this file was submitted
        
        Clears the gradezone and copies the submitted file (under its 
        original, non-timestamped name) into the zone.  Then opens a grader 
        output file and runs all process appropriate for that assignment's 
        type.  

        The grader output file starts with <div class="grader">.
        
        For each process, records any grade or output if either is not None.  
        If recording, the process gets its own <div class="graderName">
        section were name is the process's class name.  The grade will then
        be recorded in a 
        <p><span class="displayName">display name:</span> grade</p>.  
        Any output will then follow in a <pre>output</pre>.  Finally, the 
        process's div will be closed with a </div>. 
        
        Whether the process's run passes or fails does not affect output.
        It simply determines whether or not the next process should be 
        invoked.  So, if a Process is going to fail and want the student
        to know why, it should document it somehow in its self.output.
        
        After running all processes, the overall grade is stored in a 
        <p><b>Grade:</b> grade</p> line.  The grade is the sum of all
        grade values (if any was a number).  If none were a number, 
        the grade is 'OK', unless this is replaced by one or more
        processes producing either 'X' or 'ERR'.
         
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
            args['GradeFile.user'] = submitted.username
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

            grade = 'OK'
            passed = True
            try:              
                # run all processes on the submission                
                for p in processes:
                    success = p.run(args)                    
                    if p.grade or p.output:
                        print('<div class="' + p.name + '">', file=graderOut)
                        # save grade summary
                        if p.grade:
                            if not re.match(tamarin.GRADE_RE, p.grade):
                                raise TamarinError('INVALID_GRADE_FORMAT',
                                                   p.name + ' => ' + p.grade)
                            line = "".join('<p><span class="displayName">',
                                           p.displayName, ':</span> ', p.grade,
                                           '</p>')
                            print(line, file=graderOut)
                        
                            # update grade
                            if isinstance(grade, float):
                                try:
                                    grade += float(p.grade)
                                except ValueError:
                                    pass  # p.grade wasn't a number, so ignore
                            else:
                                if p.grade == 'X' or p.grade == 'ERR':
                                    grade = p.grade
                            
                        # save any output
                        if p.output:
                            print('<pre>' + p.output + '</pre>',file=graderOut)
                        print('</div>', file=graderOut)
                        
                    if not success and p.required:
                        self.logger.warn("%s required but failed, so aborting "
                                         "grading run", p.name)
                        grade = 'ERR'
                        passed = False
                        break 
                
            except:
                self.logger.exception('A grading process just crashed!')
                grade = 'ERR'
                passed = False
                # Future: send this through printError on way to file?
                print('<pre>TamarinError: GRADING_CRASH.</pre>')
            finally:
                print('<p><b>Grade:</b> ' + grade + '</p>', file=graderOut)
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
            return True

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


'''
##
## gradecore.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 12 Aug 2008.
##
## Handles the actual details of grading submitted assignments.
## Doesn't run as its own program, but is invoked through the grade 
## function.
##
## Involves moving submitted files from SUBMITTED_ROOT into
## the GRADEZONE, along with the needed grader and support files.
## Then compiles the assignment, and runs the associated grader.
## Note that it never compiles grader files; these must be pre-compiled.
##
## Always prints an output file (usually .txt) with the same name as the
## submitted file.  (This file actually includes some HTML
## markup, but is not a complete HTML document.)
## Additionally, the gradecore can print this same information to 
## the user.
##



def grade(filename, verbosity):
  """
  Grade the given filename (which should be found in SUBMITTED_ROOT), 
  printing to the screen at either SILENT, CONSOLE, or HTML settings.
  
  The filename should be ONLY the base filename, with no path information.
  
  Returns status code: 'DONE' or an error messags such as 'GRADING_ERROR', etc.
  """

    #--COMPILING--
    compiled = 0
    if result == 'OK' and EXT_HANDLERS[submitted.fileExt][COMPILE_CMD]:
      #copy grader files into gradezone (may need them for compiling)
      if result == 'OK':
        #prep will return a complaint if no assign dir found
        result = prepGradeZone(submitted.assignment, verbosity)

      #however, not really an error if not planning to grade (only compile)
      if (result == 'NO_GRADER_DIR' or result =='NO_GRADER_FILES') and \
          not EXT_HANDLERS[submitted.fileExt][GRADE_CMD]:
        if verbosity == CONSOLE:
          print "(No grader files found, but not needed to only compile)"
        result = 'OK'

      #compile assignment
      if result == 'OK':
        result = compile(submitted, outfile, verbosity)
        #determine numerical compile status
        if result == 'OK':
          compiled = 1
        result = 'OK'

    #--GRADING--
    if result == 'OK':
      if EXT_HANDLERS[submitted.fileExt][GRADE_CMD]:
        #copy grader files into gradezone again
        #(Note: This needs to be done (again) after the assignment has been 
        # compiled so that it cannot drop class files that overwrite the grader.)
        if result == 'OK':
          result = prepGradeZone(submitted.assignment, verbosity)

        #run grader  
        if result == 'OK':
          #throws a TSE if not successful
          grade = runGrader(submitted, compiled, outfile, verbosity)

      else:
        #didn't grade, so compile result is the final result
        grade = 'C' if (compiled == 1) else 'NC'

  except TamarinStatusError, tse:
    result = tse.args[0]
  except:
    traceback.print_exc(None, sys.stdout)
    result = 'GRADING_ERROR'
  
  
  

def prepGradeZone(assignment, verbosity):
  """
  Preps the GRADEZONE to grade that assignment by copying the needed 
  base files from GRADERS and the specific grader files from GRADERS/A##.
  
  Because they are copied second, assignment grader directories 
  can contain files that will overwrite ("override") files of the same
  name in the default GRADERS files.
  
  Returns 'OK', 'NO_GRADER_DIR', or 'NO_GRADER_FILES'. 
  """
  result = 'OK'

  if verbosity == CONSOLE:
    print "Copying " + assignment + " grader files into gradezone..."

  #copy all the files from GRADERS_ROOT, which should be present
  #for every grading run    
  if result == 'OK':
    graderFiles = glob.glob(os.path.join(GRADERS_ROOT, '*'))
    for gf in graderFiles:
      #copy files only
      if os.path.isfile(gf):
        shutil.copy(gf, GRADEZONE_ROOT)

  #see if we have a grader dir ready...
  if not os.path.exists(os.path.join(GRADERS_ROOT, assignment)):
    result = 'NO_GRADER_DIR'

  #...complete with files in it
  if result == 'OK':  
    graderFiles = glob.glob(os.path.join(GRADERS_ROOT, assignment, '*'))
    for gf in graderFiles:
      #do a recursive copy of any directories
      if os.path.isdir(gf):
        #remove anything already there so copy will succeed; ignore errors if not there
        shutil.rmtree(os.path.join(GRADEZONE_ROOT, os.path.basename(gf)), True)
        shutil.copytree(gf, os.path.join(GRADEZONE_ROOT, os.path.basename(gf)), True)
      else:
        shutil.copy(gf, GRADEZONE_ROOT)
    if not graderFiles:
      result = 'NO_GRADER_FILES'
          
  return result



def compile(file, outfile, verbosity):
  """
  Compiles the given SubmittedFile (after convertinb back to its original name) 
  in the GRADEZONE.  Writes output of results to outfile.
  
  Returns 'OK' if everything compiles, otherwise 'ASSIGNMENT_COMPILE_FAILED'.
  """
  result = 'OK'

  #document to screen/file what we're about to do to
  if verbosity == CONSOLE:
    print "Compiling " + file.originalFilename + "...",
  #print to file (and to screen if in HTML mode)
  tprint(outfile, '<p><b>Compiling:</b> ', verbosity == HTML)

  #run compiler
  cmd = EXT_HANDLERS[file.fileExt][COMPILE_CMD]
  #replace wildcards
  cmd = cmd.replace("$F", file.originalFilename)
  cmd = cmd.replace("$A", file.assignment)
  
  compile = subprocess.Popen(cmd.split(),  #needs to be a sequence on unix if shell=False
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             cwd=GRADEZONE_ROOT)
  output = compile.communicate()[0]  #only need stdout of (stdout, stderr)

  #determine result
  if EXT_HANDLERS[file.fileExt][COMPILED_EXT] != None:
    #Have an output ext, so check if such a file was produced
    compiledFilename = file.originalFilename.replace(file.fileExt, 
                         EXT_HANDLERS[file.fileExt][COMPILED_EXT])
    if os.path.exists(os.path.join(GRADEZONE_ROOT, compiledFilename)):
      result = 'OK'
    else:
      result = 'ASSIGNMENT_COMPILE_FAILED'
  
  else:
    #no defined output file, so assume that compiler output means failure
    result = ('ASSIGNMENT_COMPILE_FAILED' if output else 'OK')

  #print results to file
  if result == 'OK':
    tprint(outfile, '<span class="success">OK</span></p>', verbosity == HTML)  
  else:
    tprint(outfile, '<span class="fail">FAILED</span></p>', verbosity == HTML)
  if output:
    tprint(outfile, '<pre class="compiler">', verbosity == HTML)
    tprint(outfile, output + '</pre>', verbosity == HTML)

  #finish single console line with result if in that mode
  if verbosity == CONSOLE: 
    print result
    
  return result
  
  
def runGrader(file, compiled, outfile, verbosity):
  """
  Runs the grader for the given file.  The compiled status is required
  so that the grader can determine the grade, even if the assignment did
  not compile.  Writes results (both stdout and stderr) to outfile 
  (and maybe to screen, based on verbosity level).
  
  All files should already be compiled and ready to go in GRADEZONE.
  
  Returns the grade if the grader returns a valide float on stderr; 
  otherwise throws a TamarinStatusError('GRADING_ERROR').
  (May also throw other exceptions if there's a problem with the files.)
  """
  result = 'OK'
  
  #document to screen/file what we're about to do to
  if verbosity == CONSOLE:
    print "Grading " + file.originalFilename + "...",
  #print to file (and to screen if in HTML mode)
  tprint(outfile, '<p><b>Grading Output:</b></p><pre class="grader">', verbosity == HTML)
  
  #run grader
  cmd = EXT_HANDLERS[file.fileExt][GRADE_CMD]
  #replace wildcards
  cmd = cmd.replace("$F", file.originalFilename)
  cmd = cmd.replace("$A", file.assignment)
  cmd = cmd.replace("$C", str(compiled))
  grader = subprocess.Popen(cmd.split(), 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=GRADEZONE_ROOT)
  (stdout, stderr) = grader.communicate()

  #record output (if any)
  stdout = stdout.replace('<', '&lt;')
  stdout = stdout.replace('>', '&gt;')
  tprint(outfile, stdout + '</pre>', verbosity == HTML)
  
  #make sure grader returned something
  if not stderr:
    raise TamarinStatusError('NO_GRADER_OUTPUT')
  
  #record grader feedback
  if result == 'OK':
    try:
      grade = float(stderr)
      #format here is important!  See displaycore.displaySubmission in master mode.
      tprint(outfile, '<p><b>Grade:</b> ' + str(grade) + '</p>', verbosity == HTML)
    except ValueError:
      result = 'GRADER_FAILED'
      tprint(outfile, '<p><i>Grader failed to complete!</i>', verbosity == HTML)
      tprint(outfile, 'Its dying words were: </p><pre>', verbosity == HTML)
      tprint(outfile, stderr + '</pre>', verbosity == HTML)
  
  if result == 'OK':
    #finish console line
    if verbosity == CONSOLE: 
      print grade
    return grade
  else:
    #error
    raise TamarinStatusError(result)


'''