from __future__ import annotations


def overlap_score(left: list[str], right: list[str]) -> tuple[float, list[str], list[str]]:
    left_set = {item.lower() for item in left}
    right_set = {item.lower() for item in right}
    if not right_set:
        return 1.0, [], []

    matched = sorted(left_set & right_set)
    missing = sorted(right_set - left_set)
    score = len(matched) / len(right_set)
    return score, matched, missing
