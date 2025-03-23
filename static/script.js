document.addEventListener('DOMContentLoaded', () => {

    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const messageDiv = document.getElementById('message');
        const resultDiv = document.getElementById('result');

        // Upload the file
        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const uploadResult = await uploadResponse.json();

        if (uploadResult.status === 'success') {
            messageDiv.innerHTML = `<div class="message success">File uploaded! File ID: ${uploadResult.file_id}</div>`;

            const fileId = uploadResult.file_id;
            const checkStatus = async () => {
                const statusResponse = await fetch(`/file/${fileId}`);
                const statusResult = await statusResponse.json();

                if (statusResult.status === 'SUCCESS') {
                    location.reload();
                } else if (statusResult.status === 'FAILURE') {
                    resultDiv.innerHTML = `<div class="message error">
                        <h3>Error</h3>
                        <p>Status: ${statusResult.status}</p>
                    </div>`;
                } else {
                    resultDiv.innerHTML = `<div class="message">Status: ${statusResult.status}</div>`;
                    setTimeout(checkStatus, 2000);
                }
            };
            checkStatus();
        } else {
            messageDiv.innerHTML = `<div class="message error">${uploadResult.message}</div>`;
        }
    });
});


function toggleSlideDetails(fileId) {
    const detailsDiv = document.getElementById(`slide-details-${fileId}`);
    const button = document.querySelector(`button[onclick="toggleSlideDetails(${fileId})"]`);
    if (detailsDiv.style.display === 'none') {
        detailsDiv.style.display = 'block';
        button.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Slides';
    } else {
        detailsDiv.style.display = 'none';
        button.innerHTML = '<i class="fas fa-eye"></i> View Slides';
    }
}