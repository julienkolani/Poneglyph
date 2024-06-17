#!/usr/bin/env python
# coding: utf-8

import serial
import time
import logging
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration de la communication série
ser = serial.Serial('/dev/pts/14', 9600)
MAX_WAIT_TIME = 2 * 60  # 2 minutes en secondes
ACK_WAIT_TIME = 2  # 2 secondes pour attendre l'ACK

# Fonction pour envoyer un message au script principal avec accusé de réception
def send_to_main(message, max_attempts=3, delay=1):
    attempts = 0
    while attempts < max_attempts:
        logging.info(f"Envoi du message : {message}")
        ser.write((message + "\n").encode())
        time.sleep(delay)  # Attendre un peu pour laisser le temps à l'autre script de répondre
        if ser.in_waiting > 0:
            ack = ser.readline().decode().strip()
            if ack == "ACK":
                logging.info("Accusé de réception reçu.")
                return
        attempts += 1
    logging.error("Erreur : le message n'a pas été reçu après plusieurs tentatives.")

# Fonction pour lire la réponse du script principal avec accusé de réception
def read_from_main(max_wait_time=MAX_WAIT_TIME, delay=1):
    elapsed_time = 0
    while elapsed_time < max_wait_time:
        if ser.in_waiting > 0:
            message = ser.readline().decode().strip()
            ser.write("ACK\n".encode())
            return message
        time.sleep(delay)  # Attendre avant de réessayer
        elapsed_time += delay
    logging.error("Erreur : aucune réponse reçue après plusieurs tentatives.")
    return None

# Fonction pour afficher le plateau de jeu
def afficher_plateau(plateau):
    header = "    a   b   c"
    print(header)
    for i, row in enumerate(plateau, 1):
        print(f"{i} | {' | '.join(row)} |")
    print("  ------------")

# Fonction pour traduire les coordonnées de l'utilisateur en indices de matrice
def coordonnees_utilisateur(choix, taille):
    match = re.match(rf'([a-{chr(ord("a")+taille-1)}])([1-{taille}])|([1-{taille}])([a-{chr(ord("a")+taille-1)}])', choix)
    if match:
        col, row = match.group(1, 2) if match.group(1) else match.group(4, 3)
        col_index = ord(col) - ord('a')
        row_index = int(row) - 1
        return row_index, col_index
    else:
        raise ValueError(f"Coordonnées invalides, veuillez entrer une valeur comme 'a1', 'b2', etc. pour une taille de {taille}x{taille}.")

# Simulation des interactions utilisateur
def simulate_user_interaction():
    logging.info("Simulation des interactions utilisateur...")

    plateau = [['-' for _ in range(3)] for _ in range(3)]  # Initialiser un plateau vide
    move_counter = 1  # Initialiser le compteur de mouvements
    
    # Choisir qui commence
    while True:
        message = read_from_main()
        if message == "user_choice":
            while True:
                choix = input("Qui commence ? (1 pour humain, 2 pour IA) : ").strip()
                if choix in ["1", "2"]:
                    send_to_main(choix)
                    logging.info("Humain commence" if choix == "1" else "IA commence")
                    break
                else:
                    logging.warning("Choix invalide, veuillez entrer '1' pour humain ou '2' pour IA.")
                    print("Choix invalide, veuillez entrer '1' pour humain ou '2' pour IA.")
            break
    
    while True:
        # Attendre le message du script principal
        message = read_from_main()
        if message is None:
            raise RuntimeError("Erreur de communication : aucune réponse reçue.")
        logging.info(f"Message reçu : {message}")

        if re.match(r'user_move\d+', message):
            while True:
                afficher_plateau(plateau)
                move = input(f"Votre mouvement {move_counter} (par ex. a1, b2) : ").strip()
                if re.match(r'^[a-c][1-3]$', move):
                    send_to_main(f"{move}{move_counter}")  # Ajouter le compteur de mouvements
                    break
                else:
                    logging.warning("Coordonnées invalides, veuillez entrer une valeur comme 'a1', 'b2'.")
                    print("Coordonnées invalides, veuillez entrer une valeur comme 'a1', 'b2'.")
            response = read_from_main()
            if response is None:
                raise RuntimeError("Erreur de communication : aucune réponse reçue.")
            logging.info(f"Réponse : {response}")
            if response.startswith("move_invalid"):
                logging.warning("Coordonnées invalides, veuillez entrer une valeur comme 'a1', 'b2'.")
            elif response.startswith("move_occupied"):
                logging.warning("Cette case est déjà occupée. Essayez encore.")
            else:
                coord, joueur = response.split()[:2], response.split()[2]
                plateau[int(coord[0])][int(coord[1])] = joueur
                afficher_plateau(plateau)
                move_counter += 1  # Incrémenter le compteur après un mouvement valide
        
        elif message.startswith("ia_move"):
            _, move = message.split()
            coord, joueur = coordonnees_utilisateur(move, 3), "O"
            plateau[coord[0]][coord[1]] = joueur
            logging.info(f"IA joue : {move}")
            afficher_plateau(plateau)
        
        elif "gagne" in message or "match nul" in message:
            logging.info(message)
            break

        elif message == "reset_choice":
            while True:
                reset_choice = input("Voulez-vous réinitialiser le jeu ? (oui/non) : ").strip().lower()
                if reset_choice in ['oui', 'non']:
                    send_to_main(reset_choice)
                    break
                else:
                    logging.warning("Choix invalide, veuillez entrer 'oui' ou 'non'.")
                    print("Choix invalide, veuillez entrer 'oui' ou 'non'.")
            if reset_choice == 'non':
                break
            else:
                plateau = [['-' for _ in range(3)] for _ in range(3)]  # Réinitialiser le plateau
                move_counter = 1  # Réinitialiser le compteur de mouvements

    # Fin de la simulation
    ser.close()
    logging.info("Fin de la simulation")

if __name__ == "__main__":
    simulate_user_interaction()
