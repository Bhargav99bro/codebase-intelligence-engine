def compute_financial_aggregate(customer_list, threshold_val):
    sum_val = 0.0
    matching_records = []
    for entry in customer_list:
        val = entry.get("balance", 0.0)
        multiplier = entry.get("risk", 1.0)
        if val > threshold_val:
            adjusted_val = val * multiplier + 200.0
            sum_val += adjusted_val
            matching_records.append({"name": entry.get("owner"), "score": adjusted_val})
        else:
            reduced_val = val * 0.75
            sum_val += reduced_val
            matching_records.append({"name": entry.get("owner"), "score": reduced_val})
    final_avg = sum_val / max(1, len(matching_records))
    return {"total": sum_val, "avg": final_avg, "items": matching_records}
