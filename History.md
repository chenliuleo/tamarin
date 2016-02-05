## History ##
##### (by Zach Tomaszewski) #####

I started as a Teaching Assistant in the Information and Computer Science department at the University of Hawai'i--Manoa in 2002.  (I've been there for a long time!) I love teaching, but I hate the mind-numbing tedium of manual grading: open the student's email, pull off the attached code, look over the code, compile it, run it, manually run through some set of tests (hopefully with the use of a redirected input file), write feedback in a reply email, hit send. Now repeat consistently... over and over... for every other student in the class.

It wasn't long before I thought: "I could train a monkey to do this! Hell, I'm a programmer--I could _write_ a monkey to do this..."

In 2003 to 2005, I hacked together some Perl scripts (collectively named Primate) to automate some of these steps for me.  They helped, but they were very ad hoc and brittle.  When I switched to TAing courses with fewer programming assignments, I ended up dropping Primate.

In 2007, I started TAing for _ICS111: Introduction to Computer Science_. As the students' first programming course, I soon realized that we needed lots of small, regular, easily-graded assignments, rather than just a few larger assignment. I also imagined a system where students could get immediate feedback on each submission--confirmation that it compiled and some grading feedback before the deadline.  (I also wanted to try my hand at Python.)

I designed and wrote Tamarin over the summer of 2008 while I was on break.

It was designed to grade small Java assignments on a [very low-end webserver](http://snarkdreams.com/personal/tinker/): an old 75Mhz i486 laptop with 32MB of RAM.  It was developed on a WindowsXP machine but deployed on a Debian Linux machine, so it has always been cross-platform.

Tamarin has been in continuous use since Fall 2008, handling up to 150 students each semester.  Initially, Tamarin only accepted and stored submissions; I ran a second Tamarin instance on my home machine for grading. The next semester, Tamarin graded submissions as they came in. Since Fall 2009, another TA and instructor have also been using Tamarin.

Now that it has proven useful, it is time to open Tamarin up to an even larger community.

Tamarin's "backronym" is the Teaching Assistant's Menial ARtificial INtelligence.

<br>
<b>Next:</b> <a href='Philosophy.md'>Philosophy</a>