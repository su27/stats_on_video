#!/usr/bin/env python3
"""
预览图生成工具
用于快速生成单帧预览图，查看叠加效果

使用方法：
1. 修改下面的参数（视频路径、FIT路径、偏移时间）
2. 运行: uv run python preview_overlay.py
3. 查看生成的 preview_combined.png
"""
from video_processor import VideoProcessor
import subprocess
import json

# ===== 配置参数 =====
video_path = '/home/su27/2.mp4'
fit_path = '/home/su27/1.fit'
offset_seconds = 32 * 60 + 11  # 32:11
# ===================

# 创建处理器
processor = VideoProcessor(video_path, fit_path, offset_seconds, './output')

# 解析FIT数据
from fitparse import FitFile
fit = FitFile(fit_path)
processor.records = list(fit.get_messages('record'))
processor._extract_gps_data()

# 获取视频信息
result = subprocess.run(
    ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
     '-show_entries', 'stream=width,height', video_path],
    capture_output=True, text=True
)
info = json.loads(result.stdout)
video_stream = info['streams'][0]
width = video_stream['width']
height = video_stream['height']

print(f"视频尺寸: {width}x{height}")
print(f"较短边: {min(width, height)}")
print(f"地图大小: {int(min(width, height) * 0.5)}")

# 生成预览帧（使用偏移时间后的第一帧）
data = processor._get_data_at_offset(offset_seconds)
overlay = processor._create_overlay(width, height, data)

# 保存预览图
overlay.save('preview_overlay.png')
print("\n预览图已保存: preview_overlay.png")

# 提取视频的一帧作为背景
subprocess.run([
    'ffmpeg', '-y', '-ss', str(offset_seconds), '-i', video_path,
    '-frames:v', '1', 'preview_background.jpg'
], capture_output=True)

# 合成预览图
from PIL import Image
bg = Image.open('preview_background.jpg')
bg = bg.convert('RGBA')
combined = Image.alpha_composite(bg, overlay)
combined.save('preview_combined.png')
print("合成预览图已保存: preview_combined.png")
