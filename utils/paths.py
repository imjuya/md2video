"""Path utilities for md2video package."""
from pathlib import Path
from datetime import date
import os

def get_output_dir(subdir: str = "") -> Path:
    """Get standardized output directory path.
    
    Args:
        subdir: Subdirectory name (e.g. 'images', 'videos')
    
    Returns:
        Path object to output directory
    """
    today = date.today().strftime("%Y%m%d")
    output_path = Path("output") / today / subdir
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path

def get_relative_path(file_path: str) -> Path:
    """Convert file path to be relative to package root.
    
    Args:
        file_path: Input file path
        
    Returns:
        Relative Path object
    """
    return Path(os.path.relpath(file_path, start=Path(__file__).parent.parent))
