import pandas as pd

def load_timestamps(file):
    df = pd.read_csv(file, index_col = 0)
    df.index.name = 'timestamp'
    df = df.reset_index()
    df['timestamp'] = pd.to_datetime(df.timestamp)
    return df