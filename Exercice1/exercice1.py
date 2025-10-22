import machine
import utime

# Définition des broches
LED = machine.Pin(16, machine.Pin.OUT)
BUTTON = machine.Pin(18, machine.Pin.IN)

# Variable pour compter les pressions
press_count = 0

# Anti-rebond et détection d'appui
def wait_for_press():
    while BUTTON.value() == 0:
        pass
    utime.sleep(0.2)  # anti-rebond
    while BUTTON.value() == 1:
        pass
    utime.sleep(0.2)

while True:
    wait_for_press()
    press_count += 1
    if press_count > 3:
        press_count = 1  # recommencer le cycle

    while True:
        if BUTTON.value() == 1:
            break  # sortir pour gérer la prochaine pression

        if press_count == 1:
            LED.toggle()
            utime.sleep(1)  # 0.5 Hz (1s ON, 1s OFF)
        elif press_count == 2:
            LED.toggle()
            utime.sleep(0.3)  # plus rapide
        elif press_count == 3:
            LED.value(0)  # éteindre la LED
            utime.sleep(0.2)