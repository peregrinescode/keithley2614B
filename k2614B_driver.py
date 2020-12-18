"""
Module for interacting with the Keithley 2636B SMU.

Author:  Ross <peregrine dot warren at physics dot ox dot ac dot uk>
"""

import numpy as np
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


    def readBuffer(self):
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
        -- Restore Series 2600B defaults.
        smua.reset()
        
        -- Clear the buffer
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
        
        -- Set compliance to 10 mA.
        smua.source.limiti = 10e-6
        
        -- Measurement Setup
        -- To adjust the delay factor.
        smua.measure.delayfactor = 1
        smua.measure.nplc = 10
        -- SMUA setup
        smua.source.func = smua.OUTPUT_DCVOLTS
        smua.sense = smua.SENSE_LOCAL
        smua.source.autorangev = smua.AUTORANGE_ON
        smua.measure.rangei = 10e-6
        
        --DISPLAY settings
        display.screen = display.SMUA
        display.smua.measure.func = display.MEASURE_DCAMPS
        
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


    def IVsweep2(self, sample, vstart, vstop, vsteps, stepTime):
        """k2614B IV sweep."""
        # Write a tsp file
        tspScript = f"""
        -- Restore Series 2600B defaults.
        smua.reset()
        
        -- Clear the buffer
        smua.nvbuffer1.clear()
        
        smua.nvbuffer1.collectsourcevalues = 1
        
        -- Set compliance to 10 mA.
        smua.source.limiti = 10e-6    
        
        -- Linear staircase sweep
        SweepVLinMeasureI(smua, {vstart}, {vstop}, {stepTime}, {vsteps})
        
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
    
    def SweepVListMeasureI(self, myvlist, stime, points, smu="smua"):
        """
        Sets voltages as per list, and measure I
        inputs:
            smu     = Instrument channel (for example, smua refers to SMU 
                      channel A)
            vlist   = Arbitrary list of voltage source values;
                    e.g. vlist = {value1, value2, ... valueN}
            stime   = Settling time in seconds; occurs after stepping the source 
                    and before performing a measurement
            points  = Number of sweep points (must be ≥ 2)
        """
        # Write a tsp file
        tspScript = f"""
        -- Restore Series 2600B defaults.
        smua.reset()
        
        -- Clear the buffer
        smua.nvbuffer1.clear()
        
        --DISPLAY settings
        display.screen = display.SMUA
        display.smua.measure.func = display.MEASURE_DCAMPS
        
        -- Set compliance to 50 mA.
        smua.source.limiti = 50e-3    
        
        -- Perform sweep
        SweepVListMeasureI(smua, {myvlist}, {stime}, {points})
        
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
        smua.source.limiti = 50e-3
        smua.measure.rangei = 1e-2
        
        --DISPLAY settings
        display.screen = display.SMUA
        display.smua.measure.func = display.MEASURE_DCAMPS
        
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
        i = 1
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
        
        -- Measurement RAMP DOWN FROM endV
        V = -1 * Vend
        smua.source.output = smua.OUTPUT_ON
        smua.source.levelv = V
        -- forwards scan direction
        if V < 0 then
            while V <= 0 do
                    smua.source.levelv = V
                    smua.source.output = smua.OUTPUT_ON
                    delay({stepTime})
                    smua.measure.i(smua.nvbuffer1)
                    V = V + Vstep
                    smua.source.output = smua.OUTPUT_OFF
            end
        
        -- reverse scan direction
        elseif V > 0 then
            while V >= 0 do
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

    def squareVoltage(self, sample, vPos, vNeg, vTime, nRepeats):
        """Input a voltage, measure current, input -V, measure current."""
        # Write a tsp file
        tspScript = f"""
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
        vPos = {vPos}
        vNeg = {vNeg}
        vTime = {vTime}
        nRepeats = {nRepeats}
        -- Measurement Setup
        -- To adjust the delay factor.
        smua.measure.delayfactor = 1
        smua.measure.nplc = 10
        -- SMUA setup
        smua.source.func = smua.OUTPUT_DCVOLTS
        smua.sense = smua.SENSE_LOCAL
        smua.source.autorangev = smua.AUTORANGE_ON
        smua.source.limiti = 50e-3
        smua.measure.rangei = 50e-3
        
        --DISPLAY settings
        display.screen = display.SMUA
        display.smua.measure.func = display.MEASURE_DCAMPS
        
        -- For number of repeats apply voltage and hold for vTime 
        i = 0
        while i < nRepeats do
            
            smua.source.output = smua.OUTPUT_ON
            t = 0
            while t < vTime do
                smua.source.levelv = vPos
                smua.measure.i(smua.nvbuffer1)
                delay(1)
                t = t + 1
            end
            
            t = 0
            while t < vTime do
                smua.source.levelv = vNeg
                --smua.source.output = smua.OUTPUT_ON
                smua.measure.i(smua.nvbuffer1)
                delay(1)
                t = t + 1
            end
                               
           i = i + 1
        
        end
           
        smua.source.output = smua.OUTPUT_OFF
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
    
    def SweepILinMeasureV(self):
        """Input a voltage, measure current, input -V, measure current."""
        # Write a tsp file
        tspScript = f"""
        -- Restore Series 2600B defaults.
        smua.reset()
        -- Set compliance to 1 V.
        smua.source.limitv = 1
        -- Linear staircase sweep
        -- 1 mA to 10 mA, 0.1 second delay,
        -- 10 points.
        SweepILinMeasureV(smua, 1e-3, 10e-3, 0.1, 10)
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
    
    def PulseIMeasureV(self):
        """Pulse current sweep."""
        # Write a tsp file
        tspScript = f"""
        -- Restore Series 2600B defaults.
        smua.reset()
        -- Set compliance to 10 V.
        smua.source.limitv = 10
        -- Pulse current sweep, 1 mA bias,
        -- 10 mA level, 10 ms pulse on,
        -- 50 ms pulse off, 10 cycles.
        PulseIMeasureV(smua, 1e-3, 10e-3, 20e-2, 50e-2, 10)
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
    
    def PulseVMeasureI(self):
        """Pulse current sweep."""
        # Write a tsp file
        tspScript = f"""
        -- Restore Series 2600B defaults.
        smua.reset()
        -- Set compliance to 10 mA.
        smua.source.limiti = 10e-3
        -- Pulse current sweep, 0 V bias,
        -- 10 V pulse level, 10 ms pulse on,
        -- 50 ms pulse off, 10 cycles.
        PulseVMeasureI(smua, 0, 10, 20e-2, 50e-2, 10)
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
    #keithley = k2614B(address="TCPIP[board]::169.254.0.2::inst0::INSTR")
    keithley = k2614B(address="TCPIP[board]::192.168.0.2::inst0::INSTR")
    #keithley.IVsweep("driverTest", 60, -60, 1, 0.2, 1)
    #keithley.IVsweep2("driverTest", 0, 60, 120, 0.55555)
    # keithley.squareVoltage("test", 150, -150, 30, 4)

    vstart = 0
    vstop = 150
    vstep = 1
    numpoint = ((vstop - vstart) / vstep) + 1

    myvlist = np.linspace(vstart, vstop, num=numpoint)
    myvlist = np.append(myvlist, np.linspace(vstop - 1, vstart, num=numpoint - 1))
    #print(list(myvlist))
    stime = 0.5
    points = len(myvlist)

    # Format for keithley to read
    myvlist = str(list(myvlist)).replace('[', '{').replace(']', '}')
    print(myvlist)
    
    keithley.SweepVListMeasureI(myvlist, stime, points)

    df = keithley.readBuffer()
    print(df)
    save_file = "data/P3HT-test-iv.csv"
    df.to_csv(
        save_file, index=False
    )
    print("----------------------------------------")
    print(f"Data saved: data/ {save_file}")
    print("----------------------------------------")    
    keithley.closeConnection()
