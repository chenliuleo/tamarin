# Installation #

This page explains how to configure to your web server to serve Python 3 CGI scripts, install the necessary Tamarin files, and customize the details of your Tamarin instance.  It also discusses security issues you should be aware of and how to run multiple Tamarin instances on the same web server by using virtual hosts.

These directions assume you have the required administration rights to configure your web server, and that you are comfortable using a command prompt, installing software, and editing configuration files.

## Installation ##

### 0) Linux ###
While you could use a different OS, I'll assume Linux here.  I recommend Debian.  You can start with a bare-bones install (uncheck all of the major package groups).  You'll then need SSH (to log in the machine), Apache, Python 3, and Java (preferably the latest version).

### 1) Python 3 is Installed ###

Tamarin requires Python 3.0 or later release.  Check if Python 3 is installed by typing ```
python --version``` at your command prompt.  If that doesn't return an appropriate version number, you might also check if ```
python3 --version``` works.

If Python 3+ is not installed, you'll need to install it.  See http://python.org for more.

### 2) Python Scripts are Executable ###

Put the following code in a file named `hello.py`:
```
#!python3
print("Hello! Python works.")
```

You may need to change `python3` in the she-bang (#!) line to the full appropriate path to your Python 3 executable.  If so, you'll also need this path info later.

Also, if you're on a Linux/Unix machine, remember that you may need to use `chmod` to make your script file executable.

Typing ```
hello.py``` in the same directory as your file should run the script, producing the Hello message.

### 3) Web Server Works ###

Now that Python works, you'll need a working web server.  You're on your own for this.  If you don't have a preference, I recommend [Apache 2](http://apache.org/httpd/).  Your web server installation guide should walk you through the necessary steps and checks.

Double-check that your server is configured correctly be accessing one of its .html pages.

### 4) Configure CGI ###

Now configure your web server to handle Python-based CGI scripts.  Normally, these scripts will be served from a special cgi-bin directory.  As an Apache example, see http://httpd.apache.org/docs/2.4/howto/cgi.html.

To test that this works, put the following in a file named `hellocgi.py` in your cgi-bin:

```
#!python3

import sys
import cgi

sys.stderr = sys.stdout  #so that Python errors get printed to screen
cgi.test()
```

You should be able to run this file on the command line.  But, more importantly, you should also be able to direct your browser to your server's /cgi-bin/hellocgi.py and see the output in your browser.

Again, you may need to update the full path to python and the file's permissions.  You may need to do this to run the script through the web server even if it runs fine on the command line.  If you get a Internal Server Error, remember to check your server's error log for more specific error details.

By this point, your web server is ready and capable of serving Python CGI scripts.  It should be downhill from here!  (You can delete the two hello scripts now if you like.)

### 5) Download Tamarin ###

You can use SVN to download or checkout the latest copy from this repository.

Or, you can download a recent version as a zip: [Tamarin-10Oct2013.zip](http://zach.tomaszewski.name/tamarin/Tamarin-10Oct2013.zip)

The zip file should contain 3 directories: cgi-bin/, htdocs/, and tamarin/

### 6) Install Tamarin's .py scripts ###

Copy the .py files from the zip's cgi-bin/ into your cgi-bin/ directory (or wherever you're serving CGI scripts from).

Based on your experiences from above, you will likely need to adjust the file permissions and update the Python path at the head of the files.  (tamarin.py and any Tamarin file that starts with core_is a module file and so it does not need an initial #! line.)_

To check that your edits worked, try opening cgi-bin/upload.py in your web browser.  (It might look a little clunky at this point, but you should at least see a couple form fields and not an error message.  If running on Linux, you may need to check the files' line-endings as described in the comments below.)

### 7) Install Tamarin's .html files ###

Put these somewhere in your server's /htdocs directory.

### 8) Set up the tamarin/ directory ###

This folder should go at the same level as the /cgi-bin and /htdocs directories.  Do NOT put it within either of those directories because the graders and graded files should never be served or viewable as pages by the web server.

Your web server (which usually runs as www-data on Debian) must have write permission to (basically) all of the sub-folders in the tamarin/ directories.  For example, this includes uploaded/, submitted/, and the graded/ subdirectories.  You can make these folders group-writable, where the group is www-data.  Check out the `chmod g+s filename` command, where you can set a directory's group sticky bit so that any new files or directories created in that directory will inherit that same group ownership settings.

Also, you may want to set the umask settings for all users to use 002 rather than 022.  This means that all newly created files will be writeable by the group.  This way, combined with the group sticky bit trick above, if you create new subdirectories in graded/, they will automatically have the correct permissions: correct www-data group and writable by everyone in that group.

Related but separate to this, you may want TA users to be able to edit or overwrite files on the server.  All the files created by Tamarin will be owned by www-data with a group of www-data.  If you put all TA users in the www-data group, and you have the output directory's sticky bit and Apache's umask settings correct, TAs will be able to edit those files because they are in the same group and files are group-writable.  Getting Apache 2 to use 002 as a umask can be a bit tricky though.  See /etc/apache2/envvars (on Debian and Ubuntu systems) or /etc/sysconfig/httpd (for rhel or centos systems) and add the line: `umask 002`

## Configuration ##

See the first half of tamarin/tamarin.py for all global settings and variables  that you can customize for your Tamarin instance.

Be sure to test any changes by creating a test user and uploading a sample files and making sure that Tamarin correctly finishes grading it and stores the output correctly.

## Security ##
  * Tamarin user passwords are not encrypted.
  * ...

## Multiple Tamarins ##

You can setup multiple Tamarins on the same web server by using the server's virtual host capabilities.  Essentially, you duplicate the cgi-bin/, htdocs/, and tamarin/ structure for each Tamarin, and have each accessible as a different subdomain, such as ics111.mytamarin.com and ics211.mytamarin.com.

If your server is particularly starved for resources, you can then even share a single grading pipeline between all these Tamarins.  Choose one Tamarin to be the primary Tamarin, and then config the other Tamarins to use that primary's gradezone and status directories, but its own directories for everything else.  This way, there is only one pipeline.

While this shared pipeline saves server resources, a known issue is as follows:  Suppose the pipeline is grading for Tamarin A.  Someone then submits something to Tamarin B.  B's grading pipeline won't start because A's is already running.  A's pipeline finishes its grading, but Tamarin A has its own uploaded/ folder and so won't grade anything for Tamarin B.  Thus, the submission to Tamarin B will continue to sit ungraded until another submission to Tamarin B starts the grader for B (or if the grader is started manually by a Tamarin B's human TA).