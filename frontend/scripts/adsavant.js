document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Toggle Logic ---
    const btnLogin = document.getElementById('btn-show-login');
    const btnSignup = document.getElementById('btn-show-signup');
    const viewLogin = document.getElementById('view-login');
    const viewSignup = document.getElementById('view-signup');
    const footerText = document.getElementById('footer-text');

    function switchView(view) {
        if (view === 'signup') {
            btnSignup.classList.add('active');
            btnLogin.classList.remove('active');
            viewSignup.classList.add('active-view');
            viewLogin.classList.remove('active-view');
            footerText.innerHTML = `Already have an account? <strong><a href="#" onclick="document.getElementById('btn-show-login').click()">Sign in</a></strong>`;
        } else {
            btnLogin.classList.add('active');
            btnSignup.classList.remove('active');
            viewLogin.classList.add('active-view');
            viewSignup.classList.remove('active-view');
            footerText.innerHTML = `Don't have an account? <strong><a href="#" onclick="document.getElementById('btn-show-signup').click()">Sign up</a></strong>`;
        }
    }

    btnLogin.addEventListener('click', () => switchView('login'));
    btnSignup.addEventListener('click', () => switchView('signup'));


    // --- 2. Password Validation Logic ---
    const passwordInput = document.getElementById('reg-password');
    const strengthFill = document.getElementById('strength-fill');
    const strengthText = document.getElementById('strength-text');

    // Rule Elements
    const ruleLength = document.getElementById('rule-length');
    const ruleUpper = document.getElementById('rule-upper');
    const ruleLower = document.getElementById('rule-lower');
    const ruleNumber = document.getElementById('rule-number');
    const ruleSpecial = document.getElementById('rule-special');

    passwordInput.addEventListener('input', (e) => {
        const val = e.target.value;
        let score = 0;

        // Reset classes
        strengthFill.className = 'strength-fill';
        strengthText.className = '';

        // Check Length
        if (val.length >= 8) { ruleLength.classList.add('rule-pass'); score++; } 
        else { ruleLength.classList.remove('rule-pass'); }

        // Check Uppercase
        if (/[A-Z]/.test(val)) { ruleUpper.classList.add('rule-pass'); score++; } 
        else { ruleUpper.classList.remove('rule-pass'); }

        // Check Lowercase
        if (/[a-z]/.test(val)) { ruleLower.classList.add('rule-pass'); score++; } 
        else { ruleLower.classList.remove('rule-pass'); }

        // Check Number
        if (/[0-9]/.test(val)) { ruleNumber.classList.add('rule-pass'); score++; } 
        else { ruleNumber.classList.remove('rule-pass'); }

        // Check Special Char
        if (/[^A-Za-z0-9]/.test(val)) { ruleSpecial.classList.add('rule-pass'); score++; } 
        else { ruleSpecial.classList.remove('rule-pass'); }

        // Update UI based on score
        if (val.length === 0) {
            strengthText.textContent = "None";
        } else if (score <= 2) {
            strengthFill.classList.add('fill-weak');
            strengthText.textContent = "Weak";
            strengthText.classList.add('text-weak');
        } else if (score <= 4) {
            strengthFill.classList.add('fill-medium');
            strengthText.textContent = "Medium";
            strengthText.classList.add('text-medium');
        } else {
            strengthFill.classList.add('fill-strong');
            strengthText.textContent = "Strong";
            strengthText.classList.add('text-strong');
        }
    });

    // --- 3. Authentication (Login / Signup) Logic ---
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');

    if (signupForm) {
        signupForm.addEventListener('submit', (e) => {
            e.preventDefault(); // Stop the page from refreshing

            // Extract values from the signup form
            const inputs = signupForm.querySelectorAll('input');
            const email = inputs[3].value;
            const password = inputs[4].value;

            // Fetch existing users from local storage, or create an empty array
            const users = JSON.parse(localStorage.getItem('adsavant_users')) || [];

            // Check if email is already taken
            const userExists = users.find(u => u.email === email);
            if (userExists) {
                alert('An account with this email already exists!');
                return;
            }

            // Save the new user to our "database"
            users.push({ email: email, password: password });
            localStorage.setItem('adsavant_users', JSON.stringify(users));

            alert('Account created successfully! You can now log in.');

            // Switch to login tab and auto-fill the email for convenience
            switchView('login');
            const loginEmailInput = loginForm.querySelector('input[type="email"]');
            if (loginEmailInput) {
                loginEmailInput.value = email;
            }

            // Clear the signup form
            signupForm.reset();
            passwordInput.dispatchEvent(new Event('input')); // reset strength meter
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault(); // Stop the page from refreshing

            // Extract values from the login form
            const inputs = loginForm.querySelectorAll('input');
            const email = inputs[0].value;
            const password = inputs[1].value;

            // Fetch existing users from local storage
            const users = JSON.parse(localStorage.getItem('adsavant_users')) || [];

            // Check if credentials match any registered user
            const validUser = users.find(u => u.email === email && u.password === password);

            // Developer cheat code: Allow 'admin@test.com' with password 'admin'
            const isDevAdmin = (email === 'admin@test.com' && password === 'admin');

            if (validUser || isDevAdmin) {
                // Success! Redirect to the dashboard
                window.location.href = 'dashboard.html';
            } else {
                alert('Invalid email or password. Please try again.');
            }
        });
    }
});