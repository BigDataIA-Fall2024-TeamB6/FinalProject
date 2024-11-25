from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.client import User
from diagrams.onprem.workflow import Airflow
from diagrams.aws.storage import S3
from diagrams.programming.framework import FastAPI 

with Diagram("CorePipeline", show=False):
    with Cluster("Frontend"):
        users = [User("User") for _ in range(3)]

    microsoft_graph = Custom("Microsoft Graph API", "./images/GraphAPI.png")
    airflow = Airflow("Trigger Airflow")
    vector_store = Custom("Vector Store\n(Milvus)", "./images/Milvus.png")

    streamlit = Custom("Streamlit", "./images/Streamlit.png")
    users >> streamlit

    fastapi = FastAPI("FastAPI")
    with Cluster("Speech Services"):
        openai_whisper = Custom("OpenAI Whisper", "./images/OpenAI.png")
        openai_tts = Custom("OpenAI TTS", "./images/OpenAI.png")
        
        fastapi << openai_whisper
        fastapi >> openai_whisper
        
        fastapi << openai_tts
        fastapi >> openai_tts

    langraph = Custom("LangGraph", "./images/LangGraph.png")
    llm = Custom("LLM\n(GPT-4o)", "./images/OpenAI.png")
    
    with Cluster("Agents"):
        prompt_correction = Custom("Prompt Correction\nAgent", "./images/Agent.png")
        summary = Custom("Summary Agent", "./images/Agent.png")
        rag_agent = Custom("RAG Agent", "./images/Agent.png")
        response_agent = Custom("Response Agent\n(with Guardrail)", "./images/Agent.png")
    
    approval = User("Human Approval")

    streamlit >> microsoft_graph
    microsoft_graph >> streamlit
    fastapi >> airflow
    streamlit >> fastapi

    with Cluster("Storage"):
        postgres = PostgreSQL("PostgreSQL (AWS)")
        s3 = S3("S3 Bucket")
        postgres >> fastapi
        s3 >> fastapi
    
    fastapi >> langraph
    langraph >> llm
    
    llm >> prompt_correction
    prompt_correction >> langraph
    
    llm >> summary
    summary >> langraph

    llm >> rag_agent
    fastapi >> rag_agent
    vector_store >> rag_agent
    
    llm >> response_agent
    response_agent >> langraph

    response_agent >> approval
    approval >> response_agent

    response_agent >> microsoft_graph

    # Broadcast updates
    # [streamlit, langraph, llm, prompt_correction, summary] >> Edge(color="blue", style="dashed")