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
    
    def check_today_metric(self, user_id, metric_key):
        """Проверяет есть ли запись за сегодня для этой метрики."""
        worksheet = self.sh.get_worksheet(0)
        
        # Получаем все записи
        all_records = worksheet.get_all_records()
        
        # Сегодняшняя дата
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Ищем запись пользователя за сегодня
        for record in reversed(all_records):  # reversed чтобы взять последнюю
            record_date = record.get("created_at", "")[:10]  # Берём только дату
            record_user = str(record.get("user_id", ""))
            
            if record_date == today and record_user == str(user_id):
                # Нашли запись за сегодня
                value = record.get(metric_key)
                if value and value != "":
                    return value
        
        return None

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
        
    def check_today_metric(self, user_id, metric_key):
        """Проверяет есть ли уже запись за сегодня для этой метрики."""
        try:
            worksheet = self.sh.get_worksheet(0)
            headers = worksheet.row_values(1)
            
            # Находим колонки user_id и нужной метрики
            user_id_col = None
            metric_col = None
            created_at_col = None
            
            for i, header in enumerate(headers):
                header_lower = header.strip().lower()
                if header_lower == "user_id":
                    user_id_col = i + 1
                elif header_lower == metric_key.lower():
                    metric_col = i + 1
                elif header_lower == "created_at":
                    created_at_col = i + 1
            
            if not all([user_id_col, metric_col, created_at_col]):
                return None
            
            # Получаем все данные
            all_data = worksheet.get_all_values()
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Ищем запись за сегодня от этого пользователя
            for row in all_data[1:]:  # Пропускаем заголовки
                if len(row) < max(user_id_col, metric_col, created_at_col):
                    continue
                    
                row_user_id = row[user_id_col - 1]
                row_date = row[created_at_col - 1].split()[0]  # Берем только дату
                row_metric_value = row[metric_col - 1]
                
                if (str(row_user_id) == str(user_id) and 
                    row_date == today and 
                    row_metric_value and row_metric_value.strip()):
                    return row_metric_value
            
            return None
            
        except Exception as e:
            print(f"Error checking today's metric: {e}")
            return None

    def save_note(self, user_id, text, is_voice=False, duration=None, telegram_ts=None, uploaded_at=None, source="manual"):
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
