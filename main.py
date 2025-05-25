import sys
import os
import json
import re
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QListWidget, 
                            QListWidgetItem, QTextEdit, QFileDialog, QTabWidget, 
                            QComboBox, QMessageBox, QSplitter, QMenu, QAction, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt5.QtGui import QIcon

class MinecraftVersion(Enum):
    VERSION_1_12_2 = "1.12.2"
    VERSION_1_16 = "1.16"
    VERSION_1_18 = "1.18"
    VERSION_1_19 = "1.19"
    VERSION_1_20 = "1.20"

class LangFormat(Enum):
    JSON = "json"
    LANG = "lang"

def get_format_for_version(version):
    """根据Minecraft版本确定语言文件格式"""
    if version == MinecraftVersion.VERSION_1_12_2:
        return LangFormat.LANG
    else:
        return LangFormat.JSON

class TextElement:
    def __init__(self, key, original_text, translated_text=""):
        self.key = key
        self.original_text = original_text
        self.translated_text = translated_text
        self._changed = False
        
    @property
    def is_translated(self):
        return bool(self.translated_text.strip())
    
    @property
    def is_changed(self):
        return self._changed
    
    def set_translated_text(self, text):
        if text != self.translated_text:
            self.translated_text = text
            self._changed = True
            
    def reset(self):
        self.translated_text = ""
        self._changed = False
        
    def __str__(self):
        return self.translated_text if self.is_translated else self.original_text

class LangFileParser:
    @staticmethod
    def detect_format(text):
        """自动检测语言文件格式"""
        # 清理文本，移除BOM标记和空白字符
        text = text.lstrip('\ufeff').strip()
        if not text:
            raise ValueError("文件内容为空")

        # 尝试解析为JSON
        try:
            json_data = json.loads(text)
            # 检查是否是键值对格式
            if isinstance(json_data, dict) and all(isinstance(v, str) for v in json_data.values()):
                return LangFormat.JSON, MinecraftVersion.VERSION_1_16  # 默认使用1.16版本
        except json.JSONDecodeError:
            pass

        # 检查是否是LANG格式
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() and value.strip():
                        return LangFormat.LANG, MinecraftVersion.VERSION_1_12_2

        raise ValueError("无法识别的语言文件格式，请确保文件是有效的语言文件")

    @staticmethod
    def parse(text, format):
        """解析语言文件，返回键值字典"""
        if format == LangFormat.LANG:
            return LangFileParser._parse_lang(text)
        elif format == LangFormat.JSON:
            return LangFileParser._parse_json(text)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    @staticmethod
    def _parse_lang(text):
        """解析.lang格式文件"""
        result = {}
        keys = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
                
            separator_index = line.find('=')
            if separator_index == -1:
                continue
                
            key = line[:separator_index].strip()
            value = line[separator_index+1:].strip()
            
            if key and value:  # 确保键和值都不为空
                if key not in result:
                    keys.append(key)
                    result[key] = value
                
        if not result:
            raise ValueError("未找到有效的翻译条目")
                
        return result, keys
    
    @staticmethod
    def _parse_json(text):
        """解析JSON格式文件"""
        result = {}
        keys = []
        
        try:
            json_data = json.loads(text)
            for key, value in json_data.items():
                if isinstance(value, str):  # 只处理字符串值
                    keys.append(key)
                    result[key] = value
                
            if not result:
                raise ValueError("未找到有效的翻译条目")
                
            return result, keys
        except json.JSONDecodeError:
            raise ValueError("JSON格式无效")
    
    @staticmethod
    def generate_output(data, format, keys=None):
        """生成输出文件内容"""
        if format == LangFormat.LANG:
            lines = []
            for key in keys or data.keys():
                lines.append(f"{key}={data[key]}")
            return '\n'.join(lines)
        elif format == LangFormat.JSON:
            if keys:
                ordered_dict = {key: data[key] for key in keys if key in data}
                return json.dumps(ordered_dict, ensure_ascii=False, indent=4)
            else:
                return json.dumps(data, ensure_ascii=False, indent=4)
        else:
            raise ValueError(f"不支持的格式: {format}")

class ModDictionary:
    def __init__(self, mod_namespace, version):
        self.mod_namespace = mod_namespace
        self.version = version
        self.format = get_format_for_version(version)
        self.text_dictionary = {}  # 键值对字典
        self.keys = []  # 保持原始顺序
        
    def load_original_file(self, text):
        """加载原始语言文件"""
        try:
            # 先检测格式
            format, version = LangFileParser.detect_format(text)
            self.format = format
            self.version = version
            
            # 然后解析内容
            result, self.keys = LangFileParser.parse(text, self.format)
            if not result:
                raise ValueError("未找到有效的翻译条目")
                
            self.text_dictionary.clear()
            for key in self.keys:
                self.text_dictionary[key] = TextElement(key, result[key])
        except Exception as e:
            raise ValueError(f"加载文件失败: {str(e)}")
    
    def load_translated_file(self, text):
        """加载已翻译的语言文件"""
        if not self.text_dictionary:
            raise ValueError("必须先加载原始文本才能加载翻译")
            
        result, _ = LangFileParser.parse(text, self.format)
        for key, value in result.items():
            if key in self.text_dictionary:
                self.text_dictionary[key].set_translated_text(value)
    
    def export(self):
        """导出翻译后的文件"""
        output_dict = {}
        for key in self.keys:
            element = self.text_dictionary[key]
            output_dict[key] = str(element)
            
        return LangFileParser.generate_output(output_dict, self.format, self.keys)

class TranslationItem(QWidget):
    """翻译项目的UI组件"""
    saved = pyqtSignal(str, str)  # 信号：(key, translated_text)
    
    def __init__(self, text_element, parent=None):
        super().__init__(parent)
        self.text_element = text_element
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 原文
        layout.addWidget(QLabel("原文:"))
        self.original_text = QTextEdit()
        self.original_text.setPlainText(self.text_element.original_text)
        self.original_text.setReadOnly(True)
        layout.addWidget(self.original_text)
        
        # 译文
        layout.addWidget(QLabel("译文:"))
        self.translated_text = QTextEdit()
        self.translated_text.setPlainText(self.text_element.translated_text)
        self.translated_text.installEventFilter(self)
        layout.addWidget(self.translated_text)
        
        # 按钮
        buttons_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset)
        buttons_layout.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
        # 设置初始焦点到译文输入框
        self.translated_text.setFocus()
        
    def eventFilter(self, obj, event):
        """事件过滤器，处理键盘事件"""
        if obj == self.translated_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if event.modifiers() & Qt.ShiftModifier:
                    # Shift+Enter: 插入换行
                    cursor = self.translated_text.textCursor()
                    cursor.insertText("\n")
                    return True
                else:
                    # Enter: 保存并进入下一个
                    self.save()
                    return True
        return super().eventFilter(obj, event)
        
    def reset(self):
        """重置译文"""
        self.translated_text.setPlainText("")
        self.text_element.reset()
        self.translated_text.setFocus()
        
    def save(self):
        """保存译文"""
        text = self.translated_text.toPlainText()
        self.text_element.set_translated_text(text)
        self.saved.emit(self.text_element.key, text)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mod_dictionary = None
        self.current_key = None
        # 获取图标路径
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        self.check_icon = os.path.join(self.icon_path, "check.png")
        self.empty_icon = os.path.join(self.icon_path, "empty.png")
        # 检查图标文件是否存在
        if not os.path.exists(self.check_icon) or not os.path.exists(self.empty_icon):
            print(f"警告: 图标文件不存在")
            print(f"检查路径: {self.check_icon}")
            print(f"检查路径: {self.empty_icon}")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PythonTranslator - Minecraft模组翻译工具 by友野YouyEr")
        self.setMinimumSize(1000, 600)
        
        # 主窗口小部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 创建选项卡窗口
        self.tabs = QTabWidget()
        
        # 创建三个选项卡页面
        self.open_tab = QWidget()
        self.editor_tab = QWidget()
        self.export_tab = QWidget()
        
        self.tabs.addTab(self.open_tab, "打开")
        self.tabs.addTab(self.editor_tab, "翻译")
        self.tabs.addTab(self.export_tab, "导出")
        
        main_layout.addWidget(self.tabs)
        
        # 设置打开选项卡
        self.setup_open_tab()
        
        # 设置编辑器选项卡
        self.setup_editor_tab()
        
        # 设置导出选项卡
        self.setup_export_tab()
        
        # 初始设置编辑器和导出选项卡为禁用状态
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        
    def setup_open_tab(self):
        layout = QVBoxLayout(self.open_tab)
        
        # 命名空间
        namespace_layout = QHBoxLayout()
        namespace_layout.addWidget(QLabel("模组命名空间:"))
        self.namespace_edit = QLineEdit()
        self.namespace_edit.setPlaceholderText("输入模组命名空间，例如：minecraft")  # 添加占位文本
        namespace_layout.addWidget(self.namespace_edit)
        layout.addLayout(namespace_layout)
        
        # 打开文件按钮
        open_layout = QVBoxLayout()
        
        self.open_original_btn = QPushButton("打开原始语言文件")
        self.open_original_btn.clicked.connect(self.open_original_file)
        open_layout.addWidget(self.open_original_btn)
        
        self.open_translated_btn = QPushButton("打开已翻译语言文件(可选)")
        self.open_translated_btn.clicked.connect(self.open_translated_file)
        self.open_translated_btn.setEnabled(False)
        open_layout.addWidget(self.open_translated_btn)
        
        layout.addLayout(open_layout)
        
        # 文件状态
        status_layout = QVBoxLayout()
        self.original_status = QLabel("原始文件: 未加载")
        status_layout.addWidget(self.original_status)
        self.translated_status = QLabel("翻译文件: 未加载")
        status_layout.addWidget(self.translated_status)
        layout.addLayout(status_layout)
        
        # 开始翻译按钮
        self.start_btn = QPushButton("开始翻译")
        self.start_btn.clicked.connect(self.start_translation)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)
        
    def setup_editor_tab(self):
        layout = QHBoxLayout(self.editor_tab)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧列表
        self.entry_list = QListWidget()
        self.entry_list.currentItemChanged.connect(self.update_translation_item)
        splitter.addWidget(self.entry_list)
        
        # 右侧翻译区域
        self.translation_panel = QWidget()
        translation_layout = QVBoxLayout(self.translation_panel)
        
        # 翻译进度
        self.progress_label = QLabel("翻译进度: 0 / 0")
        translation_layout.addWidget(self.progress_label)
        
        # 翻译操作区
        self.translation_container = QWidget()
        self.translation_container_layout = QVBoxLayout(self.translation_container)
        translation_layout.addWidget(self.translation_container)
        
        # 导航按钮
        nav_buttons = QHBoxLayout()
        
        self.prev_btn = QPushButton("上一个")
        self.prev_btn.clicked.connect(self.go_to_previous)
        nav_buttons.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("下一个")
        self.next_btn.clicked.connect(self.go_to_next)
        nav_buttons.addWidget(self.next_btn)
        
        self.skip_btn = QPushButton("跳过")
        self.skip_btn.clicked.connect(self.skip_to_next_untranslated)
        nav_buttons.addWidget(self.skip_btn)
        
        translation_layout.addLayout(nav_buttons)
        
        # 批量操作按钮
        bulk_buttons = QHBoxLayout()
        
        self.clear_duplicates_btn = QPushButton("清除重复译文")
        self.clear_duplicates_btn.clicked.connect(self.clear_duplicate_translations)
        bulk_buttons.addWidget(self.clear_duplicates_btn)
        
        self.fill_empty_btn = QPushButton("填充原文到译文")
        self.fill_empty_btn.clicked.connect(self.fill_empty_translations)
        bulk_buttons.addWidget(self.fill_empty_btn)
        
        translation_layout.addLayout(bulk_buttons)
        
        # 完成按钮
        self.finish_btn = QPushButton("完成翻译")
        self.finish_btn.clicked.connect(self.finish_translation)
        translation_layout.addWidget(self.finish_btn)
        
        splitter.addWidget(self.translation_panel)
        
        # 设置分割比例
        splitter.setSizes([200, 800])
        
    def setup_export_tab(self):
        layout = QVBoxLayout(self.export_tab)
        
        # 预览区域
        layout.addWidget(QLabel("翻译结果预览:"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)
        
        # 导出按钮
        export_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存翻译文件")
        self.save_btn.clicked.connect(self.save_translation_file)
        export_layout.addWidget(self.save_btn)
        
        self.back_btn = QPushButton("返回翻译")
        self.back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        export_layout.addWidget(self.back_btn)
        
        layout.addLayout(export_layout)
        
    def open_original_file(self):
        """打开原始语言文件"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择原始语言文件", "", 
            "语言文件 (*.lang *.json);;所有文件 (*)", 
            options=options
        )
        
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                # 自动检测格式和版本
                format, version = LangFileParser.detect_format(content)
                
                # 创建模组字典
                namespace = self.namespace_edit.text().strip()
                if not namespace:
                    namespace = "mod"  # 默认命名空间
                    
                self.mod_dictionary = ModDictionary(namespace, version)
                self.mod_dictionary.load_original_file(content)
                
                # 更新UI
                self.original_status.setText(f"原始文件: {os.path.basename(file_name)} ({version.value})")
                self.open_translated_btn.setEnabled(True)
                self.start_btn.setEnabled(True)
                
                QMessageBox.information(self, "成功", f"已加载原始文件，包含{len(self.mod_dictionary.keys)}个翻译条目")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件失败: {str(e)}")
    
    def open_translated_file(self):
        """打开已有的翻译文件"""
        if not self.mod_dictionary:
            QMessageBox.warning(self, "警告", "请先加载原始语言文件")
            return
            
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择已有翻译文件", "", 
            "语言文件 (*.lang *.json);;所有文件 (*)", 
            options=options
        )
        
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                self.mod_dictionary.load_translated_file(content)
                
                # 更新UI
                self.translated_status.setText(f"翻译文件: {os.path.basename(file_name)}")
                
                # 计算已翻译条目数
                translated_count = sum(1 for element in self.mod_dictionary.text_dictionary.values() if element.is_translated)
                QMessageBox.information(self, "成功", f"已加载翻译文件，已翻译{translated_count}/{len(self.mod_dictionary.keys)}个条目")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件失败: {str(e)}")
    
    def start_translation(self):
        """开始翻译"""
        if not self.mod_dictionary:
            QMessageBox.warning(self, "警告", "请先加载原始语言文件")
            return
            
        # 清空列表
        self.entry_list.clear()
        
        # 填充列表
        for key in self.mod_dictionary.keys:
            element = self.mod_dictionary.text_dictionary[key]
            
            item = QListWidgetItem()
            item.setText(f"{element.original_text[:30]}...")
            item.setData(Qt.UserRole, key)
            
            # 设置状态
            if element.is_translated:
                try:
                    item.setIcon(QIcon(self.check_icon))
                except Exception as e:
                    print(f"加载check图标失败: {str(e)}")
            else:
                try:
                    item.setIcon(QIcon(self.empty_icon))
                except Exception as e:
                    print(f"加载empty图标失败: {str(e)}")
                
            self.entry_list.addItem(item)
            
        # 更新翻译进度
        self.update_translation_progress()
            
        # 选择第一项
        if self.entry_list.count() > 0:
            self.entry_list.setCurrentRow(0)
            
        # 启用编辑器选项卡
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)
        
    def update_translation_item(self, current, previous):
        """更新当前翻译项目"""
        if not current:
            return
            
        # 清除现有控件
        for i in reversed(range(self.translation_container_layout.count())): 
            widget = self.translation_container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        key = current.data(Qt.UserRole)
        self.current_key = key
        
        if key in self.mod_dictionary.text_dictionary:
            element = self.mod_dictionary.text_dictionary[key]
            translation_item = TranslationItem(element)
            translation_item.saved.connect(self.on_translation_saved)
            self.translation_container_layout.addWidget(translation_item)
            # 确保新创建的翻译项获得焦点
            QApplication.processEvents()  # 确保UI更新
            translation_item.translated_text.setFocus()
    
    def on_translation_saved(self, key, text):
        """处理翻译保存事件"""
        if key in self.mod_dictionary.text_dictionary:
            element = self.mod_dictionary.text_dictionary[key]
            element.set_translated_text(text)
            
            # 更新列表项图标
            for i in range(self.entry_list.count()):
                item = self.entry_list.item(i)
                if item.data(Qt.UserRole) == key:
                    if element.is_translated:
                        try:
                            item.setIcon(QIcon(self.check_icon))
                        except Exception as e:
                            print(f"加载check图标失败: {str(e)}")
                    else:
                        try:
                            item.setIcon(QIcon(self.empty_icon))
                        except Exception as e:
                            print(f"加载empty图标失败: {str(e)}")
                    break
            
            # 更新翻译进度
            self.update_translation_progress()
            
            # 可以选择自动移至下一项
            self.go_to_next()
    
    def update_translation_progress(self):
        """更新翻译进度"""
        if not self.mod_dictionary:
            return
            
        total = len(self.mod_dictionary.keys)
        translated = sum(1 for element in self.mod_dictionary.text_dictionary.values() if element.is_translated)
        
        self.progress_label.setText(f"翻译进度: {translated} / {total}")
        
    def go_to_previous(self):
        """跳转到前一个条目"""
        if self.entry_list.count() == 0:
            return
            
        current_row = self.entry_list.currentRow()
        if current_row > 0:
            self.entry_list.setCurrentRow(current_row - 1)
            
    def go_to_next(self):
        """跳转到下一个条目"""
        if self.entry_list.count() == 0:
            return
            
        current_row = self.entry_list.currentRow()
        if current_row < self.entry_list.count() - 1:
            self.entry_list.setCurrentRow(current_row + 1)
            
    def skip_to_next_untranslated(self):
        """跳转到下一个未翻译条目"""
        if self.entry_list.count() == 0:
            return
            
        current_row = self.entry_list.currentRow()
        
        # 从当前位置向后查找未翻译条目
        for i in range(current_row + 1, self.entry_list.count()):
            item = self.entry_list.item(i)
            key = item.data(Qt.UserRole)
            element = self.mod_dictionary.text_dictionary[key]
            
            if not element.is_translated:
                self.entry_list.setCurrentRow(i)
                return
                
        # 如果没找到，从头开始查找
        for i in range(0, current_row):
            item = self.entry_list.item(i)
            key = item.data(Qt.UserRole)
            element = self.mod_dictionary.text_dictionary[key]
            
            if not element.is_translated:
                self.entry_list.setCurrentRow(i)
                return
                
        QMessageBox.information(self, "信息", "所有条目已翻译完成")
            
    def clear_duplicate_translations(self):
        """清除与原文相同的译文"""
        if not self.mod_dictionary:
            return
            
        count = 0
        for key, element in self.mod_dictionary.text_dictionary.items():
            if element.is_translated and element.original_text == element.translated_text:
                element.reset()
                count += 1
                
                # 更新列表项图标
                for i in range(self.entry_list.count()):
                    item = self.entry_list.item(i)
                    if item.data(Qt.UserRole) == key:
                        try:
                            item.setIcon(QIcon(self.empty_icon))
                        except Exception as e:
                            print(f"加载empty图标失败: {str(e)}")
                        break
        
        # 更新翻译进度
        self.update_translation_progress()
        
        # 更新当前项目
        current = self.entry_list.currentItem()
        if current:
            self.update_translation_item(current, None)
            
        QMessageBox.information(self, "完成", f"已清除{count}个重复译文")
    
    def fill_empty_translations(self):
        """用原文填充空白译文"""
        if not self.mod_dictionary:
            return
            
        count = 0
        for key, element in self.mod_dictionary.text_dictionary.items():
            if not element.is_translated:
                element.set_translated_text(element.original_text)
                count += 1
                
                # 更新列表项图标
                for i in range(self.entry_list.count()):
                    item = self.entry_list.item(i)
                    if item.data(Qt.UserRole) == key:
                        try:
                            item.setIcon(QIcon(self.check_icon))
                        except Exception as e:
                            print(f"加载check图标失败: {str(e)}")
                        break
        
        # 更新翻译进度
        self.update_translation_progress()
        
        # 更新当前项目
        current = self.entry_list.currentItem()
        if current:
            self.update_translation_item(current, None)
            
        QMessageBox.information(self, "完成", f"已填充{count}个空白译文")
    
    def finish_translation(self):
        """完成翻译，进入导出页面"""
        if not self.mod_dictionary:
            return
            
        # 生成预览
        preview = self.mod_dictionary.export()
        self.preview_text.setPlainText(preview)
        
        # 启用导出选项卡
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)
        
    def save_translation_file(self):
        """保存翻译文件"""
        if not self.mod_dictionary:
            return
            
        options = QFileDialog.Options()
        file_format = ".json" if self.mod_dictionary.format == LangFormat.JSON else ".lang"
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存翻译文件", f"{self.mod_dictionary.mod_namespace}_zh_cn{file_format}", 
            f"语言文件 (*{file_format});;所有文件 (*)", 
            options=options
        )
        
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as file:
                    file.write(self.mod_dictionary.export())
                    
                QMessageBox.information(self, "成功", "翻译文件保存成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 加载QSS样式
    try:
        with open(os.path.join(os.path.dirname(__file__), "style.qss"), "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"样式加载失败: {e}")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 