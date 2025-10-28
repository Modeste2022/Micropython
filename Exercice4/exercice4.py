"""
Exercice 4 : Contrôle d'une LED RGB en fonction du rythme de la musique
Raspberry Pi Pico W 2022
LED RGB WS2813 Mini v1.0 sur GP20
Sound Sensor v1.6 sur ADC0
"""

from machine import Pin, ADC
from neopixel import NeoPixel
import time
import random

# ==================== CONFIGURATION ====================

# LED RGB WS2813 sur GP20
led_pin = Pin(20, Pin.OUT)
np = NeoPixel(led_pin, 1)  # 1 LED

# Capteur de son sur ADC0 (GP26)
sound_sensor = ADC(26)

# Paramètres de détection des battements
THRESHOLD = 25000  # Seuil de détection (à ajuster selon votre environnement)
MIN_BEAT_INTERVAL = 1.0  # Intervalle minimum entre deux battements (1 seconde)
SAMPLE_WINDOW = 50  # Nombre d'échantillons pour la moyenne mobile
BPM_WINDOW = 60  # Fenêtre de calcul BPM (en secondes)
NOISE_THRESHOLD = 500  # Variation minimale pour considérer que le micro est connecté

# Variables globales
last_beat_time = 0
beat_times = []  # Stockage des temps des battements
bpm_history = []  # Historique des BPM par minute
minute_start = time.time()
sound_samples = []
microphone_connected = True  # État de connexion du microphone
last_check_time = 0  # Dernier moment de vérification du micro

# ==================== FONCTIONS ====================

def read_sound_level():
    """Lit le niveau sonore du capteur"""
    return sound_sensor.read_u16()

def is_microphone_connected():
    """Vérifie si le microphone est connecté en analysant la variation du signal"""
    samples = []
    for _ in range(20):
        samples.append(read_sound_level())
        time.sleep(0.01)
    
    # Calculer la variation (écart-type simplifié)
    avg = sum(samples) / len(samples)
    variance = sum((x - avg) ** 2 for x in samples) / len(samples)
    variation = variance ** 0.5
    
    return variation > NOISE_THRESHOLD

def check_microphone_status():
    """Vérifie périodiquement si le microphone est toujours connecté"""
    global microphone_connected, last_check_time
    
    current_time = time.time()
    
    # Vérifier toutes les 5 secondes
    if current_time - last_check_time >= 5:
        last_check_time = current_time
        was_connected = microphone_connected
        microphone_connected = is_microphone_connected()
        
        # Afficher un message si l'état a changé
        if was_connected and not microphone_connected:
            print("\n" + "!" * 50)
            print("⚠️  MICROPHONE DÉBRANCHÉ!")
            print("Veuillez rebrancher le microphone.")
            print("!" * 50 + "\n")
            # Éteindre la LED
            np[0] = (0, 0, 0)
            np.write()
        elif not was_connected and microphone_connected:
            print("\n" + "=" * 50)
            print("✓ MICROPHONE RECONNECTÉ!")
            print("Reprise de la détection...")
            print("=" * 50 + "\n")

def detect_beat(current_level, avg_level):
    """Détecte un battement basé sur un pic sonore"""
    global last_beat_time
    
    current_time = time.time()
    
    # Vérifier si le niveau dépasse le seuil et respecte l'intervalle minimum
    if (current_level > avg_level + THRESHOLD and 
        current_time - last_beat_time > MIN_BEAT_INTERVAL):
        last_beat_time = current_time
        return True
    return False

def change_led_color():
    """Change la couleur de la LED de manière aléatoire"""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    np[0] = (r, g, b)
    np.write()

def calculate_bpm():
    """Calcule le BPM moyen basé sur les battements récents"""
    if len(beat_times) < 2:
        return 0
    
    # Garder seulement les battements des dernières 10 secondes
    current_time = time.time()
    recent_beats = [t for t in beat_times if current_time - t < 10]
    
    if len(recent_beats) < 2:
        return 0
    
    # Calculer les intervalles entre battements
    intervals = []
    for i in range(1, len(recent_beats)):
        intervals.append(recent_beats[i] - recent_beats[i-1])
    
    # Calculer le BPM moyen
    avg_interval = sum(intervals) / len(intervals)
    bpm = 60 / avg_interval if avg_interval > 0 else 0
    
    return bpm

def save_bpm_to_file(bpm):
    """Sauvegarde le BPM dans un fichier texte"""
    try:
        with open('bpm_log.txt', 'a') as f:
            timestamp = time.time()
            f.write(f"{timestamp},{bpm:.2f}\n")
        print(f"BPM sauvegardé: {bpm:.2f}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")

def calibrate_sensor():
    """Calibration initiale du capteur de son"""
    print("Calibration du capteur (5 secondes)...")
    samples = []
    start = time.time()
    
    while time.time() - start < 5:
        samples.append(read_sound_level())
        time.sleep(0.01)
    
    avg = sum(samples) / len(samples)
    max_val = max(samples)
    min_val = min(samples)
    
    print(f"Niveau moyen: {avg:.0f}")
    print(f"Min: {min_val}, Max: {max_val}")
    print(f"Recommandation: THRESHOLD = {int((max_val - avg) * 0.7)}")
    print()

# ==================== FONCTION PRINCIPALE ====================

def main():
    """Fonction principale"""
    global minute_start, sound_samples, beat_times, bpm_history, microphone_connected, last_check_time
    
    print("=" * 50)
    print("Contrôle LED RGB au rythme de la musique")
    print("=" * 50)
    print(f"LED RGB WS2813 sur GP20")
    print(f"Capteur son sur ADC0 (GP26)")
    print(f"Seuil de détection: {THRESHOLD}")
    print(f"Intervalle de détection: {MIN_BEAT_INTERVAL}s")
    print()
    
    # Vérification initiale de la connexion du microphone
    print("Vérification du microphone...")
    microphone_connected = is_microphone_connected()
    last_check_time = time.time()
    
    if not microphone_connected:
        print("⚠️  ATTENTION: Microphone non détecté ou non connecté!")
        print("Branchez le microphone pour commencer la détection.\n")
    else:
        print("✓ Microphone détecté\n")
    
    # Calibration optionnelle (décommenter si besoin)
    # calibrate_sensor()
    
    # Test de la LED (blanc faible puis éteint)
    print("Test de la LED...")
    np[0] = (10, 10, 10)
    np.write()
    time.sleep(1)
    np[0] = (0, 0, 0)
    np.write()
    print("LED OK - Démarrage de la détection\n")
    
    try:
        while True:
            # Vérifier périodiquement l'état du microphone
            check_microphone_status()
            
            # Si le microphone n'est pas connecté, attendre et ne rien faire
            if not microphone_connected:
                time.sleep(0.5)
                continue
            
            # Lire le niveau sonore
            sound_level = read_sound_level()
            
            # Maintenir une fenêtre glissante d'échantillons
            sound_samples.append(sound_level)
            if len(sound_samples) > SAMPLE_WINDOW:
                sound_samples.pop(0)
            
            # Calculer la moyenne des échantillons
            avg_level = sum(sound_samples) / len(sound_samples) if sound_samples else 0
            
            # Détecter un battement
            if detect_beat(sound_level, avg_level):
                # Changer la couleur de la LED
                change_led_color()
                
                # Enregistrer le temps du battement
                beat_times.append(time.time())
                
                # Garder seulement les battements récents (dernière minute)
                beat_times = [t for t in beat_times if time.time() - t < BPM_WINDOW]
                
                # Calculer et afficher le BPM
                current_bpm = calculate_bpm()
                if current_bpm > 0:
                    print(f"🎵 Battement! BPM: {current_bpm:.1f}")
                    bpm_history.append(current_bpm)
            
            # Vérifier si une minute s'est écoulée
            current_time = time.time()
            if current_time - minute_start >= 60:
                if bpm_history:
                    # Calculer la moyenne des BPM de la dernière minute
                    avg_bpm = sum(bpm_history) / len(bpm_history)
                    print(f"\n{'='*50}")
                    print(f"📊 Moyenne BPM dernière minute: {avg_bpm:.2f}")
                    print(f"{'='*50}\n")
                    save_bpm_to_file(avg_bpm)
                    bpm_history = []
                else:
                    print("\n⚠️ Aucun battement détecté cette minute\n")
                
                minute_start = current_time
            
            # Éteindre progressivement la LED (fade-out)
            current_color = np[0]
            if current_color[0] > 0 or current_color[1] > 0 or current_color[2] > 0:
                new_color = tuple(max(0, c - 5) for c in current_color)
                np[0] = new_color
                np.write()
            
            # Petit délai pour éviter une surcharge CPU
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du programme")
        np[0] = (0, 0, 0)
        np.write()
        print("LED éteinte - Programme terminé")

# ==================== POINT D'ENTRÉE ====================

if __name__ == "__main__":
    main()