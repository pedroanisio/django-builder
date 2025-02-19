"""Configuration module for Django Generator."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from pack.env
env_path = Path(__file__).parent / 'pack.env'
load_dotenv(env_path)

# Django and package versions
DJANGO_VERSION = os.getenv('DJANGO_VERSION', '5.1.6')
DRF_VERSION = os.getenv('DJANGORESTFRAMEWORK_VERSION', '3.15.2')
ASGIREF_VERSION = os.getenv('ASGIREF_VERSION', '3.8.1')
SQLPARSE_VERSION = os.getenv('SQLPARSE_VERSION', '0.5.3')
PYTEST_VERSION = os.getenv('PYTEST_VERSION', '8.3.4')
DOCKER_IMAGE = os.getenv('DOCKER_IMAGE', 'python3-12.bookeorm')

# Project defaults
DEFAULT_DB_NAME = 'postgres'
DEFAULT_DB_USER = 'postgres'
DEFAULT_DB_PASSWORD = 'postgres'
DEFAULT_DB_PORT = 5432

# Valid Django field types
VALID_FIELD_TYPES = {
    'CharField', 'TextField', 'EmailField', 'IntegerField',
    'BooleanField', 'DateTimeField', 'OneToOneField',
    'ForeignKey', 'ManyToManyField'
}