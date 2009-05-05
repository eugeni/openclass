#!/usr/bin/python
"""OpenClass network module"""

import os
import socket
import traceback
import struct
import SocketServer
import sys
import time
from threading import Thread

LISTENPORT = 40000
MCASTPORT = 40001
BCASTPORT = 40002

MCASTADDR="224.51.105.104"
BCASTADDR="255.255.255.255"

DEBUG=False

# {{{ TrafBroadcast
class TrafBroadcast(Thread):
    """Broadcast-related services"""
    def __init__(self, port, service, name):
        """Initializes listening thread"""
        Thread.__init__(self)
        self.port = port
        self.service = service
        self.name = name

    def run(self):
        """Starts listening to broadcast"""
        class BcastHandler(SocketServer.DatagramRequestHandler):
            """Handles broadcast messages"""
            def handle(self):
                """Receives a broadcast message"""
                client = self.client_address[0]
                print " >> Heartbeat from %s!" % client
                self.server.service.add_client(client)
        self.socket_bcast = SocketServer.UDPServer(('', self.port), BcastHandler)
        self.socket_bcast.service = self.service
        while 1:
            try:
                self.socket_bcast.handle_request()
            except socket.timeout:
                print "Timeout caught!"
                continue
            except:
                print "Error handling broadcast socket!"
                break
# }}}

# {{{ BcastSender
class BcastSender(Thread):
    """Sends broadcast requests"""
    def __init__(self, port, gui):
        Thread.__init__(self)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 0))
        self.gui = gui

    def run(self):
        """Starts threading loop"""
        print "Running!"
        while 1:
            # TODO: add timers to exit when required
            try:
                if DEBUG:
                    self.gui.log(_("Sending broadcasting message.."))
                self.sock.sendto("hello", ('255.255.255.255', self.port))
                time.sleep(1)
            except:
                self.gui.log("Error sending broadcast message: %s" % sys.exc_value)
                traceback.print_exc()
                time.sleep(1)
# }}}

# {{{ McastListener
class McastListener(Thread):
    """Multicast listening thread"""
    def __init__(self):
        Thread.__init__(self)
        self.actions = Queue.Queue()
        self.messages = []
        self.lock = thread.allocate_lock()

    def get_log(self):
        """Returns the execution log"""
        self.lock.acquire()
        msgs = "\n".join(self.messages)
        return "# received msgs: %d msg_size: %d\n%s" % (len(self.messages), DATAGRAM_SIZE, msgs)
        self.lock.release()

    def stop(self):
        """Stops the execution"""
        self.actions.put(1)

    def run(self):
        """Keep listening for multicasting messages"""
        # Configura o socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', MCASTPORT))
        # configura para multicast
        mreq = struct.pack("4sl", socket.inet_aton(MCASTADDR), socket.INADDR_ANY)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # configura timeout para 1 segundo
        s.settimeout(1)
        # configura o mecanismo de captura de tempo
        if get_os() == "Windows":
            timefunc = time.clock
        else:
            timefunc = time.time
        last_ts = None
        while 1:
            if not self.actions.empty():
                print "Finishing multicast capture"
                s.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                s.close()
                return
            try:
                data = s.recv(DATAGRAM_SIZE + 1024)
                count = struct.unpack("<I", data[:struct.calcsize("<I")])[0]
                self.lock.acquire()
                curtime = timefunc()
                walltime = time.time()
                if not last_ts:
                    last_ts = curtime
                    timediff = 0
                else:
                    timediff = curtime - last_ts
                    last_ts = curtime
                self.messages.append("%d %f %f %f" % (count, timediff, curtime, walltime))
                self.lock.release()
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
    def __init__(self):
        Thread.__init__(self)
        self.actions = Queue.Queue()
        self.messages = []
        self.lock = thread.allocate_lock()

    def get_log(self):
        """Returns the execution log"""
        self.lock.acquire()
        msgs = "\n".join(self.messages)
        return "# received msgs: %d msg_size: %d\n%s" % (len(self.messages), DATAGRAM_SIZE, msgs)
        self.lock.release()

    def stop(self):
        """Stops the execution"""
        self.actions.put(1)

    def run(self):
        """Keep listening for broadcasting messages"""
        # Configura o socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', BCASTPORT))
        # configura timeout para 1 segundo
        s.settimeout(1)
        # configura o mecanismo de captura de tempo
        if get_os() == "Windows":
            timefunc = time.clock
        else:
            timefunc = time.time
        last_ts = None
        while 1:
            if not self.actions.empty():
                print "Finishing broadcast capture"
                s.close()
                return
            try:
                data = s.recv(DATAGRAM_SIZE)
                count = struct.unpack("<I", data[:struct.calcsize("<I")])[0]
                self.lock.acquire()
                curtime = timefunc()
                walltime = time.time()
                if not last_ts:
                    last_ts = curtime
                    timediff = 0
                else:
                    timediff = curtime - last_ts
                    last_ts = curtime
                self.messages.append("%d %f %f %f" % (count, timediff, curtime, walltime))
                self.lock.release()
            except socket.timeout:
                #print "Timeout!"
                pass
            except:
                print "Exception!"
                traceback.print_exc()
# }}}

def connect_tcp(addr, port, timeout=None):
    """Envia mensagem por socket TCP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((addr, port))
        if timeout:
            s.settimeout(timeout)
        return s
    except:
        traceback.print_exc()
        return None

class ReusableSocketServer(SocketServer.TCPServer):
    # TODO: allow address reuse
    allow_reuse_address = True

