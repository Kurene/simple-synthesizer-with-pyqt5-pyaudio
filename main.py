"""
License: MIT
"""

import sys
import pyaudio
import numpy as np
import threading
from scipy import signal

def MarkovChordProg():
    def __init__():
        self.S = ["C", "Dm", "Em", "F", "G", "Am", "Bdim"]
        P = np.array([[0.10, 0.10, 0.10, 0.20, 0.35, 0.10, 0.05],
                     [0.10, 0.10, 0.20, 0.09, 0.30, 0.20, 0.01],
                     [0.05, 0.20, 0.10, 0.30, 0.20, 0.14, 0.01],
                     [0.20, 0.05, 0.19, 0.10, 0.10, 0.35, 0.01],
                     [0.30, 0.05, 0.10, 0.10, 0.10, 0.30, 0.05],
                     [0.10, 0.10, 0.05, 0.30, 0.25, 0.10, 0.10],
                     [0.30, 0.05, 0.05, 0.15, 0.10, 0.30, 0.05],
                    ])
        self.P_cum = [np.array([P[m, 0:n+1].sum() for n in range(P.shape[1])]) for m in range(P.shape[0])]

    def step(state_index):
        #state_index = 0
        r = np.random.random()
        state_index = np.where(self.P_cum[state_index] > r)[0][0]
        return state_index, self.S[state_index]
        #time.sleep(2)

    

class Oscillator():
    def __init__(self, rate, n_chunk, freq, gain=0.1):
        self.rate = rate
        self.n_chunk = n_chunk
        self.freq = freq
        self.gain = gain
        
        self.state = False
        self.pi2_t0 = 2 * np.pi / (rate / freq)
        self.offset = 0
        self.period = n_chunk * rate
        
        self.change_waveform("sin")

    def out(self):
        x =  np.arange(self.offset, self.offset + self.n_chunk)
        chunk = self.gain * self.generator(self.pi2_t0 * x)
        self.offset += self.n_chunk
        if self.offset == self.period:
            self.offset = 0
        return chunk
    
    def is_run(self):
        return self.state
        
    def start(self):
        self.state = True
        
    def stop(self):
        self.state = False
        self.offset = 0
        
    def change_waveform(self, type):
        self.type = type
        if self.type == "sin":
            self.generator = np.sin
        elif self.type == "saw":
            self.generator = signal.sawtooth


class Synthesizer():
    waveform = ["sin", "saw"]
    def __init__(self, rate=44100, n_chunk=1024):
        self.rate = rate
        self.n_chunk = n_chunk
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=rate, output=1,
                                  frames_per_buffer=n_chunk)
        self.oscillators = []
        
        t = threading.Thread(target=self.render)
        t.start()
     
    def __seek_osc(self, freq):
        osc = None
        for o in self.oscillators:
            if freq == o.freq:
                osc = o
        if osc is None:
            osc = Oscillator(self.rate, self.n_chunk, freq)
            self.oscillators.append(osc)
        return osc
    
    def render(self):
        while self.stream.is_active():
            
            chunk = np.zeros(self.n_chunk)
            for osc in self.oscillators:
                if osc.is_run():
                    chunk += osc.out()
            self.stream.write(chunk.astype(np.float32).tostring())
            
    def request(self, freq):
        osc = self.__seek_osc(freq)
        if not osc.is_run():
            osc.start()
            return True
        else:
            osc.stop()
            return False

    def terminate(self):
        for osc in self.oscillators:
            osc.stop()
        self.stream.close()
        self.p.terminate()

    def change_waveform(self):
        r = np.random.randint(len(Synthesizer.waveform))
        type = Synthesizer.waveform[r]
        for osc in self.oscillators:
            osc.change_waveform(type)
        return type
        
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QHBoxLayout, QMessageBox
from PyQt5.QtGui import QKeySequence
import sys
from functools import partial

class MyWidget(QWidget):
    pitch_class = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
    pitch_freq_di = {pn+str(k): 440*2**(((12*k+idx)-48)/12)
                     for idx, pn in enumerate(pitch_class)\
                     for k in range(0, 9)}
    
    def __init__(self, synthesizer=None, keyset=(39, 52)):
        super().__init__()
        self.synthesizer = synthesizer
        self.keyset = keyset
        self.keymap = { "Q": "C3", "2": "C#3", "W": "D3", "3": "D#3", "E": "E3",
                        "R": "F3", "5": "F#3", "T": "G3", "6": "G#3", 
                        "Y": "A4", "7": "A#4", "U": "B4", "I": "C4",}
        self.params_list = []
        self.init_ui() 
        self.show()
        
    def __make_bt(self, id, name):
        bt = QPushButton(name)
        if "#" in name:
            bt.key_off = lambda : bt.setStyleSheet("background-color: #999999")
            bt.key_on  = lambda : bt.setStyleSheet("background-color: #9999ff")
        else:
            bt.key_off = lambda : bt.setStyleSheet("background-color: #ffffff")
            bt.key_on  = lambda : bt.setStyleSheet("background-color: #9999ff")
        bt.key_off()
        bt.setContentsMargins(0,0,0,0)
        freq = MyWidget.pitch_freq_di[name]
        params = {"freq": freq, "name": name, "id": id, "self_bt": bt}
        bt.clicked.connect(partial(self.buttonClicked, params))
        bt.setMaximumWidth(50)
        bt.setMaximumHeight(300)
        print(f"{name}\t{freq}")
        self.params_list.append(params)
        return bt
        
    def init_ui(self):
        self.setStyleSheet("background-color: #eeeeee")
        self.setWindowTitle('Synthesizer')

        keys = QHBoxLayout()
        for n in range(self.keyset[0], self.keyset[1]):
            name = MyWidget.pitch_class[n%12] + str(n//12)
            id = n - self.keyset[0]
            keys.addWidget(self.__make_bt(id, name))
        self.setLayout(keys)

        self.setGeometry(300, 300, 720, 160) # x, y, width, height

          
    def buttonClicked(self, params):
        sender = self.sender()
        if self.synthesizer is not None:
            state = self.synthesizer.request(params["freq"])
            if state:
                params["self_bt"].key_on()
            else:
                params["self_bt"].key_off()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',  "Are you sure to quit?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.synthesizer is not None:
                self.synthesizer.terminate()
            event.accept()
        else:
            event.ignore()          

    def keyPressEvent(self, event):
        # Over
        key = QKeySequence(event.key()).toString()
        #print(key)
        if key in self.keymap.keys():
            v = self.keymap[key]
            for p in self.params_list:
                if p["name"] == v:
                    self. buttonClicked(p)
                    pass
        elif key == "@":
            type = self.synthesizer.change_waveform()
            print(type)

if __name__ == '__main__':
    synthesizer = Synthesizer()
    app = QApplication(sys.argv)
    window = MyWidget(synthesizer=synthesizer)
    sys.exit(app.exec_())
