from polling_app.database import SessionLocal
from polling_app.models import Choice, Poll, Vote


def test_delete_poll_cascades():
    db_session = SessionLocal()
    # Create poll
    poll = Poll(title="Favorite Language", question="What do you use?")
    db_session.add(poll)
    db_session.commit()

    # Add choices
    choice1 = Choice(text="Python", poll=poll)
    choice2 = Choice(text="Go", poll=poll)
    db_session.add_all([choice1, choice2])
    db_session.commit()

    # Add votes
    vote1 = Vote(username="alice", choice=choice1)
    vote2 = Vote(username="bob", choice=choice2)
    db_session.add_all([vote1, vote2])
    db_session.commit()

    # Verify setup
    assert db_session.query(Poll).filter(Poll.id == poll.id).count() == 1
    assert db_session.query(Choice).filter(Choice.poll_id == poll.id).count() == 2
    assert (
        db_session.query(Vote)
        .filter(Vote.choice_id.in_([choice1.id, choice2.id]))
        .count()
        == 2
    )

    # Delete poll
    db_session.delete(poll)
    db_session.commit()

    # Cascade delete should remove choices and votes
    assert db_session.query(Poll).filter(Poll.id == poll.id).count() == 0
    assert db_session.query(Choice).filter(Choice.poll_id == poll.id).count() == 0
    assert (
        db_session.query(Vote)
        .filter(Vote.choice_id.in_([choice1.id, choice2.id]))
        .count()
        == 0
    )
