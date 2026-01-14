import librosa
import numpy as np
from json import dump
from scipy.optimize import minimize
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from audioread import audio_open

VERSION="?"
HEATMAP = LinearSegmentedColormap.from_list("intensity",["w", "g", "orange", "r"], N=256)

#TODO: Fix action lag that happens sometimes, maybe change hop?
def load_audio_data(audio_file, hop_length=1024, frame_length=1024, plp=True):
	y, sr=None,None
	with audio_open(audio_file) as f:
		y, sr = librosa.load(f, sr=None, mono=True)

	# Compute beats
	onset = None
	if (plp):
		pulse = librosa.beat.plp(y=y, sr=sr, hop_length=hop_length)
		onset = pulse.T

	_, beats = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset, hop_length=hop_length, trim=False, units="time")

	# Compute energy (RMS)
	rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
	frames = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

	# Compute pitch
	pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=hop_length, center=True)

	pitches = np.fmax(0.01, pitches)
	magnitudes = np.fmax(0.01, magnitudes)
	#TODO: The fuck does this do
	pitches = np.sum(pitches * magnitudes, axis=0) / np.sum(magnitudes, axis=0)

	#Funny segment thing
	last = 0
	splits = [0]
	for k,v in enumerate(frames):
		if last >= len(beats):
			break
		if v > beats[last]:
			if (last > 0):
				#splits.append(int((k + splits[-1]) / 2))
				splits.append(k)
			last += 1
	splits.append(-1)

	frms = [np.sum(rms[splits[i-1]:splits[i]]) for i in range(len(beats))]
	fpitch = [np.sum(pitches[splits[i-1]:splits[i]]) for i in range(len(beats))]

	#Fix divide by zero
	fpitch = np.fmax(0.01, fpitch)
	frms = np.fmax(0.01, frms)

	return {
		"at": librosa.get_duration(y=y, sr=sr, hop_length=hop_length),
		"beats": beats,
		"pitch": np.log10(fpitch),
		"energy": frms
	}

def normalize(data):
	fmin, fmax = np.min(data), np.max(data)
	return np.array([(value-fmin)/(fmax-fmin) for value in data])

def default_peak(pos, at, last_pos, last_at):
	return [(at, min(max(0,pos),100))]

def int_at(pos, at, last_pos, last_at, limit):
	before_ratio = abs(last_pos - limit)
	after_ratio = abs(pos - limit)

	return (before_ratio * at + after_ratio * last_at) / (after_ratio + before_ratio)

def create_peak_bounce(pos, at, last_pos, last_at):
	actions = []
	action = lambda pos,at: actions.append(default_peak(pos,at,0,0)[0])

	if last_pos < 0:
		tmp_at = int_at(pos, at, last_pos, last_at, 0)
		action(0, tmp_at)
	elif last_pos > 100:
		tmp_at = int_at(pos, at, last_pos, last_at, 100)
		action(100, tmp_at)

	if pos > 100:
		tmp_at = int_at(pos, at, last_pos, last_at, 100)
		action(100, tmp_at)
		action(200 - pos, at)
	elif pos < 0:
		tmp_at = int_at(pos, at, last_pos, last_at, 0)
		action(0, tmp_at)
		action(-pos, at)
	else:
		action(pos, at)
	
	return actions

def create_peak_fold(pos, at, last_pos, last_at):
	actions = []
	action = lambda pos,at: actions.append(default_peak(pos,at,0,0)[0])

	int_att = (last_at + at) / 2
	travel = abs(last_pos - pos) / 2
	if last_pos < 0:
		action(last_pos + travel, int_att)
	elif last_pos > 100:
		action(last_pos - travel, int_att)

	if pos < 0:
		action(last_pos - travel, int_att)
		action(last_pos, at)
	elif pos > 100:
		action(last_pos + travel, int_att)
		action(last_pos, at)
	else:
		action(pos, at)
	
	return actions

peaks = [default_peak, create_peak_bounce, create_peak_fold]

def create_actions_barrier(data, start_time=0, overflow=0):
	last_at = start_time
	last_pos = 50

	actions = []
	for unoffset_pos, at, offset in zip(data["energy_to_pos"], data["beats"], data["offsets"]):
		# up
		intermediate_at = (at + last_at) / 2
		pos = unoffset_pos + offset
		actions += peaks[int(overflow)](pos, intermediate_at, last_pos, last_at)
		last_at = intermediate_at
		last_pos = pos

		# down
		pos = (unoffset_pos * -1) + offset
		actions += peaks[int(overflow)](pos, at, last_pos, last_at)
		last_at = at
		last_pos = pos

	return actions

def create_actions(data, energy_multiplier=1, pitch_range=100, overflow=0, amplitude_centering=0, center_offset=0):
	# Clone data to avoid modifying original
	processed_data = data.copy()
	
	normalized_pitch = normalize(processed_data["pitch"])
	normalized_energy = normalize(processed_data["energy"])
	
	pitch_bias = (100 - pitch_range) / 2
	
	# Determine length based on energy length as per JS slice(0, normalized_energy.length)
	length = len(normalized_energy)
	
	# Compute offsets with new formula
	# JS: pitch * pitch_range + pitch_bias + amplitude_centering * normalized_energy[i] + center_offset
	# Vectorized numpy operation:
	processed_data["offsets"] = (
		normalized_pitch[:length] * pitch_range + 
		pitch_bias + 
		amplitude_centering * normalized_energy + 
		center_offset
	)
	
	processed_data["energy_to_pos"] = normalized_energy * energy_multiplier * 50
	
	return create_actions_barrier(processed_data, overflow=overflow)

def _speed(A, B, smax=400.0):
	v = abs(B[1] - A[1]) / (B[0] - A[0])
	return v / smax
def speed(A,B, **kwargs):
	return max(min(_speed(A,B, **kwargs),1.0),0.0)

def autoval(data, tpi=15, target_speed=300, v2above=0.6, opt=1):
	def cmean(pitch):
		result = create_actions(data, energy_multiplier=0, pitch_range=pitch)
		_,Y = map(list, zip(*result))
		return np.average(Y)

	def pdst(p):
		a,b = cmean(p), tpi
		return abs(a - b)

	pres = minimize(pdst, (100,), method="Nelder-Mead", bounds=((-200,200),))
	pres = pres.x[0]

	def cemean(energy):
		result = create_actions(data, energy_multiplier=energy, pitch_range=pres)
		speeds = np.array([_speed(result[i],result[i+1],smax=1.0) for i in range(len(result)-1)], dtype=np.float32)
		return abs(np.average(speeds) - target_speed)

	# V2 works abit like lazy clustering
	# I should do more clustering
	def cemeanv2(energy):
		result = create_actions(data, energy_multiplier=energy, pitch_range=pres)
		speeds = np.array([_speed(result[i], result[i+1], smax=1.0) for i in range(len(result) - 1)], dtype=np.float32)
		
		# Counting the number of speeds above the target speed
		above_target = np.sum(speeds > target_speed)
		# Calculate the percentage of speeds above the target speed
		percentage_above_target = above_target / len(speeds)
		
		# Ensure at least 20% of speeds are above the target speed
		return abs(percentage_above_target - v2above) # Ensure 20% (0.2) are above the target speed

	def celen(energy):
		result = create_actions(data, energy_multiplier=energy, pitch_range=pres)
		actual_percentage = np.mean([abs(result[i][1] - result[i+1][1])/100 for i in range(len(result) - 1)], dtype=np.float64)
		return abs(actual_percentage - v2above)

	optimizers = [
		cemean,
		cemeanv2,
		celen
	]
	eres = minimize(optimizers[opt], (10,), method="Nelder-Mead", bounds=((0,100),), options={'xatol': 1e-10, 'disp': True})
	eres = eres.x[0]

	return pres, eres

#TODO: Do better
def render_heatmap(data, energy, pitch, oor, amplitude_centering=0, center_offset=0, w=4096, h=128):
	result = create_actions(
		data, 
		energy_multiplier=energy, 
		pitch_range = pitch,
		overflow = oor,
		amplitude_centering=amplitude_centering,
		center_offset=center_offset
	)
	speeds = np.array([speed(result[i],result[i+1]) for i in range(len(result)-1)])
	gradient = np.vstack([speeds]*h)

	dpi = mpl.rcParams["figure.dpi"]
	fig = Figure(figsize=(w/dpi, h/dpi), tight_layout=True)
	plot = fig.add_subplot(111)
	plot.imshow(gradient, cmap=HEATMAP, interpolation="lanczos")
	plot.axis("off")
	return fig

def dump_csv(f, data):
	for at, pos in data:
		f.write(f"{at*1000},{round(pos)}\n")

def dump_funscript(f, data):
	return dump({
		"actions": [{"at": int(at*1000), "pos": round(pos)} for at,pos in data],
		"inverted": False,
		"metadata": {
			"creator": "PythonDancer",
			"description": "",
			"duration": int(data[-1][0]),
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

if __name__ == "__main__":
	data = load_audio_data("/mnt/newfiles/Video/MBad2/inter_cgi/SUPERNOVA 2 - HMV⧸PMV [COMBOBEAT] [3373395].mp4")
	print(data)