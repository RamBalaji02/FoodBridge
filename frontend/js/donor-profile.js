
const API_BASE_URL = "http://127.0.0.1:8000";

const profileForm = document.getElementById("donorProfileForm");
const messageBox = document.getElementById("message");
const saveButton = document.getElementById("saveButton");

const token = localStorage.getItem("foodbridge_token");

// Show messages
function showMessage(message, type = "danger") {
    messageBox.innerHTML = "";

    const alert = document.createElement("div");
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    messageBox.appendChild(alert);
}

// Check login
if (!token) {
    window.location.href = "login.html";
}

// Load existing donor profile
async function loadDonorProfile() {
    try {
        const response = await fetch(`${API_BASE_URL}/donor/profile`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (response.status === 404) {
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to load donor profile.");
        }

        const profile = data.profile || data;

        document.getElementById("organization_name").value =
            profile.organization_name || "";

        document.getElementById("donor_type").value =
            profile.donor_type || "";

        document.getElementById("license_number").value =
            profile.license_number || "";

        document.getElementById("address").value =
            profile.address || "";

        document.getElementById("city").value =
            profile.city || "";

        document.getElementById("state").value =
            profile.state || "";

        document.getElementById("postal_code").value =
            profile.postal_code || "";

    } catch (error) {
        showMessage(error.message);
    }
}

// Save donor profile
profileForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const profileData = {
        organization_name: document.getElementById("organization_name").value.trim(),
        donor_type: document.getElementById("donor_type").value,
        license_number:
            document.getElementById("license_number").value.trim() || null,
        address: document.getElementById("address").value.trim(),
        city: document.getElementById("city").value.trim(),
        state: document.getElementById("state").value.trim(),
        postal_code: document.getElementById("postal_code").value.trim()
    };

    saveButton.disabled = true;
    saveButton.textContent = "Saving Profile...";

    messageBox.innerHTML = "";

    try {
        const response = await fetch(`${API_BASE_URL}/donor/profile`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(profileData)
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = data.detail;

            const errorMessage = Array.isArray(detail)
                ? detail.map(item => item.msg).join(", ")
                : detail || "Unable to save donor profile.";

            throw new Error(errorMessage);
        }

        showMessage(
            "Donor profile saved successfully! You can now create food donations.",
            "success"
        );

        saveButton.textContent = "Profile Saved";

        setTimeout(() => {
            window.location.href = "donor-dashboard.html";
        }, 1500);

    } catch (error) {
        showMessage(error.message);
        saveButton.disabled = false;
        saveButton.textContent = "Save Donor Profile";
    }
});

// Load profile when page opens
if (token) {
    loadDonorProfile();
}
