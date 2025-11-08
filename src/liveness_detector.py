"""
Liveness Detection Module
Multi-modal anti-spoofing for face recognition
Detects photo attacks, video replay attacks, and masks
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class LivenessDetector:
    """Advanced anti-spoofing with multi-modal liveness detection"""

    def __init__(self, config):
        self.config = config

        # Thresholds from config
        self.eye_ar_threshold = config.get('blink_threshold', 0.21)
        self.min_blinks = config.get('min_blinks', 2)
        self.texture_threshold = config.get('texture_threshold', 15.0)
        self.color_diversity_threshold = config.get('color_diversity_threshold', 10.0)
        self.liveness_threshold = config.get('liveness_threshold', 0.7)

        # State variables
        self.blink_counter = 0
        self.blink_frames = 0
        self.total_blinks = 0
        self.frame_count = 0

        print("✓ Liveness Detector initialized")

    def eye_aspect_ratio(self, eye_points: np.ndarray) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) for blink detection
        Based on: "Real-Time Eye Blink Detection using Facial Landmarks" (Soukupová & Čech, 2016)
        """
        # Compute vertical eye distances
        A = np.linalg.norm(eye_points[1] - eye_points[5])
        B = np.linalg.norm(eye_points[2] - eye_points[4])

        # Compute horizontal eye distance
        C = np.linalg.norm(eye_points[0] - eye_points[3])

        # Compute EAR
        ear = (A + B) / (2.0 * C + 1e-6)
        return ear

    def calculate_texture_score(self, face_region: np.ndarray) -> float:
        """
        Calculate texture variance using Laplacian operator
        Real faces have high texture variance, photos have low variance
        """
        try:
            if face_region.size == 0:
                return 0.0

            # Convert to grayscale
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

            # Calculate Laplacian variance
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()

            return variance

        except Exception as e:
            print(f"Texture calculation error: {e}")
            return 0.0

    def calculate_color_diversity(self, face_region: np.ndarray) -> float:
        """
        Calculate color diversity in HSV space
        Real faces have diverse colors, printed photos have limited color range
        """
        try:
            if face_region.size == 0:
                return 0.0

            # Convert to HSV
            hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)

            # Calculate standard deviation of Hue and Saturation
            h_std = np.std(hsv[:, :, 0])
            s_std = np.std(hsv[:, :, 1])

            # Combined diversity score
            diversity = (h_std + s_std) / 2.0

            return diversity

        except Exception as e:
            print(f"Color diversity error: {e}")
            return 0.0

    def calculate_frequency_score(self, face_region: np.ndarray) -> float:
        """
        Analyze frequency domain characteristics
        Real faces have different frequency patterns than photos
        """
        try:
            if face_region.size == 0:
                return 0.0

            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

            # Apply FFT
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.abs(f_shift)

            # Calculate high-frequency content
            rows, cols = magnitude.shape
            crow, ccol = rows // 2, cols // 2

            # Extract high frequency region
            high_freq = magnitude.copy()
            high_freq[crow-30:crow+30, ccol-30:ccol+30] = 0

            score = np.mean(high_freq)
            return score

        except Exception as e:
            print(f"Frequency analysis error: {e}")
            return 0.0

    def detect_mobile_screen(self, face_region: np.ndarray) -> bool:
        """
        Detect if face is from a mobile screen
        Mobile screens have specific characteristics
        """
        try:
            if face_region.size == 0:
                return False

            # Convert to LAB color space
            lab = cv2.cvtColor(face_region, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Mobile screens have higher B channel (blue)
            mean_b = np.mean(b)

            # Mobile screens have more uniform distribution
            std_l = np.std(l)

            # Detect grid patterns (pixel matrix of screens)
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.sum(edges > 0) / edges.size

            # Screen characteristics
            is_screen = (
                    mean_b > 130 or  # High blue component
                    std_l < 20 or  # Very uniform lighting
                    edge_density > 0.25  # Many sharp edges
            )

            return is_screen

        except Exception as e:
            print(f"Screen detection error: {e}")
            return False

    def calculate_reflection_score(self, face_region: np.ndarray) -> float:
        """
        Detect screen reflections and glare
        """
        try:
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

            # Find very bright spots (potential glare)
            bright_spots = np.sum(gray > 240)
            total_pixels = gray.size
            glare_ratio = bright_spots / total_pixels

            # Too much glare = likely a screen
            return 1.0 - (glare_ratio * 10)  # Penalize high glare

        except:
            return 0.5

    def detect_liveness(self, frame: np.ndarray, face_location: Tuple[int, int, int, int]) -> Tuple[bool, float]:
        """
        Enhanced liveness detection with stricter checks
        """
        try:
            top, right, bottom, left = face_location

            # Validate face region
            h, w = frame.shape[:2]
            top = max(0, top)
            left = max(0, left)
            bottom = min(h, bottom)
            right = min(w, right)

            if bottom <= top or right <= left:
                return False, 0.0

            face_region = frame[top:bottom, left:right]

            # Check minimum face size
            if face_region.shape[0] < 80 or face_region.shape[1] < 80:
                print("⚠ Face too small - possible photo")
                return False, 0.0

            # ===== STRICTER Multi-Modal Analysis =====

            # 1. Texture Analysis (35% weight)
            texture_score = self.calculate_texture_score(face_region)
            texture_alive = texture_score > self.texture_threshold
            texture_confidence = min(texture_score / 50.0, 1.0)

            if not texture_alive:
                print(f"⚠ Texture FAIL: {texture_score:.2f} < {self.texture_threshold}")

            # 2. Color Diversity Analysis (25% weight)
            color_diversity = self.calculate_color_diversity(face_region)
            color_alive = color_diversity > self.color_diversity_threshold
            color_confidence = min(color_diversity / 30.0, 1.0)

            if not color_alive:
                print(f"⚠ Color FAIL: {color_diversity:.2f} < {self.color_diversity_threshold}")

            # 3. Frequency Analysis (20% weight)
            freq_score = self.calculate_frequency_score(face_region)
            freq_confidence = min(freq_score / 1500.0, 1.0)

            if freq_score < self.config.get('frequency_threshold', 800.0):
                print(f"⚠ Frequency FAIL: {freq_score:.2f}")

            # 4. Mobile Screen Detection (15% weight) - NEW
            is_screen = self.detect_mobile_screen(face_region)
            screen_confidence = 0.0 if is_screen else 1.0

            if is_screen:
                print("⚠ MOBILE SCREEN DETECTED!")

            # 5. Reflection/Glare Analysis (5% weight) - NEW
            reflection_score = self.calculate_reflection_score(face_region)

            # ===== Weighted Fusion =====
            liveness_score = (
                    texture_confidence * 0.35 +
                    color_confidence * 0.25 +
                    freq_confidence * 0.20 +
                    screen_confidence * 0.15 +
                    reflection_score * 0.05
            )

            # Additional penalty for suspicious combinations
            if is_screen or (texture_score < 20 and color_diversity < 12):
                liveness_score *= 0.5
                print("⚠ SUSPICIOUS PATTERN - Applying penalty")

            is_live = liveness_score >= self.liveness_threshold

            # Debug output
            print(f"Liveness: {liveness_score:.3f} | Texture: {texture_score:.1f} | " +
                  f"Color: {color_diversity:.1f} | Freq: {freq_score:.1f} | " +
                  f"Screen: {is_screen} | Result: {'✓ LIVE' if is_live else '✗ SPOOF'}")

            return is_live, round(liveness_score, 3)

        except Exception as e:
            print(f"Liveness detection error: {e}")
            return False, 0.0

    def detect_blink_from_landmarks(self, landmarks: np.ndarray) -> bool:
        """
        Detect eye blinks using facial landmarks
        Note: Requires dlib facial landmarks detector
        """
        try:
            # Eye indices for 68-point landmarks
            LEFT_EYE = list(range(36, 42))
            RIGHT_EYE = list(range(42, 48))

            left_eye = landmarks[LEFT_EYE]
            right_eye = landmarks[RIGHT_EYE]

            left_ear = self.eye_aspect_ratio(left_eye)
            right_ear = self.eye_aspect_ratio(right_eye)

            ear = (left_ear + right_ear) / 2.0

            if ear < self.eye_ar_threshold:
                self.blink_frames += 1
            else:
                if self.blink_frames >= 2:
                    self.total_blinks += 1
                    print(f"👁 Blink detected! Total: {self.total_blinks}")
                self.blink_frames = 0

            return self.total_blinks >= self.min_blinks

        except Exception as e:
            print(f"Blink detection error: {e}")
            return False

    def update_blink_count(self):
        """Manually increment blink counter (for external detection)"""
        self.total_blinks += 1
        print(f"👁 Blink count: {self.total_blinks}")

    def reset(self):
        """Reset detection counters"""
        self.total_blinks = 0
        self.blink_frames = 0
        self.frame_count = 0
        print("🔄 Liveness detector reset")

    def get_detailed_scores(self, frame: np.ndarray, face_location: Tuple) -> dict:
        """Get detailed breakdown of liveness scores"""
        top, right, bottom, left = face_location
        face_region = frame[top:bottom, left:right]

        return {
            'texture_score': self.calculate_texture_score(face_region),
            'color_diversity': self.calculate_color_diversity(face_region),
            'frequency_score': self.calculate_frequency_score(face_region),
            'blinks': self.total_blinks,
            'overall_liveness': self.detect_liveness(frame, face_location)[1]
        }


# Test the liveness detector
if __name__ == "__main__":
    print("Testing Liveness Detector\n")

    # Mock config
    class MockConfig:
        def get(self, key, default):
            return default

    config = MockConfig()
    detector = LivenessDetector(config)

    # Test with dummy image
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    face_loc = (100, 300, 300, 100)

    is_live, score = detector.detect_liveness(test_frame, face_loc)
    print(f"Liveness: {is_live}, Score: {score}")

    # Test detailed scores
    scores = detector.get_detailed_scores(test_frame, face_loc)
    print(f"\nDetailed Scores:")
    for key, value in scores.items():
        print(f"  {key}: {value}")