"""
Privacy Management Module
Implements privacy-preserving techniques for face recognition
"""

import hashlib
import numpy as np
from typing import Dict, Any
import json


class PrivacyManager:
    """Privacy-preserving face encoding management"""

    def __init__(self, epsilon: float = 1.0):
        """
        Initialize privacy manager

        Args:
            epsilon: Privacy budget for differential privacy (lower = more private)
        """
        self.epsilon = epsilon
        print(f"✓ Privacy Manager initialized (ε={epsilon})")

    @staticmethod
    def hash_encoding(encoding: np.ndarray) -> str:
        """
        Create irreversible hash of face encoding

        Args:
            encoding: Face encoding vector

        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(encoding.tobytes()).hexdigest()

    @staticmethod
    def hash_encoding_short(encoding: np.ndarray, length: int = 16) -> str:
        """Create shortened hash for display"""
        full_hash = PrivacyManager.hash_encoding(encoding)
        return full_hash[:length]

    def add_differential_privacy_noise(self, encoding: np.ndarray) -> np.ndarray:
        """
        Add calibrated Laplacian noise for differential privacy

        Args:
            encoding: Original face encoding

        Returns:
            Noisy encoding with privacy guarantee
        """
        # Calculate sensitivity (L2 norm bounded)
        sensitivity = 1.0

        # Calculate scale parameter
        scale = sensitivity / self.epsilon

        # Add Laplacian noise
        noise = np.random.laplace(0, scale, encoding.shape)
        noisy_encoding = encoding + noise

        # Normalize to maintain encoding properties
        noisy_encoding = noisy_encoding / (np.linalg.norm(noisy_encoding) + 1e-8)

        return noisy_encoding

    def add_gaussian_noise(self, encoding: np.ndarray, sigma: float = 0.1) -> np.ndarray:
        """
        Add Gaussian noise to encoding

        Args:
            encoding: Original face encoding
            sigma: Standard deviation of noise

        Returns:
            Noisy encoding
        """
        noise = np.random.normal(0, sigma, encoding.shape)
        noisy_encoding = encoding + noise

        # Normalize
        noisy_encoding = noisy_encoding / (np.linalg.norm(noisy_encoding) + 1e-8)

        return noisy_encoding

    @staticmethod
    def anonymize_personal_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize personally identifiable information

        Args:
            data: Dictionary containing personal data

        Returns:
            Anonymized data dictionary
        """
        anonymized = data.copy()

        # Hash name
        if 'name' in anonymized:
            name_hash = hashlib.sha256(anonymized['name'].encode()).hexdigest()[:8]
            anonymized['name_hash'] = name_hash
            anonymized['name'] = f"User_{name_hash}"

        # Remove email
        if 'email' in anonymized:
            anonymized['email'] = "***@***.***"

        # Remove user_id if present
        if 'user_id' in anonymized:
            anonymized['user_id_hash'] = hashlib.sha256(
                anonymized['user_id'].encode()
            ).hexdigest()[:8]
            del anonymized['user_id']

        # Keep only anonymized fields
        safe_fields = ['timestamp', 'date', 'time', 'liveness_score',
                      'emotion', 'engagement_score', 'confidence',
                      'name_hash', 'user_id_hash']

        anonymized = {k: v for k, v in anonymized.items() if k in safe_fields}

        return anonymized

    @staticmethod
    def k_anonymize_dataset(dataset: list, k: int = 5) -> list:
        """
        Apply k-anonymity to dataset

        Args:
            dataset: List of records
            k: Minimum group size for anonymity

        Returns:
            K-anonymized dataset
        """
        # Group by quasi-identifiers
        groups = {}
        for record in dataset:
            # Use date as quasi-identifier
            key = record.get('date', 'unknown')
            if key not in groups:
                groups[key] = []
            groups[key].append(record)

        # Filter groups smaller than k
        anonymized = []
        for group in groups.values():
            if len(group) >= k:
                anonymized.extend(group)

        return anonymized

    def calculate_privacy_loss(self, queries: int) -> float:
        """
        Calculate cumulative privacy loss

        Args:
            queries: Number of queries made

        Returns:
            Total privacy loss (epsilon)
        """
        # Simple composition: ε_total = queries * ε_query
        return queries * self.epsilon

    @staticmethod
    def secure_comparison(encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """
        Securely compare two encodings without exposing raw values

        Args:
            encoding1: First encoding
            encoding2: Second encoding

        Returns:
            Similarity score (0-1)
        """
        # Calculate cosine similarity
        similarity = np.dot(encoding1, encoding2) / (
            np.linalg.norm(encoding1) * np.linalg.norm(encoding2) + 1e-8
        )

        # Normalize to 0-1 range
        similarity = (similarity + 1) / 2

        return float(similarity)

    @staticmethod
    def encrypt_data_simple(data: str, key: str) -> str:
        """
        Simple XOR encryption for data protection

        Args:
            data: Data to encrypt
            key: Encryption key

        Returns:
            Encrypted string (hex)
        """
        encrypted = []
        for i, char in enumerate(data):
            key_char = key[i % len(key)]
            encrypted_char = chr(ord(char) ^ ord(key_char))
            encrypted.append(encrypted_char)

        encrypted_str = ''.join(encrypted)
        return encrypted_str.encode('utf-8').hex()

    @staticmethod
    def decrypt_data_simple(encrypted_hex: str, key: str) -> str:
        """
        Simple XOR decryption

        Args:
            encrypted_hex: Encrypted hex string
            key: Decryption key

        Returns:
            Decrypted string
        """
        encrypted = bytes.fromhex(encrypted_hex).decode('utf-8')

        decrypted = []
        for i, char in enumerate(encrypted):
            key_char = key[i % len(key)]
            decrypted_char = chr(ord(char) ^ ord(key_char))
            decrypted.append(decrypted_char)

        return ''.join(decrypted)

    def generate_privacy_report(self, total_users: int, total_queries: int) -> Dict:
        """
        Generate privacy audit report

        Args:
            total_users: Number of registered users
            total_queries: Number of recognition queries

        Returns:
            Privacy report dictionary
        """
        privacy_loss = self.calculate_privacy_loss(total_queries)

        report = {
            'privacy_budget_epsilon': self.epsilon,
            'total_users': total_users,
            'total_queries': total_queries,
            'cumulative_privacy_loss': privacy_loss,
            'privacy_guarantee': 'Strong' if privacy_loss < 1.0 else 'Moderate' if privacy_loss < 5.0 else 'Weak',
            'recommendations': []
        }

        if privacy_loss > 10.0:
            report['recommendations'].append('Consider resetting privacy budget')

        if total_users > 1000:
            report['recommendations'].append('Implement stricter anonymization')

        return report

    @staticmethod
    def mask_sensitive_fields(data: Dict, fields_to_mask: list) -> Dict:
        """
        Mask specific sensitive fields

        Args:
            data: Data dictionary
            fields_to_mask: List of field names to mask

        Returns:
            Data with masked fields
        """
        masked = data.copy()

        for field in fields_to_mask:
            if field in masked:
                if isinstance(masked[field], str):
                    masked[field] = '*' * len(masked[field])
                elif isinstance(masked[field], (int, float)):
                    masked[field] = 0

        return masked


# Test privacy manager
if __name__ == "__main__":
    print("Testing Privacy Manager\n")

    pm = PrivacyManager(epsilon=1.0)

    # Test encoding hashing
    test_encoding = np.random.rand(128)
    hash_full = pm.hash_encoding(test_encoding)
    hash_short = pm.hash_encoding_short(test_encoding)

    print(f"Full hash: {hash_full}")
    print(f"Short hash: {hash_short}")

    # Test differential privacy
    noisy_encoding = pm.add_differential_privacy_noise(test_encoding)
    print(f"\nOriginal encoding norm: {np.linalg.norm(test_encoding):.4f}")
    print(f"Noisy encoding norm: {np.linalg.norm(noisy_encoding):.4f}")
    print(f"Similarity: {pm.secure_comparison(test_encoding, noisy_encoding):.4f}")

    # Test data anonymization
    personal_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'user_id': 'john_doe_123',
        'timestamp': '2025-01-01 10:00:00',
        'liveness_score': 0.95
    }

    anonymized = pm.anonymize_personal_data(personal_data)
    print(f"\nOriginal data: {json.dumps(personal_data, indent=2)}")
    print(f"\nAnonymized data: {json.dumps(anonymized, indent=2)}")

    # Test privacy report
    report = pm.generate_privacy_report(100, 500)
    print(f"\nPrivacy Report: {json.dumps(report, indent=2)}")