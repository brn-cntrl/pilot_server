from emotibit_streamer_2 import EmotiBitStreamer
import time

EMOTIBIT_PORT_NUMBER = 9005

emotibit_streamer = EmotiBitStreamer(EMOTIBIT_PORT_NUMBER)

emotibit_streamer.start()

emotibit_streamer.start_baseline_collection()

time.sleep(60)

emotibit_streamer.stop_baseline_collection()

time.sleep(2.2 * 60)

emotibit_streamer.stop()