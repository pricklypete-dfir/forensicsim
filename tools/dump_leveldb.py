"""
MIT License

Copyright (c) 2021 Alexander Bilz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import time
from pathlib import Path
from typing import Optional
import traceback
import click
import logging
from forensicsim.backend import parse_db, write_results_to_json
from forensicsim.consts import DUMP_HEADER


def setup_logs(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    debug_log = Path(output_dir) / "debug.log"
    raw_log = Path(output_dir) / "raw_data.json"
    error_log = Path(output_dir) / "error.log"
    
    logging.basicConfig(
        level=logging.DEBUG,  # Log all levels (DEBUG, INFO, WARNING, ERROR)
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(debug_log, mode="a"),  # Write logs to debug.log
            logging.StreamHandler()  # Keep logs visible in terminal
        ],
    )
        
    # Error log specifically for exceptions
    error_logger = logging.getLogger("error_logger")
    error_handler = logging.FileHandler(error_log, mode="w")
    error_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    error_logger.addHandler(error_handler)
    
    return {
        "debug_log": debug_log,
        "raw_log": raw_log,
        "error_log": error_log,
        "error_logger": error_logger,
    }


def process_level_db(
    input_path: Path,
    output_path: Path,
    blob_path: Optional[Path] = None,
    raw_dump: bool = False,
) -> None:
    # Setup logs
    logs = setup_logs(output_path.parent)
    error_logger = logs["error_logger"]
    
    # Initialize log files
    with open(logs["raw_log"], "w") as raw_log:
        start_time = time.time()
        try:
            logging.info(f"Starting LevelDB processing.\n")
            logging.info(f"Input path: {input_path}\n")
            logging.info(f"Output path: {output_path}\n")
            logging.info(f"Blob path: {blob_path if blob_path else 'None'}\n")
            logging.info(f"Raw dump mode: {raw_dump}\n")

            # Parse the database
            extracted_values = parse_db(
                input_path,
                blob_path,
                filter_db_results=False,
                raw_dump=raw_dump,
            )

            logging.info(f"Database parsed successfully.\n")
            logging.info(f"Number of records extracted: {len(extracted_values)}\n")
            
            logging.info(f"Skipped records: {skipped_records}")
            logging.info(f"Empty object stores: {empty_stores}")

            # Handle raw_dump case
            if raw_dump:
                for record in extracted_values:
                    raw_log.write(f"{record}\n")
                logging.info(f"Raw records written to raw_data.json.\n")
            else:
                # Write processed results to the output JSON file
                write_results_to_json(extracted_values, output_path)
                logging.info(f"INFO: Processed data written to {output_path}.\n")

        except Exception as e:
            #error_logger.error(f"ERROR: {str(e)}\n")
            error_logger.error(traceback.format_exc())

        finally:
            end_time = time.time()
            duration = end_time - start_time
            logging.info(f"INFO: Processing completed.\n")
            logging.info(f"Total time taken: {duration:.2f} seconds.\n")


@click.command()
@click.option(
    "-f",
    "--filepath",
    type=click.Path(
        exists=True, readable=True, writable=False, dir_okay=True, path_type=Path
    ),
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
    type=click.Path(
        exists=True, readable=True, writable=False, dir_okay=True, path_type=Path
    ),
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
