## Tamarin ##

This page explains how Tamarin stores its files and the process of submitting and grading a file.


### Directory Structure ###

Tamarin's structure is specified by a number of variables defined in tamarin.py.  The general structure is as follows:

```
[web server]
  |- CGI_ROOT
  |- HTML_ROOT

[elsewhere]
  |- TAMARIN_ROOT
     |-UPLOADED_ROOT
     |-SUBMITTED_ROOT
     |-GRADED_ROOT
     |-GRADERS_ROOT
     |-GRADEZONE_ROOT
     |-STATUS_ROOT
     |-STRIPPED_ROOT
```

Using the default values for these variables, this translates to the following folder structure and contained files:

```
[web server]
  |- cgi-bin/
     |- displaycore.py
     |- gradecore.py
     |- gradepipe.py
     |- masterview.py
     |- status.py
     |- submit.py
     |- tamarin.py
     |- upload.py
     |- view.py     
  |- htdocs/
     |- index.html
     |- tamarinhome.css
     |- tamarin.css

  |- tamarin
     |- graded/
        |- A01-20121221-0000-txt/
        |- A02-20380119-0314/
        |- ...
     |- graders/
        |- A01/
        |- A02/
        |- ...
     |- gradezone/
     |- status/
     |- stripped/
     |- submitted/
     |- uploaded/
```

The following description of Tamarin will assume this default folder structure.


### Submission and Grading Process ###

The basic process is as follows:

```
  UPLOAD -> SUBMIT -> COMPILE+GRADE -> HUMAN-VERIFY -> VIEW-FEEDBACK
```

#### Conceptual User Roles Involved ####

Different kinds of users are involved with different steps in this process.  These user roles include:

  1. the Administrator, who touches the Tamarin files and directories
  1. the Student, who submits an assignment to be graded
  1. the Teacher (or Teaching Assistant), who looks over the submitted work, confirms the tentative Tamarin grade, and provides additional feedback.

The Teacher and Administrator roles often overlap and may be filled by the same person.

The following also assumes that Tamarin has been correctly [installed](Installation.md) and [configured](Configuration.md) correctly.


#### Step 0: Create a new assignment (Admin) ####

Creating a new assignment under Tamarin requires two steps: defining the assignment and providing a grader for it.

An assignment is defined by creating a new subdirectory in tamarin/graded/.  This assignment subdirectory includes the name of the assignment (such as A02) and the date and time that it is due.  It may also include a point value and required submission file extension/type.

For example: tamarin/graded/A02-20380119-0314-4-java/

This A02 assignment is due 19 Jan 2038 (just before the 32-bit Unix timestamp rollover).  The assignment is worth 4 points and requires .java file submissions.

So the directory tells Tamarin everything it needs to know about a given assignment.  It is also where all submissions and grader output for that assignment will eventually be stored.  (More information: DefiningAssignments)

Then a grader for this specific assignment should be added to a sub-directory in tamarin/graders/.
For example, for the assignment A02, there should also be a tamarin/graders/A02/ directory that contains the necessary grader file.  This grader directory may also contain additional support files necessary for grading that assignment.  (More information: [Graders](Graders.md))


#### Step 1: The Tamarin home page (Student; index.html) ####

When the student is ready to submit an assignment, she visits the home page located at htdocs/index.html.  This page contains links to three options: submitting (upload.py), viewing previous submissions (view.py), and checking the current Tamaring status (status.py).

> [index.html screenshot](http://zach.tomaszewski.name/tamarin/screenshot/index.html.png)

We'll assume here that the student selects the "submit an assignment" link.


#### Step 2: Upload a submission (Student; upload.py) ####

The student will then be asked for the file she wants to upload.  This filename must include the student's Tamarin username and the assignment she is submitting for.  For example, if Jane Doe (username: janedoe) is submitting a Java file for A02, her file must be named JanedoeA02.java.  (The initial capital letter is requirement for Java class/file names; other file extensions, such as .c or .txt, may not have this requirement.)

The student must also enter her Tamarin password.

> [upload.py screenshot](http://zach.tomaszewski.name/tamarin/screenshot/upload.py.png)

Upon submitting, upload.py will perform a number of checks:

  * that the username, password, and assignment are all valid
  * that the submitted file has the correct extension for the given assignment
  * that the submitted file is actually plain text (if appropriate)
  * check if the deadline has passed for this assignment and whether the student may submit late

If one of these checks fails, Tamarin will provide a specific error message to the student.

> [upload.py screenshot: bad password error](http://zach.tomaszewski.name/tamarin/screenshot/upload.py-error.png)

If all checks pass, Tamarin will save a copy of the uploaded file into tamarin/uploaded/ and display the file to the student as a final check.  It will also warn the student if this submission is late, is a resubmission, etc.

> [upload.py screenshot: success with resubmit warning](http://zach.tomaszewski.name/tamarin/screenshot/upload.py-warning.png)

However, the assignment has not actually been submitted yet at this point.


#### Step 3: Confirm the submission (Student; submit.py) ####

If the student presses the Submit button, Tamarin moves the uploaded file from tamarin/uploaded/ into the tamarin/submitted/ directory.  It also appends a timestamp of the submission time to the filename.  When this is done, a success message is displayed to the student.  At this point, the student knows her work has been successfully submitted.

> [submit.py screenshot](http://zach.tomaszewski.name/tamarin/screenshot/submit.py.png)

Under the default settings, Tamarin will grade only one assignment at a time using something called the "grade pipe" (gradepipe.py).  This prevents the web server from getting overwhelmed during periods of heavy submission, such as near a deadline.  If the grade pipe is not currently running, submit.py will start it.  If it is already running, the grade pipe will continue to process everything in tamarin/submitted/, so submit.py does nothing.

The details/output of the current or latest gradepipe session can be found in tamarin/status/.  Students can use the "check Tamarin's grading status" link to status.py to see if Tamarin is currently grading and whether their submission is in the submitted/ queue.

> [status.py screenshot](http://zach.tomaszewski.name/tamarin/screenshot/status.py.png)


#### Step 4: Compile and grade the assignment (Tamarin; gradepipe.py, which uses gradecore.py) ####

As it runs, the Tamarin grade pipe will copy each new submission into tamarin/gradezone/.  For each submission,
it will also copy all the files from the tamarin/graders/ directory and from the appropriate tamarin/graders/A## directory into the gradezone.  Based on the submitted file's extension, it will run the associated compile command (if any).  It will then invoke the copied assignment-specific grader to do the grading.

Once compiling and grading are complete, Tamarin saves the output of the compiling and grading steps into a text file with a similar name to the submitted file.  For example, if the graded file is named JanedoeA02-20120108-1742.java and the grader returns a grade of 3.5 points, the grader output will be saved in JanedoeA02-20120108-1742-3.5.txt.

The two files are then moved into the appropriate tamarin/graded/A##-.../ directory.

This grading step can be customized by the Admin.  For example, the specific compiling and grading steps depend on the file type of the submitted file.  Some file types do not need to be compiled first.  Or you may choose not to automatically grade submissions, but simply assign grades manually during the next step.


#### Step 5: Verify the tentative grade (Teacher; masterview.py) ####

Due to the imperfections of automated grading, the grade provided by a Tamarin grader should always be viewed as a first-pass "tentative" grade.  A human Teacher should then verify that this grade is correct, as well as possibly provide feedback at a level beyond what is possible through automation.  (See [Philosophy#Automated\_Grading](Philosophy#Automated_Grading.md))

To do this, the Teacher uses the Master View (masterview.py) to examine the submissions for a particular student or assignment.

> [masterview.py screenshot: home page](http://zach.tomaszewski.name/tamarin/screenshot/masterview.py.png)

> [masterview.py screenshot: viewing all submissions for A00b](http://zach.tomaszewski.name/tamarin/screenshot/masterview.py-assignment-brief.png)

For each submitted file, the Teacher can add any comments, change the grader-assigned grade, and/or mark the grade as human verified.

> [masterview.py screenshot: verifying a submission](http://zach.tomaszewski.name/tamarin/screenshot/masterview.py-submission.png)

Marking the grade as human verified adds a -H to the grader output filename, as in JanedoeA02-20120108-1742-3.5-H.txt.  This has various effects, such as letting students know that their grade is correct and (usually) preventing the student from resubmitting again for that assignment.

For more information, see UsingMasterView.


#### Step 6: Viewing submissions and feedback (Student; view.py) ####

At any time, a student may view her previous submission by following the "view your submissions" link from index.html.  This takes the student to view.py, where she must enter her username and password.

> [view.py screenshot: login](http://zach.tomaszewski.name/tamarin/screenshot/view.py-login.png)

view.py and masterview.py both use the same displaycore.py code, and so many of the views are the same (or at least very similar).  For example, clicking on the button for a given submission will take the student to a submission view that shows her original code, the automated output from the compiling and grading steps, and any comments from the human Teacher.

> [view.py screenshot: all submissions](http://zach.tomaszewski.name/tamarin/screenshot/view.py.png)

> [view.py screenshot: a single graded submission](http://zach.tomaszewski.name/tamarin/screenshot/view.py-submission.png)

<br>
And that concludes this overview of Tamarin's significant parts.