from mantid.simpleapi import *
import os.path

path = "/archive/ndxwish/Instrument/data/cycle_16_3/"
output_path = os.path.join(os.path.expanduser('~'), 'data')
grouping_filename = os.path.join(os.path.expanduser('~'), 'cal_files/35922_h00_RW.cal')
focused_suffix = '-foc-h00'
crop_limits = {"XMin": 6000, "XMax": 99900 }

run_numbers = []
run_numbers.append(35991)
run_numbers.extend(range(35979,35983))
run_numbers.append(35988)
run_numbers.extend(range(35983,35985))
#run_numbers = range(35992,35994)

for runno in run_numbers:
    run_number = str(runno)
    
    raw_file = os.path.join(path, 'WISH000'+run_number+'.raw')
    LoadRaw(Filename=raw_file, OutputWorkspace=run_number, LoadLogFiles=False)
    CropWorkspace(InputWorkspace=run_number, OutputWorkspace=run_number, **crop_limits)
    NormaliseByCurrent(InputWorkspace=run_number, OutputWorkspace=run_number)
    ConvertUnits(InputWorkspace=run_number, OutputWorkspace=run_number, Target='Wavelength')
    NormaliseToMonitor(InputWorkspace=run_number, OutputWorkspace=run_number, MonitorID=4)
    ConvertUnits(InputWorkspace=run_number, OutputWorkspace=run_number, Target='dSpacing')
    
    focused = run_number + focused_suffix
    focused_xye = focused +'.dat'
    focused_nxs = focused +'.nxs'
    DiffractionFocussing(InputWorkspace=run_number, OutputWorkspace=focused, GroupingFileName=grouping_filename, PreserveEvents=False)
    SaveFocusedXYE(focused, os.path.join(output_path, focused_xye))
    SaveNexusProcessed(InputWorkspace=focused, Filename=os.path.join(output_path, focused_nxs))

    DeleteWorkspace(run_number)
    
