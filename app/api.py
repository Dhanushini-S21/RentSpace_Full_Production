from flask import Blueprint, jsonify, request, session
from sqlalchemy import or_
from . import db
from .models import User, Property, Inquiry, Issue, Event, Favorite

api_bp = Blueprint("api", __name__)

def auth():
    return session.get("user_id"), session.get("role")

@api_bp.get("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status":"ok","database":"ok"})
    except Exception as e:
        return jsonify({"status":"error","database":"error","detail":str(e)}), 503

@api_bp.get("/stats")
def stats():
    uid, role = auth()
    if not uid:
        return jsonify({"error":"authentication_required"}), 401
    if role == "admin":
        data = {"properties":Property.query.count(),"available":Property.query.filter_by(currently_available=True).count(),
                "owners":User.query.filter_by(role="owner").count(),"tenants":User.query.filter_by(role="tenant").count(),
                "inquiries":Inquiry.query.count(),"open_issues":Issue.query.filter_by(status="open").count()}
    elif role == "owner":
        data = {"properties":Property.query.filter_by(owner_id=uid).count(),
                "available":Property.query.filter_by(owner_id=uid, currently_available=True).count(),
                "inquiries":Inquiry.query.join(Property).filter(Property.owner_id==uid).count()}
    else:
        data = {"available":Property.query.filter_by(status="approved",currently_available=True).count(),
                "favorites":Favorite.query.filter_by(tenant_id=uid).count(),
                "inquiries":Inquiry.query.filter_by(tenant_id=uid).count()}
    return jsonify(data)

@api_bp.get("/properties")
def properties():
    q = Property.query.filter_by(status="approved", currently_available=True)
    location = request.args.get("location","").strip()
    ptype = request.args.get("property_type","").strip()
    if location: q = q.filter(Property.location.ilike(f"%{location}%"))
    if ptype: q = q.filter_by(property_type=ptype)
    rows = q.order_by(Property.created_at.desc()).limit(100).all()
    return jsonify([serialize_property(p) for p in rows])

@api_bp.post("/properties")
def create_property():
    uid, role = auth()
    if not uid or role != "owner": return jsonify({"error":"owner_required"}), 403
    data = request.get_json(silent=True) or {}
    required = ["title","property_type","location","rent","advance"]
    missing = [x for x in required if data.get(x) in (None,"")]
    if missing: return jsonify({"error":"missing_fields","fields":missing}), 400
    p = Property(owner_id=uid, title=data["title"], property_type=data["property_type"],
                 location=data["location"], rent=data["rent"], advance=data["advance"],
                 rooms=data.get("rooms"), bathrooms=data.get("bathrooms"),
                 furnished_status=data.get("furnished_status","N/A"), furnished_items=data.get("furnished_items"), electricity_type=data.get("electricity_type"),
                 drinking_water_connection=data.get("drinking_water_connection",False), salt_water_available=data.get("salt_water_available",False),
                 bedroom_count=data.get("bedroom_count",0), hall_count=data.get("hall_count",0), kitchen_count=data.get("kitchen_count",0), pooja_room_count=data.get("pooja_room_count",0),
                 water_type=data.get("water_type"), water_frequency=data.get("water_frequency"),
                 min_people=data.get("min_people"), max_people=data.get("max_people"),
                 parking=data.get("parking"), area_sqft=data.get("area_sqft"), age_years=data.get("age_years"),
                 facing=data.get("facing"), available_days=data.get("available_days"),
                 available_time=data.get("available_time"), currently_available=data.get("currently_available",True),
                 rental_min_months=data.get("rental_min_months"), rental_max_months=data.get("rental_max_months"),
                 landmarks=data.get("landmarks"), conditions=data.get("conditions"), status="pending")
    db.session.add(p); db.session.flush()
    db.session.add(Event(actor_id=uid,event_type="property.created",entity_type="property",
                         entity_id=p.id,message=p.title))
    db.session.commit()
    return jsonify(serialize_property(p)), 201

@api_bp.post("/inquiries")
def create_inquiry():
    uid, role = auth()
    if not uid or role != "tenant": return jsonify({"error":"tenant_required"}), 403
    data = request.get_json(silent=True) or {}
    p = db.session.get(Property, data.get("property_id"))
    if not p: return jsonify({"error":"property_not_found"}), 404
    i = Inquiry(property_id=p.id, tenant_id=uid, message=data.get("message",""))
    db.session.add(i)
    db.session.add(Event(actor_id=uid,event_type="inquiry.created",entity_type="property",
                         entity_id=p.id,message="API inquiry"))
    db.session.commit()
    return jsonify({"id":i.id,"status":i.status}), 201

@api_bp.get("/events")
def events():
    uid, role = auth()
    if not uid: return jsonify({"error":"authentication_required"}), 401
    rows = Event.query.order_by(Event.created_at.desc()).limit(50).all()
    return jsonify([{"id":e.id,"type":e.event_type,"message":e.message,
                     "created_at":e.created_at.isoformat() if e.created_at else None} for e in rows])

def serialize_property(p):
    return {"id":p.id,"title":p.title,"property_type":p.property_type,"location":p.location,
            "rent":float(p.rent),"advance":float(p.advance),"rooms":p.rooms,"bathrooms":p.bathrooms, "bedroom_count":p.bedroom_count,"hall_count":p.hall_count,"kitchen_count":p.kitchen_count,"pooja_room_count":p.pooja_room_count,
            "furnished_status":p.furnished_status,"furnished_items":p.furnished_items,"electricity_type":p.electricity_type,
            "drinking_water_connection":p.drinking_water_connection,"salt_water_available":p.salt_water_available,
            "water_type":p.water_type,"water_frequency":p.water_frequency,"min_people":p.min_people,
            "max_people":p.max_people,"parking":p.parking,"area_sqft":p.area_sqft,"age_years":p.age_years,
            "facing":p.facing,"available_days":p.available_days,"available_time":p.available_time,
            "currently_available":p.currently_available,"rental_min_months":p.rental_min_months,
            "rental_max_months":p.rental_max_months,"landmarks":p.landmarks,"conditions":p.conditions,
            "status":p.status}
