import os
import json
import logging
from typing import List, Dict, Any
from yuantus.seeder.base import BaseSeeder

class BaseFileSeeder(BaseSeeder):
    """
    Base class for seeding data from local files (JSON/CSV).
    Expects data files to be in src/yuantus/seeder/data/
    """

    @property
    def data_dir(self):
        # Resolve absolute path to 'data' directory relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'data')

    def load_json(self, filename: str) -> List[Dict[str, Any]]:
        """Load data from a JSON file in the data directory."""
        file_path = os.path.join(self.data_dir, filename)
        if not os.path.exists(file_path):
            self.log(f"Warning: Data file not found at {file_path}")
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.log(f"Loaded {len(data)} records from {filename}")
                return data
        except Exception as e:
            self.log(f"Error reading {filename}: {e}")
            return []
