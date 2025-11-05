# wifi.py - vérification_connexion WiFi
import network
import time

WIFI_SSID = "Orange-dm8dW"
WIFI_PASSWORD = "4VBPErrdJSkFMW7"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connexion au WiFi…")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        timeout = 15
        while timeout > 0:
            if wlan.isconnected():
                break
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print(" Connecté ! IP :", wlan.ifconfig()[0])
        return True
    else:
        print(" Échec de connexion.")
        return False

def verifier_connexion():
    """Vérifie l'état de la connexion WiFi"""
    wlan = network.WLAN(network.STA_IF)
    
    if wlan.isconnected():
        config = wlan.ifconfig()
        print(" STATUT WIFI:")
        print(f"  Connecté: OUI")
        print(f"  SSID: {WIFI_SSID}")
        print(f"  IP: {config[0]}")
        print(f"  Masque: {config[1]}")
        print(f"  Gateway: {config[2]}")
        print(f"  DNS: {config[3]}")
        return True
    else:
        print(" STATUT WIFI: NON CONNECTÉ")
        print(f"  SSID disponible: {WIFI_SSID in str(wlan.scan())}")
        return False

# Test immédiat
if __name__ == "__main__":
    print("=== TEST CONNEXION WIFI ===")
    connect_wifi()
    verifier_connexion()