from app.session import is_first_time


def test_first_call_for_a_sender_is_first_time():
    assert is_first_time("whatsapp:+254700000001") is True


def test_second_call_for_same_sender_is_not_first_time():
    sender = "whatsapp:+254700000002"
    assert is_first_time(sender) is True
    assert is_first_time(sender) is False
    assert is_first_time(sender) is False


def test_different_senders_are_independently_first_time():
    assert is_first_time("whatsapp:+254700000003") is True
    assert is_first_time("whatsapp:+254700000004") is True


def test_empty_sender_is_never_first_time():
    assert is_first_time("") is False
