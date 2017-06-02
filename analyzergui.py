import os
import re
import Tkinter as tk 
from tkFileDialog import askdirectory, askopenfilename
import tkMessageBox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import scipy.stats
import numpy as np
import analyzerglobals as ag

class BasicWindow:
    def showMessage(self, messageTitle, message):
        tkMessageBox.showinfo(messageTitle, message)

    def showError(self, errorTitle, error):
        tkMessageBox.showerror(errorTitle, error)

    def center(self, root):
        x = (root.winfo_screenwidth() - root.winfo_reqwidth()) / 2
        y = (root.winfo_screenheight() - root.winfo_reqheight()) / 2
        root.geometry("+%d+%d" % (x, y))

class AnalyzerWindow(BasicWindow):
    def __init__(self, root, analyzerState, mainFunction):
        self.master = root
        self.master.withdraw()
        self.master.update_idletasks()
        self.state = analyzerState 
        self.path = os.getcwd()
        self.master.title("Insect analyzer")
        self.parameterWindow = None
        self.mainFunction = mainFunction

        self.menubar = self.setupMenubar()

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

        self.histogram = self.setupFigure(size=(8, 4), dpi=100, row=3, column=0, 
                                          columnspan=6, rowspan=5)
        self.circadian = self.setupFigure(size=(8, 4), dpi=100, row=9, column=0, 
                                          columnspan=6, rowspan=5)
        self.center(self.master)
        self.master.deiconify()

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
            self.mainFunction(self.path, self, self.state)
            self.state.runSuccess()
        except OSError as e:
            self.showError("Directory Error",
                           "Error loading directory: " + self.path)    
        except RuntimeError as e:
            self.showError("Data Error",
                           "All data is outside of the parameter ranges")

    def setupFigure(self, size, dpi, row, column, rowspan=1, columnspan=1):
        figure = Figure(figsize=size, dpi=dpi, tight_layout=True)
        canvas = FigureCanvasTkAgg(figure=figure, master=self.master)
        canvas.show()
        canvasWidget = canvas.get_tk_widget()
        canvasWidget.grid(row=row, column=column,
                         rowspan=rowspan, columnspan=columnspan)
        return figure

    def setupMenubar(self):
        rootMenu = tk.Menu(self.master)
        
        fileMenu = tk.Menu(rootMenu, tearoff=0)
        fileMenu.add_command(label="Export", command=None)
        fileMenu.add_separator()
        fileMenu.add_command(label="Exit", command=None)
        
        editMenu = tk.Menu(rootMenu, tearoff=0)
        editMenu.add_command(label="Parameter Config",
                             command=self.openParameterWindow)
        
        helpMenu = tk.Menu(rootMenu, tearoff=0)
        helpMenu.add_command(label="Help", command=None)

        rootMenu.add_cascade(label="File", menu=fileMenu)
        rootMenu.add_cascade(label="Edit", menu=editMenu)
        rootMenu.add_cascade(label="Help", menu=helpMenu)

        self.master.config(menu=rootMenu)

    def openParameterWindow(self):
        if self.parameterWindow is not None:
            self.parameterWindow.window.lift()
        else: self.parameterWindow = ParameterWindow(self) 

    def plotWingBeat(self, figure, data, minimum, maximum, mean, std):
        bins = [x for x in range(self.state.minWingBeat, 
                                 self.state.maxWingBeat + 200 + 1, 200)]
        data.sort()
        figure.clf()
        gaussian = scipy.stats.norm.pdf(data, mean, std)
        axes = figure.add_subplot(1,2,1)
        axes.hist(data, bins=bins, linewidth=1, edgecolor='k', color='#1D1AB2')
        axes.set_title("Histogram of Wingbeat Frequency")
        axes.set_xlabel("Wing Beat Frequency")
        axes.set_ylabel("Total Occurances") 
        axes.text(0.65, 0.78, self.generateString(minimum, maximum, mean, std), 
                transform=axes.transAxes, bbox=dict(facecolor='white', alpha=1.0)) 

        axes = figure.add_subplot(1,2,2)
        axes.plot(data, gaussian, '-o', color='#540EAD')
        axes.set_title("Gaussian Distribution of Wingbeat Frequency")
        axes.set_xlabel("Wing Beat Frequency")
 
    def plotCircadian(self, figure, data):
        figure.clf()
        axes = figure.add_subplot(111)
        axes.plot(np.arange(ag.MIN_IN_DAY), data, color='#0B5FA5')
        y_max = axes.get_ylim()[1]
        y_offset = float(y_max) / 15 
        x_offset = float(axes.get_xlim()[1]) / 100
        if (self.state.dawn > 0):
            axes.axvline(x=self.state.dawn, ymin=0.0, ymax=1.0,
                         linewidth=1, linestyle='dashed', color='k')
            axes.annotate(s='Dawn', xy=(self.state.dawn + x_offset,
                    y_max - y_offset), verticalalignment='right',
                    horizontalalignment='left')
        if (self.state.dusk > 0):
            axes.axvline(x=self.state.dusk, ymin=0.0, ymax=1.0,
                         linewidth=1, linestyle='dashed', color='k')
            axes.annotate(s='Dusk', xy=(self.state.dusk + x_offset,
                    y_max - y_offset), verticalalignment='right',
                    horizontalalignment='left')
        axes.set_xticks(np.arange(0, ag.MIN_IN_DAY + 1, ag.MIN_IN_DAY / ag.HRS_IN_DAY ))
        axes.set_xticklabels(np.arange(0, ag.HRS_IN_DAY + 1))
        axes.set_title("Circadian Rhythm")
        axes.set_xlabel("Hour in the Day")
        axes.set_ylabel("Average Occurance per Day")

    def drawFigure(self, figure):
        figure.canvas.draw()

    def generateString(self, minimum, maximum, mean, std):
        s = "Min: {0:.0f}\nMax: {1:.0f}\nMean: {2:.2f}\nStd: {3:.2f}"
        return s.format(minimum, maximum, mean, std)

class AnalyzerState:
    def __init__(self, minwb=ag.minWingBeat, maxwb=ag.maxWingBeat,
                 sw=ag.slidingWindow, ss=ag.stepSize,
                 ct=ag.complexityThreshold, interval=ag.interval):
        self.minWingBeat = minwb
        self.maxWingBeat = maxwb
        self.slidingWindow = sw
        self.stepSize = ss
        self.complexityThreshold = ct
        self.interval = interval
        self.timeRegex = '^((1[0-2]|[1-9])(:[0-5][0-9])?[aApP][mM])$'
        self.militaryRegex = '^((2[0-3]|[0-1]?[0-9])(:[0-5][0-9]?))$'
        self.dawn = -1 
        self.dusk = -1 
        self.changed = False

    def runSuccess(self):
        self.changed = False

    def parameterUpdate(self, minWingBeat, maxWingBeat, stepSize,
                        slidingWindow, complexityThreshold, dawn, dusk):
        minWingBeat = int(minWingBeat)
        maxWingBeat = int(maxWingBeat)
        stepSize = int(stepSize)
        slidingWindow = int(slidingWindow)
        if (minWingBeat != self.minWingBeat or
            maxWingBeat != self.maxWingBeat or
            stepSize != self.stepSize or
            slidingWindow != self.slidingWindow or
            complexityThreshold != self.complexityThreshold):
                
            self.minWingBeat = minWingBeat
            self.maxWingBeat = maxWingBeat
            self.stepSize = stepSize
            self.slidingWindow = slidingWindow
            self.complexityThreshold = complexityThreshold
            self.changed = True

        self.dawn = dawn
        self.dusk = dusk

    def hasChanged(self):
        return self.changed
    
    def processTime(self, timeString):
        timeString.replace(' ', '')
        if timeString == "": 
            return -1
        time = re.search(self.militaryRegex, timeString)
        if time is not None: 
            return self.militaryTimeToInt(timeString)

        time = re.search(self.timeRegex, timeString)
        if time is not None: 
            return self.timeToInt(timeString)
        return -1

    def militaryTimeToInt(self, time):
        splitTime = time.split(':')
        hours = splitTime[0]
        minutes = 0
        if len(splitTime) > 1:
            minutes = splitTime[1]
        return int(hours) * 60 + int(minutes)

    def timeToInt(self, time):
        identifier = time[-2:-1]
        time = time[:-2]
        offset = 0
        if identifier.lower() == 'p':
            offset = 12  
        splitTime = time.split(':') 
        hours = int(splitTime[0])
        minutes = 0
        if len(splitTime) > 1:
            minutes = int(splitTime[1])
        return ((hours % 12) + offset) * 60 + minutes 

class ParameterWindow(BasicWindow):
    def __init__(self, root):
        self.master = root
        self.window = tk.Toplevel(root.master)
        self.window.withdraw()
        self.window.update_idletasks()

        # Set protocol to stop refering to this instantiation of the window.
        self.window.protocol("WM_DELETE_WINDOW", self.close)
       
        labels = ["Minimum Wing Beat", "Maximum Wing Beat",
                  "Step Size", "Sliding Window Size",
                  "Complexity Threshold", "Dawn", "Dusk"]
        state = self.master.state
        entries = [state.minWingBeat, state.maxWingBeat, 
                   state.stepSize, state.slidingWindow,
                   state.complexityThreshold, state.dawn, state.dusk] 
        
        # Create labels for parameters
        self.createLabels(labels)

        # Create entry fields for paramaters
        entryFields = self.createEntries(entries)
        self.minwbEntry = entryFields[0]
        self.maxwbEntry = entryFields[1]
        self.stepSizeEntry = entryFields[2]
        self.slidingWindowEntry = entryFields[3]
        self.complexityEntry = entryFields[4]
        self.dawnEntry = entryFields[5]
        self.duskEntry = entryFields[6]

        # Create update button for parameters
        self.updateButton = tk.Button(self.window, text="Update", 
                                      command=self.updateParameters)
        self.updateButton.grid(row=len(entryFields), column=0)
        self.center(self.window)
        self.window.deiconify()

    def createLabels(self, labels):
        for i in range(len(labels)):
            label = tk.Label(self.window, text=labels[i])
            label.grid(row=i, column=0)

    def createEntries(self, defaults):
        entries = []
        for i in range(len(defaults)):
            entry = tk.Entry(self.window)
            entry.delete(0, tk.END)
            if (defaults[i] > 0):
                entry.insert(0, str(defaults[i])) 
            entry.grid(row=i, column=1)
            entries.append(entry)
        return entries 

    def updateParameters(self):
        state = self.master.state 
        try:
            minWingBeat = float(self.minwbEntry.get())
            maxWingBeat = float(self.maxwbEntry.get())
            stepSize = float(self.stepSizeEntry.get())
            slidingWindow = float(self.slidingWindowEntry.get())
            complexityThreshold = float(self.complexityEntry.get())
            dawn = state.processTime(self.dawnEntry.get())
            dusk = state.processTime(self.duskEntry.get())
            state.parameterUpdate(minWingBeat, maxWingBeat, stepSize,
                                  slidingWindow, complexityThreshold,
                                  dawn, dusk)
            self.showMessage("Update Dialog",
                             "Parameters updated successfully")
            self.window.lift()
        except ValueError:
            self.showError("Parameter Error",
                           "Expected numerical input for parameter fields.") 

    def close(self):
        self.master.parameterWindow = None
        self.window.destroy()
            

