"""
User profile module for GANGLIA.

This module provides functionality for managing user profiles
including user information, preferences, and metadata.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class UserProfile:
    """
    Represents a user profile in the GANGLIA system.

    Contains user identity information and preferences that persist
    across sessions, as well as metadata for system use.
    """

    # User identity information
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    display_name: Optional[str] = None

    # Profile storage for images/other media
    photo_path: Optional[str] = None

    # Biometric identifiers (placeholder/stub for future implementation)
    biometric_tags: Dict[str, Any] = field(default_factory=dict)

    # User preferences
    preferences: Dict[str, Any] = field(default_factory=dict)

    # Session history
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_active_at = time.time()

    def update_name(self, name: str, display_name: Optional[str] = None):
        """
        Update the user's name and optionally the display name.

        Args:
            name: The user's actual name
            display_name: Optional display name (defaults to name if not provided)
        """
        self.name = name
        self.display_name = display_name if display_name else name
        self.update_activity()

    def update_photo(self, photo_path: str):
        """
        Update the user's photo path.

        Args:
            photo_path: Path to the user's photo
        """
        self.photo_path = photo_path
        self.update_activity()

    def add_biometric_tag(self, tag_type: str, tag_value: Any):
        """
        Add a biometric tag for the user (stub for future implementation).

        Args:
            tag_type: Type of biometric identifier
            tag_value: Value of the biometric identifier
        """
        self.biometric_tags[tag_type] = tag_value
        self.update_activity()

    def set_preference(self, key: str, value: Any):
        """
        Set a user preference.

        Args:
            key: Preference key
            value: Preference value
        """
        self.preferences[key] = value
        self.update_activity()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference.

        Args:
            key: Preference key
            default: Default value to return if preference doesn't exist

        Returns:
            The preference value or the default
        """
        return self.preferences.get(key, default)

    def add_conversation_entry(self, entry: Dict[str, Any]):
        """
        Add an entry to the conversation history.

        Args:
            entry: Conversation entry to add
        """
        self.conversation_history.append({
            **entry,
            'timestamp': time.time()
        })
        self.update_activity()

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the conversation history.

        Args:
            limit: Optional limit on the number of entries to return

        Returns:
            List of conversation entries
        """
        if limit is None:
            return self.conversation_history
        return self.conversation_history[-limit:]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the user profile to a dictionary.

        Returns:
            Dictionary representation of the user profile
        """
        return {
            'user_id': self.user_id,
            'name': self.name,
            'display_name': self.display_name,
            'photo_path': self.photo_path,
            'biometric_tags': self.biometric_tags,
            'preferences': self.preferences,
            'created_at': self.created_at,
            'last_active_at': self.last_active_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """
        Create a user profile from a dictionary.

        Args:
            data: Dictionary containing user profile data

        Returns:
            UserProfile instance
        """
        profile = cls(
            user_id=data.get('user_id', str(uuid.uuid4())),
            name=data.get('name'),
            display_name=data.get('display_name'),
            photo_path=data.get('photo_path'),
            created_at=data.get('created_at', time.time()),
            last_active_at=data.get('last_active_at', time.time())
        )

        profile.biometric_tags = data.get('biometric_tags', {})
        profile.preferences = data.get('preferences', {})
        profile.conversation_history = data.get('conversation_history', [])

        return profile
