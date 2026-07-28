import serial
import serial.tools.list_ports
import threading
import time

BAUD_RATE    = 115200   
READ_TIMEOUT = 10       
PREFIX       = "READING:"

MOCK_READINGS = {
    "A1": {
        "dark":  [120, 130, 115, 125, 118, 122, 119, 128],
        "white": [4000, 4200, 4500, 4600, 4700, 4550, 4300, 4100],
        "tooth": [1762, 1535, 1306, 2625, 2108, 2353, 2337, 3702],
    },
    "A2": {
        "dark":  [120, 130, 115, 125, 118, 122, 119, 128],
        "white": [4000, 4200, 4500, 4600, 4700, 4550, 4300, 4100],
        "tooth": [1896, 1274, 1115, 1867, 2272, 2093, 1971, 3766],
    },
    "B1": {
        "dark":  [120, 130, 115, 125, 118, 122, 119, 128],
        "white": [4000, 4200, 4500, 4600, 4700, 4550, 4300, 4100],
        "tooth": [2024, 1534, 1893, 2713, 2271, 2651, 2307, 3855],
    },
}

def list_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return []
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device}  —  {p.description}")
    return [p.device for p in ports]


def auto_detect_esp32():
    ports = serial.tools.list_ports.comports()
    keywords = ["CP210", "CH340", "UART", "USB Serial", "ESP32"]
    for p in ports:
        if any(kw.lower() in p.description.lower() for kw in keywords):
            print(f"Auto-detected ESP32 at: {p.device}  ({p.description})")
            return p.device
    return None


def parse_reading_line(line):
    line = line.strip()
    if not line.startswith(PREFIX):
        return None   

    try:
        data_part = line[len(PREFIX):]          
        values    = data_part.split(",")         
        integers  = [int(v.strip()) for v in values]

        if len(integers) != 8:
            print(f"WARNING: Expected 8 values, got {len(integers)}. Skipping.")
            return None

        if any(v < 0 or v > 65535 for v in integers):
            print(f"WARNING: Values out of valid range (0-65535). Skipping.")
            return None

        return integers

    except ValueError as e:
        print(f"WARNING: Could not parse line '{line}': {e}")
        return None

def read_from_serial(port=None, timeout=READ_TIMEOUT):
    if port is None:
        port = auto_detect_esp32()
        if port is None:
            print("ERROR: Could not auto-detect ESP32.")
            print("Run list_ports() to see available ports.")
            return None

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"Connected to {port} at {BAUD_RATE} baud.")
        print(f"Waiting for reading (timeout: {timeout}s)...")

        start = time.time()
        while time.time() - start < timeout:
            raw_line = ser.readline()
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="ignore")
            result = parse_reading_line(line)
            if result is not None:
                print(f"Received: {result}")
                ser.close()
                return result

        print("ERROR: Timed out waiting for reading.")
        ser.close()
        return None

    except serial.SerialException as e:
        print(f"ERROR: Could not open port {port}: {e}")
        return None

def read_mock(shade="A2", step="tooth"):
    if shade not in MOCK_READINGS:
        print(f"Unknown shade '{shade}'. Using A2.")
        shade = "A2"
    if step not in ("dark", "white", "tooth"):
        print(f"Unknown step '{step}'. Using tooth.")
        step = "tooth"

    values = MOCK_READINGS[shade][step]
    print(f"[MOCK] Simulating {step} reading for shade {shade}: {values}")
    return values

def read_manual():
    while True:
        raw = input("Enter 8 comma-separated sensor values: ").strip()
        result = parse_reading_line(PREFIX + raw)
        if result is not None:
            return result
        print("Invalid input. Try again.")

class SerialListener:
    def __init__(self, port=None, callback=None):
        self.port     = port or auto_detect_esp32()
        self.callback = callback
        self._thread  = None
        self._running = False

    def start(self):
        if self.port is None:
            print("ERROR: No port specified and auto-detect failed.")
            return
        self._running = True
        self._thread  = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        print(f"Serial listener started on {self.port}")

    def stop(self):
        self._running = False
        print("Serial listener stopped.")

    def _listen(self):
        try:
            ser = serial.Serial(self.port, BAUD_RATE, timeout=1)
            while self._running:
                raw_line = ser.readline()
                if not raw_line:
                    continue
                line   = raw_line.decode("utf-8", errors="ignore")
                result = parse_reading_line(line)
                if result is not None and self.callback:
                    self.callback(result)
            ser.close()
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._running = False

if __name__ == "__main__":
    print("=== Serial Reader — Standalone Test ===\n")
    print("--- Test 1: parse_reading_line() ---")

    valid   = "READING:1896,1274,1115,1867,2272,2093,1971,3766"
    invalid = "ERROR: AS7341 not found"
    short   = "READING:1896,1274,1115"

    print(f"Valid line   → {parse_reading_line(valid)}")
    print(f"Invalid line → {parse_reading_line(invalid)}")
    print(f"Short line   → {parse_reading_line(short)}")

    print("\n--- Test 2: read_mock() ---")
    for shade in ["A1", "A2", "B1"]:
        for step in ["dark", "white", "tooth"]:
            result = read_mock(shade=shade, step=step)

    print("\n--- Test 3: list_ports() ---")
    list_ports()

    print("\nAll tests passed.")