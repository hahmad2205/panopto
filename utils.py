import base64
import time
from datetime import datetime

import markdown2
import pdfkit
import requests
import streamlit as st


def show_checklist():
    """
    Display a checklist showing the status of each task in st.session_state.completed_jobs.
    - Show loader if status is "pending"
    - Show tick if status is "completed"
    - Skip tasks with status "initialized"
    """

    if "completed_jobs" not in st.session_state:
        st.warning("No job status available.")
        return False

    checklist_items = [
        (key, status)
        for key, status in st.session_state.completed_jobs.items()
        if status != "initialized"
    ]
    checklist_containers = []

    for key, status in checklist_items:
        container = st.empty()
        checklist_containers.append((key, status, container))

    for key, status, container in checklist_containers:
        pretty_name = key.replace("_", " ").capitalize()

        if status == "completed":
            container.markdown(
                f"""
                <div style="display: flex; align-items: center; margin: 4px 0;">
                    <div style="width: 24px; height: 24px; margin-right: 10px;">
                        <span style="color: #28a745; font-size: 20px;">✓</span>
                    </div>
                    <span style="color: #28a745;">{pretty_name}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif status == "pending":
            container.markdown(
                f"""
                <div style="display: flex; align-items: center; margin: 4px 0;">
                    <div style="width: 24px; height: 24px; margin-right: 10px;">
                        <div class="loader" style="border: 2px solid #ccc; border-top: 2px solid #333; border-radius: 50%; width: 16px; height: 16px; animation: spin 1s linear infinite;"></div>
                    </div>
                    <span style="color: #666;">{pretty_name}...</span>
                </div>
                <style>
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                </style>
                """,
                unsafe_allow_html=True
            )

        time.sleep(0.1)

    return True


def add_progress_styles():
    """
    Add custom CSS styles for the checklist
    """
    st.markdown(
        """
    <style>
    /* Checklist container styling */
    .checklist-container {
        background-color: #f8f9ff;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Loading animation */
    .loader {
        width: 20px;
        height: 20px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Checklist item styling */
    .checklist-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        transition: all 0.3s ease;
    }

    /* Completed item styling */
    .completed {
        color: #28a745;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def call_api(method, url, headers, params=None):
    response = requests.request(method=method, url=url, params=params, headers=headers)
    return response.json()


def parse_datetime(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def markdown_to_pdf(markdown_content):
    html_content = markdown2.markdown(markdown_content, extras=["fenced-code-blocks", "tables", "footnotes"])

    with open("logo.svg", "rb") as image_file:
        encoded_svg = base64.b64encode(image_file.read()).decode("utf-8")

    # Embed in HTML as image
    svg_img_html = f'<img src="data:image/svg+xml;base64,{encoded_svg}" class="svg-icon" alt="Logo">'

    # Create the main HTML content first
    main_html = f"""
        <div class="main-content">
            {svg_img_html}
            {html_content}
        </div>
    """

    # Add footer with CSS to ensure it appears on the last page
    full_html = f"""
        <html>
        <head>
        <meta charset='utf-8'>
        <link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
        <style>
            @page {{
                margin: 50px 40px;
                @bottom-center {{
                    content: element(footer);
                }}
            }}
            body {{
                font-family: "Open Sans", sans-serif;
            }}
            h2 {{
                font-size: 24px;
                font-weight: 600;
                line-height: 1.3;
                color: #202124;
                margin-top: 1.2em;
                margin-bottom: 0.6em;
            }}
            .svg-icon {{
                display: block;
                width: 300px;
                height: auto;
            }}
            #footer {{
                position: running(footer);
                text-align: center;
                color: grey;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }}
            .pagenumber:before {{
                content: counter(page);
            }}
            .pagecount:before {{
                content: counter(pages);
            }}
        </style>
        </head>
        <body>
            {main_html}
            <div id="footer">
                <p>This is an automated report generated by Panopto AI SDR.</p>
            </div>
        </body>
        </html>
        """

    pdf_options = {
        "page-size": "A4",
        "encoding": "UTF-8",
        "enable-local-file-access": "",
        "footer-center": "[page]/[topage]",
        "margin-bottom": "20mm",
        # Use these wkhtmltopdf options to properly handle page breaks and footers
        "footer-html": "footer.html"
    }

    # First create a footer HTML file
    with open("footer.html", "w", encoding="utf-8") as f:
        f.write("""
        <html>
        <head>
            <style>
                .footer {
                    text-align: center;
                    color: grey;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    margin-top: 1.2em;
                }
            </style>
        </head>
        <body>
            <div class="footer">This is an automated report generated by Panopto AI SDR.</div>
        </body>
        </html>
        """)

    pdf = pdfkit.from_string(full_html, output_path=None, options=pdf_options)

    # Clean up the temporary footer file
    import os
    os.remove("footer.html")

    return pdf
