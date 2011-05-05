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

        # login
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_("Your name:")), False, False)
        self.name_label = gtk.Label(_("Not logged in"))
        hbox.pack_start(self.name_label, False, False)
        self.login_button = gtk.Button(_("Click here to login"))
        self.login_button.connect('clicked', self.login)
        hbox.pack_start(self.login_button, False, False)
        self.main_vbox.pack_start(hbox, False, False)

        # teacher
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_("Current teacher:")), False, False)
        self.teacher_label = gtk.Label(_("No teacher found"))
        hbox.pack_start(self.teacher_label, False, False)
        self.leave_button = gtk.Button(_("Click here to leave this class"))
        self.leave_button.connect('clicked', self.leave_class)
        self.leave_button.set_sensitive(False)
        hbox.pack_start(self.leave_button, False, False)
        self.main_vbox.pack_start(hbox, False, False)

        self.teacher_view = gtk.Label()
        self.main_vbox.pack_start(self.teacher_view)

        self.window.show_all()

        # tooltips
        self.tooltip = gtk.Tooltips()

        # protocol handler
        self.protocol = protocol.Protocol()

        # Configura o timer
        gobject.timeout_add(1000, self.monitor)

        self.teacher = None
        self.teacher_addr = None
        self.name = None
        self.outfile = None
        # Inicializa as threads
        self.bcast = network.BcastListener(network.LISTENPORT)
        self.log( _("Starting broadcasting service.."))
        self.bcast.start()

    def quit(self, widget, param):
        """Main window was closed"""
        gtk.main_quit()
        self.bcast.actions.put(1)
        sys.exit(0)

    def leave_class(self, widget):
        """Leave a class"""
        pass

    def login(self, widget):
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
            self.name = entry_login.get_text()
            print "Login: %s" % self.name
            self.name_label.set_text(self.name)
            self.login_button.set_label(_("Login as different user"))
            dialog.destroy()
        else:
            dialog.destroy()

    def monitor(self):
        """Monitors WIFI status"""
        if self.bcast.has_msgs():
            data, source = self.bcast.get_msg()
            msg = self.protocol.parse_header(data)
            name, flags = self.protocol.parse_announce(msg)
            # TODO: support multiple teachers
            self.teacher = name
            self.teacher_addr = source
            self.teacher_label.set_text("%s (%s)" % (name, source))
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
