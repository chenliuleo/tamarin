## TamarinGrader: Java ##

The following is an overview of how Tamarin interfaces with a Java-based grader and how to use the large libarary of functions provided by TamarinGrader.java to write your own graders for Java code.

### gradecore.py-to-grader Interface ###

When Tamarin starts the grade pipe to grade a .java submission, it hands the details off to gradecore.py.  (See [Tamarin](Tamarin.md) for more information.)

gradecore.py then copies all necessary files into /tamarin/gradezone/, compiles the submission, and invokes the grader.  For Java submissions, this means that it will look for the grader at graders/A##/A##Grader.class.  (This grader file name can be customized in tamarin.py, but only globally for all Java graders.)

When gradecore.py starts A##Grader.class, it passes the grader two command line arguments: the name of the source code file to be graded (such as JanedoeA02.java) and whether that file was successfully compiled into a .class file by the earlier compile step.  (This second argument is either a 1 for compiled or 0 for not compiled.)

Whatever A##Grader.class then prints to the standard output stream (System.out / STDOUT) will be taken by gradecore.py to be grader output.  This content will be saved to the grader output text file.

A##Grader.class must also "return" (actually, print) a single numerical grade on the standard error stream (System.err / STDERR).  This value must be parsable to a float (so it can be either decimal or integer, but currently not a letter.)  If the grader fails to return this value, or if it returns something (more) that cannot be parsed, it is assumed that the grader failed to complete normally.  If it is parsable, the returned grade value (such as 4.5) is then recorded in the name of the grader output file, as in: JanedoeA02-20120114-1043-4.5.txt.

As a Teacher, one of your tasks is to write this A##Grader.class program for each specific assignment.  Using TamarinGrader.java to do this will help you greatly.


### TamarinGrader.java ###

TamarinGrader.java contains over 2000 lines of code and a number of component classes.  All of this is in a single .java file that uses the default package so as to make it easier to copy from place to place.  This is useful, since graders often need to be authored and tested in different environments.

The methods and classes of TamarinGrader.java are extensively documented.  You can run javadoc to extract this information:
```
  javadoc -d docs TamarinGrader.java
```
This places the created HTML documentation pages in a docs/ subdirectory.  (NOTE: Once all the Tamarin code has been uploaded and TamarinGrader.java cleaned up a bit, the extracted documentation will be hosted online here somewhere too.)

See this javadoc documentation for full details.  The following provides an introductory overview.

#### Sample Grader ####

The following is a very simple grader that tests a "Hello, World" program:
```
public class A00Grader {

  public static void main(String[] args) {
    TamarinGrader grader = TamarinGrader.init(args);

    grader.result(true, "Uploaded a file", 0.5);
    grader.result(grader.compiled, "Compiled", 0.5);

    grader.runMain();
    grader.result(grader.hasOutput(), "Printed something", 1.0);

    if (grader.isInOutput("hello", "world")) {
      grader.println("Printed \"Hello, World\" (or close variant)");
    }

    grader.reportGrade();
  }
  
}
```

It would produce the following output for a working submission:

```
## Uploaded file                                            (0.5 points) [PASS]
## Compiled                                                 (0.5 points) [PASS]
## Invoking main([]): [void]
hello there.
## Printed something                                          (1 points) [PASS]
## Printed "Hello, World" (or close variant)
## 
## Tamarin grade: 2.0
```

For a submission that doesn't compile, it would produce this:

```
## Uploaded file                                            (0.5 points) [PASS]
## Compiled                                                 (0.5 points) [FAIL]
## Invoking main([]): [ERROR: Not compiled]
## Printed something                                          (1 points) [FAIL]
## 
## Tamarin grade: 0.5
```


#### Initialization ####

```
public static TamarinGrader init(java.lang.String[] args)
```

This method is a factory method that builds a new TamarinGrader object for a given current submission.  This method checks that appropriate command line arguments were given and, if so, returns a new TamarinGrader instance.  If anything is wrong, it will report it appropriately to stderr and then call System.exit().

Example:
```
  TamarinGrader grader = TamarinGrader.init(args);
```

The returned TamarinGrader object contains a number of [variables](#TamarinGrader_Variables.md) and is the basis for all other TamarinGrader methods.  All examples below will assume the same "grader" variable name as shown in the example here.


#### TamarinGrader Variables ####

A TamarinGrader object contains many directly-accessible variables.  In the descriptions below, default values are given in (parentheses) where appropriate.

```
String filename
boolean compiled
File file
String className
Class _class
```
These variables all refer to the submitted file that is to be graded.  The value of the first two variables are taken from the arguments to <tt>init</tt>: the name file to grade and whether it compiled.  From this, the grader computes a reference to the File itself, computes the expected classname from the filename, and (if compiled), loads that Class.

Other than <tt>compiled</tt>, these variables rarely need to be used.

```
double grade (0.0)
```
The grade for this submission.  This variable should generally not be modified directly, but only affected through the <tt>result</tt> method (described below).

```
String in ("")
String out ("")
String err ("")
boolean echoInput (true)
boolean redirectErrToOut (true)
int maxOutBytes (10000)
int maxErrBytes  (1000)
```

Whenever a method or constructor is invoked by the grader, the in, out, and err streams in the System class are redirected in order to provide input to the submitted file and/or capture the submitted file's output.

Assign a String to <tt>in</tt> to provide input.

After invoking the method, <tt>out</tt> and <tt>err</tt> will contain any output as Strings.  A number of methods are provided for conveniently examining the contents of <tt>out</tt>, so direct access to these variable are rarely needed.

By default, the output of a program in <tt>out</tt> models what one sees on the command line: any typed input is visible and anything printed to <tt>err</tt> shows up mixed in with stuff to <tt>out</tt>.

It is possible for methods to get stuck in an infinite loop and produce a great quantity of output very quickly.  So there are limits on how much output is actually saved.

```
boolean caseSensitive (true)
```
Whenever a grader method is invoked that does pattern matching, this variable is checked.

```
double epsilon (1e-9)
String markEpsilon (" ~");
```
The amount of error to allow when comparing floats or doubles for equality.  This is often important when comparing expected and actual values in grading.  If two floating point values were not == but found to be equal after accounting for the epsilon value, <tt>markEpsilon</tt> is appended to the output for the test (in cases when there is output).

```
String[] errorMesg
```
A number of words that commonly appear in error messags but not in prompts or request for input.  This is just a convenience list for searching output for likely error messages printed by the submitted program.

```
int timeout (20000)
int cleanupTimeout (200)
```
For security, the grader always invokes methods or constructors of the submitted class in a separate thread.  By default, this thread is given only 20,000 milliseconds (0.2 seconds) to complete (<tt>timeout</tt>).  At that time, the thread is politely asked to terminate.  If it does not, it is forcibly stopped after the <tt>cleanupTimeout</tt> delay.  This ends infinite loops, hangs due to the inappropriate use of GUI components, etc.

The <tt>timeout</tt> value may occasonally need to be adjusted on a slower or busy machine or when testing methods that often take a long time (such as searches, sorts, etc).



#### Printing Messages ####
```
void print(Object string)
void println()
void println(Object string)
```
These methods act as the familiar System.out methods, except that they prepend a special String ("## " by default) to make Tamarin output stand out from submitted program output.

When using <tt>print</tt>, the printed line begins with "## "; that line should then be extended/terminated using the normal System.out methods to prevent additional "## "s in the same line.

```
void printOutput()
```
Prints whatever output is current in stored in <tt>grader.out</tt>. This is normally equal to whatever was printed by the last method of the submitted program that was invoked on the grader.


#### Setting Input ####

As mentioned, input and output streams are redirected whenever the grader invokes one of the submitted program's methods.  Set <tt>grader.in</tt> to whatever input you want the submitted program to read from System.in.

For example, suppose you are testing a program that reads in numbers from the keyboard until the user enters a empty line.  You could set grader.in as follows to have the tested program read in 5, 7, and 8.
```
  grader.in = "5\n7\n\8\n\n";
```
If the tested method does not read in all the input, the unread input will remain in <tt>grader.in</tt> after the method completes.  If the tested method attempts to read more input than what is provided, it usually results in the tested method throwing an exception.  For example, if the tested method is using a <tt>java.util.Scanner</tt> to read from System.in, it will produce a <tt>NoSuchElementException</tt> when it runs out of input.


#### Running the Submitted Program ####

```
boolean runMain(String... args)
```

This method will reload the submitted class and then invoke its main method, passing any arguments given as command line arguments.  Streams are redirected as normal and the method is terminated if it runs for too long.

Reloading the submitted class will reset any static/class variables in that class.  This simulates a fresh start of the JVM, which reflects normal use of the submitted program.  However, for technical reasons (see the JavaDocs for TamarinGrader.java's <tt>reloadClass</tt> variable for more detail), reloading a class means that the class and any invoked methods must be public for the TamarinGrader to find them after the reload.  Thus, <tt>runMain</tt> will fail if the submitted program's primary class or its main method is not public.


#### Examining Output ####

```
boolean hasOutput()
```

Returns true if there are any characters in <tt>grader.out</tt>.  This normally indicates whether a tested program printed at least one character from the last method that was invoked on it.


```
boolean isInOutput(String... regexes)
boolean areInOutput(String... regexes)
int countInOutput(String... regexes)
int findInOutput(String... regexes)
```

These convenience methods all examine the contents of <tt>grader.out</tt>.  They all take one or more regular expressions (regexes).  (See <tt>java.util.regex.Pattern</tt> for more on regular expressions under Java.)

<tt>isInOutput</tt> returns true if the output contains a match for ANY of the given regular expression.  <tt>areInOutput</tt> returns true only if ALL of the given regular expressions are found somewhere in the output.  If given only a single regular expression, these two methods are equivalent.

<tt>countInOutput</tt> will return the total number of matches found for all of the given regexes.  That is, if the output contains two matches for the first regex and and three matches for the second, <tt>countInOutput()</tt> will return 5.

<tt>findInOutput</tt> will return the number of the given regexes that resulted in at least one match.  For example, if given 3 regexes, and the first results in 3 matches, the second results in 0 matches, and the third gives 1 match, <tt>findInOutput</tt> will return 2.  This is because two of the three regexes resulted in at least one match.

Most grading of a program's output will rely on these four methods.  Because it is easier to spot when Tamarin removes points when it shouldn't (rather than times when it gives points for incorrect code), it is better to make your regexes too specific than too general.

Also, remember that regexes are usually tested for independently by these these method and so can overlap.  For example, suppose that, given the input you have provided, a submitted program should provide 14 and 4 as output.  You could use <tt>grader.findInOuptut("14", "4")</tt> to find if both of these values occur in the output somewhere.  However, because 14 includes 4, note that this test will always return 2 even if the output contains only 14.  A better test would be <tt>grader.findInOuptut("14", "\\b4")</tt>, where \b is a word boundary.  (Note that any backslash in a Java regex must be escaped with an extra backslash.)  <tt>grader.findInOuptut("14", "[^1]4")</tt> would also work, where the 4 in the second regex may not be preceded by a 1.

```
TamarinGrader.Lines getOutputLines()
```
Returns all the lines of output in a Lines object for easy filtering based on regex pattern matching.
Advanced.



#### Examing Source Code ####

```
boolean areInSource(boolean includeComments, boolean includeStrings, String... regexes)
int countInSource(boolean includeComments, boolean includeStrings, String... regexes)
int findInSource(boolean includeComments, boolean includeStrings, String... regexes)
boolean isInSource(boolean includeComments, boolean includeStrings, String... regexes)
```

#### Reporting Test Results and Grades ####

> double 	result(boolean passed, String mesg, double worth)
> > Reports whether a given test passed or failed, and adjusts this grader's grade total accordingly.

> double 	result(boolean passed, String success, String failure, double worth)
> > Reports whether a given test passed or failed, displaying one of two result messages depending.

> double 	result(double score, String mesg, double worth)
> > Reports whether a given test passed, failed, or partially passed.


> void 	reportGrade()
> > Prints this grader's grade to both stdout (with this.println) and to stderr.


#### Constructing Objects ####

boolean 	hasClass(String className)

> Returns whether the given class can be loaded by this grader.


Object construct(Object... args)

Object construct(String desc, String toConstruct, Object... args)


#### Invoking and Testing Methods ####

//invokeMethod(inst, methodName, args...)  --throws an exception, so some overhead
//runMethod(inst, methodName, args...)

Object invokeMethod(Object inst, String methodName, Object... args)
> Simply invokes the given method safely.
Object 	runMethod(Object inst, String methodName, Object... args)
> As invokeMethod(Object, String, Object...), but does not throw an exception.
boolean 	testMethod(Object expected, Object inst, String methodName, Object... args)
> == this.testMethod(null, expected, inst, methodName, args).
boolean 	testMethod(String desc, Object expected, Object inst, String methodName, Object... args)
> Tests the given method (if compiled).

#### Sample Grader ####