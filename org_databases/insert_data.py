import json
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base

# Эта часть кода определяет, где находится сам скрипт
script_dir = os.path.dirname(os.path.abspath(__file__))

# Теперь мы строим полные пути к файлам, отталкиваясь от папки скрипта
DB_FILE = os.path.join(script_dir, 'org_pol2temirtau.kz_1749304325.db')
JSON_FILE = os.path.join(script_dir, 'ticket_statistics.json')
TABLE_NAME = 'ticket_statistics'
def run_standalone_insert():
    """
    Самодостаточный скрипт для записи данных из JSON в базу данных SQLite.
    Не требует импорта моделей из исходного проекта.
    """
    # 1. Проверяем, что необходимые файлы существуют
    if not os.path.exists(DB_FILE):
        print(f"Ошибка: Файл базы данных '{DB_FILE}' не найден.")
        return
    if not os.path.exists(JSON_FILE):
        print(f"Ошибка: Файл с данными '{JSON_FILE}' не найден.")
        return

    print(f"Подключение к базе данных: '{DB_FILE}'...")
    engine = create_engine(f'sqlite:///{DB_FILE}')

    # 2. Используем Automap для "отражения" структуры БД
    # Это позволяет нам работать с таблицами, не импортируя их модели
    Base = automap_base()
    # "Подготавливаем" Base, заставляя его прочитать схему из БД
    Base.prepare(autoload_with=engine)

    # 3. Получаем класс для нашей таблицы. SQLAlchemy создает его на лету.
    # Имя класса будет таким же, как имя таблицы.
    try:
        TicketStatistics = Base.classes[TABLE_NAME]
    except KeyError:
        print(f"Ошибка: Таблица '{TABLE_NAME}' не найдена в базе данных '{DB_FILE}'.")
        print("Убедитесь, что таблица была создана приложением.")
        return

    # 4. Создаем сессию для работы с БД
    Session = sessionmaker(bind=engine)
    session = Session()

    # 5. Загружаем данные из JSON
    print(f"Чтение данных из файла '{JSON_FILE}'...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        tickets_data = json.load(f)

    print(f"Начинаю запись {len(tickets_data)} записей в таблицу '{TABLE_NAME}'...")

    # 6. Записываем данные, обернув в транзакцию для безопасности
    try:
        records_to_add = []
        for i, record in enumerate(tickets_data, 1):
            # Преобразуем строки из JSON в объекты date и time
            record_date = datetime.strptime(record['date'], '%Y-%m-%d').date()
            issue_time_obj = datetime.strptime(record['issue_time'], '%H:%M:%S.%f').time()
            call_time_obj = datetime.strptime(record['call_time'], '%H:%M:%S.%f').time()

            # Создаем объект, используя класс, который SQLAlchemy создал для нас
            # Названия атрибутов (service_id, date) должны совпадать с названиями столбцов в таблице
            new_stat = TicketStatistics(
                service_id=record['service_id'],
                date=record_date,
                issue_time=issue_time_obj,
                call_time=call_time_obj
            )
            records_to_add.append(new_stat)
            
            # Для наглядности будем выводить прогресс
            if i % 1000 == 0:
                print(f"Подготовлено {i} записей...")

        # Добавляем все подготовленные записи в сессию одним махом
        print("Добавление всех записей в сессию...")
        session.add_all(records_to_add)

        # Сохраняем все изменения в базе данных
        print("Сохранение изменений в БД (commit)...")
        session.commit()
        print(f"\nУспешно! Все {len(records_to_add)} записей были записаны в базу данных.")

    except Exception as e:
        print(f"\nПроизошла ошибка во время записи: {e}")
        session.rollback()
        print("Все изменения были отменены.")
    finally:
        session.close()
        print("Соединение с базой данных закрыто.")

if __name__ == '__main__':
    run_standalone_insert()