#!/usr/bin/env python3
"""
SecureAttend - Main Entry Point
Advanced Face Recognition Attendance System
Version 3.0 Research Edition
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main application entry point"""
    try:
        print("=" * 70)
        print("  SecureAttend - Advanced Face Recognition System v3.0")
        print("  Research Edition with Anti-Spoofing & Blockchain")
        print("=" * 70)
        print()

        # Import and run GUI
        from src.gui_application import SecureAttendApp

        app = SecureAttendApp()
        app.run()

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nPlease install required dependencies:")
        print("  pip install -r requirements.txt")
        input("\nPress Enter to exit...")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Application Error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()