from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from PIL import Image

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


# --- Models ---
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
    condition = db.Column(db.Integer)  # percentage
    price = db.Column(db.String(50))   # in RMB
    description = db.Column(db.Text, nullable=True)
    campus = db.Column(db.String(100))
    contact = db.Column(db.String(100))  # WeChat/QQ
    email = db.Column(db.String(120), nullable=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    language = db.Column(db.String(50))  # English / Chinese
    listing_type = db.Column(db.String(10))  # sell / free
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
    session['lang'] = lang  # Store language in session
    return render_template('welcome.html', lang=lang)


@app.route('/books')
def available_books():
    if 'username' not in session:
        return redirect(url_for('welcome'))
    # Get language from session or URL parameter
    lang = session.get('lang', request.args.get('lang', 'English'))
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
        qr = request.files.get('payment_qr')

        image_filename = None
        qr_filename = None

        if image and image.filename != '':
            image_filename = f"{isbn}.jpg"
            try:
                img = Image.open(image)
                img.thumbnail((120, 120))
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            except Exception as e:
                print("Image processing failed:", str(e))
                return "Error processing image", 500

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
        # Validate inputs
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        condition = request.form.get('condition', '').strip()
        price = request.form.get('price', '').strip()
        listing_type = request.form.get('listing_type', '').strip()

        # Basic validation
        if not title or not author or not isbn:
            flash('Title, Author, and ISBN are required', 'error')
            return render_template('edit_book.html', book=book)

        # Validate condition as integer between 0-100
        try:
            condition = int(condition)
            if condition < 0 or condition > 100:
                raise ValueError()
        except ValueError:
            flash('Condition must be a number between 0 and 100', 'error')
            return render_template('edit_book.html', book=book)

        # Validate listing type
        if listing_type not in ['sell', 'free']:
            flash('Listing type must be either "sell" or "free"', 'error')
            return render_template('edit_book.html', book=book)

        # Check for duplicate ISBN (excluding current book)
        existing_book = Book.query.filter(Book.isbn == isbn, Book.id != book_id).first()
        if existing_book:
            flash('ISBN already exists for another book', 'error')
            return render_template('edit_book.html', book=book)

        # Update book details
        book.title = title
        book.author = author
        book.edition = request.form.get('edition', '').strip()
        book.condition = condition  # Using validated integer
        book.price = price
        book.description = request.form.get('description', '').strip()
        book.campus = request.form.get('campus', '').strip()
        book.contact = request.form.get('contact', '').strip()
        book.email = request.form.get('email', '').strip()
        book.isbn = isbn
        book.language = request.form.get('language', 'English')
        book.listing_type = listing_type
        book.sold = bool(request.form.get('sold'))

        # Handle book image upload
        image = request.files.get('book_image')
        if image and image.filename:
            try:
                # Validate image file
                img = Image.open(image)
                img.verify()  # Verify that it's a valid image
                
                # Resize and save
                img = Image.open(image)
                img.thumbnail((120, 120))
                image_filename = f"{book.isbn}.jpg"
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                book.image_filename = image_filename
            except Exception as e:
                flash(f'Error processing book image: {str(e)}', 'error')
                # Optionally, you can choose to not update the image if there's an error

        # Handle payment QR code upload
        qr = request.files.get('payment_qr')
        if qr and qr.filename:
            try:
                qr_filename = f"{book.isbn}_qr.jpg"
                qr.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_filename))
                book.payment_qr = qr_filename
            except Exception as e:
                flash(f'Error saving payment QR code: {str(e)}', 'error')

        try:
            db.session.commit()
            flash('Book updated successfully', 'success')
            return redirect(url_for('available_books'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating book: {str(e)}', 'error')
            return render_template('edit_book.html', book=book)

    return render_template('edit_book.html', book=book)


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
    user = User.query.filter_by(username=session['username']).first()
    my_books = Book.query.filter_by(posted_by=session['username']).all()
    messages = Message.query.filter_by(receiver_id=user.id).all()
    # Get language from session or URL parameter
    lang = session.get('lang', request.args.get('lang', 'English'))
    return render_template('profile.html', user=user, books=my_books, messages=messages, lang=lang)


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

    message = Message(
        content=f"Buyer '{buyer.username}' is interested in your book: {book.title}",
        sender_id=buyer.id,
        receiver_id=seller.id
    )

    db.session.add(message)
    db.session.commit()
    return redirect(url_for('purchase_book', book_id=book.id))


@app.route('/book/<int:book_id>/purchase')
def purchase_book(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    book = Book.query.get_or_404(book_id)
    return render_template('purchase.html', book=book)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('available_books'))
        else:
            error = "Invalid username or password"
            # Return the template with error message instead of redirecting
            lang = session.get('lang', request.args.get('lang', 'English'))
            return render_template('login.html', error=error, lang=lang)

    # Get language from session or URL parameter
    lang = session.get('lang', request.args.get('lang', 'English'))
    return render_template('login.html', error=error, lang=lang)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    username = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not password or len(password) < 8:
            error = "Password must be at least 8 characters"
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                error = "Username already exists"
            else:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                new_user = User(username=username, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login'))

    lang = session.get('lang', request.args.get('lang', 'English'))
    return render_template('register.html', error=error, lang=lang, username=username)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('welcome'))


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)