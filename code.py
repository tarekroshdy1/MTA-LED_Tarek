import time
import microcontroller
from board import NEOPIXEL
import displayio
import adafruit_display_text.label
from adafruit_datetime import datetime
from adafruit_bitmap_font import bitmap_font
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network
from adafruit_pyportal import PyPortal

STOP_ID = 'A44'
DATA_SOURCE = 'https://api.wheresthefuckingtrain.com/by-id/A44'
DATA_LOCATION = "./data"
UPDATE_DELAY = 15
SYNC_TIME_DELAY = 30
MINIMUM_MINUTES_DISPLAY = 1
BACKGROUND_IMAGE = 'dashboard.bmp'
ERROR_RESET_THRESHOLD = 3

def get_arrival_in_minutes_from_now(now, date_str):
    train_date = datetime.fromisoformat(date_str).replace(tzinfo=None)
    return round((train_date - now).total_seconds() / 60.0)

def get_arrival_times():
    print("Fetching arrival times...")
    try:
        stop_trains = network.fetch_data(DATA_SOURCE, json_path=("./data"))
        print("Data fetched: ", stop_trains)
    except Exception as e:
        print("Error fetching data: ", e)
        raise e

    print("Stop retrieved")
    stop_data = stop_trains[0]
    stop_dataextra = stop_trains[1]
    northbound_trains = [x['time'] for x in stop_data['N']]
    southbound_trains = [x['time'] for x in stop_dataextra['N']]

    now = datetime.now()
    print("Now: ", now)

    northbound_arrivals = [get_arrival_in_minutes_from_now(now, x) for x in northbound_trains]
    southbound_arrivals = [get_arrival_in_minutes_from_now(now, x) for x in southbound_trains]

    n = [str(x) for x in northbound_arrivals if x >= MINIMUM_MINUTES_DISPLAY]
    s = [str(x) for x in southbound_arrivals if x >= MINIMUM_MINUTES_DISPLAY]

    n0 = n[0] if len(n) > 0 else '-'
    n1 = n[1] if len(n) > 1 else '-'
    s0 = s[0] if len(s) > 0 else '-'
    s1 = s[1] if len(s) > 1 else '-'

    return n0, n1, s0, s1

def update_text(n0, n1, s0, s1):
    text_lines[2].text = "%s,%s m" % (n0, n1)
    text_lines[4].text = "%s,%s m" % (s0, s1)
    display.root_group = group

# --- Display setup ---
matrix = Matrix()
display = matrix.display
network = Network(status_neopixel=NEOPIXEL, debug=False)

# --- Drawing setup ---
group = displayio.Group()
bitmap = displayio.OnDiskBitmap(open(BACKGROUND_IMAGE, 'rb'))
colors = [0x444444, 0xDD8000]  # [dim white, gold]

font = bitmap_font.load_font("fonts/6x10.bdf")
text_lines = [
    displayio.TileGrid(bitmap, pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter())),
    adafruit_display_text.label.Label(font, color=colors[0], x=20, y=3, text="Clinton"),
    adafruit_display_text.label.Label(font, color=colors[1], x=20, y=11, text="- mins"),
    adafruit_display_text.label.Label(font, color=colors[0], x=20, y=20, text="Clinton"),
    adafruit_display_text.label.Label(font, color=colors[1], x=20, y=28, text="- mins"),
]
for x in text_lines:
    group.append(x)
display.root_group = group

error_counter = 0
last_time_sync = None
while True:
    try:
        if last_time_sync is None or time.monotonic() > last_time_sync + SYNC_TIME_DELAY:
            # Sync clock to minimize time drift
            print("Syncing local time...")
            network.get_local_time()
            last_time_sync = time.monotonic()
        arrivals = get_arrival_times()
        update_text(*arrivals)
        error_counter = 0  # Reset error counter on successful fetch
    except (ValueError, RuntimeError, Exception) as e:
        print("Some error occurred, retrying! -", e)
        error_counter += 1
        if error_counter > ERROR_RESET_THRESHOLD:
            print("Error threshold exceeded, resetting microcontroller...")
            microcontroller.reset()

    time.sleep(UPDATE_DELAY)
