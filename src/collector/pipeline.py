from pathlib import Path
import pandas as pd
from src.collector.fetch_weather import fetch_tokyo_weather
from src.collector.fetch_odpt import fetch_tokyo_train_info

MASTER_PATH = Path("data/master/railways_master.csv")
OUTPUT_PATH = Path("data/raw/transit_weather_log.parquet")


def run_pipeline() -> None:
    weather = fetch_tokyo_weather()
    trains = fetch_tokyo_train_info()

    if not trains:
        print("No train records returned from ODPT.")
        return

    df_trains = pd.DataFrame(trains)
    df_master = pd.read_csv(MASTER_PATH)

    # Filter to target core railways and attach physical structure features
    df_merged = pd.merge(df_trains, df_master, on=["railway_id", "operator"], how="inner")

    # Attach current Tokyo weather columns
    for key, val in weather.items():
        if key != "fetched_at_jst":
            df_merged[key] = val

    # Apply double-check noise filter: clear weather (0mm rain & <6m/s wind) cannot be weather-induced
    clear_weather_mask = (df_merged["precipitation_mm"] == 0) & (df_merged["wind_speed_ms"] < 6.0)
    df_merged.loc[clear_weather_mask & (df_merged["cause_category"] == "unknown"), "cause_category"] = "noise"

    if OUTPUT_PATH.exists():
        df_existing = pd.read_parquet(OUTPUT_PATH)
        df_combined = pd.concat([df_existing, df_merged], ignore_index=True)
    else:
        df_combined = df_merged

    df_combined.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved {len(df_merged)} new rows. Total rows in dataset: {len(df_combined)}")


if __name__ == "__main__":
    run_pipeline()
