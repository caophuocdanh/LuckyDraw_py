import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import sys, json, random, math, threading, pygame
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QIcon, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QMessageBox, QGraphicsDropShadowEffect,
    QSpinBox, QLineEdit, QColorDialog, QCheckBox
)

# ==============================================================================
# HÀM TIỆN ÍCH VÀ BIẾN TOÀN CỤC
# ==============================================================================
def resource_path(relative_path):
    """
    Lấy đường dẫn tuyệt đối tới tài nguyên (CHỈ ĐỂ ĐỌC) được đóng gói bên trong file .exe.
    Không dùng cho các file cần ghi hoặc tạo mới.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if getattr(sys, 'frozen', False):
    # Chạy từ file .exe đã đóng gói
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Chạy từ file .py
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# FIX(packaging): Định nghĩa đường dẫn cho các file dữ liệu người dùng.
# Các file này phải được đặt bên cạnh file .exe (trong APP_DIR) để có thể được tạo,
# đọc và ghi một cách an toàn, tránh lỗi khi ghi vào thư mục tạm _MEIPASS.
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
RESULTS_FILE = os.path.join(APP_DIR, "results.json")

STYLESHEET = """
        #MainWindow, #LuckyDrawWindow { background-color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; }
        #LuckyDrawWindow > QFrame { background-color: transparent; }
        #ResultsScrollArea, #ResultsContainer { background-color: transparent; border: none; }
        QScrollBar:vertical { border: none; background: #f0f0f0; width: 8px; margin: 0px; }
        QScrollBar::handle:vertical { background: #c0c0c0; min-height: 20px; border-radius: 4px; }
        QScrollBar::handle:vertical:hover { background: #a0a0a0; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
        #ConfigContainer, .Card { background-color: #ffffff; border-radius: 0px; }
        QLabel.FormLabel { font-weight: 500; font-size: 14px; color: #343a40; margin-top: 10px; margin-bottom: 5px; }
        QLineEdit, QSpinBox { border: 1px solid #dee2e6; border-radius: 6px; padding: 8px 10px; font-size: 14px; background-color: #ffffff; }
        QLineEdit:focus, QSpinBox:focus { border: 1px solid #007bff; }
        #PrizesHeader { font-size: 16px; font-weight: bold; margin-top: 15px; padding-bottom: 8px; border-bottom: 1px solid #dee2e6; }
        QPushButton { border-radius: 6px; font-size: 14px; font-weight: 500; padding: 10px 15px; }
        #AddButton { color: #007bff; background-color: #e7f3ff; border: 1px solid #007bff; }
        #AddButton:hover { background-color: #d0e7ff; }
        #SaveButton { color: white; background-color: #28a745; border: none; }
        #SaveButton:hover { background-color: #218838; }
        QPushButton.DeleteButton { background-color: transparent; color: #dc3545; border: none; font-size: 24px; font-weight: bold; max-width: 30px; }
        QPushButton.DeleteButton:hover { color: #a71d2a; }
        #NumberLabel { background-color: white; color: black; border: 1px solid #ccc; border-radius: 4px; }
        #DrawButton { font-size: 60px; background-color: #f72585; color: white; border: none; min-width: 150px; min-height: 150px; border-radius: 55%; }
        #DrawButton:disabled { background-color: #cccccc; color: #888888; }
        #ResultLabel { color: white; font-size: 16px; font-weight: bold; padding: 25px; border-radius: 5px; margin: 5px;}
        #TopRightButton { background-color: transparent; border: none; font-size: 22px; color: #555; padding: 5px; }
        #TopRightButton:hover { color: #000; }
        QCheckBox { font-size: 14px; margin-top: 15px; }
        """

class QSpinBoxWithPlaceholder(QSpinBox):
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent); self._placeholder_text = placeholder_text; self.setMinimum(0)
    def textFromValue(self, value):
        if value == self.minimum() and not self.hasFocus() and self._placeholder_text: return self._placeholder_text
        return super().textFromValue(value)
    def value(self):
        if self.text() == self._placeholder_text: return self.minimum()
        return super().value()
    def focusInEvent(self, event):
        if self.text() == self._placeholder_text: self.lineEdit().clear()
        super().focusInEvent(event); self.update()
    def focusOutEvent(self, event):
        super().focusOutEvent(event); self.update()

class PrizeItemWidget(QFrame):
    deleted = Signal(QWidget)
    def __init__(self, prize_id, name, quantity, color_hex, parent=None):
        super().__init__(parent)
        self.prize_id = prize_id; self.setObjectName("PrizeItem")
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 5, 0, 5); layout.setSpacing(10)
        self.name_input = QLineEdit(name); self.name_input.setPlaceholderText("Tên giải thưởng")
        self.quantity_input = QSpinBox(); self.quantity_input.setMinimum(1); self.quantity_input.setValue(quantity); self.quantity_input.setFixedWidth(60)
        self.color_preview = QPushButton(cursor=Qt.PointingHandCursor); self.color_preview.setFixedSize(24, 24); self.color_preview.clicked.connect(self.open_color_picker)
        self.color_input = QLineEdit(color_hex); self.color_input.setFixedWidth(90); self.color_input.textChanged.connect(self.update_color_from_text)
        self.delete_button = QPushButton("🗑️", objectName="DeleteButton", toolTip="Xóa giải này", cursor=Qt.PointingHandCursor); self.delete_button.clicked.connect(lambda: self.deleted.emit(self))
        for w in [self.name_input, self.quantity_input, self.color_preview, self.color_input, self.delete_button]: layout.addWidget(w)
        self.update_color_from_text(color_hex)
    def update_color_from_text(self, text):
        color = QColor(text)
        self.color_preview.setStyleSheet(f"background-color: {text if color.isValid() else 'white'}; border: 1px solid {'#ccc' if color.isValid() else 'red'}; border-radius: 4px;")
    def open_color_picker(self):
        color = QColorDialog.getColor(QColor(self.color_input.text()), self, "Chọn màu")
        if color.isValid(): self.color_input.setText(color.name())
    def get_data(self): return {"id": self.prize_id, "name": self.name_input.text(), "count": self.quantity_input.value(), "color": self.color_input.text()}

class ConfigWindow(QWidget):
    next_prize_id = 1
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow"); self.setWindowTitle("Cấu hình Lucky Draw"); self.setMinimumWidth(550)
        main_layout = QVBoxLayout(self); main_layout.setAlignment(Qt.AlignCenter)
        container = QFrame(objectName="ConfigContainer", fixedWidth=500)
        container.setLayout(QVBoxLayout()); container.layout().setContentsMargins(25, 25, 25, 25)
        main_layout.addWidget(container)
        shadow = QGraphicsDropShadowEffect(blurRadius=25, xOffset=0, yOffset=4, color=QColor(0, 0, 0, 40))
        container.setGraphicsEffect(shadow)

        self.title_input = self.create_form_group(container, "Tiêu đề")
        self.participants_input = self.create_form_group(container, "Tổng số người", is_number=True)

        self.music_checkbox = QCheckBox("Sử dụng nhạc nền khi quay")
        container.layout().addWidget(self.music_checkbox)

        self.music_time_label = QLabel("Độ dài nhạc (giây)"); self.music_time_label.setProperty("class", "FormLabel")
        self.music_duration_input = QSpinBoxWithPlaceholder("Nhập số giây"); self.music_duration_input.setRange(0, 99999)
        self.bg_music_label = QLabel("File nhạc nền"); self.bg_music_label.setProperty("class", "FormLabel")
        self.bg_music_input = self.create_form_group(container, "", placeholder="VD: assets/background_music.mp3", add_to_layout=False)
        self.win_sound_label = QLabel("File âm thanh chiến thắng"); self.win_sound_label.setProperty("class", "FormLabel")
        self.win_sound_input = self.create_form_group(container, "", placeholder="VD: assets/win_sound.mp3", add_to_layout=False)

        music_widgets = [self.music_time_label, self.music_duration_input, self.bg_music_label, self.bg_music_input, self.win_sound_label, self.win_sound_input]
        for w in music_widgets: container.layout().addWidget(w)

        self.fixed_time_label = QLabel("Thời gian quay (giây)"); self.fixed_time_label.setProperty("class", "FormLabel")
        self.spin_time_input = QSpinBoxWithPlaceholder("Nhập số giây"); self.spin_time_input.setRange(0, 99999)
        container.layout().addWidget(self.fixed_time_label); container.layout().addWidget(self.spin_time_input)

        self.music_checkbox.stateChanged.connect(self.toggle_music_options)

        container.layout().addWidget(QLabel("Giải thưởng", objectName="PrizesHeader"))
        self.prize_list_layout = QVBoxLayout(); self.prize_list_layout.setSpacing(5); self.prize_list_layout.addStretch(1)
        container.layout().addLayout(self.prize_list_layout)

        self.load_config()

        footer_layout = QHBoxLayout()
        add_button = QPushButton("+ Thêm giải", objectName="AddButton"); add_button.clicked.connect(self.add_new_prize_item)
        save_button = QPushButton("Lưu và đóng", objectName="SaveButton"); save_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogSaveButton)); save_button.clicked.connect(self.save_config_and_close)
        footer_layout.addWidget(add_button); footer_layout.addStretch(); footer_layout.addWidget(save_button)
        container.layout().addLayout(footer_layout)

    def toggle_music_options(self, state):
        use_music = state == Qt.CheckState.Checked.value
        self.music_time_label.setVisible(use_music)
        self.music_duration_input.setVisible(use_music)
        self.bg_music_label.setVisible(use_music)
        self.bg_music_input.setVisible(use_music)
        self.win_sound_label.setVisible(use_music)
        self.win_sound_input.setVisible(use_music)

        self.fixed_time_label.setVisible(not use_music)
        self.spin_time_input.setVisible(not use_music)

    def create_form_group(self, parent_widget, label_text, is_number=False, placeholder="", add_to_layout=True):
        if label_text:
            label = QLabel(label_text); label.setProperty("class", "FormLabel")
            if add_to_layout: parent_widget.layout().addWidget(label)
        widget = QSpinBoxWithPlaceholder(placeholder_text=placeholder) if is_number else QLineEdit()
        if is_number: widget.setRange(0, 99999)
        elif placeholder: widget.setPlaceholderText(placeholder)
        if add_to_layout: parent_widget.layout().addWidget(widget)
        return widget

    def load_config(self):
        self.clear_prizes()
        max_id = 0
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: config = json.load(f)
            settings = config.get("settings", {})
            self.title_input.setText(settings.get("title", "Lucky Draw"))
            self.participants_input.setValue(settings.get("total_numbers", 0))
            self.spin_time_input.setValue(settings.get("draw_duration_seconds", 5))

            use_music = settings.get("music", False)
            self.music_checkbox.setChecked(use_music)

            self.music_duration_input.setValue(settings.get("music_duration", 20))
            self.bg_music_input.setText(settings.get("background_music_path", os.path.join("assets", "background_music.mp3")))
            self.win_sound_input.setText(settings.get("win_sound_path", os.path.join("assets", "win_sound.mp3")))

            self.toggle_music_options(self.music_checkbox.checkState().value)

            prizes = sorted(config.get("prizes", []), key=lambda p: p.get('id', 999))
            for prize_data in prizes:
                prize_id = prize_data.get('id', self.next_prize_id)
                self.add_prize_item(prize_id, prize_data.get("name"), prize_data.get("count", 1), prize_data.get("color"))
                max_id = max(max_id, prize_id)
        except (FileNotFoundError, json.JSONDecodeError): self.load_default_config()
        self.next_prize_id = max_id + 1

    def load_default_config(self):
        self.title_input.setText("Lucky Draw"); self.participants_input.setValue(56)
        self.spin_time_input.setValue(5)
        self.music_checkbox.setChecked(False)

        self.music_duration_input.setValue(20)
        self.bg_music_input.setText(os.path.join("assets", "background_music.mp3"))
        self.win_sound_input.setText(os.path.join("assets", "win_sound.mp3"))

        self.toggle_music_options(self.music_checkbox.checkState().value)
        self.clear_prizes()
        default_prizes = [{"id":1,"name":"Giải Nhất","count":1,"color":"#f72585"},{"id":2,"name":"Giải Nhì","count":2,"color":"#aa0000"},{"id":3,"name":"Giải Ba","count":2,"color":"#00557f"},{"id":4,"name":"Giải Khuyến Khích","count":4,"color":"#55aa00"}]
        for prize in default_prizes: self.add_prize_item(prize["id"], prize["name"], prize["count"], prize["color"])
        self.next_prize_id = 2

    def save_config_and_close(self):
        prizes_data = [self.prize_list_layout.itemAt(i).widget().get_data() for i in range(self.prize_list_layout.count() - 1)]
        for i, prize_dict in enumerate(prizes_data): prize_dict['id'] = i + 1

        total_prizes = sum(p.get('count', 0) for p in prizes_data)
        total_numbers = self.participants_input.value()
        warning_needed = False
        if total_numbers < total_prizes:
            warning_needed = True; total_numbers = total_prizes
            self.participants_input.setValue(total_numbers)

        config_data = {"settings": {
            "title": self.title_input.text(), "total_numbers": total_numbers,
            "draw_duration_seconds": self.spin_time_input.value(),
            "music": self.music_checkbox.isChecked(),
            "music_duration": self.music_duration_input.value(),
            "background_music_path": self.bg_music_input.text(),
            "win_sound_path": self.win_sound_input.text()},
            "prizes": prizes_data }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=2, ensure_ascii=False)
            if warning_needed: QMessageBox.warning(self, "Tự động điều chỉnh", f"Tổng số người ít hơn tổng số giải.\nĐã tự động cập nhật Tổng số người thành {total_numbers}.")
            QMessageBox.information(self, "Thành công", "Đã lưu cấu hình.\nHãy làm mới (💫) hoặc khởi động lại ứng dụng để áp dụng.")
            self.close()
        except Exception as e: QMessageBox.critical(self, "Lỗi", f"Không thể lưu file cấu hình: {e}")

    def add_prize_item(self, prize_id, name, quantity, color):
        widget = PrizeItemWidget(prize_id, name, quantity, color); widget.deleted.connect(self.remove_prize_item)
        self.prize_list_layout.insertWidget(self.prize_list_layout.count() - 1, widget)
    def add_new_prize_item(self): self.add_prize_item(self.next_prize_id, name="", quantity=1, color="#cccccc"); self.next_prize_id += 1
    def clear_prizes(self):
        while self.prize_list_layout.count() > 1:
            if (item := self.prize_list_layout.takeAt(0).widget()): item.deleteLater()
    def remove_prize_item(self, widget_to_remove): widget_to_remove.deleteLater()

class LuckyDrawApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("LuckyDrawWindow")
        self.initialized_successfully = False
        self.is_drawing = self.is_blinking = False
        self.flashed_labels, self.number_labels = [], {}
        self.results_file = RESULTS_FILE

        try: pygame.mixer.init()
        except Exception as e: print(f"Không thể khởi tạo pygame.mixer: {e}")
        if not self.load_config(): return

        self.all_numbers = list(range(1, self.settings.get('total_numbers', 0) + 1))
        self.available_numbers = self.all_numbers.copy()
        self.prize_queue = [dict(p) for p in reversed(self.prizes_config) for _ in range(p['count'])]

        self.animation_timer = QTimer(self, interval=100, timeout=self.animate_cells)
        self.blink_timer = QTimer(self, interval=200)

        self.setup_ui(); self.load_previous_results(); self.initialized_successfully = True

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: self.config = json.load(f)
            self.settings = self.config['settings']
            self.prizes_config = sorted(self.config.get("prizes", []), key=lambda p: p.get('id', 999))
            if sum(p['count'] for p in self.prizes_config) > self.settings.get('total_numbers', 0):
                QMessageBox.critical(self, "Lỗi", "Số lượng giải thưởng nhiều hơn số lượng người tham gia!"); return False
            return True
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đọc hoặc phân tích file config.json!\n{e}"); return False

    def setup_ui(self):
        self.setWindowTitle(self.settings.get('title', "Quay Số May Mắn"))
        overall_layout = QVBoxLayout(self); overall_layout.setContentsMargins(10, 5, 10, 10); overall_layout.setSpacing(10)
        self.add_top_right_buttons(overall_layout)
        main_content_layout = QHBoxLayout(); main_content_layout.setSpacing(20)
        self.left_frame = QFrame(self); self.grid_layout = QGridLayout(self.left_frame); self.grid_layout.setSpacing(5)
        self.right_frame = QFrame(self, fixedWidth=400)
        main_content_layout.addWidget(self.left_frame, 1); main_content_layout.addWidget(self.right_frame)
        overall_layout.addLayout(main_content_layout)
        self.setup_right_panel(); self.create_number_grid(); self.redraw_number_grid()

    def add_top_right_buttons(self, parent_layout):
        top_button_layout = QHBoxLayout(); top_button_layout.addStretch(1)
        buttons = [("⚙️", self.open_settings, "Cấu hình"), ("💫", self.soft_reset_app, "Bắt đầu lại (giữ kết quả)"),
                   ("🗑️", self.clear_and_reset_app, "Xóa toàn bộ kết quả và làm mới"), ("❌", self.close, "Thoát")]
        for text, cmd, tip in buttons:
            btn = QPushButton(text, objectName="TopRightButton", toolTip=tip, cursor=Qt.PointingHandCursor); btn.clicked.connect(cmd)
            top_button_layout.addWidget(btn)
        parent_layout.addLayout(top_button_layout)

    def setup_right_panel(self):
        right_layout = QVBoxLayout(self.right_frame); right_layout.setAlignment(Qt.AlignCenter)
        self.draw_button = QPushButton("👻", objectName="DrawButton", cursor=Qt.PointingHandCursor); self.draw_button.clicked.connect(self.start_draw)
        scroll_area = QScrollArea(objectName="ResultsScrollArea", widgetResizable=True)
        results_container = QWidget(objectName="ResultsContainer")
        self.results_layout = QVBoxLayout(results_container); self.results_layout.setAlignment(Qt.AlignTop); self.results_layout.setSpacing(5)
        scroll_area.setWidget(results_container)
        right_layout.addWidget(self.draw_button, 0, Qt.AlignCenter); right_layout.addSpacing(30); right_layout.addWidget(scroll_area, 1)

    def create_number_grid(self): self.number_labels = {num: QLabel(f"{num:02d}", objectName="NumberLabel", alignment=Qt.AlignCenter) for num in self.all_numbers}
    def redraw_number_grid(self):
        while (item := self.grid_layout.takeAt(0)):
            if (widget := item.widget()): widget.setParent(None)
        w, h, n = self.left_frame.width(), self.left_frame.height(), len(self.all_numbers)
        if w < 50 or h < 50 or n == 0: return
        cols = max(1, int(math.sqrt(n * w / h))); rows = math.ceil(n / cols)
        cell_height = h / rows; font_size = max(8, min(40, int(cell_height * 0.4)))
        font = QFont('Segoe UI', font_size, QFont.Bold)
        for i, number in enumerate(random.sample(self.all_numbers, n)):
            label = self.number_labels[number]; label.setFont(font); self.grid_layout.addWidget(label, i // cols, i % cols)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.draw_button.isEnabled(): self.start_draw()
        super().keyPressEvent(event)

    def start_draw(self):
        if self.is_drawing or self.is_blinking: return
        if not self.prize_queue or not self.available_numbers: return QMessageBox.information(self, "Thông báo", "Hết giải thưởng hoặc không còn số để quay!")

        self.is_drawing = True; self.draw_button.setEnabled(False); self.current_prize = self.prize_queue.pop(0)

        if self.settings.get("music", False):
            music_path = self.settings.get("background_music_path")
            self.play_sound(music_path, is_background=True)
            duration = self.settings.get("music_duration", 20)
        else:
            duration = self.settings.get('draw_duration_seconds', 5)
        self.animation_timer.start(); QTimer.singleShot(duration * 1000, self.finish_draw)

    def animate_cells(self):
        for lbl, style in self.flashed_labels: lbl.setStyleSheet(style)
        self.flashed_labels.clear()
        if self.available_numbers:
            to_flash = random.sample(self.available_numbers, min(len(self.available_numbers) // 10 + 1, len(self.available_numbers)))
            for num in to_flash:
                lbl = self.number_labels[num]; self.flashed_labels.append((lbl, lbl.styleSheet()))
                lbl.setStyleSheet("background-color: #FFD700; color: black; border: 2px solid #DAA520; border-radius: 4px;")

    def finish_draw(self):
        self.animation_timer.stop(); self.is_drawing = False
        if self.settings.get("music", False): pygame.mixer.music.stop()
        for lbl, style in self.flashed_labels: lbl.setStyleSheet(style)
        self.flashed_labels.clear()
        if not self.available_numbers: return self.draw_button.setEnabled(True)
        winner = random.choice(self.available_numbers); self.available_numbers.remove(winner)
        self.is_blinking = True; self.blink_count = 6; self.winner_label = self.number_labels[winner]
        self.blink_timer.timeout.connect(lambda: self.blink_step(winner)); self.blink_timer.start()

    def blink_step(self, winner):
        color = self.current_prize['color']; is_on = self.blink_count % 2 == 0
        style = f"background-color: {color}; color: white;" if is_on else "background-color: white; color: black;"
        self.winner_label.setStyleSheet(f"#NumberLabel {{ {style} border: 2px solid {color}; }}")
        self.blink_count -= 1
        if self.blink_count < 0: self.blink_timer.stop(); self.blink_timer.timeout.disconnect(); self.on_blink_done(winner)

    def on_blink_done(self, number):
        self.is_blinking = False; color = self.current_prize['color']
        self.number_labels[number].setStyleSheet(f"#NumberLabel {{ background-color: {color}; color: white; }}")
        self.add_result_to_list(self.current_prize, number, is_loading=False); self.save_result_to_file(self.current_prize, number)
        win_sound_path = self.settings.get("win_sound_path")
        self.play_sound(win_sound_path); self.draw_button.setEnabled(True)

    def add_result_to_list(self, prize, number, is_loading=True):
        label = QLabel(f"{prize['name']}: {number:02d}", objectName="ResultLabel", alignment=Qt.AlignCenter)
        label.setStyleSheet(f"#ResultLabel {{ background-color: {prize['color']}; }}")
        self.results_layout.insertWidget(0, label) if not is_loading else self.results_layout.addWidget(label)

    def load_previous_results(self):
        if not os.path.exists(self.results_file): return
        try:
            with open(self.results_file, "r", encoding="utf-8") as f:
                results = [json.loads(line) for line in f if line.strip()]
            for res in reversed(results):
                prize = next((p for p in self.prizes_config if p['name'] == res['prize']), None)
                if prize and res['number'] in self.available_numbers:
                    self.available_numbers.remove(res['number'])
                    self.prize_queue.remove(next(p for p in self.prize_queue if p['name'] == prize['name']))
                    self.add_result_to_list(prize, res['number'], is_loading=True)
                    self.number_labels[res['number']].setStyleSheet(f"#NumberLabel {{ background-color: {prize['color']}; color: white; }}")
        except Exception as e: print(f"Lỗi tải kết quả cũ: {e}"); os.remove(self.results_file)

    def save_result_to_file(self, prize, number):
        try:
            with open(self.results_file, "a", encoding="utf-8") as f: f.write(json.dumps({"prize": prize['name'], "number": number}, ensure_ascii=False) + "\n")
        except Exception as e: print(f"Lỗi ghi file kết quả: {e}")

    def play_sound(self, file, is_background=False):
        if not pygame.mixer.get_init() or not file:
            return

        # FIX(packaging): Sửa lỗi không tìm thấy file nhạc.
        # Đường dẫn file nhạc phải được tạo từ APP_DIR (thư mục của .exe)
        # để trỏ đến thư mục 'assets' bên ngoài.
        file_path = os.path.join(APP_DIR, file)

        if not os.path.exists(file_path):
            print(f"Cảnh báo: Không tìm thấy file âm thanh tại '{file_path}'. Bỏ qua.")
            return

        def _play():
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play(-1 if is_background else 0)
            except Exception as e:
                print(f"Lỗi phát nhạc '{file_path}': {e}")
        threading.Thread(target=_play, daemon=True).start()

    def reset_application_state(self, clear_results_file=False):
        """
        FIX(packaging): Khắc phục lỗi reset app khi đóng gói.
        Thay vì khởi động lại process (gây lỗi), hàm này sẽ reset lại trạng thái
        của ứng dụng ngay bên trong tiến trình đang chạy.
        """
        if clear_results_file:
            if os.path.exists(self.results_file):
                try: os.remove(self.results_file)
                except OSError as e: QMessageBox.critical(self, "Lỗi", f"Không thể xóa file kết quả: {e}"); return

        while self.results_layout.count() > 0:
            if (item := self.results_layout.takeAt(0).widget()): item.deleteLater()

        if not self.load_config():
            QMessageBox.critical(self, "Lỗi", "Không thể tải lại cấu hình. Ứng dụng có thể không hoạt động đúng.")
            self.draw_button.setEnabled(False); return

        self.all_numbers = list(range(1, self.settings.get('total_numbers', 0) + 1))
        self.available_numbers = self.all_numbers.copy()
        self.prize_queue = [dict(p) for p in reversed(self.prizes_config) for _ in range(p['count'])]
        self.create_number_grid(); self.redraw_number_grid()
        self.load_previous_results()
        self.setWindowTitle(self.settings.get('title', "Quay Số May Mắn"))
        self.is_drawing = self.is_blinking = False; self.animation_timer.stop(); self.blink_timer.stop()
        self.draw_button.setEnabled(bool(self.prize_queue and self.available_numbers))
        QMessageBox.information(self, "Hoàn tất", "Ứng dụng đã được làm mới.")

    def soft_reset_app(self):
        # THAY THẾ: Gọi hàm reset an toàn, không gây crash
        self.reset_application_state(clear_results_file=False)

    def clear_and_reset_app(self):
        if QMessageBox.question(self, "Xác nhận Xóa", "Bạn có chắc muốn XÓA TOÀN BỘ kết quả và làm mới?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            # THAY THẾ: Gọi hàm reset an toàn, không gây crash
            self.reset_application_state(clear_results_file=True)

    def open_settings(self): self.config_dialog = ConfigWindow(); self.config_dialog.show()
    def resizeEvent(self, event): super().resizeEvent(event); self.redraw_number_grid()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    if not os.path.exists(CONFIG_FILE):
        QMessageBox.critical(None, "Lỗi file cấu hình", f"Chưa có file cấu hình.\nXác nhận để khởi tạo file cấu hình mẫu bên cạnh file chạy.")
        config_win = ConfigWindow()
        config_win.show()
    else:
        window = LuckyDrawApp()
        if window.initialized_successfully: window.showFullScreen()
    sys.exit(app.exec())