"""Passive-buzzer voice for the Pi node (gpiozero/lgpio software PWM).

Wiring options (config "buzzer" section):
  {"pin": 4, "common": "3v3"}  buzzer between 3V3 and GPIO4 -- idle HIGH
  {"pin": 4, "common": "gnd"}  buzzer between GND and GPIO4 -- idle LOW
  {"common": "off"}            no buzzer; all calls become no-ops

Melody tables duplicated from device/tunes.py (which is MicroPython-bound);
keep them in sync if you change one. All tunes original.
"""

import time

N = {
    "C4": 262, "D4": 294, "E4": 330, "F4": 349, "G4": 392, "A4": 440,
    "B4": 494, "C5": 523, "D5": 587, "E5": 659, "F5": 698, "FS5": 740,
    "G5": 784, "A5": 880, "B5": 988, "C6": 1047, "D6": 1175, "E6": 1319,
    "R": 0,
}


def _seq(*pairs):
    return [(N[k], ms) for k, ms in pairs]


MOOD_JINGLES = {
    "curious":  _seq(("E5", 110), ("G5", 110), ("B5", 160), ("R", 60), ("A5", 140)),
    "cheerful": _seq(("C5", 90), ("E5", 90), ("G5", 90), ("C6", 200)),
    "pensive":  _seq(("A4", 200), ("R", 80), ("E5", 180), ("R", 80), ("C5", 260)),
    "wistful":  _seq(("G5", 180), ("E5", 180), ("D5", 160), ("C5", 320)),
    "alert":    _seq(("C6", 70), ("R", 40), ("C6", 70), ("R", 40), ("G5", 150)),
}
DEFAULT_MOOD = "curious"
QUESTION_TAIL = _seq(("R", 90), ("D5", 80), ("FS5", 80), ("A5", 220))
SONGS = {
    "docket_rag": _seq(("C5", 120), ("E5", 120), ("G5", 120), ("A5", 160),
                       ("G5", 120), ("E5", 120), ("C5", 160), ("R", 80),
                       ("D5", 120), ("E5", 120), ("C5", 260)),
    "harbor_waltz": _seq(("E5", 260), ("C5", 200), ("A4", 320), ("R", 100),
                         ("B4", 260), ("G4", 200), ("E4", 380), ("R", 100),
                         ("A4", 420)),
    "voltage_march": _seq(("C5", 100), ("C5", 100), ("G4", 100), ("G4", 100),
                          ("A4", 100), ("B4", 100), ("C5", 220), ("R", 80),
                          ("G4", 100), ("C5", 260)),
}
MOOD_SONG = {
    "cheerful": "docket_rag", "curious": "docket_rag",
    "alert": "voltage_march", "pensive": "harbor_waltz",
    "wistful": "harbor_waltz",
}
BOOT_CHIRP = _seq(("C5", 80), ("G5", 80), ("C6", 160))


class Buzzer:
    def __init__(self, conf=None):
        conf = conf or {}
        self.common = conf.get("common", "3v3")
        self.dev = None
        if self.common == "off":
            return
        try:
            from gpiozero import PWMOutputDevice
            self.idle = 1.0 if self.common == "3v3" else 0.0
            self.dev = PWMOutputDevice(conf.get("pin", 4), frequency=440,
                                       initial_value=self.idle)
        except Exception as e:
            print(f"buzzer disabled ({e}); running silent")

    def play(self, notes, gap_ms=30):
        if not self.dev:
            return
        try:
            for freq, ms in notes:
                if freq:
                    self.dev.frequency = freq
                    self.dev.value = 0.5
                else:
                    self.dev.value = self.idle
                time.sleep(ms / 1000)
                self.dev.value = self.idle
                time.sleep(gap_ms / 1000)
        finally:
            self.dev.value = self.idle

    def boot(self):
        self.play(BOOT_CHIRP)

    def mood(self, mood, question=False):
        tune = list(MOOD_JINGLES.get(mood, MOOD_JINGLES[DEFAULT_MOOD]))
        if question:
            tune += QUESTION_TAIL
        self.play(tune)

    def sing(self, mood):
        name = MOOD_SONG.get(mood, "docket_rag")
        self.play(SONGS[name])
        return name
