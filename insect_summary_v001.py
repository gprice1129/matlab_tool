import os
import re
from analyzergui import *
import analyzerglobals as ag
from math import floor, ceil, log
import shutil
import scipy.io
import scipy.signal
from scipy.io.wavfile import read
import numpy as np
import numpy.fft as fft
from tkFileDialog import askdirectory, askopenfilename
import calendar
import datetime as dt
import Constants
from Reader import Reader

# TODO

# Calculate total circadian rhythm over entire set of data
# Calculate average total of circadian rhythm over entire set of data
# Calculate wingbeat frequency distribution
# The above items are the three deliverables to the GUI
# Implement the calculateXYZ function

def main(path, gui, state):
    csv_reader = Reader(path)
    # If no files are found then report an error and abort
    if not csv_reader.file_names:
        gui.showError("File Error", "No .csv files found on path: " + path)
        return

    all_samples = csv_reader.readAll()

    # Calculate earliest and latest date
    lowerDate = dt.datetime(dt.MINYEAR, 1, 1, 0, 0, 0)
    upperDate = dt.datetime(dt.MAXYEAR, 12, 31, 23, 59, 59)
    earlyDate, lateDate = getDateRange(
        list(map(lambda x: x.metadata.time_info, all_samples.values())), 
        Constants.MIN_DATE, 
        Constants.MAX_DATE)

    # Generate timestamps
    earlyTimeStamp = earlyDate.strftime(Constants.STAMP_FORMAT)
    lateTimeStamp = lateDate.strftime(Constants.STAMP_FORMAT)
     
    # Get difference in dates
    deltaDate = lateDate - earlyDate
    deltaHours, deltaSeconds = divmod(deltaDate.total_seconds(), 3600)
    deltaMinutes, deltaSeconds = divmod(deltaSeconds, 60)

    # Scale sample data and convert to power spectrum
    for sample in list(all_samples.values()):
        if (sample.metadata.time_info < lowerDate or 
            sample.metadata.time_info > upperDate):
                continue
        scale(sample)
        print sample.metadata.source
        timeToPowerSpectrum(sample)
        main_freq = getMainFreq(sample, Constants.FS)
        if main_freq > Constants.MIN_FREQ and main_freq < Constants.MAX_FREQ:
            if sample.metadata.source == "8.csv":
                print("Main Freq: " + str(main_freq))
                complexityScore(sample.data, Constants.FS, main_freq) 
    return
                
        

     
    # Seperate data into insect occurances and noise
    sampleRate = read(directory + DELIM + files[0])[0]
    score = computeComplexityScore(allFFT)
    indexOfGood = []
    indexOfBad = []
    goodPath = directory + DELIM + "good"
    badPath = directory + DELIM + "bad"
    if os.path.isdir(goodPath):
        shutil.rmtree(goodPath)
    if os.path.isdir(badPath):
        shutil.rmtree(badPath)
    createDirectory(directory, "good")
    createDirectory(directory, "bad")
    
    allFFTGood = []
    allStartIndexGood = []
    allEndIndexGood = []
    allFFTBad = []
    allStartIndexBad = []
    allEndIndexBad = []
    indexOfGood = []
    indexOfBad = []
    
    for i in range(len(score)):
        if score[i] >= state.complexityThreshold:
            indexOfGood.append(i)
            shutil.copy(directory + DELIM + files[i], goodPath)
            allFFTGood.append(allFFT[i])
            allStartIndexGood.append(allStartIndex[i])
            allEndIndexGood.append(allEndIndex[i])
        else:
            indexOfBad.append(i)
            shutil.copy(directory + DELIM + files[i], badPath)
            allFFTBad.append(allFFT[i])
            allStartIndexBad.append(allStartIndex[i])
            allEndIndexBad.append(allEndIndex[i])

    allFFTGood, allStartIndexGood, allEndIndexGood = convertToArray(
        list([allFFTGood, allStartIndexGood, allEndIndexGood])) 
    saveFFT(goodPath, allFFTGood, allStartIndexGood, allEndIndexGood)

    allFFTBad, allStartIndexBad, allEndIndexBad = convertToArray(
        list([allFFTBad, allStartIndexBad, allEndIndexBad]))
    saveFFT(badPath, allFFTBad, allStartIndexBad, allEndIndexBad)

    if allFFTGood == []:
        gui.showMessage("Data Report", 
                        "All data on path: " + directory +
                        "Was found to be noise.\n\n." +
                        "You may try reducing the complexity threshold for " +
                        "better results")
        return
    # Compute plots 
    allWBF = computeWBF(goodPath, allFFTGood, sampleRate)
    minWBF = np.amin(allWBF)
    maxWBF = np.amax(allWBF)
    meanWBF = np.mean(allWBF)
    stdWBF = np.std(allWBF)

    numFilesAccepted = len(allStartIndexGood)
    numFilesRejected = len(allStartIndexBad)
    numBins = int(ceil(numFilesAccepted/10.0))
   
    circadianData = computeCircadianData(goodPath)
    gui.plotWingBeat(gui.histogram, allWBF, minWBF, maxWBF, meanWBF, stdWBF)
    gui.plotCircadian(gui.circadian, circadianData)
    gui.drawFigure(gui.histogram)
    gui.drawFigure(gui.circadian)
         
    #gui.write(outputString)
  
# Supporting function definitions

###############################################################################
# Gets the earlist and latest date of files at a given path assuming the
# following format for the filenames: 
#               [year][month][day]-[hour]_[minute]_[second]
#

# Parameters
# path: The path to the directory to search for files
# lowerDate: The lower bound on the date the function will consider
# upperDate: The upper bound on the date the function will consider
#
# Output
# Returns the earliest and latest date

def getDateRange(dates, lowerDate, upperDate):
    dates = list(filter(lambda x: x > lowerDate and x < upperDate, dates))
    #TODO: Filter the files here based on the dates
    dates.sort()
    return (dates[0], dates[len(dates) - 1])

###############################################################################

###############################################################################
# Return the scaled the signal data for a given sample

# Parameters
# sample: A sample to be scaled

# Output
# None

def scale(sample):
    sample.data -= np.mean(sample.data, dtype=np.float32)
    sample.data /= np.amax(np.absolute(sample.data))
          
###############################################################################

###############################################################################
# Returns sample data converted from a time-domain signal into a power
# spectrum using fast Fourier transform (FFT)

# Parameters
# sample: A sample in the time-domain

# Output
# None

def timeToPowerSpectrum(sample):
    sample_size = len(sample.data)
    NFFT = 2**nextPower2(sample_size)*4 # Can be optimized out
    power_spectrum = fft.fft(sample.data, NFFT) 
    power_spectrum = np.absolute(power_spectrum[0:NFFT/2+1])**2
    power_spectrum[1:-1] = power_spectrum[1:-1]*2
    power_spectrum = power_spectrum/NFFT
    power_spectrum = smooth(power_spectrum, 9)
    sample.data = power_spectrum

###############################################################################

###############################################################################
# Returns the next power of 2 that is greater than or equal to the given
# value

# Parameters
# n: A number

# Output
# power: The power of 2 such that 2^power >= n

def nextPower2(n):
    return int(ceil(log(n, 2)))

###############################################################################

###############################################################################
# Smooths the given data using a moving average filter with a span of 5

# Parameters
# data: A numpy array of data points 
# span: The span of numbers to average per data point

# Output
# smoothed_data: A numpy array of data points after applying the filter 

def smooth(data, span):
    if (data.size < 3): return data
    if (span % 2 == 0): span -= 1
    smoothed_data = np.zeros(data.size, dtype=np.float32)
    # Handle boundary data points
    cur_l = 0
    cur_r = -1
    left_bound = cur_l + 1
    right_bound = cur_r - 1
    smoothed_data[cur_l] = data[cur_l]
    smoothed_data[cur_r] = data[cur_r]
    stop_i = span / 2
    while cur_l < stop_i:
        smoothed_data[cur_l+1] = (
            smoothed_data[cur_l] + data[left_bound] + data[left_bound+1])
        smoothed_data[cur_r-1] = (
            smoothed_data[cur_r] + data[right_bound] + data[right_bound-1])
        cur_l += 1
        cur_r -= 1
        left_bound += 2
        right_bound -= 2
    divisor = 1.0
    for i in range(stop_i):
        smoothed_data[i] /= divisor
        smoothed_data[-i - 1] /= divisor
        divisor += 2.0 
    # Handle valid data points
    smoothed_data[stop_i:-stop_i] = np.convolve(
        data, np.ones((span,))/span, mode='valid')
    return smoothed_data 

###############################################################################

###############################################################################
# Gets the main wingbeat frequency for a sample 

# Parameters
# :sample: (Sample) An instance of sample data
# :fs: (int) Sample rate?

# Output
# :main_freq: (int) The main wing beat frequency for the sample 
def getMainFreq(sample, fs):
    data = sample.data
    interval = fs / 2.0 / (len(data) - 1)
    starting = 100
    start_idx = int(starting / interval)
    bandwidth_idx = int(100 / interval)
    bw_idx = int(75 / interval)
    max_idx, maxpow = getMax(data[start_idx - 1:])
    max_idx += start_idx - 1
    max_freq = (max_idx - 1) * interval
    main_freq = max_freq
    if main_freq > 200:
        data[int(max_idx) - bandwidth_idx - 1:] = 0  
        half_mid = int(max_idx / 2)
        front = half_mid - bw_idx
        back = half_mid + bw_idx
        max_idx2, maxpow2 = getMax(data[start_idx - 1:]) 
        max_idx2 += start_idx - 1
        if (max_idx2 > front and max_idx2 < back and
            maxpow2 > max(data[front - 1], data[back - 1]) * 1.5):
            max_idx = int(max_idx / 2) 
            half_freq_pow = max(data[max_idx - 1], data[max_idx])
            if (half_freq_pow >= maxpow / 10):
                main_freq = max_freq / 2
    return main_freq
###############################################################################

###############################################################################
# Utility function for repeated use in getMainFreq function
#
# Parameters
# :data: (np.array) Sample data
#
# Output
# :max_idx: The location of the max index
# :maxpow: The maximum value at max_idx

def getMax(data):
    max_idx = np.argmax(data)
    maxpow = data[int(max_idx)]
    return max_idx + 1, maxpow
   
###############################################################################

###############################################################################
# Get the complexity score of the data
#
# Parameters
# :spect: The frequency data for one sample
# :fs: Sample rate?
# :main_freq: The main frequency of the sample data
#
# Output
# :score: The complexity score of the sample

def complexityScore(spect, fs, main_freq):
    interval = fs / 2.0 / (len(spect) - 1)
    bandwidth = 50
    main_idx = int(main_freq / interval) + 1
    idx_bandwidth = int(ceil(bandwidth / interval))
    filter1 = np.zeros(len(spect), dtype=bool)
    end_idx = int(2500 / interval)
    for i in range(1, (end_idx / main_idx) + 1):
        cur_min = max(1, main_idx * i - idx_bandwidth)
        cur_max = min(end_idx, main_idx * i + idx_bandwidth)
        filter1[cur_min - 1 : cur_max] = True 
    start_idx = int(100 / interval) + 1
    filter2 = np.ones(len(spect), dtype=bool)
    filter2[:start_idx - 1] = False 
    filter2[end_idx:len(spect)] = False
    for i in range(0,len(spect),32):
        print(spect[i:i+32])
    return np.sum(spect[filter1]) / np.sum(spect[filter2]) 

###############################################################################
# Computes the circadian rhythm data for files in a directory given by path.
# Assumes the files are in the following format: 
#                      [year][month][day]-[hour]_[minute]_[second]
#
# Parameters
# path: The path to the directory of files to analyze 
#
# Output
# returns an array of occurances when insect data occured for 24 hours 

def computeCircadianData(path):
    files = getFileNames(path, ".wav")     
    dates = list(map(lambda f: fileToDate(f), files))
    occurances = np.zeros(Constants.MIN_IN_DAY)
    earlyDate = dates[0]
    lateDate = dates[len(dates) - 1]
    for date in dates:
        if (date < earlyDate):
            earlyDate = date
        if (date > lateDate):
            lateDate = date
        time = date.time()
        minute = time.hour * 60 + time.minute 
        occurances[minute] += 1
    deltaDate = lateDate - earlyDate
    deltaHours, _ = divmod(deltaDate.total_seconds(), 3600)
    numDays = (deltaHours / 24) + 1
    return occurances / numDays 
    
    
###############################################################################

gui = AnalyzerWindow(tk.Tk(), AnalyzerState(), main)
gui.start()
