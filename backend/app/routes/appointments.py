from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Appointment, Doctor, User

router = APIRouter(tags=["appointments"])


@router.get("/appointments/{phone_number}")
async def get_appointments(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all appointments for a patient identified by phone number."""
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    appt_result = await db.execute(
        select(Appointment).where(Appointment.user_id == user.id)
    )
    appointments = appt_result.scalars().all()

    output = []
    for appt in appointments:
        doc_result = await db.execute(select(Doctor).where(Doctor.id == appt.doctor_id))
        doctor = doc_result.scalar_one_or_none()
        output.append({
            "id": appt.id,
            "doctor": doctor.name if doctor else "Unknown",
            "specialization": doctor.specialization if doctor else "",
            "date": appt.date,
            "time": appt.time,
            "status": appt.status,
            "created_at": appt.created_at.isoformat() if appt.created_at else None,
        })

    return {"user": {"name": user.name, "phone": user.phone_number}, "appointments": output}


@router.get("/doctors")
async def get_doctors(db: AsyncSession = Depends(get_db)):
    """List all available doctors."""
    result = await db.execute(select(Doctor))
    doctors = result.scalars().all()
    return [{"id": d.id, "name": d.name, "specialization": d.specialization} for d in doctors]
