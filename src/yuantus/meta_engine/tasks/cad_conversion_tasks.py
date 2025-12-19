"""
CAD Conversion Tasks for Asynchronous Job Processing.
"""

import time
import logging
from typing import Dict, Any
import uuid  # Added import for uuid

logger = logging.getLogger(__name__)


def perform_cad_conversion(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates a CAD file conversion process.

    Args:
        payload: A dictionary containing task parameters, e.g.,
                 {'input_file_path': 'path/to/model.step', 'output_format': 'gltf', 'job_id': '...'}.

    Returns:
        A dictionary with conversion results, e.g.,
        {'output_file_path': 'path/to/model.gltf', 'status': 'success', 'duration_seconds': 10}.
    """
    job_id = payload.get("job_id", "unknown")
    input_file_path = payload.get("input_file_path")
    output_format = payload.get("output_format", "gltf")

    if not input_file_path:
        raise ValueError("Missing 'input_file_path' in CAD conversion payload.")

    logger.info(
        f"[{job_id}] Starting CAD conversion for '{input_file_path}' to '{output_format}'..."
    )
    start_time = time.time()

    # --- Simulate various stages of conversion ---
    logger.info(f"[{job_id}] Stage 1: Downloading source file '{input_file_path}'...")
    time.sleep(1)  # Simulate download time

    # Simulate a potential failure based on input_file_path
    if "fail" in input_file_path.lower():
        logger.error(
            f"[{job_id}] Simulated failure during conversion setup for '{input_file_path}'."
        )
        raise RuntimeError("Simulated CAD conversion setup failure!")

    logger.info(
        f"[{job_id}] Stage 2: Performing actual conversion to '{output_format}'..."
    )
    conversion_time = 2 + (
        len(input_file_path) % 3
    )  # Simulate variable conversion time
    time.sleep(conversion_time)  # Simulate conversion time

    logger.info(f"[{job_id}] Stage 3: Uploading converted file...")
    output_file_path = f"/converted_output/{uuid.uuid4().hex}.{output_format}"
    time.sleep(0.5)  # Simulate upload time

    end_time = time.time()
    duration = round(end_time - start_time, 2)

    logger.info(
        f"[{job_id}] CAD conversion completed successfully in {duration} seconds. Output: '{output_file_path}'"
    )

    # Simulate attribute extraction based on file name
    extracted_attributes = {}
    if "part_a.dwg" in input_file_path:
        extracted_attributes = {
            "part_number": "PA-001",
            "description": "Assembly Part A",
            "material": "Steel",
            "revision": "A",
        }
    elif "part_b.dwg" in input_file_path:
        extracted_attributes = {
            "part_number": "PB-002",
            "description": "Component Part B",
            "material": "Aluminum",
            "weight": 1.5,
        }

    return {
        "output_file_path": output_file_path,
        "status": "success",
        "duration_seconds": duration,
        "input_file_path": input_file_path,
        "output_format": output_format,
        "extracted_attributes": extracted_attributes,
    }
