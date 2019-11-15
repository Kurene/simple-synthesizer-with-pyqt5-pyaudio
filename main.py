"""
License: MIT
"""
import sys
import pyaudio
import numpy as np
import threading
from scipy import signal

class Oscillator():
    def __init__(self, rate, n_chunk, freq, type, gain=0.1):
        self.rate = rate
        self.n_chunk = n_chunk
        self.freq = freq
        self.gain = gain
        
        self.state = False
        self.pi2_t0 = 2 * np.pi / (rate / freq)
        self.offset = 0
        self.period = n_chunk * rate
        
        self.change_waveform(type)

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
        self.type = Synthesizer.waveform[0]
        t = threading.Thread(target=self.render)
        t.start()
     
    def __seek_osc(self, freq):
        osc = None
        for o in self.oscillators:
            if freq == o.freq:
                osc = o
        if osc is None:
            osc = Oscillator(self.rate, self.n_chunk, freq, self.type)
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
        self.type = Synthesizer.waveform[r]
        for osc in self.oscillators:
            osc.change_waveform(self.type)
        return self.type
        
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QMessageBox
from PyQt5.QtGui import QKeySequence
import sys
from functools import partial

class MyWidget(QWidget):
    pitch_class = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
    pitch_freq_di = {pn+str(k): 440*2**(((12*k+idx)-48)/12)
                     for idx, pn in enumerate(pitch_class)\
                     for k in range(0, 9)}
    
    def __init__(self, synthesizer=None, keyset=(39, 52, 51, 64)):
        super().__init__()
        self.synthesizer = synthesizer
        self.keyset = keyset
        self.keymap = { 
                        "Q": "C4", "2": "C#4", "W": "D4", "3": "D#4", "E": "E4",
                        "R": "F4", "5": "F#4", "T": "G4", "6": "G#4", 
                        "Y": "A5", "7": "A#5", "U": "B5", "I": "C5",
                        "Z": "C3", "S": "C#3", "X": "D3", "D": "D#3", "C": "E3",
                        "V": "F3", "G": "F#3", "B": "G3", "H": "G#3", 
                        "N": "A4", "J": "A#4", "M": "B4", ",": "C4",
                      }
        self.params_list = []
        print("# ================================")
        print("# Initialize")
        print("# ================================")
        self.init_ui() 
        print("")
        print("# ================================")
        print("# <<Print key input>>")
        print("# ================================")
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
        bt.clicked.connect(partial(self.buttonClicked, params["freq"], [bt]))
        bt.setMaximumWidth(40)
        bt.setMaximumHeight(300)
        print(f"{id}\t{name}\t{freq}")
        self.params_list.append(params)
        return bt
        
    def init_ui(self):
        self.setStyleSheet("background-color: #eeeeee")
        self.setWindowTitle('Synthesizer')

        keys = QGridLayout()
        id = 0
        print(f"ID\tNote\tFreq")
        for n in range(self.keyset[0], self.keyset[1]):
            name = MyWidget.pitch_class[n%12] + str(n//12)
            pos = n - self.keyset[0]
            keys.addWidget(self.__make_bt(id, name), 1, pos)
            id += 1

        for n in range(self.keyset[2], self.keyset[3]):
            name = MyWidget.pitch_class[n%12] + str(n//12)
            pos = n - self.keyset[2]
            keys.addWidget(self.__make_bt(id, name), 0, pos)
            id += 1

        self.setLayout(keys)
        self.setGeometry(300, 300, 660, 160) # x, y, width, height

    def buttonClicked(self, freq, bt_list):
        sender = self.sender()
        if self.synthesizer is not None:
            state = self.synthesizer.request(freq)
            if state:
                for bt in bt_list:
                    bt.key_on()
            else:
                for bt in bt_list:
                    bt.key_off()

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
        bt_list = []
        freq = 0.0
        name = None
        if key in self.keymap.keys():
            
            v = self.keymap[key]
            for p in self.params_list:
                if p["name"] == v:
                    name = p["name"]
                    freq = p["freq"]
                    bt_list.append(p["self_bt"])
            self.buttonClicked(freq, bt_list)
            print(f"{key}: {name}")
        elif key == "@":
            type = self.synthesizer.change_waveform()
            print(type)

if __name__ == '__main__':
    synthesizer = Synthesizer()
    app = QApplication(sys.argv)
    window = MyWidget(synthesizer=synthesizer)
    sys.exit(app.exec_())
