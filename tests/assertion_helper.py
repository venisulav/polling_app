import json
from typing import Any, Optional

from polling_app import constants as C


def assert_response_success(
    response: str, action: str, data: Optional[dict[str, Any]] = None
):
    response_json = json.loads(response)
    assert response_json["type"] == "success"
    assert response_json["action"] == action
    if data:
        assert response_json["data"] == data
    return response_json


def assert_response_error(
    response: str, expected_error_code: str, expected_error_msg: str
):
    response_json = json.loads(response)
    assert response_json["type"] == "error"
    assert response_json["code"] == expected_error_code
    assert response_json["message"] == expected_error_msg
    return response_json


def assert_vote_count(
    results: list[dict[str, Any]], choice_id: str, expected_votes: int
):
    actual_vote_count = next(
        (e["votes"] for e in results if e["id"] == choice_id), None
    )
    assert actual_vote_count == expected_votes


def assert_successful_connect(response: str):
    assert_response_success(response, C.ACTION_CONNECT, {"message": "connected"})


def assert_successful_unsubscription(response: str, poll_id: str):
    response_json = assert_response_success(response, C.ACTION_UNSUBSCRIBE)
    assert response_json["data"]["poll_id"] == poll_id


def assert_successful_disconnect(response: str):
    assert_response_success(response, C.ACTION_DISCONNECT)


def assert_successful_subscription(
    response: str, poll_id: str, choice_id: str, expected_votes: int
):
    response_json = assert_response_success(response, C.ACTION_SUBSCRIBE)
    assert poll_id == response_json["data"]["poll_id"]
    assert_vote_count(response_json["data"]["results"], choice_id, expected_votes)


def assert_result_update(
    response: str, poll_id: str, choice_id: str, expected_votes: int
):
    response_json = assert_response_success(response, C.ACTION_UPDATE)
    assert poll_id == response_json["data"]["poll_id"]
    assert_vote_count(response_json["data"]["results"], choice_id, expected_votes)


def assert_not_subscribed_error(response: str, poll_id: str):
    assert_response_error(
        response, C.ERR_NOT_SUBSCRIBED, f"Not subscribed to {poll_id}"
    )


def assert_already_subscribed_error(response: str, poll_id: str):
    assert_response_error(
        response, C.ERR_ALREADY_SUBSCRIBED, f"Already subscribed to {poll_id}"
    )


def assert_poll_not_found_error(response: str, poll_id: str):
    assert_response_error(
        response, C.ERR_POLL_NOT_FOUND, f"Poll {poll_id} does not exist"
    )


def assert_poll_deleted_error(response: str, poll_id: str):
    assert_response_error(
        response, C.ERR_POLL_DELETED, f"Poll {poll_id} has been deleted"
    )


def assert_unknown_action_error(response: str, poll_id: str):
    assert_response_error(response, C.ERR_UNKNOWN_ACTION, f"Unknown action {poll_id}")
