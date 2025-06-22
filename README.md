# PyEverything

PyEverything 是一个用 Python 构建的桌面文件快速搜索工具，灵感来自于著名的 Windows 软件 "Everything"。它通过预先建立文件索引，实现毫秒级的搜索响应，并能实时监控文件系统的变化。

## ✨ 功能特性

- **极速搜索**: 对所有索引过的文件和文件夹进行即时搜索。
- **多目录索引**: 支持同时添加、管理和搜索多个不同的磁盘目录。
- **实时更新**: 自动监控文件系统的增、删、改、移动操作，并实时更新索引，无需手动刷新。
- **图形用户界面**: 基于 PyQt6 构建，提供一个简洁直观的界面，包括搜索栏、结果列表和状态显示。
- **便捷操作**: 支持在搜索结果中双击打开文件，或右键打开文件所在位置。
- **后台处理**: 所有的索引和搜索任务都在后台线程中执行，确保用户界面始终流畅不卡顿。

## 📸 软件截图


![Image](https://github.com/user-attachments/assets/46f0c67f-e93c-4738-91ce-112c4c20cfd6)


## 🛠️ 技术栈

- **图形界面 (GUI)**: `PyQt6`
- **索引与搜索**: `SQLite (FTS5)`
- **文件系统监控**: `watchdog`
- **打包**: `pyinstaller`

## 🚀 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/seven15980/pyeverything.git
cd pyeverything
```

### 2. 安装依赖

建议在 Python 虚拟环境中使用 `pip` 安装所有必需的库：

```bash
# 创建虚拟环境 (可选但推荐)
python -m venv venv
# 激活虚拟环境 (Windows)
venv\Scripts\activate
# (macOS/Linux)
# source venv/bin/activate

# 安装依赖
pip install -r py_everything/requirements.txt
```

### 3. 运行程序

直接运行主窗口程序即可启动应用：

```bash
python py_everything/ui/main_window.py
```

首次运行时，你需要通过左侧面板的 "添加" 按钮，选择一个或多个你希望索引的文件夹。添加后，程序会自动在后台开始扫描和建立索引。

## 🏗️ 项目结构

```
py_everything/
├── core/
│   ├── indexer.py      # 封装了 Whoosh 的索引和搜索核心逻辑
│   ├── scanner.py      # 负责遍历文件目录
│   └── watcher.py      # 使用 watchdog 进行文件系统实时监控
├── ui/
│   └── main_window.py  # PyQt6 主窗口和所有界面逻辑
├── requirements.txt    # 项目依赖
└── test_backend.py     # 后端功能的测试脚本
```

## 📦 打包为可执行文件

项目包含了 `pyinstaller` 依赖，你可以使用它将整个应用打包成一个独立的可执行文件（`.exe`）。一个基本的打包命令如下：

```bash
# 确保你在 pyeverything 目录下
pyinstaller --name PyEverything --windowed --onefile py_everything/ui/main_window.py
```
*注意：打包过程可能需要根据实际情况调整参数，例如添加数据文件或隐藏的 import。*

## 🤝 如何贡献

欢迎任何形式的贡献！如果你有好的想法或发现了 Bug，请随时提交 Pull Request 或创建 Issue。

1.  Fork 本项目
2.  创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3.  提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  打开一个 Pull Request

---

希望你喜欢 PyEverything！

---

# PyEverything (English)

PyEverything is a desktop file search tool built with Python, inspired by the famous Windows software "Everything". It achieves millisecond-level search responses by pre-building a file index and can monitor file system changes in real-time.

## ✨ Features

- **Blazing-fast Search**: Instantly search all indexed files and folders.
- **Multi-directory Indexing**: Supports adding, managing, and searching multiple different disk directories simultaneously.
- **Real-time Updates**: Automatically monitors file system for creations, deletions, modifications, and moves, updating the index in real-time without manual refreshes.
- **Graphical User Interface**: Built with PyQt6, providing a clean and intuitive interface with a search bar, results list, and status display.
- **Convenient Operations**: Supports opening files by double-clicking in the search results or opening the file's location with a right-click.
- **Background Processing**: All indexing and search tasks are executed in background threads to ensure the user interface remains smooth and responsive.

## 📸 Screenshot



![Image](https://github.com/user-attachments/assets/46f0c67f-e93c-4738-91ce-112c4c20cfd6)

## 🛠️ Tech Stack

- **GUI**: `PyQt6`
- **Indexing & Search**: `SQLite (FTS5)`
- **File System Monitoring**: `watchdog`
- **Packaging**: `pyinstaller`

## 🚀 Installation and Usage

### 1. Clone the project

```bash
git clone https://github.com/seven15980/pyeverything.git
cd pyeverything
```

### 2. Install dependencies

It is recommended to use `pip` in a Python virtual environment to install all required libraries:

```bash
# Create a virtual environment (optional but recommended)
python -m venv venv
# Activate the virtual environment (Windows)
venv\Scripts\activate
# (macOS/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r py_everything/requirements.txt
```

### 3. Run the application

Run the main window program directly to start the application:

```bash
python py_everything/ui/main_window.py
```

On the first run, you will need to use the "Add" button on the left panel to select one or more folders you wish to index. After adding, the program will automatically start scanning and building the index in the background.

## 🏗️ Project Structure

```
py_everything/
├── core/
│   ├── indexer.py      # Core logic for indexing and searching with Whoosh
│   ├── scanner.py      # Responsible for traversing file directories
│   └── watcher.py      # Real-time file system monitoring using watchdog
├── ui/
│   └── main_window.py  # PyQt6 main window and all UI logic
├── requirements.txt    # Project dependencies
└── test_backend.py     # Test scripts for backend functionality
```

## 📦 Packaging as an Executable

The project includes the `pyinstaller` dependency, which you can use to package the entire application into a standalone executable (`.exe`). A basic packaging command is as follows:

```bash
# Make sure you are in the pyeverything directory
pyinstaller --name PyEverything --windowed --onefile py_everything/ui/main_window.py
```
*Note: The packaging process may require adjusting parameters based on your specific needs, such as adding data files or hidden imports.*

## 🤝 How to Contribute

Contributions of any kind are welcome! If you have great ideas or find a bug, please feel free to submit a Pull Request or create an Issue.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

Hope you enjoy PyEverything! 