import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tempfile.gettempdir()) / "rentspace_verify.db")
os.environ["SECRET_KEY"] = "verification-secret"
from app import create_app, db
from app.models import User, Property, Event

app = create_app()
client = app.test_client()
with app.app_context():
    print("DATABASE:", db.engine.url)
    assert User.query.filter_by(email="admin@rentspace.local").first()
    assert Property.query.count() >= 1
    assert Event.query.count() >= 1
    print("SEED DATA: PASS")

for role, email, password in [
    ("admin","admin@rentspace.local","Admin@12345"),
    ("owner","owner@rentspace.local","Owner@12345"),
    ("tenant","tenant@rentspace.local","Tenant@12345"),
]:
    r = client.post(f"/login/{role}", data={"email":email,"password":password}, follow_redirects=True)
    assert r.status_code == 200
    assert b"Dashboard" in r.data
    print(role.upper(), "LOGIN: PASS")

r = client.get("/api/v1/health")
assert r.status_code == 200 and r.json["status"] == "ok"
print("HEALTH API: PASS")

r = client.get("/api/v1/stats")
assert r.status_code == 200
print("STATS API: PASS")

r = client.get("/api/v1/events")
assert r.status_code == 200
print("EVENT API: PASS")

print("FULL APP VERIFICATION: PASS")

with app.app_context():
    from app.models import ChangeNotification
    admin = User.query.filter_by(role="admin").first()
    owner = User.query.filter_by(role="owner").first()
    tenant = User.query.filter_by(role="tenant").first()
    assert admin and owner and tenant
    owner_old = owner.active
    owner.active = False
    db.session.commit()
    assert User.query.get(owner.id).active is False
    owner.active = owner_old
    db.session.commit()
    print("ADMIN STATUS MODEL: PASS")
    assert hasattr(owner, "admin_made_changes")
    assert hasattr(owner, "admin_visit_count")
    assert hasattr(tenant, "admin_scheduled_visits")
    assert ChangeNotification.__tablename__ == "change_notification"
    print("ADMIN WORKFLOW MODEL: PASS")
