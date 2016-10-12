from mantid.simpleapi import *
import os

suffix = "-foc-h00"
integrate_suffix = "-int"

B = 7.85
T = [1.2,0.9,0.7,0.5,0.3,0.2,0.1,0.05]

integration_range = {"RangeLower": 16.2, "RangeUpper": 17.2}

run_numbers = []
run_numbers.append(35991)
run_numbers.extend(range(35979,35983))
run_numbers.append(35988)
run_numbers.extend(range(35983,35985))

def create_table(name, columns, num_rows):
    table = CreateEmptyTableWorkspace(OutputWorkspace=name)
    for i, c in enumerate(columns):
        table.addColumn('float', c) 
    return table

def generate_merged_name(runs, suffix):
    name = suffix 
    for r in runs:
        name = str(r) + "&" + name
    return name

def convert_run_to_name(run_number, suffix):
    convert_name = lambda r: str(r) + suffix
    if type(run_number) == list:
        return [convert_name(r) for r in run_number]
    else:
        return convert_name(run_number) 


column_names = ["T", "B", "int", "errors"]
table = create_table("Ei=3.5meV (0.219,0,0)", column_names, len(run_numbers))
run_names = map(lambda x: convert_run_to_name(x, suffix), run_numbers)

for i, run in enumerate(run_names):
    if type(run) == list:
        # generate name of OutputWorkspace for Plus function
        output_workspace = generate_merged_name(run, suffix)
        
        #average over each of the of the workspaces
        first_run = run[0]
        second_run = run[1]
        Plus(LHSWorkspace=first_run, RHSWorkspace=second_run, OutputWorkspace=output_workspace)
        if len(run) > 2:
            for run_name in run[2:]:
                Plus(LHSWorkspace=output_workspace, RHSWorkspace=run_name, OutputWorkspace=output_workspace)
        Scale(InputWorkspace=output_workspace, OutputWorkspace=output_workspace, Factor=1.0/len(run) )
    else:
        output_workspace = run

    # finally, integrate the run
    integrated_workspace = run + integrate_suffix
    Integration(InputWorkspace=output_workspace, OutputWorkspace=integrated_workspace, **integration_range)
    w1=mtd[integrated_workspace]

    row = [ T[i], B, w1.readY(0), w1.readE(0) ]
    row = map(float, row)
    table.addRow(row)

#Plus(LHSWorkspace='35943-foc-h00', RHSWorkspace='35922-foc-h00', OutputWorkspace='test')
#Scale(InputWorkspace='test', OutputWorkspace='test', Factor=0.5)
