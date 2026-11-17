
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.donor import router as donor_router
from app.routes.donations import router as donations_router
from app.routes.ngo import router as ngo_router
from app.routes.requests import router as requests_router
from app.routes.volunteer import router as volunteer_router
from app.routes.assignments import router as assignments_router
from app.routes.safety import router as safety_router
from app.routes.notifications import router as notifications_router

app = FastAPI(
    title="FoodBridge API",
    description="Food Donation and Waste Reduction Platform",
    version="1.0.0",
)

# Allow frontend to communicate with backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to FoodBridge API",
        "status": "Running",
    }


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(donor_router)
app.include_router(donations_router)
app.include_router(ngo_router)
app.include_router(requests_router)
app.include_router(volunteer_router)
app.include_router(assignments_router)
app.include_router(safety_router)
app.include_router(notifications_router)
