document.addEventListener('DOMContentLoaded', function() {
    // Password confirmation validation on register page
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('confirm_password');
    const passwordFeedback = document.getElementById('password-feedback');
    
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', function() {
            if (passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.classList.add('is-invalid');
                passwordFeedback.textContent = 'Passwords do not match';
                passwordFeedback.style.display = 'block';
            } else {
                confirmPasswordField.classList.remove('is-invalid');
                passwordFeedback.style.display = 'none';
            }
        });
        
        // Validate form before submission
        const registerForm = document.querySelector('form');
        registerForm.addEventListener('submit', function(event) {
            if (passwordField.value !== confirmPasswordField.value) {
                event.preventDefault();
                confirmPasswordField.classList.add('is-invalid');
                passwordFeedback.textContent = 'Passwords do not match';
                passwordFeedback.style.display = 'block';
            }
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
