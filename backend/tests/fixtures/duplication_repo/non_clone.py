import math

def calculate_geometric_series(start, ratio, terms):
    if terms <= 0:
        return 0.0
    current = start
    cumulative = 0.0
    for idx in range(terms):
        cumulative += current
        current *= ratio
    return cumulative
