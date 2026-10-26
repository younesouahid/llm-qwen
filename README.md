# Qwen Chatbot — FastAPI + Angular

A local AI chatbot built with **Qwen2.5-1.5B-Instruct**, **FastAPI**, and **Angular**.

## Prerequisites

Before starting, make sure you have installed:

- Git
- Miniconda or Anaconda
- Node.js and npm

## 1. Clone the repository

```bash
git clone younesouahid/llm-qwen
cd <REPOSITORY_FOLDER>
```

## 2. Set up the backend (FastAPI)

Create and activate a Conda environment:

```bash
conda create -n qwen python=3.11 -y
conda activate qwen
```

Install the required Python libraries:

```bash
pip install torch transformers accelerate safetensors fastapi "uvicorn[standard]" pypdf python-multipart huggingface_hub
```

## 3. Download the Qwen model

The model is not included in the GitHub repository.

Run this command from the project root:

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen2.5-1.5B-Instruct', local_dir='Qwen2.5-1.5B-Instruct/Qwen2.5-1.5B-Instruct')"
```

## 4. Start the backend

From the project root, run:

```bash
conda activate qwen
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The backend will be available at:

- API: http://127.0.0.1:8000


## 5. Start the frontend (Angular)

Open a second terminal:

```bash
cd qwen-frontend
npm ci
npm start
```

Open your browser at:

**http://localhost:4200**

## 6. Use the chatbot

Once both servers are running, you can:

- Send messages to Qwen.
- Receive responses in real time using streaming.
- Continue a conversation with temporary session memory.
- Clear the conversation.

**Note:** Keep both FastAPI and Angular terminals running while using the application.