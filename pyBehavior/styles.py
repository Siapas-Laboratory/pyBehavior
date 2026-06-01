"""
pyBehavior UI styles
====================
A unified dark-theme stylesheet inspired by precision scientific instruments.
Palette: deep charcoal backgrounds, warm amber accents, cool slate panels.
"""

# ── Palette ────────────────────────────────────────────────────────────────
BG_DEEP    = "#1a1d23"   # main window background
BG_PANEL   = "#22262f"   # card / groupbox backgrounds
BG_SURFACE = "#2a2f3a"   # inputs, tabs, inner surfaces
BG_HOVER   = "#313748"   # hover over buttons / rows

ACCENT     = "#e8a225"   # warm amber – primary interactive colour
ACCENT_DIM = "#a06c10"   # pressed / active variant
ACCENT_SOFT= "#3d2e0a"   # very subtle amber tint (checkbox fill etc.)

TEXT_PRIMARY   = "#e8eaf0"  # main readable text
TEXT_SECONDARY = "#8b92a8"  # labels, hints
TEXT_DISABLED  = "#4a5068"  # disabled controls
TEXT_ACCENT    = "#e8a225"  # accent-coloured text

BORDER_SUBTLE  = "#353b4a"  # hairline separators
BORDER_ACTIVE  = "#e8a225"  # focused / selected border

SUCCESS = "#4caf7d"   # green – positive states
DANGER  = "#e05252"   # red – destructive / stop
WARNING = "#e8a225"   # amber – caution / pause

MONO_FONT = "\"Courier New\", \"Consolas\", monospace"
UI_FONT   = "\"Segoe UI\", \"Helvetica Neue\", \"Arial\", sans-serif"

# ── Stylesheet ──────────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRIMARY};
    font-family: {UI_FONT};
    font-size: 12px;
}}

QMainWindow, QDialog {{
    background-color: {BG_DEEP};
}}

/* ── Labels ───────────────────────────────────────────────────────────── */
QLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    background: transparent;
    padding: 0 2px;
}}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
    padding: 5px 12px;
    font-size: 12px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT};
    color: {TEXT_PRIMARY};
}}
QPushButton:pressed {{
    background-color: {ACCENT_DIM};
    border-color: {ACCENT};
    color: {BG_DEEP};
}}
QPushButton:checked {{
    background-color: {ACCENT_SOFT};
    border-color: {ACCENT};
    color: {ACCENT};
}}
QPushButton:disabled {{
    background-color: {BG_PANEL};
    color: {TEXT_DISABLED};
    border-color: {BORDER_SUBTLE};
}}

/* Start / stop / pause semantic colouring */
QPushButton#start_btn {{
    background-color: #1c3320;
    color: {SUCCESS};
    border-color: {SUCCESS};
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton#start_btn:hover  {{ background-color: #24402c; }}
QPushButton#start_btn:checked {{ background-color: #1c3320; }}

QPushButton#stop_btn {{
    background-color: #2e1a1a;
    color: {DANGER};
    border-color: {DANGER};
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton#stop_btn:hover {{ background-color: #3d2020; }}

QPushButton#pause_btn {{
    background-color: {ACCENT_SOFT};
    color: {WARNING};
    border-color: {WARNING};
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton#pause_btn:hover  {{ background-color: #4d3610; }}
QPushButton#pause_btn:checked {{
    background-color: #4d3610;
    color: {TEXT_PRIMARY};
}}

/* ── Line Edits ───────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 3px;
    padding: 3px 7px;
    font-family: {MONO_FONT};
    font-size: 12px;
    selection-background-color: {ACCENT_DIM};
    selection-color: {BG_DEEP};
    min-height: 22px;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
    background-color: {BG_HOVER};
}}
QLineEdit:disabled {{
    background-color: {BG_PANEL};
    color: {TEXT_ACCENT};
    border-color: {BORDER_SUBTLE};
    font-family: {MONO_FONT};
}}
QLineEdit:read-only {{
    color: {TEXT_ACCENT};
    font-family: {MONO_FONT};
}}

/* ── Combo Box ────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 3px;
    padding: 3px 7px;
    font-size: 12px;
    min-height: 24px;
}}
QComboBox:hover  {{ border-color: {ACCENT}; background-color: {BG_HOVER}; }}
QComboBox:focus  {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    margin-right: 5px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT};
    outline: none;
}}

/* ── Spin Box ─────────────────────────────────────────────────────────── */
QSpinBox {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 3px;
    padding: 3px 7px;
    font-family: {MONO_FONT};
    min-height: 22px;
}}
QSpinBox:focus {{ border-color: {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {BG_HOVER};
    border: none;
    width: 16px;
}}
QSpinBox::up-arrow  {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid {TEXT_SECONDARY}; }}
QSpinBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {TEXT_SECONDARY}; }}

/* ── Group Box ────────────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    margin-top: 18px;
    padding: 8px 6px 6px 6px;
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {ACCENT};
    background-color: {BG_PANEL};
    letter-spacing: 1px;
}}

/* ── Tab Widget ───────────────────────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 0 4px 4px 4px;
}}
QTabBar::tab {{
    background-color: {BG_DEEP};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_SUBTLE};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 14px;
    margin-right: 2px;
    font-size: 11px;
    letter-spacing: 0.5px;
}}
QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {ACCENT};
    border-color: {BORDER_SUBTLE};
    border-bottom-color: {BG_PANEL};
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

/* ── Check Box ────────────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_SECONDARY};
    spacing: 6px;
    font-size: 12px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 3px;
    background: {BG_SURFACE};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

/* ── Scroll Area / Scroll Bar ─────────────────────────────────────────── */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_SUBTLE};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {BG_PANEL};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_SUBTLE};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT_DIM}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── List Widget ──────────────────────────────────────────────────────── */
QListWidget {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
    outline: none;
    font-size: 12px;
}}
QListWidget::item {{ padding: 6px 10px; border-radius: 3px; }}
QListWidget::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT};
}}
QListWidget::item:hover:!selected {{ background-color: {BG_HOVER}; }}

/* ── Dialog Buttons ───────────────────────────────────────────────────── */
QDialogButtonBox QPushButton {{
    min-width: 70px;
    padding: 5px 14px;
}}

/* ── Tool Tip ─────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT};
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 11px;
}}
"""


def apply(app):
    """Apply the pyBehavior stylesheet to a QApplication."""
    app.setStyleSheet(STYLESHEET)


# ── Colour helpers for programmatic use ────────────────────────────────────
COLORS = {
    "accent":    ACCENT,
    "success":   SUCCESS,
    "danger":    DANGER,
    "warning":   WARNING,
    "bg_panel":  BG_PANEL,
    "bg_surface": BG_SURFACE,
    "text":      TEXT_PRIMARY,
    "text_dim":  TEXT_SECONDARY,
}
