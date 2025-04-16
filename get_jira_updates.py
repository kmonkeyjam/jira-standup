import requests
from requests.auth import HTTPBasicAuth
import datetime
import os
import argparse
from urllib.parse import quote

# === CONFIGURATION ===
JIRA_BASE_URL = "https://harness.atlassian.net"
JIRA_PROJECT_KEY = "IR"
EMAIL = "tina.huang@harness.io"
API_TOKEN = os.getenv("JIRA_API_TOKEN")  # Store your token securely
MAX_RESULTS = 50

def parse_time(time_str):
    try:
        # Parse time in HH:MM format
        return datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid time format. Please use HH:MM (e.g., 10:00)")

# === AUTH ===
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {
    "Accept": "application/json"
}

def get_recent_issues(start_time, end_time):
    today = datetime.date.today()
    start_datetime = f"{today} {start_time}"
    end_datetime = f"{today} {end_time}"
    jql = f'project = IR AND updated >= "{start_datetime}" AND updated <= "{end_datetime}"'
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
    return data.get("issues", []), start_datetime, end_datetime

def get_issue_comments(issue_key):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching comments for issue {issue_key}: {e}")
        return []

    return response.json().get("comments", [])

def get_issue_updates(issue, start_time, end_time):
    """Get updates for a single issue within the time window"""
    if not isinstance(issue, dict):
        return None

    key = issue.get("key", "NO-KEY")
    updates = []
    
    # Convert time strings to datetime objects for comparison
    start_dt = datetime.datetime.strptime(f"{start_time}:00", "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.datetime.strptime(f"{end_time}:00", "%Y-%m-%d %H:%M:%S")
    
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
                'author': comment['author']['displayName'],
                'content': comment_text
            })

    # Sort updates by timestamp
    updates.sort(key=lambda x: x['time'])
    return updates if updates else None

def get_jira_link(key):
    # URL encode the key for safety, though in this case it's probably not needed
    return f"{JIRA_BASE_URL}/browse/{key}"

def print_all_updates(issues, start_time, end_time, debug=False):
    # Group issues by assignee
    assignee_groups = {}
    
    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee", {})
        assignee_name = assignee.get("displayName") if assignee else "Unassigned"
        
        updates = get_issue_updates(issue, start_time, end_time)
        if updates:  # Only include issues with updates in the time window
            if assignee_name not in assignee_groups:
                assignee_groups[assignee_name] = []
            assignee_groups[assignee_name].append({
                "key": issue.get("key"),
                "updates": updates
            })
    
    # Print grouped updates
    if not assignee_groups:
        print("No updates found in the specified time window.")
        return

    for assignee_name, issues in sorted(assignee_groups.items()):
        # Start with assignee name
        print(f"{assignee_name}:")
        
        for issue in issues:
            key = get_jira_link(issue['key'])
            updates_text = []
            
            for update in issue['updates']:
                if debug:
                    if update['type'] == 'COMMENT':
                        updates_text.append(f"[{update['time']}] {update['type']}: {update['author']}: {update['content']}")
                    else:
                        updates_text.append(f"[{update['time']}] {update['type']}: {update['content']}")
                else:
                    updates_text.append(update['content'])
            
            # Format based on number of updates
            if len(updates_text) == 1:
                print(f"{key}: {updates_text[0]}")
            else:
                print(f"{key}:")
                for text in updates_text:
                    print(f"• {text}")
        print()  # Single blank line between assignees

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get Jira updates within a time window')
    parser.add_argument('--start', type=parse_time, default="10:00",
                      help='Start time in HH:MM format (default: 10:00)')
    parser.add_argument('--end', type=parse_time, default="11:00",
                      help='End time in HH:MM format (default: 11:00)')
    parser.add_argument('--debug', action='store_true',
                      help='Show detailed debug information including timestamps')
    
    args = parser.parse_args()
    
    issues, start_time, end_time = get_recent_issues(args.start.strftime("%H:%M"), args.end.strftime("%H:%M"))
    print_all_updates(issues, start_time, end_time, args.debug)
