#!/usr/bin/env python
# coding: utf-8

from flask import Flask, request, jsonify
import threading
import numpy as np
import math
import logging

app = Flask(__name__)

# Configuration du logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Crée un plateau de jeu vide de taille spécifiée
def initial_board(size):
    return [['-' for _ in range(size)] for _ in range(size)]

# Vérifie si un joueur a gagné
def is_winner(board, player):
    size = len(board)
    # Vérifie les lignes, les colonnes et les diagonales
    for i in range(size):
        if all([cell == player for cell in board[i]]) or all([board[j][i] == player for j in range(size)]):
            return True
    if all([board[i][i] == player for i in range(size)]) or all([board[i][size - 1 - i] == player for i in range(size)]):
        return True
    return False

# Vérifie si la partie est nulle
def is_draw(board):
    return all([cell != '-' for row in board for cell in row])

# Retourne la liste des coups possibles
def get_available_moves(board):
    moves = []
    for i in range(len(board)):
        for j in range(len(board[i])):
            if board[i][j] == '-':
                moves.append((i, j))
    return moves

# Joue un coup pour un joueur donné
def make_move(board, move, player):
    board[move[0]][move[1]] = player

# Implémente l'algorithme minimax avec élagage alpha-bêta
def minimax(board, depth, is_maximizing, alpha, beta):
    if is_winner(board, 'X'):
        return -1
    elif is_winner(board, 'O'):
        return 1
    elif is_draw(board):
        return 0
    
    if is_maximizing:
        max_eval = -math.inf
        for move in get_available_moves(board):
            make_move(board, move, 'O')
            eval = minimax(board, depth + 1, False, alpha, beta)
            make_move(board, move, '-')
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = math.inf
        for move in get_available_moves(board):
            make_move(board, move, 'X')
            eval = minimax(board, depth + 1, True, alpha, beta)
            make_move(board, move, '-')
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

# Détermine le meilleur coup pour le joueur utilisant l'algorithme minimax
def best_move(board, player):
    best_val = -math.inf if player == 'O' else math.inf
    optimal_move = None
    for move in get_available_moves(board):
        make_move(board, move, player)
        move_val = minimax(board, 0, player == 'X', -math.inf, math.inf)
        make_move(board, move, '-')
        if player == 'O':
            if move_val > best_val:
                best_val = move_val
                optimal_move = move
        else:
            if move_val < best_val:
                best_val = move_val
                optimal_move = move
    return optimal_move

# Route de l'API pour traiter les demandes POST
@app.route('/api/tictactoe', methods=['POST'])
def tictactoe():
    try:
        board = request.json.get('board')
        player = request.json.get('player')
        ai = request.json.get('ai')

        logging.info(f"Requête reçue avec le plateau : {board} et le joueur humain : {player}, IA : {ai}")

        if board is None or not isinstance(board, list) or not all(isinstance(row, list) for row in board):
            return jsonify({"error": "Invalid request format"}), 400

        # Si le plateau est plein, retourner simplement le plateau
        if is_draw(board):
            logging.info("Le plateau est plein, match nul!")
            return jsonify({'board': board}), 200

        # Demander à l'IA de jouer
        ai_move = best_move(board, ai)
        if ai_move:
            make_move(board, ai_move, ai)
            logging.info(f"L'IA joue en position : {ai_move}")

        # Retourner le tableau mis à jour
        logging.info(f"Plateau mis à jour : {board}")
        return jsonify({'board': board}), 200

    except Exception as e:
        logging.error(f"Erreur lors du traitement de la requête : {e}")
        return jsonify({"error": str(e)}), 500


def run_flask():
    logging.info("Lancement du serveur Flask sur le port 5005")
    app.run(debug=False, port=5005, use_reloader=False)  # Désactive le rechargement automatique

# Démarrer le serveur Flask dans un thread séparé
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

