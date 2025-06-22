import os
import time
from .indexer import Indexer

def scan_directory(root_path, indexer: Indexer, progress_callback=None):
    """
    遍历指定目录，并将文件和文件夹信息批量添加到数据库中。
    
    :param root_path: 要扫描的根目录。
    :param indexer: Indexer 实例。
    :param progress_callback: 用于报告进度的回调函数。
    """
    if not os.path.isdir(root_path):
        if progress_callback:
            progress_callback(f"错误: 路径 '{root_path}' 不是一个有效的目录，或无权访问。")
        return

    if progress_callback:
        progress_callback(f"开始扫描: {root_path}")
    
    documents_to_add = []
    count = 0
    start_time = time.time()

    for dirpath, dirnames, filenames in os.walk(root_path):
        # 准备索引当前目录
        try:
            stat_info = os.stat(dirpath)
            documents_to_add.append(
                (dirpath, os.path.basename(dirpath), 'folder', 0, stat_info.st_mtime)
            )
            count += 1
            if count % 5000 == 0 and progress_callback:
                progress_callback(f"已发现 {count} 个条目...")
        except Exception as e:
            if progress_callback:
                progress_callback(f"错误：无法读取目录 {dirpath} 信息: {e}")

        # 准备索引子文件
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                stat_info = os.stat(file_path)
                documents_to_add.append(
                    (file_path, filename, 'file', stat_info.st_size, stat_info.st_mtime)
                )
                count += 1
                if count % 5000 == 0 and progress_callback:
                    progress_callback(f"已发现 {count} 个条目...")
            except Exception as e:
                if progress_callback:
                    progress_callback(f"错误：无法读取文件 {file_path} 信息: {e}")

    if progress_callback:
        progress_callback(f"发现 {count} 个条目，正在批量写入数据库...")
        
    indexer.add_documents_batch(documents_to_add)
    end_time = time.time()
    
    if progress_callback:
        progress_callback(f"扫描完成！索引了 {count} 个条目，耗时 {end_time - start_time:.2f} 秒。") 