#!/bin/zsh
# Double-click to start AgroSnap: backend server + Expo app (real model).
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Find this Mac's Wi-Fi/hotspot IP and point the app at it
IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
if [ -z "$IP" ]; then
  echo "No Wi-Fi IP found. Connect to Wi-Fi or the phone hotspot, then run again."
  read -k1; exit 1
fi
echo "EXPO_PUBLIC_API_BASE_URL=http://$IP:8000/api/v1" > "$ROOT/mobile/.env"
echo "Using IP $IP (written to mobile/.env)"

# Window 1: server
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/backend' && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000\""
# Window 2: Expo app
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/mobile' && npx expo start --lan --clear\""
osascript -e 'tell application "Terminal" to activate'
echo "Started. Scan the QR code in the Expo window with Expo Go."
