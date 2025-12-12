import base64
import hashlib
import http.server
import os
import socketserver
import threading
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()


def _get_env(name, default=None, required=False):
    """Return environment variable value with optional surrounding quotes stripped."""
    raw = os.environ.get(name)
    value = raw if raw is not None else default
    if isinstance(value, str):
        stripped = value.strip()
        if len(stripped) >= 2 and ((stripped[0] == stripped[-1] == '"') or (stripped[0] == stripped[-1] == "'")):
            value = stripped[1:-1]
        else:
            value = stripped
    if required and (value is None or value == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# --- Configuration ---
API_URL = _get_env("API_URL", required=True)
API_SECRET = _get_env("API_SECRET", required=True)
SERVER_PORT = int(_get_env("SERVER_PORT", "8000"))
REFRESH_INTERVAL_SECONDS = int(_get_env("REFRESH_INTERVAL_SECONDS", "15"))

# --- Authentication Credentials ---
USERNAME = _get_env("USERNAME", required=True)
PASSWORD = _get_env("PASSWORD", required=True)

# --- Global variables to store generated HTML parts ---
FULL_HTML_PAGE = "<html><body>Initializing...</body></html>"
TABLE_BODY_HTML = ""

def build_api_url(action, params=None):
    """Builds a valid BigBlueButton API URL with the correct checksum."""
    if params is None:
        params = {}
    query_string = urlencode(params)
    checksum_src = f"{action}{query_string}{API_SECRET}".encode("utf-8")
    checksum = hashlib.sha1(checksum_src).hexdigest()
    if query_string:
        return f"{API_URL}/{action}?{query_string}&checksum={checksum}"
    else:
        return f"{API_URL}/{action}?checksum={checksum}"

def fetch_and_process_data():
    """Fetches and processes data from BBB API in a background thread."""
    global FULL_HTML_PAGE, TABLE_BODY_HTML
    while True:
        get_meetings_url = build_api_url("getMeetings")
        try:
            response = requests.get(get_meetings_url, timeout=10)
            response.raise_for_status()
            xml_data = response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            TABLE_BODY_HTML = f'<tr><td colspan="5">خطا در اتصال به سرور BigBlueButton.</td></tr>'
            time.sleep(REFRESH_INTERVAL_SECONDS)
            continue

        try:
            root = ET.fromstring(xml_data)
            return_code = root.findtext('returncode', 'FAILED')
            
            if return_code != 'SUCCESS':
                message = root.findtext('message', 'An unknown error occurred.')
                TABLE_BODY_HTML = f'<tr><td colspan="5">خطای API: {message}</td></tr>'
            else:
                meetings = root.findall('./meetings/meeting')
                if not meetings:
                    TABLE_BODY_HTML = '<tr><td colspan="5">در حال حاضر کلاسی فعال نیست.</td></tr>'
                else:
                    rows = []
                    for meeting in meetings:
                        meeting_id = meeting.findtext('meetingID', '')
                        moderator_pw = meeting.findtext('moderatorPW', '')
                        attendee_pw = meeting.findtext('attendeePW', '')
                        end_url = build_api_url("end", {'meetingID': meeting_id, 'password': moderator_pw})
                        join_url = build_api_url("join", {
                            'fullName': 'Class Observer', 'meetingID': meeting_id,
                            'password': attendee_pw, 'redirect': 'true', 'listenOnly': 'true'
                        })
                        moderators = [att.findtext('fullName', '') for att in meeting.findall("./attendees/attendee[role='MODERATOR']")]
                        viewers = [att.findtext('fullName', '') for att in meeting.findall("./attendees/attendee[role='VIEWER']")]
                        attendees_formated = ""
                        if moderators: attendees_formated += f"<div class='moderator-list'><b>استاد:</b><br/>{'<br/>'.join(moderators)}</div>"
                        if viewers: attendees_formated += f"<div class='viewer-list'><b>دانشجویان:</b><br/>{'<br/>'.join(viewers)}</div>"
                        rows.append(f"""
                        <tr>
                            <td>{meeting.findtext('meetingName', 'N/A')}</td>
                            <td>{meeting.findtext('createDate', 'N/A')}</td>
                            <td>{meeting.findtext('metadata/bbb-context-name', '--')}</td>
                            <td class="attendees-cell">{attendees_formated or '--'}</td>
                            <td class="actions-cell">
                                <a href="{join_url}" target="_blank" class="button join-button">ورود</a>
                                <a href="{end_url}" onclick="return confirm('آیا از بستن این کلاس اطمینان دارید؟');" target="_blank" class="button end-button">بستن کلاس</a>
                            </td>
                        </tr>""")
                    TABLE_BODY_HTML = "\n".join(rows)
            
            FULL_HTML_PAGE = f"""
            <!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8"/><title>کلاسهای فعال</title><style>
            body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Vazirmatn',Roboto,Oxygen,Ubuntu,Cantarell,'Open Sans','Helvetica Neue',sans-serif;background-color:#f4f4f4;line-height:1.6}}h1{{text-align:center;color:#333}}table{{width:100%;border-collapse:collapse;margin:20px 0;font-size:.9em;box-shadow:0 2px 15px rgba(0,0,0,.1);background-color:#fff}}th,td{{border:1px solid #ddd;padding:12px 15px;text-align:center;vertical-align:middle}}th{{background-color:#007bff;color:#fff;font-weight:700}}tr:nth-child(even){{background-color:#f2f2f2}}tr:hover{{background-color:#e9ecef}}.attendees-cell{{text-align:right}}.moderator-list{{color:#0056b3;margin-bottom:10px}}.viewer-list{{color:#444}}.actions-cell{{min-width:150px}}.button{{display:block;padding:8px 12px;margin:4px auto;border-radius:5px;color:#fff;text-decoration:none;font-weight:700;text-align:center;transition:background-color .2s}}.join-button{{background-color:#28a745}}.join-button:hover{{background-color:#218838}}.end-button{{background-color:#dc3545}}.end-button:hover{{background-color:#c82333}}
            </style></head><body><h1>لیست کلاسهای در حال برگزاری</h1><table><thead><tr><th>نام اتاق</th><th>زمان شروع</th><th>نام دوره</th><th>شرکت‌کنندگان</th><th>عملیات</th></tr></thead>
            <tbody id="meetings-tbody">{TABLE_BODY_HTML}</tbody></table>
            <script>
                async function updateTable() {{ try {{ const response = await fetch('/update'); if (response.ok) {{ const newBodyHtml = await response.text(); document.getElementById('meetings-tbody').innerHTML = newBodyHtml; }} else {{ console.error('Authentication failed or server error during update.'); }} }} catch (error) {{ console.error('Failed to update table:', error); }} }}
                setInterval(updateTable, {REFRESH_INTERVAL_SECONDS * 1000});
            </script></body></html>"""
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            TABLE_BODY_HTML = f'<tr><td colspan="5">خطا در پردازش پاسخ سرور.</td></tr>'
        time.sleep(REFRESH_INTERVAL_SECONDS)

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    """A custom handler that implements Basic Authentication."""

    def is_authenticated(self):
        """Checks the Authorization header for correct credentials."""
        auth_header = self.headers.get('Authorization')
        if auth_header is None:
            return False
        
        # The header is "Basic <base64_encoded_credentials>"
        # We need to decode it
        try:
            encoded_creds = auth_header.split(' ')[1]
            decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
            username, password = decoded_creds.split(':', 1)
            
            return username == USERNAME and password == PASSWORD
        except (IndexError, ValueError, TypeError) as e:
            print(f"Error decoding credentials: {e}")
            return False

    def require_auth(self):
        """Sends a 401 Unauthorized response to trigger the browser's login popup."""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="BBB Monitoring"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Authentication required.</h1>')

    def do_GET(self):
        """Handles GET requests, checking for authentication first."""
        if not self.is_authenticated():
            self.require_auth()
            return

        # If authenticated, proceed to serve the content
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        
        if self.path == '/update':
            self.wfile.write(TABLE_BODY_HTML.encode('utf-8'))
        else:
            self.wfile.write(FULL_HTML_PAGE.encode('utf-8'))

if __name__ == "__main__":
    print(f"Starting server on port {SERVER_PORT}...")
    
    data_thread = threading.Thread(target=fetch_and_process_data, daemon=True)
    data_thread.start()
    
    # Give the data thread a moment to fetch initial data before starting the server
    time.sleep(2) 
    
    with socketserver.TCPServer(("", SERVER_PORT), CustomHandler) as httpd:
        print("Server is now running.")
        httpd.serve_forever()   
