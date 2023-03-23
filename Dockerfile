FROM python:3.10-windowsservercore-1809 as stage1
WORKDIR /build
RUN pip install pyinstaller
COPY . /build
RUN pip install -r requirements.txt
RUN pyinstaller --onefile kinter.py --name PythonDancer.exe

FROM scratch AS export-stage
COPY --from=stage1 /build/dist/PythonDancer.exe .