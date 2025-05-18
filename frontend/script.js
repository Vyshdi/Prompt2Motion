document.addEventListener('DOMContentLoaded', () => {
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    const statusMessage = document.getElementById('status-message');
    const animationVideo = document.getElementById('animation-video');
    const videoPlaceholderMessage = document.getElementById('video-placeholder-message');

    generateBtn.addEventListener('click', async () => {
        const promptText = promptInput.value;

        statusMessage.textContent = 'Processing... Please wait, this can take a moment.';
        statusMessage.style.color = 'orange';
        generateBtn.disabled = true;
        animationVideo.style.display = 'none';
        videoPlaceholderMessage.style.display = 'block';

        try {
            const response = await fetch('/api/generate-animation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: promptText })
            });

            const data = await response.json();

            if (response.ok && data.success && data.video_url) {
                statusMessage.textContent = 'Animation generated successfully!';
                statusMessage.style.color = 'green';
                animationVideo.src = data.video_url;
                animationVideo.style.display = 'block';
                videoPlaceholderMessage.style.display = 'none';
                animationVideo.load();
                animationVideo.play().catch(e => console.warn("Autoplay was prevented:", e));
            } else {
                statusMessage.textContent = `Error: ${data.message || 'Failed to generate animation.'}`;
                statusMessage.style.color = 'red';
            }

        } catch (error) {
            console.error('Error calling API:', error);
            statusMessage.textContent = 'Error: Could not connect to the server or an unexpected error occurred.';
            statusMessage.style.color = 'red';
        } finally {
            generateBtn.disabled = false;
        }
    });
});
