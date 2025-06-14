# app/secondary_admin/groups.py
import os
import json
from flask import jsonify, request, g, current_app
from flask_login import login_required, current_user

from . import secondary_admin
from app.db_manager import get_current_db

def load_groups(database_name=None):
    """
    Загружает группы из JSON файла для конкретной организации
    
    Args:
        database_name (str, optional): Имя базы данных организации. Если не указано, 
                                    используется база данных текущего пользователя.
    
    Returns:
        list: Список групп
    """
    if database_name is None and hasattr(current_user, 'database_name'):
        database_name = current_user.database_name
    
    if database_name:
        groups_file = os.path.join(current_app.config['DB_FOLDER'], f"{database_name}_groups.json")
    else:
        groups_file = 'groups.json'
        
    if not os.path.exists(groups_file):
        return []
        
    with open(groups_file, 'r') as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []

@secondary_admin.route('/save_group', methods=['POST'])
@login_required
def save_group():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    group_data = request.json
    groups_file = os.path.join(current_app.config['DB_FOLDER'], f"{current_user.database_name}_groups.json")
    
    if not os.path.exists(groups_file):
        with open(groups_file, 'w') as file:
            json.dump([], file)

    with open(groups_file, 'r+') as file:
        try:
            groups = json.load(file)
        except json.JSONDecodeError:
            groups = []
        groups.append(group_data)
        file.seek(0)
        file.truncate()
        json.dump(groups, file, indent=4)

    return jsonify({"status": "success"})

@secondary_admin.route('/delete_group', methods=['POST'])
@login_required
def delete_group():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    group_id = request.json.get('group_id')
    groups_file = os.path.join(current_app.config['DB_FOLDER'], f"{current_user.database_name}_groups.json")
    
    groups = load_groups(current_user.database_name)
    if group_id is not None and group_id < len(groups):
        del groups[group_id]
        with open(groups_file, 'w') as file:
            json.dump(groups, file, indent=4)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Группа не найдена"}), 400