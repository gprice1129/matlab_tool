import os
import re
from math import ceil
import shutil
import soundfile as sf
import scipy.stats
import scipy.io
import scipy.signal
import numpy as np
import numpy.fft
import Tkinter as tk 
from tkFileDialog import askdirectory, askopenfilename
import tkMessageBox
import calendar
import datetime as dt
import matplotlib

matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

MONTHS = dict((v, k) for k, v in enumerate(calendar.month_abbr))
FFT_ID = "all_fft"
START_ID = "all_start_index"
END_ID = "all_end_index"
WBF_ID = "all_WBF"
STAMP_FORMAT = "%m/%d/%Y at %I:%M:%S %p"
HRS_IN_DAY = 24
MIN_IN_DAY = 1440

#Parameters

minWingBeat = 400
maxWingBeat = 1800
slidingWindow = 1024
stepSize = 128
complexityThreshold = 0.00007
interval = 5

class AnalyzerGui:
    def __init__(self, root):
        self.master = root
        self.path = os.getcwd()
        self.master.title("Insect analyzer")

        self.pathLabel = tk.Label(self.master, text="Path to data directory")
        self.pathLabel.grid(row=0, column=0)

        self.pathEntry = tk.Entry(self.master, width=50)
        self.pathEntry.insert(0, self.path)
        self.pathEntry.grid(row=0, column=1)

        self.pathButton = tk.Button(self.master, anchor="se",
                                    text="Browse...", command=self.askPath)
        self.pathButton.grid(row=0, column=2)

        self.runButton = tk.Button(self.master, text="Run",
                                   command=self.run)
        self.runButton.grid(row=1, column=0)

#        self.outputMsg = tk.Message(self.master,
#                                    text="Data statistics will be output here")
#        self.outputMsg.grid(row=2, column=0, columnspan=2, sticky="w")

        self.histogram = self.setupFigure((6, 4), 100, 3, 0, columnspan=3)
        self.gaussian = self.setupFigure((6, 4), 100, 3, 3, columnspan=3)
        self.circadian = self.setupFigure((12, 4), 100, 4, 0, columnspan=6)

    def start(self):
        self.master.mainloop()

    def askPath(self):
        self.path = askdirectory()
        self.pathEntry.delete(0, tk.END)
        self.pathEntry.insert(0, self.path)
    
    def write(self, output):
        self.outputMsg.configure(text=output)        
    
    def run(self):
        try:
            self.path = self.pathEntry.get() 
            main(self.path, self)
        except OSError as e:
            tkMessageBox.showerror("Directory Error",
                                   "Error loading directory: " + self.path)    

    def setupFigure(self, size, dpi, row, column, rowspan=1, columnspan=1):
        figure = Figure(figsize=size, dpi=dpi, tight_layout=True)
        canvas = FigureCanvasTkAgg(figure=figure, master=self.master)
        canvas.show()
        canvasWidget = canvas.get_tk_widget()
        canvasWidget.grid(row=row, column=column,
                         rowspan=rowspan, columnspan=columnspan)
        return figure

    def plotWingBeatH(self, figure, data):
        bins = [x for x in range(minWingBeat, 
                                 maxWingBeat + 200 + 1, 200)]
        data.sort()
        figure.clf()
        axes = figure.add_subplot(111)
        axes.hist(data, bins=bins, linewidth=1, edgecolor='k')
        axes.set_xlabel("Wing Beat Frequency")
        axes.set_ylabel("Total Occurances") 
 
    def plotWingBeatG(self, figure, data, mean, std):
        data.sort()
        figure.clf()
        axes = figure.add_subplot(111)
        gaussian = scipy.stats.norm.pdf(data, mean, std)
        axes.plot(data, gaussian, '-o')
        axes.set_xlabel("Wing Beat Frequency")
        axes.set_ylabel("Percentage of Total Occurances") 
     
    def plotCircadian(self, figure, data):
        figure.clf()
        axes = figure.add_subplot(111)
        axes.plot(np.arange(MIN_IN_DAY), data)
        axes.set_xticks(np.arange(0, MIN_IN_DAY + 1, MIN_IN_DAY / HRS_IN_DAY ))
        axes.set_xticklabels(np.arange(0, HRS_IN_DAY + 1))
        axes.set_xlabel("Hour in the Day")
        axes.set_ylabel("Average Occurance per Day")

    def drawFigure(self, figure):
        figure.canvas.draw()

def main(directory, gui):
    #Get the directory containing audio files 
    getOSDelim()
    #TODO: 
    #       Calculate earliest and latest date [DONE]
    #       Generate timestamps 
    #       Get difference in dates [DONE]
    #       Try to load existing FFT data and check that there is no new data [DONE]
    #       Otherwise generate FFT file
    #       Seperate into "Good" and "Bad" data
    #       Compute WBF of "Good" data

    # Calculate earliest and latest date
    lowerDate = dt.datetime(dt.MINYEAR, 1, 1, 0, 0, 0)
    upperDate = dt.datetime(dt.MAXYEAR, 12, 31, 23, 59, 59)
    earlyDate, lateDate = getDateRange(directory, lowerDate, upperDate)
    earlyTimeStamp = earlyDate.strftime(STAMP_FORMAT)
    lateTimeStamp = lateDate.strftime(STAMP_FORMAT)
    # Generate timestamps
    
     
    # Get difference in dates
    deltaDate = lateDate - earlyDate
    deltaHours, deltaSeconds = divmod(deltaDate.total_seconds(), 3600)
    deltaMinutes, deltaSeconds = divmod(deltaSeconds, 60)

    # Try to load existing FFT data and check that there is no new data
    recalculate = False
    files = getFileNames(directory, ".wav")
    try:
        allFFTData = scipy.io.loadmat(directory + DELIM + FFT_ID + ".mat")
        allFFT = allFFTData[FFT_ID]
        if len(allFFT) == len(files):
            print("Checking FFT files... good")
            print("Attempting load on all_start_index.mat and all_end_index.mat")
            allStartIndexData = scipy.io.loadmat(directory + DELIM + 
                                                 START_ID + ".mat")
            allEndIndexData = scipy.io.loadmat(directory + DELIM +
                                               END_ID + ".mat")
            allStartIndex = allStartIndexData[START_ID][0]
            allEndIndex = allEndIndexData[END_ID][0] 
        else: recalculate = True
    except IOError:
       recalculate = True 
    finally:
        if recalculate:
            # Otherwise generate FFT file
            allFFT, allStartIndex, allEndIndex = processInBatch_1_1(directory,
                                                                    slidingWindow,
                                                                    stepSize,
                                                                    minWingBeat,
                                                                    maxWingBeat)
    
    sampleRate = sf.read(directory + DELIM + files[0])[1]
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
        if score[i] >= complexityThreshold:
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

    allWBF = computeWBF(goodPath, allFFTGood, sampleRate)
    minWBF = np.amin(allWBF)
    maxWBF = np.amax(allWBF)
    meanWBF = np.mean(allWBF)
    stdWBF = np.std(allWBF)

    numFilesAccepted = len(allStartIndexGood)
    numFilesRejected = len(allStartIndexBad)
    numBins = int(ceil(numFilesAccepted/10.0))
   
    outputString = "You are investigating a folder named '" + \
                   directory.split(DELIM)[-1] + "'.\n"
    outputString += "There are " + str(len(files)) + " wav files." + \
                    "They are sampled at " + str(sampleRate) + " Hz.\n" 
    outputString += "The earliest time stamp is " + earlyTimeStamp + \
                    ", the latest is " + lateTimeStamp + ".\n" 
    outputString += "This indicates a time span of " + str(int(deltaHours)) + \
                    " hours, " + str(int(deltaMinutes)) + " minutes and " + \
                    str(int(deltaSeconds)) + " seconds.\n"
    outputString += str(numFilesRejected) + " files have been rejected at " + \
                    "noise.\n"
    outputString += str(numFilesAccepted) + " files have been accepted as " + \
                    "containing least one insect encounter.\n" 
    outputString += "Considering only the " + str(numFilesAccepted) + \
                    " good files, we observe the following statistics for the WBF.\n"
    outputString += "Minimum WBF: " + str(minWBF) + ".\n"
    outputString += "Maximum WBF: " + str(maxWBF) + ".\n"
    outputString += "Average WBF: " + str(meanWBF) + ".\n"
    outputString += "Standard Deviation: " + str(stdWBF) + ".\n"
    outputString += "This program uses the following default parameters " + \
                    "which can be changed in the first few lines of this " + \
                    "program.\n"
    outputString += "minWingBeat = " + str(minWingBeat) + " (any file with " + \
                    "a fundamental frequency below this is considered noise).\n"
    outputString += "maxWingBeat = " + str(maxWingBeat) + " (any file with " + \
                    "a fundamental frequency above this is considered noise).\n"
    outputString += "slidingWindow = " + str(slidingWindow) + " (the size " + \
                    " of snippets to examine).\n"
    outputString += "stepSize = " + str(stepSize) + " (the jump between " + \
                    "snippets).\n"
    outputString += "complexityThreshold = " + str(complexityThreshold) + \
                    " (the higher this value the more aggressively the " + \
                    "script is when labeling files has noise).\n"
    outputString += "interval = " + str(interval) + " (used to smooth the " + \
                    "data for the circadian rhythm plot. This value is " + \
                    "measured in minutes).\n"

    circadianData = computeCircadianData(goodPath)
    gui.plotWingBeatH(gui.histogram, allWBF)
    gui.plotWingBeatG(gui.gaussian, allWBF, meanWBF, stdWBF)
    gui.plotCircadian(gui.circadian, circadianData)
    gui.drawFigure(gui.histogram)
    gui.drawFigure(gui.gaussian)
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
    month = MONTHS[month] #TODO: This is really unsafe, should do error checking
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
    scipy.io.savemat(path + DELIM + FFT_ID, {FFT_ID: allFFT})
    scipy.io.savemat(path + DELIM + START_ID, {START_ID: allStartIndex})
    scipy.io.savemat(path + DELIM + END_ID, {END_ID: allEndIndex}) 
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
# TODO: Add output

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

    data, sampleRate = sf.read(filePath)
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
        allFFT = allFFTFile[FFT_ID]

    for fft in allFFT:
        loc = np.argmax(fft)
        freqVals = sampleRate * np.arange(NFFT / 2) / NFFT;    
        allWBF.append(np.round(freqVals[loc]) + 1)

    allWBF = np.array(allWBF)
    scipy.io.savemat(path + DELIM + WBF_ID, {WBF_ID: allFFT})
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
# TODO: WHAT?

def computeCircadianData(path):
    files = getFileNames(path, ".wav")     
    dates = list(map(lambda f: fileToDate(f), files))
    dates.sort()
    currentDate = dates[0].date
    occurances = np.zeros(MIN_IN_DAY)
    numDays = 1
    for date in dates:
        if date.date < currentDate:
            numDays += 1    
        time = date.time()
        minute = time.hour * 60 + time.minute 
        occurances[minute] += 1
    return occurances / float(numDays) 
    
    
###############################################################################

rootWindow = tk.Tk()
gui = AnalyzerGui(rootWindow)
gui.start()
