from machine import Pin, PWM, ADC
import utime

# Buzzer sur GP16
buzzer = PWM(Pin(16))

# Potentiomètre sur GP28 (A2 = ADC2)
pot = ADC(2)

# Bouton poussoir sur GP18
button = Pin(18, Pin.IN, Pin.PULL_DOWN)

# LED sur GP20
led = Pin(20, Pin.OUT)

# Mélodie 1 : We Wish You a Merry Christmas (simplifiée)
melody1 = [
    392, 392, 440, 392, 523, 494,
    392, 392, 440, 392, 587, 523,
    392, 392, 784, 659, 523, 494, 440,
    698, 698, 659, 523, 587, 523
]
duration1 = [
    0.4, 0.4, 0.4, 0.4, 0.4, 0.6,
    0.4, 0.4, 0.4, 0.4, 0.4, 0.6,
    0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.6,
    0.6, 0.4, 0.4, 0.4, 0.4, 0.8
]

# Mélodie 2 : Ode à la Joie (inchangée)
melody2 = [
    330, 330, 349, 392, 392, 349, 330, 294,
    262, 262, 294, 330, 330, 294, 294,
    330, 330, 349, 392, 392, 349, 330, 294,
    262, 262, 294, 330, 294, 262, 262
]
duration2 = [
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.6,
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
    0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.6
]

# Liste des mélodies
melodies = [(melody1, duration1), (melody2, duration2)]
melody_index = 0

# Fonction anti-rebond
def wait_for_press():
    if button.value() == 1:
        utime.sleep(0.2)
        while button.value() == 1:
            pass
        utime.sleep(0.2)
        return True
    return False

while True:
    if wait_for_press():
        melody_index = (melody_index + 1) % len(melodies)

    melody, durations = melodies[melody_index]

    for i in range(len(melody)):
        pot_value = pot.read_u16()
        duty = int(pot_value)

        buzzer.freq(melody[i])
        buzzer.duty_u16(duty)
        led.value(1)
        utime.sleep(durations[i])
        buzzer.duty_u16(0)
        led.value(0)
        utime.sleep(0.05)

        if wait_for_press():
            melody_index = (melody_index + 1) % len(melodies)
            break