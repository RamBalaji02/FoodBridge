
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


// API REQUEST FUNCTION

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


// GET LIST DATA

function getList(data, key) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.[key])) return data[key];
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.users)) return data.users;
    if (Array.isArray(data?.ngos)) return data.ngos;

    return [];
}


// DISPLAY MESSAGE

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


// LOGOUT

function logout() {
    localStorage.removeItem("foodbridge_token");
    localStorage.removeItem("foodbridge_role");
    localStorage.removeItem("foodbridge_user_id");
    localStorage.removeItem("foodbridge_email");

    window.location.href = "login.html";
}


// LOAD ADMIN DASHBOARD STATISTICS

async function loadDashboard() {
    try {
        const data = await apiRequest("/admin/dashboard");

        // Backend response uses nested objects.
        document.getElementById("totalUsers").textContent =
            data.users?.total ?? 0;

        document.getElementById("pendingUsers").textContent =
            data.users?.pending_approvals ?? 0;

        document.getElementById("pendingNGOs").textContent =
            data.ngos?.pending_verifications ?? 0;

        document.getElementById("totalDonations").textContent =
            data.donations?.total ?? 0;

    } catch (error) {
        showMessage(
            "Could not load dashboard statistics: " + error.message,
            "warning"
        );
    }
}


// LOAD PENDING USERS

async function loadPendingUsers() {
    const table = document.getElementById("usersTable");

    table.innerHTML = `
        <tr>
            <td colspan="6" class="text-center">Loading users...</td>
        </tr>
    `;

    try {
        const data = await apiRequest("/admin/pending-users");
        const users = getList(data, "users");

        document.getElementById("pendingUsers").textContent =
            data.total ?? users.length;

        if (users.length === 0) {
            table.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        No pending users.
                    </td>
                </tr>
            `;
            return;
        }

        table.innerHTML = users.map(user => `
            <tr>
                <td>${escapeHTML(user.id)}</td>
                <td>${escapeHTML(user.full_name)}</td>
                <td>${escapeHTML(user.email)}</td>
                <td>${escapeHTML(user.phone || "-")}</td>
                <td>
                    <span class="badge text-bg-info">
                        ${escapeHTML(user.role)}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-success mb-1"
                        onclick="approveUser(${Number(user.id)})">
                        Approve
                    </button>

                    <button class="btn btn-sm btn-danger mb-1"
                        onclick="rejectUser(${Number(user.id)})">
                        Reject
                    </button>
                </td>
            </tr>
        `).join("");

    } catch (error) {
        table.innerHTML = `
            <tr>
                <td colspan="6" class="text-danger">
                    ${escapeHTML(error.message)}
                </td>
            </tr>
        `;
    }
}


// APPROVE USER

async function approveUser(userId) {
    if (!confirm("Are you sure you want to approve this user?")) {
        return;
    }

    try {
        await apiRequest(`/admin/users/${userId}/approve`, {
            method: "PATCH"
        });

        showMessage("User approved successfully!");

        await Promise.all([
            loadPendingUsers(),
            loadDashboard()
        ]);

    } catch (error) {
        alert(error.message);
    }
}


// REJECT USER

async function rejectUser(userId) {
    if (!confirm("Are you sure you want to reject this user?")) {
        return;
    }

    try {
        await apiRequest(`/admin/users/${userId}/reject`, {
            method: "PATCH"
        });

        showMessage("User rejected successfully.", "warning");

        await Promise.all([
            loadPendingUsers(),
            loadDashboard()
        ]);

    } catch (error) {
        alert(error.message);
    }
}


// LOAD PENDING NGOS

async function loadPendingNGOs() {
    const table = document.getElementById("ngosTable");

    table.innerHTML = `
        <tr>
            <td colspan="6" class="text-center">Loading NGOs...</td>
        </tr>
    `;

    try {
        const data = await apiRequest("/admin/pending-ngos");
        const ngos = getList(data, "ngos");

        document.getElementById("pendingNGOs").textContent =
            data.total ?? ngos.length;

        if (ngos.length === 0) {
            table.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        No pending NGO verifications.
                    </td>
                </tr>
            `;
            return;
        }

        table.innerHTML = ngos.map(ngo => `
            <tr>
                <td>${escapeHTML(ngo.id)}</td>
                <td>${escapeHTML(ngo.organization_name)}</td>
                <td>${escapeHTML(ngo.registration_number)}</td>
                <td>${escapeHTML(ngo.city)}</td>
                <td>${escapeHTML(ngo.beneficiary_count)}</td>
                <td>
                    <button class="btn btn-sm btn-success mb-1"
                        onclick="approveNGO(${Number(ngo.id)})">
                        Approve
                    </button>

                    <button class="btn btn-sm btn-danger mb-1"
                        onclick="rejectNGO(${Number(ngo.id)})">
                        Reject
                    </button>
                </td>
            </tr>
        `).join("");

    } catch (error) {
        table.innerHTML = `
            <tr>
                <td colspan="6" class="text-danger">
                    ${escapeHTML(error.message)}
                </td>
            </tr>
        `;
    }
}


// APPROVE NGO

async function approveNGO(ngoId) {
    if (!confirm("Are you sure you want to approve this NGO?")) {
        return;
    }

    try {
        await apiRequest(`/admin/ngos/${ngoId}/approve`, {
            method: "PATCH"
        });

        showMessage("NGO approved successfully!");

        await Promise.all([
            loadPendingNGOs(),
            loadDashboard()
        ]);

    } catch (error) {
        alert(error.message);
    }
}


// REJECT NGO

async function rejectNGO(ngoId) {
    if (!confirm("Are you sure you want to reject this NGO?")) {
        return;
    }

    try {
        await apiRequest(`/admin/ngos/${ngoId}/reject`, {
            method: "PATCH"
        });

        showMessage("NGO rejected successfully.", "warning");

        await Promise.all([
            loadPendingNGOs(),
            loadDashboard()
        ]);

    } catch (error) {
        alert(error.message);
    }
}


// ASSIGN VOLUNTEER

document.getElementById("assignmentForm").addEventListener(
    "submit",
    async function (event) {
        event.preventDefault();

        const button = document.getElementById("assignmentButton");
        const resultBox = document.getElementById("assignmentResult");

        const requestId = Number(
            document.getElementById("request_id").value
        );

        const volunteerId = Number(
            document.getElementById("volunteer_id").value
        );

        if (requestId <= 0 || volunteerId <= 0) {
            showMessage(
                "Enter valid request and volunteer IDs.",
                "danger"
            );
            return;
        }

        button.disabled = true;
        button.textContent = "Assigning...";

        resultBox.innerHTML = "";

        try {
            const data = await apiRequest("/assignments/assign", {
                method: "POST",
                body: JSON.stringify({
                    request_id: requestId,
                    volunteer_id: volunteerId
                })
            });

            const assignment = data.assignment || data;

            resultBox.innerHTML = `
                <div class="alert alert-success">
                    <h5>Volunteer assigned successfully!</h5>

                    <p class="mb-1">
                        <strong>Assignment ID:</strong>
                        ${escapeHTML(
                            assignment.id ?? assignment.assignment_id ?? "-"
                        )}
                    </p>

                    ${
                        assignment.pickup_otp
                            ? `<p class="mb-1">
                                <strong>Pickup OTP:</strong>
                                ${escapeHTML(assignment.pickup_otp)}
                            </p>`
                            : ""
                    }

                    ${
                        assignment.delivery_otp
                            ? `<p class="mb-0">
                                <strong>Delivery OTP:</strong>
                                ${escapeHTML(assignment.delivery_otp)}
                            </p>`
                            : ""
                    }
                </div>
            `;

            showMessage("Volunteer assignment completed!");

            document.getElementById("assignmentForm").reset();

        } catch (error) {
            resultBox.innerHTML = `
                <div class="alert alert-danger">
                    ${escapeHTML(error.message)}
                </div>
            `;

        } finally {
            button.disabled = false;
            button.textContent = "Assign Volunteer";
        }
    }
);


// INITIAL PAGE LOADING

document.addEventListener("DOMContentLoaded", async function () {

    if (!getToken()) {
        window.location.href = "login.html";
        return;
    }

    await Promise.all([
        loadDashboard(),
        loadPendingUsers(),
        loadPendingNGOs()
    ]);
});
