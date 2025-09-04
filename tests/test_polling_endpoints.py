from typing import Any

from polling_app.database import SessionLocal
from polling_app.models import Poll
from tests.base import TestBase
from tests.helper import create_color_poll, create_lunch_poll


class TestPollingAPI(TestBase):
    def test_create_poll(self):
        payload: dict[str, Any] = {
            "title": "Lunch Poll",
            "question": "What should we eat?",
            "choices": [{"text": "Pizza"}, {"text": "Sushi"}],
        }
        res = self.client.post("/polls/", json=payload)
        assert res.status_code == 200
        data = res.json()
        # check schema
        assert data["title"] == "Lunch Poll"
        assert data["question"] == "What should we eat?"
        assert len(data["choices"]) == 2
        assert data["choices"][0]["text"] == "Pizza"
        assert data["choices"][1]["text"] == "Sushi"
        assert data["choices"][0]["votes"] == 0
        assert data["choices"][1]["votes"] == 0

    def test_vote_and_results(self):
        # Create poll
        payload: dict[str, Any] = {
            "title": "Color Poll",
            "question": "Favorite color?",
            "choices": [{"text": "Red"}, {"text": "Blue"}],
        }
        poll = self.client.post("/polls/", json=payload).json()
        poll_id = poll["id"]
        choice_id = poll["choices"][0]["id"]  # vote for first choice

        # Cast a vote
        vote_payload: dict[str, str] = {"username": "alice", "choice_id": choice_id}
        res = self.client.post(f"/polls/{poll_id}/vote", json=vote_payload)
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # Check recasting vote by same user fails
        res = self.client.post(f"/polls/{poll_id}/vote", json=vote_payload)
        assert res.status_code == 400
        assert res.json()["detail"] == "User has already voted in this poll"

        # Check casting vote with different user works
        vote_payload = {"username": "bob", "choice_id": choice_id}
        res = self.client.post(f"/polls/{poll_id}/vote", json=vote_payload)
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # Check casting vote in non-existent poll fails
        res = self.client.post("/polls/89873/vote", json=vote_payload)
        assert res.status_code == 404
        assert res.json()["detail"] == "Poll not found"

        # Check querying non-existent poll fails
        res = self.client.get("/polls/89873")
        assert res.status_code == 404
        assert res.json()["detail"] == "Poll not found"

        # Check casting vote with invalid choice fails
        vote_payload = {"username": "charlie", "choice_id": "invalid_choice"}
        res = self.client.post(f"/polls/{poll_id}/vote", json=vote_payload)
        assert res.status_code == 400
        assert res.json()["detail"] == "Invalid choice"

        # Check results
        res2 = self.client.get(f"/polls/{poll_id}")
        assert res2.status_code == 200
        data = res2.json()
        assert any(c["votes"] == 2 for c in data["choices"])

        # delete poll
        res3 = self.client.delete(f"/polls/{poll_id}")
        assert res3.status_code == 200
        assert res3.json()["status"] == "deleted"

        # delete non-existent poll
        res4 = self.client.delete(f"/polls/{poll_id}")
        assert res4.status_code == 404
        assert res4.json()["detail"] == "Poll not found"

    def test_list_all_polls(self):
        create_color_poll(self.client)
        create_lunch_poll(self.client)
        res = self.client.get("/polls/")
        assert res.status_code == 200
        total_found = len(res.json())
        assert total_found >= 2
        assert SessionLocal().query(Poll).count() == total_found
