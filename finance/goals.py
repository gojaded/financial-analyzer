from datetime import datetime
from . import storage


def add_goal(name: str, target: float, deadline: str | None = None,
             saved: float = 0.0) -> dict:
    goals = storage.load_goals()
    goal = {
        "id": _next_id(goals),
        "name": name,
        "target": round(target, 2),
        "saved": round(saved, 2),
        "deadline": deadline,
        "created": datetime.today().strftime("%Y-%m-%d"),
    }
    goals.append(goal)
    storage.save_goals(goals)
    return goal


def get_goals() -> list[dict]:
    return storage.load_goals()


def contribute(goal_id: int, amount: float) -> dict | None:
    goals = storage.load_goals()
    for goal in goals:
        if goal["id"] == goal_id:
            goal["saved"] = round(goal["saved"] + amount, 2)
            storage.save_goals(goals)
            return goal
    return None


def delete_goal(goal_id: int) -> bool:
    goals = storage.load_goals()
    new = [g for g in goals if g["id"] != goal_id]
    if len(new) == len(goals):
        return False
    storage.save_goals(new)
    return True


def goal_progress(goal: dict) -> float:
    """Percentage complete (0–100)."""
    if goal["target"] == 0:
        return 100.0
    return min(round(goal["saved"] / goal["target"] * 100, 1), 100.0)


def days_remaining(goal: dict) -> int | None:
    if not goal.get("deadline"):
        return None
    delta = datetime.strptime(goal["deadline"], "%Y-%m-%d") - datetime.today()
    return max(delta.days, 0)


def _next_id(goals: list[dict]) -> int:
    return max((g["id"] for g in goals), default=0) + 1
