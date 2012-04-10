#!python

##
## view.py 
## Part of Tamarin, by Zach Tomaszewski.  Created 10 Sep 2008.
##
## Processing requests sent from view.html, allowing users to see
## their previous submissions.  Provides a brief displayUser view for
## their work, or allows them to see a single submission.
##

from tamarin import *
import displaycore

def main():
  form = cgi.FieldStorage()
  if not form:
    displayForm()
  elif ('user' in form) and ('pass' in form):
    displayViews(form)
  else:
    printHeader('File Upload Error')
    printError('BAD_SUBMITTED_FORM')
    printFooter()


def displayViews(form):
  """
  Provides the student-requested view of previously submitted work.
  """
  printHeader()
  try:

    #validate that this person is really capable of seeing this stuff
    result = authenticate(form.getfirst('user'), form.getfirst('pass'))
    
    if result == 'OK':
      if 'submission' in form:
        #wants to see a specific submission
        print '<br>'
        result = displaycore.displaySubmission(form.getfirst('submission'))
       
      else:
        #show them all their work
        #start form
        print '<form action="' + CGI_ROOT + '/view.py" method="post">'
        print '<input type="hidden" name="user" value="' + \
              form.getfirst('user') + '">'
        print '<input type="hidden" name="pass" value="' + \
              form.getfirst('pass') + '">'
        print '<div class="logout">[Close your browser to logout]</div>'
        result = displaycore.displayUser(form.getfirst('user'), brief=True)
        print '</form>'

    if result != 'OK':
      printError(result)
    
  except:
    printError('UNHANDLED_ERROR')
  finally: 
    printFooter()


def displayForm():
  """
  Displays the form to be used to view submissions.
  """
  printHeader('View Submissions')
  print """
<h2>View Submissions</h2>
<form class="html" action="/cgi-bin/view.py" method="post" enctype="multipart/form-data">
<table>
<tr><td>Username:</td><td><input type="text" name="user"></td></tr>
<tr><td>Password:</td><td><input type="password" name="pass"></td></tr>
<tr><td colspan="2" style="text-align: center;"><input type="submit" value="View my submissions"></td></tr>
</table>
</form>
  """
  printFooter()


if __name__ == "__main__":
  #running as a script (rather than as imported module)
  main() #call main
  