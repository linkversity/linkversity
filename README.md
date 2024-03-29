
# LINKVERSITY ![Static Badge](https://img.shields.io/badge/fund-opencollective%2Fshopyo%2Flinkversity-green?link=https%3A%2F%2Fopencollective.com%2Fshopyo%2Fprojects%2Flinkversity)


Create courses out of links, useful for OpenSource as well as documenting internal knowledge. It's not possible to replicate the knowledge of the web from scratch. Bring in pieces from the web to help people get started very quickly.

Demo: [contriblearn.com](https://contriblearn.com)

Create venv and install requirements


```
python -m pip install -r requirements.txt 
```


Create in linkversity/linkversity

```
mkdir instance # create instance folder
touch instance//config.py # create config file
```

Inside the config.py file, add

```python
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{username}:{password}@{server_name}/{db_name}".format(
            username='',
            password='',
            server_name='localhost',
            db_name='linkversity'
        )
PASSWORD_SALT = 'RANDOMSALT'
```

First time run


```
python manage.py initialise
```

Make sure the wsgi file is like this, sometimes the host overrides it, re-add back

```python
# +++++++++++ FLASK +++++++++++
# Flask works like any other WSGI-compatible framework, we just need
# to import the application.  Often Flask apps are called "app" so we
# may need to rename it during the import:
#
#
import sys
import os
#
## The "/home/appinv" below specifies your home
## directory -- the rest should be the directory you uploaded your Flask
## code to underneath the home directory.  So if you just ran
## "git clone git@github.com/myusername/myproject.git"
## ...or uploaded files to the directory "myproject", then you should
## specify "/home/appinv/myproject"
# on shell do pwd to get a path like this:'/home2/folder/shopyo/shopyo' set path to this
path = os.getcwd()
if path not in sys.path:
    sys.path.insert(0, path)
#
from app import app as application  # noqa

#
# NB -- many Flask guides suggest you use a file called run.py; that's
# not necessary on PythonAnywhere.  And you should make sure your code
# does *not* invoke the flask development server with app.run(), as it
# will prevent your wsgi file from working.
# whatever app you specify, modify that
```

## How the website is organised

All pages are in static/theems/front/linkolearn_theme/

Go there to modify the page you want

modules/box__linkolearn contains all config code
modules/www contains the code for handling / /username /username/path

Uses the [shopyo](https://github.com/shopyo/shopyo) web framework.
