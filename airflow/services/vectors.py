import os
import re
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv
from services.logger import start_logger
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType

# Load env
load_dotenv()

# Start logging
logger = start_logger()

def connect_to_Milvus():
    ''' Connect to Milvus Vector store '''

    logger.info("Airflow - MILVUS - connect_to_Milvus() - Connecting to Milvus database...")
    client = None
    
    try:
        client = MilvusClient(
            uri       = "http://" + os.getenv("MILVUS_HOST") + ':' + os.getenv("MILVUS_PORT"),
            user      = os.getenv("MILVUS_USER"),
            password  = os.getenv("MILVUS_PASSWORD"),
            db_name   = os.getenv("MILVUS_DATABASE"),
            timeout   = None
        )
    
    except Exception as exception:
        logger.error("Airflow - MILVUS - connect_to_Milvus() - Exception occurred when connecting to Milvus database (See exception below)")
        logger.error(f"Airflow - MILVUS - connect_to_Milvus() - {exception}")

    finally:
        return client
    
def count_tokens(text):
    '''Counts the tokens in the given text using the specified tokenizer '''
    
    tokenizer = tiktoken.get_encoding("cl100k_base")
    return len(tokenizer.encode(text))

def remove_urls(text):
    ''' Remove URLs from the text '''
    
    return re.sub(r'http\S+|www\S+', '', text)

def preprocess_text(text, max_tokens=7000):
    ''' Remove URLs from email content if token count for text exceeds max tokens '''

    token_count = count_tokens(text)

    if token_count > max_tokens:
        logger.warning(f"Airflow - MILVUS - Token count ({token_count}) exceeds {max_tokens}, removing URLs...")
        text = remove_urls(text)
        
        token_count = count_tokens(text)
        logger.warning(f"Airflow - MILVUS - Token count after URL removal: {token_count}")
    
    return text

def create_embeddings_and_index(data_to_index, metadata):
    ''' Create embeddings using OpenAI embeddings and index the vectors '''

    logger.info("Airflow - MILVUS - create_embeddings_and_index() - Creating embeddings for email content")
    
    is_indexed = False
    conn = connect_to_Milvus()
    
    if not conn:
        logger.error("Airflow - MILVUS - create_embeddings_and_index() - Cannot create embeddings because connection to Milvus failed")
        return is_indexed
    
    # Each user will have a separate collection
    collection_name = str(metadata["user_email"])
    collection_name = collection_name.replace('@', os.getenv("__AT"))
    collection_name = collection_name.replace('.', os.getenv("__PERIOD"))

    try:
        # If the collection does not exist, create one
        if not conn.has_collection(collection_name):
            logger.info(f"Airflow - MILVUS - create_embeddings_and_index() - Collection '{collection_name}' does not exist. Creating collection...")
            
            fields = [
                FieldSchema(
                    name        = "id", 
                    dtype       = DataType.INT64, 
                    is_primary  = True, 
                    auto_id     = True
                ),
                FieldSchema(
                    name    = "embedding", 
                    dtype   = DataType.FLOAT_VECTOR, 
                    dim     = 3072
                ),
                FieldSchema(
                    name    = "metadata", 
                    dtype   = DataType.JSON
                )
            ]
            schema = CollectionSchema(fields=fields, description=f"Collection for user {collection_name}")
            
            # Create the collection
            conn.create_collection(collection_name=collection_name, schema=schema)
            logger.info(f"Airflow - MILVUS - create_embeddings_and_index() - Collection '{collection_name}' created successfully.")

            # Index the embeddings for faster retrieval
            index_params = conn.prepare_index_params()
            index_params.add_index(
                field_name  = "embedding",
                index_type  = "IVF_FLAT", 
                metric_type = "COSINE", 
                params      = {"nlist": 1024}
            )
            # collection.create_index(field_name="embedding", index_params=index_params)
            conn.create_index(collection_name=collection_name, index_params=index_params)
            logger.info(f"Airflow - MILVUS - create_embeddings_and_index() - Added index to embeddings successfully.")

        else:
            logger.warning(f"Airflow - MILVUS - create_embeddings_and_index() - Collection '{collection_name}' already exists.")
    
    except Exception as exception:
        logger.error("Airflow - MILVUS - connect_to_milvus() - Exception occurred when connecting to Milvus database (See exception below)")
        logger.error(f"Airflow - MILVUS - connect_to_milvus() - {exception}")

    # Check if token limit is being exceeded
    data_to_index["body"] = preprocess_text(text=data_to_index["body"], max_tokens=7000)

    # Content to index
    content = " ".join([str(value) for value in data_to_index.values()])

    try:
        
        logger.info(f"Airflow - MILVUS - create_embeddings_and_index() - Connecting to OpenAI...")
        client = OpenAI(
            api_key      = os.getenv("OPENAI_API_KEY"),
            project      = os.getenv("PROJECT_ID"),
            organization = os.getenv("ORGANIZATION_ID")
        )

        logger.info(f"Airflow - MILVUS - create_embeddings_and_index() - Generating OpenAI embeddings...")
        embedding = client.embeddings.create(
            input = [content], 
            model = os.getenv("EMBEDDING_MODEL")
        ).data[0].embedding

        vectors = {
            "embedding" : embedding,
            "metadata"  : metadata
        }

        conn.insert(collection_name=collection_name, data=vectors)
        is_indexed = True
        logger.info(f"Airflow - MILVUS - create_embeddings_and_index() - Saved vectors with metadata to {collection_name} successfully.")
        
    except Exception as exception:
        logger.error("Airflow - MILVUS - create_embeddings_and_index() - Exception occurred when creating and indexing embeddings (See exception below)")
        logger.error(f"Airflow - MILVUS - create_embeddings_and_index() - {exception}")
    
    finally:
        conn.close()
        client.close()

        # If needed in future
        return is_indexed