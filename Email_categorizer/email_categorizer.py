import subprocess
import json

# Function to send an email to PHI3 for categorization
def send_to_phi3(email):
    """
    Sends an email's subject and body to PHI3 for categorization.
    Returns the category or an error message if the process fails.
    """
    try:
        prompt = f"Classify the following email: Subject: {email['subject']}. Body: {email['body']['content']}."
        result = subprocess.run(
            ["ollama", "chat", "phi3", "--message", prompt],  # Command to communicate with PHI3
            capture_output=True,  # Capture the output from the process
            text=True  # Decode output as text
        )
        if result.returncode == 0:
            return result.stdout.strip()  # Return the category
        else:
            return f"Error: {result.stderr.strip()}"  # Return the error message
    except KeyError:
        return "Error: Missing 'subject' or 'body' in email."

# Load emails from JSON file
def load_emails(file_path):
    """
    Load emails from the JSON file and return the 'value' field.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get("value", [])  # Access the list of emails in 'value'
    except FileNotFoundError:
        print("Error: File not found. Please check the file path.")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
        return []

# Process all emails and categorize them
def categorize_emails(file_path):
    """
    Categorizes all emails from the input JSON file using PHI3.
    """
    emails = load_emails(file_path)
    categorized_emails = []

    for email in emails:
        category = send_to_phi3(email)  # Send email to PHI3 for categorization
        email['category'] = category  # Add the category to the email
        categorized_emails.append(email)  # Store the categorized email

    return categorized_emails

# Save categorized emails to a new JSON file
def save_categorized_emails(categorized_emails, output_file):
    """
    Save the categorized emails into a new JSON file.
    """
    try:
        with open(output_file, 'w') as file:
            json.dump(categorized_emails, file, indent=4)
        print(f"Categorized emails saved successfully to {output_file}.")
    except Exception as e:
        print(f"Error while saving categorized emails: {e}")

# Main Execution
if __name__ == "__main__":
    # Input and output file paths
    input_file = "mail_responses.json"  # Path to input JSON file
    output_file = "categorized_emails.json"  # Path to save categorized emails

    # Categorize emails and save results
    categorized_emails = categorize_emails(input_file)
    save_categorized_emails(categorized_emails, output_file)
