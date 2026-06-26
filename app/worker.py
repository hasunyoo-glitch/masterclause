"""QThread worker that runs the analysis pipeline off the UI thread (plan §3, §5.3).

Emits progress/finished/failed signals so the GUI never blocks. Cancellation is
cooperative: ``cancel()`` sets a flag the analyzer checks between stages.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core import analyzer, parser, report_writer
from core.models import AnalysisOptions, AnalysisResult
from core.parser import ParsedDocument


class AnalysisWorker(QThread):
    progress = Signal(str, int)          # (stage label, percent 0-100)
    finished_ok = Signal(object, list)   # (AnalysisResult, written paths)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, options: AnalysisOptions, parsed: ParsedDocument | None = None):
        super().__init__()
        self._options = options
        self._parsed = parsed
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _should_cancel(self) -> bool:
        return self._cancel

    def run(self) -> None:  # noqa: D401 - QThread entry point
        try:
            self.progress.emit("파일 파싱 중…", 2)
            parsed = self._parsed or parser.parse(self._options.input_file_path)
            if self._should_cancel():
                self.cancelled.emit()
                return

            def on_progress(label: str, frac: float) -> None:
                self.progress.emit(label, max(2, min(95, int(frac * 95))))

            result: AnalysisResult = analyzer.analyze(
                parsed,
                self._options,
                progress=on_progress,
                should_cancel=self._should_cancel,
            )

            if self._should_cancel():
                self.cancelled.emit()
                return

            # The report at the user-chosen path is the deliverable and is always
            # written. zero_retention only suppresses the optional history DB and
            # any temp-disk caching (handled where history would be persisted).
            self.progress.emit("리포트 생성 중…", 96)
            written = report_writer.write_report(result, self._options)

            self.progress.emit("완료", 100)
            self.finished_ok.emit(result, written)

        except analyzer.AnalysisCancelled:
            self.cancelled.emit()
        except (analyzer.AnalyzerError, parser.ParserError, report_writer.ReportError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - unexpected
            self.failed.emit(f"예상치 못한 오류: {exc}")
