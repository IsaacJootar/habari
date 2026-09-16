"""In-memory-only record of which WhatsApp senders we've seen before, so a
first-time sender can get a welcome message. Deliberately NOT persisted to
disk or a database, and cleared whenever the process restarts -- this is
transient conversation state, not a stored user profile, per the project's
no-persistent-profiles privacy principle.
"""

_seen_senders: set[str] = set()


def is_first_time(sender: str) -> bool:
    """True if we haven't seen this sender before in this run. Also
    records the sender as seen -- call once per incoming message."""
    if not sender or sender in _seen_senders:
        return False
    _seen_senders.add(sender)
    return True
