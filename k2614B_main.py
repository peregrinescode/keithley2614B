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


class GUI(program_GUI.mainWindow):
    """GUI linked to measurement thread."""

    def __init__(self):
        """Take GUI and add measurement thread connection."""
        super().__init__()
        self.params = {}  # for storing parameters
        self.setupConnections()

    def setupConnections(self):
        """Connect the GUI to the measurement thread."""
        self.ivScanWidget.ivBtn.clicked.connect(self.ivSweep)
        self.ivScanWidget.readBuffer.clicked.connect(self.readBuffer)
        self.ivScanWidget.plotBtn.clicked.connect(self.dislpayMeasurement)

    def ivSweep(self):
        """Perform IV sweep."""
        # try:
        if self.ivScanWidget.SampleName is None:
            raise AttributeError
        self.params["Sample name"] = self.ivScanWidget.SampleName
        self.params["startV"] = self.ivScanWidget.startV
        self.params["stopV"] = self.ivScanWidget.stopV
        self.params["stepV"] = self.ivScanWidget.stepV
        self.params["stepT"] = self.ivScanWidget.stepT
        self.params["compl"] = self.ivScanWidget.setCompliance
        self.statusbar.showMessage("Performing IV Sweep...")
        self.ivScanWidget.hideButtons()
        self.params["Measurement"] = "iv-sweep"
        self.measureThread = measureThread(self.params)
        self.measureThread.progressSig.connect(self.update_progress_bar)
        self.measureThread.start()

        # except AttributeError or KeyError:
        #     self.popupWarning.showWindow("Sample name/parameter error!")

    def readBuffer(self):
        """Read from the buffer."""
        self.statusbar.showMessage("Attempting to read buffer...")
        self.bufferThread = bufferThread(self.params)
        self.bufferThread.bufferSig.connect(self.bufferDone)
        self.bufferThread.start()
        self.ivScanWidget.plotBtn.setEnabled(True)

    def update_progress_bar(self, percent):
        """Update display when finished measurement."""
        self.ivScanWidget.pbar.setValue(int(percent))
        if self.ivScanWidget.pbar.value() == 99:
            time.sleep(1)
            self.ivScanWidget.pbar.setValue(100)
            self.done()

    def done(self):
        """Update display when finished measurement."""
        self.statusbar.showMessage("Task complete.")
        # self.dislpayMeasurement()
        self.ivScanWidget.showButtons()

    def bufferDone(self, save_file):
        """Update display when finished buffer reading."""
        self.save_file = save_file
        self.statusbar.showMessage(f"Buffer saved as {save_file}")
        # self.dislpayMeasurement(save_file)

    def error(self, message):
        """Raise error warning."""
        self.popupWarning.showWindow(str(message))
        self.statusbar.showMessage("Measurement error!")
        self.ivScanWidget.hideButtons()

    def dislpayMeasurement(self):
        """Display the data on screen."""
        try:
            df = pd.read_csv(self.save_file)
            self.mainWidget.drawIV(df, sname="_noLabel")
            self.statusbar.showMessage(f"Plotted: {self.save_file}")


        except FileNotFoundError:
            self.popupWarning.showWindow("Could not find data!")


class measureThread(QThread):
    """Thread for running measurements."""

    progressSig = pyqtSignal(float)
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
            address = "TCPIP[board]::192.168.0.2::inst0::INSTR" #k2614B
            # address = "TCPIP[board]::192.100.10.2::inst0::INSTR" #k2635A
            keithley = k2614B_driver.k2614B(address)

            vstart = self.params["startV"]
            vstop = self.params["stopV"]
            numpoint = self.params["stepV"]
            compl = self.params["compl"]
            # numpoint = ((vstop - vstart) / vstep) + 1

            # Sweep in one direction
            myvlist = np.linspace(vstart, vstop, num=numpoint)

            # Sweep in other direction
            myvlist = np.append(myvlist, np.linspace(vstop - 1, vstart, num=numpoint - 1))
            
            stime = self.params["stepT"]
                    
            # Format for keithley to read
            myvlist = str(list(myvlist)).replace('[', '{').replace(']', '}')

            # Perform the sweep
            keithley.SweepVListMeasureI(myvlist, stime, numpoint, compl)

            # Close Keithley connection
            keithley.closeConnection()
            
            # Emit a finish signal, does this even do anything atm?
            for i in range(numpoint):
                time.sleep(stime*1.15)
                percent = (i / numpoint) * 100
                self.progressSig.emit(percent)

            self.finishedSig.emit()
            
        except ConnectionError:
            self.errorSig.emit("No measurement made. Please retry.")
            self.quit()

        except TypeError:
            self.errorSig.emit("No measurement made. Please retry.")
            self.quit()



class bufferThread(QThread):
    """Thread for running measurements."""

    bufferSig = pyqtSignal(str)
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
            self.bufferSig.emit(save_file)

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
