from fastapi.testclient import TestClient


def create_lunch_poll(client: TestClient):
    res = client.post(
        "/polls/",
        json={
            "title": "Lunch Poll",
            "question": "What would you like for lunch today?",
            "choices": [{"text": "Pizza"}, {"text": "Pasta"}, {"text": "Salad"}],
        },
    )
    assert res.status_code == 200
    return res.json()


def create_color_poll(client: TestClient):
    res = client.post(
        "/polls/",
        json={
            "title": "Color Poll",
            "question": "What's your favorite base color?",
            "choices": [{"text": "red"}, {"text": "green"}, {"text": "blue"}],
        },
    )
    assert res.status_code == 200
    return res.json()
