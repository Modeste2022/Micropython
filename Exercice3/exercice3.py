from machine import Pin, I2C, ADC, PWM
import time
import math
import dht

# ===== CONFIGURATION DES BROCHES =====
dht_sensor = dht.DHT11(Pin(16))
i2c1 = I2C(1, scl=Pin(7), sda=Pin(6), freq=100000)
potentiometer = ADC(Pin(26)) #ADC(0)

led = PWM(Pin(20))
led.freq(1000)
led.duty_u16(0)

buzzer = PWM(Pin(18))
buzzer.freq(2000)
buzzer.duty_u16(0)

# ===== CLASSE POUR L'ÉCRAN GROVE LCD 16x2 =====
class GroveLCD16x2:
    def __init__(self, i2c, addr=0x3E):
        self.i2c = i2c
        self.addr = addr
        self.init_display()
    
    def init_display(self):
        try:
            commands = [0x38, 0x39, 0x14, 0x78, 0x5E, 0x6D, 0x0C, 0x01, 0x06]
            for cmd in commands:
                self.write_command(cmd)
                time.sleep_ms(5)
            print("✅ LCD initialisé")
        except Exception as e:
            print(f"❌ Erreur LCD: {e}")
    
    def write_command(self, cmd):
        try:
            self.i2c.writeto(self.addr, bytes([0x80, cmd]))
        except:
            pass
    
    def write_data(self, data):
        try:
            self.i2c.writeto(self.addr, bytes([0x40, data]))
        except:
            pass
    
    def clear(self):
        self.write_command(0x01)
        time.sleep_ms(2)
    
    def set_cursor(self, row, col):
        addr = 0x80 if row == 0 else 0xC0
        self.write_command(addr + col)
    
    def print(self, text, row=0, col=0):
        try:
            self.set_cursor(row, col)
            for char in text[:16]:
                self.write_data(ord(char))
        except:
            pass
    
    def clear_line(self, row):
        self.print(" " * 16, row, 0)

# ===== FONCTIONS UTILITAIRES =====
def read_setpoint():
    try:
        sum_value = 0
        for _ in range(5):  # Réduit pour plus de réactivité
            sum_value += potentiometer.read_u16()
            time.sleep_ms(1)
        adc_value = sum_value // 5
        temp_setpoint = 15 + (adc_value / 65535) * 20
        return max(15, min(35, round(temp_setpoint, 1)))
    except:
        return 25.0

def read_dht11():
    """Lecture du DHT11 avec timeout court"""
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        
        # Vérification des valeurs plausibles
        if temperature is None or humidity is None:
            return None, None
        if temperature < -40 or temperature > 80:
            return None, None
        if humidity < 0 or humidity > 100:
            return None, None
            
        return temperature, humidity
    except Exception as e:
        return None, None

def activate_buzzer():
    buzzer.duty_u16(20000)

def deactivate_buzzer():
    buzzer.duty_u16(0)

def led_breathing(phase):
    brightness = int((math.sin(phase) + 1) * 15000)
    led.duty_u16(brightness)

# ===== INITIALISATION =====
print("=== THERMOSTAT EXERCICE 3 ===")
print("Initialisation...")
print("Capteur: DHT11 sur GP16")

# Initialisation écran LCD
lcd = GroveLCD16x2(i2c1)

# Message de démarrage
lcd.clear()
lcd.print("Thermostat Pico", 0, 0)
lcd.print("Connexion...", 1, 0)

# Test initial du DHT11 (1 seconde maximum)
print("Test du DHT11 (1s)...")
sensor_connected = False
start_time = time.ticks_ms()

while time.ticks_diff(time.ticks_ms(), start_time) < 1000:  # 1 seconde max
    temp, hum = read_dht11()
    if temp is not None:
        sensor_connected = True
        print(f"✅ DHT11 OK: {temp}°C, {hum}%")
        break
    time.sleep(0.1)  # Essais rapides

if not sensor_connected:
    print("❌ DHT11 non détecté après 1s")

time.sleep(1)

print("=== SYSTEME DE CONTROLE DE TEMPERATURE ===")

# Variables de contrôle
breathing_phase = 0
last_led_update = time.ticks_ms()
last_blink_toggle = time.ticks_ms()
last_sensor_read = time.ticks_ms()
last_display_update = time.ticks_ms()

sensor_read_interval = 1000  # 1 seconde entre les lectures
display_update_interval = 500  # Affichage plus rapide

# ===== BOUCLE PRINCIPALE =====
temp_setpoint = read_setpoint()
temp_measured = None
humidity = None
led_state = False
alarm_blink = False
sensor_error_count = 0

print("Démarrage - Mesures toutes les 1s")

while True:
    try:
        current_time = time.ticks_ms()
        
        # Lecture du DHT11 toutes les 1 secondes
        if time.ticks_diff(current_time, last_sensor_read) >= sensor_read_interval:
            temp_setpoint = read_setpoint()
            
            # LECTURE RAPIDE DU DHT11
            temp_read, hum_read = read_dht11()
            
            if temp_read is not None:
                temp_measured = temp_read
                humidity = hum_read
                sensor_error_count = 0
                if not sensor_connected:
                    sensor_connected = True
                    print("✅ DHT11 connecté")
            else:
                sensor_error_count += 1
                if sensor_connected and sensor_error_count >= 2:  # Seulement 2 erreurs
                    sensor_connected = False
                    temp_measured = None
                    print("❌ DHT11 DÉCONNECTÉ")
            
            last_sensor_read = current_time

        # === GESTION DES ÉTATS ===
        if not sensor_connected or temp_measured is None:
            # === MODE CAPTEUR DÉCONNECTÉ ===
            deactivate_buzzer()
            led.duty_u16(0)
            
            # Affichage erreur
            if time.ticks_diff(current_time, last_display_update) >= display_update_interval:
                lcd.clear_line(0)
                lcd.print("Set: ---.-C", 0, 0)
                lcd.clear_line(1)
                lcd.print("CAPTEUR ABSENT", 1, 0)
                last_display_update = current_time
            
            print("CAPTEUR ABSENT", end='\r')  # Sur place
            
        else:
            # === CAPTEUR CONNECTÉ ===
            temp_diff = temp_measured - temp_setpoint

            if temp_diff > 3:
                # === MODE ALARME ===
                activate_buzzer()
                
                # LED: Clignotement rapide (2Hz)
                if time.ticks_diff(current_time, last_led_update) >= 250:
                    led_state = not led_state
                    led.duty_u16(30000 if led_state else 0)
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
                    breathing_phase += 0.1
                    led_breathing(breathing_phase)
                    last_led_update = current_time
                
            else:
                # === MODE NORMAL ===
                deactivate_buzzer()
                led.duty_u16(0)
                led_state = False
                alarm_blink = False

            # === AFFICHAGE LCD ===
            if time.ticks_diff(current_time, last_display_update) >= display_update_interval:
                lcd.clear_line(0)
                lcd.print(f"Set: {temp_setpoint:.1f}C", 0, 0)
                
                lcd.clear_line(1)
                if temp_diff > 3 and alarm_blink:
                    lcd.print("*** ALARM ***", 1, 0)
                else:
                    lcd.print(f"Ambient: {temp_measured:.1f}C", 1, 0)
                
                last_display_update = current_time

            # Affichage console
            status = "ALARME" if temp_diff > 3 else "WARNING" if temp_diff > 0 else "NORMAL"
            print(f"Set:{temp_setpoint:4.1f}C Amb:{temp_measured:4.1f}C Diff:{temp_diff:+.1f}C {status:8}")

        time.sleep_ms(50)  # Boucle plus réactive

    except Exception as e:
        print(f"❌ Erreur: {e}")
        lcd.clear()
        lcd.print("ERREUR SYSTEME", 0, 0)
        deactivate_buzzer()
        led.duty_u16(0)
        time.sleep(1)

# Arrêt propre
def stop_system():
    deactivate_buzzer()
    led.duty_u16(0)
    lcd.clear()
    lcd.print("Systeme arrete", 0, 0)
    print("Système arrêté")

try:
    pass
except KeyboardInterrupt:
    stop_system()