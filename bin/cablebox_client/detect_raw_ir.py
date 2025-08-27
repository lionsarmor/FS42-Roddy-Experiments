import RPi.GPIO as GPIO
import time

IR_PIN = 9  # test again with GPIO9

GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN)

print("🔍 Watching GPIO9 for IR activity...")
print("Press any button on your IR remote.\n")

try:
    while True:
        if GPIO.input(IR_PIN) == GPIO.LOW:
            print(f"📡 IR LOW detected at {time.time()}")
            time.sleep(0.05)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("\n🛑 Exiting IR watcher.")
