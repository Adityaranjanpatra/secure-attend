"""
Emotion Detection Module
Real-time emotion recognition for engagement monitoring
"""

import cv2
import numpy as np
from collections import deque
from typing import Tuple, List


class EmotionDetector:
    """Emotion recognition for engagement analysis"""

    EMOTIONS = ['Neutral', 'Happy', 'Sad', 'Surprise', 'Anger', 'Fear', 'Disgust']
    ENGAGED_EMOTIONS = ['Happy', 'Surprise']
    DISENGAGED_EMOTIONS = ['Sad', 'Anger', 'Fear']

    def __init__(self, history_size: int = 30):
        self.history_size = history_size
        self.emotion_history = deque(maxlen=history_size)
        self.engagement_scores = deque(maxlen=history_size)

        print("✓ Emotion Detector initialized")

    def detect_emotion_simple(self, face_region: np.ndarray) -> Tuple[str, float]:
        """
        Simplified emotion detection based on facial features
        For production, replace with CNN-based model (ResNet, VGG, etc.)
        """
        try:
            if face_region.size == 0:
                return 'Neutral', 0.5

            # Convert to grayscale
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

            # Extract basic features
            brightness = np.mean(gray)
            contrast = np.std(gray)

            # Edge detection for expression analysis
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size

            # Calculate gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2).mean()

            # Simple heuristic-based classification
            emotion, confidence = self._classify_emotion(
                brightness, contrast, edge_density, gradient_magnitude
            )

            # Store in history
            self.emotion_history.append(emotion)

            return emotion, confidence

        except Exception as e:
            print(f"Emotion detection error: {e}")
            return 'Neutral', 0.5

    def _classify_emotion(self, brightness: float, contrast: float,
                         edge_density: float, gradient: float) -> Tuple[str, float]:
        """
        Classify emotion based on facial features
        This is a simplified heuristic approach
        """
        # Happy detection (bright face, high contrast, moderate edges)
        if brightness > 130 and contrast > 40 and 0.08 < edge_density < 0.15:
            return 'Happy', 0.75

        # Sad detection (darker face, low edge density)
        elif brightness < 90 and edge_density < 0.08:
            return 'Sad', 0.65

        # Surprise detection (high contrast, high edge density)
        elif contrast > 60 and edge_density > 0.15:
            return 'Surprise', 0.70

        # Anger detection (high edge density, moderate brightness)
        elif edge_density > 0.20 and 90 < brightness < 130:
            return 'Anger', 0.65

        # Fear detection (high gradient, high edge density)
        elif gradient > 30 and edge_density > 0.18:
            return 'Fear', 0.60

        # Default to Neutral
        else:
            return 'Neutral', 0.80

    def detect_emotion_advanced(self, face_region: np.ndarray) -> Tuple[str, float]:
        """
        Advanced emotion detection using HOG features
        More robust than simple heuristics
        """
        try:
            if face_region.size == 0:
                return 'Neutral', 0.5

            # Resize face region
            face_resized = cv2.resize(face_region, (64, 64))
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

            # Extract HOG features
            hog_features = self._compute_hog_features(gray)

            # Classify based on HOG features
            emotion, confidence = self._classify_from_hog(hog_features)

            self.emotion_history.append(emotion)

            return emotion, confidence

        except Exception as e:
            print(f"Advanced emotion detection error: {e}")
            return self.detect_emotion_simple(face_region)

    def _compute_hog_features(self, gray_image: np.ndarray) -> np.ndarray:
        """Compute HOG (Histogram of Oriented Gradients) features"""
        # Calculate gradients
        gx = cv2.Sobel(gray_image, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(gray_image, cv2.CV_32F, 0, 1)

        # Calculate magnitude and orientation
        magnitude = np.sqrt(gx**2 + gy**2)
        orientation = np.arctan2(gy, gx) * (180 / np.pi) % 180

        # Create histogram
        hist, _ = np.histogram(orientation, bins=9, range=(0, 180), weights=magnitude)

        # Normalize
        hist = hist / (np.sum(hist) + 1e-6)

        return hist

    def _classify_from_hog(self, hog_features: np.ndarray) -> Tuple[str, float]:
        """Classify emotion from HOG features"""
        # This is a placeholder - in production, use trained ML model
        # For now, use simple thresholds on HOG bins

        max_bin = np.argmax(hog_features)
        max_value = hog_features[max_bin]

        if max_bin in [0, 1, 8] and max_value > 0.15:
            return 'Happy', 0.70
        elif max_bin in [3, 4, 5] and max_value > 0.18:
            return 'Sad', 0.65
        elif max_value > 0.20:
            return 'Surprise', 0.68
        else:
            return 'Neutral', 0.75

    def get_dominant_emotion(self) -> str:
        """Get most frequent emotion from history"""
        if not self.emotion_history:
            return 'Neutral'

        # Count emotions
        emotion_counts = {}
        for emotion in self.emotion_history:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        # Return most common
        return max(emotion_counts, key=emotion_counts.get)

    def calculate_engagement_score(self) -> float:
        """
        Calculate engagement score based on emotion history
        Returns score from 0-100
        """
        if not self.emotion_history:
            return 50.0

        engaged_count = sum(1 for e in self.emotion_history if e in self.ENGAGED_EMOTIONS)
        disengaged_count = sum(1 for e in self.emotion_history if e in self.DISENGAGED_EMOTIONS)

        # Calculate score
        total = len(self.emotion_history)
        engagement_ratio = (engaged_count - disengaged_count * 0.5) / total

        # Map to 0-100 scale
        score = 50 + (engagement_ratio * 50)
        score = max(0, min(100, score))

        return round(score, 2)

    def get_emotion_distribution(self) -> dict:
        """Get distribution of emotions in history"""
        if not self.emotion_history:
            return {}

        distribution = {}
        total = len(self.emotion_history)

        for emotion in self.EMOTIONS:
            count = sum(1 for e in self.emotion_history if e == emotion)
            distribution[emotion] = round((count / total) * 100, 1)

        return distribution

    def is_engaged(self, threshold: float = 60.0) -> bool:
        """Check if user is currently engaged"""
        return self.calculate_engagement_score() >= threshold

    def get_engagement_trend(self) -> str:
        """Get engagement trend (improving, declining, stable)"""
        if len(self.emotion_history) < 10:
            return "insufficient_data"

        # Compare first half vs second half
        mid = len(self.emotion_history) // 2
        first_half = list(self.emotion_history)[:mid]
        second_half = list(self.emotion_history)[mid:]

        first_engaged = sum(1 for e in first_half if e in self.ENGAGED_EMOTIONS)
        second_engaged = sum(1 for e in second_half if e in self.ENGAGED_EMOTIONS)

        diff = second_engaged - first_engaged

        if diff > 2:
            return "improving"
        elif diff < -2:
            return "declining"
        else:
            return "stable"

    def reset(self):
        """Reset emotion history"""
        self.emotion_history.clear()
        self.engagement_scores.clear()
        print("🔄 Emotion detector reset")

    def export_emotion_data(self) -> List[str]:
        """Export emotion history as list"""
        return list(self.emotion_history)


# Test the emotion detector
if __name__ == "__main__":
    print("Testing Emotion Detector\n")

    detector = EmotionDetector()

    # Test with dummy face regions
    for i in range(20):
        # Create random test image
        test_face = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

        # Detect emotion
        emotion, confidence = detector.detect_emotion_simple(test_face)
        print(f"Frame {i+1}: {emotion} ({confidence:.2f})")

    # Get statistics
    print(f"\nDominant Emotion: {detector.get_dominant_emotion()}")
    print(f"Engagement Score: {detector.calculate_engagement_score()}")
    print(f"Engagement Trend: {detector.get_engagement_trend()}")

    print("\nEmotion Distribution:")
    for emotion, percentage in detector.get_emotion_distribution().items():
        print(f"  {emotion}: {percentage}%")