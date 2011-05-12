#!/usr/bin/python
"""OpenClass system module"""

import os
import socket
import traceback
import struct
import SocketServer
import time

def get_user_name():
    """Returns current user name"""
    if get_os() == "Linux":
        return os.getenv("USER")
    else:
        return "user"

def get_os():
    """Returns the name of the OS"""
    try:
        # quick workaround - windows has no 'uname' :)
        ret = os.uname()
        return "Linux"
    except:
        return "Windows"

def timefunc():
    # TODO: if windows, return time.clock(); otherwise return time.time()
    return time.time()

def open_url(url):
    """Attempts to open an url"""
    if get_os() == "Linux":
        return os.system("xdg-open %s &" % url)
    else:
        # TODO: make it work on windows
        return os.system(url)
