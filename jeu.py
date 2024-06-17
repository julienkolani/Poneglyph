#!/usr/bin/env python
# coding: utf-8

import requests
import re
import serial
import time
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration de la communication série
ser = serial.Serial('/dev/pts/13', 9600)
MAX_WAIT_TIME = 2 * 60  # 2 minutes en secondes
ACK_WAIT_TIME = 2  # 2 secondes pour attendre l'ACK

move_count = 0  # Initialisation du compteur de mouvements

# Fonction pour envoyer des messages à l'autre script avec accusé de réception
def send_to_script(message, max_attempts=3, delay=1):
    attempts = 0
    while attempts < max_attempts:
        logging.info(f"Envoi du message : {message}")
        ser.write((message + "\n").encode())
        time.sleep(delay)  # Attendre un peu pour laisser l'autre script répondre
        if ser.in_waiting > 0:
            ack = ser.readline().decode().strip()
            if ack == "ACK":
                logging.info("Accusé de réception reçu.")
                return
        attempts += 1
    logging.error("Erreur : le message n'a pas été reçu après plusieurs tentatives.")

# Fonction pour lire les messages de l'autre script avec accusé de réception
def read_from_script(max_wait_time=MAX_WAIT_TIME, delay=1):
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
    taille = len(plateau)
    header = "    " + "   ".join(chr(ord('a') + i) for i in range(taille))
    print(header)
    for i, row in enumerate(plateau, 1):
        print(f"{i} | {' | '.join(row)} |")
    print("  " + "----" * taille)

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

# Fonction pour vérifier l'état du jeu
def verifier_victoire(plateau, joueur):
    taille = len(plateau)
    for row in plateau:
        if all(s == joueur for s in row):
            return True
    for col in range(taille):
        if all(row[col] == joueur for row in plateau):
            return True
    if all(plateau[i][i] == joueur for i in range(taille)) or all(plateau[i][taille - 1 - i] == joueur for i in range(taille)):
        return True
    return False

# Fonction pour vérifier si le plateau est plein
def plateau_plein(plateau):
    return all(cell != '-' for row in plateau for cell in row)

# Fonction pour appeler l'API Flask pour le coup de l'IA
def coup_ia(plateau, joueur_humain, joueur_ia):
    url = "http://127.0.0.1:5005/api/tictactoe"
    data = {
        "board": plateau,
        "player": joueur_humain,
        "ai": joueur_ia
    }

    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        new_board = result['board']
        for i in range(len(plateau)):
            for j in range(len(plateau[i])):
                if plateau[i][j] != new_board[i][j]:
                    return i, j
    else:
        logging.error(f"Erreur: {response.status_code} {response.text}")
        return None, None

# Fonction pour initialiser le jeu
def initialiser_jeu(taille):
    return [['-' for _ in range(taille)] for _ in range(taille)]

# Fonction pour réinitialiser le jeu et informer l'autre script
def reinitialiser_jeu():
    global plateau
    plateau = initialiser_jeu(taille_plateau)
    send_to_script("reset")
    for row in plateau:
        send_to_script(" ".join(row))

# Initialisation du plateau de jeu
taille_plateau = 3  # Vous pouvez demander à l'utilisateur de spécifier la taille ici
plateau = initialiser_jeu(taille_plateau)

# Demander à l'utilisateur de choisir qui commence via l'autre script
send_to_script("user_choice")
choix_joueur = read_from_script()
if choix_joueur is None:
    raise RuntimeError("Erreur de communication : aucune réponse reçue.")
choix_joueur = choix_joueur.strip().lower()
logging.info(f"Choix du joueur : {choix_joueur}")
if choix_joueur not in ['1', '2']:
    raise ValueError("Choix invalide, veuillez entrer '1' pour humain ou '2' pour ia.")

joueur_humain = 'X' if choix_joueur == '1' else 'O'
joueur_ia = 'O' if joueur_humain == 'X' else 'X'
joueur = joueur_humain if choix_joueur == '1' else joueur_ia

# Boucle principale de jeu
while True:
    afficher_plateau(plateau)

    if joueur == joueur_humain:
        move_count += 1
        send_to_script(f"user_move{move_count}")
        choix = read_from_script()
        if choix is None:
            raise RuntimeError("Erreur de communication : aucune réponse reçue.")
        choix = choix.strip()
        try:
            row, col = coordonnees_utilisateur(choix, taille_plateau)
        except ValueError as ve:
            logging.warning(ve)
            send_to_script("move_invalid")
            continue
    else:
        row, col = coup_ia(plateau, joueur_humain, joueur_ia)
        if row is None or col is None:
            logging.error("Erreur lors de la génération du coup de l'IA. Réessayez.")
            continue
        logging.info(f"IA joue : {chr(ord('a') + col)}{row + 1}")
        send_to_script(f"ia_move {chr(ord('a') + col)}{row + 1}")

    if plateau[row][col] == '-':
        plateau[row][col] = joueur
        send_to_script(f"{row} {col} {joueur}")
    else:
        logging.warning("Cette case est déjà occupée. Essayez encore.")
        send_to_script("move_occupied")
        continue

    if verifier_victoire(plateau, joueur):
        afficher_plateau(plateau)
        send_to_script(f"{joueur} gagne")
        logging.info(f"Le joueur {joueur} a gagné!")
        break

    if plateau_plein(plateau):
        afficher_plateau(plateau)
        send_to_script("match nul")
        logging.info("Match nul!")
        break

    joueur = joueur_ia if joueur == joueur_humain else joueur_humain

if joueur == joueur_humain:
    send_to_script("reset_choice")
    reset_choice = read_from_script()
    if reset_choice is None:
        raise RuntimeError("Erreur de communication : aucune réponse reçue.")
    reset_choice = reset_choice.strip().lower()
    if reset_choice == 'oui':
        reinitialiser_jeu()
        joueur = joueur_humain if choix_joueur == '1' else joueur_ia
    else:
        exit

# Fermer le port série
ser.close()
