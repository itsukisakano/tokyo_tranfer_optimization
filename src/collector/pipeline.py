from pathlib import Path
import pandas as pd
from src.collector.fetch_weather import fetch_tokyo_weather
from src.collector.fetch_odpt import fetch_tokyo_train_info

RAW_DATA_DIR = Path("data/raw")
DATASET_PATH = RAW_DATA_DIR / "tokyo_transit_weather.parquet"


def run_pipeline() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    weather = fetch_tokyo_weather()
    trains = fetch_tokyo_train_info()

    if not trains:
        print("No train data fetched.")
        return

    df_new = pd.DataFrame(trains)
    for k, v in weather.items():
        df_new[k] = v

    if DATASET_PATH.exists():
        df_existing = pd.read_parquet(DATASET_PATH)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_parquet(DATASET_PATH, index=False)
    print(f"Saved {len(df_new)} new rows. Total rows in dataset: {len(df_combined)}")


if __name__ == "__main__":
    run_pipeline()
