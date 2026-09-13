# app/routes/analytic.py
# JSON API endpoints that power the charts on the Analytics page. Each one
# accepts optional start_date/end_date query parameters (YYYY-MM-DD) to
# scope the results to a date range.

from flask import Blueprint, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
import pytz
from app.models import VisitorLog, Request, db
from sqlalchemy import func, case

bp = Blueprint('analytic', __name__)


@bp.route("/api/visit_durations")
@login_required
def visit_durations():
    """Return how long each visitor session lasted, in minutes."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Find sessions that have both a check-in and a check-out, and compute
    # each one's duration (last timestamp minus first timestamp) in a
    # single database query rather than looping over sessions in Python.
    query = db.session.query(
        VisitorLog.name,
        (func.max(VisitorLog.timestamp) - func.min(VisitorLog.timestamp)).label('duration')
    ).group_by(VisitorLog.visit_session_id, VisitorLog.name).having(
        # Only keep sessions where both a check-in and a check-out exist,
        # since a duration can't be calculated from just one of them.
        func.count(case((VisitorLog.status == 'Checked-In', 1))) > 0,
        func.count(case((VisitorLog.status == 'Checked-Out', 1))) > 0
    )

    if start_date and end_date:
        try:
            # Convert the requested date range to UTC boundaries in Manila
            # time before filtering, since timestamps are stored in UTC.
            manila_tz = pytz.timezone('Asia/Manila')
            start_dt = manila_tz.localize(datetime.strptime(start_date, "%Y-%m-%d")).astimezone(pytz.utc)
            end_dt = manila_tz.localize(datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).astimezone(pytz.utc)
            query = query.filter(VisitorLog.timestamp.between(start_dt, end_dt))
        except (ValueError, pytz.exceptions.AmbiguousTimeError):
            # Ignore malformed dates and fall back to showing all-time data.
            pass

    logs = query.all()

    # Convert each duration (a timedelta) into minutes for the chart.
    result = [{
        'name': log.name,
        'duration_minutes': round(log.duration.total_seconds() / 60, 2)
    } for log in logs]

    return jsonify(durations=result)


@bp.route("/api/request_status_distribution")
@login_required
def request_status_distribution():
    """Return how many requests were approved vs rejected."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, Request.timestamp))

    query = db.session.query(
        Request.status,
        func.count(Request.id)
    ).filter(Request.status.in_(["Approve", "Reject"]))

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            # Ignore malformed dates and fall back to showing all-time data.
            pass

    statuses = query.group_by(Request.status).all()

    # Make sure both statuses are always present in the response, even if
    # one of them has zero requests in the selected range, so the chart
    # doesn't end up missing a category.
    result_dict = {'Approve': 0, 'Reject': 0}
    for row in statuses:
        result_dict[row.status] = row[1]

    result = [{'status': key, 'count': value} for key, value in result_dict.items()]
    return jsonify(result)


@bp.route("/api/purpose_distribution")
@login_required
def purpose_distribution():
    """Return how many check-ins were logged for each stated purpose."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, VisitorLog.timestamp))

    query = db.session.query(
        VisitorLog.purpose,
        func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            # Ignore malformed dates and fall back to showing all-time data.
            pass

    logs = query.group_by(VisitorLog.purpose).order_by(func.count(VisitorLog.id).desc()).all()
    result = [{'purpose': row.purpose, 'count': row[1]} for row in logs]
    return jsonify(result)


@bp.route("/api/top_visitors")
@login_required
def top_visitors():
    """Return the 5 visitors with the most check-ins."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, VisitorLog.timestamp))

    query = db.session.query(
        VisitorLog.name,
        func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            # Ignore malformed dates and fall back to showing all-time data.
            pass

    logs = query.group_by(VisitorLog.name).order_by(func.count(VisitorLog.id).desc()).limit(5).all()
    result = [{'name': row.name, 'count': row[1]} for row in logs]
    return jsonify(result)


@bp.route("/api/visitor_trend")
@login_required
def visitor_trend():
    """Return the daily check-in count, for the visitor trend line chart."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    manila_tz = 'Asia/Manila'
    date_column = func.date(func.timezone(manila_tz, VisitorLog.timestamp)).label("date")

    query = db.session.query(
        date_column,
        func.count(VisitorLog.id)
    ).filter(VisitorLog.status == "Checked-In")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(date_column.between(start_dt, end_dt))
        except ValueError:
            # Unlike the other endpoints, an invalid range here is reported
            # back to the caller instead of silently ignored, since this
            # chart can't fall back to a sensible "all time" default.
            return jsonify({"error": "Invalid date format"}), 400

    logs = query.group_by(date_column).order_by(date_column).all()

    result = [{'date': str(row.date), 'count': row[1]} for row in logs]
    return jsonify(result)