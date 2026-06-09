# Gain-Radar-2

GAIN-Radar is an AI-based learning assistant for students of FH Technikum Wien.
The application helps students ask questions about course material and receive grounded, course-specific answers based on retrieved documents.

The project combines an Angular frontend with a FastAPI backend and a Retrieval-Augmented Generation (RAG) pipeline. Course-specific content is retrieved from a Pinecone vector database and used as context for the language model.

## Features

* Course-specific AI chatbot
* Retrieval-Augmented Generation based on lecture/course material
* Support for multiple courses
* Source-aware answers
* Session-based conversation memory
* Agentic backend workflow
* Angular-based chat user interface
* FastAPI REST API
* Health-check endpoint for backend availability

## Supported Courses

The backend currently provides the following course configurations:

* Artificial Intelligence Einführung
* IT Security Basics
* Software Engineering

Each course has its own course code and description. These course codes are used by the backend to select the correct retrieval namespace.

## Architecture Overview

The system consists of two main parts:

```text
GAIN-Radar
├── frontend/    Angular web application
└── backend/     FastAPI backend with RAG workflow
```

### Frontend

The frontend is built with Angular. It provides the chat interface, displays available courses and sends user questions to the backend API.

Main responsibilities:

* Display available courses
* Allow users to select a course
* Send chat messages to the backend
* Display assistant responses
* Show retrieved sources
* Maintain the current session ID during the conversation

### Backend

The backend is built with FastAPI. It exposes REST endpoints for course information, chat requests and health checks.

Main responsibilities:

* Validate incoming chat requests
* Load available course configurations
* Run the agentic RAG workflow
* Retrieve course-specific documents from Pinecone
* Generate grounded answers using an LLM
* Return answers, sources and session information to the frontend

## Agentic Workflow

The backend uses a multi-step workflow to process each user request.

```text
User Question
    ↓
Analysis Agent
    ↓
Retrieval Agent
    ↓
Context Agent
    ↓
Answer Agent
    ↓
Final Response
```

### 1. Analysis Agent

The analysis agent examines the user question before retrieval happens.

It detects:

* language
* topics
* user intent
* whether the question is off-topic
* whether clarification is needed

This step helps the system decide whether the request can be answered directly or whether the user should first provide more specific information.

### 2. Retrieval Agent

The retrieval agent searches for relevant course material in Pinecone.

It uses the selected course code as namespace so that the chatbot retrieves documents only from the currently selected course.

### 3. Context Agent

The context agent filters and evaluates the retrieved documents.

It removes weak chunks, filters duplicates and decides whether the available context is sufficient for a grounded answer.

### 4. Answer Agent

The answer agent generates the final response.

It uses the prepared context and follows strict RAG rules:

* answer only based on the retrieved course material
* do not use unsupported external knowledge
* do not invent examples or details
* be honest when the material does not contain enough information
* return sources when a grounded answer is possible

## API Endpoints

### `GET /api/courses`

Returns all available courses.

Example response:

```json
{
  "courses": [
    {
      "code": "aief",
      "name": "Artificial Intelligence Einführung",
      "description": "Grundlagen der KI, Logik, Maschinelles Lernen und Neuronale Netze",
      "language": "de"
    }
  ]
}
```

### `POST /api/chat`

Sends a chat message to the backend.

Example request:

```json
{
  "text": "What is overfitting?",
  "course": "aief",
  "mode": "tutor",
  "session_id": "sess_12345678"
}
```

Example response:

```json
{
  "reply": "Generated answer based on the course material.",
  "sources": ["source.pdf (S. 3)"],
  "session_id": "sess_12345678",
  "mode_used": "tutor",
  "course_used": "aief"
}
```

### `GET /api/health`

Returns backend status information.

Example response:

```json
{
  "status": "ok",
  "version": "0.3.0",
  "workflow": "agentic"
}
```

## Tech Stack

### Frontend

* Angular
* TypeScript
* SCSS
* RxJS
* npm

### Backend

* Python
* FastAPI
* Uvicorn
* LangChain
* OpenAI
* Pinecone
* Jina Embeddings
* Pydantic
* LangSmith tracing
* python-dotenv

## Requirements

Before starting the project, make sure the following tools are installed:

* Node.js
* npm
* Python 3.11 or newer
* Access to an OpenAI API key
* Access to a Jina AI API key
* Access to a Pinecone index containing the embedded course material

## Environment Variables

Create a `.env` file inside the `backend/` directory.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
JINA_API_KEY=your_jina_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
```

Optional, if LangSmith tracing is used:

```env
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=gain-radar
```

## Backend Setup

Navigate to the backend folder:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend should now run on:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

## Frontend Setup

Navigate to the frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the Angular development server:

```bash
npm start
```

The frontend should now run on:

```text
http://localhost:4200
```

The frontend expects the backend API at:

```text
http://localhost:8000/api
```

## Development Scripts

### Frontend

```bash
npm start
```

Starts the Angular development server.

```bash
npm run build
```

Builds the Angular application.

```bash
npm test
```

Runs frontend tests.

### Backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Starts the FastAPI backend in development mode.

## Project Structure

```text
GAIN-Radar
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── prompts.py
│   │   │   └── retriever.py
│   │   ├── models/
│   │   │   └── schema.py
│   │   └── workflow/
│   │       ├── analysis_agent.py
│   │       ├── retrieval_agent.py
│   │       ├── context_agent.py
│   │       ├── answer_agent.py
│   │       ├── memory_manager.py
│   │       ├── orchestrator.py
│   │       └── state.py
│   ├── config/
│   │   └── courses.json
│   ├── requirements.txt
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── components/
│   │       │   └── chat/
│   │       └── services/
│   │           └── chat.ts
│   ├── package.json
│   └── angular.json
│
└── README.md
```

## RAG Grounding Strategy

GAIN-Radar is designed to reduce hallucinations by grounding answers in retrieved course material.

The answer prompt instructs the model to:

* use only the provided context
* avoid unsupported general knowledge
* avoid invented examples
* respond honestly when the material is insufficient
* mention which topics were found if the exact question is not covered

The context agent also checks whether enough usable context was retrieved before the answer agent generates a response.

## Session Memory

The backend stores conversation history per session.

When a user asks follow-up questions, the system can use recent conversation history to understand the context. This is especially useful for questions such as:

```text
Can you explain that again?
```

or:

```text
Give me an example.
```

The memory system uses a sliding window so that only recent messages are sent back to the LLM. This keeps prompts shorter and avoids unnecessary context growth.

## Current Limitations

* The chatbot depends on a correctly configured Pinecone index.
* Course documents must already be embedded and available in the expected namespaces.
* Only the tutor mode is actively used in the current frontend.
* The frontend currently targets a local backend URL.
* The system quality depends strongly on retrieval quality and the quality of the indexed course material.
* If the retrieved context is incomplete or irrelevant, the answer quality may decrease.

## Possible Future Improvements

* Add a document ingestion pipeline
* Add RAGAS evaluation scripts
* Add automated backend tests
* Add frontend unit tests for chat behavior
* Add admin view for failed or low-confidence answers
* Add reranking for retrieved chunks
* Add stricter source citation per answer sentence
* Add support for more learning modes such as quiz, flashcards and summaries
* Add deployment configuration with Docker
* Add configurable backend API URL for the frontend

## Contributors

* Filip Lazarevic
* Shivam Bhatt
* Samed Ali Kahraman

## License

No license specified yet.
