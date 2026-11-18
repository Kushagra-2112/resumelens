import streamlit as st
import sys
from pathlib import Path

# Put the repo root on sys.path so `from frontend.views import ...` resolves
# regardless of the directory streamlit was launched from.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure page
st.set_page_config(
    page_title="ResumeLens",
    page_icon=":material/manage_search:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auth state. Populated by Supabase sign-in / sign-up / OAuth.
for key, default in [
    ("access_token", None),
    ("refresh_token", None),
    ("user_id", None),
    ("user_email", None),
    ("auth_error", None),
    ("auth_info", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# If we just came back from Google OAuth, Supabase appends `?code=<authcode>`
# to the redirect URL. Exchange it for a session before rendering anything.
if (
    not st.session_state.access_token
    and "code" in st.query_params
):
    from frontend.services import supabase_client
    result = supabase_client.exchange_code_for_session(st.query_params["code"])

    # Always clear the ?code= param so a refresh doesn't try to re-exchange.
    st.query_params.clear()
    if "error" in result:
        st.session_state.auth_error = f"Google sign-in failed: {result['error']}"
    else:
        st.session_state.access_token  = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_id       = result["user_id"]
        st.session_state.user_email    = result["email"]
        st.rerun()

# Load custom CSS
def load_css():
    try:
        css_path = Path(__file__).parent / 'assets' / 'styles.css'
        with open(css_path, 'r', encoding='utf-8') as f:
            return f'<style>{f.read()}</style>'
    except FileNotFoundError:
        return ''

st.markdown(load_css(), unsafe_allow_html=True)

# Initialize session state for view management
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'landing'

BRAND_HTML = (
    '<div class="brand">'
    '<svg width="30" height="30" viewBox="0 0 28 28" aria-hidden="true">'
    '<rect width="28" height="28" rx="8" fill="#0E7C86"/>'
    '<circle cx="13" cy="13" r="6" fill="none" stroke="#fff" stroke-width="2.4"/>'
    '<path d="M17.6 17.6L21.5 21.5" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>'
    '</svg>'
    '<div class="brand-name">Resume<span>Lens</span></div>'
    '</div>'
)

NAV = [
    ("landing",   "Home"),
    ("scorer",    "ATS scorer"),
    ("history",   "History"),
    ("resources", "Resources"),
]

# Sidebar navigation
with st.sidebar:
    st.markdown(BRAND_HTML, unsafe_allow_html=True)

    for view_key, label in NAV:
        active = st.session_state.current_view == view_key
        if st.button(
            label,
            key=f"nav_{view_key}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            st.session_state.current_view = view_key
            st.rerun()

    st.markdown("---")
    st.markdown("### Account")

    from frontend.services import supabase_client

    if st.session_state.access_token:
        st.caption(f"Signed in as **{st.session_state.user_email}**")
        if st.button("Sign out", key="sign_out", use_container_width=True):
            supabase_client.sign_out()
            for k in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[k] = None
            st.rerun()
    else:
        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None
        if st.session_state.auth_info:
            st.info(st.session_state.auth_info)
            st.session_state.auth_info = None

        tab_in, tab_up = st.tabs(["Sign in", "Sign up"])

        with tab_in:
            with st.form("signin_form", clear_on_submit=False):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_pw")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                result = supabase_client.sign_in_with_password(email, password)
                if "error" in result:
                    st.session_state.auth_error = result["error"]
                else:
                    st.session_state.access_token  = result["access_token"]
                    st.session_state.refresh_token = result["refresh_token"]
                    st.session_state.user_id       = result["user_id"]
                    st.session_state.user_email    = result["email"]
                st.rerun()

        with tab_up:
            with st.form("signup_form", clear_on_submit=False):
                email_up = st.text_input("Email", key="signup_email")
                password_up = st.text_input("Password (min 6 characters)", type="password", key="signup_pw")
                submitted_up = st.form_submit_button("Create account", use_container_width=True)
            if submitted_up:
                result = supabase_client.sign_up_with_password(email_up, password_up)
                if "error" in result:
                    st.session_state.auth_error = result["error"]
                elif result.get("pending_confirmation"):
                    st.session_state.auth_info = (
                        f"Check your inbox. We sent a confirmation email to {result['email']}."
                    )
                else:
                    st.session_state.access_token  = result["access_token"]
                    st.session_state.refresh_token = result["refresh_token"]
                    st.session_state.user_id       = result["user_id"]
                    st.session_state.user_email    = result["email"]
                st.rerun()

        st.markdown(
            "<div style='text-align:center; margin: 10px 0; color:#5B6577; font-size:.9rem;'>or</div>",
            unsafe_allow_html=True,
        )

        oauth = supabase_client.google_oauth_url()
        if "error" in oauth:
            st.caption(f"Google sign-in unavailable: {oauth['error']}")
        else:
            st.link_button(
                "Continue with Google",
                url=oauth["url"],
                use_container_width=True,
            )

# Main content area - render based on current view
if st.session_state.current_view == 'landing':
    from frontend.views import landing
    landing.render()

elif st.session_state.current_view == 'scorer':
    from frontend.views import scorer
    scorer.render()

elif st.session_state.current_view == 'history':
    from frontend.views import history
    history.render()

elif st.session_state.current_view == 'resources':
    from frontend.views import resources
    resources.render()