package com.mouzzia.offlinebudget

import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.util.UUID

data class TopTab(
    val route: String,
    val label: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                val vm: BudgetViewModel = viewModel(factory = BudgetViewModel.Factory)
                BudgetApp(vm)
            }
        }
    }
}

@Composable
private fun BudgetApp(vm: BudgetViewModel) {
    val state by vm.state.collectAsState()
    val snackState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    val language = normalizeLanguageCode(state.settings.language)
    var currentTabIndex by rememberSaveable { mutableStateOf(0) }
    var startupDialogShown by rememberSaveable { mutableStateOf(false) }
    var pendingExportText by remember { mutableStateOf<String?>(null) }
    var pendingExportSuccessLabel by remember { mutableStateOf("") }
    var showResetDataDialog by rememberSaveable { mutableStateOf(false) }

    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        val exportText = pendingExportText ?: return@rememberLauncherForActivityResult
        runCatching {
            context.contentResolver.openOutputStream(uri)?.use { stream ->
                stream.write(exportText.toByteArray())
                stream.flush()
            } ?: error("Unable to open file")
        }.onSuccess {
            scope.launch {
                snackState.showSnackbar(
                    pendingExportSuccessLabel.ifBlank {
                        tr(language, "Data exported", "Donnees exportees")
                    }
                )
            }
        }.onFailure { exc ->
            scope.launch {
                snackState.showSnackbar(
                    tr(language, "Export failed", "Echec export") + ": ${exc.message}"
                )
            }
        }
    }

    val importLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        runCatching {
            context.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() }
                ?: error("Unable to read file")
        }.onSuccess { text ->
            val displayName = context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                ?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        cursor.getString(cursor.getColumnIndexOrThrow(OpenableColumns.DISPLAY_NAME))
                    } else {
                        null
                    }
                } ?: uri.lastPathSegment
            vm.importCompatJson(displayName, text) { result ->
                result.onSuccess { importResult ->
                    scope.launch {
                        snackState.showSnackbar(
                            tr(language, "Imported transactions", "Transactions importees") +
                                " ${importResult.transactionsAdded}/${importResult.transactionsSkipped}, " +
                                tr(language, "recurring", "recurrents") +
                                " ${importResult.recurringAdded}/${importResult.recurringSkipped}, " +
                                tr(language, "categories", "categories") +
                                " +${importResult.categoriesAdded}"
                        )
                    }
                }.onFailure { exc ->
                    scope.launch {
                        snackState.showSnackbar(
                            tr(language, "Import failed", "Echec import") + ": ${exc.message}"
                        )
                    }
                }
            }
        }.onFailure { exc ->
            scope.launch {
                snackState.showSnackbar(
                    tr(language, "Import failed", "Echec import") + ": ${exc.message}"
                )
            }
        }
    }

    val tabs = listOf(
        TopTab("dashboard", tr(language, "Dashboard", "Tableau"), Icons.Default.Dashboard),
        TopTab("graphs", tr(language, "Graphs", "Graphiques"), Icons.Default.ShowChart),
        TopTab("add", tr(language, "Add", "Ajouter"), Icons.Default.Add),
        TopTab("transactions", tr(language, "Transactions", "Transactions"), Icons.Default.List),
        TopTab("recurring", tr(language, "Recurring", "Recurrents"), Icons.Default.Refresh),
        TopTab("settings", tr(language, "Settings", "Parametres"), Icons.Default.Settings),
    )
    val pagerState = rememberPagerState(initialPage = currentTabIndex, pageCount = { tabs.size })

    LaunchedEffect(currentTabIndex) {
        if (pagerState.currentPage != currentTabIndex) {
            pagerState.animateScrollToPage(currentTabIndex)
        }
    }
    LaunchedEffect(pagerState.currentPage) {
        if (currentTabIndex != pagerState.currentPage) {
            currentTabIndex = pagerState.currentPage
        }
    }

    LaunchedEffect(state.startupAppliedRecurring) {
        if (!startupDialogShown && state.startupAppliedRecurring.isNotEmpty()) {
            startupDialogShown = true
        }
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { index, tab ->
                    NavigationBarItem(
                        selected = currentTabIndex == index,
                        onClick = { currentTabIndex = index },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) }
                    )
                }
            }
        },
        snackbarHost = { SnackbarHost(snackState) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize(),
            ) { page ->
                Box(modifier = Modifier.fillMaxSize().padding(12.dp)) {
                    when (tabs[page].route) {
                        "dashboard" -> DashboardScreen(state, language)
                        "graphs" -> GraphsScreen(state, language)
                        "add" -> AddEntryScreen(
                            language = language,
                            onAdd = { amount, label, category, type, notes ->
                                vm.addTransaction(amount, label, category, type, notes)
                                scope.launch {
                                    snackState.showSnackbar(tr(language, "Entry saved", "Entree enregistree"))
                                }
                            }
                        )
                        "transactions" -> TransactionsScreen(
                            language = language,
                            transactions = state.transactions,
                            onDelete = { vm.deleteTransaction(it) },
                            onUpdate = { vm.updateTransaction(it) },
                            onToggleExcluded = { id, excluded -> vm.setTransactionExcluded(id, excluded) }
                        )
                        "recurring" -> RecurringScreen(
                            language = language,
                            recurring = state.recurring,
                            onAddRecurring = { vm.addRecurring(it) },
                            onUpdateRecurring = { vm.updateRecurring(it) },
                            onDeleteRecurring = { vm.deleteRecurring(it) },
                            onApplyNow = { vm.applyDueRecurringNow() }
                        )
                        "settings" -> SettingsScreen(
                            language = language,
                            settings = state.settings,
                            onSave = { vm.saveSettings(it) },
                            onExport = {
                                pendingExportText = vm.exportCompatJson()
                                pendingExportSuccessLabel = tr(language, "JSON exported", "JSON exporte")
                                val filename = "budget_history_export.json"
                                exportLauncher.launch(filename)
                            },
                            onImport = {
                                importLauncher.launch(arrayOf("application/json", "text/json", "text/csv", "text/comma-separated-values", "*/*"))
                            },
                            onResetData = { showResetDataDialog = true },
                        )
                    }
                }
            }
        }
    }

    if (startupDialogShown && state.startupAppliedRecurring.isNotEmpty()) {
        AlertDialog(
            onDismissRequest = { startupDialogShown = false },
            confirmButton = {
                TextButton(onClick = { startupDialogShown = false }) {
                    Text(tr(language, "OK", "OK"))
                }
            },
            title = { Text(tr(language, "Recurring catch-up applied", "Rattrapage recurrent applique")) },
            text = {
                Column {
                    Text(
                        tr(
                            language,
                            "While the app was off, these recurring entries were added:",
                            "Pendant l'arret de l'application, ces entrees recurrentes ont ete ajoutees:"
                        )
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    state.startupAppliedRecurring.forEach { line ->
                        Text("- $line")
                    }
                }
            }
        )
    }

    if (showResetDataDialog) {
        AlertDialog(
            onDismissRequest = { showResetDataDialog = false },
            title = { Text(tr(language, "Reset current data?", "Reinitialiser les donnees actuelles ?")) },
            text = {
                Text(
                    tr(
                        language,
                        "This clears transactions, recurring entries, categories, and budget settings on this phone. Your language stays the same. Continue?",
                        "Cela efface les transactions, les recurrentes, les categories, et les reglages budgetaires sur ce telephone. Votre langue reste la meme. Continuer ?"
                    )
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    showResetDataDialog = false
                    vm.resetAllData { result ->
                        result.onSuccess {
                            scope.launch {
                                snackState.showSnackbar(
                                    tr(language, "Current app data was reset.", "Les donnees actuelles ont ete reinitialisees.")
                                )
                            }
                        }.onFailure { exc ->
                            scope.launch {
                                snackState.showSnackbar(
                                    tr(language, "Reset failed", "Echec de reinitialisation") + ": ${exc.message}"
                                )
                            }
                        }
                    }
                }) {
                    Text(tr(language, "Reset data", "Reinitialiser les donnees"))
                }
            },
            dismissButton = {
                TextButton(onClick = { showResetDataDialog = false }) {
                    Text(tr(language, "Cancel", "Annuler"))
                }
            }
        )
    }
}

@Composable
private fun DashboardScreen(state: AppState, language: String) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text(
                tr(language, "Dashboard", "Tableau de bord"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        }
        item {
            Text(
                tr(
                    language,
                    "Start with Current balance, Left this month, and Net rent this month. The sections below explain the rest.",
                    "Commencez par le solde actuel, le reste du mois, et le loyer net du mois. Les sections ci-dessous expliquent le reste."
                ),
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF556070)
            )
        }
        item {
            SummaryGrid(state.dashboard, language)
        }
        item {
            CategoryAveragesCard(
                language = language,
                rows = state.categoryAverages,
                monthsCount = state.categoryAverageMonthsCount,
            )
        }
        item {
            Text(
                tr(language, "Monthly totals", "Totaux mensuels"),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(8.dp))
            MonthlyTotalsTable(state.monthlyTotals, language)
        }
        item {
            Text(
                tr(language, "How calculations are built", "Construction des calculs"),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Card {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    state.dashboard.debugLines.forEach { line ->
                        Text(line)
                    }
                }
            }
        }
    }
}

private data class LineSeries(
    val label: String,
    val values: List<Double>,
    val color: Color,
)

@Composable
private fun GraphsScreen(state: AppState, language: String) {
    val rows = state.monthlyTotals
    val monthKeys = rows.map { it.month }
    val monthLabels = monthKeys.map(::formatMonthLabel)
    val monthlyExpenses = rows.map { it.totalExpenses.coerceAtLeast(0.0) }
    val currentMonthKey = monthKey(LocalDate.now())
    val completedRows = rows.filter { it.month <= currentMonthKey }
    val monthlyAverage = completedRows.map { it.totalExpenses.coerceAtLeast(0.0) }.takeIf { it.isNotEmpty() }?.average()
    val cumulativeExpenses = runningTotals(rows.map { it.totalExpenses })
    val cumulativePlan = runningTotals(rows.map { it.budgetPlan })
    val cumulativeProjected = runningTotals(rows.map { it.budgetProjected })
    val categoryAverageRows = state.categoryAverages.take(8)
    val categoryAverageValues = categoryAverageRows.map { it.averageMonthly }
    val categoryAverageLabels = categoryAverageRows.map { displayCategory(it.category, language) }

    val sortedTransactions = remember(state.transactions) {
        state.transactions.sortedBy { it.datetimeLocal }
    }
    val runningBalance = remember(sortedTransactions, state.settings.startingBalance, language) {
        val labels = mutableListOf<String>()
        val values = mutableListOf<Double>()
        var balance = state.settings.startingBalance
        labels += tr(language, "Start", "Depart")
        values += balance
        for (tx in sortedTransactions) {
            val sign = if (tx.type.equals("income", ignoreCase = true)) 1.0 else -1.0
            balance += sign * tx.amount
            labels += formatDateLabel(tx.datetimeLocal)
            values += balance
        }
        labels to values
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text(
                tr(language, "Graphs", "Graphiques"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        }
        item {
            Card {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        tr(language, "Monthly spending", "Depenses mensuelles"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (monthlyExpenses.isEmpty()) {
                        Text(tr(language, "No data to plot yet.", "Pas encore de donnees a tracer."))
                    } else {
                        SimpleBarChart(
                            values = monthlyExpenses,
                            barColor = Color(0xFF2B7FFF),
                            averageLine = monthlyAverage,
                            modifier = Modifier.fillMaxWidth().height(220.dp),
                        )
                        if (monthlyAverage != null) {
                            Text(
                                tr(
                                    language,
                                    "Dashed line: average spending for completed months so far.",
                                    "Ligne pointillee : depense moyenne des mois deja ecoules."
                                ),
                                style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFF5B6570)
                            )
                        }
                        AxisLabelRow(labels = monthLabels)
                    }
                }
            }
        }
        item {
            Card {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        tr(language, "Cumulative spending vs budgets", "Depenses cumulees vs budgets"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (monthKeys.isEmpty()) {
                        Text(tr(language, "No data to plot yet.", "Pas encore de donnees a tracer."))
                    } else {
                        val series = listOf(
                            LineSeries(
                                tr(language, "Expenses", "Depenses"),
                                cumulativeExpenses,
                                Color(0xFFEF476F)
                            ),
                            LineSeries(
                                tr(language, "Plan budget", "Budget plan"),
                                cumulativePlan,
                                Color(0xFF06D6A0)
                            ),
                            LineSeries(
                                tr(language, "Projected budget", "Budget projete"),
                                cumulativeProjected,
                                Color(0xFF118AB2)
                            ),
                        )
                        SimpleLineChart(
                            series = series,
                            modifier = Modifier.fillMaxWidth().height(240.dp),
                        )
                        LineLegend(series)
                        AxisLabelRow(labels = monthLabels)
                    }
                }
            }
        }
        item {
            Card {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        tr(language, "Running balance over time", "Solde cumule dans le temps"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (runningBalance.second.size < 2) {
                        Text(tr(language, "Not enough transactions yet.", "Pas assez de transactions pour tracer."))
                    } else {
                        val series = listOf(
                            LineSeries(
                                tr(language, "Estimated balance", "Solde estime"),
                                runningBalance.second,
                                Color(0xFF7B5BFF)
                            )
                        )
                        SimpleLineChart(
                            series = series,
                            modifier = Modifier.fillMaxWidth().height(240.dp),
                        )
                        LineLegend(series)
                        AxisLabelRow(labels = runningBalance.first)
                    }
                }
            }
        }
        item {
            Card {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        tr(language, "Category averages", "Moyennes par categorie"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (categoryAverageRows.isEmpty()) {
                        Text(tr(language, "No category history yet.", "Pas encore d'historique par categorie."))
                    } else {
                        SimpleBarChart(
                            values = categoryAverageValues,
                            barColor = Color(0xFF06A77D),
                            modifier = Modifier.fillMaxWidth().height(220.dp),
                        )
                        AxisLabelRow(labels = categoryAverageLabels)
                    }
                }
            }
        }
    }
}

@Composable
private fun SimpleBarChart(
    values: List<Double>,
    barColor: Color,
    averageLine: Double? = null,
    modifier: Modifier = Modifier,
) {
    val axisColor = Color(0xFF9CA3AF)
    val gridColor = Color(0xFFE5E7EB)
    val averageColor = Color(0xFFEF476F)
    Canvas(modifier = modifier) {
        if (values.isEmpty()) return@Canvas
        val maxVal = (values.maxOrNull() ?: 0.0).coerceAtLeast(1.0)
        val left = 36f
        val right = size.width - 8f
        val top = 10f
        val bottom = size.height - 24f
        val chartW = (right - left).coerceAtLeast(1f)
        val chartH = (bottom - top).coerceAtLeast(1f)
        drawLine(axisColor, start = androidx.compose.ui.geometry.Offset(left, top), end = androidx.compose.ui.geometry.Offset(left, bottom), strokeWidth = 2f)
        drawLine(axisColor, start = androidx.compose.ui.geometry.Offset(left, bottom), end = androidx.compose.ui.geometry.Offset(right, bottom), strokeWidth = 2f)
        for (i in 1..3) {
            val y = top + chartH * (i / 4f)
            drawLine(
                gridColor,
                start = androidx.compose.ui.geometry.Offset(left, y),
                end = androidx.compose.ui.geometry.Offset(right, y),
                strokeWidth = 1f
            )
        }
        val count = values.size
        val gap = chartW / count.toFloat()
        val barW = (gap * 0.62f).coerceAtLeast(3f)
        values.forEachIndexed { idx, raw ->
            val v = raw.coerceAtLeast(0.0)
            val ratio = (v / maxVal).toFloat().coerceIn(0f, 1f)
            val h = chartH * ratio
            val x = left + idx * gap + (gap - barW) / 2f
            drawRect(
                color = barColor,
                topLeft = androidx.compose.ui.geometry.Offset(x, bottom - h),
                size = androidx.compose.ui.geometry.Size(barW, h)
            )
        }
        averageLine?.takeIf { it > 0.0 }?.let { average ->
            val ratio = (average / maxVal).toFloat().coerceIn(0f, 1f)
            val y = bottom - chartH * ratio
            var x = left
            while (x < right) {
                val endX = (x + 16f).coerceAtMost(right)
                drawLine(
                    averageColor,
                    start = androidx.compose.ui.geometry.Offset(x, y),
                    end = androidx.compose.ui.geometry.Offset(endX, y),
                    strokeWidth = 3f,
                )
                x += 28f
            }
        }
    }
}

@Composable
private fun SimpleLineChart(
    series: List<LineSeries>,
    modifier: Modifier = Modifier,
) {
    val axisColor = Color(0xFF9CA3AF)
    val gridColor = Color(0xFFE5E7EB)
    Canvas(modifier = modifier) {
        val plotted = series.filter { it.values.isNotEmpty() }
        if (plotted.isEmpty()) return@Canvas
        val xCount = plotted.maxOf { it.values.size }
        if (xCount <= 0) return@Canvas
        val allValues = plotted.flatMap { s ->
            if (s.values.size == xCount) s.values else s.values + List(xCount - s.values.size) { s.values.lastOrNull() ?: 0.0 }
        }
        val minVal = allValues.minOrNull() ?: 0.0
        val maxVal = allValues.maxOrNull() ?: 1.0
        val range = (maxVal - minVal).takeIf { it > 0.0 } ?: 1.0

        val left = 36f
        val right = size.width - 8f
        val top = 10f
        val bottom = size.height - 24f
        val chartW = (right - left).coerceAtLeast(1f)
        val chartH = (bottom - top).coerceAtLeast(1f)
        drawLine(axisColor, start = androidx.compose.ui.geometry.Offset(left, top), end = androidx.compose.ui.geometry.Offset(left, bottom), strokeWidth = 2f)
        drawLine(axisColor, start = androidx.compose.ui.geometry.Offset(left, bottom), end = androidx.compose.ui.geometry.Offset(right, bottom), strokeWidth = 2f)
        for (i in 1..3) {
            val y = top + chartH * (i / 4f)
            drawLine(
                gridColor,
                start = androidx.compose.ui.geometry.Offset(left, y),
                end = androidx.compose.ui.geometry.Offset(right, y),
                strokeWidth = 1f
            )
        }
        val denom = (xCount - 1).coerceAtLeast(1).toFloat()
        plotted.forEach { s ->
            val path = Path()
            val vals = if (s.values.size == xCount) s.values else s.values + List(xCount - s.values.size) { s.values.lastOrNull() ?: 0.0 }
            vals.forEachIndexed { idx, v ->
                val x = left + (idx.toFloat() / denom) * chartW
                val y = bottom - (((v - minVal) / range).toFloat().coerceIn(0f, 1f) * chartH)
                if (idx == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(
                path = path,
                color = s.color,
                style = Stroke(width = 4f, cap = StrokeCap.Round)
            )
            if (xCount <= 24) {
                vals.forEachIndexed { idx, v ->
                    val x = left + (idx.toFloat() / denom) * chartW
                    val y = bottom - (((v - minVal) / range).toFloat().coerceIn(0f, 1f) * chartH)
                    drawCircle(color = s.color, radius = 3.5f, center = androidx.compose.ui.geometry.Offset(x, y))
                }
            }
        }
    }
}

@Composable
private fun LineLegend(series: List<LineSeries>) {
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        series.forEach { s ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(modifier = Modifier.width(14.dp).height(4.dp).background(s.color))
                Text(s.label, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun AxisLabelRow(labels: List<String>) {
    if (labels.isEmpty()) return
    val sampleLabels = if (labels.size <= 8) {
        labels
    } else {
        labels.filterIndexed { index, _ -> index % ((labels.size / 8).coerceAtLeast(1)) == 0 }
    }
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        sampleLabels.forEach { label ->
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                color = Color(0xFF5B6570)
            )
        }
    }
}

private fun runningTotals(values: List<Double>): List<Double> {
    var sum = 0.0
    return values.map { v ->
        sum += v
        sum
    }
}

private fun formatMonthLabel(monthKey: String): String {
    val parts = monthKey.split("-")
    if (parts.size == 2) {
        val y = parts[0].takeLast(2)
        val m = parts[1].padStart(2, '0')
        return "$m/$y"
    }
    return monthKey
}

private fun formatDateLabel(iso: String): String {
    val date = iso.take(10)
    return if (date.length == 10 && date[4] == '-' && date[7] == '-') {
        "${date.substring(5, 7)}/${date.substring(8, 10)}"
    } else {
        date
    }
}

@Composable
private fun SummaryGrid(snapshot: DashboardSnapshot, language: String) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "Current balance", "Solde actuel"),
                snapshot.estimatedBalance.asMoney(),
                Modifier.weight(1f),
                true
            )
            MetricCard(
                tr(language, "Left this month", "Reste ce mois-ci"),
                snapshot.monthRemainingProjected.asMoney(),
                Modifier.weight(1f),
                snapshot.monthRemainingProjected >= 0
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "Net rent this month", "Loyer net du mois"),
                snapshot.rentMonthPaid.asMoney(),
                Modifier.weight(1f),
                snapshot.rentMonthPaid <= snapshot.monthBudgetPlan || snapshot.monthBudgetPlan <= 0.0
            )
            MetricCard(
                tr(language, "Average per month", "Moyenne par mois"),
                snapshot.avgMonthlyExpenses.asMoney(),
                Modifier.weight(1f),
                false
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "Spent this month", "Depense ce mois-ci"),
                snapshot.monthSpent.asMoney(),
                Modifier.weight(1f),
                false
            )
            MetricCard(
                tr(language, "Income this month", "Revenu ce mois-ci"),
                snapshot.monthIncome.asMoney(),
                Modifier.weight(1f),
                true
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "Month budget (plan)", "Budget du mois (plan)"),
                snapshot.monthBudgetPlan.asMoney(),
                Modifier.weight(1f),
                false
            )
            MetricCard(
                tr(language, "Month budget (predicted)", "Budget du mois (projete)"),
                snapshot.monthBudgetProjected.asMoney(),
                Modifier.weight(1f),
                false
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "School-year coverage (plan)", "Couverture annee scolaire (plan)"),
                "${snapshot.schoolCoveragePlan.format2()} ${tr(language, "months", "mois")}",
                Modifier.weight(1f),
                snapshot.schoolCoveragePlan >= 0
            )
            MetricCard(
                tr(language, "School-year coverage (proj)", "Couverture annee scolaire (proj)"),
                "${snapshot.schoolCoverageProjected.format2()} ${tr(language, "months", "mois")}",
                Modifier.weight(1f),
                snapshot.schoolCoverageProjected >= 0
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "Savings vs campus (plan)", "Epargne vs campus (plan)"),
                snapshot.savingsVsCampusPlan.asMoney(),
                Modifier.weight(1f),
                snapshot.savingsVsCampusPlan >= 0
            )
            MetricCard(
                tr(language, "Savings vs campus (predicted)", "Epargne vs campus (projete)"),
                snapshot.savingsVsCampusProjected.asMoney(),
                Modifier.weight(1f),
                snapshot.savingsVsCampusProjected >= 0
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            MetricCard(
                tr(language, "Projected final expenses (plan)", "Depenses finales projetees (plan)"),
                snapshot.projectedFinalExpensesPlan.asMoney(),
                Modifier.weight(1f),
                false
            )
            MetricCard(
                tr(language, "Projected final expenses (auto)", "Depenses finales projetees (auto)"),
                snapshot.projectedFinalExpensesAuto.asMoney(),
                Modifier.weight(1f),
                false
            )
        }
    }
}

@Composable
private fun CategoryAveragesCard(
    language: String,
    rows: List<CategoryAverageRow>,
    monthsCount: Int,
) {
    Card {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                tr(language, "Category averages", "Moyennes par categorie"),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                if (rows.isEmpty()) {
                    tr(
                        language,
                        "Add a few expense transactions to see category averages.",
                        "Ajoutez quelques depenses pour voir les moyennes par categorie."
                    )
                } else {
                    tr(
                        language,
                        "Average monthly spend across $monthsCount months with history.",
                        "Depense mensuelle moyenne sur $monthsCount mois d'historique."
                    )
                },
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF5B6570)
            )
            if (rows.isEmpty()) {
                Text(tr(language, "No data yet.", "Pas encore de donnees."))
            } else {
                rows.take(6).forEach { row ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                displayCategory(row.category, language),
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                tr(language, "Used in ${row.monthsWithSpend} months", "Utilise dans ${row.monthsWithSpend} mois"),
                                style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFF5B6570)
                            )
                        }
                        Text(
                            row.averageMonthly.asMoney(),
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF0B2240)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricCard(title: String, value: String, modifier: Modifier = Modifier, positive: Boolean) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.labelMedium, color = Color(0xFF5B6570))
            Text(
                value,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = if (positive) Color(0xFF0A7C66) else Color(0xFF0B2240)
            )
        }
    }
}

@Composable
private fun MonthlyTotalsTable(rows: List<MonthlyTotal>, language: String) {
    val hScroll = rememberScrollState()
    Card {
        Box(modifier = Modifier.fillMaxWidth().horizontalScroll(hScroll)) {
            Column(modifier = Modifier.width(900.dp)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFF0C1A33))
                        .padding(vertical = 8.dp, horizontal = 8.dp)
                ) {
                    HeaderCell(tr(language, "Month", "Mois"), 110.dp)
                    HeaderCell(tr(language, "Budget (plan)", "Budget (plan)"), 150.dp)
                    HeaderCell(tr(language, "Budget (proj)", "Budget (proj)"), 150.dp)
                    HeaderCell(tr(language, "Expenses", "Depenses"), 150.dp)
                    HeaderCell(tr(language, "Delta plan", "Ecart plan"), 150.dp)
                    HeaderCell(tr(language, "Delta proj", "Ecart proj"), 150.dp)
                }
                rows.forEachIndexed { idx, row ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(if (idx % 2 == 0) Color(0xFFF8FAFC) else Color.White)
                            .padding(vertical = 8.dp, horizontal = 8.dp)
                    ) {
                        BodyCell(formatMonthLabel(row.month), 110.dp)
                        BodyCell(row.budgetPlan.asMoney(), 150.dp)
                        BodyCell(row.budgetProjected.asMoney(), 150.dp)
                        BodyCell(row.totalExpenses.asMoney(), 150.dp)
                        BodyCell(row.deltaPlan.asMoney(), 150.dp)
                        BodyCell(row.deltaProjected.asMoney(), 150.dp)
                    }
                }
            }
        }
    }
}

@Composable
private fun HeaderCell(text: String, width: androidx.compose.ui.unit.Dp) {
    Text(
        text,
        color = Color.White,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier.width(width),
        style = MaterialTheme.typography.labelSmall,
        textAlign = TextAlign.Start
    )
}

@Composable
private fun BodyCell(text: String, width: androidx.compose.ui.unit.Dp) {
    Text(
        text,
        modifier = Modifier.width(width),
        textAlign = TextAlign.Start,
        style = MaterialTheme.typography.bodySmall,
    )
}

@Composable
private fun AddEntryScreen(
    language: String,
    onAdd: (Double, String, String, String, String) -> Unit,
) {
    var quickText by rememberSaveable { mutableStateOf("") }
    var amount by rememberSaveable { mutableStateOf("") }
    var label by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf("misc") }
    var type by rememberSaveable { mutableStateOf("expense") }
    var notes by rememberSaveable { mutableStateOf("") }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text(
                tr(language, "Add entry", "Ajouter une entree"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        }

        item {
            Card {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = quickText,
                        onValueChange = { quickText = it },
                        label = { Text(tr(language, "Quick add (example: 42 Walmart)", "Ajout rapide (exemple: 42 Walmart)")) },
                        modifier = Modifier.fillMaxWidth()
                    )
                    FilledTonalButton(onClick = {
                        val parsed = parseQuickAdd(quickText)
                        if (parsed != null) {
                            amount = parsed.first.toString()
                            label = parsed.second
                            if (category.isBlank()) category = "misc"
                            notes = if (notes.isBlank()) "Quick add" else notes
                        }
                    }) { Text(tr(language, "Parse quick text", "Analyser texte rapide")) }
                }
            }
        }

        item {
            Card {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text(tr(language, "Amount", "Montant")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = label, onValueChange = { label = it }, label = { Text(tr(language, "Label", "Libelle")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = category, onValueChange = { category = it }, label = { Text(tr(language, "Category", "Categorie")) }, modifier = Modifier.fillMaxWidth())
                    TypeSelector(type = type, onChange = { type = it }, language = language)
                    OutlinedTextField(value = notes, onValueChange = { notes = it }, label = { Text(tr(language, "Notes", "Notes")) }, modifier = Modifier.fillMaxWidth())

                    Button(
                        onClick = {
                            val amt = amount.toDoubleOrNull() ?: return@Button
                            onAdd(amt, label.trim(), category.trim(), type, notes.trim())
                            amount = ""
                            label = ""
                            notes = ""
                            quickText = ""
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(tr(language, "Save entry", "Enregistrer entree"))
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TransactionsScreen(
    language: String,
    transactions: List<TransactionRecord>,
    onDelete: (String) -> Unit,
    onUpdate: (TransactionRecord) -> Unit,
    onToggleExcluded: (String, Boolean) -> Unit,
) {
    var search by rememberSaveable { mutableStateOf("") }
    var monthFilter by rememberSaveable { mutableStateOf("all") }
    var monthExpanded by remember { mutableStateOf(false) }
    var editingTx by remember { mutableStateOf<TransactionRecord?>(null) }
    val monthOptions = remember(transactions) {
        buildList {
            add("all")
            addAll(
                transactions
                    .map { monthKeyFromIsoDateTime(it.datetimeLocal) }
                    .distinct()
                    .sortedDescending()
            )
        }
    }

    val filtered = remember(transactions, search, monthFilter) {
        val s = search.trim().lowercase()
        transactions.filter { tx ->
            val monthMatches = monthFilter == "all" || monthKeyFromIsoDateTime(tx.datetimeLocal) == monthFilter
            val textMatches = s.isBlank() ||
                tx.label.lowercase().contains(s) ||
                tx.category.lowercase().contains(s) ||
                tx.notes.lowercase().contains(s)
            monthMatches && textMatches
        }
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            Text(
                tr(language, "Transactions", "Transactions"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                label = { Text(tr(language, "Search", "Rechercher")) },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))
            ExposedDropdownMenuBox(
                expanded = monthExpanded,
                onExpandedChange = { monthExpanded = !monthExpanded }
            ) {
                OutlinedTextField(
                    value = monthFilterLabel(language, monthFilter),
                    onValueChange = {},
                    readOnly = true,
                    label = { Text(tr(language, "Month", "Mois")) },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = monthExpanded) },
                    modifier = Modifier.fillMaxWidth().menuAnchor()
                )
                DropdownMenu(expanded = monthExpanded, onDismissRequest = { monthExpanded = false }) {
                    monthOptions.forEach { option ->
                        DropdownMenuItem(
                            text = { Text(monthFilterLabel(language, option)) },
                            onClick = {
                                monthFilter = option
                                monthExpanded = false
                            }
                        )
                    }
                }
            }
        }

        items(filtered, key = { it.id }) { tx ->
            Card {
                Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            tx.label.ifBlank { tr(language, "(no label)", "(sans libelle)") },
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.weight(1f)
                        )
                        Text(
                            (if (tx.type == "expense") "-" else "+") + tx.amount.asMoney().replace("$", ""),
                            color = if (tx.type == "expense") Color(0xFFB23A48) else Color(0xFF0A7C66),
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Text("${displayCategory(tx.category, language)} | ${displayTransactionType(tx.type, language)} | ${tx.datetimeLocal.take(10)}")
                    if (tx.notes.isNotBlank()) Text(tx.notes, color = Color(0xFF4C5968))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = tx.excludedFromAuto, onCheckedChange = { onToggleExcluded(tx.id, it) })
                        Text(tr(language, "Exclude from auto averages", "Exclure des moyennes auto"))
                        Spacer(modifier = Modifier.weight(1f))
                        TextButton(onClick = { editingTx = tx }) { Text(tr(language, "Edit", "Modifier")) }
                        TextButton(onClick = { onDelete(tx.id) }) { Text(tr(language, "Delete", "Supprimer")) }
                    }
                }
            }
        }
    }

    val tx = editingTx
    if (tx != null) {
        var amount by remember(tx.id) { mutableStateOf(tx.amount.toString()) }
        var label by remember(tx.id) { mutableStateOf(tx.label) }
        var category by remember(tx.id) { mutableStateOf(tx.category) }
        var notes by remember(tx.id) { mutableStateOf(tx.notes) }
        var type by remember(tx.id) { mutableStateOf(tx.type) }
        var dateTime by remember(tx.id) { mutableStateOf(tx.datetimeLocal) }
        AlertDialog(
            onDismissRequest = { editingTx = null },
            title = { Text(tr(language, "Edit transaction", "Modifier transaction")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = amount,
                        onValueChange = { amount = it },
                        label = { Text(tr(language, "Amount", "Montant")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    TypeSelector(type = type, onChange = { type = it }, language = language)
                    OutlinedTextField(
                        value = label,
                        onValueChange = { label = it },
                        label = { Text(tr(language, "Label", "Libelle")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = category,
                        onValueChange = { category = it },
                        label = { Text(tr(language, "Category", "Categorie")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = notes,
                        onValueChange = { notes = it },
                        label = { Text(tr(language, "Notes", "Notes")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = dateTime,
                        onValueChange = { dateTime = it },
                        label = { Text(tr(language, "Date/time (YYYY-MM-DD or ISO)", "Date/heure (YYYY-MM-DD ou ISO)")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val amt = amount.toDoubleOrNull()
                    if (amt == null || amt <= 0.0) return@TextButton
                    val normalizedDateTime = normalizeDateTimeInput(dateTime, tx.datetimeLocal)
                    onUpdate(
                        tx.copy(
                            amount = amt,
                            type = normalizeEntryTypeInput(type),
                            label = label.trim(),
                            category = normalizeCategory(category),
                            notes = notes.trim(),
                            datetimeLocal = normalizedDateTime,
                        )
                    )
                    editingTx = null
                }) { Text(tr(language, "Save", "Enregistrer")) }
            },
            dismissButton = {
                TextButton(onClick = { editingTx = null }) { Text(tr(language, "Cancel", "Annuler")) }
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RecurringScreen(
    language: String,
    recurring: List<RecurringCharge>,
    onAddRecurring: (RecurringCharge) -> Unit,
    onUpdateRecurring: (RecurringCharge) -> Unit,
    onDeleteRecurring: (String) -> Unit,
    onApplyNow: () -> Unit,
) {
    var label by rememberSaveable { mutableStateOf("") }
    var amount by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf("rent") }
    var type by rememberSaveable { mutableStateOf("expense") }
    var notes by rememberSaveable { mutableStateOf("") }
    var startDate by rememberSaveable { mutableStateOf(LocalDate.now().toString()) }
    var endDate by rememberSaveable { mutableStateOf("") }
    var frequency by rememberSaveable { mutableStateOf("monthly") }
    var status by rememberSaveable { mutableStateOf("automatic") }
    var editingRecurring by remember { mutableStateOf<RecurringCharge?>(null) }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text(
                tr(language, "Recurring", "Recurrents"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        }

        item {
            Card {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = label, onValueChange = { label = it }, label = { Text(tr(language, "Label", "Libelle")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text(tr(language, "Amount", "Montant")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = category, onValueChange = { category = it }, label = { Text(tr(language, "Category", "Categorie")) }, modifier = Modifier.fillMaxWidth())
                    TypeSelector(type = type, onChange = { type = it }, language = language)
                    OutlinedTextField(value = notes, onValueChange = { notes = it }, label = { Text(tr(language, "Notes", "Notes")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = startDate, onValueChange = { startDate = it }, label = { Text(tr(language, "Start date (YYYY-MM-DD)", "Date debut (YYYY-MM-DD)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = endDate, onValueChange = { endDate = it }, label = { Text(tr(language, "End date (optional)", "Date fin (optionnelle)")) }, modifier = Modifier.fillMaxWidth())

                    DropdownRow(
                        label = tr(language, "Frequency", "Frequence"),
                        value = frequency,
                        options = listOf("monthly", "weekly", "daily"),
                        onSelected = { frequency = it },
                        optionLabel = { displayRecurringFrequency(it, language) }
                    )
                    DropdownRow(
                        label = tr(language, "Status", "Statut"),
                        value = status,
                        options = listOf("automatic", "manual", "paused"),
                        onSelected = { status = it },
                        optionLabel = { displayRecurringStatus(it, language) }
                    )

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        Button(onClick = {
                            val amt = amount.toDoubleOrNull() ?: return@Button
                            val rec = RecurringCharge(
                                id = UUID.randomUUID().toString(),
                                label = label.trim(),
                                amount = amt,
                                type = type,
                                category = normalizeCategory(category),
                                notes = notes.trim(),
                                startDate = startDate.trim(),
                                endDate = endDate.trim().ifBlank { null },
                                frequency = frequency,
                                status = status,
                            )
                            onAddRecurring(rec)
                            label = ""
                            amount = ""
                            notes = ""
                        }, modifier = Modifier.weight(1f)) {
                            Text(tr(language, "Save recurring", "Enregistrer recurrent"))
                        }
                        FilledTonalButton(onClick = onApplyNow, modifier = Modifier.weight(1f)) {
                            Icon(Icons.Default.Build, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text(tr(language, "Apply due now", "Appliquer maintenant"))
                        }
                    }
                }
            }
        }

        item {
            Text(
                tr(language, "Saved recurring", "Recurrents enregistres"),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )
        }
        items(recurring, key = { it.id }) { r ->
            Card {
                Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(r.label, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        Text(r.amount.asMoney())
                    }
                    Text("${displayRecurringFrequency(r.frequency, language)} | ${displayRecurringStatus(r.status, language)} | ${displayTransactionType(r.type, language)}")
                    Text("${displayCategory(r.category, language)} | ${r.startDate} -> ${r.endDate ?: tr(language, "(open)", "(ouverte)")}")
                    Text("${tr(language, "Last applied", "Derniere application")}: ${r.lastAppliedDate ?: tr(language, "never", "jamais")}")
                    Row {
                        Spacer(modifier = Modifier.weight(1f))
                        TextButton(onClick = { editingRecurring = r }) {
                            Text(tr(language, "Edit", "Modifier"))
                        }
                        TextButton(onClick = { onDeleteRecurring(r.id) }) {
                            Text(tr(language, "Delete", "Supprimer"))
                        }
                    }
                }
            }
        }
    }

    val rec = editingRecurring
    if (rec != null) {
        var editLabel by remember(rec.id) { mutableStateOf(rec.label) }
        var editAmount by remember(rec.id) { mutableStateOf(rec.amount.toString()) }
        var editCategory by remember(rec.id) { mutableStateOf(rec.category) }
        var editType by remember(rec.id) { mutableStateOf(rec.type) }
        var editNotes by remember(rec.id) { mutableStateOf(rec.notes) }
        var editStartDate by remember(rec.id) { mutableStateOf(rec.startDate) }
        var editEndDate by remember(rec.id) { mutableStateOf(rec.endDate ?: "") }
        var editFrequency by remember(rec.id) { mutableStateOf(rec.frequency) }
        var editStatus by remember(rec.id) { mutableStateOf(rec.status) }

        AlertDialog(
            onDismissRequest = { editingRecurring = null },
            title = { Text(tr(language, "Edit recurring", "Modifier recurrent")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = editLabel,
                        onValueChange = { editLabel = it },
                        label = { Text(tr(language, "Label", "Libelle")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = editAmount,
                        onValueChange = { editAmount = it },
                        label = { Text(tr(language, "Amount", "Montant")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    TypeSelector(type = editType, onChange = { editType = it }, language = language)
                    OutlinedTextField(
                        value = editCategory,
                        onValueChange = { editCategory = it },
                        label = { Text(tr(language, "Category", "Categorie")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = editNotes,
                        onValueChange = { editNotes = it },
                        label = { Text(tr(language, "Notes", "Notes")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = editStartDate,
                        onValueChange = { editStartDate = it },
                        label = { Text(tr(language, "Start date (YYYY-MM-DD)", "Date debut (YYYY-MM-DD)")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = editEndDate,
                        onValueChange = { editEndDate = it },
                        label = { Text(tr(language, "End date (optional)", "Date fin (optionnelle)")) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    DropdownRow(
                        label = tr(language, "Frequency", "Frequence"),
                        value = editFrequency,
                        options = listOf("monthly", "weekly", "daily"),
                        onSelected = { editFrequency = it },
                        optionLabel = { displayRecurringFrequency(it, language) }
                    )
                    DropdownRow(
                        label = tr(language, "Status", "Statut"),
                        value = editStatus,
                        options = listOf("automatic", "manual", "paused"),
                        onSelected = { editStatus = it },
                        optionLabel = { displayRecurringStatus(it, language) }
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val amt = editAmount.toDoubleOrNull()
                    if (amt == null || amt <= 0.0) return@TextButton
                    val normalizedStart = parseLocalDateOrNull(editStartDate)?.toString()
                        ?: rec.startDate
                    val normalizedEnd = parseLocalDateOrNull(editEndDate)?.toString()
                    onUpdateRecurring(
                        rec.copy(
                            label = editLabel.trim().ifBlank { rec.label },
                            amount = amt,
                            type = normalizeEntryTypeInput(editType),
                            category = normalizeCategory(editCategory),
                            notes = editNotes.trim(),
                            startDate = normalizedStart,
                            endDate = normalizedEnd,
                            frequency = normalizeRecurringFrequencyInput(editFrequency),
                            status = normalizeRecurringStatusInput(editStatus),
                        )
                    )
                    editingRecurring = null
                }) { Text(tr(language, "Save", "Enregistrer")) }
            },
            dismissButton = {
                TextButton(onClick = { editingRecurring = null }) { Text(tr(language, "Cancel", "Annuler")) }
            }
        )
    }
}

private fun normalizeDateTimeInput(value: String, fallback: String): String {
    val text = value.trim()
    if (text.isBlank()) return fallback
    return try {
        java.time.LocalDateTime.parse(text).toString()
    } catch (_: Exception) {
        try {
            java.time.LocalDate.parse(text).atTime(12, 0).toString()
        } catch (_: Exception) {
            fallback
        }
    }
}

private fun normalizeEntryTypeInput(value: String): String {
    return if (value.trim().lowercase() == "income") "income" else "expense"
}

private fun normalizeRecurringFrequencyInput(value: String): String {
    return when (value.trim().lowercase()) {
        "daily", "weekly", "monthly" -> value.trim().lowercase()
        else -> "monthly"
    }
}

private fun normalizeRecurringStatusInput(value: String): String {
    return when (value.trim().lowercase()) {
        "automatic", "manual", "paused" -> value.trim().lowercase()
        else -> "automatic"
    }
}

@Composable
private fun SettingsScreen(
    language: String,
    settings: AppSettings,
    onSave: (AppSettings) -> Unit,
    onExport: () -> Unit,
    onImport: () -> Unit,
    onResetData: () -> Unit,
) {
    var startingBalance by rememberSaveable(settings.startingBalance) { mutableStateOf(settings.startingBalance.toString()) }
    var refunds by rememberSaveable(settings.refundsTotal) { mutableStateOf(settings.refundsTotal.toString()) }
    var campus by rememberSaveable(settings.campusReferenceTotal) { mutableStateOf(settings.campusReferenceTotal.toString()) }
    var food by rememberSaveable(settings.foodMonthly) { mutableStateOf(settings.foodMonthly.toString()) }
    var misc by rememberSaveable(settings.miscMonthly) { mutableStateOf(settings.miscMonthly.toString()) }
    var medical by rememberSaveable(settings.medicalMonthly) { mutableStateOf(settings.medicalMonthly.toString()) }
    var school by rememberSaveable(settings.schoolMonthly) { mutableStateOf(settings.schoolMonthly.toString()) }
    var household by rememberSaveable(settings.householdMonthly) { mutableStateOf(settings.householdMonthly.toString()) }
    var health by rememberSaveable(settings.healthMonthly) { mutableStateOf(settings.healthMonthly.toString()) }
    var extraMonthly by rememberSaveable(settings.extraMonthly) { mutableStateOf(settings.extraMonthly.toString()) }
    var rent by rememberSaveable(settings.rentMonthlyManual) { mutableStateOf(settings.rentMonthlyManual.toString()) }
    var monthsInSchool by rememberSaveable(settings.planMonthsTotal) { mutableStateOf(settings.planMonthsTotal.toString()) }
    var schoolStartMonth by rememberSaveable(settings.schoolYearStartMonth) { mutableStateOf(settings.schoolYearStartMonth.toString()) }
    var avgWindow by rememberSaveable(settings.avgWindowMonths) { mutableStateOf(settings.avgWindowMonths.toString()) }
    var includeCurrent by rememberSaveable(settings.includeCurrentMonthInAvg) { mutableStateOf(settings.includeCurrentMonthInAvg) }
    var autoMode by rememberSaveable(settings.autoMiscEnabled) { mutableStateOf(settings.autoMiscEnabled) }
    var autoIncludeRecurring by rememberSaveable(settings.autoIncludeRecurring) { mutableStateOf(settings.autoIncludeRecurring) }
    var autoWeighted by rememberSaveable(settings.autoWeighted) { mutableStateOf(settings.autoWeighted) }
    var autoHalfLife by rememberSaveable(settings.autoWeightHalfLifeMonths) { mutableStateOf(settings.autoWeightHalfLifeMonths.toString()) }
    var autoCategories by rememberSaveable(settings.autoMiscCategories) { mutableStateOf(settings.autoMiscCategories.joinToString(", ")) }
    var selectedLanguage by rememberSaveable(settings.language) { mutableStateOf(normalizeLanguageCode(settings.language)) }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text(
                tr(language, "Settings", "Parametres"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        }

        item {
            Card {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = startingBalance, onValueChange = { startingBalance = it }, label = { Text(tr(language, "Starting balance", "Solde initial")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = refunds, onValueChange = { refunds = it }, label = { Text(tr(language, "Refunds total", "Total remboursements")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = campus, onValueChange = { campus = it }, label = { Text(tr(language, "Campus reference total", "Reference campus totale")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = food, onValueChange = { food = it }, label = { Text(tr(language, "Food monthly (manual)", "Nourriture mensuelle (manuel)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = misc, onValueChange = { misc = it }, label = { Text(tr(language, "Misc monthly (manual)", "Divers mensuel (manuel)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = medical, onValueChange = { medical = it }, label = { Text(tr(language, "Medical monthly (manual)", "Medical mensuel (manuel)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = school, onValueChange = { school = it }, label = { Text(tr(language, "School monthly (manual)", "Ecole mensuelle (manuel)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = household, onValueChange = { household = it }, label = { Text(tr(language, "Household monthly (manual)", "Maison mensuelle (manuel)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = health, onValueChange = { health = it }, label = { Text(tr(language, "Health monthly (manual)", "Sante mensuelle (manuel)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = extraMonthly, onValueChange = { extraMonthly = it }, label = { Text(tr(language, "Extra monthly (12 mo)", "Extra mensuel (12 mois)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = rent, onValueChange = { rent = it }, label = { Text(tr(language, "Rent monthly (manual baseline)", "Loyer mensuel (base manuelle)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = monthsInSchool, onValueChange = { monthsInSchool = it }, label = { Text(tr(language, "Months in school year", "Mois dans l'annee scolaire")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = schoolStartMonth, onValueChange = { schoolStartMonth = it }, label = { Text(tr(language, "School year start month (1-12)", "Mois de debut scolaire (1-12)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = avgWindow, onValueChange = { avgWindow = it }, label = { Text(tr(language, "Average window months", "Fenetre moyenne (mois)")) }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(
                        value = autoHalfLife,
                        onValueChange = { autoHalfLife = it },
                        label = { Text(tr(language, "Auto half-life (months)", "Demi-vie auto (mois)")) },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = autoCategories,
                        onValueChange = { autoCategories = it },
                        label = { Text(tr(language, "Auto categories (comma-separated)", "Categories auto (separees par virgules)")) },
                        modifier = Modifier.fillMaxWidth()
                    )
                    DropdownRow(
                        label = tr(language, "App language", "Langue de l'app"),
                        value = selectedLanguage,
                        options = listOf("EN", "FR"),
                        onSelected = { selectedLanguage = normalizeLanguageCode(it) },
                        optionLabel = { displayLanguageOption(it, language) }
                    )

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = includeCurrent, onCheckedChange = { includeCurrent = it })
                        Text(tr(language, "Include current month in auto averages", "Inclure le mois courant dans les moyennes auto"))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = autoMode, onCheckedChange = { autoMode = it })
                        Text(tr(language, "Auto mode (use category averages)", "Mode auto (moyennes par categorie)"))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = autoIncludeRecurring, onCheckedChange = { autoIncludeRecurring = it })
                        Text(tr(language, "Auto mode includes recurring transactions", "Le mode auto inclut les transactions recurrentes"))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = autoWeighted, onCheckedChange = { autoWeighted = it })
                        Text(tr(language, "Auto mode uses weighted averages", "Le mode auto utilise des moyennes ponderees"))
                    }

                    Button(onClick = {
                        val parsedAutoCategories = autoCategories
                            .split(",")
                            .map { it.trim() }
                            .filter { it.isNotBlank() }
                        onSave(
                            settings.copy(
                                startingBalance = startingBalance.toDoubleOrNull() ?: settings.startingBalance,
                                refundsTotal = refunds.toDoubleOrNull() ?: settings.refundsTotal,
                                campusReferenceTotal = campus.toDoubleOrNull() ?: settings.campusReferenceTotal,
                                foodMonthly = food.toDoubleOrNull() ?: settings.foodMonthly,
                                miscMonthly = misc.toDoubleOrNull() ?: settings.miscMonthly,
                                medicalMonthly = medical.toDoubleOrNull() ?: settings.medicalMonthly,
                                schoolMonthly = school.toDoubleOrNull() ?: settings.schoolMonthly,
                                householdMonthly = household.toDoubleOrNull() ?: settings.householdMonthly,
                                healthMonthly = health.toDoubleOrNull() ?: settings.healthMonthly,
                                extraMonthly = extraMonthly.toDoubleOrNull() ?: settings.extraMonthly,
                                rentMonthlyManual = rent.toDoubleOrNull() ?: settings.rentMonthlyManual,
                                planMonthsTotal = monthsInSchool.toIntOrNull() ?: settings.planMonthsTotal,
                                schoolYearStartMonth = schoolStartMonth.toIntOrNull() ?: settings.schoolYearStartMonth,
                                avgWindowMonths = avgWindow.toIntOrNull() ?: settings.avgWindowMonths,
                                includeCurrentMonthInAvg = includeCurrent,
                                autoMiscEnabled = autoMode,
                                autoIncludeRecurring = autoIncludeRecurring,
                                autoWeighted = autoWeighted,
                                autoWeightHalfLifeMonths = autoHalfLife.toIntOrNull() ?: settings.autoWeightHalfLifeMonths,
                                autoMiscCategories = parsedAutoCategories,
                                language = normalizeLanguageCode(selectedLanguage),
                            )
                        )
                    }, modifier = Modifier.fillMaxWidth()) {
                        Text(tr(language, "Apply settings", "Appliquer parametres"))
                    }

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        FilledTonalButton(onClick = onImport, modifier = Modifier.weight(1f)) {
                            Text(tr(language, "Import data", "Importer donnees"))
                        }
                        FilledTonalButton(onClick = onExport, modifier = Modifier.weight(1f)) {
                            Text(tr(language, "Export JSON", "Exporter JSON"))
                        }
                    }
                    FilledTonalButton(onClick = onResetData, modifier = Modifier.fillMaxWidth()) {
                        Text(tr(language, "Reset data", "Reinitialiser les donnees"))
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DropdownRow(
    label: String,
    value: String,
    options: List<String>,
    onSelected: (String) -> Unit,
    optionLabel: (String) -> String = { it },
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
        OutlinedTextField(
            value = optionLabel(value),
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor()
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(optionLabel(option)) },
                    onClick = {
                        onSelected(option)
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
private fun TypeSelector(type: String, onChange: (String) -> Unit, language: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        FilledTonalButton(onClick = { onChange("expense") }, modifier = Modifier.weight(1f)) {
            Text(
                tr(language, "Expense", "Depense") +
                    if (type == "expense") tr(language, " (selected)", " (selectionne)") else ""
            )
        }
        FilledTonalButton(onClick = { onChange("income") }, modifier = Modifier.weight(1f)) {
            Text(
                tr(language, "Income", "Revenu") +
                    if (type == "income") tr(language, " (selected)", " (selectionne)") else ""
            )
        }
    }
}

private fun parseQuickAdd(input: String): Pair<Double, String>? {
    val match = Regex("^\\s*([0-9]+(?:\\.[0-9]+)?)\\s*(.*)$").find(input) ?: return null
    val amount = match.groupValues[1].toDoubleOrNull() ?: return null
    val label = match.groupValues.getOrElse(2) { "" }.trim()
    return amount to label
}

private fun tr(language: String, english: String, french: String): String {
    return if (normalizeLanguageCode(language) == "FR") french else english
}

private fun displayLanguageOption(value: String, language: String): String {
    return when (normalizeLanguageCode(value)) {
        "FR" -> tr(language, "French", "Francais")
        else -> tr(language, "English", "Anglais")
    }
}

private fun monthFilterLabel(language: String, value: String): String {
    return if (value == "all") tr(language, "All months", "Tous les mois") else value
}

private fun Double.format2(): String = String.format("%.2f", this)
