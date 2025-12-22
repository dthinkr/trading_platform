from datetime import datetime
from pathlib import Path
import json
from typing import Dict, Any

class ParameterLogger:
    def __init__(self, log_dir: str = "logs/parameters"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.log_dir / "parameter_history.json"
        
        # Initialize or load existing history
        self.parameter_history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load existing parameter history or create new if doesn't exist"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_history(self):
        """Save the parameter history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.parameter_history, f, indent=2)
    
    def log_parameter_state(self, 
                           current_state: Dict[str, Any],
                           source: str = "system"):
        """
        Log the complete parameter state at the current time.
        
        Args:
            current_state: Dictionary containing all current parameter values
            source: Source of the change (e.g., "user", "system", etc.)
        """
        now = datetime.now()
        timestamp = now.isoformat()
        unix_timestamp = int(now.timestamp())
        
        # Create a new entry with timestamp as key
        self.parameter_history[timestamp] = {
            "parameters": current_state,
            "unix_timestamp": unix_timestamp,
            "source": source
        }
        
        # Save to file
        self._save_history()
    
    def get_parameter_history(self) -> Dict:
        """Get the complete parameter history"""
        return self.parameter_history
    
    def get_latest_state(self) -> Dict:
        """Get the most recent parameter state"""
        if not self.parameter_history:
            return {}
        
        latest_timestamp = max(self.parameter_history.keys())
        return self.parameter_history[latest_timestamp]["parameters"]
    
    def log_market_start(self,
                         market_id: str,
                         participants: list,
                         session_id: str = None,
                         treatment_name: str = None,
                         treatment_index: int = None,
                         parameters: Dict[str, Any] = None):
        """
        Log when a market starts with its participants and treatment.
        
        This allows tracking which participants were in which market,
        enabling session reconstruction by finding markets with the same session_id.
        
        Args:
            market_id: Unique market identifier (e.g., SESSION_xxx_MARKET_0)
            participants: List of participant usernames
            session_id: Persistent session identifier that groups markets together
            treatment_name: Name of the treatment applied (from treatments.yaml)
            treatment_index: Index of the treatment (0-based)
            parameters: Optional snapshot of parameters used for this market
        """
        now = datetime.now()
        timestamp = now.isoformat()
        unix_timestamp = int(now.timestamp())
        
        entry = {
            "source": "market_start",
            "market_id": market_id,
            "participants": participants,
            "unix_timestamp": unix_timestamp
        }
        
        if session_id:
            entry["session_id"] = session_id
        if treatment_name:
            entry["treatment_name"] = treatment_name
        if treatment_index is not None:
            entry["treatment_index"] = treatment_index
        if parameters:
            entry["parameters"] = parameters
        
        self.parameter_history[timestamp] = entry
        self._save_history()
