#!/usr/bin/python
"""
OpenClass teacher module.

Copyright, (C) Eugeni Dodonov <eugeni@dodonov.net>, 2008-2011

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

import sys
import traceback
import time

import socket
import struct

import os
import logging
import gtk
import pygtk
import gobject
from gtk import gdk
import pynotify

from multiprocessing import Queue
import SocketServer
import socket
import urllib
from threading import Thread

import gettext
import __builtin__
__builtin__._ = gettext.gettext

try:
    gettext.install("openclass")
except IOError:
    _ = str
    traceback.print_exc()

MACHINES_X = 5
MACHINES_Y = 8

# configuration
from openclass import network, system, protocol, screen

# helper functions

# {{{ TeacherRunner
class TeacherRunner(Thread):
    selected_machines = 0
    """Teacher service"""
    def __init__(self):
        """Initializes the teacher thread"""
        Thread.__init__(self)

        # actions
        self.actions = Queue()

        # connected machines
        self.clients = []

        # actions for clients
        self.clients_actions = {}

        # authorized files for transfer
        self.authorized_files = []

        # protocol
        self.protocol = protocol.Protocol()

        # listening server
        self.server = network.HTTPListener(self)

        # broadcast sender
        self.bcast = None

        # multicast sender
        self.mcast = network.McastSender()

    def process_request(self, client, request, params):
        """Gets pending actions for a client"""
        print "Processing requests for %s (%s)" % (client, request)
        print request
        response = None
        response_params = None
        if request == protocol.REQUEST_REGISTER:
            # registering
            if "name" in params:
                name = params["name"][0]
            else:
                name = client
            print "Registering %s (%s)" % (client, name)
            print params
            self.add_client(client, name)
            response = "registered"
            self.clients.append(client)
            print self.clients
        elif request == protocol.REQUEST_ACTIONS:
            print self.clients
            if client not in self.clients:
                # not registered yet
                response = protocol.ACTION_PLEASEREGISTER
            else:
                # checking actions for the client
                response = self.gui.current_action
                if client in self.clients_actions:
                    if len(self.clients_actions[client]) > 0:
                        print len(self.clients_actions[client])
                        response, response_params = self.clients_actions[client].pop(0)
                        print len(self.clients_actions[client])
        elif request == protocol.REQUEST_RAISEHAND:
            # student raised his hand
            print "Student called your attention"
            print request
            print params
            self.raise_hand(client)
        elif request == protocol.REQUEST_SHOWSCREEN:
            # student wants to show his screen
            print "Student wants to show his screen to you"
            try:
                width = int(params["width"][0])
                height = int(params["height"][0])
                shot = params["shot"][0]
                self.gui.show_screenshot(client, width, height, shot)
            except:
                traceback.print_exc()
        elif request == protocol.REQUEST_GETFILE:
            if 'file' not in params:
                response = _("Bad request for file")
            else:
                filename = urllib.unquote(params['file'][0])
                print "Asked to open %s" % filename
                if filename not in self.authorized_files:
                    print "Error: %s not authorized for transfer to %s" % (filename, client)
                    response = _("File not authorized for transfer")
                else:
                    try:
                        with open(filename) as fd:
                            response = fd.read()
                            response_params = ""
                    except:
                        response = _("Unable to transfer %s: %s") % (filename, sys.exc_value)
        return response, response_params

    def quit(self):
        """Tells everything to quit"""
        self.actions.put(("quit", None))
        if self.bcast:
            self.bcast.actions.put(1)
        self.mcast.quit()
        self.server.actions.put(1)

    def set_gui(self, gui):
        """Associates a GUI to this service"""
        self.gui = gui

    def add_client(self, client, name):
        """Adds a new client"""
        self.gui.add_client(client, name)
        self.add_client_action(client, protocol.ACTION_NOOP)

    def raise_hand(self, client, message=_("The student asks for your attention")):
        """Calls teacher attention"""
        self.gui.queue_raise_hand(client, message)

    def add_client_action(self, client, action, params=None):
        """Adds an action for a client into a list"""
        if client not in self.clients_actions:
            self.clients_actions[client]=[]
        self.clients_actions[client].append((action, params))

    def authorize_file_transfer(self, filename):
        """Authorizes a local file for sharing with students"""
        self.authorized_files.append(filename)

    def start_multicast(self):
        """Starts multicast thread"""
        self.mcast.start()

    def start_broadcast(self, class_name):
        """Start broadcasting service"""
        self.bcast = network.BcastSender(network.LISTENPORT, self.protocol.create_announce(class_name))
        self.class_name = class_name
        self.bcast.start()

    def send_projection(self, width, height, fullscreen, chunks):
        """Send chunks of projection over multicast"""
        for chunk in chunks:
            self.mcast.put(self.protocol.pack_chunk(width, height, fullscreen, chunk))

    def run(self):
        """Starts a background thread"""
        while 1:
            action = self.actions.get()
            if not action:
                continue
            # chegou ALGO
            name, parameters = action
            print "Running %s" % name
            if name == "quit":
                return
            else:
                print "Unknown action %s" % name
# }}}

# {{{ TeacherGui
class TeacherGui:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, service):
        """Initializes the interface"""
        # internal variables
        self.class_name = None
        self.bcast = None
        self.clients_queue = Queue()
        self.service = service
        self.service.set_gui(self)
        # colors
        self.color_normal = gtk.gdk.color_parse("#99BFEA")
        self.color_active = gtk.gdk.color_parse("#FFBBFF")
        self.color_background = gtk.gdk.color_parse("#FFFFFF")

        # building the interface
        self.window = gtk.Window()
        self.window.set_resizable(False)
        self.window.set_default_size(800, 600)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.set_title(_("OpenClass Teacher"))
        self.window.connect('destroy', self.quit)

        # main layout
        MainLayout = gtk.Fixed()
        MainLayout.set_property("width_request", 640)
        MainLayout.set_property("height_request", 480)
        self.window.add(MainLayout)

        MenuVBox = gtk.VBox()
        MenuVBox.set_property("width_request", 160)
        MenuVBox.set_property("height_request", 520)
        MainLayout.put(MenuVBox, 10, 20)
        self.SendScreen = gtk.Button(_("Send Screen"))
        self.SendScreen.connect('clicked', self.send_screen)
        MenuVBox.pack_start(self.SendScreen, False, False, 5)

        self.LockScreen = gtk.Button(_("Lock Screens"))
        self.LockScreen.connect('clicked', self.lock_screen)
        MenuVBox.pack_start(self.LockScreen, False, False, 5)

        self.ShareFile = gtk.Button(_("Share files"))
        self.ShareFile.connect('clicked', self.share_files)
        MenuVBox.pack_start(self.ShareFile, False, False, 5)

        self.ShareFile = gtk.Button(_("Share a web page"))
        self.ShareFile.connect('clicked', self.share_url)
        MenuVBox.pack_start(self.ShareFile, False, False, 5)

        MenuVBox.pack_start(gtk.Label(), False, False, 120)

        self.QuitButton = gtk.Button(_("Quit"))
        self.QuitButton.connect('clicked', self.quit)
        MenuVBox.pack_start(self.QuitButton, False, False, 5)

        # scrolling machine view
        MachinesScrollWindow = gtk.ScrolledWindow()
        MachinesScrollWindow.set_property("width_request", 580)
        MachinesScrollWindow.set_property("height_request", 520)
        MainLayout.put(MachinesScrollWindow, 200, 30)

        self.MachineLayout = gtk.Layout()
        MachinesScrollWindow.add(self.MachineLayout)

        # screenshot view
        self.shot_window = gtk.Window()
        self.shot_window.set_title(_("Student view"))
        self.shot_window.connect('destroy', lambda *w: self.shot_window.hide())
        vbox = gtk.VBox()
        self.shot_window.add(vbox)
        hbox = gtk.HBox()
        vbox.pack_start(hbox, False, False)
        self.shot_label = gtk.Label()
        hbox.pack_start(self.shot_label, False, False)

        self.shot_refresh = gtk.Button(_("Refresh"))
        self.shot_refresh.connect('clicked', self.refresh_shot)
        # mark currently refreshed client
        self.shot_refresh.current_client = None
        hbox.pack_start(self.shot_refresh)

        button = gtk.Button(_("Close"))
        button.connect('clicked', lambda *w: self.shot_window.hide())
        hbox.pack_start(button)

        self.shot_drawing = gtk.Image()
        vbox.pack_start(self.shot_drawing)


        # tooltips
        self.tooltip = gtk.Tooltips()

        # Muda o background
        self.window.modify_bg(gtk.STATE_NORMAL, self.color_background)
        self.MachineLayout.modify_bg(gtk.STATE_NORMAL, self.color_background)

        # Inicializa a matriz de maquinas
        self.machine_layout = [None] * MACHINES_X
        for x in range(0, MACHINES_X):
            self.machine_layout[x] = [None] * MACHINES_Y

        self.machines = {}
        self.machines_map = {}

        # Mostra as maquinas
        self.MachineLayout.show_all()

        # inicializa o timestamp
        self.curtimestamp = 0

        # maquinas de estados
        self.current_action = protocol.ACTION_NOOP

        # projection screen
        self.projection_screen = screen.Screen()
        self.projection_width = None
        self.projection_height = None

        # Configura os timers
        # monitora os eventos
        gobject.timeout_add(1000, self.monitor)
        # monitora a projecao
        gobject.timeout_add(500, self.projection)

        self.window.show_all()

        self.login()

    def show_screenshot(self, client, width, height, shot):
        """Show a screenshot for a client"""
        print "Adding %s" % client
        self.clients_queue.put(("shot", client, {"width": width, "height": height, "shot": shot}))

    def login(self):
        """Asks teacher to login"""
        dialog = gtk.Dialog(_("Login"), self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK)
                )
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name (teacher or class name):"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(system.get_user_name())
        hbox.pack_start(entry_login)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.class_name = entry_login.get_text()
            print "Login: %s" % self.class_name
            dialog.destroy()
            # Starting broadcasting service
            self.service.start_broadcast(self.class_name)
            self.service.start_multicast()
            self.service.server.start()
            return True
        else:
            dialog.destroy()
            sys.exit(0)
            print "leaving.."
            return None

    def ask_resolution(self, title=_("Please select screen size for projection")):
        """Determines resolution of screen projection"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(title, self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(title)
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        combobox = gtk.combo_box_new_text()
        combobox.append_text(_("Full screen size"))
        for res in screen.RESOLUTIONS:
            combobox.append_text(res)
        combobox.set_active(0)
        dialog.vbox.add(combobox)
        dialog.show_all()
        response = dialog.run()
        # desired width and hight
        width = self.projection_screen.width
        height = self.projection_screen.height
        if response == gtk.RESPONSE_OK:
            exp = combobox.get_active_text()
            print exp
            dialog.destroy()
            fullscreen = 0
            if exp != _("Full screen size"):
                try:
                    width, height = exp.split("x", 1)
                    width = int(width)
                    height = int(height)
                except:
                    traceback.print_exc()
            else:
                    fullscreen = 1
            self.projection_width = width
            self.projection_height = height
            self.projection_fullscreen = fullscreen
            return True
        else:
            dialog.destroy()
            return None

    def question(self, title, input=None):
        """Asks a question :)"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(_("Question"), self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(title)
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        if input:
            entry = gtk.Entry()
            entry.set_text(input)
            dialog.vbox.add(entry)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            res = entry.get_text()
            dialog.destroy()
            if res:
                return res
            else:
                return True
        else:
            dialog.destroy()
            return None

    def show_message(self, title, message, timeout=0):
        """Shows a message to student"""
        n = pynotify.Notification(title, message)
        n.set_timeout(timeout)
        n.show()
        return

    def add_client(self, client, name):
        """Adds a new client"""
        print "Adding %s" % client
        self.clients_queue.put(("new", client, {"name": name}))

    def queue_raise_hand(self, client, message):
        """A student calls for attention"""
        print "Student %s asks for attention: %s" % (client, message)
        self.clients_queue.put(("raisehand", client, {"message": message}))

    def put_machine(self, machine):
        """Puts a client machine in an empty spot"""
        for y in range(0, MACHINES_Y):
            for x in range(0, MACHINES_X):
                if not self.machine_layout[x][y]:
                    self.machine_layout[x][y] = machine
                    self.MachineLayout.put(machine, x * 70, y * 65)
                    machine.machine_x = x
                    machine.machine_y = y
                    return
        print "Not enough layout space to add a machine!"

    def projection(self):
        """Grabs the screen for multicast projection when needed"""
        if self.current_action == protocol.ACTION_PROJECTION:
            print "Sending screens, yee-ha!"
            # we are projecting, grab stuff
            chunks = self.projection_screen.chunks(scale_x=self.projection_width, scale_y=self.projection_height)
            self.service.send_projection(self.projection_width, self.projection_height, self.projection_fullscreen, chunks)
        gobject.timeout_add(500, self.projection)

    def refresh_shot(self, widget):
        """Refreshes a screenshot"""
        self.service.add_client_action(self.shot_refresh.current_client, protocol.ACTION_SHOT)

    def show_screenshot(self, client, width, height, shot):
        """Displays a student screenshot"""
        self.shot_window.resize(width, height)
        self.shot_label.set_text(_("Viewing display of %s") % client)
        self.shot_refresh.current_client = client

        loader = gdk.PixbufLoader(image_type="jpeg")
        loader.write(shot)
        loader.close()
        pb = loader.get_pixbuf()

        self.shot_drawing.set_from_pixbuf(pb)

        self.shot_window.show_all()

    def monitor(self):
        """Monitors new machines connections"""
        while not self.clients_queue.empty():
            action, addr, params = self.clients_queue.get()
            if action == "new":
                # adding a new machine
                if addr not in self.machines:
                    # Maquina nova
                    gtk.gdk.threads_enter()
                    name = params.get("name", addr)
                    machine = self.mkmachine(name)
                    machine.button.connect('button_press_event', self.cb_machine, machine)
                    self.put_machine(machine)
                    self.machines[addr] = machine
                    self.machines_map[machine] = addr
                    machine.show_all()
                    gtk.gdk.threads_leave()
                else:
                    machine = self.machines[addr]
                    self.tooltip.set_tip(machine, _("Updated on %s") % (time.asctime()))
            elif action == "shot":
                # show a student screenshot
                width = params["width"]
                height = params["height"]
                shot = params["shot"]

                self.show_screenshot(addr, width, height, shot)
            elif action == "raisehand":
                message = params["message"]
                # shows a raisehand request from students
                name = addr
                if addr in self.machines:
                    name = self.machines[addr].machine
                self.show_message(_("Message received from %s") % name, message, timeout=0)

        gobject.timeout_add(1000, self.monitor)

    def set_offline(self, machine, message=None):
        """Marks a machine as offline"""
        if machine not in self.machines:
            print "Error: machine %s not registered!" % machine
            return
        gtk.gdk.threads_enter()
        self.machines[machine].button.set_image(self.machines[machine].button.img_off)
        if message:
            self.tooltip.set_tip(self.machines[machine], _("%s\%s!") % (time.asctime(), message))
        gtk.gdk.threads_leave()

    def send_screen(self, widget):
        """Starts screen sharing for selected machines"""
        machines = self.get_selected_machines()
        print "Sending screen to %s" % machines
        if self.current_action != protocol.ACTION_PROJECTION:
            print "Sending screens"
            res = self.ask_resolution()
            if not res:
                return
            self.SendScreen.set_label(_("Stop sending screen"))
            self.current_action = protocol.ACTION_PROJECTION
            self.LockScreen.set_sensitive(False)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_PROJECTION)
        else:
            print "Stopping sending screens"
            self.SendScreen.set_label(_("Send Screen"))
            self.current_action = protocol.ACTION_NOOP
            self.LockScreen.set_sensitive(True)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_NOOP)

    def share_url(self, widget):
        """Shares an URL with students"""
        url = self.question(_("Share a web page with students"), "http://")
        if not url:
            return
        machines = self.get_selected_machines()
        for machine in machines:
            self.service.add_client_action(machine, protocol.ACTION_OPENURL, url)

    def share_files(self, widget):
        """Shares a file with students"""
        chooser = gtk.FileChooserDialog(title=_("Select a file to share with students"),action=gtk.FILE_CHOOSER_ACTION_OPEN,
                      buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
        response = chooser.run()
        if response != gtk.RESPONSE_OK:
            chooser.destroy()
            return
        filename = chooser.get_filename()
        self.service.authorize_file_transfer(filename)
        chooser.destroy()
        machines = self.get_selected_machines()
        for machine in machines:
            self.service.add_client_action(machine, protocol.ACTION_OPENFILE, filename)

    def lock_screen(self, widget):
        """Starts screen locking for selected machines"""
        machines = self.get_selected_machines()
        print "Locking screen on %s" % machines
        if self.current_action != protocol.ACTION_ATTENTION:
            print "Locking screens"
            self.LockScreen.set_label(_("Stop locking screen"))
            self.current_action = protocol.ACTION_ATTENTION
            self.SendScreen.set_sensitive(False)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_ATTENTION)
        else:
            print "Stopping locking screens"
            self.LockScreen.set_label(_("Lock Screen"))
            self.current_action = protocol.ACTION_NOOP
            self.SendScreen.set_sensitive(True)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_NOOP)

    def get_selected_machines(self):
        """Returns the list of all selected machines"""
        machines = []
        for z in self.machines:
            machine = self.machines[z]
            img = machine.button.get_image()
            if img == machine.button.img_on:
                machines.append(z)
        return machines

    def quit(self, widget):
        """Main window was closed"""
        print "Closing pending threads.."
        self.service.quit()
        gtk.main_quit()
        print "done"

    def get_img(self, imgpath):
        """Returns image widget if exists"""
        try:
            fd = open(imgpath)
            fd.close()
            img = gtk.Image()
            img.set_from_file(imgpath)
        except:
            img=None
        return img

    def mkmachine(self, name, img="machine.png", img_offline="machine_off.png", status="online"):
        """Creates a client representation"""
        box = gtk.VBox(homogeneous=False)

        imgpath = "iface/%s" % (img)
        imgpath_off = "iface/%s" % (img_offline)

        img = self.get_img(imgpath)
        img_off = self.get_img(imgpath_off)

        button = gtk.Button()
        button.img_on = img
        button.img_off = img_off
        button.machine = name
        if status=="online":
            button.set_image(button.img_on)
        else:
            button.set_image(button.img_off)
        box.pack_start(button, expand=False)

        label = gtk.Label(_("name"))
        label.set_use_markup(True)
        label.set_markup("<small>%s</small>" % name)
        box.pack_start(label, expand=False)

        self.tooltip.set_tip(box, name)
#        box.set_size_request(52, 52)

        # Sets private variables
        box.machine = name
        box.button = button
        box.label = label
        box.wifi = None
        return box

    def send_msg_student(self, widget, machine):
        """Send a message to student"""
        if machine in self.machines_map:
            addr = self.machines_map[machine]
            message = self.question(_("Send a message to student"), _("Please, pay attention!"))
            if not message:
                return
            print "Will send: %s" % message
            self.service.add_client_action(addr, protocol.ACTION_MSG, message)
        else:
            print "Unknown machine!"

    def request_screenshot(self, widget, machine):
        """Request screenshot from student"""
        if machine in self.machines_map:
            addr = self.machines_map[machine]
            self.service.add_client_action(addr, protocol.ACTION_SHOT)
            print "Sending request to %s" % addr
        else:
            print "Unknown machine!"

    def cb_machine(self, widget, event, machine):
        """Callback when clicked on a client machine"""
        # popup menu
        popup_menu = gtk.Menu()
        menu_msg = gtk.MenuItem(_("Send message to student"))
        menu_msg.connect("activate", self.send_msg_student, machine)
        popup_menu.append(menu_msg)

        menu_view = gtk.MenuItem(_("View student screen"))
        menu_view.connect("activate", self.request_screenshot, machine)
        popup_menu.append(menu_view)

        menu_control = gtk.MenuItem(_("Remote control student computer"))
        menu_control.set_sensitive(False)
        popup_menu.append(menu_control)

        menu_disconnect = gtk.MenuItem(_("Remove student from class"))
        menu_disconnect.set_sensitive(False)
        popup_menu.append(menu_disconnect)

        popup_menu.show_all()
        popup_menu.popup(None, None, None, event.button, event.time)
        return
# }}}

if __name__ == "__main__":
    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(2)
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    print _("Starting broadcast..")
    # Main service service
    service = TeacherRunner()
    # Main interface
    gui = TeacherGui(service)
    service.start()

    # notification
    pynotify.init("OpenClass teacher")

    print _("Starting main loop..")
    gtk.main()
    gtk.gdk.threads_leave()
