import requests
from requests.auth import HTTPBasicAuth
import datetime
import os
import argparse
from urllib.parse import quote

# === CONFIGURATION ===
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not all([JIRA_BASE_URL, JIRA_PROJECT_KEY, EMAIL, API_TOKEN]):
    raise ValueError("All environment variables must be set: JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_EMAIL, JIRA_API_TOKEN")

MAX_RESULTS = 50

def parse_time(time_str):
    try:
        # Parse time in HH:MM format
        return datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid time format. Please use HH:MM (e.g., 10:00)")

def parse_datetime(datetime_str):
    try:
        # Try parsing with date and time
        return datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            # Try parsing with just time (use today's date)
            time = datetime.datetime.strptime(datetime_str, "%H:%M").time()
            return datetime.datetime.combine(datetime.date.today(), time)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid datetime format. Please use either 'HH:MM' or 'YYYY-MM-DD HH:MM'")

# === AUTH ===
auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {
    "Accept": "application/json"
}

def get_recent_issues(start_datetime, end_datetime):
    jql = f'project = {JIRA_PROJECT_KEY} AND updated >= "{start_datetime}" AND updated <= "{end_datetime}"'
    params = {
        "jql": jql,
        "expand": "changelog",
        "maxResults": MAX_RESULTS,
        "fields": ["key", "assignee", "summary"]
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
    start_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M")
    end_dt = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M")
    
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

def get_jira_link(key, debug=False):
    """Get either the full Jira link (debug) or just the key (normal mode)"""
    return f"{JIRA_BASE_URL}/browse/{key}" if debug else key

def get_ready_issues(assignee_name):
    """Get issues that are assigned to the person and marked as Ready for development"""
    jql = f'project = {JIRA_PROJECT_KEY} AND assignee = "{assignee_name}" AND status = "Ready for development"'
    params = {
        "jql": jql,
        "fields": ["key", "summary"],
        "maxResults": MAX_RESULTS
    }

    try:
        response = requests.get(f"{JIRA_BASE_URL}/rest/api/3/search", headers=headers, auth=auth, params=params)
        response.raise_for_status()
        return response.json().get("issues", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ready issues: {e}")
        return []

def print_all_updates(issues, start_time, end_time, debug=False):
    # Group issues by assignee
    assignee_groups = {}
    ready_issues = {}
    
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
                "summary": fields.get("summary", "No summary"),
                "updates": updates
            })
            
            # Get ready issues for this assignee if we haven't already
            if assignee_name not in ready_issues and assignee_name != "Unassigned":
                ready_issues[assignee_name] = get_ready_issues(assignee_name)
    
    # Print grouped updates
    if not assignee_groups:
        print("No updates found in the specified time window.")
        return

    for assignee_name, issues in sorted(assignee_groups.items()):
        # Start with assignee name
        print(f"{assignee_name}:")
        
        # Print updates
        for issue in issues:
            key = get_jira_link(issue['key'], debug)
            summary = issue['summary']
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
            print(f"{key} - {summary}")
            if len(updates_text) == 1:
                print(f"• {updates_text[0]}")
            else:
                for text in updates_text:
                    print(f"• {text}")
            print()  # Add a line between issues
        
        # Print ready issues if any exist for this assignee
        if assignee_name in ready_issues and ready_issues[assignee_name]:
            print("Up next:")
            for issue in ready_issues[assignee_name]:
                key = issue['key']
                summary = issue.get('fields', {}).get('summary', 'No summary')
                print(f"• {get_jira_link(key, debug)} - {summary}")
            print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get Jira updates within a time window')
    parser.add_argument('--start', type=parse_datetime, default=None,
                      help='Start time in HH:MM format (uses today) or YYYY-MM-DD HH:MM format')
    parser.add_argument('--end', type=parse_datetime, default=None,
                      help='End time in HH:MM format (uses today) or YYYY-MM-DD HH:MM format')
    parser.add_argument('--days', type=int, default=0,
                      help='Number of past days to include (default: 0, meaning today only)')
    parser.add_argument('--debug', action='store_true',
                      help='Show detailed debug information including timestamps')
    
    args = parser.parse_args()
    
    # Set default times if not provided
    now = datetime.datetime.now()
    if args.start is None:
        args.start = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if args.end is None:
        args.end = now.replace(hour=11, minute=0, second=0, microsecond=0)
    
    # Adjust dates based on days parameter
    if args.days > 0:
        args.start = args.start - datetime.timedelta(days=args.days)
    
    # Format dates consistently without seconds
    start_str = args.start.strftime("%Y-%m-%d %H:%M")
    end_str = args.end.strftime("%Y-%m-%d %H:%M")
    
    issues, start_time, end_time = get_recent_issues(start_str, end_str)
    print_all_updates(issues, start_time, end_time, args.debug)
