import sqlite3
import os
import time

class Indexer:
    """
    封装了 SQLite + FTS5 索引和搜索操作的类。
    支持高效的变更同步和多目录管理。
    """
    def __init__(self, db_path="app_index.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row # 允许通过列名访问结果
        self.init_db()

    def init_db(self):
        """
        初始化数据库，创建所有需要的表和触发器。
        """
        cursor = self.conn.cursor()
        
        # 新增：用于管理所有索引根目录的表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS indexed_paths (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE
        );
        """)

        # 1. 创建文件元数据主表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            size INTEGER,
            mtime REAL
        );
        """)

        # 2. 创建 FTS5 虚拟表，用于全文搜索 'name' 字段
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            name,
            content='files',
            content_rowid='id'
        );
        """)

        # 3. 创建触发器，自动同步 files 表和 files_fts 表
        
        # 当在 files 表插入新数据后，同步到 FTS 表
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS files_after_insert AFTER INSERT ON files
        BEGIN
            INSERT INTO files_fts(rowid, name) VALUES (new.id, new.name);
        END;
        """)

        # 当在 files 表删除数据后，从 FTS 表同步删除
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS files_after_delete AFTER DELETE ON files
        BEGIN
            INSERT INTO files_fts(files_fts, rowid, name) VALUES ('delete', old.id, old.name);
        END;
        """)

        # 当在 files 表更新数据后，同步更新 FTS 表
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS files_after_update AFTER UPDATE ON files
        BEGIN
            INSERT INTO files_fts(files_fts, rowid, name) VALUES ('delete', old.id, old.name);
            INSERT INTO files_fts(rowid, name) VALUES (new.id, new.name);
        END;
        """)
        
        self.conn.commit()

    def sync_changes(self, scan_path, progress_callback=None):
        """
        使用集合操作高效地同步指定路径的文件变更。
        """
        if progress_callback: progress_callback("正在准备同步...")
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT path, mtime, id FROM files WHERE path LIKE ?", (f"{scan_path}%",))
        db_files = {row['path']: (row['mtime'], row['id']) for row in cursor.fetchall()}
        db_paths = set(db_files.keys())

        if progress_callback: progress_callback(f"数据库中存在 {len(db_paths)} 个相关条目。正在扫描文件系统...")

        fs_files = set()
        to_add_or_update = []
        
        for dirpath, dirnames, filenames in os.walk(scan_path):
            # 统一处理目录和文件
            for item_name in dirnames + filenames:
                item_path = os.path.join(dirpath, item_name)
                fs_files.add(item_path)
                try:
                    stat_info = os.stat(item_path)
                    mtime = stat_info.st_mtime
                    
                    if item_path not in db_paths: # 新增
                        is_dir = os.path.isdir(item_path)
                        to_add_or_update.append((
                            item_path, item_name, 'folder' if is_dir else 'file',
                            0 if is_dir else stat_info.st_size, mtime
                        ))
                    # 修改：mtime不一致（使用1秒容差）
                    elif abs(mtime - db_files[item_path][0]) > 1:
                        is_dir = os.path.isdir(item_path)
                        to_add_or_update.append((
                            db_files[item_path][1], # 传入id以执行REPLACE
                            item_path, item_name, 'folder' if is_dir else 'file',
                            0 if is_dir else stat_info.st_size, mtime
                        ))
                except (OSError, PermissionError):
                    continue
        
        deleted_paths = db_paths - fs_files
        
        if progress_callback: 
            progress_callback(f"扫描完毕。发现 {len(to_add_or_update)} 个新增/修改，{len(deleted_paths)} 个删除。")

        # 批量处理数据库
        if deleted_paths:
            placeholders = ','.join('?' for _ in deleted_paths)
            cursor.execute(f"DELETE FROM files WHERE path IN ({placeholders})", list(deleted_paths))

        if to_add_or_update:
            self.add_documents_batch(to_add_or_update)
            
        self.conn.commit()
        if progress_callback: progress_callback("同步完成！")
        
    def clear_index(self, path: str = None):
        """
        清空索引。如果提供了路径，则只清空该路径下的记录。
        否则，清空所有记录。
        """
        cursor = self.conn.cursor()
        if path:
            cursor.execute("DELETE FROM files WHERE path LIKE ?", (f"{path}%",))
        else:
            cursor.execute("DELETE FROM files;")
            cursor.execute("DELETE FROM indexed_paths;") # 同时清空管理表
        self.conn.commit()

    def add_document(self, path, name, doc_type, size, mtime):
        """
        向数据库中添加或替换单个文件记录。
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO files (path, name, type, size, mtime) VALUES (?, ?, ?, ?, ?)",
            (str(path), str(name), str(doc_type), int(size), float(mtime))
        )
        self.conn.commit()

    def add_documents_batch(self, documents):
        """
        使用事务批量插入或替换文件记录列表。
        """
        cursor = self.conn.cursor()
        
        # 根据元组长度判断是新增还是更新
        new_docs = [doc for doc in documents if len(doc) == 5]
        updated_docs = [doc for doc in documents if len(doc) == 6]

        try:
            if new_docs:
                cursor.executemany(
                    "INSERT INTO files (path, name, type, size, mtime) VALUES (?, ?, ?, ?, ?)",
                    new_docs
                )
            if updated_docs:
                cursor.executemany(
                    "UPDATE files SET path=?, name=?, type=?, size=?, mtime=? WHERE id=?",
                    [(d[1], d[2], d[3], d[4], d[5], d[0]) for d in updated_docs]
                )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"数据库批量操作时发生错误: {e}")
            self.conn.rollback()

    def delete_document(self, path):
        """从数据库中删除指定路径的文件记录"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE path = ?", (str(path),))
        self.conn.commit()

    def search(self, query_str, limit=None):
        """
        使用 FTS5 执行全文搜索。
        新增 limit 参数以限制返回结果的数量。
        """
        cursor = self.conn.cursor()
        
        processed_query = f'{query_str}*'
        
        sql = """
            SELECT f.path, f.name, f.type, f.size, f.mtime
            FROM files f
            JOIN files_fts ON f.id = files_fts.rowid
            WHERE files_fts.name MATCH ?
            ORDER BY rank
        """
        params = (processed_query,)

        if limit:
            sql += " LIMIT ?"
            params += (limit,)
        
        cursor.execute(sql, params)
        
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    # --- 多目录管理方法 ---
    
    def get_indexed_paths(self) -> list[str]:
        """获取所有已索引的根目录路径。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT path FROM indexed_paths ORDER BY path")
        return [row['path'] for row in cursor.fetchall()]

    def add_indexed_path(self, path: str):
        """添加一个新的根目录到索引列表。"""
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO indexed_paths (path) VALUES (?)", (path,))
        self.conn.commit()

    def remove_indexed_path(self, path: str):
        """从索引列表中移除一个根目录，并删除其所有相关文件数据。"""
        cursor = self.conn.cursor()
        # 1. 从管理表中删除
        cursor.execute("DELETE FROM indexed_paths WHERE path = ?", (path,))
        # 2. 删除该目录下所有文件的索引记录 (注意通配符)
        cursor.execute("DELETE FROM files WHERE path LIKE ?", (f"{path}%",))
        self.conn.commit()
        print(f"已从索引中移除目录 '{path}' 及其所有子条目。") 