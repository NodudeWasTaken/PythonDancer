A port of https://github.com/ncdxncdx/FunscriptDancer to python

![The UI running](example.PNG)

Run it now by downloading the latest release exe!

Or run it like
```
git clone https://github.com/NodudeWasTaken/PythonDancer
cd PythonDancer
pip install -r requirements.txt

python -m dancer
python -m dancer --cli -h
```

CLI Interface
```
> PythonDancer.exe --cli -h
usage: libfun [-h] [--out_path OUT_PATH] [--csv] [-m] [-c] [-a] [-y] [--no_plp] [--cli] [--auto_pitch [0-100]]
              [--auto_speed [0-400]] [--pitch [-200-200]] [--energy [0-100]] [--overflow [0-2]]
              [audio_path]

Creates funscripts from audio

positional arguments:
  audio_path            Path to input media (default: None)

options:
  -h, --help            show this help message and exit
  --out_path OUT_PATH   Path to export funscript (default: None)
  --csv                 Export as CSV instead of funscript (default: False)
  -m, --heatmap         Export heatmap (default: False)
  -c, --convert         Automatically use ffmpeg to convert input media (default: False)
  -a, --automap         Automatically find suitable pitch and energy values (default: False)
  -y, --yes             Overwrite funscript (default: False)
  --no_plp              Disable PLP (default: False)
  --cli                 Use commandline (default: False)
  --auto_pitch [0-100]
  --auto_speed [0-400]
  --pitch [-200-200]
  --energy [0-100]
  --overflow [0-2]
```