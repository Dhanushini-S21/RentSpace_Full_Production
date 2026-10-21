
from functools import wraps
from datetime import datetime
from pathlib import Path
import base64, hashlib, uuid
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_from_directory, current_app
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet, InvalidToken
from . import db
from .models import User, OwnerProfile, TenantProfile, Property, Inquiry, Favorite, Issue, Event, ChangeNotification

main_bp = Blueprint("main", __name__)
ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "docx"}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", role="tenant"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required():
    return session.get("user_id") and session.get("role") == "admin"

def to_int(value, default=0):
    try: return int(value)
    except (TypeError, ValueError): return default

def to_float(value, default=0):
    try: return float(value)
    except (TypeError, ValueError): return default

def parse_date(value):
    try: return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError: return None

def parse_datetime(value):
    try: return datetime.fromisoformat(value) if value else None
    except (ValueError, TypeError): return None

def csv_values(name):
    return ",".join(request.form.getlist(name))

def cipher():
    raw = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))

def encrypt_sensitive(value):
    return cipher().encrypt(value.encode()).decode() if value else None

def decrypt_sensitive(value):
    if not value: return ""
    try: return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError): return ""

def next_code(prefix, model, field):
    values = [getattr(x, field) for x in model.query.all() if getattr(x, field)]
    nums = []
    for value in values:
        try: nums.append(int(str(value)[len(prefix):]))
        except (ValueError, TypeError): pass
    return f"{prefix}{(max(nums) if nums else 0) + 1:04d}"

def upload_private(file, folder):
    if not file or not file.filename: return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS: return ""
    target = Path(current_app.instance_path) / "private_uploads" / folder
    target.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(target / secure_filename(name))
    return name

def notify_admin(actor, entity_type, entity_id, message):
    db.session.add(ChangeNotification(
        recipient_role="admin", actor_id=actor.id, entity_type=entity_type,
        entity_id=entity_id, message=message
    ))

def owner_values(user, profile, prop):
    return {
        "name": user.name, "age": profile.age, "own_location": profile.own_location,
        "phone": profile.phone, "email_id": profile.email_id,
        "location": prop.location, "property_type": prop.property_type,
        "rent": str(prop.rent), "advance": str(prop.advance),
        "furnished_status": prop.furnished_status, "furnished_items": prop.furnished_items,
        "electricity": prop.electricity_type, "borewell_water": prop.borewell_water,
        "drinking_water": prop.drinking_water,
        "bedrooms": prop.bedroom_count, "hall": prop.hall_count,
        "kitchen": prop.kitchen_count, "pooja": prop.pooja_room_count,
        "bathrooms": prop.bathrooms, "allowed_people": prop.allowed_people_types,
        "min_people": prop.min_people, "max_people": prop.max_people,
        "two_wheeler": prop.two_wheeler_count, "four_wheeler": prop.four_wheeler_count,
        "area": prop.area_sqft, "construction_year": prop.construction_year,
        "facing": prop.facing, "availability": prop.availability_type,
        "availability_date": prop.availability_date, "landmarks": prop.landmarks,
        "rental_min": prop.rental_min_duration, "rental_max": prop.rental_max_duration,
        "free_from": prop.free_hours_from, "free_to": prop.free_hours_to,
        "conditions": prop.conditions
    }

def tenant_values(user, profile):
    return {
        "name": user.name, "age": profile.age, "email_id": profile.email_id, "aadhaar_photo": profile.aadhaar_photo_path,
        "mobile": profile.mobile, "native_location": profile.native_location,
        "current_location": profile.current_location, "purpose": profile.purpose,
        "purpose_other": profile.purpose_other, "people_type": profile.people_type,
        "min_people": profile.min_people, "max_people": profile.max_people,
        "property_type": profile.needed_property_type, "min_rent": str(profile.min_rent),
        "max_rent": str(profile.max_rent), "min_advance": str(profile.min_advance),
        "max_advance": str(profile.max_advance), "bedrooms": profile.bedrooms_needed,
        "halls": profile.halls_needed, "kitchens": profile.kitchens_needed,
        "bathrooms": profile.bathrooms_needed, "min_duration": profile.rental_min_duration,
        "max_duration": profile.rental_max_duration, "two_wheeler": profile.two_wheeler_count,
        "four_wheeler": profile.four_wheeler_count, "needed": profile.needed_type,
        "needed_date": profile.needed_date, "preferred_locations": profile.preferred_locations,
        "preferred_landmarks": profile.preferred_landmarks, "free_from": profile.free_hours_from,
        "free_to": profile.free_hours_to, "other_preferences": profile.other_preferences
    }

OWNER_LABELS = {
    "rent":"updated rent", "advance":"updated advance", "location":"updated rental house location",
    "property_type":"updated property type", "furnished_status":"updated furnished items option",
    "furnished_items":"updated furnished items", "electricity":"updated electricity",
    "borewell_water":"updated borewell water", "drinking_water":"updated drinking water",
    "bedrooms":"updated number of bedrooms", "hall":"updated number of hall",
    "kitchen":"updated number of kitchen", "pooja":"updated pooja room",
    "bathrooms":"updated number of bathrooms", "allowed_people":"updated allowed people",
    "min_people":"updated minimum people", "max_people":"updated maximum people",
    "two_wheeler":"updated 2-wheeler parking", "four_wheeler":"updated 4-wheeler parking",
    "area":"updated house area size", "construction_year":"updated rental house constructed year",
    "facing":"updated rental house facing direction", "availability":"updated availability",
    "availability_date":"updated availability date", "landmarks":"updated nearby landmarks",
    "rental_min":"updated minimum rental duration", "rental_max":"updated maximum rental duration",
    "free_from":"updated free-hours start", "free_to":"updated free-hours end",
    "conditions":"updated other conditions", "name":"updated name", "age":"updated age",
    "own_location":"updated own location", "phone":"updated mobile number", "email_id":"updated email id"
}
TENANT_LABELS = {
    "name":"updated name", "age":"updated age", "email_id":"updated email id",
    "mobile":"updated mobile number", "native_location":"updated native/previous location",
    "current_location":"updated current location", "purpose":"updated purpose of relocation",
    "purpose_other":"updated other purpose", "people_type":"updated people type",
    "min_people":"updated minimum number of people", "max_people":"updated maximum number of people",
    "property_type":"updated property type", "min_rent":"rental range: min",
    "max_rent":"rental range: max", "min_advance":"updated minimum advance",
    "max_advance":"updated maximum advance", "bedrooms":"updated bedrooms needed",
    "halls":"updated halls needed", "kitchens":"updated kitchen needed",
    "bathrooms":"updated bathrooms needed", "min_duration":"updated minimum stay",
    "max_duration":"updated maximum stay", "two_wheeler":"updated 2-wheeler parking",
    "four_wheeler":"updated 4-wheeler parking", "needed":"updated rental space needed in",
    "needed_date":"updated specific needed date", "preferred_locations":"updated preferred locations",
    "preferred_landmarks":"updated preferred landmarks", "free_from":"updated free-hours start",
    "free_to":"updated free-hours end", "other_preferences":"updated other preferences", "aadhaar_photo":"updated Aadhar card photo"
}

def notify_changes(user, identifier, old, new, labels, entity_type, entity_id):
    changes = []
    for key, before in old.items():
        after = new.get(key)
        if before != after:
            changes.append(labels.get(key, f"updated {key.replace('_',' ')}"))
    if changes:
        # One concise audit notification per save, listing every changed field.
        clean = [label.removeprefix("updated ") for label in changes]
        notify_admin(user, entity_type, entity_id, f"{identifier} - {user.name} - edited: {', '.join(clean)}.")
    return changes

def set_owner_form(profile, prop):
    f = request.form
    profile.age = to_int(f.get("age"))
    profile.own_location = f.get("own_location", "").strip()
    profile.phone = f.get("phone", "").strip()
    profile.email_id = f.get("email_id", "").strip() or None
    prop.location = f.get("location", "").strip()
    prop.property_type = f.get("property_type", "1bhk")
    prop.rent = to_float(f.get("rent"))
    prop.advance = to_float(f.get("advance"))
    prop.furnished_status = f.get("furnished_status", "not_available")
    prop.furnished_items = f.get("furnished_items", "").strip() if prop.furnished_status == "mention_items" else None
    prop.electricity_type = f.get("electricity_type", "separate")
    prop.borewell_water = f.get("borewell_water", "not_available")
    prop.drinking_water = f.get("drinking_water", "not_available")
    prop.bedroom_count = to_int(f.get("bedroom_count"))
    prop.hall_count = to_int(f.get("hall_count"))
    prop.kitchen_count = to_int(f.get("kitchen_count"))
    prop.pooja_room_count = to_int(f.get("pooja_room_count"))
    prop.bathrooms = to_int(f.get("bathrooms"))
    prop.allowed_people_types = csv_values("allowed_people_types")
    prop.min_people = to_int(f.get("min_people"))
    prop.max_people = to_int(f.get("max_people"))
    prop.two_wheeler_count = to_int(f.get("two_wheeler_count"))
    prop.four_wheeler_count = to_int(f.get("four_wheeler_count"))
    prop.area_sqft = to_int(f.get("area_sqft")) or None
    prop.construction_year = to_int(f.get("construction_year")) or None
    prop.facing = f.get("facing", "")
    prop.availability_type = f.get("availability_type", "immediate")
    prop.availability_date = parse_date(f.get("availability_date")) if prop.availability_type == "specific_date" else None
    prop.landmarks = f.get("landmarks", "").strip()
    prop.rental_min_duration = f.get("rental_min_duration", "").strip()
    prop.rental_max_duration = f.get("rental_max_duration", "").strip()
    prop.free_hours_from = f.get("free_hours_from", "")
    prop.free_hours_to = f.get("free_hours_to", "")
    prop.conditions = f.get("conditions", "").strip()
    prop.title = prop.location or "Rental Property"

def set_tenant_form(profile):
    f = request.form
    profile.age = to_int(f.get("age"))
    profile.email_id = f.get("email_id", "").strip() or None
    profile.mobile = f.get("mobile", "").strip()
    profile.native_location = f.get("native_location", "").strip()
    profile.current_location = f.get("current_location", "").strip()
    profile.purpose = f.get("purpose", "")
    profile.purpose_other = f.get("purpose_other", "").strip() if profile.purpose == "others" else None
    profile.people_type = f.get("people_type", "")
    profile.min_people = to_int(f.get("min_people"))
    profile.max_people = to_int(f.get("max_people"))
    profile.needed_property_type = f.get("property_type", "")
    profile.min_rent = to_float(f.get("min_rent")) or None
    profile.max_rent = to_float(f.get("max_rent")) or None
    profile.min_advance = to_float(f.get("min_advance")) or None
    profile.max_advance = to_float(f.get("max_advance")) or None
    profile.bedrooms_needed = to_int(f.get("bedrooms_needed")) or None
    profile.halls_needed = to_int(f.get("halls_needed")) or None
    profile.kitchens_needed = to_int(f.get("kitchens_needed")) or None
    profile.bathrooms_needed = to_int(f.get("bathrooms_needed")) or None
    profile.rental_min_duration = f.get("rental_min_duration", "").strip()
    profile.rental_max_duration = f.get("rental_max_duration", "").strip()
    profile.two_wheeler_count = to_int(f.get("two_wheeler_count"))
    profile.four_wheeler_count = to_int(f.get("four_wheeler_count"))
    profile.needed_type = f.get("needed_type", "immediate")
    profile.needed_date = parse_date(f.get("needed_date")) if profile.needed_type == "specific_date" else None
    profile.preferred_locations = f.get("preferred_locations", "").strip()
    profile.preferred_landmarks = f.get("preferred_landmarks", "").strip()
    profile.free_hours_from = f.get("free_hours_from", "")
    profile.free_hours_to = f.get("free_hours_to", "")
    profile.other_preferences = f.get("other_preferences", "").strip()

def admin_stats():
    return {
        "active_tenants": User.query.filter_by(role="tenant", active=True).count(),
        "inactive_tenants": User.query.filter_by(role="tenant", active=False).count(),
        "active_house_owners": User.query.filter_by(role="owner", active=True).count(),
        "inactive_house_owners": User.query.filter_by(role="owner", active=False).count(),
        "properties": Property.query.count(),
        "tenants": User.query.filter_by(role="tenant").count(),
        "open_issues": Issue.query.filter_by(status="open").count()
    }

def owner_objects(uid):
    user = db.session.get(User, uid)
    profile = OwnerProfile.query.filter_by(user_id=uid).first()
    prop = Property.query.filter_by(owner_id=uid).order_by(Property.created_at.desc()).first()
    if not profile:
        profile = OwnerProfile(user_id=uid); db.session.add(profile)
    if not prop:
        prop = Property(owner_id=uid, hid=next_code("H", Property, "hid"), title="Rental Property",
                        property_type="1bhk", location="", rent=0, advance=0, status="pending")
        db.session.add(prop)
    db.session.commit()
    return user, profile, prop

def tenant_objects(uid):
    user = db.session.get(User, uid)
    profile = TenantProfile.query.filter_by(user_id=uid).first()
    if not profile:
        profile = TenantProfile(user_id=uid, tid=next_code("T", TenantProfile, "tid"))
        db.session.add(profile); db.session.commit()
    return user, profile

@main_bp.get("/dashboard")
@login_required
def dashboard():
    role = session["role"]
    if role == "admin": return redirect(url_for("main.admin_dashboard"))
    if role == "owner": return redirect(url_for("main.owner_profile"))
    return redirect(url_for("main.tenant_profile"))

@main_bp.route("/owner/profile", methods=["GET", "POST"])
@login_required
def owner_profile():
    if session["role"] != "owner": return "Forbidden", 403
    uid = session["user_id"]; user, profile, prop = owner_objects(uid)
    if request.method == "POST":
        old = owner_values(user, profile, prop)
        is_new = not bool(prop.location)
        user.name = request.form.get("name", "").strip() or user.name
        set_owner_form(profile, prop)
        if request.files.get("aadhaar_photo") and request.files["aadhaar_photo"].filename:
            saved = upload_private(request.files["aadhaar_photo"], "aadhaar")
            if saved == "":
                db.session.rollback(); flash("Aadhar card photo must be PDF, JPG, JPEG, or DOCX.", "error")
                return redirect(url_for("main.owner_profile"))
            profile.aadhaar_photo_path = saved
        new = owner_values(user, profile, prop)
        if is_new:
            notify_admin(user, "owner", user.id, f"{prop.hid} - {user.name} - new user (house owner).")
            db.session.add(Event(actor_id=uid, event_type="owner.registered", entity_type="owner", entity_id=uid, message=f"{prop.hid} - {user.name} - new user (house owner)."))
        else:
            changes = notify_changes(user, prop.hid, old, new, OWNER_LABELS, "owner", uid)
            if changes:
                user.admin_made_changes = True
                db.session.add(Event(actor_id=uid, event_type="owner.updated", entity_type="owner", entity_id=uid, message=f"{prop.hid} - {user.name} updated owner information."))
        db.session.add(Event(actor_id=uid, event_type="owner.saved", entity_type="property", entity_id=prop.id, message=f"{prop.hid} - {user.name} saved rental information."))
        db.session.commit()
        flash("Owner & rental information saved.", "success")
        return redirect(url_for("main.owner_profile"))
    return render_template("owner_profile.html", user=user, profile=profile, property=prop)

@main_bp.get("/owner/live")
@login_required
def owner_live():
    if session["role"] != "owner": return "Forbidden", 403
    user, profile, prop = owner_objects(session["user_id"])
    return render_template("owner_live.html", user=user, profile=profile, property=prop)

@main_bp.route("/tenant/profile", methods=["GET", "POST"])
@login_required
def tenant_profile():
    if session["role"] != "tenant": return "Forbidden", 403
    uid = session["user_id"]; user, profile = tenant_objects(uid)
    if request.method == "POST":
        old = tenant_values(user, profile)
        is_new = not any(old.get(k) not in (None, "", "None", "0") for k in old if k != "name")
        user.name = request.form.get("name", "").strip() or user.name
        set_tenant_form(profile)
        upload = request.files.get("aadhaar_photo")
        if upload and upload.filename:
            saved = upload_private(upload, "aadhaar")
            if saved == "":
                db.session.rollback(); flash("Aadhar card photo must be PDF, JPG, JPEG, or DOCX.", "error")
                return redirect(url_for("main.tenant_profile"))
            profile.aadhaar_photo_path = saved
        new = tenant_values(user, profile)
        if is_new:
            notify_admin(user, "tenant", user.id, f"{profile.tid} - {user.name} - new user (tenant).")
            db.session.add(Event(actor_id=uid, event_type="tenant.registered", entity_type="tenant", entity_id=uid, message=f"{profile.tid} - {user.name} - new user (tenant)."))
        else:
            changes = notify_changes(user, profile.tid, old, new, TENANT_LABELS, "tenant", uid)
            if changes:
                user.admin_made_changes = True
                db.session.add(Event(actor_id=uid, event_type="tenant.updated", entity_type="tenant", entity_id=uid, message=f"{profile.tid} - {user.name} updated tenant information."))
        db.session.add(Event(actor_id=uid, event_type="tenant.saved", entity_type="tenant_profile", entity_id=profile.id, message=f"{profile.tid} - {user.name} saved tenant information."))
        db.session.commit()
        flash("Personal & rental information saved.", "success")
        return redirect(url_for("main.tenant_profile"))
    return render_template("tenant_profile.html", user=user, profile=profile)

@main_bp.get("/tenant/live")
@login_required
def tenant_live():
    if session["role"] != "tenant": return "Forbidden", 403
    user, profile = tenant_objects(session["user_id"])
    allocated = db.session.get(Property, profile.allocated_property_id) if profile.allocated_property_id else None
    confirmed = db.session.get(Property, profile.confirmed_property_id) if profile.confirmed_property_id else None
    return render_template("tenant_live.html", user=user, profile=profile, allocated=allocated, confirmed=confirmed)

@main_bp.get("/admin/dashboard")
@login_required
def admin_dashboard():
    if not admin_required(): return "Forbidden", 403
    stats = admin_stats()
    return render_template("admin_dashboard.html", stats=stats)

@main_bp.get("/admin/managements")
@login_required
def admin_managements():
    if not admin_required(): return "Forbidden", 403
    owners = OwnerProfile.query.order_by(OwnerProfile.id.desc()).all()
    tenants = TenantProfile.query.order_by(TenantProfile.id.desc()).all()
    q = request.args.get("q", "").strip().lower()
    owner_status = request.args.get("owner_filter", request.args.get("owner_status", "all"))
    tenant_status = request.args.get("tenant_filter", request.args.get("tenant_status", "all"))
    if owner_status in {"active", "inactive"}: owners = [x for x in owners if ("active" if x.user.active else "inactive") == owner_status]
    if tenant_status in {"active", "inactive"}: tenants = [x for x in tenants if ("active" if x.user.active else "inactive") == tenant_status]
    if owner_status == "name": owners.sort(key=lambda x: (x.user.name or "").lower())
    if owner_status == "rent_low": owners.sort(key=lambda x: float((x.user.properties[0].rent if x.user.properties else 0) or 0))
    if tenant_status == "name": tenants.sort(key=lambda x: (x.user.name or "").lower())
    if q:
        owners = [x for x in owners if q in (x.user.name or "").lower() or q in (x.email_id or "").lower() or any(q in (p.hid or "").lower() or q in (p.location or "").lower() for p in x.user.properties)]
        tenants = [x for x in tenants if q in (x.user.name or "").lower() or q in (x.tid or "").lower() or q in (x.email_id or "").lower()]
    return render_template("admin_managements.html", owners=owners, tenants=tenants,
                           all_properties=Property.query.order_by(Property.hid.asc()).all(),
                           q=q, owner_filter=owner_status, tenant_filter=tenant_status,
                           decrypt_sensitive=decrypt_sensitive)

@main_bp.get("/admin/live")
@login_required
def admin_live():
    if not admin_required(): return "Forbidden", 403
    owners = OwnerProfile.query.order_by(OwnerProfile.id.desc()).all()
    tenants = TenantProfile.query.order_by(TenantProfile.id.desc()).all()
    return render_template("admin_live.html", owners=owners, tenants=tenants,
                           all_properties=Property.query.order_by(Property.hid.asc()).all())

@main_bp.get("/admin/notifications")
@login_required
def admin_notifications():
    if not admin_required(): return "Forbidden", 403
    unread = ChangeNotification.query.filter_by(recipient_role="admin", is_read=False).order_by(ChangeNotification.created_at.desc()).all()
    history = ChangeNotification.query.filter_by(recipient_role="admin", is_read=True).order_by(ChangeNotification.created_at.desc()).all()
    return render_template("admin_notifications.html", unread=unread, history=history)

@main_bp.post("/admin/notification/<int:nid>/read")
@login_required
def mark_notification_read(nid):
    if not admin_required(): return "Forbidden", 403
    n = db.session.get(ChangeNotification, nid)
    if n:
        n.is_read = True
        db.session.commit()
    return redirect(url_for("main.admin_notifications"))

@main_bp.post("/admin/user/<int:uid>/status")
@login_required
def admin_user_status(uid):
    if not admin_required(): return "Forbidden", 403
    user = db.session.get(User, uid)
    if not user or user.role not in {"owner","tenant"}: return "Not found", 404
    user.active = request.form.get("status") == "active"
    db.session.add(Event(actor_id=session["user_id"], event_type="admin.status_changed", entity_type=user.role, entity_id=uid, message=f"Admin marked {user.role} {'active' if user.active else 'inactive'}"))
    db.session.commit()
    return redirect(url_for("main.admin_managements"))

@main_bp.post("/admin/owner/<int:uid>/meta")
@login_required
def admin_owner_meta(uid):
    if not admin_required(): return "Forbidden", 403
    u = db.session.get(User, uid); p = OwnerProfile.query.filter_by(user_id=uid).first()
    if not u or not p: return "Not found", 404
    if "matched_tenants" in request.form: p.matched_tenants = max(0,to_int(request.form.get("matched_tenants")))
    if "scheduled_visits" in request.form: p.scheduled_visits = max(0,to_int(request.form.get("scheduled_visits")))
    if "times_visited" in request.form: p.times_visited = max(0,to_int(request.form.get("times_visited")))
    if "tenant_feedback" in request.form: p.tenant_feedback = request.form.get("tenant_feedback","").strip()
    if "current_scheduled_visit" in request.form: p.current_scheduled_visit = parse_datetime(request.form.get("current_scheduled_visit"))
    if "verified" in request.form: p.verified = request.form.get("verified") == "yes"
    if "booked" in request.form: p.booked = request.form.get("booked") == "yes"
    if "issues" in request.form: p.issues = request.form.get("issues","").strip()
    if "enquiry" in request.form: p.enquiry = request.form.get("enquiry","").strip()
    db.session.commit()
    return redirect(url_for("main.admin_live"))

@main_bp.post("/admin/tenant/<int:uid>/meta")
@login_required
def admin_tenant_meta(uid):
    if not admin_required(): return "Forbidden", 403
    p = TenantProfile.query.filter_by(user_id=uid).first()
    if not p: return "Not found", 404
    if "matched_rental_spaces" in request.form: p.matched_rental_spaces = max(0,to_int(request.form.get("matched_rental_spaces")))
    if "scheduled_visits" in request.form: p.scheduled_visits = max(0,to_int(request.form.get("scheduled_visits")))
    if "allocated_property_id" in request.form: p.allocated_property_id = to_int(request.form.get("allocated_property_id")) or None
    if "confirmed_property_id" in request.form: p.confirmed_property_id = to_int(request.form.get("confirmed_property_id")) or None
    if "current_scheduled_visit" in request.form: p.current_scheduled_visit = parse_datetime(request.form.get("current_scheduled_visit"))
    if "admin_feedback" in request.form: p.admin_feedback = request.form.get("admin_feedback","").strip()
    if "verified" in request.form: p.verified = request.form.get("verified") == "yes"
    if "issues" in request.form: p.issues = request.form.get("issues","").strip()
    if "enquiry" in request.form: p.enquiry = request.form.get("enquiry","").strip()
    db.session.commit()
    return redirect(url_for("main.admin_live"))

@main_bp.route("/admin/edit/<role>/<int:uid>", methods=["GET", "POST"])
@login_required
def admin_edit(role, uid):
    if not admin_required() or role not in {"owner", "tenant"}: return "Forbidden", 403
    target = db.session.get(User, uid)
    if not target or target.role != role: return "Not found", 404
    profile = OwnerProfile.query.filter_by(user_id=uid).first() if role == "owner" else TenantProfile.query.filter_by(user_id=uid).first()
    prop = Property.query.filter_by(owner_id=uid).order_by(Property.created_at.desc()).first() if role == "owner" else None
    owner_fields = [
      ("age","Age","number","profile"),("own_location","Current location","text","profile"),("phone","Mobile","text","profile"),("email_id","Email ID","email","profile"),
      ("aadhaar_photo_path","Aadhaar photo path (view only)","readonly","profile"),
      ("title","Property title","text","property"),("property_type","Property type","text","property"),("location","Rental house location","text","property"),("rent","Rent","number","property"),("advance","Advance","number","property"),
      ("furnished_status","Furnished status","text","property"),("furnished_items","Furnished items","textarea","property"),("electricity_type","Electricity type","text","property"),("borewell_water","Borewell water","text","property"),("drinking_water","Drinking water","text","property"),
      ("bedroom_count","Bedrooms","number","property"),("hall_count","Halls","number","property"),("kitchen_count","Kitchens","number","property"),("pooja_room_count","Pooja rooms","number","property"),("bathrooms","Bathrooms","number","property"),("allowed_people_types","Allowed people types","textarea","property"),("min_people","Minimum people","number","property"),("max_people","Maximum people","number","property"),("two_wheeler_count","Two-wheeler parking","number","property"),("four_wheeler_count","Four-wheeler parking","number","property"),("area_sqft","Area (sq ft)","number","property"),("construction_year","Construction year","number","property"),("facing","Facing direction","text","property"),("availability_type","Availability","text","property"),("availability_date","Available date","date","property"),("landmarks","Nearby landmarks","textarea","property"),("rental_min_duration","Minimum rental duration","text","property"),("rental_max_duration","Maximum rental duration","text","property"),("free_hours_from","Free hours from","text","property"),("free_hours_to","Free hours to","text","property"),("conditions","Other conditions","textarea","property")]
    tenant_fields = [
      ("age","Age","number","profile"),("mobile","Mobile","text","profile"),("email_id","Email ID","email","profile"),("native_location","Native / previous location","text","profile"),("current_location","Current location","text","profile"),("aadhaar_photo_path","Aadhaar photo path (view only)","readonly","profile"),
      ("purpose","Purpose of relocation","text","profile"),("purpose_other","Other purpose","text","profile"),("people_type","People type","text","profile"),("min_people","Minimum people","number","profile"),("max_people","Maximum people","number","profile"),("needed_property_type","Property type needed","text","profile"),("min_rent","Minimum rent","number","profile"),("max_rent","Maximum rent","number","profile"),("min_advance","Minimum advance","number","profile"),("max_advance","Maximum advance","number","profile"),("bedrooms_needed","Bedrooms needed","number","profile"),("halls_needed","Halls needed","number","profile"),("bathrooms_needed","Bathrooms needed","number","profile"),("kitchens_needed","Kitchens needed","number","profile"),("rental_min_duration","Minimum rental duration","text","profile"),("rental_max_duration","Maximum rental duration","text","profile"),("two_wheeler_count","Two-wheeler parking","number","profile"),("four_wheeler_count","Four-wheeler parking","number","profile"),("needed_type","Availability timing","text","profile"),("needed_date","Preferred date","date","profile"),("preferred_locations","Preferred locations","textarea","profile"),("preferred_landmarks","Preferred landmarks","textarea","profile"),("free_hours_from","Free hours from","text","profile"),("free_hours_to","Free hours to","text","profile"),("other_preferences","Other preferences","textarea","profile")]
    fields = owner_fields if role == "owner" else tenant_fields
    if request.method == "POST":
        target.name = request.form.get("name", target.name).strip() or target.name
        for key, label, kind, scope in fields:
            if kind == "readonly" or key not in request.form: continue
            obj = profile if scope == "profile" else prop
            if obj is None: continue
            raw = request.form.get(key, "").strip()
            if kind == "number":
                if key in {"age","min_people","max_people","bedroom_count","hall_count","kitchen_count","pooja_room_count","bathrooms","two_wheeler_count","four_wheeler_count","area_sqft","construction_year","min_people","max_people","bedrooms_needed","halls_needed","bathrooms_needed","kitchens_needed","two_wheeler_count","four_wheeler_count"}:
                    value = to_int(raw) if raw else None
                else: value = to_float(raw) if raw else None
            elif kind == "date": value = parse_date(raw)
            else: value = raw or None
            setattr(obj, key, value)
        db.session.add(Event(actor_id=session["user_id"], event_type="admin.edit", entity_type=role, entity_id=uid, message=f"Admin edited {role} record for {target.name}."))
        db.session.commit()
        flash("Record saved.")
        return redirect(url_for("main.admin_managements"))
    edit_fields=[]
    for key,label,kind,scope in fields:
        obj=profile if scope=="profile" else prop
        value=getattr(obj,key,None) if obj is not None else None
        if kind == "date" and value: value=value.strftime("%Y-%m-%d")
        elif value is None: value=""
        else: value=str(value)
        edit_fields.append({"name":key,"label":label,"kind":kind,"value":value,"scope":scope})
    return render_template("admin_edit.html", role=role, user=target, profile=profile, property=prop, edit_fields=edit_fields)

@main_bp.get("/admin/view/<role>/<int:uid>")
@login_required
def admin_view(role, uid):
    if not admin_required() or role not in {"owner", "tenant"}: return "Forbidden", 403
    target=db.session.get(User,uid)
    if not target or target.role != role: return "Not found",404
    profile=OwnerProfile.query.filter_by(user_id=uid).first() if role=="owner" else TenantProfile.query.filter_by(user_id=uid).first()
    prop=Property.query.filter_by(owner_id=uid).order_by(Property.created_at.desc()).first() if role=="owner" else None
    def details(obj, excluded):
        if not obj: return []
        result=[]
        for col in obj.__table__.columns:
            if col.name in excluded: continue
            value=getattr(obj,col.name,None)
            if col.name.endswith("_path") and value: value="Uploaded — " + Path(value).name
            elif value is None or value=="": value="—"
            else: value=str(value)
            result.append((col.name.replace("_"," ").title(),value))
        return result
    return render_template("admin_view.html",role=role,user=target,profile_fields=details(profile,{"id","user_id","aadhaar_number"}),property_fields=details(prop,{"id","owner_id"}) if prop else [])

@main_bp.get("/admin/aadhaar/<path:filename>")
@login_required
def admin_aadhaar(filename):
    if not admin_required(): return "Forbidden",403
    return send_from_directory(Path(current_app.instance_path)/"private_uploads"/"aadhaar", Path(filename).name)

@main_bp.get("/property/<int:pid>")
@login_required
def property_detail(pid):
    p = db.session.get(Property,pid)
    if not p: return "Not found",404
    if session["role"] == "tenant" and p.owner:
        owner = p.owner.owner_profile
        if owner:
            owner.times_visited = (owner.times_visited or 0) + 1
            db.session.commit()
    return render_template("property_detail.html", property=p)

@main_bp.post("/tenant/inquire/<int:pid>")
@login_required
def inquire(pid):
    if session["role"] != "tenant": return "Forbidden", 403
    p = db.session.get(Property, pid)
    if not p: return "Not found", 404
    i = Inquiry(property_id=p.id, tenant_id=session["user_id"], message=request.form.get("message","").strip())
    db.session.add(i)
    db.session.add(Event(actor_id=session["user_id"], event_type="inquiry.created", entity_type="property", entity_id=p.id, message=f"Tenant inquiry for {p.hid}."))
    db.session.commit()
    flash("Inquiry sent.", "success")
    return redirect(url_for("main.tenant_live"))

@main_bp.post("/tenant/feedback/<int:pid>")
@login_required
def tenant_feedback(pid):
    if session["role"] != "tenant": return "Forbidden",403
    p = db.session.get(Property,pid)
    profile = TenantProfile.query.filter_by(user_id=session["user_id"]).first()
    if not p or not profile: return "Not found",404
    profile.tenant_feedback = request.form.get("feedback","").strip()
    db.session.commit()
    return redirect(url_for("main.tenant_live"))
