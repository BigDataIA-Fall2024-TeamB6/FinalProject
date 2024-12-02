from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2 import sql, Error
import logging
import requests
import time
import os

import boto3

# Load dotenv file
load_dotenv()


# Logger function
logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Function to create connection to PostgreSQL
def create_connection_to_postgresql(attempts=3, delay=2):
    logger.info("POSTGRESQL - create_connection() - Creating connection to PostgreSQL database")

    # Fetch connection parameters from environment variables
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
            # Establish connection
            conn = psycopg2.connect(**db_params)
            logger.info("POSTGRESQL - create_connection() - Connection to PostgreSQL database established successfully")
            return conn
        except (Error, IOError) as e:
            if attempt == attempts:
                logger.error(f"POSTGRESQL - create_connection() - Failed to connect to PostgreSQL database: {e}")
                return None
            else:
                logger.warning(f"POSTGRESQL - create_connection() - Connection Failed: {e} - Retrying {attempt}/{attempts}")
                time.sleep(delay ** attempt)
                attempt += 1
    return None



# Function to close connection to PostgreSQL
def close_connection(dbconn, cursor=None):
    logger.info("POSTGRESQL - close_connection() - Closing the database connection")
    try:
        if dbconn is not None:
            if cursor is not None:
                cursor.close()
                logger.info("POSTGRESQL - close_connection() - Cursor closed successfully")
            dbconn.close()
            logger.info("POSTGRESQL - close_connection() - Connection closed successfully")
        else:
            logger.warning("POSTGRESQL - close_connection() - Connection does not exist")
    except Exception as e:
        logger.error(f"POSTGRESQL - close_connection() - Error while closing the database connection: {e}")

# Function to get token response
def get_token_response(endpoint, refresh_token):
    logging.info("get_token_response() - Inside get_token_response() function")
    try:
        # Append the refresh token to the endpoint URL
        url = f"{endpoint}{refresh_token}"
        
        # Perform the GET request
        response = requests.get(url)
        
        # Raise an exception for HTTP errors
        response.raise_for_status()
        
        # Return the JSON response
        logger.info("get_token_response() - Token response fetched successfully")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"get_token_response() - Error while fetching token response = {e}")

def format_token_response(token_response):
    logging.info("format_token_response() - Inside format_token_response() function")

    # Extract the message dictionary first
    message = token_response.get("message", {})

    # Extract id_token_claims for nested data
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

    logging.info("format_token_response() - Formatted the response successfully")

    # Return the formatted token response
    return formatted_token_response



import boto3
import requests
import os
import logging

# Assuming logger is set up
logger = logging.getLogger(__name__)

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


def insert_attachment_data(conn, attachment_id, email_id, file_name, content_type, size, s3_url):
    """
    Insert attachment data into the attachments table.
    """
    insert_query = """
        INSERT INTO attachments (id, email_id, name, content_type, size, bucket_url)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor = conn.cursor()
    try:
        cursor.execute(insert_query, (attachment_id, email_id, file_name, content_type, size, s3_url))
        conn.commit()
        logger.info(f"Attachment {file_name} inserted into the database.")
    except Exception as e:
        logger.error(f"Failed to insert attachment {file_name} into database. Error: {e}")
        conn.rollback()
    finally:
        cursor.close()

def upload_attachments_to_s3(user_email, email_id, s3_bucket_name, access_token):
    """
    Upload attachments of a given email ID to an S3 bucket and insert the attachment details into the database.
    """
    logger.info(f"Processing attachments for email ID: {email_id}")

    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Fetch attachments using Microsoft Graph API
    attachment_url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments"
    response = requests.get(
        attachment_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code != 200:
        logger.error(f"Failed to fetch attachments for email ID: {email_id}. Response: {response.text}")
        return

    attachments = response.json().get("value", [])
    if not attachments:
        logger.info(f"No attachments found for email ID: {email_id}.")
        return

    file_extensions = {
        "JSON": [".json"],
        "Image": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
        "CSV": [".csv"],
        "Documents": [".doc", ".docx", ".pdf", ".rtf", ".txt", ".xml"],
        "Spreadsheets": [".xls", ".xlsm", ".xlsx"],
        "Presentations": [".ppt", ".pptx", ".ppsx"],
        "Archives": [".zip", ".rar"],
        "Audio": [".mp3", ".wav"],
        "Video": [".mp4", ".webm"],
    }

    #  base directory structure
    base_dir = f"{user_email}/{email_id}/attachments"

    # Subdirectories for categorizing attachment files 
    subdirectories = {
        category: os.path.join(base_dir, category) for category in file_extensions.keys()
    }

    # Subdirectories in S3 if they don't exist
    for sub_dir in subdirectories.values():
        s3_client.put_object(Bucket=s3_bucket_name, Key=f"{sub_dir}/")

    # Connect to the database
    conn = create_connection_to_postgresql()
    if not conn:
        logger.error("Failed to connect to the PostgreSQL database. Exiting function.")
        return

    # Upload attachments to S3 and insert data into the database
    for attachment in attachments:
        attachment_id = attachment.get("id")
        file_name = attachment.get("name")
        content_bytes = attachment.get("contentBytes")
        content_type = attachment.get("contentType")
        size = attachment.get("size")

        if not file_name or not content_bytes:
            continue

        # Determine the target directory based on file type
        target_dir = None
        for category, extensions in file_extensions.items():
            if any(file_name.lower().endswith(ext) for ext in extensions):
                target_dir = subdirectories.get(category)
                break

        if not target_dir:
            logger.info(f"Skipping unsupported file type: {file_name}")
            continue

        try:
            # Upload file to the S3 directory
            s3_client.put_object(
                Bucket=s3_bucket_name,
                Key=f"{target_dir}/{file_name}",
                Body=content_bytes.encode("utf-8"),
            )

            # Fetch the S3 URL for the uploaded file
            s3_url = f"s3://{s3_bucket_name}/{target_dir}/{file_name}"

            # Log the upload details
            logger.info(f"[SUCCESS] Uploaded attachment {file_name} (ID: {attachment_id}) to S3 bucket {s3_bucket_name}.")
            logger.info(f"Attachment Details: ID: {attachment_id}, Name: {file_name}, Content Type: {content_type}, Size: {size} bytes, S3 URL: {s3_url}")

            # Insert the attachment details into the database
            insert_attachment_data(conn, attachment_id, email_id, file_name, content_type, size, s3_url)

        except Exception as e:
            logger.error(f"[ERROR] Failed to upload {file_name} for email ID: {email_id}. Error: {e}")



def main():
    logger.info("main() - Inside main function")
    refresh_token = os.getenv("REFRESH_TOKEN")
    endpoint = os.getenv("ENDPOINT")
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")


    token_response = get_token_response(endpoint, refresh_token)
    logger.info(f"Airflow - main() - Token Reposnse = {token_response}")

    formatted_token_response = format_token_response(token_response)
    logger.info(f"Airflow - main() - Formatted Token Reposnse = {formatted_token_response}")
    access_token = formatted_token_response['access_token']


    emails_with_attachments = process_emails_with_attachments(access_token, s3_bucket_name)


    for user_email, email_id, has_attachments in emails_with_attachments:
        if has_attachments: 
            upload_attachments_to_s3(user_email, email_id, s3_bucket_name, access_token)

logger.info("main() - Workflow completed")




if __name__ == '__main__':
    main()