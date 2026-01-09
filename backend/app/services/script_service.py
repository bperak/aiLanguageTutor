"""
Service layer for Script learning feature.

Handles loading script datasets, validating answers, and computing progress.
"""

import json
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class ScriptService:
    """Service for managing script items and practice validation."""
    
    def __init__(self):
        """Initialize the service and load script dataset."""
        self._items: Dict[str, Dict] = {}
        self._items_by_type: Dict[str, List[Dict]] = defaultdict(list)
        self._load_dataset()
    
    def _load_dataset(self) -> None:
        """
        Load script dataset from JSON file.
        
        Raises:
            FileNotFoundError: If dataset file is missing.
            ValueError: If dataset is invalid.
        """
        # Determine dataset path
        if hasattr(settings, 'SCRIPT_DATA_PATH') and settings.SCRIPT_DATA_PATH:
            dataset_path = Path(settings.SCRIPT_DATA_PATH)
        else:
            # Default: relative to this file
            dataset_path = Path(__file__).parent.parent / "resources" / "script" / "ja_kana.json"
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Script dataset not found at {dataset_path}")
        
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
            
            # Validate and index items
            for item in items:
                if not all(key in item for key in ['id', 'script_type', 'kana', 'romaji']):
                    raise ValueError(f"Invalid item structure: missing required fields")
                
                item_id = item['id']
                script_type = item['script_type']
                
                if item_id in self._items:
                    logger.warning("Duplicate item ID", item_id=item_id)
                    continue
                
                # Normalize fields
                item['romaji_aliases'] = item.get('romaji_aliases', [])
                item['tags'] = item.get('tags', [])
                item['group'] = item.get('group')
                
                self._items[item_id] = item
                self._items_by_type[script_type].append(item)
            
            logger.info("Script dataset loaded", total_items=len(self._items), 
                       hiragana=len(self._items_by_type.get('hiragana', [])),
                       katakana=len(self._items_by_type.get('katakana', [])))
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in dataset: {e}")
        except Exception as e:
            logger.error("Failed to load script dataset", error=str(e))
            raise
    
    def get_items(
        self,
        script_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get script items with optional filtering.
        
        Args:
            script_type: Filter by script type (hiragana/katakana)
            tags: Filter by tags (must match any)
            search: Search in kana or romaji
            limit: Maximum results (1-100)
            offset: Number to skip
        
        Returns:
            List of script item dictionaries
        """
        # Start with all items or filtered by type
        if script_type:
            candidates = self._items_by_type.get(script_type, [])
        else:
            candidates = list(self._items.values())
        
        # Filter by tags
        if tags:
            tag_set = set(tags)
            candidates = [
                item for item in candidates
                if tag_set.intersection(set(item.get('tags', [])))
            ]
        
        # Filter by search
        if search:
            search_lower = search.lower().strip()
            candidates = [
                item for item in candidates
                if (search_lower in item['kana'].lower() or
                    search_lower in item['romaji'].lower() or
                    any(search_lower in alias.lower() for alias in item.get('romaji_aliases', [])))
            ]
        
        # Apply pagination
        return candidates[offset:offset + limit]
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """
        Get a script item by ID.
        
        Args:
            item_id: Script item identifier
        
        Returns:
            Item dictionary or None if not found
        """
        return self._items.get(item_id)
    
    def normalize_romaji(self, text: str) -> str:
        """
        Normalize romaji input for comparison.
        
        Args:
            text: Raw user input
        
        Returns:
            Normalized romaji string
        """
        # Unicode normalize, strip, lowercase
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.strip().lower()
        # Collapse spaces and hyphens
        normalized = normalized.replace(' ', '').replace('-', '')
        return normalized
    
    def normalize_kana(self, text: str) -> str:
        """
        Normalize kana input for comparison.
        
        Args:
            text: Raw user input
        
        Returns:
            Normalized kana string
        """
        # Unicode normalize and strip
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.strip()
        return normalized
    
    def check_answer(
        self,
        item_id: str,
        mode: str,
        user_answer: str,
        choices: Optional[List[str]] = None
    ) -> Dict:
        """
        Check if user answer is correct for a script item.
        
        Args:
            item_id: Script item ID
            mode: Practice mode (kana_to_romaji, romaji_to_kana, mcq)
            user_answer: User's answer
            choices: Multiple choice options (for mcq)
        
        Returns:
            Dictionary with is_correct, expected_answer, accepted_answers, feedback
        
        Raises:
            ValueError: If item not found or invalid mode
        """
        item = self.get_item_by_id(item_id)
        if not item:
            raise ValueError(f"Script item not found: {item_id}")
        
        if mode not in ['kana_to_romaji', 'romaji_to_kana', 'mcq']:
            raise ValueError(f"Invalid practice mode: {mode}")
        
        # Build accepted answers
        accepted_answers = [item['romaji']]
        accepted_answers.extend(item.get('romaji_aliases', []))
        
        is_correct = False
        expected_answer = ""
        feedback = ""
        
        if mode == 'kana_to_romaji':
            # User should type romaji, we show kana
            expected_answer = item['romaji']
            normalized_user = self.normalize_romaji(user_answer)
            normalized_expected = [self.normalize_romaji(a) for a in accepted_answers]
            is_correct = normalized_user in normalized_expected
            feedback = "Correct! Well done." if is_correct else f"Expected: {expected_answer}"
        
        elif mode == 'romaji_to_kana':
            # User should type kana, we show romaji
            expected_answer = item['kana']
            normalized_user = self.normalize_kana(user_answer)
            normalized_expected = self.normalize_kana(item['kana'])
            is_correct = normalized_user == normalized_expected
            feedback = "Correct! Well done." if is_correct else f"Expected: {expected_answer}"
        
        elif mode == 'mcq':
            # Multiple choice: user_answer should match one of the accepted romaji
            if choices:
                # Validate that expected is in choices
                if item['romaji'] not in choices:
                    raise ValueError("Expected answer must be in choices list")
            
            expected_answer = item['romaji']
            normalized_user = self.normalize_romaji(user_answer)
            normalized_expected = [self.normalize_romaji(a) for a in accepted_answers]
            is_correct = normalized_user in normalized_expected
            feedback = "Correct! Well done." if is_correct else f"Expected: {expected_answer}"
        
        return {
            'is_correct': is_correct,
            'expected_answer': expected_answer,
            'accepted_answers': accepted_answers,
            'feedback': feedback
        }


# Global service instance
_script_service: Optional[ScriptService] = None


def get_script_service() -> ScriptService:
    """Get or create the global script service instance."""
    global _script_service
    if _script_service is None:
        _script_service = ScriptService()
    return _script_service

