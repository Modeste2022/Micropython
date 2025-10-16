from machine import I2C, Pin, ADC, PWM
import time
import math

# ===== CONFIGURATION MATÉRIEL =====
# Configuration I2C pour l'écran OLED - avec gestion d'erreur
try:
    i2c = I2C(1, scl=Pin(7), sda=Pin(6), freq=400000)  # Fréquence réduite pour stabilité
    print("I2C initialisé avec succès")
except Exception as e:
    print(f"Erreur I2C: {e}")
    i2c = None

# Utilisez l'adresse détectée 0x3E au lieu de 0x3C
OLED_ADDR = 0x3E  # Correction de l'adresse

# Capteurs et entrées
temp_sensor = ADC(Pin(26))  # GP26 pour lecture température
potentiometer = ADC(Pin(27))  # GP27 pour potentiomètre consigne

# Sorties
led = PWM(Pin(20))  # GP20 pour LED avec PWM
led.freq(1000)
buzzer = PWM(Pin(16))  # GP16 pour buzzer
buzzer.freq(1000)
buzzer.duty_u16(0)  # Buzzer éteint au départ

# ===== CLASSE OLED SIMPLIFIÉE =====
class GroveOLED:
    def __init__(self, i2c, addr=0x3E):  # Changement d'adresse par défaut
        self.i2c = i2c
        self.addr = addr
        self.init_display()
   
    def init_display(self):
        """Initialisation simplifiée de l'écran OLED"""
        try:
            # Séquence d'initialisation de base
            init_commands = [
                0xAE,  # Display OFF
                0x20, 0x00,  # Memory addressing mode = horizontal
                0x40,  # Display start line = 0
                0xA1,  # Segment remap = 127
                0xA8, 0x3F,  # Multiplex ratio = 64
                0xC8,  # COM output scan direction = remapped
                0xD3, 0x00,  # Display offset = 0
                0xDA, 0x12,  # COM pins hardware configuration
                0x81, 0xFF,  # Contrast control
                0xA4,  # Entire display ON
                0xA6,  # Normal display (not inverted)
                0xD5, 0x80,  # Display clock divide ratio/oscillator frequency
                0x8D, 0x14,  # Enable charge pump
                0xAF   # Display ON
            ]
            
            for cmd in init_commands:
                self.write_command(cmd)
                time.sleep_ms(10)
            print("Écran OLED initialisé avec succès")
            
        except Exception as e:
            print(f"Erreur initialisation OLED: {e}")
   
    def write_command(self, cmd):
        """Envoie une commande à l'écran"""
        try:
            self.i2c.writeto(self.addr, bytes([0x00, cmd]))
        except Exception as e:
            print(f"Erreur commande OLED: {e}")
   
    def write_data(self, data):
        """Envoie des données à l'écran"""
        try:
            self.i2c.writeto(self.addr, bytes([0x40, data]))
        except Exception as e:
            print(f"Erreur données OLED: {e}")
   
    def clear(self):
        """Efface l'écran"""
        self.write_command(0x01)  # Clear display
        time.sleep_ms(2)
   
    def set_cursor(self, row, col):
        """Positionne le curseur"""
        addr = 0x80 if row == 0 else 0xC0
        self.write_command(addr + col)
   
    def print(self, text, row=0, col=0):
        """Affiche du texte à la position spécifiée"""
        try:
            self.set_cursor(row, col)
            for char in text[:16]:  # Limite à 16 caractères
                self.write_data(ord(char))
        except Exception as e:
            print(f"Erreur affichage texte: {e}")

# ===== FONCTIONS DE CONVERSION =====
def read_temperature():
    """Lit la température simulée (0-3.3V -> 15-35°C)"""
    try:
        raw_value = temp_sensor.read_u16()
        temperature = 15 + (raw_value / 65535) * 20  # 15°C à 35°C
        return round(temperature, 1)
    except:
        return 20.0  # Valeur par défaut en cas d'erreur

def read_setpoint():
    """Lit la température de consigne depuis le potentiomètre (15-35°C)"""
    try:
        raw_value = potentiometer.read_u16()
        setpoint = 15 + (raw_value / 65535) * 20  # 15°C à 35°C
        return round(setpoint, 1)
    except:
        return 25.0  # Valeur par défaut

def control_led(duty, frequency=0.5):
    """Contrôle la LED avec PWM"""
    try:
        led.duty_u16(int(duty * 65535))
    except:
        pass

def alarm_buzzer(active):
    """Active ou désactive le buzzer"""
    try:
        if active:
            buzzer.duty_u16(32768)  # 50% duty cycle
            buzzer.freq(800)       # Fréquence 800Hz
        else:
            buzzer.duty_u16(0)
    except:
        pass

# ===== FONCTIONS D'AFFICHAGE =====
def update_display(oled, setpoint, ambient, alarm_active=False, alarm_blink=False):
    """Met à jour l'affichage OLED"""
    try:
        oled.clear()
        
        # Ligne 1: Température de consigne
        oled.print(f"Set:{setpoint}C", 0, 0)
        
        # Ligne 2: Température ambiante ou ALARM
        if alarm_active and alarm_blink:
            oled.print("*** ALARM ***", 1, 0)
        else:
            oled.print(f"Amb:{ambient}C", 1, 0)
    except Exception as e:
        print(f"Erreur mise à jour affichage: {e}")

# ===== PROGRAMME PRINCIPAL =====
def main():
    print("Initialisation du thermostat...")
    
    # Vérification I2C
    if i2c is None:
        print("ERREUR: I2C non initialisé")
        return
    
    try:
        # Scan des périphériques I2C
        devices = i2c.scan()
        print(f"Périphériques I2C trouvés: {[hex(d) for d in devices]}")
        
        if OLED_ADDR not in devices:
            print(f"ERREUR: Écran OLED non trouvé à l'adresse {hex(OLED_ADDR)}")
            print("Vérifiez les connexions SDA/SCL")
            return
        
        # Initialisation OLED
        oled = GroveOLED(i2c, OLED_ADDR)
        time.sleep(1)
        
        # Message de démarrage
        oled.clear()
        oled.print("Thermostat Pico", 0, 0)
        oled.print("Pret!", 1, 0)
        time.sleep(2)
        
        print("Thermostat démarré avec succès!")
        
    except Exception as e:
        print(f"ERREUR initialisation: {e}")
        return
    
    # Variables de contrôle
    last_blink_time = 0
    last_alarm_blink_time = 0
    alarm_blink_state = False
    led_state = False
    
    while True:
        try:
            current_time = time.ticks_ms()
            
            # Lecture des températures
            setpoint = read_setpoint()
            ambient = read_temperature()
            difference = ambient - setpoint
            
            # Contrôle d'alarme
            alarm_active = difference > 3
            warning_active = difference > 0
            
            # Contrôle LED
            if warning_active:
                # Clignotement basé sur le mode
                blink_interval = 250 if alarm_active else 500  # 2Hz ou 0.5Hz
                
                if current_time - last_blink_time >= blink_interval:
                    led_state = not led_state
                    last_blink_time = current_time
                
                # Dimmer progressif en mode alarme
                if alarm_active:
                    intensity = min(1.0, (difference - 3) / 5)
                    control_led(intensity if led_state else 0)
                else:
                    control_led(1.0 if led_state else 0)
            else:
                control_led(0)
                led_state = False
            
            # Contrôle buzzer
            alarm_buzzer(alarm_active)
            
            # Clignotement texte ALARM
            if alarm_active:
                if current_time - last_alarm_blink_time >= 500:
                    alarm_blink_state = not alarm_blink_state
                    last_alarm_blink_time = current_time
            else:
                alarm_blink_state = False
            
            # Mise à jour affichage
            update_display(oled, setpoint, ambient, alarm_active, alarm_blink_state)
            
            # Affichage console pour debug
            status = "NORMAL"
            if alarm_active:
                status = "ALARME"
            elif warning_active:
                status = "AVERTISSEMENT"
            
            print(f"Set:{setpoint}C Amb:{ambient}C Diff:{difference:.1f} {status}")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Erreur boucle principale: {e}")
            time.sleep(1)

# Démarrage du programme
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
        led.duty_u16(0)
        buzzer.duty_u16(0)
        try:
            oled.clear()
            oled.print("Systeme arrete", 0, 0)
        except:
            pass
    except Exception as e:
        print(f"Erreur critique: {e}")