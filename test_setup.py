from app import app, db, Book, User, bcrypt

with app.app_context():
    # Create test user if doesn't exist
    test_user = User.query.filter_by(username="testuser").first()
    if not test_user:
        hashed_pw = bcrypt.generate_password_hash("testpass123").decode('utf-8')
        test_user = User(username="testuser", password=hashed_pw)
        db.session.add(test_user)
        db.session.commit()

    # Create test book if doesn't exist
    test_book = Book.query.filter_by(isbn="9780123456789").first()
    if not test_book:
        test_book = Book(
            title="Test Book",
            author="Test Author",
            edition="First Edition",
            condition=5,
            price="50",
            description="A test book for purchase flow testing",
            campus="Main Campus",
            contact="123-456-7890",
            email="test@example.com",
            isbn="9780123456789",
            language="English",
            listing_type="sell",
            posted_by="testuser",
            image_filename=None,
            payment_qr=None
        )
        db.session.add(test_book)
        db.session.commit()
        print("Test book created successfully!")
    else:
        print("Test book already exists!") 