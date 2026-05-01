"""
LangChain tools for hospital appointment management.

Each tool:
  1. Performs database operations via SQLAlchemy async sessions
  2. Broadcasts a LiveKit data message to the room so the frontend can
     show real-time tool execution status
"""

import json
import logging
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import and_, select
from sqlalchemy.orm import sessionmaker

from app.db.database import SessionLocal
from app.db.seed import AVAILABLE_SLOTS, DOCTORS
from app.models.models import Appointment, Doctor, User
from app.services.sms_service import send_sms_confirmation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _broadcast(room, event_type: str, payload: dict):
    """Send a LiveKit data message to all participants in the room."""
    if room is None:
        return
    try:
        msg = json.dumps({"type": event_type, **payload}).encode()
        # Create a task to broadcast asynchronously
        import asyncio
        if asyncio.get_event_loop().is_running():
            asyncio.create_task(room.local_participant.publish_data(msg, reliable=True))
        else:
            # If no event loop is running, we can't broadcast - that's ok for now
            pass
    except Exception as exc:
        logger.warning("Failed to broadcast %s: %s", event_type, exc)


def _format_appointments(appointments: list) -> list[dict]:
    return [
        {
            "id": a.id,
            "doctor": a.doctor.name,
            "specialization": a.doctor.specialization,
            "date": a.date,
            "time": a.time,
            "status": a.status,
        }
        for a in appointments
    ]


# ---------------------------------------------------------------------------
# Session state — shared across tools within one conversation
# ---------------------------------------------------------------------------

class SessionState:
    """Holds per-conversation state (user identity + room reference)."""

    def __init__(self, session_id: str, room=None):
        self.session_id = session_id
        self.room = room
        self.user_phone: Optional[str] = None
        self.user_id: Optional[int] = None
        self.user_name: Optional[str] = None
        self.summary: Optional[dict] = None


# ---------------------------------------------------------------------------
# Tool factory — returns bound LangChain tools for a given session
# ---------------------------------------------------------------------------

def create_tools(state: SessionState):
    """Return all LangChain tools bound to the given session state."""

    @tool
    def identify_user(phone_number: str, name: str = "") -> str:
        """
        Identify or register a patient by their phone number.
        Call this first before any appointment operation.
        phone_number: patient's phone number (digits only, with country code)
        name: patient's full name (optional on first call, required if new)
        """
        _broadcast(state.room, "tool_start", {"tool": "identify_user", "label": "Identifying patient..."})

        with SessionLocal() as session:
            user = session.query(User).filter(User.phone_number == phone_number).first()

            if user:
                state.user_phone = user.phone_number
                state.user_id = user.id
                state.user_name = user.name
                _broadcast(state.room, "tool_complete", {
                    "tool": "identify_user",
                    "label": f"Welcome back, {user.name}",
                    "success": True,
                })
                return f"User identified: {user.name} (ID: {user.id})"
            else:
                if not name:
                    _broadcast(state.room, "tool_complete", {
                        "tool": "identify_user",
                        "label": "New patient — name required",
                        "success": False,
                    })
                    return "User not found. Please provide patient's full name to register."

                new_user = User(name=name, phone_number=phone_number)
                session.add(new_user)
                session.commit()
                session.refresh(new_user)

                state.user_phone = new_user.phone_number
                state.user_id = new_user.id
                state.user_name = new_user.name

                _broadcast(state.room, "tool_complete", {
                    "tool": "identify_user",
                    "label": f"Registered new patient: {name}",
                    "success": True,
                })
                return f"New patient registered: {name} (ID: {new_user.id})"

    @tool
    def fetch_slots(doctor_id: Optional[int] = None, specialization: Optional[str] = None) -> str:
        """
        Fetch available appointment slots.
        Optionally filter by doctor_id or specialization.
        Returns a list of doctors with their available dates and times.
        """
        _broadcast(state.room, "tool_start", {"tool": "fetch_slots", "label": "Fetching available slots..."})

        result = []
        for doc in DOCTORS:
            if doctor_id and doc["id"] != doctor_id:
                continue
            if specialization and specialization.lower() not in doc["specialization"].lower():
                continue

            slots = AVAILABLE_SLOTS.get(doc["id"], {})
            result.append({
                "doctor_id": doc["id"],
                "doctor": doc["name"],
                "specialization": doc["specialization"],
                "available_slots": slots,
            })

        _broadcast(state.room, "tool_complete", {
            "tool": "fetch_slots",
            "label": f"Found {len(result)} doctor(s) with slots",
            "success": True,
        })

        return json.dumps(result, indent=2)

    @tool
    def book_appointment(doctor_id: int, date: str, time: str) -> str:
        """
        Book an appointment for the identified patient.
        Requires identify_user to be called first.
        doctor_id: integer ID of the doctor
        date: appointment date in YYYY-MM-DD format
        time: appointment time in HH:MM format (24-hour)
        """
        if not state.user_id:
            return "Error: Patient not identified. Please call identify_user first."

        _broadcast(state.room, "tool_start", {"tool": "book_appointment", "label": "Booking appointment..."})

        with SessionLocal() as session:
            # Check for double booking
            conflict = session.query(Appointment).filter(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.date == date,
                    Appointment.time == time,
                    Appointment.status == "confirmed",
                )
            ).first()
            
            if conflict:
                _broadcast(state.room, "tool_complete", {
                    "tool": "book_appointment",
                    "label": "Slot already booked — conflict",
                    "success": False,
                })
                return f"Error: The slot on {date} at {time} is already booked. Please choose another time."

            # Fetch doctor info
            doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
            if not doctor:
                return f"Error: Doctor with ID {doctor_id} not found."

            appt = Appointment(
                user_id=state.user_id,
                doctor_id=doctor_id,
                date=date,
                time=time,
                status="confirmed",
            )
            session.add(appt)
            session.commit()
            session.refresh(appt)

        _broadcast(state.room, "tool_complete", {
            "tool": "book_appointment",
            "label": f"Appointment confirmed with {doctor.name} on {date} at {time}",
            "success": True,
            "data": {
                "appointment_id": appt.id,
                "doctor": doctor.name,
                "date": date,
                "time": time,
            },
        })

        return (
            f"Appointment booked successfully! "
            f"Confirmation ID: {appt.id}. "
            f"Doctor: {doctor.name} ({doctor.specialization}). "
            f"Date: {date} at {time}."
        )

    @tool
    def retrieve_appointments() -> str:
        """
        Retrieve all appointments for the currently identified patient.
        Requires identify_user to be called first.
        """
        if not state.user_id:
            return "Error: Patient not identified. Please call identify_user first."

        _broadcast(state.room, "tool_start", {
            "tool": "retrieve_appointments",
            "label": "Fetching your appointments...",
        })

        with SessionLocal() as session:
            appointments = session.query(Appointment).filter(
                Appointment.user_id == state.user_id
            ).all()

            formatted = []
            for a in appointments:
                doctor = session.query(Doctor).filter(Doctor.id == a.doctor_id).first()
                formatted.append({
                    "id": a.id,
                    "doctor": doctor.name if doctor else "Unknown",
                    "specialization": doctor.specialization if doctor else "",
                    "date": a.date,
                    "time": a.time,
                    "status": a.status,
                })

        _broadcast(state.room, "tool_complete", {
            "tool": "retrieve_appointments",
            "label": f"Found {len(formatted)} appointment(s)",
            "success": True,
            "data": {"appointments": formatted},
        })

        if not formatted:
            return "You have no appointments on record."

        return json.dumps(formatted, indent=2)

    @tool
    def cancel_appointment(appointment_id: int) -> str:
        """
        Cancel an appointment by its ID.
        appointment_id: the numeric ID of the appointment to cancel
        """
        if not state.user_id:
            return "Error: Patient not identified. Please call identify_user first."

        _broadcast(state.room, "tool_start", {
            "tool": "cancel_appointment",
            "label": f"Cancelling appointment #{appointment_id}...",
        })

        with SessionLocal() as session:
            appt = session.query(Appointment).filter(
                and_(Appointment.id == appointment_id, Appointment.user_id == state.user_id)
            ).first()

            if not appt:
                _broadcast(state.room, "tool_complete", {
                    "tool": "cancel_appointment",
                    "label": "Appointment not found",
                    "success": False,
                })
                return f"Error: Appointment {appointment_id} not found or does not belong to you."

            if appt.status == "cancelled":
                return f"Appointment {appointment_id} is already cancelled."

            appt.status = "cancelled"
            session.commit()

        _broadcast(state.room, "tool_complete", {
            "tool": "cancel_appointment",
            "label": f"Appointment #{appointment_id} cancelled",
            "success": True,
        })

        return f"Appointment {appointment_id} has been successfully cancelled."

    @tool
    def modify_appointment(appointment_id: int, new_date: str, new_time: str) -> str:
        """
        Reschedule an existing appointment to a new date and time.
        appointment_id: the numeric ID of the appointment to modify
        new_date: new date in YYYY-MM-DD format
        new_time: new time in HH:MM format (24-hour)
        """
        if not state.user_id:
            return "Error: Patient not identified. Please call identify_user first."

        _broadcast(state.room, "tool_start", {
            "tool": "modify_appointment",
            "label": f"Rescheduling appointment #{appointment_id}...",
        })

        with SessionLocal() as session:
            appt = session.query(Appointment).filter(
                and_(Appointment.id == appointment_id, Appointment.user_id == state.user_id)
            ).first()

            if not appt:
                _broadcast(state.room, "tool_complete", {
                    "tool": "modify_appointment",
                    "label": "Appointment not found",
                    "success": False,
                })
                return f"Error: Appointment {appointment_id} not found or does not belong to you."

            # Check new slot isn't already booked
            conflict = session.query(Appointment).filter(
                and_(
                    Appointment.doctor_id == appt.doctor_id,
                    Appointment.date == new_date,
                    Appointment.time == new_time,
                    Appointment.status == "confirmed",
                    Appointment.id != appointment_id,
                )
            ).first()
            
            if conflict:
                _broadcast(state.room, "tool_complete", {
                    "tool": "modify_appointment",
                    "label": "New slot has a conflict",
                    "success": False,
                })
                return f"Error: The new slot on {new_date} at {new_time} is already booked. Please choose another time."

            old_date, old_time = appt.date, appt.time
            appt.date = new_date
            appt.time = new_time
            session.commit()

        _broadcast(state.room, "tool_complete", {
            "tool": "modify_appointment",
            "label": f"Rescheduled from {old_date} {old_time} to {new_date} {new_time}",
            "success": True,
        })

        return (
            f"Appointment {appointment_id} rescheduled from {old_date} at {old_time} "
            f"to {new_date} at {new_time}."
        )

    @tool
    def end_conversation() -> str:
        """
        End the conversation and generate a structured summary.
        Call this when the patient says goodbye or the conversation is complete.
        """
        _broadcast(state.room, "tool_start", {
            "tool": "end_conversation",
            "label": "Generating conversation summary...",
        })

        # Simple summary for now
        summary = {
            "session_id": state.session_id,
            "user_name": state.user_name,
            "user_phone": state.user_phone,
            "ended_at": datetime.now().isoformat(),
        }

        state.summary = summary

        _broadcast(state.room, "summary", {
            "tool": "end_conversation",
            "label": "Summary ready",
            "success": True,
            "data": summary,
        })

        return "Thank you for visiting City General Hospital. Your conversation has been saved. Goodbye!"

    return [
        identify_user,
        fetch_slots,
        book_appointment,
        retrieve_appointments,
        cancel_appointment,
        modify_appointment,
        end_conversation,
    ]
