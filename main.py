import os
import base64
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("HRONE_USERNAME")
PASSWORD = os.getenv("HRONE_PASSWORD")
EMPLOYEE_ID = os.getenv("EMPLOYEE_ID")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
GH_PAT = os.getenv("GH_PAT")
GH_REPO = os.getenv("GH_REPO")  # e.g. "Yashnotfound/Attendance_HRONE"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_access_token(username: str, password: str):
    """Password-based login. Returns (access_token, refresh_token) or (None, None).
    Store the plain password in .env — requests will URL-encode it automatically.
    """
    url = "https://gateway.app.hrone.cloud/oauth2/token"
    payload = {
        "username": username,
        "password": password,
        "grant_type": "password",
        "loginType": "1",
        "companyDomainCode": "handyonline",
        "isUpdated": "0",
        "validSource": "Y",
        "deviceName": "Chrome-mac-os-x-15",
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-GB,en;q=0.9",
        "accessmode": "W",
        "content-type": "application/x-www-form-urlencoded",
        "domaincode": "handyonline",
        "origin": "https://app.hrone.cloud",
        "referer": "https://app.hrone.cloud/",
        "x-requested-with": "https://app.hrone.cloud",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Password login successful for: {data.get('userName')}")
        return data.get("access_token"), data.get("refresh_token")
    else:
        print("Password login failed:", response.status_code, response.text)
        return None, None


def refresh_access_token(refresh_token: str, username: str):
    """Refresh-token-based login. Returns (access_token, new_refresh_token) or (None, None)."""
    url = "https://gateway.app.hrone.cloud/oauth2/token"
    payload = {
        "refreshId": refresh_token,
        "companyDomainCode": "handyonline",
        "grant_type": "refresh_token",
        "username": username,
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/x-www-form-urlencoded",
        "domaincode": "handyonline",
        "accessmode": "W",
        "hrone-refresh-header": "true",
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Refresh token login successful for: {data.get('userName')}")
        return data.get("access_token"), data.get("refresh_token")
    else:
        print("Refresh token login failed:", response.status_code, response.text)
        return None, None


# ---------------------------------------------------------------------------
# GitHub Secret write-back
# ---------------------------------------------------------------------------

def update_github_secret(pat: str, repo: str, secret_name: str, secret_value: str) -> bool:
    """
    Encrypts secret_value using the repo's public key and writes it to
    GitHub Actions Secrets via the REST API.
    Requires PyNaCl: pip install PyNaCl
    """
    try:
        from nacl import encoding, public  # type: ignore
    except ImportError:
        print("PyNaCl not installed — cannot rotate secret. Run: pip install PyNaCl")
        return False

    owner, repo_name = repo.split("/", 1)
    base_url = f"https://api.github.com/repos/{owner}/{repo_name}/actions/secrets"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # 1. Fetch the repo's public key
    resp = requests.get(f"{base_url}/public-key", headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch repo public key: {resp.status_code} {resp.text}")
        return False

    key_data = resp.json()
    key_id = key_data["key_id"]
    pub_key_b64 = key_data["key"]
    pub_key_bytes = base64.b64decode(pub_key_b64)

    # 2. Encrypt the secret value with libsodium sealed box
    sealed_box = public.SealedBox(public.PublicKey(pub_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

    # 3. PUT the encrypted secret
    put_resp = requests.put(
        f"{base_url}/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_b64, "key_id": key_id},
    )
    if put_resp.status_code in (201, 204):
        print(f"GitHub secret '{secret_name}' rotated successfully.")
        return True
    else:
        print(f"Failed to update GitHub secret: {put_resp.status_code} {put_resp.text}")
        return False


# ---------------------------------------------------------------------------
# Attendance helpers (unchanged logic)
# ---------------------------------------------------------------------------

def mark_attendance(token: str, employee_id: str):
    url = "https://app.hrone.cloud/api/timeoffice/mobile/checkin/Attendance/Request"
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    punch_time = now.strftime("%Y-%m-%dT%H:%M")

    payload = {
        "requestType": "A",
        "applyRequestSource": 10,
        "employeeId": int(employee_id),
        "latitude": "",
        "longitude": "",
        "geoAccuracy": "",
        "geoLocation": "",
        "punchTime": punch_time,
        "remarks": "",
        "uploadedPhotoOneName": "",
        "uploadedPhotoOnePath": "",
        "uploadedPhotoTwoName": "",
        "uploadedPhotoTwoPath": "",
        "attendanceSource": "W",
        "attendanceType": "Online",
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "domaincode": "handyonline",
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        print(f"Attendance marked successfully for {employee_id} at {punch_time}")
        print(response.json())
    else:
        print("Attendance failed:", response.status_code, response.text)


def check_holiday(token: str, employee_id: str) -> bool:
    url = "https://app.hrone.cloud/api/timeoffice/attendance/Calendar"
    payload = json.dumps({
        "attendanceYear": datetime.now(ZoneInfo("Asia/Kolkata")).year,
        "attendanceMonth": datetime.now(ZoneInfo("Asia/Kolkata")).month,
        "employeeId": employee_id,
        "calendarViewType": "C",
    })
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "domaincode": "handyonline",
    }
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        if (
            data
            and isinstance(data, list)
            and (
                data[today.day - 1].get("updatedFirstHalfStatus") == "HO"
                or data[today.day - 1].get("updatedFirstHalfStatus") == "WO"
            )
        ):
            print(f"Today ({today}) is a holiday/weekend.")
            return True
        else:
            print(f"Today ({today}) is not a holiday/weekend.")
            return False
    else:
        print("Failed to fetch holidays:", response.status_code, response.text)
        return False


def check_leave(token: str) -> bool:
    url = "https://app.hrone.cloud/api/Request/InboxRequest/Search"
    payload = json.dumps({
        "actionStatus": 0,
        "inboxRequestTypeId": 0,
        "employeeFilterValue": "",
        "fromDate": "",
        "toDate": "",
        "filterThreeValue": "",
        "filterInsertId": 0,
        "leaveTypes": "",
        "pagination": {"pageNumber": 1, "pageSize": 15},
    })
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "domaincode": "handyonline",
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        if data and isinstance(data, list):
            for item in data:
                data_unparsed = item.get("requestSubjectSectionTwo")
                if data_unparsed and isinstance(data_unparsed, str):
                    data_content = data_unparsed.split(" to ")[0].split("/")
                    data_parsed = f"{data_content[2]}-{data_content[1]}-{data_content[0]}"
                    print(f"Leave request found: {data_parsed}")
                    if data_parsed == today.strftime("%Y-%m-%d"):
                        print(f"Leave request found for today: {data_parsed}")
                        return True
        print("No leave requests found for today.")
        return False
    else:
        print("No leave requests found")
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not USERNAME or not EMPLOYEE_ID:
        print("Please provide HRONE_USERNAME and EMPLOYEE_ID environment variables.")
        exit(1)

    print(f"Processing attendance for username={USERNAME}, employee_id={EMPLOYEE_ID}")

    access_token = None
    new_refresh_token = None

    # --- Step 1: Obtain access token (prefer refresh flow, fall back to password) ---
    if REFRESH_TOKEN:
        print("Attempting refresh token login...")
        access_token, new_refresh_token = refresh_access_token(REFRESH_TOKEN, USERNAME)

    if not access_token:
        if not PASSWORD:
            print("Refresh token flow failed and no HRONE_PASSWORD set. Cannot authenticate.")
            exit(1)
        print("Falling back to password login...")
        access_token, new_refresh_token = get_access_token(USERNAME, PASSWORD)

    if not access_token:
        print(f"All authentication methods failed for {USERNAME}. Exiting.")
        exit(1)

    # --- Step 2: Rotate the refresh token back into GitHub Secrets ---
    if new_refresh_token and GH_PAT and GH_REPO:
        update_github_secret(GH_PAT, GH_REPO, "REFRESH_TOKEN", new_refresh_token)
    else:
        if not new_refresh_token:
            print("Warning: No new refresh token received — secret not rotated.")
        if not GH_PAT or not GH_REPO:
            print("Warning: GH_PAT or GH_REPO not set — skipping secret rotation (local run?).")

    # --- Step 3: Mark attendance if applicable ---
    if not check_holiday(access_token, EMPLOYEE_ID):
        if not check_leave(access_token):
            mark_attendance(access_token, EMPLOYEE_ID)
        else:
            print("Leave request found, skipping attendance marking.")
    else:
        print("Today is a holiday or weekend, skipping attendance marking.")