"""
Module for interacting with the Keithley 2636B SMU.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
"""

import pyvisa as visa
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.style as style
from textwrap import dedent
from os import remove


class k2614B:
    """Class for Keithley control."""

    def __init__(self, address, read_term=None, baudrate=None):
        """Make instrument connection instantly on calling class."""
        rm = visa.ResourceManager("@py")  # use py-visa backend
        self.makeConnection(rm, address, read_term, baudrate)

    def makeConnection(self, rm, address, read_term, baudrate):
        """Make initial connection to instrument."""
        try:
            # Connection via LAN (tested on windows)
            # address='TCPIP::192.168.0.2::5025:SOCKET'
            # print(f'Connecting via ethernet: "{address}"')
            self.inst = rm.open_resource(address)
            # self.inst.read_termination = str(read_term)
            # print(self.inst.query('*IDN?'))

        except IOError:
            print("CONNECTION ERROR: Check instrument address.")
            raise ConnectionError

    def closeConnection(self):
        """Close connection to keithley."""
        try:
            self.inst.close()

        except (NameError):
            print("CONNECTION ERROR: No connection established.")

        except (AttributeError):
            print("CONNECTION ERROR: No connection established.")

    def _write(self, m):
        """Write to instrument."""
        try:
            assert type(m) == str
            self.inst.write(m)
        except AttributeError:
            print("CONNECTION ERROR: No connection established.")

    def _read(self):
        """Read instrument."""
        r = self.inst.read()
        return r

    def _query(self, s):
        """Query instrument."""
        try:
            r = self.inst.query(s)
            return r

        except FileNotFoundError:
            return "CONNECTION ERROR: No connection established."
        except AttributeError:
            print("CONNECTION ERROR: No connection established.")
            return "CONNECTION ERROR: No connection established."

    def loadTSP(self, tsp):
        """Load an anonymous TSP script into the k2614B nonvolatile memory."""
        try:
            tsp_dir = "./"  # Put all tsp scripts in this folder
            self._write("loadscript")
            line_count = 1
            for line in open(str(tsp_dir + tsp), mode="r"):
                self._write(line)
                line_count += 1
            self._write("endscript")
            print("----------------------------------------")
            print("Uploaded TSP script: ", tsp)

        except FileNotFoundError:
            print("ERROR: Could not find tsp script. Check path.")
            raise SystemExit

    def runTSP(self):
        """Run the anonymous TSP script currently loaded in the k2614B memory."""
        self._write("script.anonymous.run()")
        print("Measurement in progress...")

    def readBufferIV(self):
        """Read specified buffer in keithley memory and return an array."""
        vd = [
            float(x)
            for x in self._query(
                "printbuffer" + "(1, smua.nvbuffer1.n, smua.nvbuffer1.sourcevalues)"
            ).split(",")
        ]
        c = [
            float(x)
            for x in self._query(
                "printbuffer" + "(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)"
            ).split(",")
        ]
        df = pd.DataFrame({"Channel Voltage [V]": vd, "Channel Current [A]": c})
        return df


    def IVsweep(self, sample, vstart, vstop, vstep, stepTime, repeats):
        """k2614B IV sweep."""
        # Write a tsp file
        tspScript = f"""
        -- TSP PROGRAM FOR PERFORMING IV SWEEP
        reset()
        display.clear()
        
        -- Beep in excitement
        -- beeper.beep(1, 600)
        
        -- Clear buffers
        smua.nvbuffer1.clear()
        -- Prepare buffers
        smua.nvbuffer1.collectsourcevalues = 1
        format.data = format.ASCII
        smua.nvbuffer1.appendmode = 1
        smua.measure.count = 1
        -- Set Paramters
        Vstart = {vstart}
        Vend = {vstop}
        Vstep = {vstep}
        repeats = {repeats}
        -- Measurement Setup
        -- To adjust the delay factor.
        smua.measure.delayfactor = 1
        smua.measure.nplc = 10
        -- SMUA setup
        smua.source.func = smua.OUTPUT_DCVOLTS
        smua.sense = smua.SENSE_LOCAL
        smua.source.autorangev = smua.AUTORANGE_ON
        smua.source.limiti = 1e-5
        smua.measure.rangei = 1e-5
        
        --DISPLAY settings
        display.smua.measure.func = display.MEASURE_DCAMPS
        display.screen = display.SMUA
        
        -- Measurement routine
        V = Vstart
        smua.source.output = smua.OUTPUT_ON
        smua.source.levelv = V
        
        -- forwards scan direction
        if Vstart < Vend then
            while V <= Vend do
                    smua.source.levelv = V
                    smua.source.output = smua.OUTPUT_ON
                    delay({stepTime})
                    smua.measure.i(smua.nvbuffer1)
                    V = V + Vstep
                    smua.source.output = smua.OUTPUT_OFF
            end
        
        -- reverse scan direction
        elseif Vstart > Vend then
            while V >= Vend do
                    smua.source.levelv = V
                    smua.source.output = smua.OUTPUT_ON
                    delay({stepTime})
                    smua.measure.i(smua.nvbuffer1)
                    V = V - Vstep
                    smua.source.output = smua.OUTPUT_OFF
            end
        
        else
            error("Invalid sweep parameters.")
        end
        waitcomplete()
        """

        # Write this to a file before uploading to Keithley:
        with open("iv-temp.tsp", "w") as myfile:
            myfile.write(dedent(tspScript))

        # Now run the script
        self.loadTSP("iv-temp.tsp")
        self.runTSP()

        # clean up temp .tsp file
        remove("iv-temp.tsp")
        return


    def IVsweepRep(self, sample, vstart, vstop, vstep, stepTime, repeats):
        """k2614B IV sweep with repeats."""
        # Write a tsp file
        tspScript = f"""
        -- TSP PROGRAM FOR PERFORMING IV SWEEP
        reset()
        display.clear()
        
        -- Beep in excitement
        -- beeper.beep(1, 600)
        
        -- Clear buffers
        smua.nvbuffer1.clear()
        -- Prepare buffers
        smua.nvbuffer1.collectsourcevalues = 1
        format.data = format.ASCII
        smua.nvbuffer1.appendmode = 1
        smua.measure.count = 1
        -- Set Paramters
        Vstart = {vstart}
        Vend = {vstop}
        Vstep = {vstep}
        repeats = {repeats}
        -- Measurement Setup
        -- To adjust the delay factor.
        smua.measure.delayfactor = 1
        smua.measure.nplc = 10
        -- SMUA setup
        smua.source.func = smua.OUTPUT_DCVOLTS
        smua.sense = smua.SENSE_LOCAL
        smua.source.autorangev = smua.AUTORANGE_ON
        smua.source.limiti = 1e-5
        smua.measure.rangei = 1e-5
        
        --DISPLAY settings
        display.smua.measure.func = display.MEASURE_DCAMPS
        display.screen = display.SMUA
        
        -- Measurement RAMP UP TO STARTV
        V = 0
        smua.source.output = smua.OUTPUT_ON
        smua.source.levelv = V
        -- forwards scan direction
        if Vstart > 0 then
            while V < Vstart do
                    smua.source.levelv = V
                    smua.source.output = smua.OUTPUT_ON
                    delay({stepTime})
                    smua.measure.i(smua.nvbuffer1)
                    V = V + Vstep
                    smua.source.output = smua.OUTPUT_OFF
            end
        
        -- reverse scan direction
        elseif Vstart < 0 then
            while V > Vstart do
                    smua.source.levelv = V
                    smua.source.output = smua.OUTPUT_ON
                    delay({stepTime})
                    smua.measure.i(smua.nvbuffer1)
                    V = V - Vstep
                    smua.source.output = smua.OUTPUT_OFF
            end
        
        else
            error("Invalid sweep parameters.")
        end
        
        
        -- MEASUREMENT SWEEP FROM VSTART TO VEND AND BACK
        i = 0
        while i <= repeats do
            V = Vstart
            smua.source.output = smua.OUTPUT_ON
            smua.source.levelv = V
            
            -- forwards scan direction
            if Vstart < Vend then
                while V < Vend do
                        smua.source.levelv = V
                        smua.source.output = smua.OUTPUT_ON
                        delay({stepTime})
                        smua.measure.i(smua.nvbuffer1)
                        V = V + Vstep
                        smua.source.output = smua.OUTPUT_OFF
                end
            
            -- reverse scan direction
            elseif Vstart > Vend then
                while V > Vend do
                        smua.source.levelv = V
                        smua.source.output = smua.OUTPUT_ON
                        delay({stepTime})
                        smua.measure.i(smua.nvbuffer1)
                        V = V - Vstep
                        smua.source.output = smua.OUTPUT_OFF
                end
                    
            else
                error("Invalid sweep parameters.")
            end
           
           Vstart = -1 * Vstart 
           Vend = -1 * Vend
           i = i + 1
           
        end
        
        waitcomplete()
        """

        # Write this to a file before uploading to Keithley:
        with open("iv-temp.tsp", "w") as myfile:
            myfile.write(dedent(tspScript))

        # Now run the script
        self.loadTSP("iv-temp.tsp")
        self.runTSP()

        # clean up temp .tsp file
        remove("iv-temp.tsp")
        return


########################################################################


if __name__ == "__main__":
    """For testing methods in the k2614B class."""
    keithley = k2614B(address="TCPIP[board]::169.254.0.2::inst0::INSTR")
    keithley.IVsweepRep("driverTest", 1, -1, 0.2, 0.01, 2)
    df = keithley.readBufferIV()
    print(df)
    keithley.closeConnection()
