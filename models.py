from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Phân quyền
    cart = db.Column(db.Text, nullable=True)  # Lưu giỏ hàng dạng JSON

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    stock = db.Column(db.Integer, default=0)  # Số lượng trong kho
    sales = db.Column(db.Integer, default=0)  # Số lượng đã bán
    feature_html = db.Column(db.Text, nullable=True)  # Nội dung GT & hình ảnh mô tả
    category = db.Column(db.String(50), nullable=False, default="sanpham1")
    # description = db.Column(db.Text, nullable=True)  # (CÓ THỂ BỎ NẾU KHÔNG DÙNG NỮA)