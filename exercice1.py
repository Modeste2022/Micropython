import machine

# Définition des broches
LED = machine.Pin(16, machine.Pin.OUT)
BUTTON = machine.Pin(18, machine.Pin.IN)

# Variable pour compter les pressions
press_count = 0

# Anti-rebond et détection d'appui
def wait_for_press():
    while BUTTON.value() == 0:
        pass
    while BUTTON.value() == 1:
        pass

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

        elif press_count == 2:
            LED.toggle()

        elif press_count == 3:
            LED.value(0)  # éteindre la LED
