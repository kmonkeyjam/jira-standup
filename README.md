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

Set your jira token:
Create a classic token: https://id.atlassian.com/manage-profile/security/api-tokens
```bash
export JIRA_API_TOKEN=XXXX
```

Run the script with start and end time:
```bash
python get_jira_updates.py --start 10:00 --end 11:00
```
