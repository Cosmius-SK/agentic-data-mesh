# Sprint Plan: Sprint 1 (The Live Mesh)

**Goal:** Deploy a functional Chainlit UI on GCP using Gemini 2.5 Flash to map synthetic data and render one dynamic trend chart.

---

### 🎯 Sprint Goal
Successfully host the app on GCP, link 3 synthetic CSVs using Gemini's reasoning, and render a Plotly chart in response to a natural language query.

### 📋 Sprint Backlog

#### Phase 1: Infrastructure (The "G" Setup)
- [ ] Configure VM (us-east1-b) with Python 3.10+ and a virtual environment.
- [ ] Set up GCP Firewall rules for Port 8080.
- [ ] Install lean dependencies: `chainlit`, `pandas`, `plotly`, `google-cloud-aiplatform`.

#### Phase 2: The Agentic Engine
- [ ] Implement **ADM-004**: Connect Gemini 2.5 Flash via Vertex AI.
- [ ] Create **Tool-Use** script: Functions for `list_files()` and `read_sample_rows()`.
- [ ] Test **ADM-006**: Prompt the agent to find a link between `Part_ID` and `Component_Code` and ask for user validation.

#### Phase 3: UI & Visualization
- [ ] Build the **Chainlit** wrapper (`app.py`).
- [ ] Implement a specific logic to trigger a **Plotly** chart when the user asks for a "trend" or "summary."
- [ ] Use `cl.Step` to display metadata profiling results in the UI.

### 🛠️ Definition of Done (DoD)
- [ ] App is reachable via External IP:8080.
- [ ] Agent correctly identifies relationships in the 3 synthetic CSVs.
- [ ] User can ask "Show me the production trend" and see a Plotly graph.
- [ ] Code is pushed to `main` branch.
