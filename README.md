# ironclad
**ironclad** helps developers write defensive, self-documenting Python code.

It enforces parameter types, constrains values with predicates or enums,
and raises precise errors on violation—keeping interfaces explicit and code clean.
Simple, composable guards harden functions and classes with correctness and security,
with minimal overhead and maximum readability.

[![GitHub License](https://img.shields.io/github/license/zentiph/ironclad?style=flat-square&labelColor=0f0f0f)](https://github.com/Zentiph/ironclad/blob/main/LICENSE.md)
[![Contributors](https://img.shields.io/github/contributors/zentiph/ironclad?style=flat-square&labelColor=0f0f0f)](../../graphs/contributors)
<br/>
[![GitHub commit activity](https://img.shields.io/github/commit-activity/t/zentiph/ironclad?style=flat-square&labelColor=0f0f0f)](https://github.com/zentiph/ironclad/commits/main)
[![Last Commit](https://img.shields.io/github/last-commit/zentiph/ironclad?style=flat-square&labelColor=0f0f0f)](https://github.com/zentiph/ironclad/commits/main)
<br/>
![Code Style: Ruff](https://img.shields.io/badge/code%20style-Ruff-d7ff64?style=flat-square&labelColor=0f0f0f)
![Linter: Ruff](https://img.shields.io/badge/linter-Ruff-d7ff64?style=flat-square&labelColor=0f0f0f)

## Features
* **Strict type checks:** Fail fast on mismatches with clear `TypeError`s.
* **Value constraints:** Allowlists, enums, ranges, and custom predicates.
* **Composable guards:** Combine checks for rich, readable contracts.
* **Low-boilerplate API:** Keep validation close to the signature, not scattered.
* **Security-minded:** Reduce attack surface from unexpected inputs.

## Installation
You can install **ironclad** in one of two ways:
1. Install via pip:
```bash
pip install ironclad
```
2. Clone this repository:
```bash
git clone https://github.com/Zentiph/ironclad
```

## Quick Start
### Importing the library:
```python
import ironclad as ic
```
### Creating strict type enforcements:
```python
# enforcing types with instance/type spec checks
@ic.enforce_types(price=float, tax_rate=float)
def add_sales_tax(price, tax_rate):
    return price * (1 + tax_rate)

add_sales_tax(50.0, 0.08)    # OK: 54.0
add_sales_tax(50.0, "0.08")  # TypeError
                             # (with better diagnostics)

# enforcing types with type annotations
@ic.enforce_annotations()
def get_even(l: list[int]) -> list[int]:
    return [e for e in l if e % 2 == 0]

get_even([1, 2, 3])        # OK: [2]
get_even([1.0, 2.0, 3.0])  # TypeError
                           # (with better diagnostics)
```
### Creating type-enforced runtime overloads:
```python
@ic.runtime_overload
def describe(x: int):
    return f"int: {x}"

@describe.overload
def _(x: str):
    return f"str: '{x}'"

describe(1)     # OK: 'int: 1'
describe("hi")  # OK: "str: 'hi'"
describe(2.3)   # InvalidOverloadError
```
### Creating predicates
```python
is_pos = ic.predicates.Predicate[int](
    lambda x: x > 0, "is positive"
)
is_pos(4)   # True
is_pos(-1)  # False
```

## Contributions
See [the contributing page](CONTRIBUTING.md).

## License
See [the license page](LICENSE.md).