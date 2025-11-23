# Sales Data Processing

Process CSV sales data with filtering and aggregation.

## Input Data (sales_data.csv)
- date, product, quantity, price
- 10 rows of sample data

## Task
1. Filter: quantity >= 5 AND price >= 10.0
2. Calculate total sales per product
3. Sort by total sales descending
4. Output to output.csv

## Expected Results
After filtering (quantity >= 5, price >= 10):
- Laptop: 2 rows (6 qty @ 999.99, 7 qty @ 999.99) = 12,999.87
- Mouse: 3 rows (10, 15, 20 @ 25.50) = 1,147.50
- Keyboard: 1 row (8 @ 75.00) = 600.00
- Monitor: 1 row (5 @ 299.99) = 1,499.95
