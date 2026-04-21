package com.mouzzia.offlinebudget

import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID

val APP_ZONE: ZoneId = ZoneId.systemDefault()
val TZ_NAME: String = APP_ZONE.id
private val ISO_DT: DateTimeFormatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME
private val ISO_DATE: DateTimeFormatter = DateTimeFormatter.ISO_LOCAL_DATE

val DEFAULT_CATEGORIES = listOf(
    "rent",
    "utilities",
    "food",
    "transport",
    "internet",
    "phone",
    "insurance",
    "medical",
    "school",
    "household",
    "health",
    "subscriptions",
    "entertainment",
    "travel",
    "clothing",
    "gifts",
    "pets",
    "debt",
    "fees",
    "income",
    "adjustment",
    "misc",
)

private val CATEGORY_TEXT = mapOf(
    "rent" to mapOf("EN" to "Rent", "FR" to "Loyer"),
    "utilities" to mapOf("EN" to "Utilities", "FR" to "Services"),
    "food" to mapOf("EN" to "Food", "FR" to "Nourriture"),
    "transport" to mapOf("EN" to "Transport", "FR" to "Transport"),
    "internet" to mapOf("EN" to "Internet", "FR" to "Internet"),
    "phone" to mapOf("EN" to "Phone", "FR" to "Telephone"),
    "insurance" to mapOf("EN" to "Insurance", "FR" to "Assurance"),
    "medical" to mapOf("EN" to "Medical", "FR" to "Medical"),
    "school" to mapOf("EN" to "School", "FR" to "Ecole"),
    "household" to mapOf("EN" to "Household", "FR" to "Maison"),
    "health" to mapOf("EN" to "Health", "FR" to "Sante"),
    "subscriptions" to mapOf("EN" to "Subscriptions", "FR" to "Abonnements"),
    "entertainment" to mapOf("EN" to "Entertainment", "FR" to "Loisirs"),
    "travel" to mapOf("EN" to "Travel", "FR" to "Voyage"),
    "clothing" to mapOf("EN" to "Clothing", "FR" to "Vetements"),
    "gifts" to mapOf("EN" to "Gifts", "FR" to "Cadeaux"),
    "pets" to mapOf("EN" to "Pets", "FR" to "Animaux"),
    "debt" to mapOf("EN" to "Debt", "FR" to "Dettes"),
    "fees" to mapOf("EN" to "Fees", "FR" to "Frais"),
    "income" to mapOf("EN" to "Income", "FR" to "Revenu"),
    "adjustment" to mapOf("EN" to "Adjustment", "FR" to "Ajustement"),
    "misc" to mapOf("EN" to "Misc", "FR" to "Divers"),
)

private val CATEGORY_LOOKUP = buildMap<String, String> {
    CATEGORY_TEXT.forEach { (canonical, labels) ->
        put(canonical.lowercase(), canonical)
        labels.values.forEach { label ->
            put(label.trim().lowercase(), canonical)
        }
    }
}

data class TransactionRecord(
    val id: String = UUID.randomUUID().toString(),
    val datetimeLocal: String,
    val amount: Double,
    val type: String,
    val label: String = "",
    val category: String = "misc",
    val notes: String = "",
    val recurringId: String? = null,
    val excludedFromAuto: Boolean = false,
)

data class RecurringCharge(
    val id: String = UUID.randomUUID().toString(),
    val label: String,
    val amount: Double,
    val type: String,
    val category: String,
    val notes: String,
    val startDate: String,
    val endDate: String? = null,
    val frequency: String = "monthly",
    val status: String = "automatic",
    val lastAppliedDate: String? = null,
)

data class AppSettings(
    val startingBalance: Double = 0.0,
    val countedBalance: Double? = null,
    val refundsTotal: Double = 0.0,
    val planMonthsTotal: Int = 9,
    val monthsElapsed: Int = 0,
    val rentBaseMonthly: Double = 650.0,
    val rentMonthlyManual: Double = 0.0,
    val campusReferenceTotal: Double = 17256.0,
    val foodMonthly: Double = 200.0,
    val miscMonthly: Double = 50.0,
    val medicalMonthly: Double = 0.0,
    val schoolMonthly: Double = 0.0,
    val householdMonthly: Double = 0.0,
    val healthMonthly: Double = 0.0,
    val autoMiscEnabled: Boolean = false,
    val autoMiscCategories: List<String> = emptyList(),
    val autoIncludeRecurring: Boolean = false,
    val schoolYearStartMonth: Int = 9,
    val avgWindowMonths: Int = 3,
    val autoWeighted: Boolean = false,
    val autoWeightHalfLifeMonths: Int = 6,
    val includeCurrentMonthInAvg: Boolean = false,
    val extraMonthly: Double = 0.0,
    val rentSurchargeAmount: Double = 144.0,
    val rentSurchargeMonths: Int = 3,
    val language: String = "EN",
    val theme: String = "Dune",
    val fontFamily: String = "",
    val accentColor: String = "",
)

data class MonthlyTotal(
    val month: String,
    val budgetPlan: Double,
    val budgetProjected: Double,
    val totalExpenses: Double,
    val deltaPlan: Double,
    val deltaProjected: Double,
)

data class CategoryAverageRow(
    val category: String,
    val averageMonthly: Double,
    val total: Double,
    val monthsWithSpend: Int,
    val latestMonth: Double,
)

data class DashboardSnapshot(
    val estimatedBalance: Double,
    val totalExpenses: Double,
    val totalIncome: Double,
    val monthBudgetPlan: Double,
    val monthBudgetProjected: Double,
    val monthSpent: Double,
    val monthIncome: Double,
    val monthRemainingPlan: Double,
    val monthRemainingProjected: Double,
    val rentMonthPaid: Double,
    val rentMonthIncomeOffset: Double,
    val schoolCoveragePlan: Double,
    val schoolCoverageProjected: Double,
    val savingsVsCampusPlan: Double,
    val savingsVsCampusProjected: Double,
    val projectedFinalExpensesPlan: Double,
    val projectedFinalExpensesAuto: Double,
    val avgMonthlyExpenses: Double,
    val monthsElapsedSchoolYear: Int,
    val monthsRemainingSchoolYear: Int,
    val debugLines: List<String>,
)

fun nowLocal(): LocalDateTime = LocalDateTime.now(APP_ZONE)

fun nowLocalIso(): String = nowLocal().format(ISO_DT)

fun nowIndiana(): LocalDateTime = nowLocal()

fun nowIndianaIso(): String = nowLocalIso()

fun parseLocalDate(value: String): LocalDate = try {
    LocalDate.parse(value, ISO_DATE)
} catch (_: Exception) {
    nowLocal().toLocalDate()
}

fun parseLocalDateOrNull(value: String?): LocalDate? {
    val text = value?.trim().orEmpty()
    if (text.isBlank()) return null
    if (text.equals("null", ignoreCase = true) || text.equals("none", ignoreCase = true)) {
        return null
    }
    return try {
        LocalDate.parse(text, ISO_DATE)
    } catch (_: Exception) {
        try {
            LocalDateTime.parse(text, ISO_DT).toLocalDate()
        } catch (_: Exception) {
            null
        }
    }
}

fun parseLocalDateTimeOrNull(value: String): LocalDateTime? = try {
    LocalDateTime.parse(value, ISO_DT)
} catch (_: Exception) {
    null
}

fun parseLocalDateTime(value: String): LocalDateTime = parseLocalDateTimeOrNull(value) ?: nowLocal()

fun schoolYearBounds(today: LocalDate, startMonth: Int, months: Int = 9): Pair<LocalDate, LocalDate> {
    val startYear = if (today.monthValue >= startMonth) today.year else today.year - 1
    val start = LocalDate.of(startYear, startMonth, 1)
    val end = start.plusMonths(months.toLong().coerceAtLeast(1)).minusDays(1)
    return start to end
}

fun monthsBetweenInclusive(start: LocalDate, end: LocalDate): List<LocalDate> {
    if (end.isBefore(start)) return emptyList()
    val out = mutableListOf<LocalDate>()
    var cur = start.withDayOfMonth(1)
    val last = end.withDayOfMonth(1)
    while (!cur.isAfter(last)) {
        out += cur
        cur = cur.plusMonths(1)
    }
    return out
}

fun dueDatesBetween(
    recurring: RecurringCharge,
    fromExclusive: LocalDate?,
    toInclusive: LocalDate,
): List<LocalDate> {
    val start = parseLocalDate(recurring.startDate)
    val hardStart = fromExclusive?.let {
        nextFrequencyDate(it, recurring.frequency)
    } ?: start

    val endBound = parseLocalDateOrNull(recurring.endDate) ?: toInclusive
    val finalEnd = if (endBound.isBefore(toInclusive)) endBound else toInclusive
    if (hardStart.isAfter(finalEnd)) return emptyList()

    val dates = mutableListOf<LocalDate>()
    var cur = hardStart
    while (!cur.isAfter(finalEnd)) {
        if (!cur.isBefore(start)) {
            dates += cur
        }
        cur = nextFrequencyDate(cur, recurring.frequency)
    }
    return dates
}

fun nextFrequencyDate(date: LocalDate, frequency: String): LocalDate = when (frequency.lowercase()) {
    "daily" -> date.plusDays(1)
    "weekly" -> date.plusWeeks(1)
    else -> date.plusMonths(1)
}

fun normalizeCategory(value: String): String {
    val normalized = value.trim().lowercase()
    if (normalized.isBlank()) return "misc"
    return CATEGORY_LOOKUP[normalized] ?: normalized
}

fun monthKey(date: LocalDate): String = "${date.year}-${"%02d".format(date.monthValue)}"

fun monthKeyFromIsoDateTime(dt: String): String = monthKey(parseLocalDateTime(dt).toLocalDate())

fun isWeekend(date: LocalDate): Boolean = date.dayOfWeek == DayOfWeek.SATURDAY || date.dayOfWeek == DayOfWeek.SUNDAY

fun normalizeLanguageCode(value: String): String {
    return if (value.trim().equals("FR", ignoreCase = true)) "FR" else "EN"
}

fun translatedCategory(value: String, language: String = "EN"): String {
    val raw = value.trim()
    if (raw.isBlank()) return ""
    val canonical = normalizeCategory(raw)
    val labels = CATEGORY_TEXT[canonical] ?: return raw
    val normalizedLanguage = normalizeLanguageCode(language)
    return labels[normalizedLanguage] ?: labels["EN"] ?: raw
}

fun displayCategory(value: String, language: String = "EN"): String {
    val raw = value.trim()
    if (raw.isBlank()) return if (language.trim().equals("FR", ignoreCase = true)) "Sans categorie" else "Uncategorized"
    val translated = translatedCategory(raw, language)
    return if (translated == raw) raw.replaceFirstChar { it.titlecase() } else translated
}

fun displayTransactionType(value: String, language: String = "EN"): String {
    val normalized = value.trim().lowercase()
    val isFrench = language.trim().equals("FR", ignoreCase = true)
    return if (normalized == "income") {
        if (isFrench) "Revenu" else "Income"
    } else {
        if (isFrench) "Depense" else "Expense"
    }
}

fun displayRecurringFrequency(value: String, language: String = "EN"): String {
    val normalized = value.trim().lowercase()
    val isFrench = language.trim().equals("FR", ignoreCase = true)
    return when (normalized) {
        "daily" -> if (isFrench) "Quotidien" else "Daily"
        "weekly" -> if (isFrench) "Hebdomadaire" else "Weekly"
        else -> if (isFrench) "Mensuel" else "Monthly"
    }
}

fun displayRecurringStatus(value: String, language: String = "EN"): String {
    val normalized = value.trim().lowercase()
    val isFrench = language.trim().equals("FR", ignoreCase = true)
    return when (normalized) {
        "manual" -> if (isFrench) "Manuel" else "Manual"
        "paused" -> if (isFrench) "En pause" else "Paused"
        else -> if (isFrench) "Automatique" else "Automatic"
    }
}
