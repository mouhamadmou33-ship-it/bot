import json
import os

def load_stats():
    if not os.path.exists("stats.json"):
        return {"total": 0, "users": {}}
    with open("stats.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_stats(stats):
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False)

def increment_stats(user_id):
    stats = load_stats()
    stats["total"] += 1
    user_id = str(user_id)
    if user_id not in stats["users"]:
        stats["users"][user_id] = 0
    stats["users"][user_id] += 1
    save_stats(stats)

def get_user_stats(user_id):
    stats = load_stats()
    return stats["users"].get(str(user_id), 0)

def get_total_stats():
    stats = load_stats()
    return stats["total"]
