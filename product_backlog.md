# Product Backlog: Agentic Data Mesh

## Project Goal
Create an AI-driven data analysis partner that ingests fragmented manufacturing spreadsheets and allows for conversational, multi-source querying with high transparency.

---

### Epic 1: Foundation & Data Ingestion
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-001 | Multi-file Ingestor | As a user, I want to upload 10-20 .xlsx/.csv files so the system can access all raw data. | High | To Do |
| ADM-002 | Metadata Profiler | As a user, I want the system to extract headers, data types, and sample rows automatically. | High | To Do |
| ADM-003 | Synthetic Data Setup | As a developer, I need manufacturing datasets (Inventory, Production, Quality) to test logic. | Medium | To Do |

### Epic 2: Intelligent Schema Mapping (The Mesh)
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-004 | Entity Linker | As a user, I want the AI to suggest "Connecting Points" (IDs/Keys) between different files. | High | To Do |
| ADM-005 | Discrepancy Detector | As a user, I want the AI to flag when columns like 'Part_No' and 'Part_ID' represent the same entity. | Medium | To Do |

### Epic 3: Conversational Logic & Reasoning
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-006 | Query Parser | As a user, I want to ask questions in plain English (e.g., "What is our spend on Part X?"). | High | To Do |
| ADM-007 | Clarification Loop | As a user, I want the AI to ask me questions if data is ambiguous rather than guessing. | High | To Do |
| ADM-008 | Caveat Reporting | As a user, I want the AI to list the assumptions it made to arrive at a specific cost or metric. | Medium | To Do |

### Epic 4: Analytics & Projections
| ID | Title | User Story | Priority | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADM-009 | What-if Analysis | As a user, I want to simulate scenarios (e.g., "What if defect rates double?"). | Low | To Do |
| ADM-010 | Automated Metric Gen | As a user, I want the AI to automatically generate MIS-style reports from raw dumps. | Medium | To Do |
