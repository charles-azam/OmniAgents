"""Calculator module with some bugs to fix."""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide a by b.

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base: float, exponent: int) -> float:
    """
    Calculate base raised to exponent.

    BUG: Off-by-one error in the loop
    """
    result = 1.0
    for _ in range(exponent - 1):  # BUG: Should be range(exponent)
        result *= base
    return result


def is_even(n: int) -> bool:
    """
    Check if a number is even.

    BUG: Logic error
    """
    return n % 2 == 1  # BUG: Should be == 0


def average(numbers: list[float]) -> float:
    """
    Calculate average of numbers.

    BUG: Doesn't handle empty list
    """
    total = sum(numbers)
    return total / len(numbers)  # BUG: Will crash on empty list


def factorial(n: int) -> int:
    """Calculate factorial (this one is correct)."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
