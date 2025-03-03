import os
import time
from pathlib import Path
from typing import Optional
import traceback
import click
import logging
from forensicsim.backend import parse_db, write_results_to_json
from forensicsim.consts import DUMP_HEADER

RAW_DUMP_ENABLED = False

def setup_logs(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    debug_log = Path(output_dir) / "debug.log"
    error_log = Path(output_dir) / "error.log"

    # Configure logging to file only
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(debug_log, mode="a")],  # File-only logging
    )
    
    error_logger = logging.getLogger("error_logger")
    error_handler = logging.FileHandler(error_log, mode="w")
    error_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    error_logger.addHandler(error_handler)
    
    return {
        "debug_log": debug_log,
        "error_log": error_log,
        "error_logger": error_logger,
    }


def process_level_db(
    input_path: Path,
    output_path: Path,
    blob_path: Optional[Path] = None,
    raw_dump: bool = False,
) -> None:
    global RAW_DUMP_ENABLED #use the global variable
    RAW_DUMP_ENABLED = raw_dump
    
    logs = setup_logs(output_path.parent)
    error_logger = logs["error_logger"]

    start_time = time.time()
    skipped_records = 0
    empty_stores = 0

    # Initialize extracted_values to avoid UnboundLocalError
    extracted_values = []
        
    try:
        logging.info("Starting LevelDB processing.")
        logging.info(f"Input path: {input_path}")
        logging.info(f"Output path: {output_path}")
        logging.info(f"Blob path: {blob_path if blob_path else 'None'}")
        logging.info(f"Raw dump mode: {raw_dump}")

        # Open raw_log only if RAW_DUMP_ENABLED is True
        raw_log = None
        if RAW_DUMP_ENABLED:
            raw_log = open(Path(output_path.parent) / "raw_data.json", "w")
            
        # Parse database
        extracted_values = parse_db(
            input_path,
            blob_path,
            filter_db_results=False,
            raw_dump=raw_dump,
            log_paths=logs,
        )

        # Write raw dump if enabled
        if RAW_DUMP_ENABLED and raw_log:
            for record in extracted_values:
                raw_log.write(f"{record}\n")
            logging.info(f"Raw records written to raw_data.json.")
            raw_log.close()  # Close the raw log properly

        else:
            # Write structured JSON if not raw_dump
            write_results_to_json(extracted_values, output_path)
            logging.info(f"Processed data written to {output_path}.")
            
    except Exception as e:
        error_logger.error(traceback.format_exc())

    finally:
        end_time = time.time()
        duration = end_time - start_time
        logging.info(f"Processing completed in {duration:.2f} seconds.")
        logging.info(f"Parsed records count: {len(extracted_values)}")
        logging.info(f"Skipped records: {skipped_records}")
        logging.info(f"Empty object stores: {empty_stores}")


@click.command()
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True, readable=True, writable=False, dir_okay=True, path_type=Path),
    required=True,
    help="File path to the .leveldb folder of the IndexedDB.",
)
@click.option(
    "-o",
    "--outputpath",
    type=click.Path(writable=True, path_type=Path),
    required=True,
    help="File path to the processed output.",
)
@click.option(
    "-b",
    "--blobpath",
    type=click.Path(exists=True, readable=True, writable=False, dir_okay=True, path_type=Path),
    required=False,
    help="File path to the .blob folder of the IndexedDB.",
)
@click.option(
    "--raw-dump",
    is_flag=True,
    default=False,
    help="Dump raw records without processing into structured JSON.",
)

def process_cmd(
    filepath: Path, outputpath: Path, blobpath: Optional[Path] = None, raw_dump: bool = False
) -> None:
    click.echo(DUMP_HEADER)
    process_level_db(filepath, outputpath, blobpath, raw_dump)


if __name__ == "__main__":
    process_cmd()
