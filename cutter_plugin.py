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
        global _kernel
        _kernel = kernel.IPythonKernel()
        self.kernel = _kernel
        self.widget = None
        
        if not self.kernel.started:
            self.kernel.start()

    def setupInterface(self, main):
        if self.widget is None:
            self.widget = cutter_qtconsole.IPythonConsole(self.kernel.connection_file)
            self.widget.create()
            
            _kernel.start()

        
        action = QAction("IPyCutter", main)
        action.setCheckable(True)
        main.addPluginDockWidget(widget, action)


    def terminate(self):
        if self.widget:
            self.widget.Close(0)
            self.widget = None
        if self.kernel:
            self.kernel.stop()

def ipycutterplugin():
    return InitializeIPyCutter()


