#Welcome to ugly piece of shit gui 1.0!
from tkinter import *
from tkinter import filedialog as fd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, BoundaryNorm
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from test import load_audio_data, create_actions
import subprocess, os, json
import numpy as np

master = Tk()
plt.style.use(["ggplot", "dark_background", "fast"])

data = None
heatmap = True

def ree():
	global data

	if data != None:
		# plotting the graph
		plot1.plot(data["pitch"], label="pitch", linewidth=.3)
		plot1.plot(data["energy"], label="energy", linewidth=.3)
		plot1.legend()

	canvas1.draw()
	plot1.clear()

if True:
	# the figure that will contain the plot
	fig1 = Figure(figsize=(11, 3), dpi=150, tight_layout=True)

	# adding the subplot
	plot1 = fig1.add_subplot(111)

	# creating the Tkinter canvas
	# containing the Matplotlib figure
	canvas1 = FigureCanvasTkAgg(fig1, master=master)  
	canvas1.draw()

	# placing the canvas on the Tkinter window
	canvas1.get_tk_widget().pack()

def speed(A,B):
	return (abs(B[1] - A[1]) / abs(B[0] - A[0])) / 500

result = []
my_cmap = LinearSegmentedColormap.from_list("intensity",["w", "g", "orange", "r"], N=256)
def res():
	global result
	global data
	global heatmap

	if data != None:
		result = create_actions(
			data, 
			energy_multiplier=energy_mult.get(), 
			pitch_range=pitch_offset.get(), 
			overflow=options_list.index(value_inside.get())
		)

		# plotting the graph
		X,Y = map(list, zip(*result))
		if (not heatmap):
			plot2.plot(X,Y, linewidth=.5)
		else:
			points = np.array([X, Y]).T.reshape(-1, 1, 2)
			segments = np.concatenate([points[:-1], points[1:]], axis=1)

			colors = np.array([my_cmap(speed((X[i-1], Y[i-1]), (X[i], Y[i]))) for i in range(1,len(Y))])

			lc = LineCollection(segments, colors=colors, linewidths=.5)
			plot2.add_collection(lc)
			plot2.autoscale()
		#TODO: Heatbar for performance?
		plot2.margins(0.05)

	canvas2.draw()
	plot2.clear()

if True:
	# the figure that will contain the plot
	fig2 = Figure(figsize=(11,3), dpi=150, tight_layout=True)

	# adding the subplot
	plot2 = fig2.add_subplot(111)

	# creating the Tkinter canvas
	# containing the Matplotlib figure
	canvas2 = FigureCanvasTkAgg(fig2, master=master)
	canvas2.draw()

	# placing the canvas on the Tkinter window
	canvas2.get_tk_widget().pack()

pitch_offset = Scale(master, from_=200, to=-200, length=150, orient='vertical', command=lambda v: res())
pitch_offset.set(100)
pitch_offset.pack(side=LEFT)
energy_mult = Scale(master, from_=10, to=0, length=150, resolution=-1 , orient='vertical', command=lambda v: res())
energy_mult.set(1)
energy_mult.pack(side=LEFT)

#TODO: Vstack buttons
#TODO: Status bar
# Create the optionmenu widget and passing 
value_inside = StringVar(master)
options_list = ["Crop", "Bounce", "Fold"]
value_inside.set(options_list[0])
question_menu = OptionMenu(master, value_inside, *options_list, command=lambda v: res())
question_menu.pack(side=LEFT)

cur_file = None
def loadfile():
	global data
	global cur_file

	filename = fd.askopenfile(title='Open a file')
	if (filename == None):
		return
	data = None
	audio_file = os.path.basename(filename.name)
	cur_file = audio_file
	audio_file = os.path.splitext(audio_file)[0] + ".wav"
	audio_file = os.path.join("tmp", audio_file)

	try:
		os.mkdir("tmp")
	except:
		pass

	try:
		subprocess.check_call([
			"ffmpeg",
			"-y",
			"-i", filename.name,
			"-ar", "48000",
			audio_file
		])

		data = load_audio_data(audio_file)
		master.title(cur_file)
	except Exception as ex:
		print(ex)
		master.title("Error")
	finally:
		res()
		ree()

def savefile():
	with fd.asksaveasfile(
		title="Save funscript", 
		initialfile=f"{os.path.splitext(cur_file)[0]}.funscript", 
		filetypes=[("Funscript", ".funscript")]
		) as f:
			json.dump({
				"actions": [{"at": int(at*1000), "pos": round(pos)} for at,pos in result],
				"inverted": False,
				"metadata": {
					"creator": "PythonDancer",
					"description": "",
					"duration": int(result[-1][0]),
					"license": "None",
					"notes": "",
					"performers": [],
					"script_url": "",
					"tags": [],
					"title": "",
					"type": "basic",
					"video_url": "",
				},
				"range": 100,
				"version": "1.0",
			}, f)

loadbtn = Button(text="Load", command=loadfile)
loadbtn.pack(side=LEFT)
savebtn = Button(text="Save", command=savefile)
savebtn.pack(side=LEFT)

def asd():
	global heatmap
	heatmap=var1.get()
	res()
var1 = BooleanVar(value=True)
c1 = Checkbutton(text='Heatmapping',variable=var1, onvalue=True, offvalue=False, command=asd)
c1.pack(side=LEFT)

if __name__ == "__main__":
	mainloop()