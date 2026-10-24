# ProjectForge

**A simple, self-hosted project management tool inspired by Jira and Confluence.** Track epics, stories, tasks, bugs, sprints, and project documentation in one lightweight application powered by React, FastAPI, and SQLite.

ProjectForge is intended for individuals and small teams who want a straightforward project tracker they can run locally without needing a cloud account or a separate database server.

## At a glance

- **Web UI:** React + TypeScript + Vite
- **API:** Python + FastAPI
- **Database:** SQLite; no database server installation required
- **Work tracking:** Epics, stories, tasks, bugs, subtasks, and spikes
- **Planning:** Kanban board, issue hierarchy, and sprint planning
- **Documentation:** Rich-text WYSIWYG pages with headings, formatting, lists, links, quotes, code blocks, and horizontal rules
- **Collaboration:** Issue comments and file attachments
- **Access:** Login, user directory, and basic roles
- **License:** MIT (see `LICENSE`)
- **Platform:** Designed to run on Windows, with manual setup also available on Linux/macOS

## Features

### Projects and work items

- Create, edit, and delete projects.
- Organize work with Jira-inspired issue types: **Epic, Story, Task, Bug, Sub-task, and Spike**.
- Record issue summaries, long-form rich-text descriptions, parent relationships, assignees, status, priority, story points, and due dates where supported by the UI.
- Edit and delete issues.
- Browse the parent-child issue tree, for example **Epic → Story → Task/Sub-task**.

### Kanban board and progress views

- View issues on a status-based Kanban board.
- Drag issue cards between status columns to update their status.
- Use the project dashboard to see issue counts, progress, and status/priority visualizations.
- Review issues in a table/list view.

### Sprint planning

- Create and manage project sprints.
- Set sprint goals and date ranges.
- Add or remove issues from a sprint.
- Update sprint state and remove sprints when needed.

### Issue details and collaboration

- Use the WYSIWYG editor for long Epic and Story descriptions, with headings, bold/italic/underline, lists, links, block quotes, code blocks and dividers.
- Add comments to issues and review the discussion in the issue UI.
- Upload and download issue attachments. The default per-file limit is **25 MB**.
- View parent/child relationships from the issue hierarchy.

### Project documentation

- Create, edit, and delete project knowledge pages.
- Write project documentation in a WYSIWYG editor with rich formatting. Existing plain-text and Markdown content remains readable; newly edited content is stored as HTML.
- Use pages to keep project notes, decisions, requirements, and lightweight technical documentation alongside tracked work.

### Users and administration

- Log in with a username and password.
- Browse the user directory and create users with the administrator account.
- Basic roles are available: `admin`, `manager`, `member`, and `viewer`.
- Audit-event endpoints are available for administrative review.

### Developer-friendly architecture

- React components, shared types, and API client are separated in the frontend.
- FastAPI owns business logic and SQLite access; the browser does not access the database file directly.
- SQLite tables are initialized by the backend, and attachment storage can be configured.
- The REST API is documented by FastAPI at `/docs`.
- The API/frontend separation leaves room for future modules, PostgreSQL, notifications, integrations, and desktop packaging.

## Quick start on Windows

### Requirements

- Python 3.11 or later
- Node.js 20 or later (includes `npm.cmd`)
- Windows PowerShell

### Option A: one-BAT launch

The repository includes `run-projectforge.bat`. It starts the API and frontend in separate terminal windows and installs missing dependencies on first launch.

Run it from the extracted repository root with two arguments:

1. The **full path to your Python virtual environment's `Activate.ps1`**.
2. The **full path to `npm.cmd`**.

Example using a virtual environment in this repository and the usual Node.js installation path:

```bat
run-projectforge.bat "%CD%\backend\.venv\Scripts\Activate.ps1" "C:\Program Files\nodejs\npm.cmd"
```

Or specify both paths explicitly:

```bat
run-projectforge.bat "C:\dev\projectforge\backend\.venv\Scripts\Activate.ps1" "C:\Program Files\nodejs\npm.cmd"
```

If you do not already have a virtual environment, create one first from the repository root:

```powershell
py -3.11 -m venv backend\.venv
```

The BAT file expects the activation script to exist. It checks for Python dependencies and installs `backend\requirements.txt` if needed; it runs `npm install` only when the frontend's `node_modules` folder is absent.

Once both terminals report that their services are ready, open:

- **Application:** http://localhost:5173
- **API documentation:** http://127.0.0.1:8000/docs
- **Health check:** http://127.0.0.1:8000/api/health

Demo login:

- Username: `admin`
- Password: `ChangeMe123!`

Change the demo password before using the application with real project data.

### Option B: manual setup

Open two terminals from the repository root.

**Terminal 1 — backend**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PROJECTFORGE_SECRET = "replace-with-a-long-random-secret"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend**

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Linux/macOS manual setup

**Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export PROJECTFORGE_SECRET="replace-with-a-long-random-secret"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Frontend**, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Configuration and local data

| Setting | Purpose | Default |
|---|---|---|
| `PROJECTFORGE_SECRET` | Secret used to sign authentication tokens | Set a strong secret for your environment |
| `PROJECTFORGE_DB` | SQLite database location | `./projectforge.db` relative to the backend working directory |
| `PROJECTFORGE_UPLOAD_DIR` | Attachment storage directory | `backend/uploads` |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | Development origins in `.env.example` |
| `VITE_API_URL` | API base URL for the frontend | `http://localhost:8000` |

The SQLite database is local to the backend, and uploaded files are stored on disk separately. Back up **both** the database and the uploads directory if you need to preserve project data and attachments.

## API

The API is available under `/api`. Explore the live interactive API reference at `http://127.0.0.1:8000/docs` while the backend is running. Core areas include authentication, users, projects, issues, comments, documents, sprints, attachments, analytics, audit events, and health status.

## Current scope and limitations

ProjectForge is a lightweight, evolving open-source MVP—not a drop-in replacement for Jira or Confluence. It is best suited to local evaluation, personal projects, and small trusted teams.

Before exposing it to the internet or using it for sensitive or business-critical data, review and strengthen authorization, project-level access enforcement, secret management, password/session lifecycle, CORS, HTTPS, attachment validation and malware scanning, backup/restore, database migrations, and automated tests. The WYSIWYG editor uses TipTap with StarterKit and Link/Underline extensions; rendered HTML is sanitized in the browser with DOMPurify. The Windows BAT launcher is a local development launcher, not a production service installer.

## Roadmap ideas

- Fine-grained project membership and permission enforcement
- Formal database migrations and automated test/CI workflows
- Document version history and collaborative editing
- Issue links, configurable workflows, filters, saved views, and notifications
- Burndown charts, velocity, workload planning, and portfolio views
- Docker Compose and backup/restore utilities
- Native desktop packaging with Tauri or Electron
- Optional PostgreSQL support for multi-user deployments

## Contributing

Issues, bug reports, feature requests, and pull requests are welcome. Please include reproduction steps for bugs and describe the expected behavior. For substantial changes, open an issue first so the design can be discussed before implementation.

## License

Distributed under the MIT License. See `LICENSE`.
