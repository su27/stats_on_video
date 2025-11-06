# 视频数据叠加工具

将运动数据（FIT文件）叠加到视频上的Web工具。

## 功能特性

- 从FIT文件读取运动数据（心率、配速、步频、距离、功率）
- 将数据叠加到视频上
- Web界面操作，无需命令行
- 实时显示处理进度

## 安装

使用 uv 管理依赖：

```bash
# 安装依赖
uv sync

# 或者使用 pip
uv pip install -e .
```

## 使用方法

### 启动Web服务

```bash
# 方式1: 使用uv运行
uv run python app.py

# 方式2: 使用已安装的命令
uv run make-video-server

# 方式3: 激活虚拟环境后运行
source .venv/bin/activate
python app.py
```

### 使用Web界面

1. 打开浏览器访问 `http://localhost:5000`
2. 填写以下信息：
   - **视频文件路径**: 本地视频文件的完整路径（如 `/home/user/video.mp4`）
   - **FIT文件路径**: 本地FIT文件的完整路径（如 `/home/user/data.fit`）
   - **运动起始时间**: 视频相对于运动开始的偏移时间（格式：MM:SS）
   - **输出目录**: 输出文件保存目录（默认：`./output`）
3. 点击"开始处理"
4. 等待处理完成，查看输出文件路径

## 系统要求

- Python >= 3.10
- ffmpeg（用于视频处理）
- ffprobe（用于获取视频信息）

安装ffmpeg：
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## 项目结构

```
make_video/
├── app.py              # Flask Web服务
├── video_processor.py  # 视频处理核心逻辑
├── static/             # 前端文件
│   ├── index.html
│   ├── app.js
│   └── style.css
├── output/             # 默认输出目录
└── pyproject.toml      # 项目配置和依赖
```

## 开发

```bash
# 安装开发依赖
uv sync

# 运行服务（开发模式）
uv run python app.py
```

## 注意事项

- 确保视频和FIT文件路径正确且可读
- 视频处理可能需要较长时间，取决于视频长度和系统性能
- 输出文件名为原视频名加 `_with_data.mp4` 后缀
