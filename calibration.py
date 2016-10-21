from tube_calib_fit_params import TubeCalibFitParams
from tube_spec import TubeSpec
import numpy as np
import tube
#run_number = 'WISH00025383' # 9 lines
run_number = 'WISH00030541'


# load your data and integrate it
ws = LoadRaw(run_number+".raw", OutputWorkspace=run_number)
ws = CropWorkspace(ws, 6000, 99000, OutputWorkspace=run_number)
ws = Integration(ws, 6000, 99000, OutputWorkspace=run_number)

# remove any calibration parameters (for reference)
ws_uncalib = ws.clone()
empty_instr = LoadEmptyInstrument('/Users/samueljackson/git/mantid-main/instrument/WISH_Definition.xml')
CopyInstrumentParameters(empty_instr, ws_uncalib)

# definition of the parameters static for the calibration
#lower_tube = np.array([-0.41,-0.31,-0.21,-0.11,-0.02, 0.09, 0.18, 0.28, 0.39 ])
lower_tube = np.array([-274.81703361, -131.75052481,    0.,  131.75052481, 274.81703361])
upper_tube = np.array(lower_tube)
funcForm = 5*[1] # 5 gaussian peaks
margin = 20

spec = TubeSpec(ws)
spec.setTubeSpecByString('WISH')

fitPar = TubeCalibFitParams( [59, 161, 258, 353, 448])
fitPar.setAutomatic(True)
calibrationTable, peaks = tube.calibrate(ws, spec, lower_tube, funcForm, margin=15,
    outputPeak=True, fitPar=fitPar)

ApplyCalibration(ws,calibrationTable)

def analisePeakTable(pTable, peaksName='Peaks', threashold=10):
	print 'parsing the peak table'
	n = len(pTable)
	peaks = pTable.columnCount() -1
	peaksId = n*['']
	data = np.zeros((n,peaks))
	line = 0
	for row in pTable:
		data_row = [row['Peak%d'%(i)] for i in range(1,peaks+1)]
		data[line,:] = data_row
		peaksId[line] = row['TubeId']
		line+=1
	# data now has all the peaks positions for each tube
	# the mean value is the expected value for the peak position for each tube
	expected_peak_pos = np.mean(data,axis=0)
	print expected_peak_pos
	#calculate how far from the expected position each peak position is
	distance_from_expected =  np.abs(data - expected_peak_pos)
 
	Peaks = CreateWorkspace(range(n),distance_from_expected,NSpec=peaks, OutputWorkspace=peaksName)
	check = np.where(distance_from_expected > threashold)[0]
	problematic_tubes = list(set(check))
	print 'Tubes whose distance is far from the expected value: ', problematic_tubes
	return expected_peak_pos, problematic_tubes

a, b = analisePeakTable(peaks, 'peaksLow')