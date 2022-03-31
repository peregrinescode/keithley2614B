"""
Qt5 GUI for making OFET measurements with a Keithley 2636.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
"""

import sys
import fnmatch
import numpy as np
import pandas as pd
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QWidget,
    QDesktopWidget,
    QApplication,
    QGridLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QAction,
    qApp,
    QSizePolicy,
    QTextEdit,
    QPlainTextEdit,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QProgressBar,
)

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.ticker import FormatStrFormatter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as mplToolb
import seaborn as sns
from matplotlib.figure import Figure
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings("ignore")
import k2614B_driver  # Driver for keithley 2636

#matplotlib.use("Qt5Agg")


class mainWindow(QMainWindow):
    """Create mainwindow of GUI."""

    def __init__(self):
        """Initalise mainwindow."""
        super().__init__()
        self.initUI()

    def initUI(self):
        """Make signal connections."""
        # Add central widget
        self.mainWidget = mplWidget()
        self.setCentralWidget(self.mainWidget)

        # Add other window widgets
        self.keithleyConnectionWindow = keithleyConnectionWindow()
        self.keithleyErrorWindow = keithleyErrorWindow()
        self.popupWarning = warningWindow()

        # Dock setup
        # Matplotlib control widget
        self.dockWidget2 = QDockWidget("Plotting controls")
        self.dockWidget2.setWidget(mplToolb(self.mainWidget, self))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget2)
        # IV scan widget
        self.ivScanWidget=ivScanWidget()
        self.dockWidget1=QDockWidget("IV scan")
        self.dockWidget1.setWidget(self.ivScanWidget)
        self.addDockWidget(Qt.TopDockWidgetArea, self.dockWidget1)
        # self.tabifyDockWidget(self.dockWidget2, self.dockWidget1)
        # Conductivity widget
        self.conductivityWidget=conductivityWidget()
        self.dockWidget3=QDockWidget("Conductivity fit")
        self.dockWidget3.setWidget(self.conductivityWidget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget3)
        # self.conductivityWidget.fitSignal.connect(self.)

        # Menu bar setup
        # Shutdown program
        exitAction=QAction("&Exit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Exit application")
        exitAction.triggered.connect(qApp.quit)
        # Load old data
        loadAction=QAction("&Load", self)
        loadAction.setShortcut("Ctrl+L")
        loadAction.setStatusTip("Load data to be displayed")
        loadAction.triggered.connect(self.showFileOpen)

        # Clear data
        clearAction=QAction("Clear", self)
        clearAction.setShortcut("Ctrl+K")
        clearAction.setStatusTip("Clear data on graph")
        clearAction.triggered.connect(self.mainWidget.clear)
        # Keithley settings popup
        keithleyAction=QAction("Settings", self)
        keithleyAction.setShortcut("Ctrl+S")
        keithleyAction.setStatusTip("Adjust scan parameters")
        keithleyConAction=QAction("Connect", self)
        keithleyConAction.setShortcut("Ctrl+J")
        keithleyConAction.setStatusTip("Reconnect to keithley 2636")
        keithleyConAction.triggered.connect(self.keithleyConnectionWindow.show)
        keithleyError=QAction("Error Log", self)
        keithleyError.setShortcut("Ctrl+E")
        keithleyError.triggered.connect(self.keithleyErrorWindow.show)

        # Add items to menu bars
        menubar=self.menuBar()
        fileMenu=menubar.addMenu("&File")
        fileMenu.addAction(loadAction)
        fileMenu.addAction(clearAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)
        keithleyMenu=menubar.addMenu("&Keithley")
        keithleyMenu.addAction(keithleyConAction)
        keithleyMenu.addAction(keithleyAction)
        keithleyMenu.addAction(keithleyError)

        # Status bar setup
        self.statusbar=self.statusBar()

        # Attempt to connect to a keithley
#        self.testKeithleyConnection()
#        self.keithleyConnectionWindow.connectionSig.connect
#        (self.ivScanWidget.showButtons)
#
        # Window setup
        self.resize(1200, 1000)
        self.centre()
        self.setWindowTitle("k2614B - Measurement program")
        self.show()

#    def testKeithleyConnection(self):
#        """Connect to the keithley on initialisation."""
#        try:
#            address = "TCPIP[board]::192.168.0.2::inst0::INSTR"
#            # address = "TCPIP[board]::169.254.0.2::inst0::INSTR"
#            self.keithley = k2614B_driver.k2614B(address)
#            self.statusbar.showMessage("Keithley found.")
#            self.ivScanWidget.showButtons()
#            self.keithley.closeConnection()
#        except ConnectionError:
#            self.ivScanWidget.hideButtons()
#            self.statusbar.showMessage("No keithley connection.")
    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2
        )

    def showFileOpen(self):
        """Pop up for file selection."""
        filt1 = "*.csv"
        fname = QFileDialog.getOpenFileName(
            self, "Open file", filter=filt1, directory="data"
        )
        if fname[0]:
            try:
                df = pd.read_csv(fname[0], ",")
                if fnmatch.fnmatch(fname[0], "*iv.csv"):
                    self.mainWidget.drawIV(df, fname[0].split("/")[-1].split(".")[0])
                    self.conductivityWidget.latestData = df
                    self.conductivityWidget.sample = fname[0].split("/")[-1].split(".")[0]
                elif fnmatch.fnmatch(fname[0], "*squareV.csv"):
                    self.mainWidget.drawSquareV(df, fname[0].split("/")[-1].split(".")[0])
                else:
                    raise FileNotFoundError
            except KeyError or FileNotFoundError:
                self.popupWarning.showWindow("Unsupported file.")

    def updateStatusbar(slf, s):
        """Put text in status bar."""
        self.statusbar.showMessage(s)


class ivScanWidget(QWidget):
    """Defines class with buttons controlling keithley."""

    # Define signals to be emitted from widget
    cancelSignal = pyqtSignal()

    def __init__(self):
        """Initialise setup of widget."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Columns
        col1 = QLabel("Start Voltage (V)")
        col2 = QLabel("Stop Voltage (V)")
        col3 = QLabel("# of steps")
        col4 = QLabel("Step Time (s)")
        col5 = QLabel("Compliance 1e-{?} (A)")
        grid.addWidget(col1, 1, 2)
        grid.addWidget(col2, 1, 3)
        grid.addWidget(col3, 1, 4)
        grid.addWidget(col4, 1, 5)
        grid.addWidget(col5, 1, 6)

        # Start voltage
        ivFirstV = QDoubleSpinBox(self)
        grid.addWidget(ivFirstV, 2, 2)
        ivFirstV.setMinimum(-200)
        ivFirstV.setMaximum(200)
        ivFirstV.setValue(-10)
        self.startV = -10
        ivFirstV.valueChanged.connect(self.updateStartV)

        # Stop voltage
        ivLastV = QDoubleSpinBox(self)
        grid.addWidget(ivLastV, 2, 3)
        ivLastV.setMinimum(-200)
        ivLastV.setMaximum(200)
        ivLastV.setValue(10)
        self.stopV = 10
        ivLastV.valueChanged.connect(self.updateStopV)

        # Number of steps
        ivStepV = QSpinBox(self)
        grid.addWidget(ivStepV, 2, 4)
        ivStepV.setSingleStep(1)
        ivStepV.setValue(100)
        self.stepV = 100
        ivStepV.setMaximum(10000)
        ivStepV.valueChanged.connect(self.updateStepV)

        # Step time
        ivStepT = QDoubleSpinBox(self)
        grid.addWidget(ivStepT, 2, 5)
        ivStepT.setSingleStep(0.5)
        ivStepT.setValue(0.1)
        self.stepT = 0.1
        ivStepT.valueChanged.connect(self.updateStepT)

        # Set Compliance
        setCompliance = QSpinBox(self)
        grid.addWidget(setCompliance, 2, 6)
        setCompliance.setMinimum(-9)
        setCompliance.setMaximum(-1)
        setCompliance.setValue(-3)
        self.setCompliance = -3
        setCompliance.valueChanged.connect(self.updateCompliance)


        # Push button setup
        self.ivBtn = QPushButton("1. Perform IV sweep")
        grid.addWidget(self.ivBtn, 2, 7)
        self.ivBtn.clicked.connect(self.showSampleNameInput)

        # Read from buffer
        self.readBuffer = QPushButton("2. Save buffer")
        grid.addWidget(self.readBuffer, 2, 8)
        self.readBuffer.setEnabled(False)

        # Read from buffer
        self.plotBtn = QPushButton("3. PLOT")
        grid.addWidget(self.plotBtn, 2, 9)
        self.plotBtn.setEnabled(False)

        # Progress Bar
        self.pbar = QProgressBar(self)
        self.pbar.setValue(0)
        self.resize(300, 100)
        grid.addWidget(self.pbar, 3, 2, 1, 8)


    def showSampleNameInput(self):
        """Popup for sample name input."""
        samNam = QInputDialog()
        try:
            text, ok = samNam.getText(
                self,
                "Sample Name",
                "Enter sample name:",
                QLineEdit.Normal,
                str(self.SampleName),
            )

        except AttributeError:
            text, ok = samNam.getText(self, "Sample Name", "Enter sample name:")
        if ok:
            if text != "":  # to catch empty input
                self.SampleName = str(text)
        else:
            self.SampleName = None
            self.cancelSignal.emit()  # doesnt link to anything yet

    def hideButtons(self):
        """Hide control buttons."""
        self.ivBtn.setEnabled(False)

    def showButtons(self):
        """Show control buttons."""
        self.ivBtn.setEnabled(True)
        self.readBuffer.setEnabled(True)

    def updateStartV(self, startV):
        """Set/update start voltage."""
        self.startV = startV

    def updateStopV(self, stopV):
        """Set/update start voltage."""
        self.stopV = stopV

    def updateStepV(self, stepV):
        """Set/update start voltage."""
        self.stepV = stepV

    def updateStepT(self, stepT):
        """Set/update start voltage."""
        self.stepT = stepT

    def updateCompliance(self, compliance):
        """Set/update repeat number."""
        self.setCompliance = compliance
        
        
class conductivityWidget(QWidget):
    """docked widget for conductivity analysis."""
    fitSignal = pyqtSignal()

    def __init__(self):
        """Initialise setup of widget."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Columns
        col1 = QLabel("Film thickness (nm)")
        col2 = QLabel("Channel length (um)")
        col3 = QLabel("Channel width (mm)")
        grid.addWidget(col1, 1, 2)
        grid.addWidget(col2, 1, 3)
        grid.addWidget(col3, 1, 4)

        # Film thickness
        filmT = QDoubleSpinBox(self)
        grid.addWidget(filmT, 2, 2)
        filmT.setMinimum(1)
        filmT.setMaximum(1000)
        filmT.setValue(15)
        self.filmT = 15
        filmT.valueChanged.connect(self.updateFilmT)

        # Channel length
        channelL = QDoubleSpinBox(self)
        grid.addWidget(channelL, 2, 3)
        channelL.setMinimum(1)
        channelL.setMaximum(1000)
        channelL.setValue(50)
        self.channelL = 50
        channelL.valueChanged.connect(self.updateChannelL)

        # Channel width
        channelW = QDoubleSpinBox(self)
        grid.addWidget(channelW, 2, 4)
        channelW.setMinimum(1)
        channelW.setMaximum(1000)        
        channelW.setValue(30)
        self.channelW = 30
        channelW.setMaximum(1000)
        channelW.valueChanged.connect(self.updateChannelW)

        # Push button setup
        self.fitButton = QPushButton("Find sigma!")
        grid.addWidget(self.fitButton, 2, 5, 1, 3)
        self.fitButton.clicked.connect(self.fitConductivity)
        
        # Results box
        self.conResults = QPlainTextEdit()
        grid.addWidget(self.conResults, 3, 2, 1, 6)
        self.conResults.setFixedHeight(40)


    def fitConductivity(self):
        """What to do when find sigma button is clicked!."""

        dat1 = self.latestData
        sample = self.sample
        l = self.channelL * 1e-6
        t = self.filmT * 1e-9
        w = self.channelW * 1e-3
        
        # Make a LINEAR FIT
        def Ohms_law(V, R):
            return V / R
        
        popt, pcov = curve_fit(Ohms_law, dat1['Channel Voltage [V]'], dat1['Channel Current [A]'])
        perr = np.sqrt(np.diag(pcov))
        
        # Calculate/print out the conductivity
        R = popt[0]  # Gradient is the device resistance
        sigma = (l / (t * w)) * (1/R)

        self.conResults.appendHtml(f"{sample}: <b> &sigma; = {sigma / 100:.3g} S/cm</b>")

        x1 = dat1['Channel Voltage [V]'].min()
        x2 = dat1['Channel Voltage [V]'].max()
        
        # Plot the linear fit
        self.plotFit = Ohms_law(np.linspace(x1, x2, 30), popt[0])

        self.fitSignal.emit()

    def updateFilmT(self, filmT):
        """Set/update start voltage."""
        self.filmT = filmT

    def updateChannelL(self, channelL):
        """Set/update start voltage."""
        self.channelL = channelL

    def updateChannelW(self, channelW):
        """Set/update start voltage."""
        self.channelW = channelW


class mplWidget(FigureCanvas):
    """Widget for matplotlib figure and data analysis."""

    def __init__(self, parent=None):
        """Create plotting widget."""
        self.initWidget()

    def initWidget(self, parent=None, width=8, height=(8 / (1.618)), dpi=300):
        """Set parameters of plotting widget."""

        sns.set_style('white')

        # Options
        #params = {'text.usetex': True,
                  #'font.size': 9,
                  #'font.family': 'DejaVu Sans',
                  #}
        #plt.rcParams.update(params)
        
        #markerSize = 3        

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = self.fig.gca()

        self.ax1.set_xlabel("Voltage (V)")
        self.ax1.set_ylabel("Current (A)")

        sns.despine(self.fig)
        
        #formatter = ticker.ScalarFormatter(useMathText=True)
        #formatter.set_scientific(True)
        #self.ax1.yaxis.set_major_formatter(formatter)
        #self.ax1.xaxis.major.formatter._useMathText = True
        
        #self.ax1.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.fig.subplots_adjust(left=0.18, right=0.95, bottom=0.22, top=0.90)


    def drawIV(self, df, sname):
        """Take a data frame and draw it."""
        self.ax1.clear()
        # self.ax1 = self.fig.add_subplot(111)

        self.ax1.plot(df["Channel Voltage [V]"], df["Channel Current [A]"], ".", label=sname)

        self.ax1.set_xlabel("Voltage (V)")
        self.ax1.set_ylabel("Current (A)")
        self.ax1.legend(loc="best", fontsize=8, frameon=False)
        sns.despine(self.fig)
        #self.ax1.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        FigureCanvas.draw(self)

    def drawSquareV(self, df, sname):
        """Take a data frame and draw it."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.plot(
            df.index, df["Channel Current [A]"] / 1e-6, "-", label=sname
        )
        #self.ax1.set_title("IV Sweep")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("Current ($\mu$A)")
        #self.ax1.legend(loc="lower right", fontsize=8)
        #self.ax1.set_ylim(-1 * abs(df["Channel Current [A]"]).max(), abs(df["Channel Current [A]"]).max())
        FigureCanvas.draw(self)
        
    def rescale(self):
        """Rescale plot. {unfinished}"""
        #if len(self.ax1.lines) == 0:
            #if df["Channel Current [A]"].max() > 0.1e-3:
                #self.ax1.scale = 1e-3
                #self.ax1.set_ylabel("Current (mA)")
            #if 0.1e-6 < df["Channel Current [A]"].max() < 0.1e-3:
                #self.ax1.scale = 1e-6
                #self.ax1.set_ylabel(f"Current ($\mu$A)")
            #elif df["Channel Current [A]"].max() < 0.1e-6:
                #self.ax1.scale = 1e-9
                #self.ax1.set_ylabel(f"Current (nA)")

        #elif len(self.ax1.lines) != 0:
            #ydata = []
            #for lines in self.ax1.lines:


            #ydata = np.array(ydata)
            #if ydata.max() > 0.1e-3:
                #self.ax1.scale = 1e-3
                #self.ax1.set_ylabel("Current (mA)")
            #if 0.1e-6 < ydata.max() < 0.1e-3:
                #self.ax1.scale = 1e-6
                #self.ax1.set_ylabel(f"Current ($\mu$A)")
            #elif ydata.max() < 0.1e-6:
                #self.ax1.scale = 1e-9
                #self.ax1.set_ylabel(f"Current (nA)")
        #FigureCanvas.draw(self)
        pass

    def clear(self):
        """Clear the plot."""
        self.ax1.clear()
        self.ax1.set_xlabel("Voltage (V)")
        self.ax1.set_ylabel("Current (A)")
        FigureCanvas.draw(self)


class keithleyConnectionWindow(QWidget):
    """Popup for connecting to instrument."""

    connectionSig = pyqtSignal()

    def __init__(self):
        """Initialise setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Connection status box
        self.connStatus = QTextEdit("Push button to connect to keithley...")
        self.connButton = QPushButton("Connect")
        self.connButton.clicked.connect(self.reconnect2keithley)
        grid.addWidget(self.connStatus, 1, 1)
        grid.addWidget(self.connButton, 2, 1)

        # Window setup
        self.resize(300, 100)
        self.centre()
        self.setWindowTitle("k2614B - Connecting")

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2
        )

    def reconnect2keithley(self):
        """Reconnect to instrument."""
        try:
            address = "TCPIP[board]::192.168.0.2::inst0::INSTR"
            # address = "TCPIP[board]::169.254.0.2::inst0::INSTR"
            self.keithley = k2614B_driver.k2614B(address)
            self.connStatus.append("Connection successful")
            self.connectionSig.emit()
            self.keithley.closeConnection()

        except ConnectionError:
            self.connStatus.append("No Keithley can be found.")


class keithleyErrorWindow(QWidget):
    """Popup for reading error messages."""

    def __init__(self):
        """Initialise setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Connection status box
        self.errorStatus = QTextEdit("ERROR CODE------------------MESSAGE")
        self.errorButton = QPushButton("Read error")
        self.errorButton.clicked.connect(self.readError)
        grid.addWidget(self.errorStatus, 1, 1)
        grid.addWidget(self.errorButton, 2, 1)

        # Window setup
        self.resize(600, 300)
        self.centre()
        self.setWindowTitle("k2614B - Error Log")

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2
        )

    def readError(self):
        """Reconnect to instrument."""
        self.keithley = k2614B_driver.k2614B(
            address="TCPIP[board]::192.168.0.2::inst0::INSTR",
            read_term="\n",
            baudrate=57600,
        )

        self.keithley._write(
            "errorCode, message, severity, errorNode" + "= errorqueue.next()"
        )
        self.keithley._write("print(errorCode, message)")
        error = self.keithley._query("")
        self.errorStatus.append(error)
        self.keithley.closeConnection()


class warningWindow(QWidget):
    """Warning window popup."""

    def __init__(self):
        """Intial setup."""
        super().__init__()
        self.initWidget()

    def initWidget(self):
        """Initialise connections."""
        # Set widget layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Connection status box
        self.warning = QLabel()
        self.continueButton = QPushButton("Continue")
        self.continueButton.clicked.connect(self.hide)
        grid.addWidget(self.warning, 1, 1)
        grid.addWidget(self.continueButton, 2, 1)

        # Window setup
        self.resize(180, 80)
        self.centre()
        self.setWindowTitle("Error!")

    def centre(self):
        """Find screen size and place in centre."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2
        )

    def showWindow(self, s):
        """Write error message and show window."""
        self.warning.setText(s)
        self.show()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    GUI = mainWindow()
    sys.exit(app.exec_())
