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

        self.window = gtk.Window()
        self.window.set_title("Support client")
        self.window.set_default_size(640, 480)
        self.window.connect('delete-event', self.quit)

        self.main_vbox = gtk.VBox()
        self.window.add(self.main_vbox)

        self.window.show_all()


        # tooltips
        self.tooltip = gtk.Tooltips()

        # protocol handler
        self.protocol = protocol.Protocol()

        # Configura o timer
        gobject.timeout_add(1000, self.monitor)

        self.teacher = None
        self.outfile = None
        # Inicializa as threads
        self.bcast = network.BcastListener(network.LISTENPORT)
        self.log( _("Starting broadcasting service.."))
        self.bcast.start()

        self.login()

    def quit(self, widget, param):
        """Main window was closed"""
        gtk.main_quit()
        self.bcast.actions.put(1)
        sys.exit(0)

    def login(self):
        """Asks student to login"""
        dialog = gtk.Dialog(_("Login"), self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name:"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(_("Meu nome"))
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

    def log(self, text):
        """Logs something somewhere"""
        print text

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
