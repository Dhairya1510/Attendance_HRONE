import os
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

USERNAME = os.getenv("HRONE_USERNAME")
PASSWORD = os.getenv("HRONE_PASSWORD")
EMPLOYEE_ID = os.getenv("EMPLOYEE_ID")

def get_access_token(username:str, password:str):
    url = "https://gateway.hrone.cloud/oauth2/token"
    payload = f"username={username}&password={password}&grant_type=password&loginType=1&companyDomainCode=handyonline&isUpdated=0&validSource=Y&deviceName=Chrome-mac-os-x-15"

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
        print(f"login successful for username: {user}")
        return data.get("access_token")
    else:
        print("Login failed:", response.status_code, response.text)
        return None

def mark_attendance(token, employee_id):
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
        print(f"Attendance marked successfully for {employee_id} at {punch_time}")
        print(response.json())
    else:
        print("Attendance failed:", response.status_code, response.text)

def check_holiday(token:str, employee_id:int)-> bool:
    url = "https://app.hrone.cloud/api/timeoffice/attendance/Calendar"

    payload = json.dumps({
    "attendanceYear": datetime.now(ZoneInfo("Asia/Kolkata")).year,
    "attendanceMonth": datetime.now(ZoneInfo("Asia/Kolkata")).month,
    "employeeId": employee_id,
    "calendarViewType": "C"
    })
    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f'Bearer {token}',
        'content-type': 'application/json',
        'domaincode': 'handyonline',
    }
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list) and (data[today.day - 1].get("updatedFirstHalfStatus")=="HO" or data[today.day - 1].get("updatedFirstHalfStatus")=="WO"):
            print(f"Today ({today}) is a holiday/weekend.")
            return True
        else:
            print(f"Today ({today}) is not a holiday/weekend.")
            return False
    else:
        print("Failed to fetch holidays:", response.status_code, response.text)
        return False

def check_leave(token:str):
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
    "pagination": {
        "pageNumber": 1,
        "pageSize": 15
    }
    })
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f'Bearer {token}',
        'content-type': 'application/json',
        'domaincode': 'handyonline',
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
                if data_parsed and data_parsed == today.strftime("%Y-%m-%d"):
                    print(f"Leave request found for today : {data_parsed}")
                    return True
        print("No leave requests found for today.")
        return False
    else:
        print("No leave requests found")
        return False

if __name__ == "__main__":
    usernames = USERNAME.split(",")
    passwords = PASSWORD.split(",")
    employee_ids = EMPLOYEE_ID.split(",")
    for i in range(len(usernames)):
        print(f"Processing for {usernames[i]} with employee ID {employee_ids[i]}")
        token = get_access_token(usernames[i], passwords[i])
        if token:
            if not check_holiday(token, int(employee_ids[i])):
                if not check_leave(token):
                    mark_attendance(token, employee_ids[i])
                else:
                    print("Leave request found, skipping attendance marking.")
            else:
                print("Today is a holiday or weekend, skipping attendance marking.")
        else:
            print(f"Failed to get access token for {usernames[i]}")