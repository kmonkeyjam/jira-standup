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
    jql = f'project = {JIRA_PROJECT_KEY} AND updated >= -{DAYS_BACK}d'
    params = {
        "jql": jql,
        "expand": "changelog",
        "maxResults": MAX_RESULTS
    }

    response = requests.get(f"{JIRA_BASE_URL}/rest/api/3/search", headers=headers, auth=auth, params=params)
    response.raise_for_status()
    return response.json().get("issues", [])

def get_issue_comments(issue_key):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    response = requests.get(url, headers=headers, auth=auth)
    response.raise_for_status()
    return response.json().get("comments", [])

def print_issue_updates(issue):
    key = issue["key"]
    print(f"\n=== {key} ===")

    # Print changelog
    for history in issue.get("changelog", {}).get("histories", []):
        for item in history.get("items", []):
            if item["field"] == "status":
                print(f"[{history['created']}] STATUS: {item['fromString']} -> {item['toString']}")

    # Print comments
    comments = get_issue_comments(key)
    for comment in comments:
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
        
        print(f"[{comment['created']}] COMMENT by {comment['author']['displayName']}: {comment_text}")

if __name__ == "__main__":
    issues = get_recent_issues()
    for issue in issues:
        print_issue_updates(issue)
