import tkinter as tk
from tkinter import ttk, messagebox, filedialog 

import sys, os, json
from pathlib import Path

from threading import Thread
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas

from .cli import cmd

from .libfun import load_audio_data, create_actions, dump_funscript, speed, autoval, render_heatmap, VERSION, HEATMAP
from .util import cli_args, ffmpeg_check, ffmpeg_conv

plt.style.use(["ggplot", "dark_background", "fast"])

class Config:
	def __init__(self) -> None:
		self.configfile = "config.json"
		self.data = {}
		if os.path.exists(self.configfile):
			with open(self.configfile, "r") as f:
				self.data = json.load(f)
	def save(self, name, val):
		self.data[name] = val
		with open(self.configfile, "w") as f:
			json.dump(self.data, f)
	def get(self, name, default):
		if name in self.data:
			return self.data[name]
		return default

cfg = Config()


# Thanks to https://stackoverflow.com/a/61253373
def disableChildren(parent):
	for child in parent.winfo_children():
		wtype = child.winfo_class()
		if wtype not in ('Frame','Labelframe','TFrame','TLabelframe'):
			child.configure(state='disable')
		else:
			disableChildren(child)

def enableChildren(parent):
	for child in parent.winfo_children():
		wtype = child.winfo_class()
		#print (wtype)
		if wtype not in ('Frame','Labelframe','TFrame','TLabelframe'):
			child.configure(state='normal')
		else:
			enableChildren(child)

class ImageWorker:
	progressed = None
	finished = None
	w,h = 0,0

	def pre(self):
		# the figure that will contain the plot
		dpi = mpl.rcParams["figure.dpi"]
		self.fig = Figure(figsize=(self.w/dpi, self.h/dpi), dpi=dpi, tight_layout=True)

		# adding the subplot
		self.plot = self.fig.add_subplot(111)

		# canvas to draw on
		#self.canvas = FigureCanvas(self.fig)

	def post(self):
		self.progressed(90, "Drawing...")

		#self.canvas.draw()

		#w, h = self.canvas.get_width_height()
		#ch = 4
		#bytesPerLine = ch * w
		#im = QtGui.QImage(self.canvas.buffer_rgba(), w, h, bytesPerLine, QtGui.QImage.Format_RGBA8888)
		#self.img = QtGui.QPixmap(im)
		#buf = self.canvas.buffer_rgba()

		self.progressed(100, "Done!")

class LoadWorker(ImageWorker):
	done = None

	def __init__(self, size, fileName, data, plp):
		super().__init__()
		self.w, self.h = size
		self.fileName = fileName
		self.data = data
		self.plp = plp

	def run(self):
		self.progressed(5, "Converting to wav...")

		self.pre()

		if (isinstance(self.fileName, Path)):
			try:
				self.data = load_audio_data(self.fileName, plp=self.plp)
			except Exception as e:
				self.progressed(-1, "Failed to transform audio data!")
				self.finished()
				return

			self.progressed(50, "Plotting waveforms...")

		if len(self.data) > 0:
			# plotting the graph
			self.plot.plot(self.data["pitch"], label="pitch", linewidth=.5)
			self.plot.plot(self.data["energy"], label="energy", linewidth=.5)
			self.plot.legend()

		self.post()

		self.done(self.data, self.fig, isinstance(self.fileName, Path))
		self.finished()


class RenderWorker(ImageWorker):
	done = None

	def __init__(self, size, data, energy_mult, pitch_offset, overflow, heatmap, automode):
		super().__init__()
		self.w, self.h = size
		self.data = data
		self.energy_mult = energy_mult
		self.pitch_offset = pitch_offset
		self.overflow = overflow
		self.heatmap = heatmap
		self.automode = automode

	def run(self):
		self.pre()
		result = []

		if len(self.data) > 0:
			self.progressed(50, "Creating actions...")

			# plotting the graph
			try:
				result = create_actions(
					self.data, 
					energy_multiplier=self.energy_mult,
					pitch_range=self.pitch_offset,
					overflow=self.overflow
				)
			except Exception as e:
				print(e)
				self.progressed(-1, "Failed to create actions!")
				self.finished()
				return

			# plotting the graph
			X,Y = map(list, zip(*result))
			if (self.heatmap):
				points = np.array([X, Y]).T.reshape(-1, 1, 2)
				segments = np.concatenate([points[:-1], points[1:]], axis=1)

				colors = np.array([HEATMAP(speed((X[i], Y[i]), (X[i+1], Y[i+1]))) for i in range(len(Y)-1)])

				lc = LineCollection(segments, colors=colors, linewidths=.5)
				self.plot.add_collection(lc)
				self.plot.autoscale()
			else:
				self.plot.plot(X,Y, linewidth=.5)
			
			#self.plot.axhline(y=np.nanmean(Y))

		self.plot.set_ylim(0,100)
		if ("at" in self.data): #If data exists
			self.plot.set_xlim(0,self.data["at"])

		self.post()

		self.done(result, self.fig)
		self.finished()

class MainWindow(tk.Tk):
	def __init__(self, args):
		super().__init__()

		self.title(f"PythonDancer {VERSION}")
		self.geometry("711x980")
		self.minsize(711, 980)

		# Central widget layout
		central_frame = ttk.Frame(self)
		central_frame.grid(row=0, column=0, sticky="nsew")
		
		# Configure grid for central_frame
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)
		central_frame.columnconfigure(0, weight=1)
		central_frame.rowconfigure(1, weight=3)  # Audio data section gets more weight

		# Media GroupBox
		media_group = ttk.LabelFrame(central_frame, text="Media")
		media_group.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
		media_group.columnconfigure(2, weight=1)

		self.about_button = ttk.Button(media_group, text="About")
		self.about_button.grid(row=0, column=0, padx=5, pady=5)

		self.load_button = ttk.Button(media_group, text="Load")
		self.load_button.grid(row=0, column=1, padx=5, pady=5)

		progress_frame = ttk.Frame(media_group)
		progress_frame.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
		progress_frame.columnconfigure(0, weight=1)

		self.progress_label = ttk.Label(progress_frame, text="TextLabel")
		self.progress_label.grid(row=0, column=0, sticky="ew")

		self.progress_bar = ttk.Progressbar(progress_frame, value=0, maximum=100)
		self.progress_bar.grid(row=1, column=0, sticky="ew")

		# Audio Data GroupBox
		audio_group = ttk.LabelFrame(central_frame, text="Audio Data")
		audio_group.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
		audio_group.columnconfigure(0, weight=1)
		audio_group.rowconfigure(0, weight=1)
		audio_group.rowconfigure(1, weight=1)

		self.audio_input = tk.Canvas(audio_group, bg="white")
		self.audio_input.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
		self.audio_input.columnconfigure(0, weight=1)
		self.audio_input.rowconfigure(0, weight=1)

		self.audioi_canvas = FigureCanvas(master=self.audio_input)
		self.audioi_canvas.draw()
		self.audioi_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

		self.audio_output = tk.Canvas(audio_group, bg="white")
		self.audio_output.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
		self.audio_output.columnconfigure(0, weight=1)
		self.audio_output.rowconfigure(0, weight=1)

		self.audioo_canvas = FigureCanvas(master=self.audio_output)
		self.audioo_canvas.draw()
		self.audioo_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

		# Settings GroupBox
		self.settings_group = ttk.LabelFrame(central_frame, text="Settings")
		self.settings_group.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
		self.settings_group.columnconfigure(2, weight=1)

		pitch_group = ttk.LabelFrame(self.settings_group, text="Pitch -> Offset")
		pitch_group.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
		pitch_group.rowconfigure(0, weight=1)

		self.pitch_slider = ttk.Scale(pitch_group, orient=tk.VERTICAL, from_=200, to=-200, value=100)
		self.pitch_slider.grid(row=0, column=0, sticky="ns")

		energy_group = ttk.LabelFrame(self.settings_group, text="Energy -> Magnitude")
		energy_group.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
		energy_group.rowconfigure(0, weight=1)

		self.energy_slider = ttk.Scale(energy_group, orient=tk.VERTICAL, from_=100, to=0, value=10)
		self.energy_slider.grid(row=0, column=0, sticky="ns")

		options_group = ttk.LabelFrame(self.settings_group, text="Options")
		options_group.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
		options_group.columnconfigure(1, weight=1)
		options_group.rowconfigure(0, weight=1)

		range_group = ttk.LabelFrame(options_group, text="Out of range")
		range_group.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
		range_group.columnconfigure(0, weight=1)

		self.var_oor = tk.StringVar(value="crop")
		self.crop_button = ttk.Radiobutton(range_group, text="Crop", variable=self.var_oor, value="crop")
		self.crop_button.grid(row=0, column=0, sticky="w")

		self.bounce_button = ttk.Radiobutton(range_group, text="Bounce", variable=self.var_oor, value="bounce")
		self.bounce_button.grid(row=1, column=0, sticky="w")

		self.fold_button = ttk.Radiobutton(range_group, text="Fold", variable=self.var_oor, value="fold")
		self.fold_button.grid(row=2, column=0, sticky="w")

		misc_group = ttk.LabelFrame(options_group, text="Misc")
		misc_group.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
		misc_group.columnconfigure(0, weight=1)

		self.heatmap_var = tk.BooleanVar(value=True)
		self.heatmap_check = ttk.Checkbutton(misc_group, text="Heatmap", variable=self.heatmap_var)
		self.heatmap_check.grid(row=0, column=0, sticky="w")

		self.plp_var = tk.BooleanVar(value=True)
		self.plp_check = ttk.Checkbutton(misc_group, text="PLP estimation", variable=self.plp_var)
		self.plp_check.grid(row=1, column=0, sticky="w")

		self.map_var = tk.BooleanVar(value=True)
		self.map_check = ttk.Checkbutton(misc_group, text="Automap", variable=self.map_var)
		self.map_check.grid(row=2, column=0, sticky="w")

		self.automap_group = ttk.LabelFrame(options_group, text="Automap settings")
		self.automap_group.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
		self.automap_group.columnconfigure(0, weight=1)

		self.var_automap = tk.StringVar(value="meanv2")
		self.mean_button = ttk.Radiobutton(self.automap_group, text="Mean", variable=self.var_automap, value="mean")
		self.mean_button.grid(row=0, column=0, sticky="w")

		self.meanv2_button = ttk.Radiobutton(self.automap_group, text="MeanV2", variable=self.var_automap, value="meanv2")
		self.meanv2_button.grid(row=1, column=0, sticky="w")

		self.length_button = ttk.Radiobutton(self.automap_group, text="Length", variable=self.var_automap, value="length")
		self.length_button.grid(row=2, column=0, sticky="w")

		speed_frame = ttk.Frame(self.automap_group)
		speed_frame.grid(row=3, column=0, sticky="ew", pady=5)
		speed_frame.columnconfigure(1, weight=1)

		speed_label = ttk.Label(speed_frame, text="Target Speed")
		speed_label.grid(row=0, column=0)

		self.speed_spinbox_var = tk.IntVar(value=250)
		self.speed_spinbox = tk.Spinbox(speed_frame, from_=0, to=500, width=5, textvariable=self.speed_spinbox_var)
		self.speed_spinbox.grid(row=0, column=1, padx=5)

		pitch_frame = ttk.Frame(self.automap_group)
		pitch_frame.grid(row=4, column=0, sticky="ew", pady=5)
		pitch_frame.columnconfigure(1, weight=1)

		pitch_label = ttk.Label(pitch_frame, text="Target Pitch")
		pitch_label.grid(row=0, column=0)

		self.pitch_spinbox_var = tk.IntVar(value=20)
		self.pitch_spinbox = tk.Spinbox(pitch_frame, from_=0, to=100, width=5, textvariable=self.pitch_spinbox_var)
		self.pitch_spinbox.grid(row=0, column=1, padx=5)

		per_frame = ttk.Frame(self.automap_group)
		per_frame.grid(row=5, column=0, sticky="ew", pady=5)
		per_frame.columnconfigure(1, weight=1)

		per_label = ttk.Label(per_frame, text="Target %")
		per_label.grid(row=0, column=0)

		self.per_spinbox_var = tk.IntVar(value=65)
		self.per_spinbox = tk.Spinbox(per_frame, from_=0, to=100, width=5, textvariable=self.per_spinbox_var)
		self.per_spinbox.grid(row=0, column=1, padx=5)

		# Export GroupBox
		export_group = ttk.LabelFrame(central_frame, text="Export")
		export_group.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
		export_group.columnconfigure(1, weight=1)

		self.funscript_button = ttk.Button(export_group, text="Funscript")
		self.funscript_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

		self.heatmap_button = ttk.Button(export_group, text="Heatmap")
		self.heatmap_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
		self.funscript_button["state"] = "disabled"
		self.heatmap_button["state"] = "disabled"
	
		self.ready(args)

	def ready(self, args):
		self.fileName = None
		self.data = {}
		self.result = None

		self.__loadworker = Thread()
		self.__renderworker = Thread()
		self.__waitloader = None

		self.about_button.bind("<Button-1>", lambda event: messagebox.showinfo("About", """Thanks to ncdxncdx for the original application!
Thanks to Nodude for the Python port!
Thanks to you for using this software!""") )
		self.load_button.bind("<Button-1>", self.loadPressed)
		# TODO: More binds

		if (ffmpeg_check()):
			self.disableUX()
			self.progress_label["text"] = "FFMpeg is missing, please download it!"
		elif (args.audio_path):
			self.loadfile(args.audio_path)
		else:
			self.LoadWorker()

		self.config_load()
		self._cmapPressed()

	def config_load(self):
		# Load
		OOR = cfg.get("OOR", "crop")
		self.var_oor.set(OOR)
		# Save
		self.var_oor.trace("w", lambda *args: cfg.save("OOR", self.var_oor.get()))
		
		# Load
		AUTOMODE = cfg.get("automode", "meanv2")
		self.var_automap.set(AUTOMODE)
		# Save
		self.var_automap.trace("w", lambda *args: cfg.save("automode", self.var_automap.get()))

		# Load
		self.pitch_spinbox_var.set(cfg.get("tpitch", self.pitch_spinbox_var.get()))
		self.speed_spinbox_var.set(cfg.get("tspeed", self.speed_spinbox_var.get()))
		self.per_spinbox_var.set(cfg.get("tper", self.per_spinbox_var.get()))
		# Save
		self.pitch_spinbox_var.trace("w", lambda *args: cfg.save("tpitch", self.pitch_spinbox_var.get()))
		self.speed_spinbox_var.trace("w", lambda *args: cfg.save("tspeed", self.speed_spinbox_var.get()))
		self.per_spinbox_var.trace("w", lambda *args: cfg.save("tper", self.per_spinbox_var.get()))

		# Load
		self.pitch_slider["value"] = cfg.get("pitch", self.pitch_slider.get())
		self.energy_slider["value"] = cfg.get("energy", self.energy_slider.get())
		# Save
		self.pitch_slider.bind("<ButtonRelease-1>", lambda x: cfg.save("pitch", self.pitch_slider.get()))
		self.energy_slider.bind("<ButtonRelease-1>", lambda x: cfg.save("energy", self.energy_slider.get()))

		# Load
		self.heatmap_var.set(cfg.get("heatmap", self.heatmap_var.get()))
		self.plp_var.set(cfg.get("plp", self.plp_var.get()))
		self.map_var.set(cfg.get("automap", self.map_var.get()))
		# Save
		self.heatmap_var.trace("w", lambda *args: cfg.save("heatmap", self.heatmap_var.get()))
		self.plp_var.trace("w", lambda *args: cfg.save("plp", self.plp_var.get()))
		self.map_var.trace("w", lambda *args: cfg.save("automap", self.map_var.get()))

		# Triggers
		self.var_oor.trace("w", lambda *args: self.RenderWorker())

		self.heatmap_var.trace("w", lambda *args: self.RenderWorker())
		self.plp_var.trace("w", lambda *args: self.LoadWorker(self.fileName))
		self.map_var.trace("w", lambda *args: self.cmapPressed())

		self.var_automap.trace("w", lambda *args: self.cmapPressed())

		self.pitch_spinbox_var.trace("w", lambda *args: self.cmapPressed())
		self.speed_spinbox_var.trace("w", lambda *args: self.cmapPressed())
		self.per_spinbox_var.trace("w", lambda *args: self.cmapPressed())

		self.pitch_slider.bind("<ButtonRelease-1>", lambda x: self.RenderWorker())
		self.energy_slider.bind("<ButtonRelease-1>", lambda x: self.RenderWorker())

		self.funscript_button.bind("<Button-1>", lambda x: self.bfunscriptPressed())
		self.heatmap_button.bind("<Button-1>", lambda x: self.bheatmapPressed())


	def loadPressed(self, event):
		filetypes = (
			('Media files', '*.*'),
		)

		fileName = filedialog.askopenfilename(
			title='Open a media file',
			filetypes=filetypes
		)

		if fileName:
			self.loadfile(fileName)

	def loadfile(self, fileName):
		self.fileName = Path(fileName)
		self.title(f"PythonDancer {VERSION} - {self.fileName.name}")
		self.progress_label["text"] = f"Opening video: {self.fileName.name}"
		self.data = {}
		self.disableUX()
		self.LoadWorker(self.fileName)

	def __load_done(self, data, img, init):
		self.data = data
		if (init):
			self.automap()
			self.funscript_button["state"] = "normal"
			self.heatmap_button["state"] = "normal"

		self.RenderWorker()
		self.audioi_canvas.figure = img
		self.audioi_canvas.draw()
		self.enableUX()

	def __load_prog(self, val, s):
		self.progress_bar["value"] = val
		self.progress_label["text"] = s
		if (val == -1):
			self.enableUX()

	def __load_thread(self, fileName=None) -> Thread:
		worker = LoadWorker(
			(
				self.audio_input.winfo_width(),
				self.audio_input.winfo_height()
			),
			fileName,
			self.data,
			self.plp_var.get()
		)
		thread = Thread(target=worker.run)

		worker.done = self.__load_done
		worker.progressed = self.__load_prog
		worker.finished = lambda: None

		return thread

	def LoadWorker(self, fileName=None):
		if not self.__loadworker.is_alive():
			self.__loadworker = self.__load_thread(fileName)
			self.__loadworker.start()

	def __render_done(self, result, img):
		self.result = result
		self.audioo_canvas.figure = img
		self.audioo_canvas.draw()

	def __render_repeat_aux(self):
		#TODO: While loop it without UI freeze
		if (self.__renderworker.is_alive()):
			self.after(10, self.__render_repeat_aux)
			return

		if (self.__waitloader != None):
			self.__renderworker = self.__render_thread()
			self.__waitloader = None

			self.__renderworker.start()

	def __render_repeat(self):
		self.after(10, self.__render_repeat_aux)

	def __render_thread(self) -> Thread:
		worker = RenderWorker(
			(
				self.audio_output.winfo_width(),
				self.audio_output.winfo_height()
			),
			self.data,
			self.energy_slider.get() / 10.0,
			self.pitch_slider.get(),
			self.OOR(),
			self.heatmap_var.get(),
			self.Automode(),
		)
		thread = Thread(target=worker.run)

		worker.done = self.__render_done
		worker.progressed = self.__load_prog
		worker.finished = self.__render_repeat

		return thread

	def RenderWorker(self):
		if not self.__renderworker.is_alive():
			self.__renderworker = self.__render_thread()
			self.__renderworker.start()
		else:
			self.__waitloader = True

	def enableUX(self):
		self.load_button["state"] = "normal"
		enableChildren(self.settings_group)
	def disableUX(self):
		self.load_button["state"] = "disabled"
		disableChildren(self.settings_group)

	def automap(self):
		if (self.map_var.get() and len(self.data) > 0):
			pitch, energy = autoval(self.data, tpi=self.pitch_spinbox_var.get(), target_speed=self.speed_spinbox_var.get(), v2above=self.per_spinbox_var.get()/100.0, opt=self.Automode())
			self.pitch_slider["value"] = int(pitch)
			self.energy_slider["value"] = int(energy * 10.0)

	def OOR(self):
		if self.var_oor.get() == "crop":
			return 0
		elif self.var_oor.get() == "bounce":
			return 1
		else: # fold
			return 2
	def Automode(self):
		if self.var_automap.get() == "mean":
			return 0
		elif self.var_automap.get() == "meanv2":
			return 1
		else: # length
			return 2

	def _cmapPressed(self):
		if self.map_var.get():
			enableChildren(self.automap_group)
		else:
			disableChildren(self.automap_group)
	def cmapPressed(self):
		self._cmapPressed()
		self.automap()
		self.RenderWorker()
		
	def bfunscriptPressed(self):
		if (not self.result):
			return

		initial_file = str(self.fileName.with_suffix(".funscript").name)
		options = {
			"title": "Save a funscript",
			"initialfile": initial_file,  # Initial file name
			"filetypes": [("Funscript Files", "*.funscript")],  # File types filter
		}

		fileName = filedialog.asksaveasfilename(**options)

		if fileName:
			with open(fileName, "w") as f:
				dump_funscript(f, self.result)
		else:
			print("File save cancelled.")

	def bheatmapPressed(self):
		if (len(self.data) <= 0):
			return

		initial_file = str(self.fileName.with_stem(self.fileName.stem + "_heatmap").with_suffix(".png").name)
		options = {
			'defaultextension': '.png',
			'filetypes': [('PNG Files', '.png')],
			'initialfile': initial_file,
			'title': 'Save a heatmap'
		}

		fileName = filedialog.asksaveasfilename(**options)
		if fileName:
			#fig = render_heatmap(
			#	self.data, 
			#	self.energy_slider.get() / 10.0,
			#	self.pitch_slider.get(),
			#	self.OOR()
			#)
			self.audioo_canvas.savefig(fileName, bbox_inches="tight", pad_inches=0)
		else:
			print("File save cancelled.")


def ux(args):
	app = MainWindow(args)
	app.mainloop()

if __name__ == "__main__":
	ux(cli_args().parse_args())
