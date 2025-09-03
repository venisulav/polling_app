import asyncio
import websockets
import requests

BASE = "http://127.0.0.1:8000"

# Step 1: Create a poll
poll = {
    "title": "Lunch Poll",
    "question": "What should we eat?",
    "choices": [{"text": "Pizza"}, {"text": "Sushi"}, {"text": "Salad"}],
}
poll_id = requests.post(f"{BASE}/polls", json=poll).json()["id"]
print("Poll created:", poll_id)

# Step 2: Cast a vote
choices = requests.get(f"{BASE}/polls/{poll_id}").json()["choices"]
pizza_id = choices[0]["id"]
requests.post(
    f"{BASE}/polls/{poll_id}/vote", json={"username": "alice", "choice_id": pizza_id}
)


# Step 3: Listen for live updates
async def listen():
    uri = f"ws://127.0.0.1:8000/polls/19258e1f-431f-4b51-b4e2-bf5d9d0146fd"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket, waiting for updates...")
        while True:
            msg = await websocket.recv()
            print("Live update:", msg)


asyncio.run(listen())
