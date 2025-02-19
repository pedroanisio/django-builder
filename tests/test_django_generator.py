import os
import pytest
try:
    from src.django_generator import DjangoProjectGenerator
    from src.config import (
        DJANGO_VERSION,
        DRF_VERSION,
        DOCKER_IMAGE
    )
except ImportError:
    from django_generator import DjangoProjectGenerator
    from config import (
        DJANGO_VERSION,
        DRF_VERSION,
        DOCKER_IMAGE
    )


@pytest.fixture
def xml_file(tmp_path):
    """Create a temporary XML file for testing."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<django_project>
    <name>testproject</name>
    <app>
        <name>testapp</name>
        <entities>
            <entity>
                <name>TestModel</name>
                <fields>
                    <field>
                        <name>title</name>
                        <type>CharField</type>
                        <max_length>100</max_length>
                    </field>
                </fields>
            </entity>
        </entities>
    </app>
</django_project>'''
    xml_path = tmp_path / "test_template.xml"
    xml_path.write_text(content)
    return xml_path


@pytest.fixture
def existing_project(tmp_path):
    """Create an existing project structure for testing"""
    project_path = tmp_path / "myproject"
    project_path.mkdir()
    app_path = tmp_path / "myapp"
    app_path.mkdir()
    return tmp_path


def test_project_initialization():
    with pytest.raises(FileNotFoundError):
        DjangoProjectGenerator('nonexistent.xml')


def test_valid_project_generation(tmp_path):
    # Test implementation
    pass


def test_docker_file_generation_with_env_vars(tmp_path, xml_file):
    """Test Docker file generation with environment variables"""
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        generator = DjangoProjectGenerator(str(xml_file))
        generator.generate_project()
        
        # Check Dockerfile content
        with open(tmp_path / "testproject" / "Dockerfile") as f:
            dockerfile_content = f.read()
            assert f"FROM {DOCKER_IMAGE}" in dockerfile_content
        
        # Check requirements.txt content
        with open(tmp_path / "testproject" / "requirements.txt") as f:
            reqs = f.read()
            assert f"Django=={DJANGO_VERSION}" in reqs
            assert f"djangorestframework=={DRF_VERSION}" in reqs
    
    finally:
        os.chdir(original_dir)


def test_project_generation_with_existing_dirs(existing_project, xml_file):
    """Test project generation when directories already exist"""
    original_dir = os.getcwd()
    os.chdir(existing_project)
    
    try:
        generator = DjangoProjectGenerator(str(xml_file))
        generator.generate_project()  # Should succeed now
        
        project_dir = existing_project / "testproject"
        # Verify project was created
        assert project_dir.exists()
        assert (project_dir / "manage.py").exists()
        assert (project_dir / "testapp").exists()
        
    finally:
        os.chdir(original_dir) 