import pytest

from app import session


@pytest.fixture(autouse=True)
def _reset_session_state():
    """app.session tracks "seen" WhatsApp senders in a module-level set so
    a first-time sender gets a welcome message. Without resetting it
    between tests, whichever test happens to run first for a given phone
    number "consumes" its first-time status, making later tests that reuse
    the same number order-dependent."""
    session._seen_senders.clear()
    yield
    session._seen_senders.clear()
