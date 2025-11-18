import sys
import os
import subprocess
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QProgressBar, QSpinBox, QGroupBox, QDialog, QLineEdit,
    QGridLayout, QMessageBox, QStackedWidget, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import (
    QFont, QDragEnterEvent, QDropEvent, QIcon, QPixmap, 
    QPainter, QPainterPath, QColor, QPen
)
from PIL import Image
import cv2
import numpy as np
import json
import yt_dlp
import re


class IconFactory:
    @staticmethod
    def create_icon(icon_name, color):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(color, 5.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.transparent)

        if icon_name == "profile":
            painter.drawEllipse(16, 12, 32, 32)
            path = QPainterPath()
            path.moveTo(8, 60)
            path.quadTo(32, 40, 56, 60)
            painter.drawPath(path)
        elif icon_name == "folder":
            painter.drawRoundedRect(6, 16, 52, 36, 6, 6)
            painter.drawRoundedRect(4, 10, 26, 10, 4, 4)
        elif icon_name == "upscaler":
            painter.drawLine(32, 8, 32, 44)
            painter.drawLine(20, 20, 32, 8)
            painter.drawLine(44, 20, 32, 8)
            painter.drawRect(12, 44, 40, 12)
        elif icon_name == "downloader":
            painter.drawLine(32, 8, 32, 44)
            painter.drawLine(20, 32, 32, 44)
            painter.drawLine(44, 32, 32, 44)
            painter.drawRect(12, 52, 40, 8)
            painter.drawLine(12, 52, 12, 60)
            painter.drawLine(52, 52, 52, 60)

        painter.end()
        return QIcon(pixmap)


class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.background_widget = QWidget()
        self.background_widget.setStyleSheet("""
            QWidget {
                background: rgba(13, 17, 23, 245);
                border-radius: 25px;
            }
        """)
        bg_layout = QVBoxLayout(self.background_widget)
        bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_layout.setContentsMargins(30, 30, 30, 30)

        layout.addWidget(self.background_widget)
        
        title = QLabel("Media Tools")
        title.setFont(QFont('Arial', 36, QFont.Weight.Bold))
        title.setStyleSheet("""
            background: transparent;
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                   stop:0 #58a6ff, stop:1 #3fb950);
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_layout.addWidget(title)
        
        self.loading_label = QLabel("●●●")
        self.loading_label.setFont(QFont('Arial', 24))
        self.loading_label.setStyleSheet("background: transparent; color: #58a6ff;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_layout.addWidget(self.loading_label)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(400)
        self.dot_count = 0
        
    def animate(self):
        dots = ["●", "●●", "●●●", "●●●●"]
        self.loading_label.setText(dots[self.dot_count % len(dots)])
        self.dot_count += 1


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background: rgba(13, 17, 23, 245);
                border-radius: 20px;
                font-family: 'Bahnschrift', Arial;
            }
            QLabel {
                color: #c9d1d9;
                font-size: 15px;
                background: transparent;
            }
            QLineEdit {
                background: rgba(22, 27, 34, 200);
                border: 2px solid rgba(48, 54, 61, 150);
                border-radius: 8px;
                padding: 2px;
                color: #c9d1d9;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(88, 166, 255, 200);
            }
            QPushButton {
                background: rgba(35, 134, 54, 200);
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background: rgba(46, 160, 67, 220);
            }
            QPushButton#browseBtn {
                background: rgba(33, 38, 45, 200);
                color: #c9d1d9;
                min-width: 80px;
            }
            QPushButton#browseBtn:hover {
                background: rgba(48, 54, 61, 220);
            }
            QPushButton#cancelBtn {
                background: rgba(33, 38, 45, 200);
                color: #c9d1d9;         
            }
            QPushButton#cancelBtn:hover {
                background: rgba(48, 54, 61, 220);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        avatar_title = QLabel("Профиль")
        avatar_title.setFont(QFont('Bahnschrift', 18, QFont.Weight.Bold))
        avatar_title.setStyleSheet("color: #58a6ff; margin-bottom: 5px;")
        layout.addWidget(avatar_title)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet("""
            background: rgba(88, 166, 255, 30);
            border-radius: 60px;
            border: 3px solid rgba(88, 166, 255, 100);
        """)
        
        self.load_avatar()
        
        avatar_container = QHBoxLayout()
        avatar_container.addStretch()
        avatar_container.addWidget(self.avatar_label)
        avatar_container.addStretch()
        layout.addLayout(avatar_container)
        
        change_btn = QPushButton("Изменить фото")
        change_btn.clicked.connect(self.change_avatar)
        layout.addWidget(change_btn)
        
        layout.addSpacing(20)

        folder_title = QLabel("Сохранение")
        folder_title.setFont(QFont('Bahnschrift', 18, QFont.Weight.Bold))
        folder_title.setStyleSheet("color: #58a6ff; margin-bottom: 5px;")
        layout.addWidget(folder_title)

        folder_label = QLabel("Папка для сохранения файлов:")
        folder_label.setFont(QFont('Bahnschrift', 14))
        layout.addWidget(folder_label)

        folder_input_layout = QHBoxLayout()
        folder_input_layout.setSpacing(10)

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Выберите папку для сохранения...")
        self.folder_input.setReadOnly(True)
        folder_input_layout.addWidget(self.folder_input)

        browse_btn = QPushButton("Обзор")
        browse_btn.setObjectName("browseBtn")
        browse_btn.clicked.connect(self.browse_folder)
        folder_input_layout.addWidget(browse_btn)

        layout.addLayout(folder_input_layout)
        layout.addStretch()
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.addStretch()
        
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.load_settings()

    def create_default_avatar(self, size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen_color = QColor(88, 166, 255) 
        pen_width = max(1, int((size / 110.0) * 3))
        
        pen = QPen(pen_color, pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        head_radius = size * 0.2
        head_center_y = size * 0.35
        body_top_y = head_center_y + head_radius
        body_bottom_y = size * 0.85
        body_width = size * 0.6
        
        painter.drawEllipse(QPoint(int(size / 2), int(head_center_y)), int(head_radius), int(head_radius))
        
        path = QPainterPath()
        path.moveTo(int(size / 2 - body_width / 2), int(body_bottom_y))
        path.quadTo(size / 2, body_top_y + pen_width, size / 2 + body_width / 2, body_bottom_y)
        painter.drawPath(path)
        
        painter.end()
        return pixmap

    def load_avatar(self):
        avatar_path = Path("avatar.png")
        if avatar_path.exists():
            pixmap = QPixmap(str(avatar_path)).scaled(
                110, 110,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            rounded = QPixmap(110, 110)
            rounded.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            path = QPainterPath()
            path.addEllipse(0, 0, 110, 110)
            painter.setClipPath(path)
            
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            self.avatar_label.setPixmap(rounded)
        else:
            self.avatar_label.setPixmap(self.create_default_avatar(110))
    
    def change_avatar(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите фото",
            "", "Изображения (*.jpg *.jpeg *.png);;Все (*.*)"
        )
        if file_path:
            try:
                img = Image.open(file_path)
                img = img.convert('RGB')
                img.thumbnail((500, 500))
                img.save("avatar.png", "PNG")
                self.load_avatar()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить фото: {e}")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_input.setText(folder)

    def load_settings(self):
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.folder_input.setText(settings.get('output_folder', ''))
            except:
                pass

    def save_settings(self):
        settings = {
            'output_folder': self.folder_input.text()
        }
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def get_output_folder(self):
        return self.folder_input.text()


class DownloadThread(QThread):
    progress = pyqtSignal(dict)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, url, output_path_template, quality, audio_mode, audio_format):
        super().__init__()
        self.url = url
        self.output_path_template = output_path_template
        self.quality = quality
        self.audio_mode = audio_mode
        self.audio_format = audio_format
        
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                
                if total > 0:
                    percent = int((downloaded / total) * 100)
                else:
                    percent = 0
                
                self.progress.emit({
                    'percent': percent,
                    'speed': speed,
                    'total': total,
                    'downloaded': downloaded
                })
            except Exception as e:
                print(f"Progress hook error: {e}")
    
    def run(self):
        try:
            ydl_opts = {
                'outtmpl': self.output_path_template,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'noprogress': True,
                'postprocessor_hooks': [self.progress_hook],
            }
            
            if self.audio_mode == "Только звук":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.audio_format.lower(),
                }]
            elif self.audio_mode == "Без звука":
                if self.quality == "Плохое":
                    ydl_opts['format'] = 'worstvideo'
                elif self.quality == "Среднее":
                    ydl_opts['format'] = 'bestvideo[height<=720]'
                else:
                    ydl_opts['format'] = 'bestvideo'
            else:
                if self.quality == "Плохое":
                    ydl_opts['format'] = 'worstvideo+worstaudio/worst'
                elif self.quality == "Среднее":
                    ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
                else:
                    ydl_opts['format'] = 'bestvideo*+bestaudio/best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.finished.emit(self.output_path_template)
        except Exception as e:
            self.error.emit(f"Ошибка загрузки: {str(e)}")


class UpscaleThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, input_path, output_path, width, height, file_type):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.width = width
        self.height = height
        self.file_type = file_type

    def run(self):
        try:
            if self.file_type in ['image', 'gif']:
                self.upscale_image()
            elif self.file_type == 'video':
                self.upscale_video()
        except Exception as e:
            self.error.emit(f"Ошибка: {str(e)}")

    def upscale_image(self):
        img = Image.open(self.input_path)

        if self.input_path.lower().endswith('.gif'):
            frames = []
            try:
                while True:
                    frames.append(img.copy())
                    img.seek(img.tell() + 1)
            except EOFError:
                pass

            if not frames:
                self.error.emit("Не удалось прочитать GIF")
                return

            resized_frames = []
            for i, frame in enumerate(frames):
                resized = frame.resize((self.width, self.height), Image.Resampling.LANCZOS)
                resized_frames.append(resized)
                self.progress.emit(int(((i+1) / len(frames)) * 100))

            resized_frames[0].save(
                self.output_path,
                save_all=True,
                append_images=resized_frames[1:],
                loop=0,
                duration=img.info.get('duration', 100),
                optimize=False
            )
        else:
            result = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
            self.progress.emit(50)

            if self.output_path.lower().endswith(('.jpg', '.jpeg')):
                result.save(self.output_path, quality=100, subsampling=0)
            else:
                result.save(self.output_path, compress_level=1)

            self.progress.emit(100)

        self.finished.emit(self.output_path)

    def upscale_video(self):
        cap = cv2.VideoCapture(self.input_path)
        if not cap.isOpened():
            self.error.emit("Не удалось открыть видеофайл")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 60.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        temp_video_path = str(
            Path(self.output_path).with_name(Path(self.output_path).stem + "_video_tmp.mp4")
        )

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps, (self.width, self.height))
        
        if not out.isOpened():
            cap.release()
            self.error.emit("Не удалось инициализировать VideoWriter (кодек mp4v)")
            return

        is_upscaling = (self.width > orig_width) or (self.height > orig_height)
        same_size = (self.width == orig_width) and (self.height == orig_height)

        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if same_size:
                output_frame = frame
            else:
                if is_upscaling:
                    output_frame = cv2.resize(
                        frame, (self.width, self.height),
                        interpolation=cv2.INTER_LANCZOS4
                    )
                else:
                    output_frame = cv2.resize(
                        frame, (self.width, self.height),
                        interpolation=cv2.INTER_AREA
                    )

            out.write(output_frame)

            frame_count += 1
            if total_frames > 0:
                progress = int((frame_count / total_frames) * 100)
                self.progress.emit(progress)

        cap.release()
        out.release()

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", temp_video_path,
                "-i", self.input_path,
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-c:v", "copy",
                "-shortest",
                self.output_path
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode != 0:
                if not os.path.exists(self.output_path):
                    os.replace(temp_video_path, self.output_path)
        except FileNotFoundError:
            if not os.path.exists(self.output_path):
                try:
                    os.replace(temp_video_path, self.output_path)
                except Exception:
                    pass
        finally:
            if os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except Exception:
                    pass

        self.progress.emit(100)
        self.finished.emit(self.output_path)


class DropArea(QLabel):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.update_style(False)
        self.setText("Перетащите файл сюда")

    def update_style(self, hover=False):
        if hover:
            self.setStyleSheet("""
                QLabel {
                    border: 3px dashed rgba(88, 166, 255, 200);
                    border-radius: 12px;
                    background: rgba(88, 166, 255, 30);
                    color: #58a6ff;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    border: 3px dashed rgba(48, 54, 61, 150);
                    border-radius: 12px;
                    background: rgba(22, 27, 34, 150);
                    color: #8b949e;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.update_style(True)

    def dragLeaveEvent(self, event):
        self.update_style(False)

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.fileDropped.emit(files[0])
        self.update_style(False)


class SegmentedButton(QWidget):
    button_clicked = pyqtSignal(str)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.buttons = {}
        self.current_value = ""

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        for i, text in enumerate(items):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName("segmentBtn")
            btn.clicked.connect(self.on_button_clicked)
            self.buttons[text] = btn
            layout.addWidget(btn)

        if items:
            self.set_active(items[0])

    def on_button_clicked(self):
        sender = self.sender()
        new_value = sender.text()
        self.set_active(new_value)
        self.button_clicked.emit(new_value)

    def set_active(self, text):
        self.current_value = text
        for btn_text, btn in self.buttons.items():
            if btn_text == text:
                btn.setChecked(True)
                btn.setProperty("active", True)
            else:
                btn.setChecked(False)
                btn.setProperty("active", False)
            
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def get_value(self):
        return self.current_value


class MediaUpscaler(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.original_width = 0
        self.original_height = 0
        self.output_folder = ""
        self.load_settings()
        self.init_ui()

    def load_settings(self):
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.output_folder = settings.get('output_folder', '')
            except:
                pass

    def init_ui(self):
        self.setWindowTitle("Media Tools")
        self.setMinimumSize(650, 650)
        self.resize(650, 660)

        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            self.setWindowIcon(IconFactory.create_icon("upscaler", QColor("#58a6ff")))

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(13, 17, 23, 250), stop:1 rgba(22, 27, 34, 250));
            }
            QWidget {
                color: #c9d1d9;
                font-family: 'Bahnschrift', Arial;
            }
            QPushButton {
                background: rgba(35, 134, 54, 180);
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(46, 160, 67, 200);
            }
            QPushButton:pressed {
                background: rgba(31, 111, 42, 200);
            }
            QPushButton:disabled {
                background: rgba(33, 38, 45, 150);
                color: rgba(110, 118, 129, 150);
            }
            
            QPushButton#navBtn {
                background: rgba(33, 38, 45, 150);
                color: #8b949e;
                padding: 4px;
                border-radius: 10px;
                min-width: 50px;
                max-width: 50px; 
                min-height: 36px;
                max-height: 36px;
                font-weight: bold;
                font-size: 14px;
                text-align: center;
            }
            QPushButton#navBtn:hover {
                background: rgba(48, 54, 61, 180);
                color: #c9d1d9;
            }
            QPushButton#navBtn[active="true"] {
                background: rgba(88, 166, 255, 100);
                color: #58a6ff;
                max-width: 200px; 
                padding: 4px 14px;
                text-align: left;
            }
            QPushButton#navBtn[active="true"]:hover {
                background: rgba(88, 166, 255, 130);
                color: #7abeff;
            }

            QPushButton#profileBtn {
                background: rgba(33, 38, 45, 150);
                border-radius: 25px;
                padding: 0;
                min-width: 50px;
                max-width: 50px;
                min-height: 50px;
                max-height: 50px;
            }
            QPushButton#profileBtn:hover {
                background: rgba(48, 54, 61, 180);
            }
            QPushButton#folderBtn {
                background: rgba(33, 38, 45, 150);
                border-radius: 25px;
                padding: 0;
                min-width: 50px;
                max-width: 50px;
                min-height: 50px;
                max-height: 50px;
            }
            QPushButton#folderBtn:hover {
                background: rgba(48, 54, 61, 180);
            }
            
            QSpinBox, QLineEdit {
                background: rgba(22, 27, 34, 180);
                border: 2px solid rgba(48, 54, 61, 150);
                border-radius: 8px;
                padding: 10px;
                font-size: 15px;
                color: #c9d1d9;
                min-height: 30px; 
            }
            QSpinBox {
                padding-right: 0px; 
            }
            QSpinBox:focus, QLineEdit:focus {
                border: 2px solid rgba(88, 166, 255, 200);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: rgba(33, 38, 45, 180);
                border: none;
                width: 24px;
                border-radius: 4px;
                margin-right: 4px;
            }
            QSpinBox::up-button {
                margin-bottom: 2px;
            }
            QSpinBox::down-button {
                margin-top: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: rgba(48, 54, 61, 200);
            }

            QPushButton#segmentBtn {
                background: rgba(22, 27, 34, 180);
                border: 2px solid rgba(48, 54, 61, 150);
                color: #8b949e;
                padding: 8px;
                font-size: 14px;
                font-weight: normal;
                min-height: 28px;
                border-radius: 8px;
            }
            QPushButton#segmentBtn:hover {
                background: rgba(48, 54, 61, 150);
            }
            QPushButton#segmentBtn[active="true"] {
                background: rgba(88, 166, 255, 100);
                border-color: rgba(88, 166, 255, 150);
                color: #c9d1d9;
            }
            
            QCheckBox {
                color: #c9d1d9;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid rgba(48, 54, 61, 150);
                background: rgba(22, 27, 34, 180);
            }
            QCheckBox::indicator:checked {
                background: rgba(88, 166, 255, 200);
                border: 2px solid rgba(88, 166, 255, 200);
            }
            QProgressBar {
                border: none;
                border-radius: 10px;
                background: rgba(22, 27, 34, 180);
                text-align: center;
                color: #c9d1d9;
                font-weight: bold;
                height: 35px;
            }
            QProgressBar::chunk {
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(35, 134, 54, 200), stop:1 rgba(46, 160, 67, 200));
            }
            QGroupBox {
                background: rgba(13, 17, 23, 150);
                border: 2px solid rgba(48, 54, 61, 150);
                border-radius: 12px;
                margin-top: 20px;
                padding: 35px 15px 15px 15px;
                font-weight: bold;
                color: #58a6ff;
                font-size: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 10px;
                padding: 0 5px 5px 5px;
            }
            QPushButton#cancelBtn {
                background: rgba(210, 54, 61, 180);
                color: #ffffff;
                padding: 12px 24px;
            }
            QPushButton#cancelBtn:hover {
                background: rgba(248, 81, 73, 200);
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        if icon_path.exists():
            icon_label = QLabel()
            pixmap = QIcon(str(icon_path)).pixmap(QSize(40, 40))
            icon_label.setPixmap(pixmap)
            icon_label.setFixedSize(40, 40)
            header_layout.addWidget(icon_label)

        title = QLabel("Media Tools")
        title.setFont(QFont('Bahnschrift', 24, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #58a6ff, stop:1 #3fb950);
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.upscaler_btn = QPushButton(" Upscaler")
        self.upscaler_btn.setObjectName("navBtn")
        self.upscaler_btn.setIcon(IconFactory.create_icon("upscaler", QColor("#8b949e")))
        self.upscaler_btn.setIconSize(QSize(32, 32)) 
        self.upscaler_btn.setToolTip("Media Upscaler")
        self.upscaler_btn.clicked.connect(lambda: self.switch_page(0))
        nav_layout.addWidget(self.upscaler_btn)

        self.downloader_btn = QPushButton(" Downloader")
        self.downloader_btn.setObjectName("navBtn")
        self.downloader_btn.setIcon(IconFactory.create_icon("downloader", QColor("#8b949e")))
        self.downloader_btn.setIconSize(QSize(32, 32)) 
        self.downloader_btn.setToolTip("Media Downloader")
        self.downloader_btn.clicked.connect(lambda: self.switch_page(1))
        nav_layout.addWidget(self.downloader_btn)

        header_layout.addLayout(nav_layout)
        header_layout.addSpacing(10)

        self.folder_btn = QPushButton("")
        self.folder_btn.setObjectName("folderBtn")
        self.folder_btn.setIcon(IconFactory.create_icon("folder", QColor("#c9d1d9")))
        self.folder_btn.setIconSize(QSize(28, 28)) 
        self.folder_btn.setToolTip("Открыть папку сохранения")
        self.folder_btn.clicked.connect(self.open_output_folder)
        header_layout.addWidget(self.folder_btn)

        self.profile_btn = QPushButton("")
        self.profile_btn.setObjectName("profileBtn")
        self.profile_btn.setToolTip("Настройки")
        self.profile_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(self.profile_btn)

        main_layout.addLayout(header_layout)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.create_upscaler_page())
        self.stacked_widget.addWidget(self.create_downloader_page())
        main_layout.addWidget(self.stacked_widget)

        self.update_nav_buttons()

    def create_upscaler_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.load_file)
        layout.addWidget(self.drop_area)

        self.select_btn = QPushButton("Выбрать файл")
        self.select_btn.clicked.connect(self.select_file)
        layout.addWidget(self.select_btn)

        self.file_info = QLabel("Файл не выбран")
        self.file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_info.setStyleSheet("color: #8b949e; font-size: 14px;")
        layout.addWidget(self.file_info)

        size_group = QGroupBox("Размеры")
        grid = QGridLayout()
        grid.setContentsMargins(10, 5, 10, 10)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)

        width_label = QLabel("Ширина:")
        width_label.setFixedWidth(100)
        width_label.setStyleSheet("font-size: 15px; color: #c9d1d9;")

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(1920)
        self.width_spin.setSuffix(" px")
        self.width_spin.setMinimumHeight(45)

        height_label = QLabel("Высота:")
        height_label.setFixedWidth(100)
        height_label.setStyleSheet("font-size: 15px; color: #c9d1d9;")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(1080)
        self.height_spin.setSuffix(" px")
        self.height_spin.setMinimumHeight(45)

        grid.addWidget(width_label, 0, 0)
        grid.addWidget(self.width_spin, 0, 1)
        grid.addWidget(height_label, 1, 0)
        grid.addWidget(self.height_spin, 1, 1)

        size_group.setLayout(grid)
        layout.addWidget(size_group)

        self.process_btn = QPushButton(" Преобразовать")
        self.process_btn.setIcon(IconFactory.create_icon("upscaler", QColor("#ffffff")))
        self.process_btn.setIconSize(QSize(32, 32))
        self.process_btn.clicked.connect(self.process_file)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 14px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()
        return page

    def create_downloader_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        url_group = QGroupBox("Ссылка на видео")
        url_layout = QVBoxLayout()
        url_layout.setContentsMargins(10, 0, 10, 5)
        url_layout.setSpacing(0)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте ссылку на видео (YouTube, Twitter, Instagram и т.д.)")
        url_layout.addWidget(self.url_input)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        settings_group = QGroupBox("Настройки загрузки")
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(12)

        quality_layout = QHBoxLayout()
        quality_label = QLabel("Качество:")
        quality_label.setFixedWidth(100)
        quality_label.setStyleSheet("font-size: 15px; color: #c9d1d9;") 
        quality_layout.addWidget(quality_label)

        self.quality_segment = SegmentedButton(["Плохое", "Среднее", "Наилучшее"])
        self.quality_segment.set_active("Наилучшее")
        quality_layout.addWidget(self.quality_segment)

        settings_layout.addLayout(quality_layout)

        audio_layout = QHBoxLayout()
        audio_label = QLabel("Аудио:")
        audio_label.setFixedWidth(100)
        audio_label.setStyleSheet("font-size: 15px; color: #c9d1d9;")
        audio_layout.addWidget(audio_label)

        self.audio_segment = SegmentedButton(["Со звуком", "Без звука", "Только звук"])
        self.audio_segment.button_clicked.connect(self.update_audio_format_visibility)
        audio_layout.addWidget(self.audio_segment)

        settings_layout.addLayout(audio_layout)

        self.format_container = QWidget()
        self.format_layout = QHBoxLayout(self.format_container)
        self.format_layout.setContentsMargins(0, 0, 0, 0)
        self.format_layout.setSpacing(12)

        self.format_label = QLabel("Формат:")
        self.format_label.setFixedWidth(100)
        self.format_label.setStyleSheet("font-size: 15px; color: #c9d1d9;") 
        self.format_layout.addWidget(self.format_label)

        self.format_segment = SegmentedButton(["MP3", "M4A", "WAV", "OPUS"])
        self.format_layout.addWidget(self.format_segment)

        settings_layout.addWidget(self.format_container)
        
        self.format_container.setVisible(False)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        download_btn_layout = QHBoxLayout()
        download_btn_layout.setSpacing(15)
        
        self.download_btn = QPushButton(" Скачать")
        self.download_btn.setIcon(IconFactory.create_icon("downloader", QColor("#ffffff")))
        self.download_btn.setIconSize(QSize(32, 32))
        self.download_btn.clicked.connect(self.download_video)
        download_btn_layout.addWidget(self.download_btn, 1) 
        
        self.download_cancel_btn = QPushButton("Отмена")
        self.download_cancel_btn.setObjectName("cancelBtn")
        self.download_cancel_btn.clicked.connect(self.cancel_download)
        self.download_cancel_btn.setVisible(False) 
        download_btn_layout.addWidget(self.download_cancel_btn)

        layout.addLayout(download_btn_layout)

        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        layout.addWidget(self.download_progress)

        self.download_info = QLabel("")
        self.download_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_info.setStyleSheet("color: #8b949e; font-size: 13px;")
        self.download_info.setWordWrap(True)
        layout.addWidget(self.download_info)

        self.download_status = QLabel("")
        self.download_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_status.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 14px;")
        self.download_status.setWordWrap(True)
        layout.addWidget(self.download_status)

        layout.addStretch()
        return page

    def update_audio_format_visibility(self, text):
        is_visible = (text == "Только звук")
        self.format_container.setVisible(is_visible)

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.update_nav_buttons()

    def update_nav_buttons(self):
        current = self.stacked_widget.currentIndex()
        
        if current == 0:
            self.upscaler_btn.setProperty("active", True)
            self.upscaler_btn.setText(" Upscaler")
            self.downloader_btn.setProperty("active", False)
            self.downloader_btn.setText("")
            self.upscaler_btn.setIcon(IconFactory.create_icon("upscaler", QColor("#58a6ff")))
            self.downloader_btn.setIcon(IconFactory.create_icon("downloader", QColor("#8b949e")))
        else:
            self.upscaler_btn.setProperty("active", False)
            self.upscaler_btn.setText("")
            self.downloader_btn.setProperty("active", True)
            self.downloader_btn.setText(" Downloader")
            self.upscaler_btn.setIcon(IconFactory.create_icon("upscaler", QColor("#8b949e")))
            self.downloader_btn.setIcon(IconFactory.create_icon("downloader", QColor("#58a6ff")))
            
        self.upscaler_btn.style().unpolish(self.upscaler_btn)
        self.upscaler_btn.style().polish(self.upscaler_btn)
        self.downloader_btn.style().unpolish(self.downloader_btn)
        self.downloader_btn.style().polish(self.downloader_btn)

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_settings()
            self.output_folder = dialog.get_output_folder()
            self.load_profile_avatar() 

    def load_profile_avatar(self):
        avatar_path = Path("avatar.png")
        if avatar_path.exists():
            pixmap = QPixmap(str(avatar_path)).scaled(
                40, 40,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            rounded = QPixmap(40, 40)
            rounded.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            path = QPainterPath()
            path.addEllipse(0, 0, 40, 40)
            painter.setClipPath(path)
            
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            self.profile_btn.setIcon(QIcon(rounded))
            self.profile_btn.setIconSize(QSize(40, 40)) 
        else:
            self.profile_btn.setIcon(IconFactory.create_icon("profile", QColor("#c9d1d9")))
            self.profile_btn.setIconSize(QSize(28, 28)) 

    def open_output_folder(self):
        folder = self.output_folder
        if not folder or not os.path.isdir(folder):
            QMessageBox.information(
                self, "Папка не выбрана",
                "Сначала выберите папку для сохранения в настройках (иконка профиля)."
            )
            self.open_settings()
            folder = self.output_folder 
        
        if folder and os.path.isdir(folder):
            try:
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder])
            except:
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть папку.")
        
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл",
            "", "Медиа (*.jpg *.jpeg *.png *.gif *.mp4 *.avi *.mov *.mkv);;Все (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        self.current_file = file_path
        filename = Path(file_path).name

        try:
            ext = Path(file_path).suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                img = Image.open(file_path)
                self.original_width = img.width
                self.original_height = img.height
            else:
                cap = cv2.VideoCapture(file_path)
                self.original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
        except Exception as e:
            self.process_error(f"Не удалось прочитать файл: {e}")
            return

        self.width_spin.setValue(self.original_width)
        self.height_spin.setValue(self.original_height)

        self.file_info.setText(f"Файл: {filename} | {self.original_width}x{self.original_height}")
        self.file_info.setStyleSheet("color: #58a6ff; font-size: 14px; font-weight: bold;")
        self.drop_area.setText(f"✓ {filename}")
        self.process_btn.setEnabled(True)
        self.status_label.setText("")

    def process_file(self):
        if not self.current_file:
            return

        width = self.width_spin.value()
        height = self.height_spin.value()

        file_ext = Path(self.current_file).suffix.lower()
        base_stem = f"{Path(self.current_file).stem}_upscaled"

        if self.output_folder and os.path.exists(self.output_folder):
            upscaler_folder = Path(self.output_folder) / "Media Upscaler"
            upscaler_folder.mkdir(exist_ok=True)
            base_dir = upscaler_folder
        else:
            base_dir = Path(self.current_file).parent

        candidate = base_dir / f"{base_stem}{file_ext}"
        counter = 1
        while candidate.exists():
            candidate = base_dir / f"{base_stem}_{counter}{file_ext}"
            counter += 1

        output_path = str(candidate)

        if file_ext in ['.jpg', '.jpeg', '.png']:
            file_type = 'image'
        elif file_ext == '.gif':
            file_type = 'gif'
        else:
            file_type = 'video'

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.process_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.status_label.setText("Обработка...")
        self.status_label.setStyleSheet("color: #f0883e; font-weight: bold;")

        self.thread = UpscaleThread(self.current_file, output_path, width, height, file_type)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.process_finished)
        self.thread.error.connect(self.process_error)
        self.thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def process_finished(self, output_path):
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.status_label.setText(f"Готово! {Path(output_path).name}")
        self.status_label.setStyleSheet("color: #3fb950; font-weight: bold;")

    def process_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.status_label.setText(error_msg)
        self.status_label.setStyleSheet("color: #f85149; font-weight: bold;")

    def download_video(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите ссылку на видео")
            return

        if not self.output_folder or not os.path.isdir(self.output_folder):
            QMessageBox.information(
                self, "Папка не выбрана",
                "Сначала выберите папку для сохранения в настройках (иконка профиля)."
            )
            self.open_settings()
            if not self.output_folder or not os.path.isdir(self.output_folder):
                return 

        quality = self.quality_segment.get_value()
        audio_mode = self.audio_segment.get_value()
        audio_format = self.format_segment.get_value()

        downloader_folder = Path(self.output_folder) / "Media Downloader"
        downloader_folder.mkdir(exist_ok=True)
        
        output_template = str(downloader_folder / "%(title)s.%(ext)s")

        self.download_progress.setValue(0)
        self.download_progress.setVisible(True)
        self.download_btn.setEnabled(False)
        self.download_cancel_btn.setVisible(True) 
        self.download_status.setText("Загрузка...")
        self.download_status.setStyleSheet("color: #f0883e; font-weight: bold;")
        self.download_info.setText("")

        self.download_thread = DownloadThread(url, output_template, quality, audio_mode, audio_format)
        self.download_thread.progress.connect(self.update_download_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()

    def update_download_progress(self, data):
        percent = data.get('percent', 0)
        speed = data.get('speed', 0)
        total = data.get('total', 0)
        downloaded = data.get('downloaded', 0)

        self.download_progress.setValue(percent)

        if speed and speed > 0:
            speed_mb = speed / (1024 * 1024)
            speed_text = f"{speed_mb:.2f} MB/s"
        else:
            speed_text = "-- MB/s"

        if total > 0:
            total_mb = total / (1024 * 1024)
            downloaded_mb = downloaded / (1024 * 1024)
            size_text = f"{downloaded_mb:.1f} / {total_mb:.1f} MB"
        else:
            size_text = "Размер неизвестен"

        self.download_info.setText(f"Скорость: {speed_text} | {size_text}")

    def download_finished(self, output_path):
        self.download_progress.setVisible(False)
        self.download_btn.setEnabled(True)
        self.download_cancel_btn.setVisible(False) 
        self.download_status.setText(f"Готово! Файл сохранён")
        self.download_status.setStyleSheet("color: #3fb950; font-weight: bold;")
        self.download_info.setText("")

    def download_error(self, error_msg):
        self.download_progress.setVisible(False)
        self.download_btn.setEnabled(True)
        self.download_cancel_btn.setVisible(False) 
        self.download_status.setText(error_msg)
        self.download_status.setStyleSheet("color: #f85149; font-weight: bold;")
        self.download_info.setText("")

    def cancel_download(self):
        if hasattr(self, 'download_thread') and self.download_thread.isRunning():
            try:
                self.download_thread.terminate() 
                self.download_thread.wait(1000) 
            except Exception as e:
                print(f"Error terminating thread: {e}")
        
        self.download_error("Загрузка отменена")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion') 

    loading = LoadingScreen()
    loading.show()
    app.processEvents() 

    window = MediaUpscaler()
    window.load_profile_avatar() 

    def show_main():
        window.show()
        window.raise_()
        window.activateWindow()
        loading.close()

    QTimer.singleShot(1500, show_main) 
    
    sys.exit(app.exec())