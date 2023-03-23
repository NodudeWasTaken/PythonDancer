import librosa
import numpy as np

#TODO: Fix action lag that happens sometimes, maybe change hop?
def load_audio_data(audio_file, hop_length=1024, frame_length=1024):
	y, sr = librosa.load(audio_file, sr=None, mono=True)

	# Compute beats
	tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length, trim=False, units="time")

	# Compute energy (RMS)
	rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
	frames = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

	# Compute pitch
	pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=hop_length, center=True)
	#TODO: The fuck does this do
	mean_pitches = np.sum(pitches * magnitudes, axis=0) / np.sum(magnitudes, axis=0)

	rms = np.nan_to_num(rms)
	mean_pitches = np.nan_to_num(mean_pitches)

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
	fpitch = [np.sum(mean_pitches[splits[i-1]:splits[i]]) for i in range(len(beats))]

	#TODO: Nan sometimes
	fpitch = np.array([max(i,1) for i in fpitch])

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

def create_actions(data, energy_multiplier=1, pitch_range=100, overflow=0):
	data["offsets"] = np.array([i * pitch_range + ((100 - pitch_range) / 2) for i in normalize(data["pitch"])])
	data["energy_to_pos"] = np.array([i * energy_multiplier * 50 for i in normalize(data["energy"])])
	return create_actions_barrier(data, overflow=overflow)

def dump_csv(data):
	with open("test.csv", "w") as f:
		for at, pos in data:
			f.write(f"{at*1000},{round(pos)}\n")

if __name__ == "__main__":
	dump_csv(create_actions(load_audio_data("STAR.wav"), energy_multiplier=2))