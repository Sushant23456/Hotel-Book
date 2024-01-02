import bcrypt
from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user, LoginManager, login_user, logout_user
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import BadSignature, URLSafeTimedSerializer, SignatureExpired
import mysql.connector
from mysql.connector import Error
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from flask_mail import Message
from io import BytesIO
import random
import os
import re


app = Flask(__name__)
app.config['SECRET_KEY'] = b'\xd0\x14\x95\xacZ\xb6h\x95\x854f.\x0cPE(u\xd7\xc5\xdb\xc9\xbf\x1d\xd5'
app.debug = True

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sandpbooking@gmail.com'
app.config['MAIL_PASSWORD'] = 'lpdx xmxb rbtn pmvd'
app.config['MAIL_DEFAULT_SENDER'] = 'sandpbooking@gmail.com'

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'hotel_users_data'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            user=app.config['MYSQL_DATABASE_USER'],
            password=app.config['MYSQL_DATABASE_PASSWORD'],
            host=app.config['MYSQL_DATABASE_HOST'],
            database=app.config['MYSQL_DATABASE_DB']
        )
    except Error as e:
        print(f"Error connecting to MySQL Platform: {e}")
    return connection

@app.route('/')
def index():
        return redirect(url_for('search'))

    
@app.route('/search_page')
def search_page():
    return render_template('search.html')

@app.context_processor
def inject_user():
    return dict(username=session.get('username'))


# @app.route('/search', methods=['GET'])
# def search():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login'))

#     location = request.args.get('location')
#     checkin_date = request.args.get('checkin_date')  
#     checkout_date = request.args.get('checkout_date') 

#     if location:
#         connection = get_db_connection()
#         cursor = connection.cursor(dictionary=True)

#         try:
#             cursor.execute("SELECT * FROM hotels WHERE LOWER(location) = LOWER(%s)", (location,))
#             available_hotels = cursor.fetchall()
#         except mysql.connector.Error as err:
#             print(f"Error: {err}")
#             available_hotels = []  # Default to an empty list if there's an error
#         finally:
#             cursor.close()
#             connection.close()

#         return render_template('results.html', hotels=available_hotels, username=current_user.username, checkin_date=checkin_date, checkout_date=checkout_date)
#     else:
#         return render_template('search.html', username=current_user.username)

@app.route('/search', methods=['GET'])
def search():
    location = request.args.get('location')
    checkin_date = request.args.get('checkin_date')  
    checkout_date = request.args.get('checkout_date') 

    username = current_user.username if current_user.is_authenticated else None

    if location:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM hotels WHERE LOWER(location) = LOWER(%s)", (location,))
            available_hotels = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            available_hotels = []
        finally:
            cursor.close()
            connection.close()

        return render_template('results.html', hotels=available_hotels, username=username, checkin_date=checkin_date, checkout_date=checkout_date)
    else:
        return render_template('search.html', username=username)



def get_rooms(hotel_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM rooms WHERE hotel_id = %s", (hotel_id,))
        room_data = cursor.fetchall()
        return room_data
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


@app.route('/view_rooms/<int:hotel_id>')
def view_rooms(hotel_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    checkin_date = request.args.get('checkin_date', '') 
    checkout_date = request.args.get('checkout_date', '')

    try:
        cursor.execute("SELECT * FROM rooms WHERE hotel_id = %s", (hotel_id,))
        rooms = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template('view_rooms.html', rooms=rooms, checkin_date=checkin_date, checkout_date=checkout_date)

def send_cancellation_email(booking):
    msg = Message("Booking Cancellation Confirmation",
                  recipients=[booking.email])
    msg.body = f"""
    Dear {booking.customer_name},

    Your booking at {booking.hotel_name} has been cancelled.
    Check-in Date: {booking.checkin_date}
    Check-out Date: {booking.checkout_date}

    We hope to see you again.
    """
    mail.send(msg)

@app.route('/results')
def results():
    location = request.args.get('location')
    checkin_date = request.args.get('checkin_date')
    checkout_date = request.args.get('checkout_date')

    hotels = []
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = "SELECT * FROM hotels WHERE location LIKE %s"
        cursor.execute(query, ('%' + location + '%',))

        hotels = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while fetching search results.', 'error')
    finally:
        cursor.close()
        connection.close()

    return render_template('results.html', hotels=hotels, checkin_date=checkin_date, checkout_date=checkout_date)

@app.route('/reserve_options')
def reserve_options():
    room_id = request.args.get('room_id')
    checkin_date = request.args.get('checkin_date')
    checkout_date = request.args.get('checkout_date')

    if not room_id or not checkin_date or not checkout_date:
        # If any of these are not provided, redirect to a default page
        flash('Missing reservation details.', 'error')
        return redirect(url_for('index'))

    # If the user is logged in, redirect them directly to the booking form
    if current_user.is_authenticated:
        return redirect(url_for('booking_form', room_id=room_id, checkin_date=checkin_date, checkout_date=checkout_date))
    
    # For non-logged-in users, show the reserve options page
    return render_template(
        'reserve_options.html',
        room_id=room_id,
        checkin_date=checkin_date,
        checkout_date=checkout_date
    )


# @app.route('/booking_form/<int:room_id>', methods=['GET'])
# def booking_form(room_id):
#     connection = get_db_connection()
#     cursor = connection.cursor(dictionary=True)

#     checkin_date = request.args.get('checkin_date', '')
#     checkout_date = request.args.get('checkout_date', '')

#     try:
#         cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
#         room = cursor.fetchone()
#         if room:
#             cursor.execute("SELECT * FROM hotels WHERE id = %s", (room['hotel_id'],))
#             hotel = cursor.fetchone()
#     finally:
#         cursor.close()
#         connection.close()

#     return render_template('booking-form.html', room=room, hotel=hotel, checkin_date=checkin_date, checkout_date=checkout_date)

@app.route('/booking_form/<int:room_id>', methods=['GET'])
def booking_form(room_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    checkin_date_str = request.args.get('checkin_date', '')
    checkout_date_str = request.args.get('checkout_date', '')

    # Initialize dates as None
    checkin_date = None
    checkout_date = None

    # Only parse the dates if they are non-empty strings
    if checkin_date_str:
        try:
            checkin_date = datetime.strptime(checkin_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid check-in date format. Please use YYYY-MM-DD.', 'error')
            return redirect(request.referrer or url_for('index'))
    if checkout_date_str:
        try:
            checkout_date = datetime.strptime(checkout_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid check-out date format. Please use YYYY-MM-DD.', 'error')
            return redirect(request.referrer or url_for('index'))

    try:
        cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
        room = cursor.fetchone()
        if room:
            cursor.execute("SELECT * FROM hotels WHERE id = %s", (room['hotel_id'],))
            hotel = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return render_template('booking-form.html', room=room, hotel=hotel, checkin_date=checkin_date, checkout_date=checkout_date)



@app.route('/edit_account', methods=['GET', 'POST'])
@login_required
def edit_account():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        new_password = request.form.get('password')  # Get the new password

        try:
            # Update user details
            update_query = """
            UPDATE users SET username = %s, email = %s, first_name = %s, last_name = %s, phone = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (username, email, first_name, last_name, phone, current_user.id))

            # Update password if provided
            if new_password:
                password_hash = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hash, current_user.id)
                )

            connection.commit()
            flash('Your account has been updated.', 'success')
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash('An error occurred while updating your account.', 'error')
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('edit_account'))

    # Retrieve current user details to pre-fill the form
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s", (current_user.id,))
        user_data = cursor.fetchone()
        user_details = {
            'username': user_data['username'],
            'email': user_data['email'],
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'phone': user_data.get('phone', '')
        }
    except mysql.connector.Error as err:
        print(f"Error fetching user data: {err}")
        user_details = {}
    finally:
        cursor.close()
        connection.close()

    return render_template('edit_account.html', user_details=user_details)





@app.route('/edit_hotel/<int:hotel_id>', methods=['GET', 'POST'])
@login_required
def edit_hotel(hotel_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        updated_name = request.form['name']
        updated_location = request.form['location']
        updated_price = request.form['price']
        updated_reviews = request.form['reviews']

        try:
            cursor.execute("UPDATE hotels SET name = %s, location = %s, price = %s, reviews = %s WHERE id = %s",
                           (updated_name, updated_location, updated_price, updated_reviews, hotel_id))
            connection.commit()
            flash('Hotel updated successfully!', 'success')
            return redirect(url_for('hotels'))
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash('An error occurred while updating the hotel.', 'error')
        finally:
            cursor.close()
            connection.close()
    else:
        try:
            cursor.execute("SELECT * FROM hotels WHERE id = %s", (hotel_id,))
            hotel_data = cursor.fetchone()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            hotel_data = None
        finally:
            cursor.close()
            connection.close()

        if hotel_data:
            return render_template('edit_hotel.html', hotel=hotel_data)
        else:
            flash('Hotel not found.', 'error')
            return redirect(url_for('hotels'))

    return render_template('edit_hotel.html')

@app.route('/delete_hotel/<int:hotel_id>', methods=['POST'])
@login_required
def delete_hotel(hotel_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('admin_hotels'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        connection.commit()
        flash('Hotel deleted successfully.', 'success')
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while deleting the hotel.', 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin_hotels'))



@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
@login_required
def delete_booking(booking_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()

        if booking and booking['user_id'] == current_user.id:
            cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
            connection.commit()

            html_body = render_template('email/cancellation_email.html', 
                                    customer_name=booking['customer_name'],
                                    hotel_name=booking['hotel_name'],
                                    hotel_location=booking['hotel_location'],
                                    checkin_date=booking['checkin_date'],
                                    checkout_date=booking['checkout_date'],
                                    hotel_price=booking['hotel_price'])

            msg = Message("Booking Cancellation", recipients=[booking['email']])
            msg.body = "Your booking has been cancelled."
            msg.html = html_body
            mail.send(msg)

            flash('Booking deleted and email sent successfully!', 'success')
        else:
            flash('Booking not found.', 'error')

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while deleting the booking.', 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('bookings'))


@app.route('/reserve_room/<int:room_id>')
@login_required
def reserve_room(room_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    room_details = None
    hotel_details = None

    try:
        cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
        room_details = cursor.fetchone()

        if room_details:
            hotel_id = room_details['hotel_id']
            cursor.execute("SELECT * FROM hotels WHERE id = %s", (hotel_id,))
            hotel_details = cursor.fetchone()

            if not hotel_details:
                flash("Hotel details not found.", "error")
                return redirect(url_for('index'))

        else:
            flash("Room details not found.", "error")
            return redirect(url_for('index')) 

    except Error as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('booking_form', room_id=room_id, hotel_id=hotel_id))


@app.route('/hotels')
def hotels():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM hotels")
        hotel_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        hotel_data = []
    finally:
        cursor.close()
        connection.close()
    print(hotel_data)
    return render_template('results.html', hotels=hotel_data)

@app.route('/admin/hotels')
@login_required
def admin_hotels():
    if not current_user.is_admin:
        return "Access denied", 403

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM hotels")
        hotel_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        hotel_data = []
    finally:
        cursor.close()
        connection.close()

    return render_template('admin_hotels.html', hotels=hotel_data, is_admin=True)


@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not current_user.is_admin:
        return "Access denied", 403

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM bookings")
        booking_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        booking_data = []
    finally:
        cursor.close()
        connection.close()

    return render_template('admin_bookings.html', bookings=booking_data)


UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/add_hotel', methods=['GET', 'POST'])
@login_required
def add_hotel():
    if request.method == 'POST':
        # Extract the form data
        hotel_name = request.form['name']
        hotel_location = request.form['location']
        hotel_price = request.form['price']
        hotel_reviews = request.form['reviews']

        # Handle the image file
        if 'hotel_image' in request.files:
            hotel_image = request.files['hotel_image']
            if hotel_image.filename != '':
                filename = secure_filename(hotel_image.filename)
                image_path = os.path.join('static/images', filename)
                hotel_image.save(image_path)

                db_image_path = os.path.join('images', filename)

                connection = get_db_connection()
                cursor = connection.cursor()

                try:
                    cursor.execute("INSERT INTO hotels (name, location, price, reviews, image_path) VALUES (%s, %s, %s, %s, %s)",
                                   (hotel_name, hotel_location, hotel_price, hotel_reviews, db_image_path))
                    connection.commit()
                    flash('New hotel added successfully!', 'success')
                except mysql.connector.Error as err:
                    print(f"Error: {err}")
                    flash('An error occurred while adding the hotel.', 'error')
                finally:
                    cursor.close()
                    connection.close()

                return redirect(url_for('admin_hotels'))
        else:
            flash('No image file selected.', 'error')

    return render_template('add_hotel.html')


@app.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if request.method == 'POST':
        hotel_id = request.form.get('hotel_id')
        room_type = request.form.get('type')
        description = request.form.get('description')
        size = request.form.get('size')
        amenities = request.form.get('amenities')
        price = request.form.get('price')
        discount = request.form.get('discount')
        room_image = request.files.get('room_image')

        if 'room_image' in request.files:
            room_image = request.files['room_image']
            if room_image.filename != '':
                filename = secure_filename(room_image.filename)
                image_path = os.path.join('static/images', filename)
                room_image.save(image_path)

                db_image_path = os.path.join('images', filename)

            connection = get_db_connection()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO rooms (hotel_id, type, description, size, amenities, price, discount, image_path) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (hotel_id, room_type, description, size, amenities, price, discount, db_image_path)
                )
                connection.commit()
                flash('New room added successfully!', 'success')
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                flash('An error occurred while adding the room.', 'error')
            finally:
                cursor.close()
                connection.close()

            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid or no image file selected.', 'error')

    return render_template('add_room.html')


def send_confirmation_email(email, booking_details):
    html_body = render_template('email/confirmation_email_admin.html', 
                                customer_name=booking_details['customer_name'],
                                hotel_name=booking_details['hotel_name'],
                                hotel_location=booking_details['hotel_location'],
                                checkin_date=booking_details['checkin_date'],
                                checkout_date=booking_details['checkout_date'],
                                hotel_price=booking_details['hotel_price'],
                                room_type=booking_details['room_type'],
                                room_price=booking_details['room_price'])

    msg = Message("Booking Confirmation", recipients=[email])
    msg.body = "Your booking is confirmed. Please check the attached details." 
    msg.html = html_body
    mail.send(msg)



def send_rejection_email(email, booking_details):
    html_body = render_template('email/rejection_email.html', 
                                customer_name=booking_details['customer_name'],
                                hotel_name=booking_details['hotel_name'],
                                hotel_location=booking_details['hotel_location'],
                                checkin_date=booking_details['checkin_date'],
                                checkout_date=booking_details['checkout_date'],
                                hotel_price=booking_details['hotel_price'],
                                room_type=booking_details['room_type'],
                                room_price=booking_details['room_price'])

    msg = Message("Booking Rejection", recipients=[email])
    msg.body = "Unfortunately, your booking cannot be accommodated at this time." 
    msg.html = html_body
    mail.send(msg)

@app.route('/confirm_booking/<int:booking_id>')
@login_required
def confirm_booking(booking_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", ('confirmed', booking_id))
        connection.commit()
        flash('Booking confirmed successfully!', 'success')

        cursor.execute("SELECT customer_name, email, hotel_name, hotel_location, checkin_date, checkout_date, hotel_price, room_type, room_price FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()
        if booking:
            send_confirmation_email(booking['email'], booking)  

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while confirming the booking.', 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin_bookings'))


@app.route('/reject_booking/<int:booking_id>')
@login_required
def reject_booking(booking_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", ('rejected', booking_id))
        connection.commit()
        flash('Booking rejected successfully!', 'success')

        cursor.execute("SELECT customer_name, email, hotel_name, hotel_location, checkin_date, checkout_date, hotel_price, room_type, room_price FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()
        if booking:
            send_rejection_email(booking['email'], booking)

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while rejecting the booking.', 'error')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin_bookings'))


@app.route('/book', methods=['POST'])
def book_hotel():


    if current_user.is_authenticated:
        user_id = current_user.id
        is_guest = False
    else:
        user_id = None
        is_guest = True

    hotel_id = request.form.get('hotel_id')
    room_id = request.form.get('room_id')
    checkin_date = request.form.get('checkin_date')
    checkout_date = request.form.get('checkout_date')
    customer_name = request.form.get('customer_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    hotel_name = request.form.get('hotel_name')
    hotel_location = request.form.get('hotel_location')
    hotel_price = request.form.get('hotel_price')
    room_type = request.form.get('room_type')
    room_price = request.form.get('room_price')
    
    booking_number = generate_booking_number()

    if not hotel_id or not room_id:
        flash('Missing hotel or room information.', 'error')
        return redirect(url_for('index'))
    
    try:
        checkin_datetime = datetime.strptime(checkin_date, '%Y-%m-%d %H:%M:%S')
        checkout_datetime = datetime.strptime(checkout_date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('booking_form', room_id=room_id))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO bookings (user_id, hotel_id, room_id, checkin_date, checkout_date, hotel_name, hotel_location, hotel_price, customer_name, email, phone, booking_number, is_guest, room_type, room_price) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, hotel_id, room_id, checkin_datetime, checkout_datetime, hotel_name, hotel_location, hotel_price, customer_name, email, phone, booking_number, is_guest, room_type, room_price)
        )
        connection.commit()
        flash(f'Your booking has been confirmed! Booking number: {booking_number}', 'success')

        booking_details = {
            'booking_number': booking_number,
            'customer_name': customer_name,
            'hotel_name': hotel_name,
            'hotel_location': hotel_location,
            'checkin_date': checkin_date,
            'checkout_date': checkout_date,
            'hotel_price': hotel_price
        }

        html_body = render_template('email/confirmation_email.html', **booking_details)

        msg = Message("Booking Confirmation", recipients=[email])
        msg.body = f"Your booking is confirmed. Booking number: {booking_number}. Please check the attached details."
        msg.html = html_body
        mail.send(msg)
        
        if is_guest:
            session['guest_booking_details'] = {
            'booking_number': booking_number,
            'customer_name': customer_name,
            'email': email,
            'phone': phone,
            'hotel_location': hotel_location,
            'hotel_price': hotel_price,
            'room_type': room_type,
            'room_price': room_price,
            'checkin_date': checkin_date,
            'checkout_date': checkout_date
        }
            return redirect(url_for('guest_confirmation'))

    except mysql.connector.Error as err:
        flash('An error occurred while booking the hotel.', 'error')
        return redirect(url_for('booking_form', room_id=room_id))
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for('bookings'))

def generate_booking_number():
    return f"BK-{random.randint(1000, 9999)}-{int(datetime.now().timestamp())}"

@app.route('/guest_confirmation')
def guest_confirmation():
    if 'guest_booking_details' in session:
        booking_details = session['guest_booking_details']
        return render_template('guest_confirmation.html', booking=booking_details)
    else:
        flash('No booking details found. Please start a new booking.')
        return redirect(url_for('index'))


# @app.route('/admin/login', methods=['GET', 'POST'])
# def admin_login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
        
#         user = User.get_user_by_username(username)

#         if user and user.verify_password(password) and user.is_admin:
#             login_user(user)
#             return redirect(url_for('admin_dashboard'))
#         else:
#             flash('Invalid username or password', 'error')

#     return render_template('admin_login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.get_user_by_username(username)

        if user and user.verify_password(password):
            if user.is_admin:
                login_user(user)
                print("Login successful, redirecting to admin dashboard")
                return redirect(url_for('admin_dashboard'))
            else:
                print("User is not an admin")
                flash('Access denied. Only administrators can log in here.', 'error')
        else:
            print("Invalid username or password")
            flash('Invalid username or password', 'error')

    return render_template('admin_login.html')


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     app.logger.debug('Login route accessed')
#     if current_user.is_authenticated:
#         app.logger.debug('User is already authenticated, redirecting to search')
#         return redirect(url_for('search'))
    
#     if request.method == 'POST':
#         username_or_email = request.form.get('username_or_email')
#         password = request.form.get('password')

#         connection = get_db_connection()
#         cursor = connection.cursor(dictionary=True)

#         try:
#             cursor.execute(
#                 "SELECT * FROM users WHERE username = %s OR email = %s",
#                 (username_or_email, username_or_email)
#             )
#             user_record = cursor.fetchone()

#             if user_record and check_password_hash(user_record['password_hash'], password):
#                 user = User(user_record['id'], user_record['username'], user_record['email'], user_record['password_hash'])

#                 login_user(user)

#                 return redirect(url_for('search'))
#             else:

#                 flash('Incorrect username/email or password', 'error')
#         except mysql.connector.Error as err:
#             print(f"Error: {err}")
#             flash('An error occurred during login.', 'error')
#         finally:
#             cursor.close()
#             connection.close()

#     return render_template('login.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     app.logger.debug('Login route accessed')
#     if current_user.is_authenticated:
#         app.logger.debug('User is already authenticated, redirecting to search')
#         return redirect(url_for('search'))
    
#     if request.method == 'POST':
        
#         username_or_email = request.form.get('username_or_email')
#         password = request.form.get('password')

#         connection = get_db_connection()
#         cursor = connection.cursor(dictionary=True)

#         try:
#             cursor.execute(
#                 "SELECT * FROM users WHERE username = %s OR email = %s",
#                 (username_or_email, username_or_email)
#             )
#             user_record = cursor.fetchone()

#             if user_record and check_password_hash(user_record['password_hash'], password):
#                 user = User(user_record['id'], user_record['username'], user_record['email'], user_record['password_hash'])

#                 login_user(user)

#                 # Get the next page from the request arguments
#                 next_page = request.args.get('next') or url_for('index')
#                 return redirect(next_page)  # Redirect to the next page or index if not specified
#             else:
#                 flash('Incorrect username/email or password', 'error')
#         except mysql.connector.Error as err:
#             print(f"Error: {err}")
#             flash('An error occurred during login.', 'error')
#         finally:
#             cursor.close()
#             connection.close()

#     return render_template('login.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.debug('Login route accessed')
    if current_user.is_authenticated:
        app.logger.debug('User is already authenticated, redirecting to search')
        return redirect(url_for('search'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s OR email = %s",
                (username_or_email, username_or_email)
            )
            user_record = cursor.fetchone()

            if user_record and check_password_hash(user_record['password_hash'], password):
                user = User(user_record['id'], user_record['username'], user_record['email'], user_record['password_hash'])

                login_user(user)

                next_page = request.form.get('next') or url_for('index')  # Change here for POST request
                return redirect(next_page)  # Redirect to the next page or index if not specified
            else:
                flash('Incorrect username/email or password', 'error')
        except mysql.connector.Error as err:
            app.logger.error(f"Error: {err}")
            flash('An error occurred during login.', 'error')
        finally:
            cursor.close()
            connection.close()

    # The next parameter for GET requests to prefill the form if it's there
    next_param = request.args.get('next')
    return render_template('login.html', next=next_param)



# @app.route('/guest_booking', methods=['POST'])
# def guest_booking():

#     return render_template('guest_booking_confirmation.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            connection.commit()
            flash('You have been registered successfully!', 'success')
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash(f"An error occurred during registration: {err}", 'error')
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            user_record = cursor.fetchone()

            if user_record:
                token = s.dumps(email, salt='email-reset-salt')
                
                msg = Message('Password Reset Request', recipients=[email])
                link = url_for('reset_password', token=token, _external=True)
                msg.body = f'Your link to reset your password is {link}'
                mail.send(msg)

                flash('A password reset link has been sent to your email.', 'info')
            else:
                flash('Email not found.', 'error')
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            # Handle errors if necessary
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('login'))

    return render_template('forgot-password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='email-reset-salt', max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('The token is expired or invalid!', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        hashed_password = generate_password_hash(new_password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (hashed_password, email)
            )
            connection.commit()

            flash('Your password has been updated!', 'success')
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            # Handle errors if necessary
            flash('An error occurred while updating the password.', 'error')
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('login'))

    return render_template('reset-password.html', token=token)


# @app.route('/bookings')
# @login_required
# def bookings():
#     user_id = current_user.id
#     connection = get_db_connection()
#     cursor = connection.cursor(dictionary=True)

#     try:
#         cursor.execute("SELECT * FROM bookings WHERE user_id = %s", (user_id,))
#         user_bookings = cursor.fetchall()
#     except mysql.connector.Error as err:
#         print(f"Error: {err}")
#         flash('An error occurred while fetching your bookings.', 'error')
#         user_bookings = [] 
#     finally:
#         cursor.close()
#         connection.close()

#     return render_template('bookings.html', bookings=user_bookings)

@app.route('/admin_cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def admin_cancel_booking(booking_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('admin_login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()

        if booking:
            cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", ('cancelled', booking_id))
            connection.commit()
            flash('Booking has been successfully cancelled.', 'success')

            # Send cancellation email to the user
            html_body = render_template('email/cancellation_email.html', 
                                        customer_name=booking['customer_name'],
                                        hotel_name=booking['hotel_name'],
                                        hotel_location=booking['hotel_location'],
                                        checkin_date=booking['checkin_date'].strftime('%Y-%m-%d'),
                                        checkout_date=booking['checkout_date'].strftime('%Y-%m-%d'),
                                        hotel_price=booking['hotel_price'])

            msg = Message("Booking Cancellation", recipients=[booking['email']])
            msg.body = "Your booking has been cancelled."
            msg.html = html_body
            mail.send(msg)

        else:
            flash('Booking not found.', 'error')

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while cancelling the booking.', 'error')

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin_bookings'))

@app.route('/bookings')
def bookings():
    # Check if the user is logged in
    if current_user.is_authenticated:
        user_id = current_user.id
        query = "SELECT * FROM bookings WHERE user_id = %s"
        query_params = (user_id,)
    else:
        # For guests, use another identifier, e.g., booking reference stored in session
        booking_reference = session.get('booking_reference')
        if not booking_reference:
            # Handle case where there is no booking reference (e.g., redirect to home or show message)
            flash('No booking reference found. Please start a new booking.', 'info')
            return redirect(url_for('index'))
        
        query = "SELECT * FROM bookings WHERE booking_reference = %s"
        query_params = (booking_reference,)

    # Connect to the database and execute the query
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(query, query_params)
        bookings = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('An error occurred while fetching your bookings.', 'error')
        bookings = []
    finally:
        cursor.close()
        connection.close()

    return render_template('bookings.html', bookings=bookings)

@app.route('/check_booking', methods=['GET', 'POST'])
def check_booking():
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        search_value = request.form.get('search_value')

        if search_type == 'email':
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM bookings WHERE email = %s", (search_value,))
            bookings = cursor.fetchall()
            cursor.close()
            connection.close()

        elif search_type == 'booking_number':
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM bookings WHERE booking_number = %s", (search_value,))
            bookings = cursor.fetchall()
            cursor.close()
            connection.close()

        else:
            flash('Invalid search type.', 'error')
            return redirect(url_for('check_booking'))

        if bookings:
            columns = [
                'id', 'unknown_field1', 'room_type_id', 'user_status', 
                'checkin_date', 'checkout_date', 'customer_name', 
                'email', 'phone', 'hotel_name', 'hotel_location', 
                'hotel_price', 'booking_status', 'booking_number', 
                'is_guest', 'unknown_field2'
            ]

            bookings_list = []
            for booking_tuple in bookings:
                booking_dict = dict(zip(columns, booking_tuple))
                bookings_list.append(booking_dict)

            print("Bookings data to be passed to template:", bookings_list)
            # Return statement moved outside of the for loop
            return render_template('booking_details.html', bookings=bookings_list)
        else:
            flash('No booking found with the provided information.', 'error')
            return redirect(url_for('check_booking'))

    return render_template('check_booking.html')


class User(UserMixin):
    def __init__(self, id, username, email, password_hash, first_name=None, last_name=None, phone=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.is_admin = is_admin

    def get_id(self):
        return self.id

    @staticmethod
    def get_user_by_id(user_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                is_admin_bool = bool(user_data['is_admin'])

                return User(
                    user_data['id'], 
                    user_data['username'], 
                    user_data['email'], 
                    user_data['password_hash'],
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    phone=user_data.get('phone'),
                    is_admin=is_admin_bool
                )
            else:
                return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_user_by_username(username):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            if user_data:
                is_admin_bool = bool(user_data['is_admin'])

                return User(
                    user_data['id'], 
                    user_data['username'], 
                    user_data['email'], 
                    user_data['password_hash'],
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    phone=user_data.get('phone'),
                    is_admin=is_admin_bool
                )
            else:
                return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

    def verify_password(self, password):
        encoded_password = password.encode()
        encoded_hash = self.password_hash.encode()

        if bcrypt.checkpw(encoded_password, encoded_hash):
            print("Password match")
            return True
        else:
            print("Password does not match") 
            return False

@login_manager.user_loader
def load_user(user_id):
    return User.get_user_by_id(user_id)


@app.route('/contact', methods=['GET'])
def contact():
    return render_template('contact.html')

@app.route('/send_contact_email', methods=['POST'])
def send_contact_email():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    content = request.form.get('message')

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        insert_query = "INSERT INTO messages (name, email, subject, content) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (name, email, subject, content))
        connection.commit()
        cursor.close()
        flash('Your message has been sent.', 'success')
    except Exception as e:
        flash('Your message could not be sent. Please try again later.', 'error')
        print(e)
    finally:
        if connection:
            connection.close()

    return redirect(url_for('contact'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "Access denied", 403
    messages = get_messages_from_db() 
    return render_template('admin_dashboard.html', messages=messages)

def get_messages_from_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM messages")
    messages = cursor.fetchall()
    cursor.close()
    connection.close()
    return messages

@app.route('/admin/messages')
@login_required
def admin_messages():
    if not current_user.is_admin:
        return "Access denied", 403

    messages = get_messages_from_db()
    return render_template('admin_messages.html', messages=messages)


@app.route('/send_reply/<int:message_id>', methods=['POST'])
@login_required
def send_reply(message_id):
    if not current_user.is_admin:
        return "Access denied", 403
    

    recipient_email = request.form.get('recipient_email')
    reply = request.form.get('reply')

    try:
        msg = Message("Reply from S&P Booking", 
                      sender='sandpbooking@gmail.com',  
                      recipients=[recipient_email],
                      body=reply)
        
        msg.html = render_template('email/admin_reply_email.html',
                                   customer_name='Recipient Name',
                                   reply=reply)
        mail.send(msg)

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        connection.commit()
        cursor.close()
        connection.close()

        flash('Reply sent successfully and message removed!', 'success')
    except Exception as e:
        flash('Failed to send reply.', 'error')
        print(e)

    return redirect(url_for('admin_messages'))

@app.route('/logout')
@login_required 
def logout():
    logout_user()
    session.clear() 
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    response = get_chatbot_response(user_message)
    return jsonify({'message': response})


# def get_chatbot_response(user_input):
#     user_input = user_input.lower()

#     booking_id = extract_booking_id(user_input)
#     if booking_id:
#         # Here, decide what to do with the booking number. For example:
#         # - Check booking status
#         # - Offer to delete or modify the booking
#         # For demonstration, we'll assume the user wants to delete the booking.
#         return delete_booking_by_id(booking_id)

#     if 'price' in user_input:
#         return "The price depends on the hotel and room type. Can you specify your hotel or room preference?"
    
#     elif 'availability' in user_input or 'available' in user_input:
#         return "I can check availability for you. Please provide the hotel name and dates."

#     elif 'cancel' in user_input:
#         return "To cancel a booking, please provide your booking number."

#     elif 'delete booking' in user_input:  # New conditional for booking deletion
#         booking_id = extract_booking_id(user_input)
#         if booking_id:
#             return delete_booking_by_id(booking_id)
#         else:
#             return "Please provide a valid booking ID for deletion."

#     elif 'help' in user_input or 'options' in user_input:
#         return "I can help with booking prices, availability, and cancellation. What do you need help with?"

#     else:
#         return "I'm sorry, I didn't understand that. Can you please rephrase?"

def process_booking_cancellation(booking_number):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check if the booking exists
        cursor.execute("SELECT * FROM bookings WHERE booking_number = %s", (booking_number,))
        booking = cursor.fetchone()

        if booking:
            # Update the booking status to 'cancelled' or a similar status
            cursor.execute("UPDATE bookings SET status = %s WHERE booking_number = %s", ('cancelled', booking_number))
            connection.commit()
            return f"Booking number {booking_number} has been successfully cancelled."

        else:
            return "Booking not found. Please check the booking number and try again."

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return "An error occurred while processing the cancellation."

    finally:
        cursor.close()
        connection.close()


def get_chatbot_response(user_input):
    user_input = user_input.lower()

    # Check for context in the session
    last_intent = session.get('last_intent')

    # Extract booking number
    booking_number = extract_booking_number(user_input)

    # Intent: Cancel Booking
    if 'cancel' in user_input or last_intent == 'cancel_booking':
        if booking_number:
            session['last_intent'] = None  # Clear the last intent
            return process_booking_cancellation(booking_number)
        else:
            session['last_intent'] = 'cancel_booking'
            return "Please provide your booking number for cancellation."

    # Intent: Delete Booking
    elif 'delete booking' in user_input or last_intent == 'delete_booking':
        if booking_number:
            session['last_intent'] = None
            return delete_booking_by_number(booking_number)
        else:
            session['last_intent'] = 'delete_booking'
            return "Please provide your booking number for deletion."

    # Other Intents
    elif 'price' in user_input:
        return "The price depends on the hotel and room type. Can you specify your hotel or room preference?"
    elif 'availability' in user_input or 'available' in user_input:
        return "I can check availability for you. Please provide the hotel name and dates."
    elif 'help' in user_input or 'options' in user_input:
        return "I can help with booking prices, availability, and cancellation. What do you need help with?"

    # No intent recognized
    session['last_intent'] = None
    return "I'm sorry, I didn't understand that. Can you please rephrase?"



def delete_booking_by_number(booking_number):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM bookings WHERE booking_number = %s", (booking_number,))
        booking = cursor.fetchone()

        if booking:
            cursor.execute("DELETE FROM bookings WHERE booking_number = %s", (booking_number,))
            connection.commit()
            return f"Booking with number {booking_number} has been successfully deleted."
        else:
            return "Booking not found."

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return "An error occurred while deleting the booking."

    finally:
        cursor.close()
        connection.close()


def extract_booking_number(input_text):
    match = re.search(r'BK-\d{4}-\d{9}', input_text)
    return match.group() if match else None



if __name__ == '__main__':
    app.run(debug=True)
