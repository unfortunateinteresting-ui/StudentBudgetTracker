# Student Budget Tracker

Standalone Windows desktop budget tracker built with `Tauri 2 + React + TypeScript + Rust + SQLite`.

This repository contains the rebuilt desktop application only. It does not include the old Python desktop app, Android prototype, packaged binaries, or generated report files from the original mixed workspace.

## Product Scope

- offline-first and local-only
- multi-account student cash-flow tracking
- typed ledger flows for `expense`, `funding`, `rent_credit`, `transfer`, and `adjustment`
- recurring bills, monthly caps, and school-year runway planning
- rent credit that offsets rent analytics only
- explainable metrics with shared backend snapshots
- automatic backups, recovery, undo, and legacy migration support

## Workspace Layout

- `Home`: balances, monthly pressure, runway, rent status, upcoming obligations, recent activity
- `Activity`: full ledger, filters, quick add, guided edit, delete, undo-aware actions
- `Plan`: recurring rules, monthly caps, school-year planning summary
- `Accounts`: account balances, transfers, reconciliation tools
- `Insights`: charts, monthly breakdowns, rent analysis, runway analysis, calculation drill-downs
- `Settings`: backups, migration, import/export, reset tools

## Stack

Frontend:

- React 18
- TypeScript
- Vite
- Radix UI primitives
- `visx`
- `Newsreader` and `IBM Plex Sans`

Backend:

- Tauri 2
- Rust
- SQLite with `rusqlite`
- `chrono`, `serde`, `uuid`

## Repository Layout

- [src/App.tsx](src/App.tsx)
- [src/components](src/components)
- [src/pages](src/pages)
- [src/lib](src/lib)
- [src-tauri/src/lib.rs](src-tauri/src/lib.rs)
- [src-tauri/src/models.rs](src-tauri/src/models.rs)
- [e2e-tests](e2e-tests)

## Prerequisites

Windows is the target platform for v1.

- Node.js 24+ with `corepack`
- Rust stable with the `x86_64-pc-windows-msvc` toolchain
- Visual Studio 2022 Build Tools with C++
- Microsoft Edge WebView2 Runtime

## Install

```powershell
corepack enable
pnpm install
rustup default stable-x86_64-pc-windows-msvc
```

## Development

Frontend only:

```powershell
pnpm dev
```

Full desktop app:

```powershell
pnpm tauri:dev
```

Production web build:

```powershell
pnpm build
```

Windows desktop bundle:

```powershell
pnpm tauri:build
```

Helper build script:

```powershell
.\build_windows.ps1
```

## Tests

Frontend tests:

```powershell
pnpm test
```

Rust tests:

```powershell
cargo test --manifest-path src-tauri/Cargo.toml
```

Windows end-to-end tests:

```powershell
pnpm test:e2e
```

## Migration And Data Safety

- SQLite is the single source of truth
- every mutation is atomic
- every mutation recomputes derived state and creates a timestamped backup
- backup retention defaults to `50`
- startup validates the database and can recover from the latest valid backup
- legacy SQLite and legacy JSON import paths remain supported

