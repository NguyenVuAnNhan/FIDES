from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock
from typing import Any

from backend.app.config import get_settings

_driver = None
_driver_lock = Lock()


def graph_available() -> bool:
    settings = get_settings()
    if not settings.neo4j_enabled:
        return False
    try:
        import neo4j  # noqa: F401
    except ImportError:
        return False
    return True


def health_check() -> bool:
    if not graph_available():
        return False
    try:
        with graph_session() as session:
            result = session.run("RETURN 1 AS ok")
            return result.single()["ok"] == 1
    except Exception:
        return False


@contextmanager
def graph_session() -> Iterator[Any]:
    driver = _get_driver()
    if driver is None:
        raise RuntimeError("Neo4j is not enabled or the driver is unavailable.")
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def run_write(query: str, parameters: dict[str, Any] | None = None) -> None:
    if not graph_available():
        return
    with graph_session() as session:
        session.execute_write(lambda tx: tx.run(query, parameters or {}).consume())


def run_read(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not graph_available():
        return []

    def _read(tx: Any) -> list[dict[str, Any]]:
        result = tx.run(query, parameters or {})
        return [record.data() for record in result]

    with graph_session() as session:
        return session.execute_read(_read)


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver
    if not graph_available():
        return None

    settings = get_settings()
    with _driver_lock:
        if _driver is not None:
            return _driver
        from neo4j import GraphDatabase

        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        return _driver
