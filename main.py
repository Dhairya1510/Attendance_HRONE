import os
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# Load credentials
USERNAME = os.getenv("HRONE_USERNAME")
PASSWORD = os.getenv("HRONE_PASSWORD")
EMPLOYEE_ID = os.getenv("EMPLOYEE_ID")

def get_access_token():
    url = "https://gateway.hrone.cloud/oauth2/token"
    payload = f"username={USERNAME}&password={PASSWORD}&grant_type=password&loginType=1&companyDomainCode=handyonline&isUpdated=0&validSource=Y&deviceName=Chrome-mac-os-x-15"

    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer',
        'content-type': 'application/x-www-form-urlencoded',
        'domaincode': 'handyonline',
    }

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        user = data.get("userName")
        return data.get("access_token")
        print("login successful for username:{user}")
    else:
        print("Login failed:", response.status_code, response.text)
        return None

def mark_attendance(token):
    url = "https://app.hrone.cloud/api/timeoffice/mobile/checkin/Attendance/Request"
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    punch_time = now.strftime("%Y-%m-%dT%H:%M")

    payload = {
        "requestType": "A",
        "applyRequestSource": 10,
        "employeeId": int(EMPLOYEE_ID),
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
        "attendanceType": "Online"
    }

    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f'Bearer {token}',
        'content-type': 'application/json',
        'domaincode': 'handyonline',
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        print("Attendance marked successfully for {EMPLOYEE_ID}")
        print(response.json())
    else:
        print("Attendance failed:", response.status_code, response.text)

if __name__ == "__main__":
    token = get_access_token()
    if token:
        mark_attendance(token)
