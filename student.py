#!/usr/bin/python
"""
OpenClass student module.

Copyright, (C) Eugeni Dodonov <eugeni@dodonov.net>, 2008-2011

Distributed under GPLv2 license, please see COPYING for details.

"""

import sys
import traceback
import time

from multiprocessing import Queue

import socket
import SocketServer
import struct

import os
import logging
import gtk
import gtk.glade
import pygtk
import gobject
from gtk import gdk

from threading import Thread
import thread
import socket
import traceback
import time
import pynotify

import urllib, urllib2

import gettext
import __builtin__
__builtin__._ = gettext.gettext

try:
    gettext.install("openclass")
except IOError:
    _ = str
    traceback.print_exc()

from openclass import network, system, protocol, screen

DEBUG=False

# configuracoes globais
commands = None
iface_selected = 0

class Student:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, guifile, max_missed_commands=30):
        """Initializes the interface"""
        # colors
        self.color_normal = gtk.gdk.color_parse("#99BFEA")
        self.color_active = gtk.gdk.color_parse("#FFBBFF")
        self.color_background = gtk.gdk.color_parse("#FFFFFF")

        self.icon = gtk.StatusIcon()

        menu = '''
            <ui>
             <menubar name="Menubar">
              <menu action="Menu">
               <menuitem action="Login"/>
               <menuitem action="Teacher"/>
               <separator/>
               <menuitem action="RaiseHand"/>
               <separator/>
               <menuitem action="About"/>
               <separator/>
               <menuitem action="Quit"/>
              </menu>
             </menubar>
            </ui>
        '''
        actions = [
            ('Menu',  None, 'Menu'),
            ('Login', None, _('_Login'), None, _('Identify yourself to the teacher'), self.login),
            ('Teacher', gtk.STOCK_PREFERENCES, _('_Teacher'), None, _('Select your teacher'), self.choose_teacher),
            ('RaiseHand', gtk.STOCK_INFO, _('_Call attention'), None, _('Raise your hand to call teacher attention'), self.raise_hand),
            ('About', gtk.STOCK_ABOUT, _('_About'), None, _('About OpenClass'), self.on_about),
            ('Quit', gtk.STOCK_QUIT, _('_Quit'), None, _('Quit class'), lambda *w: self.quit(None, None))
            ]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent
        search = self.manager.get_widget('/Menubar/Menu/Login')
        search.get_children()[0].set_markup('<b>_Login...</b>')
        search.get_children()[0].set_use_underline(True)
        search.get_children()[0].set_use_markup(True)
        # disconnected by default
        self.disconnect()
        self.icon.set_visible(True)
        self.icon.connect('activate', self.on_activate)
        self.icon.connect('popup-menu', self.on_popup_menu)

        # protocol handler
        self.protocol = protocol.Protocol()

        # Configura o timer
        gobject.timeout_add(1000, self.monitor_bcast)
        gobject.timeout_add(500, self.monitor_mcast)
        gobject.timeout_add(1000, self.monitor_teacher)

        self.teacher = None
        self.teacher_addr = None
        self.name = None
        self.outfile = None
        self.missed_commands = 0
        self.max_missed_commands = max_missed_commands

        # Inicializa as threads
        self.bcast = network.BcastListener(network.LISTENPORT)
        self.log( _("Starting broadcasting service.."))
        self.bcast.start()

        self.mcast = network.McastListener()

        self.screen = screen.Screen()

        # drawing
        self.projection_window = gtk.Window()
        self.projection_window.set_resizable(False)
        #self.projection_window.set_has_frame(False)
        #self.projection_window.set_decorated(False)
        self.projection_window.set_keep_above(True)
        self.projection_window.connect('delete-event', lambda *w: True)
        self.projection_window.visible = False
        vbox = gtk.VBox()
        self.projection_window.add(vbox)
        self.gc = None
        self.drawing = gtk.DrawingArea()
        self.drawing.set_size_request(self.screen.width, self.screen.height)
        vbox.pack_start(self.drawing)
        self.projection_window.hide()


        # attention
        self.attention_window = gtk.Window()
        self.attention_window.set_resizable(False)
        self.attention_window.set_has_frame(False)
        self.attention_window.set_decorated(False)
        self.attention_window.set_keep_above(True)
        self.attention_window.connect('delete-event', lambda *w: True)
        self.attention_window.visible = False

        vbox = gtk.VBox()
        self.attention_window.add(vbox)
        self.attention_label = gtk.Label()
        self.attention_label.set_use_markup(True)
        vbox.pack_start(self.attention_label)

        self.attention_window.hide()

        self.login(None)

    def disconnect(self):
        """Disconnected from teacher"""
        self.icon.set_from_file("iface/machine_off.png")
        self.icon.set_tooltip(_('OpenClass student (disconnected)'))
        teacher_label = self.manager.get_widget('/Menubar/Menu/Teacher')
        teacher_label.get_children()[0].set_markup(_("Disconnected from teacher"))
        teacher_label.get_children()[0].set_use_markup(True)
        self.teacher = None
        self.teacher_addr = None

    def connect_to_teacher(self, teacher):
        """Disconnected from teacher"""
        self.icon.set_from_file("iface/machine.png")
        self.icon.set_tooltip(_('OpenClass student (connected to %s)') % teacher)
        teacher_label = self.manager.get_widget('/Menubar/Menu/Teacher')
        teacher_label.get_children()[0].set_markup(_("Connected to <b>%s</b>") % teacher)
        teacher_label.get_children()[0].set_use_markup(True)

    def on_activate(self, data):
        """Tray icon is clicked"""
        pass

    def on_popup_menu(self, status, button, time):
        """Right mouse button is clicked on tray icon"""
        self.menu.popup(None, None, None, button, time)

    def choose_teacher(self, data):
        """Select different teacher or disconnection from current one"""
        print 'No way to choose multiple teachers yet, sorry'

    def raise_hand(self, data):
        """Raise your hand to teacher"""
        command, params = self.send_command(protocol.REQUEST_RAISEHAND)
        print command

    def on_about(self, data):
        dialog = gtk.AboutDialog()
        dialog.set_name('OpenClass')
        dialog.set_version('0.0.1')
        dialog.set_comments('A Simple and Small class control application. ')
        dialog.set_website('github.com/eugeni/openclass')
        dialog.run()
        dialog.destroy()

    def quit(self, widget, param):
        """Main window was closed"""
        gtk.main_quit()
        self.bcast.actions.put(1)
        self.mcast.actions.put(1)
        sys.exit(0)

    def leave_class(self, widget):
        """Leave a class"""
        pass

    def ask_attention(self, message=_("Teacher asked you for attention")):
        """Asks for attention"""
        self.attention_label.set_markup("<big><b>%s</b></big>" % message)
        self.attention_window.set_size_request(self.screen.width, self.screen.height)
        self.attention_window.show_all()
        self.attention_window.stick()
        self.attention_window.fullscreen()

    def start_projection(self):
        """Starts screen projection"""
        self.projection_window.visible = True
        self.projection_window.stick()
        self.projection_window.show_all()

    def noop(self):
        """Back to noop state"""
        self.projection_window.visible = False
        self.projection_window.hide()
        self.attention_window.visible = False
        self.attention_window.hide()

    def login(self, widget):
        """Asks student to login"""
        dialog = gtk.Dialog(_("Login"), None, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name:"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(system.get_user_name())
        hbox.pack_start(entry_login)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.name = entry_login.get_text()
            print "Login: %s" % self.name
            name_label = self.manager.get_widget('/Menubar/Menu/Login')
            name_label.get_children()[0].set_markup(_("Logged in as <b>%s</b>") % self.name)
            name_label.get_children()[0].set_use_markup(True)

            # start threads
            if not self.mcast.isAlive():
                self.mcast.start()
            dialog.destroy()
        else:
            dialog.destroy()

    def monitor_teacher(self):
        """Periodically checks for teacher commands"""
        if self.teacher_addr:
            # connect to teacher for instructions
            command, params = self.send_command(protocol.REQUEST_ACTIONS)
            if command == protocol.ACTION_PROJECTION:
                print "Projecting"
                self.start_projection()
            elif command == protocol.ACTION_ATTENTION:
                print "Attention!"
                self.ask_attention()
                print params
            elif command == protocol.ACTION_MSG:
                print "Message: %s" % params
                self.show_message(params)
                self.noop()
            elif command == protocol.ACTION_NOOP:
                print "Stopping everything"
                self.noop()
            elif command == protocol.ACTION_PLEASEREGISTER:
                print "Students needs to register again"
                self.noop()
                self.disconnect()
            elif command == protocol.ACTION_SHOT:
                print "Teacher requested our screenshot"
                self.shot()
            elif command == protocol.ACTION_OPENFILE:
                filename = urllib.quote(params)
                print "Teacher requested us to open his file %s" % filename
                url = "http://%s:%d/%s?file=%s" % (self.teacher_addr, network.LISTENPORT, protocol.REQUEST_GETFILE, filename)
                system.open_url(url)
            elif command == protocol.ACTION_OPENURL:
                url = params
                print "Teacher requested us to open the link at %s" % url
                system.open_url(url)
            else:
                print "Unknown command %s" % command
        gobject.timeout_add(1000, self.monitor_teacher)

    def show_message(self, message):
        """Shows a message to student"""
        n = pynotify.Notification(_("Message received from teacher"), message)
        n.set_timeout(0)
        n.show()
        return

    def shot(self):
        """Send a screenshot to teacher"""
        width, height, shot = self.screen.capture()
        params = {"width": width,
                "height": height,
                "shot": shot
                }
        self.send_command(protocol.REQUEST_SHOWSCREEN, params=params)

    def send_command(self, command, params={}, teacher=None):
        """Sends a command to teacher"""
        if not teacher:
            teacher = self.teacher_addr
        if not teacher:
            print "Error: no teacher yet!"
            return None, None
        if not self.name:
            print "Error: not logged in yet!"
            return None, None
        # TODO: proper user-agent
        url = "http://%s:%d/%s" % (teacher, network.LISTENPORT, command)
        if params:
            url += "?%s" % urllib.urlencode(params)
        headers = {'User-Agent': 'openclass'}

        command = None
        params = None
        try:
            req = urllib2.Request(url, None, headers)
            response = urllib2.urlopen(req)
            ret = response.read()
            try:
                if ret:
                    command, params = ret.split(" ", 1)
            except:
                traceback.print_exc()
                command = ret
                params = None
            self.missed_commands = 0
        except:
            # something went wrong, disconnect
            self.missed_commands += 1
            if self.missed_commands > self.max_missed_commands:
                print "Too many missing commands, leaving this teacher"
                self.noop()
                self.teacher = None
                self.teacher_addr = None
                self.disconnect()
                print "Unable to talk to teacher: %s" % sys.exc_value
            print "Unable to talk to teacher for %d time: %s" % (self.missed_commands, sys.exc_value)
        return command, params

    def monitor_mcast(self):
        """Monitor for multicast messages"""
        while not self.mcast.messages.empty():
            message = self.mcast.messages.get()
            screen_width, screen_height, fullscreen, pos_x, pos_y, step_x, step_y, img = self.protocol.unpack_chunk(message)
            print "Received image at %dx%d-%dx%d (fullscreen=%s)" % (pos_x, pos_y, step_x, step_y, fullscreen)
            try:
                loader = gdk.PixbufLoader(image_type="jpeg")
                loader.write(img)
                loader.close()
                pb = loader.get_pixbuf()

                gc = self.drawing.get_style().fg_gc[gtk.STATE_NORMAL]
                # are we in fullscreen mode ?
                if fullscreen == 1:
                    width = self.screen.width
                    height = self.screen.height
                    if width != screen_width or height != screen_height:
                        self.projection_window.set_size_request(screen_width, screen_height)
                        self.drawing.set_size_request(screen_width, screen_height)
                    self.projection_window.set_has_frame(False)
                    self.projection_window.set_decorated(False)
                    self.projection_window.fullscreen()
                    scaling_ratio_x = 1.0 * width / screen_width
                    scaling_ratio_y = 1.0 * height / screen_height
                else:
                    width, height = self.projection_window.get_size()
                    if width != screen_width or height != screen_height:
                        self.projection_window.set_size_request(screen_width, screen_height)
                        self.drawing.set_size_request(screen_width, screen_height)
                    self.projection_window.set_has_frame(True)
                    self.projection_window.set_decorated(True)
                    scaling_ratio_x = 1
                    scaling_ratio_y = 1
                # drawing or scaling
                if scaling_ratio_x != 1 or scaling_ratio_y != 1:
                    # scaling received stuff
                    new_pos_x = int(pos_x * scaling_ratio_x)
                    new_pos_y = int(pos_y * scaling_ratio_y)
                    new_step_x = int(step_x * scaling_ratio_x)
                    new_step_y = int(step_y * scaling_ratio_y)
                    pb2 = pb.scale_simple(new_step_x, new_step_y, gtk.gdk.INTERP_BILINEAR)
                    self.drawing.window.draw_pixbuf(gc, pb2, 0, 0, new_pos_x, new_pos_y, new_step_x, new_step_y)
                else:
                    self.drawing.window.draw_pixbuf(gc, pb, 0, 0, pos_x, pos_y, step_x, step_y)

            except:
                traceback.print_exc()

        gobject.timeout_add(1000, self.monitor_mcast)

    def monitor_bcast(self):
        """Monitors broadcast teacher status"""
        if self.bcast.has_msgs():
            data, source = self.bcast.get_msg()
            # if there is an announce, but we are not yet logged in, skip
            if not self.name:
                print "ERROR: found teacher, but not yet logged in!"
            else:
                msg = self.protocol.parse_header(data)
                name, flags = self.protocol.parse_announce(msg)
                # TODO: support multiple teachers
                if not self.teacher:
                    # register on teacher
                    ret, params = self.send_command(protocol.REQUEST_REGISTER, {"name": self.name}, teacher=source)
                    if ret == "registered":
                        # registered successfully
                        self.teacher = name
                        self.teacher_addr = source
                        self.connect_to_teacher(self.teacher)
                    elif ret == "rejected":
                        print "rejected by teacher"
                    else:
                        print "Unknown answer: %s" % ret

                elif self.teacher != name:
                    print "ERROR: Multiple teachers not yet supported"
                else:
                    # same teacher
                    pass
        gobject.timeout_add(1000, self.monitor_bcast)

    def log(self, text):
        """Logs something somewhere"""
        print text

if __name__ == "__main__":
    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(5)
    # Atualizando a lista de interfaces
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()

    # notification
    pynotify.init("OpenClass student")

    print _("Starting GUI..")
    gui = Student("iface/student.glade")
    try:
        gui.log(_("\nWelcome to OpenClass Student!!\n\n"))
        gtk.main()
        gtk.gdk.threads_leave()
    except:
        print "exiting.."
        sys.exit()
