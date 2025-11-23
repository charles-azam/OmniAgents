"""Tests for the codebase."""
import pytest
from src.main import calculate_total, process_order
from src.utils import get_average, format_total


def test_calculate_total():
    """Test calculate_total function."""
    assert calculate_total([1.0, 2.0, 3.0]) == 6.0
    assert calculate_total([]) == 0.0


def test_process_order():
    """Test process_order function."""
    result = process_order([10.0, 20.0])
    assert result["subtotal"] == 30.0
    assert result["tax"] == 3.0
    assert result["total"] == 33.0


def test_get_average():
    """Test get_average function."""
    assert get_average([1.0, 2.0, 3.0]) == 2.0
    assert get_average([]) == 0.0


def test_format_total():
    """Test format_total function."""
    assert format_total([10.5, 20.3]) == "$30.80"
