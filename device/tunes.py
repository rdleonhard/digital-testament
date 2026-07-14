"""Buzzer voice for the avatar node.

Passive buzzer wired 3V3 <-> GPIO4: sound is PWM at 50% duty; SILENCE means
holding the pin HIGH so both buzzer terminals sit at the same potential (a
low idle pin would push DC through the coil).

All melodies are original compositions. Moods map to short jingles; questions
get a rising interrogative tail; [sing] gets a longer song picked by mood.
"""

import time

from machine import Pin, PWM

BUZZER_PIN = 4

# Note frequencies (Hz), equal temperament
N = {
    "C4": 262, "D4": 294, "E4": 330, "F4": 349, "G4": 392, "A4": 440,
    "B4": 494, "C5": 523, "D5": 587, "E5": 659, "F5": 698, "FS5": 740,
    "G5": 784, "A5": 880, "B5": 988, "C6": 1047, "D6": 1175, "E6": 1319,
    "R": 0,  # rest
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

# Rising interrogative tail appended when the avatar asks a question
QUESTION_TAIL = _seq(("R", 90), ("D5", 80), ("FS5", 80), ("A5", 220))

SONGS = {
    # bouncy little rag for good moods
    "docket_rag": _seq(("C5", 120), ("E5", 120), ("G5", 120), ("A5", 160),
                       ("G5", 120), ("E5", 120), ("C5", 160), ("R", 80),
                       ("D5", 120), ("E5", 120), ("C5", 260)),
    # slow falling waltz for remembering
    "harbor_waltz": _seq(("E5", 260), ("C5", 200), ("A4", 320), ("R", 100),
                         ("B4", 260), ("G4", 200), ("E4", 380), ("R", 100),
                         ("A4", 420)),
    # chipper march for busy moods
    "voltage_march": _seq(("C5", 100), ("C5", 100), ("G4", 100), ("G4", 100),
                          ("A4", 100), ("B4", 100), ("C5", 220), ("R", 80),
                          ("G4", 100), ("C5", 260)),
}

MOOD_SONG = {
    "cheerful": "docket_rag",
    "curious": "docket_rag",
    "alert": "voltage_march",
    "pensive": "harbor_waltz",
    "wistful": "harbor_waltz",
}

BOOT_CHIRP = _seq(("C5", 80), ("G5", 80), ("C6", 160))


class Buzzer:
    def __init__(self, pin=BUZZER_PIN):
        self.pin = pin
        self._idle()

    def _idle(self):
        # match the 3V3 rail: no potential across the coil
        Pin(self.pin, Pin.OUT, value=1)

    def play(self, notes, gap_ms=30):
        pwm = PWM(Pin(self.pin), freq=440, duty_u16=0)
        try:
            for freq, ms in notes:
                if freq:
                    pwm.freq(freq)
                    pwm.duty_u16(32768)
                else:
                    pwm.duty_u16(0)
                time.sleep_ms(ms)
                pwm.duty_u16(0)
                time.sleep_ms(gap_ms)
        finally:
            pwm.deinit()
            self._idle()

    def mood(self, mood, question=False):
        tune = list(MOOD_JINGLES.get(mood, MOOD_JINGLES[DEFAULT_MOOD]))
        if question:
            tune += QUESTION_TAIL
        self.play(tune)

    def sing(self, mood):
        name = MOOD_SONG.get(mood, "docket_rag")
        self.play(SONGS[name])
        return name
