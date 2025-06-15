# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, HiddenField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from datetime import datetime, timedelta
from flask import g

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=55)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
    
class ServiceForm(FlaskForm):
    name = StringField('Название услуги', validators=[DataRequired()])
    start_number = IntegerField('Начальный номер', validators=[DataRequired()])
    end_number = IntegerField('Конечный номер', validators=[DataRequired()])
    cabinet = StringField('Номер кабинета', validators=[Optional()])
    submit = SubmitField('Сохранить изменения')
   
class ServiceSelectForm(FlaskForm):
    service = SelectField('Service', coerce=int)
    submit = SubmitField('Get Ticket')

    def __init__(self, *args, **kwargs):
        super(ServiceSelectForm, self).__init__(*args, **kwargs)
        # Заполняем choices динамически из текущей БД, если она доступна
        from app.db_manager import get_current_db
        from app.models.secondary_admin import Service
        
        org_db = get_current_db()
        if org_db:
            self.service.choices = [(service.id, service.name) for service in org_db.query(Service).all()]
        else:
            self.service.choices = []
        
class AssignServiceForm(FlaskForm):
    user_id = SelectField('Пользователь', coerce=int, validators=[DataRequired()])
    service_id = SelectField('Услуга', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Назначить')

    # Не заполняем choices при инициализации - это будет делаться в представлении

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password')
    role = SelectField('Role', choices=[
        ('main_admin', 'Main Admin'),
        ('secondary_admin', 'Secondary Admin')
    ])
    submit = SubmitField('Add User')
    
    def validate_username(self, username):
        from app.models.models_app import Admin
        admin = Admin.query.filter_by(username=username.data).first()
        if admin:
            raise ValidationError('Этот логин уже занят. Пожалуйста, выберите другой.')
    
class UserForm(FlaskForm):
    user_id = HiddenField('user_id')
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Пароль', validators=[Optional()])
    marquee_text = TextAreaField('Текст бегущей строки', validators=[Optional()])
    cabinet = StringField('Cabinet', validators=[Optional()])

    role = SelectField('Роль', choices=[
        ('admin', 'Администратор'),
        ('user', 'Пользователь'),
        ('tablo', 'Табло'),
        ('terminal', 'Терминал')
    ])
    video = StringField('Настройки видео', validators=[Optional()])
    style_type = SelectField('Стиль интерфейса', choices=[
        ('default', 'Стандартный'),
        ('custom', 'Кастомный')
    ], validators=[DataRequired()])
    submit = SubmitField('Добавить пользователя')
    
    def validate_username(self, username):
        if not self.user_id.data:  # Только для новых пользователей
            from app.db_manager import get_current_db
            from app.models.secondary_admin import User
            
            org_db = get_current_db()
            if org_db:
                existing_user = org_db.query(User).filter_by(username=username.data).first()
                if existing_user:
                    raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')
    
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Старый пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), EqualTo('confirm_new_password', message='Пароли должны совпадать')])
    confirm_new_password = PasswordField('Подтвердите новый пароль', validators=[DataRequired()])
    submit = SubmitField('Изменить пароль')
    
class AssignRoleForm(FlaskForm):
    role = SelectField('Роль', choices=[
        ('admin', 'Администратор'),
        ('user', 'Пользователь'),
        ('tablo', 'Табло'),
        ('terminal', 'Терминал')
    ], validators=[DataRequired()])
    submit = SubmitField('Назначить роль')

class DisplaySettingsForm(FlaskForm):
    columns = SelectField('Columns', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')], validators=[DataRequired()])
    rows = SelectField('Rows', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], validators=[DataRequired()])
    background_color = StringField('Background Color', validators=[DataRequired()], default="#FFFFFF")
    text_color = StringField('Text Color', validators=[DataRequired()], default="#000000")
    refresh_rate = SelectField('Refresh Rate', choices=[('5', '5 seconds'), ('10', '10 seconds'), ('30', '30 seconds'), ('60', '1 minute')], validators=[DataRequired()])
    display_info = SelectField('Display Information', choices=[('number', 'Ticket Number'), ('service', 'Service Name'), ('both', 'Ticket Number and Service Name')], validators=[DataRequired()])
    queue_movement = SelectField('Queue Movement', choices=[('static', 'Static'), ('dynamic', 'Dynamic')], validators=[DataRequired()])
    submit = SubmitField('Save Settings')

class SecondaryAdminForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), EqualTo('confirm_password', message='Пароли должны совпадать')])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired()])
    organization_name = StringField('Название организации', validators=[DataRequired()])
    organization_address = StringField('Адрес организации', validators=[Optional()])
    additional_info = TextAreaField('Дополнительная информация', validators=[Optional()])
    access_expiry_date = DateField('Дата обнуления доступа', validators=[Optional()], default=(datetime.now() + timedelta(days=365)).date())
    submit = SubmitField('Создать администратора организации')
    
    def validate_username(self, username):
        from app.models.models_app import Admin
        admin = Admin.query.filter_by(username=username.data).first()
        if admin:
            raise ValidationError('Этот логин уже занят. Пожалуйста, выберите другой.')
        
class DisplaySettingsForm(FlaskForm):
    columns = SelectField('Columns', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')], validators=[DataRequired()])
    rows = SelectField('Rows', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], validators=[DataRequired()])
    background_color = StringField('Background Color', validators=[DataRequired()], default="#FFFFFF")
    text_color = StringField('Text Color', validators=[DataRequired()], default="#000000")
    refresh_rate = SelectField('Refresh Rate', choices=[('5', '5 seconds'), ('10', '10 seconds'), ('30', '30 seconds'), ('60', '1 minute')], validators=[DataRequired()])
    display_info = SelectField('Display Information', choices=[('number', 'Ticket Number'), ('service', 'Service Name'), ('both', 'Ticket Number and Service Name')], validators=[DataRequired()])
    queue_movement = SelectField('Queue Movement', choices=[('static', 'Static'), ('dynamic', 'Dynamic')], validators=[DataRequired()])
    submit = SubmitField('Save Settings')

class UserStyleSettingsForm(FlaskForm):
    """Форма для настройки стилей пользователей организации"""
    admin_style = SelectField('Стиль для Администраторов', choices=[
        ('default', 'Стандартный'),
        ('custom', 'Кастомный')
    ], validators=[DataRequired()])
    user_style = SelectField('Стиль для Пользователей', choices=[
        ('default', 'Стандартный'),
        ('custom', 'Кастомный')
    ], validators=[DataRequired()])
    tablo_style = SelectField('Стиль для Табло', choices=[
        ('default', 'Стандартный'),
        ('custom', 'Кастомный')
    ], validators=[DataRequired()])
    terminal_style = SelectField('Стиль для Терминалов', choices=[
        ('default', 'Стандартный'),
        ('custom', 'Кастомный')
    ], validators=[DataRequired()])
    submit = SubmitField('Сохранить настройки стилей')

