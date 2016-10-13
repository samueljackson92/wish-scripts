from mantid.simpleapi import *
import numpy as np

# Script Parameters
# ---------------------------------------------------------------------------------------

run_numbers = []
run_numbers.append(35991)
run_numbers.extend(range(35979,35983))
run_numbers.append(35988)
run_numbers.extend(range(35983,35985))

suffix = "-foc-h00"
integrate_suffix = "-int"

min_run = min(map(lambda x: x if type(x) == int else min(x), run_numbers))
max_run = max(map(lambda x: x if type(x) == int else max(x), run_numbers))
group_name = str(min_run) + '-' + str(max_run) + suffix + integrate_suffix

table_name = "Ei=3.5meV (0.219,0,0)"
log_names = ["MC_temp", "Tesl_setB"]
integration_range = {"RangeLower": 16.2, "RangeUpper": 17.2}

# ---------------------------------------------------------------------------------------

def create_table(name, columns, num_rows):
    """ Create an empty table workspace with the given columns """
    # build table with log names
    table = CreateEmptyTableWorkspace(OutputWorkspace=name)
    for i, c in enumerate(columns):
        table.addColumn('float', c)
        table.setPlotType(c, 1)
     
    # Add columns for data from workspace last
    table.addColumn('float', 'int')
    table.setPlotType('int', 2)
    table.addColumn('float', 'error')
    table.setPlotType('error', 5)
    return table

def convert_run_to_name(run_number, suffix):
    """ Convert a list of run numbers to workspace names
   
    The name will be <runno><suffix>. This can handle
    the case of sublists of run numbers.
    """
    convert_name = lambda r: str(r) + suffix
    if type(run_number) == list:
        return [convert_name(r) for r in run_number]
    else:
        return convert_name(run_number) 

def get_log(ws, name):
    """ Get a log from a workspace.
    
    If the log contains multiple values then the
    mean of the values will be returned.
    """
    logs = ws.getRun()
    prop = logs.getProperty(name)
    if isinstance(prop.value, np.ndarray):
        return prop.value.mean()
    else:
        return prop.value

table = create_table(table_name, log_names, len(run_numbers))
run_names = map(lambda x: convert_run_to_name(x, suffix), run_numbers)

output_names = []
for i, run in enumerate(run_names):
    if type(run) == list:
        # multiple runs, average over all of them
        output_workspace = '&'.join(run) + integrate_suffix
        Mean(','.join(run), OutputWorkspace=output_workspace)
    else:
        # single run, use name as is
        output_workspace = run

    #integrate the run
    integrated_workspace = output_workspace + integrate_suffix
    Integration(InputWorkspace=output_workspace, OutputWorkspace=integrated_workspace, **integration_range)
    w1=mtd[integrated_workspace]

    # add to table
    row = [get_log(w1, name) for name in log_names]
    row .extend([w1.readY(0), w1.readE(0) ])
    row = map(float, row)
    table.addRow(row)
    
    # add to workspace group
    output_names.append(integrated_workspace)
    
GroupWorkspaces(output_names, OutputWorkspace=group_name)

#Plus(LHSWorkspace='35943-foc-h00', RHSWorkspace='35922-foc-h00', OutputWorkspace='test')
#Scale(InputWorkspace='test', OutputWorkspace='test', Factor=0.5)
