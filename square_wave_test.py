'''
Code for inputting a square wave
'''

import numpy as np
import k2614B_driver
from math import ceil

# Parameters
vList = [10, 20, 30, 40]
holdPoints = 30       # how many points to measure during hold
stime = 0.5           # make a measurement every x (s)
nCycles = 2           # how many times to cycle

myvlist = []

for v in vList:
    myvlist.extend(([v] * holdPoints + [-1 * v] * holdPoints) * nCycles)

points = len(myvlist)

# Format for keithley to read
myvlist = str(list(myvlist)).replace('[', '{').replace(']', '}')
print(myvlist)


keithley = k2614B_driver.k2614B(address="TCPIP[board]::192.168.0.2::inst0::INSTR")
keithley.SweepVListMeasureI(myvlist, stime, points)

print(f"Estimated measurement time = {ceil(stime * points)} seconds ({(stime * points)/60:.1f} minutes)")

df = keithley.readBuffer()
print(df)
save_file = "data/P3HT-Motdf-dev1-squareV.csv"
df.to_csv(save_file, index=False)
print("----------------------------------------")
print(f"Data saved: data/ {save_file}")
print("----------------------------------------")    
keithley.closeConnection()
