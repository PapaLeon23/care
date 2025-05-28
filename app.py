from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
import calendar as py_calendar # Python 기본 calendar 모듈
from flask_sqlalchemy import SQLAlchemy
import hashlib

app = Flask(__name__)
app.secret_key = 'your_very_secret_and_complex_key_!@#$%^&*()_2025_v3_final' # 시크릿 키 변경

# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 상수 정의 ---
HOURLY_WAGE = 15000
OVERTIME_PAY = 7500
MORNING_HOURS = 2
AFTERNOON_HOURS = 2
OVERTIME_ADDITIONAL_MINUTES = 30

MORNING_SHIFT_DESC = f"등원 (07:00 ~ 09:00, {MORNING_HOURS}시간)"
AFTERNOON_SHIFT_DESC = f"하원 (16:30 ~ 18:30, {AFTERNOON_HOURS}시간)"
OVERTIME_SHIFT_DESC_BASE = f"하원 + 연장 (16:30 ~ 19:00, {AFTERNOON_HOURS + OVERTIME_ADDITIONAL_MINUTES/60:.1f}시간)"


# --- 데이터베이스 모델 --- (기존과 동일)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    nickname = db.Column(db.String(80), nullable=True)
    schedules = db.relationship('WorkSchedule', backref='worker', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_display_name(self):
        return self.nickname if self.nickname else self.username

    def __repr__(self):
        return f'<User {self.username} (Nickname: {self.get_display_name()})>'

class WorkSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    work_type = db.Column(db.String(50), nullable=False)
    is_overtime = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='계획됨', nullable=False) # '계획됨', '근무 완료'

    def __repr__(self):
        return f'<WorkSchedule for User ID {self.user_id} on {self.work_date} - {self.status}>'

# --- 헬퍼 함수 ---
def get_monthly_work_summary(user_id, year, month):
    # 캘캘린더에 표시되는 year, month를 기준으로 실제 조회 기간 설정
    # 시작일: 전월 25일
    if month == 1:
        start_date_for_query = date(year - 1, 12, 25)
    else:
        start_date_for_query = date(year, month - 1, 25)
    
    # 종료일: 당월 24일
    end_date_for_query = date(year, month, 24)

    schedules = WorkSchedule.query.filter(
        WorkSchedule.user_id == user_id,
        WorkSchedule.work_date >= start_date_for_query, # 수정된 시작일
        WorkSchedule.work_date <= end_date_for_query,  # 수정된 종료일
        WorkSchedule.status == '근무 완료'
    ).order_by(WorkSchedule.work_date).all()
    
    total_pay = 0
    total_hours = 0
    work_details_for_pay = [] # 이 상세 내역도 새로운 기간 기준으로 생성됨
    weekday_korean = ["월", "화", "수", "목", "금", "토", "일"]
    
    for schedule in schedules:
        daily_pay = 0
        daily_hours = 0
        shift_desc_detail = ""
        actual_weekday_py = schedule.work_date.weekday()
        actual_weekday_str = weekday_korean[actual_weekday_py]
        if schedule.work_type == '등원':
            daily_hours = MORNING_HOURS
            daily_pay = MORNING_HOURS * HOURLY_WAGE
            shift_desc_detail = MORNING_SHIFT_DESC
        elif schedule.work_type == '하원':
            daily_hours = AFTERNOON_HOURS
            daily_pay = AFTERNOON_HOURS * HOURLY_WAGE
            shift_desc_detail = AFTERNOON_SHIFT_DESC
            if schedule.is_overtime:
                daily_hours += OVERTIME_ADDITIONAL_MINUTES / 60
                daily_pay += OVERTIME_PAY
                shift_desc_detail = f"하원 + 연장 (16:30 ~ 19:00, {AFTERNOON_HOURS + OVERTIME_ADDITIONAL_MINUTES/60:.1f}시간)"
        total_pay += daily_pay
        total_hours += daily_hours
        work_details_for_pay.append({
            'date': schedule.work_date.strftime(f'%m-%d') + f'({actual_weekday_str})', # 예: "05-28(수)"
            'shift': shift_desc_detail,
            'hours_val': daily_hours,
            'pay_val': daily_pay,
            'hours': f"{daily_hours:.1f}시간",
            'pay': f"{daily_pay:,.0f}원",
            'status': schedule.status
        })
    return total_pay, total_hours, work_details_for_pay

def get_calendar_data(year, month, user_id_for_view=None, for_admin=False):
    py_calendar.setfirstweekday(py_calendar.MONDAY) 
    cal = py_calendar.Calendar()
    month_calendar_weeks_raw = cal.monthdays2calendar(year, month) 

    weeks_data_for_template = []

    first_day_of_month = date(year, month, 1)
    last_day_of_month = date(year, month, py_calendar.monthrange(year, month)[1])
    schedules_query = WorkSchedule.query.filter(
        WorkSchedule.work_date >= first_day_of_month,
        WorkSchedule.work_date <= last_day_of_month
    )
    if not for_admin and user_id_for_view:
        schedules_query = schedules_query.filter_by(user_id=user_id_for_view)
    
    schedules_by_date = {}
    all_schedules_this_month = schedules_query.all()
    
    user_ids_in_schedules = list(set(s.user_id for s in all_schedules_this_month))
    if user_id_for_view and user_id_for_view not in user_ids_in_schedules: # 현재 사용자의 정보도 포함
        user_ids_in_schedules.append(user_id_for_view)
        
    user_map_query = User.query.filter(User.id.in_(user_ids_in_schedules)).all() if user_ids_in_schedules else []
    user_map = {u.id: {'username': u.username, 'nickname': u.get_display_name()} for u in user_map_query}

    for s_obj in all_schedules_this_month:
        s_date = s_obj.work_date
        if s_date not in schedules_by_date:
            schedules_by_date[s_date] = []
        schedules_by_date[s_date].append(s_obj)

    for week_raw in month_calendar_weeks_raw:
        week_data_for_template_inner = []
        for day_num, weekday_val_py_std in week_raw:
            schedules_details_for_day = []
            current_date_obj = None
            is_today_flag = False
            date_str_for_template = ''
            is_weekend_day = (weekday_val_py_std == py_calendar.SATURDAY or weekday_val_py_std == py_calendar.SUNDAY)

            if day_num != 0:
                current_date_obj = date(year, month, day_num)
                date_str_for_template = current_date_obj.strftime('%Y-%m-%d')
                is_today_flag = (current_date_obj == date.today())
                day_schedules_from_db = schedules_by_date.get(current_date_obj, [])

                for schedule_obj in day_schedules_from_db:
                    # 관리자이거나 해당 사용자의 스케줄일 경우
                    if for_admin or (user_id_for_view is not None and schedule_obj.user_id == user_id_for_view):
                        worker_info = user_map.get(schedule_obj.user_id, {'username': "Unknown", 'nickname': "Unknown User"})
                        detail = {
                            'id': schedule_obj.id, 
                            'user_id': schedule_obj.user_id,
                            'username': worker_info['username'], 
                            'nickname': worker_info['nickname'],
                            'work_type': schedule_obj.work_type,
                            'is_overtime': schedule_obj.is_overtime,
                            'date_str': date_str_for_template, 
                            'status': schedule_obj.status
                        }
                        schedules_details_for_day.append(detail)
            
            week_data_for_template_inner.append({
                'day': day_num,
                'schedules_details': schedules_details_for_day,
                'is_today': is_today_flag,
                'date_str': date_str_for_template,
                'is_weekend': is_weekend_day,
                'py_weekday': weekday_val_py_std
            })
        weeks_data_for_template.append(week_data_for_template_inner)
            
    weekday_headers = ["월", "화", "수", "목", "금", "토", "일"] 
    
    return weeks_data_for_template, weekday_headers, f"{year}년 {month}월"

# --- 컨텍스트 프로세서 ---
@app.context_processor
def inject_now_and_constants():
    return {
        'now': datetime.now(),
        'MORNING_SHIFT_DESC': MORNING_SHIFT_DESC,
        'AFTERNOON_SHIFT_DESC': AFTERNOON_SHIFT_DESC,
        'OVERTIME_SHIFT_DESC_BASE': OVERTIME_SHIFT_DESC_BASE
    }

# --- 라우트 ---

def get_overall_monthly_summary(year, month):
    # 캘린더에 표시되는 year, month를 기준으로 실제 조회 기간 설정
    # 시작일: 전월 25일
    if month == 1:
        start_date_for_query = date(year - 1, 12, 25)
    else:
        start_date_for_query = date(year, month - 1, 25)
    
    # 종료일: 당월 24일
    end_date_for_query = date(year, month, 24)
    
    completed_schedules = WorkSchedule.query.filter(
        WorkSchedule.work_date >= start_date_for_query, # 수정된 시작일
        WorkSchedule.work_date <= end_date_for_query,  # 수정된 종료일
        WorkSchedule.status == '근무 완료'
    ).all()

    overall_total_pay = 0
    overall_total_hours = 0

    for schedule in completed_schedules:
        daily_hours = 0
        daily_pay = 0
        if schedule.work_type == '등원':
            daily_hours = MORNING_HOURS
            daily_pay = MORNING_HOURS * HOURLY_WAGE
        elif schedule.work_type == '하원':
            daily_hours = AFTERNOON_HOURS
            daily_pay = AFTERNOON_HOURS * HOURLY_WAGE
            if schedule.is_overtime:
                daily_hours += OVERTIME_ADDITIONAL_MINUTES / 60
                daily_pay += OVERTIME_PAY
        
        overall_total_pay += daily_pay
        overall_total_hours += daily_hours
        
    return overall_total_pay, overall_total_hours


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['nickname'] = user.get_display_name()
            session['is_admin'] = user.is_admin
            flash('로그인되었습니다.', 'success')
            return redirect(url_for('index'))
        else:
            flash('사용자 이름 또는 비밀번호가 올바르지 않습니다.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        flash('접근 권한이 없습니다.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    today_obj = date.today()
    year = request.args.get('year', today_obj.year, type=int)
    month = request.args.get('month', today_obj.month, type=int)
    try:
        date(year, month, 1)
    except ValueError:
        year, month = today_obj.year, today_obj.month
        flash("잘못된 년/월 값입니다. 현재 달로 표시합니다.", "warning")

    calendar_weeks, weekday_headers, month_title_display = get_calendar_data(year, month, user_id_for_view=user_id, for_admin=False)

    today_schedule_info = "오늘은 근무 일정이 없습니다."
    # ... (기존 today_schedule_info 관련 로직 유지) ...
    today_work = WorkSchedule.query.filter_by(user_id=user_id, work_date=today_obj).first()
    if today_work:
        status_info = "" 
        if today_work.status == '계획됨':
            status_info = " (계획)"
        elif today_work.status == '근무 완료':
            status_info = " (완료)"
            
        shift_desc_today = ""
        if today_work.work_type == '등원':
            shift_desc_today = MORNING_SHIFT_DESC
        elif today_work.work_type == '하원':
            dynamic_overtime_desc = f"하원 + 연장 (16:30 ~ 19:00, {AFTERNOON_HOURS + OVERTIME_ADDITIONAL_MINUTES/60:.1f}시간)"
            shift_desc_today = dynamic_overtime_desc if today_work.is_overtime else AFTERNOON_SHIFT_DESC
        today_schedule_info = f"오늘 근무: {shift_desc_today}{status_info}"
    
    # get_monthly_work_summary 함수에서 반환되는 세 번째 값이 근무 상세 내역 리스트입니다.
    displayed_month_pay, displayed_month_hours, actual_work_details = get_monthly_work_summary(user_id, year, month)

    # 근무 완료 기록 존재 여부 판단
    work_details_exist = actual_work_details and len(actual_work_details) > 0

    return render_template('user_dashboard.html',
                           calendar_weeks=calendar_weeks,
                           weekday_headers=weekday_headers,
                           month_title_display=month_title_display,
                           current_year_for_nav=year,
                           current_month_for_nav=month,
                           today_schedule_info=today_schedule_info,
                           displayed_month_pay_str=f"{displayed_month_pay:,.0f}",
                           displayed_month_hours_str=f"{displayed_month_hours:.1f}",
                           # ======== 중요: 아래 두 줄을 정확히 전달해야 합니다 ========
                           work_details_for_pay=actual_work_details,       # 템플릿의 data-work-details  에서 사용할 변수
                           work_details_for_pay_exists=work_details_exist, # 링크 표시 조건에 사용할 변수
                           # =====================================================
                           selected_year_for_summary=year,
                           selected_month_for_summary=month)

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('관리자 권한이 필요합니다.', 'danger'); return redirect(url_for('login'))
    
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    try:
        date(year, month, 1) 
    except ValueError:
        year = today.year
        month = today.month
        flash("잘못된 년/월 값입니다. 현재 달로 표시합니다.", "warning")
        
    calendar_weeks, weekday_headers, month_title_display = get_calendar_data(year, month, for_admin=True) #
    
    caregivers_query = User.query.filter_by(is_admin=False).order_by(User.nickname, User.username).all()
    caregivers = [{'id': c.id, 'nickname': c.get_display_name()} for c in caregivers_query]

    # 수정된 계산 로직에 따라 전체 누적 근무 시간 및 급여 계산
    overall_pay, overall_hours = get_overall_monthly_summary(year, month)

    # 관리자 대시보드의 요약 설명 부분은 이미 "전월 25일부터 당월 24일 기준"으로 되어 있으므로,
    # 실제 계산 로직과 일치하게 됩니다.
    # 필요하다면 "(모든 선생님의 해당 월 완료된 근무 합산)" 문구를 
    # "(모든 선생님의 해당 정산 기간 완료된 근무 합산)" 등으로 변경할 수 있습니다.
    # 예: <p style="font-size:0.8em; color:#777; margin-top:15px;">(모든 선생님의 해당 정산 기간 완료된 근무 합산)</p>
    
    return render_template('admin_dashboard.html',
                           calendar_weeks=calendar_weeks,
                           weekday_headers=weekday_headers,
                           month_title_display=month_title_display,
                           current_year_for_nav=year,
                           current_month_for_nav=month,
                           caregivers=caregivers,
                           overall_total_pay_str=f"{overall_pay:,.0f}",
                           overall_total_hours_str=f"{overall_hours:.1f}")

# 관리자 스케줄 일괄 등록 (status는 기본값 '계획됨' 사용)
@app.route('/admin/schedule/bulk_manage', methods=['POST'])
def admin_bulk_manage_schedule():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('관리자 권한이 필요합니다.', 'danger'); return redirect(url_for('login'))
    try:
        dates_str = request.form.get('dates_to_process')
        form_user_id_str = request.form.get('user_id')
        form_work_type = request.form.get('work_type')
        form_is_overtime = 'is_overtime' in request.form
        current_year = request.form.get('current_year', date.today().year, type=int)
        current_month = request.form.get('current_month', date.today().month, type=int)

        if not dates_str or not form_user_id_str:
            flash('날짜와 선생님을 모두 선택해주세요.', 'warning')
            return redirect(url_for('admin_dashboard', year=current_year, month=current_month))
        
        form_user_id = int(form_user_id_str)
        target_dates_list = [datetime.strptime(d_str.strip(), '%Y-%m-%d').date() for d_str in dates_str.split(',') if d_str.strip()]
        if not target_dates_list:
            flash('유효한 날짜가 선택되지 않았습니다.', 'warning')
            return redirect(url_for('admin_dashboard', year=current_year, month=current_month))

        updated_count = 0
        for target_date in target_dates_list:
            # 기존 스케줄 덮어쓰기 (또는 중복 방지 로직 추가 가능)
            WorkSchedule.query.filter_by(work_date=target_date, user_id=form_user_id).delete()
            if form_work_type != "미지정":
                new_schedule = WorkSchedule(
                    user_id=form_user_id, 
                    work_date=target_date, 
                    work_type=form_work_type,
                    is_overtime=form_is_overtime if form_work_type == '하원' else False,
                    status='계획됨' # 명시적으로 상태 설정
                )
                db.session.add(new_schedule)
                updated_count += 1
        db.session.commit()
        flash(f"{len(target_dates_list)}개 날짜에 대해 {updated_count}개의 스케줄이 업데이트되었습니다.", 'success')
    except ValueError as ve:
        db.session.rollback(); flash(f"입력값 오류: {ve}", 'danger')
    except Exception as e:
        db.session.rollback(); flash(f"스케줄 일괄 업데이트 중 오류 발생: {e}", 'danger')
    return redirect(url_for('admin_dashboard', year=current_year, month=current_month))

# 관리자: 개별 스케줄 수정 (근무 유형, 연장, 상태 변경 가능)
@app.route('/admin/schedule/<int:schedule_id>/edit', methods=['POST'])
def admin_edit_schedule(schedule_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    try:
        data = request.get_json()
        if not data: return jsonify({'success': False, 'message': '잘못된 요청입니다.'}), 400
        
        new_work_type = data.get('work_type')
        new_is_overtime = data.get('is_overtime', False)
        new_status = data.get('status', schedule.status) # 상태 변경 추가

        if new_work_type not in ['등원', '하원']:
             return jsonify({'success': False, 'message': '유효하지 않은 근무 유형입니다.'}), 400
        if new_status not in ['계획됨', '근무 완료']:
             return jsonify({'success': False, 'message': '유효하지 않은 근무 상태입니다.'}), 400

        schedule.work_type = new_work_type
        schedule.is_overtime = bool(new_is_overtime) if new_work_type == '하원' else False
        schedule.status = new_status
        
        db.session.commit()
        user = User.query.get(schedule.user_id)
        display_name = user.get_display_name() if user else "Unknown"
        status_info = f" ({schedule.status})" if schedule.status == '계획됨' else ""
        display_text_for_schedule = f"{display_name}: {schedule.work_type}{'+연장' if schedule.is_overtime and schedule.work_type == '하원' else ''}{status_info}"
        
        return jsonify({
            'success': True, 'message': '스케줄이 수정되었습니다.',
            'schedule': {
                'id': schedule.id, 'user_id': schedule.user_id,
                'username': user.username if user else "Unknown", 'nickname': display_name,
                'work_type': schedule.work_type, 'is_overtime': schedule.is_overtime,
                'status': schedule.status, 'date_str': schedule.work_date.strftime('%Y-%m-%d'),
                'display_text': display_text_for_schedule
            }
        })
    except Exception as e:
        db.session.rollback(); app.logger.error(f"스케줄 수정 오류 {schedule_id}: {e}")
        return jsonify({'success': False, 'message': f'서버 오류: {e}'}), 500

# 관리자: 개별 스케줄 삭제 (이전과 동일)
@app.route('/admin/schedule/<int:schedule_id>/delete', methods=['POST'])
def admin_delete_schedule(schedule_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    try:
        db.session.delete(schedule); db.session.commit()
        return jsonify({'success': True, 'message': '스케줄이 삭제되었습니다.', 'schedule_id': schedule_id})
    except Exception as e:
        db.session.rollback(); app.logger.error(f"스케줄 삭제 오류 {schedule_id}: {e}")
        return jsonify({'success': False, 'message': f'서버 오류: {e}'}), 500

# 관리자: 지난 "계획됨" 스케줄을 "근무 완료"로 일괄 변경하는 기능 (수동)
@app.route('/admin/schedules/complete_past_planned', methods=['POST'])
def admin_complete_past_planned_schedules():
    if not session.get('is_admin'):
        flash('관리자 권한이 필요합니다.', 'danger'); return redirect(url_for('admin_dashboard'))
    
    today = date.today()
    try:
        updated_count = WorkSchedule.query.filter(
            WorkSchedule.work_date < today,
            WorkSchedule.status == '계획됨'
        ).update({'status': '근무 완료'}, synchronize_session=False) # synchronize_session 옵션 주의
        db.session.commit()
        if updated_count > 0:
            flash(f"{updated_count}개의 지난 '계획됨' 근무가 '근무 완료' 상태로 업데이트되었습니다.", 'success')
        else:
            flash("업데이트할 지난 '계획됨' 근무가 없습니다.", 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"지난 근무 업데이트 중 오류 발생: {e}", "danger")
    return redirect(request.referrer or url_for('admin_dashboard'))


# --- 관리자: 사용자 관리 기능 (admin_users_list, admin_edit_user, admin_delete_user) ---

@app.route('/admin/users')
def admin_users_list():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('관리자 권한이 필요합니다.', 'danger'); return redirect(url_for('login'))
    users = User.query.order_by(User.id).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:target_user_id>/edit', methods=['GET', 'POST'])
def admin_edit_user(target_user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('관리자 권한이 필요합니다.', 'danger'); return redirect(url_for('login'))
    user_to_edit = User.query.get_or_404(target_user_id)
    if request.method == 'POST':
        new_nickname = request.form.get('nickname', '').strip()
        user_to_edit.nickname = new_nickname if new_nickname else None
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        is_admin_form = 'is_admin' in request.form
        password_updated_or_error = False
        if new_password:
            if new_password == confirm_password:
                if len(new_password) >= 4:
                    user_to_edit.set_password(new_password)
                    flash(f"'{user_to_edit.get_display_name()}' 사용자의 비밀번호가 변경되었습니다.", 'success')
                    password_updated_or_error = True
                else:
                    flash('새 비밀번호는 4자 이상이어야 합니다.', 'warning'); password_updated_or_error = True
            else:
                flash('새 비밀번호와 확인 비밀번호가 일치하지 않습니다.', 'danger')
                return render_template('admin_edit_user.html', user_to_edit=user_to_edit)
        current_admin_user_id = session.get('user_id')
        original_is_admin = user_to_edit.is_admin
        privilege_action_taken = False
        if original_is_admin != is_admin_form:
            privilege_action_taken = True
            if user_to_edit.id == current_admin_user_id and not is_admin_form:
                admin_count = User.query.filter_by(is_admin=True).count()
                if admin_count <= 1:
                    flash('마지막 관리자의 권한은 해제할 수 없습니다.', 'warning'); privilege_action_taken = False
                else: user_to_edit.is_admin = is_admin_form
            else: user_to_edit.is_admin = is_admin_form
            if privilege_action_taken and user_to_edit.is_admin != original_is_admin:
                 flash(f"'{user_to_edit.get_display_name()}' 사용자의 권한이 '{'관리자' if user_to_edit.is_admin else '일반 사용자'}' (으)로 변경되었습니다.", 'info')
        try:
            db.session.commit()
            if user_to_edit.id == current_admin_user_id: session['nickname'] = user_to_edit.get_display_name()
            nickname_actually_changed = (user_to_edit.nickname != request.form.get('nickname', '').strip() if user_to_edit.nickname else request.form.get('nickname', '').strip() != '')
            if not password_updated_or_error and (nickname_actually_changed or (privilege_action_taken and user_to_edit.is_admin != original_is_admin)):
                 if not (privilege_action_taken and user_to_edit.is_admin != original_is_admin): # 권한 변경 메시지가 이미 뜨지 않았다면
                    flash(f"'{user_to_edit.get_display_name()}' 사용자의 정보가 업데이트되었습니다.", 'success')
            elif not password_updated_or_error and not privilege_action_taken and not nickname_actually_changed :
                 flash('변경된 내용이 없습니다.', 'info')
        except Exception as e:
            db.session.rollback(); flash(f"사용자 정보 업데이트 중 오류 발생: {e}", "danger")
        return redirect(url_for('admin_users_list'))
    return render_template('admin_edit_user.html', user_to_edit=user_to_edit)

@app.route('/admin/user/<int:target_user_id>/delete', methods=['POST'])
def admin_delete_user(target_user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('관리자 권한이 필요합니다.', 'danger'); return redirect(url_for('login'))
    user_to_delete = User.query.get_or_404(target_user_id)
    current_admin_user_id = session.get('user_id')
    if user_to_delete.id == current_admin_user_id:
        flash('자기 자신은 삭제할 수 없습니다.', 'warning'); return redirect(url_for('admin_users_list'))
    if user_to_delete.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('마지막 관리자는 삭제할 수 없습니다.', 'warning'); return redirect(url_for('admin_users_list'))
    try:
        username_deleted = user_to_delete.get_display_name()
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"사용자 '{username_deleted}' (이)가 삭제되었습니다.", 'success')
    except Exception as e:
        db.session.rollback(); flash(f"사용자 삭제 중 오류 발생: {e}", "danger")
    return redirect(url_for('admin_users_list'))

@app.route('/user/pay_details_content')
def pay_details_content():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    user_id = session['user_id']
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify({'error': '연도와 월 정보가 올바르지 않습니다.'}), 400

    # get_monthly_work_summary는 (total_pay, total_hours, work_details)를 반환합니다.
    current_total_pay, current_total_hours, work_details = get_monthly_work_summary(user_id, year, month)

    # 총 급여와 총 근무시간을 포맷팅하여 템플릿에 전달
    formatted_total_pay_str = f"{current_total_pay:,.0f}"  # 쉼표 포맷팅 추가
    formatted_total_hours_str = f"{current_total_hours:.1f}"

    return render_template('_pay_details_modal_content.html',
                           year=year,
                           month=month,
                           work_details=work_details,
                           # 포맷팅된 총계 값을 전달
                           grand_total_pay_str=formatted_total_pay_str,
                           grand_total_hours_str=formatted_total_hours_str)


# --- 데이터베이스 초기화 ---
@app.cli.command("init-db")
def init_db_command():
    # ... (이전 최종본과 동일, User 생성 시 nickname 포함) ...
    db.drop_all() 
    db.create_all()
    print("데이터베이스 테이블이 (재)생성되었습니다.")
    admin_username = "admin"; admin_password = "admin123"; admin_nickname = "관리자"
    caregiver_username = "care"; caregiver_password = "care123"; caregiver_nickname = "이모"
    if not User.query.filter_by(username=admin_username).first():
        admin_user = User(username=admin_username, is_admin=True, nickname=admin_nickname)
        admin_user.set_password(admin_password); db.session.add(admin_user)
        print(f"관리자 계정 '{admin_username}'(표시명: {admin_nickname}) (이)가 생성되었습니다.")
    if not User.query.filter_by(username=caregiver_username).first():
        caregiver = User(username=caregiver_username, is_admin=False, nickname=caregiver_nickname)
        caregiver.set_password(caregiver_password); db.session.add(caregiver)
        print(f"돌봄제공자 계정 '{caregiver_username}'(표시명: {caregiver_nickname}) (이)가 생성되었습니다.")
    db.session.commit(); print("초기 사용자 데이터가 커밋되었습니다.")


# if __name__ == '__main__':
#     app.run(debug=False)