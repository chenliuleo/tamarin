## Philosophy ##


#### Automated Grading ####

When I initially envisioned Tamarin, my hope was to completely automate grading. I have since come to realize that this is both impossible and undesirable.

Automation is impossible because no automated system is perfect.  Your graders are only as good as the pattern-matching regular expressions you used to write them.  There are always exceptions or fringe cases that slip through.  A human needs to double-check the correctness and validity of the output.  (In practice, Tamarin does quite well, with only about a 90% error rate.  Also, of those errors, about 90% are usually false negatives--taking off points when it shouldn't--and so are very easy to spot and correct.)

Automation is undesirable because grading is an essential part of teaching.  It's a chance to get to know your students and their abilities.  You can give feedback on an appropriate level for each student--deeper explanations as to why the code failed to pass Tamarin's tests or pointers on better design even when the code technically passes the tests.  It's your chance to encourage students, to provide deeper insight into the material based on what they've actually done, and to provide a human touch.

Think about it: if your feedback could really be reproduced by a few hundred lines of code, what value are you currently providing as a teacher?  Could you really be replaced by a recorded lecture, standardized multiple choice tests, and an automated grader? Or are you providing something more than that?

Yet Tamarin still has great value.  Its goal is not to automate or replace, but rather to aid and support the human grader.  It does this because it:

  * Automates the submission process. This saves you time and prevents problems like lost emails or missing attachments.
  * Provides a consistent first pass. Tamarin doesn't get tired or sloppy; it grades all submissions in the same way.
  * Gives students immediate feedback.  This allows them to correct their errors and resubmit before the deadline.
  * Frees up your time to give feedback on higher-level details. If written well, a grader will already provide feedback on what tests it ran and which ones failed.  You can then focus your comments on coding, design, and conceptual understanding.


#### Simple Design ####

Tamarin has a very simple design in terms of how it stores data:

  * Global configurations are in one place (tamarin.py).
  * Details of an assignment are all in the name of the folder created for that assignment.
  * Grading results for a submission are in an accompanying text file.

The use of folder structure (rather than, for example, a database) means it is easy to manually muck around with Tamarin files using existing tools when you have to.  Want to regrade an assignment?  Just drop it back into the submitted folder and run it through the grader again.  Want to extend an assignment deadline?  Just rename the folder that contains the submissions for that assignment.  Want to delete a submission?  Just delete the file.

This simplicity and transparency is one of Tamarin's strengths.

The tradeoff is that it may limit some of the additional features Tamarin will be able to handle (without a massive redesign).  If Tamarin isn't capable of doing what you need/want done, see [Links](Links.md) for some other systems that might work for you instead.