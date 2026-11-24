
import streamlit as st

from modules.authentication import require_role, get_current_user
from modules.complaint_manager import (
    create_complaint,
    COMPLAINT_CATEGORIES,
)
from modules.image_handler import (
    save_images,
    save_video,
    delete_images,
    delete_media,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Report a Complaint | CivicTrack",
    page_icon="📝",
    layout="wide"
)


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

require_role("citizen")
user = get_current_user()


# --------------------------------------------------
# SUCCESS DIALOG STATE
# --------------------------------------------------

if "complaint_success_id" not in st.session_state:
    st.session_state.complaint_success_id = None


@st.dialog("Complaint submitted successfully")
def show_success_dialog():

    st.success("Your complaint has been registered successfully.")

    st.write("Your Complaint ID:")

    st.code(
        st.session_state.complaint_success_id,
        language=None
    )

    st.info(
        "Please save this Complaint ID for future reference."
    )

    if st.button("OK", use_container_width=True):
        st.session_state.complaint_success_id = None
        st.rerun()


if st.session_state.complaint_success_id:
    show_success_dialog()


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("📝 Report a Civic Issue")

st.write(
    "Help improve your community by reporting a public "
    "infrastructure or civic problem."
)

st.info(
    "Please provide accurate information so that the "
    "responsible department can review your complaint."
)


# --------------------------------------------------
# COMPLAINT FORM
# --------------------------------------------------

with st.form(
    "complaint_submission_form",
    clear_on_submit=True
):

    st.subheader("Complaint Information")

    title = st.text_input(
        "Complaint Title",
        placeholder="Example: Large pothole near main road",
        max_chars=120
    )

    category = st.selectbox(
        "Complaint Category",
        COMPLAINT_CATEGORIES
    )

    description = st.text_area(
        "Detailed Description",
        placeholder="Describe the civic issue in detail.",
        height=150,
        max_chars=3000
    )

    # --------------------------------------------------
    # LOCATION DETAILS
    # --------------------------------------------------

    st.subheader("Location Details")

    issue_location = st.text_input(
        "Location of the Civic Issue",
        placeholder="Example: Near the public bus stop"
    )

    street_locality = st.text_input(
        "Street or Locality",
        placeholder="Enter street or locality"
    )

    col1, col2 = st.columns(2)

    with col1:
        ward_number = st.text_input(
            "Ward Number",
            placeholder="Enter ward number"
        )

    with col2:
        municipality = st.text_input(
            "Municipality or Municipal Corporation",
            placeholder="Enter municipality name"
        )

    col3, col4 = st.columns(2)

    with col3:
        district = st.text_input(
            "District",
            placeholder="Enter district"
        )

    with col4:
        state = st.text_input(
            "State",
            placeholder="Enter state"
        )

    # --------------------------------------------------
    # MEDIA ATTACHMENTS
    # --------------------------------------------------

    st.subheader("Supporting Evidence")

    uploaded_images = st.file_uploader(
        "Upload Photographs",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help=(
            "You can upload multiple photographs. "
            "Maximum 5 MB per photograph."
        )
    )

    uploaded_video = st.file_uploader(
        "Upload a Short Video (Optional)",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        accept_multiple_files=False,
        help=(
            "Only one video is allowed. "
            "Maximum duration: 30 seconds. "
            "Maximum size: 50 MB."
        )
    )

    # --------------------------------------------------
    # COMPLAINANT DETAILS
    # --------------------------------------------------

    st.subheader("Complainant Details")

    complainant_name = st.text_input(
        "Full Name",
        value=user.get("full_name", "") or "",
        max_chars=120
    )

    complainant_phone = st.text_input(
        "Contact Number",
        value=user.get("phone", "") or "",
        max_chars=20
    )

    # --------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------

    agree = st.checkbox(
        "I confirm that the information provided is accurate."
    )

    submitted = st.form_submit_button(
        "Submit Complaint",
        use_container_width=True
    )


# --------------------------------------------------
# FORM PROCESSING
# --------------------------------------------------

if submitted:

    required_fields = {
        "Complaint title": title,
        "Description": description,
        "Location of the civic issue": issue_location,
        "Street or locality": street_locality,
        "Ward number": ward_number,
        "Municipality or municipal corporation": municipality,
        "District": district,
        "State": state,
        "Complainant full name": complainant_name,
        "Contact number": complainant_phone,
    }

    missing_fields = [
        field
        for field, value in required_fields.items()
        if not str(value).strip()
    ]

    phone_digits = (
        complainant_phone.strip()
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
    )

    if missing_fields:

        st.error(
            "Please complete these required fields: "
            + ", ".join(missing_fields)
        )

    elif not phone_digits.isdigit():

        st.error("Please enter a valid contact number.")

    elif not 7 <= len(phone_digits) <= 15:

        st.error(
            "Contact number must contain 7 to 15 digits."
        )

    elif not agree:

        st.error(
            "Please confirm the information before submitting."
        )

    else:

        saved_image_paths = []
        saved_video_path = None

        try:

            # --------------------------------------------------
            # SAVE PHOTOGRAPHS
            # --------------------------------------------------

            if uploaded_images:

                saved_image_paths, image_message = save_images(
                    uploaded_images
                )

                if not saved_image_paths:
                    raise ValueError(image_message)

            # --------------------------------------------------
            # SAVE VIDEO
            # --------------------------------------------------

            if uploaded_video is not None:

                saved_video_path, video_message = save_video(
                    uploaded_video
                )

                if not saved_video_path:
                    raise ValueError(video_message)

            # --------------------------------------------------
            # CREATE COMPLAINT
            # --------------------------------------------------

            success, result = create_complaint(
                citizen_id=user["id"],
                title=title.strip(),
                category=category,
                description=description.strip(),

                issue_location=issue_location.strip(),
                street_locality=street_locality.strip(),
                ward_number=ward_number.strip(),
                municipality=municipality.strip(),
                district=district.strip(),
                state=state.strip(),

                complainant_name=complainant_name.strip(),
                complainant_phone=complainant_phone.strip(),

                image_paths=saved_image_paths,
                video_path=saved_video_path
            )

            if success:

                st.session_state.complaint_success_id = result
                st.rerun()

            else:

                if saved_image_paths:
                    delete_images(saved_image_paths)

                if saved_video_path:
                    delete_media(saved_video_path)

                st.error(result)

        except Exception as error:

            # Remove uploaded files if submission fails.
            if saved_image_paths:
                delete_images(saved_image_paths)

            if saved_video_path:
                delete_media(saved_video_path)

            st.error(str(error))


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "CivicTrack | Complaint Reporting Portal"
)
