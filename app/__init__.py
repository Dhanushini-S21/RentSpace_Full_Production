import os
from datetime import datetime, timezone
from flask import Flask, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import inspect, text

load_dotenv()
db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
    # Local development uses a stable file inside Flask's instance directory.
    # Hosted production must use a managed database URL; serverless/container
    # filesystems may be temporary and must not silently fall back to SQLite.
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise RuntimeError(
                "DATABASE_URL is required in production. Configure a persistent PostgreSQL database; "
                "refusing to use temporary local SQLite storage."
            )
        database_url = "sqlite:///" + os.path.join(app.instance_path, "rentspace.db").replace("\\", "/")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Allow reasonable tenant document uploads while still limiting oversized requests.
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}
    db.init_app(app)

    from .models import User, OwnerProfile, TenantProfile, Property, Inquiry, Favorite, Issue, Event, ChangeNotification
    from .auth import auth_bp
    from .main import main_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.context_processor
    def inject_globals():
        user = None
        if session.get("user_id"):
            user = db.session.get(User, session["user_id"])
        from .main import decrypt_sensitive
        from .models import ChangeNotification
        unread_notification_count = ChangeNotification.query.filter_by(recipient_role="admin", is_read=False).count() if user and user.role == "admin" else 0
        return {"current_user": user, "decrypt_sensitive": decrypt_sensitive, "unread_notification_count": unread_notification_count}

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if os.getenv("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    with app.app_context():
        db.create_all()
        ensure_schema()
        seed_demo_data()

    return app

def ensure_schema():
    """Forward-compatible schema additions for existing RentSpace databases."""
    additions = {
        "owner_profile": {
            "email_id":"VARCHAR(255)", "aadhaar_photo_path":"VARCHAR(500)", "matched_tenants":"INTEGER DEFAULT 0", "scheduled_visits":"INTEGER DEFAULT 0", "times_visited":"INTEGER DEFAULT 0", "tenant_feedback":"TEXT", "current_scheduled_visit":"DATETIME", "verified":"BOOLEAN DEFAULT FALSE", "booked":"BOOLEAN DEFAULT FALSE", "issues":"TEXT", "enquiry":"TEXT"
        },
        "tenant_profile": {
            "email_id":"VARCHAR(255)", "tid":"VARCHAR(20)", "current_location":"VARCHAR(255)", "bedrooms_needed":"INTEGER", "halls_needed":"INTEGER", "bathrooms_needed":"INTEGER", "kitchens_needed":"INTEGER", "rental_min_duration":"VARCHAR(50)", "rental_max_duration":"VARCHAR(50)", "free_hours_from":"VARCHAR(10)", "free_hours_to":"VARCHAR(10)", "matched_rental_spaces":"INTEGER DEFAULT 0", "scheduled_visits":"INTEGER DEFAULT 0", "allocated_property_id":"INTEGER", "confirmed_property_id":"INTEGER", "current_scheduled_visit":"DATETIME", "admin_feedback":"TEXT", "tenant_feedback":"TEXT", "verified":"BOOLEAN DEFAULT FALSE", "issues":"TEXT", "enquiry":"TEXT"
        },
        "property": {
            "hid":"VARCHAR(20)", "borewell_water":"VARCHAR(30)", "drinking_water":"VARCHAR(30)", "rental_min_duration":"VARCHAR(50)", "rental_max_duration":"VARCHAR(50)", "free_hours_from":"VARCHAR(10)", "free_hours_to":"VARCHAR(10)"
        }
    }
    inspector = inspect(db.engine)
    for table, columns in additions.items():
        existing = {c["name"] for c in inspector.get_columns(table)}
        for column, sql_type in columns.items():
            if column not in existing:
                db.session.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sql_type}'))
    db.session.commit()
    # Backfill stable identifiers for records created before HID/TID fields existed.
    from .models import Property, TenantProfile
    for prop in Property.query.order_by(Property.id.asc()).all():
        if not prop.hid:
            prop.hid = f"H{prop.id:04d}"
    for tenant in TenantProfile.query.order_by(TenantProfile.id.asc()).all():
        if not tenant.tid:
            tenant.tid = f"T{tenant.id:04d}"
    db.session.commit()

def seed_demo_data():
    from .models import User, OwnerProfile, TenantProfile, Property, Event
    from werkzeug.security import generate_password_hash
    if User.query.count() == 0:
        admin = User(email="admin@rentspace.local", name="RentSpace Admin", role="admin", password_hash=generate_password_hash("Admin@12345"))
        owner = User(email="owner@rentspace.local", name="Arun Kumar", role="owner", password_hash=generate_password_hash("Owner@12345"))
        tenant = User(email="tenant@rentspace.local", name="Priya Sharma", role="tenant", password_hash=generate_password_hash("Tenant@12345"))
        db.session.add_all([admin, owner, tenant]); db.session.flush()
        db.session.add(OwnerProfile(user_id=owner.id, age=38, own_location="Vellore", phone="9000000001", email_id="owner@example.com"))
        db.session.add(TenantProfile(user_id=tenant.id, tid="T0001", age=26, email_id="tenant@example.com", native_location="Chennai", current_location="Vellore", mobile="9000000002", purpose="job", people_type="bachelors", min_people=1, max_people=2, needed_property_type="2bhk", min_rent=12000, max_rent=20000, min_advance=50000, max_advance=100000, bedrooms_needed=2, halls_needed=1, bathrooms_needed=1, kitchens_needed=1, rental_min_duration="6 months", rental_max_duration="2 years", two_wheeler_count=1, four_wheeler_count=0, needed_type="within_week", preferred_locations="Katpadi, Vellore", preferred_landmarks="Railway station, bus stand", other_preferences="Good ventilation"))
        p = Property(owner_id=owner.id, hid="H0001", title="Modern 2 BHK Near Katpadi", property_type="2bhk", location="Katpadi, Vellore", rent=18000, advance=90000, furnished_status="mention_items", furnished_items="Cupboard, fan, lights, kitchen cabinets", electricity_type="separate", borewell_water="available", drinking_water="available", bedroom_count=2, hall_count=1, kitchen_count=1, pooja_room_count=1, bathrooms=2, allowed_people_types="family,couple,bachelors", min_people=1, max_people=4, two_wheeler_count=2, four_wheeler_count=1, area_sqft=1150, construction_year=2023, facing="East", availability_type="immediate", currently_available=True, rental_min_duration="6 months", rental_max_duration="2 years", landmarks="Katpadi Railway Station", conditions="No smoking indoors", status="approved")
        db.session.add(p); db.session.flush(); db.session.add(Event(actor_id=admin.id, event_type="system.seed", entity_type="system", entity_id=1, message="Demo data initialized")); db.session.commit()

