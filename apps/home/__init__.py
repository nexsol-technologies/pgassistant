# -*- encoding: utf-8 -*-
"""
Init Blueprint
"""

from flask import Blueprint

blueprint = Blueprint(
    'home_blueprint',
    __name__,
    url_prefix=''
)
