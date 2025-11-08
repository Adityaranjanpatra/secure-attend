#!/usr/bin/env python3
"""
GUI Application Module - COMPLETE FIXED VERSION
With Registration Number & Admin Panel
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import cv2
import numpy as np
import face_recognition
import os
import datetime
import threading
from PIL import Image, ImageTk
import sys
import hashlib
import sqlite3

# Import our modules
try:
    from src.config import Config
    from src.blockchain import Blockchain
    from src.liveness_detector import LivenessDetector
    from src.emotion_detector import EmotionDetector
    from src.database_manager import DatabaseManager
    from src.privacy_manager import PrivacyManager
except ImportError:
    from config import Config
    from blockchain import Blockchain
    from liveness_detector import LivenessDetector
    from emotion_detector import EmotionDetector
    from database_manager import DatabaseManager
    from privacy_manager import PrivacyManager


class AttendanceTracker:
    """Manages smooth attendance tracking without flickering"""

    def __init__(self):
        # Detection smoothing
        self.detection_history = {}
        self.detection_threshold = 5
        self.detection_cooldown = 30

        # UI state management
        self.ui_states = {}
        self.display_duration = 45

        # Frame counter
        self.frame_count = 0

        # Today's recognized users
        self.recognized_today = set()

        # Liveness check history
        self.liveness_history = {}
        self.liveness_window = 10

    def update_detection(self, user_id: str, is_detected: bool,
                         liveness_score: float = None) -> bool:
        """Update detection state with smoothing"""
        current_frame = self.frame_count

        if user_id not in self.detection_history:
            self.detection_history[user_id] = {
                'consecutive_detections': 0,
                'last_seen': 0,
                'is_stable': False
            }

        state = self.detection_history[user_id]

        if is_detected:
            state['consecutive_detections'] += 1
            state['last_seen'] = current_frame

            if state['consecutive_detections'] >= self.detection_threshold:
                state['is_stable'] = True
        else:
            frames_since_seen = current_frame - state['last_seen']

            if frames_since_seen > self.detection_cooldown:
                state['consecutive_detections'] = 0
                state['is_stable'] = False

        return state['is_stable']

    def update_liveness_smooth(self, user_id: str, liveness_score: float):
        """Smooth liveness detection"""
        if user_id not in self.liveness_history:
            from collections import deque
            self.liveness_history[user_id] = deque(maxlen=self.liveness_window)

        self.liveness_history[user_id].append(liveness_score)
        smoothed_score = np.mean(self.liveness_history[user_id])
        is_live = smoothed_score >= 0.7

        return is_live, smoothed_score

    def should_display(self, user_id: str) -> bool:
        """Check if we should display UI for this user"""
        if user_id not in self.detection_history:
            return False

        state = self.detection_history[user_id]
        frames_since_seen = self.frame_count - state['last_seen']

        return state['is_stable'] and frames_since_seen < self.display_duration

    def is_already_marked(self, user_id: str) -> bool:
        """Check if user already marked attendance today"""
        return user_id in self.recognized_today

    def increment_frame(self):
        """Increment frame counter"""
        self.frame_count += 1

    def reset(self):
        """Reset tracker"""
        self.detection_history.clear()
        self.ui_states.clear()
        self.liveness_history.clear()
        self.frame_count = 0


class SecureAttendApp:
    """Main GUI Application"""

    def __init__(self):
        # Initialize components
        self.config = Config()
        self.db = DatabaseManager(self.config.get('database_file'))
        self.blockchain = Blockchain(self.config.get('blockchain_file'))
        self.liveness_detector = LivenessDetector(self.config)
        self.emotion_detector = EmotionDetector()
        self.privacy_manager = PrivacyManager(self.config.get('differential_privacy_epsilon'))

        # State variables
        self.attendance_running = False
        self.known_encodings = []
        self.known_names = []
        self.known_user_ids = []

        # Setup GUI
        self.root = tk.Tk()
        self.setup_main_window()

        # Load users AFTER GUI is shown (prevents freezing)
        self.root.after(500, self.load_registered_users_fast)  # ← ADD THIS LINE

        print("✓ SecureAttend Application initialized")

    def setup_main_window(self):
        """Setup the main application window"""
        self.root.title("🔒 SecureAttend - Advanced System v3.0")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')

        # Setup styles
        self.setup_styles()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create all tabs
        self.create_dashboard_tab()
        self.create_attendance_tab()
        self.create_users_tab()
        self.create_admin_tab()
        self.create_blockchain_tab()
        self.create_analytics_tab()
        self.create_settings_tab()

        # Create status bar
        self.create_status_bar()

        # Update stats
        self.update_dashboard_stats()

    def setup_styles(self):
        """Configure TTK styles"""
        style = ttk.Style()
        style.theme_use('clam')

        bg = '#1a1a2e'
        fg = '#eee'
        accent = '#16213e'
        highlight = '#0f3460'

        style.configure('TNotebook', background=bg, borderwidth=0)
        style.configure('TNotebook.Tab', background=accent, foreground=fg,
                        padding=[20, 10], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', highlight)])

        style.configure('TFrame', background=bg)
        style.configure('Card.TFrame', background=accent, relief='raised')

        style.configure('TLabel', background=bg, foreground=fg, font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#00d4ff')
        style.configure('Subtitle.TLabel', font=('Segoe UI', 12), foreground='#aaa')
        style.configure('Stat.TLabel', font=('Segoe UI', 24, 'bold'), foreground='#00d4ff')

        style.configure('TButton', font=('Segoe UI', 10), padding=[10, 5])
        style.configure('Primary.TButton', font=('Segoe UI', 11, 'bold'), padding=[15, 8])
        style.configure('Danger.TButton', font=('Segoe UI', 11, 'bold'), padding=[15, 8])

    def create_dashboard_tab(self):
        """Create main dashboard"""
        dashboard = ttk.Frame(self.notebook)
        self.notebook.add(dashboard, text='🏠 Dashboard')

        title_frame = ttk.Frame(dashboard)
        title_frame.pack(fill='x', padx=20, pady=20)

        ttk.Label(title_frame, text="SecureAttend Dashboard",
                  style='Title.TLabel').pack(anchor='w')
        ttk.Label(title_frame,
                  text="Face Recognition with Anti-Spoofing, Blockchain & Admin Panel",
                  style='Subtitle.TLabel').pack(anchor='w', pady=(5, 0))

        stats_frame = ttk.Frame(dashboard)
        stats_frame.pack(fill='x', padx=20, pady=10)

        self.stat_labels = {}
        stats = [
            ('users', '👥 Users', '0'),
            ('today', '📅 Today', '0'),
            ('blocks', '⛓️ Blocks', '0'),
            ('status', '🔐 Status', 'Active')
        ]

        for i, (key, title, value) in enumerate(stats):
            card = self.create_stat_card(stats_frame, title, value, key)
            card.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            stats_frame.columnconfigure(i, weight=1)

        actions_frame = ttk.Frame(dashboard)
        actions_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(actions_frame, text="Quick Actions",
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 15))

        btn_frame = ttk.Frame(actions_frame)
        btn_frame.pack(fill='x')

        buttons = [
            ("🎥 Start Attendance", self.start_attendance_clicked, 'Primary.TButton'),
            ("👤 Register New User", self.register_user_clicked, 'Primary.TButton'),
            ("🔐 Admin Panel", lambda: self.notebook.select(3), 'Primary.TButton'),
            ("📊 Analytics", lambda: self.notebook.select(5), 'TButton'),
        ]

        for text, command, style in buttons:
            ttk.Button(btn_frame, text=text, command=command,
                       style=style).pack(fill='x', pady=5)

    def create_stat_card(self, parent, title, value, key):
        """Create stat card"""
        card = ttk.Frame(parent, style='Card.TFrame', relief='raised', borderwidth=2)
        ttk.Label(card, text=title, font=('Segoe UI', 10)).pack(pady=(15, 5))
        label = ttk.Label(card, text=value, style='Stat.TLabel')
        label.pack(pady=(0, 15))
        self.stat_labels[key] = label
        return card

    def create_attendance_tab(self):
        """Attendance tab with registration number"""
        att_frame = ttk.Frame(self.notebook)
        self.notebook.add(att_frame, text='📋 Attendance')

        ctrl_frame = ttk.Frame(att_frame)
        ctrl_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(ctrl_frame, text="Attendance Records",
                  font=('Segoe UI', 14, 'bold')).pack(side='left')

        ttk.Button(ctrl_frame, text="🔄 Refresh",
                   command=self.refresh_attendance).pack(side='right', padx=5)
        ttk.Button(ctrl_frame, text="💾 Export",
                   command=self.export_attendance).pack(side='right', padx=5)

        table_frame = ttk.Frame(att_frame)
        table_frame.pack(fill='both', expand=True, padx=20, pady=10)

        columns = ('Name', 'RegNo', 'Date', 'Time', 'Liveness', 'Emotion', 'Engagement')
        self.attendance_tree = ttk.Treeview(table_frame, columns=columns,
                                            show='headings', height=25)

        for col in columns:
            self.attendance_tree.heading(col, text=col)
            width = 140 if col == 'Name' else 100
            self.attendance_tree.column(col, width=width, anchor='center')

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.attendance_tree.yview)
        self.attendance_tree.configure(yscrollcommand=vsb.set)

        self.attendance_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.refresh_attendance()

    def create_users_tab(self):
        """Users tab with registration number"""
        users_frame = ttk.Frame(self.notebook)
        self.notebook.add(users_frame, text='👥 Users')

        ctrl_frame = ttk.Frame(users_frame)
        ctrl_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(ctrl_frame, text="Registered Users",
                  font=('Segoe UI', 14, 'bold')).pack(side='left')

        ttk.Button(ctrl_frame, text="➕ Add",
                   command=self.register_user_clicked).pack(side='right', padx=5)
        ttk.Button(ctrl_frame, text="🔄 Refresh",
                   command=self.refresh_users).pack(side='right', padx=5)

        list_frame = ttk.Frame(users_frame)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)

        columns = ('Name', 'RegNo', 'Department', 'Attendance', 'LastSeen')
        self.users_tree = ttk.Treeview(list_frame, columns=columns,
                                       show='headings', height=25)

        for col in columns:
            self.users_tree.heading(col, text=col)
            width = 180 if col == 'Name' else 120
            self.users_tree.column(col, width=width, anchor='center')

        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=vsb.set)

        self.users_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.refresh_users()

    def create_admin_tab(self):
        """Admin panel tab"""
        admin_frame = ttk.Frame(self.notebook)
        self.notebook.add(admin_frame, text='🔐 Admin Panel')

        title_frame = ttk.Frame(admin_frame)
        title_frame.pack(fill='x', padx=20, pady=20)

        ttk.Label(title_frame, text="Administrator Panel",
                  font=('Segoe UI', 16, 'bold'), foreground='#00d4ff').pack(anchor='w')

        # Search
        search_frame = ttk.LabelFrame(admin_frame, text="Search Users", padding=15)
        search_frame.pack(fill='x', padx=20, pady=10)

        search_controls = ttk.Frame(search_frame)
        search_controls.pack(fill='x')

        ttk.Label(search_controls, text="Search:").pack(side='left', padx=5)
        self.admin_search_var = tk.StringVar()
        ttk.Entry(search_controls, textvariable=self.admin_search_var,
                  width=30).pack(side='left', padx=5)

        ttk.Button(search_controls, text="🔍 By Name",
                   command=self.admin_search_user).pack(side='left', padx=5)
        ttk.Button(search_controls, text="🔍 By Reg No",
                   command=self.admin_search_by_regno).pack(side='left', padx=5)
        ttk.Button(search_controls, text="🔄 Show All",
                   command=self.admin_refresh_users).pack(side='left', padx=5)

        # User list
        mgmt_frame = ttk.LabelFrame(admin_frame, text="User Management", padding=15)
        mgmt_frame.pack(fill='both', expand=True, padx=20, pady=10)

        list_frame = ttk.Frame(mgmt_frame)
        list_frame.pack(fill='both', expand=True, pady=10)

        columns = ('UserID', 'Name', 'RegNo', 'Department', 'TotalAtt', 'Status')
        self.admin_tree = ttk.Treeview(list_frame, columns=columns,
                                      show='headings', height=15)

        for col in columns:
            self.admin_tree.heading(col, text=col)
            width = 150 if col in ['UserID', 'Name'] else 120
            self.admin_tree.column(col, width=width, anchor='center')

        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self.admin_tree.yview)
        self.admin_tree.configure(yscrollcommand=vsb.set)

        self.admin_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Action buttons
        btn_frame = ttk.Frame(mgmt_frame)
        btn_frame.pack(fill='x', pady=10)

        ttk.Button(btn_frame, text="✏️ Edit User",
                   command=self.admin_edit_user,
                   style='Primary.TButton').pack(side='left', padx=5)

        ttk.Button(btn_frame, text="📊 View History",
                   command=self.admin_view_history,
                   style='Primary.TButton').pack(side='left', padx=5)

        ttk.Button(btn_frame, text="🗑️ Delete User",
                   command=self.admin_delete_user,
                   style='Danger.TButton').pack(side='left', padx=5)

        self.admin_refresh_users()

    def create_blockchain_tab(self):
        """Blockchain tab"""
        bc_frame = ttk.Frame(self.notebook)
        self.notebook.add(bc_frame, text='⛓️ Blockchain')

        ctrl_frame = ttk.Frame(bc_frame)
        ctrl_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(ctrl_frame, text="Blockchain Explorer",
                  font=('Segoe UI', 14, 'bold')).pack(side='left')

        ttk.Button(ctrl_frame, text="✅ Verify",
                  command=self.verify_blockchain_clicked).pack(side='right', padx=5)
        ttk.Button(ctrl_frame, text="🔄 Refresh",
                  command=self.refresh_blockchain).pack(side='right', padx=5)

        self.bc_info_label = ttk.Label(bc_frame, text="")
        self.bc_info_label.pack(padx=20, pady=10)

        viewer_frame = ttk.Frame(bc_frame)
        viewer_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.blockchain_text = scrolledtext.ScrolledText(viewer_frame, wrap=tk.WORD,
                                                        font=('Courier New', 9), height=30)
        self.blockchain_text.pack(fill='both', expand=True)

        self.refresh_blockchain()

    def create_analytics_tab(self):
        """Analytics tab - FIXED"""
        analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(analytics_frame, text='📊 Analytics')

        ttk.Label(analytics_frame, text="Analytics Dashboard",
                  font=('Segoe UI', 14, 'bold')).pack(pady=20)

        # Get analytics with proper null handling
        total, eng, live, conf = self.db.get_analytics_summary()

        # Handle None values
        eng = eng if eng is not None else 0.0
        live = live if live is not None else 0.0
        conf = conf if conf is not None else 0.0

        stats_text = f"""
        📊 SYSTEM STATISTICS

        Total Attendance Records: {total}
        Average Engagement Score: {eng:.2f}%
        Average Liveness Score: {live:.3f}
        Average Confidence: {conf:.3f}

        Registered Users: {len(self.known_names)}
        Blockchain Blocks: {len(self.blockchain)}
        Blockchain Valid: {self.blockchain.is_chain_valid()}
        """

        ttk.Label(analytics_frame, text=stats_text, justify='left',
                  font=('Courier New', 10)).pack(padx=20)

    def create_settings_tab(self):
        """Settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text='⚙️ Settings')

        ttk.Label(settings_frame, text="System Configuration",
                  font=('Segoe UI', 14, 'bold')).pack(pady=20)

        form_frame = ttk.Frame(settings_frame)
        form_frame.pack(fill='both', expand=True, padx=50, pady=20)

        settings_config = [
            ("Camera Index", "camera_index", "0"),
            ("Face Tolerance", "face_tolerance", "0.6"),
            ("Liveness Threshold", "liveness_threshold", "0.85"),
        ]

        self.setting_vars = {}

        for i, (label, key, default) in enumerate(settings_config):
            ttk.Label(form_frame, text=f"{label}:").grid(row=i, column=0,
                                                         sticky='w', pady=10)
            var = tk.StringVar(value=str(self.config.get(key, default)))
            ttk.Entry(form_frame, textvariable=var, width=30).grid(
                row=i, column=1, sticky='w', padx=20, pady=10)
            self.setting_vars[key] = var

        ttk.Button(form_frame, text="💾 Save Settings",
                  style='Primary.TButton',
                  command=self.save_settings).grid(row=len(settings_config),
                                                   column=0, columnspan=2, pady=20)

    def create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side='bottom', fill='x')

        self.status_label = ttk.Label(status_frame, text="Ready", relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True)

        ttk.Label(status_frame, text="v3.0", relief='sunken').pack(side='right')

    def load_registered_users_fast(self):
        """
        FAST user loading - HOG only (no CNN to prevent hanging)
        This runs quickly without freezing the GUI
        """
        try:
            images_path = self.config.get('images_folder', 'registered_faces')
            if not os.path.exists(images_path):
                os.makedirs(images_path)
                self.update_status("No registered users")
                return

            self.known_encodings = []
            self.known_names = []
            self.known_user_ids = []

            print(f"\n{'=' * 60}")
            print(f"  LOADING REGISTERED USERS (FAST MODE)")
            print(f"{'=' * 60}")
            print(f"Looking in: {images_path}\n")

            loaded_count = 0
            failed_images = []

            image_files = [f for f in os.listdir(images_path)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

            for filename in image_files:
                img_path = os.path.join(images_path, filename)
                user_id = os.path.splitext(filename)[0]

                print(f"Processing: {filename}... ", end='', flush=True)

                # Load image
                img = cv2.imread(img_path)

                # Validate image
                if img is None:
                    print("✗ Cannot load")
                    failed_images.append((filename, "Cannot load image"))
                    continue

                if img.shape[0] < 100 or img.shape[1] < 100:
                    print("✗ Too small")
                    failed_images.append((filename, "Image too small"))
                    continue

                # Convert to RGB
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # FAST face detection - HOG only, single upsampling
                # This is MUCH faster than CNN and prevents freezing
                face_locations = face_recognition.face_locations(
                    rgb_img,
                    model='hog',  # HOG is fast
                    number_of_times_to_upsample=1  # Reduce upsamplings for speed
                )

                if not face_locations:
                    print("✗ No face")
                    failed_images.append((filename, "No face detected"))
                    continue

                # Get face encoding with minimal jitters (faster)
                try:
                    encodings = face_recognition.face_encodings(
                        rgb_img,
                        face_locations,
                        num_jitters=1  # Reduce from default 100 to 1 for speed
                    )

                    if not encodings:
                        print("✗ Cannot encode")
                        failed_images.append((filename, "Cannot encode face"))
                        continue

                except Exception as e:
                    print(f"✗ Error: {e}")
                    failed_images.append((filename, f"Encoding error: {e}"))
                    continue

                # Get user info from database
                user_info = self.db.get_user_info(user_id)

                if user_info:
                    name = user_info[1]
                    regno = user_info[2] if user_info[2] else 'N/A'
                else:
                    # Fallback: extract name from filename
                    if '_' in user_id:
                        parts = user_id.split('_', 1)
                        name = parts[1].replace('_', ' ').title()
                    else:
                        name = user_id.replace('_', ' ').title()
                    regno = 'N/A'

                # Add to known lists
                self.known_encodings.append(encodings[0])
                self.known_names.append(name)
                self.known_user_ids.append(user_id)

                print(f"✓ {name} ({regno})")
                loaded_count += 1

            print(f"\n{'=' * 60}")
            print(f"  RESULTS")
            print(f"{'=' * 60}")
            print(f"  ✓ Loaded: {loaded_count}")
            print(f"  ✗ Failed: {len(failed_images)}")

            if failed_images:
                print(f"\n  Failed images:")
                for img_name, reason in failed_images:
                    print(f"    - {img_name}: {reason}")

            print(f"{'=' * 60}\n")

            # Update UI
            self.update_status(f"Loaded {loaded_count} users")
            self.update_dashboard_stats()

            # Show result message
            if loaded_count == 0:
                if failed_images:
                    msg = f"⚠ No users loaded!\n\n"
                    msg += f"{len(failed_images)} image(s) failed face detection.\n\n"
                    msg += "Common issues:\n"
                    msg += "• Face not clearly visible\n"
                    msg += "• Poor lighting\n"
                    msg += "• Face too small in image\n"
                    msg += "• Image blurry or corrupted\n\n"
                    msg += "Solution: Delete failed images and re-register users."
                    messagebox.showwarning("No Users Loaded", msg)
                else:
                    messagebox.showinfo("No Users",
                                        "No registered users found.\nPlease register users first.")
            else:
                if hasattr(self, 'root') and self.root.winfo_exists():
                    # Only show success if there were users loaded
                    print(f"✓ Successfully loaded {loaded_count} user(s)")

        except Exception as e:
            print(f"✗ Error loading users: {e}")
            import traceback
            traceback.print_exc()
            self.update_status("Error loading users")

    def update_status(self, message="Ready"):
        """Update status bar"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)

    def update_dashboard_stats(self):
        """Update dashboard statistics"""
        try:
            if 'users' in self.stat_labels:
                self.stat_labels['users'].config(text=str(len(self.known_names)))

            today = datetime.datetime.now().strftime('%Y-%m-%d')
            today_records = self.db.get_attendance_records(date=today)
            if 'today' in self.stat_labels:
                self.stat_labels['today'].config(text=str(len(today_records)))

            if 'blocks' in self.stat_labels:
                self.stat_labels['blocks'].config(text=str(len(self.blockchain)))

        except Exception as e:
            print(f"Stats update error: {e}")

    def register_user_clicked(self):
        """Handle register user - FIXED"""
        # Create registration dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Register New User")
        dialog.geometry("450x400")
        dialog.configure(bg='#2c3e50')
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        # Form
        form_frame = ttk.Frame(dialog, padding=20)
        form_frame.pack(fill='both', expand=True)

        fields = {}

        ttk.Label(form_frame, text="Full Name:*",
                  font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=8)
        fields['name'] = ttk.Entry(form_frame, width=35, font=('Segoe UI', 10))
        fields['name'].grid(row=0, column=1, pady=8, padx=5)

        ttk.Label(form_frame, text="Registration Number:*",
                  font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=8)
        fields['regno'] = ttk.Entry(form_frame, width=35, font=('Segoe UI', 10))
        fields['regno'].grid(row=1, column=1, pady=8, padx=5)

        ttk.Label(form_frame, text="Email:",
                  font=('Segoe UI', 10)).grid(row=2, column=0, sticky='w', pady=8)
        fields['email'] = ttk.Entry(form_frame, width=35, font=('Segoe UI', 10))
        fields['email'].grid(row=2, column=1, pady=8, padx=5)

        ttk.Label(form_frame, text="Department:",
                  font=('Segoe UI', 10)).grid(row=3, column=0, sticky='w', pady=8)
        fields['department'] = ttk.Entry(form_frame, width=35, font=('Segoe UI', 10))
        fields['department'].grid(row=3, column=1, pady=8, padx=5)

        ttk.Label(form_frame, text="Phone:",
                  font=('Segoe UI', 10)).grid(row=4, column=0, sticky='w', pady=8)
        fields['phone'] = ttk.Entry(form_frame, width=35, font=('Segoe UI', 10))
        fields['phone'].grid(row=4, column=1, pady=8, padx=5)

        ttk.Label(form_frame, text="* Required fields",
                  foreground='red', font=('Segoe UI', 9)).grid(
            row=5, column=0, columnspan=2, pady=10)

        def submit():
            # READ ALL VALUES BEFORE DESTROYING DIALOG
            try:
                name = fields['name'].get().strip()
                regno = fields['regno'].get().strip()
                email = fields['email'].get().strip()
                department = fields['department'].get().strip()
                phone = fields['phone'].get().strip()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read form: {e}")
                return

            # Validate
            if not name or not regno:
                messagebox.showwarning("Missing Fields",
                                       "Name and Registration Number are required!")
                return

            # Validate registration number format
            if not regno.replace('-', '').replace('/', '').isalnum():
                messagebox.showwarning("Invalid Format",
                                       "Registration number can only contain letters, numbers, - and /")
                return

            # Close dialog AFTER reading values
            dialog.destroy()

            # Create user data dictionary
            user_data = {
                'name': name,
                'regno': regno,
                'email': email,
                'department': department,
                'phone': phone
            }

            # Show info message
            messagebox.showinfo("Starting Camera",
                                "Camera will open.\n\n" +
                                "• Position yourself in front of camera\n" +
                                "• Press 'S' to capture your face\n" +
                                "• Press 'Q' to cancel")

            # Start camera capture in thread
            threading.Thread(target=self.register_user_camera,
                             args=(user_data,), daemon=True).start()

        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="📸 Capture Face",
                   command=submit,
                   style='Primary.TButton',
                   width=15).pack(side='left', padx=5)

        ttk.Button(btn_frame, text="❌ Cancel",
                   command=dialog.destroy,
                   width=15).pack(side='left', padx=5)

        # Focus on name field
        fields['name'].focus()


    def register_user_camera(self, user_data):
        """Camera capture for registration - with validation"""
        try:
            name = user_data['name']
            regno = user_data['regno']
            user_id = f"{regno}_{name.lower().replace(' ', '_')}"

            # Check if regno exists
            existing = self.db.get_user_by_regno(regno)
            if existing:
                self.root.after(0, lambda: messagebox.showerror("Error",
                                                                f"Registration number {regno} already exists!"))
                return

            # Create images folder
            images_path = self.config.get('images_folder', 'registered_faces')
            os.makedirs(images_path, exist_ok=True)

            img_path = os.path.join(images_path, f"{user_id}.jpg")

            # Open camera
            camera_index = int(self.config.get('camera_index', 0))
            cap = cv2.VideoCapture(camera_index)

            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Camera Error",
                                                                f"Cannot access camera {camera_index}"))
                return

            # Set high quality
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Wait for camera to stabilize
            for _ in range(5):
                cap.read()

            self.update_status(f"Registering: {name}")

            print(f"\n{'=' * 60}")
            print(f"  REGISTERING: {name} ({regno})")
            print(f"{'=' * 60}")
            print("\nInstructions:")
            print("  • Look directly at camera")
            print("  • Ensure good lighting")
            print("  • Keep face in frame")
            print("  • Press 'S' to capture")
            print("  • Press 'Q' to cancel\n")

            captured = False
            face_encoding = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                # Detect face for visualization
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame, model='hog')

                # Draw face rectangle and guide
                display_frame = frame.copy()

                if face_locations:
                    for (top, right, bottom, left) in face_locations:
                        # Draw green rectangle around face
                        cv2.rectangle(display_frame, (left, top), (right, bottom),
                                      (0, 255, 0), 2)

                        # Check face size
                        face_width = right - left
                        face_height = bottom - top

                        if face_width < 150 or face_height < 150:
                            cv2.putText(display_frame, "Move Closer", (left, top - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                        else:
                            cv2.putText(display_frame, "Good! Press 'S'", (left, top - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    # Show warning if no face
                    cv2.putText(display_frame, "No Face Detected!", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Add registration info
                cv2.putText(display_frame, f"Registering: {name}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f"Reg No: {regno}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(display_frame, "Press 'S' to Save | 'Q' to Quit", (10,
                                                                               display_frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                cv2.imshow('Register User - SecureAttend', display_frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord('s') or key == ord('S'):
                    if not face_locations:
                        print("⚠ No face detected! Please position yourself properly.")
                        continue

                    if len(face_locations) > 1:
                        print("⚠ Multiple faces detected! Only one person should be in frame.")
                        continue

                    print("📸 Capturing face...")

                    # Save high-quality image
                    cv2.imwrite(img_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

                    # Validate saved image
                    is_valid, error_msg, encoding = self.validate_face_image(img_path)

                    if is_valid:
                        face_encoding = encoding
                        captured = True
                        print(f"✓ Face captured and validated")
                        print(f"✓ Saved to: {img_path}")
                        break
                    else:
                        print(f"✗ Validation failed: {error_msg}")
                        print("  Please try again")
                        os.remove(img_path)  # Remove invalid image

                elif key == ord('q') or key == ord('Q'):
                    print("❌ Registration cancelled")
                    break

            # Release camera
            cap.release()
            cv2.destroyAllWindows()

            if captured and face_encoding is not None:
                print("💾 Saving to database...")

                # Add to database
                success = self.db.add_user(
                    user_id=user_id,
                    name=name,
                    face_encoding=face_encoding,
                    registration_number=regno,
                    email=user_data.get('email') or None,
                    department=user_data.get('department') or None,
                    phone=user_data.get('phone') or None,
                    created_by='admin'
                )

                if success:
                    print("✓ Saved to database")

                    # Reload users (fast mode)
                    self.load_registered_users_fast()
                    self.root.after(0, self.refresh_users)
                    self.root.after(0, self.update_dashboard_stats)

                    # Show success
                    self.root.after(0, lambda: messagebox.showinfo("✅ Success",
                                                                   f"User registered successfully!\n\n" +
                                                                   f"Name: {name}\n" +
                                                                   f"Reg No: {regno}\n" +
                                                                   f"Department: {user_data.get('department', 'N/A')}"))

                    self.update_status(f"✓ Registered: {name}")
                    print(f"\n✅ Registration complete for {name} ({regno})\n")
                else:
                    print("✗ Database save failed")
                    self.root.after(0, lambda: messagebox.showerror("Error",
                                                                    "Failed to save to database"))
            else:
                self.update_status("Registration cancelled")

        except Exception as e:
            print(f"✗ Registration error: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("Error",
                                                            f"Registration failed:\n{str(e)}"))

    def start_attendance_clicked(self):
        """Start attendance tracking"""
        if self.attendance_running:
            messagebox.showinfo("Info", "Attendance is already running")
            return

        threading.Thread(target=self.start_attendance, daemon=True).start()

    def validate_face_image(self, img_path):
        """
        Validate if an image is suitable for face recognition
        Returns: (is_valid, error_message, face_encoding or None)
        """
        try:
            # Load image
            img = cv2.imread(img_path)

            if img is None:
                return False, "Cannot load image file", None

            # Check size
            height, width = img.shape[:2]
            if height < 200 or width < 200:
                return False, f"Image too small ({width}x{height}), need at least 200x200", None

            # Check brightness
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)

            if brightness < 40:
                return False, "Image too dark", None
            elif brightness > 220:
                return False, "Image too bright", None

            # Convert to RGB
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Detect face
            face_locations = face_recognition.face_locations(rgb_img, model='hog')

            if not face_locations:
                return False, "No face detected", None

            if len(face_locations) > 1:
                return False, f"Multiple faces detected ({len(face_locations)})", None

            # Check face size
            top, right, bottom, left = face_locations[0]
            face_width = right - left
            face_height = bottom - top

            if face_width < 80 or face_height < 80:
                return False, f"Face too small ({face_width}x{face_height})", None

            # Get encoding
            encodings = face_recognition.face_encodings(rgb_img, face_locations, num_jitters=1)

            if not encodings:
                return False, "Cannot create face encoding", None

            return True, "OK", encodings[0]

        except Exception as e:
            return False, f"Error: {str(e)}", None

    def start_attendance(self):
        """
        SMOOTH attendance tracking - NO FLICKERING
        Replace your existing start_attendance method with this complete version
        """
        try:
            self.attendance_running = True
            self.update_status("Starting attendance...")

            if not self.known_encodings:
                self.root.after(0, lambda: messagebox.showinfo("Info",
                                                               "No registered users. Please register users first."))
                self.attendance_running = False
                return

            # Initialize tracker for smooth detection
            tracker = AttendanceTracker()

            camera_index = int(self.config.get('camera_index', 0))
            cap = cv2.VideoCapture(camera_index)

            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Error",
                                                                "Cannot access camera"))
                self.attendance_running = False
                return

            # Set camera properties for smooth video
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.update_status("Attendance tracking active")

            self.liveness_detector.reset()
            self.emotion_detector.reset()

            print(f"\n{'=' * 70}")
            print("  ATTENDANCE TRACKING STARTED")
            print(f"{'=' * 70}")
            print("  Press 'Q' to stop")
            print(f"{'=' * 70}\n")

            # Process every N frames for face recognition (smoother)
            process_interval = 2  # Process every 2nd frame

            # Store detected faces for UI rendering
            detected_faces = {}  # face_id -> {name, bbox, status, liveness, etc.}

            while self.attendance_running:
                ret, frame = cap.read()
                if not ret:
                    print("⚠ Failed to read frame")
                    break

                tracker.increment_frame()

                # Create display frame
                display_frame = frame.copy()

                # === FACE DETECTION & RECOGNITION (every N frames) ===
                if tracker.frame_count % process_interval == 0:
                    # Resize for faster processing
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    # Detect faces
                    face_locations = face_recognition.face_locations(rgb_small, model='hog')
                    face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

                    # Clear old detections
                    current_detections = set()

                    for face_encoding, face_location in zip(face_encodings, face_locations):
                        # Scale back coordinates
                        top, right, bottom, left = [v * 2 for v in face_location]

                        # Match with known faces
                        matches = face_recognition.compare_faces(
                            self.known_encodings,
                            face_encoding,
                            tolerance=float(self.config.get('face_tolerance', 0.6))
                        )

                        face_distances = face_recognition.face_distance(
                            self.known_encodings,
                            face_encoding
                        )

                        if len(face_distances) > 0 and True in matches:
                            best_match_idx = np.argmin(face_distances)

                            if matches[best_match_idx]:
                                name = self.known_names[best_match_idx]
                                user_id = self.known_user_ids[best_match_idx]
                                confidence = round((1 - face_distances[best_match_idx]) * 100, 2)

                                # Get user info
                                user_info = self.db.get_user_info(user_id)
                                regno = user_info[2] if user_info and user_info[2] else 'N/A'

                                # ✅ ADD THIS ENTIRE BLOCK ✅
                                # === CHECK IF ALREADY MARKED TODAY IN DATABASE ===
                                today = datetime.datetime.now().strftime('%Y-%m-%d')
                                already_marked_in_db = False

                                # Check database for today's attendance
                                existing_records = self.db.get_attendance_records(date=today, user_id=user_id)
                                if existing_records:
                                    already_marked_in_db = True
                                    # Add to tracker's recognized list so we don't try to mark again
                                    tracker.recognized_today.add(user_id)
                                    print(f"ℹ️ {name} already marked today (found in database)")
                                # ✅ END OF NEW CODE ✅

                                # === ANTI-SPOOFING (with smoothing) ===
                                is_live = True
                                liveness_score = 1.0

                                if self.config.get('enable_antispoofing', True):
                                    is_live_raw, liveness_raw = self.liveness_detector.detect_liveness(
                                        frame, (top, right, bottom, left)
                                    )

                                    # Apply smoothing
                                    is_live, liveness_score = tracker.update_liveness_smooth(
                                        user_id, liveness_raw
                                    )

                                # Update detection tracker
                                is_stable = tracker.update_detection(user_id, True, liveness_score)

                                current_detections.add(user_id)

                                # Store detection info for rendering
                                detected_faces[user_id] = {
                                    'name': name,
                                    'regno': regno,
                                    'bbox': (top, right, bottom, left),
                                    'confidence': confidence,
                                    'is_live': is_live,
                                    'liveness_score': liveness_score,
                                    'is_stable': is_stable,
                                    'user_id': user_id,
                                    'face_encoding': face_encoding,
                                    'already_marked_in_db': already_marked_in_db
                                }

                                # === MARK ATTENDANCE (only if stable and live) ===
                                if is_stable and is_live and user_id not in tracker.recognized_today:
                                    # Emotion detection
                                    emotion = 'Neutral'
                                    engagement = 50.0

                                    if self.config.get('enable_emotion', True):
                                        face_region = frame[top:bottom, left:right]
                                        if face_region.size > 0:
                                            emotion, _ = self.emotion_detector.detect_emotion_simple(face_region)
                                            engagement = self.emotion_detector.calculate_engagement_score()

                                    # Prepare attendance data
                                    attendance_data = {
                                        'type': 'attendance',
                                        'user_id': user_id,
                                        'name': name,
                                        'registration_number': regno,
                                        'timestamp': datetime.datetime.now().isoformat(),
                                        'liveness_score': liveness_score,
                                        'confidence': confidence,
                                        'emotion': emotion,
                                        'engagement': engagement
                                    }

                                    # Add to blockchain
                                    blockchain_hash = 'N/A'
                                    if self.config.get('enable_blockchain', True):
                                        blockchain_hash = self.blockchain.add_block(attendance_data)

                                    # Mark in database
                                    success, msg = self.db.mark_attendance(
                                        user_id, name, regno, liveness_score, emotion,
                                        engagement, blockchain_hash, face_encoding,
                                        confidence / 100.0, "Main Campus"
                                    )

                                    if success:
                                        tracker.recognized_today.add(user_id)
                                        detected_faces[user_id]['just_marked'] = True  # Mark as JUST marked
                                        detected_faces[user_id]['mark_time'] = tracker.frame_count  # Track when marked
                                        self.update_status(f"✓ Attendance: {name} ({regno})")
                                        print(f"✓ Attendance marked: {name} ({regno}) - Live: {liveness_score:.2f}")

                    # Update detection states for users not currently detected
                    for user_id in list(detected_faces.keys()):
                        if user_id not in current_detections:
                            tracker.update_detection(user_id, False)

                    # Transition just_marked flag to blue after 3 seconds (90 frames at 30fps)
                    for uid in list(detected_faces.keys()):
                        if detected_faces[uid].get('just_marked', False):
                            mark_time = detected_faces[uid].get('mark_time', 0)
                            if tracker.frame_count - mark_time > 90:  # 3 seconds
                                detected_faces[uid]['just_marked'] = False

                # === RENDER UI (every frame - smooth) ===

                # Draw boxes for all detected/tracked faces
                for user_id, face_data in detected_faces.items():
                    if not tracker.should_display(user_id):
                        continue  # Skip if shouldn't display anymore

                    top, right, bottom, left = face_data['bbox']
                    name = face_data['name']
                    regno = face_data['regno']
                    is_live = face_data['is_live']
                    liveness_score = face_data['liveness_score']
                    confidence = face_data['confidence']

                  # Determine box color based on status
                    # Get the database flag
                    already_marked_in_db = face_data.get('already_marked_in_db', False)

                    # Determine box color based on status
                    if not is_live:
                        # SPOOFING - Red box
                        color = (0, 0, 255)
                        status_text = "⚠ SPOOFING DETECTED"
                        status_color = (0, 0, 255)
                    elif user_id in tracker.recognized_today or already_marked_in_db:  # ✅ MODIFIED
                        # Check if JUST marked or was ALREADY marked
                        if face_data.get('just_marked', False):
                            # JUST MARKED - Green box (stays green for 3 seconds)
                            color = (0, 255, 0)
                            status_text = "✓ ATTENDANCE MARKED"
                            status_color = (0, 255, 0)
                        else:
                            # ALREADY MARKED - Blue box
                            color = (255, 200, 0)  # Blue in BGR
                            status_text = "✓ ALREADY MARKED TODAY"
                            status_color = (255, 200, 0)
                    elif face_data.get('is_stable', False):
                        # VERIFYING - Orange box
                        color = (0, 165, 255)
                        status_text = "Verifying..."
                        status_color = (0, 165, 255)
                    else:
                        # DETECTING - Yellow box
                        color = (0, 255, 255)
                        status_text = "Detecting..."
                        status_color = (0, 255, 255)

                    # Draw main rectangle (thicker for visibility)
                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 3)

                    # Draw semi-transparent background for text
                    overlay = display_frame.copy()
                    cv2.rectangle(overlay, (left, top - 70), (right, top), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.6, display_frame, 0.4, 0, display_frame)

                    # Draw name
                    cv2.putText(display_frame, name, (left + 5, top - 45),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    # Draw registration number
                    cv2.putText(display_frame, f"Reg: {regno}", (left + 5, top - 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

                    # Draw liveness score
                    cv2.putText(display_frame, f"Live: {liveness_score:.2f}",
                                (left + 5, top - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

                    # Draw status below box
                    cv2.putText(display_frame, status_text, (left, bottom + 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

                    # Draw confidence
                    cv2.putText(display_frame, f"Conf: {confidence:.1f}%",
                                (left, bottom + 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # === DRAW HEADER INFO ===
                # Semi-transparent header background
                header_overlay = display_frame.copy()
                cv2.rectangle(header_overlay, (0, 0), (display_frame.shape[1], 100),
                              (0, 0, 0), -1)
                cv2.addWeighted(header_overlay, 0.7, display_frame, 0.3, 0, display_frame)

                # Title
                cv2.putText(display_frame, "SecureAttend - Live Attendance", (20, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

                # Stats
                cv2.putText(display_frame,
                            f"Recognized Today: {len(tracker.recognized_today)}",
                            (20, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Anti-spoofing indicator
                if self.config.get('enable_antispoofing', True):
                    cv2.putText(display_frame, "Anti-Spoofing: ACTIVE",
                                (20, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # === DRAW FOOTER INFO ===
                footer_y = display_frame.shape[0] - 20
                cv2.putText(display_frame, "Press 'Q' to exit", (20, footer_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Frame counter
                fps_text = f"Frame: {tracker.frame_count}"
                cv2.putText(display_frame, fps_text,
                            (display_frame.shape[1] - 150, footer_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Show frame
                cv2.imshow('SecureAttend - Attendance Tracking', display_frame)

                # Handle key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    print("\n⏹ Stopping attendance tracking...")
                    break

            # Cleanup
            cap.release()
            cv2.destroyAllWindows()

            print(f"\n{'=' * 70}")
            print("  ATTENDANCE TRACKING STOPPED")
            print(f"{'=' * 70}")
            print(f"  Total Recognized: {len(tracker.recognized_today)}")
            print(f"{'=' * 70}\n")

        except Exception as e:
            print(f"✗ Attendance error: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("Error",
                                                            f"Attendance tracking failed: {e}"))
        finally:
            self.attendance_running = False
            msg = f"Stopped. {len(tracker.recognized_today) if 'tracker' in locals() else 0} users recognized"
            self.update_status(msg)
            self.root.after(0, self.refresh_attendance)
            self.root.after(0, self.update_dashboard_stats)

    def refresh_attendance(self):
        """Refresh attendance records"""
        try:
            for item in self.attendance_tree.get_children():
                self.attendance_tree.delete(item)

            records = self.db.get_attendance_records(limit=100)

            for record in records:
                values = (
                    record[2],  # name
                    record[3] if record[3] else 'N/A',  # regno
                    record[5],  # date
                    record[6],  # time
                    f"{record[7]:.2f}" if record[7] else 'N/A',  # liveness
                    record[8] if record[8] else 'N/A',  # emotion
                    f"{record[9]:.1f}%" if record[9] else 'N/A',  # engagement
                )
                self.attendance_tree.insert('', 'end', values=values)

        except Exception as e:
            print(f"Refresh attendance error: {e}")

    def refresh_users(self):
        """Refresh users list"""
        try:
            for item in self.users_tree.get_children():
                self.users_tree.delete(item)

            users = self.db.get_all_users()

            for user in users:
                values = (
                    user[1],  # name
                    user[2] if user[2] else 'N/A',  # regno
                    user[4] if user[4] else 'N/A',  # department
                    user[8],  # total_attendance
                    user[9] if user[9] else 'Never'  # last_attendance
                )
                self.users_tree.insert('', 'end', values=values)

        except Exception as e:
            print(f"Refresh users error: {e}")

    def admin_refresh_users(self):
        """Refresh admin user list"""
        try:
            for item in self.admin_tree.get_children():
                self.admin_tree.delete(item)

            users = self.db.get_all_users(active_only=False)

            for user in users:
                values = (
                    user[0],  # user_id
                    user[1],  # name
                    user[2] if user[2] else 'N/A',  # regno
                    user[4] if user[4] else 'N/A',  # department
                    user[8],  # total_attendance
                    'Active' if user[9] == 1 else 'Inactive'  # status
                )
                self.admin_tree.insert('', 'end', values=values)

        except Exception as e:
            print(f"Admin refresh error: {e}")

    def admin_search_user(self):
        """Search user by name"""
        search_term = self.admin_search_var.get().strip().lower()
        if not search_term:
            self.admin_refresh_users()
            return

        for item in self.admin_tree.get_children():
            self.admin_tree.delete(item)

        users = self.db.get_all_users(active_only=False)
        for user in users:
            if search_term in user[1].lower():
                values = (
                    user[0], user[1],
                    user[2] if user[2] else 'N/A',
                    user[4] if user[4] else 'N/A',
                    user[8],
                    'Active' if user[9] == 1 else 'Inactive'
                )
                self.admin_tree.insert('', 'end', values=values)

    def admin_search_by_regno(self):
        """Search user by registration number"""
        regno = self.admin_search_var.get().strip()
        if not regno:
            self.admin_refresh_users()
            return

        user = self.db.get_user_by_regno(regno)

        for item in self.admin_tree.get_children():
            self.admin_tree.delete(item)

        if user:
            values = (
                user[0], user[1],
                user[2] if user[2] else 'N/A',
                user[4] if user[4] else 'N/A',
                user[8],
                'Active' if user[9] == 1 else 'Inactive'
            )
            self.admin_tree.insert('', 'end', values=values)
        else:
            messagebox.showinfo("Not Found", f"No user with Reg No: {regno}")

    def admin_delete_user(self):
        """Delete selected user"""
        selected = self.admin_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a user to delete")
            return

        item = self.admin_tree.item(selected[0])
        user_id = item['values'][0]
        name = item['values'][1]
        regno = item['values'][2]

        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to DELETE this user?\n\n" +
                                      f"Name: {name}\n" +
                                      f"Reg No: {regno}\n\n" +
                                      "This action CANNOT be undone!")

        if confirm:
            success = self.db.delete_user_permanently(user_id)

            if success:
                images_path = self.config.get('images_folder', 'registered_faces')
                img_path = os.path.join(images_path, f"{user_id}.jpg")
                if os.path.exists(img_path):
                    os.remove(img_path)

                self.load_registered_users()
                self.admin_refresh_users()
                self.update_dashboard_stats()

                messagebox.showinfo("Success", f"User '{name}' deleted")
                self.update_status(f"Deleted: {name}")
            else:
                messagebox.showerror("Error", "Failed to delete user")

    def admin_edit_user(self):
        """Edit user details"""
        selected = self.admin_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a user to edit")
            return

        item = self.admin_tree.item(selected[0])
        user_id = item['values'][0]

        user = self.db.get_user_info(user_id)
        if not user:
            messagebox.showerror("Error", "User not found")
            return

        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit User: {user[1]}")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()

        form_frame = ttk.Frame(dialog, padding=20)
        form_frame.pack(fill='both', expand=True)

        fields = {}

        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky='w', pady=5)
        fields['name'] = ttk.Entry(form_frame, width=30)
        fields['name'].insert(0, user[1])
        fields['name'].grid(row=0, column=1, pady=5)

        ttk.Label(form_frame, text="Email:").grid(row=1, column=0, sticky='w', pady=5)
        fields['email'] = ttk.Entry(form_frame, width=30)
        if user[3]:
            fields['email'].insert(0, user[3])
        fields['email'].grid(row=1, column=1, pady=5)

        ttk.Label(form_frame, text="Department:").grid(row=2, column=0, sticky='w', pady=5)
        fields['department'] = ttk.Entry(form_frame, width=30)
        if user[4]:
            fields['department'].insert(0, user[4])
        fields['department'].grid(row=2, column=1, pady=5)

        ttk.Label(form_frame, text="Phone:").grid(row=3, column=0, sticky='w', pady=5)
        fields['phone'] = ttk.Entry(form_frame, width=30)
        if user[5]:
            fields['phone'].insert(0, user[5])
        fields['phone'].grid(row=3, column=1, pady=5)

        def save_changes():
            try:
                conn = sqlite3.connect(self.db.db_file)
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE users 
                    SET name = ?, email = ?, department = ?, phone = ?
                    WHERE user_id = ?
                ''', (
                    fields['name'].get().strip(),
                    fields['email'].get().strip(),
                    fields['department'].get().strip(),
                    fields['phone'].get().strip(),
                    user_id
                ))

                conn.commit()
                conn.close()

                messagebox.showinfo("Success", "User details updated!")
                dialog.destroy()
                self.admin_refresh_users()
                self.load_registered_users()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to update: {e}")

        ttk.Button(form_frame, text="💾 Save",
                   command=save_changes,
                   style='Primary.TButton').grid(row=4, column=0, pady=20)

        ttk.Button(form_frame, text="Cancel",
                   command=dialog.destroy).grid(row=4, column=1, pady=20)

    def admin_view_history(self):
        """View user attendance history"""
        selected = self.admin_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a user")
            return

        item = self.admin_tree.item(selected[0])
        user_id = item['values'][0]
        name = item['values'][1]

        history_window = tk.Toplevel(self.root)
        history_window.title(f"History: {name}")
        history_window.geometry("800x500")

        ttk.Label(history_window, text=f"Attendance History for {name}",
                  font=('Segoe UI', 12, 'bold')).pack(pady=20)

        history = self.db.get_user_attendance_history(user_id, limit=100)

        table_frame = ttk.Frame(history_window)
        table_frame.pack(fill='both', expand=True, padx=20, pady=10)

        columns = ('Date', 'Time', 'Liveness', 'Emotion', 'Engagement')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor='center')

        for record in history:
            values = (
                record[0],
                record[1],
                f"{record[2]:.2f}" if record[2] else 'N/A',
                record[3] if record[3] else 'N/A',
                f"{record[4]:.1f}%" if record[4] else 'N/A'
            )
            tree.insert('', 'end', values=values)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def refresh_blockchain(self):
        """Refresh blockchain display"""
        try:
            self.blockchain_text.delete(1.0, tk.END)

            self.blockchain_text.insert(tk.END, "=" * 80 + "\n")
            self.blockchain_text.insert(tk.END, "BLOCKCHAIN ATTENDANCE RECORDS\n")
            self.blockchain_text.insert(tk.END, "=" * 80 + "\n\n")

            for block in self.blockchain.chain:
                self.blockchain_text.insert(tk.END, f"Block #{block.index}\n")
                self.blockchain_text.insert(tk.END, f"Timestamp: {block.timestamp}\n")
                self.blockchain_text.insert(tk.END, f"Hash: {block.hash[:16]}...\n")
                self.blockchain_text.insert(tk.END, f"Nonce: {block.nonce}\n")

                import json
                self.blockchain_text.insert(tk.END,
                                            f"Data: {json.dumps(block.data, indent=2)}\n")
                self.blockchain_text.insert(tk.END, "-" * 80 + "\n\n")

            self.bc_info_label.config(
                text=f"Total Blocks: {len(self.blockchain)} | " +
                     f"Valid: {self.blockchain.is_chain_valid()}")

        except Exception as e:
            print(f"Blockchain refresh error: {e}")

    def verify_blockchain_clicked(self):
        """Verify blockchain integrity"""
        is_valid = self.blockchain.is_chain_valid()

        if is_valid:
            messagebox.showinfo("Blockchain Verification",
                                "✅ Blockchain is VALID!\n\nAll blocks are properly chained.")
        else:
            messagebox.showerror("Blockchain Verification",
                                 "❌ Blockchain has been TAMPERED!")

    def export_attendance(self):
        """Export attendance to CSV"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Attendance"
            )

            if file_path:
                self.db.export_to_csv(file_path)
                messagebox.showinfo("Success", f"Exported to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def save_settings(self):
        """Save configuration settings"""
        try:
            for key in ['camera_index', 'face_tolerance', 'liveness_threshold']:
                if key in self.setting_vars:
                    value = self.setting_vars[key].get()
                    # store numeric values appropriately
                    if '.' in value:
                        self.config.set(key, float(value))
                    else:
                        # camera_index is integer; other integer-like settings will be saved as int
                        try:
                            self.config.set(key, int(value))
                        except ValueError:
                            # fallback to string if not convertible
                            self.config.set(key, value)

            messagebox.showinfo("Success", "Settings saved!")
            self.update_status("Settings updated")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def run(self):
        """Run the application"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"Application error: {e}")

    def on_closing(self):
        """Handle window closing"""
        if self.attendance_running:
            if messagebox.askokcancel("Quit", "Attendance is running. Quit anyway?"):
                self.attendance_running = False
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    try:
        app = SecureAttendApp()
        app.run()
    except Exception as e:
        print(f"Startup error: {e}")
        import traceback
        traceback.print_exc()
