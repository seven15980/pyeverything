import sys
import os

# 动态添加项目根目录到 sys.path, 兼容源码运行和 PyInstaller 打包
if getattr(sys, 'frozen', False):
    # 如果是 PyInstaller 打包的程序
    # sys._MEIPASS 是 PyInstaller 在运行时创建的临时文件夹
    # 我们假设 core 模块被打包到了这个临时文件夹的根目录
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
else:
    # 正常从源码运行
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 使用 insert(0, ...) 确保我们的路径有最高优先级
if base_path not in sys.path:
    sys.path.insert(0, base_path)

# 为了帮助 PyInstaller 的静态分析器找到模块，可以保留一个 'import core'
# 但更好的方式是在打包时通过参数告诉 PyInstaller
try:
    import core
except ImportError:
    pass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTableView, QHeaderView, 
    QFileDialog, QPushButton, QListWidget, QMessageBox, QSplitter, QStatusBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QSettings, pyqtSlot, QTimer, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QAction, QIcon
from core.indexer import Indexer
from core.watcher import start_watching
from core.scanner import scan_directory

class SearchWorker(QObject):
    """
    在后台线程中执行搜索任务的 Worker。
    """
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.indexer = None # 将在线程内创建

    @pyqtSlot()
    def clean_up(self):
        """关闭数据库连接"""
        if self.indexer:
            self.indexer.close()
            print("[DEBUG] SearchWorker's indexer closed.")

    def run_search(self, query_str: str):
        """执行搜索，并通过信号返回结果。"""
        try:
            if self.indexer is None:
                self.indexer = Indexer(self.db_path)
                print("[DEBUG] SearchWorker created its own indexer.")

            if not query_str.strip():
                self.results_ready.emit([])
                return
            results = self.indexer.search(query_str)
            self.results_ready.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ScanningWorker(QObject):
    """在后台线程中执行所有索引相关任务的 Worker。"""
    paths_updated = pyqtSignal(list) # 完成操作后，发送最新的路径列表
    status_update = pyqtSignal(str)

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.indexer = None # 将在线程内创建

    def _ensure_indexer(self):
        if not self.indexer:
            self.indexer = Indexer(self.db_path)

    @pyqtSlot()
    def clean_up(self):
        """关闭数据库连接"""
        if self.indexer:
            self.indexer.close()
            print("[DEBUG] ScanningWorker's indexer closed.")

    @pyqtSlot()
    def sync_all_paths(self):
        """同步所有已索引目录的变更。"""
        self._ensure_indexer()
        self.status_update.emit("正在同步所有目录...")
        paths = self.indexer.get_indexed_paths()
        for path in paths:
            self.status_update.emit(f"正在同步: {path}...")
            self.indexer.sync_changes(path, self.status_update.emit)
        self.status_update.emit("所有目录同步完成！")
        self.paths_updated.emit(self.indexer.get_indexed_paths())

    @pyqtSlot(str)
    def add_path(self, path):
        """添加并扫描一个新目录。"""
        self._ensure_indexer()
        self.status_update.emit(f"正在添加新目录: {path}...")
        self.indexer.add_indexed_path(path)
        # 执行全盘扫描
        documents = []
        for dp, dn, fn in os.walk(path):
            for it in dn + fn:
                fp = os.path.join(dp, it)
                try:
                    si = os.stat(fp)
                    documents.append((fp, it, 'folder' if os.path.isdir(fp) else 'file', si.st_size, si.st_mtime))
                except OSError: continue
        self.indexer.add_documents_batch(documents)
        self.status_update.emit(f"目录 '{path}' 添加成功！")
        self.paths_updated.emit(self.indexer.get_indexed_paths())

    @pyqtSlot(str)
    def remove_path(self, path):
        """移除一个索引目录。"""
        self._ensure_indexer()
        self.indexer.remove_indexed_path(path)
        self.status_update.emit(f"目录 '{path}' 已被移除。")
        self.paths_updated.emit(self.indexer.get_indexed_paths())

    @pyqtSlot()
    def get_initial_paths(self):
        self._ensure_indexer()
        self.paths_updated.emit(self.indexer.get_indexed_paths())

class FileSearchTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._results = []
        self._headers = ["名称", "路径", "类型", "大小 (Bytes)"]

    def rowCount(self, parent=None):
        return len(self._results)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        row_data = self._results[index.row()]
        column = index.column()

        if column == 0:
            return row_data.get('name')
        elif column == 1:
            return row_data.get('path')
        elif column == 2:
            return row_data.get('type')
        elif column == 3:
            return str(row_data.get('size'))
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None
    
    @pyqtSlot(list)
    def update_data(self, results):
        self.beginResetModel()
        self._results = results
        self.endResetModel()

class MainWindow(QMainWindow):
    # 后台任务触发信号
    trigger_search = pyqtSignal(str)
    trigger_sync_all = pyqtSignal()
    trigger_add_path = pyqtSignal(str)
    trigger_remove_path = pyqtSignal(str)
    trigger_get_paths = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyEverything - 多目录文件搜索引擎")
        self.setGeometry(100, 100, 1000, 700)

        self.settings = QSettings("MyCompany", "PyEverything")
        self.indexed_directory = ""
        self.watcher_observer = None
        self.db_path = "app_index.db"
        self.watchers = []

        self.setup_ui()
        self.setup_threads()
        
        # 设置搜索防抖计时器
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300) # 300毫秒延迟
        self.search_timer.timeout.connect(self.perform_search)
        
        self.load_settings()
        
        # 启动时加载路径并触发同步
        self.trigger_get_paths.emit()
        self.trigger_sync_all.emit()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板 (目录管理)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMinimumWidth(200)
        left_panel.setMaximumWidth(400)
        
        self.path_list_widget = QListWidget()
        
        path_button_layout = QHBoxLayout()
        add_button = QPushButton("添加")
        remove_button = QPushButton("删除")
        add_button.clicked.connect(self.add_directory)
        remove_button.clicked.connect(self.remove_directory)
        path_button_layout.addWidget(add_button)
        path_button_layout.addWidget(remove_button)

        left_layout.addWidget(self.path_list_widget)
        left_layout.addLayout(path_button_layout)
        
        # 右侧主面板 (搜索和结果)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("在此搜索所有已索引目录...")
        self.search_box.textChanged.connect(self.debounce_search)
        
        self.results_table = QTableView()
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.results_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_results_context_menu)
        self.results_table.doubleClicked.connect(self.open_selected_item)

        right_layout.addWidget(self.search_box)
        right_layout.addWidget(self.results_table)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 750])

        main_layout.addWidget(splitter)
        
        self.setStatusBar(QStatusBar())

    def setup_threads(self):
        # 搜索线程
        self.search_thread = QThread()
        self.search_worker = SearchWorker(self.db_path)
        self.search_worker.moveToThread(self.search_thread)
        self.trigger_search.connect(self.search_worker.run_search)

        # 创建模型并设置给视图
        self.model = FileSearchTableModel()
        self.results_table.setModel(self.model)

        self.search_worker.results_ready.connect(self.model.update_data)
        self.search_worker.results_ready.connect(self.on_search_complete)
        self.search_worker.error_occurred.connect(lambda e: self.statusBar().showMessage(f"搜索错误: {e}"))
        self.search_thread.finished.connect(self.search_worker.clean_up)
        self.search_thread.start()

        # 索引/扫描线程
        self.scan_thread = QThread()
        self.scan_worker = ScanningWorker(self.db_path)
        self.scan_worker.moveToThread(self.scan_thread)
        self.trigger_sync_all.connect(self.scan_worker.sync_all_paths)
        self.trigger_add_path.connect(self.scan_worker.add_path)
        self.trigger_remove_path.connect(self.scan_worker.remove_path)
        self.trigger_get_paths.connect(self.scan_worker.get_initial_paths)
        self.scan_worker.paths_updated.connect(self.update_path_list)
        self.scan_worker.status_update.connect(self.statusBar().showMessage)
        self.scan_thread.finished.connect(self.scan_worker.clean_up)
        self.scan_thread.start()

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "选择要索引的文件夹")
        if path:
            print(f"[DEBUG] Directory selected: {path}")
            self.search_box.setDisabled(True)
            self.results_table.setRowCount(0)
            print("[DEBUG] Emitting scan_triggered signal for full scan...")
            self.scan_triggered.emit(path, False) # False表示全盘扫描
    
    def on_scan_finished(self, path: str):
        print(f"[DEBUG] Scan/Sync finished for path: {path}")
        self.indexed_directory = path
        self.settings.setValue("indexed_directory", path)
        self.search_box.setDisabled(False)
        self.search_box.setPlaceholderText(f"正在同步 {path}...")
        
        # 停止旧的监控并启动新的
        if self.watcher_observer:
            self.watcher_observer.stop()
            self.watcher_observer.join()
        
        try:
            self.watcher_observer = start_watching(path, self.db_path)
            self.statusBar().showMessage(f"已完成对 {path} 的索引，并启动实时监控。", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"启动文件监控失败: {e}")

    def load_settings(self):
        path = self.settings.value("indexed_directory")
        if path and os.path.exists(path):
            self.indexed_directory = path
            self.statusBar().showMessage(f"已加载上次索引的目录: {path}。")
            self.search_box.setPlaceholderText(f"正在同步 {path}...")
            # 触发后台同步
            
            # 启动监控的逻辑移到 on_scan_finished 中
        else:
            self.statusBar().showMessage("欢迎使用！请从'文件'菜单选择一个目录开始索引。")

    def debounce_search(self):
        """
        重置搜索计时器以实现防抖。
        每次按键都会调用此方法，并重新启动一个300毫秒的计时器。
        """
        self.search_timer.start()

    @pyqtSlot()
    def perform_search(self):
        """
        在计时器超时后实际触发搜索。
        """
        self.trigger_search.emit(self.search_box.text())

    @pyqtSlot(list)
    def on_search_complete(self, results):
        """当搜索完成时，在状态栏更新结果数量。"""
        self.statusBar().showMessage(f"找到了 {len(results)} 个结果")

    def on_search_error(self, error_message: str):
        """当搜索发生错误时，更新状态栏。"""
        self.statusBar().showMessage(f"搜索出错: {error_message}")

    def closeEvent(self, event):
        """关闭窗口时，确保后台线程被正确清理。"""
        # 停止搜索线程
        self.search_thread.quit()
        self.search_thread.wait()
        
        # 停止文件监控线程
        if self.watcher_observer:
            self.watcher_observer.stop()
            self.watcher_observer.join()
            print("文件监控已停止。")
        
        # 关闭数据库连接
        # self.indexer.close() # 已不需要，由各个 worker 自行管理
        # print("数据库连接已关闭。")

        super().closeEvent(event)

    def add_directory(self):
        path = QFileDialog.getExistingDirectory(self, "选择要索引的文件夹")
        if path:
            self.trigger_add_path.emit(path)

    def remove_directory(self):
        selected_item = self.path_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "未选择", "请先在列表中选择一个要删除的目录。")
            return
        path = selected_item.text()
        reply = QMessageBox.question(self, "确认删除", 
            f"确定要从索引中移除 '{path}' 吗？\n这将删除所有与该目录相关的索引数据。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.trigger_remove_path.emit(path)

    @pyqtSlot(list)
    def update_path_list(self, paths):
        self.path_list_widget.clear()
        self.path_list_widget.addItems(paths)
        self.restart_watchers(paths)

    def restart_watchers(self, paths):
        for watcher in self.watchers:
            watcher.stop()
            watcher.join()
        self.watchers.clear()
        
        for path in paths:
            try:
                watcher = start_watching(path, self.db_path)
                self.watchers.append(watcher)
            except Exception as e:
                self.statusBar().showMessage(f"启动对 '{path}' 的监控失败: {e}")
        print(f"文件监控已更新，正在监控 {len(self.watchers)} 个目录。")

    def show_results_context_menu(self, pos):
        """为结果表格创建并显示右键上下文菜单。"""
        index = self.results_table.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu()
        open_action = menu.addAction("打开")
        open_location_action = menu.addAction("打开所在位置")

        # 在鼠标位置执行菜单，并获取用户选择的动作
        action = menu.exec(self.results_table.viewport().mapToGlobal(pos))

        if action == open_action:
            self.open_selected_item(index)
        elif action == open_location_action:
            self.open_item_location(index)

    @pyqtSlot(QModelIndex)
    def open_selected_item(self, index):
        """打开双击或在菜单中选择的条目（文件或目录）。"""
        if not index.isValid():
            # 如果是通过信号槽直接调用（非右键菜单），可能需要获取当前选择
            index = self.results_table.currentIndex()
            if not index.isValid():
                return

        # 从模型中获取路径（在第2列，索引为1）
        path_index = self.results_table.model().index(index.row(), 1)
        path = self.results_table.model().data(path_index)

        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                self.statusBar().showMessage(f"无法打开 '{path}': {e}", 5000)
        else:
            self.statusBar().showMessage(f"路径不存在: '{path}'", 5000)

    def open_item_location(self, index):
        """打开选中文件所在的文件夹。"""
        if not index.isValid():
            return
        
        # 从模型中获取路径（在第2列，索引为1）
        path_index = self.results_table.model().index(index.row(), 1)
        path = self.results_table.model().data(path_index)

        if path and os.path.exists(path):
            # 获取文件所在的目录
            directory = os.path.dirname(path)
            try:
                os.startfile(directory)
            except Exception as e:
                self.statusBar().showMessage(f"无法打开目录 '{directory}': {e}", 5000)
        else:
            self.statusBar().showMessage(f"路径不存在: '{path}'", 5000)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec()) 