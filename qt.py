
import sys, os
from pathlib import Path

import PyQt5.QtWidgets as QtWidgets
from PyQt5 import uic
from PyQt5 import QtGui, QtCore

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from libfun import load_audio_data, create_actions, dump_funscript, speed, autoval
from util import ffmpeg_check, ffmpeg_conv

plt.style.use(["ggplot", "dark_background", "fast"])

class ImageWorker(QtCore.QObject):
	progressed = QtCore.pyqtSignal(int, str)
	finished = QtCore.pyqtSignal()

	def pre(self):
		# the figure that will contain the plot
		dpi = mpl.rcParams["figure.dpi"]
		self.fig = Figure(figsize=(self.w/dpi, self.h/dpi), dpi=dpi, tight_layout=True)

		# adding the subplot
		self.plot = self.fig.add_subplot(111)

		# canvas to draw on
		self.canvas = FigureCanvas(self.fig)

	def post(self):
		self.progressed.emit(90, "Drawing...")

		self.canvas.draw()

		w, h = self.canvas.get_width_height()
		ch = 4
		bytesPerLine = ch * w
		im = QtGui.QImage(self.canvas.buffer_rgba(), w, h, bytesPerLine, QtGui.QImage.Format_RGBA8888)
		self.img = QtGui.QPixmap(im)

		self.progressed.emit(100, "Done!")

class LoadWorker(ImageWorker):
	done = QtCore.pyqtSignal(dict, QtGui.QPixmap, bool)

	def __init__(self, size, fileName, data, plp):
		super().__init__()
		self.w = size[0]
		self.h = size[1]
		self.fileName = fileName
		self.data = data
		self.plp = plp

	def run(self):
		self.progressed.emit(5, "Converting to wav...")

		self.pre()

		if (isinstance(self.fileName, Path)):
			audioFile = Path("tmp", self.fileName.with_suffix(".wav").name)
			audioFile.parent.mkdir(parents=True, exist_ok=True)

			if (len(self.data) <= 0):
				try:
					ffmpeg_conv(self.fileName, audioFile)
				except:
					self.progressed.emit(-1, "Failed to convert to wav!")
					self.finished.emit()
					return

				self.progressed.emit(20, "Transforming audio data...")

			try:
				self.data = load_audio_data(audioFile, plp=self.plp)
			except:
				self.progressed.emit(-1, "Failed to transform audio data!")
				self.finished.emit()
				return

			self.progressed.emit(50, "Plotting waveforms...")

		if len(self.data) > 0:
			# plotting the graph
			self.plot.plot(self.data["pitch"], label="pitch", linewidth=.5)
			self.plot.plot(self.data["energy"], label="energy", linewidth=.5)
			self.plot.legend()

		self.post()

		self.done.emit(self.data, self.img, isinstance(self.fileName, Path))
		self.finished.emit()


class RenderWorker(ImageWorker):
	done = QtCore.pyqtSignal(list, QtGui.QPixmap)
	my_cmap = LinearSegmentedColormap.from_list("intensity",["w", "g", "orange", "r"], N=256)

	def __init__(self, size, data, energy_mult, pitch_offset, overflow, heatmap):
		super().__init__()
		self.w = size[0]
		self.h = size[1]
		self.data = data
		self.energy_mult = energy_mult
		self.pitch_offset = pitch_offset
		self.overflow = overflow
		self.heatmap = heatmap

	def run(self):
		self.pre()
		result = []

		if len(self.data) > 0:
			self.progressed.emit(50, "Creating actions...")

			# plotting the graph
			try:
				result = create_actions(
					self.data, 
					energy_multiplier=self.energy_mult,
					pitch_range=self.pitch_offset,
					overflow=self.overflow
				)
			except:
				self.progressed.emit(-1, "Failed to create actions!")
				self.finished.emit()
				return

			# plotting the graph
			X,Y = map(list, zip(*result))
			if (self.heatmap):
				points = np.array([X, Y]).T.reshape(-1, 1, 2)
				segments = np.concatenate([points[:-1], points[1:]], axis=1)

				colors = np.array([self.my_cmap(speed((X[i], Y[i]), (X[i+1], Y[i+1]))) for i in range(len(Y)-1)])

				lc = LineCollection(segments, colors=colors, linewidths=.5)
				self.plot.add_collection(lc)
				self.plot.autoscale()
			else:
				self.plot.plot(X,Y, linewidth=.5)
			
			#self.plot.axhline(y=np.nanmean(Y))

		self.plot.set_ylim(0,100)
		if ("at" in self.data):
			self.plot.set_xlim(0,self.data["at"])

		self.post()

		self.done.emit(result, self.img)
		self.finished.emit()

# Define function to import external files when using PyInstaller.
# https://stackoverflow.com/a/37920111
def resource_path(relative_path):
	""" Get absolute path to resource, works for dev and for PyInstaller """
	try:
		# PyInstaller creates a temp folder and stores path in _MEIPASS
		base_path = sys._MEIPASS
	except Exception:
		base_path = os.path.abspath(".")

	return os.path.join(base_path, relative_path)

uiForm = resource_path("dancerUI.ui")
class MainUi(QtWidgets.QMainWindow):
	resized = QtCore.pyqtSignal()

	def __init__(self):
		super(MainUi, self).__init__()
		uic.loadUi(uiForm, self)
		self.setWindowTitle("PythonDancer")
		self.fileName = None
		self.data = {}
		self.result = None

		self.babout = self.findChild(QtWidgets.QToolButton, "aboutButton")
		self.bload = self.findChild(QtWidgets.QToolButton, "mediaButton")
		self.babout.clicked.connect(self.baboutPressed)
		self.bload.clicked.connect(self.bloadPressed)
		self.pbat = self.findChild(QtWidgets.QProgressBar, "progressBar")
		self.pbat.setValue(0)
		self.plabel = self.findChild(QtWidgets.QLabel, "progressLabel")

		self.ginput = self.findChild(QtWidgets.QGraphicsView, "audioInput")
		self.goutput = self.findChild(QtWidgets.QGraphicsView, "audioOutput")
		self.gsinput = QtWidgets.QGraphicsScene()
		self.gsoutput = QtWidgets.QGraphicsScene()
		self.ginput.setScene(self.gsinput)
		self.goutput.setScene(self.gsoutput)
		self.ginput.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.ginput.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.goutput.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.goutput.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		self.bbounce = self.findChild(QtWidgets.QRadioButton, "bounceButton")
		self.bcrop = self.findChild(QtWidgets.QRadioButton, "cropButton")
		self.bfold = self.findChild(QtWidgets.QRadioButton, "foldButton")
		self.bbounce.clicked.connect(self.RenderWorker)
		self.bcrop.clicked.connect(self.RenderWorker)
		self.bfold.clicked.connect(self.RenderWorker)

		self.cheat = self.findChild(QtWidgets.QCheckBox, "heatOpt")
		self.cheat.clicked.connect(self.cheatPressed)
		self.cplp = self.findChild(QtWidgets.QCheckBox, "plpOpt")
		self.cplp.clicked.connect(self.cplpPressed)
		self.cmap = self.findChild(QtWidgets.QCheckBox, "mapOpt")
		self.cmap.clicked.connect(self.cmapPressed)
		self.stpitch = self.findChild(QtWidgets.QSpinBox, "pitchBox")
		self.stspeed = self.findChild(QtWidgets.QSpinBox, "speedBox")
		self.stpitch.editingFinished.connect(self.cmapPressed)
		self.stspeed.editingFinished.connect(self.cmapPressed)

		self.spitch = self.findChild(QtWidgets.QSlider, "pitchSlider")
		self.senergy = self.findChild(QtWidgets.QSlider, "energySlider")
		self.spitch.valueChanged.connect(self.RenderWorker)
		self.senergy.valueChanged.connect(self.RenderWorker)

		self.bfunscript = self.findChild(QtWidgets.QPushButton, "funscriptButton")
		self.bheatmap = self.findChild(QtWidgets.QPushButton, "heatmapButton")
		self.bfunscript.clicked.connect(self.bfunscriptPressed)
		self.bheatmap.clicked.connect(self.bheatmapPressed)

		self.__loadworker = QtCore.QThread()
		self.__renderworker = QtCore.QThread()
		self.__waitloader = None

		self.resized.connect(self.LoadWorker)

		self.LoadWorker()

		if (ffmpeg_check()):
			self.disableUX()
			self.plabel.setText("FFMpeg is missing, please download it!")

	def resizeEvent(self, event):
		self.resized.emit()
		return super(MainUi, self).resizeEvent(event)

	def baboutPressed(self):
		QtWidgets.QMessageBox.about(self, "About", """Not Implemented""")

	def OOR(self):
		if (self.bcrop.isChecked()):
			return 0
		elif (self.bbounce.isChecked()):
			return 1
		elif (self.bfold.isChecked()):
			return 2

	def enableUX(self):
		for i in [
			self.bload,
			self.spitch,
			self.senergy,
			self.bfunscript,
			self.bheatmap,
			self.bbounce,
			self.bcrop,
			self.bfold,
		]:
			i.setEnabled(True)
	def disableUX(self):
		for i in [
			self.bload,
			self.spitch,
			self.senergy,
			self.bfunscript,
			self.bheatmap,
			self.bbounce,
			self.bcrop,
			self.bfold,
		]:
			i.setEnabled(False)

	def __load_done(self, data, img, init):
		self.data = data
		if (init):
			self.automap()
		self.RenderWorker()
		self.gsinput.clear()
		gfxPixItem = self.gsinput.addPixmap(img)
		self.ginput.fitInView(gfxPixItem)
		self.enableUX()

	def __load_prog(self, val, s):
		self.pbat.setValue(val)
		self.plabel.setText(s)
		if (val == -1):
			self.enableUX()

	def __load_thread(self, fileName=None):
		thread = QtCore.QThread()
		worker = LoadWorker(
			(
				self.ginput.width(),
				self.ginput.height()
			),
			fileName,
			self.data,
			self.cplp.isChecked()
		)
		worker.moveToThread(thread)

		# this is essential when worker is in local scope!
		thread.worker = worker

		thread.started.connect(worker.run)
		worker.done.connect(self.__load_done)
		worker.progressed.connect(self.__load_prog)
		worker.finished.connect(thread.quit)

		return thread

	def LoadWorker(self, fileName=None):
		if not self.__loadworker.isRunning():
			self.__loadworker = self.__load_thread(fileName)
			self.__loadworker.start()

	def __render_done(self, result, img):
		self.result = result
		self.gsoutput.clear()
		gfxPixItem = self.gsoutput.addPixmap(img)
		self.goutput.fitInView(gfxPixItem)

	def __render_repeat_aux(self):
		#TODO: While loop it without UI freeze
		if (self.__renderworker.isRunning()):
			QtCore.QTimer.singleShot(10, self.__render_repeat_aux)
			return

		if (self.__waitloader != None):
			self.__renderworker = self.__render_thread()
			self.__waitloader = None

			self.__renderworker.start()

	def __render_repeat(self):
		QtCore.QTimer.singleShot(10, self.__render_repeat_aux)

	def __render_thread(self):
		thread = QtCore.QThread()
		worker = RenderWorker(
			(
				self.goutput.width(),
				self.goutput.height()
			),
			self.data,
			self.senergy.value() / 10.0,
			self.spitch.value(),
			self.OOR(),
			self.cheat.isChecked()
		)
		worker.moveToThread(thread)

		# this is essential when worker is in local scope!
		thread.worker = worker

		thread.started.connect(worker.run)
		worker.done.connect(self.__render_done)
		worker.progressed.connect(self.__load_prog)
		worker.finished.connect(self.__render_repeat)
		worker.finished.connect(thread.quit)

		return thread

	def RenderWorker(self):
		if not self.__renderworker.isRunning():
			self.__renderworker = self.__render_thread()
			self.__renderworker.start()
		else:
			self.__waitloader = True

	def bloadPressed(self):
		options = QtWidgets.QFileDialog.Options()
		#options |= QtWidgets.QFileDialog.DontUseNativeDialog
		fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
			self,
			"Open a media file", 
			"",
			"Media Files (*);", 
			options=options
		)
		if fileName:
			self.fileName = Path(fileName)
			self.setWindowTitle(f"PythonDancer - {self.fileName.name}")
			self.plabel.setText(f"Opening video: {self.fileName.name}")
			self.data = {}
			self.disableUX()
			self.LoadWorker(self.fileName)

	def bfunscriptPressed(self):
		if (not self.result):
			return

		options = QtWidgets.QFileDialog.Options()
		#options |= QtWidgets.QFileDialog.DontUseNativeDialog
		fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
			self,
			"Save a funscript", 
			str(self.fileName.with_suffix(".funscript").resolve()), 
			"Funscript Files (*.funscript)", 
			options=options
		)
		if fileName:
			with open(fileName, "w") as f:
				dump_funscript(f, self.result)

	def bheatmapPressed(self):
		QtWidgets.QMessageBox.about(self, "Sample Text", "Not Implemented!")

	def cplpPressed(self):
		self.LoadWorker(self.fileName)

	def cheatPressed(self):
		self.RenderWorker()

	def automap(self):
		if (self.cmap.isChecked() and len(self.data) > 0):
			pitch, energy = autoval(self.data, tpi=self.stpitch.value(), ten=self.stspeed.value())
			self.spitch.setValue(int(pitch))
			self.senergy.setValue(int(energy * 10.0))

	def cmapPressed(self):
		self.automap()
		self.RenderWorker()

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	window = MainUi()
	window.show()
	sys.exit(app.exec_())
