# Bug Fix Task

Fix 3 bugs in calculator.py to make all tests pass.

## Bugs to Find
1. **power()** - Off-by-one error in loop
2. **is_even()** - Logic error in condition
3. **average()** - Doesn't handle empty list (should raise ValueError)

## Running Tests
```bash
python -m pytest -v
```

## Expected Behavior
- power(2, 3) should return 8 (not 4)
- is_even(2) should return True (not False)
- average([]) should raise ValueError with message "Cannot calculate average"
