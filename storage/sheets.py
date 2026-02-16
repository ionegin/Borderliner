import gspread
from config import CREDENTIALS_FILE, GOOGLE_SHEET_ID
from datetime import datetime, timedelta

class GoogleSheetsStorage:
    def __init__(self):
        self.gc = gspread.service_account(filename=CREDENTIALS_FILE)
        self.sh = self.gc.open_by_key(GOOGLE_SHEET_ID)

    def check_today_metric(self, user_id, metric_key, logical_date):
        """
        Находит все записи за логическую дату и:
        - Суммирует (для числовых метрик)
        - Возвращает последнее (для остальных)
        """
        try:
            worksheet = self.sh.get_worksheet(0)
            # Читаем всё как список списков, чтобы не зависеть от пустых ячеек в словарях
            all_values = worksheet.get_all_values()
            if not all_values:
                return None
            
            headers = all_values[0]
            try:
                date_idx = headers.index("Date")
                user_idx = headers.index("user_id")
                metric_idx = headers.index(metric_key)
            except ValueError:
                return None # Колонка не найдена

            matching_values = []
            
            # Проходим по всем строкам (пропуская заголовки)
            for row in all_values[1:]:
                # Проверяем длину строки, чтобы избежать IndexError
                if len(row) <= max(date_idx, user_idx, metric_idx):
                    continue
                    
                row_date = row[date_idx].strip()
                row_user = str(row[user_idx]).strip()
                row_val = row[metric_idx].strip()
                
                if row_date == logical_date and row_user == str(user_id):
                    if row_val:
                        matching_values.append(row_val)

            if not matching_values:
                return None

            # ЛОГИКА СУММИРОВАНИЯ
            SUM_METRICS = ['sleep_hours', 'productivity_hours', 'meditate_minutes']
            if metric_key in SUM_METRICS:
                total = 0.0
                for v in matching_values:
                    try:
                        # Заменяем запятую на точку для float
                        total += float(v.replace(',', '.'))
                    except ValueError:
                        continue
                return total if total > 0 else None
            
            # Для остальных (yes/no) возвращаем последнее значение
            return matching_values[-1]

        except Exception as e:
            print(f"Error in check_today_metric: {e}")
            return None

    def save_daily(self, user_id, data):
        """Добавляет новую строку, строго соблюдая порядок заголовков."""
        try:
            worksheet = self.sh.get_worksheet(0)
            headers = worksheet.row_values(1)
            row_to_append = [data.get(h, "") for h in headers]
            worksheet.append_row(row_to_append)
        except Exception as e:
            print(f"Error saving daily: {e}")

    def save_note(self, user_id, text, is_voice=False, duration=None, telegram_ts=None, uploaded_at=None, source="manual"):
        try:
            try:
                worksheet = self.sh.worksheet("Notes")
            except:
                worksheet = self.sh.add_worksheet(title="Notes", rows="100", cols="20")
                worksheet.append_row(["created_at", "uploaded_at", "user_id", "format", "note", "duration"])

            created_str = telegram_ts.strftime("%Y-%m-%d %H:%M:%S") if telegram_ts else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            uploaded_str = uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if uploaded_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            worksheet.append_row([
                created_str,
                uploaded_str,
                str(user_id),
                "Voice" if is_voice else "Text",
                text,
                duration if duration else 0
            ])
        except Exception as e:
            print(f"Error saving note: {e}")