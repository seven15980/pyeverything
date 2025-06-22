import sys
import os

# 将 'core' 目录的父目录（即 py_everything）添加到 Python 路径中
# 这样我们就可以使用 from core.indexer import Indexer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.indexer import Indexer
from core.scanner import scan_directory

def main():
    """
    测试后端索引和搜索功能的主函数。
    """
    # 1. 初始化索引器
    # 索引将被存储在 'app_index.db' 文件中
    db_path = "app_index.db"
    indexer = Indexer(db_path=db_path)
    print(f"数据库路径: {os.path.abspath(db_path)}")

    try:
        # 2. 定义要扫描的目录
        target_directory = ".." 
        print("="*50)
        print(f"准备清空旧索引并扫描目录: {os.path.abspath(target_directory)}")
        print("="*50)

        # 3. 执行扫描和索引
        indexer.clear_index() # 开始前清空
        scan_directory(target_directory, indexer, progress_callback=print)
        
        print("\n" + "="*50)
        print("索引建立完毕. 现在开始测试搜索功能...")
        print("="*50)

        # 4. 执行搜索
        while True:
            try:
                query_str = input("请输入搜索词 (输入 'q' 或 'quit' 退出): ")
                if query_str.lower() in ['q', 'quit']:
                    break
                
                if not query_str.strip():
                    print("请输入有效的搜索词。")
                    continue

                print(f"\n正在搜索: '{query_str}'")
                results = indexer.search(query_str)
                
                if results:
                    print(f"找到了 {len(results)} 个结果:")
                    for r in results:
                        # 结果现在是字典
                        print(f"  - 名称: {r.get('name')}")
                        print(f"    路径: {r.get('path')}")
                        print(f"    类型: {r.get('type')}, 大小: {r.get('size')} bytes, 修改时间: {r.get('mtime')}")
                else:
                    print("未找到相关结果。")
                print("-" * 20)

            except KeyboardInterrupt:
                print("\n程序退出。")
                break
    finally:
        indexer.close()
        print("数据库连接已关闭。")

if __name__ == "__main__":
    main() 