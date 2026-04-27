import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, Course } from '../../services/chat';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
})
export class ChatComponent implements OnInit {
  // === User-Eingabe ===
  userInput: string = '';
  isLoading: boolean = false;

  // === Fächer & Auswahl ===
  courses: Course[] = [];
  selectedCourse: Course | null = null;
  coursesError: string = '';

  // === Modi (für später - aktuell nur tutor aktiv) ===
  selectedMode: string = 'tutor';

  // === Chat-Verlauf ===
  messages: any[] = [];

  constructor(
    private chatService: ChatService,
    private cdr: ChangeDetectorRef,
  ) {}

  /**
   * Beim Laden der Komponente: Fächer vom Backend holen.
   */
  ngOnInit(): void {
    this.loadCourses();
  }

  /**
   * Lädt die Fächer-Liste vom Backend.
   */
  loadCourses(): void {
    this.chatService.getCourses().subscribe({
      next: (res) => {
        this.courses = res.courses;
        if (this.courses.length > 0) {
          this.selectedCourse = this.courses[0];
        }
        // 🔧 FIX: Change Detection manuell auslösen,
        // weil HTTP-Callback außerhalb der Zone laufen kann
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Fehler beim Laden der Fächer:', err);
        this.coursesError = 'Backend nicht erreichbar. Läuft uvicorn?';
        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Wechselt das ausgewählte Fach und löscht den Chat-Verlauf.
   * (Sonst hätte man Kontext-Mix zwischen Fächern.)
   */
  selectCourse(course: Course): void {
    if (this.selectedCourse?.code === course.code) return; // gleiche Auswahl
    this.selectedCourse = course;
    this.messages = []; // Chat zurücksetzen beim Fach-Wechsel
  }

  /**
   * Sendet eine Nachricht ans Backend.
   */
  sendMessage(): void {
    if (!this.userInput.trim()) return;
    if (!this.selectedCourse) {
      alert('Bitte wähle zuerst ein Fach aus.');
      return;
    }

    // User-Nachricht in den Chat aufnehmen
    this.messages.push({ text: this.userInput, sender: 'user' });
    const currentInput = this.userInput;
    this.userInput = '';
    this.isLoading = true;

    this.chatService
      .sendMessage(currentInput, this.selectedCourse.code, this.selectedMode)
      .subscribe({
        next: (res) => {
          this.messages.push({
            text: res.reply,
            sender: 'bot',
            sources: res.sources,
          });
          this.isLoading = false;
          this.cdr.detectChanges(); // 🔧 FIX
        },
        error: (err) => {
          console.error('Fehler:', err);
          this.messages.push({
            text: 'Fehler beim Abruf der Antwort. Backend prüfen.',
            sender: 'bot',
            sources: [],
          });
          this.isLoading = false;
          this.cdr.detectChanges(); // 🔧 FIX
        },
      });
  }
}
