#voicing_tickets.py
import re
from flask_socketio import join_room, emit
from flask import current_app

def get_audio_sequence(input_value):
    """
    Функция, которая по входному значению (например, "123" или "123А") генерирует последовательности
    аудиофайлов для казахской (KZ) и русской (RU) озвучки.
    """
    sequence_kz = []
    sequence_ru = []
    # Приводим входное значение к строке, если это не так
    if not isinstance(input_value, str):
        input_value = str(input_value)
    # Регулярное выражение для числовой части и необязательной буквы (русские буквы)
    match = re.match(r'^(\d+)([А-Яа-я])?$', input_value)
    if not match:
        current_app.logger.error(f"Invalid input for audio sequence: {input_value}")
        return sequence_kz, sequence_ru

    number = int(match.group(1))
    letter = match.group(2)

    # Обработка числовой части:
    if number >= 1000:
        thousands = (number // 1000) * 1000
        sequence_kz.append(f"woomen_kz/{thousands}.mp3")
        sequence_ru.append(f"male_rus/{thousands}.mp3")
        number %= 1000
    if number >= 100:
        hundreds = (number // 100) * 100
        sequence_kz.append(f"woomen_kz/{hundreds}.mp3")
        sequence_ru.append(f"male_rus/{hundreds}.mp3")
        number %= 100
    if 11 <= number <= 19:
        sequence_kz.append(f"woomen_kz/{number}.mp3")
        sequence_ru.append(f"male_rus/{number}.mp3")
    else:
        if number >= 10:
            tens = (number // 10) * 10
            sequence_kz.append(f"woomen_kz/{tens}.mp3")
            sequence_ru.append(f"male_rus/{tens}.mp3")
            number %= 10
        if number > 0:
            sequence_kz.append(f"woomen_kz/{number}.mp3")
            sequence_ru.append(f"male_rus/{number}.mp3")

    # Если есть буквенная часть – добавляем её
    if letter:
        sequence_kz.append(f"woomen_kz/{letter}.mp3")
        sequence_ru.append(f"male_rus/{letter}.mp3")

    return sequence_kz, sequence_ru

def register_voicing_tickets_events(socketio):
    """
    Регистрирует обработчики событий для озвучивания тикетов.
    Работает в отдельном неймспейсе "/voicing".
    """

# Обновление voicing_tickets.py для поддержки персональных комнат

def register_voicing_tickets_events(socketio):
    """
    Регистрирует обработчики событий для озвучивания тикетов.
    Работает в отдельном неймспейсе "/voicing".
    """
    
    @socketio.on('connect', namespace='/voicing')
    def handle_connect():
        """
        Когда пользователь подключается, автоматически добавляем его в персональную комнату
        на основе его user_id.
        """
        from flask_login import current_user
        if current_user.is_authenticated:
            user_room = f'user_{current_user.id}'
            join_room(user_room)
            current_app.logger.info(f"User {current_user.username} (ID: {current_user.id}) joined personal room: {user_room}")

    @socketio.on('register_tab', namespace='/voicing')
    def handle_register_tab(data):
        """
        Клиент (например, табло) при подключении отправляет свои параметры:
          - tabId: идентификатор табло
          - assignedServices: список ID услуг, для которых этот клиент должен получать озвучку
        Для каждой назначенной услуги клиент будет присоединён к комнате "service_<serviceId>".
        """
        tab_id = data.get('tabId')
        assigned_services = data.get('assignedServices', [])
        
        # Присоединяем клиента к комнатам услуг
        for service_id in assigned_services:
            join_room(f"service_{service_id}")
        
        current_app.logger.info(f"Tab registered: {tab_id}, assigned services: {assigned_services}")

    @socketio.on('join_operator_room', namespace='/voicing')
    def handle_join_operator_room(data):
        """
        Оператор может явно присоединиться к персональной комнате.
        Используется, когда оператор меняет услуги или перезагружает страницу.
        """
        from flask_login import current_user
        if current_user.is_authenticated:
            user_room = f'user_{current_user.id}'
            join_room(user_room)
            current_app.logger.info(f"Operator {current_user.username} explicitly joined room: {user_room}")
            
            # Также присоединяемся к комнатам услуг, если они указаны
            service_ids = data.get('service_ids', [])
            for service_id in service_ids:
                join_room(f"service_{service_id}")
                current_app.logger.info(f"Operator joined service room: service_{service_id}")
            
            return {'status': 'success', 'room': user_room}

    @socketio.on('call_ticket', namespace='/voicing')
    def handle_call_ticket(data):
        """
        Обработчик события вызова тикета.
        Ожидается получение данных:
          - ticketNumber: номер тикета (например, "123" или "123А")
          - cabinetNumber: номер кабинета (аналогично)
          - serviceId: ID услуги, к которой относится тикет
        Функция генерирует аудио последовательности для двух языков и отправляет событие 'play_audio'
        в комнату, соответствующую serviceId.
        """
        ticket_number = data.get('ticketNumber')
        cabinet_number = data.get('cabinetNumber')
        service_id = data.get('serviceId')

        if ticket_number is None or cabinet_number is None or service_id is None:
            current_app.logger.error("call_ticket: отсутствуют необходимые данные")
            return

        # Генерируем последовательности для номера тикета и кабинета
        ticket_seq_kz, ticket_seq_ru = get_audio_sequence(ticket_number)
        cabinet_seq_kz, cabinet_seq_ru = get_audio_sequence(cabinet_number)

        # Формируем итоговые последовательности аудиофайлов:
        # Для казахской озвучки добавляем префиксы/суффиксы
        audio_sequence_kz = (
            ['woomen_kz/at_work.mp3', 'woomen_kz/клиент_номер.mp3'] +
            ticket_seq_kz +
            ['woomen_kz/Подойдите_в_кабинет.mp3'] +
            cabinet_seq_kz
        )
        # Для русской озвучки
        audio_sequence_ru = (
            ['male_rus/клиент_номер.mp3'] +
            ticket_seq_ru +
            ['male_rus/Подойдите_в_кабинет.mp3'] +
            cabinet_seq_ru
        )

        # Отправляем событие 'play_audio' в комнату, соответствующую данной услуге
        room = f"service_{service_id}"
        emit('play_audio', {'sequence': audio_sequence_kz, 'serviceId': service_id}, room=room, namespace='/voicing')
        emit('play_audio', {'sequence': audio_sequence_ru, 'serviceId': service_id}, room=room, namespace='/voicing')
        current_app.logger.info(f"Processed call_ticket for service {service_id}")

    @socketio.on('disconnect', namespace='/voicing')
    def handle_disconnect():
        current_app.logger.info("Client disconnected from voicing namespace.")