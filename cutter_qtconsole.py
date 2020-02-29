# -*- encoding: utf8 -*-
#
# This module integreate a qtconsole to the IDA GUI.
# See README.adoc for more details.
#
# Copyright (c) 2015-2018 ESET
# Author: Marc-Etienne M.Léveillé <leveille@eset.com>
# See LICENSE file for redistribution.


from PySide2 import QtGui, QtWidgets
import cutter

import sys

# QtSvg binairies are not bundled with IDA. So we monkey patch PySide to avoid
# IPython to load a module with missing binary files. This *must* happend before
# importing RichJupyterWidget
# In the case of pyqt5, we have to avoid patch the binding detection too.

# import qtconsole.qt_loaders
# original_has_binding = qtconsole.qt_loaders.has_binding
# def hooked_has_bindings(arg):
#     if arg == 'pyqt5':
#         return True
#     else:
#         return original_has_binding(arg)
# qtconsole.qt_loaders.has_binding = hooked_has_bindings

import PySide2
PySide2.QtSvg = None
PySide2.QtPrintSupport = type("EmptyQtPrintSupport", (), {})


from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager
from qtconsole.client import QtKernelClient
from jupyter_client import find_connection_file
import ipycutter.kernel

class CutterRichJupyterWidget(RichJupyterWidget):
    def _is_complete(self, source, interactive):
        # The original implementation in qtconsole is synchronous. IDA Python is
        # single threaded and the IPython kernel runs on the same thread as the
        # UI so the is_complete request can never be processed by the kernel,
        # which results in always returning (False, '') and having to to
        # <Shift-Enter> to execute a command.
        #
        # Our solution here was to copy the original _is_complete and call the
        # kernel's do_one_iteration before expecting a reply. Original implemetation is in:
        # https://github.com/jupyter/qtconsole/blob/4.3.1/qtconsole/frontend_widget.py#L260
        print ("\n======= " + "2"*15)

        try:
            from queue import Empty
        except ImportError:
            from Queue import Empty
        kc = self.blocking_client
        if kc is None:
            self.log.warn("No blocking client to make is_complete requests")
            return False, u''
        msg_id = kc.is_complete(source)
        MAX_RETRY_COUNT = 5
        retry_count = 0
        is_complete_timeout = self.is_complete_timeout / float(MAX_RETRY_COUNT)
        while True:
            try:
                ipycutter.kernel.do_one_iteration()
                reply = kc.shell_channel.get_msg(block=True, timeout=is_complete_timeout)
            except Empty:
                ipycutter.kernel.do_one_iteration()
                if retry_count < MAX_RETRY_COUNT:
                    retry_count += 1
                    continue
                else:
                    # assume incomplete output if we get no reply in time
                    return False, u''
            if reply['parent_header'].get('msg_id', None) == msg_id:
                status = reply['content'].get('status', u'complete')
                indent = reply['content'].get('indent', u'')
                return status != 'incomplete', indent

_user_widget_options = {}

def set_widget_options(options):
    """"
    This function is intended to be called in ipyidarc.py to set additionnal
    options during the creation of if the RichJupyterWidget.

    Args: options is expected to be a dict

    See https://qtconsole.readthedocs.io/en/stable/config_options.html for a
    list of available options.
    """
    global _user_widget_options
    _user_widget_options = options.copy()

class IPythonConsole(cutter.CutterDockWidget):
    
    def __init__(self, connection_file, *args):
        print ("[10] inside IPythonConsole init")
        super(IPythonConsole, self).__init__(*args)
        self.connection_file = connection_file
    
    def create(self):
        print ("[11] inside IPythonConsole create")
        try:
            layout = self._createConsoleWidget()
            self.parent.setLayout(layout)
        except:
            import traceback
            print(traceback.format_exc())

    def _createConsoleWidget(self):
        print ("[12] inside IPythonConsole _createConsoleWidget")
        layout = QtWidgets.QVBoxLayout()

        connection_file = find_connection_file(self.connection_file)
        self.kernel_manager = QtKernelManager(connection_file=connection_file)
        self.kernel_manager.load_connection_file()
        self.kernel_manager.client_factory = QtKernelClient
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        widget_options = {}
        if sys.platform.startswith('linux'):
            # Some upstream bug crashes IDA when the ncurses completion is
            # used. I'm not sure where the bug is exactly (IDA's Qt5 bindings?)
            # but using the "droplist" instead works around the crash. The
            # problem is present only on Linux.
            # See: https://github.com/eset/ipyida/issues/8
            widget_options["gui_completion"] = 'droplist'
        widget_options.update(_user_widget_options)
        print ("[13] inside IPythonConsole before creating CutterRichJupyterWidget")

        class fake_font():
            def pointSize(self):
                return 16
        QtWidgets.QApplication.instance().font = fake_font

        self.ipython_widget = CutterRichJupyterWidget(self.parent, **widget_options)
        print ("[15] inside IPythonConsole after creating CutterRichJupyterWidget")


        self.ipython_widget.kernel_manager = self.kernel_manager
        self.ipython_widget.kernel_client = self.kernel_client
        layout.addWidget(self.ipython_widget)

        return layout


    def setFocusToPrompt(self):
        # This relies on the internal _control widget but it's the most reliable
        # way I found so far.
        if hasattr(self.ipython_widget, "_control"):
            self.ipython_widget._control.setFocus()
        else:
            print("[IPyIDA] setFocusToPrompt: Widget has no _control attribute.")

    def close(self, form):
        try:
            pass
        except:
            import traceback
            print(traceback.format_exc())

