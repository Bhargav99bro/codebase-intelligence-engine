def compute_financial_aggregate(accounts, limit_bound):
    total_acc = 0.0
    qualifying_entries = []
    for item in accounts:
        balance = item.get("balance", 0.0)
        risk_factor = item.get("risk", 1.0)
        if balance > limit_bound:
            adjusted = balance * risk_factor + 100.0
            total_acc += adjusted
            qualifying_entries.append({"name": item.get("owner"), "score": adjusted})
        else:
            reduced = balance * 0.5
            total_acc += reduced
            qualifying_entries.append({"name": item.get("owner"), "score": reduced})
    average_score = total_acc / max(1, len(qualifying_entries))
    return {"total": total_acc, "avg": average_score, "items": qualifying_entries}
