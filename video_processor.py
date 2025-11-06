#!/usr/bin/env python3
"""
视频处理模块
负责从FIT文件提取运动数据并叠加到视频上
"""
from fitparse import FitFile
from PIL import Image, ImageDraw, ImageFont
import subprocess
import os
import json
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing


class VideoProcessor:
    """
    视频处理器
    
    功能：
    - 解析FIT文件获取运动数据（心率、配速、步频、距离、功率）
    - 提取GPS轨迹数据
    - 生成数据叠加图层（数据面板、全局路线图、近距离小地图）
    - 使用多线程加速帧生成
    - 使用GPU加速视频编码（如果可用）
    """
    def __init__(self, video_path, fit_path, offset_seconds, output_path, progress_callback=None):
        self.video_path = video_path
        self.fit_path = fit_path
        self.offset_seconds = offset_seconds
        self.output_path = output_path
        self.progress_callback = progress_callback
        self.gpu_encoder = self._detect_gpu_encoder()
        
    def _detect_gpu_encoder(self):
        """检测可用的GPU编码器"""
        # 检测NVIDIA
        result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], 
                              capture_output=True, text=True)
        encoders = result.stdout
        
        if 'h264_nvenc' in encoders:
            return 'nvenc'
        elif 'h264_qsv' in encoders:
            return 'qsv'
        elif 'h264_vaapi' in encoders:
            return 'vaapi'
        elif 'h264_amf' in encoders:
            return 'amf'
        else:
            return None
        
    def process(self):
        """处理视频，返回输出文件路径"""
        try:
            # 解析FIT数据
            self._update_progress(0, "解析FIT文件...")
            fit = FitFile(self.fit_path)
            self.records = list(fit.get_messages('record'))
            
            # 提取GPS坐标并预处理
            self._extract_gps_data()
            
            # 获取视频信息
            self._update_progress(5, "获取视频信息...")
            width, height, fps, duration = self._get_video_info()
            total_frames = int(duration * fps)
            
            # 生成叠加图层
            self._update_progress(10, f"生成叠加图层 (共{total_frames}帧)...")
            overlay_dir = 'overlay_frames'
            os.makedirs(overlay_dir, exist_ok=True)
            
            start_time = time.time()
            completed_frames = 0
            
            # 使用多线程生成帧
            max_workers = min(multiprocessing.cpu_count(), 8)  # 最多8个线程
            
            def generate_frame(frame_num):
                video_time = frame_num / fps
                activity_time = self.offset_seconds + video_time
                data = self._get_data_at_offset(activity_time)
                overlay = self._create_overlay(width, height, data)
                overlay.save(f'{overlay_dir}/frame_{frame_num:04d}.png')
                return frame_num
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(generate_frame, i): i for i in range(total_frames)}
                
                for future in as_completed(futures):
                    completed_frames += 1
                    if completed_frames % 10 == 0 or completed_frames == total_frames:
                        progress = 10 + int(completed_frames / total_frames * 70)
                        elapsed = time.time() - start_time
                        eta = elapsed / completed_frames * (total_frames - completed_frames)
                        self._update_progress(
                            progress, 
                            f"生成叠加图层: {completed_frames}/{total_frames} (剩余 {int(eta)}s, {max_workers}线程)"
                        )
            
            # 合成视频
            encoder_info = f" (GPU: {self.gpu_encoder})" if self.gpu_encoder else " (CPU)"
            self._update_progress(80, f"合成视频{encoder_info}...")
            output_file = os.path.join(self.output_path, os.path.basename(self.video_path).replace('.mp4', '_with_data.mp4'))
            os.makedirs(self.output_path, exist_ok=True)
            
            # 构建FFmpeg命令
            ffmpeg_cmd = ['ffmpeg', '-y']
            
            # 添加硬件加速
            if self.gpu_encoder == 'nvenc':
                ffmpeg_cmd.extend(['-hwaccel', 'cuda'])
            elif self.gpu_encoder == 'qsv':
                ffmpeg_cmd.extend(['-hwaccel', 'qsv'])
            elif self.gpu_encoder == 'vaapi':
                ffmpeg_cmd.extend(['-hwaccel', 'vaapi'])
            
            ffmpeg_cmd.extend([
                '-i', self.video_path,
                '-framerate', str(fps),
                '-i', f'{overlay_dir}/frame_%04d.png',
                '-filter_complex', '[0:v][1:v]overlay=0:0'
            ])
            
            # 选择编码器
            if self.gpu_encoder == 'nvenc':
                ffmpeg_cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '28'])
            elif self.gpu_encoder == 'qsv':
                ffmpeg_cmd.extend(['-c:v', 'h264_qsv', '-preset', 'medium', '-global_quality', '28'])
            elif self.gpu_encoder == 'vaapi':
                ffmpeg_cmd.extend(['-c:v', 'h264_vaapi', '-qp', '28'])
            elif self.gpu_encoder == 'amf':
                ffmpeg_cmd.extend(['-c:v', 'h264_amf', '-quality', 'balanced', '-qp_i', '28'])
            else:
                # 回退到CPU编码
                ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '28'])
            
            ffmpeg_cmd.extend(['-c:a', 'copy', output_file])
            
            subprocess.run(ffmpeg_cmd, capture_output=True)
            
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
            'power': int(power),
            'current_idx': idx
        }
    
    def _extract_gps_data(self):
        """提取并预处理GPS数据"""
        self.gps_coords = []
        for record in self.records:
            lat = record.get_value('position_lat')
            lon = record.get_value('position_long')
            if lat and lon:
                # 转换semicircles到度
                lat_deg = lat * (180 / 2**31)
                lon_deg = lon * (180 / 2**31)
                self.gps_coords.append((lat_deg, lon_deg))
            else:
                self.gps_coords.append(None)
        
        # 计算有效坐标的边界
        valid_coords = [c for c in self.gps_coords if c is not None]
        if valid_coords:
            lats = [c[0] for c in valid_coords]
            lons = [c[1] for c in valid_coords]
            self.lat_min, self.lat_max = min(lats), max(lats)
            self.lon_min, self.lon_max = min(lons), max(lons)
            
            # 计算缩放比例（保持纵横比）
            lat_range = self.lat_max - self.lat_min
            lon_range = self.lon_max - self.lon_min
            self.coord_range = max(lat_range, lon_range)
        else:
            self.gps_coords = []
    
    def _gps_to_pixel(self, lat, lon, map_size, center_lat=None, center_lon=None, zoom_range=None):
        """将GPS坐标转换为像素坐标"""
        if zoom_range:
            # 小地图模式：以中心点为基准
            if center_lat is None or center_lon is None:
                return map_size // 2, map_size // 2
            x = int((lon - (center_lon - zoom_range)) / (zoom_range * 2) * (map_size - 20) + 10)
            y = int(((center_lat + zoom_range) - lat) / (zoom_range * 2) * (map_size - 20) + 10)
        else:
            # 全局地图模式
            if self.coord_range == 0:
                return map_size // 2, map_size // 2
            x = int((lon - self.lon_min) / self.coord_range * (map_size - 20) + 10)
            y = int((self.lat_max - lat) / self.coord_range * (map_size - 20) + 10)
        return x, y
    
    def _draw_mini_map(self, draw, current_idx, map_x, map_y, map_size):
        """绘制近距离小地图（右下角）"""
        if not self.gps_coords or current_idx >= len(self.gps_coords):
            return
        
        current_coord = self.gps_coords[current_idx]
        if not current_coord:
            return
        
        # 使用绝对距离：前后100米
        # 1度纬度约等于111km，1度经度在北纬40度约等于85km
        # 100米 ≈ 0.0009度纬度，≈ 0.0012度经度（粗略估算）
        zoom_distance_meters = 100  # 显示前后100米
        zoom_range_lat = zoom_distance_meters / 111000  # 纬度范围
        zoom_range_lon = zoom_distance_meters / 85000   # 经度范围（北纬40度附近）
        zoom_range = max(zoom_range_lat, zoom_range_lon)  # 取较大值保证显示完整
        
        # 绘制圆形背景（半透明黑色）
        draw.ellipse(
            [(map_x, map_y), (map_x + map_size, map_y + map_size)],
            fill=(0, 0, 0, 120)
        )
        
        # 计算线条宽度
        line_width = max(2, int(map_size * 0.01))
        dot_size = max(6, int(map_size * 0.03))
        
        # 找出当前范围内的路线点
        center_lat, center_lon = current_coord
        
        # 绘制路线（只绘制范围内的点）
        prev_pixel = None
        prev_in_circle = False
        for i, coord in enumerate(self.gps_coords):
            if coord:
                lat, lon = coord
                # 检查是否在显示范围内
                if (abs(lat - center_lat) <= zoom_range and 
                    abs(lon - center_lon) <= zoom_range):
                    pixel = self._gps_to_pixel(lat, lon, map_size, center_lat, center_lon, zoom_range)
                    pixel = (map_x + pixel[0], map_y + pixel[1])
                    
                    # 检查当前点是否在圆形区域内
                    curr_in_circle = self._is_in_circle(pixel[0], pixel[1], map_x + map_size//2, map_y + map_size//2, map_size//2)
                    
                    # 只有当前点和前一个点都在圆内时才画线
                    if curr_in_circle and prev_pixel and prev_in_circle:
                        # 已走过的用灰白色，未走过的用白色
                        color = (200, 200, 200, 255) if i <= current_idx else (255, 255, 255, 255)
                        draw.line([prev_pixel, pixel], fill=color, width=line_width)
                    
                    if curr_in_circle:
                        prev_pixel = pixel
                        prev_in_circle = True
                    else:
                        prev_pixel = None
                        prev_in_circle = False
                else:
                    prev_pixel = None
                    prev_in_circle = False
        
        # 绘制当前位置（中心的白色圆点）
        center_x = map_x + map_size // 2
        center_y = map_y + map_size // 2
        draw.ellipse(
            [center_x - dot_size, center_y - dot_size, 
             center_x + dot_size, center_y + dot_size],
            fill=(255, 255, 255, 255)
        )
        
        # 绘制圆形边框
        draw.ellipse(
            [(map_x, map_y), (map_x + map_size, map_y + map_size)],
            outline=(255, 255, 255, 150),
            width=2
        )
    
    def _is_in_circle(self, x, y, center_x, center_y, radius):
        """判断点是否在圆内"""
        return (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
    
    def _draw_route_map(self, draw, current_idx, map_x, map_y, map_size):
        """绘制路线图"""
        if not self.gps_coords:
            return
        
        # 计算线条宽度（根据地图大小）
        line_width_gray = max(3, int(map_size * 0.008))  # 未走路线
        line_width_green = max(5, int(map_size * 0.012))  # 已走路线
        dot_size = max(12, int(map_size * 0.02))  # 圆点大小（更大）
        
        # 绘制完整路线（白色）
        prev_pixel = None
        for coord in self.gps_coords:
            if coord:
                pixel = self._gps_to_pixel(coord[0], coord[1], map_size)
                pixel = (map_x + pixel[0], map_y + pixel[1])
                if prev_pixel:
                    draw.line([prev_pixel, pixel], fill=(255, 255, 255, 255), width=line_width_gray)
                prev_pixel = pixel
        
        # 绘制已走过的路线（略灰的白色）
        prev_pixel = None
        for i, coord in enumerate(self.gps_coords[:current_idx + 1]):
            if coord:
                pixel = self._gps_to_pixel(coord[0], coord[1], map_size)
                pixel = (map_x + pixel[0], map_y + pixel[1])
                if prev_pixel:
                    draw.line([prev_pixel, pixel], fill=(200, 200, 200, 255), width=line_width_green)
                prev_pixel = pixel
        
        # 绘制起点（白色圆点）
        if self.gps_coords[0]:
            start_pixel = self._gps_to_pixel(self.gps_coords[0][0], self.gps_coords[0][1], map_size)
            start_pixel = (map_x + start_pixel[0], map_y + start_pixel[1])
            draw.ellipse(
                [start_pixel[0] - dot_size, start_pixel[1] - dot_size, 
                 start_pixel[0] + dot_size, start_pixel[1] + dot_size],
                fill=(255, 255, 255, 255)
            )
        
        # 绘制当前位置（白色圆点）
        if current_idx < len(self.gps_coords) and self.gps_coords[current_idx]:
            curr_coord = self.gps_coords[current_idx]
            curr_pixel = self._gps_to_pixel(curr_coord[0], curr_coord[1], map_size)
            curr_pixel = (map_x + curr_pixel[0], map_y + curr_pixel[1])
            draw.ellipse(
                [curr_pixel[0] - dot_size, curr_pixel[1] - dot_size, 
                 curr_pixel[0] + dot_size, curr_pixel[1] + dot_size],
                fill=(255, 255, 255, 255)
            )
    
    def _create_overlay(self, width, height, data):
        """创建叠加图层"""
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 根据视频尺寸计算比例
        base_size = min(width, height)
        font_size = int(base_size * 0.05)  # 字体大小为短边的5%
        font_size_small = int(base_size * 0.035)  # 小字体为短边的3.5%
        
        try:
            font_bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
            font_regular = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size_small)
        except:
            try:
                font_bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size)
                font_regular = font_bold
            except:
                font_bold = ImageFont.load_default()
                font_regular = font_bold
        
        # 数据面板（左上角）- 无背景
        margin = int(base_size * 0.03)  # 边距为短边的3%
        padding = int(base_size * 0.025)  # 内边距
        
        panel_x, panel_y = margin, margin
        
        y = panel_y + padding
        line_height = int(font_size * 1.3)
        
        # 绘制数据（数值用粗体，单位用细体小字）
        data_items = [
            (f"♥ {data['hr']}", "bpm"),
            (f"⚡ {data['pace']}", "/km"),
            (f"⟳ {data['cadence']}", "spm"),
            (f"⊙ {data['distance']:.2f}", "km"),
            (f"⚙ {data['power']}", "W")
        ]
        
        for value_text, unit_text in data_items:
            x = panel_x + padding
            # 绘制数值（粗体）
            draw.text((x, y), value_text, fill=(255, 255, 255, 255), font=font_bold)
            # 计算数值文本宽度
            value_bbox = draw.textbbox((x, y), value_text, font=font_bold)
            value_width = value_bbox[2] - value_bbox[0]
            # 绘制单位（细体小字，稍微偏下对齐）
            unit_y = y + int(font_size * 0.15)  # 稍微下移对齐基线
            draw.text((x + value_width + 5, unit_y), unit_text, fill=(255, 255, 255, 200), font=font_regular)
            y += line_height
        
        # 路线图（右上角）- 大小为短边的一半
        if self.gps_coords:
            map_size = int(base_size * 0.5)
            map_x = width - map_size - margin
            map_y = margin
            self._draw_route_map(draw, data['current_idx'], map_x, map_y, map_size)
            
            # 小地图（右下角）- 大小为短边的30%
            mini_map_size = int(base_size * 0.3)
            mini_map_x = width - mini_map_size - margin
            mini_map_y = height - mini_map_size - margin
            self._draw_mini_map(draw, data['current_idx'], mini_map_x, mini_map_y, mini_map_size)
        
        return img
    
    def _update_progress(self, percent, message):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)
