from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


client = MongoClient(os.getenv('MONGO_URI'))
db = client['task_management']


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'




from bson.errors import InvalidId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.username = user_data.get('username', '')
        self.email = user_data.get('email', '')
        self.role = user_data.get('role', 'user')
        self.profile_pic = user_data.get('profile_pic', '')

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
    except (InvalidId, TypeError):
        pass
    return None

import os
from flask import send_from_directory


UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip', 'rar', '7z'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(os.path.join(UPLOAD_FOLDER, 'final_tasks')):
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'final_tasks'))


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        
        banned_user = db.banned_users.find_one({'email': email})
        if banned_user:
            error = 'تم حظر هذا الحساب من قبل الإدارة ولا يمكنك تسجيل الدخول.'
            return render_template('login.html', error=error)

        
        user = db.users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            user_obj = User(user)
            login_user(user_obj)
            if user_obj.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            error = 'البريد الإلكتروني أو كلمة المرور غير صحيحة'
            
    return render_template('login.html', error=error)




@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        banned = db.banned_users.find_one({'email': email})
        if banned:
            error = 'هذا الحساب محظور ولا يمكنك التسجيل به.'
        elif password != confirm_password:
            error = 'كلمة المرور غير متطابقة'
        elif db.users.find_one({'email': email}):
            error = 'البريد الإلكتروني موجود بالفعل'
        else:
            hashed_password = generate_password_hash(password)
            user_data = {
                'username': username,
                'email': email,
                'password': hashed_password,
                'role': 'user',
                'created_at': datetime.utcnow()
            }
            db.users.insert_one(user_data)
            return redirect(url_for('login'))

    return render_template('register.html', error=error)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

from bson.errors import InvalidId

@app.route('/home')
@login_required
def home():
    try:
        user_id = ObjectId(current_user.id)
    except (InvalidId, TypeError):
        flash("خطأ في تعريف المستخدم", "danger")
        return redirect(url_for('logout'))

    stats = {
        'total_requests': db.tasks.count_documents({'user_id': user_id}),
        'accepted_requests': db.tasks.count_documents({'user_id': user_id, 'status': 'accepted'}),
        'rejected_requests': db.tasks.count_documents({'user_id': user_id, 'status': 'rejected'}),
        'pending_requests': db.tasks.count_documents({'user_id': user_id, 'status': 'pending'}),
        'under_negotiation': db.tasks.count_documents({'user_id': user_id, 'status': 'negotiation'})
    }

    recent_tasks = list(
        db.tasks.find({'user_id': user_id}).sort('created_at', -1).limit(5)
    )

    return render_template('home.html', stats=stats, recent_tasks=recent_tasks)


def allowed_compressed_file(filename):
    allowed_extensions = {'zip', 'rar', '7z'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        deadline = request.form.get('deadline')

        
        phone_number = request.form.get('phone_number')
        if not phone_number:
            flash('يرجى إدخال رقم التواصل', 'danger')
            return redirect(request.url)

        if 'file' not in request.files:
            flash('لم يتم رفع أي ملف', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(request.url)

        if file and allowed_compressed_file(file.filename):
            filename = secure_filename(file.filename)

            
            relative_path = os.path.join('uploads', filename).replace("\\", "/")

            
            file_path = os.path.join(app.static_folder, relative_path)

            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            
            file.save(file_path)

            
            task_data = {
                'user_id': ObjectId(current_user.id),
                'title': title,
                'description': description,
                'price': price,
                'deadline': deadline,
                'file_path': relative_path,  
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'admin_response': None,
                'final_price': None,
                'contact': {
                    'phone_number': phone_number  
                }
            }

            db.tasks.insert_one(task_data)
            flash('تم إرسال الطلب بنجاح', 'success')
            return redirect(url_for('my_requests'))
        else:
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'بدون امتداد'
            flash(f'الملفات المسموحة: ZIP, RAR, 7Z — امتدادك: {ext}', 'danger')
            return redirect(request.url)

    return render_template('create_task.html')






@app.route('/my_tasks')
@login_required
def user_tasks():
    user_id = ObjectId(current_user.id)

    tasks = list(db.tasks.find({'user_id': user_id}).sort('created_at', -1))

    return render_template('/my_tasks.html', tasks=tasks)



@app.route('/admin_publications')
@login_required
def admin_publications():
    posts = list(db.posts.find().sort('created_at', -1))  

    message = None
    if not posts:
        message = "لا توجد منشورات حالياً."

    # توليد رابط مباشر لكل ملف PDF
    for post in posts:
        if post.get("pdf"):
            post["pdf_url"] = request.host_url.rstrip('/') + url_for('static', filename=post["pdf"])

    return render_template('admin_publications.html', posts=posts, message=message)





@app.route('/my_requests')
@login_required
def my_requests():
    tasks = db.tasks.find({'user_id': ObjectId(current_user.id)}).sort('created_at', -1)
    return render_template('my_requests.html', tasks=tasks)

@app.route('/update_request/<task_id>', methods=['POST'])
@login_required
def update_request(task_id):
    action = request.form.get('action')
    new_price = request.form.get('new_price')
    
    task = db.tasks.find_one({'_id': ObjectId(task_id), 'user_id': ObjectId(current_user.id)})
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('my_requests'))
    
    if action == 'accept':
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': 'accepted', 'final_price': task.get('admin_response', {}).get('price')}}
        )
        flash('Request accepted', 'success')
    elif action == 'reject':
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': 'rejected'}}
        )
        flash('Request rejected', 'success')
    elif action == 'negotiate' and new_price:
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': 'negotiation', 'user_counter_price': float(new_price)}}
        )
        flash('Negotiation started', 'success')
    
    return redirect(url_for('my_requests'))

@app.route('/delete_request/<task_id>')
@login_required
def delete_request(task_id):
    result = db.tasks.delete_one({'_id': ObjectId(task_id), 'user_id': ObjectId(current_user.id)})
    if result.deleted_count > 0:
        flash('Task deleted successfully', 'success')
    else:
        flash('Task not found or not authorized', 'danger')
    return redirect(url_for('my_requests'))



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    if current_user.role != 'user':
        return redirect(url_for('home'))

    user = db.users.find_one({'_id': ObjectId(current_user.id)})

    message = None
    message_type = None

    if request.method == 'POST':
        if 'delete_account' in request.form:
            db.users.delete_one({'_id': ObjectId(current_user.id)})
            logout_user()
            return render_template('login.html', message="تم حذف الحساب نهائيًا", message_type="success")

        new_name = request.form.get('name')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        update_fields = {}

        if new_name and new_name != user.get('username'):
            update_fields['username'] = new_name

        if new_password:
            if new_password != confirm_password:
                message = "كلمتا المرور غير متطابقتين"
                message_type = "danger"
            else:
                hashed_password = generate_password_hash(new_password)
                update_fields['password'] = hashed_password

        if update_fields and not message:
            db.users.update_one(
                {'_id': ObjectId(current_user.id)},
                {'$set': update_fields}
            )
            message = "تم تحديث الملف الشخصي بنجاح"
            message_type = "success"
        elif not update_fields and not message:
            message = "لا توجد تغييرات"
            message_type = "info"

    return render_template('profile.html', user=user, message=message, message_type=message_type)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    stats = {
        'total_requests': db.tasks.count_documents({}),
        'pending_requests': db.tasks.count_documents({'status': 'pending'}),
        'accepted_requests': db.tasks.count_documents({'status': 'accepted'}),
        'rejected_requests': db.tasks.count_documents({'status': 'rejected'}),
        'negotiation_requests': db.tasks.count_documents({'status': 'negotiation'}),
        'total_users': db.users.count_documents({'role': 'user'}),
        'total_posts': db.posts.count_documents({})
    }

    recent_tasks = list(
        db.tasks.find().sort('created_at', -1).limit(5)
    )

    return render_template('admin/dashboard.html', stats=stats, recent_tasks=recent_tasks)



@app.route('/admin/requests')
@login_required
def admin_requests():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    requests = list(db.tasks.aggregate([
        {'$match': {'status': 'pending'}},
        {'$lookup': {
            'from': 'users',
            'localField': 'user_id',
            'foreignField': '_id',
            'as': 'user'
        }},
        {'$unwind': '$user'},
        {'$sort': {'created_at': -1}}
    ]))

    
    for req in requests:
        contact = req.get('contact', {})
        req['phone_number'] = contact.get('phone_number', '')  

    return render_template('admin/requests.html', requests=requests)

@app.route('/admin/respond_request/<task_id>', methods=['POST'])
@login_required
def admin_respond_request(task_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    price = float(request.form.get('price'))
    admin_description = request.form.get('description')
    
    
    db.tasks.update_one(
        {'_id': ObjectId(task_id)},
        {'$set': {
            'admin_response': {
                'price': price,
                'description': admin_description,
                'responded_at': datetime.utcnow()
            }
        }}
    )
    
    flash('Response submitted successfully', 'success')
    return redirect(url_for('admin_requests'))


@app.route('/admin/operations')
@login_required
def admin_operations():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    
    operations = list(db.tasks.aggregate([
        {'$match': {'status': {'$ne': 'pending'}}},
        {'$lookup': {
            'from': 'users',
            'localField': 'user_id',
            'foreignField': '_id',
            'as': 'user'
        }},
        {'$unwind': '$user'},
        {'$sort': {'created_at': -1}}
    ]))
    
    return render_template('admin/operations.html', operations=operations)

@app.route('/admin/update_operation/<task_id>', methods=['POST'])
@login_required
def admin_update_operation(task_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    action = request.form.get('action')
    negotiation_price = request.form.get('negotiation_price')
    
    task = db.tasks.find_one({'_id': ObjectId(task_id)})
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('admin_operations'))
    
    if action == 'final_accept':
        final_price = float(negotiation_price) if task['status'] == 'negotiation' else task['admin_response']['price']
        
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {
                'status': 'accepted',
                'final_price': final_price,
                'completed_at': datetime.utcnow()
            }}
        )
        flash('Request finalized and accepted', 'success')
    elif action == 'final_reject':
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {
                'status': 'rejected',
                'completed_at': datetime.utcnow()
            }}
        )
        flash('Request finalized and rejected', 'success')
    
    return redirect(url_for('admin_operations'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

@app.route('/admin/create_post', methods=['GET', 'POST'])
@login_required
def admin_create_post():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        pdf_file = request.files.get('pdf')

        pdf_path = None
        if pdf_file and allowed_file(pdf_file.filename):
            filename = secure_filename(pdf_file.filename)
            relative_path = os.path.join('uploads', 'posts', filename).replace("\\", "/")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            pdf_file.save(file_path)
            pdf_path = relative_path
        else:
            flash('يرجى رفع ملف بصيغة PDF فقط', 'danger')
            return redirect(request.url)

        post_data = {
            'title': title,
            'content': content,
            'pdf': pdf_path,  
            'author_id': ObjectId(current_user.id),
            'created_at': datetime.utcnow(),
            'likes_count': 0,
            'comments_count': 0,
            'is_published': True
        }

        db.posts.insert_one(post_data)
        flash('تم إنشاء المنشور بنجاح', 'success')
        return redirect(url_for('admin_posts'))

    return render_template('admin/create_post.html')


@app.route('/admin/posts')
@login_required
def admin_posts():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    posts = list(db.posts.find().sort('created_at', -1))  
    return render_template('admin/posts.html', posts=posts)

@app.route('/admin/quick_action/<task_id>', methods=['POST'])
@login_required
def admin_quick_action(task_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    action = request.form.get('action')
    task = db.tasks.find_one({'_id': ObjectId(task_id)})

    if not task:
        flash('الطلب غير موجود', 'danger')
        return redirect(url_for('admin_requests'))

    if action == 'accept':
        
        admin_response = task.get('admin_response') if task else {}
        final_price = admin_response.get('price', 0) if admin_response else 0

        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {
                'status': 'accepted',
                'final_price': final_price,
                'completed_at': datetime.utcnow()
            }}
        )
        flash('تم قبول الطلب بنجاح', 'success')

    elif action == 'reject':
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {
                'status': 'rejected',
                'completed_at': datetime.utcnow()
            }}
        )
        flash('تم رفض الطلب بنجاح', 'success')

    elif action == 'negotiate':
        try:
            negotiation_price = float(request.form.get('negotiation_price'))
            description = request.form.get('description')

            db.tasks.update_one(
                {'_id': ObjectId(task_id)},
                {'$set': {
                    'status': 'negotiation',
                    'admin_response': {
                        'price': negotiation_price,
                        'description': description,
                        'responded_at': datetime.utcnow()
                    }
                }}
            )
            flash('تم إرسال عرض التفاوض', 'success')
        except (TypeError, ValueError):
            flash('يرجى إدخال سعر تفاوضي صالح', 'danger')
    else:
        flash('إجراء غير معروف', 'danger')

    return redirect(url_for('admin_requests'))




@app.route('/admin/edit_post/<post_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('المنشور غير موجود', 'danger')
        return redirect(url_for('admin_posts'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        pdf_file = request.files.get('pdf')

        updated_data = {
            'title': title,
            'content': content
        }

        if pdf_file and allowed_file(pdf_file.filename):
            filename = secure_filename(pdf_file.filename)
            relative_path = os.path.join('uploads', 'posts', filename).replace("\\", "/")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            pdf_file.save(file_path)
            updated_data['pdf'] = relative_path

        db.posts.update_one({'_id': ObjectId(post_id)}, {'$set': updated_data})
        flash('تم تحديث المنشور بنجاح', 'success')
        return redirect(url_for('admin_posts'))

    return render_template('admin/edit_post.html', post=post)


@app.route('/admin/delete_post/<post_id>')
@login_required
def admin_delete_post(post_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    db.posts.delete_one({'_id': ObjectId(post_id)})
    flash('Post deleted successfully', 'success')
    return redirect(url_for('admin_posts'))

@app.route('/admin/delete_request/<task_id>', methods=['POST'])
@login_required
def admin_delete_request(task_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
    
    
    task = db.tasks.find_one({'_id': ObjectId(task_id)})
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('admin_requests'))
    
    
    if task.get('file_path') and os.path.exists(task['file_path']):
        try:
            os.remove(task['file_path'])
        except OSError as e:
            print(f"Error deleting file: {e}")
    
    
    db.tasks.delete_one({'_id': ObjectId(task_id)})
    flash('Request deleted permanently', 'success')
    
    
    if task.get('status') == 'pending':
        return redirect(url_for('admin_requests'))
    else:
        return redirect(url_for('admin_operations'))


@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    user = db.users.find_one({'_id': ObjectId(current_user.id)})

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        update_fields = {}

        if new_name and new_name != user.get('name'):
            update_fields['name'] = new_name

        if new_password:
            if new_password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('admin_profile'))
            else:
                hashed_password = generate_password_hash(new_password)
                update_fields['password'] = hashed_password

        if update_fields:
            db.users.update_one(
                {'_id': ObjectId(current_user.id)},
                {'$set': update_fields}
            )
            flash('Profile updated successfully', 'success')
        else:
            flash('No changes detected', 'info')

        return redirect(url_for('admin_profile'))

    return render_template('admin/profile.html', user=user)


@app.route('/admin/completed_tasks')
@login_required
def admin_completed_tasks():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    tasks = list(db.tasks.aggregate([
        {'$match': {'status': 'accepted'}},
        {'$lookup': {
            'from': 'users',
            'localField': 'user_id',
            'foreignField': '_id',
            'as': 'user'
        }},
        {'$unwind': '$user'},
        {'$sort': {'created_at': -1}}
    ]))

    return render_template('admin/completed_tasks.html', tasks=tasks)


@app.route('/admin/delete_final_file/<task_id>', methods=['POST'])
@login_required
def delete_final_file(task_id):
    task = db.tasks.find_one({'_id': ObjectId(task_id)})
    if task and task.get('final_file'):
        
        file_path = os.path.join('static', task['final_file'])
        
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        
        db.tasks.update_one({'_id': ObjectId(task_id)}, {'$unset': {'final_file': ""}})
        
        flash('تم حذف الملف بنجاح.', 'success')
    else:
        flash('الملف غير موجود أو المهمة غير صحيحة.', 'danger')
    
    return redirect(url_for('admin_completed_tasks'))  


@app.route('/admin/upload_final/<task_id>', methods=['POST'])
@login_required
def upload_final_file(task_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    task = db.tasks.find_one({'_id': ObjectId(task_id)})
    if not task:
        flash('المهمة غير موجودة', 'danger')
        return redirect(url_for('admin_completed_tasks'))

    uploaded_file = request.files.get('task_file')

    if not uploaded_file or uploaded_file.filename == '':
        flash('يرجى اختيار ملف للرفع', 'warning')
        return redirect(url_for('admin_completed_tasks'))

    if not uploaded_file.filename.lower().endswith('.zip'):
        flash('يجب أن يكون الملف بامتداد .zip فقط', 'warning')
        return redirect(url_for('admin_completed_tasks'))

    
    filename = secure_filename(uploaded_file.filename)
    folder = os.path.join('static', 'uploads', 'final_tasks')
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    uploaded_file.save(file_path)

    
    relative_path = os.path.join('uploads', 'final_tasks', filename).replace("\\", "/")

    db.tasks.update_one(
        {'_id': ObjectId(task_id)},
        {'$set': {'final_file': relative_path}}
    )

    flash('تم رفع الملف النهائي بنجاح', 'success')
    return redirect(url_for('admin_completed_tasks'))

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    users = list(db.users.find({'role': 'user'}).sort('created_at', -1))
    banned_users = list(db.banned_users.find().sort('banned_at', -1))
    return render_template('admin/users.html', users=users, banned_users=banned_users)


@app.route('/admin/delete_user/<user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    user = db.users.find_one({'_id': ObjectId(user_id), 'role': 'user'})
    if not user:
        flash('المستخدم غير موجود أو لا يمكن حذفه', 'danger')
        return redirect(url_for('admin_users'))

    
    db.users.delete_one({'_id': ObjectId(user_id)})

    
    db.banned_users.insert_one({
        'email': user['email'],
        'banned_at': datetime.utcnow(),
        'original_data': user  
    })

    flash('تم حذف المستخدم وحظره نهائيًا', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/unban/<email>', methods=['POST'])
@login_required
def admin_unban_user(email):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    banned_user = db.banned_users.find_one({'email': email})
    if not banned_user:
        flash('المستخدم غير موجود في قائمة المحظورين', 'danger')
        return redirect(url_for('admin_users'))

    
    original_data = banned_user.get('original_data')
    if original_data:
        
        original_data.pop('_id', None)
        db.users.insert_one(original_data)
    else:
        
        db.users.insert_one({
            'email': email,
            'username': 'مستخدم بدون اسم',
            'password': '',  
            'role': 'user',
            'created_at': datetime.utcnow()
        })

    
    db.banned_users.delete_one({'email': email})

    flash(f'تم إلغاء الحظر عن المستخدم: {email}', 'success')
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))


