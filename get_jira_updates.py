import requests
from requests.auth import HTTPBasicAuth
import datetime
import os

# === CONFIGURATION ===
JIRA_BASE_URL = "https://harness.atlassian.net"
JIRA_PROJECT_KEY = "IR"
DAYS_BACK = 1
EMAIL = "tina.huang@harness.io"
API_TOKEN = os.getenv("JIRA_API_TOKEN")  # Store your token securely
MAX_RESULTS = 50

# === AUTH ===
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {
    "Accept": "application/json"
}

def get_recent_issues():
    today = datetime.date.today()
    start_time = f"{today} 10:00"
    end_time = f"{today} 11:00"
    jql = f'project = IR AND updated >= "{start_time}" AND updated <= "{end_time}"'
    params = {
        "jql": jql,
        "expand": "changelog",
        "maxResults": MAX_RESULTS,
        "fields": ["key", "assignee"]
    }

    try:
        response = requests.get(f"{JIRA_BASE_URL}/rest/api/3/search", headers=headers, auth=auth, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching recent issues: {e}")
        return []

    data = response.json()
    print(f"Found {len(data.get('issues', []))} issues")
    return data.get("issues", []), start_time, end_time

def get_issue_comments(issue_key):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching comments for issue {issue_key}: {e}")
        return []

    return response.json().get("comments", [])

def print_issue_updates(issue, start_time, end_time):
    if not isinstance(issue, dict):
        print(f"Unexpected issue format: {issue}")
        return

    key = issue.get("key", "NO-KEY")
    fields = issue.get("fields", {})
    if not fields:
        print(f"No fields found for issue {key}")
    
    assignee = fields.get("assignee", {})
    assignee_name = assignee.get("displayName") if assignee else "Unassigned"
    
    # Convert time strings to datetime objects for comparison
    start_dt = datetime.datetime.strptime(f"{start_time}:00", "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.datetime.strptime(f"{end_time}:00", "%Y-%m-%d %H:%M:%S")

    # Combine and sort all updates by timestamp
    updates = []
    
    # Add status changes
    for history in issue.get("changelog", {}).get("histories", []):
        created_time = datetime.datetime.strptime(history['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
        if start_dt <= created_time <= end_dt:
            for item in history.get("items", []):
                if item["field"] == "status":
                    updates.append({
                        'time': history['created'],
                        'type': 'STATUS',
                        'content': f"{item['fromString']} -> {item['toString']}"
                    })

    # Add comments
    comments = get_issue_comments(key)
    for comment in comments:
        created_time = datetime.datetime.strptime(comment['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
        if start_dt <= created_time <= end_dt:
            # Extract text from ADF format
            comment_text = ""
            try:
                for content in comment['body']['content']:
                    if content['type'] == 'paragraph':
                        for text_node in content['content']:
                            if text_node['type'] == 'text':
                                comment_text += text_node['text']
            except (KeyError, IndexError):
                comment_text = "[Complex content]"
            
            updates.append({
                'time': comment['created'],
                'type': 'COMMENT',
                'content': f"{comment['author']['displayName']}: {comment_text}"
            })

    # Only print the header if we have updates in the time window
    if updates:
        print(f"\n=== {key} - {assignee_name} ===")
        print("Updates:")
        
        # Sort all updates by timestamp
        updates.sort(key=lambda x: x['time'])
        
        # Print updates in chronological order
        for update in updates:
            print(f"[{update['time']}] {update['type']}: {update['content']}")

if __name__ == "__main__":
    issues, start_time, end_time = get_recent_issues()
    for issue in issues:
        print_issue_updates(issue, start_time, end_time)
