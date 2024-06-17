import serial
import time

# Ouvrir les deux ports série
ser1 = serial.Serial('/dev/pts/8', 9600)
ser2 = serial.Serial('/dev/pts/5', 9600)

# Attendre que les ports soient prêts
time.sleep(2)

# Écrire sur le premier port série
print("Writing to ser1")
ser1.write(b"Hello\n")

# Attendre un peu pour laisser le temps à l'autre appareil de répondre
time.sleep(2)

# Lire sur le deuxième port série
print("Reading from ser2")
response = ser2.readline().decode().strip()
print(f"Response: {response}")

# Fermer les deux ports série
ser1.close()
ser2.close()
