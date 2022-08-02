from datetime import datetime
from ext import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))
    institution = db.Column(db.String(255))
    # role


set2user = db.Table('set2user',
                    db.Column('set_id', db.Integer, db.ForeignKey('question_set.id')),
                    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                    db.PrimaryKeyConstraint('set_id', 'user_id'))

set2question = db.Table('set2question',
                        db.Column('set_id', db.Integer, db.ForeignKey('question_set.id')),
                        db.Column('question_id', db.Integer, db.ForeignKey('question.id')),
                        db.PrimaryKeyConstraint('set_id', 'question_id'))


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255))
    content = db.Column(db.String(3000))
    embedding = db.Column(db.JSON)  # 好像实际上存的是 String?
    modified_at = db.Column(db.DateTime, default=datetime.now)
    modified_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    modified_by = db.relationship('User', backref='modified_question', uselist=False, foreign_keys=[modified_by_id])
    belongs = db.relationship('QuestionSet', secondary=set2question, back_populates='questions', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', backref='created_question', uselist=False, foreign_keys=[created_by_id])


class QuestionSet(db.Model):
    # 预计大公共库占用 id=1
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))
    questions = db.relationship('Question', secondary=set2question, back_populates='belongs', lazy='dynamic')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref='own', uselist=False, foreign_keys=[owner_id])
    maintainer = db.relationship('User', secondary=set2user, backref='maintain', lazy='dynamic')
    modified_at = db.Column(db.DateTime, default=datetime.now)
    modified_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    modified_by = db.relationship('User', backref='modified_set', uselist=False, foreign_keys=[modified_by_id])
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', backref='created_set', uselist=False, foreign_keys=[created_by_id])
    # permission
    # passwd


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Public, Protected, Private


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # User, Admin
