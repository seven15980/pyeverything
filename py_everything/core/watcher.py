import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemMovedEvent
from .indexer import Indexer

class IndexingEventHandler(FileSystemEventHandler):
    """
    处理文件系统事件，并更新 SQLite 索引。
    为保证线程安全，每个事件都会创建独立的 Indexer 实例。
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path

    def _execute_action(self, action, *args, **kwargs):
        """通用执行器，确保 Indexer 的创建和关闭。"""
        indexer = None
        try:
            indexer = Indexer(self.db_path)
            action(indexer, *args, **kwargs)
        except Exception as e:
            print(f"执行数据库操作时出错: {e}")
        finally:
            if indexer:
                indexer.close()
    
    def on_created(self, event):
        """当文件或目录被创建时调用。"""
        print(f"检测到创建: {event.src_path}")
        self._execute_action(self._add_item_action, event.src_path)

    def on_deleted(self, event):
        """当文件或目录被删除时调用。"""
        print(f"检测到删除: {event.src_path}")
        def delete_action(indexer, path):
            indexer.delete_document(path)
            print(f"索引已删除: {path}")
        self._execute_action(delete_action, event.src_path)

    def on_modified(self, event):
        """当文件或目录被修改时调用。"""
        print(f"检测到修改: {event.src_path}")
        self._execute_action(self._add_item_action, event.src_path)

    def on_moved(self, event: FileSystemMovedEvent):
        """当文件或目录被移动或重命名时调用。"""
        print(f"检测到移动: 从 {event.src_path} 到 {event.dest_path}")
        def move_action(indexer, src_path, dest_path):
            indexer.delete_document(src_path)
            print(f"索引已删除 (移动源): {src_path}")
            self._add_item_action(indexer, dest_path)
        self._execute_action(move_action, event.src_path, event.dest_path)

    def _add_item_action(self, indexer: Indexer, path: str):
        """实际添加项目的操作，供 _execute_action 调用。"""
        try:
            time.sleep(0.1) 
            if not os.path.exists(path):
                return
            
            stat_info = os.stat(path)
            doc_type = 'folder' if os.path.isdir(path) else 'file'
            size = 0 if doc_type == 'folder' else stat_info.st_size
            
            indexer.add_document(
                path=path,
                name=os.path.basename(path),
                doc_type=doc_type,
                size=size,
                mtime=stat_info.st_mtime
            )
            print(f"索引已添加/更新: {path}")
        except Exception as e:
            print(f"添加/更新索引失败 '{path}': {e}")


def start_watching(path: str, db_path: str):
    """
    启动文件系统监控。
    
    :param path: 要监控的目录路径。
    :param db_path: 数据库文件路径。
    """
    event_handler = IndexingEventHandler(db_path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"已开始监控目录: {path}")
    return observer

# 注意： on_created 和 on_modified 的逻辑比较复杂。
# 一个健壮的实现需要处理：
# 1. 文件夹的创建（需要递归添加所有子内容）。
# 2. 短时间内的大量事件（防抖/节流）。
# 3. 获取文件元数据时的权限或锁定问题。
# 在当前版本中，我们为了保持简洁，仅实现了删除和移动的逻辑框架。 