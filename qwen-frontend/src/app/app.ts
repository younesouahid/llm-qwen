
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { QwenService } from './servies/qwen-service';
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {

  private qwenService = inject(QwenService);

  sessionId = crypto.randomUUID();

  prompt = '';
  loading = signal(false);
  messages = signal<ChatMessage[]>([]);

  async sendMessage() {
    const text = this.prompt.trim();

    if (!text || this.loading()) return;

    this.prompt = '';

    this.messages.update(messages => [
      ...messages,
      { role: 'user', content: text },
      { role: 'assistant', content: '' }
    ]);

    this.loading.set(true);

    try {
      await this.qwenService.streamChat(
        text,
        this.sessionId,
        (token) => {
          this.messages.update(messages => {
            const updated = [...messages];
            const last = updated[updated.length - 1];

            updated[updated.length - 1] = {
              ...last,
              content: last.content + token
            };

            return updated;
          });
        }
      );

    } catch (error) {
      console.error(error);

      this.messages.update(messages => {
        const updated = [...messages];
        const last = updated[updated.length - 1];

        updated[updated.length - 1] = {
          ...last,
          content: last.content +
            '\n[Error communicating with Qwen]'
        };

        return updated;
      });

    } finally {
      this.loading.set(false);
    }
  }

  async clearConversation() {
    if (this.loading()) return;

    try {
      await this.qwenService.clearChat(this.sessionId);
      this.messages.set([]);
    } catch (error) {
      console.error('Could not clear conversation', error);
    }
  }
}
