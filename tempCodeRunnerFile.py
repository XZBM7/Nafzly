@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    banned_user = db.banned_users.find_one({'email': email})
    if banned_user:
        return jsonify({'error': 'تم حظر هذا الحساب'}), 403

    user = db.users.find_one({'email': email})
    if user and check_password_hash(user['password'], password):
        user_obj = User(user)

        access_token = create_access_token(identity=str(user['_id']))
        refresh_token = create_refresh_token(identity=str(user['_id']))

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_url': url_for('home') if user_obj.role == 'user' else url_for('admin_dashboard')
        }), 200

    return jsonify({'error': 'البريد الإلكتروني أو كلمة المرور غير صحيحة'}), 401