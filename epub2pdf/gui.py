import os
import sys
import tempfile
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QProgressBar, QTextEdit, QGroupBox, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QEvent
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

from .epub import extract_epub, get_chapters, validate_epub, InvalidEPUBError
from .html_builder import build_html
from .pdf import render_pdf

logger = logging.getLogger(__name__)


class LogSignalHandler(logging.Handler):
    """Logging handler that emits log records through a QThread signal."""

    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class ConversionWorker(QThread):
    """Background thread for EPUB to PDF conversion."""

    progress = Signal(str, int)  # (status_message, percent)
    log = Signal(str)  # log message
    finished = Signal(str)  # output_path on success
    error = Signal(str)  # error message

    def __init__(self, epub_path, output_path, verbose=False):
        super().__init__()
        self.epub_path = epub_path
        self.output_path = output_path
        self.verbose = verbose

    def run(self):
        try:
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG if self.verbose else logging.WARNING)

            # Remove any existing handlers (prevents console output)
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            # Add a handler that routes to the GUI log window
            handler = LogSignalHandler(self.log)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            root_logger.addHandler(handler)

            if not self.verbose:
                logging.getLogger("xhtml2pdf").setLevel(logging.ERROR)

            validate_epub(self.epub_path)

            self.progress.emit("Extracting EPUB...", 10)
            self.log.emit(f"Input: {self.epub_path}")
            with tempfile.TemporaryDirectory() as tmp:
                extract_epub(self.epub_path, tmp)

                self.progress.emit("Reading chapters...", 25)
                chapters, epub_root, toc = get_chapters(tmp)

                if not chapters:
                    self.error.emit("No readable chapters found in EPUB")
                    return

                self.log.emit(f"Found {len(chapters)} chapters, {len(toc)} TOC entries")

                self.progress.emit(f"Building HTML ({len(chapters)} chapters)...", 45)
                html = build_html(chapters, epub_root, toc=toc)

                self.progress.emit("Generating PDF...", 60)
                self.log.emit("Rendering PDF (this may take a while)...")
                render_pdf(html, self.output_path)

            self.progress.emit("Done!", 100)
            self.finished.emit(self.output_path)

        except InvalidEPUBError as e:
            self.error.emit(str(e))
        except FileNotFoundError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Conversion failed: {e}")


class LogWindow(QWidget):
    """Separate, resizable log window."""

    visibility_changed = Signal(bool)  # True = visible, False = hidden

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conversion Log")
        self.setMinimumSize(500, 350)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.log_text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self.log_text.clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    def append(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def showEvent(self, event):
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibility_changed.emit(False)


class DropArea(QFrame):
    """Drag-and-drop area for EPUB files."""

    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
            QFrame:hover {
                border-color: #0078d4;
                background-color: #f0f7ff;
            }
        """)
        layout = QVBoxLayout(self)
        label = QLabel("Drop EPUB file here or use Browse")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #666; font-size: 13px; border: none;")
        layout.addWidget(label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".epub"):
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        QFrame {
                            border: 2px dashed #0078d4;
                            border-radius: 8px;
                            background-color: #e8f4fd;
                        }
                    """)
                    return

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
            QFrame:hover {
                border-color: #0078d4;
                background-color: #f0f7ff;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f8f8f8;
            }
            QFrame:hover {
                border-color: #0078d4;
                background-color: #f0f7ff;
            }
        """)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".epub"):
                self.file_dropped.emit(path)
                return


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB to PDF Converter")
        self.setMinimumSize(600, 420)
        self.setMaximumSize(700, 520)
        self.worker = None
        self.log_window = LogWindow()
        self.log_window.visibility_changed.connect(self._on_log_visibility_changed)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("EPUB to PDF Converter")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Drop area
        self.drop_area = DropArea()
        self.drop_area.file_dropped.connect(self._on_file_dropped)
        main_layout.addWidget(self.drop_area)

        # Input file
        input_group = QGroupBox("Input")
        input_layout = QHBoxLayout(input_group)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Select an EPUB file...")
        self.input_edit.setReadOnly(True)
        input_layout.addWidget(self.input_edit)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setFixedWidth(90)
        self.browse_btn.clicked.connect(self._browse_input)
        input_layout.addWidget(self.browse_btn)
        main_layout.addWidget(input_group)

        # Output file
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout(output_group)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output PDF path...")
        output_layout.addWidget(self.output_edit)
        self.output_btn = QPushButton("Browse...")
        self.output_btn.setFixedWidth(90)
        self.output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_btn)
        main_layout.addWidget(output_group)

        # Options row
        options_row = QHBoxLayout()
        self.verbose_cb = QCheckBox("Verbose logging")
        options_row.addWidget(self.verbose_cb)
        options_row.addStretch()
        self.log_btn = QPushButton("Show Log")
        self.log_btn.setFixedWidth(90)
        self.log_btn.clicked.connect(self._toggle_log)
        options_row.addWidget(self.log_btn)
        main_layout.addLayout(options_row)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        main_layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.status_label)

        # Convert button
        self.convert_btn = QPushButton("Convert to PDF")
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #006cbd; }
            QPushButton:pressed { background-color: #005a9e; }
            QPushButton:disabled { background-color: #ccc; color: #888; }
        """)
        self.convert_btn.clicked.connect(self._start_conversion)
        main_layout.addWidget(self.convert_btn)

    # --- Log window ---

    def _toggle_log(self):
        if self.log_window.isVisible():
            self.log_window.hide()
        else:
            self.log_window.show()
            self.log_window.raise_()

    @Slot(bool)
    def _on_log_visibility_changed(self, visible):
        self.log_btn.setText("Hide Log" if visible else "Show Log")

    def _log(self, message):
        self.log_window.append(message)

    # --- File selection ---

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select EPUB File", "", "EPUB Files (*.epub);;All Files (*)"
        )
        if path:
            self._set_input(path)

    def _browse_output(self):
        base = Path(self.input_edit.text()).stem if self.input_edit.text() else "output"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As", f"{base}.pdf", "PDF Files (*.pdf)"
        )
        if path:
            self.output_edit.setText(path)

    def _on_file_dropped(self, path):
        self._set_input(path)

    def _set_input(self, path):
        self.input_edit.setText(path)
        if not self.output_edit.text():
            out = str(Path(path).with_suffix(".pdf"))
            self.output_edit.setText(out)
        self._log(f"Selected: {Path(path).name}")

    # --- Conversion ---

    def _start_conversion(self):
        epub_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()

        if not epub_path:
            self.status_label.setText("Error: No EPUB file selected")
            self.status_label.setStyleSheet("color: red;")
            return

        if not output_path:
            output_path = str(Path(epub_path).with_suffix(".pdf"))
            self.output_edit.setText(output_path)

        # Auto-open log window on conversion start
        if not self.log_window.isVisible():
            self._toggle_log()

        self._log(f"\n--- Converting: {Path(epub_path).name} ---")
        self._set_ui_enabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Converting...")
        self.status_label.setStyleSheet("color: #0078d4;")

        self.worker = ConversionWorker(
            epub_path, output_path, self.verbose_cb.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    @Slot(str, int)
    def _on_progress(self, message, percent):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    @Slot(str)
    def _on_finished(self, output_path):
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Success! Saved to: {output_path}")
        self.status_label.setStyleSheet("color: green;")
        self._log(f"Done! PDF saved: {output_path}")
        self._set_ui_enabled(True)

    @Slot(str)
    def _on_error(self, message):
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: red;")
        self._log(f"ERROR: {message}")
        self._set_ui_enabled(True)

    def _set_ui_enabled(self, enabled):
        self.convert_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.output_btn.setEnabled(enabled)
        self.drop_area.setAcceptDrops(enabled)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
