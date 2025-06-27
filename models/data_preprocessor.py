import pandas as pd
import numpy as np
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class DataPreprocessor:
    """Class for handling data preprocessing operations using pandas DataFrame."""
    
    def __init__(self):
        self.cleaning_log = []
    
    @staticmethod
    def preprocess_data(file_path: str) -> Tuple[bool, str, Optional[pd.DataFrame]]:
        """
        Preprocess data from various file formats using pandas.
        
        Args:
            file_path: Path to the input file
            
        Returns:
            Tuple containing:
            - Success status (bool)
            - Status message (str)
            - Preprocessed DataFrame (optional)
        """
        try:
            file_path = Path(file_path)
            file_extension = file_path.suffix.lower()
            
            # Load data based on file type using pandas
            if file_extension in ['.csv']:
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif file_extension == '.json':
                df = pd.read_json(file_path)
            elif file_extension == '.xml':
                # Convert XML to DataFrame
                tree = ET.parse(file_path)
                root = tree.getroot()
                data = []
                for child in root:
                    data.append({elem.tag: elem.text for elem in child})
                df = pd.DataFrame(data)
            else:
                return False, f"Unsupported file format: {file_extension}", None
            
            # Basic cleaning operations
            df = DataPreprocessor._clean_dataframe(df)
            
            return True, "Data preprocessing completed successfully", df
            
        except Exception as e:
            error_msg = f"Error preprocessing file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply basic cleaning operations to the DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Make a copy to avoid modifying the original
        df = df.copy()
        
        # 1. Handle Missing Values
        # Drop columns with more than 50% missing values
        missing_threshold = 0.5
        cols_to_drop = df.columns[df.isnull().mean() > missing_threshold]
        if len(cols_to_drop) > 0:
            df = df.drop(columns=cols_to_drop)
        
        # Fill remaining missing values with appropriate defaults
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                df[col] = df[col].fillna(df[col].median())
            else:
                # Fill empty strings and None values with "null"
                df[col] = df[col].fillna("null")
                # Replace empty strings with "null"
                df[col] = df[col].replace('', "null")
                # Replace whitespace-only strings with "null"
                df[col] = df[col].apply(lambda x: "null" if isinstance(x, str) and x.strip() == '' else x)
        
        # 2. Remove Duplicates
        df = df.drop_duplicates()
        
        # 3. Reset Index
        df = df.reset_index(drop=True)
        
        return df 