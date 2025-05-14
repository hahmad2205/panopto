import base64

from decouple import config
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Content,
    Disposition,
    Email,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from streamlit_styles import processing_spinner_style


class EmailClient:
    def send_email(self, linkedin_profile, final_pdf, email_to, storage_path, pdf):
        processing_spinner_style()

        email_template = f"""
                <html>
                    <body>
                        <p>Hello <strong>{email_to.split("@")[0]}</strong>,</p>

                        <p>
                          The AI-generated profile report for the prospect <strong>{linkedin_profile.get('full_name')}</strong> is now ready.
                        </p>

                        <p>You'll find the detailed report attached, including:</p>

                        <ul>
                          <li>Prospect's role, focus areas, and recent initiatives</li>
                          <li>Company overview, growth indicators, and key updates</li>
                          <li>Opportunities and potential conversation starters</li>
                        </ul>

                        <p>
                          You can use this report to personalize your outreach and identify potential value areas where <strong>Panopto</strong> can assist.
                        </p>
                        <p>You can access and download the detailed report via the link below:</p>
                        <a href="{final_pdf}">Download Report</a>

                        <p>Best regards,<br />
                        <strong>Panopto SDR AI</strong></p>
                    </body>
                </html>
                """

        self.send_email_with_attachment(
            email_to=email_to,
            email_subject="Panopto SDR AI Prospect Profile ready for review",
            email_body=email_template,
            attachments=[
                {
                    "filename": storage_path,
                    "content": pdf,
                    "mimetype": "application/pdf",
                }
            ],
        )

    def send_email_with_attachment(self, email_to, email_subject, email_body, attachments=None):
        """Send email with attachments using SendGrid API"""

        message = Mail(
            from_email=Email(config("EMAIL_HOST_USER")),
            to_emails=email_to,
            subject=email_subject,
            html_content=Content("text/html", email_body),
        )

        for attachment in attachments:
            encoded_file = base64.b64encode(attachment["content"]).decode()
            attached_file = Attachment(
                FileContent(encoded_file),
                FileName(attachment["filename"]),
                FileType(attachment["mimetype"]),
                Disposition("attachment"),
            )
            message.add_attachment(attached_file)

        try:
            sg = SendGridAPIClient(config("SENDGRID_API_KEY"))
            sg.send(message)
        except Exception as e:
            print(f"Error sending email: {e}")
