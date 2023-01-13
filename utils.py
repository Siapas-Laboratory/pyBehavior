import numpy as np
import pandas as pd

def load_mapping():
    params = np.load('params.npy', allow_pickle = True).item()
    map_file = params['map-file']
    # load the currently selected map file
    # TODO: need to wrap this in a try except clause to make sure 'port' is an existing  column
    # just in case people want to edit the csv in excel
    mapping = pd.read_csv(map_file)

    return params, map_file, mapping