from flask_login import UserMixin
from sqlalchemy.orm import relationship
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from datetime import datetime
from apps import db, login_manager
from apps.authentication.util import hash_pass, verify_pass

class Users(db.Model, UserMixin):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.LargeBinary)
    oauth_github = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    address = db.Column(db.String(128), nullable=True)
    city = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(64), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    about_me = db.Column(db.Text, nullable=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            if property == 'password':
                value = hash_pass(value)  # Use hash_pass from util.py
            setattr(self, property, value)

    def check_password(self, password):
        return verify_pass(password, self.password)  # Use verify_pass from util.py
    
    def __repr__(self):
        return str(self.username)


class Videos(db.Model):
    __tablename__ = 'Videos'

    id = db.Column(db.Integer, primary_key=True)
    video_name = db.Column(db.String(128), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    trimmed_file_name = db.Column(db.String(128), nullable=True)
    process_time = db.Column(db.Time, default=datetime.utcnow().time)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)

    user = db.relationship('Users', backref=db.backref('videos', lazy=True))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)
    
    def __repr__(self):
        return f"<Video {self.video_name}>"


class Audios(db.Model):
    __tablename__ = 'Audios'

    id = db.Column(db.Integer, primary_key=True)
    audio_name = db.Column(db.String(128), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    trimmed_file_name = db.Column(db.String(128), nullable=True)
    process_time = db.Column(db.Time, default=datetime.utcnow().time)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)

    user = db.relationship('Users', backref=db.backref('audios', lazy=True))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)

    def __repr__(self):
        return f"<Audio {self.audio_name}>"


class Process(db.Model):
    __tablename__ = 'Process'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('Videos.id'), nullable=True)
    audio_id = db.Column(db.Integer, db.ForeignKey('Audios.id'), nullable=True)
    audio_name = db.Column(db.String(128), nullable=True)
    video_name = db.Column(db.String(128), nullable=True)
    process_id = db.Column(db.String(64), unique=True, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True) 
    status = db.Column(db.String(32), nullable=False, default='pending')

    user = db.relationship('Users', backref=db.backref('processes', lazy=True))
    video = db.relationship('Videos', backref=db.backref('processes', lazy=True))
    audio = db.relationship('Audios', backref=db.backref('processes', lazy=True))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            setattr(self, property, value)

    def __repr__(self):
        return f"<Process {self.process_id} for User {self.user_id}>"



class Feedback(db.Model):
    __tablename__ = 'Feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('Videos.id'), nullable=True)  # Optional if feedback can be on videos
    audio_id = db.Column(db.Integer, db.ForeignKey('Audios.id'), nullable=True)    # Optional if feedback can be on audios
    feedback_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # For example, 1-5 stars
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('Users', backref=db.backref('feedbacks', lazy=True))
    video = db.relationship('Videos', backref=db.backref('feedbacks', lazy=True), foreign_keys=[video_id])
    audio = db.relationship('Audios', backref=db.backref('feedbacks', lazy=True), foreign_keys=[audio_id])

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            setattr(self, property, value)

    def __repr__(self):
        return f"<Feedback {self.id} from User {self.user_id}>"


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("Users.id", ondelete="cascade"), nullable=False)
    user = db.relationship(Users)
