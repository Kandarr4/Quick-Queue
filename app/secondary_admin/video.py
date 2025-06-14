# app/secondary_admin/video.py
import os
import shutil
import math
import traceback
from datetime import datetime
from flask import jsonify, request, current_app, url_for
from flask_login import login_required, current_user

from app.db_manager import get_current_db
from . import secondary_admin

@secondary_admin.route('/get_disk_space', methods=['GET'])
@login_required
def get_disk_space():
    # Внутренняя функция для преобразования размера в байтах в человекочитаемый формат
    def convert_size(size_bytes):
        """
        Преобразует размер в байтах в человекочитаемый формат
        """
        if size_bytes == 0:
            return "0 B"
        
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        
        return f"{s} {size_name[i]}"
    
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    current_app.logger.info('Вызван эндпоинт get_disk_space')
    
    # Создаем директорию для видео организации, если она не существует
    org_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    if not os.path.exists(org_video_dir):
        os.makedirs(org_video_dir)
    
    try:
        current_app.logger.info(f'Получение информации о диске для директории: {org_video_dir}')
        
        # Получаем размер используемого пространства (только для папки текущей организации)
        used_space = 0
        for dirpath, dirnames, filenames in os.walk(org_video_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp) and os.path.isfile(fp):
                    used_space += os.path.getsize(fp)
        
        # Пробуем получить значение лимита прямо из объекта пользователя
        total_space = 1073741824  # 1 ГБ по умолчанию
        
        # Сначала проверяем, есть ли атрибут disk_space_limit у текущего пользователя
        if hasattr(current_user, 'disk_space_limit'):
            total_space = current_user.disk_space_limit
        else:
            # Если нет, пробуем получить из базы через SQL запрос
            from flask import g
            from app.db_manager import get_main_db
            
            try:
                # Получаем соединение с основной БД
                main_db = get_main_db()
                
                # Выполняем прямой SQL запрос
                result = main_db.execute("SELECT disk_space_limit FROM admins WHERE username = ?", 
                                        (current_user.username,)).fetchone()
                
                if result and result[0]:
                    total_space = result[0]
            except Exception as db_error:
                current_app.logger.warning(f"Не удалось получить лимит из БД: {str(db_error)}")
                # Продолжаем использовать значение по умолчанию
        
        # Рассчитываем свободное пространство
        free_space = max(0, total_space - used_space)
        
        # Рассчитываем процент использования
        used_percentage = min(100, round((used_space / total_space) * 100, 2)) if total_space > 0 else 100
        
        result = {
            'status': 'success',
            'total': total_space,
            'used': used_space,
            'free': free_space,
            'total_readable': convert_size(total_space),
            'used_readable': convert_size(used_space),
            'free_readable': convert_size(free_space),
            'used_percentage': used_percentage
        }
        
        current_app.logger.info(f'Информация о диске: {result}')
        return jsonify(result)
    
    except Exception as e:
        current_app.logger.error(f'Ошибка при получении информации о диске: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error', 
            'message': f'Ошибка при получении информации о диске: {str(e)}',
            'trace': traceback.format_exc()
        }), 500
        
# app/secondary_admin/video.py

@secondary_admin.route('/video/list', methods=['GET'])
@login_required
def video_list():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    path = request.args.get('path', '').strip('/')
    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    
    if not os.path.exists(base_video_dir):
        os.makedirs(base_video_dir)
        
    video_dir = os.path.join(base_video_dir, path) if path else base_video_dir

    if not os.path.exists(video_dir) or not os.path.isdir(video_dir) or \
       not os.path.abspath(video_dir).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Указанная директория не существует или доступ к ней запрещен'}), 400

    folders = []
    videos = []
    valid_video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']

    try:
        for item in os.listdir(video_dir):
            item_path = os.path.join(video_dir, item)
            if os.path.isdir(item_path):
                folder_stat = os.stat(item_path)
                folders.append({'name': item, 'created': datetime.fromtimestamp(folder_stat.st_ctime).strftime('%d.%m.%Y %H:%M')})
            elif os.path.isfile(item_path) and any(item.lower().endswith(ext) for ext in valid_video_extensions):
                file_stat = os.stat(item_path)
                
                # --- НАЧАЛО ИЗМЕНЕНИЙ ---
                # Собираем относительный путь для url_for, включая подпапки
                relative_path_for_url = os.path.join('video', current_user.database_name, path, item).replace('\\', '/')
                
                video_info = {
                    'name': item,
                    'size': file_stat.st_size,
                    'created': datetime.fromtimestamp(file_stat.st_ctime).strftime('%d.%m.%Y %H:%M'),
                    'url': url_for('static', filename=relative_path_for_url) # <-- ДОБАВЛЯЕМ ПОЛНЫЙ URL
                }
                # --- КОНЕЦ ИЗМЕНЕНИЙ ---
                videos.append(video_info)
    except Exception as e:
        current_app.logger.error(f'Ошибка при чтении директории {video_dir}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при чтении директории: {str(e)}'}), 500

    folders.sort(key=lambda x: x['name'].lower())
    videos.sort(key=lambda x: x['name'].lower())

    return jsonify({'status': 'success', 'data': {'folders': folders, 'videos': videos}})

@secondary_admin.route('/video/folders', methods=['GET'])
@login_required
def video_folders():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    
    # Создаем директорию, если она не существует
    if not os.path.exists(base_video_dir):
        os.makedirs(base_video_dir)
        
    folders = []

    def scan_folders(dir_path, rel_path=''):
        if os.path.exists(dir_path):
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isdir(item_path):
                    item_rel_path = os.path.join(rel_path, item) if rel_path else item
                    folders.append(item_rel_path)
                    scan_folders(item_path, item_rel_path)

    try:
        scan_folders(base_video_dir)
    except Exception as e:
        current_app.logger.error(f'Ошибка при сканировании папок: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при сканировании папок: {str(e)}'}), 500

    return jsonify({'status': 'success', 'folders': folders})


@secondary_admin.route('/video/create_folder', methods=['POST'])
@login_required
def video_create_folder():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    data = request.get_json()
    if not data or 'folder_name' not in data:
        return jsonify({'status': 'error', 'message': 'Не указано имя папки'}), 400

    folder_name = data['folder_name'].strip()
    path = data.get('path', '').strip('/')
    if not folder_name:
        return jsonify({'status': 'error', 'message': 'Имя папки не может быть пустым'}), 400

    if any(c in '\\/:|?*"<>' for c in folder_name):
        return jsonify({'status': 'error', 'message': 'Имя папки содержит недопустимые символы'}), 400

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    
    # Создаем базовую директорию, если она не существует
    if not os.path.exists(base_video_dir):
        os.makedirs(base_video_dir)
        
    new_folder_path = os.path.join(base_video_dir, path, folder_name) if path else os.path.join(base_video_dir, folder_name)

    if not os.path.abspath(new_folder_path).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Недопустимый путь для создания папки'}), 400

    try:
        if os.path.exists(new_folder_path):
            return jsonify({'status': 'error', 'message': 'Папка с таким именем уже существует'}), 400
        os.makedirs(new_folder_path)
        return jsonify({'status': 'success', 'message': 'Папка успешно создана'})
    except Exception as e:
        current_app.logger.error(f'Ошибка при создании папки {new_folder_path}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при создании папки: {str(e)}'}), 500


@secondary_admin.route('/video/upload', methods=['POST'])
@login_required
def video_upload():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'Не выбран файл для загрузки'}), 400

    file = request.files['video']
    path = request.form.get('path', '').strip('/')

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Не выбран файл для загрузки'}), 400

    valid_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
    filename = file.filename
    file_ext = os.path.splitext(filename)[1].lower()

    if file_ext not in valid_extensions:
        return jsonify({'status': 'error', 'message': f'Недопустимый тип файла. Разрешены только: {", ".join(valid_extensions)}'}), 400

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    
    # Создаем базовую директорию, если она не существует
    if not os.path.exists(base_video_dir):
        os.makedirs(base_video_dir)
        
    upload_dir = os.path.join(base_video_dir, path) if path else base_video_dir

    if not os.path.abspath(upload_dir).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Недопустимый путь для загрузки файла'}), 400

    if not os.path.exists(upload_dir) or not os.path.isdir(upload_dir):
        try:
            os.makedirs(upload_dir)
        except Exception as e:
            current_app.logger.error(f'Ошибка при создании директории для загрузки {upload_dir}: {str(e)}')
            return jsonify({'status': 'error', 'message': f'Ошибка при создании директории для загрузки: {str(e)}'}), 500

    secure_filename_value = filename.replace(' ', '_')
    file_path = os.path.join(upload_dir, secure_filename_value)

    if os.path.exists(file_path):
        name, ext = os.path.splitext(secure_filename_value)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        secure_filename_value = f'{name}_{timestamp}{ext}'
        file_path = os.path.join(upload_dir, secure_filename_value)

    try:
        file.save(file_path)
        return jsonify({'status': 'success', 'message': 'Файл успешно загружен', 'filename': secure_filename_value})
    except Exception as e:
        current_app.logger.error(f'Ошибка при сохранении файла {file_path}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при сохранении файла: {str(e)}'}), 500


@secondary_admin.route('/video/rename', methods=['POST'])
@login_required
def video_rename():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    data = request.get_json()
    if not data or 'path' not in data or 'new_name' not in data or 'type' not in data:
        return jsonify({'status': 'error', 'message': 'Не указаны необходимые параметры'}), 400

    item_path = data['path'].strip('/')
    new_name = data['new_name'].strip()
    item_type = data['type']

    if not new_name:
        return jsonify({'status': 'error', 'message': 'Новое имя не может быть пустым'}), 400

    if any(c in '\\/:|?*"<>' for c in new_name):
        return jsonify({'status': 'error', 'message': 'Новое имя содержит недопустимые символы'}), 400

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    full_item_path = os.path.join(base_video_dir, item_path)

    if not os.path.abspath(full_item_path).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Недопустимый путь для переименования'}), 400

    if not os.path.exists(full_item_path):
        return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} не найден(а)'}), 404

    if (item_type == 'folder' and not os.path.isdir(full_item_path)) or \
       (item_type == 'video' and not os.path.isfile(full_item_path)):
        return jsonify({'status': 'error', 'message': f'Указанный путь не является {"папкой" if item_type == "folder" else "файлом"}'}), 400

    parent_dir = os.path.dirname(full_item_path)
    if item_type == 'video':
        _, ext = os.path.splitext(os.path.basename(full_item_path))
        new_name_with_ext = new_name if new_name.lower().endswith(ext.lower()) else new_name + ext
        new_path = os.path.join(parent_dir, new_name_with_ext)
    else:
        new_path = os.path.join(parent_dir, new_name)

    if os.path.exists(new_path):
        return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} с таким именем уже существует'}), 400

    try:
        os.rename(full_item_path, new_path)
        return jsonify({'status': 'success', 'message': f'{"Папка" if item_type == "folder" else "Файл"} успешно переименован(а)'})
    except Exception as e:
        current_app.logger.error(f'Ошибка при переименовании {full_item_path} -> {new_path}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при переименовании: {str(e)}'}), 500


@secondary_admin.route('/video/move', methods=['POST'])
@login_required
def video_move():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    data = request.get_json()
    if not data or 'path' not in data or 'target_folder' not in data or 'type' not in data:
        return jsonify({'status': 'error', 'message': 'Не указаны небходимые параметры'}), 400

    item_path = data['path'].strip('/')
    target_folder = data['target_folder'].strip('/')
    item_type = data['type']

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    full_item_path = os.path.join(base_video_dir, item_path)

    if not os.path.abspath(full_item_path).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Недопустимый путь для перемещения'}), 400

    if not os.path.exists(full_item_path):
        return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} не найден(а)'}), 404

    if (item_type == 'folder' and not os.path.isdir(full_item_path)) or \
       (item_type == 'video' and not os.path.isfile(full_item_path)):
        return jsonify({'status': 'error', 'message': f'Указанный путь не является {"папкой" if item_type == "folder" else "файлом"}'}), 400

    target_dir = base_video_dir if target_folder == '/' else os.path.join(base_video_dir, target_folder)

    if not os.path.abspath(target_dir).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Недопустимый путь целевой директории'}), 400

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return jsonify({'status': 'error', 'message': 'Целевая директория не существует'}), 404

    item_name = os.path.basename(full_item_path)
    target_path = os.path.join(target_dir, item_name)

    if os.path.dirname(full_item_path) == target_dir:
        return jsonify({'status': 'error', 'message': 'Элемент уже находится в указанной директории'}), 400

    if item_type == 'folder' and os.path.abspath(target_dir).startswith(os.path.abspath(full_item_path)):
        return jsonify({'status': 'error', 'message': 'Нельзя переместить папку в её собственную подпапку'}), 400

    if os.path.exists(target_path):
        return jsonify({'status': 'error', 'message': f'В целевой директории уже существует {"папка" if item_type == "folder" else "файл"} с таким именем'}), 400

    try:
        shutil.move(full_item_path, target_path)
        return jsonify({'status': 'success', 'message': f'{"Папка" if item_type == "folder" else "Файл"} успешно перемещен()'})
    except Exception as e:
        current_app.logger.error(f'Ошибка при перемещении {full_item_path} -> {target_path}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при перемещении: {str(e)}'}), 500


@secondary_admin.route('/video/delete', methods=['POST'])
@login_required
def video_delete():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    data = request.get_json()
    if not data or 'path' not in data or 'type' not in data:
        return jsonify({'status': 'error', 'message': 'Не указаны необходимые параметры'}), 400

    item_path = data['path'].strip('/')
    item_type = data['type']

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    full_item_path = os.path.join(base_video_dir, item_path)

    if not os.path.abspath(full_item_path).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Недопустимый путь для удаления'}), 400

    if not os.path.exists(full_item_path):
        return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} не найден(а)'}), 404

    if (item_type == 'folder' and not os.path.isdir(full_item_path)) or \
       (item_type == 'video' and not os.path.isfile(full_item_path)):
        return jsonify({'status': 'error', 'message': f'Указанный путь не является {"папкой" if item_type == "folder" else "файлом"}'}), 400

    try:
        if item_type == 'folder':
            shutil.rmtree(full_item_path)
        else:
            os.remove(full_item_path)
        return jsonify({'status': 'success', 'message': f'{"Папка" if item_type == "folder" else "Файл"} успешно удален(а)'})
    except Exception as e:
        current_app.logger.error(f'Ошибка при удалении {full_item_path}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при удалении: {str(e)}'}), 500


@secondary_admin.route('/get_video_list')
@login_required
def get_video_list():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500

    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    
    # Создаем директорию, если она не существует
    if not os.path.exists(base_video_dir):
        try:
            os.makedirs(base_video_dir)
            current_app.logger.info(f'Создана директория для видео: {base_video_dir}')
        except Exception as e:
            current_app.logger.error(f'Не удалось создать директорию для видео: {str(e)}')
            return jsonify({'videos': []})

    video_files = []
    valid_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']

    try:
        for filename in os.listdir(base_video_dir):
            file_path = os.path.join(base_video_dir, filename)
            if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in valid_extensions):
                video_path = url_for('static', filename=f'video/{current_user.database_name}/{filename}')
                video_files.append(video_path)
    except Exception as e:
        current_app.logger.error(f'Ошибка при чтении директории с видео: {str(e)}')

    return jsonify({'status': 'success', 'videos': video_files})


@secondary_admin.route('/get_video_folders')
@login_required
def get_video_folders():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

    video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)

    if not os.path.exists(video_dir):
        try:
            os.makedirs(video_dir)
            current_app.logger.info(f'Создана директория для видео: {video_dir}')
        except Exception as e:
            current_app.logger.error(f'Не удалось создать директорию для видео: {str(e)}')
            return jsonify({'folders': []})

    folders = []
    try:
        for item in os.listdir(video_dir):
            item_path = os.path.join(video_dir, item)
            if os.path.isdir(item_path):
                folders.append(item)
        folders.insert(0, 'default')
    except Exception as e:
        current_app.logger.error(f'Ошибка при чтении списка папок с видео: {str(e)}')

    return jsonify({'status': 'success', 'folders': folders})

@secondary_admin.route('/get_directory_contents', methods=['GET'])
@login_required
def get_directory_contents():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
    
    path = request.args.get('path', '').strip('/')
    base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
    
    # Создаем директорию, если она не существует
    if not os.path.exists(base_video_dir):
        try:
            os.makedirs(base_video_dir)
            current_app.logger.info(f'Создана директория для видео: {base_video_dir}')
        except Exception as e:
            current_app.logger.error(f'Не удалось создать директорию для видео: {str(e)}')
            return jsonify({'status': 'error', 'message': f'Не удалось создать директорию: {str(e)}'}), 500
            
    video_dir = os.path.join(base_video_dir, path) if path else base_video_dir

    if not os.path.exists(video_dir) or not os.path.isdir(video_dir) or \
       not os.path.abspath(video_dir).startswith(os.path.abspath(base_video_dir)):
        return jsonify({'status': 'error', 'message': 'Указанная директория не существует или доступ к ней запрещен'}), 400

    folders = []
    files = []
    valid_video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']

    try:
        for item in os.listdir(video_dir):
            item_path = os.path.join(video_dir, item)
            if os.path.isdir(item_path):
                folder_stat = os.stat(item_path)
                folders.append({
                    'name': item, 
                    'created': datetime.fromtimestamp(folder_stat.st_ctime).strftime('%d.%m.%Y %H:%M')
                })
            elif os.path.isfile(item_path) and any(item.lower().endswith(ext) for ext in valid_video_extensions):
                file_stat = os.stat(item_path)
                video_info = {
                    'name': item,
                    'size': file_stat.st_size,
                    'created': datetime.fromtimestamp(file_stat.st_ctime).strftime('%d.%m.%Y %H:%M')
                }
                files.append(video_info)
    except Exception as e:
        current_app.logger.error(f'Ошибка при чтении директории {video_dir}: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Ошибка при чтении директории: {str(e)}'}), 500

    folders.sort(key=lambda x: x['name'].lower())
    files.sort(key=lambda x: x['name'].lower())

    return jsonify({
        'status': 'success', 
        'data': {
            'folders': folders, 
            'files': files
        }
    })

@secondary_admin.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
   if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
       return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
   
   folder_name = request.form.get('name', '').strip()
   path = request.form.get('path', '').strip('/')
   
   if not folder_name:
       return jsonify({'status': 'error', 'message': 'Не указано имя папки'}), 400

   if any(c in '\\/:|?*"<>' for c in folder_name):
       return jsonify({'status': 'error', 'message': 'Имя папки содержит недопустимые символы'}), 400

   base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
   
   # Создаем базовую директорию, если она не существует
   if not os.path.exists(base_video_dir):
       try:
           os.makedirs(base_video_dir)
       except Exception as e:
           current_app.logger.error(f'Не удалось создать базовую директорию: {str(e)}')
           return jsonify({'status': 'error', 'message': f'Не удалось создать базовую директорию: {str(e)}'}), 500
           
   new_folder_path = os.path.join(base_video_dir, path, folder_name) if path else os.path.join(base_video_dir, folder_name)

   if not os.path.abspath(new_folder_path).startswith(os.path.abspath(base_video_dir)):
       return jsonify({'status': 'error', 'message': 'Недопустимый путь для создания папки'}), 400

   try:
       if os.path.exists(new_folder_path):
           return jsonify({'status': 'error', 'message': 'Папка с таким именем уже существует'}), 400
       os.makedirs(new_folder_path)
       return jsonify({'status': 'success', 'message': 'Папка успешно создана'})
   except Exception as e:
       current_app.logger.error(f'Ошибка при создании папки {new_folder_path}: {str(e)}')
       return jsonify({'status': 'error', 'message': f'Ошибка при создании папки: {str(e)}'}), 500


@secondary_admin.route('/upload_video', methods=['POST'])
@login_required
def upload_video():
   if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
       return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
   
   if 'video' not in request.files:
       return jsonify({'status': 'error', 'message': 'Не выбран файл для загрузки'}), 400

   file = request.files['video']
   path = request.form.get('path', '').strip('/')

   if file.filename == '':
       return jsonify({'status': 'error', 'message': 'Не выбран файл для загрузки'}), 400

   valid_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
   filename = file.filename
   file_ext = os.path.splitext(filename)[1].lower()

   if file_ext not in valid_extensions:
       return jsonify({'status': 'error', 'message': f'Недопустимый тип файла. Разрешены только: {", ".join(valid_extensions)}'}), 400

   base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
   
   # Создаем базовую директорию, если она не существует
   if not os.path.exists(base_video_dir):
       try:
           os.makedirs(base_video_dir)
       except Exception as e:
           current_app.logger.error(f'Не удалось создать базовую директорию: {str(e)}')
           return jsonify({'status': 'error', 'message': f'Не удалось создать базовую директорию: {str(e)}'}), 500
           
   upload_dir = os.path.join(base_video_dir, path) if path else base_video_dir

   if not os.path.abspath(upload_dir).startswith(os.path.abspath(base_video_dir)):
       return jsonify({'status': 'error', 'message': 'Недопустимый путь для загрузки файла'}), 400

   if not os.path.exists(upload_dir):
       try:
           os.makedirs(upload_dir)
       except Exception as e:
           current_app.logger.error(f'Ошибка при создании директории для загрузки {upload_dir}: {str(e)}')
           return jsonify({'status': 'error', 'message': f'Ошибка при создании директории для загрузки: {str(e)}'}), 500

   secure_filename_value = filename.replace(' ', '_')
   file_path = os.path.join(upload_dir, secure_filename_value)

   if os.path.exists(file_path):
       name, ext = os.path.splitext(secure_filename_value)
       timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
       secure_filename_value = f'{name}_{timestamp}{ext}'
       file_path = os.path.join(upload_dir, secure_filename_value)

   try:
       file.save(file_path)
       return jsonify({'status': 'success', 'message': 'Файл успешно загружен', 'filename': secure_filename_value})
   except Exception as e:
       current_app.logger.error(f'Ошибка при сохранении файла {file_path}: {str(e)}')
       return jsonify({'status': 'error', 'message': f'Ошибка при сохранении файла: {str(e)}'}), 500


@secondary_admin.route('/rename_item', methods=['POST'])
@login_required
def rename_item():
   if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
       return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

   item_type = request.form.get('type')
   path = request.form.get('path')
   new_name = request.form.get('new_name')
   
   if not all([item_type, path, new_name]):
       return jsonify({'status': 'error', 'message': 'Не указаны необходимые параметры'}), 400

   new_name = new_name.strip()
   if not new_name:
       return jsonify({'status': 'error', 'message': 'Новое имя не может быть пустым'}), 400

   if any(c in '\\/:|?*"<>' for c in new_name):
       return jsonify({'status': 'error', 'message': 'Новое имя содержит недопустимые символы'}), 400

   base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
   full_item_path = os.path.join(base_video_dir, path.strip('/'))

   if not os.path.abspath(full_item_path).startswith(os.path.abspath(base_video_dir)):
       return jsonify({'status': 'error', 'message': 'Недопустимый путь для переименования'}), 400

   if not os.path.exists(full_item_path):
       return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} не найден(а)'}), 404

   if (item_type == 'folder' and not os.path.isdir(full_item_path)) or \
      (item_type == 'video' and not os.path.isfile(full_item_path)):
       return jsonify({'status': 'error', 'message': f'Указанный путь не является {"папкой" if item_type == "folder" else "файлом"}'}), 400

   parent_dir = os.path.dirname(full_item_path)
   if item_type == 'video':
       _, ext = os.path.splitext(os.path.basename(full_item_path))
       new_name_with_ext = new_name if new_name.lower().endswith(ext.lower()) else new_name + ext
       new_path = os.path.join(parent_dir, new_name_with_ext)
   else:
       new_path = os.path.join(parent_dir, new_name)

   if os.path.exists(new_path):
       return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} с таким именем уже существует'}), 400

   try:
       os.rename(full_item_path, new_path)
       return jsonify({'status': 'success', 'message': f'{"Папка" if item_type == "folder" else "Файл"} успешно переименован(а)'})
   except Exception as e:
       current_app.logger.error(f'Ошибка при переименовании {full_item_path} -> {new_path}: {str(e)}')
       return jsonify({'status': 'error', 'message': f'Ошибка при переименовании: {str(e)}'}), 500


@secondary_admin.route('/move_item', methods=['POST'])
@login_required
def move_item():
   if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
       return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

   item_type = request.form.get('type')
   path = request.form.get('path')
   target_folder = request.form.get('target_folder')
   
   if not all([item_type, path, target_folder is not None]):
       return jsonify({'status': 'error', 'message': 'Не указаны необходимые параметры'}), 400

   base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
   full_item_path = os.path.join(base_video_dir, path.strip('/'))

   if not os.path.abspath(full_item_path).startswith(os.path.abspath(base_video_dir)):
       return jsonify({'status': 'error', 'message': 'Недопустимый путь для перемещения'}), 400

   if not os.path.exists(full_item_path):
       return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} не найден(а)'}), 404

   if (item_type == 'folder' and not os.path.isdir(full_item_path)) or \
      (item_type == 'video' and not os.path.isfile(full_item_path)):
       return jsonify({'status': 'error', 'message': f'Указанный путь не является {"папкой" if item_type == "folder" else "файлом"}'}), 400

   target_folder = target_folder.strip('/')
   target_dir = base_video_dir if target_folder == '' or target_folder == '/' else os.path.join(base_video_dir, target_folder)

   if not os.path.abspath(target_dir).startswith(os.path.abspath(base_video_dir)):
       return jsonify({'status': 'error', 'message': 'Недопустимый путь целевой директории'}), 400

   if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
       return jsonify({'status': 'error', 'message': 'Целевая директория не существует'}), 404

   item_name = os.path.basename(full_item_path)
   target_path = os.path.join(target_dir, item_name)

   if os.path.dirname(full_item_path) == target_dir:
       return jsonify({'status': 'error', 'message': 'Элемент уже находится в указанной директории'}), 400

   if item_type == 'folder' and os.path.abspath(target_dir).startswith(os.path.abspath(full_item_path)):
       return jsonify({'status': 'error', 'message': 'Нельзя переместить папку в её собственную подпапку'}), 400

   if os.path.exists(target_path):
       return jsonify({'status': 'error', 'message': f'В целевой директории уже существует {"папка" if item_type == "folder" else "файл"} с таким именем'}), 400

   try:
       import shutil
       shutil.move(full_item_path, target_path)
       return jsonify({'status': 'success', 'message': f'{"Папка" if item_type == "folder" else "Файл"} успешно перемещен(а)'})
   except Exception as e:
       current_app.logger.error(f'Ошибка при перемещении {full_item_path} -> {target_path}: {str(e)}')
       return jsonify({'status': 'error', 'message': f'Ошибка при перемещении: {str(e)}'}), 500


@secondary_admin.route('/delete_item', methods=['POST'])
@login_required
def delete_item():
   if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
       return jsonify({"status": "error", "message": "Доступ запрещен"}), 403

   item_type = request.form.get('type')
   path = request.form.get('path')
   
   if not all([item_type, path]):
       return jsonify({'status': 'error', 'message': 'Не указаны необходимые параметры'}), 400

   base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
   full_item_path = os.path.join(base_video_dir, path.strip('/'))

   if not os.path.abspath(full_item_path).startswith(os.path.abspath(base_video_dir)):
       return jsonify({'status': 'error', 'message': 'Недопустимый путь для удаления'}), 400

   if not os.path.exists(full_item_path):
       return jsonify({'status': 'error', 'message': f'{"Папка" if item_type == "folder" else "Файл"} не найден(а)'}), 404

   if (item_type == 'folder' and not os.path.isdir(full_item_path)) or \
      (item_type == 'video' and not os.path.isfile(full_item_path)):
       return jsonify({'status': 'error', 'message': f'Указанный путь не является {"папкой" if item_type == "folder" else "файлом"}'}), 400

   try:
       if item_type == 'folder':
           import shutil
           shutil.rmtree(full_item_path)
       else:
           os.remove(full_item_path)
       return jsonify({'status': 'success', 'message': f'{"Папка" if item_type == "folder" else "Файл"} успешно удален(а)'})
   except Exception as e:
       current_app.logger.error(f'Ошибка при удалении {full_item_path}: {str(e)}')
       return jsonify({'status': 'error', 'message': f'Ошибка при удалении: {str(e)}'}), 500


@secondary_admin.route('/get_folders_list', methods=['GET'])
@login_required
def get_folders_list():
   if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
       return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
   
   base_video_dir = os.path.join(current_app.static_folder, 'video', current_user.database_name)
   
   # Создаем директорию, если она не существует
   if not os.path.exists(base_video_dir):
       try:
           os.makedirs(base_video_dir)
       except Exception as e:
           current_app.logger.error(f'Не удалось создать директорию: {str(e)}')
           return jsonify({'status': 'error', 'message': f'Не удалось создать директорию: {str(e)}'}), 500
   
   folders = ['/']  # Корневая директория

   def scan_folders(dir_path, rel_path=''):
       try:
           for item in os.listdir(dir_path):
               item_path = os.path.join(dir_path, item)
               if os.path.isdir(item_path):
                   item_rel_path = os.path.join(rel_path, item).replace('\\', '/') if rel_path else item
                   folders.append(item_rel_path)
                   scan_folders(item_path, item_rel_path)
       except PermissionError:
           pass

   try:
       scan_folders(base_video_dir)
   except Exception as e:
       current_app.logger.error(f'Ошибка при сканировании папок: {str(e)}')
       return jsonify({'status': 'error', 'message': f'Ошибка при сканировании папок: {str(e)}'}), 500

   return jsonify({'status': 'success', 'folders': folders})