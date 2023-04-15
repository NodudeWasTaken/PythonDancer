import sys
import pyqtgraph as pg
import PyQt5.QtWidgets as QtWidgets
from PyQt5 import uic
from PyQt5 import QtGui, QtCore
from pathlib import Path
import subprocess

from test import load_audio_data, create_actions

class MainUi(QtWidgets.QMainWindow):
	def __init__(self):
		super(MainUi, self).__init__()
		uic.loadUi("dancerUI.ui", self)
		self.OOR = 0

		self.babout = self.findChild(QtWidgets.QToolButton, "aboutButton")
		self.bload = self.findChild(QtWidgets.QToolButton, "mediaButton")
		self.babout.clicked.connect(self.baboutPressed)
		self.bload.clicked.connect(self.bloadPressed)
		self.pbat = self.findChild(QtWidgets.QProgressBar, "progressBar")
		self.pbat.setValue(0)

		self.ginput = self.findChild(pg.PlotWidget, "audioInput")
		self.goutput = self.findChild(pg.PlotWidget, "audioOutput")
		self.ginput.setMouseEnabled(False,False)
		self.goutput.setMouseEnabled(False,False)

		self.bbounce = self.findChild(QtWidgets.QRadioButton, "bounceButton")
		self.bcrop = self.findChild(QtWidgets.QRadioButton, "cropButton")
		self.bfold = self.findChild(QtWidgets.QRadioButton, "foldButton")
		self.bbounce.clicked.connect(self.bbouncePressed)
		self.bcrop.clicked.connect(self.bcropPressed)
		self.bfold.clicked.connect(self.bfoldPressed)

		self.spitch = self.findChild(QtWidgets.QSlider, "pitchSlider")
		self.senergy = self.findChild(QtWidgets.QSlider, "energySlider")
		self.spitch.setRange(-200,200)
		self.spitch.setValue(100)
		self.senergy.setRange(0,10)
		self.senergy.setValue(1)
		self.spitch.sliderReleased.connect(self.draw_fun)
		self.senergy.sliderReleased.connect(self.draw_fun)

		self.bfunscript = self.findChild(QtWidgets.QPushButton, "funscriptButton")
		self.bheatmap = self.findChild(QtWidgets.QPushButton, "heatmapButton")
		self.bfunscript.clicked.connect(self.bfunscriptPressed)
		self.bheatmap.clicked.connect(self.bheatmapPressed)

		self.show()

	def speed(self,A,B):
		return (abs(B[1] - A[1]) / abs(B[0] - A[0])) / 500

	def baboutPressed(self):
		print("baboutPressed")

	def bbouncePressed(self):
		self.OOR = 1
		self.draw_fun()

	def bcropPressed(self):
		self.OOR = 0
		self.draw_fun()

	def bfoldPressed(self):
		self.OOR = 2
		self.draw_fun()

	def bloadPressed(self):
		options = QtWidgets.QFileDialog.Options()
		options |= QtWidgets.QFileDialog.DontUseNativeDialog
		fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
		if fileName:
			fileName = Path(fileName)
			self.setWindowTitle(f"Video: {fileName.name}")
			self.load_file(fileName)

	def load_file(self, fileName):
		audioFile = Path("tmp", fileName.name)
		audioFile.parent.mkdir(parents=True, exist_ok=True)

		#TODO: QThread
		self.pbat.setValue(0)
		subprocess.check_call([
			"ffmpeg",
			"-y",
			"-i", fileName,
			"-ar", "48000",
			audioFile
		])
		self.pbat.setValue(25)

		self.data = load_audio_data(audioFile)
		self.pbat.setValue(90)
		self.ginput.clear()
		self.ginput.plot(self.data["pitch"], label="pitch", linewidth=.3, pen="#E69F00")
		self.ginput.plot(self.data["energy"], label="energy", linewidth=.3, pen="#0072B2")
		self.pbat.setValue(100)
		self.draw_fun()

	def draw_fun(self):
		#TODO: QThread
		pitch = self.spitch.value()
		energy = self.senergy.value()
		outofrange = self.OOR

		print("spitchPressed", pitch)
		print("senergyPressed", energy)

		self.result = create_actions(
			self.data, 
			energy_multiplier=energy,
			pitch_range=pitch,
			overflow=outofrange
		)

		self.goutput.clear()

		cm = pg.colormap.get("CET-L9")
		pen = pg.mkPen(QtGui.QColor(255, 0, 0), width=0.5)
		for i in range(len(self.result)-1):
			A,B = self.result[i], self.result[i+1]
			pen.setColor(cm[self.speed(A, B)])
			self.goutput.plot((A[0],B[0]), (A[1],B[1]), pen=pen, clear=False)

	def bfunscriptPressed(self):
		print("bfunscriptPressed")

	def bheatmapPressed(self):
		print("bheatmapPressed")

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	window = MainUi()
	app.exec_()
