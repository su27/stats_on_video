const form = document.getElementById('processForm');
const submitBtn = document.getElementById('submitBtn');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const statusText = document.getElementById('statusText');
const resultContainer = document.getElementById('resultContainer');
const outputFile = document.getElementById('outputFile');

let pollInterval = null;

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const videoPath = document.getElementById('videoPath').value;
    const fitPath = document.getElementById('fitPath').value;
    const offset = document.getElementById('offset').value;
    const outputPath = document.getElementById('outputPath').value;
    
    // 重置UI
    progressContainer.classList.remove('hidden');
    resultContainer.classList.add('hidden');
    submitBtn.disabled = true;
    progressFill.style.width = '0%';
    progressText.textContent = '提交任务...';
    statusText.textContent = '';
    
    try {
        // 提交任务
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_path: videoPath,
                fit_path: fitPath,
                offset: offset,
                output_path: outputPath
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '提交失败');
        }
        
        // 开始轮询状态
        pollStatus(data.task_id);
        
    } catch (error) {
        alert('错误: ' + error.message);
        submitBtn.disabled = false;
        progressContainer.classList.add('hidden');
    }
});

async function pollStatus(taskId) {
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${taskId}`);
            const data = await response.json();
            
            // 更新进度
            progressFill.style.width = data.progress + '%';
            progressText.textContent = `${data.progress}%`;
            statusText.textContent = data.message;
            
            // 检查状态
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                submitBtn.disabled = false;
                resultContainer.classList.remove('hidden');
                outputFile.textContent = data.output_file;
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                submitBtn.disabled = false;
                alert('处理失败: ' + data.message);
            }
            
        } catch (error) {
            clearInterval(pollInterval);
            submitBtn.disabled = false;
            alert('查询状态失败: ' + error.message);
        }
    }, 1000);
}
