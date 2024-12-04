import os
import json

def organize_emails_by_category(categorized_emails):
    """
    Organizes emails into categories.
    Returns a dictionary where keys are categories and values are lists of emails.
    """
    categories = {}
    for email in categorized_emails:
        # Get the category of the email, default to "Uncategorized" if missing
        category = email.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = []  # Create a new category if it doesn't exist
        categories[category].append(email)  # Add the email to the category
    return categories

def save_emails_by_category(categories, output_dir="categorized_emails"):
    """
    Saves emails organized by categories into separate JSON files.
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for category, emails in categories.items():
        # Create a filename based on the category
        file_name = f"{category}.json"
        file_path = os.path.join(output_dir, file_name)
        try:
            # Write the emails of the category into a JSON file
            with open(file_path, 'w') as file:
                json.dump(emails, file, indent=4)
            print(f"Saved emails for category '{category}' in {file_path}")
        except Exception as e:
            print(f"Error while saving category '{category}': {e}")

if __name__ == "__main__":
    # Input file containing categorized emails
    categorized_emails_file = "categorized_emails.json"

    # Load categorized emails from the file
    try:
        with open(categorized_emails_file, 'r') as file:
            categorized_emails = json.load(file)
        print("Categorized emails loaded successfully.")
    except FileNotFoundError:
        print(f"Error: File '{categorized_emails_file}' not found.")
        categorized_emails = []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
        categorized_emails = []

    # Organize emails by category
    if categorized_emails:
        categories = organize_emails_by_category(categorized_emails)
        
        # Save categorized emails into separate files
        save_emails_by_category(categories)
    else:
        print("No categorized emails to process.")
