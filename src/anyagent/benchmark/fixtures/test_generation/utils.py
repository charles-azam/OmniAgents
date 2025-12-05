"""Utility functions for mathematical operations and string processing."""


def add_numbers(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide_numbers(a: float, b: float) -> float:
    """
    Divide two numbers.

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def reverse_string(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


def count_vowels(text: str) -> int:
    """Count vowels in a string."""
    if not text:
        return 0
    vowels = "aeiouAEIOU"
    return sum(1 for char in text if char in vowels)


def is_palindrome(text: str) -> bool:
    """Check if a string is a palindrome (ignoring spaces and case)."""
    cleaned = "".join(text.split()).lower()
    return cleaned == cleaned[::-1]


def factorial(n: int) -> int:
    """
    Calculate factorial of n.

    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def find_max(numbers: list[float]) -> float:
    """
    Find maximum number in a list.

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot find max of empty list")
    return max(numbers)
