# EasyDoc

Easy Doc Correct

EasyDoc corrects text in a document you already have. Upload a PDF, JPG, or PNG, change only the words you choose, and download a file that still looks like the original. It works on real documents such as receipts, bills, invoices, quotations, and statements, and it does not rebuild them from a template.

**Original document + edit operations = final document.** The upload is kept. Each change is stored as an operation (`replace_text`, `insert_text`, `delete_text`). Export applies those operations to a derived file.

## Stack

- Angular 20 frontend
- Python / FastAPI backend
- SQLite for local development, PostgreSQL (Neon or Docker) when configured
- Firebase Hosting for the frontend

## Run locally

Use two terminals from the repository root.

**API** at http://127.0.0.1:8000

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On macOS or Linux, activate with `source .venv/bin/activate`.

- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

Leave `DATABASE_URL` unset to use SQLite at `backend/storage/docedit.db`. Copy `backend/.env.example` when you want Postgres.

**App** at http://localhost:4200

```bash
cd frontend
npm install
npm start
```

The dev server calls `http://localhost:8000/api/v1`.

From the repository root you can also use `npm run backend` and `npm run frontend`.

## Docker

Postgres and the API:

```bash
npm run docker:up
```

Stop with `npm run docker:down`. The Angular app still runs with `npm run frontend`.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run frontend` | Start the Angular dev server |
| `npm run frontend:build` | Production build |
| `npm run backend` | Start the API on port 8000 |
| `npm run docker:up` | Build and start Postgres and the API |
| `npm run deploy:hosting` | Build the frontend and deploy Firebase Hosting |

## Product rule

Change only what the user edits. Leave logos, layout, background, and unrelated text as they are.
