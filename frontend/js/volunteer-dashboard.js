
const API_BASE_URL = "http://127.0.0.1:8000";

const getToken = () => localStorage.getItem("foodbridge_token");

document.getElementById("currentYear").textContent =
    new Date().getFullYear();

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}

async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${getToken()}`,
            ...options.headers
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
            ? detail.map(item => item.msg).join(", ")
            : detail;

        throw new Error(message || "Something went wrong.");
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
    document.getElementById("message").innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show">
            ${escapeHTML(message)}
            <button type="button" class="btn-close"
                data-bs-dismiss="alert"></button>
        </div>
    `;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function logout() {
    localStorage.removeItem("foodbridge_token");
    localStorage.removeItem("foodbridge_role");
    localStorage.removeItem("foodbridge_user_id");
    window.location.href = "login.html";
}

// Load assignments
async function loadAssignments() {
    const container = document.getElementById("assignmentsList");
    container.innerHTML = '<p class="text-muted">Loading assignments...</p>';

    try {
        const data = await apiRequest("/assignments/my");
        const assignments = getList(data, "assignments");

        document.getElementById("totalAssignments").textContent =
            assignments.length;

        document.getElementById("assignedCount").textContent =
            assignments.filter(item =>
                ["ASSIGNED", "ACCEPTED"].includes(item.status)
            ).length;

        document.getElementById("transitCount").textContent =
            assignments.filter(item => item.status === "IN_TRANSIT").length;

        document.getElementById("deliveredCount").textContent =
            assignments.filter(item => item.status === "DELIVERED").length;

        if (!assignments.length) {
            container.innerHTML =
                '<p class="text-muted">No assignments available yet.</p>';
            return;
        }

        container.innerHTML = assignments.map(item => {
            const status = item.status || "ASSIGNED";

            return `
                <div class="dashboard-card mb-3">
                    <div class="d-flex justify-content-between flex-wrap gap-2">
                        <h5 class="fw-bold">Assignment #${escapeHTML(item.id)}</h5>
                        <span class="badge ${
                            status === "DELIVERED"
                                ? "text-bg-success"
                                : status === "CANCELLED"
                                ? "text-bg-danger"
                                : "text-bg-warning"
                        }">${escapeHTML(status)}</span>
                    </div>

                    <hr>

                    <p><strong>Donation:</strong>
                        ${escapeHTML(item.donation_title || item.donation_id || "-")}
                    </p>

                    <p><strong>Pickup Address:</strong>
                        ${escapeHTML(item.pickup_address || "-")}
                    </p>

                    <p><strong>City:</strong>
                        ${escapeHTML(item.pickup_city || "-")}
                    </p>

                    <div class="row g-2 mt-2">
                        ${
                            status === "ASSIGNED"
                                ? `<div class="col-md-6">
                                    <button class="btn btn-food w-100"
                                        onclick="updateAssignment(${Number(item.id)}, 'ACCEPT')">
                                        Accept Assignment
                                    </button>
                                </div>`
                                : ""
                        }

                        ${
                            status === "ACCEPTED"
                                ? `<div class="col-md-6">
                                    <button class="btn btn-food w-100"
                                        onclick="verifyPickup(${Number(item.id)})">
                                        Verify Pickup OTP
                                    </button>
                                </div>`
                                : ""
                        }

                        ${
                            status === "COLLECTED"
                                ? `<div class="col-md-6">
                                    <button class="btn btn-food w-100"
                                        onclick="updateAssignment(${Number(item.id)}, 'IN_TRANSIT')">
                                        Start Delivery
                                    </button>
                                </div>`
                                : ""
                        }

                        ${
                            status === "IN_TRANSIT"
                                ? `<div class="col-md-6">
                                    <button class="btn btn-food w-100"
                                        onclick="verifyDelivery(${Number(item.id)})">
                                        Verify Delivery OTP
                                    </button>
                                </div>`
                                : ""
                        }
                    </div>
                </div>
            `;
        }).join("");

    } catch (error) {
        container.innerHTML =
            `<p class="text-danger">${escapeHTML(error.message)}</p>`;
    }
}

// Update assignment status
async function updateAssignment(assignmentId, action) {
    if (!confirm("Are you sure you want to continue?")) return;

    try {
        await apiRequest(`/assignments/${assignmentId}/status`, {
            method: "PATCH",
            body: JSON.stringify({ action: action })
        });

        showMessage("Assignment status updated successfully!");
        await loadAssignments();

    } catch (error) {
        alert(error.message);
    }
}

// Verify pickup OTP
async function verifyPickup(assignmentId) {
    const otp = prompt("Enter the 6-digit pickup OTP:");

    if (otp === null) return;

    if (!/^\d{6}$/.test(otp.trim())) {
        alert("Please enter a valid 6-digit OTP.");
        return;
    }

    try {
        await apiRequest(`/assignments/${assignmentId}/status`, {
            method: "PATCH",
            body: JSON.stringify({
                action: "PICKUP",
                otp: otp.trim()
            })
        });

        showMessage("Pickup verified successfully!");
        await loadAssignments();

    } catch (error) {
        alert(error.message);
    }
}

// Verify delivery OTP
async function verifyDelivery(assignmentId) {
    const otp = prompt("Enter the 6-digit delivery OTP:");

    if (otp === null) return;

    if (!/^\d{6}$/.test(otp.trim())) {
        alert("Please enter a valid 6-digit OTP.");
        return;
    }

    try {
        await apiRequest(`/assignments/${assignmentId}/status`, {
            method: "PATCH",
            body: JSON.stringify({
                action: "DELIVER",
                otp: otp.trim()
            })
        });

        showMessage("Food delivery completed successfully!");
        await loadAssignments();

    } catch (error) {
        alert(error.message);
    }
}

// Load volunteer profile
async function loadProfile() {
    try {
        const data = await apiRequest("/volunteer/profile");
        const profile = data.profile || data;

        ["vehicle_type", "vehicle_number", "city", "emergency_contact"]
            .forEach(field => {
                const input = document.getElementById(field);
                if (input && profile[field] != null) {
                    input.value = profile[field];
                }
            });

        const toggle = document.getElementById("availabilityToggle");
        toggle.checked = Boolean(profile.is_available);
        updateAvailabilityLabel();

    } catch (error) {
        console.log("Volunteer profile:", error.message);
    }
}

// Save volunteer profile
document.getElementById("profileForm").addEventListener("submit", async event => {
    event.preventDefault();

    const button = document.getElementById("profileButton");
    button.disabled = true;
    button.textContent = "Saving...";

    const payload = {
        vehicle_type: document.getElementById("vehicle_type").value,
        vehicle_number: document.getElementById("vehicle_number").value.trim() || null,
        city: document.getElementById("city").value.trim(),
        emergency_contact: document.getElementById("emergency_contact").value.trim()
    };

    try {
        await apiRequest("/volunteer/profile", {
            method: "POST",
            body: JSON.stringify(payload)
        });

        showMessage("Volunteer profile saved successfully!");

    } catch (error) {
        showMessage(error.message, "danger");

    } finally {
        button.disabled = false;
        button.textContent = "Save Volunteer Profile";
    }
});

// Availability
function updateAvailabilityLabel() {
    const toggle = document.getElementById("availabilityToggle");
    document.getElementById("availabilityLabel").textContent =
        toggle.checked ? "Available" : "Unavailable";
}

document.getElementById("availabilityToggle").addEventListener("change", async function () {
    const toggle = this;
    const previousValue = !toggle.checked;

    try {
        await apiRequest("/volunteer/availability", {
            method: "PATCH",
            body: JSON.stringify({ is_available: toggle.checked })
        });

        updateAvailabilityLabel();
        showMessage(toggle.checked
            ? "You are now available for assignments."
            : "You are now unavailable for assignments.");

    } catch (error) {
        toggle.checked = previousValue;
        updateAvailabilityLabel();
        alert(error.message);
    }
});

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

        container.innerHTML = notifications.map(item => `
            <div class="border rounded p-3 mb-2 ${item.is_read ? "" : "bg-light"}">
                <div class="d-flex justify-content-between gap-2">
                    <div>
                        <strong>${escapeHTML(item.title)}</strong>
                        <p class="mb-1">${escapeHTML(item.message)}</p>
                        <small class="text-muted">${escapeHTML(item.created_at || "")}</small>
                    </div>
                    ${
                        item.is_read
                            ? '<span class="badge text-bg-secondary">Read</span>'
                            : `<button class="btn btn-sm btn-outline-success"
                                onclick="markNotificationRead(${Number(item.id)})">
                                Mark Read
                              </button>`
                    }
                </div>
            </div>
        `).join("");

    } catch (error) {
        container.innerHTML =
            `<p class="text-danger">${escapeHTML(error.message)}</p>`;
    }
}

async function markNotificationRead(notificationId) {
    try {
        await apiRequest(`/notifications/${notificationId}/read`, {
            method: "PATCH"
        });
        await loadNotifications();

    } catch (error) {
        alert(error.message);
    }
}

// Initial loading
document.addEventListener("DOMContentLoaded", async () => {
    if (!getToken()) {
        window.location.href = "login.html";
        return;
    }

    await Promise.all([
        loadAssignments(),
        loadProfile(),
        loadNotifications()
    ]);
});

