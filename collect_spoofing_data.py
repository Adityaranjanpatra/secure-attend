"""
Spoofing Attack Data Collection Script
Systematically collect attack samples for research
"""

import cv2
import datetime
import os
import csv


def collect_spoofing_sample():
    """Collect single spoofing attack sample"""

    print("\n" + "=" * 70)
    print("  SPOOFING ATTACK DATA COLLECTION")
    print("=" * 70 + "\n")

    # Get metadata
    user_id = input("User ID (e.g., user001): ")
    attack_type = input("Attack Type (photo/screen/video): ")
    device = input("Device/Material (e.g., iPhone12/PrintedPhoto/A4Paper): ")
    lighting = input("Lighting (bright/normal/dim): ")
    distance = input("Distance (close/medium/far): ")
    notes = input("Additional notes: ")

    # Create folder
    base_path = f"datasets/spoofing_attacks/{attack_type}_attacks"
    os.makedirs(base_path, exist_ok=True)

    # Capture
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Cannot access camera!")
        return

    print("\n✓ Camera ready!")
    print("• Press 'S' to capture sample")
    print("• Press 'Q' to quit")
    print("\nPosition the attack sample in front of camera...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Add overlay
        cv2.putText(frame, f"Attack: {attack_type} - {device}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, "Press 'S' to capture, 'Q' to quit", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow('Spoofing Data Collection', frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('s') or key == ord('S'):
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{user_id}_{attack_type}_{device.replace(' ', '_')}_{timestamp}.jpg"
            filepath = os.path.join(base_path, filename)

            cv2.imwrite(filepath, frame)
            print(f"\n✓ Saved: {filename}")

            # Save metadata
            metadata_file = 'datasets/spoofing_metadata.csv'
            file_exists = os.path.exists(metadata_file)

            with open(metadata_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['UserID', 'AttackType', 'Device', 'Lighting',
                                     'Distance', 'Timestamp', 'Filepath', 'Notes'])
                writer.writerow([user_id, attack_type, device, lighting,
                                 distance, timestamp, filepath, notes])

            print("✓ Metadata saved")
            break

        elif key == ord('q') or key == ord('Q'):
            print("\n❌ Cancelled")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "=" * 70)
    print("  Data collection complete!")
    print("=" * 70)


if __name__ == "__main__":
    # Create datasets folder
    os.makedirs('datasets/spoofing_attacks/photo_attacks', exist_ok=True)
    os.makedirs('datasets/spoofing_attacks/screen_attacks', exist_ok=True)
    os.makedirs('datasets/spoofing_attacks/video_attacks', exist_ok=True)

    collect_spoofing_sample()

    # Ask if want to collect more
    again = input("\nCollect another sample? (y/n): ")
    if again.lower() == 'y':
        collect_spoofing_sample()