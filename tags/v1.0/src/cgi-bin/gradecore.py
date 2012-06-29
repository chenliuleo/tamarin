#!python

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

from tamarin import *
import subprocess

#verbosity settings
SILENT = 0    #print nothing to stdout except errors
CONSOLE = 1   #print a single line describing each stage of grading
HTML = 2      #print all file output to stdout, and HTML format error msgs


def grade(filename, verbosity):
  """
  Grade the given filename (which should be found in SUBMITTED_ROOT), 
  printing to the screen at either SILENT, CONSOLE, or HTML settings.
  
  The filename should be ONLY the base filename, with no path information.
  
  Returns status code: 'DONE' or an error messags such as 'GRADING_ERROR', etc.
  """
  outfile = None
  result = 'OK'
  grade = 'ERR'  #hopefully to be replaced
  if verbosity == CONSOLE:
    print filename + ": "

  try:
    #check filename exists and grab details
    if result == 'OK':
      submitted = SubmittedFile(filename)
    
      #see if we can grade this
      if submitted.fileExt not in EXT_HANDLERS.keys():
        result = 'UNHANDLED_FILE_EXTENSION'

    #see if we should bother grading this
    if result == 'OK':
      if not EXT_HANDLERS[submitted.fileExt][COMPILE_CMD] and \
         not EXT_HANDLERS[submitted.fileExt][GRADE_CMD]:
         if verbosity == CONSOLE:
           print "Skipped: No need to either compile or grade", submitted.fileExt, "files."
         result = 'GRADING_METHOD_UNDEFINED'

    #open the output file to store results
    if result == 'OK':
      try: 
        outfile = openResultsFile(submitted)
        tprint(outfile, '<div class="grader">', verbosity == HTML)
      except TamarinStatusError, tse:
        result = tse.args[0]
      except EnvironmentError: 
        result = 'NO_RESULTS_FILE'
        
    #clean up the gradezone before we start
    if result == 'OK':
      clearGradeZone(verbosity)
    
      #copy the assignment into the gradezone
      if verbosity == CONSOLE:
        print "Copying " + submitted.originalFilename + " into gradezone... "
      shutil.copy(submitted.path, os.path.join(GRADEZONE_ROOT, submitted.originalFilename))

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
  
  #close up output (even if crashed somehow along the way)
  if outfile:
    tprint(outfile, '</div>', verbosity == HTML)
    outfile.close()

  #--SAVE RESULTS--
  #rename the closed gradefile; move the graded file into graded too
  if result == 'OK' or MOVE_PROBLEM_FILES_INTO_GRADED_DIR:
    #only moving files out of submitted if successfully graded;
    #otherwise, we'll leave the output file only, sans grade (for debugging)
    try:
      #outfile.name has the correct path, so we'll just reuse here
      gradedOutput = outfile.name.replace('-.', '-' + str(grade) + '.')
      gradedSubmitted = outfile.name.replace('-.' + GRADER_OUTPUT_FILE_EXT, 
                                             '.' + submitted.fileExt)
      
      #delete any other files already there with same name (through timestamp)
      gradedFiles = glob.glob(outfile.name.replace('-.' + GRADER_OUTPUT_FILE_EXT, '*'))
      if len(gradedFiles) > 1:
        #more than just the output file
        for file in gradedFiles:
          if file != outfile.name:
            os.remove(file)
      
      #move out two files into place
      shutil.move(outfile.name, gradedOutput)
      shutil.move(submitted.path, gradedSubmitted)
    except:
      result = 'COULD_NOT_STORE_RESULTS'

  if result == 'OK':
    result = 'DONE'
    
  #DONE.  Print any real errors encountered along way
  if result != 'DONE' and STATUS[result][0] >= 400:
    printError(result, verbosity == HTML)
    
  return result  
  
  

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


def openResultsFile(submittedFile):
  """
  Given a submitted File to be graded, opens a "filename-.txt" in the correct GRADED directory.

  Returns the opened file handle; 
  otherwise throws a TamarinStatusError (on problems with the assignment dir)
    or (possibly) an IOError
  """
  assignDir = glob.glob(os.path.join(GRADED_ROOT, submittedFile.assignment + '-*'))
  if len(assignDir) <= 0:
    raise TamarinStatusError('NO_SUCH_ASSIGNMENT')
  elif len(assignDir) > 1:
    raise TamarinStatusError('DUPLICATED_ASSIGNMENTS')

  resultsFilename = submittedFile.filename.replace("." + submittedFile.fileExt, 
                                                   "-." + GRADER_OUTPUT_FILE_EXT)
  return open(os.path.join(assignDir[0], resultsFilename), 'w')


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
  

def clearGradeZone(verbosity):
  """
  Recursively deletes all files and directories in the GRADEZONE.
  """
  if verbosity == CONSOLE: 
    print "Cleaning up the gradezone..."
    
  zoneFiles = glob.glob(GRADEZONE_ROOT + '/*')
  for zf in zoneFiles:
    #remove both directories and files
    if os.path.isdir(zf):
      shutil.rmtree(zf)
    else:
      os.remove(zf)    
  return
