import gspread
from config import CREDENTIALS_FILE, GOOGLE_SHEET_ID
from datetime import datetime

class GoogleSheetsStorage:
    def __init__(self):
        self.gc = gspread.service_account(filename=CREDENTIALS_FILE)
        self.sh = self.gc.open_by_key(GOOGLE_SHEET_ID)

    def check_today_metric(self, user_id, metric_key, logical_date):
        try:
            worksheet = self.sh.get_worksheet(0)
            all_values = worksheet.get_all_values()
            if not all_values:
                return None

            headers = [h.strip() for h in all_values[0]]
            try:
                date_idx = headers.index("Date")
                user_idx = headers.index("user_id")
                metric_idx = headers.index(metric_key)
            except ValueError:
                return None

            matching_values = []
            for row in all_values[1:]:
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

            SUM_METRICS = ['sleep_hours', 'productivity_hours', 'meditate_minutes']
            if metric_key in SUM_METRICS:
                total = 0.0
                for v in matching_values:
                    try:
                        total += float(v.replace(',', '.'))
                    except ValueError:
                        continue
                return total if total > 0 else None

            return matching_values[-1]

        except Exception as e:
            print(f"[SHEETS] Error in check_today_metric: {e}")
            return None

    def get_day_data(self, user_id, logical_date):
        """Возвращает все метрики за день одним запросом"""
        try:
            worksheet = self.sh.get_worksheet(0)
            all_values = worksheet.get_all_values()
            if not all_values:
                return {}

            headers = [h.strip() for h in all_values[0]]
            date_idx = headers.index("Date")
            user_idx = headers.index("user_id")

            result = {}
            for row in all_values[1:]:
                if len(row) <= max(date_idx, user_idx):
                    continue
                if row[date_idx].strip() == logical_date and str(row[user_idx]).strip() == str(user_id):
                    for i, val in enumerate(row):
                        if i < len(headers) and val.strip():
                            result[headers[i]] = val.strip()
            return result

        except Exception as e:
            print(f"[SHEETS] Error in get_day_data: {e}")
            return {}

    def save_daily(self, user_id, data):
        try:
            worksheet = self.sh.get_worksheet(0)
            headers = [h.strip() for h in worksheet.row_values(1)]

            # Автосоздание колонок для новых метрик
            new_keys = [k for k in data if k not in headers]
            if new_keys:
                print(f"[SHEETS] adding new columns: {new_keys}")
                for key in new_keys:
                    headers.append(key)
                    worksheet.update_cell(1, len(headers), key)

            print(f"[SHEETS] headers={headers}")

            row_to_append = [
                "" if data.get(h) is None else str(data.get(h, ""))
                for h in headers
            ]

            print(f"[SHEETS] row_to_append={row_to_append}")
            worksheet.append_row(row_to_append)
            print(f"[SHEETS] append_row OK")

        except Exception as e:
            print(f"[SHEETS] ERROR in save_daily: {e}")
            import traceback
            traceback.print_exc()

    def save_note(self, user_id, text, is_voice=False, duration=None, telegram_ts=None, uploaded_at=None, source="manual"):
        try:
            try:
                worksheet = self.sh.worksheet("Notes")
            except Exception:
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
            print(f"[SHEETS] Error saving note: {e}")