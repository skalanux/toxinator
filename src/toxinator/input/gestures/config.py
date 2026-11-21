"""Gesture tuning constants.

Values are the starting point from ``docs/design/gestures.md``; they get
adjusted in the ``toxinator dev gestures`` lab against real traces, so keep
them here rather than inline.
"""

from __future__ import annotations

# Tilt / steer posture
TILT_DEADZONE = 3.0          # degrees
TILT_SATURATION = 30.0       # degrees
TILT_CUTOFF = 0.4            # degrees, below which the posture reads as zero
TILT_SMOOTH_TAU = 0.060      # seconds, EMA time constant
STEER_SATURATION = 25.0      # degrees
STEER_EXPO = 1.4

# Flick
FLICK_START = 11.8           # m/s² (1.2 g)
FLICK_RELEASE = 3.4          # m/s² (0.35 g)
FLICK_WINDOW = 0.150         # seconds
FLICK_MAX = 34.4             # m/s² (3.5 g) -> intensity 1.0
FLICK_AMBIGUITY = 0.70
FLICK_COOLDOWN = 0.300       # seconds

# Swing
SWING_START = 180.0          # deg/s
SWING_END = 90.0             # deg/s
SWING_MIN = 0.080            # seconds
SWING_INTENSITY = 360.0      # degrees -> intensity 1.0
SWING_COOLDOWN = 0.400       # seconds

# Twist
TWIST_START = 60.0           # deg/s
TWIST_ANGLE = 40.0           # degrees
TWIST_WINDOW = 0.500         # seconds
TWIST_INTENSITY = 120.0      # degrees -> intensity 1.0
TWIST_COOLDOWN = 0.300       # seconds

# Shake
SHAKE_RATE = 120.0           # deg/s
SHAKE_REVERSALS = 3
SHAKE_WINDOW = 0.700         # seconds
SHAKE_COOLDOWN = 0.800       # seconds

# Flip
FLIP_ANGLE = 140.0           # degrees
FLIP_WINDOW = 0.600          # seconds
FLIP_INTENSITY = 180.0       # degrees -> intensity 1.0
FLIP_COOLDOWN = 0.800        # seconds

# Aim
AIM_DEADZONE = 6.0           # deg/s
AIM_FOV = 60.0               # degrees to traverse the screen
AIM_SENSITIVITY = 1.0
AIM_SENSITIVITY_MIN = 0.4
AIM_SENSITIVITY_MAX = 2.5

# Recognizer state
BUFFER_SECONDS = 0.5         # seconds of history kept per recognizer
EVENT_QUEUE = 32             # pending gestures per slot
