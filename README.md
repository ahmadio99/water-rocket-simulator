# Water Rocket Simulator 🚀

A multiplayer, physics‑accurate water rocket simulator with live events like sudden wind gusts, leaks, turbo boosts, and storms.

## 🎮 Features
- **Realistic physics**: Bottle volume, nozzle size, water amount, air pressure, and temperature all affect flight.
- **Live events**: 🌬 Wind gusts, 💦 leaks, 🔥 turbo boosts, 🌩 storms.
- **Multiplayer**: Compete with friends in real time.
- **Launch log**: Track altitude and range for each launch.

## 🖥 How to Play
1. Enter your **player name**.
2. Adjust launch settings:
   - Bottle volume (L)
   - Bottle diameter (cm)
   - Nozzle diameter (cm)
   - Water volume (L)
   - Air pressure (psi gauge)
   - Soap amount (0–1)
   - Wind speed (m/s)
   - Temperature (°C)
3. (Optional) Enable live events for extra chaos.
4. Hit **Launch** and watch your rocket fly!

## 📦 Installation
No installation needed — just open `index.html` in your browser.

For multiplayer/live events to work locally:
- Run a local server (e.g., with Python):
  ```bash
  python -m http.server
