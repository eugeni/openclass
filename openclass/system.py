#!/usr/bin/python
"""OpenClass system module"""

import os
import socket
import traceback
import struct
import SocketServer

def run_subprocess(cmd, background=True):
    """Runs a background command"""
    print "Running: %s" % cmd
    os.system("%s" % cmd)
    pass


def get_os():
    """Returns the name of the OS"""
    try:
        # quick workaround - windows has no 'uname' :)
        ret = os.uname()
        return "Linux"
    except:
        return "Windows"
