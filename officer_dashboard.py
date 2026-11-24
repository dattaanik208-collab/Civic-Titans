
import json
from pathlib import Path
from datetime import datetime

import streamlit as st

from modules.authentication import require_role, get_current_user
from modules.complaint_manager import (
    get_officer_complaints,
    get_status_history,
    update_complaint_status,
    reject_complaint,
)
from modules.image_handler import get_image_path


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Officer Dashboard | CivicTrack",
    page_icon="👮",
    layout="wide",
)

require_role("officer")
user = get_current_user()

st.title("👮 Officer Dashboard")
st.write(f"Welcome, {user['full_name']}.")


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

ACTIVE_STATUSES = [
    "Assigned",
    "Under Review",
    "In Progress",
]


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def select_officer_view(view):

    st.session_state["officer_complaint_view"] = view


def get_complaint_images(complaint):

    image_paths = complaint.get("image_paths")

    if isinstance(image_paths, str):

        try:
            image_paths = json.loads(image_paths)

        except (json.JSONDecodeError, TypeError):
            image_paths = []

    if not isinstance(image_paths, list):
        image_paths = []

    if not image_paths and complaint.get("image_path"):
        image_paths = [complaint["image_path"]]

    return image_paths


def get_media_path(file_path):

    if not file_path:
        return None

    try:

        resolved = Path(file_path)

        if not resolved.is_absolute():
            resolved = Path.cwd() / resolved

        resolved = resolved.resolve()

        if resolved.is_file():
            return str(resolved)

    except (OSError, TypeError, ValueError):
        pass

    return None


def get_complaint_date(complaint):

    date_value = complaint.get("created_at")

    if not date_value:
        return datetime.min

    try:

        date_text = str(date_value).strip()

        if date_text.endswith("Z"):
            date_text = date_text[:-1] + "+00:00"

        parsed_date = datetime.fromisoformat(date_text)

        if parsed_date.tzinfo is not None:

            parsed_date = parsed_date.astimezone(
                datetime.now().astimezone().tzinfo
            ).replace(tzinfo=None)

        return parsed_date

    except (ValueError, TypeError, OverflowError):
        return datetime.min


def display_complaint_details(complaint):

    st.markdown(
        f"### {complaint.get('title', 'Untitled Complaint')}"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**Complaint ID:** "
            f"{complaint.get('tracking_id', 'Not available')}"
        )

        st.write(
            f"**Category:** "
            f"{complaint.get('category', 'Not available')}"
        )

        st.write(
            f"**Status:** "
            f"{complaint.get('status', 'Not available')}"
        )

        st.write(
            f"**Submitted:** "
            f"{complaint.get('created_at', 'Not available')}"
        )

    with col2:

        st.write(
            f"**Complainant:** "
            f"{complaint.get('complainant_name') or complaint.get('citizen_name') or 'Not available'}"
        )

        st.write(
            f"**Contact Number:** "
            f"{complaint.get('complainant_phone') or complaint.get('citizen_phone') or 'Not available'}"
        )

        st.write(
            f"**Department:** "
            f"{complaint.get('department_name', 'Not available')}"
        )

    st.divider()

    st.markdown("**Location of the Civic Issue**")

    st.write(
        complaint.get("issue_location") or "Not available"
    )

    address_fields = [
        ("Street or Locality", "street_locality"),
        ("Ward Number", "ward_number"),
        ("Municipality / Municipal Corporation", "municipality"),
        ("District", "district"),
        ("State", "state"),
    ]

    for label, key in address_fields:

        st.write(
            f"**{label}:** "
            f"{complaint.get(key) or 'Not available'}"
        )

    st.divider()

    st.markdown("**Complaint Description**")

    st.write(
        complaint.get("description") or "No description available."
    )

    if complaint.get("status") == "Rejected":

        st.divider()
        st.error("This complaint has been rejected.")

        rejection_reason = complaint.get("officer_remarks")

        if rejection_reason:

            st.markdown("**Recorded Rejection Reason**")
            st.write(rejection_reason)

    st.divider()

    st.markdown("**Complaint Evidence**")

    # ----------------------------------------------
    # PHOTOGRAPHS
    # ----------------------------------------------

    image_paths = get_complaint_images(complaint)

    st.markdown("**Uploaded Photographs**")

    if image_paths:

        image_columns = st.columns(4)
        displayed_count = 0

        for index, image_file in enumerate(image_paths, start=1):

            image_path = get_image_path(image_file)

            if image_path:

                with image_columns[displayed_count % 4]:

                    st.image(
                        image_path,
                        caption=f"Complaint Photograph {index}",
                        width=160,
                    )

                displayed_count += 1

            else:

                st.warning(
                    f"Photograph {index} could not be located."
                )

        if displayed_count == 0:

            st.warning(
                "None of the uploaded photographs could be located."
            )

    else:

        st.info("No photographs uploaded.")

    # ----------------------------------------------
    # VIDEO
    # ----------------------------------------------

    st.markdown("**Uploaded Video**")

    video_file = complaint.get("video_path")

    if video_file:

        video_path = get_media_path(video_file)

        if video_path:

            video_columns = st.columns([1, 2, 1])

            with video_columns[1]:
                st.video(video_path)

        else:

            st.warning("The uploaded video could not be located.")

    else:

        st.info("No video uploaded.")


# --------------------------------------------------
# LOAD ASSIGNED COMPLAINTS
# --------------------------------------------------

complaints = get_officer_complaints(user["id"])

if not complaints:

    st.info("You currently have no complaints assigned to you.")
    st.stop()


# --------------------------------------------------
# FILTER COMPLAINTS
# --------------------------------------------------

assigned_complaints = complaints

active_complaints = [
    complaint
    for complaint in complaints
    if complaint.get("status") in ACTIVE_STATUSES
]

resolved_complaints = [
    complaint
    for complaint in complaints
    if complaint.get("status") == "Resolved"
]

rejected_complaints = [
    complaint
    for complaint in complaints
    if complaint.get("status") == "Rejected"
]


# --------------------------------------------------
# INITIAL SELECTED DASHBOARD CARD
# --------------------------------------------------

if "officer_complaint_view" not in st.session_state:

    st.session_state["officer_complaint_view"] = "Active"


# --------------------------------------------------
# CLICKABLE DASHBOARD COUNT CARDS
# --------------------------------------------------

st.divider()

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:

    st.button(
        f"**Assigned Complaints**  \n\n({len(assigned_complaints)})",
        key="dashboard_assigned_card",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state["officer_complaint_view"] == "Assigned"
            else "secondary"
        ),
        on_click=select_officer_view,
        args=("Assigned",),
    )


with metric2:

    st.button(
        f"**Active Complaints**  \n\n({len(active_complaints)})",
        key="dashboard_active_card",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state["officer_complaint_view"] == "Active"
            else "secondary"
        ),
        on_click=select_officer_view,
        args=("Active",),
    )


with metric3:

    st.button(
        f"**Resolved Complaints**  \n\n({len(resolved_complaints)})",
        key="dashboard_resolved_card",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state["officer_complaint_view"] == "Resolved"
            else "secondary"
        ),
        on_click=select_officer_view,
        args=("Resolved",),
    )


with metric4:

    st.button(
        f"**Rejected Complaints**  \n\n({len(rejected_complaints)})",
        key="dashboard_rejected_card",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state["officer_complaint_view"] == "Rejected"
            else "secondary"
        ),
        on_click=select_officer_view,
        args=("Rejected",),
    )


# --------------------------------------------------
# DISPLAY COMPLAINTS SELECTED THROUGH COUNT CARDS
# --------------------------------------------------

selected_view = st.session_state["officer_complaint_view"]

if selected_view == "Assigned":

    displayed_complaints = assigned_complaints
    section_title = "All Assigned Complaints"

elif selected_view == "Active":

    displayed_complaints = active_complaints
    section_title = "Your Active Complaints"

elif selected_view == "Resolved":

    displayed_complaints = resolved_complaints
    section_title = "Your Resolved Complaints"

else:

    displayed_complaints = rejected_complaints
    section_title = "Your Rejected Complaints"


st.divider()
st.subheader(section_title)

if not displayed_complaints:

    st.info(
        f"There are currently no {selected_view.lower()} complaints."
    )

else:

    for complaint in displayed_complaints:

        with st.container(border=True):

            left, right = st.columns(2)

            with left:

                st.markdown(
                    f"**{complaint.get('title', 'Untitled Complaint')}**"
                )

                st.write(
                    f"**Location:** "
                    f"{complaint.get('issue_location') or 'Not available'}"
                )

                st.write(
                    f"**Municipality:** "
                    f"{complaint.get('municipality') or 'Not available'}"
                )

            with right:

                st.write(
                    f"**Complainant:** "
                    f"{complaint.get('complainant_name') or complaint.get('citizen_name') or 'Not available'}"
                )

                st.write(
                    f"**Submitted:** "
                    f"{complaint.get('created_at', 'Not available')}"
                )

                st.write(
                    f"**Status:** "
                    f"{complaint.get('status', 'Not available')}"
                )

            with st.expander("View Complete Complaint Details"):

                display_complaint_details(complaint)


# --------------------------------------------------
# MANAGE ACTIVE COMPLAINTS
# SHOW ONLY WHEN ACTIVE COMPLAINTS EXIST
# --------------------------------------------------

if active_complaints:

    st.divider()
    st.subheader("Manage a Complaint")

    complaint_options = {
        "None": None
    }

    for item in active_complaints:

        label = (
            f"{item.get('tracking_id', 'Unknown ID')} — "
            f"{item.get('title', 'Untitled Complaint')}"
        )

        complaint_options[label] = item

    selected_label = st.selectbox(
        "Select an active complaint",
        list(complaint_options.keys()),
        index=0,
        key="officer_complaint_management_selector",
    )

    selected = complaint_options[selected_label]

    if selected is None:

        st.info(
            "Select an active complaint from the dropdown above "
            "to view its details and manage its status."
        )

    else:

        # ------------------------------------------
        # SELECTED COMPLAINT DETAILS
        # ------------------------------------------

        st.divider()
        st.subheader("Selected Complaint")

        display_complaint_details(selected)

        # ------------------------------------------
        # COMPLAINT STATUS HISTORY
        # ------------------------------------------

        history = get_status_history(selected["id"])

        with st.expander("View Complaint History"):

            if history:

                for item in history:

                    history_status = (
                        item.get("status")
                        or item.get("new_status")
                        or "Status update"
                    )

                    changed_at = (
                        item.get("changed_at")
                        or item.get("created_at")
                        or "Time not available"
                    )

                    st.markdown(
                        f"**{history_status}** — {changed_at}"
                    )

                    updated_by = item.get("updated_by_name")
                    updated_role = item.get("updated_by_role")

                    if updated_by:

                        role_label = (
                            updated_role.title()
                            if updated_role
                            else "User"
                        )

                        st.caption(
                            f"Updated by: {updated_by} ({role_label})"
                        )

                    if item.get("remarks"):
                        st.write(item["remarks"])

                    st.divider()

            else:

                st.write("No history available.")

        # ------------------------------------------
        # REJECT COMPLAINT
        # ------------------------------------------

        st.divider()
        st.subheader("Reject Complaint")

        st.warning(
            "Use this option only after the complaint has been "
            "physically verified and found to be false, invalid, "
            "or incorrect. A rejected complaint cannot be "
            "processed further."
        )

        rejection_reason = st.text_area(
            "Reason for Rejection",
            placeholder=(
                "Explain why the complaint is being rejected "
                "after verification..."
            ),
            key=f"rejection_reason_{selected['id']}",
        )

        confirm_rejection = st.checkbox(
            "I confirm that this complaint has been verified "
            "and should be permanently rejected.",
            key=f"confirm_rejection_{selected['id']}",
        )

        if st.button(
            "Reject Complaint",
            type="primary",
            key=f"reject_complaint_{selected['id']}",
            disabled=(
                len(rejection_reason.strip()) < 5
                or not confirm_rejection
            ),
        ):

            success, message = reject_complaint(
                complaint_id=selected["id"],
                rejection_reason=rejection_reason.strip(),
            )

            if success:

                st.success(message)
                st.rerun()

            else:

                st.error(message)

        # ------------------------------------------
        # UPDATE COMPLAINT STATUS
        # ------------------------------------------

        st.divider()
        st.subheader("Update Complaint Status")

        allowed_statuses = [
            "Under Review",
            "In Progress",
            "Resolved",
        ]

        new_status = st.selectbox(
            "New Status",
            allowed_statuses,
            key=f"new_status_{selected['id']}",
        )

        remarks = st.text_area(
            "Officer Remarks",
            placeholder="Write an update for the citizen...",
            key=f"officer_remarks_{selected['id']}",
        )

        resolution_details = ""

        if new_status == "Resolved":

            resolution_details = st.text_area(
                "Resolution Details",
                placeholder="Explain how the complaint was resolved...",
                key=f"resolution_details_{selected['id']}",
            )

        if st.button(
            "Save Status Update",
            type="primary",
            key=f"save_status_{selected['id']}",
        ):

            if (
                new_status == "Resolved"
                and not resolution_details.strip()
            ):

                st.error(
                    "Please provide resolution details before resolving."
                )

            else:

                try:

                    success, message = update_complaint_status(
                        complaint_id=selected["id"],
                        new_status=new_status,
                        remarks=remarks.strip(),
                        resolution_details=resolution_details.strip(),
                    )

                    if success:

                        st.success(message)
                        st.rerun()

                    else:

                        st.error(message)

                except Exception as error:

                    st.error(
                        f"Could not update complaint: {error}"
                    )


# --------------------------------------------------
# COMPLAINT HISTORY
# --------------------------------------------------

st.divider()
st.subheader("Complaint History")

st.caption(
    "All complaints assigned to you are listed below in ascending "
    "submission date and time."
)

chronological_complaints = sorted(
    complaints,
    key=get_complaint_date,
)

for complaint in chronological_complaints:

    tracking_id = complaint.get(
        "tracking_id",
        "Unknown ID",
    )

    title = complaint.get(
        "title",
        "Untitled Complaint",
    )

    status = complaint.get(
        "status",
        "Unknown Status",
    )

    submitted = complaint.get(
        "created_at",
        "Date not available",
    )

    location = complaint.get(
        "issue_location"
    ) or "Location not available"

    municipality = complaint.get(
        "municipality"
    ) or "Municipality not available"

    history_label = (
        f"{tracking_id} | {title} | "
        f"{location} | {municipality} | "
        f"{status} | {submitted}"
    )

    with st.expander(history_label):

        st.markdown("### View Complaint Details")

        display_complaint_details(complaint)

        st.divider()
        st.markdown("**Status History**")

        history = get_status_history(complaint["id"])

        if history:

            for item in history:

                history_status = (
                    item.get("status")
                    or item.get("new_status")
                    or "Status update"
                )

                changed_at = (
                    item.get("changed_at")
                    or item.get("created_at")
                    or "Time not available"
                )

                st.markdown(
                    f"**{history_status}** — {changed_at}"
                )

                updated_by = item.get("updated_by_name")
                updated_role = item.get("updated_by_role")

                if updated_by:

                    role_label = (
                        updated_role.title()
                        if updated_role
                        else "User"
                    )

                    st.caption(
                        f"Updated by: {updated_by} ({role_label})"
                    )

                if item.get("remarks"):
                    st.write(item["remarks"])

                st.divider()

        else:

            st.info("No status history available.")
