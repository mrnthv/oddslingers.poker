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
    0: "SB", 1: "BB", 2: "UTG", 3: "UTG1", 4: "UTG2",
    5: "LJ", 6: "HJ", 7: "CO", 8: "BTN",
}

def get_player_by_username(players, username):
    for player in players:
        if player.username == username:
            return player
    return None

def generate_rfpoker_json(table, players, hand_history):
    """
    Generates the rfpoker JSON using the comprehensive hand_data dictionary.
    """
    now = timezone.now().isoformat()
    
    if len(hand_history.hands) < 2:
        return None
    completed_hand_obj = hand_history.hands[-2]
    hand_data = completed_hand_obj.filtered_json()

    if not hand_data:
        return None

    events = hand_data.get('events', [])
    actions = hand_data.get('actions', [])
    full_log = sorted(events + actions, key=lambda x: x.get('ts', ''))

    # === Main Round Data ===
    round_data = {
        "timestamp": now,
        "variation": hand_data.get('table', {}).get('table_type'),
        "button": hand_data.get('table', {}).get('btn_idx'),
        "blinds": { 
            "sb": int(Decimal(hand_data.get('table', {}).get('sb', 0))), 
            "bb": int(Decimal(hand_data.get('table', {}).get('bb', 0))) 
        },
        "handNumber": hand_data.get('table', {}).get('hand_number'),
        "pot": int(sum(p.wagers for p in players)),
    }

    # === Player Hand Data ===
    hands_data = []
    initial_players_state = hand_data.get('players', [])
    for player_state in initial_players_state:
        player_obj = get_player_by_username(players, player_state.get('username'))
        if not player_obj:
            continue

        player_log_items = [log for log in full_log if log.get('subj') == player_state.get('username')]
        player_cards = [
            item['args']['card'] for item in player_log_items 
            if item.get('event') == 'DEAL' and 'card' in item.get('args', {})
        ]
        is_winner = any(item.get('event') == 'WIN' and item.get('subj') == player_state.get('username') for item in player_log_items)

        hands_data.append({
            "cards": player_cards,
            "startingStack": int(Decimal(player_state.get('stack', 0))),
            "endingStack": int(player_obj.stack),
            "seat": player_state.get('position'),
            "position": POSITION_MAP.get(player_state.get('position'), "UNKNOWN"),
            "playerNameOverride": player_state.get('username'),
            "isWinner": is_winner,
        })

    # === Streets and Actions Data (Corrected Logic) ===
    streets_data = []
    actions_data_final = []
    current_street = "PREFLOP"
    
    # Reconstruct board cards directly from DEALER events
    board_cards = [
        item['args']['card'] for item in events 
        if item.get('event') == 'DEAL' and item.get('subj') == 'DEALER'
    ]
    
    # Track which streets have been seen
    seen_streets = {"PREFLOP"}

    for log_item in full_log:
        event_name = log_item.get('event')
        action_name = log_item.get('action')

        # Only advance the street on the main "side_effect" event
        if event_name == 'NEW_STREET' and log_item.get('subj') == 'side_effect':
            if current_street == "PREFLOP":
                current_street = "FLOP"
                seen_streets.add("FLOP")
            elif current_street == "FLOP":
                current_street = "TURN"
                seen_streets.add("TURN")
            elif current_street == "TURN":
                current_street = "RIVER"
                seen_streets.add("RIVER")
        
        elif action_name:
            # This is an action, assign it the current street
            acting_player = get_player_by_username(players, log_item.get('subj'))
            if acting_player:
                actions_data_final.append({
                    "bet": int(Decimal(log_item.get('args', {}).get('amt', 0))),
                    "actionType": action_name,
                    "timestamp": log_item.get('ts'),
                    "street": current_street, # Assign the correct, tracked street
                    "actingSeat": acting_player.position
                })

    # Assemble the final streets data ONLY for streets that were seen
    if "PREFLOP" in seen_streets:
        streets_data.append({"streetType": "PREFLOP", "cards": []})
    if "FLOP" in seen_streets:
        streets_data.append({"streetType": "FLOP", "cards": board_cards[:3]})
    if "TURN" in seen_streets:
        streets_data.append({"streetType": "TURN", "cards": board_cards[:4]})
    if "RIVER" in seen_streets:
        streets_data.append({"streetType": "RIVER", "cards": board_cards})
    
    # === Final Assembly ===
    rfpoker_data = {
        "tournament_id": TOURNAMENT_ID,
        "round": round_data,
        "hands": hands_data,
        "streets": streets_data,
        "actions": actions_data_final,
        "tableId": str(table.id),
        "sessions": [],
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
