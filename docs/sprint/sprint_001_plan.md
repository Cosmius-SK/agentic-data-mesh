# Sprint Plan: Sprint 1 (Foundations)

**Duration:** [Set Dates Here]
**Goal:** Establish the data ingestion pipeline and initial "Schema Discovery" using synthetic manufacturing data.

---

### 🎯 Sprint Goal
Successfully ingest 3-5 related manufacturing spreadsheets and have the AI identify at least one primary key relationship between them.

### 📋 Sprint Backlog (User Stories)

1. **ADM-001: Multi-file Ingestor**
   - *Task:* Create a Python script to scan a local `/data` folder.
   - *Task:* Load `.xlsx` and `.csv` using Pandas.
   - *Task:* Log file names and row counts.

2. **ADM-003: Synthetic Data Setup**
   - *Task:* Download or generate 3 files: `Suppliers.xlsx`, `Production_Logs.csv`, `Inventory.xlsx`.
   - *Task:* Ensure overlapping fields (e.g., `Part_ID`) exist for testing.

3. **ADM-002: Metadata Profiler**
   - *Task:* Generate a JSON summary for each file (Columns, Non-null counts, Sample values).
   - *Task:* Feed this summary to the LLM to test "General Understanding."

4. **ADM-004: Entity Linker (Initial Proof of Concept)**
   - *Task:* Prompt LLM to suggest which columns might be used for VLOOKUP-style joins.
   - *Task:* Display these suggestions to the user for validation.

### 🛠️ Definition of Done (DoD)
- [ ] Python script runs without errors for multiple file types.
- [ ] JSON metadata summaries are generated for all files in the folder.
- [ ] AI correctly identifies the link between `Part_ID` across at least two files.
- [ ] Documentation updated in GitHub.

### 📉 Risks & Mitigations
- **Risk:** LLM hallucinating connections.
- **Mitigation:** Implement the "Clarification Loop" where the user must confirm a link before it is stored.
