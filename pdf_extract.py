from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2 import sql, Error
import logging
import requests
import time
import os
import boto3
from unidecode import unidecode
import fitz  
import json
import os
import filetype


# Load dotenv file
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Downloads folder
downloads_folder = "./downloads" 

# Function to create connection to PostgreSQL
def create_connection_to_postgresql(attempts=3, delay=2):
    logger.info("POSTGRESQL - create_connection() - Creating connection to PostgreSQL database")
    db_params = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USERNAME"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT"))
    }
    attempt = 1
    while attempt <= attempts:
        try:
            conn = psycopg2.connect(**db_params)
            logger.info("POSTGRESQL - Connection established successfully")
            return conn
        except (Error, IOError) as e:
            if attempt == attempts:
                logger.error(f"POSTGRESQL - Failed to connect: {e}")
                return None
            logger.warning(f"POSTGRESQL - Connection Failed: {e} - Retrying {attempt}/{attempts}")
            time.sleep(delay ** attempt)
            attempt += 1
    return None

# Function to close connection to PostgreSQL
def close_connection(dbconn, cursor=None):
    logger.info("POSTGRESQL - Closing the database connection")
    try:
        if dbconn:
            if cursor:
                cursor.close()
                logger.info("POSTGRESQL - Cursor closed successfully")
            dbconn.close()
            logger.info("POSTGRESQL - Connection closed successfully")
    except Exception as e:
        logger.error(f"POSTGRESQL - Error while closing the connection: {e}")

# Function to get token response
def get_token_response(endpoint, refresh_token):
    try:
        url = f"{endpoint}{refresh_token}"
        response = requests.get(url)
        response.raise_for_status()
        logger.info("Token response fetched successfully")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching token response: {e}")

# Function to format token response
def format_token_response(token_response):
    message = token_response.get("message", {})
    id_token_claims = message.get("id_token_claims", {})
    formatted_token_response = {
        "id": id_token_claims.get("oid"),
        "tenant_id": id_token_claims.get("tid"),
        "name": id_token_claims.get("name"),
        "email": id_token_claims.get("preferred_username"),
        "token_type": message.get("token_type"),
        "access_token": message.get("access_token"),
        "refresh_token": message.get("refresh_token"),
        "id_token": message.get("id_token"),
        "scope": message.get("scope"),
        "token_source": message.get("token_source"),
        "iat": datetime.utcfromtimestamp(id_token_claims.get("iat", 0)),
        "exp": datetime.utcfromtimestamp(id_token_claims.get("exp", 0)),
        "nonce": id_token_claims.get("aio"),
    }
    logger.info("Formatted the response successfully")
    return formatted_token_response

def process_emails_with_attachments(auth, s3_bucket_name):
    """
    Process emails with attachments from the database and upload attachments to S3.
    """
    query = """
    SELECT 
        u.email AS user_email,
        e.id AS email_id,
        e.has_attachments
    FROM 
        emails e
    JOIN 
        senders s ON s.email_id = e.id
    JOIN 
        recipients r ON r.email_id = e.id
    JOIN 
        users u ON (u.email = s.email_address OR u.email = r.email_address)
    WHERE 
        e.has_attachments = TRUE;
    """

    conn = create_connection_to_postgresql()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            emails_with_attachments = cursor.fetchall()
            return emails_with_attachments
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
        finally:
            close_connection(conn, cursor)
    else:
        print("Failed to connect to the database.")
        return []
    

# Function to normalize file paths
def normalize_path(file_path):
    """
    Normalize a file path to handle special characters and system-specific path separators.
    """
    return os.path.normpath(file_path)


# Function to download attachments from S3
def download_attachments_from_s3(user_email, email_id, s3_bucket_name):
    logger.info(f"Downloading attachments for email ID: {email_id} from S3.")
    s3_client = boto3.client("s3")
    base_download_dir = f"./downloads/{user_email}/{email_id}/attachments"
    base_s3_prefix = f"{user_email}/{email_id}/attachments"
    try:
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix=base_s3_prefix)
        if "Contents" not in response:
            logger.info(f"No attachments found in S3 for email ID: {email_id}.")
            return
        for obj in response["Contents"]:
            key = obj["Key"]
            relative_path = key[len(base_s3_prefix):].lstrip("/")
            local_file_path = os.path.join(base_download_dir, relative_path)
            create_local_directory(os.path.dirname(local_file_path))
            if os.path.exists(local_file_path):
                logger.info(f"File already exists locally: {local_file_path}. Skipping download.")
                continue
            s3_client.download_file(s3_bucket_name, key, local_file_path)
            logger.info(f"Downloaded {key} to {local_file_path}")
    except Exception as e:
        logger.error(f"Failed to download attachments for email ID: {email_id}. Error: {e}")




# Function to create directories
def create_local_directory(directory_path):
    """
    Creates a directory if it doesn't exist.
    """
    directory_path = normalize_path(directory_path)
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        logger.info(f"Created directory: {directory_path}")

# Function to process PDFs in the downloads folder
def process_pdfs_in_downloads():
    """
    Iterates through all folders in the downloads directory and processes files with a .pdf extension.
    """
    logger.info("Processing PDFs in downloads folder...")
    for root, dirs, files in os.walk(normalize_path(downloads_folder)):
        logger.debug(f"Inspecting directory: {root}")
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = normalize_path(os.path.join(root, file))
                base_dir = normalize_path(os.path.splitext(pdf_path)[0])
                logger.info(f"Found PDF: {pdf_path}")
                try:
                    extract_content_from_pdf(pdf_path, base_dir)
                except Exception as e:
                    logger.error(f"Error while processing {pdf_path}: {e}")
            else:
                logger.debug(f"Skipping non-PDF file: {file}")

# Function to extract content from a PDF
def extract_content_from_pdf(pdf_path, base_dir):
    """
    Extract content from a PDF with validation of the file type and additional debugging.
    """
    try:
        # Normalize paths
        pdf_path = normalize_path(pdf_path)
        base_dir = normalize_path(base_dir)
        
        # Log the file path
        logger.debug(f"Checking file path: {pdf_path}")
        if not os.path.exists(pdf_path):
            logger.error(f"File does not exist: {pdf_path}")
            return

        # Check the file size
        file_size = os.path.getsize(pdf_path)
        logger.debug(f"File size: {file_size} bytes for {pdf_path}")
        if file_size == 0:
            logger.error(f"File is empty: {pdf_path}")
            return

        # Check the file type
        logger.debug(f"Validating file type for: {pdf_path}")
        guessed_type = filetype.guess(pdf_path)
        if guessed_type is None:
            logger.error(f"Unable to determine file type for: {pdf_path}. Skipping.")
            return

        if guessed_type.mime != 'application/pdf':
            logger.error(f"File is not a valid PDF: {pdf_path}. Detected type: {guessed_type.mime}. Skipping.")
            return

        logger.info(f"File type verified as PDF for: {pdf_path}")

        # Open the PDF file
        document = fitz.open(pdf_path)
        logger.debug(f"Opened PDF successfully: {pdf_path}")

        # Prepare directories for saving extracted data
        json_dir = normalize_path(os.path.join(base_dir, 'JSON'))
        img_dir = normalize_path(os.path.join(base_dir, 'Image'))
        csv_dir = normalize_path(os.path.join(base_dir, 'CSV'))
        create_local_directory(json_dir)
        create_local_directory(img_dir)
        create_local_directory(csv_dir)

        # Process each page in the document
        for page_num in range(document.page_count):
            page = document[page_num]
            page_id = page_num + 1
            page_content = {"page_id": page_id, "content": {}}

            # Extract text
            text = page.get_text("text")
            if text.strip():
                logger.info(f"Extracted text for page {page_id}")
                page_content["content"]["text"] = unidecode(text)

            # Extract images
            images = page.get_images(full=True)
            image_list = []
            for img_index, img in enumerate(images):
                xref = img[0]
                img_data = document.extract_image(xref)
                img_ext = img_data["ext"]
                img_bytes = img_data["image"]
                img_name = f"page_{page_id}_image_{img_index}.{img_ext}"
                img_path = normalize_path(os.path.join(img_dir, img_name))
                with open(img_path, "wb") as img_file:
                    img_file.write(img_bytes)
                image_list.append(img_name)

            if image_list:
                logger.info(f"Extracted {len(image_list)} images for page {page_id}")
                page_content["content"]["images"] = image_list

            # Save extracted content as JSON
            json_file_path = normalize_path(os.path.join(json_dir, f"page_{page_id}.json"))
            with open(json_file_path, "w") as json_file:
                json.dump(page_content, json_file, indent=4)
                logger.info(f"Saved JSON for page {page_id}")

    except Exception as e:
        logger.error(f"Failed to process PDF {pdf_path}: {e}")

# Main function
def main():
    logger.info("Starting the workflow")
    refresh_token = os.getenv("REFRESH_TOKEN")
    endpoint = os.getenv("ENDPOINT")
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")
    token_response = get_token_response(endpoint, refresh_token)
    if not token_response:
        logger.error("Failed to fetch token response. Exiting workflow.")
        return
    formatted_token_response = format_token_response(token_response)
    access_token = formatted_token_response['access_token']
    emails_with_attachments = process_emails_with_attachments(access_token, s3_bucket_name)
    if not emails_with_attachments:
        logger.info("No emails with attachments found. Exiting workflow.")
        return
    for user_email, email_id, has_attachments in emails_with_attachments:
        if has_attachments:
            download_attachments_from_s3(user_email, email_id, s3_bucket_name)
    process_pdfs_in_downloads()
    logger.info("Workflow completed successfully")

if __name__ == "__main__":
    main()

