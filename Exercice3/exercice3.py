from machine import Pin, I2C, ADC, PWM
import time
import math

# ===== CONFIGURATION DES BROCHES =====
# Deux bus I2C séparés
i2c0 = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)  # DHT20 (capteur température/humidité) sur I2C0
i2c1 = I2C(1, scl=Pin(7), sda=Pin(6), freq=100000)  # Écran LCD sur I2C1
potentiometer = ADC(Pin(26)) #ADC(0)

# LED avec PWM pour dimmer
led = PWM(Pin(20))
led.freq(1000)
led.duty_u16(0)

# Buzzer
buzzer = PWM(Pin(18))
buzzer.freq(2000)
buzzer.duty_u16(0)

# ===== CAPTEUR DHT20 =====
class DHT20Simulator:
    """Simulateur de capteur DHT20 en attendant le vrai capteur"""
    def __init__(self):
        self.temperature = 22.0
        self.humidity = 50.0
        
    @property
    def measurements(self):
        # Simulation d'une température autour de 22°C ±2°C
        import random
        self.temperature = 22.0 + (random.random() - 0.5) * 4
        self.humidity = 45.0 + (random.random() - 0.5) * 10
        
        return {
            't': round(self.temperature, 1),
            'rh': round(self.humidity, 1),
            'crc_ok': True
        }

# ===== CLASSE POUR L'ÉCRAN GROVE LCD 16x2 =====
class GroveLCD16x2:
    def __init__(self, i2c, addr=0x3E):
        self.i2c = i2c
        self.addr = addr
        self.init_display()
    
    def init_display(self):
        """Initialisation de l'écran LCD Grove 16x2"""
        try:
            # Séquence d'initialisation pour LCD
            commands = [
                0x38,  # Function set: 8-bit, 2 lines, 5x8 dots
                0x39,  # Function set: 8-bit, 2 lines, 5x8 dots
                0x14,  # Internal OSC frequency
                0x78,  # Contrast set
                0x5E,  # Power/ICON control/Contrast set
                0x6D,  # Follower control
                0x0C,  # Display ON, cursor OFF, blink OFF
                0x01,  # Clear display
                0x06,  # Entry mode set
            ]
            for cmd in commands:
                self.write_command(cmd)
                time.sleep_ms(5)
            print("LCD initialisé avec succès")
        except Exception as e:
            print(f"Erreur init LCD: {e}")
    
    def write_command(self, cmd):
        """Écrit une commande sur le LCD"""
        try:
            self.i2c.writeto(self.addr, bytes([0x80, cmd]))
        except Exception as e:
            print(f"Erreur commande LCD: {e}")
    
    def write_data(self, data):
        """Écrit des données sur le LCD"""
        try:
            self.i2c.writeto(self.addr, bytes([0x40, data]))
        except Exception as e:
            print(f"Erreur données LCD: {e}")
    
    def clear(self):
        """Efface l'écran"""
        self.write_command(0x01)
        time.sleep_ms(2)
    
    def set_cursor(self, row, col):
        """Positionne le curseur"""
        addr = 0x80 if row == 0 else 0xC0
        self.write_command(addr + col)
    
    def print(self, text, row=0, col=0):
        """Affiche du texte à la position spécifiée"""
        try:
            self.set_cursor(row, col)
            for char in text[:16]:  # Limité à 16 caractères par ligne
                self.write_data(ord(char))
        except Exception as e:
            print(f"Erreur affichage: {e}")
    
    def clear_line(self, row):
        """Efface une ligne spécifique"""
        self.print(" " * 16, row, 0)

# ===== FONCTIONS UTILITAIRES =====
def read_setpoint():
    """Lecture du potentiomètre avec moyennage pour réduire le bruit"""
    try:
        sum_value = 0
        for _ in range(10):
            sum_value += potentiometer.read_u16()
            time.sleep_ms(1)
        
        adc_value = sum_value // 10
        temp_setpoint = 15 + (adc_value / 65535) * 20
        return max(15, min(35, round(temp_setpoint, 1)))
    except:
        return 25.0  # Valeur par défaut

def activate_buzzer():
    try:
        buzzer.duty_u16(15000)  # Volume réduit
    except:
        pass

def deactivate_buzzer():
    try:
        buzzer.duty_u16(0)
    except:
        pass

def led_breathing(phase):
    """Effet de respiration (dimmer progressif) pour la LED"""
    try:
        brightness = int((math.sin(phase) + 1) * 15000)  # Intensité réduite
        led.duty_u16(brightness)
    except:
        pass

# ===== INITIALISATION =====
print("Initialisation du système de thermostat...")
print("Scan des périphériques I2C...")

# Scan I2C0 (DHT20)
print("I2C0 (DHT20):")
devices_i2c0 = i2c0.scan()
print(f"Périphériques trouvés: {[hex(d) for d in devices_i2c0]}")

# Scan I2C1 (LCD)
print("I2C1 (LCD):")
devices_i2c1 = i2c1.scan()
print(f"Périphériques trouvés: {[hex(d) for d in devices_i2c1]}")

# Initialisation écran LCD
lcd = None
if 0x3E in devices_i2c1:
    lcd = GroveLCD16x2(i2c1)
    print("Écran LCD Grove 16x2 initialisé")
else:
    print("Écran LCD non détecté à l'adresse 0x3E")

# Initialisation capteur DHT20
sensor = None
if 0x38 in devices_i2c0:
    try:
        from dht20 import DHT20
        sensor = DHT20(0x38, i2c0)
        print("DHT20 réel initialisé avec succès")
    except Exception as e:
        print(f"Erreur initialisation DHT20: {e}")
        sensor = DHT20Simulator()
        print("DHT20 simulé activé")
else:
    sensor = DHT20Simulator()
    print("DHT20 non détecté, simulateur activé")

# Message de démarrage
if lcd:
    lcd.clear()
    lcd.print("Thermostat Pico", 0, 0)
    lcd.print("Systeme OK", 1, 0)
    time.sleep(2)

print("=== SYSTEME DE CONTROLE DE TEMPERATURE ===")
print("Exercice 3 - Thermostat multi-états")

# Variables de contrôle
breathing_phase = 0
last_led_update = time.ticks_ms()
last_blink_toggle = time.ticks_ms()
last_sensor_read = time.ticks_ms()
last_display_update = time.ticks_ms()

sensor_read_interval = 2000  # Lecture capteur toutes les 2 secondes
display_update_interval = 500  # Mise à jour écran toutes les 500ms

# ===== BOUCLE PRINCIPALE =====
# INITIALISATION DES VARIABLES IMPORTANTES
temp_setpoint = read_setpoint()  # Lecture initiale de la consigne
temp_measured = 22.0
humidity = 50.0
led_state = False
alarm_blink = False

print("Démarrage de la boucle principale...")

while True:
    try:
        current_time = time.ticks_ms()
        
        # Lecture du capteur (toutes les 2 secondes)
        if time.ticks_diff(current_time, last_sensor_read) >= sensor_read_interval:
            temp_setpoint = read_setpoint()  # Mise à jour de la consigne
            
            try:
                data = sensor.measurements
                temp_measured = data['t']
                humidity = data['rh']
                print(f"Lecture capteur: {temp_measured:.1f}°C, {humidity:.1f}%")
            except Exception as e:
                print(f"Erreur lecture capteur: {e}")
                # Garder les dernières valeurs valides
            
            last_sensor_read = current_time

        # Calculer la différence
        temp_diff = temp_measured - temp_setpoint

        # === GESTION DES ÉTATS ===
        if temp_diff > 3:
            # === MODE ALARME ===
            activate_buzzer()
            
            # LED: Clignotement rapide (2Hz)
            if time.ticks_diff(current_time, last_led_update) >= 250:
                led_state = not led_state
                led.duty_u16(25000 if led_state else 0)
                last_led_update = current_time
            
            # Clignotement ALARM
            if time.ticks_diff(current_time, last_blink_toggle) >= 500:
                alarm_blink = not alarm_blink
                last_blink_toggle = current_time
            
        elif temp_diff > 0:
            # === MODE AVERTISSEMENT ===
            deactivate_buzzer()
            
            # LED: Effet breathing à 0.5Hz
            if time.ticks_diff(current_time, last_led_update) >= 50:
                breathing_phase += 0.08  # Plus lent pour 0.5Hz
                led_breathing(breathing_phase)
                last_led_update = current_time
            
        else:
            # === MODE NORMAL ===
            deactivate_buzzer()
            led.duty_u16(0)
            led_state = False
            alarm_blink = False

        # === AFFICHAGE LCD ===
        if lcd and time.ticks_diff(current_time, last_display_update) >= display_update_interval:
            # Ligne 1: Consigne
            lcd.clear_line(0)
            lcd.print(f"Set: {temp_setpoint:.1f}C", 0, 0)
            
            # Ligne 2: Température ambiante ou ALARM
            lcd.clear_line(1)
            if temp_diff > 3 and alarm_blink:
                lcd.print("*** ALARM ***", 1, 0)
            else:
                lcd.print(f"Ambient: {temp_measured:.1f}C", 1, 0)
            
            last_display_update = current_time

        # Affichage console pour debug
        status = "ALARME" if temp_diff > 3 else "WARNING" if temp_diff > 0 else "NORMAL"
        print(f"Set:{temp_setpoint:4.1f}C Amb:{temp_measured:4.1f}C Diff:{temp_diff:+.1f}C {status:8}")

        time.sleep_ms(100)

    except Exception as e:
        print(f"Erreur système: {e}")
        if lcd:
            lcd.clear()
            lcd.print("ERREUR SYSTEME", 0, 0)
        deactivate_buzzer()
        led.duty_u16(0)
        time.sleep(2)

# Arrêt propre
def stop_system():
    deactivate_buzzer()
    led.duty_u16(0)
    if lcd:
        lcd.clear()
        lcd.print("Systeme arrete", 0, 0)
    print("Système arrêté")

try:
    pass
except KeyboardInterrupt:
    stop_system()