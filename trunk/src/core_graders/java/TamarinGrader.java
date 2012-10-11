import java.lang.reflect.*; //we do a lot of this here
import java.io.*;           //for I/O redirection
import java.util.regex.*;   //for pattern matching
import java.util.Scanner;   //for reading through source code files

/**
 * Serves as a kind of grader library for specific Tamarin graders,
 * offering a number of useful utility methods for grading Java methods,
 * etc. An instance of TamarinGrader is specific to the single assignment
 * submission being graded, and so it also contains a number of details
 * about that submission file.
 * <p>
 * When done, graders must return their final results on
 * <code>System.err</code>. A decimal (<code>double</code>) value is
 * assumed to be a grade. Anything else is interpreted as an error message
 * (assumed to be grading failure) and is passed to the user by Tamarin.
 * <p>
 * TamarinGrader is <i>not</i> thread-safe.  That is, don't try to run two
 * grading threads at once.
 * <p>
 * See the Tamarin wiki for more on writing and using Java graders.
 *
 * @author Zach Tomaszewski
 * @since 31 Aug 2008
 * @version 16 Jan 2012
 */
public class TamarinGrader {

//XXX: JOptionPanes can hang Tamarin.  By themselves, they're fine.  But killing one,
//catching the exception in the submission, and popping up another seems to hang Tamarin.
//See TacrasA17 for an example of this.
//LATER: I don't think this it true anymore, but still need to test if that's so.


  //--Features of the assignment submission to be graded--

  /** The filename of the submission being graded */
  public String filename;
  /** The submission file being graded */
  public File file;
  /** Whether this submission compiled (as specified to {@link #init}) */
  public boolean compiled;
  /** The submission's main class name,
      assumed from the name of the submitted .java filename */
  public String className;
  /** This submission's main class (if the file was compiled) */
  public Class _class;
  /** The grade this submission current has (added to by each test) */
  public double grade;


  //--Grading and test controls--

  /**
   * Whether regular expression searches of output and source code
   * should be case-sensitive or not.  (Default: false)
   */
  public boolean caseSensitive = false;

  /**
   * Common strings that tend to appear in error messages but generally
   * not in prompts for input.  This can be handy when testing output
   * for likely error messages.
   */
  public String[] errorMesg = {"error", "sorry", "n't", "not", "bad",
                               "valid", "only", "must", "try", "again",
                               "correct", "wrong"};

  /**
   * The amount by which two floating points number can differ and
   * still be considered equal for grading purposes.
   * <p>
   * This is used when testing methods that return a floating point
   * value (either a <code>float</code> or <code>double</code>).
   * When such values are the result of a calculation, they can vary
   * in the last few decimal places depending on the order in which
   * the operations  were performed.  This means comparing them
   * directly with == to the expected value can often lead to failed
   * tests when the difference was not actually significant.
   * <p>
   * If this variable == 0.0, doubles and floats are compared exactly.
   * (Default: 1e-9)
   */
  public double epsilon = 1e-9;

  /**
   * If <code>true</code>, will mark any testMethod description in which
   * the use of {@link #epsilon} determined the success of the test.
   * Specifically, when the expected and actual result of a method test
   * are deemed equal due to the use of {@link #epsilon} but are not
   * strictly == normally, the given String is append to the result value
   * in any printed description of the test.  If <code>null</code> or "",
   * the successful use of epsilon is not marked in grader output.
   * (Default: " ~")
   */
  public String markEpsilon = " ~";

  /**
   * The number of milliseconds this grader should give a method invoked from
   * the graded assignment to finish.  This prevents infinite loops by killing
   * the invoked method if it takes too long to finish.  However, if set too
   * low this may incorrectly kill time-intensive processes early, especially
   * on a slow grading machine.  (Default: 20000 ms)
   */
  public int timeout = 20000;

  /**
   * When killing a hung method, the grader gives the interrupted thread this
   * much time to finish up whatever it needs to do before going ahead and
   * calling Tread's deprecated stop() method. (Default: 200ms)
   */
  public int cleanupTimeout = 200;


  //--INPUT/OUTPUT Streams--

  /*
   * Note: After a testMethod run, all streams will point to a String (empty
   *       or otherwise), and so won't be null.
   */

  /**
   * The string that tested methods read from instead of/as if
   * from <code>System.in</code>.
   * Set this before calling <code>testMethod</code> if you expect the
   * method to read input from System.in.  After the call, the string will
   * contain any remaing text not read in.
   */
  public String in = "";

  /**
   * The string that tested methods will write to instead of/as if
   * from <code>System.out</code>.
   * Check this for the method's output after calling testMethod.
   */
  public String out = "";

  /**
   * The string that a tested method will write to
   * instead of/as if from <code>System.err</code>.
   * However, see {@link #redirectErrToOut}
   */
  public String err = "";

  /**
   * If true, output sent to System.err will instead be appended to
   * {@link #out}.  (The err redirection stream is still constructed,
   * it is just not used and so will be empty after any test.)
   * (Default: true)
   */
  public boolean redirectErrToOut = true;

  /** The maximum number of byte a single method invocation can output
      to System.out (which is actually redirected to <code>this.out</code>).
      This primarily serves to cap output for infinite output loops, which
      may still output MBs of text before killed due to time out.
      (Default: 10000 bytes) */
  public int maxOutBytes = 10000;
  /** The maximum number of bytes a single method invocation can output
      to System.err (as described for {@link #maxOutBytes}).
      (Default: 1000 bytes)  */
  public int maxErrBytes = 1000;

  /**
   * Whether to echo any input read so that it also appears in the output.
   * When true, any input read from <code>this.in</code>
   * also appears in (is echoed to) <code>this.out</code>,
   * thus preserving normal output formatting and making tests clearer.
   * However, if you don't want any input read from <code>this.in</code>
   * to be echoed to <code>this.out</code> as it is read, set this to
   * <code>false</code> before testing a method.  (Default: true)
   */
  public boolean echoInput = true;


  //--Advanced features--

  /**
   * Whether to reload the given class before testing a method, such as with
   * <code>testMethod</code>.  No class is reloaded if this is null.
   * <p>
   * If non-null, the given class will be loaded with a custom ClassLoader.
   * This forces a reset of all static variables (such as input stream readers,
   * etc.)  However, it also introduces a host of other problems.
   * <p>
   * For example, it is possible for more than one definition of the same class
   * to exist in the VM at the same time if loaded by two different ClassLoaders.
   * These classes are treated as being in effectively two different runtime
   * packages.  Thus, if this grader is loaded by the default ClassLoader and
   * the assignment code is loaded by another differernt ClassLoader
   * (as happens when <code>reloadClass</code> is not null),
   * then this grader suddenly can't access any non-public members in the
   * assignment class (even when both are in the same directory/package).
   * This means this grader won't even able to invoke main on the submitted
   * code if the containing class is not public.
   * <p>
   * Also, creating an instance, reloading the class, and then attempting to
   * invoke methods on the original instance will fail.
   * <p>
   * In short, introducing another ClassLoader is a headache and a source of
   * subtle input/output and member access bugs.  But sometimes you may still
   * want to do it to force a reset of static variables.
   * However, you should definitely know what you're doing before playing
   * with it.
   * <p>
   * Normally, TamarinGrader only uses this when running a class's main method,
   * since main is always public and this closely models normal main method
   * behavior of the class being reloaded each time the program is run.
   * (Note that, even in this case, any other classes used by the main class
   * may not be reloaded.  And, again, the reloaded class itself must be
   * public to access any of its members after the reload.)
   */
  protected Class reloadClass = null;

  /**
   * Whether to treat an attempt to end a program using System.exit (or similar
   * requests to exit the VM) as an error.  Such a request could come from within
   * any method or constructor.  It cannot be allowed by TamarinGrader (as it would
   * crash/quit the grader), but by default it is not reported as an error but only
   * as a warning.  (Default: false)
   */
  protected boolean exitVMIsError = false;

  /**
   * The text to prepend to any output from the grader, to differentiate it
   * from output from the submission being graded.  Note that the Default
   * is currently used by Tamarin's gradecore.py to markup output with
   * <span>s for html display.  (Default: "## ")
   */
  protected String prepend = "## ";

  /**
   * Turn off the security manager.
   * This is a hold-out from earlier versions of Tamarin that would start
   * crashing due to security prohibitions.  This turned out to be due to
   * how the class loader works and how it reloads a class after the 16th
   * method call.  This bug has been fixed, but, just in case you ever
   * find you're getting weird security exceptions, try disabling security
   * in your grader and see if it fixes the problem.
   */
  protected boolean disableSecurity = false;

  /**
   * Frequently, when debugging this class, problems are masked by the fact
   * that all output (and input) is being redirected.  Set this variable to
   * false so you can see what's going on.
   * <p>
   * During normal operation, TamarinGrader methods are often examining the
   * stored output and reading from a safely prepared input stream, so turn
   * this off <b>only</b> when debugging!
   */
  protected boolean redirectStreams = true;


  //storage for the real System.in, out, and err, so they can be replaced again
  private InputStream _in;
  private PrintStream _out;
  private PrintStream _err;

  //the actual buffers that in, out, and err will be using
  private OutputStream outBuffer;
  private OutputStream errBuffer;
  private InputStream inBuffer;



  //-- MAIN (init) --

  /**
   * Checks that appropriate command line arguments were given and
   * returns a new instance of TamarinGrader to be used to grade the
   * given submssion.
   * <p>
   * This method is meant to be used by the sub-grader so that it does
   * not have to bother parsing its own command line args:
   *
   * <pre>
   *   public static void main(String[] args) {
   *     TamarinGrader grader = TamarinGrader.init(args);
   *     //... grade assignment using grader object
   *   }
   * </pre>
   * <p>
   * The command line arguments given in <code>args</code> should include
   * 1) the name of the file to grade (in the current directory) and
   * 2) the compile status.
   * This way the specific grader can determine the grade recieved
   * for compiling. For compile status, 1 is compiled;
   * anything else (preferably 0) is not compiled.
   * <p>
   * If anything is wrong, it will report it appropriately to stderr
   * and then call <code>System.exit()</code>
   */
  public static TamarinGrader init(String[] args) {

    //check for the correct # of args
    if (args.length != 2) {
      System.err.println("Grader not invoked correctly: " + args.length +
                         " arguments given (should be 2).");
      System.exit(1);
    }

    try {
      //translate compiled status from int to a boolean
      int compiledStatus = Integer.parseInt(args[1]);
      boolean compiled = (compiledStatus == 1);

      //return the new grader object
      return new TamarinGrader(args[0], compiled);

    }catch (NumberFormatException nfe) {
      System.err.println("Grader not passed an integer for compiled status " +
                         "as its second arg.");
    }catch (IllegalArgumentException iae) {
      //problem from TamarinGrader constructor
      System.err.println("TamarinGrader: " + iae.getMessage());
      if (iae.getCause() != null) {
        System.err.println("Caused by: " + iae.getCause());
      }
    }
    //made it here because of an exception, so quit
    System.exit(1);
    return null;  //to get it to compile
  }


  //-- CONSTRUCTOR --

  /**
   * Creates a grader for the given file, which should
   * have compiled with the given status.
   *
   * @param filename  The name of the .java file this grader will be grading.
   * @param compiled   Whether the file has been compiled successfully
   *                  to a .class file.
   *
   * @throws IllegalArgumentException  if filename does not correspond to an
   *                                   existing .java file, or if that .java file's
   *                                   class of the same name cannot be loaded.
   */
  public TamarinGrader(String filename, boolean compiled)
                       throws IllegalArgumentException {

    this.filename = filename;
    this.file = new File(filename);
    this.compiled = compiled;
    this.grade = 0.0;

    //check that such a file really exists
    if (!this.file.exists()) {
      throw new IllegalArgumentException("Given assignment file \"" + filename +
                                         "\" does not exist.");
    }

    if (compiled) {
      //make sure said file really is a valid, compiled, loadable java file.
      try {
        this.className = this.filename.substring(0, this.filename.indexOf(".java"));
      }catch (StringIndexOutOfBoundsException sioobe) {
        throw new IllegalArgumentException("Given compiled assignment file " +
                                           "is not a .java file.");
      }

      try {
        //Need to redirect streams before loading class.  Otherwise, when class
        //is loaded, any static members will be initialized, and any static
        //Scanners or other stream readers will latch on to real stdin,
        //causing problems.
        //Such problems will probably still exist (trying to read from empty streams),
        //but at least it won't lead to a grader hang.
        this.setTestStreams(); //reset in finally in case of class loader exceptions
        this._class = Class.forName(this.className);
      }catch (ClassNotFoundException cnfe) {
        throw new IllegalArgumentException("Given assignment not loadable " +
              "(really compiled?).");
      }catch (Throwable e) {
        throw new IllegalArgumentException("Could find but not load given assignment", e);
      }finally {
        this.resetStreams();
      }
    }
  }


  // ===== PUBLIC methods: INSPECTING OUTPUT methods =====

//Notes:
//--add tip somewhere that you can set grader.out and then regex on it.
//--due to varargs, regexes always at end

//count: return the total number of matches found
//find: the number of multiple regexes found to match at least once
//is: existance or not (of any)
//are: exitance or not of all

//Still needed:
//
// getLinesOfOutput()/(int) - returns a String[] of all lines
// countInLimitedOutput(int lineLimit, String... regexes) - int
//  --getLines, join, and temporarily replace this.out to do a normal search
// isInLO, areInLO, findInLO
//
// For when you actually want to check out the data yourself:
// ?filterLinesFor(String[] lines, String... regexes) - String[] subset containing any regex
// ??joinLines(String[] lines) - String  [when you can then assign to this.out to search further)
//
// ??isErrorMessageInOutput()/(int limit) - isInLO using stored error regexes
//
// Some sort of "in-order" search for a list of regexes.  Basically,
// findInOrderInOutput.  So, pick up where the last one left off.
// If it can't find the next one, skip it and continue.
//

  /**
   * Returns true if something is in <code>this.out</code>
   * (ie, whether a tested program printed at least one character).
   */
  public boolean hasOutput() {
    return (this.out != null && !this.out.equals(""));
  }


  /**
   * Returns whether <i>all</i> of the given regexes appear in
   * <code>this.out</code> at least once.
   * Since each regex is searched for separately, they may
   * overlap/match the same output.
   * <p>
   * When searching for only a single regex, is equivalent to
   * {@link #isInOutput}.
   * <p>
   * Returns true if all are found; otherwise false.
   *
   * @see #countInOutput
   */
  public boolean areInOutput(String... regexes) {
    //check for existance of each regex
    for (String regex : regexes) {
      if (this.countInOutput(regex) == 0) {
        //didn't find this one
        return false;
      }
    }
    //seem to have found at least one match for each of them
    return true;
  }

//XXX: Make countInSource mutliline too.
  /**
   * Returns the total number of times the given regular expressions
   * appear in <code>this.out</code>.
   * <p>
   * After finding a match, resumes the search just after the end of the
   * previous match. Thus, the search may find more than one match of the
   * same regex per line and regexes (if written to do so) may span line
   * boundaries.  The search uses Pattern.MULTILINE, so ^ and $ match the
   * beginning and end of any line (not just the beginning and end of all
   * output).
   * <p>
   * If more than one regex is given, returns the
   * sum of the total matches found for each regex.  For example, if the
   * <code>this.out.equals("Hello, World")</code>, then
   * <code>countInOutput("Hello", "o") == 3</code>
   * <p>
   * Searches are case-sensitive or not depending on the current value of
   * <code>this.caseSensitive</code>.
   * <p>
   * If <code>!this.hasOutput()</code>, 0 matches will be found.
   * <p>
   * Note that regexes with a lot of wild cards can cause a hang as it needs
   * to do a lot of backtracking.  Negated character classes may be safer than
   * using ".".
   */
  public int countInOutput(String... regexes) {
    if (!this.hasOutput()) {
      return 0;  //avoid an NPE by trying to match against null
    }

    //repeat for each regex in passed list
    int found = 0;
    for (String regex : regexes) {
      int std = Pattern.MULTILINE;
      Pattern toFind = (this.caseSensitive) ?
                       Pattern.compile(regex, std) :
                       Pattern.compile(regex, std | Pattern.CASE_INSENSITIVE);
      Matcher search = toFind.matcher(this.out);
      while (search.find()) {
        //count all matches found
        found++;
      }
    }
    return found;
  }

  /**
   * Returns the number of the given regexes that appear in <code>this.out</code>.
   * That is, searches for the existance of each regex, adding 1 to the returned
   * total if it is found at least once, or 0 if it is not found.
   * <p>
   * The idea behind this method is that, if you are looking for 5 answers in
   * the output, pass them as parameters to this method and it will return the
   * number of those different regexes that actually found/matched something.
   * Just remember that, as always, different regexes may end up matching the
   * same text.
   * <p>
   * Because find returns the number of regexes that matched, it is often a
   * mistake to use it with only one regex.  (countInOutput is usually meant
   * instead.) In this case, it would act like isInOutput,
   * only returning 1 or 0 instead of true or false (regardless of
   * the number of matches this single regex found).
   */
  public int findInOutput(String... regexes) {
    int found = 0;
    //count how many of the regexes match something
    for (String regex : regexes) {
      if (this.countInOutput(regex) > 0) {
        found++;
      }
    }
    return found;
  }

  /**
   * Returns whether <i>any</i> of the given regexes appears in
   * <code>this.out</code>.
   * <p>
   * When searching for only a single regex, is equivalent to
   * {@link #areInOutput}.
   * <p>
   * Returns true if a match is found for at least one of the given regexes;
   * otherwise false.
   *
   * @see #countInOutput
   */
  public boolean isInOutput(String... regexes) {
    //check for existance of each regex
    for (String regex : regexes) {
      if (this.countInOutput(regex) > 0) {
        //found a match
        return true;
      }
    }
    //didn't find any of them
    return false;
  }

//---------------------------------------------

  /**
   * Returns all the lines of output in a Lines object for easy filtering
   * based on regex pattern matching.  If no output, returned Lines is emtpy.
   */
  public Lines getOutputLines() {
    //nothing to search through
    if (!this.hasOutput()) {
      return new Lines(new String[0]);
    }else {
      return new Lines(this.out.split("[\\n\\r]+"));
    }
  }

  @Deprecated
  public String[] getLinesFromOutput(String[]... regexes) {
    Lines lines = this.getOutputLines();
    for (String[] regex : regexes) {
      lines = lines.any(regex);
    }
    if (lines.isTrue()) {
      return lines.toArray();
    }else {
      return null;
    }
  }


// ===== PUBLIC methods: INSPECTING SOURCE methods =====

  /**
   * Returns whether <i>all</i> of the given regexes appear in
   * the source code at least once.
   * Since each regex is searched for separately, they may
   * overlap/match the same output.
   * <p>
   * When searching for only a single regex, is equivalent to
   * {@link #isInOutput}.
   * <p>
   * Returns true if all are found; otherwise false.
   *
   * @see #countInSource
   */
  public boolean areInSource(boolean includeComments, boolean includeStrings,
                             String... regexes) {
    //check for existance of each regex
    for (String regex : regexes) {
      if (this.countInSource(includeComments, includeStrings, regex) == 0) {
        //didn't find this one
        return false;
      }
    }
    //seem to have found at least one match for each of them
    return true;
  }

  /**
   * This method will search the submitted file's source code
   * for each of the given regexes,
   * returning the total number of matches found.
   * <p>
   * The source code is assumed to be in <code>this.file</code>.
   * <p>
   * If <code>includeCommments</code> is false, any material in Java comments
   * will be removed before performing the search.
   * <p>
   * Similarly, if <code>includeStrings</code> is false,
   * any text found in "quotes" will be skipped.  This includes any Strings
   * found within quotes.   This method can handle escaped quotes (\").
   * If a String is malformed in that it does not close by the end of the line,
   * this method will treat the end of the line as the end of the String.
   * <p>
   * Searches are case-sensitive based on the current value of
   * <code>this.caseSensitive</code>
   * <p>
   * Returns the total number of matches found.
   * If an I/O error is encountered (such as if the submitted file
   * could not be found/read) will return -1 instead.
   */
  public int countInSource(boolean includeComments, boolean includeStrings,
                           String... regexes) {
    int found = 0;
    try {
      Scanner file = new Scanner(this.file);
      String contents = "";

      //add each line into contents, removing any comments/Strings as necessary
      String line;
      boolean inBlockComment = false;
      while (file.hasNextLine()) {
        line = file.nextLine();

        while (!includeStrings && line.contains("\"")) {
          //need to remove content in quotes, regardless of where it occurs.
          //(do this first to avoid problems like S.o.println("//");)
          int start = line.indexOf("\"");
          while (start > 0) {
            //find the true, unescaped start
            if (line.charAt(start - 1) == '\\' || line.charAt(start - 1) == '\'') {
              //escaped or char literal, so see if we can find another "
              start = line.indexOf("\"", start + 1);
            }else {
              break;  //found a real starting "
            }
          }
          if (start >= 0) {
            //okay, found a real start; let's find the end
            int end = line.indexOf("\"", start + 1);
            while (end > 1) {
              //find the true, unescaped end
              //(won't find a char literal in a string though)
              if (line.charAt(end - 1) == '\\') {
                //escaped, so see if we can find another "
                end = line.indexOf("\"", end + 1);
              }else {
                //not escaped
                break;
              }
            }
            if (end > 0) {
              //grab before and after string, but don't include ending "
              line = line.substring(0, start) + line.substring(end + 1);
            }else {
              //didn't find an ending ", so a malformed string (drop to \n)
              line = line.substring(0, start);
            }

          }else {
            //" not really the start of a string, such as: char quote = '"';
            break;
          }
        }

        if (!includeComments) {
          //need to remove comment material

          //a //comment  (currently removing even if within a /* ... */)
          // (want to check for // first to catch comments like: "//******")
          if (line.contains("//")) {
            String nonComment = line.substring(0, line.indexOf("//"));
            if (inBlockComment && line.contains("*/")) {
              //then only want to go to */, rather than end of line
              nonComment += line.substring(line.indexOf("*/"));
              //now let "*/" case below deal with it
            }
            line = nonComment;
          }

          //start of /* ... */
          if (line.contains("/*")) {
            if (line.contains("*/")) {
              //comment contained within the line, so can just cut it out
              line = line.substring(0, line.indexOf("/*")) +
                     line.substring(line.indexOf("*/") + 2);
            }else {
              //comment doesn't end on line, so cut to end of line
              //and keep an eye open for the end marker
              line = line.substring(0, line.indexOf("/*"));
              inBlockComment = true;
            }
          }
          //end of /* ... */
          if (inBlockComment) {
            if (line.contains("*/")) {  //reached end of block
              line = line.substring(line.indexOf("*/") + 2);
              inBlockComment = false;
            }else {
              //in block comment, so toss this line
              line = "";
            }
          }
        }

        //now, if line's not empty, append it to contents (keeping linebreaks)
        if (!line.equals("")) {
          contents += line + "\n";
        }
      }
      file.close();

      //now have file contents, so get read to search
      //cheat: use findInOutput on this.out to perform actual search
      String oldOut = this.out;
      this.out = contents;
      found = this.countInOutput(regexes);
      this.out = oldOut;
      return found;

    }catch (FileNotFoundException fnfe) {
      return -1;
    }
  }

  /**
   * As with {@link #findInOutput}, returns the number of the given regexes
   * found in the source code.
   *
   * @see #countInSource
   */
  public int findInSource(boolean includeComments, boolean includeStrings,
                          String... regexes) {
    int found = 0;
    //count how many of the regexes match something
    for (String regex : regexes) {
      if (this.countInSource(includeComments, includeStrings, regex) > 0) {
        found++;
      }
    }
    return found;
  }

  /**
   * Returns whether <i>any</i> of the given regexes appears in
   * the source code.
   * <p>
   * When searching for only a single regex, is equivalent to
   * {@link #areInSource}.
   * <p>
   * Returns true if a match is found for at least one of the given regexes;
   * otherwise false.
   *
   * @see #countInSource
   */
  public boolean isInSource(boolean includeComments, boolean includeStrings,
                            String... regexes) {
    //check for existance of each regex
    for (String regex : regexes) {
      if (this.countInSource(includeComments, includeStrings, regex) > 0) {
        //found a match
        return true;
      }
    }
    //didn't find any of them
    return false;
  }

  /**
   * Returns whether the given class can be loaded by this grader.
   *
   * This is a decent way to see if a submitted file provides a
   * given class.  However, note that a class can also be loaded
   * from other sources, such as the java library or grader files
   * copied into the same directory.  In this case,
   * <code>isInSource(false, false, "class\\s+ClassName")</code>
   * might be a better test.
   *
   * This method is generally silent, but will print a message if
   * the class cannot be loaded due to a LinkageError or
   * ExceptionInInitializerError.
   */
  public boolean hasClass(String className) {
    boolean hasClass = false;
    try {
      try {
        Class.forName(className);
        hasClass = true;
      }catch (ClassNotFoundException cnfe) {
        hasClass = false;
      }
    }catch (Error e) {
      this.println("Couldn't load class " + className + ": " + e);
    }
    return hasClass;
  }

//===============================================================

// ===== PUBLIC Methods: PRINTING and REPORTING methods

  /**
   * Prints the given message to stdout, but prepends the TamarinGrader prompt
   * {@link #prepend}
   * to differentiate grader output from program output.
   */
  public void print(Object string) {
    System.out.print(this.prepend + string);
  }

  /**
   * Prints the given message to stdout, but prepends the TamarinGrader prompt
   * {@link #prepend}
   * to differentiate grader output from program output.
   * Then ends the line with a newline.
   */
  public void println(Object string) {
    System.out.println(this.prepend + string);
  }

  /**
   * Prints a blank line prepended by the TamarinGrader prompt.
   *
   * @see #println(Object)
   */
  public void println() {
    System.out.println(this.prepend);
  }

  /**
   * Prints whatever output is current in stored in <code>this.out</code>.
   * Will do this in a safe, pretty way:
   * if it is null or an empty string, will print nothing.
   * If <code>this.out</code> does not end in a newline,
   * this method will add one.
   * <p>
   * As this is the output of the program being graded, no
   * {@link #prepend}ing is done.
   */
  public void printOutput() {
    if (this.hasOutput()) {
      //need to print something
      if (this.out.endsWith("\n")) {
        System.out.print(this.out);
      }else {
        System.out.println(this.out);
      }
    }
  }


  /**
   * Prints this grader's grade to both stdout (with this.println)
   * and to stderr.
   * <p>
   * Will round the grade to 3 digits
   * after the decimal place (with a minimum of 1 digit after the decimal).
   * This is often handy since if you're doing any math with a double,
   * there's always a chance that it just slightly off its "true"
   * value, which makes for unsightly long printing.
   */
  public void reportGrade() {
    java.text.DecimalFormat format = new java.text.DecimalFormat();
    format.setMaximumFractionDigits(3);
    format.setMinimumFractionDigits(1);
    this.println("");
    this.println("Tamarin grade: " + format.format(this.grade));
    System.err.println(format.format(this.grade));
  }


  /**
   * Reports whether a given test passed or failed, and adjusts this
   * grader's grade total accordingly.
   * <p>
   * Prints the <code>mesg</code> describing this test,
   * prepended as if by using {@link #println(Object) println}.
   * Then prints the score acheived (either <code>worth</code> if the test passed
   * or 0 if the test failed) over the total worth of the test.
   * Finally prints <code>[PASS]</code> or <code>[FAIL]</code>.
   * <p>
   * So, if <code>mesg.equals("Success")</code>, output will look something like
   * this:
   * <pre>
   * <code>## Success                          (1.0 points) [PASS]</code>
   * </pre>
   * <p>
   * Returns (and adds to {@link #grade}) <code>worth</code>
   * if <code>passed == true</code>, else <code>0</code>.
   */
  public double result(boolean passed, String mesg, double worth) {
    StringBuffer output = new StringBuffer(mesg);
    java.text.DecimalFormat format = new java.text.DecimalFormat();
    format.setMaximumFractionDigits(3);
    String points = " (" + format.format(worth) + " points) ";
    String result = (passed) ? "[PASS]" : "[FAIL]";
    //indent result to far right column
    for (int i = output.length();
         i < (79 - points.length() - result.length() - this.prepend.length());
         i++) {
      output.append(" ");
    }
    output.append(points);
    output.append(result);
    this.println(output.toString());
    double outcome = (passed) ? worth : 0;
    grade += outcome;
    return outcome;
  }

  /**
   * Reports whether a given test passed or failed,
   * displaying one of two result messages depending.
   * Also adjusts this grader's {@link #grade} total accordingly.
   * <p>
   * If <code>passed</code> is true, the <code>success</code> String is printed;
   * if not, <code>failure</code> is printed.  Otherwises, output follows
   * the formatting of {@link #result(boolean, String, double)}
   * <p>
   * Returns <code>worth</code> if <code>passed == true</code>,
   * else <code>0</code>.
   */
  public double result(boolean passed, String success, String failure, double worth) {
    return this.result(passed, (passed) ? success : failure, worth);
  }

  /**
   * Reports whether a given test passed, failed, or partially
   * passed. Also adjusts this grader's grade total accordingly.
   * <p>
   * Prints <code>mesg</code>, which is simply a description of the test.
   * If <code>score</code> is <= 0, the test <code>FAIL</code>ed;
   * if it is == <code>worth</code>, then the test <code>PASS</code>ed;
   * if it is > <code>worth</code>, then it is <code>EXTRA</code>;
   * otherwise, it only <code>PART</code>ially passed.
   * Prints this result with score/worth the same general format as
   * {@link #result(boolean, String, double)}
   * <p>
   * Returns (and adds to <code>this.grade</code>) <code>score</code>.
   */
  public double result(double score, String mesg, double worth) {
    StringBuffer output = new StringBuffer(mesg);
    java.text.DecimalFormat format = new java.text.DecimalFormat();
    format.setMaximumFractionDigits(3);
    String points = " (" + format.format(score) + "/"+ format.format(worth) + " points) ";
    String result;
    if (score - worth >= 1e-5) {
      //score more than worth (excluding margin of error): extra credit
      result = "[EXTRA]";
    }else if (Math.abs(score - worth) <= 1e-5) { //basically, == 0
      //to prevent false PARTs due to double rounding errors
      result = "[PASS]";
    }else if (score <= 0) {
      result = "[FAIL]";
    }else {
      result = "[PART]";
    }
    //indent result to far right column
    for (int i = output.length();
         i < (79 - points.length() - result.length() - this.prepend.length());
         i++) {
      output.append(" ");
    }
    output.append(points);
    output.append(result);
    this.println(output.toString());
    this.grade += score;
    return score;
  }



//===== PUBLIC methods: RUNNING and TESTING methods =====

  /**
   * Runs the main method of {@link #_class} with the given arguments
   * (which can be empty/none).  Then calls {@link #printOutput()} to
   * display any printed output.
   * <p>
   * Before running main, this method will reload the given class (if it
   * compiled).  This forces a reset of all static variables (such as buffered
   * stream readers, etc) and more closely models the normal execution of main
   * as a fresh process.
   * <p>
   * To run main without reloading or to run it without printing output, try:
   * <pre>
   *   this.runMethod(this._class, "main", (Object) args);
   * </pre>
   * <p>
   * Returns false if the class cannot be reloaded; otherwise returns whether
   * main completed without exceptions.
   */
  public boolean runMain(String... args) {
    Class reloadSetting = this.reloadClass;
    this.reloadClass = this._class;
    boolean result = this.testMethod(null, void.class, this._class, "main", (Object) args);
    this.reloadClass = reloadSetting;
    this.printOutput();
    return result;
  }


  /**
   * As {@link #invokeMethod}, but does not throw an exception.
   * Instead, invokes <code>inst.methodName(args)</code> and returns the result
   * produced by the method.
   * If the method cannot be successfully invoked (such as when
   * <code>inst</code> is <code>null</code> or if the method throws an
   * exception) or if the invoked method has a void return type, returns
   * <code>void.class</code> instead.
   * <p>
   * This method runs silently (does not print to output), even if an exception
   * is produced.
   */
  public Object runMethod(Object inst, String methodName, Object... args) {
    try {
      return this.invokeMethod(inst, methodName, args);
    }catch (InvocationException ie) {
      return void.class;
    }
  }

  /**
   * == <code>this.testMethod(null, expected, inst, methodName, args)</code>.
   * That is, runs as <code>testMethod</code> using the default test description.
   */
  public boolean testMethod(Object expected, Object inst, String methodName, Object... args) {
    return this.testMethod(null, expected, inst, methodName, args);
  }

  /**
   * Simply invokes the given method safely.
   * Does not print any output.
   * Returns the object returned by the method (which may be null).
   * <p>
   * If the method cannot be invoked, will throw a
   * TamarinGrader.InvocationException containing the expection generated.
   * This will also happen if the given <code>inst</code> is null.
   */
  public Object invokeMethod(Object inst, String methodName, Object... args)
                            throws TamarinGrader.InvocationException {
    try {
      if (inst == null) {
        throw new TamarinGrader.InvocationException(
                "Could not invoke method on null object.",
                new NullPointerException());
      }
      Class targetClass = (inst instanceof Class) ? (Class) inst : inst.getClass();
      Class[] params = this.getParameters(args);
      Method method = this.getMethod(targetClass, methodName, params);
      return this.invokeMember(inst, method, args);

    }catch (Exception e) {  //from not finding it
      throw new TamarinGrader.InvocationException(e);
    }
  }


//XXX: What if constructor is expected to return an exception?
//     Make a testConstructor method for this:
//     testConstructor(String desc, Class expected, Class toConstr, args)

  /**
   * Constructs and returns an instance of the class <code>toConstruct</code>.
   * <p>
   * First displays the given description of the test.
   * If desc.equals(""), nothing is printed at all by this test
   * (even if there is an error).
   * If desc is null, will instead
   * provide the default of "Constructing toConstruct(args)", where toConstruct and
   * args are expanded to their actual values.
   * <p>
   * Next, the constructor is invoked, if possible.
   * If this.compiled == false, this step is skipped.
   * The type of parameteres for the constructor
   * is produced by polling the class types of the args objects.  If any of these
   * are wrapper classes (Integer, Character, etc.), it will first try invoking
   * the constructor with the equivalent primitive type aguments.
   * (The grader will not tolerate a method with a mix of primitive parameters
   * and wrapper class parameters though--it needs to be all primitives or all
   * wrappers.)
   * <p>
   * Construction is done safely.  The constructor is invoked in a separate thread,
   * which is terminated if it fails to complete by TamarinGrader.TIMEOUT.  (This
   * prevents hangs from infinite loops or unexpected reads from stdin.)
   * If the constructor does not exist, or throws some unexpected exception, these
   * will be caught.  In all these cases, a brief "[ERROR: ...]" explanation will
   * appended to the earlier output.
   * <p>
   * Returns the constructed object, or null if the object could not be constructed
   * due to one of a number possible errors.
   *
   * @param desc     The description of this test; null will use the default prompt;
   *                  "" will silence all output from this test.
   * @param toConstruct  The name of the class to construct an instance of.
   * @param args     The arguments to pass to the tested constructor.  Additionally,
   *                 the type of the args are used to determine the parameter list for
   *                 the constructor.
   * @return         The constructed instance, or null.
   */
  public Object construct(String desc, String toConstruct, Object... args) {

    boolean silent = (desc != null && desc.equals("")) ? true : false;

    //print a description of this test
    if (!silent) {
      if (desc == null) {
        //default description
        this.print("Constructing " + toConstruct);
        this.printArgs(args);
      }else {
        this.print(desc);
      }
    }

    //should we even bother continuing?
    if (!this.compiled) {
      if (!silent) {
        System.out.println(": [ERROR: Not compiled]");
      }
      return null;
    }

    //now try finding and invoking the constructor
    try {
      //get paramater list
      Class[] params = this.getParameters(args);
      Class classToConstruct = Class.forName(toConstruct);
      Constructor constr = this.getConstructor(classToConstruct, params);
      Object instance = this.invokeMember(null, constr, args);

      //there was no expected result to display; but still need to end line
      if (!silent) {
        System.out.println(".");
      }
      return instance;

    }catch (NoSuchMethodException nsme) {  //from not finding it
      if (!silent) System.out.println(": [ERROR: No such constructor]");
    }catch (ClassNotFoundException cnfe) {  //from not finding it
      if (!silent) System.out.println(": [ERROR: No such class]");
    }catch (NoClassDefFoundError ncdfe) {  //from not finding it (usually wrong case)
      if (!silent) System.out.println(": [ERROR: No such class (wrong case/name?)]");
    }catch (TamarinGrader.InvocationException ie) {  //couldn't invoke
      if (!silent) {
        System.out.print(": [ERROR: " + ie.getMessage());
        if (ie.getCause() != null) {
          System.out.print(": " + ie.getCause());
        }
        System.out.println("]");
      }
    }catch (InvocationTargetException ite) {
      if (!silent) System.out.println(": [ERROR: Constructor threw " + ite.getCause() + "]");
    }
    return null;
  }

  /**
   * <code>== this.construct(null, this._class, args)</code>
   * That is, constructs an instance of the class being graded by this grader
   * with the default description and the given args.
   */
  public Object construct(Object... args) {
    return this.construct(null, this.className, args);
  }



  /**
   * Tests the given method (if compiled).
   * <p>
   * First displays the given description of the test.
   * If <code>desc.equals("")</code>, nothing is printed at all by this
   * test (even expected values or any error messages.
   * If <code>desc</code> is <code>null</code>, will instead
   * provide the default of "Invoking methodName(args) ",
   * where <i>methodName</i> and <i>args</i> are expanded to their actual
   * values.
   * <p>
   * Then prints the expected value in [braces].
   * <code>null</code> is frequently a valid expected result.
   * If no value is expected (either because it's a void method or because you
   * just want to run the method and not compare its returned value to expected)
   * give void.class for this.  In this void case, no [braces] or expected value is
   * printed.  (This use of void means the grader simply doesn't compare the returned
   * result, and so it can't enforce a void return type.
   * The assignment could actually be returning something when you expect nothing.
   * The reverse is not true: if you're expecting something and the assignment's
   * method is void, the test will fail.)
   * <p>
   * The expected value can also be a Class object representing some sort of
   * Exception class, which is taken to mean you expect the method to throw
   * an instance of that specific kind of exception.  That is, the result of the
   * method should be an exception of the same class (though not necessarily the
   * same contents) as <code>expected</code>. (So note that this is different
   * than passing an instance of an exception, in which case you expect the
   * method to return an object <code>.equals</code> to that exception.)
   * <p>
   * This single line of "desc [expected]" is then ended with a ": "
   * <p>
   * Next, the methodName method is invoked, if possible.
   * If <code>this.compiled == false</code>, this step is skipped.
   * The type of arguments for the method
   * is produced by polling the class types of the args objects.  If any of these
   * are wrapper classes (Integer, Character, etc.), it will first try invoking
   * the method with the equivalent primitive type aguments.  (The grader will not
   * tolerate a method with a mix of primitive parameters and wrapper class
   * parameters though--it needs to be all primitives or all wrappers.)
   * <p>
   * If (inst instanceof Class), then it is assumed that methodName is a static
   * method of this class.  If it is null, this is considered an error.
   * Otherwise, methodName must be an instance method
   * found in the class of which inst is an instance.
   * In the case of an instance method,
   * the method will then be invoked on the inst object.
   * <p>
   * Finally, if expected is not void, the returned value will be appended to the
   * "desc [expected]: " line.  (If this is a double or float value, this may
   * be followed by a '~' on successful test depending on {@link #markEpsilon}.)
   * <p>
   * All of this testing is done safely.  The method is invoked in a separate thread,
   * which is terminated if it fails to complete by {@link #timeout}.  (This
   * prevents hangs from infinite loops or unexpected reads from stdin.)
   * If the method does not exist, or throws some unexpected exception, these will
   * be caught.  In all these cases, a brief "[ERROR: ...]" explanation will be
   * printed in place of the returned value (even if expected is void).
   * <p>
   * Returns true if the returned result <code>.equals</code> expected
   * (or if expected was void and the method did not timeout or result
   * in some exception); false otherwise.  If {@link #epsilon} != 0 and
   * the method returns a float or double, the returned and expected
   * results will be considered equal if the absolute value of their
   * difference is less than the absolute value of epsilon.
   *
   *
   * @param desc     The description of this test; null will use the default prompt;
   *                  "" will silence all output from this test.
   * @param expected  The object that should be .equals to the returned result of the
   *                  method.  If void.class, then no results are expected/tested.
   *                  If a kind of exception, that kind of exception is expected.
   * @param inst     The instance to invoke the tested method on.  If inst is a
   *                 Class object, then methodName is assumed to be a static method.
   * @param methodName   The name of the method to invoke/test.
   * @param args     The arguments to pass to the tested method.  Additionally, the
   *                 type of the args are used to determine the parameter list for
   *                 the methodName method.
   */
  public boolean testMethod(String desc, Object expected, Object inst,
                            String methodName, Object... args) {

    boolean success = false;
    boolean silent = (desc != null && desc.equals("")) ? true : false;

    //get paramater list
    Class[] params = this.getParameters(args);
    //print a description of this test
    if (!silent) {
      this.printTestDescription(desc, expected, methodName, args);
    }

    //should we even bother continuing?
    if (!this.compiled) {
      if (!silent) {
        System.out.println("[ERROR: Not compiled]");
      }
      return false;
    }else if (inst == null) {
      if (!silent) {
        System.out.println("[ERROR: Method could not be invoked on null object)]");
      }
      return false;
    }

    //now try finding and invoking the method
    try {
      Class targetClass = (inst instanceof Class) ? (Class) inst : inst.getClass();
      Method method = this.getMethod(targetClass, methodName, params);
      Object result = this.invokeMember(inst, method, args);

      success = true;  //completed successfully

      //print result (even if nothing expected)
      if (!silent) {
        System.out.print((method.getReturnType().equals(void.class)) ? "[void]" : result);
      }

      //now, see if success should actually be based on expected vs. result
      if ((expected == null) ||
          (expected != null && !expected.equals(void.class))) {
        //there was an expected result, so determine success

        if (this.epsilon != 0.0 &&
            ((expected instanceof Double && result instanceof Double) ||
            (expected instanceof Float || result instanceof Float))) {
          //need to compare floating point values using epsilon
          double difference;
          if (expected instanceof Double) {
            //casting followed by auto-unboxing
            difference = Math.abs((Double) expected - (Double) result);
          }else {
            //same, but for floats
            difference = Math.abs((Float) expected - (Float) result);
          }
          success = (difference <= Math.abs(this.epsilon));
          if (success && !silent && this.markEpsilon != null &&
              !result.equals(expected)) {
            //indicate that the use of epsilon made a difference in this test
            System.out.print(this.markEpsilon);
          }

        }else {
          //comare normally using .equals
          success = (result == null) ? result == expected : result.equals(expected);
        }
      }

      //End line
      if (!silent) System.out.println();

    }catch (NoSuchMethodException nsme) {  //from not finding it
      if (!silent) System.out.println("[ERROR: No such method]");
    }catch (NoClassDefFoundError ncdfe) {
      //from method signature refering to unavailable class
      if (!silent) System.out.println("[ERROR: Method needs an unavailable class]");
    }catch (TamarinGrader.InvocationException ie) {  //couldn't invoke
      if (!silent) {
        System.out.print("[ERROR: " + ie.getMessage());
        if (ie.getCause() != null) {
          System.out.print(": "+ ie.getCause());
//XXX: ie.getCause().printStackTrace();
        }
        System.out.println("]");
      }
    }catch (InvocationTargetException ite) {
      if (expected != null && expected instanceof Class &&
          ite.getCause().getClass().equals(expected)) {
        //method is supposed to throw this kind of exception
        if (!silent) System.out.println(ite.getCause()); //print exception caught
        success = true;
      }else if (ite.getCause() instanceof ExitVMException) {
        //method tried to kill the VM, which may or may not be an error
        if (!silent) {
          System.out.println("[" +
                             ((this.exitVMIsError) ? "ERROR" : "WARNING") +
                             ": Method ended by System.exit (or similar)]");
        }
        success = !this.exitVMIsError;
      }else {
        //just a normal error from method
        if (!silent) System.out.println("[ERROR: Method threw " + ite.getCause() + "]");
//XXX: ite.getCause().printStackTrace();
      }
    }
    return success;
  }


//===== PROTECTED HELPER METHODS =====

  /**
   * Tries to find the given constructor (with the given parameter list)
   * in the targetClass.
   * <p>
   * If any of the parameters are wrapper classes, they will first all be
   * translated to primitives, and the constructor sought that way.  If this
   * fails, then the constructor will be sought using the original wrapper classes.
   * In both cases, it will search for a declared constructor first, then any
   * public constructor.
   * <p>
   * If the method requested cannot be found either way,
   * a NoSuchMethodException will be thrown.
   *
   * @return   The requested method, named methodName, with params parameter list,
   *           found in targetClass.
   * @throws  NoSuchMethodException  if such a method cannot be found in targetClass
   */
  protected Constructor getConstructor(Class<?> targetClass, Class[] params)
                                  throws NoSuchMethodException {

    Class[] primitiveParams = this.getPrimitiveParameters(params);
    //now, try to find and return the constructor

    try {
      //try with declared with primitives first
      return targetClass.getDeclaredConstructor(primitiveParams);
    }catch (NoSuchMethodException nsme1) {
      //nope, didn't find it that way...
      try {
        return targetClass.getConstructor(primitiveParams);
      }catch (NoSuchMethodException nsme2) {
        try {
          return targetClass.getDeclaredConstructor(params);
        }catch (NoSuchMethodException nsme3) {
          //try public with originals (and if this fails too, let NSME go back to caller)
          return targetClass.getConstructor(params);
        }
      }
    }
  }

  /**
   * Tries to find the given method (with the given parameter list)
   * in the targetClass.
   * <p>
   * If any of the parameters are wrapper classes, they will first all be
   * translated to primitives, and the method sought that way.  If this
   * fails, then the method will be sought using the original wrapper classes.
   * <p>
   * Whenever a method is sought, it will first be checked as a declared method.
   * (That is, it must actually be declared/written in the class itself; this
   * does not include inherited methods.)  If this fails, then all public methods
   * will be checked, which can include inherited methods.
   * <p>
   * Note that this means inherited protected and package-private methods
   * cannot be found by this method.  (This is currently due to limitations
   * of Class's getMethod and getDeclaredMethod.)
   * <p>
   * If, after all these attempts, the method requested can still not be found,
   * a NoSuchMethodException will be thrown.
   *
   * @return   The requested method, named methodName, with params parameter list,
   *           found in targetClass.
   * @throws  NoSuchMethodException  if such a method cannot be found in targetClass
   */
  protected Method getMethod(Class targetClass, String methodName, Class[] params)
                             throws NoSuchMethodException {

    Class[] primitiveParams = this.getPrimitiveParameters(params);
    //now, try to find and return the method
    try {
      return this.getSpecificMethod(targetClass, methodName, primitiveParams);
    }catch (NoSuchMethodException nsme) {
      //well, didn't find it with the primitives; try again with wrappers
      return this.getSpecificMethod(targetClass, methodName, params);
    }
  }

  /**
   * Tries finding the given method with the given parameters in the given
   * targetClass.  Unlike getMethod, does not attempt to replace wrapper
   * class with primitives in the parameter list.  Will try declared methods
   * first, and, if that fails, public methods (which include inherited).
   */
  protected Method getSpecificMethod(Class<?> targetClass, String methodName, Class[] params)
                            throws NoSuchMethodException {
    if (methodName == null) {
      //short-circuit the NPE that will result below
      throw new NoSuchMethodException("Method name == null");
    }
    try {
      //try declared methods first
      return targetClass.getDeclaredMethod(methodName, params);
    }catch (NoSuchMethodException nsme) {
      //nope, didn't find it that way...
      //try public (and if this fails too, let NSME go back to caller)
      return targetClass.getMethod(methodName, params);
    }
  }

  /**
   * Returns an array of the types (each an instance of Class) corresponding
   * to the type of each of the given args.
   * <p>
   * If args is null, null is returned.
   * If any of the arguments in args == null, then the corresponding
   * paramter will also == null.
   */
  protected Class[] getParameters(Object[] args) {
    Class[] params = null;
    if (args != null) {
      params = new Class[args.length];
      for (int i = 0; i < args.length; i++) {
        //get the class of this arg
        if (args[i] != null) {
          params[i] = args[i].getClass();
        }
      }
    }
    return params;
  }

  /**
   * Translates any wrapper class Classes listed in params into the matching
   * primitive data type "class" (such as int.class, boolean.class, etc.)
   * Returns a copy of params with the changes made.
   * If params is null, so will the returned array be.
   */
  protected Class[] getPrimitiveParameters(Class[] params) {
    Class[] primitiveParams;
    if (params == null) {
      primitiveParams = null;
    }else {
      primitiveParams = new Class[params.length];
      //define a wrapper-to-primitive mapping
      Class[][] map = {{Byte.class, byte.class}, {Short.class, short.class},
                       {Integer.class, int.class}, {Long.class, long.class},
                       {Float.class, float.class}, {Double.class, double.class},
                       {Character.class, char.class}, {Boolean.class, boolean.class}};
      //loop over params, copying and converting any wrappers
      for (int i = 0; i < params.length; i++) {
        primitiveParams[i] = params[i];
        for (int m = 0; m < map.length; m++) {
          if (params[i] != null && params[i].equals(map[m][0])) {
            primitiveParams[i] = map[m][1];  //overwrite with primitive
          }
        }
      }
    }
    return primitiveParams;
  }


  /**
   * Prints the given args as a comma-separated list in parantheses.
   * If args as a whole is null, nothing is printed in the ()s.
   * If any specific arg is null, it is printed as 'null'.
   * If any arg is an array, its contents are expanded in a []s.
   * Does <i>not</i> terminate the output with a newline.
   */
  protected void printArgs(Object[] args) {
      System.out.print("(");
      if (args != null) {
        for (int i = 0; i < args.length; i++) {
          //print out any arrays
          if (args[i] != null && args[i].getClass().isArray()) {
            System.out.print(java.util.Arrays.toString((Object[]) args[i]));
          }else {
            System.out.print(args[i]);
          }
          if (i < args.length - 1) {
            System.out.print(", ");
          }
        }
      }
      System.out.print(")");
  }

 /**
   * If desc is not null, simply prints that.  Otherwise, prints the
   * default message of "Invoking methodName(args)", where methodName
   * and the details of args are given.
   *
   * If expected is not void.class, will then print the expected value
   * in [brackets].
   *
   * Ends the line with a ": ", but does not terminate it with a newline.
   */
  protected void printTestDescription(String desc, Object expected,
                                      String methodName, Object[] args) {
    //print description
    if (desc == null) {
      //provide default description
      System.out.print(this.prepend + "Invoking " + methodName);
      this.printArgs(args);
    }else {
      //print the passed description instead
      System.out.print(this.prepend + desc);
    }

    //print expected value (if expected not void)
    if (expected == null || !expected.equals(void.class)) {
      System.out.print(" [" + expected + "]");
    }

    //done with summary of test
    System.out.print(": ");
  }

  /**
   * Safely invokes the specified method or constructor.
   * If <code>member</code> is a method, will invoke it on the given inst
   * with the given args.  If <code>member</code> is a constructor,
   * will invoke it with the given args.
   * <p>
   * Collects all the things that could go wrong with normal grading (ie,
   * problems caused by the underlying class not meeting the expectations of
   * the grader) and bundles them into a single TamarinGrader.InvocationException.
   * In this case, the method could not even be invoked (or else was invoked
   * but hung for longer than this.{@link #timeout} and had to be
   * terminated).
   * <p>
   * Does let InvocationTargetException through though.  This exception
   * mean the method was successfully invoked, but itself threw an exception
   * (which is then contained in the ITE).
   * Throwing an exception could be proper/intended behavior of the method,
   * so the grader will need to see the ITE to decide what to do with the
   * contained exception.
   * <p>
   * Sets the test streams so that all input/output will come/go from this
   * TamarinGrader, rather than System.
   * <p>
   * If this.{@link #reloadClass} is set, will reload the
   * given class using a custom ClassLoader before invoking the member.
   * <p>
   * Returns whatever the invoked method returned, or the constructed
   * object for constructors.
   */
  @SuppressWarnings("deprecation") //for stop method
  protected Object invokeMember(Object inst, Member member, Object[] args)
                                throws InvocationTargetException,
                                       InvocationException {
    try {

      if (this.redirectStreams) this.setTestStreams();  //reset in finally(s), below

      //some basic error checking
      Method method = null;
      Constructor constructor = null;
      if (member instanceof Method) {
        method = (Method) member;
        if (!Modifier.isStatic(method.getModifiers()) && inst instanceof Class) {
          //grader meant to pull up a static method, but didn't
          //which means we'll crash if we try to invoke it as if it were static
          throw new InvocationException("Method should be static, but it is not.");
        }
      }else if (member instanceof Constructor) {
        constructor = (Constructor) member;
      }else {
        //neither method or constructor
        throw new InvocationException("Trying to invoke a member that is " +
                                      "neither a method nor constructor.");
      }

      if (this.reloadClass != null) {
        //reload that class in order to refresh it
        TamarinClassLoader loader = new TamarinClassLoader();
        Class<?> refreshedClass = loader.loadClass(this.reloadClass.getName());
        //make sure we then invoke the method in that refreshed class
        // (not the originally loaded one, which probably also still exists the VM)
        if (member instanceof Method) {
          member = refreshedClass.getMethod(method.getName(),
                                            method.getParameterTypes());
        }else {
          member = refreshedClass.getConstructor(constructor.getParameterTypes());
        }
      }

      MemberInvocation t = new MemberInvocation(inst, member, args);
      //set up security before invoking
      SecurityManager originalSM = System.getSecurityManager();
      if (!disableSecurity) System.setSecurityManager(new TamarinSecurityManager());

      t.start();
      t.join(this.timeout);
      if (t.isAlive()) {
        //didn't rejoin us here in the main thread, so need to kill it
        t.interrupt();  //first, ask politely (might just be sleeping)
        t.join(this.cleanupTimeout); //give it a moment to finish
        if (t.isAlive()) {
          //Okay, that's it! We asked nicely...
          //NOTE: Yes, stop() is deprecated, but it's the only way to kill a
          //      thread stuck in an infinite loop
          t.stop();
          //set, rather than throw, so we can reset the security manager below
          t.exception = new InvocationException("Method forcibly terminated (infinite loop?)");
        }
      }

      if (!disableSecurity) {
        //reenable
        System.setSecurityManager(originalSM);
      }

      if (t.exception != null) {
        //invoked method ended, but threw an exception somewhere
        if (t.exception instanceof InvocationException) {
          throw (InvocationException) t.exception;
        }else if (t.exception instanceof IllegalAccessException) {
          throw new InvocationException("Could not access method (private?)", t.exception);
        }else if (t.exception instanceof IllegalArgumentException) {
          //instance is not of the class it should be, or
          //args didn't match parameters after all, etc. (shouldn't happen)
          throw new InvocationException("Could not invoke method " +
                       "(Maybe: wrong arguments? Instance is from different classloader?)",
                       t.exception);
        }else if (t.exception instanceof ExceptionInInitializerError) {
          throw new InvocationException("Could not initialize the class " +
            "to which this method belongs", t.exception);
        }else if (t.exception instanceof InstantiationException){
          throw new InvocationException("Could not create an instance " +
            "of abstract class", t.exception);
        }else if (t.exception instanceof InvocationTargetException){
          throw (InvocationTargetException) t.exception;
        }else {
          throw new InvocationException("Very unexpected error", t.exception);
        }
      }else {
        //method finished okay
        return t.result;
      }

    }catch (InterruptedException ie) {
       throw new InvocationException("Strange: the grader thread was itself interrupted " +
                                     "while waiting for an invoked method to finish.");
    }catch (ClassNotFoundException cnfe) {
      throw new InvocationException("Could not reload class", cnfe);
    }catch (NoSuchMethodException nsme) {
      throw new InvocationException("Could not find same method " +
                                    "in reloaded class", nsme);
    }catch (SecurityException se) {
      throw new InvocationException("Could not change security manager", se);
    }finally {
      if (this.redirectStreams) this.resetStreams();
    }
  }


  /**
   * Changes System.in, System.out, and System.err to point to the Strings
   * in this TamarinGrader's in, out, and err instance variables.
   */
  protected void setTestStreams() {
    //save current System settings
    this._in = System.in;
    this._out = System.out;
    this._err = System.err;

    //construct streams
    this.inBuffer = new StringInputStream(this.in, this.echoInput);
    this.outBuffer = new LimitedByteArrayOutputStream(this.maxOutBytes);
    this.errBuffer = new LimitedByteArrayOutputStream(this.maxErrBytes);

    //override System
    System.setIn(this.inBuffer);
    System.setOut(new PrintStream(this.outBuffer));
    System.setErr(new PrintStream((this.redirectErrToOut) ?
                                   this.outBuffer : this.errBuffer));
  }

  /**
   * Resets the standard System streams, and dumps any output from the
   * test streams into this TamarinGrader's out and err instance variables.
   * Also dumps any input remaining in the input stream to this.in.
   */
  protected void resetStreams() {
    //make sure everything made it into the byte arrays
    System.out.flush();
    System.err.flush();

    //save output (using ByteArrayOutputStream's override of toString)
    this.out = this.outBuffer.toString();
    this.err = this.errBuffer.toString();

    //save any left over input
    this.in = this.inBuffer.toString();

    //not closing anything because javadocs say all the relevant close()
    //methods actually do nothing, yet would still force us to catch IOExceptions

    //resest the temporary test streams with the saved standard streams
    System.setIn(this._in);
    System.setOut(this._out);
    System.setErr(this._err);
  }



// ===== NESTED HELPER CLASSES =====

  /**
   * Represents an attempt by the graded submission to exit the VM, usually
   * by calling System.exit().
   */
  public class ExitVMException extends SecurityException {
     public ExitVMException() { super();}
     public ExitVMException(String msg) { super(msg);}
     public ExitVMException(String msg, Throwable cause) { super(msg, cause);}
     public ExitVMException(Throwable cause) { super(cause);}
  }

  /**
   * Represents a problem trying to invoke a method that most likely
   * represents a problem with the underlying method, rather than with the
   * grader.  Includes a handy, printable message, but also the cause (if
   * any).
   */
  public class InvocationException extends Exception {
     public InvocationException() { super();}
     public InvocationException(String msg) { super(msg);}
     public InvocationException(String msg, Throwable cause) { super(msg, cause);}
     public InvocationException(Throwable cause) { super(cause);}
  }

  /**
   * Used to invoke either a method or constructor in a separate thread.
   * This way, that thread can be killed if the method or constructor
   * enters an infinite loop, etc.
   * <p>
   * The result of running the method/constructor will be stored into the
   * public result or exception.
   */
  public class MemberInvocation extends Thread {

    public Object result = null;
    public Throwable exception = null;
    protected Method method = null;
    protected Object instance = null;
    protected Object[] args = null;
    protected Constructor constructor = null;

    /**
     * Invoke the given method on the given instance (which can be null
     * for static methods) and the given arguments to the methd.
     */
    public MemberInvocation(Object instance, Member member, Object[] args) {
      this.instance = instance;
      if (member instanceof Method) {
        this.method = (Method) member;
      }else if (member instanceof Constructor) {
        this.constructor = (Constructor) member;
      }else {
        throw new ClassCastException("Specified member is not a method " +
                                      "or constructor.");
      }
      this.args = args;
    }

    /**
     * Safely invoke the method and save the results.
     */
    public void run() {
      try {
        if (this.method != null) {
          result = this.method.invoke(instance, args);
        }else {
          result = this.constructor.newInstance(args);
        }
      }catch (Throwable e) {
        //need to save it so we can "catch" it and report it in the main thread
        exception = e;
      }
    }
  }

  /**
   * This allows input read from this.in to still echo to this.out, in
   * order to preserve formatting.
   * <p>
   * Also, echoed input is printed with \n, to mirror the echoed entered key.
   * <p>
   * Echoing goes to System.out, which will normally point to this.out when
   * this class is in use.
   */
  protected class StringInputStream extends InputStream {
    /** The complete string to read from */
    protected String str;
    /** The current position in str (where 0 <= pos < str.length) */
    protected int strPos;
    /** The next line to read (or finish reading) */
    protected byte[] nextLine;
    /** The current position in nextLine */
    protected int linePos;
    /** Whether to echo the output read */
    protected boolean echo;

    /**
     * Constructs a stream that will read from <code>s</code>, echoing each read
     * to <code>System.out</code> depending on <code>echo</code>.
     */
    public StringInputStream(String s, boolean echo) {
     this.str = (s != null) ? s : "";
     this.strPos = 0;
     this.echo = echo;
     this.loadNextLine();
    }

   /**
    * Load the nextLine array with the next line (if any),
    * updating all the positions as necessary.
    * Sets linePos to -1 if there is nothing left of the string
    * to load into nextLine and read.
    *
    * Returns whether there actually is a nextLine to read.
    */
   private boolean loadNextLine() {
     if (strPos == str.length()) {
       //no more to read
       linePos = -1;
       return false;
     }else {
       //figure out how much we'd like to return
       int nextNewline = str.indexOf('\n', strPos);
       String toRead;
       if (nextNewline == -1) {
         //no newline found, so go to end of string
         toRead = str.substring(strPos);
         strPos = str.length();
       }else {
         toRead = str.substring(strPos, nextNewline + 1);
         strPos = nextNewline + 1;
       }
       this.nextLine = toRead.getBytes();
       this.linePos = 0;
       return true;
     }
   }

    @Override
    public int available() {
      return (linePos == -1) ? 0 : linePos;
    }

    /**
     * Returns the full, original string this stream reads from.
     */
    public String getString() {
      return this.str;
    }

    /**
    * Will read up to the next \n or the end of the contained string,
    * or up to len bytes, whichever is smaller.  Echoes what was read.
    */
    @Override
    public int read(byte[] b, int off, int len) {
      if (linePos == -1) {
       //nothing left here to read
       return -1;
      }else {
       //read up to len, if we have that much
       int read = 0;
       for (; read < len && linePos < nextLine.length; read++, linePos++) {
         b[off + read] = nextLine[linePos];
       }

       if (this.echo) {
         //Note: Try to display, tho behavior undefined if bytes don't convert
         System.out.print(new String(b, off, read));
       }

       if (linePos == nextLine.length) {
         //done with this line, so get next one ready
         this.loadNextLine();
       }
       return read;
      }
    }

    @Override
    public int read() {
     byte[] b = new byte[1]; //only need to read one byte
     this.read(b, 0, 1);
     return b[0];
    }

    /**
     * Returns the remainder of the contained String that has not yet been read,
     * thus representing the remaining data for this stream.  Will be an empty
     * string if all the characters have been read.
     */
    public String toString() {
      //need to remember to grab what's been pre loaded into nextLine too
      return ((linePos > -1) ?
                 new String(nextLine, linePos, nextLine.length - linePos) :
                 "")
              + this.str.substring(strPos);
    }

  }//end StringInputStream


  /**
   * This OutputStream works much like java.io.ByteArrayOutputStream, but
   * it does not grow beyond the limit set when it was constructed.
   * If more than that is written to the steam, it will throw an
   * IOException. This
   * ensures that a graded assignment locked in an infinite loop that includes
   * printing doesn't swamp system memory.  (For example, in one real world
   * case, 2 seconds of looping generated over 15MB of text.)
   * <p>
   * Be aware that, because System.out and System.err are PrintStreams, they
   * never pass on the IOException; they just stop outputting.  To clarify
   * TamarinGrader output, this class will append a message to the end of
   * a full stream so it is clear why output was suddenly cut off.
   */
  public class LimitedByteArrayOutputStream extends OutputStream {

    /** Message appended to a full buffer/steam by toString() */
    public static final String warning = "MAX_OUTPUT";
    /** Where bytes sent to the stream are stored. */
    protected byte[] storage;
    /** Number of bytes sent so far */
    protected int count;

    /**
     * Limited to the given number of bytes.
     * If maxBytes is <= 0, it is treated as 0 (and so no bytes can be
     * sent to this steam).
     */
    public LimitedByteArrayOutputStream(int maxBytes) {
      if (maxBytes < 0) {
        maxBytes = 0;
      }
      this.storage = new byte[maxBytes];
      this.count = 0;
    }

    @Override
    public void write(int b) throws IOException {
      if (count == storage.length) {
        //oops, already full
        throw new IOException("Exceeded output steam capacity (" +
                              storage.length + " bytes)");
      }else {
        storage[count++] = (byte) b;
      }
    }

    /**
     * Returns the current contents of this stream as a String
     * according to the default charset.
     */
    @Override
    public String toString() {
      if (count == storage.length) {
        String message = "[" + warning + ": " + storage.length + "b]";
        return new String(storage, 0, count) + message;
      }else {
        return new String(storage, 0, count);
      }
    }

  }//end LimitedByteArrayOutputStream


  /**
   * This security manager extends the default security manager
   * (which java usually uses when running applets).  Therefore,
   * most permissions are already locked down.
   * <p>
   * However, some actions (such as System.exit()) are allowed by
   * the default manager when running appliations.  There is no way to
   * remove a permission using a policy file (you can only grant permissions)
   * and so it was required to restrict some permissions in code.
   * To consolidate all security management in one place, to do away with
   * an extra policy file (which can get lost, forgotten, or misplaced),
   * and to prevent strange conflicts between different possible security
   * managers, all of Tamarin security management is now done here instead.
   */
  protected class TamarinSecurityManager extends SecurityManager {

    /**
     * Allows some things required by TamarinGrader
     *(such as creating new class loaders),
     * locks other things down (such as calls to System.exit),
     * but otherwise just lets the default SecurityManager handle things.
     */
    public void checkPermission(java.security.Permission perm) {

      //for some reason, these are always needed by Java
      if (perm.getName().equals("getProperty.networkaddress.cache.ttl") ||
          perm.getName().equals("getProperty.networkaddress.cache.negative.ttl") ||
          perm.equals(new java.util.PropertyPermission("sun.net.inetaddr.ttl", "read"))){
        return;
      }

      //these permissions are applied to submission code
      if (perm.getName().startsWith("exitVM")) {
        //DENY: don't let submission exit and thus kill the grader as well
        //(Also, this special exception is caught elsewhere to determine if
        // exiting the VM is an error or just a warning.)
        throw new ExitVMException("System.exit() request refused");

      }else if (perm.equals(new RuntimePermission("setSecurityManager")) &&
        this.getClassContext()[3].equals(TamarinGrader.class)) {
        //getClassContext gets the runtime stack; 3 calls ago is the method
        //that called to set the security manager.

        //GRANT: Only accept requests from TamarinGrader to reset the SM
        //(Note: This sort of assumes there's only one TamarinGrader class
        //floating around...)
        return;

      }else if (perm.equals(new RuntimePermission("createClassLoader"))){
        //SecurityManager's getClassContext hides references to
        //java.lang.reflect.Method.invoke(), etc.  So going the long way...
        StackTraceElement[] stack = new Throwable().fillInStackTrace().getStackTrace();
        if (stack.length > 12 &&
             (stack[11].getClassName().equals("sun.reflect.NativeMethodAccessorImpl") ||
             stack[11].getClassName().equals("sun.reflect.NativeConstructorAccessorImpl") ||
             stack[12].getClassName().equals("sun.reflect.NativeMethodAccessorImpl") ||
             stack[12].getClassName().equals("sun.reflect.NativeConstructorAccessorImpl"))) {
          //Each single method or constructor can only be invoked through
          //reflection a number of times equals to
          //sun.reflect.ReflectionFactory.inflationThreshold (currently 15)
          //before the JVM reloads the class (to use byte code rather than
          //native code; interstingly, this does not seem to refresh static
          //fields).  (For more on this, see sun.reflect.*; it's not part
          //of the java source, so do a search, such as for openjdk-7).
          //Therefore, we have to allow this.  This currently assumes that if
          //this call came from NativeMethodAccessorImpl.invoke() (where the
          //choice is made whether or not to reload the class), we're probably
          //safe.  Note that if this implementation changes, so that the call
          //is not index 11 of the runtime stack, this test will fail.

          //Update: Recently started being one step further down at index 12.
          //Due to different java version?

          //GRANT: Allow JVM to reload a class on the 16th call to a method.
          return;
        }
        for (int i = stack.length - 1; i > 0; i--) {
          if (stack[i].getClassName().equals("java.util.Scanner")) {
            //This request for a classLoader comes directly from something
            //Scanner is doing
            //GRANT: Under Java 1.5, the Scanner needs this.  (Don't know why.)
            return;
          }
        }

      }else if (perm.equals(new RuntimePermission("accessClassInPackage.sun.reflect"))){
        StackTraceElement[] stack = new Throwable().fillInStackTrace().getStackTrace();
        if (stack.length > 11 &&
             (stack[11].getClassName().equals("sun.reflect.NativeMethodAccessorImpl") ||
             stack[11].getClassName().equals("sun.reflect.NativeConstructorAccessorImpl") ||
             stack[10].getClassName().equals("sun.reflect.NativeMethodAccessorImpl") ||
             stack[10].getClassName().equals("sun.reflect.NativeConstructorAccessorImpl"))) {
          //GRANT: Ability to look at sun.reflect classes, required for solution
          //above.
          //Update: And then changed to be one less: 10, rather than 12.
          return;
        }
      }else if (perm.equals(new ReflectPermission("suppressAccessChecks"))){
        StackTraceElement[] stack = new Throwable().fillInStackTrace().getStackTrace();
        if (stack.length > 10) {
          if (stack[10].getClassName().equals("sun.reflect.NativeMethodAccessorImpl")||
              stack[10].getClassName().equals("sun.reflect.NativeConstructorAccessorImpl")) {
            //GRANT: Also required by sun.reflect.
            return;
          }
        }
        for (int i = stack.length - 1; i > 0; i--) {
          if (stack[i].getClassName().equals("java.util.Scanner")) {
            //Again, this comes directly from something Scanner is doing
            //GRANT: Under Java 1.5, the Scanner needs this.  (Don't know why.)
            return;
          }
        }

      }else if (perm.equals(new java.util.PropertyPermission("user.dir", "read")) ||
                (perm instanceof java.io.FilePermission &&
                (new java.io.FilePermission("-", "read")).implies(perm))) {
        //GRANT: read access to current directory (and subdirectories)
        //(Also allows reading from System.in with old
        // BufferedReader(InputStreamReader)) keyboard reading technique)
        return;

      }else if (perm.equals(new java.util.PropertyPermission("user.dir", "write")) ||
                (perm instanceof java.io.FilePermission &&
                (new java.io.FilePermission("*", "write")).implies(perm))) {
        //GRANT: write access to current directory (only)
        return;

      }else if (perm.equals(new java.util.PropertyPermission("file.encoding", "read"))) {
        //GRANT: Under Java 1.5, needed to read from a file
        return;

      }else {
        //other checks requiring loops first:
        StackTraceElement[] stack = new Throwable().fillInStackTrace().getStackTrace();
        for (int i = 0; i < stack.length - 1; i++) {
          if (stack[i].getClassName().equals("java.io.FileInputStream") &&
              stack[i+1].getClassName().equals("java.util.Scanner")) {
            //GRANT: When you use a Scanner to read from a file, the resulting
            //java.io.FileInputStream.getChannel() call makes all kinds of
            //requests:
            // * java.lang.RuntimePermission loadLibrary.net
            // * java.io.FilePermission ?\jre6\bin\net.dll read
            // * java.util.PropertyPermission java.net.preferIPv4Stack read
            // * java.lang.RuntimePermission loadLibrary.nio
            // * java.io.FilePermission ?\jre6\bin\nio.dll read
            // (This should be safe provided the submitted code wasn't
            // allowed to use its own class loader.)
            if ((perm instanceof RuntimePermission && perm.getName().startsWith("loadLibrary.")) ||
                 perm.equals(new java.util.PropertyPermission("java.net.preferIPv4Stack", "read")) ||
                (perm instanceof java.io.FilePermission && perm.getActions().equals("read") &&
                  (perm.getName().endsWith("net.dll") || perm.getName().endsWith("nio.dll") ||
                   perm.getName().endsWith("libnet.so") || perm.getName().endsWith("libnio.so"))) ) {
              return;
            }
          }
        }
      }

      //block (or not) according to default SecurityManager
      java.security.AccessController.checkPermission(perm);
    }
  }


  /**
   * A ClassLoader capable of loading only classes in the current directory.
   * If the class to be loaded is in a package, the request is passed up
   * to the parent (normal) class loader.
   */
  protected class TamarinClassLoader extends ClassLoader {
    /*
     * Thanks be to:
     * http://tutorials.jenkov.com/java-reflection/dynamic-class-loading-reloading.html
     */
    public TamarinClassLoader() {
      super();
    }

    /**
     * Does not allow the parent class loader a chance to confirm that the class
     * is already loaded if it is in the current directory.
     * This is because, if we did, we wouldn't be able
     * talk to other non-public classes in the same/default package.  (See
     * http://osdir.com/ml/windows.devel.java.advanced/2004-05/msg00044.html
     * for more.)
     * Does pass all packaged names up to parent classloader though.
     */
    public Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
      Class loaded = this.findLoadedClass(name);
      if (loaded == null) {
        //not loaded yet
        if (name.contains(".")) {
          //in a package, so pass it along to parent
          loaded = super.loadClass(name, resolve);
        }else {
          loaded = this.findClass(name);
          if (resolve) {
            this.resolveClass(loaded);
          }
        }
      }
      return loaded;
    }


    /**
     * Actually find and loads a class from file.
     */
    public Class<?> findClass(String name) throws ClassNotFoundException {
      try {
        File fileName = new File(name + ".class");
        FileInputStream fileIn = new FileInputStream(fileName);
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();

        int data = fileIn.read();
        while(data != -1){
            buffer.write(data);
            data = fileIn.read();
        }
        fileIn.close();
        byte[] classData = buffer.toByteArray();

        return super.defineClass(name, classData, 0, classData.length);
      }catch (IOException ioe) {
        throw new ClassNotFoundException();
      }
    }
  }


  /**
   * A list of lines (Strings) taken from output.  Lines objects
   * are immutable, but they support a number of regular expression
   * filtering operations that return new Lines sets with the
   * filtered lines removed.
   * <p>
   * Lines objects cannot be built directly.
   * See {@link #getOutputLines()} instead.
   */
  public class Lines {
    private java.util.List<String> lines;

    // NOTE: Lines are only immutable if the passed array/List is not
    // changed by the caller.  Since the only caller can be a TamarinGrader,
    // this can be ensured above.
    private Lines(String[] lines) {
      this.lines = java.util.Arrays.asList(lines);
    }
    private Lines(java.util.List<String> lines) {
      this.lines = lines;
    }

    /**
     * Returns a new Lines that contains only those lines in this
     * object that match any one of the given regexes.  That is,
     * each line that does not match at least one of the given regexes
     * is removed.
     * <p>
     * Searches are case-sensitive depending on {@link #caseSensitive}
     */
    public Lines any(String... regexes) {
      java.util.List<String> found = new java.util.LinkedList<String>();
      for (String line : this.lines) {
        for (String regex : regexes) {
          Pattern toFind = (caseSensitive) ?  //from TamarinGrader above
                           Pattern.compile(regex) :
                           Pattern.compile(regex, Pattern.CASE_INSENSITIVE);
          if (toFind.matcher(line).find()) {
            found.add(line);
            break; //found a match for this line, so lets move on the next line
          }
        }
      }
      return new Lines(found);
    }


    /**
     * Returns a new Lines that contains only those lines in this
     * object that match all of the given regexes.  That is,
     * each line that does not contain a match for every one of the
     * given regexes is removed.
     * <p>
     * Searches are case-sensitive depending on {@link #caseSensitive}
     */
    public Lines all(String... regexes) {
      java.util.List<String> found = new java.util.LinkedList<String>();
      for (String line : this.lines) {
        boolean matched = true;
        for (String regex : regexes) {
          Pattern toFind = (caseSensitive) ?
                           Pattern.compile(regex) :
                           Pattern.compile(regex, Pattern.CASE_INSENSITIVE);
          if (!toFind.matcher(line).find()) {
            //didn't find this regex, so skip this line
            matched = false;
            break; //found a match for this line, so lets move on the next line
          }
        }
        if (matched) {
          //made it through all regexes without skipping one
          found.add(line);
        }
      }
      return new Lines(found);
    }

    /**
     * Returns a new Lines object that contains only those lines in this
     * object that are also in the given other Lines.  That is,
     * each line that that is not also in the given Lines
     * is removed.
     * <p>
     * Lines are compared as String, so differences such as
     * whitespace are important.  Comparison honors {@link #caseSensitive}.
     */
    public Lines not(Lines others) {
      java.util.List<String> found = new java.util.LinkedList<String>();
      for (String line : this.lines) {
        boolean inOthers = false;
        for (String other : others.lines) {
          boolean equal = (caseSensitive) ? line.equals(other) :
                                            line.equalsIgnoreCase(other);
          if (equal) {
            inOthers = true;
            break;
          }
        }
        if (!inOthers) {
          found.add(line);
        }
      }
      return new Lines(found);
    }

    /**
     * Returns a Lines containing those lines that do not contain
     * one or more of the given regexes.  That is, if a line contains
     * all of the given regexes, it is excluded; otherwise, it is among
     * the returned.
     * <p>
     * Thus
     * <pre>
     * Lines none = lines.notAll("Hello", "World");
     * </pre>
     * is equivalent to
     * <pre>
     * Lines none = lines.not(lines.all("Hello", "World"));
     * </pre>
     */
    public Lines notAll(String... regexes) {
      return this.not(this.all(regexes));
    }

    /**
     * Returns a Lines containing those lines that do not contain
     * a match to any of the given regexes.  Thus,
     * <pre>
     * Lines noHellos = lines.notAny("Hello");
     * </pre>
     * is equivalent to
     * <pre>
     * Lines noHellos = lines.not(lines.any("Hello"));
     * </pre>
     */
    public Lines notAny(String... regexes) {
      return this.not(this.any(regexes));
    }

    /**
     * Returns whether this Lines includes 1 or more lines.
     * A Lines object is usually used as a filter for output, so, if
     * any output lines emain, the sought content exists.
     */
     public boolean isTrue() {
       return this.lines.size() > 0;
     }
//rename: isNotEmpty/isEmpty?

    /**
     * Returns whether this Lines contains no lines.
     * A Lines object is usually used as a filter for output, so, if
     * no output lines remain, the sought content does not exist.
     */
     public boolean isFalse() {
       return this.lines.size() == 0;
     }

    /**
     * Returns the number of lines in this Lines object.
     */
    public int size() {
      return this.lines.size();
    }

    /**
     * Returns all the lines in this Lines object.
     */
    public String[] toArray() {
      return this.lines.toArray(new String[this.lines.size()]);
    }

    /**
     * Returns all the lines in this Lines as a string, with
     * linebreaks between them.
     */
    @Override
    public String toString() {
      StringBuilder output = new StringBuilder();
      for (String line : this.lines) {
        output.append(line);
      }
      return output.toString();
    }

  }
}


