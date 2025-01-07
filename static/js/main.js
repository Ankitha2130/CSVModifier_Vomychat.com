document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const status = document.getElementById('status');
    const log = document.getElementById('log');
    
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData();
        const fileInput = document.getElementById('file');
        const instructions = document.getElementById('instructions').value;
        
        if (!fileInput.files.length) {
            status.innerHTML = '<p class="error">Please select a file</p>';
            return;
        }
        
        formData.append('file', fileInput.files[0]);
        formData.append('instructions', instructions);
        
        try {
            status.innerHTML = '<p>Processing file...</p>';
            
            const response = await fetch('/upload/', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                status.innerHTML = '<p class="success">File processed successfully!</p>';
                
                // Display detailed logs
                if (result.logs && result.logs.length > 0) {
                    log.innerHTML += '<p class="success">Processing steps:</p>';
                    result.logs.forEach(logEntry => {
                        log.innerHTML += `<p>• ${logEntry}</p>`;
                    });
                }
                
                if (result.download_url) {
                    document.getElementById('download').style.display = 'block';
                    document.getElementById('downloadLink').href = result.download_url;
                }
            } else {
                throw new Error(result.message || 'Processing failed');
            }
        } catch (error) {
            status.innerHTML = `<p class="error">Error: ${error.message}</p>`;
            log.innerHTML += `<p class="error">${new Date().toLocaleString()}: ${error.message}</p>`;
        }
    });
}); 