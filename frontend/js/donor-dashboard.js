
const API_BASE_URL = "http://127.0.0.1:8000";

function getToken() {
    return localStorage.getItem("foodbridge_token");
}

function logout() {
    localStorage.removeItem("foodbridge_token");
    localStorage.removeItem("foodbridge_role");
    localStorage.removeItem("foodbridge_user_id");
    localStorage.removeItem("foodbridge_email");
    window.location.href = "login.html";
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`
    };
}

function showMessage(elementId, message, type = "success") {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="alert alert-${type} mt-3">
                ${escapeHTML(message)}
            </div>
        `;
    }
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function convertToISO(value) {
    if (!value) {
        throw new Error("Please enter preparation and expiry times.");
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        throw new Error("Please enter valid date and time values.");
    }

    return date.toISOString();
}

// Common API helper
async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            ...authHeaders(),
            ...options.headers
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = Array.isArray(data.detail)
            ? data.detail.map(item => item.msg).join(", ")
            : data.detail;

        throw new Error(detail || "Something went wrong.");
    }

    return data;
}

// Load donor donations
async function loadDonations() {
    const table = document.getElementById("donationTable");

    try {
        const data = await apiRequest("/donations/my");

        const donations = Array.isArray(data)
            ? data
            : (data.donations || []);

        document.getElementById("totalDonations").textContent =
            donations.length;

        document.getElementById("availableDonations").textContent =
            donations.filter(d => d.status === "AVAILABLE").length;

        document.getElementById("requestedDonations").textContent =
            donations.filter(d =>
                ["REQUESTED", "ACCEPTED"].includes(d.status)
            ).length;

        document.getElementById("deliveredDonations").textContent =
            donations.filter(d => d.status === "DELIVERED").length;

        if (!donations.length) {
            table.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">
                        No donations yet.
                    </td>
                </tr>`;
            return;
        }

        table.innerHTML = donations.map(d => `
            <tr>
                <td>${escapeHTML(d.title)}</td>
                <td>${escapeHTML(d.quantity)} ${escapeHTML(d.unit)}</td>
                <td>${escapeHTML(d.pickup_city)}</td>
                <td>
                    <span class="badge bg-success">
                        ${escapeHTML(d.status)}
                    </span>
                </td>
                <td>
                    ${d.expires_at
                        ? new Date(d.expires_at).toLocaleString()
                        : "-"}
                </td>
            </tr>
        `).join("");

    } catch (error) {
        table.innerHTML = `
            <tr>
                <td colspan="5" class="text-danger">
                    ${escapeHTML(error.message)}
                </td>
            </tr>`;
    }
}

// Submit new donation
document.getElementById("donationForm").addEventListener(
    "submit",
    async function(event) {
        event.preventDefault();

        const button = document.getElementById("donationButton");
        button.disabled = true;
        button.textContent = "Submitting...";

        try {
            const preparedValue =
                document.getElementById("prepared_at").value;

            const expiresValue =
                document.getElementById("expires_at").value;

            const preparedDate = new Date(preparedValue);
            const expiresDate = new Date(expiresValue);

            if (
                Number.isNaN(preparedDate.getTime()) ||
                Number.isNaN(expiresDate.getTime())
            ) {
                throw new Error("Please enter valid preparation and expiry times.");
            }

            if (expiresDate <= preparedDate) {
                throw new Error(
                    "Expiry time must be after preparation time."
                );
            }

            const donation = {
                category_id: Number(
                    document.getElementById("category_id").value
                ),
                title: document.getElementById("title").value.trim(),
                description: document.getElementById("description").value.trim(),
                food_type: document.getElementById("food_type").value,
                quantity: Number(
                    document.getElementById("quantity").value
                ),
                unit: document.getElementById("unit").value.trim(),
                prepared_at: convertToISO(preparedValue),
                expires_at: convertToISO(expiresValue),
                storage_instructions:
                    document.getElementById("storage_instructions").value.trim(),
                packaging_type:
                    document.getElementById("packaging_type").value.trim(),
                allergen_info:
                    document.getElementById("allergen_info").value.trim() || null,
                pickup_address:
                    document.getElementById("pickup_address").value.trim(),
                pickup_city:
                    document.getElementById("pickup_city").value.trim(),
                pickup_lat:
                    document.getElementById("pickup_lat").value
                        ? Number(document.getElementById("pickup_lat").value)
                        : null,
                pickup_lng:
                    document.getElementById("pickup_lng").value
                        ? Number(document.getElementById("pickup_lng").value)
                        : null,
                image_url:
                    document.getElementById("image_url").value.trim() || null
            };

            await apiRequest("/donations/", {
                method: "POST",
                body: JSON.stringify(donation)
            });

            showMessage(
                "donationMessage",
                "Donation submitted successfully!",
                "success"
            );

            document.getElementById("donationForm").reset();

            await loadDonations();

        } catch (error) {
            showMessage(
                "donationMessage",
                error.message,
                "danger"
            );
        } finally {
            button.disabled = false;
            button.innerHTML =
                '<i class="bi bi-plus-circle"></i> Submit Donation';
        }
    }
);

// Load incoming NGO requests
async function loadRequests() {
    const container = document.getElementById("requestList");

    try {
        const data = await apiRequest("/requests/incoming");

        const requests = Array.isArray(data)
            ? data
            : (data.requests || []);

        if (!requests.length) {
            container.innerHTML =
                "<p class='text-muted'>No incoming requests yet.</p>";
            return;
        }

        container.innerHTML = requests.map(r => `
            <div class="border rounded p-3 mb-3">
                <div class="d-flex justify-content-between flex-wrap gap-2">
                    <strong>Request #${Number(r.id)}</strong>
                    <span class="badge ${
                        r.status === "ACCEPTED"
                            ? "bg-success"
                            : r.status === "REJECTED"
                            ? "bg-danger"
                            : "bg-warning text-dark"
                    }">
                        ${escapeHTML(r.status)}
                    </span>
                </div>

                <p class="mb-1 mt-2">
                    <strong>Food:</strong>
                    ${escapeHTML(r.donation_title || r.donation_id)}
                </p>

                <p class="mb-1">
                    <strong>Requested Quantity:</strong>
                    ${escapeHTML(r.requested_quantity)}
                    ${escapeHTML(r.donation_unit || "")}
                </p>

                <p class="mb-1">
                    <strong>NGO ID:</strong>
                    ${escapeHTML(r.ngo_id)}
                </p>

                <p class="mb-2">
                    <strong>Message:</strong>
                    ${escapeHTML(r.message || "No message")}
                </p>

                ${
                    r.status === "PENDING"
                        ? `
                            <button
                                class="btn btn-success btn-sm me-2"
                                onclick="respondToRequest(${Number(r.id)}, 'ACCEPT')">
                                <i class="bi bi-check-circle"></i>
                                Accept
                            </button>

                            <button
                                class="btn btn-danger btn-sm"
                                onclick="respondToRequest(${Number(r.id)}, 'REJECT')">
                                <i class="bi bi-x-circle"></i>
                                Reject
                            </button>
                        `
                        : `
                            <small class="text-muted">
                                This request has already been processed.
                            </small>
                        `
                }
            </div>
        `).join("");

    } catch (error) {
        container.innerHTML =
            `<p class="text-danger">${escapeHTML(error.message)}</p>`;
    }
}

// Accept or reject NGO request
async function respondToRequest(requestId, action) {
    let rejectionReason = null;

    if (action === "REJECT") {
        rejectionReason = prompt("Enter the reason for rejecting this request:");

        if (rejectionReason === null) return;

        if (!rejectionReason.trim()) {
            alert("Please enter a rejection reason.");
            return;
        }
    }

    const confirmation = confirm(
        action === "ACCEPT"
            ? "Are you sure you want to accept this food request?"
            : "Are you sure you want to reject this food request?"
    );

    if (!confirmation) return;

    try {
        await apiRequest(`/requests/${requestId}/respond`, {
            method: "PATCH",
            body: JSON.stringify({
                action: action,
                rejection_reason: rejectionReason
            })
        });

        alert(
            action === "ACCEPT"
                ? "Food request accepted successfully!"
                : "Food request rejected successfully!"
        );

        await Promise.all([
            loadRequests(),
            loadDonations(),
            loadNotifications()
        ]);

    } catch (error) {
        alert(error.message);
    }
}

// Load notifications
async function loadNotifications() {
    const container = document.getElementById("notificationList");

    try {
        const data = await apiRequest("/notifications/my");

        const notifications = data.notifications || [];

        if (!notifications.length) {
            container.innerHTML =
                "<p class='text-muted'>No notifications yet.</p>";
            return;
        }

        container.innerHTML = notifications.map(n => `
            <div class="border-bottom py-3">
                <strong>${escapeHTML(n.title)}</strong>
                <p class="mb-1">${escapeHTML(n.message)}</p>
                <small class="text-muted">
                    ${n.created_at
                        ? new Date(n.created_at).toLocaleString()
                        : ""}
                </small>

                ${n.is_read ? "" : `
                    <button
                        class="btn btn-sm btn-outline-success ms-2"
                        onclick="markNotificationRead(${Number(n.id)})">
                        Mark read
                    </button>
                `}
            </div>
        `).join("");

    } catch (error) {
        container.innerHTML =
            `<p class="text-danger">${escapeHTML(error.message)}</p>`;
    }
}

// Mark notification as read
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

// Initial dashboard loading
if (!getToken()) {
    window.location.href = "login.html";
} else {
    loadDonations();
    loadNotifications();
    loadRequests();
}
