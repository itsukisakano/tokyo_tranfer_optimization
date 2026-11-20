import os
import re
from datetime import datetime, timezone, timedelta
import requests

JST = timezone(timedelta(hours=9))

WEATHER_KEYWORDS = [
    "大雨", "強風", "台風", "大雪", "雪", "落雷", "雷", "濃霧", "霧",
    "飛来物", "倒木", "冠水", "浸水", "気象", "悪天候", "暴風", "突風",
]

NOISE_KEYWORDS = [
    "人身事故", "お客様救護", "急病人", "救護", "車両点検", "信号確認",
    "信号トラブル", "踏切", "動物", "シカ", "イノシシ", "荷物", "ドア点検",
    "線路内立入", "混雑", "異音", "ブレーキ", "安全確認",
]


def classify_delay_cause(status: str, text: str) -> str:
    """Classify railway status into normal, weather, noise (non-weather), or unknown."""
    if not text or "平常" in status or "平常" in text:
        return "normal"
    if any(kw in text for kw in NOISE_KEYWORDS):
        return "noise"
    if any(kw in text for kw in WEATHER_KEYWORDS):
        return "weather"
    return "unknown"


def extract_delay_minutes(text: str) -> int:
    """Extract estimated delay minutes from Japanese announcement text."""
    if not text:
        return 0
    if "運転見合わせ" in text or "運休" in text:
        return 999  # Sentinel value for service suspension
    match = re.search(r"(\d+)\s*分", text)
    return int(match.group(1)) if match else 0


def fetch_tokyo_train_info(access_token: str | None = None) -> list[dict]:
    """Fetch real-time train status from ODPT API for JR-East, TokyoMetro, and Toei."""
    token = access_token or os.environ.get("ODPT_ACCESS_TOKEN")
    if not token:
        raise ValueError("ODPT_ACCESS_TOKEN is not set.")

    operators = [
        "odpt.Operator:JR-East",
        "odpt.Operator:TokyoMetro",
        "odpt.Operator:Toei",
    ]
    url = "https://api.odpt.org/api/v4/odpt:TrainInformation"
    fetched_at = datetime.now(JST).isoformat()
    records = []

    for op in operators:
        params = {"odpt:operator": op, "acl:consumerKey": token}
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        for item in resp.json():
            status_obj = item.get("odpt:trainInformationStatus", {})
            text_obj = item.get("odpt:trainInformationText", {})
            status_ja = status_obj.get("ja", "平常運転") if isinstance(status_obj, dict) else str(status_obj)
            text_ja = text_obj.get("ja", "") if isinstance(text_obj, dict) else str(text_obj)

            cause = classify_delay_cause(status_ja, text_ja)
            delay_min = extract_delay_minutes(text_ja)

            records.append({
                "fetched_at_jst": fetched_at,
                "railway_id": item.get("odpt:railway"),
                "operator": op.split(":")[-1],
                "status_ja": status_ja,
                "text_ja": text_ja,
                "cause_category": cause,
                "estimated_delay_min": delay_min,
                "is_delayed_weather": 1 if (cause == "weather" and delay_min > 0) else 0,
            })

    return records
