#!/usr/bin/python
"""OpenClass network module

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
"""

import os
from multiprocessing import Queue
import socket
import traceback
import struct
import SocketServer
import sys
import time
import thread
import ssl
from threading import Thread

import cgi

import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

# constants
LISTENPORT = 40000
MCASTPORT = 40001
BCASTPORT = 40002

MCASTADDR="224.51.105.104"
BCASTADDR="255.255.255.255"

DATAGRAM_SIZE=65000

DEBUG=False

import system

# {{{ BcastSender
class BcastSender(Thread):
    """Sends broadcast requests"""
    def __init__(self, logger, port, data):
        Thread.__init__(self)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 0))
        self.actions = Queue()
        self.data = data
        self.logger = logger

    def stop():
        """Stops sending"""
        self.actions.put()

    def run(self):
        """Starts threading loop"""
        while 1:
            # TODO: add timers to exit when required
            try:
                if not self.actions.empty():
                    # exiting
                    return
                if DEBUG:
                    self.logger.debug("Sending broadcasting message..")
                self.sock.sendto(self.data, ('255.255.255.255', self.port))
                time.sleep(1)
            except:
                self.logger.exception("Error sending broadcast message: %s" % sys.exc_value)
                time.sleep(1)
# }}}

# {{{ HTTPListener
class HTTPRequestHandler(SimpleHTTPRequestHandler):
    """Handles HTTP requests"""
    listener = None

    def log_request(self, code='-', size='-'):
        """Log request"""
        pass

    def do_GET(self):
        """GET request"""
        client = self.client_address[0]

        # find out what to reply
        p = self.path.split("?")
        # strip leading /
        path = p[0][1:]
        if len(p) > 1:
            params = cgi.parse_qs(p[1], True, True)
        else:
            params = {}
        # Support additional client identifiers, like $DISPLAY for multi-seat
        # or windows login identifier for microsoft multi-seat version
        if "client_id" in params:
            try:
                client_s = "%s%s" % (client, params["client_id"][0])
                client = client_s
            except:
                traceback.print_exc()
        results, params = self.server.controller.process_request(client, path, params)

        self.send_response(200)
        self.end_headers()

        if results:
            self.wfile.write("%s %s" % (results, params))

class HTTPListener(Thread):
    def __init__(self, controller):
        Thread.__init__(self)
        self.actions = Queue()
        self.messages = []
        self.lock = thread.allocate_lock()

        self.socket = ReusableTCPServer(("", LISTENPORT), HTTPRequestHandler)
        self.socket.set_controller(controller)

    def run(self):
        while 1:
            if not self.actions.empty():
                print "Finishing server listening"
                return
            self.socket.handle_request()
# }}}

# {{{ McastListener
class McastListener(Thread):
    """Multicast listening thread"""
    def __init__(self, addr=MCASTADDR, port=MCASTPORT):
        Thread.__init__(self)
        self.actions = Queue()
        self.messages = Queue()
        self.addr = addr
        self.port = port

    def stop(self):
        """Stops the execution"""
        self.actions.put(1)

    def run(self):
        """Keep listening for multicasting messages"""
        # Configura o socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        # configura para multicast
        mreq = struct.pack("4sl", socket.inet_aton(self.addr), socket.INADDR_ANY)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # configura timeout para 1 segundo
        s.settimeout(1)
        while 1:
            if not self.actions.empty():
                print "Finishing multicast capture"
                s.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                s.close()
                return
            try:
                data, client_addr = s.recvfrom(DATAGRAM_SIZE + 1024)
                self.messages.put((data, client_addr[0]))
            except socket.timeout:
                #print "Timeout!"
                pass
            except:
                print "Exception!"
                traceback.print_exc()
# }}}

# {{{ BcastListener
class BcastListener(Thread):
    """Broadcast listening thread"""
    def __init__(self, logger, port=BCASTPORT, datagram_size=DATAGRAM_SIZE):
        Thread.__init__(self)
        self.port = port
        self.datagram_size = datagram_size
        self.actions = Queue()
        self.messages = Queue()
        self.lock = thread.allocate_lock()
        self.logger = logger

    def get_msg(self):
        """Returns one of received messages"""
        if not self.messages.empty():
            return self.messages.get()
        else:
            return None

    def has_msgs(self):
        """Returns if we have new messages"""
        return not self.messages.empty()

    def stop(self):
        """Stops the execution"""
        self.actions.put(1)

    def run(self):
        """Keep listening for broadcasting messages"""
        # Configura o socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', self.port))
        # configura timeout para 1 segundo
        s.settimeout(1)
        # configura o mecanismo de captura de tempo
        while 1:
            if not self.actions.empty():
                self.logger.info("Finishing broadcast capture")
                s.close()
                return
            try:
                data, client_addr = s.recvfrom(self.datagram_size)
                self.logger.info("Received %s from %s" % (data, client_addr[0]))
                self.messages.put((data, client_addr[0]))
            except socket.timeout:
                #print "Timeout!"
                pass
            except:
                self.logger.exception("Exception while handling broadcast")
# }}}

# {{{ TcpClient
class TcpClient:
    """TCP Client"""
    def __init__(self, addr, port, use_ssl=False):
        """Initializes a TCP connection"""
        self.addr = addr
        self.port = port
        self.use_ssl = use_ssl
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if use_ssl:
            self.sock = ssl.wrap_socket(self.sock)

    def connect(self, timeout=None, retries=1):
        """Attempts to connect"""
        while retries > 0:
            try:
                self.sock.connect((self.addr, self.port))
                if timeout:
                    s.settimeout(timeout)
                return True
            except:
                traceback.print_exc()
                continue
        # Unable to establish a connection
        return False

    def close(self, msg=None):
        """Closes a connection"""
        if msg:
            self.sock.send(msg)
        self.sock.close()

    def send(self, msg):
        """Sends a message"""
        self.sock.write(msg)

    def recv(self, msg_size):
        """Receives a message"""
        try:
            data = self.sock.read(msg_size)
            return data
        except:
            traceback.print_exc()
            return None
# }}}

# {{{ McastSender
class McastSender(Thread):
    """Multicast socket for sending stuff"""
    def __init__(self, logger, interval=0.05):
        """Configures multicast sender. Interval is the minimum interval between packets"""
        Thread.__init__(self)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.queue = Queue()
        self.socket = s
        self.interval = interval
        self.logger = logger

    def send(self, data, addr=MCASTADDR, port=MCASTPORT):
        """Sends stuff via multicast"""
        self.socket.sendto(bytes(data), (addr, port))

    def run(self):
        """Runs the thread, waiting for instructions via queue interface"""
        lasttime = system.timefunc()
        curtime = lasttime
        while 1:
            command, payload = self.queue.get()
            if command == "quit":
                return
            elif command == "send":
                curtime = system.timefunc()
                curdelay = curtime - lasttime
                if curdelay < self.interval:
                    delay = self.interval - curdelay
                    self.logger.debug("Sending too fast, sleeping for %f" % curdelay)
                    time.sleep(curdelay)
                # do the sending
                self.send(payload)
                lasttime = curtime

    def put(self, payload):
        """Queues a packet for multicast sending"""
        self.queue.put(("send", payload))

    def quit(self):
        """Tells thread to leave"""
        self.queue.put(("quit", None))
# }}}

class ReusableForkingTCPServer(SocketServer.ForkingTCPServer):
    allow_reuse_address = True

    def set_controller(self, controller):
        """Sets a fallback countroller"""
        self.controller = controller

class ReusableTCPServer(SocketServer.TCPServer):
    allow_reuse_address = True

    def set_controller(self, controller):
        """Sets a fallback countroller"""
        self.controller = controller

class ReusableSocketServer(SocketServer.TCPServer):
    allow_reuse_address = True

