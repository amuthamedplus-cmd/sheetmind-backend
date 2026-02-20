/**
 * Creates the SheetMind menu when the spreadsheet opens.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("SheetMind")
    .addItem("Open Sidebar", "showSidebar")
    .addToUi();
}

/**
 * Opens the SheetMind sidebar.
 */
function showSidebar() {
  var html = HtmlService.createHtmlOutputFromFile("index")
    .setTitle("SheetMind")
    .setWidth(450);
  SpreadsheetApp.getUi().showSidebar(html);
}

// Pre-built column letter cache
var _colCache = {};
function _colLetter(col) {
  if (_colCache[col]) return _colCache[col];
  var letter = "";
  var c = col;
  while (c > 0) {
    var mod = (c - 1) % 26;
    letter = String.fromCharCode(65 + mod) + letter;
    c = Math.floor((c - 1) / 26);
  }
  _colCache[col] = letter;
  return letter;
}

/**
 * Convert a column letter (A, B, AA) to 1-indexed number.
 */
function _letterToColumn(letter) {
  var col = 0;
  for (var i = 0; i < letter.length; i++) {
    col = col * 26 + (letter.charCodeAt(i) - 64);
  }
  return col;
}

// Must exceed backend RAG_THRESHOLD_ROWS (500) so RAG can activate on large sheets.
// The MAX_CELLS (50,000) safety check below still prevents memory issues on wide sheets.
var MAX_ROWS = 2000;

/**
 * Get list of all sheets in the spreadsheet.
 * @return {Array<Object>} Array of {name, rowCount, isActive}
 */
function getAllSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var activeSheet = ss.getActiveSheet();
  var sheets = ss.getSheets();

  return sheets.map(function(sheet) {
    return {
      name: sheet.getName(),
      rowCount: sheet.getLastRow(),
      isActive: sheet.getName() === activeSheet.getName()
    };
  });
}

/**
 * Get data from a specific sheet by name.
 * @param {string} sheetName - Name of the sheet to read
 * @return {Object} Sheet data object
 */
function getSheetDataByName(sheetName) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = sheetName ? ss.getSheetByName(sheetName) : ss.getActiveSheet();

  if (!sheet) {
    return { error: "Sheet not found: " + sheetName };
  }

  return _readSheetData(sheet);
}

/**
 * Internal function to read data from a sheet.
 */
function _readSheetData(sheet) {
  var dataRange = sheet.getDataRange();
  var numRows = dataRange.getNumRows();
  var numCols = dataRange.getNumColumns();
  var startRow = dataRange.getRow();
  var startCol = dataRange.getColumn();

  var rowsToRead = Math.min(numRows, MAX_ROWS);
  var readRange = sheet.getRange(startRow, startCol, rowsToRead, numCols);
  var values = readRange.getValues();

  var colLetters = [];
  for (var c = 0; c < numCols; c++) {
    colLetters[c] = _colLetter(startCol + c);
  }

  var cells = {};
  for (var r = 0; r < values.length; r++) {
    var row = values[r];
    var rowNum = startRow + r;
    for (var c = 0; c < row.length; c++) {
      var val = row[c];
      if (val === "" || val === null || val === undefined) continue;
      cells[colLetters[c] + rowNum] = String(val);
    }
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var selection = ss.getActiveRange();
  var selectedRange = selection ? selection.getA1Notation() : null;
  var selectedValues = selection ? selection.getValues() : [];

  // Check payload size — prevent sidebar memory crashes on huge sheets
  var cellCount = Object.keys(cells).length;
  var MAX_CELLS = 50000;
  if (cellCount > MAX_CELLS) {
    return {
      sheetName: sheet.getName(),
      dataRange: dataRange.getA1Notation(),
      cells: {},
      totalRows: numRows,
      totalColumns: numCols,
      truncated: true,
      truncatedReason: "Sheet has " + cellCount + " cells (max " + MAX_CELLS + "). Please select a smaller range.",
      cellCount: cellCount,
      selectedRange: selectedRange,
      selectedValues: selectedValues
    };
  }

  return {
    sheetName: sheet.getName(),
    dataRange: dataRange.getA1Notation(),
    cells: cells,
    totalRows: numRows,
    totalColumns: numCols,
    truncated: numRows > MAX_ROWS,
    selectedRange: selectedRange,
    selectedValues: selectedValues
  };
}

/**
 * Reads data from the active sheet and returns it to the sidebar.
 */
function getSheetData() {
  var sheet = SpreadsheetApp.getActiveSheet();
  return _readSheetData(sheet);
}

// ─────────────────────────────────────────────
// Sheet Actions — called from the sidebar
// ─────────────────────────────────────────────

/**
 * Execute a sheet action from the AI.
 * @param {Object} action - The action object from the AI response.
 * @return {string} Status message.
 */
function executeSheetAction(action) {
  if (!action || !action.action) return "No action provided";

  switch (action.action) {
    case "filter":
      return _applyFilter(action.column, action.criteria);
    case "sort":
      return _applySort(action.column, action.ascending !== false);
    case "highlight":
      return _applyHighlight(action.range, action.color || "#FFFF00");
    case "setValue":
      return _setCellValue(action.cell, action.value);
    case "insertColumn":
      return _insertColumn(action.after, action.header);
    case "chart":
      return _createChart(action.type || "BAR", action.dataRange, action.title);
    case "createChart":
      return _createChartFromColumns(action.chartType, action.title, action.dataSheet, action.labelColumn, action.valueColumn, action.startRow, action.endRow);
    // Agent-style actions
    case "createSheet":
      return createSheet(action.name);
    case "setFormula":
      return setFormula(action.sheet, action.cell, action.formula, action.fillDown);
    case "setValues":
      return setValues(action.sheet, action.range, action.values);
    case "autoFillDown":
      return autoFillDown(action.sheet, action.sourceCell, action.lastRow);
    case "formatRange":
      return formatRange(action.sheet, action.range, action);
    case "readRange":
      return JSON.stringify(readRange(action.sheet, action.range));
    default:
      return "Unknown action: " + action.action;
  }
}

/**
 * Filter the sheet by a column using Google Sheets built-in filter.
 */
function _applyFilter(columnLetter, criteria) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var dataRange = sheet.getDataRange();

  // Remove existing filter if any
  var existingFilter = sheet.getFilter();
  if (existingFilter) existingFilter.remove();

  var colIndex = _letterToColumn(columnLetter.toUpperCase());
  var startCol = dataRange.getColumn();
  var relativeCol = colIndex - startCol + 1;

  // Create a new filter on the data range
  var filter = dataRange.createFilter();

  // Parse criteria like ">100", ">=50", "<10", "=Apple", "!=0"
  var match = criteria.match(/^(>=|<=|!=|>|<|=)?\s*(.+)$/);
  if (!match) return "Invalid criteria: " + criteria;

  var operator = match[1] || "=";
  var value = match[2].trim();
  var numValue = Number(value);
  var isNum = !isNaN(numValue) && value !== "";

  // Get all values in the column to build a hide list
  var values = dataRange.getValues();
  var hideValues = [];

  for (var r = 1; r < values.length; r++) { // skip header row
    var cellVal = values[r][relativeCol - 1];
    var cellNum = Number(cellVal);
    var shouldHide = false;

    if (isNum) {
      if (operator === ">" && !(cellNum > numValue)) shouldHide = true;
      else if (operator === ">=" && !(cellNum >= numValue)) shouldHide = true;
      else if (operator === "<" && !(cellNum < numValue)) shouldHide = true;
      else if (operator === "<=" && !(cellNum <= numValue)) shouldHide = true;
      else if (operator === "=" && !(cellNum === numValue)) shouldHide = true;
      else if (operator === "!=" && !(cellNum !== numValue)) shouldHide = true;
    } else {
      var cellStr = String(cellVal).toLowerCase();
      var matchStr = value.toLowerCase();
      if (operator === "=" && cellStr !== matchStr) shouldHide = true;
      else if (operator === "!=" && cellStr === matchStr) shouldHide = true;
    }

    if (shouldHide) {
      hideValues.push(String(cellVal));
    }
  }

  if (hideValues.length > 0) {
    var filterCriteria = SpreadsheetApp.newFilterCriteria()
      .setHiddenValues(hideValues)
      .build();
    filter.setColumnFilterCriteria(relativeCol, filterCriteria);
  }

  return "Filtered column " + columnLetter + " where " + criteria;
}

/**
 * Sort the sheet by a column.
 */
function _applySort(columnLetter, ascending) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var dataRange = sheet.getDataRange();
  var colIndex = _letterToColumn(columnLetter.toUpperCase());
  var startCol = dataRange.getColumn();
  var relativeCol = colIndex - startCol + 1;

  // Sort excluding header row
  var numRows = dataRange.getNumRows();
  var numCols = dataRange.getNumColumns();
  if (numRows > 1) {
    var sortRange = sheet.getRange(2, startCol, numRows - 1, numCols);
    sortRange.sort({ column: colIndex, ascending: ascending });
  }

  return "Sorted by column " + columnLetter + (ascending ? " (A-Z)" : " (Z-A)");
}

/**
 * Highlight a range of cells with a background color.
 */
function _applyHighlight(rangeStr, color) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var range = sheet.getRange(rangeStr);
  range.setBackground(color);
  return "Highlighted " + rangeStr + " with " + color;
}

/**
 * Set a value in a specific cell.
 */
function _setCellValue(cell, value) {
  var sheet = SpreadsheetApp.getActiveSheet();
  sheet.getRange(cell).setValue(value);
  return "Set " + cell + " to " + value;
}

/**
 * Insert a new column after a given column letter.
 */
function _insertColumn(afterLetter, header) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var colIndex = _letterToColumn(afterLetter.toUpperCase());
  sheet.insertColumnAfter(colIndex);
  if (header) {
    sheet.getRange(1, colIndex + 1).setValue(header);
  }
  return "Inserted column after " + afterLetter + (header ? " with header '" + header + "'" : "");
}

/**
 * Create a chart on the active sheet.
 */
function _createChart(chartType, dataRangeStr, title) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var range = sheet.getRange(dataRangeStr || sheet.getDataRange().getA1Notation());

  // Map string type to Charts enum
  var typeMap = {
    "BAR": Charts.ChartType.BAR,
    "LINE": Charts.ChartType.LINE,
    "PIE": Charts.ChartType.PIE,
    "COLUMN": Charts.ChartType.COLUMN,
    "SCATTER": Charts.ChartType.SCATTER,
    "AREA": Charts.ChartType.AREA
  };

  var type = typeMap[(chartType || "BAR").toUpperCase()] || Charts.ChartType.BAR;

  var chart = sheet.newChart()
    .setChartType(type)
    .addRange(range)
    .setPosition(2, range.getLastColumn() + 2, 0, 0)
    .setOption("title", title || "Chart")
    .setOption("width", 500)
    .setOption("height", 300)
    .build();

  sheet.insertChart(chart);

  return "Created " + (chartType || "BAR") + " chart from " + range.getA1Notation();
}

/**
 * Create a chart from specified columns (agent-style).
 * Handles both adjacent and non-adjacent column pairs correctly.
 * @param {string} chartType - bar, line, pie, doughnut, scatter
 * @param {string} title - Chart title
 * @param {string} dataSheet - Sheet name containing the data
 * @param {string} labelColumn - Column letter for labels (e.g., "A", "B")
 * @param {string} valueColumn - Column letter for values (e.g., "B", "G")
 * @param {number} startRow - First data row (default 2)
 * @param {number} endRow - Last data row (optional)
 */
function _createChartFromColumns(chartType, title, dataSheet, labelColumn, valueColumn, startRow, endRow) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = dataSheet ? ss.getSheetByName(dataSheet) : ss.getActiveSheet();

  if (!sheet) {
    return "Sheet not found: " + dataSheet;
  }

  // Determine the last row if not provided
  var lastRow = endRow || sheet.getLastRow();
  var firstRow = startRow || 2;

  // Build separate ranges for labels and values
  var labelRangeStr = labelColumn + firstRow + ":" + labelColumn + lastRow;
  var valueRangeStr = valueColumn + firstRow + ":" + valueColumn + lastRow;

  var labelRange = sheet.getRange(labelRangeStr);
  var valueRange = sheet.getRange(valueRangeStr);

  // Map string type to Charts enum
  var typeMap = {
    "bar": Charts.ChartType.BAR,
    "column": Charts.ChartType.COLUMN,
    "line": Charts.ChartType.LINE,
    "pie": Charts.ChartType.PIE,
    "doughnut": Charts.ChartType.PIE,  // GAS doesn't have doughnut, use pie
    "scatter": Charts.ChartType.SCATTER,
    "area": Charts.ChartType.AREA
  };

  var type = typeMap[(chartType || "bar").toLowerCase()] || Charts.ChartType.BAR;

  // Create chart with both label and value ranges
  var chart = sheet.newChart()
    .setChartType(type)
    .addRange(labelRange)
    .addRange(valueRange)
    .setPosition(2, sheet.getLastColumn() + 2, 0, 0)
    .setOption("title", title || "Chart")
    .setOption("width", 500)
    .setOption("height", 350)
    .setOption("legend", {position: "bottom"})
    .build();

  sheet.insertChart(chart);

  return "Created " + (chartType || "bar") + " chart '" + title + "' from " + dataSheet + " (" + labelRangeStr + ", " + valueRangeStr + ")";
}

// ─────────────────────────────────────────────
// Agent-style actions — Phase 2C
// ─────────────────────────────────────────────

/**
 * Create a new sheet with the given name.
 * If a sheet with that name already exists, it will be cleared and reused.
 * @param {string} name - The name for the new sheet.
 * @return {string} Status message.
 */
function createSheet(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var existing = ss.getSheetByName(name);
  if (existing) {
    existing.clear();
    return "Cleared existing sheet '" + name + "'";
  }
  ss.insertSheet(name);
  return "Created sheet '" + name + "'";
}

/**
 * Set a formula in a specific cell on a named sheet.
 * Optionally fills the formula down based on adjacent column data.
 * @param {string} sheetName - The target sheet name.
 * @param {string} cell - The cell reference (e.g. "B2").
 * @param {string} formula - The formula to set (e.g. "=SUMIF(...)").
 * @param {boolean} fillDown - If true, copy the formula down to match adjacent data.
 * @return {string} Status message.
 */
function setFormula(sheetName, cell, formula, fillDown) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return "Sheet '" + sheetName + "' not found";

  var range = sheet.getRange(cell);
  range.setFormula(formula);

  // CRITICAL: Never use fillDown with array formulas that auto-spill
  // These formulas automatically expand: UNIQUE, FILTER, SORT, SEQUENCE, etc.
  var autoSpillFormulas = /^=\s*(UNIQUE|FILTER|SORT|SORTN|SEQUENCE|ARRAYFORMULA|SPLIT|TRANSPOSE|FLATTEN)\s*\(/i;
  var isAutoSpill = autoSpillFormulas.test(formula);

  if (fillDown && !isAutoSpill) {
    // Wait for the formula to evaluate, then determine how far to fill
    SpreadsheetApp.flush();

    // Parse cell to get column letter and row number
    var cellMatch = cell.match(/^([A-Z]+)(\d+)$/);
    if (cellMatch) {
      var colLetter = cellMatch[1];
      var startRow = parseInt(cellMatch[2]);
      var colIndex = _letterToColumn(colLetter);

      // Find the adjacent column to determine data length
      // Look at column A or the column to the left
      var refCol = colIndex > 1 ? colIndex - 1 : colIndex + 1;
      var lastDataRow = sheet.getLastRow();

      if (lastDataRow > startRow) {
        var numRows = lastDataRow - startRow;
        var sourceRange = sheet.getRange(startRow, colIndex, 1, 1);
        var destRange = sheet.getRange(startRow, colIndex, numRows + 1, 1);
        sourceRange.copyTo(destRange);
      }
    }
    return "Set formula in " + sheetName + "!" + cell + " (filled down)";
  } else if (fillDown && isAutoSpill) {
    return "Set formula in " + sheetName + "!" + cell + " (auto-spill, fillDown skipped)";
  }

  return "Set formula in " + sheetName + "!" + cell;
}

/**
 * Set multiple values in a range on a named sheet.
 * @param {string} sheetName - The target sheet name.
 * @param {string} rangeStr - The range reference (e.g. "A1:B1").
 * @param {Array<Array>} values - 2D array of values to set.
 * @return {string} Status message.
 */
function setValues(sheetName, rangeStr, values) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return "Sheet '" + sheetName + "' not found";

  var range = sheet.getRange(rangeStr);
  range.setValues(values);
  return "Set values in " + sheetName + "!" + rangeStr;
}

/**
 * Copy a formula from sourceCell down to lastRow on a named sheet.
 * @param {string} sheetName - The target sheet name.
 * @param {string} sourceCell - The source cell with the formula (e.g. "B2").
 * @param {number} lastRow - The last row to fill down to.
 * @return {string} Status message.
 */
function autoFillDown(sheetName, sourceCell, lastRow) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return "Sheet '" + sheetName + "' not found";

  var cellMatch = sourceCell.match(/^([A-Z]+)(\d+)$/);
  if (!cellMatch) return "Invalid cell reference: " + sourceCell;

  var colLetter = cellMatch[1];
  var startRow = parseInt(cellMatch[2]);
  var colIndex = _letterToColumn(colLetter);

  if (lastRow <= startRow) return "lastRow must be greater than source row";

  var sourceRange = sheet.getRange(startRow, colIndex, 1, 1);
  var destRange = sheet.getRange(startRow, colIndex, lastRow - startRow + 1, 1);
  sourceRange.copyTo(destRange);

  return "Filled formula from " + sourceCell + " down to row " + lastRow;
}

/**
 * Format a range on a named sheet (bold, background color, font color).
 * @param {string} sheetName - The target sheet name.
 * @param {string} rangeStr - The range reference (e.g. "A1:C1").
 * @param {Object} options - Formatting options: bold, background, fontColor.
 * @return {string} Status message.
 */
function formatRange(sheetName, rangeStr, options) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return "Sheet '" + sheetName + "' not found";

  var range = sheet.getRange(rangeStr);

  if (options.bold) {
    range.setFontWeight("bold");
  }
  if (options.background) {
    range.setBackground(options.background);
  }
  if (options.fontColor) {
    range.setFontColor(options.fontColor);
  }

  return "Formatted " + sheetName + "!" + rangeStr;
}

/**
 * Read values from a range on a named sheet (for verification).
 * @param {string} sheetName - The target sheet name.
 * @param {string} rangeStr - The range reference (e.g. "A1:C10").
 * @return {Object} Object with values array and status.
 */
function readRange(sheetName, rangeStr) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) return { error: "Sheet '" + sheetName + "' not found", values: [] };

  var range = sheet.getRange(rangeStr);
  var values = range.getDisplayValues();

  return {
    sheet: sheetName,
    range: rangeStr,
    values: values
  };
}

/**
 * Execute an array of steps sequentially.
 * Each step is an action object passed to executeSheetAction.
 * @param {Array<Object>} steps - Array of step objects with action property.
 * @return {Array<Object>} Array of results for each step.
 */
function executeStepPlan(steps) {
  var results = [];
  for (var i = 0; i < steps.length; i++) {
    var step = steps[i];
    try {
      var result = executeSheetAction(step.action || step);
      results.push({
        step: step.step || (i + 1),
        status: "done",
        result: result
      });
    } catch (e) {
      results.push({
        step: step.step || (i + 1),
        status: "error",
        result: "Error: " + e.message
      });
      // Stop on error
      break;
    }
    // Flush after each step to ensure changes are applied
    SpreadsheetApp.flush();
  }
  return results;
}

// ─────────────────────────────────────────────
// Undo — reverse agent-created sheet actions
// ─────────────────────────────────────────────

/**
 * Undo agent actions by deleting created sheets and clearing modified cells.
 * @param {Object} undoInfo - Object with sheetsToDelete and cellsToClear
 *   sheetsToDelete: string[] - sheet names to delete
 *   cellsToClear: Array<{sheet: string, range: string}> - cells to clear
 * @return {string} Status message.
 */
function undoSheetActions(undoInfo) {
  if (!undoInfo) return "Nothing to undo";

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var results = [];

  // Delete created sheets
  var sheetsToDelete = undoInfo.sheetsToDelete || [];
  for (var i = 0; i < sheetsToDelete.length; i++) {
    var sheet = ss.getSheetByName(sheetsToDelete[i]);
    if (sheet) {
      // Prevent deleting the last sheet
      if (ss.getSheets().length > 1) {
        ss.deleteSheet(sheet);
        results.push("Deleted sheet '" + sheetsToDelete[i] + "'");
      } else {
        results.push("Cannot delete '" + sheetsToDelete[i] + "' (last sheet)");
      }
    }
  }

  // Clear modified cells on existing sheets
  var cellsToClear = undoInfo.cellsToClear || [];
  for (var j = 0; j < cellsToClear.length; j++) {
    var entry = cellsToClear[j];
    var targetSheet = ss.getSheetByName(entry.sheet);
    if (targetSheet) {
      targetSheet.getRange(entry.range).clear();
      results.push("Cleared " + entry.sheet + "!" + entry.range);
    }
  }

  if (results.length === 0) return "Nothing to undo";
  return results.join("; ");
}

/**
 * Custom function: =SHEETMIND("prompt", A1:B10)
 *
 * Setup: Set your backend URL in Script Properties:
 *   File → Project settings → Script properties → Add:
 *     Key: SHEETMIND_API_URL
 *     Value: https://your-backend.onrender.com/api
 */
function SHEETMIND(prompt, range) {
  var props = PropertiesService.getScriptProperties();
  var API_URL = (props.getProperty("SHEETMIND_API_URL") || "https://YOUR_BACKEND_URL/api") + "/formula/execute";

  var payload = {
    prompt: prompt,
    range_data: range || null
  };

  try {
    var response = UrlFetchApp.fetch(API_URL, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    var code = response.getResponseCode();
    if (code !== 200) return "Error: " + code;

    var json = JSON.parse(response.getContentText());
    return json.result || "No result";
  } catch (e) {
    return "Error: " + e.message;
  }
}
