import os
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

class AnalyzerWindow:
    def __init__(self, root, analyzerState, mainFunction):
        self.master = root
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

    def start(self):
        self.master.mainloop()

    def askPath(self):
        self.path = askdirectory()
        self.pathEntry.delete(0, tk.END)

    def write(self, output):
        self.outputMsg.configure(text=output)        
    
    def run(self):
        try:
            self.path = self.pathEntry.get() 
            self.mainFunction(self.path, self, self.state)
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

    def plotWingBeat(self, figure, data, mean, std):
        bins = [x for x in range(self.state.minWingBeat, 
                                 self.state.maxWingBeat + 200 + 1, 200)]
        data.sort()
        figure.clf()
        gaussian = scipy.stats.norm.pdf(data, mean, std)

        axes = figure.add_subplot(1,2,1)
        axes.hist(data, bins=bins, linewidth=1, edgecolor='k')
        axes.set_xlabel("Wing Beat Frequency")
        axes.set_ylabel("Total Occurances") 

        axes = figure.add_subplot(1,2,2)
        axes.plot(data, gaussian, '-o')
        axes.set_xlabel("Wing Beat Frequency")
        axes.set_ylabel("Percentage of Total Occurances")
 
    def plotCircadian(self, figure, data):
        figure.clf()
        axes = figure.add_subplot(111)
        axes.plot(np.arange(ag.MIN_IN_DAY), data)
        axes.set_xticks(np.arange(0, ag.MIN_IN_DAY + 1, ag.MIN_IN_DAY / ag.HRS_IN_DAY ))
        axes.set_xticklabels(np.arange(0, ag.HRS_IN_DAY + 1))
        axes.set_xlabel("Hour in the Day")
        axes.set_ylabel("Average Occurance per Day")

    def drawFigure(self, figure):
        figure.canvas.draw()

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

class ParameterWindow:
    def __init__(self, root):
        self.master = root
        self.window = tk.Toplevel(root.master)

        # Set protocol to stop refering to this instantiation of the window.
        self.window.protocol("WM_DELETE_WINDOW", self.close)
       
        labels = ["Minimum Wing Beat", "Maximum Wing Beat",
                  "Step Size", "Sliding Window Size",
                  "Complexity Threshold"]
        state = self.master.state
        entries = [state.minWingBeat, state.maxWingBeat, 
                   state.stepSize, state.slidingWindow,
                   state.complexityThreshold] 
        
        # Create labels for parameters
        self.createLabels(labels)

        # Create entry fields for paramaters
        entryFields = self.createEntries(entries)
        self.minwbEntry = entryFields[0]
        self.maxwbEntry = entryFields[1]
        self.stepSizeEntry = entryFields[2]
        self.slidingWindowEntry = entryFields[3]
        self.complexityEntry = entryFields[4]

        # Create update button for parameters
        self.updateButton = tk.Button(self.window, text="Update", 
                                      command=self.updateParameters)
        self.updateButton.grid(row=5, column=0)

    def createLabels(self, labels):
        for i in range(len(labels)):
            label = tk.Label(self.window, text=labels[i])
            label.grid(row=i, column=0)

    def createEntries(self, defaults):
        entries = []
        for i in range(len(defaults)):
            entry = tk.Entry(self.window)
            entry.delete(0, tk.END)
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
            state.minWingBeat = int(minWingBeat)
            state.maxWingBeat = int(maxWingBeat)
            state.stepSize = int(stepSize)
            state.slidingWindow = int(slidingWindow)
            state.complexityThreshold = complexityThreshold
            tkMessageBox.showinfo("Update Dialog",
                                  "Updated parameters successfully")
        except ValueError:
            tkMessageBox.showerror("Parameter Error",
                                   "Expected numerical input for parameter fields.") 

    def close(self):
        self.master.parameterWindow = None
        self.window.destroy()
            

