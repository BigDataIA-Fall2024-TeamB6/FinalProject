import json

# Function to load emails from the JSON file
def load_emails(file_path):
    """
    Load emails from the JSON file and return the 'value' field
    containing the list of emails.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data["value"]  # Access the list of emails in 'value'
    except FileNotFoundError:
        print("Error: File not found. Please check the file path.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
    return []

# Provide the path to the JSON file
file_path = "mail_responses.json"

# Load the emails
emails = load_emails(file_path)

# Print the first two emails to inspect their structure
if emails:
    print("First two emails:")
    for email in emails[:2]:  # Show only the first two emails
        print(json.dumps(email, indent=4))  # Pretty print the email
else:
    print("No emails found or unable to load the file.")
