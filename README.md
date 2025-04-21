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
Run the script with various time and date options:

```bash
# Get updates between 10:00 and 11:00 today (default behavior)
python get_jira_updates.py

# Specify custom time window for today
python get_jira_updates.py --start 09:00 --end 17:00

# Get updates from the last 2 days
python get_jira_updates.py --days 2

# Get updates for a specific date range
python get_jira_updates.py --start "2025-04-19 09:00" --end "2025-04-21 17:00"

# Show detailed information including timestamps
python get_jira_updates.py --debug
```

The script supports several ways to specify the time window:
- Use `--start` and `--end` with just times (HH:MM) to get updates for today
- Use `--start` and `--end` with full datetime (YYYY-MM-DD HH:MM) for specific dates
- Use `--days` to look back a specific number of days from now
- Combine `--days` with `--start` and `--end` to adjust the time window
