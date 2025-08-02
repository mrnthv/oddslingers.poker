import json
from decimal import Decimal
import requests
from django.utils import timezone
from poker.cards import Card
from poker import rankings
from poker.constants import Event

API_ENDPOINT = "https://dev.sidebetz.ai/api/next-hand"
TOURNAMENT_ID = "YOUR_TOURNAMENT_ID"

POSITION_MAP = {
    0: "SB",
    1: "BB",
    2: "UTG",
    3: "UTG1",
    4: "UTG2",
    5: "LJ",
    6: "HJ",
    7: "CO",
    8: "BTN",
}

def generate_rfpoker_json(table, players, hand_history):
    """
    Generates the rfpoker JSON for the given table and players.
    """
    now = timezone.now().isoformat()
    hand_history_log = hand_history.get_log(current_hand_only=True)
    current_hand_log = hand_history_log['hands'][0] if hand_history_log['hands'] else None

    if not current_hand_log:
        return None

    round_data = {
        "timestamp": now,
        "variation": table.table_type,
        "difficulty": "ADVANCED",
        "button": table.btn_idx,
        "blindLevel": {
            "index": 0,
            "bombPot": 0,
            "boards": 1,
            "smallestDenomination": 25,
            "blinds": {
                "sb": int(table.sb),
                "bb": int(table.bb),
            },
            "antes": {},
            "straddles": {},
            "duration": 0,
            "breakTime": 0,
        },
        "mode": "CASH",
        "handNumber": table.hand_number,
        "pot": int(sum(p.wagers for p in players)),
        "isStarred": False,
        "permissions": "PRIVATE",
        "timeLeft": 0,
        "totalPlayers": len(players),
        "activePlayers": len([p for p in players if p.is_active()]),
    }

    hands_data = []
    winner_username = None
    for event in current_hand_log.get('events', []):
        if event['event'] == 'WIN':
            winner_username = event['subj']
            break

    for player in players:
        starting_stack = 0
        cards = []
        is_winner = player.username == winner_username
        is_all_in = False

        if current_hand_log and 'players' in current_hand_log:
            for p_log in current_hand_log['players']:
                if p_log['id'] == player.id:
                    starting_stack = p_log['stack']
                    break

        for event in current_hand_log.get('events', []):
            if event['event'] == 'DEAL' and event['subj'] == player.username:
                cards.append(event['args']['card'])
            if event['event'] in ['BET', 'RAISE_TO', 'CALL'] and event['args'].get('all_in'):
                is_all_in = True


        hand_class = ""
        if cards and len(cards) + len(table.board) >= 5:
            best_hand = rankings.best_hand_from_cards([Card(c) for c in cards] + table.board)
            hand_class = rankings.hand_to_name(best_hand)


        hands_data.append({
            "cards": cards,
            "startingStack": int(starting_stack),
            "endingStack": int(player.stack),
            "seat": player.position,
            "position": POSITION_MAP.get(player.position, "UNKNOWN"),
            "playerNameOverride": player.username,
            "playerId": str(player.user.id) if player.user else None,
            "sessionId": None,  # Placeholder
            "buyIn": int(player.user.default_buyin * table.bb) if player.user else 0,
            "bonus": 5,
            "tips": 0,
            "isWinner": is_winner,
            "isShowdown": False,  # To be implemented
            "isAllIn": is_all_in,
            "handClasses": [hand_class],
            "timestamp": now,
            "permissions": "PRIVATE",
        })

    streets_data = []
    actions_data = []

    if current_hand_log:
        street = "PREFLOP"
        pot_size = 0
        for event in current_hand_log.get('events', []):
            if event['event'] == 'NEW_STREET':
                if street == "PREFLOP":
                    street = "FLOP"
                elif street == "FLOP":
                    street = "TURN"
                elif street == "TURN":
                    street = "RIVER"

            if event['event'] in ['POST', 'ANTE', 'BET', 'RAISE_TO', 'CALL']:
                pot_size += int(float(event['args']['amt']))


        streets = ["PREFLOP", "FLOP", "TURN", "RIVER"]
        board = table.board
        street_cards = {
            "PREFLOP": [],
            "FLOP": board[:3],
            "TURN": board[:4],
            "RIVER": board[:5],
        }

        for street_name in streets:
            streets_data.append({
                "cards": [str(c) for c in street_cards[street_name]],
                "boards": 1,
                "pot": 0,  # To be implemented
                "timestamp": now,
                "streetType": street_name,
                "equities": [],
                "playerSeats": [],
            })

        for action in current_hand_log.get('actions', []):
            actions_data.append({
                "bet": int(float(action.get('args', {}).get('amt', 0))),
                "actionType": action['action'],
                "timestamp": action['ts'],
                "call": 0, # To be implemented
                "minRaise": 0, # To be implemented
                "maxRaise": 0, # To be implemented
                "stack": 0, # To be implemented
                "actingSeat": 0, # To be implemented
                "equities": [],
                "street": "", # To be implemented
                "playerSeats": [],
                "pot": 0, # To be implemented
                "powerupType": "NONE",
            })


    rfpoker_data = {
        "tournament_id": TOURNAMENT_ID,
        "round": round_data,
        "hands": hands_data,
        "streets": streets_data,
        "actions": actions_data,
        "tableId": str(table.id),
        "sessions": [], # Placeholder
    }
    return rfpoker_data

def send_to_endpoint(data):
    """
    Sends the given data to the API endpoint.
    """
    try:
        response = requests.post(API_ENDPOINT, json=data)
        response.raise_for_status()
        print(f"Successfully sent data to {API_ENDPOINT}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to {API_ENDPOINT}: {e}")

def write_to_file(data):
    """
    Writes the given data to a file.
    """
    with open("rfpoker.json", "w") as f:
        json.dump(data, f, indent=4)
    print("Successfully wrote data to rfpoker.json")
