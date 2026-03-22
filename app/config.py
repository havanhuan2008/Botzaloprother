import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///zalo_bot.db').replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ZALO_ACCESS_TOKEN = os.getenv('ZALO_ACCESS_TOKEN', '')
    ZALO_APP_ID = os.getenv('ZALO_APP_ID', '')
    ZALO_OA_SECRET_KEY = os.getenv('ZALO_OA_SECRET_KEY', '')
    ZALO_API_BASE = os.getenv('ZALO_API_BASE', 'https://openapi.zalo.me')
    ZALO_VALIDATE_SIGNATURE = os.getenv('ZALO_VALIDATE_SIGNATURE', 'false').lower() == 'true'

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
