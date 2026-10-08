# Student Placement Management System — Frontend Demo

This frontend follows the synopsis technology stack: **HTML, CSS, and vanilla JavaScript**. It runs without a backend and stores demo changes in your browser with `localStorage`.

## Run the demo

1. Extract the ZIP into `D:\Mini Project\Frontend`.
2. Open `index.html` in a modern browser. A local web server such as VS Code Live Server also works.
3. From the landing page, choose **Get started** or **Student login**.

### Demo access

- Student: `aarav@example.com` with any password of at least 6 characters. Student sign-in accepts any email; an email not in the demo data opens the first sample student. Registration creates a separate local demo profile.
- Admin: `admin@pathway.demo` / `admin123`

## Included pages

- Landing page, student login and registration
- Student overview, profile, opportunity search and filters, job details and eligibility, application tracking and notifications
- Admin login and overview, student directory, company management, job posting and application status management

## Demo behavior and reset

Applications, profile edits, new companies, posted jobs, notification changes and saved roles persist in the current browser. This is demo-only storage and is not shared between devices or users. To reset to the sample data, clear this site's browser storage (for a file URL, clear storage for the page's file origin) and reload.

## Backend handoff

The selected backend and database are still undecided in the synopsis, so this package has no framework or server dependency. In `js/app.js`, the `Store` helpers currently read and write local demo data. The `API_BASE` and `api.request()` helper mark the fetch integration point. Replace the relevant store operations with endpoint calls when the backend API contract is ready. For production, the backend should own authentication, authorization, eligibility checks, and persistent data; file-name resume fields are placeholders for a real upload endpoint.

## Project structure

```text
Frontend/
├── index.html, login.html, register.html
├── student/       student-facing pages
├── admin/         placement-cell pages
├── css/styles.css shared responsive styles
├── js/app.js      page rendering, validation and demo data
└── README.md
```