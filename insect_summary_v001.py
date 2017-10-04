import os
import re
#from analyzergui import *
#import analyzerglobals as ag
from math import ceil, log
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

#TODO: Bug: Doesn't correctly choose to generate new files if parameters change
#      Bug: Doesn't correctly handle the case where user chooses a directory
#           with no data files
#      Feature: Center the parameter window when it is opened
#      Feature: Add dusk and dawn parameters and mark them on the plot

def main(path, gui, state):
    print smooth(np.array([10,15,22,89,11,2,1,99,1000,3,21]))
    return
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

    # Normalize sample data and convert to power spectrum
    for file_name in csv_reader.file_names:
        scale(all_samples[file_name])
        timeToPowerSpectrum(all_samples[file_name], file_name)
    return   

    for file_name in csv_reader.file_names:
        print file_name
        scale(all_samples[file_name])
        print(all_samples[file_name].data[:5])
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
# Creates a directory with a given name in a given path

# Parameters
# path: The path to where the directory should be created
# directoryName: The name of the directory to be created

# Output
# None

def createDirectory(path, directoryName):
    directoryPath = path + DELIM + directoryName
    try:
        os.makedirs(directoryPath)
    except OSError:
        if not os.path.isdir(directoryPath):
            raise
        else: pass

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

def timeToPowerSpectrum(sample, file_name):
    print file_name
    sample_size = len(sample.data)
    NFFT = 2**nextPower2(sample_size)*4 # Can be optimized out
    power_spectrum = fft.fft(sample.data, NFFT) 
    power_spectrum = np.absolute(power_spectrum[0:NFFT/2+1])**2
    power_spectrum[1:-1] = power_spectrum[1:-1]*2
    power_spectrum = power_spectrum/NFFT
    power_spectrum = smooth(power_spectrum)
    print power_spectrum[:5]
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
    if (data.size < 3) return data
    if (span % 2 != 0): span -= 1
    smoothed_data = np.zeros(data.size, dtype=np.float32)
    # Handle boundary data points
    cur_l = 0
    cur_r = -1
    left_bound = cur_l + 1
    right_bound = cur_r - 1
    smoothed_data[cur_l] = data[cur_l]
    smoothed_data[cur_r] = data[cur_r]
    stop_i = (span / 2 ) - 1
    while cur_l < stop_i:
        smoothed_data[cur_l+1] = (
            smoothed_data[cur_l] + data[left_bound] + data[left_bound+1])
        smoothed_data[cur_r-1] = (
            smoothed_data[cur_r] + data[right_bound] + data[right_bound-1])
        cur_l += 1
        cur_r -= 1
        left_bound += 2
        right_bound -= 2
    # Handle valid data points
    smoothed_data[2:-2] = np.convolve(data, np.ones((5,))/5, mode='valid')
    return smoothed_data 

###############################################################################

###############################################################################
# Computes the wing beat frequencies for the given frequency data 

# Parameters
# path: The path to the directory of the frequency data. This is only used
#       if no frequency data is passed in.
# allFFT: The frequency data. If this is None then an attempt will be made to
#         load the frequency data from the given path
# sampleRate: The rate the frequency data was sampled at.

# Output
# allWBF: The wing beat frequencies for all the frequency data provided
def computeWBF(path, allFFT, sampleRate):
    NFFT = 1024
    allWBF = []

    for fft in allFFT:
        loc = np.argmax(fft)
        freqVals = sampleRate * np.arange(NFFT / 2) / NFFT;    
        allWBF.append(np.round(freqVals[loc]) + 1)

    allWBF = np.array(allWBF)
    return allWBF

###############################################################################

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
