"""
Configuration Management Module
Handles all system configuration settings
"""

import json
import os
from pathlib import Path

class Config:
    """System Configuration Manager"""

    CONFIG_FILE = "advanced_config.json"

    DEFAULT_CONFIG = {
        # Camera Settings
        "camera_index": 0,
        "frame_width": 640,
        "frame_height": 480,

        # Face Recognition Settings
        "face_tolerance": 0.6,
        "face_detection_model": "hog",

        # Paths
        "images_folder": "registered_faces",
        "database_file": "attendance.db",
        "blockchain_file": "blockchain_data.json",
        "log_file": "logs/app.log",

        # Feature Flags
        "enable_antispoofing": True,
        "enable_blockchain": True,
        "enable_emotion": True,
        "enable_privacy": True,

        # Anti-Spoofing Settings - STRICTER
        "liveness_threshold": 0.85,  # Increased from 0.7
        "blink_threshold": 0.21,
        "min_blinks": 2,
        "texture_threshold": 25.0,  # Increased from 15.0
        "color_diversity_threshold": 15.0,  # Increased from 10.0
        "frequency_threshold": 800.0,  # NEW
        "mobile_screen_detection": True,  # NEW

        # Blockchain Settings
        "mining_difficulty": 2,
        "max_chain_size": 10000,

        # Emotion Settings
        "emotion_history_size": 30,
        "engagement_window": 30,

        # Performance Settings
        "process_every_n_frames": 3,
        "resize_factor": 0.5,

        # Privacy Settings
        "differential_privacy_epsilon": 1.0,
        "anonymize_exports": True
    }

    def __init__(self):
        self.config_path = Path(self.CONFIG_FILE)
        self.data = {}
        self.load_config()

    def load_config(self):
        """Load configuration from file or create default"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.data = json.load(f)
                print(f"✓ Configuration loaded from {self.CONFIG_FILE}")
            else:
                self.data = self.DEFAULT_CONFIG.copy()
                self.save_config()
                print(f"✓ Default configuration created: {self.CONFIG_FILE}")
        except Exception as e:
            print(f"✗ Config load error: {e}")
            self.data = self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=4)
            print(f"✓ Configuration saved to {self.CONFIG_FILE}")
        except Exception as e:
            print(f"✗ Config save error: {e}")

    def get(self, key, default=None):
        """Get configuration value"""
        return self.data.get(key, default)

    def set(self, key, value):
        """Set configuration value and save"""
        self.data[key] = value
        self.save_config()

    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.data = self.DEFAULT_CONFIG.copy()
        self.save_config()
        print("✓ Configuration reset to defaults")

    def validate(self):
        """Validate configuration values"""
        issues = []

        # Check camera index
        if not isinstance(self.get("camera_index"), int):
            issues.append("camera_index must be an integer")

        # Check face tolerance
        tolerance = self.get("face_tolerance")
        if not (0.1 <= tolerance <= 1.0):
            issues.append("face_tolerance must be between 0.1 and 1.0")

        # Check liveness threshold
        liveness = self.get("liveness_threshold")
        if not (0.0 <= liveness <= 1.0):
            issues.append("liveness_threshold must be between 0.0 and 1.0")

        if issues:
            print("⚠ Configuration validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        print("✓ Configuration validated successfully")
        return True

    def __str__(self):
        """String representation of config"""
        return json.dumps(self.data, indent=2)


# Global config instance
config = Config()

if __name__ == "__main__":
    # Test configuration
    config = Config()
    config.validate()
    print("\nCurrent Configuration:")
    print(config)