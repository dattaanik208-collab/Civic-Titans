
import json
from pathlib import Path

import streamlit as st
import pandas as pd

from modules.authentication import (
    require_role,
    get_current_user,
    get_all_users,
    create_user_account_by_admin,
    update_user_status,
    delete_user_account,
)

from modules.complaint_manager import (
    get_all_complaints,
    get_all_departments,
    get_department_officers,
    assign_complaint,
    reject_complaint,
    get_status_history,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Admin Dashboard | CivicTrack",
    page_icon="🛡️",
    layout="wide",
)

require_role("admin")
user = get_current_user()

st.title("🛡️ CivicTrack Admin Dashboard")
st.write(f"Welcome, {user['full_name']}.")


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_complaint_address(complaint):
    fields = [
        ("Location", complaint.get("issue_location")),
        ("Street / Locality", complaint.get("street_locality")),
        ("Ward", complaint.get("ward_number")),
        ("Municipality", complaint.get("municipality")),
        ("District", complaint.get("district")),
        ("State", complaint.get("state")),
    ]

    return [
        f"{label}: {value}"
        for label, value in fields
        if value and str(value).strip()
    ]


def get_complaint_images(complaint):
    image_paths = complaint.get("image_paths")

    if isinstance(image_paths, list):
        return image_paths

    if isinstance(image_paths, str):

        try:
            decoded = json.loads(image_paths)

            if isinstance(decoded, list):
                return decoded

            if isinstance(decoded, str):
                return [decoded]

        except (json.JSONDecodeError, TypeError):
            return [image_paths] if image_paths.strip() else []

    old_image = complaint.get("image_path")

    return [old_image] if old_image else []


def resolve_media_path(file_path):
    if not file_path:
        return None

    try:
        path = Path(str(file_path))

        if path.is_absolute():
            return path.resolve() if path.is_file() else None

        project_path = (Path.cwd() / path).resolve()

        if project_path.is_file():
            return project_path

    except (OSError, TypeError, ValueError):
        pass

    return None


def display_complaint_details(complaint):
    st.markdown("#### Complaint Information")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Complaint ID**")
        st.code(
            str(complaint.get("tracking_id") or "Not available"),
            language=None,
        )

        st.write("**Complaint Title**")
        st.write(complaint.get("title") or "Not provided")

        st.write("**Category**")
        st.write(complaint.get("category") or "Not provided")

    with col2:
        st.write("**Current Status**")
        st.write(complaint.get("status") or "Not available")

        st.write("**Submitted On**")
        st.write(complaint.get("created_at") or "Not available")

        st.write("**Assigned Department**")
        st.write(
            complaint.get("department_name") or "Not assigned"
        )

        st.write("**Assigned Officer**")
        st.write(
            complaint.get("officer_name")
            or complaint.get("assigned_officer_name")
            or "Not assigned"
        )

    if complaint.get("status") == "Rejected":
        st.error("This complaint has been rejected.")

        rejection_reason = complaint.get("officer_remarks")

        if rejection_reason:
            st.write("**Rejection Reason**")
            st.warning(rejection_reason)

    st.divider()

    st.markdown("#### Complainant Details")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Full Name**")
        st.write(
            complaint.get("complainant_name")
            or complaint.get("citizen_name")
            or "Not available"
        )

    with col2:
        st.write("**Contact Number**")
        st.write(
            complaint.get("complainant_phone")
            or "Not available"
        )

    st.divider()

    st.markdown("#### Location Details")

    address_fields = [
        ("Location of Civic Issue", "issue_location"),
        ("Street or Locality", "street_locality"),
        ("Ward Number", "ward_number"),
        ("Municipality / Municipal Corporation", "municipality"),
        ("District", "district"),
        ("State", "state"),
    ]

    address_columns = st.columns(2)

    for index, (label, key) in enumerate(address_fields):
        with address_columns[index % 2]:
            st.write(f"**{label}**")
            st.write(complaint.get(key) or "Not provided")

    st.divider()

    st.markdown("#### Complaint Description")
    st.write(
        complaint.get("description") or "No description available."
    )

    st.divider()

    # ----------------------------------------------
    # SUPPORTING EVIDENCE
    # ----------------------------------------------

    st.markdown("#### Supporting Evidence")

    image_paths = get_complaint_images(complaint)
    video_path = complaint.get("video_path")

    # ----------------------------------------------
    # ALL PHOTOGRAPHS IN COMPACT GRID
    # ----------------------------------------------

    st.markdown("**Uploaded Photographs**")

    if image_paths:

        image_columns = st.columns(4)
        displayed_count = 0

        for index, image_file in enumerate(image_paths, start=1):

            resolved_path = resolve_media_path(image_file)

            if resolved_path:

                with image_columns[displayed_count % 4]:

                    st.image(
                        str(resolved_path),
                        caption=f"Photograph {index}",
                        width=160,
                    )

                displayed_count += 1

            else:

                st.warning(
                    f"Photograph {index} could not be found."
                )

        if displayed_count == 0:
            st.warning(
                "None of the uploaded photographs could be located."
            )

    else:
        st.info("No photographs were attached.")

    # ----------------------------------------------
    # VIDEO IN COMPACT PLAYER
    # ----------------------------------------------

    st.markdown("**Uploaded Video**")

    if video_path:

        resolved_video = resolve_media_path(video_path)

        if resolved_video:

            video_columns = st.columns([1, 2, 1])

            with video_columns[1]:
                st.video(str(resolved_video))

        else:
            st.warning("The uploaded video could not be found.")

    else:
        st.info("No video was attached.")

    # ----------------------------------------------
    # STATUS HISTORY
    # ----------------------------------------------

    st.divider()
    st.markdown("#### Complaint Status History")

    try:
        history = get_status_history(complaint["id"])

        if history:
            for entry in history:
                old_status = entry.get("old_status") or "New"
                new_status = entry.get("new_status") or "Unknown"
                updated_by = entry.get("updated_by_name") or "System"
                updated_role = entry.get("updated_by_role") or ""
                remarks = entry.get("remarks") or "No remarks"
                updated_at = entry.get("updated_at") or ""

                with st.container(border=True):
                    st.write(
                        f"**{old_status} → {new_status}**"
                    )
                    st.caption(
                        f"Updated by: {updated_by} "
                        f"({updated_role}) | {updated_at}"
                    )
                    st.write(remarks)
        else:
            st.info("No status history available.")

    except Exception as error:
        st.warning(f"Could not load status history: {error}")


# --------------------------------------------------
# OFFICER REGISTRATION SUCCESS DIALOG
# --------------------------------------------------

@st.dialog("User Registration Successful")
def show_officer_registration_dialog():

    details = st.session_state.get(
        "pending_officer_registration"
    )

    if not details:
        return

    st.success("User registration successful!")

    st.write(f"**Officer Name:** {details['name']}")
    st.write(f"**Email ID:** {details['email']}")
    st.write(f"**Mobile Number:** {details['phone']}")
    st.write(f"**Locality/Area:** {details['address']}")

    st.markdown("### Generated Officer UID")

    st.markdown(
        f"""
        <div style="
            color: var(--ct-green);
            font-size: 28px;
            font-weight: bold;
            padding: 10px 0;
        ">
            {details['uid']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Please save this UID. The officer will use it to log in."
    )

    if st.button(
        "OK",
        type="primary",
        use_container_width=True,
        key="close_officer_registration_dialog",
    ):
        st.session_state.pop(
            "pending_officer_registration",
            None,
        )
        st.rerun()


if st.session_state.get("pending_officer_registration"):
    show_officer_registration_dialog()


# --------------------------------------------------
# LOAD APPLICATION DATA
# --------------------------------------------------

try:
    complaints = get_all_complaints()
    users = get_all_users()
    departments = get_all_departments()

    department_options = {
        department["department_name"]: department
        for department in departments
    }

except Exception as error:
    st.error(f"Could not load dashboard data: {error}")
    st.stop()


citizens = [
    account for account in users
    if account.get("role") == "citizen"
]

officers = [
    account for account in users
    if account.get("role") == "officer"
]

administrators = [
    account for account in users
    if account.get("role") == "admin"
]

# --------------------------------------------------
# SYSTEM COUNTS
# --------------------------------------------------

total_complaints = len(complaints)

pending_complaints = sum(
    complaint.get("status") in [
        "Pending",
        "Under Review",
        "Assigned",
        "In Progress",
    ]
    for complaint in complaints
)

resolved_complaints = sum(
    complaint.get("status") == "Resolved"
    for complaint in complaints
)

rejected_complaints = sum(
    complaint.get("status") == "Rejected"
    for complaint in complaints
)

total_users = len(users)
total_citizens = len(citizens)
total_officers = len(officers)


# --------------------------------------------------
# SYSTEM OVERVIEW
# --------------------------------------------------

st.subheader("System Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Complaints", total_complaints)
col2.metric("Active Complaints", pending_complaints)
col3.metric("Resolved Complaints", resolved_complaints)
col4.metric("Rejected Complaints", rejected_complaints)

col5, col6, col7 = st.columns(3)

col5.metric("Registered Users", total_users)
col6.metric("Registered Citizens", total_citizens)
col7.metric("Officers", total_officers)

st.divider()


# --------------------------------------------------
# COMPLAINT MANAGEMENT
# --------------------------------------------------

st.subheader("📋 Complaint Management")

if complaints:

    # ----------------------------------------------
    # COMPLAINT TABLE
    # ----------------------------------------------

    complaint_rows = []

    for complaint in complaints:
        complaint_rows.append({
            "Complaint ID": complaint.get("tracking_id") or "—",
            "Title": complaint.get("title") or "—",
            "Category": complaint.get("category") or "—",
            "Status": complaint.get("status") or "—",
            "Location": complaint.get("issue_location") or "—",
            "Street / Locality": complaint.get("street_locality") or "—",
            "Ward": complaint.get("ward_number") or "—",
            "Municipality": complaint.get("municipality") or "—",
            "District": complaint.get("district") or "—",
            "State": complaint.get("state") or "—",
            "Complainant": (
                complaint.get("complainant_name")
                or complaint.get("citizen_name")
                or "—"
            ),
            "Contact Number": complaint.get("complainant_phone") or "—",
            "Department": complaint.get("department_name") or "Not assigned",
            "Assigned Officer": (
                complaint.get("officer_name")
                or complaint.get("assigned_officer_name")
                or "Not assigned"
            ),
            "Submitted On": complaint.get("created_at") or "—",
        })

    complaint_df = pd.DataFrame(complaint_rows)

    st.dataframe(
        complaint_df,
        use_container_width=True,
        hide_index=True,
    )

    # ----------------------------------------------
    # SELECT COMPLAINT
    # ----------------------------------------------

    st.markdown("### View Complete Complaint Details")

    complaint_options = {
        f"{item.get('tracking_id', 'No ID')} — "
        f"{item.get('title', 'Untitled')}": item
        for item in complaints
    }

    complaint_labels = ["None"] + list(complaint_options.keys())

    selected_label = st.selectbox(
        "Select complaint to view its complete details",
        complaint_labels,
        index=0,
        key="admin_selected_complaint",
    )

    if selected_label != "None":

        selected_complaint = complaint_options[selected_label]
        selected_status = selected_complaint.get("status")
        selected_complaint_id = selected_complaint["id"]

        with st.expander(
            "Open Complete Complaint Details",
            expanded=True,
        ):
            display_complaint_details(selected_complaint)

        st.divider()

        # ------------------------------------------
        # ADMINISTRATOR REJECTION
        # ------------------------------------------

        st.markdown("### Reject Complaint")

        is_unassigned = (
            selected_complaint.get("assigned_officer_id") is None
        )

        can_admin_reject = (
            is_unassigned
            and selected_status in ("Pending", "Under Review")
        )

        if can_admin_reject:


            rejection_reason = st.text_area(
                "Reason for rejecting this complaint",
                placeholder=(
                    "Explain why this complaint is being rejected..."
                ),
                key=f"admin_rejection_reason_{selected_complaint_id}",
            )

            confirm_rejection = st.checkbox(
                "I confirm that I have reviewed this complaint "
                "and want to reject it permanently.",
                key=f"admin_confirm_rejection_{selected_complaint_id}",
            )

            if st.button(
                "Reject Complaint",
                type="primary",
                key=f"admin_reject_button_{selected_complaint_id}",
                disabled=(
                    not confirm_rejection
                    or len(rejection_reason.strip()) < 5
                ),
            ):

                success, message = reject_complaint(
                    selected_complaint_id,
                    rejection_reason,
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        elif selected_status == "Rejected":

            st.error(
                "This complaint has already been rejected. "
                "It cannot be processed or assigned again."
            )

        elif selected_status == "Resolved":

            st.info(
                "This complaint has already been resolved. "
                "It cannot be rejected or assigned again."
            )

        elif not is_unassigned:

            st.info(
                "This complaint has already been assigned to an officer. "
                "The assigned officer is responsible for verification "
                "and rejection if necessary."
            )

        else:

            st.info(
                "This complaint is not currently eligible for "
                "administrator rejection."
            )

        st.divider()

        # ------------------------------------------
        # ASSIGN COMPLAINT TO OFFICER
        # ------------------------------------------

        st.markdown("### Assign Complaint to Officer")

        can_assign = (
            is_unassigned
            and selected_status in ("Pending", "Under Review")
        )

        if can_assign:

            st.write(f"**Current Status:** {selected_status}")

            st.caption(
                "First select the officer's department. "
                "Then select an active officer from that department. "
                "The complaint's original department will remain unchanged."
            )

            # --------------------------------------
            # STEP 1: SELECT OFFICER DEPARTMENT
            # --------------------------------------

            if department_options:

                selected_assignment_department_name = st.selectbox(
                    "Select Officer Department",
                    list(department_options.keys()),
                    key=f"assign_department_{selected_complaint_id}",
                    placeholder="Choose a department",
                )

                selected_assignment_department = department_options[
                    selected_assignment_department_name
                ]

                selected_assignment_department_id = (
                    selected_assignment_department["id"]
                )

                # ----------------------------------
                # STEP 2: LOAD OFFICERS FROM SELECTED
                # DEPARTMENT ONLY
                # ----------------------------------

                available_officers = get_department_officers(
                    selected_assignment_department_id
                )

                if available_officers:

                    officer_options = {
                        (
                            f"{officer['full_name']} "
                            f"({officer['email']})"
                        ): officer
                        for officer in available_officers
                    }

                    selected_officer_label = st.selectbox(
                        "Select Officer",
                        list(officer_options.keys()),
                        key=(
                            f"assign_officer_"
                            f"{selected_complaint_id}_"
                            f"{selected_assignment_department_id}"
                        ),
                    )

                    selected_officer = officer_options[
                        selected_officer_label
                    ]

                    st.caption(
                        f"Selected Department: "
                        f"{selected_assignment_department_name}"
                    )

                    st.caption(
                        f"Selected Officer: "
                        f"{selected_officer['full_name']}"
                    )

                    # ------------------------------
                    # FINAL ASSIGNMENT
                    # ------------------------------

                    if st.button(
                        "Assign Complaint",
                        type="primary",
                        key=f"assign_complaint_{selected_complaint_id}",
                    ):

                        try:
                            success, message = assign_complaint(
                                selected_complaint_id,
                                selected_officer["id"],
                            )

                            if success:

                                st.session_state[
                                    f"assignment_success_{selected_complaint_id}"
                                ] = True

                                st.rerun()

                            else:
                                st.error(message)

                        except Exception as error:
                            st.error(
                                f"Assignment failed: {error}"
                            )

                else:

                    st.warning(
                        "There are no active officers in "
                        f"{selected_assignment_department_name}. "
                        "Please select another department."
                    )

            else:

                st.warning(
                    "No departments are available. "
                    "Please create a department before assigning complaints."
                )

        else:

            assignment_success_key = (
                f"assignment_success_{selected_complaint_id}"
            )

            if (
                st.session_state.get(assignment_success_key)
                and selected_complaint.get("assigned_officer_id") is not None
            ):
                st.success(
                    "Officer successfully assigned to this complaint."
                )

                st.session_state.pop(
                    assignment_success_key,
                    None,
                )

            elif selected_complaint.get("assigned_officer_id") is not None:

                st.success(
                    "An officer has already been successfully assigned "
                    "to this complaint."
                )

                st.info(
                    "You can view the assigned officer in the complaint "
                    "details above."
                )

            elif selected_status in ("Resolved", "Rejected"):

                st.info(
                    "This complaint is closed. No further assignment "
                    "is available."
                )

            else:

                st.info(
                    "This complaint is not currently awaiting assignment."
                )

    else:
        st.info(
            "Select a complaint from the dropdown above to view "
            "its complete details or manage its status."
        )

else:
    st.info("No complaints have been submitted yet.")

st.divider()


# --------------------------------------------------
# USER MANAGEMENT
# --------------------------------------------------

st.subheader("👥 User Management")


# --------------------------------------------------
# ADMINISTRATOR TABLE
# --------------------------------------------------

if administrators:

    st.markdown("### Administrator Accounts")

    admin_rows = []

    for index, account in enumerate(administrators, start=1):
        admin_rows.append({
            "S.No.": index,
            "Name": account.get("full_name") or "—",
            "Email": account.get("email") or "—",
            "Role": "Administrator",
            "Admin UID": account.get("admin_id") or "—",
            "Active": (
                "Yes" if account.get("is_active") else "No"
            ),
        })

    st.dataframe(
        pd.DataFrame(admin_rows),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# OFFICER TABLE
# --------------------------------------------------

if officers:

    st.markdown("### Officer Accounts")

    officer_rows = []

    for index, account in enumerate(officers, start=1):
        officer_rows.append({
            "S.No.": index,
            "Name": account.get("full_name") or "—",
            "Email": account.get("email") or "—",
            "Role": "Officer",
            "Officer UID": account.get("officer_uid") or "—",
            "Mobile Number": account.get("phone") or "None",
            "Locality/Area": account.get("address") or "None",
            "Department": account.get("department_name") or "None",
            "Active": (
                "Yes" if account.get("is_active") else "No"
            ),
        })

    st.dataframe(
        pd.DataFrame(officer_rows),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# CITIZEN TABLE
# --------------------------------------------------

if citizens:

    st.markdown("### Citizen Accounts")

    citizen_rows = []

    for index, account in enumerate(citizens, start=1):
        citizen_rows.append({
            "S.No.": index,
            "Name": account.get("full_name") or "—",
            "Email": account.get("email") or "—",
            "Role": "Citizen",
            "Mobile Number": account.get("phone") or "None",
            "Address": account.get("address") or "None",
            "Active": (
                "Yes" if account.get("is_active") else "No"
            ),
        })

    st.dataframe(
        pd.DataFrame(citizen_rows),
        use_container_width=True,
        hide_index=True,
    )


if not users:
    st.info("No user accounts found.")


# --------------------------------------------------
# MANAGE USER ACCOUNTS
# --------------------------------------------------

manageable_users = [
    account for account in users
    if account.get("role") in ["citizen", "officer"]
]

if manageable_users:

    st.markdown("### Manage Account")

    account_options = {
        f"{account['full_name']} — {account['email']} "
        f"({account['role'].title()})": account
        for account in manageable_users
    }

    account_labels = ["None"] + list(account_options.keys())

    selected_account_label = st.selectbox(
        "Select citizen or officer account",
        account_labels,
        index=0,
        key="manage_account",
    )

    if selected_account_label != "None":

        selected_account = account_options[
            selected_account_label
        ]

        account_active = bool(
            selected_account.get("is_active")
        )

        st.write(
            f"**Current status:** "
            f"{'Active' if account_active else 'Inactive'}"
        )

        new_active_status = st.toggle(
            "Account active",
            value=account_active,
            key=f"account_active_{selected_account['id']}",
        )

        if new_active_status != account_active:

            if st.button(
                "Save Account Status",
                key="save_account_status",
            ):

                try:
                    success, message = update_user_status(
                        selected_account["id"],
                        new_active_status,
                    )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

                except Exception as error:
                    st.error(
                        f"Could not update account: {error}"
                    )

        st.markdown("### Delete Account")

        st.warning(
            "Deleting an account is permanent. The authentication module "
            "also removes or updates records associated with that account."
        )

        confirm_delete = st.checkbox(
            f"I confirm that I want to permanently delete "
            f"{selected_account['full_name']}.",
            key=f"confirm_delete_{selected_account['id']}",
        )

        if st.button(
            "Delete Selected Account",
            type="secondary",
            disabled=not confirm_delete,
            key="delete_selected_account",
        ):

            try:
                success, message = delete_user_account(
                    selected_account["id"]
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

            except Exception as error:
                st.error(
                    f"Could not delete account: {error}"
                )

    else:
        st.info(
            "Select a citizen or officer account to manage its status "
            "or access the deletion panel."
        )

else:
    st.info(
        "There are currently no citizen or officer accounts to manage."
    )

st.divider()


# --------------------------------------------------
# CREATE CITIZEN OR OFFICER ACCOUNT
# --------------------------------------------------

st.subheader("➕ Create User Account")

st.write(
    "The administrator can create citizen and officer accounts. "
    "Every new account must have a security question and answer."
)


# --------------------------------------------------
# REGISTRATION NOTIFICATION
# --------------------------------------------------

registration_notice = st.session_state.pop(
    "admin_registration_notice",
    None,
)

if registration_notice:
    st.success(registration_notice)


# --------------------------------------------------
# ACCOUNT TYPE
# --------------------------------------------------

new_role = st.selectbox(
    "Account type",
    ["citizen", "officer"],
    key="admin_new_account_role",
)


# --------------------------------------------------
# COMMON REGISTRATION FIELDS
# --------------------------------------------------

new_name = st.text_input(
    "Full name",
    key="admin_new_account_name",
)

new_email = st.text_input(
    "Email address",
    key="admin_new_account_email",
)

new_phone = st.text_input(
    "Mobile number",
    key="admin_new_account_phone",
)


# --------------------------------------------------
# ADDRESS / LOCALITY FIELD
# --------------------------------------------------

if new_role == "citizen":

    new_address = st.text_area(
        "ADDRESS",
        key="admin_new_account_address",
    )

else:

    new_address = st.text_area(
        "LOCALITY/AREA",
        key="admin_new_account_address",
    )


# --------------------------------------------------
# OFFICER DEPARTMENT
# --------------------------------------------------

new_department_id = None

staff_department_names = list(
    department_options.keys()
)

if new_role == "officer":

    if staff_department_names:

        selected_department_name = st.selectbox(
            "Officer Department",
            staff_department_names,
            key="admin_new_officer_department",
        )

        new_department_id = department_options[
            selected_department_name
        ]["id"]

    else:
        st.warning(
            "No departments are available. "
            "Create a department before creating an officer."
        )


# --------------------------------------------------
# PASSWORD DETAILS
# --------------------------------------------------

new_password = st.text_input(
    "Initial password",
    type="password",
    key="admin_new_account_password",
)

confirm_password = st.text_input(
    "Confirm password",
    type="password",
    key="admin_new_account_confirm_password",
)


# --------------------------------------------------
# ACCOUNT RECOVERY DETAILS
# --------------------------------------------------

st.markdown("#### Account Recovery Details")

security_questions = [
    "What was the name of your first school?",
    "What is the name of your childhood best friend?",
    "What is your favourite childhood memory?",
    "What was the name of your first pet?",
    "What is the name of your favourite teacher?",
]

security_question = st.selectbox(
    "Security question",
    security_questions,
    key="admin_new_account_security_question",
)

security_answer = st.text_input(
    "Security answer",
    type="password",
    key="admin_new_account_security_answer",
)

confirm_security_answer = st.text_input(
    "Confirm security answer",
    type="password",
    key="admin_new_account_confirm_security_answer",
)


# --------------------------------------------------
# CREATE ACCOUNT BUTTON
# --------------------------------------------------

create_account = st.button(
    "Create Account",
    type="primary",
    use_container_width=True,
    key="admin_create_account_button",
)


if create_account:

    if not all([
        new_name.strip(),
        new_email.strip(),
        new_password,
        confirm_password,
        new_phone.strip(),
        new_address.strip(),
        security_question,
        security_answer.strip(),
        confirm_security_answer.strip(),
    ]):

        st.error("Please complete all required fields.")

    elif new_password != confirm_password:

        st.error("The passwords do not match.")

    elif security_answer.strip().casefold() != (
        confirm_security_answer.strip().casefold()
    ):

        st.error("The security answers do not match.")

    elif (
        new_role == "officer"
        and new_department_id is None
    ):

        st.error(
            "Please create a department before creating an officer."
        )

    else:

        try:

            success, message = create_user_account_by_admin(
                full_name=new_name.strip(),
                email=new_email.strip(),
                password=new_password,
                role=new_role,
                phone=new_phone.strip(),
                address=new_address.strip(),
                department_id=new_department_id,
                security_question=security_question,
                security_answer=security_answer.strip(),
            )

            if success:

                if new_role == "officer":

                    uid_marker = "Officer UID:"

                    if uid_marker in message:

                        new_uid = message.split(
                            uid_marker,
                            1,
                        )[1].strip()

                        st.session_state[
                            "pending_officer_registration"
                        ] = {
                            "name": new_name.strip(),
                            "email": new_email.strip(),
                            "phone": new_phone.strip(),
                            "address": new_address.strip(),
                            "uid": new_uid,
                        }

                        st.rerun()

                    else:
                        st.error(
                            "Officer was created, but the UID "
                            "could not be extracted from the response. "
                            f"System message: {message}"
                        )

                else:
                    st.session_state[
                        "admin_registration_notice"
                    ] = message

                    st.rerun()

            else:
                st.error(message)

        except Exception as error:
            st.error(
                f"Could not create account: {error}"
            )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "CivicTrack is a project prototype. Account and complaint data "
    "are stored in the application's local database."
)
