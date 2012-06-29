#!python3

""" 
A wrapper for directly creating a cgi object for unit-testing purposes.

If you write your cgi script's main method like this:

    def main(form=None):
        if form is None:
            form = cgi.FieldStorage()
        ...use form object for all submitted form data...
      
then you can easily build a CGI unit using this cgifactory module and pass 
it in, like so:

    form = cgifactory.get(key1='value1', ...)

    sys.stdout = io.StringIO()  #redirect stdout as a string
    myscript.main(form)         #run your script with the given CGI input
    ...run unit tests based on the output in sys.stdout.getvalue()...
    
    #restore stdout
    sys.stdout.close()
    sys.stdout = sys.__stdout__ 


For the example of manual CGI object creation, thanks to: 
http://bugs.python.org/file9507/cgitest.py

Author:  Zach Tomaszewski
Created: 22 Jun 2012

"""

import cgi
import io
import urllib.parse

def get(**pairs):
    """
    Returns a CGI object with the given GET key-value pairs.

    All text of keys and values is assumed to use UTF-8 encoding.
    A single key can have multiple values if a sequence of values is given.

    The returned CGI object is built from a URL-encoded GET-based query.
        
    Examples:
    
    An empty form:
    >>> import cgifactory
    >>> form = cgifactory.get()
    >>> form
    FieldStorage(None, None, [])

    A form with one value that requires urlencoding escapes:
    >>> form = cgifactory.get(key1='a long & complicated value...?')
    >>> form.getvalue('key1')
    'a long & complicated value...?'
    
    Multiple keys, one of which has multiple values:
    >>> form = cgifactory.get(key1='v1', key2=('v2', 'value2', 'etc'))
    >>> form.getfirst('key1')
    'v1'
    >>> form.getfirst('key2')
    'v2'
    >>> form.getlist('key2')
    ['v2', 'value2', 'etc']
    
    """    
    environ = {
        'CONTENT_TYPE':     'application/x-www-form-urlencoded',
        'REQUEST_METHOD':   'GET',
        'QUERY_STRING':     urllib.parse.urlencode(pairs, doseq=True),
    }
    return cgi.FieldStorage(environ=environ)
    

def post(filenames={}, **pairs):
    """
    Returns a CGI object with the given POST key-value pairs.

    If a filenames dictionary is also given, the values of the 
    corresponding keys in pairs are treated as the contents of
    plain-text files.  The values of the filenames dict are the
    original names of the those files.

    All text of keys, values, and file contents is assumed to use 
    UTF-8 encoding.  However, any file data retrieved from the
    returned CGI object will be bytes (as is normal for CGI).

    The returned CGI object is built from a POST-based query.
        
    Examples:
        
    Simple key-value:
    >>> import cgifactory
    >>> form = cgifactory.post(key1='value1', key2='v2')
    >>> form.getvalue('key2')
    'v2'

    A file upload:
    >>> form = cgifactory.post(user='John Doe', upload='one line file', \
    filenames={'upload': 'testfile.txt'})
    >>> form.getvalue('user')
    'John Doe'
    >>> form['user'].filename
    >>> form.getvalue('upload')
    b'one line file'
    >>> form['upload'].filename
    'testfile.txt'
    
    """
    data = ''
    for k,v in pairs.items():
        data += '---123\n'
        data += 'Content-Disposition: form-data; name="' + k + '"'
        if k in filenames:
            data += '; filename="' + filenames[k] + '"'
        data += '\n\n'
        if v:
            data += v
            data += '\n'

    data = bytes(data, 'utf-8')  #convert to bytes

    environ = {
        'CONTENT_TYPE':    'multipart/form-data; boundary=-123',
        'REQUEST_METHOD':  'POST',
        'CONTENT_LENGTH':  str(len(data)),
    }
    return cgi.FieldStorage(environ=environ, fp=io.BytesIO(data))
    
    