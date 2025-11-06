# 视频数据叠加工具

将运动数据（FIT文件）叠加到视频上的Web工具，支持GPS路线图和实时运动数据显示。

## 功能特性

### 数据显示
- ❤️ 心率 (bpm)
- ⚡ 配速 (分:秒/km)
- ⟳ 步频 (spm)
- ⊙ 距离 (km)
- ⚙ 功率 (W)

### 路线图
- **全局路线图**（右上角）：显示完整运动轨迹
- **近距离小地图**（右下角）：类似游戏小地图，显示当前位置周围100米范围

### 性能优化
- 多线程并行生成帧（2-8倍提速）
- GPU硬件加速视频编码（3-10倍提速）
  - 自动检测NVIDIA、Intel、AMD显卡
  - 无GPU时自动回退到CPU编码

### 界面特点
- 所有元素大小按视频尺寸自动缩放
- 简洁的白色系设计，适合各种视频背景
- 无背景遮挡，保持视频画面清晰

## 安装

### 系统要求
- Python >= 3.10
- ffmpeg（用于视频处理）
- ffprobe（用于获取视频信息）

### 安装ffmpeg
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 安装Python依赖
使用 uv 管理依赖：

```bash
# 安装依赖
uv sync

# 或者使用 pip
uv pip install -e .
```

## 使用方法

### 方式1: Web界面（推荐）

1. **启动服务**
```bash
# 使用uv运行
uv run python app.py

# 或使用已安装的命令
uv run make-video-server
```

2. **打开浏览器**
访问 `http://localhost:5000`

3. **填写信息**
   - **视频文件路径**: 本地视频文件的完整路径（如 `/home/user/video.mp4`）
   - **FIT文件路径**: 本地FIT文件的完整路径（如 `/home/user/data.fit`）
   - **运动起始时间**: 视频相对于运动开始的偏移时间（格式：MM:SS，如 `14:49`）
   - **输出目录**: 输出文件保存目录（默认：`./output`）

4. **开始处理**
点击"开始处理"，实时查看进度

5. **获取结果**
处理完成后，在输出目录找到 `原文件名_with_data.mp4`

### 方式2: 预览单帧

快速生成单帧预览图，查看叠加效果：

```bash
# 1. 编辑 preview_overlay.py，修改参数
# 2. 运行
uv run python preview_overlay.py

# 3. 查看生成的预览图
# - preview_combined.png: 完整预览（视频+叠加层）
# - preview_overlay.png: 纯叠加层（透明背景）
```

## 项目结构

```
make_video/
├── app.py                 # Flask Web服务
├── video_processor.py     # 视频处理核心逻辑
├── preview_overlay.py     # 预览图生成工具
├── static/                # 前端文件
│   ├── index.html        # Web界面
│   ├── app.js            # 前端交互逻辑
│   └── style.css         # 样式
├── output/                # 默认输出目录
├── pyproject.toml         # 项目配置和依赖
└── README.md              # 本文档
```

## 技术细节

### 坐标系统
- FIT文件使用semicircles单位存储GPS坐标
- 自动转换为度数（latitude/longitude）
- 小地图使用绝对距离（100米）而非百分比

### 视频编码
自动检测并使用最佳编码器：
- **NVIDIA GPU**: h264_nvenc
- **Intel GPU**: h264_qsv
- **AMD GPU**: h264_vaapi / h264_amf
- **CPU**: libx264（回退方案）

### 多线程处理
- 自动使用CPU核心数（最多8线程）
- 并行生成叠加帧
- 显著提升处理速度

## 注意事项

- 确保视频和FIT文件路径正确且可读
- 视频处理时间取决于视频长度和系统性能
- 建议使用SSD存储临时文件以提升速度
- GPU加速需要对应的驱动程序

## 开发

```bash
# 安装开发依赖
uv sync

# 运行服务（开发模式）
uv run python app.py

# 生成预览图
uv run python preview_overlay.py
```

## 示例

### 输入
- 视频：4K (3840x2160)，30fps，42秒
- FIT文件：包含GPS轨迹和运动数据
- 偏移时间：00:00

### 输出
- 视频：相同分辨率和帧率
- 叠加内容：
  - 左上角：运动数据面板
  - 右上角：全局路线图（1080x1080）
  - 右下角：近距离小地图（648x648，圆形）

### 处理时间（参考）
- 8核CPU + NVIDIA GPU：约1-2分钟
- 4核CPU（无GPU）：约5-10分钟

## License

MIT
