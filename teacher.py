#!/usr/bin/python
"""
Teacher GUI using GLADE
"""

# TODO: detectar quando conexoes nao sao estabelecidas
# TODO: tirar redundancias entre multicast e broadcast

import sys
import traceback
import time

import socket
import struct

import os
import logging
import gtk
import gtk.glade
import pygtk
import gobject

from multiprocessing import Queue
import SocketServer
import socket
from threading import Thread

import gettext
import __builtin__
__builtin__._ = gettext.gettext

MACHINES_X = 8
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

        # connected machines
        self.machines = []

        # actions
        self.actions = Queue()

        # actions for clients
        self.clients_actions = {}

        # protocol
        self.protocol = protocol.Protocol()

        # listening server
        self.server = network.HTTPListener(self)

        # broadcast sender
        self.bcast = None

        # multicast sender
        self.mcast = network.McastSender()

    def process_request(self, client, request, params, seqno):
        """Gets pending actions for a client, starting with seqno"""
        print "Processing requests for %s (%s)" % (client, request)
        print request
        if request == "/register":
            # registering
            if "name" in params:
                name = params["name"][0]
            else:
                name = client
            print "Registering %s (%s)" % (client, name)
            print params
            self.add_client(client, name)
            return "registered"
        elif request == "/actions":
            # checking actions for the client
            if client not in self.clients_actions:
                return protocol.ACTION_NOOP
            else:
                return self.clients_actions[client]

    def quit(self):
        """Tells everything to quit"""
        self.actions.put(("quit", None))
        if self.bcast:
            self.bcast.actions.put(1)
        self.server.actions.put(1)

    def set_gui(self, gui):
        """Associates a GUI to this service"""
        self.gui = gui

    def add_client(self, client, name):
        """Adds a new client"""
        self.gui.add_client(client, name)
        self.add_client_action(client, protocol.ACTION_NOOP)

    def add_client_action(self, client, action):
        """Adds an action for a client into a list"""
        # TODO: implement seqnos
        self.clients_actions[client] = action

    def start_broadcast(self, class_name):
        """Start broadcasting service"""
        self.bcast = network.BcastSender(network.LISTENPORT, self.protocol.create_announce(class_name))
        self.class_name = class_name
        self.bcast.start()

    def send_projection(self, width, height, chunks):
        """Send chunks of projection over multicast"""
        for chunk in chunks:
            self.mcast.send(self.protocol.pack_chunk(width, height, chunk))

    def run(self):
        """Starts a background thread"""
        while 1:
            action = self.actions.get()
            if not action:
                continue
            # chegou ALGO
            name, parameters = action
            print "Running %s" % name
            if name == "multicast":
                machines, num_msgs, bandwidth = parameters
                self.multicast(machines, num_msgs, bandwidth, type="broadcast")
            elif name == "quit":
                return
            else:
                print "Unknown action %s" % name
# }}}

# {{{ TeacherGui
class TeacherGui:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, guifile, service):
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

        self.wTree = gtk.glade.XML(guifile)

        # Callbacks
        dic = {
                "on_MainWindow_destroy": self.on_MainWindow_destroy # fecha a janela principal
                }
        self.wTree.signal_autoconnect(dic)

        # tooltips
        self.tooltip = gtk.Tooltips()

        # Muda o background
        self.MainWindow.modify_bg(gtk.STATE_NORMAL, self.color_background)
        self.MachineLayout.modify_bg(gtk.STATE_NORMAL, self.color_background)

        # Configura os botoes
        self.QuitButton.connect('clicked', self.on_MainWindow_destroy)
        self.SelectAllButton.connect('clicked', self.select_all)
        self.UnselectAllButton.connect('clicked', self.unselect_all)
        self.SendScreen.connect('clicked', self.send_screen)
        #self.StopCapture.connect('clicked', self.stop_capture)
        #self.BandwidthButton.connect('clicked', self.bandwidth)
        #self.MulticastButton.connect('clicked', self.multicast)
        #self.BroadcastButton.connect('clicked', self.multicast, "broadcast")
        #self.AnalyzeButton.connect('clicked', self.analyze)

        # Inicializa a matriz de maquinas
        self.machine_layout = [None] * MACHINES_X
        for x in range(0, MACHINES_X):
            self.machine_layout[x] = [None] * MACHINES_Y

        self.machines = {}

        # Mostra as maquinas
        self.MachineLayout.show_all()

        # inicializa o timestamp
        self.curtimestamp = 0

        # maquinas de estados
        self.projection_running = False
        self.projection_screen = screen.Screen()

        # Configura os timers
        # monitora os eventos
        gobject.timeout_add(1000, self.monitor)
        # monitora a projecao
        gobject.timeout_add(500, self.projection)

        self.login()

    def login(self):
        """Asks teacher to login"""
        dialog = gtk.Dialog(_("Login"), self.MainWindow, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name (teacher or class name):"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(_("My name"))
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
            self.service.server.start()
            return True
        else:
            dialog.destroy()
            return None

    def question(self, title, input=None):
        """Asks a question :)"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(_("Question"), self.MainWindow, 0,
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
            dialog.destroy()
            if input:
                return entry.get_text()
            else:
                return True
        else:
            dialog.destroy()
            return None

    def add_client(self, client, name):
        """Adds a new client"""
        print "Adding %s" % client
        self.clients_queue.put(("new", client, {"name": name}))

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
        if self.projection_running == True:
            print "Sending screens, yee-ha!"
            # we are projecting, grab stuff
            chunks = self.projection_screen.chunks()
            self.service.send_projection(self.projection_screen.width, self.projection_screen.height, chunks)
        gobject.timeout_add(500, self.projection)

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
                    machine.button.connect('clicked', self.cb_machine, machine)
                    self.put_machine(machine)
                    self.machines[addr] = machine
                    machine.show_all()
                    self.StatusLabel.set_text("Found %s (%d machines connected)!" % (addr, len(self.machines)))
                    gtk.gdk.threads_leave()
                else:
                    machine = self.machines[addr]
                    self.tooltip.set_tip(machine, _("Updated on %s" % (time.asctime())))

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

    def multicast(self, widget, type="multicast"):
        """Inicia transmissao de multicast"""
        print "Bandwidth to estimate: %s Kbps" % (bandwidth)

        machines = []
        for z in self.machines:
            img = self.machines[z].button.get_image()
            if img == self.machines[z].button.img_on:
                machines.append(z)

        self.service.actions.put((type, (machines, num_msgs, bandwidth)))

    def send_screen(self, widget):
        """Starts screen sharing for selected machines"""
        machines = self.get_selected_machines()
        print "Sending screen to %s" % machines
        if self.projection_running == False:
            print "Sending screens"
            self.SendScreen.set_label(_("Stop sending screen"))
            self.projection_running = True
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_PROJECTION)
        else:
            print "Stopping sending screens"
            self.SendScreen.set_label(_("Send Screen"))
            self.projection_running = False
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

    def select_all(self, widget):
        """Selects all machines"""
        for z in self.machines.values():
            z.button.set_image(z.button.img_on)

    def unselect_all(self, widget):
        """Selects all machines"""
        for z in self.machines.values():
            z.button.set_image(z.button.img_off)

    def __getattr__(self, attr):
        """Requests an attribute from Glade"""
        obj = self.wTree.get_widget(attr)
        if not obj:
            return None
        else:
            return obj

    def on_MainWindow_destroy(self, widget):
        """Main window was closed"""
        gtk.main_quit()
        print "Closing pending threads.."
        self.service.quit()

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

    def cb_machine(self, widget, machine):
        """Callback when clicked on a client machine"""
        img = machine.button.get_image()
        if img == machine.button.img_off:
            machine.button.set_image(machine.button.img_on)
        else:
            machine.button.set_image(machine.button.img_off)

        # muda o texto

    def mkbutton(self, img, img2, text, action, color_normal, color_active):
        """Creates a callable button"""
        box = gtk.HBox(homogeneous=False)
        # Imagem 1
        imgpath = "%s/%s" % (self.appdir, img)
        # Verifica se arquivo existe
        try:
            fd = open(imgpath)
            fd.close()
        except:
            imgpath=None
        if imgpath:
            img = gtk.Image()
            img.set_from_file(imgpath)
            box.pack_start(img, expand=False)

        # Verifica se arquivo existe
        try:
            fd = open(imgpath)
            fd.close()
        except:
            imgpath=None
        if imgpath:
            img2 = gtk.Image()
            img2.set_from_file(imgpath)

        # Texto
        label = gtk.Label(text)
        label.set_use_markup(True)
        label.set_markup("<b>%s</b>" % text)
        box.pack_start(label, expand=False)

        button = gtk.Button()
        button.modify_bg(gtk.STATE_NORMAL, color_normal)
        button.modify_bg(gtk.STATE_PRELIGHT, color_active)

        button.add(box)

        # callback
        if action:
            button.connect('clicked', action, "")
        button.show_all()
        return button
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
    gui = TeacherGui("iface/teacher.glade", service)
    service.start()

    print _("Starting main loop..")
    gtk.main()
    gtk.gdk.threads_leave()
