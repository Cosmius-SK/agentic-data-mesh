# Sprint Plan: Sprint 1 (Foundations)

**Goal:** Establish the data ingestion pipeline and initial "Schema Discovery" using synthetic manufacturing data.

---

### 🎯 Sprint Goal
Successfully ingest 3-5 related manufacturing spreadsheets and have the AI identify at least one primary key relationship between them.

### 📋 Sprint Backlog
1. **ADM-001: Multi-file Ingestor**
   - Script to scan a local `/data` folder.
   - Load `.xlsx` and `.csv` using Pandas.
2. **ADM-003: Synthetic Data Setup**
   - Source 3 files: `Suppliers.xlsx`, `Production_Logs.csv`, `Inventory.xlsx`.
   - Ensure overlapping fields (e.g., `Part_ID`) exist for testing.
3. **ADM-002: Metadata Profiler**
   - Generate a JSON summary for each file (Columns, Non-null counts, Sample values).
4. **ADM-004: Entity Linker (PoC)**
   - Prompt AI to suggest which columns might be used for joins/vlookups.

### 🛠️ Definition of Done (DoD)
- [ ] Python script runs without errors for multiple file types.
- [ ] AI correctly identifies the link between `Part_ID` across at least two files.
- [ ] Documentation updated in GitHub.
