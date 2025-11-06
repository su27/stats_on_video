#!/usr/bin/env python3
"""
Flask Web服务
提供Web界面用于视频数据叠加处理
"""
from flask import Flask, request, jsonify, send_from_directory
from video_processor import VideoProcessor
import threading
import uuid
import os

app = Flask(__name__, static_folder='static', static_url_path='')

# 任务状态存储（内存中）
tasks = {}


@app.route('/')
def index():
    """返回主页"""
    return send_from_directory('static', 'index.html')


@app.route('/api/process', methods=['POST'])
def process_video():
    """
    创建视频处理任务
    
    请求参数：
    - video_path: 视频文件路径
    - fit_path: FIT文件路径
    - offset: 视频起始偏移时间 (MM:SS格式)
    - output_path: 输出目录
    
    返回：
    - task_id: 任务ID，用于查询状态
    """
    data = request.json
    video_path = data.get('video_path')
    fit_path = data.get('fit_path')
    offset_str = data.get('offset', '00:00')
    output_path = data.get('output_path', './output')
    
    # 验证输入
    if not video_path or not fit_path:
        return jsonify({'error': '请提供视频和FIT文件路径'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'视频文件不存在: {video_path}'}), 400
    
    if not os.path.exists(fit_path):
        return jsonify({'error': f'FIT文件不存在: {fit_path}'}), 400
    
    if not os.access(video_path, os.R_OK):
        return jsonify({'error': f'无法读取视频文件: {video_path}'}), 400
    
    if not os.access(fit_path, os.R_OK):
        return jsonify({'error': f'无法读取FIT文件: {fit_path}'}), 400
    
    # 解析偏移时间
    try:
        parts = offset_str.split(':')
        offset_seconds = int(parts[0]) * 60 + int(parts[1])
    except:
        return jsonify({'error': '时间格式错误，请使用 MM:SS 格式'}), 400
    
    # 创建任务
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'message': '等待处理...',
        'output_file': None
    }
    
    # 启动后台线程处理
    def process_task():
        def update_progress(percent, message):
            tasks[task_id]['progress'] = percent
            tasks[task_id]['message'] = message
            if percent < 0:
                tasks[task_id]['status'] = 'error'
            elif percent >= 100:
                tasks[task_id]['status'] = 'completed'
            else:
                tasks[task_id]['status'] = 'processing'
        
        try:
            processor = VideoProcessor(video_path, fit_path, offset_seconds, output_path, update_progress)
            output_file = processor.process()
            tasks[task_id]['output_file'] = output_file
        except Exception as e:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['message'] = str(e)
    
    thread = threading.Thread(target=process_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    查询任务状态
    
    返回：
    - status: pending/processing/completed/error
    - progress: 进度百分比 (0-100)
    - message: 状态消息
    - output_file: 输出文件路径（完成时）
    """
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(tasks[task_id])


def main():
    """命令行入口"""
    print("启动视频数据叠加服务...")
    print("访问 http://localhost:5000 使用Web界面")
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()
