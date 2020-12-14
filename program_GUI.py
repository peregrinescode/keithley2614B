"""
Qt5 GUI for making OFET measurements with a Keithley 2636.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
"""

import sys
import fnmatch
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
    QFileDialog,
    QInputDialog,
    QLineEdit,
)

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as mplToolb
import matplotlib.style as style
from matplotlib.figure import Figure
import k2614B_driver  # Driver for keithley 2636

matplotlib.use("Qt5Agg")


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
        self.analysisWindow = analysisWindow()
        self.keithleyErrorWindow = keithleyErrorWindow()
        self.popupWarning = warningWindow()

        # Dock setup
        # Keithley dock widget
        self.buttonWidget = keithleyButtonWidget()
        self.dockWidget1 = QDockWidget("IV control")
        self.dockWidget1.setWidget(self.buttonWidget)
        self.addDockWidget(Qt.TopDockWidgetArea, self.dockWidget1)

        # Matplotlib control widget
        self.dockWidget2 = QDockWidget("Plotting controls")
        self.dockWidget2.setWidget(mplToolb(self.mainWidget, self))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget2)

        # Menu bar setup
        # Shutdown program
        exitAction = QAction("&Exit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Exit application")
        exitAction.triggered.connect(qApp.quit)
        # Load old data
        loadAction = QAction("&Load", self)
        loadAction.setShortcut("Ctrl+L")
        loadAction.setStatusTip("Load data to be displayed")
        loadAction.triggered.connect(self.showFileOpen)

        # Clear data
        clearAction = QAction("Clear", self)
        clearAction.setShortcut("Ctrl+C")
        clearAction.setStatusTip("Clear data on graph")
        clearAction.triggered.connect(self.mainWidget.clear)
        # Keithley settings popup
        keithleyAction = QAction("Settings", self)
        keithleyAction.setShortcut("Ctrl+K")
        keithleyAction.setStatusTip("Adjust scan parameters")
        keithleyConAction = QAction("Connect", self)
        keithleyConAction.setShortcut("Ctrl+J")
        keithleyConAction.setStatusTip("Reconnect to keithley 2636")
        keithleyConAction.triggered.connect(self.keithleyConnectionWindow.show)
        keithleyError = QAction("Error Log", self)
        keithleyError.setShortcut("Ctrl+E")
        keithleyError.triggered.connect(self.keithleyErrorWindow.show)
        analysisAction = QAction("Analysis", self)
        analysisAction.setShortcut("Ctrl+A")
        analysisAction.triggered.connect(self.analysisWindow.show)

        # Add items to menu bars
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(loadAction)
        fileMenu.addAction(clearAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)
        keithleyMenu = menubar.addMenu("&Keithley")
        keithleyMenu.addAction(keithleyConAction)
        keithleyMenu.addAction(keithleyAction)
        keithleyMenu.addAction(keithleyError)
        analysisMenu = menubar.addMenu("&Analysis")
        #analysisMenu.addAction(analysis)

        # Status bar setup
        self.statusbar = self.statusBar()

        # Attempt to connect to a keithley
        self.testKeithleyConnection()
        self.keithleyConnectionWindow.connectionSig.connect
        (self.buttonWidget.showButtons)

        # Window setup
        self.resize(800, 800)
        self.centre()
        self.setWindowTitle("k2614B - Measurement program")
        self.show()

    def testKeithleyConnection(self):
        """Connect to the keithley on initialisation."""
        try:
            self.keithley = k2614B_driver.k2614B(
                address="TCPIP[board]::192.168.0.2::inst0::INSTR"
            )
            self.statusbar.showMessage("Keithley found.")
            self.buttonWidget.showButtons()
            self.keithley.closeConnection()
        except ConnectionError:
            self.buttonWidget.hideButtons()
            self.statusbar.showMessage("No keithley connection.")

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
                else:
                    raise FileNotFoundError
            except KeyError or FileNotFoundError:
                self.popupWarning.showWindow("Unsupported file.")

    def updateStatusbar(slf, s):
        """Put text in status bar."""
        self.statusbar.showMessage(s)


class keithleyButtonWidget(QWidget):
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
        col3 = QLabel("Voltage Step (V)")
        col4 = QLabel("Step Time (s)")
        col5 = QLabel("Repeat sweeps")
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
        ivFirstV.setValue(-5)
        self.startV = -5
        ivFirstV.valueChanged.connect(self.updateStartV)

        # Stop voltage
        ivLastV = QDoubleSpinBox(self)
        grid.addWidget(ivLastV, 2, 3)
        ivLastV.setMinimum(-200)
        ivLastV.setMaximum(200)
        ivLastV.setValue(5)
        self.stopV = 5
        ivLastV.valueChanged.connect(self.updateStopV)

        # Voltage step
        ivStepV = QDoubleSpinBox(self)
        grid.addWidget(ivStepV, 2, 4)
        ivStepV.setSingleStep(0.1)
        ivStepV.setValue(0.1)
        self.stepV = 0.1
        ivStepV.valueChanged.connect(self.updateStepV)

        # Step time
        ivStepT = QDoubleSpinBox(self)
        grid.addWidget(ivStepT, 2, 5)
        ivStepT.setSingleStep(0.1)
        ivStepT.setValue(0.2)
        self.stepT = 0.2
        ivStepT.valueChanged.connect(self.updateStepT)

        # Reverse scan + Number of repeats
        ivRepeats = QSpinBox(self)
        grid.addWidget(ivRepeats, 2, 6)
        ivRepeats.setSingleStep(1)
        ivRepeats.setValue(0)
        self.ivRepeats = 0
        ivRepeats.valueChanged.connect(self.updateRepeats)


        # Push button setup
        self.ivBtn = QPushButton("Perform IV sweep")
        grid.addWidget(self.ivBtn, 2, 7)
        self.ivBtn.clicked.connect(self.showSampleNameInput)

        # Read from buffer
        self.readBuffer = QPushButton("Read buffer")
        grid.addWidget(self.readBuffer, 2, 8)

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

    def updateRepeats(self, ivRepeats):
        """Set/update repeat number."""
        self.ivRepeats = ivRepeats


class mplWidget(FigureCanvas):
    """Widget for matplotlib figure."""

    def __init__(self, parent=None):
        """Create plotting widget."""
        self.initWidget()

    def initWidget(self, parent=None, width=5, height=4, dpi=100):
        """Set parameters of plotting widget."""
        style.use("seaborn-white")

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = self.fig.add_subplot(111)

        self.ax1.set_xlabel("Voltage (V)", fontsize=12)
        self.ax1.set_ylabel("Current (A)", fontsize=12)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def drawIV(self, df, sname):
        """Take a data frame and draw it."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.plot(
            df["Channel Voltage [V]"], df["Channel Current [A]"], "o-", label=sname
        )
        self.ax1.set_title("IV Sweep", fontsize=12)
        self.ax1.set_xlabel("Voltage (V)", fontsize=12)
        self.ax1.set_ylabel("Current (A)", fontsize=12)
        self.ax1.legend(loc="best")
        FigureCanvas.draw(self)

    def clear(self):
        """Clear the plot."""
        self.ax1.clear()
        self.ax1.set_xlabel("Voltage (V)", fontsize=12)
        self.ax1.set_ylabel("Current (A)", fontsize=12)
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
            self.keithley = k2614B_driver.k2614B(
                address="TCPIP[board]::192.168.0.2::inst0::INSTR",
                read_term="\n",
                baudrate=57600,
            )
            self.connStatus.append("Connection successful")
            self.connectionSig.emit()
            self.keithley.closeConnection()

        except ConnectionError:
            self.connStatus.append("No Keithley can be found.")


class analysisWindow(QWidget):
    """Popup for analysis window."""

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
            self.keithley = k2614B_driver.k2614B(
                address="TCPIP[board]::192.168.0.2::inst0::INSTR",
                read_term="\n",
                baudrate=57600,
            )
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
