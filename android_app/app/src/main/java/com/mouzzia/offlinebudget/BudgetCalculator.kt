package com.mouzzia.offlinebudget

import java.time.LocalDate
import java.time.temporal.ChronoUnit
import kotlin.math.max
import kotlin.math.pow

object BudgetCalculator {

    private data class AutoCategoryStats(
        val selected: List<String>,
        val totals: Map<String, Double>,
        val monthly: Map<String, Double>,
        val monthlyTotal: Double,
        val monthsCount: Int,
        val historyMonths: List<LocalDate>,
    )

    private data class CoreProjection(
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
        val schoolMonths: List<LocalDate>,
        val budgetPlanByMonth: Map<String, Double>,
        val budgetProjectedByMonth: Map<String, Double>,
        val totalExpenseByMonth: Map<String, Double>,
    )

    fun buildSnapshot(
        settings: AppSettings,
        transactions: List<TransactionRecord>,
        recurring: List<RecurringCharge>,
        today: LocalDate = nowLocal().toLocalDate(),
    ): DashboardSnapshot {
        val core = computeCore(settings, transactions, recurring, today)
        return DashboardSnapshot(
            estimatedBalance = core.estimatedBalance,
            totalExpenses = core.totalExpenses,
            totalIncome = core.totalIncome,
            monthBudgetPlan = core.monthBudgetPlan,
            monthBudgetProjected = core.monthBudgetProjected,
            monthSpent = core.monthSpent,
            monthIncome = core.monthIncome,
            monthRemainingPlan = core.monthRemainingPlan,
            monthRemainingProjected = core.monthRemainingProjected,
            rentMonthPaid = core.rentMonthPaid,
            rentMonthIncomeOffset = core.rentMonthIncomeOffset,
            schoolCoveragePlan = core.schoolCoveragePlan,
            schoolCoverageProjected = core.schoolCoverageProjected,
            savingsVsCampusPlan = core.savingsVsCampusPlan,
            savingsVsCampusProjected = core.savingsVsCampusProjected,
            projectedFinalExpensesPlan = core.projectedFinalExpensesPlan,
            projectedFinalExpensesAuto = core.projectedFinalExpensesAuto,
            avgMonthlyExpenses = core.avgMonthlyExpenses,
            monthsElapsedSchoolYear = core.monthsElapsedSchoolYear,
            monthsRemainingSchoolYear = core.monthsRemainingSchoolYear,
            debugLines = core.debugLines,
        )
    }

    fun monthlyTable(
        settings: AppSettings,
        transactions: List<TransactionRecord>,
        recurring: List<RecurringCharge>,
        today: LocalDate = nowLocal().toLocalDate(),
    ): List<MonthlyTotal> {
        val core = computeCore(settings, transactions, recurring, today)
        return core.schoolMonths.map { monthStart ->
            val key = monthKey(monthStart)
            val total = core.totalExpenseByMonth[key] ?: 0.0
            val plan = core.budgetPlanByMonth[key] ?: 0.0
            val projected = core.budgetProjectedByMonth[key] ?: 0.0
            MonthlyTotal(
                month = key,
                budgetPlan = plan,
                budgetProjected = projected,
                totalExpenses = total,
                deltaPlan = total - plan,
                deltaProjected = total - projected,
            )
        }
    }

    fun categoryAverageRows(transactions: List<TransactionRecord>): Pair<Int, List<CategoryAverageRow>> {
        val monthlyCategoryTotals = linkedMapOf<String, MutableMap<String, Double>>()
        val displayNames = linkedMapOf<String, String>()

        for (tx in transactions) {
            if (tx.excludedFromAuto) continue
            val parsedDate = parseTransactionMonth(tx) ?: continue
            val monthKey = monthKey(parsedDate)
            val monthMap = monthlyCategoryTotals.getOrPut(monthKey) { linkedMapOf() }

            when {
                tx.type.equals("expense", ignoreCase = true) -> {
                    val categoryKey = normalizeCategory(tx.category)
                    val displayName = displayCategory(tx.category.ifBlank { categoryKey }, "EN")
                    displayNames.putIfAbsent(categoryKey, displayName)
                    monthMap[categoryKey] = (monthMap[categoryKey] ?: 0.0) + tx.amount
                }
                isRentCreditTx(tx) -> {
                    val categoryKey = rentCategoryKey(tx)
                    displayNames.putIfAbsent(categoryKey, displayCategory(tx.category.ifBlank { "rent" }, "EN"))
                    monthMap[categoryKey] = (monthMap[categoryKey] ?: 0.0) - tx.amount
                }
            }
        }

        monthlyCategoryTotals.values.forEach { monthMap ->
            monthMap.replaceAll { _, amount -> amount.coerceAtLeast(0.0) }
        }

        val monthKeys = monthlyCategoryTotals.keys.sorted()
        val monthsCount = monthKeys.size
        if (monthsCount == 0) return 0 to emptyList()

        val totals = linkedMapOf<String, Double>()
        val monthsWithSpend = linkedMapOf<String, Int>()
        val latestMonth = monthKeys.last()

        monthKeys.forEach { monthKey ->
            monthlyCategoryTotals[monthKey].orEmpty().forEach { (categoryKey, amount) ->
                totals[categoryKey] = (totals[categoryKey] ?: 0.0) + amount
                if (amount > 0.0) {
                    monthsWithSpend[categoryKey] = (monthsWithSpend[categoryKey] ?: 0) + 1
                }
            }
        }

        val rows = totals.map { (categoryKey, total) ->
            CategoryAverageRow(
                category = displayNames[categoryKey] ?: displayCategory(categoryKey, "EN"),
                averageMonthly = total / monthsCount.toDouble(),
                total = total,
                monthsWithSpend = monthsWithSpend[categoryKey] ?: 0,
                latestMonth = monthlyCategoryTotals[latestMonth]?.get(categoryKey) ?: 0.0,
            )
        }.sortedWith(
            compareByDescending<CategoryAverageRow> { it.averageMonthly }
                .thenBy { it.category.lowercase() }
        )
        return monthsCount to rows
    }

    private fun computeCore(
        settings: AppSettings,
        transactions: List<TransactionRecord>,
        recurring: List<RecurringCharge>,
        today: LocalDate,
    ): CoreProjection {
        val (schoolStart, schoolEnd) = schoolYearBounds(today, settings.schoolYearStartMonth, settings.planMonthsTotal)
        val schoolMonths = monthsBetweenInclusive(schoolStart, schoolEnd)
        val schoolMonthKeys = schoolMonths.map(::monthKey)
        val currentMonthStart = today.withDayOfMonth(1)
        val currentMonthKey = monthKey(today)

        val expenses = transactions.filter { it.type.equals("expense", ignoreCase = true) }
        val incomes = transactions.filter { it.type.equals("income", ignoreCase = true) }
        val totalExpenses = expenses.sumOf { it.amount }
        val totalIncome = incomes.sumOf { it.amount } + settings.refundsTotal
        val estimatedBalance = settings.startingBalance - totalExpenses + totalIncome

        val expenseByMonth = mutableMapOf<String, Double>()
        for (tx in expenses) {
            val key = txMonthKey(tx) ?: continue
            expenseByMonth[key] = (expenseByMonth[key] ?: 0.0) + tx.amount
        }

        val schoolMonthsToDate = schoolMonths.filter { !it.isAfter(currentMonthStart) }
        val schoolMonthsToDateKeys = schoolMonthsToDate.map(::monthKey).toSet()
        val remainingSchoolMonths = schoolMonths.filter { !it.isBefore(currentMonthStart) }
        val monthsElapsed = schoolMonthsToDate.size.coerceIn(0, settings.planMonthsTotal)
        val monthsRemaining = remainingSchoolMonths.size

        val expensesToDatePlan = expenses.sumOf { tx ->
            val key = txMonthKey(tx)
            if (key != null && key in schoolMonthsToDateKeys) tx.amount else 0.0
        }

        val recurringExpenseCategories = recurring
            .filter { it.type.equals("expense", ignoreCase = true) }
            .map { normalizeCategory(it.category) }
            .toSet()

        val autoStats = autoCategoryStats(
            settings = settings,
            transactions = expenses,
            recurringExpenseCategories = recurringExpenseCategories,
            schoolMonths = schoolMonths,
            today = today,
        )

        val autoSelectedFood = autoStats.selected.any { isFoodText(it) }
        val autoSelectedMisc = autoStats.selected.any { isMiscText(it) }
        val autoSelectedMedical = autoStats.selected.any { isMedicalText(it) }
        val autoSelectedSchool = autoStats.selected.any { isSchoolText(it) }
        val autoSelectedHousehold = autoStats.selected.any { isHouseholdText(it) }
        val autoSelectedHealth = autoStats.selected.any { isHealthText(it) }

        val autoFoodHasData = autoStats.selected.any { isFoodText(it) && (autoStats.totals[it] ?: 0.0) > 0.0 }
        val autoMiscHasData = autoStats.selected.any { isMiscText(it) && (autoStats.totals[it] ?: 0.0) > 0.0 }
        val autoMedicalHasData = autoStats.selected.any { isMedicalText(it) && (autoStats.totals[it] ?: 0.0) > 0.0 }
        val autoSchoolHasData = autoStats.selected.any { isSchoolText(it) && (autoStats.totals[it] ?: 0.0) > 0.0 }
        val autoHouseholdHasData = autoStats.selected.any { isHouseholdText(it) && (autoStats.totals[it] ?: 0.0) > 0.0 }
        val autoHealthHasData = autoStats.selected.any { isHealthText(it) && (autoStats.totals[it] ?: 0.0) > 0.0 }

        val autoMode = settings.autoMiscEnabled
        val manualVariableMonthlyTotal = settings.foodMonthly + settings.miscMonthly +
            settings.medicalMonthly + settings.schoolMonthly + settings.householdMonthly + settings.healthMonthly
        val essentialManualMonthlyTotal = settings.foodMonthly +
            settings.medicalMonthly + settings.schoolMonthly + settings.householdMonthly + settings.healthMonthly

        val manualFallbackFood = if (!autoSelectedFood || (autoMode && !autoFoodHasData)) settings.foodMonthly else 0.0
        val manualFallbackMisc = if (!autoSelectedMisc || (autoMode && !autoMiscHasData)) settings.miscMonthly else 0.0
        val manualFallbackMedical = if (!autoSelectedMedical || (autoMode && !autoMedicalHasData)) settings.medicalMonthly else 0.0
        val manualFallbackSchool = if (!autoSelectedSchool || (autoMode && !autoSchoolHasData)) settings.schoolMonthly else 0.0
        val manualFallbackHousehold = if (!autoSelectedHousehold || (autoMode && !autoHouseholdHasData)) settings.householdMonthly else 0.0
        val manualFallbackHealth = if (!autoSelectedHealth || (autoMode && !autoHealthHasData)) settings.healthMonthly else 0.0

        val predictedVariableMonthlyRaw = autoStats.monthlyTotal +
            manualFallbackFood + manualFallbackMisc + manualFallbackMedical +
            manualFallbackSchool + manualFallbackHousehold + manualFallbackHealth
        val predictedVariableMonthly = if (autoMode && autoStats.monthsCount <= 0) {
            manualVariableMonthlyTotal
        } else {
            predictedVariableMonthlyRaw
        }

        val autoEssentialMonthly = autoStats.monthly
            .filterKeys { isEssentialText(it) }
            .values
            .sum()
        val predictedEssentialMonthlyRaw = autoEssentialMonthly +
            manualFallbackFood + manualFallbackMedical + manualFallbackSchool +
            manualFallbackHousehold + manualFallbackHealth
        val predictedEssentialMonthly = if (autoMode && autoStats.monthsCount <= 0) {
            essentialManualMonthlyTotal
        } else {
            predictedEssentialMonthlyRaw
        }

        val rentAutoMonthly = autoKeywordMonthlyAverage(
            settings = settings,
            transactions = transactions,
            schoolMonths = schoolMonths,
            today = today,
            matcher = { tx -> isRentTx(tx) },
            creditMatcher = { tx -> isRentCreditTx(tx) },
        )
        val rentManualMonthly = settings.rentMonthlyManual

        val recurringSchedule = recurringExpenseSchedule(recurring, schoolMonths)
        val rentSchedule = rentSchedule(recurring, schoolMonths)
        val recurringNonRentSchedule = schoolMonthKeys.associateWith { key ->
            max(0.0, (recurringSchedule[key] ?: 0.0) - (rentSchedule[key] ?: 0.0))
        }

        val budgetPlanByMonth = mutableMapOf<String, Double>()
        val budgetProjectedByMonth = mutableMapOf<String, Double>()
        for (key in schoolMonthKeys) {
            val recurringFull = recurringSchedule[key] ?: 0.0
            val recurringNonRent = recurringNonRentSchedule[key] ?: 0.0
            val rentPlan = if (rentManualMonthly > 0.0) rentManualMonthly else (rentSchedule[key] ?: 0.0)
            val rentProjected = if (rentAutoMonthly > 0.0) rentAutoMonthly else rentPlan
            val planBudget = if (rentManualMonthly > 0.0) {
                recurringNonRent + rentPlan + manualVariableMonthlyTotal
            } else {
                recurringFull + manualVariableMonthlyTotal
            }
            val projectedBudget = recurringNonRent + rentProjected + predictedVariableMonthly
            budgetPlanByMonth[key] = planBudget
            budgetProjectedByMonth[key] = projectedBudget
        }

        val monthSpent = expenseByMonth[currentMonthKey] ?: 0.0
        val monthIncome = incomes.sumOf { tx ->
            if (txMonthKey(tx) == currentMonthKey) tx.amount else 0.0
        }
        val monthBudgetPlan = budgetPlanByMonth[currentMonthKey] ?: 0.0
        val monthBudgetProjected = budgetProjectedByMonth[currentMonthKey] ?: 0.0
        val monthRemainingPlan = monthBudgetPlan - monthSpent
        val monthRemainingProjected = monthBudgetProjected - monthSpent
        val rentMonthPaidGross = expenses.sumOf { tx ->
            if (txMonthKey(tx) == currentMonthKey && isRentTx(tx)) tx.amount else 0.0
        }
        val rentMonthIncomeOffset = incomes.sumOf { tx ->
            if (txMonthKey(tx) == currentMonthKey && isRentCreditTx(tx)) tx.amount else 0.0
        }
        val rentMonthPaid = (rentMonthPaidGross - rentMonthIncomeOffset).coerceAtLeast(0.0)

        var plannedRemainingTotal = 0.0
        var projectedRemainingTotal = 0.0
        val coveragePlanBudgets = mutableListOf<Double>()
        val coverageProjectedBudgets = mutableListOf<Double>()
        val remainingKeys = remainingSchoolMonths.map(::monthKey).toSet()
        for (key in schoolMonthKeys) {
            if (key !in remainingKeys) continue
            val planBudget = budgetPlanByMonth[key] ?: 0.0
            val projectedBudget = budgetProjectedByMonth[key] ?: 0.0
            if (key == currentMonthKey) {
                val planRemaining = planBudget - monthSpent
                val projectedRemaining = projectedBudget - monthSpent
                plannedRemainingTotal += max(0.0, planRemaining)
                projectedRemainingTotal += max(0.0, projectedRemaining)
                coveragePlanBudgets += planRemaining
                coverageProjectedBudgets += projectedRemaining
            } else {
                plannedRemainingTotal += planBudget
                projectedRemainingTotal += projectedBudget
                coveragePlanBudgets += planBudget
                coverageProjectedBudgets += projectedBudget
            }
        }

        val projectedFinalExpensesPlan = expensesToDatePlan + plannedRemainingTotal
        val projectedFinalExpensesAuto = expensesToDatePlan + projectedRemainingTotal
        val savingsVsCampusPlan = settings.campusReferenceTotal - projectedFinalExpensesPlan
        val savingsVsCampusProjected = settings.campusReferenceTotal - projectedFinalExpensesAuto

        val schoolCoveragePlan = coverageMonths(estimatedBalance, coveragePlanBudgets)
        val schoolCoverageProjected = coverageMonths(estimatedBalance, coverageProjectedBudgets)

        val avgMonthlyExpenses = averageMonthlyExpenses(
            settings = settings,
            expenses = expenses,
            schoolMonths = schoolMonths,
            today = today,
        )

        val debug = buildList {
            add("School year start: $schoolStart")
            add("School year end: $schoolEnd")
            add("Months elapsed/remaining: $monthsElapsed/$monthsRemaining")
            add("Auto mode: ${if (autoMode) "ON" else "OFF"}")
            add("Auto categories selected: ${if (autoStats.selected.isEmpty()) "-" else autoStats.selected.joinToString(", ")}")
            add("Auto history months: ${autoStats.monthsCount}")
            add("Manual variable monthly: ${manualVariableMonthlyTotal.asMoney()}")
            add("Predicted variable monthly: ${predictedVariableMonthly.asMoney()}")
            add("Predicted essential monthly: ${predictedEssentialMonthly.asMoney()}")
            add("Current month plan budget: ${monthBudgetPlan.asMoney()}")
            add("Current month projected budget: ${monthBudgetProjected.asMoney()}")
            add("Current month spent: ${monthSpent.asMoney()}")
            add("Current month income: ${monthIncome.asMoney()}")
            add("Net rent this month: ${rentMonthPaid.asMoney()}")
            add("Current month remaining (plan): ${monthRemainingPlan.asMoney()}")
            add("Current month remaining (projected): ${monthRemainingProjected.asMoney()}")
            add("Expenses to date (school-year horizon): ${expensesToDatePlan.asMoney()}")
            add("Planned remaining total: ${plannedRemainingTotal.asMoney()}")
            add("Projected remaining total: ${projectedRemainingTotal.asMoney()}")
            add("Projected final expenses (plan): ${projectedFinalExpensesPlan.asMoney()}")
            add("Projected final expenses (auto): ${projectedFinalExpensesAuto.asMoney()}")
            add("Savings vs campus (plan): ${savingsVsCampusPlan.asMoney()}")
            add("Savings vs campus (auto): ${savingsVsCampusProjected.asMoney()}")
        }

        return CoreProjection(
            estimatedBalance = estimatedBalance,
            totalExpenses = totalExpenses,
            totalIncome = totalIncome,
            monthBudgetPlan = monthBudgetPlan,
            monthBudgetProjected = monthBudgetProjected,
            monthSpent = monthSpent,
            monthIncome = monthIncome,
            monthRemainingPlan = monthRemainingPlan,
            monthRemainingProjected = monthRemainingProjected,
            rentMonthPaid = rentMonthPaid,
            rentMonthIncomeOffset = rentMonthIncomeOffset,
            schoolCoveragePlan = schoolCoveragePlan,
            schoolCoverageProjected = schoolCoverageProjected,
            savingsVsCampusPlan = savingsVsCampusPlan,
            savingsVsCampusProjected = savingsVsCampusProjected,
            projectedFinalExpensesPlan = projectedFinalExpensesPlan,
            projectedFinalExpensesAuto = projectedFinalExpensesAuto,
            avgMonthlyExpenses = avgMonthlyExpenses,
            monthsElapsedSchoolYear = monthsElapsed,
            monthsRemainingSchoolYear = monthsRemaining,
            debugLines = debug,
            schoolMonths = schoolMonths,
            budgetPlanByMonth = budgetPlanByMonth,
            budgetProjectedByMonth = budgetProjectedByMonth,
            totalExpenseByMonth = expenseByMonth,
        )
    }

    private fun recurringExpenseSchedule(
        recurring: List<RecurringCharge>,
        months: List<LocalDate>,
    ): Map<String, Double> {
        val expenseRecurring = recurring.filter { it.type.equals("expense", ignoreCase = true) }
        val out = mutableMapOf<String, Double>()
        for (monthStart in months) {
            val monthEnd = monthStart.withDayOfMonth(monthStart.lengthOfMonth())
            var total = 0.0
            for (charge in expenseRecurring) {
                total += countOccurrencesInMonth(charge, monthStart, monthEnd) * charge.amount
            }
            out[monthKey(monthStart)] = total
        }
        return out
    }

    private fun rentSchedule(
        recurring: List<RecurringCharge>,
        months: List<LocalDate>,
    ): Map<String, Double> {
        val rentRecurring = recurring.filter {
            it.type.equals("expense", ignoreCase = true) && isRentText(it.category)
        }
        val out = mutableMapOf<String, Double>()
        for (monthStart in months) {
            val monthEnd = monthStart.withDayOfMonth(monthStart.lengthOfMonth())
            var total = 0.0
            for (charge in rentRecurring) {
                total += countOccurrencesInMonth(charge, monthStart, monthEnd) * charge.amount
            }
            out[monthKey(monthStart)] = total
        }
        return out
    }

    private fun countOccurrencesInMonth(
        recurring: RecurringCharge,
        monthStart: LocalDate,
        monthEnd: LocalDate,
    ): Int {
        if (recurring.status.equals("paused", ignoreCase = true)) return 0
        val startDate = parseLocalDate(recurring.startDate)
        val endDate = parseLocalDateOrNull(recurring.endDate)
        val effectiveStart = if (startDate.isAfter(monthStart)) startDate else monthStart
        val effectiveEnd = when {
            endDate == null -> monthEnd
            endDate.isBefore(monthEnd) -> endDate
            else -> monthEnd
        }
        if (effectiveStart.isAfter(effectiveEnd)) return 0

        return when (recurring.frequency.lowercase()) {
            "daily" -> ChronoUnit.DAYS.between(effectiveStart, effectiveEnd).toInt() + 1
            "weekly" -> {
                val deltaDays = ChronoUnit.DAYS.between(startDate, effectiveStart).toInt()
                val first = if (deltaDays <= 0) {
                    startDate
                } else {
                    val offset = deltaDays % 7
                    if (offset == 0) effectiveStart else effectiveStart.plusDays((7 - offset).toLong())
                }
                if (first.isAfter(effectiveEnd)) 0
                else 1 + (ChronoUnit.DAYS.between(first, effectiveEnd).toInt() / 7)
            }
            else -> {
                val scheduledDay = minOf(startDate.dayOfMonth, monthEnd.dayOfMonth)
                val scheduled = monthStart.withDayOfMonth(scheduledDay)
                if (scheduled.isBefore(effectiveStart) || scheduled.isAfter(effectiveEnd)) 0 else 1
            }
        }
    }

    private fun autoCategoryStats(
        settings: AppSettings,
        transactions: List<TransactionRecord>,
        recurringExpenseCategories: Set<String>,
        schoolMonths: List<LocalDate>,
        today: LocalDate,
    ): AutoCategoryStats {
        val selected = settings.autoMiscCategories
            .map { normalizeCategory(it) }
            .filter { it.isNotBlank() && it !in recurringExpenseCategories }
            .distinct()

        val historyMonths = selectHistoryMonths(settings, schoolMonths, today)
        val historyKeys = historyMonths.map(::monthKey).toSet()
        val totals = selected.associateWith { 0.0 }.toMutableMap()
        val monthCategory = historyMonths
            .associate { monthKey(it) to mutableMapOf<String, Double>() }
            .toMutableMap()

        for (tx in transactions) {
            if (!settings.autoIncludeRecurring && tx.recurringId != null) continue
            if (tx.excludedFromAuto) continue
            val txMonth = txMonthKey(tx) ?: continue
            if (txMonth !in historyKeys) continue
            val category = normalizeCategory(tx.category)
            if (category !in totals) continue
            totals[category] = (totals[category] ?: 0.0) + tx.amount
            val monthMap = monthCategory.getOrPut(txMonth) { mutableMapOf<String, Double>() }
            monthMap[category] = (monthMap[category] ?: 0.0) + tx.amount
        }

        val monthly = selected.associateWith { 0.0 }.toMutableMap()
        if (selected.isNotEmpty() && historyMonths.isNotEmpty()) {
            if (settings.autoWeighted) {
                var weightSum = 0.0
                val monthWeights = mutableMapOf<String, Double>()
                for (monthStart in historyMonths) {
                    val key = monthKey(monthStart)
                    val weight = monthWeight(
                        monthStart = monthStart,
                        today = today,
                        halfLifeMonths = settings.autoWeightHalfLifeMonths,
                    )
                    monthWeights[key] = weight
                    weightSum += weight
                }
                for (name in selected) {
                    var weightedTotal = 0.0
                    for (monthStart in historyMonths) {
                        val key = monthKey(monthStart)
                        val monthTotal = monthCategory[key]?.get(name) ?: 0.0
                        weightedTotal += monthTotal * (monthWeights[key] ?: 0.0)
                    }
                    monthly[name] = if (weightSum > 0.0) weightedTotal / weightSum else 0.0
                }
            } else {
                val monthCount = historyMonths.size.toDouble()
                for (name in selected) {
                    var total = 0.0
                    for (monthStart in historyMonths) {
                        val key = monthKey(monthStart)
                        total += monthCategory[key]?.get(name) ?: 0.0
                    }
                    monthly[name] = if (monthCount > 0.0) total / monthCount else 0.0
                }
            }
        }

        return AutoCategoryStats(
            selected = selected,
            totals = totals,
            monthly = monthly,
            monthlyTotal = monthly.values.sum(),
            monthsCount = historyMonths.size,
            historyMonths = historyMonths,
        )
    }

    private fun autoKeywordMonthlyAverage(
        settings: AppSettings,
        transactions: List<TransactionRecord>,
        schoolMonths: List<LocalDate>,
        today: LocalDate,
        matcher: (TransactionRecord) -> Boolean,
        creditMatcher: ((TransactionRecord) -> Boolean)? = null,
    ): Double {
        val historyMonths = selectHistoryMonths(settings, schoolMonths, today)
        if (historyMonths.isEmpty()) return 0.0
        val historyKeys = historyMonths.map(::monthKey).toSet()
        val monthTotals = historyKeys.associateWith { 0.0 }.toMutableMap()
        for (tx in transactions) {
            if (!settings.autoIncludeRecurring && tx.recurringId != null) continue
            if (tx.excludedFromAuto) continue
            val txMonth = txMonthKey(tx) ?: continue
            if (txMonth !in historyKeys) continue
            when {
                tx.type.equals("expense", ignoreCase = true) && matcher(tx) -> {
                    monthTotals[txMonth] = (monthTotals[txMonth] ?: 0.0) + tx.amount
                }
                creditMatcher != null && creditMatcher(tx) -> {
                    monthTotals[txMonth] = (monthTotals[txMonth] ?: 0.0) - tx.amount
                }
            }
        }
        monthTotals.replaceAll { _, value -> value.coerceAtLeast(0.0) }
        if (!settings.autoWeighted) {
            return monthTotals.values.sum() / historyMonths.size
        }
        var weightSum = 0.0
        var weightedTotal = 0.0
        for (monthStart in historyMonths) {
            val key = monthKey(monthStart)
            val weight = monthWeight(
                monthStart = monthStart,
                today = today,
                halfLifeMonths = settings.autoWeightHalfLifeMonths,
            )
            weightSum += weight
            weightedTotal += (monthTotals[key] ?: 0.0) * weight
        }
        return if (weightSum > 0.0) weightedTotal / weightSum else 0.0
    }

    private fun averageMonthlyExpenses(
        settings: AppSettings,
        expenses: List<TransactionRecord>,
        schoolMonths: List<LocalDate>,
        today: LocalDate,
    ): Double {
        val historyMonths = selectHistoryMonths(settings, schoolMonths, today)
        if (historyMonths.isEmpty()) return 0.0
        val historyKeys = historyMonths.map(::monthKey).toSet()
        val monthTotals = historyKeys.associateWith { 0.0 }.toMutableMap()
        for (tx in expenses) {
            if (!settings.autoIncludeRecurring && tx.recurringId != null) continue
            if (tx.excludedFromAuto) continue
            val key = txMonthKey(tx) ?: continue
            if (key !in historyKeys) continue
            monthTotals[key] = (monthTotals[key] ?: 0.0) + tx.amount
        }
        if (!settings.autoWeighted) {
            return monthTotals.values.sum() / historyMonths.size
        }
        var weightSum = 0.0
        var weightedTotal = 0.0
        for (monthStart in historyMonths) {
            val key = monthKey(monthStart)
            val weight = monthWeight(
                monthStart = monthStart,
                today = today,
                halfLifeMonths = settings.autoWeightHalfLifeMonths,
            )
            weightSum += weight
            weightedTotal += (monthTotals[key] ?: 0.0) * weight
        }
        return if (weightSum > 0.0) weightedTotal / weightSum else 0.0
    }

    private fun selectHistoryMonths(
        settings: AppSettings,
        schoolMonths: List<LocalDate>,
        today: LocalDate,
    ): List<LocalDate> {
        val currentMonthStart = today.withDayOfMonth(1)
        val eligible = schoolMonths.filter { monthStart ->
            if (settings.includeCurrentMonthInAvg) !monthStart.isAfter(currentMonthStart)
            else monthStart.isBefore(currentMonthStart)
        }
        if (eligible.isEmpty()) return emptyList()
        val win = settings.avgWindowMonths.coerceAtLeast(1)
        return eligible.takeLast(win)
    }

    private fun monthWeight(monthStart: LocalDate, today: LocalDate, halfLifeMonths: Int): Double {
        val halfLife = halfLifeMonths.coerceAtLeast(1)
        val age = max(monthOffset(monthStart, today.withDayOfMonth(1)), 0)
        return 0.5.pow(age.toDouble() / halfLife.toDouble())
    }

    private fun coverageMonths(balance: Double, budgets: List<Double>): Double {
        var covered = 0.0
        var remaining = balance
        for (budget in budgets) {
            when {
                budget < 0.0 -> {
                    remaining -= budget
                    covered += 1.0
                }
                budget == 0.0 -> {
                    covered += 1.0
                }
                remaining >= budget -> {
                    remaining -= budget
                    covered += 1.0
                }
                else -> {
                    covered += max(remaining, 0.0) / budget
                    return covered
                }
            }
        }
        return covered
    }

    private fun monthOffset(start: LocalDate, end: LocalDate): Int {
        return (end.year - start.year) * 12 + (end.monthValue - start.monthValue)
    }

    private fun txMonthKey(tx: TransactionRecord): String? {
        parseLocalDateTimeOrNull(tx.datetimeLocal)?.let { return monthKey(it.toLocalDate()) }
        return try {
            val d = LocalDate.parse(tx.datetimeLocal.take(10))
            monthKey(d)
        } catch (_: Exception) {
            null
        }
    }

    private fun containsKeywords(value: String, keywords: Set<String>): Boolean {
        val text = value.trim().lowercase()
        return keywords.any { text.contains(it) }
    }

    private fun isRentText(value: String): Boolean {
        val text = value.trim().lowercase()
        if (text.isBlank()) return false
        return Regex("\\b(rent|loyer)\\b").containsMatchIn(text)
    }
    private fun isFoodText(value: String): Boolean = containsKeywords(
        value,
        setOf("food", "grocery", "grocer", "restaurant", "meal", "cafe", "diner"),
    )
    private fun isMiscText(value: String): Boolean = containsKeywords(value, setOf("misc", "miscellaneous", "other", "extra"))
    private fun isMedicalText(value: String): Boolean = containsKeywords(value, setOf("medical", "med", "doctor", "clinic", "hospital", "pharmacy", "therapy", "dental", "dentist"))
    private fun isSchoolText(value: String): Boolean = containsKeywords(value, setOf("school", "tuition", "class", "course", "book", "textbook", "supplies", "campus", "lab"))
    private fun isHouseholdText(value: String): Boolean = containsKeywords(value, setOf("household", "home", "clean", "cleaning", "supplies", "furniture", "appliance"))
    private fun isHealthText(value: String): Boolean = containsKeywords(value, setOf("health", "gym", "fitness", "insurance", "wellness", "healthcare"))
    private fun isEssentialText(value: String): Boolean = isFoodText(value) || isMedicalText(value) || isSchoolText(value) || isHouseholdText(value) || isHealthText(value)
    private fun isRentTx(tx: TransactionRecord): Boolean = isRentText(tx.category) || isRentText(tx.label) || isRentText(tx.notes)
    private fun isRentCreditTx(tx: TransactionRecord): Boolean = tx.type.equals("income", ignoreCase = true) && isRentTx(tx)
    private fun rentCategoryKey(tx: TransactionRecord?): String {
        if (tx != null && isRentText(tx.category)) {
            return normalizeCategory(tx.category)
        }
        return "rent"
    }

    private fun parseTransactionMonth(tx: TransactionRecord): LocalDate? {
        parseLocalDateTimeOrNull(tx.datetimeLocal)?.let { return it.toLocalDate() }
        return try {
            LocalDate.parse(tx.datetimeLocal.take(10))
        } catch (_: Exception) {
            null
        }
    }
}

fun Double.asMoney(): String = String.format("$%,.2f", this)

fun Double.asSig2(): String {
    if (this == 0.0) return "0"
    return "%.2g".format(this)
}
