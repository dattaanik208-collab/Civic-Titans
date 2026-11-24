
import json
from pathlib import Path

import streamlit as st

from modules.authentication import require_role, get_current_user
from modules.complaint_manager import (
    get_complaint_by_tracking_id,
    get_status_history,
)
from modules.image_handler import get_image_path


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Track Complaint | CivicTrack",
    page_icon="🔎",
    layout="wide",
)


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

require_role("citizen")
user = get_current_user()


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_complaint_images(complaint):

    image_paths = complaint.get("image_paths")

    if isinstance(image_paths, str):

        try:
            image_paths = json.loads(image_paths)

        except (json.JSONDecodeError, TypeError):
            image_paths = []

    if not isinstance(image_paths, list):
        image_paths = []

    # Backward compatibility
    if not image_paths and complaint.get("image_path"):
        image_paths = [complaint["image_path"]]

    return image_paths


def get_video_path(video_file):

    if not video_file:
        return None

    try:

        video_path = Path(video_file)

        if not video_path.is_absolute():
            video_path = Path.cwd() / video_path

        video_path = video_path.resolve()

        if video_path.is_file():
            return str(video_path)

    except (OSError, TypeError, ValueError):
        pass

    return None


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("🔎 Track Your Complaint")

st.write(
    "Enter your complaint tracking ID to view its current "
    "status and history."
)


# --------------------------------------------------
# TRACKING INPUT
# --------------------------------------------------

tracking_id = st.text_input(
    "Complaint Tracking ID",
    placeholder="Example: CT-XXXXXXXX",
    key="complaint_tracking_input",
).strip().upper()


# --------------------------------------------------
# TRACK COMPLAINT BUTTON
# --------------------------------------------------

if st.button("Track Complaint", type="primary"):

    if not tracking_id:

        st.session_state.pop("tracked_complaint", None)

        st.warning("Please enter your tracking ID.")

    else:

        complaint = get_complaint_by_tracking_id(
            tracking_id,
            citizen_id=user["id"],
        )

        if complaint:

            st.session_state["tracked_complaint"] = complaint

        else:

            st.session_state.pop("tracked_complaint", None)

            st.error(
                "No complaint was found with this tracking ID "
                "in your account."
            )


# --------------------------------------------------
# DISPLAY TRACKED COMPLAINT
# --------------------------------------------------

complaint = st.session_state.get("tracked_complaint")


if complaint:

    st.divider()

    st.subheader(
        complaint.get("title", "Complaint Details")
    )

    # ----------------------------------------------
    # CURRENT STATUS
    # ----------------------------------------------

    st.metric(
        "Current Status",
        complaint.get("status", "Not available"),
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Tracking ID:**",
            complaint.get("tracking_id", "Not available"),
        )

        st.write(
            "**Category:**",
            complaint.get("category", "Not available"),
        )

        st.write(
            "**Department:**",
            complaint.get("department_name") or "Not assigned",
        )

        st.write(
            "**Submitted:**",
            complaint.get("created_at", "Not available"),
        )

    with col2:

        st.write(
            "**Last Updated:**",
            complaint.get("updated_at", "Not available"),
        )

        st.write(
            "**Location:**",
            complaint.get("issue_location")
            or complaint.get("address")
            or "Not available",
        )

        address_fields = [
            ("Street or Locality", "street_locality"),
            ("Ward Number", "ward_number"),
            ("Municipality", "municipality"),
            ("District", "district"),
            ("State", "state"),
        ]

        for label, key in address_fields:

            value = complaint.get(key)

            if value:
                st.write(f"**{label}:**", value)

    # ----------------------------------------------
    # DESCRIPTION
    # ----------------------------------------------

    st.markdown("### Complaint Description")

    st.write(
        complaint.get("description", "No description available.")
    )

    # ----------------------------------------------
    # COMPLAINANT INFORMATION
    # ----------------------------------------------

    st.markdown("### Complainant Information")

    st.write(
        "**Name:**",
        complaint.get("complainant_name")
        or user.get("full_name", "Not available"),
    )

    st.write(
        "**Contact Number:**",
        complaint.get("complainant_phone")
        or user.get("phone", "Not available"),
    )

    # ----------------------------------------------
    # OFFICER REMARKS
    # ----------------------------------------------

    if complaint.get("officer_remarks"):

        if complaint.get("status") == "Rejected":

            st.markdown("### Rejection Information")

            st.error("This complaint has been rejected.")

            st.write(
                "**Reason:**",
                complaint["officer_remarks"],
            )

        else:

            st.markdown("### Officer Remarks")

            st.info(complaint["officer_remarks"])

    # ----------------------------------------------
    # RESOLUTION DETAILS
    # ----------------------------------------------

    if complaint.get("resolution_details"):

        st.markdown("### Resolution Details")

        st.success(complaint["resolution_details"])

    # ----------------------------------------------
    # ALL UPLOADED PHOTOGRAPHS
    # ----------------------------------------------

    st.divider()

    st.subheader("Uploaded Complaint Photographs")

    image_paths = get_complaint_images(complaint)

    if image_paths:

        columns = st.columns(4)
        displayed_count = 0

        for index, image_file in enumerate(image_paths):

            image_path = get_image_path(image_file)

            if image_path:

                with columns[displayed_count % 4]:

                    st.image(
                        image_path,
                        caption=f"Photograph {index + 1}",
                        use_container_width=True,
                    )

                displayed_count += 1

        if displayed_count == 0:

            st.warning(
                "Uploaded photographs could not be located."
            )

    else:

        st.info("No photographs were uploaded.")

    # ----------------------------------------------
    # UPLOADED VIDEO
    # ----------------------------------------------

    st.subheader("Uploaded Complaint Video")

    video_file = complaint.get("video_path")

    if video_file:

        video_path = get_video_path(video_file)

        if video_path:

            video_columns = st.columns([1, 2, 1])

            with video_columns[1]:
                st.video(video_path)

        else:

            st.warning(
                "The uploaded video could not be located."
            )

    else:

        st.info("No video was uploaded.")

    # ----------------------------------------------
    # STATUS HISTORY
    # ----------------------------------------------

    st.divider()

    st.subheader("Complaint Status History")

    history = get_status_history(complaint["id"])

    if history:

        for item in history:

            with st.container(border=True):

                st.markdown(
                    f"**{item.get('status', 'Status update')}**"
                )

                st.caption(
                    item.get("changed_at", "Date not available")
                )

                if item.get("changed_by_name"):

                    st.write(
                        f"Updated by: {item['changed_by_name']}"
                    )

                if item.get("remarks"):

                    st.write(item["remarks"])

    else:

        st.info(
            "No status history is available yet."
        )
