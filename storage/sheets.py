import gspread
from config import CREDENTIALS_FILE, GOOGLE_SHEET_ID
from metrics import METRICS
from datetime import datetime


class GoogleSheetsStorage:
    def __init__(self):
        self.gc = gspread.service_account(filename=CREDENTIALS_FILE)
        self.sh = self.gc.open_by_key(GOOGLE_SHEET_ID)

    def _ensure_headers(self, worksheet, required_headers):
        """Читает заголовки, добавляет недостающие колонки. Возвращает актуальный список заголовков."""
        existing = worksheet.row_values(1)
        if not existing:
            worksheet.append_row(required_headers)
            return required_headers

        headers = [h.strip().lower() for h in existing if h]
        for h in required_headers:
            if h not in headers:
                col_idx = len(headers) + 1
                worksheet.update_cell(1, col_idx, h)
                headers.append(h)
        return headers

    def save_daily(self, user_id, answers, created_at=None, uploaded_at=None):
        worksheet = self.sh.get_worksheet(0)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_ts = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else now
        uploaded_ts = uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if uploaded_at else now

        # Минимальный набор колонок
        required_headers = ["created_at", "uploaded_at", "user_id"] + list(METRICS.keys())
        headers = self._ensure_headers(worksheet, required_headers)

        # Строка по заголовкам: значение для каждой колонки
        row_data = {
            "created_at": created_ts,
            "uploaded_at": uploaded_ts,
            "user_id": user_id,
            **answers,
        }

        row = [row_data.get(h, "") for h in headers]
        worksheet.append_row(row)

    def save_note(self, user_id, text, is_voice=False, duration=0, telegram_ts=None, uploaded_at=None):
        try:
            worksheet = self.sh.worksheet("Notes")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.sh.add_worksheet(title="Notes", rows="100", cols="20")
            worksheet.append_row(["created_at", "uploaded_at", "User_ID", "Type", "Text", "Duration"])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_ts = telegram_ts.strftime("%Y-%m-%d %H:%M:%S") if telegram_ts else now
        uploaded_ts = uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if uploaded_at else now

        note_type = "Voice" if is_voice else "Text"
        worksheet.append_row([created_ts, uploaded_ts, user_id, note_type, text, duration])
