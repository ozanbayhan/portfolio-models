# Security policy

## Supported versions

Only the latest release and `main` receive fixes.

## Reporting a vulnerability

Please **do not** open a public issue. Use
[GitHub's private vulnerability reporting](https://github.com/ozanbayhan/portfolio-models/security/advisories/new)
instead. You will get an answer within a week.

Of particular interest: anything that lets one signed-in user read or change another user's data, leaks secrets,
or allows code execution through uploaded files.

## Hardening tips for self-hosters

- Serve over HTTPS (see [docs/self-hosting.md](docs/self-hosting.md#https-with-a-reverse-proxy)).
- Set a long, fixed `PM_COOKIE_SECRET` and keep `.env` out of version control.
- Use a dedicated database user and keep regular backups.
- Keep the image up to date: `docker compose pull && docker compose up -d`.
