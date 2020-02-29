# -*- encoding: utf8 -*-
#
# This module allows an IPython to be embeded inside IDA.
# You need the IPython module to be accessible from IDA for this to work.
# See README.adoc for more details.
#
# Copyright (c) 2015-2018 ESET
# Author: Marc-Etienne M.Léveillé <leveille@eset.com>
# See LICENSE file for redistribution.

from PySide2 import QtCore

from ipykernel.kernelapp import IPKernelApp
import IPython.utils.frame
import ipykernel.iostream

_cutter_ipython_qtimer = None
import sys
import os 

# The IPython kernel will override sys.std{out,err}. We keep a copy to let the
# existing embeded IDA console continue working, and also let IPython output to
# it.
_cutter_stdout = sys.stdout
_cutter_stderr = sys.stderr

# Path to a file to load into the kernel's namespace during its creation.
# Similar to the idapythonrc.py file.

if sys.__stdout__ is None or sys.__stdout__.fileno() < 0:
    # IPython insist on using sys.__stdout__, however it's not available in IDA
    # on Windows. We'll replace __stdout__ to the "nul" to avoid exception when
    # writing and flushing on the bogus file descriptor.
    sys.__stdout__ = open(os.devnull, "w")

# IPython will override sys.excepthook and send exception to sys.__stderr__. IDA
# expect exception to be written to sys.stderr (overridden by IDA) to print them
# in the console window. Used by wrap_excepthook.
_ida_excepthook = sys.excepthook

class CutterTeeOutStream(ipykernel.iostream.OutStream):

    def write(self, string):
        "Write on both the previously saved Cutter std output and zmq's stream"
        if self.name == "stdout" and _cutter_stdout:
            _cutter_stdout.write(string)
        elif self.name == "stderr" and _cutter_stderr:
            _cutter_stderr.write(string)
        super(self.__class__, self).write(string)

def wrap_excepthook(ipython_excepthook):
    """
    Return a function that will call both the ipython kernel execepthook
    and IDA's
    """
    def ipyida_excepthook(*args):
        _ida_excepthook(*args)
        ipython_excepthook(*args)
    return ipyida_excepthook

class IPythonKernel(object):
    def __init__(self):
        print ("[3] inside IPythonKernel init")
        self._cutter_ipython_qtimer = None
        self.connection_file = None
    
    def start(self):
        print ("[4] inside IPythonKernel start")

        if self._cutter_ipython_qtimer is not None:
            raise Exception("IPython kernel is already running.")

        # The IPKernelApp initialization is based on the IPython source for
        # IPython.embed_kernel available here:
        # https://github.com/ipython/ipython/blob/rel-3.2.1/IPython/kernel/zmq/embed.py
        if IPKernelApp.initialized():
            print ("[5] inside IPythonKernel check IPKernelApp.initialized")
            app = IPKernelApp.instance()
        else:
            print ("[6] inside IPythonKernel IPKernelApp not initialized")

            app = IPKernelApp.instance(
                outstream_class='ipycutter.kernel.CutterTeeOutStream'
            )
            app.initialize()
            print ("[7] inside IPythonKernel IPKernelApp after initialize")

            main = app.kernel.shell._orig_sys_modules_main_mod
            if main is not None:
                sys.modules[app.kernel.shell._orig_sys_modules_main_name] = main
        
            # IPython <= 3.2.x will send exception to sys.__stderr__ instead of
            # sys.stderr. IDA's console will not be able to display exceptions if we
            # don't send it to IDA's sys.stderr. To fix this, we call both the
            # ipython's and IDA's excepthook (IDA's excepthook is actually Python's
            # default).
            sys.excepthook = wrap_excepthook(sys.excepthook)
        print ("[8] inside IPythonKernel IPKernelApp after if-else for initializing")

        app.shell.set_completer_frame()

        app.kernel.start()
        app.kernel.do_one_iteration()
    
        self.connection_file = app.connection_file

        # Schedule the IPython kernel to run on the Qt main loop with a QTimer
        qtimer = QtCore.QTimer()

        # Use _poll_interval as docuementented here:
        # https://ipython.org/ipython-doc/dev/config/eventloops.html
        qtimer.setInterval(int(1000 * app.kernel._poll_interval))
        qtimer.timeout.connect(app.kernel.do_one_iteration)

        qtimer.start()

        # We keep tht qtimer in a global variable to this module to allow to
        # manually stop the kernel later with stop_ipython_kernel.
        # There's a second purpose: If there is no more reference to the QTimer,
        # it will get garbage collected and the timer will stop calling
        # kernel.do_one_iteration. Keep this in mind before removing this line.
        self._cutter_ipython_qtimer = qtimer

    def stop(self):
        if self._cutter_ipython_qtimer is not None:
            self._cutter_ipython_qtimer.stop()
        self._cutter_ipython_qtimer = None
        self.connection_file = None
        sys.stdout = _cutter_stdout
        sys.stderr = _cutter_stderr

    @property
    def started(self):
        return self._cutter_ipython_qtimer is not None

def do_one_iteration():
    print ("\n=====" +"D"*15)
    """Perform an iteration on IPython kernel runloop"""
    if IPKernelApp.initialized():
        app = IPKernelApp.instance()
        app.kernel.do_one_iteration()
    else:
        raise Exception("Kernel is not initialized")
