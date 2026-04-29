from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.models import Doctor

DOCTORS = [
    {
        "id": 1,
        "name": "Dr. Sarah Mitchell",
        "specialization": "General Physician",
    },
    {
        "id": 2,
        "name": "Dr. James Patel",
        "specialization": "Cardiologist",
    },
    {
        "id": 3,
        "name": "Dr. Anika Sharma",
        "specialization": "Dermatologist",
    },
    {
        "id": 4,
        "name": "Dr. Robert Chen",
        "specialization": "Orthopedic Surgeon",
    },
    {
        "id": 5,
        "name": "Dr. Laura Nguyen",
        "specialization": "Pediatrician",
    },
]

# Hardcoded available slots per doctor (date → times)
AVAILABLE_SLOTS = {
    1: {
        "2025-02-10": ["09:00", "10:00", "11:00", "14:00", "15:00"],
        "2025-02-11": ["09:30", "11:00", "13:00", "16:00"],
        "2025-02-12": ["10:00", "11:30", "14:30"],
    },
    2: {
        "2025-02-10": ["08:30", "10:30", "13:30", "15:30"],
        "2025-02-11": ["09:00", "11:00", "14:00"],
        "2025-02-12": ["10:30", "12:00", "15:00", "16:30"],
    },
    3: {
        "2025-02-10": ["09:00", "10:00", "13:00", "14:00"],
        "2025-02-11": ["08:30", "11:30", "15:00"],
        "2025-02-12": ["09:30", "11:00", "13:30", "16:00"],
    },
    4: {
        "2025-02-10": ["10:00", "11:00", "15:00"],
        "2025-02-11": ["09:00", "10:30", "14:30", "16:00"],
        "2025-02-12": ["08:30", "11:00", "13:00", "15:30"],
    },
    5: {
        "2025-02-10": ["09:00", "10:30", "12:00", "14:00", "15:30"],
        "2025-02-11": ["09:30", "11:00", "13:30", "15:00"],
        "2025-02-12": ["10:00", "11:30", "14:00", "16:00"],
    },
}


async def seed_doctors():
    async with AsyncSessionLocal() as session:
        for doc_data in DOCTORS:
            result = await session.execute(select(Doctor).where(Doctor.id == doc_data["id"]))
            existing = result.scalar_one_or_none()
            if not existing:
                doctor = Doctor(**doc_data)
                session.add(doctor)
        await session.commit()
