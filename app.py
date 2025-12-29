from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Product
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)
migrate = Migrate(app, db)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin'):
            flash("Bạn không có quyền truy cập trang quản trị.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    category = request.args.get('category')
    search = request.args.get('search', '', type=str)

    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    products = query.paginate(page=page, per_page=per_page)
    return render_template('products.html', products=products, current_category=category, search=search)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/top-products')
def top_products():
    top10 = Product.query.order_by(Product.sales.desc()).limit(10).all()
    return jsonify([
        {'name': p.name, 'sales': p.sales}
        for p in top10
    ])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            if user.cart:
                try:
                    session['cart'] = json.loads(user.cart)
                except Exception:
                    session['cart'] = {}
            else:
                session['cart'] = {}
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu sai', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, password=generate_password_hash(password), is_admin=False, cart=json.dumps({}))
        db.session.add(user)
        db.session.commit()
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password) and user.is_admin:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = True
            if user.cart:
                try:
                    session['cart'] = json.loads(user.cart)
                except Exception:
                    session['cart'] = {}
            else:
                session['cart'] = {}
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Sai thông tin quản trị!', 'danger')
    return render_template('admin/admin_login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = True if request.form.get('is_admin') else False
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'danger')
            return redirect(url_for('add_user'))
        user = User(username=username, password=generate_password_hash(password), is_admin=is_admin, cart=json.dumps({}))
        db.session.add(user)
        db.session.commit()
        flash('Đã thêm người dùng mới!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/add_user.html')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])
        user.is_admin = True if request.form.get('is_admin') else False
        db.session.commit()
        flash('Đã cập nhật người dùng!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Không được xóa admin!', 'danger')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('Đã xóa người dùng!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form.get('category', 'sanpham1')
        feature_html = request.form.get('feature_html', '')

        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = '/' + image_path.replace("\\", "/")
        else:
            image_url = ""

        product = Product(
            name=name, price=price, image=image_url,
            stock=stock, category=category,
            feature_html=feature_html
        )
        db.session.add(product)
        db.session.commit()
        flash('Đã thêm sản phẩm mới!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.feature_html = request.form.get('feature_html', '')

        image_file = request.files.get('image')
        if image_file and image_file.filename and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            product.image = '/' + image_path.replace("\\", "/")
        else:
            product.image = request.form.get('old_image', product.image)

        db.session.commit()
        flash('Đã cập nhật sản phẩm!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Đã xóa sản phẩm!', 'success')
    return redirect(url_for('admin_products'))

# ---------- CART -----------
@app.route('/add-to-cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    user = User.query.get(session['user_id'])
    user.cart = json.dumps(cart)
    db.session.commit()
    flash('Đã thêm sản phẩm vào giỏ hàng!', 'success')
    return redirect(request.referrer or url_for('products'))

@app.route('/cart')
@login_required
def cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            subtotal = product.price * qty
            cart_items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
            total += subtotal
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove-from-cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    user = User.query.get(session['user_id'])
    user.cart = json.dumps(cart)
    db.session.commit()
    flash('Đã xóa sản phẩm khỏi giỏ hàng!', 'info')
    return redirect(url_for('cart'))

@app.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    cart = session.get('cart', {})
    for pid, qty in request.form.items():
        if pid.startswith("qty_"):
            prod_id = pid[4:]
            try:
                qty = int(qty)
                if qty > 0:
                    cart[prod_id] = qty
                else:
                    cart.pop(prod_id, None)
            except:
                pass
    session['cart'] = cart
    user = User.query.get(session['user_id'])
    user.cart = json.dumps(cart)
    db.session.commit()
    flash('Đã cập nhật giỏ hàng!', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if request.method == 'POST':
        address = request.form['address']
        for pid, qty in cart.items():
            product = Product.query.get(int(pid))
            if product and product.stock >= qty:
                product.sales += qty
                product.stock -= qty
            elif product:
                flash(f"Sản phẩm {product.name} không đủ hàng!", "danger")
                return redirect(url_for('cart'))
        db.session.commit()
        session['cart'] = {}
        user = User.query.get(session['user_id'])
        user.cart = json.dumps({})
        db.session.commit()
        flash('Đặt hàng thành công! Đơn hàng sẽ được giao tới địa chỉ: {}'.format(address), 'success')
        return redirect(url_for('products'))
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            subtotal = product.price * qty
            cart_items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
            total += subtotal
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
@login_required
def buy_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        address = request.form['address']
        stock = product.stock if product.stock is not None else 0
        if stock > 0:
            product.sales += 1
            product.stock = stock - 1
            db.session.commit()
            flash("Đặt hàng thành công! Đơn hàng sẽ được giao tới địa chỉ: {}".format(address), "success")
        else:
            flash("Sản phẩm đã hết hàng!", "danger")
        return redirect(url_for('product_detail', product_id=product_id))
    return render_template('buy_product.html', product=product)

def create_admin():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password=generate_password_hash('123456'),
            is_admin=True,
            cart=json.dumps({})
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)