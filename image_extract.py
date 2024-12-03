import os
import base64
import logging
from PIL import Image
import pytesseract
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from dotenv import load_dotenv

openai_api_key = os.getenv("OPENAI_API_KEY")
# Load dotenv file
load_dotenv()
# Downloads folder
downloads_folder = "./downloads" 

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to normalize file paths
def normalize_path(file_path):
    """
    Normalize a file path to handle special characters and system-specific path separators.
    """
    return os.path.normpath(file_path)

# Function to extract text from an image using Tesseract OCR
def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    """
    try:
        image = Image.open(image_path)
        image.verify()  # Verify image file integrity
        image = Image.open(image_path)  # Re-open after verification
        text = pytesseract.image_to_string(image)
        logger.info(f"Extracted text from image {image_path} successfully.")
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from image {image_path}: {e}")
        return None

# Function to encode an image to Base64 format
def encode_image_to_base64(image_path):
    """
    Encode an image to Base64 format.
    """
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode image to Base64: {e}")
        return None

# Function to summarize image content using OpenAI
def summarize_image(image_path, prompt):
    """
    Summarize the image by sending extracted text and Base64 content to OpenAI GPT.
    """
    logger.info(f"Summarizing image: {image_path}")
    try:
        # Extract text from the image
        extracted_text = extract_text_from_image(image_path) or "No text could be extracted from the image."

        # Encode the image to Base64
        img_base64 = encode_image_to_base64(image_path)
        if not img_base64:
            logger.warning(f"Failed to encode image to Base64: {image_path}")
            return "Failed to encode image to Base64 for summarization."

        # Construct the prompt
        full_prompt = (
            f"{prompt}\n\nExtracted Text:\n{extracted_text}\n\n"
            f"Base64 Content: {img_base64[:1000]}... (truncated)"
        )

        # Initialize ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable.")

        chat = ChatOpenAI(
            model="gpt-4",
            max_tokens=1024,
            openai_api_key=api_key
        )

        # Generate response
        response = chat.invoke([HumanMessage(content=full_prompt)])
        logger.info("Summary generated successfully")
        return response.content
    except Exception as e:
        logger.error(f"Error summarizing image: {e}")
        return "An error occurred while summarizing the image."

# Function to process images in the downloads folder
def process_images_in_folder(folder_path):
    """
    Process images in a folder, extract text, summarize them, and save the summaries.
    """
    logger.info(f"Processing images in folder: {folder_path}")
    summaries = []
    prompt = (
        "You are an AI assistant tasked with summarizing the content of images for retrieval. "
        "Summarize the extracted text and include relevant insights based on the image content."
    )

    # Traverse all subdirectories in the folder
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith((".png", ".jpeg", ".jpg")):  # Supported image formats
                image_path = normalize_path(os.path.join(root, file))
                logger.info(f"Processing image: {image_path}")

                # Generate summary for the image
                summary = summarize_image(image_path, prompt)
                if summary:
                    summaries.append({"file": file, "summary": summary})
                    logger.info(f"Summary for {file}: {summary}")

                    # Save summary to a text file in the same directory as the image
                    summary_path = normalize_path(os.path.join(root, f"{os.path.splitext(file)[0]}_summary.txt"))
                    try:
                        with open(summary_path, "w") as f:
                            f.write(summary)
                        logger.info(f"Saved summary for {file} to {summary_path}")
                    except Exception as e:
                        logger.error(f"Error saving summary for {file}: {e}")
                else:
                    logger.warning(f"Failed to summarize image: {file}")

    logger.info(f"Finished processing images in folder: {folder_path}")
    return summaries

# Main function
def main():
    logger.info("Starting the workflow")

    # Step 1: Process images in the downloads folder
    logger.info("Starting image processing...")
    summaries = process_images_in_folder(downloads_folder)

    # Step 2: Output summaries for verification
    for summary in summaries:
        print(f"File: {summary['file']}\nSummary: {summary['summary']}\n")

    logger.info("Workflow completed successfully")

# Run the script
if __name__ == "__main__":
    main()
