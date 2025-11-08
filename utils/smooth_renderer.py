#!/usr/bin/env python3
"""
Smooth UI Renderer for Attendance System
Prevents flickering with animation and state interpolation
"""

import cv2
import numpy as np
from collections import deque
from typing import Dict, Tuple, Optional


class SmoothUIRenderer:
    """
    Handles smooth UI rendering with animation and anti-flicker
    """

    def __init__(self):
        # Color schemes
        self.colors = {
            'live': (0, 255, 0),  # Green
            'spoofing': (0, 0, 255),  # Red
            'verifying': (255, 165, 0),  # Orange
            'detecting': (0, 255, 255),  # Yellow
            'marked': (0, 200, 0)  # Dark green
        }

        # Animation states
        self.box_states = {}  # user_id -> animation state
        self.fade_speed = 0.15  # How fast colors transition
        self.scale_speed = 0.1  # How fast boxes scale

        # Text backgrounds
        self.text_bg_alpha = 0.7

    def interpolate_color(self, color1: Tuple, color2: Tuple, t: float) -> Tuple:
        """Smoothly interpolate between two colors"""
        return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))

    def get_or_create_state(self, user_id: str, target_status: str) -> Dict:
        """Get or create animation state for a user"""
        if user_id not in self.box_states:
            self.box_states[user_id] = {
                'current_color': self.colors[target_status],
                'target_color': self.colors[target_status],
                'alpha': 0.0,  # Start invisible
                'scale': 0.8,  # Start small
                'pulse_phase': 0.0
            }

        state = self.box_states[user_id]
        state['target_color'] = self.colors[target_status]

        return state

    def update_animation(self, user_id: str) -> Dict:
        """Update animation state for smooth transitions"""
        if user_id not in self.box_states:
            return None

        state = self.box_states[user_id]

        # Fade in
        if state['alpha'] < 1.0:
            state['alpha'] = min(1.0, state['alpha'] + self.fade_speed)

        # Scale up
        if state['scale'] < 1.0:
            state['scale'] = min(1.0, state['scale'] + self.scale_speed)

        # Color transition
        current = state['current_color']
        target = state['target_color']

        if current != target:
            state['current_color'] = self.interpolate_color(
                current, target, self.fade_speed
            )

        # Pulse animation
        state['pulse_phase'] = (state['pulse_phase'] + 0.1) % (2 * np.pi)

        return state

    def draw_smooth_box(self, frame: np.ndarray, bbox: Tuple,
                        user_id: str, status: str,
                        info: Dict) -> np.ndarray:
        """
        Draw a smooth, non-flickering box with info

        Args:
            frame: Input frame
            bbox: (top, right, bottom, left)
            user_id: User identifier
            status: 'live', 'spoofing', 'verifying', 'detecting', 'marked'
            info: Dict with name, regno, confidence, liveness, etc.
        """
        top, right, bottom, left = bbox

        # Get/update animation state
        state = self.get_or_create_state(user_id, status)
        state = self.update_animation(user_id)

        if state is None:
            return frame

        # Apply alpha blending
        overlay = frame.copy()

        # Get current color
        color = state['current_color']
        alpha = state['alpha']

        # Pulse effect for certain statuses
        if status in ['verifying', 'detecting']:
            pulse = 0.2 * np.sin(state['pulse_phase'])
            thickness = int(3 + pulse * 2)
        else:
            thickness = 3

        # Draw main rectangle
        cv2.rectangle(overlay, (left, top), (right, bottom), color, thickness)

        # Draw corner accents (modern look)
        corner_length = 20
        accent_color = tuple(min(c + 50, 255) for c in color)

        # Top-left
        cv2.line(overlay, (left, top), (left + corner_length, top), accent_color, 4)
        cv2.line(overlay, (left, top), (left, top + corner_length), accent_color, 4)

        # Top-right
        cv2.line(overlay, (right, top), (right - corner_length, top), accent_color, 4)
        cv2.line(overlay, (right, top), (right, top + corner_length), accent_color, 4)

        # Bottom-left
        cv2.line(overlay, (left, bottom), (left + corner_length, bottom), accent_color, 4)
        cv2.line(overlay, (left, bottom), (left, bottom - corner_length), accent_color, 4)

        # Bottom-right
        cv2.line(overlay, (right, bottom), (right - corner_length, bottom), accent_color, 4)
        cv2.line(overlay, (right, bottom), (right, bottom - corner_length), accent_color, 4)

        # Apply alpha blending
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha * 0.3, 0, frame)

        # Draw info panel with smooth background
        self.draw_info_panel(frame, bbox, info, color, alpha)

        return frame

    def draw_info_panel(self, frame: np.ndarray, bbox: Tuple,
                        info: Dict, color: Tuple, alpha: float):
        """Draw information panel above the box"""
        top, right, bottom, left = bbox

        # Calculate panel dimensions
        panel_height = 85
        panel_top = max(0, top - panel_height)

        # Draw semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (left, panel_top), (right, top), (0, 0, 0), -1)
        cv2.addWeighted(overlay, self.text_bg_alpha * alpha, frame,
                        1 - self.text_bg_alpha * alpha, 0, frame)

        # Draw colored top border
        cv2.line(frame, (left, panel_top), (right, panel_top), color, 2)

        # Text positions
        text_x = left + 8
        line_height = 20
        current_y = panel_top + line_height

        # Draw name (bold)
        name = info.get('name', 'Unknown')
        cv2.putText(frame, name, (text_x, current_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        current_y += line_height

        # Draw registration number
        regno = info.get('regno', 'N/A')
        cv2.putText(frame, f"Reg: {regno}", (text_x, current_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
        current_y += line_height

        # Draw liveness
        liveness = info.get('liveness_score', 0.0)
        liveness_color = (0, 255, 0) if liveness >= 0.7 else (0, 165, 255)
        cv2.putText(frame, f"Live: {liveness:.2f}", (text_x, current_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, liveness_color, 1)

        # Draw confidence on same line
        conf = info.get('confidence', 0.0)
        cv2.putText(frame, f"Conf: {conf:.1f}%", (text_x + 90, current_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    def draw_status_badge(self, frame: np.ndarray, bbox: Tuple,
                          status: str, user_id: str):
        """Draw status badge below the box"""
        top, right, bottom, left = bbox

        status_messages = {
            'live': '✓ VERIFIED',
            'spoofing': '⚠ SPOOFING',
            'verifying': '⏳ VERIFYING',
            'detecting': '🔍 DETECTING',
            'marked': '✓ MARKED'
        }

        message = status_messages.get(status, status.upper())

        state = self.box_states.get(user_id)
        if state:
            alpha = state['alpha']
            color = state['current_color']

            # Badge position
            badge_y = bottom + 30
            text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX,
                                        0.6, 2)[0]

            # Draw badge background
            padding = 10
            badge_left = left
            badge_right = left + text_size[0] + padding * 2
            badge_top = badge_y - text_size[1] - padding
            badge_bottom = badge_y + padding

            overlay = frame.copy()
            cv2.rectangle(overlay, (badge_left, badge_top),
                          (badge_right, badge_bottom), color, -1)
            cv2.addWeighted(overlay, 0.8 * alpha, frame, 1 - 0.8 * alpha, 0, frame)

            # Draw text
            cv2.putText(frame, message, (left + padding, badge_y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def cleanup_old_states(self, active_user_ids: set):
        """Remove animation states for users no longer visible"""
        to_remove = [uid for uid in self.box_states if uid not in active_user_ids]
        for uid in to_remove:
            del self.box_states[uid]

    def draw_header(self, frame: np.ndarray, stats: Dict) -> np.ndarray:
        """Draw header with stats"""
        height = 110

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Gradient effect at bottom
        for i in range(10):
            alpha = 0.1 - (i * 0.01)
            y = height + i
            cv2.line(frame, (0, y), (frame.shape[1], y), (0, 0, 0), 1)

        # Title
        cv2.putText(frame, "SecureAttend", (25, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

        cv2.putText(frame, "Live Attendance Tracking", (25, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Stats on right
        recognized = stats.get('recognized', 0)
        cv2.putText(frame, f"Recognized: {recognized}", (25, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Anti-spoofing indicator
        if stats.get('antispoofing', False):
            shield_x = frame.shape[1] - 280
            cv2.putText(frame, "🛡️ Anti-Spoofing", (shield_x, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, "ACTIVE", (shield_x + 30, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return frame

    def draw_footer(self, frame: np.ndarray, info: Dict) -> np.ndarray:
        """Draw footer with instructions"""
        height = 50
        y_start = frame.shape[0] - height

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, y_start), (frame.shape[1], frame.shape[0]),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Instructions
        cv2.putText(frame, "Press 'Q' to exit", (25, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # FPS/Frame counter
        frame_info = info.get('frame', 0)
        cv2.putText(frame, f"Frame: {frame_info}",
                    (frame.shape[1] - 150, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return frame

