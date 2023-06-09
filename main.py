from flask import Flask, redirect, session, request, render_template, make_response, jsonify
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, FieldList, FormField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, InputRequired
from data import db_session, users, groups,  groups_tests, tests, tests_api, test_tasks
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
import datetime
import random
import os
import string
from forms.testgenerate import TestGenerateForm
from forms.taskgenerate import TaskGenerateForm

User = users.User
Group = groups.Group
Test = tests.Tests
Test_task = test_tasks.Test_tasks
GroupTest = tests.Tests
# Question = tests.Question

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
    days=365
)

login_manager = LoginManager()
login_manager.init_app(app)


def generatePasswordToUsers():
    db_sess = db_session.create_session()
    password = ''
    a = string.ascii_lowercase + string.ascii_uppercase + '1234567890'
    for i in range(10):
        password += random.choice(a)
    exist = db_sess.query(User).filter(User.hashed_password == generate_password_hash(password)).first()
    while exist:
        for i in range(10):
            password += random.choice(a)
        exist = db_sess.query(User).filter(User.hashed_password == generate_password_hash(password)).first()
    return password


def generateAccessKey():
    nums = '1234567890'
    key = ''
    for i in range(7):
        key += random.choice(nums)
    return key + random.choice(string.ascii_uppercase)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')
    register_btn = SubmitField('Зарегестрироваться', render_kw={'formnovalidate': True})


class RegisterForm(FlaskForm):
    name = StringField('ФИО', validators=[DataRequired()])
    login = StringField('Введите логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегестрироваться')
    login_btn = SubmitField('Войти', render_kw={'formnovalidate': True})


class B(FlaskForm):
    inits = StringField()


class GroupAppend(FlaskForm):
    initials = FieldList(FormField(B), min_entries=0, label='Введите всех учеников одной группы/класса в формате ФИО')
    login = StringField('Введите логин группы', validators=[DataRequired()])
    name_group = StringField('Введите название группы', validators=[DataRequired()])
    submit = SubmitField('Создать группу')
    count = StringField('Введите количество учеников группы:', validators=[DataRequired()])
    refresh = SubmitField(label='Обновить', render_kw={'formnovalidate': True})


class PreGroupAppend(FlaskForm):
    count = StringField('Введите количество учеников группы:', validators=[DataRequired()])
    refresh = SubmitField(label='Обновить', render_kw={'formnovalidate': True})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.register_btn.data:
        return redirect('/register')
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.login == form.login.data).first()
        if user and check_password_hash(user.hashed_password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            if current_user.teacher:
                return redirect("/listtestst") # редирект на страницу с тестами для учителя
            else:
                return redirect("/listtestss") # редирект на страницу с тестами для ученика (меняется последняя буква)
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/class_generate', methods=['GET', 'POST'])
@login_required
def class_generate():
    global GroupAppend
    db_sess = db_session.create_session()
    form = GroupAppend()
    form1 = PreGroupAppend()
    if form.refresh.data:
        if form.count.data:
            class GroupAppend(FlaskForm):
                initials = FieldList(FormField(B), min_entries=int(form.count.data), max_entries=int(form.count.data),
                                     label='Введите всех учеников одной группы/класса в формате ФИО')
                login = StringField('Введите логин группы', validators=[DataRequired()])
                name_group = StringField('Введите название группы', validators=[DataRequired()])
                submit = SubmitField('Создать группу')
                count = StringField('Введите количество учеников группы:', validators=[DataRequired()])
                refresh = SubmitField(label='Обновить', render_kw={'formnovalidate': True})
            form = GroupAppend()
            return render_template('class_generate.html', title='Создаие группы', form=form)
        else:
            return render_template('preClassGenerate.html', title='Создаие группы', form=form1)
    if request.method == 'POST':
        if form.validate:
            login = db_sess.query(User).filter(User.login == form.login.data).first()
            names_class = db_sess.query(Group.name_group).filter(Group.id_teacher == current_user.id).all()
            if login:
                return render_template('class_generate.html', title='Создаие группы', form=form, message='Логин уже занят')
            for i in names_class:
                if form.name_group.data == i[0]:
                    return render_template('class_generate.html', title='Создаие группы', form=form,
                                            message='Вы уже создавали группу с таким наименованием')
            listOfPasswords = []
            trueInits = []
            u = []
            key = generateAccessKey()
            for i in form.initials.data:
                name = i['inits'].strip()
                if i['inits'] != '':
                    password = generatePasswordToUsers()
                    listOfPasswords.append((name, password))
                    user = User()
                    user.initials = name
                    user.hashed_password = generate_password_hash(password)
                    user.teacher = False
                    user.login = form.login.data
                    user.hashed_key_access = None
                    if listOfPasswords:
                        for j in listOfPasswords:
                            if len(j[0].split()) != 3:
                                return render_template('class_generate.html', title='Создаие группы', form=form,
                                                       message='ФИО введнеы неккоректно')
                    u.append(user)

            for i in u:
                db_sess.add(i)
                db_sess.commit()
            group = Group()
            group.login_group = form.login.data
            group.name_group = form.name_group.data
            group.id_teacher = current_user.id
            group.hashed_key_access = generate_password_hash(key)
            group.creator = True
            db_sess = db_session.create_session()
            db_sess.add(group)
            db_sess.commit()
            if len(listOfPasswords) % 3 == 1:
                for i in range(2):
                    listOfPasswords.append(('', ''))
            elif len(listOfPasswords) % 3 == 2:
                listOfPasswords.append(('', ''))
            session['last_login_added'] = listOfPasswords
            session['key_access'] = key
            return redirect('/password_list')
        else:
            print(listOfPasswords)
            return render_template('class_generate.html', title='Создаие группы', form=form,
                            message='Не было введено ни одного инициала')
    return render_template('preClassGenerate.html', title='Создаие группы', form=form1)


@app.route('/listtestst', methods=['GET', 'POST'])
@login_required
def listtestst():
    if current_user.teacher:
        list_tests = []
        db_sess = db_session.create_session()
        allTests = db_sess.query(GroupTest).filter(GroupTest.id_teacher == current_user.id).all()
        return render_template('teacher_home.html', title='Ваши тесты', quantity=len(allTests), allTests=allTests)
    else:
        return 'access denied'


@app.route('/listtestss', methods=['GET', 'POST'])
@login_required
def listtestss():
    if current_user.teacher:
        return 'access denied'
    else:
        return 'now u are student'


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.login_btn.data:
        return redirect('/login')
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if form.password.data == form.confirm_password.data:
            user = User()
            user.initials = form.name.data
            user.hashed_password = generate_password_hash(form.password.data)
            user.teacher = True
            user.login = form.login.data
            user.hashed_key_access = None
            db_sess = db_session.create_session()
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
        else:
            return render_template('register_form.html',
                                   message="Пароли не совпадают",
                                   form=form)
    return render_template('register_form.html', title='Регистрация', form=form)


@app.route('/password_list', methods=['GET', 'POST'])
@login_required
def passList():
    return render_template('passwordsList.html', title='Парооли для группы', list=session['last_login_added'],
                           len=len(session['last_login_added']), key=session['key_access'])


@app.route('/')
def home():
    return redirect('/login')



@app.route('/generate_tests',  methods=['GET', 'POST'])
def generate_tests():
    if current_user.teacher:
        form = TestGenerateForm()
        if form.go_out_btn.data:
            return redirect('/listtestst')
        if request.method == 'POST':
            if request.form['do_test'] == 'Создать тест':
                if form.validate:
                    db_sess = db_session.create_session()
                    groups = db_sess.query(Group).filter(Group.id_teacher == current_user.id)
                    if len(list(groups)):
                        groups_names = list(map(lambda x: x.name_group, groups))
                        if form.to_who.data not in groups_names:
                             return render_template('generate_tests.html', title='Создание тестов', form=form,
                                                     message=f'У вас нет группы с названием {form.to_who.data}', pos='1')
                        if form.count.data is None:
                            return render_template('generate_tests.html', title='Создание тестов', form=form,
                                                   message=f'Не верный тип данных. Должно быть целое число.', pos='2')
                        elif form.count.data < 1:
                            return render_template('generate_tests.html', title='Создание тестов', form=form,
                                            message=f'Количество заданий должно быть больше нуля', pos='2')
                        elif form.count.data > 100:
                            return render_template('generate_tests.html', title='Создание тестов', form=form,
                                            message=f'Количество заданий должно быть меньше сотни', pos='2')

                        if form.time_to_test.data is None:
                            return render_template('generate_tests.html', title='Создание тестов', form=form,
                                                       message=f'Не верный тип данных. Должно быть целое число.',
                                                       pos='3')
                        elif form.time_to_test.data < 1:
                            return render_template('generate_tests.html', title='Создание тестов', form=form,
                                                       message=f'Время на тест должно быть больше нуля', pos='3')
                        test = Test()
                        test.name = form.name.data
                        test.id_teacher = current_user.id
                        test.questions = form.count.data
                        test.time_test = (':').join((str(form.time_to_test.data), str(form.ed_izm.data)))
                        test.test_redacting = True
                        test.is_published = False
                        db_sess = db_session.create_session()
                        db_sess.add(test)
                        db_sess.commit()
                        what_test = max(list(map(lambda x: x.id, db_sess.query(Test).filter(
                            Test.name == form.name.data))))
                        db_sess.close()
                        return redirect(f'/generate_tasks/{what_test}')
                    else:
                        return render_template('generate_tests.html', title='Создание тестов',
                                               form=form, message='У вас нет групп', pos='1')
        return render_template('generate_tests.html', title='Создание тестов', form=form, pos='0')
    else:
        return 'access denied'


@app.route('/generate_tasks/<int:id>',  methods=['GET', 'POST'])
def generate_tasks(id):
    if current_user.teacher:
        db_sess = db_session.create_session()
        what_test = db_sess.query(Test).filter(Test.id == id).first()
        if what_test.is_published:
            return 'access denied'
        id_what_test = what_test.id
        count = what_test.questions
        form = TaskGenerateForm()
        nums = [i for i in range(count)]
        if request.method == 'POST':
            if form.do_test_task.data:
                if form.validate_on_submit:
                    for task in range(count):
                        f_task = form.tasks_list[task]
                        cond = any(list(map(lambda x: len(x.strip('\r').strip()), f_task.condition.data.split('\n'))))
                        true_answ = len(f_task.true_answer.data.strip('\r').strip())
                        if not(cond) or not(true_answ):
                            return render_template('tasks_generate.html', title='Создание заданий тестов', form=form, nums=nums, message='Не все поля заполнены', pos='1')
                        if f_task.cost.data is None:
                            return render_template('tasks_generate.html', title='Создание заданий тестов', form=form,
                                                   nums=nums, message='Не тот тип данных для поля количество баллов', pos='1')
                        elif 0 >= f_task.cost.data:
                            return render_template('tasks_generate.html', title='Создание заданий тестов', form=form,
                                                   nums=nums, message='количество баллов должно быть больше нуля',
                                                   pos='1')
                    for task_num in range(count):
                        db_sess = db_session.create_session()
                        old_task = db_sess.query(Test_task).filter(what_test.id == Test_task.id_test,
                                                                   task_num + 1 == Test_task.num_in_test).first()
                        if old_task:
                            f_task = form.tasks_list[task_num]
                            old_task.id_test = id_what_test
                            old_task.question = f_task.condition.data
                            if f_task.type_answer.data == 1:
                                old_task.answers = 0
                                old_task.type_answer = 1
                            else:
                                old_task.answers = ('@').join(list(map(lambda x: x.answer.data, f_task.answers)))
                                old_task.type_answer = f_task.type_answer.data
                            old_task.true_answer = f_task.true_answer.data
                            old_task.cost = f_task.cost.data
                            old_task.num_in_test = task_num + 1
                            db_sess.commit()
                        else:
                            f_task = form.tasks_list[task_num]
                            task = Test_task()
                            task.id_test = id_what_test
                            task.question = f_task.condition.data
                            if f_task.type_answer.data == 1:
                                task.answers = 0
                                task.type_answer = 1
                            else:
                                task.answers = ('@').join(list(map(lambda x: x.answer.data, f_task.answers)))
                                task.type_answer = f_task.type_answer.data
                            task.true_answer = f_task.true_answer.data
                            task.cost = f_task.cost.data
                            task.num_in_test = task_num + 1
                            db_sess = db_session.create_session()
                            db_sess.add(task)
                            db_sess.commit()
            if form.task_reset.data:
                pass
        return render_template('tasks_generate.html', title='Создание заданий тестов', form=form, nums=nums)
    else:
        return 'access denied'

def main():
    db_session.global_init("db/tests.db")
    app.register_blueprint(tests_api.blueprint)
    app.run()

    # port = int(os.environ.get("PORT", 5000))
    # app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
