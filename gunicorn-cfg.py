# -*- encoding: utf-8 -*-
"""
Copyright (c) 2024 - present Nexsol technologies
"""

bind = '0.0.0.0:5005'
workers = 5
threads = 4 
accesslog = '-'
loglevel = 'info'
capture_output = True
enable_stdio_inheritance = True
worker_class = 'sync'
timeout = 600  
preload_app = True
max_requests = 1000
max_requests_jitter = 50