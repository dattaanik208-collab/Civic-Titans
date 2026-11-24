
import json
from pathlib import Path

import streamlit as st
import pandas as pd

from modules.authentication import require_role, get_current_user
from modules.complaint_manager import get_complaints_by_citizen
from modules.image_handler import get_image_path


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Citizen Dashboard | CivicTrack",
    page_icon="👤",
    layout="wide"
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

    if not image_paths and complaint.get("image_path"):
        image_paths = [complaint["image_path"]]

    return image_paths


def get_media_path(file_path):
    if not file_path:
        return None

    try:
        path = Path(file_path)

        if not path.is_absolute():
            path = Path.cwd() / path

        path = path.resolve()

        if path.is_file():
            return str(path)

    except (OSError, TypeError, ValueError):
        pass

    return None


# --------------------------------------------------
# HEADER
# --------------------------------------------------

import html

safe_name = html.escape(str(user.get("full_name", "Citizen")))

st.markdown(f"""
<div class="dashboard-header">
    <h1>Welcome, {safe_name} 👋</h1>
    <p>Manage your civic complaints and follow their progress.</p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# FETCH CITIZEN COMPLAINTS
# --------------------------------------------------

complaints = get_complaints_by_citizen(user["id"])

total = len(complaints)

pending = sum(
    complaint.get("status") == "Pending"
    for complaint in complaints
)

in_progress = sum(
    complaint.get("status") in (
        "Assigned",
        "Under Review",
        "In Progress"
    )
    for complaint in complaints
)

resolved = sum(
    complaint.get("status") == "Resolved"
    for complaint in complaints
)

rejected = sum(
    complaint.get("status") == "Rejected"
    for complaint in complaints
)


# --------------------------------------------------
# STATISTICS
# --------------------------------------------------

st.subheader("Your Complaint Overview")

columns = st.columns(5)

statistics = [
    ("📋 Total Complaints", total),
    ("⏳ Pending", pending),
    ("🔄 In Progress", in_progress),
    ("✅ Resolved", resolved),
    ("❌ Rejected", rejected)
]

for column, (label, value) in zip(columns, statistics):
    with column:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)


# --------------------------------------------------
# COMPLAINT HISTORY
# --------------------------------------------------

st.subheader("Your Complaint History")

if not complaints:

    st.info(
        "You haven't submitted any complaints yet. "
        "Use the Report Complaint page to submit your first report."
    )

else:

    dataframe = pd.DataFrame(complaints)

    display_columns = [
        "tracking_id",
        "title",
        "category",
        "status",
        "created_at"
    ]

    display_dataframe = dataframe.reindex(
        columns=display_columns
    ).copy()

    display_dataframe.columns = [
        "Tracking ID",
        "Title",
        "Category",
        "Status",
        "Submitted On"
    ]

    st.dataframe(
        display_dataframe,
        use_container_width=True,
        hide_index=True
    )


# --------------------------------------------------
# COMPLAINT DETAILS
# --------------------------------------------------

if complaints:

    st.subheader("View Complaint Details")

    complaint_options = {
        "None": None
    }

    for complaint in complaints:

        label = (
            f"{complaint.get('tracking_id', 'Unknown ID')} — "
            f"{complaint.get('title', 'Untitled Complaint')}"
        )

        complaint_options[label] = complaint

    selected_label = st.selectbox(
        "Select a complaint",
        list(complaint_options.keys()),
        index=0,
        key="citizen_complaint_details_selector"
    )

    selected_complaint = complaint_options[selected_label]

    if selected_complaint is None:

        st.info(
            "Select a complaint from the dropdown above "
            "to view its complete information."
        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("#### Complaint Information")

            st.write(
                "**Tracking ID:**",
                selected_complaint.get("tracking_id", "Not available")
            )

            st.write(
                "**Title:**",
                selected_complaint.get("title", "Not available")
            )

            st.write(
                "**Category:**",
                selected_complaint.get("category", "Not available")
            )

            st.write(
                "**Status:**",
                selected_complaint.get("status", "Not available")
            )

            st.write(
                "**Location:**",
                selected_complaint.get("issue_location")
                or selected_complaint.get("address")
                or "Not available"
            )

            address_fields = [
                ("Street or Locality", "street_locality"),
                ("Ward Number", "ward_number"),
                ("Municipality", "municipality"),
                ("District", "district"),
                ("State", "state")
            ]

            for label, key in address_fields:

                value = selected_complaint.get(key)

                if value:
                    st.write(f"**{label}:**", value)

        with col2:

            st.markdown("#### Department Information")

            st.write(
                "**Department:**",
                selected_complaint.get("department_name")
                or "Not assigned"
            )

            st.write(
                "**Assigned Officer:**",
                selected_complaint.get("officer_name")
                or "Not assigned"
            )

            st.write(
                "**Submitted On:**",
                selected_complaint.get("created_at", "Not available")
            )

            st.write(
                "**Complainant:**",
                selected_complaint.get("complainant_name")
                or user.get("full_name", "Not available")
            )

            st.write(
                "**Contact Number:**",
                selected_complaint.get("complainant_phone")
                or user.get("phone", "Not available")
            )

        st.markdown("#### Description")

        st.write(
            selected_complaint.get("description")
            or "No description available."
        )

        # ------------------------------------------
        # ALL UPLOADED PHOTOGRAPHS
        # ------------------------------------------

        st.markdown("#### Uploaded Photographs")

        image_paths = get_complaint_images(selected_complaint)

        if image_paths:

            image_columns = st.columns(4)
            displayed_count = 0

            for index, image_file in enumerate(image_paths):

                image_path = get_image_path(image_file)

                if image_path:

                    with image_columns[displayed_count % 4]:

                        st.image(
                            image_path,
                            caption=f"Photograph {index + 1}",
                            use_container_width=True
                        )

                    displayed_count += 1

            if displayed_count == 0:
                st.warning(
                    "Uploaded photographs could not be located."
                )

        else:
            st.info("No photographs uploaded.")

        # ------------------------------------------
        # UPLOADED VIDEO
        # ------------------------------------------

        st.markdown("#### Uploaded Video")

        video_file = selected_complaint.get("video_path")

        if video_file:

            video_path = get_media_path(video_file)

            if video_path:

                video_columns = st.columns([1, 2, 1])

                with video_columns[1]:
                    st.video(video_path)

            else:
                st.warning(
                    "The uploaded video could not be located."
                )

        else:
            st.info("No video uploaded.")

        # ------------------------------------------
        # RESOLUTION DETAILS
        # ------------------------------------------

        if selected_complaint.get("resolution_details"):

            st.markdown("#### Resolution Details")

            st.success(
                selected_complaint["resolution_details"]
            )

        # ------------------------------------------
        # REJECTION DETAILS
        # ------------------------------------------

        if selected_complaint.get("status") == "Rejected":

            st.markdown("#### Rejection Information")

            st.error("This complaint has been rejected.")

            rejection_reason = selected_complaint.get(
                "officer_remarks"
            )

            if rejection_reason:
                st.write(
                    "**Rejection Reason:**",
                    rejection_reason
                )

        # ------------------------------------------
        # OFFICER REMARKS
        # ------------------------------------------

        if selected_complaint.get("status") != "Rejected":

            st.markdown("#### Officer Remarks")

            st.write(
                selected_complaint.get("officer_remarks")
                or "No remarks have been added yet."
            )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "CivicTrack | Citizen Dashboard | "
    "Your voice helps improve public services."
)
