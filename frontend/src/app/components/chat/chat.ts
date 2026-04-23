import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat'; 

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss'
})
export class ChatComponent {
  userInput: string = '';
  selectedMode: string = 'tutor'; 
  messages: any[] = [];
  isLoading: boolean = false;

  constructor(private chatService: ChatService) {}

  // Neue Methode: Modus wechseln über die Sidebar
  setMode(mode: string) {
    this.selectedMode = mode;
  }

  // Neue Methode: Den Namen des Modus für die Überschrift holen
  getModeName(): string {
    const modes: any = {
      'tutor': 'Tutor-Modus',
      'quiz': 'Quiz-Modus',
      'flashcards': 'Lernkarten',
      'summary': 'Zusammenfassung'
    };
    return modes[this.selectedMode] || 'Agent';
  }

  sendMessage() {
    if (!this.userInput.trim()) return;

    this.messages.push({ text: this.userInput, sender: 'user' });
    const currentInput = this.userInput;
    this.userInput = '';
    this.isLoading = true;

    this.chatService.sendMessage(currentInput, this.selectedMode).subscribe({
      next: (res) => {
        this.messages.push({ 
          text: res.reply, 
          sender: 'bot', 
          sources: res.sources 
        });
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Fehler:', err);
        this.isLoading = false;
      }
    });
  }
}