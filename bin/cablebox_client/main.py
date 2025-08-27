#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import requests
from threading import Thread

# ==============================
# CONFIG
# ==============================
TAILSCALE_HOST = "http://100.69.71.33:8000"  # FS42 web remote Tailscale URL
API_ENDPOINT = f"{TAILSCALE_HOST}/api/command"

ENC_CLK = 11
ENC_DT = 0
IR_PIN = 9
DISP_CLK = 5
DISP_DIO = 6

# Available channels (real channels)
AVAILABLE_CHANNELS = [1, 15, 17, 19, 20, 21, 22, 23, 24]
#AVAILABLE_CHANNELS = [1, 10, 15, 17, 19, 20, 21, 22, 23, 24,  69, 70, 80]
# ==============================
# TM1637 DRIVER
# ==============================
class TM1637:
    def __init__(self, clk, dio):
        self.clk = clk
        self.dio = dio
        self._brightness = 7
        GPIO.setup(self.clk, GPIO.OUT)
        GPIO.setup(self.dio, GPIO.OUT)

    def start(self):
        GPIO.output(self.clk, 1)
        GPIO.output(self.dio, 1)
        GPIO.output(self.dio, 0)
        GPIO.output(self.clk, 0)

    def stop(self):
        GPIO.output(self.clk, 0)
        GPIO.output(self.dio, 0)
        GPIO.output(self.clk, 1)
        GPIO.output(self.dio, 1)

    def write_byte(self, data):
        for i in range(8):
            GPIO.output(self.clk, 0)
            GPIO.output(self.dio, (data >> i) & 1)
            time.sleep(0.00001)
            GPIO.output(self.clk, 1)
            time.sleep(0.00001)
        GPIO.output(self.clk, 0)
        GPIO.setup(self.dio, GPIO.IN)
        time.sleep(0.00001)
        GPIO.output(self.clk, 1)
        time.sleep(0.00001)
        GPIO.setup(self.dio, GPIO.OUT)

    def show(self, digits):
        SEGMENTS = [0x3F, 0x06, 0x5B, 0x4F, 0x66,
                    0x6D, 0x7D, 0x07, 0x7F, 0x6F]
        self.start()
        self.write_byte(0x40)
        self.stop()
        self.start()
        self.write_byte(0xC0)
        for d in digits:
            self.write_byte(SEGMENTS[d] if 0 <= d < 10 else 0)
        self.stop()
        self.start()
        self.write_byte(0x88 + self._brightness)
        self.stop()

    def brightness(self, val):
        self._brightness = val & 0x07


# ==============================
# STATE
# ==============================
GPIO.setmode(GPIO.BCM)
GPIO.setup([ENC_CLK, ENC_DT, IR_PIN], GPIO.IN, pull_up_down=GPIO.PUD_UP)

disp = TM1637(clk=DISP_CLK, dio=DISP_DIO)
disp.brightness(7)

channel = 1
last_clk = GPIO.input(ENC_CLK)

# ==============================
# HELPERS
# ==============================
def update_display(n):
    digits = [int(x) for x in str(n).rjust(4, "0")[-4:]]
    disp.show(digits)

def send_command(cmd, channel):
    payload = {
        "command": cmd,
        "channel": channel
    }
    try:
        r = requests.post(API_ENDPOINT, json=payload, timeout=2)
        if r.status_code == 200:
            print(f"✅ FS42 command sent: direct to channel {channel}")
        else:
            print(f"⚠ FS42 HTTP {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ FS42 HTTP error: {e}")


# ==============================
# THREADS
# ==============================
def rotary_thread():
    global channel, last_clk
    rotary_counter = 0  # Track rotary movements
    rotary_threshold = 10  # How many clicks before sending a command (adjustable)

    while True:
        clk_state = GPIO.input(ENC_CLK)
        dt_state = GPIO.input(ENC_DT)

        if clk_state != last_clk:
            # Increment or decrement rotary counter based on direction
            if dt_state != clk_state:
                rotary_counter += 1
            else:
                rotary_counter -= 1

            # Update the display when the counter hits the threshold
            if abs(rotary_counter) >= rotary_threshold:
                # Move through available channels
                index = (AVAILABLE_CHANNELS.index(channel) + (rotary_counter // rotary_threshold)) % len(AVAILABLE_CHANNELS)
                channel = AVAILABLE_CHANNELS[index]
                rotary_counter = 0  # Reset counter after moving

                print(f"🔁 Rotary → Channel {channel}")
                update_display(channel)
                send_command("direct", channel)

            last_clk = clk_state
        time.sleep(0.01)

def ir_thread():
    global channel
    print("📡 IR thread started (GPIO9)...")
    last_state = GPIO.input(IR_PIN)
    trigger_time = 0
    while True:
        state = GPIO.input(IR_PIN)
        if last_state == 1 and state == 0:
            trigger_time = time.time()
        elif last_state == 0 and state == 1:
            duration = time.time() - trigger_time
            if 0.002 < duration < 0.2:
                print(f"🛰 IR Burst Detected → Channel {channel}")
                send_command("direct", channel)
        last_state = state
        time.sleep(0.005)

# ==============================
# MAIN
# ==============================
def main():
    update_display(channel)
    Thread(target=rotary_thread, daemon=True).start()
    Thread(target=ir_thread, daemon=True).start()
    print(f"🚀 Controller started. Starting on channel {channel}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        disp.show([0, 0, 0, 0])

if __name__ == "__main__":
    main()
