import json
import re
import datetime
from typing import Dict, Any
from backend.app.tools.appointment_tools import (
    book_appointment, cancel_appointment, reschedule_appointment, check_availability
)
from backend.app.tools.doctor_tools import search_doctors
from backend.app.config import settings


class AppointmentAgent:
    name = "Appointment Agent"
    description = "Executes transaction-safe appointment bookings, cancellations, and reschedulings."

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        patient_id = context.get("patient_id", 1)
        msg_lower = message.lower()
        tools_called = []
        tool_results = {}

        # 1. Check for Cancellation Intent
        cancel_match = re.search(r"\b(cancel)\b.*?(?:appointment\s*#?|#)?(\d+)", msg_lower)
        if cancel_match:
            appt_id = int(cancel_match.group(2))
            tools_called.append("cancel_appointment")
            tool_results["cancellation"] = cancel_appointment(appt_id, patient_id=patient_id)
            res = tool_results["cancellation"]
            if res.get("status") == "success":
                msg = f"✅ **Appointment #{appt_id} Successfully Cancelled**.\n\nA confirmation notice has been sent to your email."
            else:
                msg = f"❌ **Unable to Cancel Appointment**: {res.get('message')}"
            return {
                "agent": self.name,
                "tools_called": tools_called,
                "tool_results": tool_results,
                "response": msg
            }

        # 2. Check for Reschedule Intent
        reschedule_match = re.search(r"\b(reschedule)\b.*?(?:appointment\s*#?|#)?(\d+)", msg_lower)
        date_match = re.search(r"\b(202\d-\d{2}-\d{2})\b", message)
        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", message)

        if reschedule_match and date_match and time_match:
            appt_id = int(reschedule_match.group(2))
            new_date = date_match.group(1)
            new_time = time_match.group(1)
            if len(new_time.split(":")[0]) == 1:
                new_time = f"0{new_time}"

            tools_called.append("reschedule_appointment")
            tool_results["reschedule"] = reschedule_appointment(
                appointment_id=appt_id,
                new_date_str=new_date,
                new_time_str=new_time,
                patient_id=patient_id
            )
            res = tool_results["reschedule"]
            if res.get("status") == "success":
                msg = f"✅ **Appointment #{appt_id} Rescheduled** to **{new_date}** at **{new_time}**."
            else:
                msg = f"❌ **Could not reschedule**: {res.get('message')}"
            return {
                "agent": self.name,
                "tools_called": tools_called,
                "tool_results": tool_results,
                "response": msg
            }

        # 3. Check for Booking Intent
        if "book" in msg_lower or "schedule" in msg_lower or "reserve" in msg_lower:
            # Extract doctor ID or search by name
            doc_id = None
            doc_match = re.search(r"(?:doctor\s*|dr\.?\s*)#?(\d+)", msg_lower)
            if doc_match:
                doc_id = int(doc_match.group(1))
            else:
                # Check doctor names
                for name_sub, d_id in [("mitchell", 1), ("chen", 2), ("vance", 3), ("wilson", 4), ("patel", 5)]:
                    if name_sub in msg_lower:
                        doc_id = d_id
                        break

            # Date extraction
            target_date = None
            if date_match:
                target_date = date_match.group(1)
            elif "tomorrow" in msg_lower:
                target_date = str(datetime.date.today() + datetime.timedelta(days=1))
            
            # Time extraction
            target_time = None
            if time_match:
                target_time = time_match.group(1)
                if len(target_time.split(":")[0]) == 1:
                    target_time = f"0{target_time}"

            # If we have all required booking information
            if doc_id and target_date and target_time:
                tools_called.append("book_appointment")
                reason = "Consultation"
                if "reason" in msg_lower:
                    reason = message.split("reason")[-1].strip(": ")
                
                tool_results["booking"] = book_appointment(
                    patient_id=patient_id,
                    doctor_id=doc_id,
                    date_str=target_date,
                    time_str=target_time,
                    reason=reason
                )

                res = tool_results["booking"]
                if res.get("status") == "success":
                    b = res["booking"]
                    msg = (
                        f"🎉 **Appointment Successfully Confirmed!**\n\n"
                        f"- **Appointment ID**: `#{b['appointment_id']}`\n"
                        f"- **Doctor**: {b['doctor_name']}\n"
                        f"- **Date**: {b['date']}\n"
                        f"- **Time**: {b['time']}\n"
                        f"- **Reason**: {b['reason_for_visit']}\n\n"
                        f"✉️ A confirmation email and notification have been dispatched."
                    )
                elif res.get("status") == "conflict":
                    msg = f"⚠️ **Slot Unavailable**: {res.get('message')}\nWould you like me to check other available slots for Dr. #{doc_id} on {target_date}?"
                else:
                    msg = f"❌ **Booking Failed**: {res.get('message')}"

                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": msg
                }

            elif doc_id and target_date:
                # We have doctor and date, but need slot selection!
                tools_called.append("check_availability")
                slots_data = check_availability(doc_id, target_date)
                tool_results["availability"] = slots_data
                slots = slots_data.get("slots", [])
                if slots:
                    msg = (
                        f"Here are the available slots for Doctor #{doc_id} on **{target_date}**:\n\n"
                        f"`" + "`, `".join(slots) + "`\n\n"
                        f"Which time would you like to book? For example, reply:\n"
                        f"*\"Book with Doctor {doc_id} on {target_date} at {slots[0]}\"*"
                    )
                else:
                    msg = f"There are no available slots for Doctor #{doc_id} on {target_date}. Please choose another weekday."
                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": msg
                }
            else:
                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": (
                        "To book an appointment, please provide:\n"
                        "1. Doctor Name or Specialty (e.g., Dr. Mitchell, Cardiologist)\n"
                        "2. Preferred Date (YYYY-MM-DD)\n"
                        "3. Preferred Time Slot (e.g. 10:00)\n\n"
                        "Example: *\"Book appointment with Dr. Mitchell on 2026-09-17 at 10:30\"*"
                    )
                }

        # Default query handler
        return {
            "agent": self.name,
            "tools_called": [],
            "tool_results": {},
            "response": "I can help you book, reschedule, or cancel hospital appointments. What would you like to do?"
        }
