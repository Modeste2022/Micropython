"""
Exercice 5 : Construction d'une horloge avec Raspberry Pi Pico W et servo moteur
Raspberry Pi Pico W 2022
Servo moteur analogique 4.8-6.0V sur GP20
Bouton poussoir sur GP18
Bonus : Changement de fuseau horaire et mode 24h
"""

from machine import Pin, PWM, RTC
import network
import ntptime
import time

# ==================== CONFIGURATION ====================

# Configuration WiFi
WIFI_SSID = "Orange-dm8dW"
WIFI_PASSWORD = "4VBPErrdJSkFMW7"

# Configuration matérielle
SERVO_PIN = 20
BUTTON_PIN = 18

# Fuseaux horaires disponibles
TIMEZONES = [
    ("UTC", 0),
    ("UTC+1 (Bruxelles hiver)", 1),
    ("UTC+2 (Bruxelles été)", 2),
    ("UTC-5 (New York)", -5),
    ("UTC+9 (Tokyo)", 9),
    ("UTC-8 (Los Angeles)", -8),
]

# Variables globales
current_timezone_index = 1  # Par défaut UTC+1 (Bruxelles hiver)
is_24h_mode = False  # Mode 12h par défaut

# ==================== FONCTIONS WIFI ====================

def connect_wifi():
    """Se connecte au réseau WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print(f"✓ Déjà connecté à {WIFI_SSID}")
        print(f"Adresse IP : {wlan.ifconfig()[0]}")
        return wlan
    
    print(f"Connexion au Wi-Fi '{WIFI_SSID}'...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5
        print(".", end="")
    
    print()
    
    if wlan.isconnected():
        print(f"✓ Connecté à {WIFI_SSID}")
        print(f"Adresse IP : {wlan.ifconfig()[0]}")
        return wlan
    else:
        print("✗ Échec de connexion WiFi")
        return None

def sync_time():
    """Synchronise l'heure avec un serveur NTP"""
    try:
        print("Synchronisation de l'heure via NTP...")
        ntptime.settime()
        print("✓ Heure synchronisée !")
        return True
    except Exception as e:
        print(f" Erreur de synchronisation NTP : {e}")
        return False

# ==================== CLASSE SERVO ====================

class Servo:
    """
    Classe pour contrôler un servo moteur analogique 4.8-6.0V
    Compatible avec la plupart des servos standards
    """
    
    def __init__(self, pin):
        self.servo = PWM(Pin(pin))
        self.servo.freq(50)  # 50Hz (période de 20ms)
        self.current_angle = 90
        
    def set_angle(self, angle):
        """Définit l'angle du servo (0° à 180°)"""
        angle = max(0, min(180, angle))
        
        # Conversion angle -> duty cycle
        duty_min = 1640   # 0° (pulse 0.5ms)
        duty_max = 8190   # 180° (pulse 2.5ms)
        duty = int(duty_min + (angle / 180) * (duty_max - duty_min))
        
        self.servo.duty_u16(duty)
        self.current_angle = angle
    
    def smooth_move(self, target_angle, steps=15, delay=0.03):
        """Déplace le servo progressivement vers l'angle cible"""
        current = self.current_angle
        step_size = (target_angle - current) / steps
        
        for i in range(steps):
            current += step_size
            self.set_angle(current)
            time.sleep(delay)
        
        self.set_angle(target_angle)
    
    def off(self):
        """Désactive le PWM du servo"""
        self.servo.deinit()

# ==================== CLASSE BOUTON ====================

class Button:
    """Classe pour gérer le bouton avec détection de simple et double clic"""
    
    def __init__(self, pin):
        self.button = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.last_state = 1  # 1 = non pressé (pull-up)
        self.last_press_time = 0
        self.waiting_for_double = False
        self.double_click_timeout = 0.4  # 400ms pour double clic
        
    def is_pressed(self):
        """Vérifie si le bouton est actuellement pressé"""
        return self.button.value() == 0  # 0 = pressé (pull-up)
    
    def check_click(self):
        """
        Vérifie de manière non-bloquante s'il y a eu un clic
        Retourne : 'single', 'double', ou None
        """
        current_state = self.button.value()
        current_time = time.time()
        
        # Détection du front descendant (appui)
        if self.last_state == 1 and current_state == 0:
            # Anti-rebond
            time.sleep(0.02)
            if self.button.value() == 0:  # Confirmer que c'est bien un appui
                if self.waiting_for_double and (current_time - self.last_press_time) < self.double_click_timeout:
                    # Double clic détecté !
                    self.waiting_for_double = False
                    self.last_state = current_state
                    return 'double'
                else:
                    # Premier clic, on attend pour voir s'il y a un second
                    self.last_press_time = current_time
                    self.waiting_for_double = True
        
        # Si on attend un double clic et que le timeout est dépassé
        if self.waiting_for_double and (current_time - self.last_press_time) > self.double_click_timeout:
            self.waiting_for_double = False
            self.last_state = current_state
            return 'single'
        
        self.last_state = current_state
        return None

# ==================== FONCTIONS HORLOGE ====================

def get_local_time(timezone_offset):
    """Récupère l'heure locale avec le fuseau horaire"""
    rtc = RTC()
    year, month, day, weekday, hour, minute, second, subsecond = rtc.datetime()
    
    # Appliquer le fuseau horaire
    hour = (hour + timezone_offset) % 24
    
    return hour, minute, second

def calculate_hour_angle_12h(hour, minute):
    """
    Calcule l'angle pour le mode 12 heures
    12h = 0°, 3h = 45°, 6h = 90°, 9h = 135°
    """
    hour_12 = hour % 12
    angle = (hour_12 * 15) + (minute * 0.25)
    return angle

def calculate_hour_angle_24h(hour, minute):
    """
    Calcule l'angle pour le mode 24 heures
    0h (minuit) = 0°, 12h (midi) = 90°, 24h (minuit) = 180°
    """
    angle = (hour * 7.5) + (minute * 0.125)
    return angle

def display_status(hour, minute, second, angle, mode, timezone_name):
    """Affiche l'état actuel de l'horloge"""
    mode_str = "24H" if mode else "12H"
    print(f" {hour:02d}:{minute:02d}:{second:02d} [{mode_str}] | {timezone_name} | Angle: {angle:5.1f}°")

# ==================== FONCTION PRINCIPALE ====================

def main():
    """Fonction principale de l'horloge"""
    global current_timezone_index, is_24h_mode
    
    print("=" * 60)
    print("HORLOGE AVEC SERVO MOTEUR + BOUTON POUSSOIR")
    print("Raspberry Pi Pico W 2022")
    print("=" * 60)
    print("Servo sur GP20 | Bouton sur GP18")
    print()
    print("COMMANDES :")
    print("• 1 clic  → Changer de fuseau horaire")
    print("• 2 clics → Basculer entre mode 12h et 24h")
    print("=" * 60 + "\n")
    
    # Connexion WiFi
    wlan = connect_wifi()
    if not wlan:
        print("Impossible de continuer sans WiFi")
        return
    
    # Synchronisation de l'heure
    if not sync_time():
        print("Impossible de synchroniser l'heure")
        return
    
    print()
    
    # Initialisation du matériel
    print(f"Initialisation du servo sur GP{SERVO_PIN}...")
    servo = Servo(SERVO_PIN)
    
    print(f"Initialisation du bouton sur GP{BUTTON_PIN}...")
    button = Button(BUTTON_PIN)
    
    # Test du servo
    print("\nTest du servo : 0° → 90° → 180° → 90°")
    servo.set_angle(0)
    time.sleep(1)
    servo.smooth_move(90)
    time.sleep(0.5)
    servo.smooth_move(180)
    time.sleep(0.5)
    servo.smooth_move(90)
    time.sleep(0.5)
    print("✓ Servo OK\n")
    
    print("=" * 60)
    print("DÉMARRAGE DE L'HORLOGE")
    print("=" * 60)
    
    # Afficher le fuseau horaire initial
    tz_name, tz_offset = TIMEZONES[current_timezone_index]
    mode_str = "24 heures" if is_24h_mode else "12 heures"
    print(f"Mode : {mode_str}")
    print(f"Fuseau horaire : {tz_name}")
    print("=" * 60 + "\n")
    
    update_counter = 0
    last_update = time.time()
    
    try:
        while True:
            # Vérifier les clics du bouton (non-bloquant)
            click = button.check_click()
            
            if click == 'single':
                # Changer de fuseau horaire
                current_timezone_index = (current_timezone_index + 1) % len(TIMEZONES)
                tz_name, tz_offset = TIMEZONES[current_timezone_index]
                print(f"\n{'='*60}")
                print(f" CHANGEMENT DE FUSEAU HORAIRE → {tz_name}")
                print(f"{'='*60}\n")
                # Forcer une mise à jour immédiate
                last_update = 0
                
            elif click == 'double':
                # Basculer entre mode 12h et 24h
                is_24h_mode = not is_24h_mode
                mode_str = "24 heures" if is_24h_mode else "12 heures"
                print(f"\n{'='*60}")
                print(f" CHANGEMENT DE MODE → {mode_str}")
                if is_24h_mode:
                    print("   0h=0° | 6h=45° | 12h=90° | 18h=135° | 24h=180°")
                else:
                    print("   12h=0° | 3h=45° | 6h=90° | 9h=135°")
                print(f"{'='*60}\n")
                # Forcer une mise à jour immédiate
                last_update = 0
            
            # Mettre à jour l'horloge toutes les secondes
            current_time = time.time()
            if current_time - last_update >= 1.0:
                last_update = current_time
                
                # Récupérer l'heure avec le fuseau horaire actuel
                tz_name, tz_offset = TIMEZONES[current_timezone_index]
                hour, minute, second = get_local_time(tz_offset)
                
                # Calculer l'angle selon le mode
                if is_24h_mode:
                    angle = calculate_hour_angle_24h(hour, minute)
                else:
                    angle = calculate_hour_angle_12h(hour, minute)
                
                # Positionner le servo
                servo.set_angle(angle)
                
                # Afficher l'état
                mode = is_24h_mode
                display_status(hour, minute, second, angle, mode, tz_name)
                
                # Resynchroniser l'heure toutes les heures
                update_counter += 1
                if update_counter >= 3600:  # 1 heure
                    print("\n--- Resynchronisation de l'heure ---")
                    sync_time()
                    update_counter = 0
                    print()
            
            time.sleep(0.01)  # Petite pause pour éviter surcharge CPU
            
    except KeyboardInterrupt:
        print("\n\n Arrêt de l'horloge")
        servo.smooth_move(0)
        time.sleep(0.5)
        servo.off()
        print("Servo désactivé - Programme terminé")

# ==================== POINT D'ENTRÉE ====================

if __name__ == "__main__":
    main()