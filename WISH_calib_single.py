from tube import calibrate
ws = Load('WISH17701')
ws = Integration(ws)
known_pos = [-0.41,-0.31,-0.21,-0.11,-0.02, 0.09, 0.18, 0.28, 0.39 ]
peaks_form = 9*[1] # all the peaks are gaussian peaks
calibTable = calibrate(ws,'WISH/panel03',known_pos, peaks_form, rangeList=[3], plotTube=3)