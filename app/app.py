# app/search_service.py
import pandas as pd
from collections import defaultdict


def normalize_address(city: str, street: str, housenumber: str) -> str:
    s = f"{city} {street} {housenumber}".strip().lower()
    return " ".join(s.split())


def trigrams(text: str) -> set[str]:
    text = f"  {text}  "
    return {text[i:i+3] for i in range(len(text) - 2)}


def build_index(df: pd.DataFrame):
    """
    Возвращает:
        df_reset      — df c индексом 0..N-1
        full_list     — список нормализованных строк
        trigram_sets  — список множеств триграмм (по row_id)
        inverted      — dict: trigram -> set(row_id)
    """
    df_reset = df.reset_index(drop=True)
    full_list = []
    trigram_sets = []
    inverted = defaultdict(set)

    for row_id, row in df_reset.iterrows():
        full = normalize_address(row["city"], row["street"], row["housenumber"])
        full_list.append(full)

        tset = trigrams(full)
        trigram_sets.append(tset)

        for tg in tset:
            inverted[tg].add(row_id)

    return df_reset, full_list, trigram_sets, inverted


def levenshtein_distance(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()
    la, lb = len(a), len(b)

    if la == 0:
        return lb
    if lb == 0:
        return la

    dp = [[0] * (lb + 1) for _ in range(la + 1)]

    for i in range(la + 1):
        dp[i][0] = i
    for j in range(lb + 1):
        dp[0][j] = j

    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # удаление
                dp[i][j - 1] + 1,      # вставка
                dp[i - 1][j - 1] + cost,  # замена
            )

    return dp[la][lb]


def levenshtein_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    dist = levenshtein_distance(a, b)
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - dist / max_len


def metrics(A_pred: str, A_true: str) -> float:
    """
    score = 1 - L(A_pred, A_true) / max(len(A_pred), len(A_true))
    """
    A_pred = A_pred or ""
    A_true = A_true or ""

    if not A_pred and not A_true:
        return 1.0

    dist = levenshtein_distance(A_pred, A_true)
    denom = max(len(A_pred), len(A_true))
    if denom == 0:
        return 1.0

    return 1.0 - dist / denom


def search_lev(
    query: str,
    df,
    full_list,
    trigram_sets,
    inverted,
    top_k: int = 1,
    max_candidates: int = 300,
    min_common_trigrams: int = 2,
    min_common_ratio: float = 0.1,
    min_lev_sim: float = 0.3,
):
    """
    Возвращает dict:
    {
        "searched_address": <исходный запрос>,
        "objects": [
            {
                "locality": <city>,
                "street": <street>,
                "number": <housenumber>,
                "lon": <lon>,
                "lat": <lat>,
                "score": <similarity>
            },
            ...
        ]
    }
    """

    q_norm = " ".join(query.strip().lower().split())
    q_trg = trigrams(q_norm)
    if not q_trg:
        return {
            "searched_address": query,
            "objects": []
        }

    candidate_scores = defaultdict(int)
    for tg in q_trg:
        if tg in inverted:
            for row_id in inverted[tg]:
                candidate_scores[row_id] += 1

    q_trg_count = len(q_trg)
    filtered = []
    for row_id, common in candidate_scores.items():
        if common < min_common_trigrams:
            continue
        if common / q_trg_count < min_common_ratio:
            continue
        filtered.append((row_id, common))

    if not filtered:
        return {
            "searched_address": query,
            "objects": []
        }

    filtered.sort(key=lambda x: x[1], reverse=True)
    top_candidates = [row_id for row_id, _ in filtered[:max_candidates]]

    scored = []
    for row_id in top_candidates:
        addr = full_list[row_id]
        sim = levenshtein_similarity(q_norm, addr)
        if sim >= min_lev_sim:
            scored.append((row_id, sim))

    if not scored:
        return {
            "searched_address": query,
            "objects": []
        }

    scored.sort(key=lambda x: x[1], reverse=True)
    top_scored = scored[:top_k]

    objects = []
    for row_id, sim in top_scored:
        row = df.loc[row_id]
        # тут используем твою метрику поверх найденного результата:
        pred_str = query
        true_str = f"{row.get('street', '')} {row.get('housenumber', '')}"
        score = metrics(pred_str, true_str)

        objects.append({
            "locality": row.get("city", None),
            "street": row.get("street", None),
            "number": row.get("housenumber", None),
            "lon": float(row.get("lon", 0)) if row.get("lon", None) is not None else None,
            "lat": float(row.get("lat", 0)) if row.get("lat", None) is not None else None,
            "score": float(score),
        })

    return {
        "searched_address": query,
        "objects": objects
    }