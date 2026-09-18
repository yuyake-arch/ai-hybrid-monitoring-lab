import os

import requests
import streamlit as st


AI_BACKEND_URL = os.getenv(
    "AI_BACKEND_URL",
    "http://10.10.10.20:8000",
)


st.set_page_config(
    page_title="Remediation Operator Console",
    page_icon="🛠️",
    layout="wide",
)

st.title("Remediation Operator Console")

st.caption(
    "Human-in-the-loop remediation management "
    "for the AI-Assisted Hybrid Monitoring Lab"
)

st.subheader("Remediation Proposals")


try:
    response = requests.get(
        f"{AI_BACKEND_URL}/remediation/",
        timeout=5,
    )

    response.raise_for_status()
    remediations = response.json()

    if not remediations:
        st.info("No remediation proposals found.")

    else:
        table_rows = []

        for item in remediations:
            table_rows.append(
                {
                    "remediation_id": item.get("remediation_id"),
                    "event_id": item.get("event_id"),
                    "host": item.get("host"),
                    "target_host": item.get("target_host"),
                    "action_id": item.get("action_id"),
                    "risk": item.get("risk"),
                    "status": item.get("status"),
                }
            )

        table_event = st.dataframe(
            table_rows,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="remediation_table",
        )

        selected_rows = table_event.selection.rows

        if not selected_rows:
            st.info(
                "Select a remediation from the table "
                "to view details and available actions."
            )

        else:
            selected_index = selected_rows[0]
            selected = remediations[selected_index]

            selected_id = selected.get("remediation_id")
            status = selected.get("status")

            st.divider()

            #
            # Remediation Details
            #
            st.subheader("Remediation Details")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Remediation ID**")
                st.code(
                    selected.get(
                        "remediation_id",
                        "N/A",
                    )
                )

                st.write("**Incident ID**")
                st.write(
                    selected.get(
                        "event_id",
                        "N/A",
                    )
                )

                st.write("**Host**")
                st.write(
                    selected.get(
                        "host",
                        "N/A",
                    )
                )

                st.write("**Target Host**")
                st.write(
                    selected.get(
                        "target_host",
                        "N/A",
                    )
                )

            with col2:
                st.write("**Status**")
                st.write(
                    selected.get(
                        "status",
                        "N/A",
                    )
                )

                st.write("**Risk**")
                st.write(
                    selected.get(
                        "risk",
                        "N/A",
                    )
                )

                st.write("**Approval Required**")
                st.write(
                    selected.get(
                        "approval_required",
                        "N/A",
                    )
                )

                st.write("**Created At**")
                st.write(
                    selected.get(
                        "created_at",
                        "N/A",
                    )
                )

            st.divider()

            #
            # AI Recommendation
            #
            st.subheader("AI Recommendation")

            ai_actions = selected.get(
                "ai_recommended_actions",
                [],
            )

            if ai_actions:
                for action in ai_actions:
                    st.write(f"- {action}")

            else:
                st.write(
                    "No AI recommendations available."
                )

            #
            # Deterministic Action
            #
            st.subheader(
                "Deterministic Executable Action"
            )

            st.write("**Action ID**")

            st.code(
                selected.get(
                    "action_id",
                    "No executable action available",
                )
            )

            st.write("**Action Description**")

            st.write(
                selected.get(
                    "action_description",
                    "No description available.",
                )
            )

            st.caption(
                "The executable action is selected by "
                "deterministic policy. AI recommendations "
                "do not directly execute infrastructure changes."
            )

            st.divider()

            #
            # Human Decision
            #
            st.subheader("Human Decision")

            if status == "PENDING_APPROVAL":

                st.info(
                    "This remediation is waiting for "
                    "an operator decision."
                )

                username = st.text_input(
                    "Operator username",
                    value="lab-operator",
                    key=f"decision_username_{selected_id}",
                )

                password = st.text_input(
                    "Operator password",
                    type="password",
                    key=f"decision_password_{selected_id}",
                )

                col_approve, col_reject = st.columns(2)

                with col_approve:

                    approve_clicked = st.button(
                        "Approve",
                        type="primary",
                        use_container_width=True,
                        key=f"approve_{selected_id}",
                    )

                    if approve_clicked:
                        try:
                            approve_response = requests.post(
                                (
                                    f"{AI_BACKEND_URL}"
                                    f"/remediation/"
                                    f"{selected_id}"
                                    f"/approve"
                                ),
                                auth=(
                                    username,
                                    password,
                                ),
                                timeout=10,
                            )

                            approve_response.raise_for_status()

                            st.success(
                                "Remediation approved successfully."
                            )

                            st.rerun()

                        except requests.RequestException as exc:
                            st.error(
                                "Failed to approve remediation."
                            )

                            st.code(str(exc))

                with col_reject:

                    reject_clicked = st.button(
                        "Reject",
                        use_container_width=True,
                        key=f"reject_{selected_id}",
                    )

                    if reject_clicked:
                        try:
                            reject_response = requests.post(
                                (
                                    f"{AI_BACKEND_URL}"
                                    f"/remediation/"
                                    f"{selected_id}"
                                    f"/reject"
                                ),
                                auth=(
                                    username,
                                    password,
                                ),
                                timeout=10,
                            )

                            reject_response.raise_for_status()

                            st.success(
                                "Remediation rejected successfully."
                            )

                            st.rerun()

                        except requests.RequestException as exc:
                            st.error(
                                "Failed to reject remediation."
                            )

                            st.code(str(exc))

            else:

                decision_col1, decision_col2 = (
                    st.columns(2)
                )

                with decision_col1:
                    st.write("**Decision By**")
                    st.write(
                        selected.get(
                            "decision_by",
                            "N/A",
                        )
                    )

                with decision_col2:
                    st.write("**Decision At**")
                    st.write(
                        selected.get(
                            "decision_at",
                            "N/A",
                        )
                    )

            #
            # APPROVED
            #
            if status == "APPROVED":

                st.success(
                    "This remediation has been approved "
                    "and is ready for execution."
                )

                st.divider()

                st.subheader("Automation Execution")

                username = st.text_input(
                    "Operator username",
                    value="lab-operator",
                    key=f"execute_username_{selected_id}",
                )

                password = st.text_input(
                    "Operator password",
                    type="password",
                    key=f"execute_password_{selected_id}",
                )

                execute_clicked = st.button(
                    "Execute Remediation",
                    type="primary",
                    use_container_width=True,
                    key=f"execute_{selected_id}",
                )

                if execute_clicked:
                    try:
                        execute_response = requests.post(
                            (
                                f"{AI_BACKEND_URL}"
                                f"/remediation/"
                                f"{selected_id}"
                                f"/execute"
                            ),
                            auth=(
                                username,
                                password,
                            ),
                            timeout=150,
                        )

                        execute_response.raise_for_status()

                        execution_result = (
                            execute_response.json()
                        )

                        st.success(
                            "Remediation execution completed."
                        )

                        st.subheader(
                            "Automation Result"
                        )

                        result_col1, result_col2 = (
                            st.columns(2)
                        )

                        with result_col1:
                            st.write("**Status**")
                            st.write(
                                execution_result.get(
                                    "status",
                                    "N/A",
                                )
                            )

                            st.write("**Success**")
                            st.write(
                                execution_result.get(
                                    "success",
                                    "N/A",
                                )
                            )

                            st.write("**Changed**")
                            st.write(
                                execution_result.get(
                                    "changed",
                                    "N/A",
                                )
                            )

                        with result_col2:
                            st.write("**Return Code**")
                            st.write(
                                execution_result.get(
                                    "return_code",
                                    "N/A",
                                )
                            )

                            st.write("**Executed By**")
                            st.write(
                                execution_result.get(
                                    "executed_by",
                                    "N/A",
                                )
                            )

                            st.write(
                                "**Execution Finished At**"
                            )
                            st.write(
                                execution_result.get(
                                    "execution_finished_at",
                                    "N/A",
                                )
                            )

                        st.write("**Result Summary**")

                        st.write(
                            execution_result.get(
                                "result_summary",
                                "No result summary available.",
                            )
                        )

                    except requests.RequestException as exc:
                        st.error(
                            "Failed to execute remediation."
                        )

                        st.code(str(exc))

            #
            # REJECTED
            #
            elif status == "REJECTED":

                st.warning(
                    "This remediation was rejected "
                    "by the operator."
                )

            #
            # SUCCESS / FAILED
            #
            elif status in ("SUCCESS", "FAILED"):

                st.divider()

                st.subheader("Automation Result")

                if status == "SUCCESS":
                    st.success(
                        "Remediation execution completed "
                        "successfully."
                    )

                else:
                    st.error(
                        "Remediation execution failed."
                    )

                result_col1, result_col2 = (
                    st.columns(2)
                )

                with result_col1:
                    st.write("**Status**")
                    st.write(
                        selected.get(
                            "status",
                            "N/A",
                        )
                    )

                    st.write("**Success**")
                    st.write(
                        selected.get(
                            "success",
                            "N/A",
                        )
                    )

                    st.write("**Changed**")

                    changed = selected.get(
                        "changed"
                    )

                    if changed == 1:
                        st.write(True)
                    elif changed == 0:
                        st.write(False)
                    else:
                        st.write(
                            changed
                            if changed is not None
                            else "N/A"
                        )

                    st.write("**Return Code**")
                    st.write(
                        selected.get(
                            "return_code",
                            "N/A",
                        )
                    )

                with result_col2:
                    st.write("**Executed By**")
                    st.write(
                        selected.get(
                            "executed_by",
                            "N/A",
                        )
                    )

                    st.write(
                        "**Execution Started At**"
                    )
                    st.write(
                        selected.get(
                            "execution_started_at",
                            "N/A",
                        )
                    )

                    st.write(
                        "**Execution Finished At**"
                    )
                    st.write(
                        selected.get(
                            "execution_finished_at",
                            "N/A",
                        )
                    )

                st.write("**Result Summary**")

                st.write(
                    selected.get(
                        "result_summary",
                        "No result summary available.",
                    )
                )

            #
            # EXECUTING
            #
            elif status == "EXECUTING":

                st.divider()

                st.subheader("Automation Execution")

                st.info(
                    "Remediation is currently executing."
                )

                st.write("**Executed By**")
                st.write(
                    selected.get(
                        "executed_by",
                        "N/A",
                    )
                )

                st.write(
                    "**Execution Started At**"
                )
                st.write(
                    selected.get(
                        "execution_started_at",
                        "N/A",
                    )
                )


except requests.RequestException as exc:

    st.error(
        "Unable to retrieve remediation proposals "
        "from the AI Backend."
    )

    st.code(str(exc))
