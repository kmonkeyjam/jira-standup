## Installation and Setup
The project requires python (> 3.11). It is recommended you use a python venv.
```bash
python3 -m venv .venv
```

To install the project dependencies, activate the venv and run the following commands:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
The script requires the following environment variables to be set:

- `JIRA_BASE_URL`: Your Jira instance URL
- `JIRA_PROJECT_KEY`: Your Jira project key
- `JIRA_EMAIL`: Your Jira email address
- `JIRA_API_TOKEN`: Your Jira API token (Create a classic token: https://id.atlassian.com/manage-profile/security/api-tokens)

## Usage
Run the script with start and end time:
```bash
python get_jira_updates.py --start 10:00 --end 11:00
python get_jira_updates.py --start 10:00 --end 11:00 --debug
