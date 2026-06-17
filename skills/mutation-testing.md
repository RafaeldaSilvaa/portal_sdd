# Mutation Testing Strategy

## Intent
Validate test suite quality by injecting artificial faults (mutants) and measuring detection rate.

## Configuration
```toml
[tool.mutmut]
paths-to-mutate = ["src/"]
runner = "pytest -x"
exclude = ["tests/", "*.pyc"]
backup = false
```

## Mutation Score Target: >= 85%

## Operators
| Mutator | Description |
|---------|-------------|
| Arithmetic | Replace + with -, * with / |
| Boolean | Flip True/False, and/or |
| Comparison | Swap > with >=, == with != |
| Null | Replace not-None with None |

## Anti-patterns to Block
- Tests that pass without asserting anything
- Snapshot-based tests that accept any output
- Tests that mock the entire system under test

## Testing Pattern
```python
def test_mutation_killing_example():
    # Arrange
    calculator = BillingCalculator(tax_rate=0.1)
    # Act
    result = calculator.apply_tax(1000)
    # Assert - specific enough to catch arithmetic mutants
    assert result == 1100, f"Expected 1100, got {result}"
    assert isinstance(result, int)
```
