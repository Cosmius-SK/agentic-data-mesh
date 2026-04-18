# Product Backlog: Agentic Data Mesh

## Project Goal
Create an AI-driven data partner that ingests fragmented manufacturing spreadsheets and allows for conversational, multi-source querying with high transparency and "human-in-the-loop" validation.

---

### Epic 1: Foundation & Data Ingestion
| ID | Title | User Story | Priority |
| :--- | :--- | :--- | :--- |
| ADM-001 | Multi-file Ingestor | As a user, I want to upload 10-20 .xlsx/.csv files so the system can access all raw data. | High |
| ADM-002 | Metadata Profiler | As a user, I want the system to extract headers, data types, and sample rows automatically. | High |
| ADM-003 | Synthetic Data Setup | As a developer, I need manufacturing datasets (Inventory, Production, Quality) to test logic. | Medium |

### Epic 2: Intelligent Schema Mapping (The Mesh)
| ID | Title | User Story | Priority |
| :--- | :--- | :--- | :--- |
| ADM-004 | Entity Linker | As a user, I want the AI to suggest "Connecting Points" (IDs/Keys) between different files. | High |
| ADM-005 | Discrepancy Detector | As a user, I want the AI to flag when columns like 'Part_No' and 'Part_ID' represent the same thing. | Medium |

### Epic 3: Conversational Logic & Reasoning
| ID | Title | User Story | Priority |
| :--- | :--- | :--- | :--- |
| ADM-006 | Query Parser | As a user, I want to ask questions in plain English (e.g., "How much was spent on X?"). | High |
| ADM-007 | Clarification Loop | As a user, I want the AI to ask me questions if data is ambiguous rather than guessing. | High |
| ADM-008 | Caveat Reporting | As a user, I want the AI to list the assumptions it made to arrive at a cost or metric. | Medium |
