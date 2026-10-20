import numpy as np

class BatchHistogram:
    def __init__(self, size: int, durations: list, bins: int):
        self.SIZE = size
        self.DURATIONS = durations
        counts, bin_edges = np.histogram(durations / size, bins)
        self.COUNTS = counts
        self.BINS = bin_edges
        self.MEAN = np.mean(durations / size)
        self.STD = np.std(durations / size)