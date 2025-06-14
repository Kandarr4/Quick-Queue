# app/secondary_admin/users.py
from flask import render_template, url_for, jsonify, request, flash, redirect
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import exc

from app.db_manager import get_current_db
from app.models.secondary_admin import User
from app.forms import UserForm
from . import secondary_admin

@secondary_admin.route('/add-user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')
        cabinet = request.form.get('cabinet', '')

        if not username or not password or not role:
            error_message = 'Все поля обязательны для заполнения'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': error_message}), 400
            else:
                flash(error_message, 'danger')
                return redirect(url_for('secondary_admin.dashboard'))

        existing_user = org_db.query(User).filter_by(username=username).first()
        if existing_user:
            error_message = f'Пользователь с именем "{username}" уже существует. Выберите другое имя.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': error_message}), 400
            else:
                flash(error_message, 'danger')
                return redirect(url_for('secondary_admin.dashboard'))

        try:
            new_user = User(
                username=username,
                role=role,
                cabinet=cabinet if cabinet else None
            )
            new_user.set_password(password)
            org_db.add(new_user)
            org_db.commit()

            success_message = f'Пользователь "{username}" успешно добавлен'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'success',
                    'message': success_message,
                    'user': {
                        'id': new_user.id,
                        'username': new_user.username,
                        'role': new_user.role,
                        'cabinet': new_user.cabinet
                    }
                })
            else:
                flash(success_message, 'success')
                return redirect(url_for('secondary_admin.dashboard'))
        except exc.IntegrityError:
            org_db.rollback()
            error_message = f'Ошибка при добавлении пользователя "{username}". Возможно, пользователь с таким именем уже существует.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': error_message}), 400
            else:
                flash(error_message, 'danger')
                return redirect(url_for('secondary_admin.dashboard'))
        except Exception as e:
            org_db.rollback()
            error_message = f'Произошла неожиданная ошибка при добавлении пользователя: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': error_message}), 500
            else:
                flash(error_message, 'danger')
                return redirect(url_for('secondary_admin.dashboard'))

    form = UserForm()
    return render_template('secondary_admin/add_user.html', form=form)

@secondary_admin.route('/edit-user/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500

    user = org_db.query(User).get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'Пользователь не найден'}), 404
        
    data = request.get_json()

    # Проверяем, не занято ли имя пользователя другим пользователем
    existing_user = org_db.query(User).filter(User.username == data['username'], User.id != user_id).first()
    if existing_user:
        return jsonify({'status': 'error', 'message': 'Пользователь с таким именем уже существует.'}), 400

    try:
        user.username = data['username']
        user.role = data['role']
        user.cabinet = data['cabinet']
        
        if data.get('password'):
            user.set_password(data['password'])
            
        if 'video' in data:
            user.video = data['video']
            
        org_db.commit()
        return jsonify({'status': 'success', 'message': 'Пользователь успешно обновлен'})
    except exc.IntegrityError:
        org_db.rollback()
        return jsonify({'status': 'error', 'message': 'Ошибка сохранения данных.'}), 400
    except Exception as e:
        org_db.rollback()
        return jsonify({'status': 'error', 'message': f'Произошла ошибка: {str(e)}'}), 500

@secondary_admin.route('/change-password', methods=['POST'])
@login_required
def change_password():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500

    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')
    confirm_new_password = data.get('confirm_new_password')

    if new_password != confirm_new_password:
        return jsonify({'status': 'error', 'message': 'Новый пароль и подтверждение пароля не совпадают.'}), 400

    user = org_db.query(User).get(user_id)
    if user:
        user.set_password(new_password)
        org_db.commit()
        return jsonify({'status': 'success', 'message': 'Пароль успешно изменен'})
    else:
        return jsonify({'status': 'error', 'message': 'Пользователь не найден.'}), 400

@secondary_admin.route('/assign-role/<int:user_id>', methods=['POST'])
@login_required
def assign_role(user_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    data = request.get_json()
    role = data['role']
    user = org_db.query(User).get(user_id)
    
    if not user:
        return jsonify({'status': 'error', 'message': 'Пользователь не найден.'}), 404
        
    if role:
        user.role = role
        org_db.commit()
        return jsonify({'message': 'Роль успешно назначена.'})
    return jsonify({'message': 'Ошибка при назначении роли.'}), 400

@secondary_admin.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    user = org_db.query(User).get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'Пользователь не найден.'}), 404
        
    try:
        org_db.delete(user)
        org_db.commit()
        return jsonify({'status': 'success', 'message': 'Пользователь был успешно удален.'})
    except Exception as e:
        org_db.rollback()
        return jsonify({'status': 'error', 'message': f'Ошибка при удалении пользователя: {str(e)}'}), 500