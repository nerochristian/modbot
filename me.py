import websocket
import json
import threading
import time
import requests
import sys

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("USER_TOKEN")
if not TOKEN:
    print("USER_TOKEN not found in .env file. Please add it.")
    sys.exit(1)
CHANNEL_ID = "1388268039773884592"

def main():
    print("Fetching channel info...")
    headers = {
        "Authorization": TOKEN
    }
    req = requests.get(f"https://discord.com/api/v9/channels/{CHANNEL_ID}", headers=headers)
    if req.status_code != 200:
        print("Failed to get channel info. Check your token and channel ID.")
        print(req.text)
        sys.exit(1)
        
    guild_id = req.json().get("guild_id")
        
    def send_json_request(ws, request):
        ws.send(json.dumps(request))

    def receive_json_response(ws):
        while True:
            response = ws.recv()
            if response:
                return json.loads(response)

    def heartbeat(interval, ws):
        print("Heartbeat thread started")
        while True:
            time.sleep(interval)
            heartbeatJSON = {
                "op": 1,
                "d": None
            }
            try:
                send_json_request(ws, heartbeatJSON)
            except Exception:
                break

    print("Connecting to Discord Gateway...")
    ws = websocket.WebSocket()
    ws.connect('wss://gateway.discord.gg/?v=9&encoding=json')
    event = receive_json_response(ws)
    heartbeat_interval = event['d']['heartbeat_interval'] / 1000

    threading.Thread(target=heartbeat, args=(heartbeat_interval, ws), daemon=True).start()

    print("Identifying...")
    payload = {
        'op': 2,
        "d": {
            "token": TOKEN,
            "properties": {
                "os": "windows",
                "browser": "Chrome",
                "device": "pc"
            }
        }
    }
    send_json_request(ws, payload)
    
    time.sleep(2)
    
    print(f"Joining VC {CHANNEL_ID}...")
    voice_payload = {
        "op": 4,
        "d": {
            "guild_id": guild_id,
            "channel_id": CHANNEL_ID,
            "self_mute": True,
            "self_deaf": True
        }
    }
    send_json_request(ws, voice_payload)
    print("Successfully requested to join VC. Keeping connection alive...")
    
    try:
        while True:
            # Keep receiving to avoid buffer overflow and keep connection alive
            ws.recv()
    except KeyboardInterrupt:
        print("Exiting...")
        ws.close()
    except Exception as e:
        print(f"Connection lost: {e}")

if __name__ == "__main__":
    main()
