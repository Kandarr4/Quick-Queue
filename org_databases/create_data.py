import json
import random
from datetime import date, time, datetime, timedelta
import holidays

# --- НАСТРОЙКИ ГЕНЕРАЦИИ ---

START_DATE = date(2025, 1, 5)
END_DATE = date(2025, 6, 12)
SERVICE_IDS = [1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
OUTPUT_FILE = 'ticket_statistics.json'

# Рабочее время
WORK_DAY_START = time(8, 0)
WORK_DAY_END = time(19, 0)
SATURDAY_END = time(12, 0)

# --- ЛОГИКА ГЕНЕРАЦИИ ---

def generate_ticket_data_per_service():
    """
    Генерирует правдоподобные данные, создавая по 100-200 талонов
    для КАЖДОЙ услуги в день, а затем сортирует их по времени.
    """
    # Получаем праздники Казахстана на 2025 год
    kz_holidays = holidays.KZ(years=[2025])
    
    all_tickets = []
    ticket_id = 1
    current_date = START_DATE

    print(f"Начинаю генерацию данных с {START_DATE} по {END_DATE}...")
    print(f"ВНИМАНИЕ: Будет сгенерировано по 100-200 талонов для каждой из {len(SERVICE_IDS)} услуг в день.")

    while current_date <= END_DATE:
        # День недели: 0 = Понедельник, 5 = Суббота, 6 = Воскресенье
        weekday = current_date.weekday()

        # Пропускаем воскресенья и официальные праздники
        if weekday == 6 or current_date in kz_holidays:
            print(f"\n[{current_date.strftime('%Y-%m-%d')}] - Выходной день, пропускаем.")
            current_date += timedelta(days=1)
            continue

        # Определяем время окончания работы
        if weekday == 5: # Суббота
            closing_time = SATURDAY_END
            day_type = "Суббота (сокращенный день)"
        else: # Будний день
            closing_time = WORK_DAY_END
            day_type = "Будний день"
            
        print(f"\n[{current_date.strftime('%Y-%m-%d')}] - {day_type}. Генерация талонов...")

        tickets_for_today = []
        # --- НОВАЯ ЛОГИКА: Цикл по каждой услуге ---
        for service_id in SERVICE_IDS:
            # Случайное количество талонов для этой конкретной услуги
            num_tickets_for_this_service = random.randint(100, 200)
            
            # Начальное время для первого талона (каждый раз сбрасывается для каждой услуги)
            last_issue_dt = datetime.combine(current_date, WORK_DAY_START) + timedelta(seconds=random.randint(1, 300))

            service_ticket_count = 0
            for _ in range(num_tickets_for_this_service):
                # Следующий талон выдается через случайный промежуток времени (от 10 секунд до 3 минут)
                issue_interval = timedelta(seconds=random.randint(10, 180))
                current_issue_dt = last_issue_dt + issue_interval

                # Если время выдачи превысило время закрытия, прекращаем
                if current_issue_dt.time() > closing_time:
                    break

                # Время ожидания вызова (от 5 до 45 минут)
                wait_time = timedelta(seconds=random.randint(300, 2700))
                call_dt = current_issue_dt + wait_time

                # Сохраняем во временный список с полными объектами datetime для сортировки
                tickets_for_today.append({
                    "service_id": service_id,
                    "issue_datetime": current_issue_dt,
                    "call_datetime": call_dt,
                })
                
                last_issue_dt = current_issue_dt
                service_ticket_count += 1
            print(f"  - Для услуги #{service_id} сгенерировано {service_ticket_count} талонов.")

        # --- СОРТИРОВКА И ФИНАЛИЗАЦИЯ ---
        # Сортируем все талоны за день по времени выдачи, чтобы создать реалистичный поток
        print(f"  > Сортировка {len(tickets_for_today)} талонов за день...")
        tickets_for_today.sort(key=lambda x: x['issue_datetime'])

        # Теперь присваиваем ID и форматируем для JSON
        for temp_ticket in tickets_for_today:
            final_ticket = {
                "id": ticket_id,
                "service_id": temp_ticket['service_id'],
                "date": temp_ticket['issue_datetime'].strftime('%Y-%m-%d'),
                "issue_time": temp_ticket['issue_datetime'].strftime('%H:%M:%S.%f'),
                "call_time": temp_ticket['call_datetime'].strftime('%H:%M:%S.%f'),
            }
            all_tickets.append(final_ticket)
            ticket_id += 1

        # Переходим к следующему дню
        current_date += timedelta(days=1)

    # Сохраняем все данные в JSON файл
    print(f"\nГенерация завершена. Всего создано {len(all_tickets)} записей.")
    print(f"Сохраняю данные в файл: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_tickets, f, ensure_ascii=False, indent=4)
    
    print("Готово!")

if __name__ == '__main__':
    generate_ticket_data_per_service()