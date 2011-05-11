#!/usr/bin/python
"""This file describes the communication protocol of OpenClass."""

OPENCLASS_HEADER="Open Class"
OPENCLASS_VERSION_MAJOR=0
OPENCLASS_VERSION_MINOR=1
OPENCLASS_BUILD=1

# protocol commands
ACTION_NOOP="noop"
ACTION_MSG="msg"
ACTION_ATTENTION="attention"
ACTION_PROJECTION="projection"
ACTION_SHOT="shot"
ACTION_PLEASEREGISTER="pleaseregister"

# requests
REQUEST_REGISTER="register"
REQUEST_ACTIONS="actions"
REQUEST_RAISEHAND="raisehand"
REQUEST_SHOWSCREEN="showscreen"

import struct
import traceback

class Protocol:
    """This is the main class for OpenClass protocol."""
    # protocol commands
    COMMAND_ANNOUNCE=1
    # class announce flags
    ANNOUNCE_RESTRICTED = 1<<0

    def __init__(self):
        """Initializes protocol processing class"""
        # protocol messages
        self.header = struct.pack("!10sii", OPENCLASS_HEADER, OPENCLASS_VERSION_MAJOR, OPENCLASS_VERSION_MINOR)
        self.header_len = len(self.header)

    def parse_header(self, msg):
        """Parses header"""
        if len(msg) < self.header_len:
            # message too short
            print "Message too short"
            return None
        header = msg[:self.header_len]
        name, major, minor = struct.unpack("!10sii", header)
        if name != OPENCLASS_HEADER:
            # wrong app name
            print "Wrong app name: <%s|%s>" % (name, OPENCLASS_HEADER)
            return None
        if major != OPENCLASS_VERSION_MAJOR or minor != OPENCLASS_VERSION_MINOR:
            # bad version
            print "Wrong app version"
            return None
        # all ok
        return msg[self.header_len:]

    def create_announce(self, class_name, restricted=False):
        """Creates announce message."""
        header = self.header
        header += struct.pack("!64p", class_name)
        flags = 0
        if restricted:
            flags |= ANNOUNCE_RESTRICTED
        header += struct.pack("i", flags)
        return header

    def parse_announce(self, announce):
        """Parses a class announcment"""
        try:
            name, flags = struct.unpack("!64pi", announce)
            print name
            # strip trailing null bytes
            return (name, flags)
        except:
            traceback.print_exc()
            return None

    def pack_chunk(self, screen_width, screen_height, chunk):
        """Packs a chunk into network-specific format for sending"""
        pos_x, pos_y, step_x, step_y, img = chunk
        data = struct.pack("!iiiiii", screen_width, screen_height, pos_x, pos_y, step_x, step_y)
        return data + img

    def unpack_chunk(self, data):
        """Unpacks a chunk of data"""
        head_size = struct.calcsize("!iiiiii")
        screen_width, screen_height, pos_x, pos_y, step_x, step_y = struct.unpack("!iiiiii", data[:head_size])
        return screen_width, screen_height, pos_x, pos_y, step_x, step_y, data[head_size:]

