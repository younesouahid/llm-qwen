
import io
import json
from pathlib import Path
from threading import Lock, Thread

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pypdf import PdfReader
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)

from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="Qwen Local API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "Qwen2.5-1.5B-Instruct"
    / "Qwen2.5-1.5B-Instruct"
)

print("Loading Qwen model...")

tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH))

model = AutoModelForCausalLM.from_pretrained(
    str(MODEL_PATH),
    dtype="auto",
    device_map="auto",
)
model.eval()

print("Qwen model loaded!")

SYSTEM = {
    "role": "system",
    "content": "You are Qwen, a helpful AI assistant."
}

# Development-only storage: lost when the server restarts
conversations = {}
model_lock = Lock()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    session_id: str = Field(default="default", min_length=1, max_length=100)


def prepare_inputs(request: ChatRequest):
    history = conversations.get(request.session_id, [])

    messages = [
        SYSTEM,
        *history[-10:],
        {"role": "user", "content": request.message}
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        [text],
        return_tensors="pt"
    ).to(model.device)

    if inputs.input_ids.shape[1] > 28000:
        raise HTTPException(
            status_code=413,
            detail="Conversation too long. Clear the session."
        )

    return inputs, history


def save_history(request, history, answer):
    conversations[request.session_id] = [
        *history[-10:],
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": answer}
    ]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "Qwen2.5-1.5B-Instruct"
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    with model_lock:
        inputs, history = prepare_inputs(request)

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )

        response_ids = output[0][inputs.input_ids.shape[1]:]
        answer = tokenizer.decode(
            response_ids,
            skip_special_tokens=True
        )

        save_history(request, history, answer)

        return {
            "session_id": request.session_id,
            "response": answer
        }


@app.post("/api/chat/stream")
def stream_chat(request: ChatRequest):
    def generate_stream():
        with model_lock:
            inputs, history = prepare_inputs(request)

            streamer = TextIteratorStreamer(
                tokenizer,
                skip_prompt=True,
                skip_special_tokens=True,
                timeout=180.0
            )

            errors = []

            def run_model():
                try:
                    with torch.inference_mode():
                        model.generate(
                            **inputs,
                            max_new_tokens=256,
                            do_sample=False,
                            pad_token_id=tokenizer.eos_token_id,
                            streamer=streamer
                        )
                except Exception as exc:
                    errors.append(str(exc))
                    streamer.end()

            thread = Thread(target=run_model)
            thread.start()

            chunks = []

            try:
                for chunk in streamer:
                    chunks.append(chunk)
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
            except Exception as exc:
                errors.append(str(exc))
            finally:
                thread.join()

            if errors:
                yield f"data: {json.dumps({'error': errors[0]})}\n\n"
                return

            answer = "".join(chunks)
            save_history(request, history, answer)

            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.delete("/api/chat/{session_id}")
def clear_chat(session_id: str):
    with model_lock:
        conversations.pop(session_id, None)

    return {"message": "Conversation cleared"}


@app.post("/api/pdf/text")
async def extract_pdf_text(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    try:
        # Limit upload size to 10 MB
        contents = await file.read(10 * 1024 * 1024 + 1)

        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(413, "PDF exceeds 10 MB")

        reader = PdfReader(io.BytesIO(contents))
        if len(reader.pages) > 100:
            raise HTTPException(413, "Too many PDF pages")

        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append(f"--- Page {i + 1} ---\n{text}")

        return {
            "filename": file.filename,
            "pages": len(reader.pages),
            "text": "\n\n".join(pages)
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Could not read PDF")
    finally:
        await file.close()
