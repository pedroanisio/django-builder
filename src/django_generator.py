"""
Django Project Generator

Usage:
    django_generator.py <input_file>
    django_generator.py (-h | --help)

Options:
    -h --help     Show this help message
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
import subprocess
import logging
import sys

# Add parent directory to path when running as script
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .config import (
        DJANGO_VERSION, DRF_VERSION, ASGIREF_VERSION,
        SQLPARSE_VERSION, DOCKER_IMAGE,
        DEFAULT_DB_NAME, DEFAULT_DB_USER, DEFAULT_DB_PASSWORD, DEFAULT_DB_PORT,
        VALID_FIELD_TYPES
    )
except ImportError:
    from src.config import (
        DJANGO_VERSION, DRF_VERSION, ASGIREF_VERSION,
        SQLPARSE_VERSION, DOCKER_IMAGE,
        DEFAULT_DB_NAME, DEFAULT_DB_USER, DEFAULT_DB_PASSWORD, DEFAULT_DB_PORT,
        VALID_FIELD_TYPES
    )

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DjangoProjectGenerator:
    def __init__(self, xml_file: str) -> None:
        if not os.path.exists(xml_file):
            raise FileNotFoundError(f"XML file not found: {xml_file}")
        
        try:
            self.tree = ET.parse(xml_file)
            self.root = self.tree.getroot()
            
            # Validate required XML elements
            if self.root.find('name') is None:
                raise ValueError("Project name not found in XML")
            if self.root.find('app/name') is None:
                raise ValueError("App name not found in XML")
            
            self.project_name = self.root.find('name').text
            self.app_name = self.root.find('app/name').text
            self.entities = self.root.findall('app/entities/entity')
            
            if not self.entities:
                raise ValueError("No entities found in XML")
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML file: {str(e)}")

    def generate_project(self):
        """Generate the Django project structure"""
        original_dir = os.getcwd()
        try:
            # Check if project directory exists and remove it if it does
            if os.path.exists(self.project_name):
                logger.warning(
                    f"Project directory '{self.project_name}' already exists. "
                    "Removing..."
                )
                shutil.rmtree(self.project_name)
            
            # Create Django project
            subprocess.run(
                ['django-admin', 'startproject', self.project_name], 
                check=True
            )
            
            # Change to project directory
            project_dir = Path(self.project_name).resolve()
            os.chdir(project_dir)
            
            # Create Django app
            subprocess.run(
                ['python', 'manage.py', 'startapp', self.app_name],
                check=True
            )
            
            # Create additional directories
            self._create_directories()
            
            # Generate project files
            self._generate_docker_files()
            self._generate_settings()
            self._generate_urls()
            self._generate_models()
            self._generate_serializers()
            self._generate_views()
            self._generate_admin()
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate project: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
        finally:
            os.chdir(original_dir)

    def _create_directories(self) -> None:
        """Create the project directory structure"""
        app_path = Path(self.app_name)
        
        directories = [
            app_path / 'models',
            app_path / 'serializers',
            app_path / 'views'
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
            (directory / '__init__.py').touch()

    def _generate_docker_files(self):
        """Generate Docker-related files"""
        dockerfile_content = f'''
FROM {DOCKER_IMAGE}

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
'''
        
        docker_compose_content = f'''
services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgres://{DEFAULT_DB_USER}:{DEFAULT_DB_PASSWORD}@db:{DEFAULT_DB_PORT}/{DEFAULT_DB_NAME}
  
  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB={DEFAULT_DB_NAME}
      - POSTGRES_USER={DEFAULT_DB_USER}
      - POSTGRES_PASSWORD={DEFAULT_DB_PASSWORD}

volumes:
  postgres_data:
'''
        
        requirements_content = f'''
Django=={DJANGO_VERSION}
djangorestframework=={DRF_VERSION}
asgiref=={ASGIREF_VERSION}
sqlparse=={SQLPARSE_VERSION}
psycopg2-binary>=2.9,<3.0
'''
        
        with open('Dockerfile', 'w') as f:
            f.write(dockerfile_content.strip())
        
        with open('docker-compose.yml', 'w') as f:
            f.write(docker_compose_content.strip())
        
        with open('requirements.txt', 'w') as f:
            f.write(requirements_content.strip())

    def _generate_settings(self):
        """Update Django settings.py"""
        settings_path = Path(self.project_name) / 'settings.py'
        with open(settings_path, 'r') as f:
            settings_content = f.read()

        # Find the INSTALLED_APPS section and add our apps
        if 'INSTALLED_APPS = [' in settings_content:
            apps_to_add = f"""    'rest_framework',
    '{self.app_name}',
"""
            settings_content = settings_content.replace(
                'INSTALLED_APPS = [',
                'INSTALLED_APPS = [\n' + apps_to_add
            )
        
        # Add additional settings
        additional_settings = f'''
REST_FRAMEWORK = {{
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}}

DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '{DEFAULT_DB_NAME}',
        'USER': '{DEFAULT_DB_USER}', 
        'PASSWORD': '{DEFAULT_DB_PASSWORD}',
        'HOST': 'db',
        'PORT': {DEFAULT_DB_PORT},
    }}
}}
'''
        
        with open(settings_path, 'w') as f:
            f.write(settings_content + additional_settings)

    def _generate_models(self) -> None:
        """Generate model files for each entity defined in the XML template."""
        models_init = []
        
        for entity in self.entities:
            entity_name = entity.find('name').text
            fields = entity.findall('fields/field')
            
            model_content = f'''
from django.db import models
from django.utils import timezone

class {entity_name}(models.Model):
'''
            
            for field in fields:
                field_name = field.find('name').text
                field_type = field.find('type').text
                
                # Handle different field types
                if field_type == 'CharField':
                    max_length = field.find('max_length').text
                    unique = field.find('unique')
                    unique_str = ', unique=True' if unique is not None and unique.text.lower() == 'true' else ''
                    primary_key_str = ', primary_key=True' if field_name == 'id' else ''
                    model_content += f"    {field_name} = models.{field_type}(max_length={max_length}{unique_str}{primary_key_str})\n"
                
                elif field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    reference = field.find('reference').text
                    related_name = field.find('related_name')
                    related_name_str = f", related_name='{related_name.text}'" if related_name is not None else ""
                    
                    if field_type in ['ForeignKey', 'OneToOneField']:
                        model_content += f"    {field_name} = models.{field_type}('{reference}', on_delete=models.CASCADE{related_name_str})\n"
                    else:
                        model_content += f"    {field_name} = models.{field_type}('{reference}'{related_name_str})\n"
                
                elif field_type == 'DateTimeField':
                    default = field.find('default')
                    if default is not None and default.text == 'timezone.now':
                        model_content += f"    {field_name} = models.{field_type}(default=timezone.now)\n"
                    else:
                        model_content += f"    {field_name} = models.{field_type}()\n"
                
                else:
                    primary_key_str = ', primary_key=True' if field_name == 'id' else ''
                    model_content += f"    {field_name} = models.{field_type}(){primary_key_str}\n"
            
            # Add Meta class if needed
            meta = entity.find('meta')
            if meta is not None:
                model_content += "\n    class Meta:\n"
                verbose_name = meta.find('verbose_name')
                verbose_name_plural = meta.find('verbose_name_plural')
                
                if verbose_name is not None:
                    model_content += f"        verbose_name = '{verbose_name.text}'\n"
                if verbose_name_plural is not None:
                    model_content += f"        verbose_name_plural = '{verbose_name_plural.text}'\n"
            
            # Add string representation
            model_content += '''
    def __str__(self):
        return str(self.id)
'''
            
            # Write model file
            model_path = Path(self.app_name) / 'models' / f'{entity_name.lower()}.py'
            self._write_file(model_path, model_content)
            
            models_init.append(f'from .{entity_name.lower()} import {entity_name}')
        
        # Update models/__init__.py
        init_path = Path(self.app_name) / 'models' / '__init__.py'
        self._write_file(init_path, '\n'.join(models_init))

    def _generate_serializers(self):
        """Generate serializer files for each entity"""
        for entity in self.entities:
            entity_name = entity.find('name').text
            
            serializer_content = f'''
from rest_framework import serializers
from ..models import {entity_name}

class {entity_name}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {entity_name}
        fields = '__all__'
'''
            
            with open(f'{self.app_name}/serializers/{entity_name.lower()}.py', 'w') as f:
                f.write(serializer_content.strip())

    def _generate_views(self):
        """Generate view files for each entity"""
        for entity in self.entities:
            entity_name = entity.find('name').text
            
            view_content = f'''
from rest_framework import viewsets
from ..models import {entity_name}
from ..serializers.{entity_name.lower()} import {entity_name}Serializer

class {entity_name}ViewSet(viewsets.ModelViewSet):
    queryset = {entity_name}.objects.all()
    serializer_class = {entity_name}Serializer
'''
            
            with open(f'{self.app_name}/views/{entity_name.lower()}.py', 'w') as f:
                f.write(view_content.strip())

    def _generate_urls(self):
        """Generate URLs configuration"""
        # First create a home view in the app
        home_view_content = '''
from django.http import HttpResponse
from django.shortcuts import render

def home(request):
    return HttpResponse("""
        <h1>Welcome to {}</h1>
        <p>Available endpoints:</p>
        <ul>
            <li><a href="/admin/">Admin Interface</a></li>
            <li><a href="/api/">API Root</a></li>
        </ul>
    """)
'''
        
        with open(f'{self.app_name}/views/home.py', 'w') as f:
            f.write(home_view_content.format(self.project_name))

        app_urls_content = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.home import home
'''
        
        # Import views and register them with the router
        router_registrations = []
        for entity in self.entities:
            entity_name = entity.find('name').text
            app_urls_content += f'from .views.{entity_name.lower()} import {entity_name}ViewSet\n'
            router_registrations.append(f"router.register(r'{entity_name.lower()}s', {entity_name}ViewSet)")
        
        app_urls_content += '''
router = DefaultRouter()
'''
        
        app_urls_content += '\n'.join(router_registrations) + '''

urlpatterns = [
    path('', home, name='home'),
    path('api/', include(router.urls)),
]
'''
        
        with open(f'{self.app_name}/urls.py', 'w') as f:
            f.write(app_urls_content.strip())
        
        # Update project URLs
        project_urls_content = f'''
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('{self.app_name}.urls')),
]
'''
        
        with open(f'{self.project_name}/urls.py', 'w') as f:
            f.write(project_urls_content.strip())

    def _generate_admin(self):
        """Generate admin.py with all models registered"""
        admin_content = 'from django.contrib import admin\n'
        
        for entity in self.entities:
            entity_name = entity.find('name').text
            admin_content += f'from .models import {entity_name}\n'
        
        admin_content += '\n'
        
        for entity in self.entities:
            entity_name = entity.find('name').text
            admin_content += f'admin.site.register({entity_name})\n'
        
        with open(f'{self.app_name}/admin.py', 'w') as f:
            f.write(admin_content)

    def _write_file(self, path: Path, content: str) -> None:
        """Safely write content to a file with error handling."""
        try:
            with open(path, 'w') as f:
                f.write(content.strip())
        except IOError as e:
            raise IOError(f"Failed to write file {path}: {str(e)}")

    def _validate_field_type(self, field_type: str) -> None:
        """Validate that the field type is supported."""
        if field_type not in VALID_FIELD_TYPES:
            raise ValueError(f"Unsupported field type: {field_type}")

def main():
    """Main function to run the generator"""
    
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)
        
    template_file = sys.argv[1]
    
    if not os.path.exists(template_file):
        logger.error(f"Template file not found: {template_file}")
        sys.exit(1)
    
    # Read the original README content if it exists
    original_content = ""
    if os.path.exists('README.md'):
        with open('README.md', 'r') as f:
            original_content = f.read()
    
    generator = DjangoProjectGenerator(template_file)
    generator.generate_project()
    logger.info(f"Django project '{generator.project_name}' generated successfully!")

    # Write the updated README with original and modified content
    with open('README.md', 'w') as f:
        if original_content:
            f.write("Original File:\n")
            f.write(original_content)
            f.write("\nModified File:\n")
        f.write(__doc__.strip() if __doc__ else "")

if __name__ == '__main__':
    main()
