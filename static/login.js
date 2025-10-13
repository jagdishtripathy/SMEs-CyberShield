document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    console.log("Form data:", { username, password });

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `username=${username}&password=${password}`,
    })
    .then(response => response.json())
    .then(data => {
        console.log("Response data:", data);
        if (data.success) {
            console.log("Login successful, redirecting to /dashboard");
            window.location.replace('/dashboard'); // Using replace
        } else {
            console.log("Login failed:", data.error);
            document.getElementById('loginError').textContent = data.error;
        }
    })
    .catch(error => {
        console.error('Login error:', error);
        document.getElementById('loginError').textContent = 'An error occurred during login.';
    });
});
