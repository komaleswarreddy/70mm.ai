"""
Session-scoped event loop for the test suite.

app/database.py creates one module-level async SQLAlchemy engine (and
asyncpg connection pool) at import time, bound to whatever event loop is
active then. pytest-asyncio's default is a *fresh* event loop per test
function; reusing pooled asyncpg connections across different loops raises
"attached to a different loop" / proactor errors. Sharing a single event
loop for the whole test session keeps every test on the same loop the
engine was created on, matching how a real long-running server process
(one event loop for its entire lifetime) actually behaves.
"""
import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
