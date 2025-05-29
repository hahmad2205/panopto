import os
import os
import re
import sentry_sdk
import streamlit as st
import subprocess
import subprocess
import sys
import threading
import time
from decouple import config
from queue import Empty, Queue
from sentry_sdk.integrations.logging import LoggingIntegration

from graph import SDRAgent

@st.cache_resource
def install_playwright():
    try:
        # Install playwright browsers
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
        print("Playwright browsers installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing playwright: {e}")

install_playwright()
SENTRY_DSN = config('SENTRY_DSN')

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            LoggingIntegration(),
        ],
        send_default_pii=True,
        environment=os.environ.get("ENVIRONMENT", "development"),
    )

def execute_graph_async(linkedin_url, email, progress_queue):
    """Execute the graph in a separate thread"""

    def progress_callback(msg_type, data):
        progress_queue.put({'type': msg_type, 'data': data})

    try:
        # Create the modified SDRAgent with progress callback
        graph_agent = SDRAgent(progress_callback)

        # Execute the graph
        success, message = graph_agent.invoke_graph(linkedin_url, email)

        # Send final result
        progress_queue.put({
            'type': 'complete',
            'success': success,
            'message': message
        })

    except Exception as e:
        progress_queue.put({
            'type': 'complete',
            'success': False,
            'message': f"An error occurred: {str(e)}"
        })


def check_progress():
    """Check for progress updates and handle completion"""
    try:
        while True:
            update = st.session_state.progress_queue.get_nowait()

            if update['type'] == 'spinner':
                st.session_state.current_step = update['data']

            elif update['type'] == 'status':
                status_data = update['data']
                st.session_state.progress_messages.append(status_data)

            elif update['type'] == 'complete':
                # Handle completion
                st.session_state.api_call_status = update['success']
                st.session_state.api_message = update['message']
                st.session_state.search_complete = True
                st.session_state.run_search = False
                st.session_state.execution_thread = None
                st.session_state.current_step = ""
                break

    except Empty:
        # No updates available
        pass


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- Session state initialization ---
if "run_search" not in st.session_state:
    st.session_state.run_search = False
if "search_complete" not in st.session_state:
    st.session_state.search_complete = False
if "api_call_status" not in st.session_state:
    st.session_state.api_call_status = None
if "api_message" not in st.session_state:
    st.session_state.api_message = ""
if 'progress_queue' not in st.session_state:
    st.session_state.progress_queue = Queue()
if 'execution_thread' not in st.session_state:
    st.session_state.execution_thread = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = ""
if 'progress_messages' not in st.session_state:
    st.session_state.progress_messages = []


# --- Callback for starting search ---
def start_search():
    email = st.session_state.email
    linkedin_url = st.session_state.linkedin_url

    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    valid_email = re.match(email_pattern, email)
    valid_linkedin = linkedin_url.startswith("https://www.linkedin.com/in/")

    if not valid_linkedin:
        st.session_state.api_call_status = False
        st.session_state.api_message = "❌ Please enter a valid LinkedIn URL"
    elif not valid_email:
        st.session_state.api_call_status = False
        st.session_state.api_message = "❌ Please enter a valid email address"
    else:
        st.session_state.run_search = True


# --- Reset function ---
def reset():
    st.session_state.run_search = False
    st.session_state.search_complete = False
    st.session_state.api_call_status = None
    st.session_state.api_message = ""
    st.session_state.linkedin_url = ""
    st.session_state.email = ""
    st.session_state.progress_messages = []
    st.session_state.progress_queue = Queue()


# --- Page Config ---
st.set_page_config(page_title="Panopto SDR Agent", layout="wide")

# --- Render based on authentication ---
if st.session_state.authenticated:
    # Hide Streamlit elements using CSS
    st.markdown(
        """
        <style>
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #f8f9ff !important;  /* or any hex/color you prefer */
                color-scheme: light !important;        /* Prevents switching to dark mode */
            }

            .status-message {
                margin-top: 20px;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
            }

            .status-success {
                background-color: #d4edda;
                color: #155724;
            }

            .status-error {
                background-color: #f8d7da;
                color: #721c24;
            }

            /* Hide Streamlit elements */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}

            /* Container styling */
            .main-container {
                max-width: 1200px !important;
                padding: 0 1rem !important;
                margin: 0 auto !important;
            }

            /* Global font styles */
            * {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }

            /* Form container */
            .form-container {
                background-color: #f8f9ff;
                border-radius: 12px;
                padding: 40px;
                text-align: center;
                margin-bottom: 40px;
            }

            /* Style for Streamlit input fields */
            div[data-baseweb="input"] {
                background-color: #f2f3f5 !important;
                border-radius: 50px !important;
                border: none !important;
                padding: 5px 15px !important;
            }

            div[data-baseweb="input"] > div {
                background-color: transparent !important;
                border: none !important;
            }

            div[data-baseweb="input"] input {
                font-size: 16px !important;
            }

            .stTextInput > div > div > input {
                background-color: white !important;
                border-radius: 8px !important;
                border: 1px solid #e0e0e0 !important;
                padding: 10px 40px !important;
                font-size: 15px !important;
                width: 100% !important;
                box-shadow: none !important;
                color: #666 !important;
                caret-color: black !important;
            }

            .stTextInput > div > div > input::placeholder {
                color: grey !important;
                font-size: 14px !important;
            }

            .stTextInput > div > div > * {
                color: black !important;
            }

            /* Button style override */
            .stButton > button {
                width: 100%;
                background-color: black;
                color: white;
                padding: 14px 20px;
                margin: 8px 0;
                border: none;
                border-radius: 50px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 400;
            }

            /* Card styling */
            .feature-card {
                background-color: #f8f9ff;
                border-radius: 12px;
                padding: 24px;
                height: 100%;
                box-sizing: border-box;
                margin-top: 20px;
            }

            .icon-circle {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            /* Remove extra padding in Streamlit */
            .block-container {
                padding: 0.5rem !important;
                padding-bottom: 0 !important;
                max-width: 100% !important;
            }

            /* Remove spacing between rows */
            [data-testid="stVerticalBlock"] {
                gap: 0 !important;
            }

            /* Fix spacing around columns */
            [data-testid="stHorizontalBlock"] {
                gap: 1rem !important;
            }

            /* Custom CSS for styling */

            /* Input field styling */
            .stTextInput > div > div > input {
                background-color: #f2f3f5 !important;
                border-radius: 50px !important;
                border: none !important;
                padding: 12px 20px !important;
                font-size: 16px !important;
            }
            /* Add margin to input container */
            .stTextInput {
                margin-bottom: 20px !important;
            }

            /* Label styling */
            .input-label {
                text-align: left !important;
                color: #666 !important;
                font-size: 15px !important;
                margin-bottom: 16px !important;
                margin-left: 4px !important;
                display: block !important;
                position: static !important;
                z-index: 1 !important;
                background: none !important;
            }
            /* Button styling */
            .stButton > button {
                width: 100% !important;
                background-color: black !important;
                color: white !important;
                border-radius: 50px !important;
                padding: 12px 20px !important;
                border: none !important;
                font-size: 16px !important;
                font-weight: 500 !important;
                margin-top: 10px !important;
                cursor: pointer !important;
            }
            .stButton > button:hover {
                background-color: #1a1a1a !important;
            }
            /* Container styling */
            [data-testid="stVerticalBlock"] > div > div {
                background-color: transparent !important;
                border: none !important;
                padding: 0 !important;
            }

            /* Loading spinner */
            .spinner {
                width: 40px;
                height: 40px;
                margin: 10px auto;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #000;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Status message */
            .status-message {
                margin-top: 10px;
                margin-bottom: 25px;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
            }

            .status-success {
                background-color: #d4edda;
                color: #155724;
            }

            .status-error {
                background-color: #f8d7da;
                color: #721c24;
            }

            .status-loading {
                background-color: #e2e6ea;
                color: #383d41;
            }

            .main {
                padding: 0rem 1rem;
            }
            .stProgress > div > div > div > div {
                background-color: rgb(114, 134, 211);
            }
            .step-box {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
                text-align: center;
            }
            .big-font {
                font-size: 24px !important;
                font-weight: bold;
                margin-bottom: 10px;
            }

            .stTextInput > div > div > input:disabled {
                -webkit-text-fill-color: gray !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "api_call_status" not in st.session_state:
        st.session_state.api_call_status = None
    if "api_message" not in st.session_state:
        st.session_state.api_message = ""

    # Create a container for the entire app
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    # Header with logo and Deploy text
    col1, col2 = st.columns([1, 1])
    with col1:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "logo.svg")
        st.markdown(
            """
            <div style="text-align: left; margin: 0; padding: 0;">
            """,
            unsafe_allow_html=True,
        )
        st.image(logo_path, width=200)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.run_search and not st.session_state.search_complete:
        st.markdown(
            """
            <div style="display: flex; justify-content: center; align-items: center; width: 100%;">
                <div style="background-color: #C0C0C0; padding: 10px 20px; margin-top: 20px; border-radius: 5px; width: 60%; text-align: center;">
                    ⓘ️  The prospects report generation will take ~2 minutes. Do not refresh or close the page.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Main header and form
    st.markdown(
        """
    <div style="text-align: center; margin: 0px auto 30px auto; max-width: 800px;">
        <h1 style="font-size: 2.2rem; font-weight: 600; margin-bottom: 0; color: #333;">
            Generate AI-Powered PDFs & OutReach Emails
        </h1>
        <h1 style="font-size: 2.2rem; font-weight: 600; margin-top: -2rem; color: #333;">
            That Speak Your Prospect's Language
        </h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Create center column for form with custom width
    _, center_col, _ = st.columns([1, 3.8, 1])

    with center_col:
        # Open outer gray box container
        st.markdown(
            """
        <div style="border-radius: 12px; padding: 20px 60px; text-align: center; width: 100%;">
            <h3 style="font-size: 1.2rem; font-weight: 500; margin: 2px 0; color: #333;">
                Collect valuable insights on potential marketing prospects.
            </h3>
    """,
            unsafe_allow_html=True,
        )

        # Create internal column for form elements - this stays INSIDE the gray box
        internal_col1, internal_form_col, internal_col3 = st.columns([1, 6.8, 1])

        with internal_form_col:
            inputs_disabled = st.session_state.run_search or st.session_state.search_complete

            st.markdown('<div class="input-label">Prospect\'s LinkedIn Profile</div>', unsafe_allow_html=True)
            st.text_input(
                "",
                placeholder="https://www.linkedin.com/in/public-indentifier/",
                label_visibility="collapsed",
                key="linkedin_url",
                disabled=inputs_disabled,
            )

            # Email input with label
            st.markdown('<div class="input-label">Recipient\'s Email</div>', unsafe_allow_html=True)
            st.text_input(
                "",
                placeholder="name@example.com",
                label_visibility="collapsed",
                key="email",
                disabled=inputs_disabled,
            )

            if not st.session_state.run_search and not st.session_state.search_complete:
                # Submit button (on_click)
                st.button("✨ Start Search", key="submit_button", on_click=start_search)

                # If validation fails, show error message
                if st.session_state.api_call_status is False and st.session_state.api_message:
                    st.markdown(
                        f'<div class="status-message status-error">{st.session_state.api_message}</div>',
                        unsafe_allow_html=True,
                    )

            # Once "run_search" is True, start the async execution
            if st.session_state.run_search and not st.session_state.search_complete:
                # Start the execution thread if not already running
                if st.session_state.execution_thread is None:
                    st.session_state.execution_thread = threading.Thread(
                        target=execute_graph_async,
                        args=(st.session_state.linkedin_url, st.session_state.email, st.session_state.progress_queue)
                    )
                    st.session_state.execution_thread.start()

                # Show progress container
                progress_container = st.container()
                with progress_container:
                    # Check for progress updates
                    check_progress()

                    # Show current step if available
                    if st.session_state.current_step:
                        st.markdown(f"""
                            <div style="
                                background-color: #C0C0C0;
                                border-left: 5px solid black;
                                padding: 10px 15px;
                                border-radius: 8px;
                                margin-bottom: 20px;
                                font-size: 16px;
                                color: #1a1a1a;
                                display: flex;
                                align-items: center;
                            ">
                                <div style="
                                    border: 4px solid #f3f3f3;
                                    border-top: 4px solid black;
                                    border-radius: 50%;
                                    width: 18px;
                                    height: 18px;
                                    animation: spin 1s linear infinite;
                                    margin-right: 10px;
                                "></div>
                                <strong>Current Step:</strong> {st.session_state.current_step}
                            </div>

                            <style>
                            @keyframes spin {{
                                0% {{ transform: rotate(0deg); }}
                                100% {{ transform: rotate(360deg); }}
                            }}
                            </style>
                        """, unsafe_allow_html=True)

                    # Show progress messages
                    if st.session_state.progress_messages:
                        st.markdown("**Progress:**")
                        for msg in st.session_state.progress_messages:  # Show last 5 messages
                            status_color = "green" if msg['status'] == 'success' else "red"
                            st.markdown(
                                f'<span style="color:{status_color};">{msg["message"]}</span>',
                                unsafe_allow_html=True
                            )

                    # If still running, rerun after a short delay
                    if st.session_state.run_search:
                        time.sleep(1)
                        st.rerun()

            # Display results and "Start Over"
            if st.session_state.search_complete:
                if st.session_state.api_call_status is not None:
                    status_class = "status-success" if st.session_state.api_call_status else "status-error"
                    st.markdown(
                        f'<div class="status-message {status_class}">{st.session_state.api_message}</div>',
                        unsafe_allow_html=True,
                    )

                st.button("🔁 Start Over", on_click=reset)

        # Close the gray box
        st.markdown("""</div>""", unsafe_allow_html=True)

        # Only show feature cards when not in search process
        if not st.session_state.run_search and not st.session_state.search_complete:
            cols = st.columns(4)

            card_style = """
            <div style="
                background-color: #eef1f9;
                border-radius: 12px;
                padding: 20px;
                height: 250px;
                margin-bottom: 20px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                box-sizing: border-box;
                max-width: 280px;
                margin-left: auto;
                margin-right: auto;
            ">
                <div style="width: 36px; height: 36px; border-radius: 50%; background-color: {icon_bg}; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 18px;">{icon}</span>
                </div>
                <h4 style="font-size: 1rem; font-weight: 600; margin: 14px 0 6px 0; color: #333;">{title}</h4>
                <p style="font-size: 0.85rem; color: #666; line-height: 1.4; flex-grow: 1;">{description}</p>
            </div>
            """

            features = [
                {
                    "icon": "🔍",
                    "icon_bg": "#e8f4ea",
                    "title": "Discover Prospects",
                    "description": "Enter a LinkedIn profile URL and recipient's email to start targeting the right audience."
                },
                {
                    "icon": "🧪",
                    "icon_bg": "#e8eaf6",
                    "title": "Collect Public Data",
                    "description": "Our AI gathers insights from LinkedIn, company websites, news, and online publications."
                },
                {
                    "icon": "📝",
                    "icon_bg": "#fff8e1",
                    "title": "Generate Personalized Pitch",
                    "description": "AI crafts a customized proposal tailored to each prospect's background and needs."
                },
                {
                    "icon": "📧",
                    "icon_bg": "#fce4ec",
                    "title": "Receive Your Report by Email",
                    "description": "Get the full personalized proposal and research report delivered straight to your inbox."
                }
            ]

            for col, feature in zip(cols, features):
                with col:
                    st.markdown(
                        card_style.format(
                            icon=feature["icon"],
                            icon_bg=feature["icon_bg"],
                            title=feature["title"],
                            description=feature["description"]
                        ),
                        unsafe_allow_html=True
                    )

elif not st.session_state.authenticated:
    st.markdown(
        """
    <style>
        /* Style the show password icon */
        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        html, body, [data-testid="stAppViewContainer"] {
            background-color: #f8f9ff !important;  /* or any hex/color you prefer */
            color-scheme: light !important;        /* Prevents switching to dark mode */
        }

        /* Global font styles */
        * {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        .status-message {
            margin-top: 20px;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }

        .status-success {
            background-color: #d4edda;
            color: #155724;
        }

        .status-error {
            background-color: #f8d7da;
            color: #721c24;
        }

        /* Title styling */
        .login-title {
            font-size: 28px !important;
            font-weight: 500 !important;
            color: #333 !important;
            margin-top: 150px !important;
            margin-bottom: 8px !important;
            text-align: center !important;
        }

        /* Subtitle styling */
        .login-subtitle {
            font-size: 14px !important;
            color: #666 !important;
            margin-bottom: 24px !important;
            text-align: center !important;
        }

        /* Input container styling */
        .input-container {
            position: relative;
            margin-bottom: 8px;
        }

        /* Input field styling */
        .stTextInput > div > div > input {
            background-color: white !important;
            border-radius: 8px !important;
            border: 1px solid #e0e0e0 !important;
            padding: 10px 40px !important;
            font-size: 15px !important;
            width: 100% !important;
            box-shadow: none !important;
            color: #666 !important;
            caret-color: black !important;
        }

        .stTextInput > div > div > input::placeholder {
            color: grey !important;
            font-size: 14px !important;
        }

        .stTextInput > div > div > * {
            color: black !important;
        }

        /* Button styling */
        .stButton > button {
            width: 100% !important;
            background-color: black !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            border: none !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            margin-top: 0 !important;
            cursor: pointer !important;
        }

        .stButton > button:hover {
            background-color: #1a1a1a !important;
        }

        /* Block container padding */
        .block-container {
            padding-top: 3rem !important;
            max-width: 100% !important;
        }

        /* Remove extra padding */
        .css-1544g2n {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        .css-1kyxreq {
            justify-content: center !important;
            margin-top: 0 !important;
            gap: 0 !important;
        }

        .css-ocqkz7 {
            gap: 0 !important;
        }

        div[data-testid="stVerticalBlock"] > div {
            gap: 0 !important;
        }

        /* Style for Streamlit input fields */
        div[data-baseweb="input"] {
            background-color: #f2f3f5 !important;
            border-radius: 50px !important;
            border: none !important;
            padding: 5px 15px !important;
        }

        div[data-baseweb="input"] > div {
            background-color: transparent !important;
            border: none !important;
        }

        div[data-baseweb="input"] input {
            font-size: 16px !important;
        }

        /* Remove extra padding in Streamlit */
        .block-container {
            padding: 0.5rem !important;
            padding-bottom: 0 !important;
            max-width: 100% !important;
        }

        /* Custom CSS for styling */

        /* Input field styling */
        .stTextInput > div > div > input {
            background-color: #f2f3f5 !important;
            border-radius: 50px !important;
            border: none !important;
            padding: 12px 20px !important;
            font-size: 16px !important;
        }
        /* Add margin to input container */
        .stTextInput {
            margin-bottom: 8px !important;
        }
        /* Last input before button needs less margin */
        .stTextInput:last-of-type {
            margin-bottom: 12px !important;
        }
        /* Label styling */

        .input-label {
            display: block;
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin-left: 20px;
            text-align: left;
        }
        /* Button styling */
        .stButton > button {
            width: 100% !important;
            background-color: black !important;
            color: white !important;
            border-radius: 50px !important;
            padding: 12px 20px !important;
            border: none !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            margin-top: 0px !important;
            cursor: pointer !important;
        }
        .stButton > button:hover {
            background-color: #1a1a1a !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "logo.svg")
        st.markdown(
            """
            <div style="text-align: left; margin: 0; padding: 0;">
            """,
            unsafe_allow_html=True,
        )
        st.image(logo_path, width=200)
        st.markdown("</div>", unsafe_allow_html=True)

    # Create center column for form
    _, center_col, _ = st.columns([1, 1.2, 1])

    with center_col:
        # Title and subtitle
        st.markdown(
            '<h1 class="login-title">Login to Panopto</h1>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="input-label">Enter Password</div>', unsafe_allow_html=True)

        password = st.text_input(
            "",
            placeholder="Your password",
            type="password",
            label_visibility="collapsed",
            key="password",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Login", key="login_button"):

            if password == config("CORRECT_PASSWORD"):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.markdown(
                    """
                    <div class="status-message status-error">
                        ❌ Incorrect Password
                    </div>
                """,
                    unsafe_allow_html=True,
                )
