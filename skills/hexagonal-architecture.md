# Hexagonal Architecture (Ports & Adapters)

## Intent
Isolate domain logic from infrastructure concerns through strict interface boundaries.

## Layer Structure
```
domain/          # Enterprise business rules (pure Python, zero deps)
  entities.py    # Aggregates, value objects
  ports.py       # Repository, service interfaces
  use_cases.py   # Application business rules

application/     # Use case orchestration
  services.py    # Command/Query handlers

infrastructure/  # Adapter implementations
  db/            # SQLAlchemy repositories
  api/           # REST controllers
  messaging/     # Message queue adapters
```

## Port Definition Pattern
```python
# domain/ports.py
class InvoicePort(Protocol):
    async def create(self, cmd: CreateInvoiceCommand) -> Invoice: ...

class InvoiceRepositoryPort(Protocol):
    async def save(self, invoice: Invoice) -> None: ...
    async def next_identity(self) -> str: ...
```

## Anti-patterns to Block
- NO direct infrastructure imports in domain layer
- NO business logic in adapters (controllers/repositories)
- NO circular dependencies between layers

## Testing Pattern
```python
def test_create_invoice():
    # Arrange
    repo = FakeInvoiceRepository()
    use_case = CreateInvoiceUseCase(repo)
    cmd = CreateInvoiceCommand(amount=1000, currency="USD")

    # Act
    invoice = await use_case.execute(cmd)

    # Assert
    assert invoice.amount_cents == 1000
    assert invoice.currency == "USD"
```
