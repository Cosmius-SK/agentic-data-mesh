# Agentic Data Mesh — Data Chat Interface

Talk to your data in plain English. Upload files and ask questions.

## Supported file types

| Type | Extensions | What the agent can do |
|------|-----------|----------------------|
| Spreadsheet | `.csv`, `.xlsx`, `.xls` | Query rows, aggregate, filter, join, chart |
| PDF | `.pdf` | Extract text + tables, answer questions |
| Word | `.docx` | Extract text + tables, summarize |
| PowerPoint | `.pptx` | Extract slides + speaker notes, summarize |

## Example questions

- *"What are the top 10 products by revenue?"*
- *"Show me a bar chart of monthly sales"*
- *"Are there any missing values in the data?"*
- *"Summarize the key points from this PDF"*
- *"Merge the two CSV files on the customer ID column and show totals"*
- *"Which slide talks about Q3 results?"*

## How to use

1. Attach one or more files to your message
2. Ask a question — or just upload and explore
3. The agent will query your data, run calculations, and generate charts as needed

Uploaded files are saved to `data/uploads/` and reloaded automatically on next session.
