from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from PIL import Image
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'books.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

UPLOAD_FOLDER = os.path.join(basedir, 'static', 'book_images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    books = db.relationship('Book', backref='owner', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender_rel', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver_rel', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150))
    edition = db.Column(db.String(100))
    condition = db.Column(db.Integer)
    price = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=True)
    campus = db.Column(db.String(100))
    contact = db.Column(db.String(100))
    email = db.Column(db.String(120), nullable=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    language = db.Column(db.String(50))
    listing_type = db.Column(db.String(10))
    sold = db.Column(db.Boolean, default=False)
    posted_by = db.Column(db.String(80), db.ForeignKey('user.username'))
    image_filename = db.Column(db.String(255))
    payment_qr = db.Column(db.String(255), nullable=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/')
def home_redirect():
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    lang = request.args.get('lang', 'English')
    return render_template('welcome.html', lang=lang)

@app.route('/books')
def available_books():
    if 'username' not in session:
        return redirect(url_for('welcome'))
    lang = request.args.get('lang', 'English')
    search_query = request.args.get('search')
    query = Book.query.filter(Book.sold == False)
    if search_query:
        query = query.filter(
            Book.title.contains(search_query) |
            Book.author.contains(search_query) |
            Book.isbn.contains(search_query)
        )
    books = query.all()
    return render_template('index.html', books=books, lang=lang)

@app.route('/post_book', methods=['GET', 'POST'])
def post_book():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        edition = request.form.get('edition')
        condition = request.form.get('condition')
        price = request.form.get('price')
        description = request.form.get('description')
        campus = request.form.get('campus')
        contact = request.form.get('contact')
        email = request.form.get('email')
        isbn = request.form.get('isbn')
        language = request.form.get('language')
        listing_type = request.form.get('listing_type')

        image = request.files.get('book_image')
        image_filename = None
        qr_filename = None

        if image and image.filename != '':
            image_filename = f"{isbn}.jpg"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        qr = request.files.get('payment_qr')
        if qr and qr.filename != '':
            qr_filename = f"{isbn}_qr.jpg"
            qr.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_filename))

        new_book = Book(
            title=title,
            author=author,
            edition=edition,
            condition=condition,
            price=price,
            description=description,
            campus=campus,
            contact=contact,
            email=email,
            isbn=isbn,
            language=language,
            listing_type=listing_type,
            posted_by=session['username'],
            image_filename=image_filename,
            payment_qr=qr_filename
        )

        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('available_books'))

    lang = request.args.get('lang', 'English')
    return render_template('post_book.html', lang=lang)

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    book = Book.query.get_or_404(book_id)
    if book.posted_by != session['username']:
        return "Access Denied", 403
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.edition = request.form.get('edition')
        book.condition = request.form.get('condition')
        book.price = request.form.get('price')
        book.description = request.form.get('description')
        book.campus = request.form.get('campus')
        book.contact = request.form.get('contact')
        book.email = request.form.get('email')
        book.isbn = request.form.get('isbn')
        book.language = request.form.get('language')
        book.listing_type = request.form.get('listing_type')
        book.sold = True if request.form.get('sold') else False

        image = request.files.get('book_image')
        if image and image.filename != '':
            image_filename = f"{book.isbn}.jpg"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            book.image_filename = image_filename

        qr = request.files.get('payment_qr')
        if qr and qr.filename != '':
            qr_filename = f"{book.isbn}_qr.jpg"
            qr.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_filename))
            book.payment_qr = qr_filename

        db.session.commit()
        return redirect(url_for('available_books'))

    lang = request.args.get('lang', 'English')
    return render_template('edit_book.html', book=book, lang=lang)

@app.route('/delete_book/<int:book_id>')
def delete_book(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    book = Book.query.get_or_404(book_id)
    if book.posted_by != session['username']:
        return "Access Denied", 403
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    my_books = Book.query.filter_by(posted_by=session['username']).all()
    messages = Message.query.filter_by(receiver_id=user.id).all()
    return render_template('profile.html', user=user, books=my_books, messages=messages, lang=request.args.get('lang', 'English'))

@app.route('/message/<string:to_username>', methods=['GET', 'POST'])
def send_message(to_username):
    if 'username' not in session:
        return redirect(url_for('login'))
    sender = User.query.filter_by(username=session['username']).first()
    receiver = User.query.filter_by(username=to_username).first()
    if not receiver:
        return "User not found", 404
    if request.method == 'POST':
        content = request.form.get('content')
        msg = Message(content=content, sender_id=sender.id, receiver_id=receiver.id)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('available_books'))
    return render_template('send_message.html', to=receiver.username)

@app.route('/i_want_this/<int:book_id>')
def i_want_this(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    book = Book.query.get_or_404(book_id)
    seller = User.query.filter_by(username=book.posted_by).first()
    buyer = User.query.filter_by(username=session['username']).first()

    msg = Message(
        content=f"Buyer '{buyer.username}' is interested in your book: {book.title}",
        sender_id=buyer.id,
        receiver_id=seller.id
    )
    db.session.add(msg)
    db.session.commit()
    return redirect(url_for('available_books'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('available_books'))
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not password or len(password) < 8:
            return "Password must be at least 8 characters"
        if User.query.filter_by(username=username).first():
            return "Username already taken"
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('available_books'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('welcome'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
@app.route('/book/<int:book_id>/purchase')
def purchase_book(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    book = Book.query.get_or_404(book_id)
    return render_template('purchase.html', book=book)
@app.route('/i_want_this/<int:book_id>')
def i_want_this(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    book = Book.query.get_or_404(book_id)
    seller = User.query.filter_by(username=book.posted_by).first()
    buyer = User.query.filter_by(username=session['username']).first()

    message = Message(
        content=f"Buyer '{buyer.username}' is interested in your book: {book.title}",
        sender_id=buyer.id,
        receiver_id=seller.id
    )
    db.session.add(message)
    db.session.commit()

    return redirect(url_for('purchase_book', book_id=book.id))
