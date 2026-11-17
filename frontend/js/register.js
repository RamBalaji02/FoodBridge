
const API_BASE_URL = "http://127.0.0.1:8000";

const registerForm = document.getElementById("registerForm");
const messageBox = document.getElementById("message");
const registerButton = document.getElementById("registerButton");

document.getElementById("currentYear").textContent =
    new Date().getFullYear();

registerForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const userData = {
        full_name: document.getElementById("full_name").value.trim(),
        email: document.getElementById("email").value.trim(),
        phone: document.getElementById("phone").value.trim(),
        password: document.getElementById("password").value,
        role: document.getElementById("role").value
    };

    registerButton.disabled = true;
    registerButton.textContent = "Creating Account...";
    messageBox.innerHTML = "";

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(userData)
        });

        const data = await response.json();

        if (!response.ok) {
            const errorMessage = Array.isArray(data.detail)
                ? data.detail.map(item => item.msg).join(", ")
                : data.detail || "Registration failed.";

            throw new Error(errorMessage);
        }

        messageBox.innerHTML = `
            <div class="alert alert-success">
                <strong>Registration successful!</strong><br>
                Your account is pending admin approval.
                Once approved, you can login to FoodBridge.
            </div>
        `;

        registerForm.reset();
        registerButton.textContent = "Account Created";

    } catch (error) {
        messageBox.innerHTML = `
            <div class="alert alert-danger">
                ${error.message}
            </div>
        `;

        registerButton.disabled = false;
        registerButton.innerHTML =
            'Create Account <i class="bi bi-arrow-right"></i>';
    }
});
