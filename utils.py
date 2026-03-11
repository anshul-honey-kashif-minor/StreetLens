import json
import logging
import pandas as pd
from pathlib import Path

def setup_logger():
    """Sets up a basic logger for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logger()

def save_outputs(data_list, output_dir):
    """Saves the extracted data to JSON and CSV formats."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    if not data_list:
        logger.warning("No data to save.")
        return

    # Save JSON
    json_path = out_path / "results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, indent=2)
    logger.info(f"Saved JSON output to {json_path}")

    # Save CSV
    csv_path = out_path / "results.csv"
    df = pd.DataFrame(data_list)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved CSV output to {csv_path}")