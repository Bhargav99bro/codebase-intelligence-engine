# Alternative sensor processor with different documentation

def process_sensor_records(records, threshold):
    # Process each record carefully
    results = []
    for item in records:
        val = item.get("reading", 0.0)
        if val > threshold:
            scaled = val * 1.5 + 10.0
            results.append({"id": item.get("id"), "scaled": scaled})
        else:
            scaled = val * 0.8
            results.append({"id": item.get("id"), "scaled": scaled})
    return results
