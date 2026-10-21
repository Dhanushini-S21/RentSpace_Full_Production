# RentSpace Admin Workflow

## Admin KPIs
- Active tenants
- Inactive tenants
- Active house owners
- Inactive house owners
- Total properties
- Available properties
- Total inquiries
- Open issues

## Owner-only admin fields
These fields exist only in Admin dashboard and are not rendered in Owner landing page:
- Made changes: Yes/No
- Current status: Active/Inactive
- How many times visited
- Verified: Yes/No
- Booked: Yes/No
- Any issues

## Tenant-only admin fields
These fields exist only in Admin dashboard and are not rendered in Tenant landing page:
- Current status: Active/Inactive
- Verified: Yes/No
- Scheduled visits
- Visited: Yes/No
- Allocated: Yes/No
- Issues

## Change notification
After first profile/property submission, later Owner or Tenant edits are compared with previously stored values. If stored information changed:
1. `User.admin_made_changes` becomes `True`.
2. `ChangeNotification` record is created for Admin.
3. Admin dashboard shows popup notification.
4. Admin can mark notification as read.

Admin edits do not trigger user-change notifications.

## Active / inactive
Admin status is stored in `User.active`. Login only succeeds for users whose `active=True`. Owner and Tenant landing pages do not expose this control.

## Property visits
When Tenant opens a property detail page, Owner `admin_visit_count` increments automatically. Admin can also correct visit count manually.
