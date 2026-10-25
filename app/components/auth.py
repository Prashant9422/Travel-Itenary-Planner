import streamlit as st

from app.services.auth_service import authenticate, initialize_auth_db


def require_authentication() -> bool:
    initialize_auth_db()
    username = st.session_state.get("authenticated_user")
    if username:
        with st.sidebar:
            st.caption(f"Signed in as **{username}**")
            if st.button("Log out", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        return True

    st.title("Sign in to the Travel Itinerary Planner")
    st.caption("Accounts are provisioned by the application administrator.")
    with st.form("login_form"):
        username_input = st.text_input("Username", autocomplete="username")
        password_input = st.text_input(
            "Password", type="password", autocomplete="current-password"
        )
        submitted = st.form_submit_button("Sign in")

    if submitted:
        authenticated_username = authenticate(username_input, password_input)
        if authenticated_username is None:
            st.error("Invalid username or password.")
        else:
            st.session_state["authenticated_user"] = authenticated_username
            st.rerun()
    return False
