import os
import soundfile as sf
import scipy.io
import scipy.signal
import numpy as np
import numpy.fft
from Tkinter import Tk
from tkFileDialog import askdirectory, askopenfilename
import calendar

MONTHS = dict((v, k) for k, v in enumerate(calendar.month_abbr))

#Parameters

minWingBeat = 400
maxWingBeat = 1800
slidingWindow = 1024
stepSize = 128

#Get the directory containing audio files 
Tk().withdraw() # Disable a full GUI
directory = askdirectory()
processInBatch_1_1(directory, slidingWindow, stepSize, minWingBeat, maxWingBeat)


# Supporting function definitions

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
            filePath = path + "/" + file
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
        
            cannotProcessDir = path + "/cannot_process/"
            try:
                os.makedirs(cannotProcessDir)

            except OSError:
                if not os.path.isdir(cannotProcessDir):
                    raise
                else: pass

#            os.rename(path + "/" + file, cannotProcessDir + file) 


    allFFT = np.array(FFTList)
    allStartIndex = np.array(StartIndexList)
    allEndIndex = np.array(EndIndexList)
    scipy.io.savemat(path + "/FFT", {"FFT": allFFT})
    scipy.io.savemat(path + "/all_start_index", {"Start": allStartIndex})
    scipy.io.savemat(path + "/all_end_index", {"End": allEndIndex}) 
    return

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
# TODO: Give description of this function. What is WBF?
# TODO: Give better parameter names
def computeWBF(path, allFFT, sampleRate):
    NFFT = 1024
    allWBF = []

    if allFFT is None:
        filePath = askopenfilename(filetypes=[('all files', '.*'), 
                                              ('MAT files', '.mat')])
        allFFTFile = scipy.io.loadmat(filePath)
        allFFT = allFFTFile['FFT']

    for fft in allFFT:
        loc = np.argmax(fft)
        freqVals = sampleRate * np.arange(NFFT / 2) / NFFT;    
        allWBF.append(np.round(freqVals[loc]) + 1)

    allWBF = np.array(allWBF)
    scipy.io.savemat(path + "/all_WBF", {"WBF": allFFT})
    return allWBF

###############################################################################


