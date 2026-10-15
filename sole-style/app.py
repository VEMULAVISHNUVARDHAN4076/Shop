"""SoleStyle footwear reservation application."""
import os
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_socketio import SocketIO, join_room
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, or_, select
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
db = SQLAlchemy()
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins=[])


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(40), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    bookings = db.relationship("Booking", backref="customer", lazy=True)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(90), unique=True, nullable=False)


class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    compare_at = db.Column(db.Numeric(10, 2))
    image = db.Column(db.String(500), default="")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brand.id"), nullable=False)
    gender = db.Column(db.String(30), default="Unisex")
    featured = db.Column(db.Boolean, default=False)
    bestseller = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    category = db.relationship("Category")
    brand = db.relationship("Brand")
    variants = db.relationship("Variant", backref="product", cascade="all, delete-orphan", lazy=True)

    @property
    def stock(self):
        return sum(v.stock for v in self.variants)

    @property
    def sizes(self):
        return sorted({v.size for v in self.variants})

    @property
    def colors(self):
        return sorted({v.color for v in self.variants})


class Variant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    size = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(40), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (db.UniqueConstraint("product_id", "size", "color"),)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("variant.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    variant = db.relationship("Variant")
    __table_args__ = (db.UniqueConstraint("user_id", "variant_id"),)


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product = db.relationship("Product")
    __table_args__ = (db.UniqueConstraint("user_id", "product_id"),)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    status = db.Column(db.String(40), default="Pending Confirmation", nullable=False, index=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    customer_note = db.Column(db.String(500), default="")
    admin_note = db.Column(db.String(1000), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    items = db.relationship("BookingItem", backref="booking", cascade="all, delete-orphan", lazy=True)


class BookingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    product_name = db.Column(db.String(180), nullable=False)
    image = db.Column(db.String(500), default="")
    size = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(40), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("variant.id"), nullable=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(240), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Setting(db.Model):
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(500), nullable=False)


STATUSES = ["Pending Confirmation", "Confirmed", "Ready for Pickup", "Completed", "Cancelled"]
CATEGORIES = ["Sneakers", "Formal", "Sandals", "Slippers", "Sports", "Heels"]
PLACEHOLDER = "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85"


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    database_url = os.getenv("DATABASE_URL") or f"sqlite:///{Path(app.instance_path) / 'sole_style.db'}"
    # Render provides postgres:// URLs; SQLAlchemy 2 uses postgresql+psycopg.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", str(Path(app.instance_path) / "uploads")),
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    )
    db.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    @app.context_processor
    def inject_globals():
        user = current_user()
        return {"current_user": user, "cart_count": CartItem.query.filter_by(user_id=user.id).count() if user else 0,
                "unread_count": Notification.query.filter_by(user_id=user.id, read=False).count() if user else 0,
                "shop_name": get_setting("shop_name", "SoleStyle"), "shop_address": get_setting("shop_address", "12 Market Street, Bengaluru"),
                "now_year": datetime.now().year, "now_date": datetime.now().strftime("%A, %d %B %Y").upper()}

    @app.template_filter("money")
    def money(value):
        return "₹{:,.0f}".format(float(value or 0))

    @app.template_filter("datefmt")
    def datefmt(value):
        return value.strftime("%d %b %Y, %I:%M %p") if value else "—"

    @app.before_request
    def expire_inactive_user():
        uid = session.get("user_id")
        if uid:
            user = db.session.get(User, uid)
            if not user or not user.active:
                session.clear()
                flash("Your session has expired. Please sign in again.", "info")

    register_routes(app)
    return app


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


@socketio.on("connect")
def socket_connect(auth=None):
    user = current_user()
    if user:
        join_room(f"user_{user.id}")


def get_setting(key, default=""):
    item = db.session.get(Setting, key)
    return item.value if item else default


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user.role != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped


def notify(user_id, title, message):
    note = Notification(user_id=user_id, title=title, message=message)
    db.session.add(note)
    db.session.flush()
    socketio.emit("notification", {"title": title, "message": message, "id": note.id}, to=f"user_{user_id}")
    return note


def slugify(text):
    import re
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or secrets.token_hex(4)


def register_routes(app):
    @app.get("/")
    def index():
        featured = Product.query.filter_by(active=True, featured=True).order_by(Product.created_at.desc()).limit(4).all()
        if not featured:
            featured = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(4).all()
        categories = Category.query.order_by(Category.name).all()
        return render_template("index.html", featured=featured, categories=categories)

    @app.get("/healthz")
    def healthz():
        db.session.execute(db.text("SELECT 1"))
        return {"status": "ok"}, 200

    @app.get("/products")
    def products():
        query = Product.query.filter_by(active=True)
        term = request.args.get("q", "").strip()
        category = request.args.get("category", "")
        brand = request.args.get("brand", "")
        gender = request.args.get("gender", "")
        size = request.args.get("size", "")
        color = request.args.get("color", "")
        min_price = request.args.get("min", "")
        max_price = request.args.get("max", "")
        if term:
            query = query.join(Brand).join(Category).filter(or_(Product.name.ilike(f"%{term}%"), Brand.name.ilike(f"%{term}%"), Category.name.ilike(f"%{term}%")))
        if category:
            query = query.join(Category, isouter=True).filter(Category.slug == category)
        if brand:
            query = query.join(Brand, isouter=True).filter(Brand.name == brand)
        if gender:
            query = query.filter(Product.gender == gender)
        if size or color:
            query = query.join(Variant)
            if size: query = query.filter(Variant.size == size)
            if color: query = query.filter(Variant.color.ilike(f"%{color}%"))
        try:
            if min_price: query = query.filter(Product.price >= Decimal(min_price))
            if max_price: query = query.filter(Product.price <= Decimal(max_price))
        except Exception:
            flash("Enter a valid price range.", "warning")
        sort = request.args.get("sort", "newest")
        if sort == "price_low": query = query.order_by(Product.price.asc())
        elif sort == "price_high": query = query.order_by(Product.price.desc())
        elif sort == "popular": query = query.order_by(Product.bestseller.desc(), Product.created_at.desc())
        else: query = query.order_by(Product.created_at.desc())
        items = query.distinct().all()
        return render_template("products.html", products=items, categories=Category.query.order_by(Category.name).all(), brands=Brand.query.order_by(Brand.name).all(), filters=request.args)

    @app.get("/products/<slug>")
    def product_detail(slug):
        product = Product.query.filter_by(slug=slug, active=True).first_or_404()
        similar = Product.query.filter(Product.active.is_(True), Product.category_id == product.category_id, Product.id != product.id).limit(4).all()
        available_colors = sorted({v.color for v in product.variants if v.stock > 0})
        return render_template("product_detail.html", product=product, similar=similar, available_colors=available_colors)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user(): return redirect(url_for("dashboard"))
        if request.method == "POST":
            name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
            phone, password = request.form.get("phone", "").strip(), request.form.get("password", "")
            if len(name) < 2 or "@" not in email or len(password) < 8:
                flash("Enter your name, a valid email and a password of at least 8 characters.", "danger")
            elif User.query.filter_by(email=email).first():
                flash("An account already uses that email. Please sign in.", "warning")
            else:
                user = User(name=name, email=email, phone=phone, password_hash=generate_password_hash(password))
                db.session.add(user); db.session.commit()
                session.clear(); session["user_id"] = user.id; session.permanent = True
                flash("Welcome to SoleStyle. Your account is ready.", "success")
                return redirect(url_for("dashboard"))
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user(): return redirect(url_for("admin_dashboard" if current_user().role == "admin" else "dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if user and user.active and check_password_hash(user.password_hash, request.form.get("password", "")):
                session.clear(); session["user_id"] = user.id; session.permanent = bool(request.form.get("remember"))
                return redirect(request.args.get("next") or url_for("admin_dashboard" if user.role == "admin" else "dashboard"))
            flash("Those details didn’t match an active account. Try again.", "danger")
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear(); flash("You have been signed out.", "info")
        return redirect(url_for("index"))

    @app.get("/forgot-password")
    def forgot_password():
        return render_template("forgot_password.html")

    @app.post("/forgot-password")
    def request_password_reset():
        # Deliberately no email provider dependency; deployment must wire a secure token-delivery service.
        flash("If an account matches that email, contact the shop to reset your password. Online reset delivery is not configured yet.", "info")
        return redirect(url_for("login"))

    @app.get("/admin/create-first")
    def first_admin_info():
        if User.query.filter_by(role="admin").first():
            return "Initial administrator has already been created.", 403
        return "Run `flask --app app create-admin` from a trusted local terminal. This one-time setup route does not expose administrator creation over the web.", 200

    @app.route("/cart", methods=["GET", "POST"])
    @login_required
    def cart():
        user = current_user()
        if request.method == "POST":
            action = request.form.get("action")
            row = CartItem.query.filter_by(id=request.form.get("item_id", type=int), user_id=user.id).first()
            if action == "add":
                variant = db.session.get(Variant, request.form.get("variant_id", type=int))
                qty = request.form.get("quantity", 1, type=int)
                if not variant or not variant.product.active or qty < 1:
                    flash("Choose an available size and color.", "danger")
                elif variant.stock < qty:
                    flash("There isn’t enough stock for that quantity.", "warning")
                else:
                    row = CartItem.query.filter_by(user_id=user.id, variant_id=variant.id).first()
                    if row: row.quantity = min(variant.stock, row.quantity + qty)
                    else: db.session.add(CartItem(user_id=user.id, variant_id=variant.id, quantity=qty))
                    db.session.commit(); flash("Added to your reservation bag.", "success")
                    return redirect(request.referrer or url_for("cart"))
            elif row and action == "remove":
                db.session.delete(row); db.session.commit(); flash("Removed from your bag.", "info")
            elif row and action in ("increase", "decrease"):
                desired = row.quantity + (1 if action == "increase" else -1)
                if desired <= 0: db.session.delete(row)
                elif desired <= row.variant.stock: row.quantity = desired
                else: flash("That quantity exceeds current stock.", "warning")
                db.session.commit()
            return redirect(url_for("cart"))
        rows = CartItem.query.filter_by(user_id=user.id).all()
        total = sum((r.variant.product.price * r.quantity for r in rows if r.variant and r.variant.product.active), Decimal("0.00"))
        return render_template("cart.html", rows=rows, total=total)

    @app.route("/booking/confirm", methods=["GET", "POST"])
    @login_required
    def confirm_booking():
        user = current_user()
        rows = CartItem.query.filter_by(user_id=user.id).all()
        if not rows:
            flash("Your bag is empty.", "info"); return redirect(url_for("products"))
        total = sum((r.variant.product.price * r.quantity for r in rows if r.variant and r.variant.product.active), Decimal("0.00"))
        if request.method == "POST":
            try:
                # Serialize reservation attempts for the same inventory. On SQLite the write transaction
                # itself serializes writers; MySQL additionally locks matching variant rows below.
                if db.engine.dialect.name == "sqlite":
                    db.session.execute(db.text("BEGIN IMMEDIATE"))
                # Lock variant rows on MySQL; transactional stock check prevents concurrent overbooking.
                locked = {v.id: v for v in Variant.query.filter(Variant.id.in_([r.variant_id for r in rows])).with_for_update().all()}
                for row in rows:
                    variant = locked.get(row.variant_id)
                    if not variant or not variant.product.active or row.quantity > variant.stock:
                        raise ValueError(f"Stock changed for {row.variant.product.name}; please update your bag.")
                booking = Booking(code="SS-" + secrets.token_hex(4).upper(), user_id=user.id, total=total, customer_note=request.form.get("note", "")[:500])
                db.session.add(booking); db.session.flush()
                for row in rows:
                    variant = locked[row.variant_id]
                    db.session.add(BookingItem(booking_id=booking.id, product_name=variant.product.name, image=variant.product.image, size=variant.size, color=variant.color, quantity=row.quantity, unit_price=variant.product.price, variant_id=variant.id))
                    variant.stock -= row.quantity
                    db.session.delete(row)
                notify(user.id, "Reservation received", f"Booking {booking.code} is awaiting shop confirmation. Visit our store for pickup or purchase.")
                db.session.commit()
                return redirect(url_for("booking_success", code=booking.code))
            except ValueError as exc:
                db.session.rollback(); flash(str(exc), "warning")
            except Exception:
                db.session.rollback(); app.logger.exception("Booking failed")
                flash("We couldn’t complete the reservation. Please try again.", "danger")
        return render_template("booking_confirm.html", rows=rows, total=total)

    @app.get("/booking/success/<code>")
    @login_required
    def booking_success(code):
        booking = Booking.query.filter_by(code=code, user_id=current_user().id).first_or_404()
        return render_template("booking_success.html", booking=booking)

    @app.get("/my-bookings")
    @login_required
    def my_bookings():
        bookings = Booking.query.filter_by(user_id=current_user().id).order_by(Booking.created_at.desc()).all()
        return render_template("my_bookings.html", bookings=bookings)

    @app.post("/my-bookings/<int:booking_id>/cancel")
    @login_required
    def cancel_booking(booking_id):
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user().id).with_for_update().first_or_404()
        if booking.status not in ("Pending Confirmation", "Confirmed"):
            flash("This booking can no longer be cancelled online. Please contact the shop.", "warning")
        else:
            booking.status = "Cancelled"
            for item in booking.items:
                if item.variant_id:
                    variant = db.session.get(Variant, item.variant_id)
                    if variant: variant.stock += item.quantity
            notify(booking.user_id, "Booking cancelled", f"Booking {booking.code} was cancelled and its stock was released.")
            db.session.commit(); flash("Booking cancelled. Reserved stock has been released.", "info")
        return redirect(url_for("my_bookings"))

    @app.route("/wishlist", methods=["GET", "POST"])
    @login_required
    def wishlist():
        user = current_user()
        if request.method == "POST":
            product = Product.query.filter_by(id=request.form.get("product_id", type=int), active=True).first_or_404()
            row = Wishlist.query.filter_by(user_id=user.id, product_id=product.id).first()
            if row: db.session.delete(row); flash("Removed from your wishlist.", "info")
            else: db.session.add(Wishlist(user_id=user.id, product_id=product.id)); flash("Saved to your wishlist.", "success")
            db.session.commit(); return redirect(request.referrer or url_for("wishlist"))
        rows = Wishlist.query.filter_by(user_id=user.id).all()
        return render_template("wishlist.html", rows=rows)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        user = current_user()
        if request.method == "POST":
            action = request.form.get("action")
            if action == "profile":
                name, phone = request.form.get("name", "").strip(), request.form.get("phone", "").strip()
                if len(name) < 2: flash("Please enter your name.", "danger")
                else: user.name, user.phone = name, phone; db.session.commit(); flash("Profile updated.", "success")
            elif action == "password":
                if not check_password_hash(user.password_hash, request.form.get("current_password", "")):
                    flash("Current password is incorrect.", "danger")
                elif len(request.form.get("new_password", "")) < 8:
                    flash("Choose a password with at least 8 characters.", "warning")
                else:
                    user.password_hash = generate_password_hash(request.form["new_password"]); db.session.commit(); flash("Password changed.", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html")

    @app.get("/notifications")
    @login_required
    def notifications():
        rows = Notification.query.filter_by(user_id=current_user().id).order_by(Notification.created_at.desc()).all()
        for n in rows: n.read = True
        db.session.commit()
        return render_template("notifications.html", notifications=rows)

    @app.get("/dashboard")
    @login_required
    def dashboard():
        user = current_user()
        bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).limit(5).all()
        active_count = Booking.query.filter(Booking.user_id == user.id, Booking.status.notin_(["Completed", "Cancelled"])).count()
        return render_template("dashboard.html", bookings=bookings, booking_count=Booking.query.filter_by(user_id=user.id).count(), active_count=active_count)

    # Admin
    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        counts = {"products": Product.query.filter_by(active=True).count(), "stock": db.session.query(func.coalesce(func.sum(Variant.stock), 0)).scalar(),
                  "low": Product.query.filter_by(active=True).all(), "customers": User.query.filter_by(role="customer", active=True).count(),
                  "bookings": Booking.query.count(), "pending": Booking.query.filter_by(status="Pending Confirmation").count(),
                  "confirmed": Booking.query.filter_by(status="Confirmed").count(), "ready": Booking.query.filter_by(status="Ready for Pickup").count(),
                  "completed": Booking.query.filter_by(status="Completed").count(), "cancelled": Booking.query.filter_by(status="Cancelled").count()}
        counts["low"] = [p for p in counts["low"] if 0 < p.stock <= 5]
        recent = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()
        trend = db.session.query(func.date(Booking.created_at), func.count(Booking.id)).group_by(func.date(Booking.created_at)).order_by(func.date(Booking.created_at).desc()).limit(14).all()
        return render_template("admin/dashboard.html", counts=counts, recent=recent, trend=list(reversed(trend)))

    @app.get("/admin/products")
    @admin_required
    def admin_products():
        term = request.args.get("q", "").strip()
        query = Product.query
        if term: query = query.filter(Product.name.ilike(f"%{term}%"))
        return render_template("admin/products.html", products=query.order_by(Product.created_at.desc()).all())

    @app.route("/admin/products/new", methods=["GET", "POST"])
    @app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_product(product_id=None):
        product = db.session.get(Product, product_id) if product_id else None
        if product_id and not product: abort(404)
        categories, brands = Category.query.order_by(Category.name).all(), Brand.query.order_by(Brand.name).all()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            try: price = Decimal(request.form.get("price", "0"))
            except Exception: price = Decimal("0")
            category = db.session.get(Category, request.form.get("category_id", type=int))
            brand = db.session.get(Brand, request.form.get("brand_id", type=int))
            compare_raw = request.form.get("compare_at", "").strip()
            try: compare_at = Decimal(compare_raw) if compare_raw else None
            except Exception: compare_at = Decimal("0")
            if not name or price <= 0 or not category or not brand or (compare_at is not None and compare_at < price):
                flash("Enter a product name, valid price, category and brand.", "danger")
            else:
                if not product:
                    slug = slugify(name)
                    if Product.query.filter_by(slug=slug).first(): slug += "-" + secrets.token_hex(2)
                    product = Product(name=name, slug=slug); db.session.add(product)
                product.name, product.description, product.price = name, request.form.get("description", ""), price
                product.compare_at = compare_at
                product.category_id, product.brand_id = category.id, brand.id
                product.gender = request.form.get("gender", "Unisex")
                product.featured, product.bestseller = bool(request.form.get("featured")), bool(request.form.get("bestseller"))
                product.active = bool(request.form.get("active", "1"))
                image = request.files.get("image")
                if image and image.filename:
                    ext = Path(secure_filename(image.filename)).suffix.lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                        flash("Use a JPG, PNG or WebP product image.", "warning")
                        return render_template("admin/product_form.html", product=product, categories=categories, brands=brands)
                    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                    filename = secrets.token_hex(12) + ext
                    image.save(Path(app.config["UPLOAD_FOLDER"]) / filename)
                    product.image = "/uploads/" + filename
                db.session.flush()
                # Replace variant grid; referenced variants are retained as inactive zero stock if historic.
                sizes = list(dict.fromkeys(s.strip() for s in request.form.get("sizes", "").split(",") if s.strip()))
                colors = list(dict.fromkeys(c.strip() for c in request.form.get("colors", "").split(",") if c.strip()))
                stock = max(0, request.form.get("stock", 0, type=int))
                if not sizes or not colors:
                    flash("Add at least one size and one color so customers can reserve a variant.", "danger")
                    db.session.rollback()
                    return render_template("admin/product_form.html", product=product, categories=categories, brands=brands)
                wanted = {(size_value, color_value) for size_value in sizes for color_value in colors}
                for v in list(product.variants):
                    key = (v.size, v.color)
                    if key not in wanted and not BookingItem.query.filter_by(variant_id=v.id).first(): db.session.delete(v)
                for size_value, color_value in wanted:
                    variant = Variant.query.filter_by(product_id=product.id, size=size_value, color=color_value).first()
                    if not variant:
                        db.session.add(Variant(product_id=product.id, size=size_value, color=color_value, stock=stock))
                db.session.add(Activity(admin_id=current_user().id, action=f"{'Updated' if product_id else 'Created'} product: {product.name}"))
                db.session.commit(); flash("Product saved.", "success"); return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", product=product, categories=categories, brands=brands)

    @app.post("/admin/products/<int:product_id>/toggle")
    @admin_required
    def toggle_product(product_id):
        product = db.session.get(Product, product_id) or abort(404)
        product.active = not product.active
        db.session.add(Activity(admin_id=current_user().id, action=f"{'Activated' if product.active else 'Deactivated'} product: {product.name}"))
        db.session.commit(); flash("Product visibility updated.", "success"); return redirect(url_for("admin_products"))

    @app.get("/admin/bookings")
    @admin_required
    def admin_bookings():
        query = Booking.query.join(User)
        term, status = request.args.get("q", "").strip(), request.args.get("status", "")
        if term: query = query.filter(or_(Booking.code.ilike(f"%{term}%"), User.name.ilike(f"%{term}%"), User.phone.ilike(f"%{term}%"), Booking.items.any(BookingItem.product_name.ilike(f"%{term}%"))))
        if status in STATUSES: query = query.filter(Booking.status == status)
        bookings = query.order_by(Booking.created_at.desc()).all()
        return render_template("admin/bookings.html", bookings=bookings, statuses=STATUSES)

    @app.post("/admin/bookings/<int:booking_id>/update")
    @admin_required
    def update_booking(booking_id):
        booking = db.session.get(Booking, booking_id) or abort(404)
        status = request.form.get("status")
        if status not in STATUSES: abort(400)
        old = booking.status
        if status == "Cancelled" and old != "Cancelled":
            for item in booking.items:
                variant = db.session.get(Variant, item.variant_id) if item.variant_id else None
                if variant: variant.stock += item.quantity
        if old == "Cancelled" and status != "Cancelled":
            for item in booking.items:
                variant = db.session.get(Variant, item.variant_id) if item.variant_id else None
                if not variant or variant.stock < item.quantity:
                    flash("Insufficient stock to reopen this booking.", "danger"); db.session.rollback(); return redirect(url_for("admin_bookings"))
                variant.stock -= item.quantity
        booking.status, booking.admin_note = status, request.form.get("admin_note", "")[:1000]
        if old != status:
            notify(booking.user_id, f"Booking {status.lower()}", f"Your booking {booking.code} is now {status}. Visit the store for pickup or purchase.")
        db.session.add(Activity(admin_id=current_user().id, action=f"Changed {booking.code}: {old} → {status}"))
        db.session.commit(); flash("Booking updated and customer notified.", "success"); return redirect(url_for("admin_bookings"))

    @app.get("/admin/customers")
    @admin_required
    def admin_customers():
        term = request.args.get("q", "").strip()
        query = User.query.filter_by(role="customer")
        if term: query = query.filter(or_(User.name.ilike(f"%{term}%"), User.email.ilike(f"%{term}%"), User.phone.ilike(f"%{term}%")))
        return render_template("admin/customers.html", customers=query.order_by(User.created_at.desc()).all())

    @app.post("/admin/customers/<int:user_id>/toggle")
    @admin_required
    def toggle_customer(user_id):
        user = User.query.filter_by(id=user_id, role="customer").first_or_404()
        user.active = not user.active
        db.session.add(Activity(admin_id=current_user().id, action=f"{'Activated' if user.active else 'Deactivated'} customer: {user.email}"))
        db.session.commit(); flash("Customer account updated.", "success"); return redirect(url_for("admin_customers"))

    @app.get("/admin/reports")
    @admin_required
    def reports():
        products = Product.query.filter_by(active=True).all()
        popular = sorted(products, key=lambda p: sum(i.quantity for b in Booking.query.filter(Booking.status != "Cancelled").all() for i in b.items if i.product_name == p.name), reverse=True)[:8]
        return render_template("admin/reports.html", products=products, popular=popular)

    @app.get("/admin/export/<kind>.csv")
    @admin_required
    def export_csv(kind):
        import csv, io
        buf = io.StringIO(); writer = csv.writer(buf)
        if kind == "bookings":
            writer.writerow(["Booking ID", "Customer", "Phone", "Status", "Items", "Reservation value", "Created"])
            for b in Booking.query.order_by(Booking.created_at.desc()).all(): writer.writerow([b.code, b.customer.name, b.customer.phone, b.status, sum(i.quantity for i in b.items), b.total, b.created_at.isoformat()])
        elif kind == "inventory":
            writer.writerow(["Product", "Brand", "Category", "Price", "Stock", "Active"])
            for p in Product.query.all(): writer.writerow([p.name, p.brand.name, p.category.name, p.price, p.stock, p.active])
        else: abort(404)
        from flask import Response
        return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=sole-style-{kind}.csv"})

    @app.route("/admin/settings", methods=["GET", "POST"])
    @admin_required
    def admin_settings():
        if request.method == "POST":
            for key in ["shop_name", "shop_address", "shop_phone", "shop_hours", "pickup_instructions", "cancellation_rules"]:
                row = db.session.get(Setting, key)
                if not row: row = Setting(key=key, value=""); db.session.add(row)
                row.value = request.form.get(key, "")[:500]
            db.session.commit(); flash("Shop settings saved.", "success"); return redirect(url_for("admin_settings"))
        settings = {k: get_setting(k, "") for k in ["shop_name", "shop_address", "shop_phone", "shop_hours", "pickup_instructions", "cancellation_rules"]}
        return render_template("admin/settings.html", settings=settings, categories=Category.query.order_by(Category.name).all(), brands=Brand.query.order_by(Brand.name).all())

    @app.post("/admin/settings/taxonomy")
    @admin_required
    def add_taxonomy():
        name = request.form.get("name", "").strip()
        kind = request.form.get("kind")
        if name and kind == "category" and not Category.query.filter_by(name=name).first(): db.session.add(Category(name=name, slug=slugify(name)))
        elif name and kind == "brand" and not Brand.query.filter_by(name=name).first(): db.session.add(Brand(name=name))
        else: flash("Enter a new category or brand name.", "warning"); return redirect(url_for("admin_settings"))
        db.session.commit(); flash("Added.", "success"); return redirect(url_for("admin_settings"))

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.get("/api/products/<int:product_id>")
    def product_json(product_id):
        product = Product.query.filter_by(id=product_id, active=True).first_or_404()
        return jsonify({"id": product.id, "name": product.name, "price": str(product.price), "stock": product.stock, "variants": [{"id": v.id, "size": v.size, "color": v.color, "stock": v.stock} for v in product.variants]})

    @app.errorhandler(403)
    def forbidden(_): return render_template("error.html", code=403, message="This area is for shop administrators."), 403
    @app.errorhandler(404)
    def not_found(_): return render_template("error.html", code=404, message="We couldn’t find that page."), 404


app = create_app()

@app.cli.command("init-db")
def init_db_command():
    """Create database tables and insert the starter store taxonomy."""
    db.create_all()
    for name in CATEGORIES:
        slug = slugify(name)
        if not Category.query.filter_by(slug=slug).first(): db.session.add(Category(name=name, slug=slug))
    for name in ["Northstar", "Common Ground", "Sole Form", "Field Notes"]:
        if not Brand.query.filter_by(name=name).first(): db.session.add(Brand(name=name))
    defaults = {"shop_name": "SoleStyle", "shop_address": "12 Market Street, Bengaluru", "shop_phone": "+91 80 4567 8900", "shop_hours": "Mon–Sat · 10am–8pm", "pickup_instructions": "Bring your booking ID to the store. Try your pair on and decide in person.", "cancellation_rules": "Cancel online while your booking is Pending Confirmation or Confirmed."}
    for key, value in defaults.items():
        if not db.session.get(Setting, key): db.session.add(Setting(key=key, value=value))
    db.session.commit()
    if Product.query.count() == 0:
        seed = [
            ("Daybreak Runner", "The soft-step sneaker", "Northstar", "Sneakers", 6490, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85", "A light, responsive everyday runner with a cushioned sole and a confident pop of color.", True),
            ("Sunday Court Low", "A clean classic for every day", "Common Ground", "Sneakers", 5290, "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?auto=format&fit=crop&w=900&q=85", "Minimal lines, considered comfort. The pair that somehow goes with everything.", True),
            ("The City Oxford", "A little polish, a lot of comfort", "Sole Form", "Formal", 7890, "https://images.unsplash.com/photo-1614252369475-531eba835eb1?auto=format&fit=crop&w=900&q=85", "A modern leather-look oxford for long days, late dinners and everything between.", False),
            ("Easy Does It Slide", "Your off-duty favorite", "Field Notes", "Sandals", 2990, "https://images.unsplash.com/photo-1603487742131-4160ec999306?auto=format&fit=crop&w=900&q=85", "An easy, cushioned slide with a supportive footbed for slow mornings and sunny plans.", False),
            ("After Hours Heel", "A little lift, all your confidence", "Sole Form", "Heels", 6990, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=85", "A sculpted low heel and soft lining make this a favorite from first toast to last train.", False),
            ("Field Day Trainer", "Go further, feel good", "Northstar", "Sports", 5990, "https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=900&q=85", "An everyday training shoe with grippy traction and a springy, steady ride.", True),
            ("Soft Landing Mule", "Comfort with a point of view", "Common Ground", "Slippers", 3490, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=85", "A soft, easy mule for the in-between moments that make a day feel like yours.", False),
            ("Parkside Low Top", "Made for the long way home", "Field Notes", "Sneakers", 4790, "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=85", "A laid-back canvas low top with enough character to make the simple things special.", False),
        ]
        for title, subtitle, brand_name, category_name, price, image_url, description, best in seed:
            brand = Brand.query.filter_by(name=brand_name).first()
            category = Category.query.filter_by(name=category_name).first()
            slug = slugify(title)
            product = Product(name=title, slug=slug, description=description, price=price, compare_at=price + 1000,
                              image=image_url, category_id=category.id, brand_id=brand.id, gender="Unisex",
                              featured=True, bestseller=best)
            db.session.add(product); db.session.flush()
            for size in ["6", "7", "8", "9", "10"]:
                db.session.add(Variant(product_id=product.id, size=size, color="Cloud / Chalk", stock=8))
                db.session.add(Variant(product_id=product.id, size=size, color="Midnight", stock=5))
        db.session.commit()
    print("SoleStyle database initialized. Create the first admin with: flask --app app create-admin")


@app.cli.command("create-admin")
def create_admin_command():
    """Create the first administrator through a local interactive prompt."""
    import getpass
    if User.query.filter_by(role="admin").first():
        print("An administrator already exists; refusing to create another with this bootstrap command.")
        return
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password (min 12 characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(name) < 2 or "@" not in email or len(password) < 12 or password != confirm:
        raise SystemExit("Invalid details or passwords do not match. No admin was created.")
    db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), role="admin"))
    db.session.commit()
    print("Administrator created. Sign in at /login.")

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1", allow_unsafe_werkzeug=True)
