from tube_calib_fit_params import TubeCalibFitParams
from tube_calib import getCalibratedPixelPositions, getPoints
from tube_spec import TubeSpec
from ideal_tube import IdealTube
import numpy as np
import tube

# ----------------------------------------------------------------------------------------------------

#run_number = 'WISH00025383' # 9 lines
run_number = '30541'
file_name = 'WISH000' + run_number + '.raw' # 5 lines

# load your data and integrate it
ws = LoadRaw(file_name, OutputWorkspace=run_number)
ws = CropWorkspace(ws, 6000, 99000, OutputWorkspace=run_number)
ws = Integration(ws, 6000, 99000, OutputWorkspace=run_number)

# remove any calibration parameters (for reference)
ws_uncalib = ws.clone(OutputWorkspace=run_number + "_uncalib")
ws_calib = ws.clone(OutputWorkspace=run_number + "_calib")
ws_corr = ws.clone(OutputWorkspace=run_number + "_corrected")

empty_instr = LoadEmptyInstrument(InstrumentName='WISH')
CopyInstrumentParameters(empty_instr, ws_uncalib)
CopyInstrumentParameters(empty_instr, ws_calib)
CopyInstrumentParameters(empty_instr, ws_corr)
DeleteWorkspace(empty_instr)

# definition of the parameters static for the calibration
#lower_tube = np.array([-0.41,-0.31,-0.21,-0.11,-0.02, 0.09, 0.18, 0.28, 0.39 ])
lower_tube = np.array([-274.81703361, -131.75052481,    0.,  131.75052481, 274.81703361])
upper_tube = lower_tube # assume upper and lower tubes are the same
funcForm = 5*[1] # 5 gaussian peaks
margin = 20

fitPar = TubeCalibFitParams( [59, 161, 258, 353, 448])
fitPar.setAutomatic(True)

# ----------------------------------------------------------------------------------------------------

instrument = ws.getInstrument()
spec = TubeSpec(ws)
spec.setTubeSpecByString(instrument.getFullName())

idealTube = IdealTube()
idealTube.setArray(lower_tube)

# First calibrate all of the detectors
calibrationTable, peaks = tube.calibrate(ws, spec, lower_tube, funcForm, margin=15,
    outputPeak=True, fitPar=fitPar)

ApplyCalibration(ws_calib, calibrationTable)
ApplyCalibration(ws_corr, calibrationTable)


def findBadPeakFits(peaksTable, threshold=10):
    """ Find peaks whose fit values fall outside of a given tolerance
    of the mean peak centers across all tubes.
    
    Tubes are defined as have a bad fit if the absolute difference
    between the fitted peak centers for a specific tube and the 
    mean of the fitted peak centers for all tubes differ more than
    the threshold parameter.
    
    @param peakTable: the table containing fitted peak centers
    @param threshold: the tolerance on the difference from the mean value
    @return A list of expected peak positions and a list of indicies of tubes 
    to correct
    """
    n = len(peaksTable)
    num_peaks = peaksTable.columnCount()-1
    column_names = ['Peak%d'%(i) for i in range(1, num_peaks+1)]
    data = np.zeros((n, num_peaks))
    for i, row in enumerate(peaksTable):
        data_row = [row[name] for name in column_names]
        data[i,:] = data_row
    
    # data now has all the peaks positions for each tube
    # the mean value is the expected value for the peak position for each tube
    expected_peak_pos = np.mean(data,axis=0)
    
    #calculate how far from the expected position each peak position is
    distance_from_expected =  np.abs(data - expected_peak_pos)
    check = np.where(distance_from_expected > threshold)[0]
    problematic_tubes = list(set(check))
    print "Problematic tubes are: " + str(problematic_tubes)
    return expected_peak_pos, problematic_tubes

def cleanUpFit():
    """Clean up workspaces created by calibration fitting """
    for ws_name in ('TubePlot', 'RefittedPeaks', 'PolyFittingWorkspace',
                            'QF_NormalisedCovarianceMatrix', 
                            'QF_Parameters', 'QF_Workspace'):
        try:
            DeleteWorkspace(ws_name)
        except:
            pass

def correctMisalignedTubes(ws, calibrationTable, peaksTable, spec, idealTube, fitPar, threshold=10):
    """ Correct misaligned tubes due to poor fitting results 
    during the first round of calibration.
    
    Misaligned tubes are first identified according to a tolerance
    applied to the absolute difference between the fitted tube 
    positions and the mean across all tubes.
    
    The FindPeaks algorithm is then used to find a better fit 
    with the ideal tube positions as starting parameters 
    for the peak centers.
    
    From the refitted peaks the positions of the detectors in the
    tube are recalculated.
    
    @param ws: the workspace to get the tube geometry from
    @param calibrationTable: the calibration table ouput from running calibration
    @param peaksTable: the table containing the fitted peak centers from calibration
    @param spec: the tube spec for the instrument
    @param idealTube: the ideal tube for the instrument
    @param fitPar: the fitting parameters for calibration
    @param threshold: tolerance defining is a peak is outside of the acceptable range
    @return table of corrected detector positions
    """
    table_name = calibrationTable.name() + 'Corrected'
    corrections_table = CreateEmptyTableWorkspace(OutputWorkspace=table_name)
    corrections_table.addColumn('int', "Detector ID")
    corrections_table.addColumn('V3D', "Detector Position")
    
    mean_peaks, bad_tubes = findBadPeakFits(peaksTable, threshold)

    for index in bad_tubes:
        print "Refitting tube %s" % spec.getTubeName(index)
        tube_dets, _ = spec.getTube(index)
        actualTube = getPoints(ws, idealTube.getFunctionalForms(), fitPar, tube_dets)
        tube_ws = mtd['TubePlot']
        fit_ws = FindPeaks(InputWorkspace=tube_ws, WorkspaceIndex=0, 
                       PeakPositions=fitPar.getPeaks(), PeaksList='RefittedPeaks')
        centers = [row['centre'] for row in fit_ws]
        detIDList, detPosList = getCalibratedPixelPositions(ws, centers, idealTube.getArray(), tube_dets)
        
        for id, pos in zip(detIDList, detPosList):
            corrections_table.addRow({'Detector ID': id, 'Detector Position': V3D(*pos)})
            
        cleanUpFit()
    
    return corrections_table

corrected_calibration_table = correctMisalignedTubes(ws_corr, calibrationTable, peaks, spec, idealTube, fitPar)
ApplyCalibration(ws_corr, corrected_calibration_table)
