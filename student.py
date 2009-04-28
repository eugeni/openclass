#!/usr/bin/python
"""
Traffic analysis client.
"""

# TODO:
# - adicionar wireshark no path (!!)
# - imprimir mensagens no log
# - pedir para escolher a interface logo na inicializacao

import sys
import traceback
import time

import Queue

import socket
import SocketServer
import struct

import os
import logging
import gtk
import gtk.glade
import pygtk
import gobject

from threading import Thread
import thread
import socket
import traceback
import time

import gettext
import __builtin__
__builtin__._ = gettext.gettext

from config import *

DEBUG=False

# configuracoes globais
commands = None
iface_selected = 0

class Student:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, guifile):
        """Initializes the interface"""
        # colors
        self.color_normal = gtk.gdk.color_parse("#99BFEA")
        self.color_active = gtk.gdk.color_parse("#FFBBFF")
        self.color_background = gtk.gdk.color_parse("#FFFFFF")

        self.wTree = gtk.glade.XML(guifile)

        # Callbacks
        dic = {
                "on_MainWindow_destroy": self.on_MainWindow_destroy # fecha a janela principal
                }
        self.wTree.signal_autoconnect(dic)

        # tooltips
        self.tooltip = gtk.Tooltips()

        # Configura os botoes
        self.QuitButton.connect('clicked', self.on_MainWindow_destroy)

        # Configura o timer
        gobject.timeout_add(1000, self.monitor)

        # configura as interfaces
        self.IfacesBox.set_model(gtk.ListStore(str))
        cell = gtk.CellRendererText()
        self.IfacesBox.pack_start(cell, True)
        self.IfacesBox.add_attribute(cell, 'text', 0)
        self.IfacesBox.append_text(_("Network interface"))

        self.IfacesBox.set_active(0)
        self.iface = None
        self.outfile = None
        # Inicializa as threads
        self.bcast = BcastSender(LISTENPORT, self)
        self.client = StudentClient(LISTENPORT, self)
        self.log( _("Starting broadcasting service.."))
        self.bcast.start()
        self.log( _("Starting listening service.."))
        self.client.start()

    def monitor(self):
        """Monitors WIFI status"""
        #self.StatusLabel.set_markup("<b>Link:</b> %s, <b>Signal:</b> %s, <b>Noise:</b> %s" % (link, level, noise))
        #gobject.timeout_add(1000, self.monitor)

    def __getattr__(self, attr):
        """Requests an attribute from Glade"""
        obj = self.wTree.get_widget(attr)
        if not obj:
            #bluelab_config.error("Attribute %s not found!" % attr)
            return None
        else:
            return obj

    def on_MainWindow_destroy(self, widget):
        """Main window was closed"""
        gtk.main_quit()
        sys.exit(0)

    def log(self, text):
        """Logs a string"""
        #gtk.gdk.threads_enter()
        buffer = self.textview1.get_buffer()
        iter = buffer.get_iter_at_offset(0)
        print text
        buffer.insert(iter, "%s: %s\n" % (time.asctime(), text))
        #gtk.gdk.threads_leave()

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
                gui.log("Error sending broadcast message: %s" % sys.exc_value)
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

class StudentClient(Thread):
    """Handles server messages"""
    def __init__(self, port, gui):
        """Initializes listening thread"""
        Thread.__init__(self)
        self.port = port
        self.socket_client = None
        self.gui = gui
        gui.outfile = None
        # Determina comandos a utilizar

    def run(self):
        """Starts listening to connections"""
        class MessageHandler(SocketServer.StreamRequestHandler):
            """Handles server messages"""
            def handle(self):
                """Handles incoming requests"""
                addr = self.client_address[0]
                gui.log(_("Received request from %s" % addr))
                msg = self.request.recv(1)
                cmd = struct.unpack('<b', msg)[0]
                print cmd

        self.socket_client = ReusableSocketServer(('', self.port), MessageHandler)
        while 1:
            try:
                self.socket_client.handle_request()
            except socket.timeout:
                print "Timeout caught!"
                continue
            except:
                print "Error handling client socket!"
                break

if __name__ == "__main__":
    if get_os() == "Linux":
        print "Rodando em Linux"
        commands = commands_linux
    else:
        print "Rodando em Windows"
        commands = commands_windows

    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(5)
    # Atualizando a lista de interfaces
    gtk.gdk.threads_init()

    print _("Starting GUI..")
    gui = Student("iface/student.glade")
    try:
        gtk.gdk.threads_enter()
        gui.log(_("\nWelcome to OpenClass Student!!\n\n"))
        gtk.main()
        gtk.gdk.threads_leave()
    except:
        print "exiting.."
        sys.exit()
