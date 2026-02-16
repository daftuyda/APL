import sys
import json
import os
import webbrowser
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QRunnable, QObject, pyqtSignal, pyqtSlot, QThreadPool
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QStatusBar, QMessageBox, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QStyle
)
from PyQt5.QtGui import QFont, QCursor, QColor, QPen, QPainter
from pFactor import getPFactorData

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class WorkerSignals(QObject):
    progress = pyqtSignal(int, int, str)
    result = pyqtSignal(object)
    error = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            data = getPFactorData(self.username, progress_callback=self._progress)
            self.signals.result.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))

    def _progress(self, current, total, message):
        self.signals.progress.emit(current, total, message)


class NumericTableItem(QTableWidgetItem):
    """Table item that sorts numerically instead of alphabetically."""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            return super().__lt__(other)


class GroupBorderDelegate(QStyledItemDelegate):
    """Draws group outline borders on grouped rows."""

    # Accent colors for group left-edge bars
    GROUP_ACCENTS = [
        QColor('#7c4dff'),  # purple
        QColor('#448aff'),  # blue
        QColor('#26a69a'),  # teal
        QColor('#ffa726'),  # amber
        QColor('#ef5350'),  # red
        QColor('#66bb6a'),  # green
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.group_map = {}  # row -> (group_idx, group_size, is_first, is_last)

    def set_group_map(self, data):
        """Build row -> group info mapping from result data."""
        self.group_map.clear()
        prev_group = None
        group_start = 0
        for row, anime in enumerate(data):
            group = anime.get('group', -1)
            group_size = anime.get('groupSize', 1)
            if group_size <= 1:
                prev_group = None
                continue
            is_first = (group != prev_group)
            # Look ahead to check if this is the last in the group
            is_last = (row + 1 >= len(data) or
                       data[row + 1].get('group', -1) != group or
                       data[row + 1].get('groupSize', 1) <= 1)
            self.group_map[row] = (group, group_size, is_first, is_last)
            prev_group = group

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        row = index.row()
        if row not in self.group_map:
            return

        group_idx, group_size, is_first, is_last = self.group_map[row]
        accent = self.GROUP_ACCENTS[group_idx % len(self.GROUP_ACCENTS)]
        border_color = QColor(accent)
        border_color.setAlpha(160)

        painter.save()
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        rect = option.rect

        col = index.column()
        col_count = index.model().columnCount() if index.model() else 10
        is_first_col = (col == 0)
        is_last_col = (col == col_count - 1)

        # Top border (first row of group)
        if is_first:
            painter.drawLine(rect.left(), rect.top() + 1, rect.right(), rect.top() + 1)

        # Bottom border (last row of group)
        if is_last:
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # Left border (first column only)
        if is_first_col:
            painter.drawLine(rect.left() + 1, rect.top(), rect.left() + 1, rect.bottom())

        # Right border (last column only)
        if is_last_col:
            painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())

        painter.restore()


COLUMNS = ['#', 'Title', 'APL', 'Score', 'Eps', 'Min/Ep', 'Hours', 'P-Factor', 'B-Factor', 'Relation']
USERDATA_PATH = os.path.join(BASE_DIR, 'userdata.json')

# Group background tints (applied to grouped rows)
GROUP_BG = [
    QColor(42, 30, 62),   # purple tint
    QColor(30, 42, 62),   # blue tint
    QColor(30, 52, 48),   # teal tint
    QColor(55, 42, 28),   # amber tint
    QColor(55, 30, 32),   # red tint
    QColor(32, 50, 35),   # green tint
]

STYLESHEET = """
    QMainWindow {
        background-color: #1a1a2e;
    }
    QWidget#central {
        background-color: #1a1a2e;
    }
    QLabel {
        color: #e0e0e0;
    }
    QLineEdit {
        background-color: #16213e;
        color: #e0e0e0;
        border: 1px solid #0f3460;
        padding: 6px;
        border-radius: 4px;
        selection-background-color: #533483;
    }
    QLineEdit:focus {
        border: 1px solid #533483;
    }
    QPushButton {
        background-color: #533483;
        color: #ffffff;
        border: none;
        padding: 6px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #6a42a0;
    }
    QPushButton:pressed {
        background-color: #3e2563;
    }
    QPushButton:disabled {
        background-color: #3a3a4a;
        color: #777;
    }
    QPushButton#clearCache {
        background-color: #0f3460;
    }
    QPushButton#clearCache:hover {
        background-color: #154785;
    }
    QTableWidget {
        background-color: #16213e;
        alternate-background-color: #1a2744;
        color: #e0e0e0;
        gridline-color: #0f3460;
        border: 1px solid #0f3460;
        border-radius: 4px;
        selection-background-color: #533483;
        selection-color: #ffffff;
    }
    QTableWidget::item {
        padding: 4px;
    }
    QHeaderView::section {
        background-color: #0f3460;
        color: #e0e0e0;
        padding: 6px;
        border: 1px solid #16213e;
        font-weight: bold;
    }
    QProgressBar {
        background-color: #16213e;
        border: 1px solid #0f3460;
        border-radius: 4px;
        text-align: center;
        color: #e0e0e0;
    }
    QProgressBar::chunk {
        background-color: #533483;
        border-radius: 3px;
    }
    QStatusBar {
        background-color: #0f3460;
        color: #e0e0e0;
    }
    QScrollBar:vertical {
        background-color: #16213e;
        width: 12px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: #533483;
        border-radius: 4px;
        min-height: 20px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background-color: #16213e;
        height: 12px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: #533483;
        border-radius: 4px;
        min-width: 20px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        self.data = []
        self.group_delegate = GroupBorderDelegate()
        self._init_ui()
        self._load_userdata()

    def _init_ui(self):
        self.setWindowTitle("Anime Priority List v3")
        self.setWindowIcon(QtGui.QIcon(os.path.join(BASE_DIR, 'icon.ico')))
        self.setMinimumSize(900, 550)
        self.resize(1100, 700)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # --- Top bar ---
        top_bar = QHBoxLayout()

        lbl = QLabel("AniList Username:")
        lbl.setFont(QFont('Segoe UI', 10))
        top_bar.addWidget(lbl)

        self.username_input = QLineEdit()
        self.username_input.setFont(QFont('Segoe UI', 10))
        self.username_input.setPlaceholderText("Enter your AniList username")
        self.username_input.setFixedWidth(250)
        self.username_input.returnPressed.connect(self.generate)
        top_bar.addWidget(self.username_input)

        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.btn_generate.setFixedSize(110, 32)
        self.btn_generate.clicked.connect(self.generate)
        top_bar.addWidget(self.btn_generate)

        self.btn_save = QPushButton("Save User")
        self.btn_save.setFont(QFont('Segoe UI', 9))
        self.btn_save.setFixedSize(95, 32)
        self.btn_save.clicked.connect(self.save_userdata)
        top_bar.addWidget(self.btn_save)

        self.btn_clear_cache = QPushButton("Clear Cache")
        self.btn_clear_cache.setObjectName("clearCache")
        self.btn_clear_cache.setFont(QFont('Segoe UI', 9))
        self.btn_clear_cache.setFixedSize(105, 32)
        self.btn_clear_cache.clicked.connect(self.clear_cache)
        top_bar.addWidget(self.btn_clear_cache)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # --- Progress bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont('Segoe UI', 9))
        self.table.setShowGrid(True)
        self.table.setItemDelegate(self.group_delegate)

        header = self.table.horizontalHeader()
        header.setFont(QFont('Segoe UI', 9, QFont.Bold))
        header.setSectionResizeMode(0, QHeaderView.Fixed)        # #
        header.setSectionResizeMode(1, QHeaderView.Stretch)      # Title
        header.setSectionResizeMode(9, QHeaderView.Stretch)      # Relation
        for col in range(2, 9):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.table.setColumnWidth(0, 40)
        self.table.doubleClicked.connect(self.open_anilist)

        layout.addWidget(self.table)

        # --- Status bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready - enter your AniList username and click Generate")
        self.status_bar.addWidget(self.status_label)
        self.stats_label = QLabel("")
        self.status_bar.addPermanentWidget(self.stats_label)

    def _load_userdata(self):
        if os.path.exists(USERDATA_PATH):
            try:
                with open(USERDATA_PATH, 'r') as f:
                    data = json.load(f)
                self.username_input.setText(data.get('Anilist', ''))
            except (json.JSONDecodeError, IOError):
                pass

    def save_userdata(self):
        with open(USERDATA_PATH, 'w') as f:
            json.dump({'Anilist': self.username_input.text()}, f)
        self.status_label.setText("User data saved.")

    def clear_cache(self):
        from cache import cache
        cache.clear()
        self.status_label.setText("Cache cleared.")

    def generate(self):
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "APL", "Please enter an AniList username.")
            return

        self.btn_generate.setEnabled(False)
        self.setCursor(QCursor(Qt.WaitCursor))
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Fetching data...")

        worker = Worker(username)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.result.connect(self.on_result)
        worker.signals.error.connect(self.on_error)
        self.threadpool.start(worker)

    def on_progress(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(message)

    def on_result(self, data):
        self.data = data
        self.group_delegate.set_group_map(data)
        self._populate_table(data)
        self.btn_generate.setEnabled(True)
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.progress_bar.setVisible(False)

        total_hours = sum(a['watchTime'] for a in data)
        groups = len({a['group'] for a in data if a.get('groupSize', 1) > 1})
        group_text = f" | {groups} franchise groups" if groups else ""
        self.status_label.setText(f"{len(data)} anime loaded{group_text}")
        self.stats_label.setText(f"Total watch time: {total_hours:,.1f} hours")

    def on_error(self, error_msg):
        self.btn_generate.setEnabled(True)
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error occurred")
        QMessageBox.critical(
            self, "APL Error", f"Failed to fetch data:\n\n{error_msg}"
        )

    def _populate_table(self, data):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(data))

        sequel_color = QColor('#66bb6a')
        apl_color = QColor('#ce93d8')

        for row, anime in enumerate(data):
            group_size = anime.get('groupSize', 1)
            group_idx = anime.get('group', 0)

            # Determine background color
            if group_size > 1:
                bg = GROUP_BG[group_idx % len(GROUP_BG)]
            else:
                bg = None  # use default alternating colors

            # #
            item = NumericTableItem(str(row + 1))
            item.setTextAlignment(Qt.AlignCenter)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 0, item)

            # Title
            item = QTableWidgetItem(anime['title'])
            item.setData(Qt.UserRole, anime['id'])
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 1, item)

            # APL
            item = NumericTableItem(str(anime['APL']))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(apl_color)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 2, item)

            # Score
            item = NumericTableItem(str(anime['averageScore']))
            item.setTextAlignment(Qt.AlignCenter)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 3, item)

            # Episodes
            item = NumericTableItem(str(anime['episodes']))
            item.setTextAlignment(Qt.AlignCenter)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 4, item)

            # Duration
            item = NumericTableItem(str(anime['duration']))
            item.setTextAlignment(Qt.AlignCenter)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 5, item)

            # Watch Time (hours)
            wt = anime['watchTime']
            item = NumericTableItem(str(wt) if wt > 0 else "")
            item.setTextAlignment(Qt.AlignCenter)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 6, item)

            # P-Factor
            pf = anime['pfactor']
            item = NumericTableItem(str(pf) if pf > 0 else "")
            item.setTextAlignment(Qt.AlignCenter)
            if pf > 0:
                item.setForeground(sequel_color)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 7, item)

            # B-Factor
            bf = anime['bfactor']
            item = NumericTableItem(str(bf) if bf > 0 else "")
            item.setTextAlignment(Qt.AlignCenter)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 8, item)

            # Relation
            rel_text = anime.get('relation') or ""
            item = QTableWidgetItem(rel_text)
            if rel_text:
                item.setForeground(sequel_color)
            if bg:
                item.setBackground(bg)
            self.table.setItem(row, 9, item)

        self.table.setSortingEnabled(True)

    def open_anilist(self, index):
        """Open the AniList page for the double-clicked anime."""
        row = index.row()
        title_item = self.table.item(row, 1)
        if title_item:
            anime_id = title_item.data(Qt.UserRole)
            if anime_id:
                webbrowser.open(f"https://anilist.co/anime/{anime_id}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
