DARK_STYLE = """
QWidget {
    background-color: #0b1220;
    color: #e5e7eb;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0b1220;
}

QFrame#HeaderFrame {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 16px;
}

QFrame#SidebarFrame {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 16px;
}

QFrame#ContentFrame {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 16px;
}

QPushButton {
    background-color: #1f2937;
    color: #f9fafb;
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2b3547;
}

QPushButton:pressed {
    background-color: #374151;
}

QPushButton#NavButton {
    min-height: 42px;
}

QPushButton#PrimaryButton {
    background-color: #0891b2;
    border: 1px solid #0ea5e9;
    text-align: center;
}

QPushButton#PrimaryButton:hover {
    background-color: #0e7490;
}

QLabel#TitleLabel {
    font-size: 26px;
    font-weight: 700;
    color: #f9fafb;
}

QLabel#SubTitleLabel {
    font-size: 13px;
    color: #9ca3af;
}

QLabel#SectionTitle {
    font-size: 18px;
    font-weight: 700;
    color: #f9fafb;
}

QLabel#ModeBadge {
    background-color: #12311d;
    color: #86efac;
    border: 1px solid #166534;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 700;
}

QComboBox, QLineEdit, QTextEdit, QListWidget, QTableWidget {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 6px;
    color: #e5e7eb;
}

QHeaderView::section {
    background-color: #1f2937;
    color: #f9fafb;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #374151;
    font-weight: 700;
}

QTableWidget {
    gridline-color: #253041;
}

QScrollBar:vertical {
    background: #111827;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #374151;
    min-height: 20px;
    border-radius: 6px;
}

QFrame#InfoCard {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 14px;
}

QLabel#CardTitle {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
}

QLabel#CardValue {
    color: #f8fafc;
    font-size: 22px;
    font-weight: 800;
    padding-top: 4px;
}

QTableWidget {
    selection-background-color: #164e63;
    selection-color: white;
}

QLabel#StatusGood {
    color: #86efac;
    font-weight: 700;
}

QLabel#StatusWarn {
    color: #facc15;
    font-weight: 700;
}

QLabel#StatusBad {
    color: #fca5a5;
    font-weight: 700;
}
QFrame#PanelCard {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 14px;
}

QLabel#PanelTitle {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 700;
}

QLabel#MutedText {
    color: #94a3b8;
    font-size: 12px;
}

QLabel#GoodBadge {
    background-color: #12311d;
    color: #86efac;
    border: 1px solid #166534;
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}

QLabel#InfoBadge {
    background-color: #0f2942;
    color: #7dd3fc;
    border: 1px solid #0369a1;
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}

QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    text-align: center;
    min-height: 20px;
}

QProgressBar::chunk {
    background-color: #0891b2;
    border-radius: 8px;
}
"""

