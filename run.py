# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
import random
import string
#from   flask_migrate import Migrate
from   flask_minify  import Minify
from   sys import exit

from apps.config import config_dict
from apps import create_app, db
from flask import session

# WARNING: Don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False')

# The configuration
get_config_mode = 'Production'

try:
    # Load the configuration using the default values
    app_config = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

app = create_app(app_config)
if not os.getenv('SECRET_KEY'):
    os.environ['SECRET_KEY']=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(31))
    print(" * Env var SECRET_KEY is not set. Using a random key")

app.secret_key = os.getenv('SECRET_KEY')

Minify(app=app, html=True, js=False, cssless=False)

if __name__ == "__main__":    
    app.run()
