# Offline Budget Tracker Android (APK Starter)

This folder contains a native Android app starter for your budget tracker.

## What is implemented now

- Offline-only local storage with SQLite (`budget_android.db`).
- Indiana timezone default (`America/Indiana/Indianapolis`).
- Tabs:
  - Dashboard
  - Add Entry
  - Transactions
  - Recurring
  - Settings
- Quick add parser (`42 Walmart`).
- Automatic recurring catch-up on startup (with notification dialog).
- Recurring supports `daily`, `weekly`, `monthly` and `automatic/manual/paused`.
- Dashboard "show work" section for calculations.
- Monthly totals table (plan vs projected).
- Import/Export compatibility JSON with desktop schema:
  - `settings`
  - `transactions`
  - `recurring_charges`
  - `categories`

## Build APK (Android Studio)

1. Install Android Studio.
2. Open this folder as a project:
   - `Offline_budget_tracker/Offline_budget_tracker/android_app`
3. Let Gradle sync and install SDK components when prompted.
4. Build debug APK:
   - Menu: `Build -> Build Bundle(s) / APK(s) -> Build APK(s)`
5. APK output path:
   - `app/build/outputs/apk/debug/app-debug.apk`

Optional helper script:

```powershell
.\setup_android_toolchain.ps1
```

## Build APK (command line)

After Android SDK is installed and `local.properties` exists:

```powershell
cd C:\Users\mouzzia\Desktop\Offline_budget_tracker\Offline_budget_tracker\android_app
.\gradlew.bat assembleDebug
```

## Notes

- This is a clean APK-first foundation. We can now port the remaining desktop-specific features one by one (PDF export design, Excel export, advanced projections, multi-theme/font customizer, language pack updates).
- The Android DB is separate from your desktop `budget.db` to avoid accidental data corruption while we iterate.
- Export default filename: `budget_history_export.json` (desktop importer-compatible).
