# Stats on Video

将 Garmin 运动数据（FIT文件）叠加到运动相机视频上，支持心率、配速、步频、距离、功率显示以及 GPS 路线图。

## 功能特性

### 数据显示
- ❤️ 心率 (bpm)
- ⚡ 配速 (分:秒/km)
- ⟳ 步频 (spm)
- ⊙ 距离 (km)
- ⚙ 功率 (W)

### 路线图
- **全局路线图**（右上角）：显示完整运动轨迹，白色标记已走过的路线，高亮当前位置
- **近距离小地图**（右下角）：类似游戏小地图，圆形显示当前位置周围 100 米范围

### 性能优化
- 多线程并行生成叠加帧（自动使用 CPU 核心数，最多 8 线程）
- GPU 硬件加速视频编码（自动检测，无 GPU 时回退到 CPU）
  - NVIDIA: h264_nvenc
  - Intel: h264_qsv
  - AMD: h264_vaapi / h264_amf
  - CPU 回退: libx264

### 界面特点
- 所有元素大小按视频分辨率自动缩放
- 简洁的白色系设计，适合各种视频背景
- 无背景遮挡，保持视频画面清晰

## 系统要求

- Python >= 3.10
- ffmpeg / ffprobe

### 安装 ffmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 从 https://ffmpeg.org/download.html 下载
```

## 安装

```bash
# 使用 uv（推荐）
uv sync

# 或者使用 pip
pip install .
```

## 使用方法

### 方式一：Web 界面（推荐）

1. **启动服务**

```bash
# 使用 uv 运行
uv run make-video-server

# 或者直接运行
uv run python app.py
```

2. **打开浏览器**访问 http://localhost:5000

3. **填写参数**
   - **视频文件路径**：运动相机视频的完整路径（如 `/home/user/video.mp4`）
   - **FIT 文件路径**：Garmin FIT 文件的完整路径（如 `/home/user/activity.fit`）
   - **运动起始时间 (MM:SS)**：视频相对于运动开始的偏移时间。例如你在运动开始后第 14 分 49 秒才开始录像，就填 `14:49`
   - **输出目录**：输出文件保存目录（默认 `./output`）

4. **点击"开始处理"**，页面会实时显示处理进度

5. **获取结果**：处理完成后，在输出目录找到 `原文件名_with_data.mp4`

> ⚠️ **注意**：这是一个本地工具，Web 界面接受的是本机文件路径，请勿将服务暴露到公网。

### 处理时间参考

以 4K (3840×2160)、30fps、42 秒视频为例：
- 8 核 CPU + NVIDIA GPU：约 1-2 分钟
- 4 核 CPU（无 GPU）：约 5-10 分钟

## 项目结构

```
├── app.py                 # Flask Web 服务，提供 API 和任务管理
├── video_processor.py     # 核心视频处理逻辑
├── static/
│   ├── index.html         # Web 界面
│   ├── app.js             # 前端交互逻辑
│   └── style.css          # 样式
├── pyproject.toml         # 项目配置和依赖
├── LICENSE                # MIT 许可证
└── README.md              # 本文档
```

## 技术细节

### FIT 文件解析
- 使用 `garmin-fit-sdk` 解析 FIT 文件
- GPS 坐标从 semicircles 单位自动转换为经纬度
- 支持提取心率、配速、步频、距离、功率等字段

### 视频处理流程
1. 解析 FIT 文件，提取逐秒运动记录和 GPS 坐标
2. 多线程并行生成透明 PNG 叠加帧（数据面板 + 路线图）
3. 使用 ffmpeg 将叠加帧合成到原始视频上
4. 自动选择最佳可用编码器（GPU 优先，CPU 回退）

### 坐标系统
- FIT 文件使用 semicircles 单位存储 GPS 坐标，自动转换为度数
- 全局路线图根据轨迹边界自动缩放
- 小地图使用绝对距离（100 米半径）而非百分比，确保缩放一致

### 跨平台支持
- 自动查找系统字体（Windows / macOS / Linux）
- 临时文件使用系统临时目录，不污染工作目录
- ffmpeg 未安装时提供对应平台的安装指引

## 注意事项

- 确保视频和 FIT 文件路径正确且可读
- 视频处理时间取决于视频长度、分辨率和系统性能
- 建议使用 SSD 存储以提升临时文件读写速度
- GPU 加速需要安装对应的驱动程序

## License

MIT
