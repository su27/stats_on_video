#!/usr/bin/env python3
from fitparse import FitFile
from PIL import Image, ImageDraw, ImageFont
import subprocess
import os
import json
import time
import shutil

class VideoProcessor:
    def __init__(self, video_path, fit_path, offset_seconds, output_path, progress_callback=None):
        self.video_path = video_path
        self.fit_path = fit_path
        self.offset_seconds = offset_seconds
        self.output_path = output_path
        self.progress_callback = progress_callback
        
    def process(self):
        """处理视频，返回输出文件路径"""
        try:
            # 解析FIT数据
            self._update_progress(0, "解析FIT文件...")
            fit = FitFile(self.fit_path)
            self.records = list(fit.get_messages('record'))
            
            # 获取视频信息
            self._update_progress(5, "获取视频信息...")
            width, height, fps, duration = self._get_video_info()
            total_frames = int(duration * fps)
            
            # 生成叠加图层
            self._update_progress(10, f"生成叠加图层 (共{total_frames}帧)...")
            overlay_dir = 'overlay_frames'
            os.makedirs(overlay_dir, exist_ok=True)
            
            start_time = time.time()
            for frame_num in range(total_frames):
                video_time = frame_num / fps
                activity_time = self.offset_seconds + video_time
                
                data = self._get_data_at_offset(activity_time)
                overlay = self._create_overlay(width, height, data)
                overlay.save(f'{overlay_dir}/frame_{frame_num:04d}.png')
                
                if frame_num % 10 == 0 or frame_num == total_frames - 1:
                    progress = 10 + int((frame_num + 1) / total_frames * 70)
                    elapsed = time.time() - start_time
                    eta = elapsed / (frame_num + 1) * (total_frames - frame_num - 1)
                    self._update_progress(
                        progress, 
                        f"生成叠加图层: {frame_num+1}/{total_frames} (剩余 {int(eta)}s)"
                    )
            
            # 合成视频
            self._update_progress(80, "合成视频...")
            output_file = os.path.join(self.output_path, os.path.basename(self.video_path).replace('.mp4', '_with_data.mp4'))
            os.makedirs(self.output_path, exist_ok=True)
            
            subprocess.run([
                'ffmpeg', '-y',
                '-i', self.video_path,
                '-framerate', str(fps),
                '-i', f'{overlay_dir}/frame_%04d.png',
                '-filter_complex', '[0:v][1:v]overlay=0:0',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '28',
                '-c:a', 'copy',
                output_file
            ], capture_output=True)
            
            # 清理临时文件
            self._update_progress(95, "清理临时文件...")
            shutil.rmtree(overlay_dir)
            
            self._update_progress(100, "完成")
            return output_file
            
        except Exception as e:
            self._update_progress(-1, f"错误: {str(e)}")
            raise
    
    def _get_video_info(self):
        """获取视频信息"""
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
             '-show_entries', 'stream=width,height,r_frame_rate', self.video_path],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        video_stream = info['streams'][0]
        width = video_stream['width']
        height = video_stream['height']
        fps = eval(video_stream['r_frame_rate'])
        
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_entries', 'format=duration', self.video_path],
            capture_output=True, text=True
        )
        duration = float(json.loads(result.stdout)['format']['duration'])
        
        return width, height, fps, duration
    
    def _get_data_at_offset(self, offset_seconds):
        """获取指定偏移时间的运动数据"""
        idx = min(int(offset_seconds), len(self.records) - 1)
        record = self.records[idx]
        
        hr = record.get_value('heart_rate') or 0
        speed = record.get_value('enhanced_speed') or record.get_value('speed') or 0
        cadence = record.get_value('cadence') or 0
        distance = (record.get_value('distance') or 0) / 1000
        power = record.get_value('power') or 0
        
        if speed > 0:
            pace_seconds = 1000 / speed
            pace_min = int(pace_seconds // 60)
            pace_sec = int(pace_seconds % 60)
            pace_str = f"{pace_min}:{pace_sec:02d}"
        else:
            pace_str = "--:--"
        
        return {
            'hr': int(hr),
            'pace': pace_str,
            'cadence': int(cadence * 2) if cadence else 0,
            'distance': distance,
            'power': int(power)
        }
    
    def _create_overlay(self, width, height, data):
        """创建叠加图层"""
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 90)
        except:
            font = ImageFont.load_default()
        
        panel_x, panel_y = 60, 60
        panel_w, panel_h = 600, 660
        padding = 40
        
        draw.rectangle(
            [(panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h)],
            fill=(0, 0, 0, 90)
        )
        
        y = panel_y + padding
        line_height = 120
        
        texts = [
            f"♥ {data['hr']} bpm",
            f"⚡ {data['pace']} /km",
            f"⟳ {data['cadence']} spm",
            f"⊙ {data['distance']:.2f} km",
            f"⚙ {data['power']} W"
        ]
        
        for text in texts:
            draw.text((panel_x + padding, y), text, fill=(255, 255, 255, 255), font=font)
            y += line_height
        
        return img
    
    def _update_progress(self, percent, message):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)
