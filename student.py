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

from openclass import network, system, protocol

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

        # protocol handler
        self.protocol = protocol.Protocol()

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
        self.bcast = network.BcastListener(network.LISTENPORT)
        self.client = StudentClient(network.LISTENPORT, self)
        self.log( _("Starting broadcasting service.."))
        self.bcast.start()
        self.log( _("Starting listening service.."))
        self.client.start()

        self.login()

    def login(self):
        """Asks student to login"""
        dialog = gtk.Dialog(_("Login"), self.MainWindow, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name:"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(_("My class"))
        hbox.pack_start(entry_login)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.class_name = entry_login.get_text()
            print "Login: %s" % self.class_name
            dialog.destroy()
            # Starting broadcasting service
            return True
        else:
            dialog.destroy()
            return None

    def monitor(self):
        """Monitors WIFI status"""
        if self.bcast.has_msgs():
            msg = self.protocol.parse_header(self.bcast.get_msg())
            print "Got a message: %s" % self.protocol.parse_announce(msg)
        #self.StatusLabel.set_markup("<b>Link:</b> %s, <b>Signal:</b> %s, <b>Noise:</b> %s" % (link, level, noise))
        gobject.timeout_add(1000, self.monitor)

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

        self.socket_client = network.ReusableSocketServer(('', self.port), MessageHandler)
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
    if system.get_os() == "Linux":
        print "Rodando em Linux"
    else:
        print "Rodando em Windows"

    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(5)
    # Atualizando a lista de interfaces
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()

    print _("Starting GUI..")
    gui = Student("iface/student.glade")
    try:
        gui.log(_("\nWelcome to OpenClass Student!!\n\n"))
        gtk.main()
        gtk.gdk.threads_leave()
    except:
        print "exiting.."
        sys.exit()
