function toggleChatbot() {
    var chatbot = document.getElementById('chatbot');
    var toggleButton = document.getElementById('chatbot-toggle');

    chatbot.classList.toggle('active');
    toggleButton.classList.toggle('circle'); // Toggle the circle class on the button
}

function sendMessage(event) {
    if (event.keyCode === 13) {
        var input = document.getElementById('chatbot-input');
        var message = input.value.trim();
        if (message) {
            // Add message to chat window
            var chatWindow = document.getElementById('chatbot-messages');
            chatWindow.innerHTML += '<div>You: ' + message + '</div>';

            // Send message to server and get response
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 'message': message }),
            })
            .then(response => response.json())
            .then(data => {
                chatWindow.innerHTML += '<div>Bot: ' + data.message + '</div>';
                chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to the bottom
            })
            .catch(error => console.error('Error:', error));

            input.value = '';
        }
    }
}
