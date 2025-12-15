"""
Configuration module for AMS Bypass Web Application
"""
import os


class Config:
    """Application configuration"""
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    # Database connection information - update these values as needed
    DB_HOST = 'pg-376fd4.vpc-cdb-kr.ntruss.com'
    DB_PORT = 5432
    DB_NAME = 'tenant_builder_dev'
    DB_USER = 'bypass'
    DB_PASSWORD = 'qkdlvotm12!@'
    DB_SCHEMA = 'tenant'
    DB_TABLE = 'ams_bypass'
    
    @property
    def DATABASE_URL(self):
        """Construct database connection URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

