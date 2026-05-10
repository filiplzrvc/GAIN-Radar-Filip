import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Typen-Definitionen passend zum Backend
export interface Course {
  code: string;
  name: string;
  description: string;
  language: string;
}

export interface CoursesResponse {
  courses: Course[];
}

export interface ChatRequest {
  text: string;
  course: string;
  mode: string;
  session_id?: string;
}

export interface ChatResponse {
  reply: string;
  sources: string[];
  session_id?: string;
  mode_used?: string;
  course_used?: string;
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private baseUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  /**
   * Holt die Liste aller verfügbaren Fächer vom Backend.
   * Wird beim Start der App aufgerufen, um die Sidebar zu bauen.
   */
  getCourses(): Observable<CoursesResponse> {
    return this.http.get<CoursesResponse>(`${this.baseUrl}/courses`);
  }

  /**
   * Schickt eine Chat-Anfrage ans Backend.
   * Course ist jetzt PFLICHTFELD - Backend lehnt ohne ab!
   */
  sendMessage(
    text: string,
    course: string,
    mode: string = 'tutor',
    sessionId: string | null = null,
  ): Observable<ChatResponse> {
    const payload: ChatRequest = { text, course, mode };
    if (sessionId) {
      payload.session_id = sessionId;
    }
    return this.http.post<ChatResponse>(`${this.baseUrl}/chat`, payload);
  }
}
