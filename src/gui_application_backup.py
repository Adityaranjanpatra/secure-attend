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
        self.load_registered_users()

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

    def load_registered_users(self):
        """Load registered users - FIXED with better error handling"""
        try:
            images_path = self.config.get('images_folder', 'registered_faces')
            if not os.path.exists(images_path):
                os.makedirs(images_path)
                return

            self.known_encodings = []
            self.known_names = []
            self.known_user_ids = []

            print(f"\n{'=' * 60}")
            print(f"  LOADING REGISTERED USERS")
            print(f"{'=' * 60}")
            print(f"Looking in: {images_path}\n")

            # Get all users from database
            all_users = self.db.get_all_users()
            print(f"Found {len(all_users)} users in database")

            loaded_count = 0
            failed_images = []

            for filename in os.listdir(images_path):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(images_path, filename)
                    user_id = os.path.splitext(filename)[0]  # Remove extension

                    print(f"Processing: {filename}")

                    # Load image with better error handling
                    img = cv2.imread(img_path)

                    if img is None:
                        print(f"  ✗ Could not load image")
                        failed_images.append((filename, "Failed to load image file"))
                        continue

                    # Check if image is too small
                    if img.shape[0] < 100 or img.shape[1] < 100:
                        print(f"  ✗ Image too small: {img.shape}")
                        failed_images.append((filename, f"Image too small: {img.shape}"))
                        continue

                    # Get face encoding with multiple detection attempts
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    # Try both HOG and CNN models
                    face_locations = face_recognition.face_locations(rgb_img, model='hog')

                    if not face_locations:
                        # Try with CNN model (more accurate but slower)
                        print(f"  ⚠ HOG failed, trying CNN model...")
                        face_locations = face_recognition.face_locations(rgb_img, model='cnn')

                    if not face_locations:
                        # Try with different number of upsamplings
                        print(f"  ⚠ Trying with more upsamplings...")
                        face_locations = face_recognition.face_locations(rgb_img, number_of_times_to_upsample=2)

                    if not face_locations:
                        print(f"  ✗ No face detected after multiple attempts")
                        failed_images.append((filename, "No face detected in image"))
                        continue

                    # Get face encodings
                    encodings = face_recognition.face_encodings(rgb_img, face_locations)

                    if not encodings:
                        print(f"  ✗ Could not encode face")
                        failed_images.append((filename, "Could not encode face"))
                        continue

                    # Find user in database to get correct name
                    user_info = self.db.get_user_info(user_id)

                    if user_info:
                        name = user_info[1]  # Get name from database
                        regno = user_info[2] if user_info[2] else 'N/A'
                        print(f"  ✓ Loaded: {name} (Reg: {regno})")
                    else:
                        # Fallback: extract name from filename
                        if '_' in user_id:
                            parts = user_id.split('_', 1)
                            name = parts[1].replace('_', ' ').title()
                        else:
                            name = user_id.replace('_', ' ').title()
                        print(f"  ✓ Loaded: {name} (not in database)")

                    # Add to known lists
                    self.known_encodings.append(encodings[0])
                    self.known_names.append(name)
                    self.known_user_ids.append(user_id)
                    loaded_count += 1

            print(f"\n{'=' * 60}")
            print(f"  TOTAL LOADED: {loaded_count} users")

            if failed_images:
                print(f"  FAILED: {len(failed_images)} images")
                print(f"\n  Failed Images:")
                for img_name, reason in failed_images:
                    print(f"    - {img_name}: {reason}")

            print(f"{'=' * 60}\n")

            self.update_status(f"Loaded {loaded_count} users ({len(failed_images)} failed)")

            if loaded_count == 0:
                print("⚠ WARNING: No users loaded!")
                print(f"Check if valid face images exist in: {os.path.abspath(images_path)}")
                if failed_images:
                    print("\nTroubleshooting:")
                    print("1. Ensure face is clearly visible in photos")
                    print("2. Face should be well-lit and front-facing")
                    print("3. Image resolution should be at least 200x200 pixels")
                    print("4. Try recapturing the face photo")

        except Exception as e:
            print(f"✗ Error loading users: {e}")
            import traceback
            traceback.print_exc()

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
        """Camera capture for registration - FIXED"""
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
            if not os.path.exists(images_path):
                os.makedirs(images_path)

            img_path = os.path.join(images_path, f"{user_id}.jpg")

            # Open camera
            camera_index = int(self.config.get('camera_index', 0))
            cap = cv2.VideoCapture(camera_index)

            # Try multiple times if camera doesn't open immediately
            if not cap.isOpened():
                for i in range(3):
                    print(f"Trying to open camera... Attempt {i + 1}")
                    cap = cv2.VideoCapture(camera_index)
                    if cap.isOpened():
                        break
                    import time
                    time.sleep(1)

            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Camera Error",
                                                                f"Cannot access camera {camera_index}.\n\n" +
                                                                "Try:\n" +
                                                                "1. Check if camera is connected\n" +
                                                                "2. Close other apps using camera\n" +
                                                                "3. Change camera_index in settings"))
                return

            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            self.update_status(f"Registering: {name}")

            print(f"\n{'=' * 60}")
            print(f"  CAMERA READY - Registering: {name}")
            print(f"  Registration Number: {regno}")
            print(f"{'=' * 60}")
            print("\nInstructions:")
            print("  • Look directly at the camera")
            print("  • Press 'S' to capture your face")
            print("  • Press 'Q' to cancel registration")
            print(f"\n{'=' * 60}\n")

            captured = False
            face_encoding = None
            attempts = 0
            max_attempts = 100  # Allow 100 frames before timeout

            while attempts < max_attempts:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read frame from camera")
                    attempts += 1
                    continue

                attempts += 1

                # Add registration info overlay
                cv2.putText(frame, f"Registering: {name}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"Reg No: {regno}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, "Press 'S' to Save", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(frame, "Press 'Q' to Quit", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                # Detect face in current frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)

                # Draw rectangle if face detected
                if face_locations:
                    top, right, bottom, left = face_locations[0]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, "Face Detected ✓", (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "No Face Detected ✗", (10, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # Show frame
                cv2.imshow('Register User - SecureAttend', frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord('s') or key == ord('S'):
                    if not face_locations:
                        print("⚠ No face detected! Please look at the camera and try again.")
                        continue

                    print("Capturing face...")

                    # Get face encoding
                    encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                    if encodings:
                        # Save image
                        cv2.imwrite(img_path, frame)
                        face_encoding = encodings[0]
                        captured = True
                        print(f"✓ Face captured successfully for {name}")
                        print(f"✓ Image saved to: {img_path}")
                        break
                    else:
                        print("⚠ Could not encode face. Please try again.")

                elif key == ord('q') or key == ord('Q'):
                    print("Registration cancelled by user")
                    break

            # Release camera
            cap.release()
            cv2.destroyAllWindows()

            if captured and face_encoding is not None:
                print("Saving to database...")

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
                    print("✓ User saved to database")

                    # Reload users
                    self.load_registered_users()
                    self.root.after(0, self.refresh_users)
                    self.root.after(0, self.update_dashboard_stats)

                    # Show success message
                    self.root.after(0, lambda: messagebox.showinfo("✅ Success",
                                                                   f"User registered successfully!\n\n" +
                                                                   f"Name: {name}\n" +
                                                                   f"Registration Number: {regno}\n" +
                                                                   f"Department: {user_data.get('department', 'N/A')}"))

                    self.update_status(f"✓ Registered: {name} ({regno})")
                else:
                    print("✗ Failed to save user to database")
                    self.root.after(0, lambda: messagebox.showerror("Error",
                                                                    "Failed to save user to database!"))
            else:
                print("Registration incomplete or cancelled")
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

    def start_attendance(self):
        """Main attendance tracking"""
        try:
            self.attendance_running = True
            self.update_status("Starting attendance...")

            if not self.known_encodings:
                self.root.after(0, lambda: messagebox.showinfo("Info",
                                                               "No registered users. Please register users first."))
                self.attendance_running = False
                return

            camera_index = int(self.config.get('camera_index', 0))
            cap = cv2.VideoCapture(camera_index)

            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Error",
                                                                 "Cannot access camera"))
                self.attendance_running = False
                return

            self.update_status("Attendance tracking active")
            recognized_today = set()
            frame_count = 0

            self.liveness_detector.reset()
            self.emotion_detector.reset()

            print("Attendance started. Press 'Q' to stop.")

            while self.attendance_running:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                if frame_count % 3 != 0:
                    cv2.imshow('SecureAttend - Attendance', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    continue

                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small)
                face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

                for face_encoding, face_location in zip(face_encodings, face_locations):
                    top, right, bottom, left = [v * 2 for v in face_location]

                    face_distances = face_recognition.face_distance(
                        self.known_encodings, face_encoding)

                    if len(face_distances) > 0:
                        best_match_idx = np.argmin(face_distances)
                        confidence = round((1 - face_distances[best_match_idx]) * 100, 2)

                        tolerance = float(self.config.get('face_tolerance', 0.6))

                        if face_distances[best_match_idx] < tolerance:
                            name = self.known_names[best_match_idx]
                            user_id = self.known_user_ids[best_match_idx]

                            # Get user info
                            user_info = self.db.get_user_info(user_id)
                            regno = user_info[2] if user_info and user_info[2] else 'N/A'

                            # Anti-spoofing
                            is_live = True
                            liveness_score = 1.0

                            if self.config.get('enable_antispoofing', True):
                                is_live, liveness_score = self.liveness_detector.detect_liveness(
                                    frame, (top, right, bottom, left))

                                if not is_live:
                                    cv2.putText(frame, "⚠ SPOOFING DETECTED!", (10, 60),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                                    cv2.rectangle(frame, (left, top), (right, bottom),
                                                  (0, 0, 255), 3)
                                    continue

                            # Emotion detection
                            emotion = 'Neutral'
                            engagement = 50.0

                            if self.config.get('enable_emotion', True):
                                face_region = frame[top:bottom, left:right]
                                if face_region.size > 0:
                                    emotion, _ = self.emotion_detector.detect_emotion_simple(face_region)
                                    engagement = self.emotion_detector.calculate_engagement_score()

                            # Draw on frame
                            color = (0, 255, 0)
                            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

                            cv2.putText(frame, f"{name}", (left, top - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                            cv2.putText(frame, f"Reg: {regno}", (left, top - 35),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                            cv2.putText(frame, f"Live: {liveness_score:.2f}", (left, bottom + 20),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

                            # Mark attendance
                            if user_id not in recognized_today:
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
                                    recognized_today.add(user_id)
                                    self.update_status(f"✓ Attendance: {name} ({regno})")
                                    print(f"✓ Attendance marked: {name} ({regno})")

                cv2.putText(frame, f"Recognized Today: {len(recognized_today)}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Press 'Q' to exit", (10, frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

                if self.config.get('enable_antispoofing', True):
                    cv2.putText(frame, "🛡️ Anti-Spoofing: ACTIVE",
                                (10, frame.shape[0] - 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.imshow('SecureAttend - Attendance', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

        except Exception as e:
            print(f"Attendance error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error",
                                                            f"Attendance tracking failed: {e}"))
        finally:
            self.attendance_running = False
            msg = f"Stopped. {len(recognized_today) if 'recognized_today' in locals() else 0} users"
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
