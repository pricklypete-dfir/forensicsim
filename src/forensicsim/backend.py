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

import json
from pathlib import Path
from typing import Any, Optional
import time
from ccl_chromium_reader import (
    ccl_chromium_indexeddb,
    ccl_chromium_localstorage,
    ccl_chromium_sessionstorage,
)

TEAMS_DB_OBJECT_STORES = ["replychains", "conversations", "people", "buddylist"]

ENCODING = "iso-8859-1"

def parse_db(
    filepath: Path,
    blobpath: Optional[Path] = None,
    filter_db_results: Optional[bool] = True,
    raw_dump: bool = False,
    log_paths: Optional[dict] = None  # Pass log paths
) -> list[dict[str, Any]]:
    
    # Open raw access to a LevelDB and deserialize the records.
    wrapper = ccl_chromium_indexeddb.WrappedIndexDB(filepath, blobpath)
    extracted_values = []
    failed_records = []  # <-- new structure to hold records that fail
    
    # Initialize counters
    record_count = 0
    skipped_records = 0
    errors = 0

    # Open debug log (always required)
    debug_log = open(log_paths['debug_log'], "w", encoding="utf-8") if log_paths else None

    # Open raw_log **only if raw_dump=True**
    raw_log = None
    if raw_dump and log_paths:
        raw_log = open(log_paths['raw_log'], "w", encoding="utf-8")
        
    try:        
        for db_info in wrapper.database_ids:
            if db_info.dbid_no is None:
                continue

            db = wrapper[db_info.dbid_no]

            for obj_store_name in db.object_store_names:
                if obj_store_name is None:
                    continue

                # Log object stores dynamically
                debug_log.write(f"Processing object store: {obj_store_name}")

                # Allow all object stores, even unknown ones
                if obj_store_name not in TEAMS_DB_OBJECT_STORES:
                    debug_log.write(f"Unknown object store encountered: {obj_store_name}")

                obj_store = db[obj_store_name]
                records_per_object_store = 0

                for record in obj_store.iterate_records():
                    try:
                        record_count += 1
                        if debug_log:
                            debug_log.write(f"[DEBUG] Processing record {record_count}: Key={record.key.raw_key}\n")

                        # Handle empty values
                        if not hasattr(record, "value") or record.value is None:
                            skipped_records += 1
                            if debug_log:
                                debug_log.write(f"[WARNING] Skipped empty record {record_count}\n")
                            continue
                        if not hasattr(record, "origin_file") or record.origin_file is None:
                            continue

                        records_per_object_store += 1

                        # Collect raw records for JSON output
                        data_dict = {
                            "key": record.key.raw_key,
                            "value": record.value,
                            "origin_file": record.origin_file,
                            "store": obj_store_name,
                            "state": None,
                            "seq": None,
                        }
                        extracted_values.append(data_dict)

                        if debug_log:
                            debug_log.write(f"[DEBUG] Record {record_count} processed successfully.\n")
                        
                        # Write to raw_log only if raw_dump is enabled
                        if raw_dump and raw_log:
                            json.dump(record.value, raw_log, indent=4, default=str, ensure_ascii=False)
                            
                    except Exception as e:
                        errors += 1
                        failed_data_dict = {
                            "key": record.key.raw_key,
                            "origin_file": getattr(record, "origin_file", "N/A"),
                            "store": obj_store_name,
                            "error": str(e),
                            "value_fragment": repr(record.value)[:500],  # partial snippet
                        }
                        failed_records.append(failed_data_dict)
    finally:
        # Final log summary
        if log_paths:
            debug_log.write(f"[INFO] parse_db finished:\n")
            debug_log.write(f"[INFO] Total records processed: {record_count}\n")
            debug_log.write(f"[INFO] Skipped records: {skipped_records}\n")
            debug_log.write(f"[INFO] Errors encountered: {errors}\n")
            debug_log.close()
        
        # Close raw_log if it was opened
        if raw_log:
            raw_log.close()        

    # **Optional**: Dump failed_records to a separate JSON file for analysis
    if failed_records and log_paths and 'debug_log' in log_paths:
        unrecognized_path = Path(log_paths['debug_log']).parent / "unrecognized.json"
        with open(unrecognized_path, "w", encoding="utf-8") as f:
            json.dump(failed_records, f, indent=4, default=str, ensure_ascii=False)
            
    return extracted_values


def parse_localstorage(filepath: Path) -> list[dict[str, Any]]:
    local_store = ccl_chromium_localstorage.LocalStoreDb(filepath)
    extracted_values = []
    for record in local_store.iter_all_records():
        try:
            extracted_values.append(json.loads(record.value, strict=False))
        except json.decoder.JSONDecodeError:
            continue
    return extracted_values


def parse_sessionstorage(filepath: Path) -> list[dict[str, Any]]:
    session_storage = ccl_chromium_sessionstorage.SessionStoreDb(filepath)
    extracted_values = []
    for host in session_storage:
        print(host)
        # Hosts can have multiple sessions associated with them
        for session_store_values in session_storage.get_all_for_host(host).values():
            for session_store_value in session_store_values:
                # response is of type SessionStoreValue

                # Make a nice dictionary out of it
                entry = {
                    "key": host,
                    "value": session_store_value.value,
                    "guid": session_store_value.guid,
                    "leveldb_sequence_number": session_store_value.leveldb_sequence_number,
                }
                extracted_values.append(entry)
    return extracted_values


def write_results_to_json(data: list[dict[str, Any]], outputpath: Path) -> None:
    try:
        with open(outputpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, default=str, ensure_ascii=False)
    except Exception as e:
        error_log.write(f"Failed to write results.json: {str(e)}")

