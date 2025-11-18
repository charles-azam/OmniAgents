"""Tests for calculator module."""
import pytest
from calculator import (
    add, subtract, multiply, divide, power,
    is_even, average, factorial
)


def test_add():
    """Test addition."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    """Test subtraction."""
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5


def test_multiply():
    """Test multiplication."""
    assert multiply(3, 4) == 12
    assert multiply(0, 5) == 0


def test_divide():
    """Test division."""
    assert divide(10, 2) == 5
    assert divide(7, 2) == 3.5

    with pytest.raises(ValueError):
        divide(5, 0)


def test_power():
    """Test power function - THIS WILL FAIL DUE TO BUG."""
    assert power(2, 3) == 8  # 2^3 = 8
    assert power(5, 2) == 25  # 5^2 = 25
    assert power(3, 0) == 1  # 3^0 = 1
    assert power(10, 1) == 10  # 10^1 = 10


def test_is_even():
    """Test is_even function - THIS WILL FAIL DUE TO BUG."""
    assert is_even(2) == True
    assert is_even(4) == True
    assert is_even(0) == True
    assert is_even(1) == False
    assert is_even(3) == False
    assert is_even(7) == False


def test_average():
    """Test average function - THIS WILL FAIL DUE TO BUG."""
    assert average([1, 2, 3, 4, 5]) == 3.0
    assert average([10, 20]) == 15.0
    assert average([5]) == 5.0

    # Should handle empty list gracefully
    with pytest.raises(ValueError, match="Cannot calculate average"):
        average([])


def test_factorial():
    """Test factorial (this should pass)."""
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    assert factorial(3) == 6

    with pytest.raises(ValueError):
        factorial(-1)
