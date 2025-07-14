from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_with_secure_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///profesapp.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


class Config(object):
    pass


db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey('group.id'),
        nullable=False,
    )
    group = db.relationship(
        'Group',
        backref=db.backref('students', lazy=True),
    )


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('student.id'),
        nullable=False,
    )
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    student = db.relationship(
        'Student',
        backref=db.backref('attendances', lazy=True),
    )


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('student.id'),
        nullable=False,
    )
    assignment = db.Column(db.String(120))
    grade = db.Column(
        db.String(20),
    )  # supports qualitative or quantitative
    student = db.relationship(
        'Student',
        backref=db.backref('grades', lazy=True),
    )


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey('group.id'),
        nullable=False,
    )
    name = db.Column(db.String(120))
    filename = db.Column(db.String(120))
    group = db.relationship(
        'Group',
        backref=db.backref('assignments', lazy=True),
    )


def login_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    groups = Group.query.all()
    return render_template('index.html', groups=groups)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return 'User already exists'
        hashed = generate_password_hash(password)
        db.session.add(User(username=username, password_hash=hashed))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return 'Invalid credentials'
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/groups/new', methods=['GET', 'POST'])
@login_required
def new_group():
    if request.method == 'POST':
        name = request.form['name']
        db.session.add(Group(name=name))
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_group.html')


@app.route('/groups/<int:group_id>')
@login_required
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    return render_template('group_detail.html', group=group)


@app.route('/groups/<int:group_id>/students/add', methods=['POST'])
@login_required
def add_student(group_id):
    name = request.form['name']
    db.session.add(Student(name=name, group_id=group_id))
    db.session.commit()
    return redirect(url_for('group_detail', group_id=group_id))


@app.route('/students/<int:student_id>/attendance', methods=['POST'])
@login_required
def mark_attendance(student_id):
    status = request.form['status']
    date = request.form['date']
    db.session.add(
        Attendance(
            student_id=student_id,
            status=status,
            date=date,
        )
    )
    db.session.commit()
    return redirect(
        url_for(
            'group_detail',
            group_id=Student.query.get(student_id).group_id,
        )
    )


@app.route('/students/<int:student_id>/grade', methods=['POST'])
@login_required
def add_grade(student_id):
    assignment = request.form['assignment']
    grade = request.form['grade']
    db.session.add(
        Grade(
            student_id=student_id,
            assignment=assignment,
            grade=grade,
        )
    )
    db.session.commit()
    return redirect(
        url_for(
            'group_detail',
            group_id=Student.query.get(student_id).group_id,
        )
    )


@app.route('/groups/<int:group_id>/assignments', methods=['POST'])
@login_required
def upload_assignment(group_id):
    f = request.files['file']
    filename = f.filename
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(path)
    db.session.add(
        Assignment(
            group_id=group_id,
            name=request.form['name'],
            filename=filename,
        )
    )
    db.session.commit()
    return redirect(url_for('group_detail', group_id=group_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
