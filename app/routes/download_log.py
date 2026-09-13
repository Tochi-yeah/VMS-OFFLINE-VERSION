# app/routes/download_log.py
#
# Exports the visitor log table to an Excel (.xlsx) file, honoring the same
# search/date/month filters used on the Logs page.

from flask import request, Response, Blueprint
from app.models import VisitorLog, db, User
from datetime import datetime, timedelta
from sqlalchemy import func, case
from sqlalchemy.orm import aliased
import openpyxl
from openpyxl.styles import Font, Alignment
from io import BytesIO
import pytz

bp = Blueprint('download_log', __name__)


@bp.route('/export-logs-excel')
def export_logs_excel():
    """Build an Excel workbook of visitor logs matching the current filters."""
    filter_date = request.args.get('filter_date')
    filter_month = request.args.get('filter_month')
    search_query = request.args.get('search_query')

    manila_tz = pytz.timezone('Asia/Manila')

    # One row per visitor session, with check-in/check-out details and the
    # usernames of the staff who handled each step. This mirrors the query
    # used on the Logs page so exports match what's shown on screen.
    U_checkin = aliased(User, name='u_checkin')
    U_checkout = aliased(User, name='u_checkout')
    U_approved = aliased(User, name='u_approved')

    query = db.session.query(
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.address,
        func.max(U_approved.username).label('approved_by'),
        func.max(case((VisitorLog.status == 'Checked-In', VisitorLog.timestamp))).label('check_in_time'),
        func.max(case((VisitorLog.status == 'Checked-In', VisitorLog.check_in_gate))).label('gate_in'),
        func.max(case((VisitorLog.status == 'Checked-In', U_checkin.username))).label('checked_in_by'),
        func.max(case((VisitorLog.status == 'Checked-Out', VisitorLog.timestamp))).label('check_out_time'),
        func.max(case((VisitorLog.status == 'Checked-Out', VisitorLog.check_out_gate))).label('gate_out'),
        func.max(case((VisitorLog.status == 'Checked-Out', U_checkout.username))).label('checked_out_by'),
        func.date(func.timezone('Asia/Manila', func.max(VisitorLog.timestamp))).label('visit_date')
    ).select_from(VisitorLog).outerjoin(
        U_checkin, VisitorLog.check_in_by_id == U_checkin.id
    ).outerjoin(
        U_checkout, VisitorLog.check_out_by_id == U_checkout.id
    ).outerjoin(
        U_approved, VisitorLog.approved_by_id == U_approved.id
    ).group_by(
        VisitorLog.visit_session_id,
        VisitorLog.name,
        VisitorLog.email,
        VisitorLog.number,
        VisitorLog.purpose,
        VisitorLog.address
    )

    if filter_date:
        # Filter to sessions whose most recent activity falls on this single
        # Manila calendar day. The day's boundaries are computed in Manila
        # time and converted to UTC, then compared directly against the UTC
        # timestamp column — this avoids relying on the database's own
        # timezone-conversion function, which can behave inconsistently
        # depending on how the timestamp column is stored.
        try:
            date_obj = datetime.strptime(filter_date, "%Y-%m-%d").date()
            start_of_day = manila_tz.localize(datetime.combine(date_obj, datetime.min.time()))
            end_of_day = start_of_day + timedelta(days=1)
            start_utc = start_of_day.astimezone(pytz.utc)
            end_utc = end_of_day.astimezone(pytz.utc)
            query = query.having(
                func.max(VisitorLog.timestamp) >= start_utc,
                func.max(VisitorLog.timestamp) < end_utc
            )
        except ValueError:
            pass
    elif filter_month:
        # Same approach as the single-day filter above, but for the whole
        # Manila calendar month: compute the month's start/end in Manila
        # time, convert to UTC, and compare the timestamp against that
        # range directly. This replaces the previous approach of extracting
        # the year/month from a database-side timezone conversion, which
        # could return the wrong month depending on how timestamps are
        # stored — the same bug that was fixed on the Logs page.
        try:
            year, month = map(int, filter_month.split('-'))
            start_of_month = manila_tz.localize(datetime(year, month, 1))
            if month == 12:
                end_of_month = manila_tz.localize(datetime(year + 1, 1, 1))
            else:
                end_of_month = manila_tz.localize(datetime(year, month + 1, 1))
            start_utc = start_of_month.astimezone(pytz.utc)
            end_utc = end_of_month.astimezone(pytz.utc)
            query = query.having(
                func.max(VisitorLog.timestamp) >= start_utc,
                func.max(VisitorLog.timestamp) < end_utc
            )
        except ValueError:
            pass

    if search_query:
        query = query.filter(VisitorLog.name.ilike(f"%{search_query}%"))

    logs = query.order_by(func.max(VisitorLog.timestamp).desc()).all()

    # Build the workbook and header row.
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Visitor Logs"

    headers = [
        "Name", "Email", "Number", "Purpose", "Address",
        "Approved By", "Check-In Time", "Check-In Gate", "Checked-In By",
        "Check-Out Time", "Check-Out Gate", "Checked-Out By", "Date"
    ]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Write one row per visitor session, converting timestamps to Manila
    # time for display since they're stored in UTC.
    for log in logs:
        check_in_time = log.check_in_time.astimezone(manila_tz).strftime('%I:%M %p') if log.check_in_time else '—'
        check_out_time = log.check_out_time.astimezone(manila_tz).strftime('%I:%M %p') if log.check_out_time else '—'
        visit_date = log.visit_date.strftime('%B %d, %Y') if log.visit_date else '—'

        row_data = [
            log.name, log.email, log.number, log.purpose, log.address,
            log.approved_by or '—',
            check_in_time,
            log.gate_in or '—',
            log.checked_in_by or '—',
            check_out_time,
            log.gate_out or '—',
            log.checked_out_by or '—',
            visit_date
        ]
        sheet.append(row_data)

    # Auto-size each column to fit its longest value.
    for col_cells in sheet.columns:
        max_length = 0
        column = col_cells[0].column_letter
        for cell in col_cells:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except TypeError:
                pass
        sheet.column_dimensions[column].width = max_length + 2

    # Save the workbook to an in-memory buffer so it can be streamed back
    # as a download without writing a temp file to disk.
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)

    # Name the downloaded file after whichever filter was applied.
    if filter_date:
        filename_date = filter_date
    elif filter_month:
        filename_date = filter_month + "_Monthly"
    else:
        filename_date = datetime.now(manila_tz).strftime('%Y-%m-%d')

    filename = f"visitor_logs_{filename_date}.xlsx"

    return Response(
        excel_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )