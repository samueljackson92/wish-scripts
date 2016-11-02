from tube_calib_fit_params import TubeCalibFitParams
from tube_calib import getCalibratedPixelPositions
from tube_spec import TubeSpec
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

# Tube correction parameters
correction_params = {
    'threshold': 10,    # tolerance for a good peak fit
    'n': 10                      # number of neighbouring tubes to use for interpolation
}

# ----------------------------------------------------------------------------------------------------

instrument = ws.getInstrument()
spec = TubeSpec(ws)
spec.setTubeSpecByString(instrument.getFullName())

# First calibrate all of the detectors
calibrationTable, peaks = tube.calibrate(ws, spec, lower_tube, funcForm, margin=15,
    outputPeak=True, fitPar=fitPar)

ApplyCalibration(ws_calib, calibrationTable)

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


def findTubeCenter(ws, tube):
    """ Find the center point of a tubeCalibrationCorrection
    
    @param ws: the workspace to get the instrument geometry from
    @param tube: the ordered list of detectors in the tube
    @return V3D for the center of the tube
    """
    det0 = ws.getDetector(tube[0])
    detN = ws.getDetector (tube[-1])
    d0pos,dNpos = det0.getPos(), detN.getPos()
    center = (dNpos+d0pos)*0.5
    return center


def findAdjacentTubes(index, tubeMap, spec, n=6):
    """ Find tubes adjacent to the current index
    
    This makes the assumption that tubes are ordered spatially according to
    there index which might be incorrect!
    
    If a tube is near the lower/upper range of tubes then the full set of may
    not be used.
    
    @param index: the index of tube to find neighbours for
    @param spec: the tube spec for an instrument
    @n: number of neighbours to use in averaging
    @return a list of neighbouring tubes
    """
    # this is dodgy because we're assuming tubes with adjacent indicies are 
    # spatially related.
    offset = n / 2
    name = spec.getTubeName(index)
    index = int(name[-3:])
    adjacent_indicies = np.arange(index-offset, index+offset+1)
    
    neighbours = []
    for i in adjacent_indicies:
        key = name[:-3] + str(i).zfill(3)
        if i != index and i > 0 and i < spec.getNumTubes() and key in tubeMap:
            neighbours.append(tubeMap[key])

    return [spec.getTube(t)[0] for t in neighbours]


def interpolateCorrectPositions(ws, dets, neighbours):
    """ Calculate the correct position for a tube from its
    neighbouring tubes
    
    @param ws: the workspace to correct tubes in
    @param dets: list of detectors for single tube to correct
    @param neighbours: list of neighbouring tubes to interpolate with
    @return a list of corrected detector ids and a list of corrected positions
    """
    
    centers = np.array([findTubeCenter(ws, t) for t in neighbours])
    center_avg = centers.mean(axis=0)
    
    npos = np.array([[np.array(ws.getDetector(id).getPos()) for id in t] for t in neighbours])
    positions = np.array([ws.getDetector(d).getPos() for d in dets])
    ids = np.array([ws.getDetector(d).getID() for d in dets])
    
    positions = npos.mean(axis=0)

    return ids, positions


def tubeCalibrationCorrection(ws, peaksTable, calibrationTable, spec, threshold=10, n=6):
    """ Perform corrections to an already calibrated set of tubes.
    
    This will find tubes which are incorrectly aligned after a tube calibration. 
    The positions of the poorly fitted tubes will then be interploated from the 
    positions of the surronding tubes.
    
    This will return a table workspace containing corrected detector positions
    based on the interpolated positions of adjacent tubes which can be applied
    using ApplyCalibration
    
    @param ws: the workspace to correct calibrated tubes for
    @param peaksTable: the table of fitted peak centers from tube calibration
    @param calibrationTable: the table of calibrated detectors from tube calibration
    @param spec: the tube spec for the instrument
    @param threshold: the threshold to use to decide if tubes are bad
    @param n: the number of neighbouring tubes to use to interpolate the position
    @return a table workspace containing corrected detector positions
    """   
    table_name = calibrationTable.name() + 'Corrected'
    corrections_table = CreateEmptyTableWorkspace(OutputWorkspace=table_name)
    corrections_table.addColumn('int', "Detector ID")
    corrections_table.addColumn('V3D', "Detector Position")
    
    mean_peaks, bad_tubes = findBadPeakFits(peaksTable, threshold)

    print "Correcting badly fitted tubes"

    tubeMap = {}
    for index in range(1, spec.getNumTubes()+1):
        name = spec.getTubeName(index)
        tubeMap[name] = index
        
    for index in bad_tubes:
        print "Correcting tube %s" % spec.getTubeName(index)
        dets, skipped = spec.getTube(index)

        tubes = findAdjacentTubes(index, tubeMap, spec, n)
        ids, positions = interpolateCorrectPositions(ws, dets, tubes)
        
        for id, pos in zip(ids, positions):
            corrections_table.addRow({'Detector ID': id, 'Detector Position': V3D(*pos)})

    return corrections_table

# Now correct any remaining outlying detectors using the average
corrected_calibration_table = tubeCalibrationCorrection(ws_corr, peaks, calibrationTable, spec, **correction_params)
        
ApplyCalibration(ws_corr, corrected_calibration_table)