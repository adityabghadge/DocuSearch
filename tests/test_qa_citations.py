from app.services.qa import grounded_answer


def test_grounded_answer_no_sources():
    assert "couldn't find" in grounded_answer("q", []).lower()