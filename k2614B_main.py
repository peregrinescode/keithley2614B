#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
k2614B measurement main program linking gui and measurement thread.

Author:  Ross <ross dot warren at protonmail dot com>
"""

import program_GUI  # GUI
import k2614B_driver  # driver
import sys
import time
import numpy as np
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from math import ceil


class GUI(program_GUI.mainWindow):
    """GUI linked to measurement thread."""

    def __init__(self):
        """Take GUI and add measurement thread connection."""
        super().__init__()
        self.params = {}  # for storing parameters
        self.setupConnections()

    def setupConnections(self):
        """Connect the GUI to the measurement thread."""
        self.buttonWidget.ivBtn.clicked.connect(self.ivSweep)
        self.buttonWidget.readBuffer.clicked.connect(self.readBuffer)

    def ivSweep(self):
        """Perform IV sweep."""
        try:
            if self.buttonWidget.SampleName is None:
                raise AttributeError
            self.params["Sample name"] = self.buttonWidget.SampleName
            self.params["startV"] = self.buttonWidget.startV
            self.params["stopV"] = self.buttonWidget.stopV
            self.params["stepV"] = self.buttonWidget.stepV
            self.params["stepT"] = self.buttonWidget.stepT
            self.params["compl"] = self.buttonWidget.setCompliance
            self.statusbar.showMessage("Performing IV Sweep...")
            self.buttonWidget.hideButtons()
            self.params["Measurement"] = "iv-sweep"
            self.measureThread = measureThread(self.params)
            self.measureThread.finishedSig.connect(self.done)
            self.measureThread.start()
        except AttributeError or KeyError:
            self.popupWarning.showWindow("Sample name/parameter error!")

    def readBuffer(self):
        """Read from the buffer."""
        self.statusbar.showMessage("Attempting to read buffer...")
        self.bufferThread = bufferThread(self.params)
        self.bufferThread.finishedSig.connect(self.bufferDone)
        self.bufferThread.start()

    def done(self):
        """Update display when finished measurement."""
        self.statusbar.showMessage("Task complete.")
        # self.dislpayMeasurement()
        self.buttonWidget.showButtons()

    def bufferDone(self):
        """Update display when finished buffer reading."""
        saveFile = "data/" + str(self.params["Sample name"]) + "-iv.csv"
        self.statusbar.showMessage(f"Buffer saved as {saveFile}")
        # self.dislpayMeasurement()

    def error(self, message):
        """Raise error warning."""
        self.popupWarning.showWindow(str(message))
        self.statusbar.showMessage("Measurement error!")
        self.buttonWidget.hideButtons()

    def dislpayMeasurement(self):
        """Display the data on screen."""
        try:
            # IV sweep display
            if self.params["Measurement"] == "iv-sweep":
                df = pd.read_csv(
                    str(
                        self.params["Sample name"]
                        + "-"
                        + self.params["Measurement"]
                        + ".csv"
                    ),
                    "\t",
                )
                self.mainWidget.drawIV(df)

        except FileNotFoundError:
            self.popupWarning.showWindow("Could not find data!")


class measureThread(QThread):
    """Thread for running measurements."""

    finishedSig = pyqtSignal()
    errorSig = pyqtSignal(str)

    def __init__(self, params):
        """Initialise threads."""
        QThread.__init__(self)
        self.params = params

    def __del__(self):
        """When thread is deconstructed wait for porcesses to complete."""
        self.wait()

    def run(self):
        """Logic to be run in background thread."""
        try:
            address = "TCPIP[board]::192.168.0.2::inst0::INSTR"
            # address = "TCPIP[board]::169.254.0.2::inst0::INSTR"
            keithley = k2614B_driver.k2614B(address)

            vstart = self.params["startV"]
            vstop = self.params["stopV"]
            vstep = self.params["stepV"]
            compl = self.params["compl"]
            print(compl)
            numpoint = ((vstop - vstart) / vstep) + 1
        
            myvlist = np.linspace(vstart, vstop, num=numpoint)
            myvlist = np.append(myvlist, np.linspace(vstop - 1, vstart, num=numpoint - 1))
            #print(list(myvlist))
            stime = self.params["stepT"]
            points = len(myvlist)
        
            # Format for keithley to read
            myvlist = str(list(myvlist)).replace('[', '{').replace(']', '}')

            # Perform the sweep
            keithley.SweepVListMeasureI(myvlist, stime, points, compl)

            # Close Keithley connection
            keithley.closeConnection()
            
            # Emit a finish signal, does this even do anything atm?
            self.finishedSig.emit()
            
        except ConnectionError:
            self.errorSig.emit("No measurement made. Please retry.")
            self.quit()


class bufferThread(QThread):
    """Thread for running measurements."""

    finishedSig = pyqtSignal()
    errorSig = pyqtSignal(str)

    def __init__(self, params):
        """Initialise threads."""
        QThread.__init__(self)
        self.params = params

    def __del__(self):
        """When thread is deconstructed wait for porcesses to complete."""
        self.wait()

    def run(self):
        """Logic to be run in background thread."""
        try:
            address = "TCPIP[board]::192.168.0.2::inst0::INSTR"
            # address = "TCPIP[board]::169.254.0.2::inst0::INSTR"
            keithley = k2614B_driver.k2614B(address)
            df = keithley.readBuffer()
            print(df)
            save_file = "data/" + str(self.params["Sample name"]) + "-iv.csv"
            df.to_csv(
                save_file, index=False
            )
            print("----------------------------------------")
            print(f"Data saved: data/ {save_file}")
            print("----------------------------------------")

            keithley.closeConnection()
            self.finishedSig.emit()

        except ConnectionError:
            self.errorSig.emit("No measurement made. Please retry.")
            self.quit()

        except KeyError:
            self.errorSig.emit("No measurement made. Please retry.")
            self.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainGUI = GUI()
    sys.exit(app.exec_())
