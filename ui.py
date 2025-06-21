import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QFileDialog,
    QTabWidget,
    QComboBox,
    QMessageBox,
    QSplitter,
    QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt5.QtGui import QIcon
from core import TextElement, ModDictionary, LangFormat  # 从核心模块导入类

class TranslationItem(QWidget):
    """
    单个翻译项的UI组件，用于显示原文和编辑译文
    
    属性:
        saved: 保存信号，在用户保存翻译时触发
    """
    
    saved = pyqtSignal(str, str)  # 信号参数: (key, translated_text)

    def __init__(self, text_element, parent=None):
        """
        初始化翻译项组件
        
        参数:
            text_element: TextElement对象，包含翻译数据
            parent: 父组件
        """
        super().__init__(parent)
        self.text_element = text_element
        self.init_ui()

    def init_ui(self):
        """设置UI布局和控件"""
        layout = QVBoxLayout(self)

        # 原文显示区域
        layout.addWidget(QLabel("原文:"))
        self.original_text = QTextEdit()
        self.original_text.setPlainText(self.text_element.original_text)
        self.original_text.setReadOnly(True)  # 原文不可编辑
        layout.addWidget(self.original_text)

        # 译文编辑区域
        layout.addWidget(QLabel("译文:"))
        self.translated_text = QTextEdit()
        self.translated_text.setPlainText(self.text_element.translated_text)
        self.translated_text.installEventFilter(self)  # 安装事件过滤器处理快捷键
        layout.addWidget(self.translated_text)

        # 操作按钮
        buttons_layout = QHBoxLayout()
        
        # 重置按钮
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset)
        buttons_layout.addWidget(self.reset_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)

        # 设置初始焦点到译文输入框
        self.translated_text.setFocus()

    def eventFilter(self, obj, event):
        """
        事件过滤器，处理键盘快捷键
        
        参数:
            obj: 事件来源对象
            event: 事件对象
            
        返回:
            bool: True表示事件已处理，False表示未处理
        """
        # 处理译文输入框的按键事件
        if obj == self.translated_text and event.type() == QEvent.KeyPress:
            # Enter键保存并跳转下一项
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
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
        """重置译文内容"""
        self.translated_text.setPlainText("")
        self.text_element.reset()
        self.translated_text.setFocus()  # 重置后保持焦点在输入框

    def save(self):
        """保存译文并发射信号"""
        text = self.translated_text.toPlainText()
        self.text_element.set_translated_text(text)
        self.saved.emit(self.text_element.key, text)  # 发射保存信号


class MainWindow(QMainWindow):
    """主窗口类，包含翻译工具的所有UI组件"""
    
    def __init__(self):
        super().__init__()
        self.mod_dictionary = None  # 模组翻译字典
        self.current_key = None     # 当前选中的翻译项键
        
        # 图标路径处理
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(base_dir, "icons")
        self.check_icon = os.path.join(self.icon_path, "check.png")  # 已翻译图标
        self.empty_icon = os.path.join(self.icon_path, "empty.png")  # 未翻译图标
        
        # 验证图标文件是否存在
        if not all(os.path.exists(icon) for icon in [self.check_icon, self.empty_icon]):
            print("警告: 图标文件缺失，请检查icons目录")
        
        self.init_ui()  # 初始化UI

    def init_ui(self):
        """初始化主窗口UI"""
        self.setWindowTitle("PythonTranslator - Minecraft模组翻译工具 by友野YouyEr")
        self.setMinimumSize(1200, 820)  # 设置最小窗口尺寸
        
        # 主窗口布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        self.open_tab = QWidget()   # 文件打开选项卡
        self.editor_tab = QWidget() # 翻译编辑选项卡
        self.export_tab = QWidget() # 导出选项卡
        
        # 添加选项卡
        self.tabs.addTab(self.open_tab, "打开")
        self.tabs.addTab(self.editor_tab, "翻译")
        self.tabs.addTab(self.export_tab, "导出")
        
        main_layout.addWidget(self.tabs)
        
        # 设置各选项卡内容
        self.setup_open_tab()
        self.setup_editor_tab()
        self.setup_export_tab()
        
        # 初始禁用翻译和导出选项卡
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

    def setup_open_tab(self):
        """设置'打开'选项卡内容"""
        layout = QVBoxLayout(self.open_tab)
        
        # 命名空间输入
        namespace_layout = QHBoxLayout()
        namespace_layout.addWidget(QLabel("模组命名空间:"))
        self.namespace_edit = QLineEdit()
        self.namespace_edit.setPlaceholderText("输入模组命名空间，例如：minecraft")
        namespace_layout.addWidget(self.namespace_edit)
        layout.addLayout(namespace_layout)
        
        # 文件操作按钮
        open_layout = QVBoxLayout()
        
        # 打开原始文件按钮
        self.open_original_btn = QPushButton("打开原始语言文件")
        self.open_original_btn.clicked.connect(self.open_original_file)
        open_layout.addWidget(self.open_original_btn)
        
        # 打开翻译文件按钮
        self.open_translated_btn = QPushButton("打开已翻译语言文件(可选)")
        self.open_translated_btn.clicked.connect(self.open_translated_file)
        self.open_translated_btn.setEnabled(False)  # 初始禁用
        open_layout.addWidget(self.open_translated_btn)
        
        layout.addLayout(open_layout)
        
        # 文件状态显示
        status_layout = QVBoxLayout()
        self.original_status = QLabel("原始文件: 未加载")
        status_layout.addWidget(self.original_status)
        self.translated_status = QLabel("翻译文件: 未加载")
        status_layout.addWidget(self.translated_status)
        layout.addLayout(status_layout)
        
        # 开始翻译按钮
        self.start_btn = QPushButton("开始翻译")
        self.start_btn.clicked.connect(self.start_translation)
        self.start_btn.setEnabled(False)  # 初始禁用
        layout.addWidget(self.start_btn)

    def setup_editor_tab(self):
        """设置'翻译'选项卡内容"""
        layout = QHBoxLayout(self.editor_tab)
        
        # 创建水平分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧条目列表
        self.entry_list = QListWidget()
        self.entry_list.currentItemChanged.connect(self.update_translation_item)
        splitter.addWidget(self.entry_list)
        
        # 右侧翻译面板
        self.translation_panel = QWidget()
        translation_layout = QVBoxLayout(self.translation_panel)
        
        # 翻译进度显示
        self.progress_label = QLabel("翻译进度: 0 / 0")
        translation_layout.addWidget(self.progress_label)
        
        # 翻译编辑容器
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
        
        # 设置分割器比例
        splitter.setSizes([430, 780])  # 左侧列表宽度430像素

    def setup_export_tab(self):
        """设置'导出'选项卡内容"""
        layout = QVBoxLayout(self.export_tab)
        
        # 预览区域
        layout.addWidget(QLabel("翻译结果预览:"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)  # 预览只读
        layout.addWidget(self.preview_text)
        
        # 操作按钮
        export_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存翻译文件")
        self.save_btn.clicked.connect(self.save_translation_file)
        export_layout.addWidget(self.save_btn)
        
        self.back_btn = QPushButton("返回翻译")
        self.back_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        export_layout.addWidget(self.back_btn)
        
        layout.addLayout(export_layout)

    def open_original_file(self):
        """打开原始语言文件并加载内容"""
        # 获取文件路径
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择原始语言文件",
            "",
            "语言文件 (*.lang *.json);;所有文件 (*)",
            options=options,
        )

        if not file_name:
            return  # 用户取消选择

        try:
            # 读取文件内容
            with open(file_name, "r", encoding="utf-8") as file:
                content = file.read()
            
            # 获取命名空间
            namespace = self.namespace_edit.text().strip() or "mod"  # 默认为"mod"
            
            # 创建并加载模组字典
            self.mod_dictionary = ModDictionary(namespace)
            self.mod_dictionary.load_original_file(content)
            
            # 更新UI状态
            self.original_status.setText(
                f"原始文件: {os.path.basename(file_name)} ({self.mod_dictionary.format.value})"
            )
            self.open_translated_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            
            # 显示成功消息
            QMessageBox.information(
                self,
                "成功",
                f"已加载原始文件，包含{len(self.mod_dictionary.keys)}个翻译条目",
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件失败: {str(e)}")

    def open_translated_file(self):
        """打开已有的翻译文件并加载内容"""
        if not self.mod_dictionary:
            QMessageBox.warning(self, "警告", "请先加载原始语言文件")
            return

        # 获取文件路径
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择已有翻译文件",
            "",
            "语言文件 (*.lang *.json);;所有文件 (*)",
            options=options,
        )

        if not file_name:
            return  # 用户取消选择

        try:
            # 读取文件内容
            with open(file_name, "r", encoding="utf-8") as file:
                content = file.read()
            
            # 加载翻译文件
            self.mod_dictionary.load_translated_file(content)
            
            # 更新UI状态
            self.translated_status.setText(f"翻译文件: {os.path.basename(file_name)}")
            
            # 计算并显示翻译进度
            translated_count = sum(
                1 for element in self.mod_dictionary.text_dictionary.values()
                if element.is_translated
            )
            QMessageBox.information(
                self,
                "成功",
                f"已加载翻译文件，已翻译{translated_count}/{len(self.mod_dictionary.keys)}个条目",
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件失败: {str(e)}")

    def start_translation(self):
        """开始翻译，初始化翻译界面"""
        if not self.mod_dictionary:
            QMessageBox.warning(self, "警告", "请先加载原始语言文件")
            return

        # 清空条目列表
        self.entry_list.clear()
        
        # 填充条目列表
        for key in self.mod_dictionary.keys:
            element = self.mod_dictionary.text_dictionary[key]
            
            # 创建列表项
            item = QListWidgetItem()
            item.setText(f"{element.original_text[:30]}...")  # 显示前30个字符
            item.setData(Qt.UserRole, key)  # 存储键值
            
            # 设置状态图标
            try:
                if element.is_translated:
                    item.setIcon(QIcon(self.check_icon))  # 已翻译图标
                else:
                    item.setIcon(QIcon(self.empty_icon))  # 未翻译图标
            except:
                pass  # 图标加载失败时忽略
            
            self.entry_list.addItem(item)
        
        # 更新翻译进度
        self.update_translation_progress()
        
        # 默认选择第一项
        if self.entry_list.count() > 0:
            self.entry_list.setCurrentRow(0)
        
        # 启用翻译选项卡并切换
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

    def update_translation_item(self, current, previous):
        """
        更新当前翻译项目显示
        
        参数:
            current: 当前选中的列表项
            previous: 之前选中的列表项
        """
        if not current:
            return  # 没有选中项时返回
        
        # 清除现有翻译组件
        for i in reversed(range(self.translation_container_layout.count())):
            widget = self.translation_container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 获取当前翻译项数据
        key = current.data(Qt.UserRole)
        self.current_key = key
        
        if key in self.mod_dictionary.text_dictionary:
            element = self.mod_dictionary.text_dictionary[key]
            
            # 创建新翻译组件
            translation_item = TranslationItem(element)
            translation_item.saved.connect(self.on_translation_saved)  # 连接保存信号
            self.translation_container_layout.addWidget(translation_item)
            
            # 确保新组件获得焦点
            QApplication.processEvents()
            translation_item.translated_text.setFocus()

    def on_translation_saved(self, key, text):
        """
        处理翻译保存事件
        
        参数:
            key: 翻译项的键
            text: 翻译文本
        """
        if not key or not self.mod_dictionary:
            return
        
        # 更新翻译项状态
        element = self.mod_dictionary.text_dictionary[key]
        element.set_translated_text(text)
        
        # 更新列表项图标
        for i in range(self.entry_list.count()):
            item = self.entry_list.item(i)
            if item.data(Qt.UserRole) == key:
                try:
                    if element.is_translated:
                        item.setIcon(QIcon(self.check_icon))  # 已翻译图标
                    else:
                        item.setIcon(QIcon(self.empty_icon))  # 未翻译图标
                except:
                    pass  # 图标加载失败时忽略
                break
        
        # 更新进度并跳转下一项
        self.update_translation_progress()
        self.go_to_next()

    def update_translation_progress(self):
        """更新翻译进度显示"""
        if not self.mod_dictionary:
            return
        
        total = len(self.mod_dictionary.keys)
        translated = sum(
            1 for element in self.mod_dictionary.text_dictionary.values()
            if element.is_translated
        )
        
        self.progress_label.setText(f"翻译进度: {translated} / {total}")

    def go_to_previous(self):
        """跳转到前一个翻译条目"""
        if self.entry_list.count() == 0:
            return
        
        current_row = self.entry_list.currentRow()
        if current_row > 0:
            self.entry_list.setCurrentRow(current_row - 1)

    def go_to_next(self):
        """跳转到下一个翻译条目"""
        if self.entry_list.count() == 0:
            return
        
        current_row = self.entry_list.currentRow()
        if current_row < self.entry_list.count() - 1:
            self.entry_list.setCurrentRow(current_row + 1)

    def skip_to_next_untranslated(self):
        """跳转到下一个未翻译条目"""
        if not self.mod_dictionary or self.entry_list.count() == 0:
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
        
        # 所有条目都已翻译
        QMessageBox.information(self, "信息", "所有条目已翻译完成")

    def clear_duplicate_translations(self):
        """清除与原文相同的译文"""
        if not self.mod_dictionary:
            return
        
        count = 0
        for key, element in self.mod_dictionary.text_dictionary.items():
            if element.is_translated and element.original_text == element.translated_text:
                element.reset()  # 重置翻译
                count += 1
                
                # 更新列表项图标
                for i in range(self.entry_list.count()):
                    item = self.entry_list.item(i)
                    if item.data(Qt.UserRole) == key:
                        try:
                            item.setIcon(QIcon(self.empty_icon))  # 设置为未翻译图标
                        except:
                            pass
                        break
        
        # 更新UI
        self.update_translation_progress()
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
                            item.setIcon(QIcon(self.check_icon))  # 设置为已翻译图标
                        except:
                            pass
                        break
        
        # 更新UI
        self.update_translation_progress()
        current = self.entry_list.currentItem()
        if current:
            self.update_translation_item(current, None)
        
        QMessageBox.information(self, "完成", f"已填充{count}个空白译文")

    def finish_translation(self):
        """完成翻译，进入导出页面"""
        if not self.mod_dictionary:
            return
        
        # 生成预览内容
        preview = self.mod_dictionary.export()
        self.preview_text.setPlainText(preview)
        
        # 启用导出选项卡并切换
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

    def save_translation_file(self):
        """保存翻译文件"""
        if not self.mod_dictionary:
            return
        
        # 获取保存路径
        options = QFileDialog.Options()
        file_format = ".json" if self.mod_dictionary.format == LangFormat.JSON else ".lang"
        default_name = f"{self.mod_dictionary.mod_namespace}_zh_cn{file_format}"
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "保存翻译文件",
            default_name,
            f"语言文件 (*{file_format});;所有文件 (*)",
            options=options,
        )

        if not file_name:
            return  # 用户取消保存

        try:
            # 导出并保存文件
            content = self.mod_dictionary.export()
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(content)
            
            QMessageBox.information(self, "成功", "翻译文件保存成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")