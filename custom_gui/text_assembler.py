from typing import List, Dict, Any

def assemble_text(lines: List[Dict[str, Any]]) -> str:
    """
    Assemble a single string from a list of OCR line dictionaries.
    Maintains the exact order of the input list.
    
    Args:
        lines: List of dictionaries, each containing a "text" key.
        
    Returns:
        A single string with the text of each line joined by a newline character.
    """
    return "\n".join(line.get("text", "") for line in lines)
