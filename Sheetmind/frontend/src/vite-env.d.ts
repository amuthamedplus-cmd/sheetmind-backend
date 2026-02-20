/// <reference types="vite/client" />

interface SheetData {
  sheetName: string;
  dataRange: string;
  cells: Record<string, string>;
  totalRows: number;
  totalColumns: number;
  selectedRange: string | null;
  selectedValues: unknown[][];
}

interface SheetInfo {
  name: string;
  rowCount: number;
  isActive: boolean;
}

declare namespace google {
  namespace script {
    namespace host {
      function close(): void;
    }
    namespace run {
      function withSuccessHandler<T>(fn: (result: T) => void): typeof run;
      function withFailureHandler(fn: (error: Error) => void): typeof run;
      function getSheetData(): void;
      function getAllSheets(): void;
      function getSheetDataByName(sheetName: string): void;
      function executeSheetAction(action: Record<string, unknown>): void;
      function undoSheetActions(undoInfo: Record<string, unknown>): void;
    }
  }
}
