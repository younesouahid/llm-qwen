import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class QwenService {
   private apiUrl = 'http://127.0.0.1:8000';

  async streamChat(
    message: string,
    sessionId: string,
    onToken: (token: string) => void
  ): Promise<void> {

    const response = await fetch(
      `${this.apiUrl}/api/chat/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        })
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Streaming is not supported');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';
    let completed = false;

    const processEvent = (event: string) => {
      const dataLines = event
        .split('\n')
        .filter(line => line.startsWith('data:'));

      if (!dataLines.length) return;

      const data = JSON.parse(
        dataLines.map(line => line.slice(5).trimStart()).join('\n')
      );

      if (typeof data.token === 'string') {
        onToken(data.token);
      }

      if (data.error) {
        throw new Error(data.error);
      }

      if (data.done) {
        completed = true;
      }
    };

    const processBuffer = () => {
      let boundary: number;

      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const event = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        processEvent(event);
      }
    };

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder
          .decode(value, { stream: true })
          .replace(/\r\n/g, '\n');

        processBuffer();
      }

      buffer += decoder.decode();
      processBuffer();

      if (!completed) {
        throw new Error('Stream ended unexpectedly');
      }

    } finally {
      reader.releaseLock();
    }
  }

  async clearChat(sessionId: string): Promise<void> {
    const response = await fetch(
      `${this.apiUrl}/api/chat/${encodeURIComponent(sessionId)}`,
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Could not clear conversation');
    }
  }
}
