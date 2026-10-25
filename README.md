# Qwen Local Chat — FastAPI + Angular

A local AI chatbot powered by **Qwen2.5-1.5B-Instruct**, **Python/FastAPI**, and **Angular**. The application supports normal chat responses, real-time streaming with Server-Sent Events (SSE), and temporary conversation history per session. The backend also exposes a PDF text-extraction endpoint.

> **The model weights are not included in this repository.** Each developer must download them separately before starting the API. The application runs locally; no hosted inference API is needed.

## Requirements

- **Git**
- **Miniconda or Anaconda** (Python 3.11)
- **Node.js and npm** (use a Node.js version supported by the Angular version specified in `qwen-frontend/package.json`; see [Angular compatibility](https://angular.dev/reference/versions))
- Internet access for the initial dependency and model downloads
- Enough RAM/disk space for the ~1.5B-parameter model and its dependencies; an NVIDIA GPU is optional but can improve generation speed

## Project structure

```text
llm/
├── .gitignore
├── README.md                  # This file
├── main.py                    # FastAPI backend + model inference
├── Qwen2.5-1.5B-Instruct/     # Download separately (gitignored)
│   └── Qwen2.5-1.5B-Instruct/
│       ├── config.json
│       ├── tokenizer.json
│       └── model.safetensors  # Or model weight shards
└── qwen-frontend/             # Angular application
    ├── package.json
    ├── package-lock.json
    └── src/
```

## Quick start (Windows / PowerShell)

### 1. Clone the repository

```powershell
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>
```

Run the next backend commands from the repository root, where `main.py` is located.

### 2. Create a Python environment

```powershell
conda create -n qwen python=3.11 -y
conda activate qwen
```

### 3. Install backend dependencies

```powershell
python -m pip install torch transformers accelerate safetensors fastapi "uvicorn[standard]" pypdf python-multipart huggingface_hub
```

**GPU users:** For a CUDA-enabled PyTorch installation, use the appropriate command from the [official PyTorch installer](https://pytorch.org/get-started/locally/). You can check GPU visibility with:

```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### 4. Download Qwen model files

From the repository root, run:

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen2.5-1.5B-Instruct', local_dir='Qwen2.5-1.5B-Instruct/Qwen2.5-1.5B-Instruct')"
```

This preserves the directory layout expected by `main.py`:

```python
MODEL_PATH = (
    Path(__file__).resolve().parent
    / "Qwen2.5-1.5B-Instruct"
    / "Qwen2.5-1.5B-Instruct"
)
```

If your backend uses a different model path, change either the path in `main.py` or the download destination. The downloaded weights are intentionally ignored by Git.

### 5. Start FastAPI

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Leave this terminal open. The model loads once when the backend starts.

- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### 6. Start the Angular frontend

Open **a second PowerShell terminal**:

```powershell
cd <YOUR_REPOSITORY_FOLDER>\qwen-frontend
npm ci
npm start
```

Open http://localhost:4200 (if npm asks about configuration or your `start` script differs, you can use `npx ng serve`).

**CORS:** `main.py` must allow `http://localhost:4200` in its `CORSMiddleware` `allow_origins` list. The Angular service should use `http://127.0.0.1:8000` as its API base URL. Restart FastAPI after changing the backend.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend status |
| `POST` | `/api/chat` | Generate a full response |
| `POST` | `/api/chat/stream` | Stream chunks as SSE events |
| `DELETE` | `/api/chat/{session_id}` | Clear the conversation for a session |
| `POST` | `/api/pdf/text` | Extract text from an uploaded PDF (does not ask Qwen about it) |

### Chat request

`POST http://127.0.0.1:8000/api/chat`

```json
{
  "message": "Explain what deep learning is.",
  "session_id": "demo-1"
}
```

Sample response shape:

```json
{
  "session_id": "demo-1",
  "response": "Deep learning is ..."
}
```

### Streaming request

`POST http://127.0.0.1:8000/api/chat/stream` accepts the same JSON body and responds with `Content-Type: text/event-stream`.

Sample SSE events (the chunks will vary):

```text
data: {"token": "Deep learning "}

data: {"token": "uses neural networks."}

data: {"done": true}
```

To test with **Postman**, select `POST`, choose **Body → raw → JSON**, paste the request body, and click **Send**. The Angular UI automatically processes SSE chunks.

To test from **PowerShell**, use a JSON file to avoid quoting issues:

```powershell
@'
{"message":"Explain deep learning.","session_id":"demo-1"}
'@ | Set-Content -Encoding utf8 request.json

curl.exe -N -X POST "http://127.0.0.1:8000/api/chat/stream" -H "Content-Type: application/json" --data-binary "@request.json"
```

## Troubleshooting

| Problem | What to check |
|---|---|
| `conda activate qwen` fails | Run `conda info --envs`; create the environment as shown above. |
| Model folder / `config.json` not found | Verify the nested model folder and `MODEL_PATH` in `main.py`. |
| `ModuleNotFoundError` | Activate `qwen`, then reinstall the missing backend package. |
| `CUDA out of memory` | Reduce `max_new_tokens`, run on CPU, or use a smaller/quantized model. |
| Angular reports a CORS error | Add the frontend origin to FastAPI's CORS middleware; restart the server. |
| Angular cannot connect to the API | Make sure FastAPI is running on port `8000` and the Angular service URL is correct. |
| `npm ci` fails | Check Node.js compatibility with the Angular version and ensure `package-lock.json` is committed. |
| Model answers arrive slowly | CPU generation can be slow; GPU acceleration is optional. |

## Notes and limitations

- Conversation history is kept **in memory** and is lost when the backend restarts.
- The current backend handles one model generation at a time to prevent overlapping inference.
- The SSE endpoint sends text chunks, not necessarily individual model tokens.
- `/api/pdf/text` extracts selectable PDF text only; PDF question answering and OCR are not implemented.
- The app is intended for **local development**. Add authentication, session limits, secure storage, and deployment hardening before exposing it publicly.
- Do not commit downloaded model weights, `.env` files, Python caches, or `node_modules`.

## Technology stack

- Backend: Python, FastAPI, Uvicorn, Hugging Face Transformers, PyTorch
- Model: [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- Frontend: Angular, TypeScript, CSS
- Streaming: Server-Sent Events (SSE)
