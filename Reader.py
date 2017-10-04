import os
import numpy as np 
from Constants import DATA_POINTS_PER_FILE as NUM_POINTS
import Constants
from Metadata import Metadata
from Sample import Sample

class Reader:
    def __init__(self, path=None, extension=Constants.DEFAULT_EXTENSION):
        self.path = path
        self.file_names = []
        self.file_index = 0
        self.extension = extension 
        self.delim = self.getOSDelim()
        if self.path is not None:
            self.getFileNames(self.path)

    def setPath(self, new_path):
        self.path = new_path
        self.getFileNames(self.path)

    def getOSDelim(self):
        if os.name == Constants.NT:
            return '\\'
        return '/'

    def getFileNames(self, path=None):
        if path is None:
            return self.file_names

        self.file_names = []
        self.file_index = 0
        for f in os.listdir(path):
            if f.endswith(self.extension):
                self.file_names.append(f) 
        return self.file_names

    def parse_metadata(self, metadata):
        metadata = metadata.split('-')
        date = metadata[0]
        time = metadata[1]
        temperature = metadata[2]
        pressure = metadata[3]
        return Metadata(date, time, temperature, pressure)

    def read(self, file_name):
        data = np.empty(NUM_POINTS, dtype=np.float32) 
        file_path = self.path + self.delim + file_name
        with open(file_path) as f:
            for i in range(NUM_POINTS):
                line = f.readline()
                data[i] = (int(line)) 
            metadata = self.parse_metadata(f.readline()) 
        return Sample(data, metadata)

    def readNext(self):
        if self.file_index >= len(self.file_names):
            return None 

        sample = self.read(self.file_names[self.file_index])
        self.file_index += 1
        return sample

    def readAll(self):
        all_samples = {} 
        for file_name in self.file_names:
            sample = self.readNext()
            all_samples[file_name] = sample
        return all_samples 


