"""The avatar's eye: IMX500 AI Camera presence watcher + frame source.

Person detection runs ON THE SENSOR (Sony IMX500 neural accelerator) — no
frames leave the camera for presence sensing, only detection metadata.
When someone arrives after a long absence the node greets them through the
buzzer/voice box. The same camera hands /observe its stills.

Degrades gracefully: without picamera2/imx500 the node falls back to
rpicam-still captures and presence stays off.

Config ("presence" section):
  {"enabled": true, "score": 0.55, "greet_after_min": 30}
"""

import threading
import time

MODEL = ("/usr/share/imx500-models/"
         "imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk")
PERSON_CLASS = 0        # COCO
LINGER_S = 60           # still "present" this long after last sighting


class Eye:
    def __init__(self, conf, on_arrival=None):
        conf = conf or {}
        self.enabled = False
        self.present = False
        self.last_seen = 0.0
        self.score = conf.get("score", 0.55)
        self.greet_after = conf.get("greet_after_min", 30) * 60
        self.on_arrival = on_arrival
        if conf.get("enabled", True) is False:
            print("eye: disabled by config")
            return
        try:
            from picamera2 import Picamera2
            from picamera2.devices import IMX500
        except ImportError as e:
            print(f"eye: picamera2 unavailable ({e}); presence off")
            return
        try:
            self.imx500 = IMX500(MODEL)  # uploads network to the sensor
            self.cam = Picamera2(self.imx500.camera_num)
            self.cam.configure(self.cam.create_preview_configuration(
                main={"size": (1280, 960), "format": "RGB888"},
                controls={"FrameRate": 10}))
            self.cam.start()
            self.enabled = True
            threading.Thread(target=self._watch, daemon=True).start()
            print("eye: open (on-sensor person detection)")
        except Exception as e:
            print(f"eye: init failed ({e}); presence off")

    def _person_in(self, metadata):
        outs = self.imx500.get_outputs(metadata)
        if outs is None or len(outs) < 3:
            return False
        scores, classes = outs[1].flatten(), outs[2].flatten()
        return any(int(c) == PERSON_CLASS and float(s) >= self.score
                   for s, c in zip(scores, classes))

    def _watch(self):
        while True:
            try:
                seen = self._person_in(self.cam.capture_metadata())
                now = time.time()
                if seen:
                    if not self.present:
                        gap = now - self.last_seen
                        self.present = True
                        if gap >= self.greet_after and self.on_arrival:
                            print(f"eye: arrival after {int(gap / 60)}m away")
                            self.on_arrival()
                    self.last_seen = now
                elif self.present and now - self.last_seen > LINGER_S:
                    self.present = False
            except Exception as e:
                print(f"eye: watch error ({e})")
                time.sleep(5)
            time.sleep(0.4)

    def snapshot(self, path):
        """Grab a still from the running camera. True on success."""
        if not self.enabled:
            return False
        self.cam.capture_file(path)
        return True
