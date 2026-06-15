import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, Course } from '../../services/chat';

export interface Flashcard {
  front: string;
  back: string;
  flipped: boolean;
}

export interface Message {
  text: string;
  sender: 'user' | 'bot';
  sources?: string[];
  flashcards?: Flashcard[];
  isFlashcardMessage?: boolean;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
})
export class ChatComponent implements OnInit {
  userInput: string = '';
  isLoading: boolean = false;

  courses: Course[] = [];
  selectedCourse: Course | null = null;
  coursesError: string = '';

  selectedMode: string = 'tutor';

  messages: Message[] = [];
  sessionId: string | null = null;

  constructor(
    private chatService: ChatService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadCourses();
  }

  loadCourses(): void {
    this.chatService.getCourses().subscribe({
      next: (res) => {
        this.courses = res.courses;
        if (this.courses.length > 0) {
          this.selectedCourse = this.courses[0];
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Fehler beim Laden der Fächer:', err);
        this.coursesError = 'Backend nicht erreichbar. Läuft uvicorn?';
        this.cdr.detectChanges();
      },
    });
  }

  selectCourse(course: Course): void {
    if (this.selectedCourse?.code === course.code) return;
    this.selectedCourse = course;
    this.messages = [];
    this.sessionId = null;
  }

  /**
   * Baut die URL für eine klickbare Quelle.
   *
   * Eingabe vom Backend:  "03_MaschinellesLernen.pdf (S. 12)"
   * Ausgabe:              "http://localhost:8000/api/pdf/03_MaschinellesLernen.pdf#page=12"
   *
   * Das #page=N Fragment wird von allen modernen PDF-Viewern (Chrome, Firefox, Edge)
   * unterstützt und springt direkt zur richtigen Seite.
   */
  buildPdfUrl(source: string): string {
    if (!this.selectedCourse) {
      return '#';
    }

    const course = this.selectedCourse.code;

    // Format: "Dateiname.pdf (S. 12)"
    const match = source.match(/^(.+?\.pdf)\s*\(S\.\s*(\d+)\)$/i);

    if (match) {
      const filename = match[1].trim();
      const page = match[2];

      return `http://localhost:8000/api/pdf/${encodeURIComponent(course)}/${encodeURIComponent(filename)}#page=${page}`;
    }

    // Fallback: nur Dateiname ohne Seite
    const pdfMatch = source.match(/^(.+?\.pdf)/i);

    if (pdfMatch) {
      const filename = pdfMatch[1].trim();

      return `http://localhost:8000/api/pdf/${encodeURIComponent(course)}/${encodeURIComponent(filename)}`;
    }

    return '#';
  }

  /**
   * Parst den Backend-Text und erkennt ob es Lernkarten sind.
   */
  private parseFlashcards(text: string): Flashcard[] | null {
    if (!text.includes('KARTENVORDERSEITE') || !text.includes('KARTENRÜCKSEITE')) {
      return null;
    }

    const cards: Flashcard[] = [];
    const cardBlocks = text.split(/\s*---\s*/);

    for (const block of cardBlocks) {
      const trimmed = block.trim();
      if (!trimmed || !trimmed.includes('KARTENVORDERSEITE')) continue;

      const frontMatch = trimmed.match(
        /\*\*KARTENVORDERSEITE[^*]*\*\*[:\s]*([\s\S]*?)(?=\*\*KARTENRÜCKSEITE)/i,
      );
      const backMatch = trimmed.match(/\*\*KARTENRÜCKSEITE[^*]*\*\*[:\s]*([\s\S]*?)$/i);

      if (frontMatch && backMatch) {
        const front = frontMatch[1]
          .trim()
          .replace(/^\*\*|\*\*$/g, '')
          .trim();
        const back = backMatch[1].trim().replace(/^- /gm, '• ');

        if (front && back) {
          cards.push({ front, back, flipped: false });
        }
      }
    }

    return cards.length > 0 ? cards : null;
  }

  flipCard(msg: Message, index: number): void {
    if (msg.flashcards) {
      msg.flashcards[index].flipped = !msg.flashcards[index].flipped;
      this.cdr.detectChanges();
    }
  }

  sendMessage(): void {
    if (!this.userInput.trim()) return;
    if (!this.selectedCourse) {
      alert('Bitte wähle zuerst ein Fach aus.');
      return;
    }

    this.messages.push({ text: this.userInput, sender: 'user' });
    const currentInput = this.userInput;
    this.userInput = '';
    this.isLoading = true;

    this.chatService
      .sendMessage(currentInput, this.selectedCourse.code, this.selectedMode, this.sessionId)
      .subscribe({
        next: (res) => {
          if (res.session_id) {
            this.sessionId = res.session_id;
          }

          const flashcards = this.parseFlashcards(res.reply);

          const botMsg: Message = {
            text: res.reply,
            sender: 'bot',
            sources: res.sources,
          };

          if (flashcards) {
            botMsg.flashcards = flashcards;
            botMsg.isFlashcardMessage = true;
          }

          this.messages.push(botMsg);
          this.isLoading = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('Fehler:', err);
          this.messages.push({
            text: 'Fehler beim Abruf der Antwort. Backend prüfen.',
            sender: 'bot',
            sources: [],
          });
          this.isLoading = false;
          this.cdr.detectChanges();
        },
      });
  }
}
