# Product Backlog: Agentic Data Mesh

## Project Goal
Create a lightweight, AI-driven data partner that ingests fragmented manufacturing spreadsheets and allows for conversational querying, real-time visualization, and "human-in-the-loop" validation, hosted on GCP.

---

### Epic 1: Cloud Foundation & Ingestion
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-001 | Lean GCP Setup | As a dev, I need to configure a 1GB RAM VM in us-east1-b with port 8080 open for Chainlit. | High | To Do |
| ADM-002 | Multi-file Ingestor | As a user, I want to scan a /data folder for .xlsx/.csv files without overloading memory. | High | To Do |
| ADM-003 | Metadata Profiler | As an agent, I need a JSON summary (headers/types) to understand the mesh structure. | High | To Do |

### Epic 2: Agentic Intelligence (Gemini 2.5 Flash)
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-004 | Vertex AI Integration | As a dev, I want to use Gemini 2.5 Flash via SDK to offload heavy reasoning from the VM. | High | To Do |
| ADM-005 | Function Calling Logic | As an agent, I want to "call" Python tools to slice data only when needed (Lazy Loading). | High | To Do |
| ADM-006 | The "SK" Clarification Loop | As an agent, I must pause and ask SK for confirmation on ambiguous join keys. | High | To Do |

### Epic 3: UI & Visual Analytics
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-007 | Chainlit Chat Interface | As a user, I want a clean chat UI to interact with my data mesh. | High | To Do |
| ADM-008 | Inline Plotly Charts | As a user, I want to see trend lines and defect charts rendered directly in the chat. | Medium | To Do |
| ADM-009 | Step-by-Step Reasoning | As a user, I want to see the "Agent's Thoughts" as it processes multiple files. | Medium | To Do |
