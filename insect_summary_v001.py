import os
import re
from analyzergui import *
import analyzerglobals as ag
from math import ceil
import shutil
import scipy.io
import scipy.signal
from scipy.io.wavfile import read
import numpy as np
import numpy.fft
from tkFileDialog import askdirectory, askopenfilename
import calendar
import datetime as dt

#TODO: Bug: Doesn't correctly choose to generate new files if parameters change
#      Bug: Doesn't correctly handle the case where user chooses a directory
#           with no data files
#      Feature: Center the parameter window when it is opened
#      Feature: Add dusk and dawn parameters and mark them on the plot

def main(directory, gui, state):
    getOSDelim()

    files = getFileNames(directory, ".wav")
    # If no files are found then report an error and abort
    if files == []:
        gui.showError("File Error", "No .wav files found on path: " + directory)
        return

    # Calculate earliest and latest date
    lowerDate = dt.datetime(dt.MINYEAR, 1, 1, 0, 0, 0)
    upperDate = dt.datetime(dt.MAXYEAR, 12, 31, 23, 59, 59)
    earlyDate, lateDate = getDateRange(directory, lowerDate, upperDate)
    # Generate timestamps
    earlyTimeStamp = earlyDate.strftime(ag.STAMP_FORMAT)
    lateTimeStamp = lateDate.strftime(ag.STAMP_FORMAT)
     
    # Get difference in dates
    deltaDate = lateDate - earlyDate
    deltaHours, deltaSeconds = divmod(deltaDate.total_seconds(), 3600)
    deltaMinutes, deltaSeconds = divmod(deltaSeconds, 60)

    # Try to load existing FFT data and check that there is no new data
    recalculate = False
    try:
        allFFTData = scipy.io.loadmat(directory + DELIM + ag.FFT_ID + ".mat")
        allFFT = allFFTData[ag.FFT_ID]
        if len(allFFT) == len(files) and not gui.state.hasChanged():
            print("Checking FFT files... good")
            print("Attempting load on all_start_index.mat and all_end_index.mat")
            allStartIndexData = scipy.io.loadmat(directory + DELIM + 
                                                 ag.START_ID + ".mat")
            allEndIndexData = scipy.io.loadmat(directory + DELIM +
                                               ag.END_ID + ".mat")
            allStartIndex = allStartIndexData[ag.START_ID][0]
            allEndIndex = allEndIndexData[ag.END_ID][0] 
        else: recalculate = True
    except IOError:
       recalculate = True 
    finally:
        if recalculate:
            # Otherwise generate FFT file
            fftData = processInBatch_1_1(directory,
                                         state.slidingWindow,
                                         state.stepSize,
                                         state.minWingBeat,
                                         state.maxWingBeat)
            allFFT, allStartIndex, allEndIndex = fftData
                
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
# Sets the global delimiter based on the OS being used
#
# Parameters
# None
#
# Output
# None

def getOSDelim():
    global DELIM
    if os.name == 'nt': DELIM = "\\"
    else: DELIM = "/"
    
###############################################################################

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

def getDateRange(path, lowerDate, upperDate):
    files = getFileNames(path, '.wav')
    dates = list(map(lambda x: fileToDate(x), files))
    dates = list(filter(lambda x: x > lowerDate and x < upperDate, dates))
    #TODO: Filter the files here based on the dates
    dates.sort()
    return (dates[0], dates[len(dates) - 1])

###############################################################################

###############################################################################
# Saves a list of lists as numpy arrays and returns them.
#
# Parameters
# dataLists: A list of data that should be converted to numpy arrays
#
# Output
# arrayLists: A list of the data in numpy array form

def convertToArray(dataLists):
    arrayLists = []
    for dataList in dataLists:
        arrayLists.append(np.array(dataList))
    return arrayLists
    
###############################################################################

###############################################################################
# Converts a filename in the format:
#               [year][month][day]-[hour]_[minute]_[second]
# to a datetime object.
#
# Parameters
# filename: The filename to convert to a datetime object

def fileToDate(filename):
    year, month, day, hr, minute, sec = re.findall('\d+|[A-Z][a-z]+', filename);
    month = ag.MONTHS[month] #TODO: This is really unsafe, should do error checking
    year, day, hr, minute, sec = list(map(lambda x: int(x),
                                          [year, day, hr, minute, sec])) 
    return dt.datetime(year, month, day, hr, minute, sec)

###############################################################################

###############################################################################
# Gets all filenames with a given extension and returns them in a list

# Parameters
# path: The path to the directory to search for files
# extension: The extension to look for

# Output
# A list containing the filenames in the given path with the given extension

def getFileNames(path, extension):
    files = []
    for file in os.listdir(path):
        if file.endswith(extension):
            files.append(file)
    files.sort() 
    return files

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
# Save the FFT and associated indicies to disk

# Parameters
# path: The path to the directory to save the files to
# allFFT: The windows of FFT data where there is potential insect data
# allStartIndex: The starting index of where the potential insect data is
# allEndIndex: The ending index of where the potential insect data is

# Output
# Returns the values back as numpy arrays 

def saveFFT(path, FFTList, startIndexList, endIndexList):
    allFFT = np.array(FFTList)
    allStartIndex = np.array(startIndexList)
    allEndIndex = np.array(endIndexList)
    scipy.io.savemat(path + DELIM + ag.FFT_ID, {ag.FFT_ID: allFFT})
    scipy.io.savemat(path + DELIM + ag.START_ID, {ag.START_ID: allStartIndex})
    scipy.io.savemat(path + DELIM + ag.END_ID, {ag.END_ID: allEndIndex}) 
    return allFFT, allStartIndex, allEndIndex

###############################################################################

###############################################################################
# Process the signal for each file in 'directory' and preserve only the window
# corresponding to the insect. Set all other values to 0. Write the result in 
# the folder_processed directory.

# Get the FFT for each insect window within the frequence range from 1-2000.
# and writes it to a single file in the FFT directory.
# Each row of the resulting file will contain the FFT time series for one
# insect window. The first column of each row will be the class label.

# Gets the peak wingbeat frequency in the range 200-900 of the insect window
# and writes the results to a single file in the WBF folder. The resulting file
# has two columns. The first column is the class label, the second column is
# the peak wingbeat frequency.

# Parameters
# path: The path to the directory containing the signal data

# Output
# allFFT: All the FFT data aggregated together
# allStartIndex: The starting index for the insect region for each FFT datum
# allEndIndex: The ending index for the insect regsion for each FFT datum

def processInBatch_1_1(path, slidingWindow, stepSize, minWingBeat, maxWingBeat):
    
    FFTList = []
    StartIndexList = [] 
    EndIndexList = []

    fileNames = getFileNames(path, ".wav") 

    for file in fileNames:
        try:
            filePath = path + DELIM + file
            results = test_1_1(filePath, slidingWindow, stepSize,
                    minWingBeat, maxWingBeat)

            decision, startIndex, endIndex, fftWindow, fftWindowF, sampleRate = results
            
            FFTList.append(fftWindow)
            StartIndexList.append(startIndex)
            EndIndexList.append(endIndex)
        
        except RuntimeError as e:
            raise e
        except Exception as e:
            print(e)
            print("Cannot process file: " + file)
            print("Moving unprocessed file to 'cannot_process' directory")
        
            cannotProcessDir = path + DELIM + "cannot_process" + DELIM
            createDirectory(path, "cannot_process")
            
#            os.rename(path + DELIM + file, cannotProcessDir + file) 


    allFFT, allStartIndex, allEndIndex = convertToArray(
        list([FFTList, StartIndexList, EndIndexList]))
    saveFFT(path, allFFT, allStartIndex, allEndIndex) 
    return allFFT, allStartIndex, allEndIndex

###############################################################################

###############################################################################
# Test if a signal contains an insect region.

# If the signal has any of the following properties it is considered an in
# insect region:
#    1) The peak amplitude in the frequency range 400-1800 is greater than 0.2
#    2) The peak amplitude in the frequency range 400-1800 is greater than or
#       equal to 0.01, the peak amplitude between the frequency range 50-200
#       is less than 0.03, and the peak amplitude in the frequency range
#       1200-2000 is less than 0.03

# Parameters
# filePath: The path to a file containing signal data.
# decision: True if the signal contains the signal region, False otherwise.
# startIndex: The most likely starting index of the insect region of the.
#             signal. 

# Output
# decision: Insect classifier decision (UNUSED CURRENTLY)
# startIndex: The starting index of the insect region of the signal
# endIndex: The ending index of the insect region of the signal
# fftWindow: TODO 
# fftWindowF: TODO

def test_1_1(filePath, slidingWindowLength, stepSize, targetedFrequencyStart,
             targetedFrequencyEnd):

    sampleRate, data = read(filePath)
    data = data.astype(np.float32) / np.iinfo(data.dtype).max
    decision = 0
    startIndex = 0
    endIndex = len(data) - 1 
    fftWindow = 0
    fftWindowF = 0
    maxPeak = 0


    # Apply high pass filter
    order = 6
    frequencyCutoff = 200
    b, a = scipy.signal.butter(order,
            frequencyCutoff / (sampleRate / 2.0), 'high') 
    data = scipy.signal.lfilter(b, a, data)

    # Pad signal in case sliding window goes out of bounds
    signal = np.pad(data, ((0, slidingWindowLength)),
            "constant", constant_values = 0) 

    # TODO: More decriptive variables names
    for i in range(0, (len(signal) - slidingWindowLength), stepSize):
        window = signal[i:i + slidingWindowLength] 
        NFFT = 1024
        w_P2 = numpy.fft.rfft(window, NFFT) 
        w_P1 = w_P2*np.conjugate(w_P2)/float(NFFT*len(window))
        w_P1 = w_P1[0: (NFFT / 2)]
        w_f = (float(sampleRate) / NFFT) * np.arange(NFFT / 2)
        
        targeted_frequency = np.where((w_f > targetedFrequencyStart) &
                                      (w_f < targetedFrequencyEnd))
        if targeted_frequency[0].size == 0:
            raise RuntimeError("No valid insect data to process")

        peak = np.amax(w_P1[targeted_frequency]) 

        if peak > maxPeak:
            maxPeak = peak
            startIndex = i
            fftWindow = w_P1
            fftWindowF = w_f
    
    slidingWindowBoundary = startIndex + slidingWindowLength
    if len(data) > slidingWindowBoundary:
        endIndex = slidingWindowBoundary - 1

    # Get the frequency range from 20-2000 inclusive
    targetedRange = np.where((fftWindowF >= 20) &
                             (fftWindowF <= 2000))

    fftWindow = np.take(fftWindow, targetedRange)
    fftWindowF = np.take(fftWindowF, targetedRange)

    return (decision, startIndex, endIndex, fftWindow[0], fftWindowF[0], sampleRate)

###############################################################################

###############################################################################
# TODO: Give description of this function. What is meant by "complexity score"?
def computeComplexityScore(allFFT):
    score = []
    for fft in allFFT:
        complexity = 0
        sum = 0
        sqsum = 0
        lnsum = 0
        sc = 0
        for i in range(len(fft)):
            f = fft[i]
            sum += f
            sqsum += f * f
            lnsum += np.log(f)
            sc += (i + 1) * f
            if i > 0:
                fDif = f - fft[i - 1]
                complexity += (fDif * fDif) 
        complexity = np.sqrt(complexity)
        score.append(complexity) 
    return score

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

    if allFFT is None:
        filePath = askopenfilename(filetypes=[('all files', '.*'), 
                                              ('MAT files', '.mat')])
        allFFTFile = scipy.io.loadmat(filePath)
        allFFT = allFFTFile[ag.FFT_ID]

    for fft in allFFT:
        loc = np.argmax(fft)
        freqVals = sampleRate * np.arange(NFFT / 2) / NFFT;    
        allWBF.append(np.round(freqVals[loc]) + 1)

    allWBF = np.array(allWBF)
    scipy.io.savemat(path + DELIM + ag.WBF_ID, {ag.WBF_ID: allFFT})
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
    occurances = np.zeros(ag.MIN_IN_DAY)
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
