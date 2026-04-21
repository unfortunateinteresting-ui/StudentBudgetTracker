package com.mouzzia.offlinebudget

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.CreationExtras
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class AppState(
    val settings: AppSettings = AppSettings(),
    val transactions: List<TransactionRecord> = emptyList(),
    val recurring: List<RecurringCharge> = emptyList(),
    val categories: List<String> = emptyList(),
    val categoryAverages: List<CategoryAverageRow> = emptyList(),
    val categoryAverageMonthsCount: Int = 0,
    val dashboard: DashboardSnapshot = DashboardSnapshot(
        estimatedBalance = 0.0,
        totalExpenses = 0.0,
        totalIncome = 0.0,
        monthBudgetPlan = 0.0,
        monthBudgetProjected = 0.0,
        monthSpent = 0.0,
        monthIncome = 0.0,
        monthRemainingPlan = 0.0,
        monthRemainingProjected = 0.0,
        rentMonthPaid = 0.0,
        rentMonthIncomeOffset = 0.0,
        schoolCoveragePlan = 0.0,
        schoolCoverageProjected = 0.0,
        savingsVsCampusPlan = 0.0,
        savingsVsCampusProjected = 0.0,
        projectedFinalExpensesPlan = 0.0,
        projectedFinalExpensesAuto = 0.0,
        avgMonthlyExpenses = 0.0,
        monthsElapsedSchoolYear = 0,
        monthsRemainingSchoolYear = 0,
        debugLines = emptyList(),
    ),
    val monthlyTotals: List<MonthlyTotal> = emptyList(),
    val startupAppliedRecurring: List<String> = emptyList(),
)

class BudgetViewModel(application: Application) : AndroidViewModel(application) {
    private val store = BudgetStore(BudgetDbHelper(application))
    private val vmScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val _state = MutableStateFlow(AppState())
    val state: StateFlow<AppState> = _state.asStateFlow()

    init {
        vmScope.launch {
            val applied = store.applyDueRecurring()
            refresh(applied)
        }
    }

    fun refresh(applied: List<String> = emptyList()) {
        vmScope.launch {
            val settings = store.loadSettings()
            val recurring = store.listRecurring()
            val transactions = store.listTransactions()
            val dashboard = BudgetCalculator.buildSnapshot(settings, transactions, recurring)
            val monthly = BudgetCalculator.monthlyTable(settings, transactions, recurring)
            val (categoryAverageMonthsCount, categoryAverages) = BudgetCalculator.categoryAverageRows(transactions)
            _state.value = AppState(
                settings = settings,
                transactions = transactions,
                recurring = recurring,
                categories = store.listCategories(),
                categoryAverages = categoryAverages,
                categoryAverageMonthsCount = categoryAverageMonthsCount,
                dashboard = dashboard,
                monthlyTotals = monthly,
                startupAppliedRecurring = applied,
            )
        }
    }

    fun addTransaction(amount: Double, label: String, category: String, type: String, notes: String) {
        vmScope.launch {
            val tx = TransactionRecord(
                datetimeLocal = nowLocalIso(),
                amount = amount,
                label = label,
                category = normalizeCategory(category),
                type = type,
                notes = notes,
            )
            store.insertTransaction(tx)
            refresh()
        }
    }

    fun deleteTransaction(id: String) {
        vmScope.launch {
            store.deleteTransaction(id)
            refresh()
        }
    }

    fun updateTransaction(tx: TransactionRecord) {
        vmScope.launch {
            store.updateTransaction(tx)
            refresh()
        }
    }

    fun setTransactionExcluded(id: String, excluded: Boolean) {
        vmScope.launch {
            store.updateTransactionExclusion(id, excluded)
            refresh()
        }
    }

    fun addRecurring(charge: RecurringCharge) {
        vmScope.launch {
            store.insertRecurring(charge)
            refresh()
        }
    }

    fun updateRecurring(charge: RecurringCharge) {
        vmScope.launch {
            store.updateRecurring(charge)
            refresh()
        }
    }

    fun deleteRecurring(id: String) {
        vmScope.launch {
            store.deleteRecurring(id)
            refresh()
        }
    }

    fun applyDueRecurringNow() {
        vmScope.launch {
            val applied = store.applyDueRecurring()
            refresh(applied)
        }
    }

    fun saveSettings(settings: AppSettings) {
        vmScope.launch {
            store.saveSettings(settings)
            refresh()
        }
    }

    fun exportCompatJson(): String {
        val snapshot = _state.value
        return store.exportCompatJson(snapshot.settings, snapshot.transactions, snapshot.recurring)
    }

    fun importCompatJson(
        displayName: String?,
        jsonText: String,
        onDone: (Result<ImportCompatResult>) -> Unit,
    ) {
        vmScope.launch {
            try {
                val result = store.importCompatData(displayName, jsonText)
                refresh()
                withContext(Dispatchers.Main) {
                    onDone(Result.success(result))
                }
            } catch (exc: Exception) {
                withContext(Dispatchers.Main) {
                    onDone(Result.failure(exc))
                }
            }
        }
    }

    fun resetAllData(onDone: (Result<Unit>) -> Unit) {
        vmScope.launch {
            try {
                store.resetAllData()
                refresh()
                withContext(Dispatchers.Main) {
                    onDone(Result.success(Unit))
                }
            } catch (exc: Exception) {
                withContext(Dispatchers.Main) {
                    onDone(Result.failure(exc))
                }
            }
        }
    }

    companion object {
        val Factory: ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            override fun <T : androidx.lifecycle.ViewModel> create(
                modelClass: Class<T>,
                extras: CreationExtras
            ): T {
                val app = checkNotNull(extras[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY])
                return BudgetViewModel(app) as T
            }
        }
    }
}
