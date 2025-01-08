"""
MIT License

Copyright (c) 2021 Alexander Bilz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
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

from pathlib import Path
from typing import Optional
import os
import click
from forensicsim.backend import write_results_to_json
from forensicsim.consts import DUMP_HEADER
from forensicsim.parser import parse_db



def setup_logs(output_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    return {
        "debug_log": Path(output_dir) / "debug.log",
        "raw_log": Path(output_dir) / "raw_data.json",
        "error_log": Path(output_dir) / "error.log",
    }


def process_level_db(
    input_path: Path,
    output_path: Path,
    blob_path: Optional[Path] = None,
    raw_dump: bool = False,
) -> None:
    # Setup logs
    logs = setup_logs(output_path.parent)

    # Initialize log files
    with open(logs["debug_log"], "w") as debug_log, \
         open(logs["raw_log"], "w") as raw_log, \
         open(logs["error_log"], "w") as error_log:

        try:
            # Parse the database
            extracted_values = parse_db(
                input_path,
                blob_path,
                filter_db_results=False,
                raw_dump=raw_dump,
            )

            # Handle raw_dump case
            if raw_dump:
                # Write raw data to raw_log instead of terminal
                for record in extracted_values:
                    raw_log.write(f"{record}\n")
            else:
                # Write processed results to the output JSON file
                write_results_to_json(extracted_values, output_path)

        except Exception as e:
            # Capture errors in the error log
            error_log.write(f"ERROR: {str(e)}\n")

        finally:
            debug_log.write("Processing complete.\n")


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
