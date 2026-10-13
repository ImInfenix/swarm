# Swarm architecture

This document describes the intended architecture of Swarm. The 2022 prototype, preserved on the `prototype_2022` branch, uses Next.js, React, Prisma, and PostgreSQL; those technologies are not part of the architecture chosen below.

## 1. Technology choices and rationale

### Application: Python and Django 5.2

Django provides routing, page rendering, forms, validation, account management, permissions, data access, and migrations in one application. This integration reduces the number of components to assemble and maintain for a tool mainly built around lists, forms, and discussions.

The 5.2 release series supports Python 3.10, which is already installed in the development environment. Dependencies will be pinned to specific versions for reproducible installation.

### Data: SQLite

SQLite stores data in a local file. A single Swarm instance on one server can therefore run without a separate database service, simplifying development, installation, and self-hosting.

The database file will live in a persistent location outside files replaced during deployment. Backups must produce a consistent copy of a database in use, and restoration must be tested. The file will not be shared between servers over a network file system.

The data model will use Django ORM features shared across database engines wherever possible. A later move to PostgreSQL should then require migrating the schema, data, and deployment, without rewriting the application. SQLite remains the initial choice while load and concurrency needs allow it.

### Interface: Django templates, HTML, CSS, and plain JavaScript

The server renders the pages. CSS provides a responsive and accessible interface; JavaScript is reserved for interactions that improve usability. No frontend library is required for the first version. This approach avoids a second application, an API for every internal interaction, and a JavaScript build pipeline.

A lightweight library may be added later for a specific interaction if needed. React and Next.js are not used in this version.

The interface uses Django's built-in translations. English is the default language, and French remains available. A member's preference is saved with their account; a visitor's preference is stored in a cookie.

### External API: Django REST Framework

A versioned JSON API covers accounts, projects, their versions, tickets, votes, comments, and reports. Django REST Framework provides request validation, JSON responses, pagination, and access control without creating a second application or duplicating the data model. The HTML pages and API share the same business rules.

External clients use a revocable Bearer token valid for 30 days. Only its SHA-256 digest is stored in the database; the raw token is returned only when created. Public reads remain available without a token. Clients must use HTTPS in production. Calls from another website are not permitted by CORS in the initial configuration.

### Accounts and security: built-in Django features

Password authentication, sessions, cross-site request forgery protection, and access checks rely on Django. API clients use tokens separate from website sessions. Every sensitive operation checks permissions on the server. Account creation, votes, and reports are rate-limited with the local cache; the reverse proxy remains responsible for broader abuse protection. Login through an external provider may be considered later.

### Operations and verification

The intended deployment is a single application instance behind an HTTPS reverse proxy, with persistent storage for SQLite and any user-uploaded files. Migrations will be run explicitly during updates. Django's test tools will verify the main user flows and permission rules.

The prototype's PostgreSQL database will remain separate unless migration of its data is planned and verified. No secrets should be committed to the repository. Old local environment files have been removed; any real credentials they held must be rotated before deployment.

## 2. Application concept

Swarm is a community feedback platform for game developers and other projects. It brings together bug reports and feature requests, lets the community support important topics, and helps project owners organize the work.

### People and access

- A visitor can browse projects, tickets, and their discussions.
- A member can create a project, open a ticket, join discussions, vote on a topic, and report abusive content.
- A project's creator is its owner: they can edit its presentation and organize its tickets.
- A ticket's author can edit its description. Decisions about its progress belong to the project owner.
- An administrator can manage accounts, review reports, and hide content in cases of abuse or error.
- Anyone can use the interface in English or French. A member's choice is restored when they sign in again.
- A member can change their password, sign out on all devices, or delete their account. After deletion, their contributions remain visible without their name, and an administrator can take over their projects.

### Projects

Each project has a name, a description, and an owner. Its page brings together its tickets, highlights the most supported open requests, and lists released or planned versions. The owner creates and updates these versions; visitors can view them.

### Tickets

A ticket belongs to a project. Every contribution is either a **bug report** or a **feature request**. The type is required when creating a ticket through the web interface or API. A bug includes reproduction steps, expected behavior, actual behavior, and the affected version if known.

Each signed-in member can add or remove one vote per ticket. Votes make popular requests more visible without replacing the priority set by the owner during triage. The owner can set a target version and later record the version that contains the fix. They can also close a duplicate and point it to the original ticket; existing votes on the duplicate then count toward the original without counting the same member twice.

Ticket statuses are **open**, **in progress**, **needs information**, **resolved**, and **closed**. The owner can change a ticket's status and priority. Closing a ticket requires a reason and explanation, except when it is linked to a duplicate. Requests for information also include an explanation. Discussions remain visible after resolution.

Members can comment on a ticket to add details or follow its resolution. They can report an inappropriate ticket or comment. Creation time and latest activity are shown to provide context for the discussion.

### First-version user journey

A visitor explores projects and tickets, searches for an existing request, and filters or sorts by type, status, version, and popularity. A project roadmap separates tickets targeted for planned versions from tickets delivered in released versions. To contribute, visitors create an account and sign in. Ticket creation suggests possible duplicates. Members can open tickets, attach up to three images to bug reports, vote, reply, and follow tickets for notifications about comments and triage changes. The owner uses the triage dashboard, groups duplicates, plans versions, and moves tickets through to closure.

Real-time discussions and external integrations remain topics for later consideration.
