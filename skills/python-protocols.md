# Python Protocols & Structural Subtyping

## Intent
Use `typing.Protocol` for static duck typing in hexagonal architecture ports.

## Blueprint
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class InvoiceRepository(Protocol):
    async def save(self, invoice: "Invoice") -> None: ...
    async def get_by_id(self, invoice_id: str) -> "Invoice | None": ...

class PostgresInvoiceRepository:
    async def save(self, invoice: "Invoice") -> None: ...
    async def get_by_id(self, invoice_id: str) -> "Invoice | None": ...
```

## Anti-patterns to Block
- Do NOT use ABC for interface definitions in Python 3.12+
- Do NOT use `type: ignore` to bypass protocol mismatches
- Do NOT define methods outside the protocol that should be part of it

## Testing Pattern
```python
class FakeInvoiceRepository:
    def __init__(self):
        self._store: dict[str, Invoice] = {}

    async def save(self, invoice: Invoice) -> None:
        self._store[invoice.id] = invoice

    async def get_by_id(self, invoice_id: str) -> Invoice | None:
        return self._store.get(invoice_id)
```
