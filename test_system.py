"""
System Testing Script
Tests all components of SecureAttend
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from src.config import Config
from src.blockchain import Blockchain
from src.liveness_detector import LivenessDetector
from src.emotion_detector import EmotionDetector
from src.database_manager import DatabaseManager
from src.privacy_manager import PrivacyManager


def test_config():
    """Test configuration module"""
    print("\n" + "=" * 70)
    print("Testing Configuration Module")
    print("=" * 70)

    config = Config()

    # Test get
    camera = config.get('camera_index')
    print(f"✓ Camera index: {camera}")

    # Test set
    config.set('test_key', 'test_value')
    assert config.get('test_key') == 'test_value'
    print("✓ Set/Get working")

    # Test validation
    config.validate()
    print("✓ Validation working")

    print("✅ Configuration module PASSED")
    return True


def test_blockchain():
    """Test blockchain module"""
    print("\n" + "=" * 70)
    print("Testing Blockchain Module")
    print("=" * 70)

    # Create test blockchain
    bc = Blockchain("test_blockchain.json")

    initial_length = len(bc)
    print(f"✓ Initial chain length: {initial_length}")

    # Add test blocks
    test_data = {
        'type': 'test',
        'user_id': 'test_user',
        'timestamp': '2025-01-01 12:00:00'
    }

    block_hash = bc.add_block(test_data)
    assert block_hash is not None
    print(f"✓ Block added: {block_hash[:16]}...")

    # Verify chain
    assert bc.is_chain_valid()
    print("✓ Chain is valid")

    # Test tampering detection
    if len(bc.chain) > 1:
        bc.chain[1].data['tampered'] = True
        assert not bc.is_chain_valid()
        print("✓ Tamper detection working")

    print("✅ Blockchain module PASSED")

    # Cleanup
    if os.path.exists("test_blockchain.json"):
        os.remove("test_blockchain.json")

    return True


def test_liveness_detector():
    """Test liveness detection"""
    print("\n" + "=" * 70)
    print("Testing Liveness Detector")
    print("=" * 70)

    config = Config()
    detector = LivenessDetector(config)

    # Create test frame
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    face_location = (100, 400, 400, 100)

    # Test detection
    is_live, score = detector.detect_liveness(test_frame, face_location)
    print(f"✓ Liveness detection: Live={is_live}, Score={score:.3f}")

    # Test detailed scores
    scores = detector.get_detailed_scores(test_frame, face_location)
    print(f"✓ Texture score: {scores['texture_score']:.2f}")
    print(f"✓ Color diversity: {scores['color_diversity']:.2f}")

    # Test reset
    detector.reset()
    print("✓ Reset working")

    print("✅ Liveness detector PASSED")
    return True


def test_emotion_detector():
    """Test emotion detection"""
    print("\n" + "=" * 70)
    print("Testing Emotion Detector")
    print("=" * 70)

    detector = EmotionDetector()

    # Create test face region
    test_face = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    # Test detection
    emotion, confidence = detector.detect_emotion_simple(test_face)
    print(f"✓ Detected emotion: {emotion} ({confidence:.2f})")

    # Add multiple emotions
    for _ in range(10):
        detector.detect_emotion_simple(test_face)

    # Test statistics
    dominant = detector.get_dominant_emotion()
    engagement = detector.calculate_engagement_score()

    print(f"✓ Dominant emotion: {dominant}")
    print(f"✓ Engagement score: {engagement:.2f}")

    # Test distribution
    dist = detector.get_emotion_distribution()
    print(f"✓ Emotion distribution: {len(dist)} emotions")

    print("✅ Emotion detector PASSED")
    return True


def test_database():
    """Test database operations"""
    print("\n" + "=" * 70)
    print("Testing Database Manager")
    print("=" * 70)

    db = DatabaseManager("test_attendance.db")

    # Test add user
    test_encoding = np.random.rand(128)
    success = db.add_user("test_user", "Test User", test_encoding)
    assert success
    print("✓ User added")

    # Test mark attendance
    success, msg = db.mark_attendance(
        "test_user", "Test User", 0.95, "Happy", 85.0,
        "test_hash", test_encoding, 0.98, "Test Location"
    )
    assert success
    print(f"✓ Attendance marked: {msg}")

    # Test get records
    records = db.get_attendance_records(limit=10)
    print(f"✓ Retrieved {len(records)} records")

    # Test analytics
    total, eng, live, conf = db.get_analytics_summary()
    print(f"✓ Analytics: Total={total}, Engagement={eng:.2f}")

    # Test user list
    users = db.get_all_users()
    print(f"✓ Total users: {len(users)}")

    print("✅ Database manager PASSED")

    # Cleanup
    if os.path.exists("test_attendance.db"):
        os.remove("test_attendance.db")

    return True


def test_privacy_manager():
    """Test privacy protection"""
    print("\n" + "=" * 70)
    print("Testing Privacy Manager")
    print("=" * 70)

    pm = PrivacyManager(epsilon=1.0)

    # Test encoding hashing
    test_encoding = np.random.rand(128)
    hash_val = pm.hash_encoding(test_encoding)
    print(f"✓ Encoding hash: {hash_val[:16]}...")

    # Test differential privacy
    noisy = pm.add_differential_privacy_noise(test_encoding)
    similarity = pm.secure_comparison(test_encoding, noisy)
    print(f"✓ Privacy noise added, similarity: {similarity:.3f}")

    # Test anonymization
    personal_data = {
        'name': 'John Doe',
        'email': 'john@test.com',
        'user_id': 'john_123'
    }

    anonymized = pm.anonymize_personal_data(personal_data)
    assert 'name_hash' in anonymized
    print("✓ Data anonymization working")

    # Test privacy report
    report = pm.generate_privacy_report(100, 500)
    print(f"✓ Privacy report generated: {report['privacy_guarantee']}")

    print("✅ Privacy manager PASSED")
    return True


def run_all_tests():
    """Run all system tests"""
    print("\n" + "=" * 70)
    print("  SECUREATTEND SYSTEM TESTS")
    print("=" * 70)

    tests = [
        ("Configuration", test_config),
        ("Blockchain", test_blockchain),
        ("Liveness Detection", test_liveness_detector),
        ("Emotion Detection", test_emotion_detector),
        ("Database", test_database),
        ("Privacy Manager", test_privacy_manager)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! System is ready for use.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review errors above.")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)