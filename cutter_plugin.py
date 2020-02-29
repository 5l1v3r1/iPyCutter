# -*- encoding: utf8 -*-
#
# IDA plugin definition.
#
# Copyright (c) 2015-2018 ESET
# Author: Marc-Etienne M.Léveillé <leveille@eset.com>
# See LICENSE file for redistribution.

import cutter
from ipycutter import cutter_qtconsole, kernel
from PySide2.QtCore import QObject, SIGNAL
from PySide2.QtWidgets import QAction, QLabel





class InitializeIPyCutter(cutter.CutterPlugin):
    name = "IPyCutter"
    description = "Starts an IPython qtconsole in Cutter!"
    version = "1.0"
    author = "TODO"

    def setupPlugin(self):
        print ("[2] inside setupPlugin")
        self.kernel = kernel.IPythonKernel()
        self.widget = None
        
        if not self.kernel.started:
            self.kernel.start()

    def setupInterface(self, main):
        print ("[9] inside setupInterface")

        if self.widget is None:
            action = QAction("IPyCutter", main)
            action.setCheckable(True)

            self.widget = cutter_qtconsole.IPythonConsole(self.kernel.connection_file, main, action)
            self.widget.create()
            main.addPluginDockWidget(self.widget, action)
        self.widget.show()
    
        


    def terminate(self):
        if self.widget:
            self.widget.Close(0)
            self.widget = None
        if self.kernel:
            self.kernel.stop()

def ipycutterplugin():
    print ("[1] inside ipycutterplugin")
    return InitializeIPyCutter()


