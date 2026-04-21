package com.mouzzia.offlinebudget

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.util.UUID

private const val DB_NAME = "budget_android.db"
private const val DB_VERSION = 2

private val CSV_TRANSACTION_HEADER_MAP = mapOf(
    "date" to "datetime_local",
    "datetime" to "datetime_local",
    "datetime local" to "datetime_local",
    "datetime_local" to "datetime_local",
    "type" to "type",
    "amount" to "amount",
    "montant" to "amount",
    "label" to "label",
    "libelle" to "label",
    "category" to "category",
    "categorie" to "category",
    "notes" to "notes",
    "id" to "id",
    "uuid" to "id",
    "transaction id" to "id",
    "transaction_id" to "id",
    "transactionid" to "id",
    "recurring id" to "recurring_id",
    "recurring_id" to "recurring_id",
    "recurringid" to "recurring_id",
    "id recurrent" to "recurring_id",
    "excluded from averages" to "excluded_from_averages",
    "exclude from averages" to "excluded_from_averages",
    "avg excluded" to "excluded_from_averages",
    "exclu des moyennes" to "excluded_from_averages",
)

private val IMPORT_TYPE_ALIASES = mapOf(
    "expense" to "expense",
    "depense" to "expense",
    "income" to "income",
    "revenu" to "income",
)

private data class RecurringFingerprint(
    val label: String,
    val amount: Double,
    val type: String,
    val category: String,
    val notes: String,
    val startDate: String,
    val endDate: String,
    val frequency: String,
    val status: String,
)

data class ImportCompatResult(
    val transactionsAdded: Int,
    val transactionsSkipped: Int,
    val recurringAdded: Int,
    val recurringSkipped: Int,
    val categoriesAdded: Int,
    val settingsUpdated: Boolean,
)

class BudgetDbHelper(context: Context) : SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE transactions (
                id TEXT PRIMARY KEY,
                datetime_local TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                label TEXT,
                category TEXT,
                notes TEXT,
                recurring_id TEXT,
                excluded_from_averages INTEGER NOT NULL DEFAULT 0
            )
            """.trimIndent()
        )

        db.execSQL(
            """
            CREATE TABLE recurring (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category TEXT,
                notes TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                frequency TEXT NOT NULL,
                status TEXT NOT NULL,
                last_applied_date TEXT
            )
            """.trimIndent()
        )

        db.execSQL(
            """
            CREATE TABLE categories (
                name TEXT PRIMARY KEY
            )
            """.trimIndent()
        )

        db.execSQL(
            """
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                starting_balance REAL NOT NULL DEFAULT 0,
                counted_balance REAL,
                refunds_total REAL NOT NULL DEFAULT 0,
                plan_months_total INTEGER NOT NULL DEFAULT 9,
                months_elapsed INTEGER NOT NULL DEFAULT 0,
                rent_base_monthly REAL NOT NULL DEFAULT 650,
                rent_monthly_manual REAL NOT NULL DEFAULT 0,
                food_house_monthly REAL NOT NULL DEFAULT 200,
                misc_monthly REAL NOT NULL DEFAULT 50,
                medical_monthly REAL NOT NULL DEFAULT 0,
                school_monthly REAL NOT NULL DEFAULT 0,
                household_monthly REAL NOT NULL DEFAULT 0,
                health_monthly REAL NOT NULL DEFAULT 0,
                auto_misc_enabled INTEGER NOT NULL DEFAULT 0,
                auto_misc_categories TEXT NOT NULL DEFAULT '[]',
                auto_include_recurring INTEGER NOT NULL DEFAULT 0,
                auto_include_current_month INTEGER NOT NULL DEFAULT 0,
                auto_window_months INTEGER NOT NULL DEFAULT 3,
                auto_weighted INTEGER NOT NULL DEFAULT 0,
                auto_weight_half_life_months INTEGER NOT NULL DEFAULT 6,
                extra_monthly REAL NOT NULL DEFAULT 0,
                rent_surcharge_amount REAL NOT NULL DEFAULT 144,
                rent_surcharge_months INTEGER NOT NULL DEFAULT 3,
                campus_reference_total REAL NOT NULL DEFAULT 17256,
                language TEXT NOT NULL DEFAULT 'EN',
                theme TEXT NOT NULL DEFAULT 'Dune',
                font_family TEXT NOT NULL DEFAULT '',
                accent_color TEXT NOT NULL DEFAULT '',
                school_year_start_month INTEGER NOT NULL DEFAULT 9
            )
            """.trimIndent()
        )

        db.insert("settings", null, ContentValues().apply { put("id", 1) })
        insertDefaultCategories(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            ensureColumn(db, "transactions", "recurring_id", "TEXT")
            ensureColumn(db, "transactions", "excluded_from_averages", "INTEGER NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "counted_balance", "REAL")
            ensureColumn(db, "settings", "plan_months_total", "INTEGER NOT NULL DEFAULT 9")
            ensureColumn(db, "settings", "months_elapsed", "INTEGER NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "rent_base_monthly", "REAL NOT NULL DEFAULT 650")
            ensureColumn(db, "settings", "rent_monthly_manual", "REAL NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "food_house_monthly", "REAL NOT NULL DEFAULT 200")
            ensureColumn(db, "settings", "misc_monthly", "REAL NOT NULL DEFAULT 50")
            ensureColumn(db, "settings", "medical_monthly", "REAL NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "school_monthly", "REAL NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "household_monthly", "REAL NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "health_monthly", "REAL NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "auto_misc_enabled", "INTEGER NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "auto_misc_categories", "TEXT NOT NULL DEFAULT '[]'")
            ensureColumn(db, "settings", "auto_include_recurring", "INTEGER NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "auto_include_current_month", "INTEGER NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "auto_window_months", "INTEGER NOT NULL DEFAULT 3")
            ensureColumn(db, "settings", "auto_weighted", "INTEGER NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "auto_weight_half_life_months", "INTEGER NOT NULL DEFAULT 6")
            ensureColumn(db, "settings", "extra_monthly", "REAL NOT NULL DEFAULT 0")
            ensureColumn(db, "settings", "rent_surcharge_amount", "REAL NOT NULL DEFAULT 144")
            ensureColumn(db, "settings", "rent_surcharge_months", "INTEGER NOT NULL DEFAULT 3")
            ensureColumn(db, "settings", "language", "TEXT NOT NULL DEFAULT 'EN'")
            ensureColumn(db, "settings", "theme", "TEXT NOT NULL DEFAULT 'Dune'")
            ensureColumn(db, "settings", "font_family", "TEXT NOT NULL DEFAULT ''")
            ensureColumn(db, "settings", "accent_color", "TEXT NOT NULL DEFAULT ''")
            ensureColumn(db, "settings", "school_year_start_month", "INTEGER NOT NULL DEFAULT 9")

            db.execSQL("CREATE TABLE IF NOT EXISTS categories (name TEXT PRIMARY KEY)")
            db.execSQL("INSERT OR IGNORE INTO settings(id) VALUES (1)")
        }
        insertDefaultCategories(db)
    }

    private fun ensureColumn(db: SQLiteDatabase, table: String, column: String, definition: String) {
        db.rawQuery("PRAGMA table_info($table)", null).use { c ->
            while (c.moveToNext()) {
                if (c.getString(c.getColumnIndexOrThrow("name")) == column) {
                    return
                }
            }
        }
        db.execSQL("ALTER TABLE $table ADD COLUMN $column $definition")
    }
}

class BudgetStore(private val dbHelper: BudgetDbHelper) {

    init {
        repairLegacyRecurringDates()
        ensureCategories(DEFAULT_CATEGORIES)
    }

    private fun repairLegacyRecurringDates() {
        val db = dbHelper.writableDatabase
        db.execSQL(
            """
            UPDATE recurring
            SET end_date = NULL
            WHERE end_date IS NOT NULL
              AND TRIM(LOWER(end_date)) IN ('', 'null', 'none', 'nil', 'nan')
            """.trimIndent()
        )
        db.execSQL(
            """
            UPDATE recurring
            SET last_applied_date = NULL
            WHERE last_applied_date IS NOT NULL
              AND TRIM(LOWER(last_applied_date)) IN ('', 'null', 'none', 'nil', 'nan')
            """.trimIndent()
        )
        db.rawQuery("SELECT id, start_date, end_date, last_applied_date FROM recurring", null).use { c ->
            while (c.moveToNext()) {
                val id = c.getString(c.getColumnIndexOrThrow("id"))
                val startRaw = c.getStringOrEmpty("start_date")
                val endRaw = c.getNullableString("end_date")
                val lastRaw = c.getNullableString("last_applied_date")

                val normalizedStart = parseLocalDateOrNull(startRaw)?.toString()
                    ?: LocalDate.now(APP_ZONE).toString()
                val normalizedEnd = parseLocalDateOrNull(endRaw)?.toString()
                val normalizedLast = parseLocalDateOrNull(lastRaw)?.toString()

                val needsUpdate =
                    normalizedStart != startRaw ||
                    normalizedEnd != endRaw ||
                    normalizedLast != lastRaw
                if (!needsUpdate) continue

                val values = ContentValues().apply {
                    put("start_date", normalizedStart)
                    put("end_date", normalizedEnd)
                    put("last_applied_date", normalizedLast)
                }
                db.update("recurring", values, "id = ?", arrayOf(id))
            }
        }
    }

    fun loadSettings(): AppSettings {
        val db = dbHelper.readableDatabase
        db.rawQuery("SELECT * FROM settings WHERE id = 1", null).use { c ->
            if (!c.moveToFirst()) return AppSettings()
            return AppSettings(
                startingBalance = c.getDoubleOrZero("starting_balance"),
                countedBalance = c.getNullableDouble("counted_balance"),
                refundsTotal = c.getDoubleOrZero("refunds_total"),
                planMonthsTotal = c.getIntOrZero("plan_months_total").coerceAtLeast(1),
                monthsElapsed = c.getIntOrZero("months_elapsed").coerceAtLeast(0),
                rentBaseMonthly = c.getDoubleOrZero("rent_base_monthly"),
                rentMonthlyManual = c.getDoubleOrZero("rent_monthly_manual"),
                campusReferenceTotal = c.getDoubleOrZero("campus_reference_total"),
                foodMonthly = c.getDoubleOrZero("food_house_monthly"),
                miscMonthly = c.getDoubleOrZero("misc_monthly"),
                medicalMonthly = c.getDoubleOrZero("medical_monthly"),
                schoolMonthly = c.getDoubleOrZero("school_monthly"),
                householdMonthly = c.getDoubleOrZero("household_monthly"),
                healthMonthly = c.getDoubleOrZero("health_monthly"),
                autoMiscEnabled = c.getIntOrZero("auto_misc_enabled") == 1,
                autoMiscCategories = parseJsonStringList(c.getStringOrEmpty("auto_misc_categories")),
                autoIncludeRecurring = c.getIntOrZero("auto_include_recurring") == 1,
                includeCurrentMonthInAvg = c.getIntOrZero("auto_include_current_month") == 1,
                avgWindowMonths = c.getIntOrZero("auto_window_months").coerceAtLeast(1),
                autoWeighted = c.getIntOrZero("auto_weighted") == 1,
                autoWeightHalfLifeMonths = c.getIntOrZero("auto_weight_half_life_months").coerceAtLeast(1),
                extraMonthly = c.getDoubleOrZero("extra_monthly"),
                rentSurchargeAmount = c.getDoubleOrZero("rent_surcharge_amount"),
                rentSurchargeMonths = c.getIntOrZero("rent_surcharge_months").coerceAtLeast(0),
                language = c.getStringOrEmpty("language").ifBlank { "EN" },
                theme = c.getStringOrEmpty("theme").ifBlank { "Dune" },
                fontFamily = c.getStringOrEmpty("font_family"),
                accentColor = c.getStringOrEmpty("accent_color"),
                schoolYearStartMonth = c.getIntOrZero("school_year_start_month").coerceIn(1, 12),
            )
        }
    }

    fun saveSettings(s: AppSettings) {
        val db = dbHelper.writableDatabase
        val values = settingsToValues(s)
        db.update("settings", values, "id = 1", null)
    }

    fun listCategories(): List<String> {
        val db = dbHelper.readableDatabase
        db.rawQuery("SELECT name FROM categories ORDER BY name ASC", null).use { c ->
            val out = mutableListOf<String>()
            while (c.moveToNext()) out += c.getString(c.getColumnIndexOrThrow("name"))
            return out
        }
    }

    fun ensureCategories(names: List<String>): Int {
        val cleaned = names.mapNotNull { normalizeCategoryName(it) }.distinctBy { it.lowercase() }
        if (cleaned.isEmpty()) return 0
        val existing = listCategories().map { it.lowercase() }.toMutableSet()
        var added = 0
        val db = dbHelper.writableDatabase
        cleaned.forEach { name ->
            if (existing.add(name.lowercase())) {
                db.insert("categories", null, ContentValues().apply { put("name", name) })
                added += 1
            }
        }
        return added
    }

    fun resetAllData() {
        val db = dbHelper.writableDatabase
        val current = loadSettings()
        val resetSettings = AppSettings(
            language = normalizeLanguageCode(current.language),
            theme = current.theme,
            fontFamily = current.fontFamily,
            accentColor = current.accentColor,
        )
        db.beginTransaction()
        try {
            db.delete("transactions", null, null)
            db.delete("recurring", null, null)
            db.delete("categories", null, null)
            db.delete("settings", "id = 1", null)
            db.insert(
                "settings",
                null,
                settingsToValues(resetSettings).apply { put("id", 1) }
            )
            insertDefaultCategories(db)
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    fun insertTransaction(tx: TransactionRecord) {
        val db = dbHelper.writableDatabase
        ensureCategories(listOf(tx.category))
        db.insert("transactions", null, tx.toValues())
    }

    fun deleteTransaction(id: String) {
        val db = dbHelper.writableDatabase
        db.delete("transactions", "id = ?", arrayOf(id))
    }

    fun updateTransaction(tx: TransactionRecord) {
        val db = dbHelper.writableDatabase
        ensureCategories(listOf(tx.category))
        db.update("transactions", tx.toValues(), "id = ?", arrayOf(tx.id))
    }

    fun updateTransactionExclusion(id: String, excluded: Boolean) {
        val db = dbHelper.writableDatabase
        val values = ContentValues().apply { put("excluded_from_averages", if (excluded) 1 else 0) }
        db.update("transactions", values, "id = ?", arrayOf(id))
    }

    fun listTransactions(): List<TransactionRecord> {
        val db = dbHelper.readableDatabase
        db.rawQuery("SELECT * FROM transactions ORDER BY datetime_local DESC", null).use { c ->
            val out = mutableListOf<TransactionRecord>()
            while (c.moveToNext()) out += c.toTransaction()
            return out
        }
    }

    fun listTransactionsBetween(startIso: String, endIso: String): List<TransactionRecord> {
        val db = dbHelper.readableDatabase
        db.rawQuery(
            "SELECT * FROM transactions WHERE datetime_local >= ? AND datetime_local <= ? ORDER BY datetime_local ASC",
            arrayOf(startIso, endIso),
        ).use { c ->
            val out = mutableListOf<TransactionRecord>()
            while (c.moveToNext()) out += c.toTransaction()
            return out
        }
    }

    fun insertRecurring(r: RecurringCharge) {
        val db = dbHelper.writableDatabase
        ensureCategories(listOf(r.category))
        db.insert("recurring", null, r.toValues())
    }

    fun updateRecurring(r: RecurringCharge) {
        val db = dbHelper.writableDatabase
        ensureCategories(listOf(r.category))
        db.update("recurring", r.toValues(), "id = ?", arrayOf(r.id))
    }

    fun deleteRecurring(id: String) {
        val db = dbHelper.writableDatabase
        db.delete("recurring", "id = ?", arrayOf(id))
    }

    fun listRecurring(): List<RecurringCharge> {
        val db = dbHelper.readableDatabase
        db.rawQuery("SELECT * FROM recurring ORDER BY start_date ASC", null).use { c ->
            val out = mutableListOf<RecurringCharge>()
            while (c.moveToNext()) out += c.toRecurring()
            return out
        }
    }

    fun applyDueRecurring(todayIso: String = nowLocal().toLocalDate().toString()): List<String> {
        val today = parseLocalDate(todayIso)
        val recurring = listRecurring()
        val appliedSummary = mutableListOf<String>()

        recurring.forEach { r ->
            if (r.status.lowercase() != "automatic") return@forEach
            if (r.type.lowercase() !in setOf("expense", "income")) return@forEach
            val last = r.lastAppliedDate?.let { parseLocalDate(it) }
            val dueDates = dueDatesBetween(r, last, today)
            if (dueDates.isEmpty()) return@forEach

            dueDates.forEach { date ->
                val tx = TransactionRecord(
                    datetimeLocal = date.atTime(12, 0).toString(),
                    amount = r.amount,
                    type = r.type,
                    label = r.label,
                    category = r.category,
                    notes = if (r.notes.isBlank()) "Applied from recurring" else r.notes,
                    recurringId = r.id,
                )
                insertTransaction(tx)
            }

            val updated = r.copy(lastAppliedDate = dueDates.last().toString())
            updateRecurring(updated)
            appliedSummary += "${r.label}: +${dueDates.size}"

            val endDate = parseLocalDateOrNull(r.endDate)
            if (endDate != null && endDate.isBefore(today)) {
                updateRecurring(updated.copy(status = "paused"))
            }
        }

        return appliedSummary
    }

    fun exportCompatJson(
        settings: AppSettings = loadSettings(),
        transactions: List<TransactionRecord> = listTransactions(),
        recurring: List<RecurringCharge> = listRecurring(),
    ): String {
        val categories = (listCategories() + transactions.map { it.category } + recurring.map { it.category })
            .mapNotNull { normalizeCategoryName(it) }
            .distinctBy { it.lowercase() }
            .sortedBy { it.lowercase() }

        val root = JSONObject()
        root.put("app", "OfflineBudgetTrackerAndroid")
        root.put("exported_at", nowLocalIso())
        root.put("timezone", TZ_NAME)

        val settingsObj = JSONObject()
        settingsObj.put("starting_balance", settings.startingBalance)
        settingsObj.put("counted_balance", settings.countedBalance)
        settingsObj.put("refunds_total", settings.refundsTotal)
        settingsObj.put("plan_months_total", settings.planMonthsTotal)
        settingsObj.put("months_elapsed", settings.monthsElapsed)
        settingsObj.put("rent_base_monthly", settings.rentBaseMonthly)
        settingsObj.put("rent_monthly_manual", settings.rentMonthlyManual)
        settingsObj.put("food_house_monthly", settings.foodMonthly)
        settingsObj.put("misc_monthly", settings.miscMonthly)
        settingsObj.put("medical_monthly", settings.medicalMonthly)
        settingsObj.put("school_monthly", settings.schoolMonthly)
        settingsObj.put("household_monthly", settings.householdMonthly)
        settingsObj.put("health_monthly", settings.healthMonthly)
        settingsObj.put("auto_misc_enabled", settings.autoMiscEnabled)
        settingsObj.put("auto_misc_categories", JSONArray(settings.autoMiscCategories))
        settingsObj.put("auto_include_recurring", settings.autoIncludeRecurring)
        settingsObj.put("auto_include_current_month", settings.includeCurrentMonthInAvg)
        settingsObj.put("auto_window_months", settings.avgWindowMonths)
        settingsObj.put("auto_weighted", settings.autoWeighted)
        settingsObj.put("auto_weight_half_life_months", settings.autoWeightHalfLifeMonths)
        settingsObj.put("extra_monthly", settings.extraMonthly)
        settingsObj.put("rent_surcharge_amount", settings.rentSurchargeAmount)
        settingsObj.put("rent_surcharge_months", settings.rentSurchargeMonths)
        settingsObj.put("campus_reference_total", settings.campusReferenceTotal)
        settingsObj.put("language", settings.language)
        settingsObj.put("theme", settings.theme)
        settingsObj.put("font_family", settings.fontFamily)
        settingsObj.put("accent_color", settings.accentColor)
        settingsObj.put("school_year_start_month", settings.schoolYearStartMonth)
        root.put("settings", settingsObj)

        val txArray = JSONArray()
        transactions.sortedByDescending { it.datetimeLocal }.forEach { tx ->
            txArray.put(
                JSONObject().apply {
                    put("id", tx.id)
                    put("datetime_local", tx.datetimeLocal)
                    put("amount", tx.amount)
                    put("type", tx.type)
                    put("label", tx.label)
                    put("category", tx.category)
                    put("notes", tx.notes)
                    put("recurring_id", tx.recurringId)
                    put("excluded_from_averages", tx.excludedFromAuto)
                }
            )
        }
        root.put("transactions", txArray)

        val recurringArray = JSONArray()
        recurring.forEach { r ->
            recurringArray.put(
                JSONObject().apply {
                    put("id", r.id)
                    put("label", r.label)
                    put("amount", r.amount)
                    put("type", r.type)
                    put("category", r.category)
                    put("notes", r.notes)
                    put("start_date", r.startDate)
                    put("end_date", r.endDate)
                    put("status", r.status)
                    put("frequency", r.frequency)
                    put("last_applied", r.lastAppliedDate)
                }
            )
        }
        root.put("recurring_charges", recurringArray)
        root.put("categories", JSONArray(categories))
        return root.toString(2)
    }

    fun importCompatData(displayName: String?, rawText: String): ImportCompatResult {
        val normalizedText = rawText.removePrefix("\uFEFF")
        val loweredName = displayName?.trim()?.lowercase().orEmpty()
        return when {
            loweredName.endsWith(".csv") -> importCompatCsv(normalizedText)
            loweredName.endsWith(".json") -> importCompatJson(normalizedText)
            normalizedText.trimStart().startsWith("{") || normalizedText.trimStart().startsWith("[") -> importCompatJson(normalizedText)
            looksLikeCsv(normalizedText) -> importCompatCsv(normalizedText)
            else -> throw IllegalArgumentException("Unsupported import file. Use JSON or CSV.")
        }
    }

    fun importCompatJson(jsonText: String): ImportCompatResult {
        val payload = JSONObject(jsonText)

        val settingsObj = payload.optJSONObject("settings")
        val txArray = payload.optJSONArray("transactions") ?: JSONArray()
        val recurringArray = payload.optJSONArray("recurring_charges")
            ?: payload.optJSONArray("recurring")
            ?: JSONArray()
        val categoriesArray = payload.optJSONArray("categories") ?: JSONArray()

        val parsedCategories = mutableListOf<String>()
        for (i in 0 until categoriesArray.length()) {
            parsedCategories += categoriesArray.optString(i)
        }

        val existingTxFingerprints = listTransactions().map { fingerprintTx(it) }.toMutableSet()
        var txAdded = 0
        var txSkipped = 0

        for (i in 0 until txArray.length()) {
            val obj = txArray.optJSONObject(i) ?: continue
            val tx = parseImportedTransaction(obj)
            if (tx == null) {
                txSkipped += 1
                continue
            }
            val fp = fingerprintTx(tx)
            if (!existingTxFingerprints.add(fp)) {
                txSkipped += 1
                continue
            }
            insertTransaction(tx)
            txAdded += 1
            parsedCategories += tx.category
        }

        val existingRecurring = listRecurring()
        val existingRecurringIds = existingRecurring.map { it.id }.toMutableSet()
        val existingRecurringFingerprints = existingRecurring.map { fingerprintRecurring(it) }.toMutableSet()
        var recurringAdded = 0
        var recurringSkipped = 0

        for (i in 0 until recurringArray.length()) {
            val obj = recurringArray.optJSONObject(i) ?: continue
            val recurring = parseImportedRecurring(obj)
            if (recurring == null) {
                recurringSkipped += 1
                continue
            }
            val fp = fingerprintRecurring(recurring)
            if (existingRecurringIds.contains(recurring.id) || !existingRecurringFingerprints.add(fp)) {
                recurringSkipped += 1
                continue
            }
            insertRecurring(recurring)
            existingRecurringIds += recurring.id
            recurringAdded += 1
            parsedCategories += recurring.category
        }

        val categoriesAdded = ensureCategories(parsedCategories)
        var settingsUpdated = false
        if (settingsObj != null) {
            saveSettings(mapImportedSettings(loadSettings(), settingsObj))
            settingsUpdated = true
        }

        return ImportCompatResult(
            transactionsAdded = txAdded,
            transactionsSkipped = txSkipped,
            recurringAdded = recurringAdded,
            recurringSkipped = recurringSkipped,
            categoriesAdded = categoriesAdded,
            settingsUpdated = settingsUpdated,
        )
    }

    fun importCompatCsv(csvText: String): ImportCompatResult {
        val rows = parseCsvRows(csvText)
        if (rows.isEmpty()) {
            throw IllegalArgumentException("No CSV rows found.")
        }
        val existingTxIds = listTransactions().map { it.id }.toMutableSet()
        val existingTxFingerprints = listTransactions().map { fingerprintTx(it) }.toMutableSet()
        var txAdded = 0
        var txSkipped = 0
        val parsedCategories = mutableListOf<String>()

        rows.forEach { row ->
            val tx = parseImportedCsvTransaction(row) ?: run {
                txSkipped += 1
                return@forEach
            }
            val fingerprint = fingerprintTx(tx)
            if ((tx.id in existingTxIds) || !existingTxFingerprints.add(fingerprint)) {
                txSkipped += 1
                return@forEach
            }
            insertTransaction(tx)
            existingTxIds += tx.id
            parsedCategories += tx.category
            txAdded += 1
        }

        val categoriesAdded = ensureCategories(parsedCategories)
        return ImportCompatResult(
            transactionsAdded = txAdded,
            transactionsSkipped = txSkipped,
            recurringAdded = 0,
            recurringSkipped = 0,
            categoriesAdded = categoriesAdded,
            settingsUpdated = false,
        )
    }

    private fun mapImportedSettings(current: AppSettings, raw: JSONObject): AppSettings {
        return current.copy(
            startingBalance = raw.optDoubleOr(current.startingBalance, "starting_balance"),
            countedBalance = raw.optNullableDouble("counted_balance") ?: current.countedBalance,
            refundsTotal = raw.optDoubleOr(current.refundsTotal, "refunds_total", "refunds_received_total"),
            planMonthsTotal = raw.optIntOr(current.planMonthsTotal, "plan_months_total").coerceAtLeast(1),
            monthsElapsed = raw.optIntOr(current.monthsElapsed, "months_elapsed").coerceAtLeast(0),
            rentBaseMonthly = raw.optDoubleOr(current.rentBaseMonthly, "rent_base_monthly"),
            rentMonthlyManual = raw.optDoubleOr(current.rentMonthlyManual, "rent_monthly_manual"),
            foodMonthly = raw.optDoubleOr(current.foodMonthly, "food_house_monthly"),
            miscMonthly = raw.optDoubleOr(current.miscMonthly, "misc_monthly"),
            medicalMonthly = raw.optDoubleOr(current.medicalMonthly, "medical_monthly"),
            schoolMonthly = raw.optDoubleOr(current.schoolMonthly, "school_monthly"),
            householdMonthly = raw.optDoubleOr(current.householdMonthly, "household_monthly"),
            healthMonthly = raw.optDoubleOr(current.healthMonthly, "health_monthly"),
            autoMiscEnabled = raw.optBooleanOr(current.autoMiscEnabled, "auto_misc_enabled"),
            autoMiscCategories = raw.optStringArray("auto_misc_categories").ifEmpty { current.autoMiscCategories },
            autoIncludeRecurring = raw.optBooleanOr(current.autoIncludeRecurring, "auto_include_recurring"),
            includeCurrentMonthInAvg = raw.optBooleanOr(current.includeCurrentMonthInAvg, "auto_include_current_month"),
            avgWindowMonths = raw.optIntOr(current.avgWindowMonths, "auto_window_months").coerceAtLeast(1),
            autoWeighted = raw.optBooleanOr(current.autoWeighted, "auto_weighted"),
            autoWeightHalfLifeMonths = raw.optIntOr(current.autoWeightHalfLifeMonths, "auto_weight_half_life_months").coerceAtLeast(1),
            extraMonthly = raw.optDoubleOr(current.extraMonthly, "extra_monthly"),
            rentSurchargeAmount = raw.optDoubleOr(current.rentSurchargeAmount, "rent_surcharge_amount"),
            rentSurchargeMonths = raw.optIntOr(current.rentSurchargeMonths, "rent_surcharge_months").coerceAtLeast(0),
            campusReferenceTotal = raw.optDoubleOr(current.campusReferenceTotal, "campus_reference_total"),
            language = raw.optStringOr(current.language, "language").ifBlank { current.language },
            theme = raw.optStringOr(current.theme, "theme").ifBlank { current.theme },
            fontFamily = raw.optStringOr(current.fontFamily, "font_family"),
            accentColor = raw.optStringOr(current.accentColor, "accent_color"),
            schoolYearStartMonth = raw.optIntOr(current.schoolYearStartMonth, "school_year_start_month").coerceIn(1, 12),
        )
    }

    private fun parseImportedTransaction(obj: JSONObject): TransactionRecord? {
        val normalizedDateTime = normalizeImportedDateTime(obj.optString("datetime_local"))
            ?: normalizeImportedDateTime(obj.optString("datetime"))
            ?: normalizeImportedDateTime(obj.optString("date"))
            ?: return null
        return TransactionRecord(
            id = obj.optString("id").ifBlank { UUID.randomUUID().toString() },
            datetimeLocal = normalizedDateTime,
            amount = obj.optDouble("amount", 0.0),
            type = normalizeImportedType(obj.optString("type", "expense")),
            label = obj.optString("label", ""),
            category = normalizeCategory(obj.optString("category", "misc")),
            notes = obj.optString("notes", ""),
            recurringId = obj.optString("recurring_id").ifBlank { null },
            excludedFromAuto = obj.optBooleanOr(
                false,
                "excluded_from_averages",
                "exclude_from_averages",
                "avg_excluded",
                "excluded_from_auto",
            ),
        )
    }

    private fun parseImportedRecurring(obj: JSONObject): RecurringCharge? {
        val startDateRaw = obj.optString("start_date", LocalDate.now(APP_ZONE).toString())
        val startDate = parseLocalDateOrNull(startDateRaw)?.toString()
            ?: return null
        val endDate = parseLocalDateOrNull(obj.optString("end_date"))?.toString()
        return RecurringCharge(
            id = obj.optString("id").ifBlank { UUID.randomUUID().toString() },
            label = obj.optString("label", "Recurring"),
            amount = obj.optDouble("amount", 0.0),
            type = normalizeImportedType(obj.optString("type", "expense")),
            category = normalizeCategory(obj.optString("category", "misc")),
            notes = obj.optString("notes", ""),
            startDate = startDate,
            endDate = endDate,
            frequency = normalizeFrequency(obj.optString("frequency", "monthly")),
            status = normalizeRecurringStatus(obj.optString("status", "automatic")),
            lastAppliedDate = obj.optString("last_applied").ifBlank {
                obj.optString("last_applied_date").ifBlank { null }
            },
        )
    }

    private fun normalizeImportedDateTime(value: String?): String? {
        return normalizeImportedDateTimeValue(value)
    }

    private fun fingerprintTx(tx: TransactionRecord): String {
        return listOf(
            tx.datetimeLocal,
            "%.2f".format(tx.amount),
            tx.type.lowercase(),
            tx.label.trim().lowercase(),
            tx.category.trim().lowercase(),
            tx.notes.trim().lowercase(),
            tx.recurringId.orEmpty().trim().lowercase(),
            tx.excludedFromAuto.toString(),
        ).joinToString("|")
    }

    private fun fingerprintRecurring(r: RecurringCharge): RecurringFingerprint {
        return RecurringFingerprint(
            label = r.label.trim().lowercase(),
            amount = kotlin.math.round(r.amount * 100.0) / 100.0,
            type = r.type.trim().lowercase(),
            category = r.category.trim().lowercase(),
            notes = r.notes.trim().lowercase(),
            startDate = r.startDate,
            endDate = r.endDate ?: "",
            frequency = normalizeFrequency(r.frequency),
            status = normalizeRecurringStatus(r.status),
        )
    }
}

private fun TransactionRecord.toValues(): ContentValues = ContentValues().apply {
    put("id", id)
    put("datetime_local", datetimeLocal)
    put("amount", amount)
    put("type", normalizeType(type))
    put("label", label)
    put("category", normalizeCategory(category))
    put("notes", notes)
    put("recurring_id", recurringId)
    put("excluded_from_averages", if (excludedFromAuto) 1 else 0)
}

private fun RecurringCharge.toValues(): ContentValues = ContentValues().apply {
    put("id", id)
    put("label", label)
    put("amount", amount)
    put("type", normalizeType(type))
    put("category", normalizeCategory(category))
    put("notes", notes)
    put("start_date", startDate)
    put("end_date", endDate)
    put("frequency", normalizeFrequency(frequency))
    put("status", normalizeRecurringStatus(status))
    put("last_applied_date", lastAppliedDate)
}

private fun Cursor.toTransaction(): TransactionRecord = TransactionRecord(
    id = getString(getColumnIndexOrThrow("id")),
    datetimeLocal = getString(getColumnIndexOrThrow("datetime_local")),
    amount = getDoubleOrZero("amount"),
    type = getString(getColumnIndexOrThrow("type")),
    label = getStringOrEmpty("label"),
    category = getStringOrEmpty("category"),
    notes = getStringOrEmpty("notes"),
    recurringId = getNullableString("recurring_id"),
    excludedFromAuto = getIntOrZero("excluded_from_averages") == 1 || getIntOrZero("excluded_from_auto") == 1,
)

private fun Cursor.toRecurring(): RecurringCharge = RecurringCharge(
    id = getString(getColumnIndexOrThrow("id")),
    label = getStringOrEmpty("label"),
    amount = getDoubleOrZero("amount"),
    type = getString(getColumnIndexOrThrow("type")),
    category = getStringOrEmpty("category"),
    notes = getStringOrEmpty("notes"),
    startDate = parseLocalDateOrNull(getString(getColumnIndexOrThrow("start_date")))?.toString()
        ?: LocalDate.now(APP_ZONE).toString(),
    endDate = parseLocalDateOrNull(getNullableString("end_date"))?.toString(),
    frequency = normalizeFrequency(getString(getColumnIndexOrThrow("frequency"))),
    status = normalizeRecurringStatus(getString(getColumnIndexOrThrow("status"))),
    lastAppliedDate = getNullableString("last_applied_date"),
)

private fun Cursor.getDoubleOrZero(column: String): Double {
    val idx = getColumnIndex(column)
    if (idx < 0 || isNull(idx)) return 0.0
    return getDouble(idx)
}

private fun Cursor.getNullableDouble(column: String): Double? {
    val idx = getColumnIndex(column)
    if (idx < 0 || isNull(idx)) return null
    return getDouble(idx)
}

private fun Cursor.getIntOrZero(column: String): Int {
    val idx = getColumnIndex(column)
    if (idx < 0 || isNull(idx)) return 0
    return getInt(idx)
}

private fun Cursor.getStringOrEmpty(column: String): String {
    val idx = getColumnIndex(column)
    if (idx < 0 || isNull(idx)) return ""
    return getString(idx) ?: ""
}

private fun Cursor.getNullableString(column: String): String? {
    val idx = getColumnIndex(column)
    if (idx < 0 || isNull(idx)) return null
    return getString(idx)
}

private fun parseJsonStringList(value: String): List<String> {
    if (value.isBlank()) return emptyList()
    return try {
        val arr = JSONArray(value)
        buildList {
            for (i in 0 until arr.length()) {
                val item = arr.optString(i).trim()
                if (item.isNotBlank()) add(item)
            }
        }
    } catch (_: Exception) {
        emptyList()
    }
}

private fun normalizeCategoryName(value: String?): String? {
    val text = value?.trim().orEmpty()
    if (text.isBlank()) return null
    return text
}

private fun normalizeImportedDateTimeValue(value: String?): String? {
    val text = value?.trim().orEmpty()
    if (text.isBlank()) return null
    return try {
        LocalDateTime.parse(text).toString()
    } catch (_: Exception) {
        try {
            OffsetDateTime.parse(text)
                .atZoneSameInstant(APP_ZONE)
                .toLocalDateTime()
                .toString()
        } catch (_: Exception) {
            try {
                LocalDate.parse(text).atTime(12, 0).toString()
            } catch (_: Exception) {
                null
            }
        }
    }
}

private fun settingsToValues(s: AppSettings): ContentValues = ContentValues().apply {
    put("starting_balance", s.startingBalance)
    put("counted_balance", s.countedBalance)
    put("refunds_total", s.refundsTotal)
    put("plan_months_total", s.planMonthsTotal)
    put("months_elapsed", s.monthsElapsed)
    put("rent_base_monthly", s.rentBaseMonthly)
    put("rent_monthly_manual", s.rentMonthlyManual)
    put("campus_reference_total", s.campusReferenceTotal)
    put("food_house_monthly", s.foodMonthly)
    put("misc_monthly", s.miscMonthly)
    put("medical_monthly", s.medicalMonthly)
    put("school_monthly", s.schoolMonthly)
    put("household_monthly", s.householdMonthly)
    put("health_monthly", s.healthMonthly)
    put("auto_misc_enabled", if (s.autoMiscEnabled) 1 else 0)
    put("auto_misc_categories", JSONArray(s.autoMiscCategories).toString())
    put("auto_include_recurring", if (s.autoIncludeRecurring) 1 else 0)
    put("auto_include_current_month", if (s.includeCurrentMonthInAvg) 1 else 0)
    put("auto_window_months", s.avgWindowMonths)
    put("auto_weighted", if (s.autoWeighted) 1 else 0)
    put("auto_weight_half_life_months", s.autoWeightHalfLifeMonths)
    put("extra_monthly", s.extraMonthly)
    put("rent_surcharge_amount", s.rentSurchargeAmount)
    put("rent_surcharge_months", s.rentSurchargeMonths)
    put("language", normalizeLanguageCode(s.language))
    put("theme", s.theme)
    put("font_family", s.fontFamily)
    put("accent_color", s.accentColor)
    put("school_year_start_month", s.schoolYearStartMonth)
}

private fun insertDefaultCategories(db: SQLiteDatabase) {
    DEFAULT_CATEGORIES.forEach { category ->
        db.insertWithOnConflict(
            "categories",
            null,
            ContentValues().apply { put("name", category) },
            SQLiteDatabase.CONFLICT_IGNORE,
        )
    }
}

private fun normalizeType(value: String): String {
    return if (value.trim().lowercase() == "income") "income" else "expense"
}

private fun normalizeImportedType(value: String): String {
    val normalized = value.trim().lowercase()
    return IMPORT_TYPE_ALIASES[normalized] ?: "expense"
}

private fun normalizeFrequency(value: String): String {
    return when (value.trim().lowercase()) {
        "daily", "weekly", "monthly" -> value.trim().lowercase()
        else -> "monthly"
    }
}

private fun normalizeRecurringStatus(value: String): String {
    return when (value.trim().lowercase()) {
        "manual", "paused", "automatic" -> value.trim().lowercase()
        else -> "automatic"
    }
}

private fun JSONObject.optDoubleOr(default: Double, vararg keys: String): Double {
    keys.forEach { key ->
        if (has(key) && !isNull(key)) return optDouble(key, default)
    }
    return default
}

private fun JSONObject.optNullableDouble(key: String): Double? {
    if (!has(key) || isNull(key)) return null
    return optDouble(key)
}

private fun JSONObject.optIntOr(default: Int, vararg keys: String): Int {
    keys.forEach { key ->
        if (has(key) && !isNull(key)) return optInt(key, default)
    }
    return default
}

private fun JSONObject.optBooleanOr(default: Boolean, vararg keys: String): Boolean {
    keys.forEach { key ->
        if (has(key) && !isNull(key)) {
            return when (val value = opt(key)) {
                is Boolean -> value
                is Number -> value.toInt() != 0
                else -> value?.toString()?.trim()?.lowercase() in setOf("1", "true", "yes", "y", "on")
            }
        }
    }
    return default
}

private fun JSONObject.optStringOr(default: String, vararg keys: String): String {
    keys.forEach { key ->
        if (has(key) && !isNull(key)) return optString(key, default)
    }
    return default
}

private fun JSONObject.optStringArray(key: String): List<String> {
    val arr = optJSONArray(key) ?: return emptyList()
    return buildList {
        for (i in 0 until arr.length()) {
            val value = arr.optString(i).trim()
            if (value.isNotBlank()) add(value)
        }
    }
}

private fun looksLikeCsv(text: String): Boolean {
    val firstLine = text.lineSequence()
        .firstOrNull { it.isNotBlank() }
        ?.trim()
        ?.lowercase()
        ?: return false
    return firstLine.contains(",") && (
        firstLine.contains("date") ||
            firstLine.contains("datetime") ||
            firstLine.contains("amount") ||
            firstLine.contains("montant")
        )
}

private fun parseCsvRows(text: String): List<Map<String, String>> {
    val lines = text.lineSequence()
        .map { it.trimEnd('\r') }
        .filter { it.isNotBlank() }
        .toList()
    if (lines.isEmpty()) return emptyList()
    val rawHeaders = parseCsvLine(lines.first())
    if (rawHeaders.isEmpty()) return emptyList()
    val headers = rawHeaders.map { header ->
        val normalized = header.trim().lowercase()
        CSV_TRANSACTION_HEADER_MAP[normalized] ?: normalized
    }
    return lines.drop(1).mapNotNull { line ->
        val cells = parseCsvLine(line)
        if (cells.isEmpty()) return@mapNotNull null
        buildMap {
            headers.forEachIndexed { index, header ->
                if (header.isBlank()) return@forEachIndexed
                put(header, cells.getOrElse(index) { "" }.trim())
            }
        }
    }
}

private fun parseCsvLine(line: String): List<String> {
    if (line.isBlank()) return emptyList()
    val out = mutableListOf<String>()
    val current = StringBuilder()
    var inQuotes = false
    var index = 0
    while (index < line.length) {
        val ch = line[index]
        when {
            ch == '"' && inQuotes && index + 1 < line.length && line[index + 1] == '"' -> {
                current.append('"')
                index += 1
            }
            ch == '"' -> inQuotes = !inQuotes
            ch == ',' && !inQuotes -> {
                out += current.toString()
                current.clear()
            }
            else -> current.append(ch)
        }
        index += 1
    }
    out += current.toString()
    return out
}

private fun parseImportedCsvTransaction(row: Map<String, String>): TransactionRecord? {
    val normalizedDateTime = normalizeImportedDateTimeValue(
        row["datetime_local"] ?: row["datetime"] ?: row["date"]
    ) ?: return null
    val amount = row["amount"]?.toDoubleOrNull() ?: return null
    return TransactionRecord(
        id = row["id"].orEmpty().ifBlank { UUID.randomUUID().toString() },
        datetimeLocal = normalizedDateTime,
        amount = amount,
        type = normalizeImportedType(row["type"].orEmpty()),
        label = row["label"].orEmpty(),
        category = normalizeCategory(row["category"].orEmpty()),
        notes = row["notes"].orEmpty(),
        recurringId = row["recurring_id"].orEmpty().ifBlank { null },
        excludedFromAuto = row["excluded_from_averages"].orEmpty().trim().lowercase() in setOf("1", "true", "yes", "y", "on"),
    )
}
