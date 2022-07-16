from typing import Iterable, Any, Protocol

class SupportsCursor(Protocol):
    description: Any

    def execute(self, __sql: str, __parameters: Iterable = ...) -> 'SupportsCursor':
        ...

    def fetchone(self) -> Any:
        ...

    def fetchall(self) -> list:
        ...
