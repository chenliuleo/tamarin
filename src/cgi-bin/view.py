#!python

## view.py 

"""
Allows users to see their previous submissions.
  
Provides a brief displayUser overview of all their work or else 
allows them to see a single submission.

Part of Tamarin, by Zach Tomaszewski.  
Created: 10 Sep 2008.
"""

import cgi

import tamarin
import core_view

def main(form=None):
    """
    Determine whether to show view login form, show all the user's work,
    or show a single given submission.
    """
    if not form:
        form = cgi.FieldStorage()
    if not form:
        # no values passed
        displayLogin()
    elif ('user' in form) and ('pass' in form):
        displayWork(form)
    else:
        tamarin.printHeader('File Upload Error')
        tamarin.printError('BAD_SUBMITTED_FORM')
        tamarin.printFooter()


def displayWork(form):
    """
    Provides the student-requested view of previously submitted work.
    """
    tamarin.printHeader()
    try:
        # Validate that this person is really capable of seeing this stuff
        # (throws exception if not)
        tamarin.authenticate(form.getfirst('user'), form.getfirst('pass'))
        if 'submission' in form:
            #wants to see a specific submission
            print('<br>')
            core_view.displaySubmission(form.getfirst('submission'))       
        else:
            #show them all their work
            #start form
            print('<form action="' + tamarin.CGI_URL + 'view.py" '
                  'method="post">')
            print('<input type="hidden" name="user" value="' + 
                  form.getfirst('user') + '">')
            print('<input type="hidden" name="pass" value="' + 
                  form.getfirst('pass') + '">')
            print('<div class="logout">[Close your browser to logout]</div>')
            core_view.displayUser(form.getfirst('user'), brief=True)
            print('</form>')
    
    except tamarin.TamarinError as err:
        tamarin.printError(err)
    except:
        tamarin.printError('UNHANDLED_ERROR')
    finally: 
        tamarin.printFooter()

def displayLogin():
    """
    Displays the login form to be used to view submissions.
    """
    tamarin.printHeader('View Submissions')
    print("""
<h2>View Submissions</h2>
<form class="html" action="/cgi-bin/view.py" method="post" 
  enctype="multipart/form-data">
<table>
<tr><td>Username:</td><td><input type="text" name="user"></td></tr>
<tr><td>Password:</td><td><input type="password" name="pass"></td></tr>
<tr><td colspan="2" style="text-align: center;">
  <input type="submit" value="View my submissions"></td></tr>
</table>
</form>
    """)
    tamarin.printFooter()
    

if __name__ == "__main__":
    #running as a script (rather than as imported module)
    main() #call main
