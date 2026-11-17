
const API_BASE_URL = "http://127.0.0.1:8000";

const loginForm = document.getElementById("loginForm");
const messageBox = document.getElementById("message");
const loginButton = document.getElementById("loginButton");

document.getElementById("currentYear").textContent =
    new Date().getFullYear();

loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    loginButton.disabled = true;
    loginButton.textContent = "Logging in...";
    messageBox.innerHTML = "";

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed. Please try again.");
        }

        if (!data.access_token || !data.role) {
            throw new Error("Invalid login response from server.");
        }

        const role = String(data.role).toUpperCase();

        // Save login information.
        localStorage.setItem("foodbridge_token", data.access_token);
        localStorage.setItem("foodbridge_role", role);
        localStorage.setItem("foodbridge_user_id", data.user_id);
        localStorage.setItem("foodbridge_email", data.email);

        // Redirect according to user role.
        const dashboards = {
            DONOR: "donor-dashboard.html",
            NGO: "ngo-dashboard.html",
            VOLUNTEER: "volunteer-dashboard.html",
            ADMIN: "admin-dashboard.html"
        };

        if (!dashboards[role]) {
            throw new Error("Unknown user role.");
        }

        messageBox.innerHTML =
            '<div class="alert alert-success">Login successful! Redirecting...</div>';

        loginButton.textContent = "Login Successful";

        window.location.href = dashboards[role];

    } catch (error) {
        messageBox.innerHTML =
            `<div class="alert alert-danger">${error.message}</div>`;

        loginButton.disabled = false;
        loginButton.innerHTML =
            'Login <i class="bi bi-arrow-right"></i>';
    }
});
