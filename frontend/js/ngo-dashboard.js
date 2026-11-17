
const API_BASE_URL = "http://127.0.0.1:8000";

const getToken = () => localStorage.getItem("foodbridge_token");

document.getElementById("currentYear").textContent =
    new Date().getFullYear();

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#039;"
    })[c]);
}

// Central API helper
async function apiRequest(endpoint, options = {}) {
    const token = getToken();

    if (!token) {
        window.location.href = "login.html";
        throw new Error("Please login again.");
    }

    const headers = {
        "Content-Type": "application/json",
        ...options.headers,
        "Authorization": `Bearer ${token.trim().replace(/^Bearer\s+/i, "")}`
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
            ? detail.map(item => item.msg).join(", ")
            : detail;

        if (response.status === 401) {
            localStorage.removeItem("foodbridge_token");
            localStorage.removeItem("foodbridge_role");
            localStorage.removeItem("foodbridge_user_id");
            localStorage.removeItem("foodbridge_email");
            throw new Error("Session expired. Please login again.");
        }

        throw new Error(message || `Request failed (${response.status}).`);
    }

    return data;
}

function getList(data, key) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.[key])) return data[key];
    if (Array.isArray(data?.items)) return data.items;
    return [];
}

function showMessage(message, type = "success") {
    const box = document.getElementById("message");
    if (!box) return;

    box.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show">
            ${escapeHTML(message)}
            <button type="button" class="btn-close"
                data-bs-dismiss="alert"></button>
        </div>`;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function logout() {
    localStorage.removeItem("foodbridge_token");
    localStorage.removeItem("foodbridge_role");
    localStorage.removeItem("foodbridge_user_id");
    localStorage.removeItem("foodbridge_email");
    window.location.href = "login.html";
}

// Available donations
async function loadDonations() {
    const container = document.getElementById("donationsList");
    container.innerHTML = '<p class="text-muted">Loading donations...</p>';

    try {
        const data = await apiRequest("/donations/available");
        const donations = getList(data, "donations");

        document.getElementById("availableCount").textContent =
            donations.length;

        if (!donations.length) {
            container.innerHTML =
                '<p class="text-muted">No available donations.</p>';
            return;
        }

        container.innerHTML = donations.map(d => `
            <div class="col-md-6 col-xl-4">
                <div class="dashboard-card">
                    <h5 class="fw-bold">${escapeHTML(d.title)}</h5>
                    <p class="text-muted small">${escapeHTML(d.description)}</p>
                    <p><strong>Food Type:</strong> ${escapeHTML(d.food_type)}</p>
                    <p><strong>Quantity:</strong>
                        ${escapeHTML(d.quantity)} ${escapeHTML(d.unit)}</p>
                    <p><strong>City:</strong> ${escapeHTML(d.pickup_city)}</p>
                    <p><strong>Expiry:</strong> ${escapeHTML(d.expires_at)}</p>
                    <button class="btn btn-food w-100"
                        onclick="requestDonation(${Number(d.id)})">
                        <i class="bi bi-send me-1"></i> Request Food
                    </button>
                </div>
            </div>
        `).join("");

    } catch (error) {
        container.innerHTML =
            `<p class="text-danger">${escapeHTML(error.message)}</p>`;
    }
}

// Submit donation request
async function requestDonation(donationId) {
    const quantityInput = prompt("Enter the quantity you need:");
    if (quantityInput === null) return;

    const quantity = Number(quantityInput);

    if (!Number.isFinite(quantity) || quantity <= 0) {
        alert("Enter a valid quantity.");
        return;
    }

    const message = prompt("Enter an optional message:") || "";

    try {
        await apiRequest("/requests/", {
            method: "POST",
            body: JSON.stringify({
                donation_id: Number(donationId),
                requested_quantity: quantity,
                message: message
            })
        });

        showMessage("Food request submitted successfully!");
        await loadRequests();

    } catch (error) {
        alert(error.message);
    }
}

// My requests
async function loadRequests() {
    const table = document.getElementById("requestsTable");
    table.innerHTML =
        '<tr><td colspan="5" class="text-center">Loading...</td></tr>';

    try {
        const data = await apiRequest("/requests/my");
        const requests = getList(data, "requests");

        document.getElementById("totalRequests").textContent =
            requests.length;

        document.getElementById("acceptedRequests").textContent =
            requests.filter(r => r.status === "ACCEPTED").length;

        document.getElementById("pendingRequests").textContent =
            requests.filter(r => r.status === "PENDING").length;

        if (!requests.length) {
            table.innerHTML = `
                <tr><td colspan="5" class="text-center text-muted">
                    No requests yet.
                </td></tr>`;
            return;
        }

        table.innerHTML = requests.map(r => `
            <tr>
                <td>#${escapeHTML(r.id)}</td>
                <td>${escapeHTML(r.donation_title || r.donation_id)}</td>
                <td>${escapeHTML(r.requested_quantity)}</td>
                <td>${escapeHTML(r.status)}</td>
                <td>${escapeHTML(r.created_at || "-")}</td>
            </tr>
        `).join("");

    } catch (error) {
        table.innerHTML = `
            <tr><td colspan="5" class="text-danger">
                ${escapeHTML(error.message)}
            </td></tr>`;
    }
}

// NGO profile
async function loadProfile() {
    try {
        const data = await apiRequest("/ngo/profile");
        const profile = data.profile || data;

        const fields = [
            "organization_name", "registration_number",
            "beneficiary_count", "storage_capacity_description",
            "address", "city", "state", "postal_code",
            "latitude", "longitude"
        ];

        fields.forEach(field => {
            const input = document.getElementById(field);
            if (input && profile[field] != null) {
                input.value = profile[field];
            }
        });

    } catch (error) {
        console.log("Profile:", error.message);
    }
}

// Save NGO profile
document.getElementById("profileForm").addEventListener(
    "submit", async function(event) {
        event.preventDefault();

        const button = document.getElementById("profileButton");
        button.disabled = true;
        button.textContent = "Saving...";

        const payload = {
            organization_name: document.getElementById("organization_name").value.trim(),
            registration_number: document.getElementById("registration_number").value.trim(),
            beneficiary_count: Number(document.getElementById("beneficiary_count").value),
            storage_capacity_description: document.getElementById("storage_capacity_description").value.trim() || null,
            address: document.getElementById("address").value.trim(),
            city: document.getElementById("city").value.trim(),
            state: document.getElementById("state").value.trim(),
            postal_code: document.getElementById("postal_code").value.trim(),
            latitude: document.getElementById("latitude").value
                ? Number(document.getElementById("latitude").value) : null,
            longitude: document.getElementById("longitude").value
                ? Number(document.getElementById("longitude").value) : null
        };

        try {
            await apiRequest("/ngo/profile", {
                method: "POST",
                body: JSON.stringify(payload)
            });
            showMessage("NGO profile saved successfully!");

        } catch (error) {
            showMessage(error.message, "danger");

        } finally {
            button.disabled = false;
            button.textContent = "Save NGO Profile";
        }
    }
);

// Notifications
async function loadNotifications() {
    const container = document.getElementById("notificationsList");
    container.innerHTML = '<p class="text-muted">Loading...</p>';

    try {
        const data = await apiRequest("/notifications/my");
        const notifications = getList(data, "notifications");

        if (!notifications.length) {
            container.innerHTML =
                '<p class="text-muted">No notifications available.</p>';
            return;
        }

        container.innerHTML = notifications.map(n => `
            <div class="border rounded p-3 mb-2">
                <strong>${escapeHTML(n.title)}</strong>
                <p class="mb-1">${escapeHTML(n.message)}</p>
                <small class="text-muted">${escapeHTML(n.created_at || "")}</small>
                ${n.is_read ? "" : `
                    <button class="btn btn-sm btn-outline-success"
                        onclick="markNotificationRead(${Number(n.id)})">
                        Mark Read
                    </button>`}
            </div>
        `).join("");

    } catch (error) {
        container.innerHTML =
            `<p class="text-danger">${escapeHTML(error.message)}</p>`;
    }
}

async function markNotificationRead(id) {
    try {
        await apiRequest(`/notifications/${id}/read`, {
            method: "PATCH"
        });
        await loadNotifications();
    } catch (error) {
        alert(error.message);
    }
}

// Initial loading
document.addEventListener("DOMContentLoaded", async function() {
    if (!getToken()) {
        window.location.href = "login.html";
        return;
    }

    await Promise.all([
        loadDonations(),
        loadRequests(),
        loadProfile(),
        loadNotifications()
    ]);
});
