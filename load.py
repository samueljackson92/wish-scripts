from mantid.simpleapi import *
import os.path

suffix = "-foc-h00"

run_numbers = []
run_numbers.append(35991)
run_numbers.extend(range(35979,35983))
run_numbers.append(35988)
run_numbers.extend(range(35983,35985))

data_path = os.path.join(os.path.expanduser('~'), 'data')

def load_single_run(name, data_path):
    file_name = os.path.join(data_path, name + '.nxs')
    Load(file_name, OutputWorkspace=name)

def load_runs(run_numbers, data_path):
    for run in run_numbers:
        if type(run) == list:
            [load_single_run(run_part, data_path) for run_part in run]
        else:
            load_single_run(run, data_path)

def convert_run_to_name(run_number, suffix):
    convert_name = lambda r: str(r) + suffix
    if type(run_number) == list:
        return [convert_name(r) for r in run_number]
    else:
        return convert_name(run_number) 

run_names = map(lambda x: convert_run_to_name(x, suffix), run_numbers)
load_runs(run_names, data_path)
