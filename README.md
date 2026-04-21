# Student Budget Tracker

Windows-first offline student budget tracker rebuilt as `Tauri 2 + React + TypeScript + Rust + SQLite`.

This repo is no longer centered on the original PySide desktop UI. The new app keeps the same local-only trust model and migration path, but moves calculations, persistence, backups, and recovery into Rust while React renders a single backend snapshot.

## Product Focus

The rebuild is not a generic budget tab app. It is shaped around student cash flow:

- multiple custom accounts
- typed ledger flows
- recurring bills and monthly caps
- rent credit that offsets rent only
- school-year runway from September through May by default
- explainable metrics with exact calculation breakdowns
- automatic backups, undo, recovery, and migration safety

## Workspace Model

The desktop app uses a left-sidebar workspace:

- `Home`: cash position, month pressure, runway, rent status, upcoming obligations, recent activity
- `Activity`: full ledger with quick add, guided entry, search, filters, edit/delete
- `Plan`: recurring rules, monthly caps, school-year planning summary, rent plan status
- `Accounts`: account balances, transfers, reconciliation actions
- `Insights`: charts, month-by-month source data, rent analysis, runway analysis
- `Settings`: migration, backups, undo, JSON import/export, reset tools

## Domain Model

Rust owns the core ledger semantics. Entry kinds are:

- `expense`: reduces one account and counts toward category spend
- `funding`: increases one account and never offsets category spend
- `rent_credit`: increases one account and offsets rent analytics only
- `transfer`: linked movement between two accounts
- `adjustment`: reconcile or correction entry tied to one account

Current v1 rules:

- rent is the only offset-style credit
- categories remain the only spend taxonomy
- `exclude_from_insights` keeps an entry in the ledger while excluding it from derived insight views
- recurring rules support `automatic`, `manual`, and `paused`
- recurring frequencies support `daily`, `weekly`, and `monthly`

## Data Safety

The app is offline-first and local-only in behavior.

- SQLite is the single source of truth
- every mutation is atomic
- every mutation triggers recomputation and a timestamped backup
- the app keeps the latest `50` backups
- startup validates the database
- corruption recovery restores the latest valid backup and surfaces a warning
- undo is action-based with a bounded stack

## Legacy Migration

The rebuild is designed to preserve history from the old app.

- first-run migration backs up the legacy database before changing anything
- legacy rows are moved into a default `Primary Account`
- legacy `income` becomes `funding`, except rent-related income which becomes `rent_credit`
- recurring legacy income follows the same conversion rule
- legacy JSON import remains supported
- the new exporter writes schema version `2`

## Tech Stack

Frontend:

- React 18
- TypeScript
- Vite
- Radix primitives for dialogs/tooltips
- `visx` for charts
- `Newsreader` and `IBM Plex Sans` for typography

Backend:

- Tauri 2
- Rust
- SQLite via `rusqlite`
- `chrono`, `serde`, `uuid`

## Prerequisites

Windows is the target platform for v1.

Install these before running the full desktop app:

- Node.js 24+ with `corepack` enabled, or another way to run `pnpm`
- Rust stable with the `x86_64-pc-windows-msvc` toolchain
- Visual Studio 2022 Build Tools with the C++ toolchain
- Microsoft Edge WebView2 Runtime

Without MSVC build tools, frontend-only checks can still pass, but `cargo test` and Tauri packaging will fail because `link.exe` is missing.

## Install

From the repo root:

```powershell
corepack enable
pnpm install
rustup default stable-x86_64-pc-windows-msvc
```

If `corepack` is not on `PATH`, use the local Node install you prefer and run `pnpm` through it.

## Development

Frontend only:

```powershell
pnpm dev
```

Full Tauri desktop app:

```powershell
pnpm tauri:dev
```

Production web build used by Tauri:

```powershell
pnpm build
```

Windows bundle:

```powershell
pnpm tauri:build
```

## Tests

Frontend tests:

```powershell
pnpm test
```

Rust unit tests:

```powershell
cargo test --manifest-path src-tauri/Cargo.toml
```

## Current Verification

Verified in this repo state:

- `pnpm test`
- `pnpm build`
- `cargo fmt --all --check --manifest-path src-tauri/Cargo.toml`
- `cargo test --manifest-path src-tauri/Cargo.toml`
- `pnpm tauri:dev` startup and desktop render smoke test
- `pnpm tauri:build`

## Project Layout

- [src/App.tsx](src/App.tsx)
- [src/pages](src/pages)
- [src/components](src/components)
- [src/lib](src/lib)
- [src-tauri/src/lib.rs](src-tauri/src/lib.rs)
- [src-tauri/src/models.rs](src-tauri/src/models.rs)

## Legacy Code

The original Python project files may still exist in the repo for reference or migration fixtures, but the active rebuild target is the Tauri desktop app described above.
