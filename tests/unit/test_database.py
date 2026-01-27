"""
Unit tests for Database Models

Tests User and Session models and database operations.

Run with: pytest tests/unit/test_database.py -v
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.database import Base, get_db, init_db
from backend.models.user import User
from backend.models.session import Session as SessionModel
from backend.models.environment import Environment


class TestDatabaseInitialization:
    """Test database initialization"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        # Create temp file
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Set environment variable
        original_path = os.environ.get('DATABASE_PATH')
        os.environ['DATABASE_PATH'] = db_path
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        if original_path:
            os.environ['DATABASE_PATH'] = original_path
        else:
            del os.environ['DATABASE_PATH']
    
    def test_init_db_creates_file(self, temp_db):
        """Test that init_db creates database file"""
        # Remove if exists
        if os.path.exists(temp_db):
            os.remove(temp_db)
        
        # Initialize
        init_db()
        
        # Should exist now
        assert os.path.exists(temp_db)
    
    def test_init_db_creates_tables(self, temp_db):
        """Test that init_db creates all required tables"""
        # Force reload of database module to pick up new DATABASE_PATH
        import importlib
        import backend.models.database
        importlib.reload(backend.models.database)
        from backend.models.database import init_db as reloaded_init_db
        
        reloaded_init_db()
        
        # Create engine to inspect
        engine = create_engine(f"sqlite:///{temp_db}")
        
        # Check tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert 'users' in tables
        assert 'sessions' in tables
        assert 'environments' in tables


class TestUserModel:
    """Test User model"""
    
    @pytest.fixture
    def db_session(self):
        """Create in-memory database session for testing"""
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_user(self, db_session):
        """Test creating a user"""
        user = User(
            username='admin',
            password_hash='hashed_password_here'
        )
        db_session.add(user)
        db_session.commit()
        
        # Should be in database
        retrieved = db_session.query(User).first()
        assert retrieved is not None
        assert retrieved.username == 'admin'
        assert retrieved.password_hash == 'hashed_password_here'
    
    def test_user_default_values(self, db_session):
        """Test that user has correct default values"""
        user = User(password_hash='test_hash')
        db_session.add(user)
        db_session.commit()
        
        retrieved = db_session.query(User).first()
        assert retrieved.username == 'admin'  # Default
        assert retrieved.force_password_change is False
        assert retrieved.password_reset_at is None
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
    
    def test_user_timestamps(self, db_session):
        """Test that timestamps are set correctly"""
        user = User(password_hash='test_hash')
        db_session.add(user)
        db_session.commit()
        
        # Timestamps should be recent
        now = datetime.utcnow()
        assert (now - user.created_at).total_seconds() < 1
        assert (now - user.updated_at).total_seconds() < 1
    
    def test_user_force_password_change(self, db_session):
        """Test force password change flag"""
        user = User(
            password_hash='test_hash',
            force_password_change=True
        )
        db_session.add(user)
        db_session.commit()
        
        retrieved = db_session.query(User).first()
        assert retrieved.force_password_change is True
    
    def test_user_password_reset_timestamp(self, db_session):
        """Test password reset timestamp"""
        reset_time = datetime.utcnow()
        user = User(
            password_hash='test_hash',
            password_reset_at=reset_time
        )
        db_session.add(user)
        db_session.commit()
        
        retrieved = db_session.query(User).first()
        assert retrieved.password_reset_at is not None
        assert abs((retrieved.password_reset_at - reset_time).total_seconds()) < 1


class TestSessionModel:
    """Test Session model"""
    
    @pytest.fixture
    def db_session(self):
        """Create in-memory database session for testing"""
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_session(self, db_session):
        """Test creating a session"""
        expires_at = datetime.utcnow() + timedelta(hours=8)
        session_obj = SessionModel(
            token_hash='a' * 64,
            expires_at=expires_at
        )
        db_session.add(session_obj)
        db_session.commit()
        
        # Should be in database
        retrieved = db_session.query(SessionModel).first()
        assert retrieved is not None
        assert retrieved.token_hash == 'a' * 64
    
    def test_session_timestamps(self, db_session):
        """Test that session timestamps are set"""
        expires_at = datetime.utcnow() + timedelta(hours=8)
        session_obj = SessionModel(
            token_hash='b' * 64,
            expires_at=expires_at
        )
        db_session.add(session_obj)
        db_session.commit()
        
        retrieved = db_session.query(SessionModel).first()
        assert retrieved.created_at is not None
        
        # Created timestamp should be recent
        now = datetime.utcnow()
        assert (now - retrieved.created_at).total_seconds() < 1
    
    def test_session_expiry(self, db_session):
        """Test session expiry timestamp"""
        expires_at = datetime.utcnow() + timedelta(hours=8)
        session_obj = SessionModel(
            token_hash='c' * 64,
            expires_at=expires_at
        )
        db_session.add(session_obj)
        db_session.commit()
        
        retrieved = db_session.query(SessionModel).first()
        
        # Expires at should match (within 1 second tolerance)
        time_diff = abs((retrieved.expires_at - expires_at).total_seconds())
        assert time_diff < 1
    
    def test_session_metadata(self, db_session):
        """Test session metadata (user agent, IP)"""
        expires_at = datetime.utcnow() + timedelta(hours=8)
        session_obj = SessionModel(
            token_hash='d' * 64,
            expires_at=expires_at,
            user_agent='TestBrowser/1.0',
            ip_address='192.168.1.100'
        )
        db_session.add(session_obj)
        db_session.commit()
        
        retrieved = db_session.query(SessionModel).first()
        assert retrieved.user_agent == 'TestBrowser/1.0'
        assert retrieved.ip_address == '192.168.1.100'
    
    def test_session_last_accessed(self, db_session):
        """Test last accessed timestamp"""
        expires_at = datetime.utcnow() + timedelta(hours=8)
        last_accessed = datetime.utcnow()
        session_obj = SessionModel(
            token_hash='e' * 64,
            expires_at=expires_at,
            last_accessed=last_accessed
        )
        db_session.add(session_obj)
        db_session.commit()
        
        retrieved = db_session.query(SessionModel).first()
        assert retrieved.last_accessed is not None
        time_diff = abs((retrieved.last_accessed - last_accessed).total_seconds())
        assert time_diff < 1
    
    def test_session_unique_token_hash(self, db_session):
        """Test that token_hash must be unique"""
        expires_at = datetime.utcnow() + timedelta(hours=8)
        
        # Create first session
        session1 = SessionModel(token_hash='f' * 64, expires_at=expires_at)
        db_session.add(session1)
        db_session.commit()
        
        # Try to create duplicate
        session2 = SessionModel(token_hash='f' * 64, expires_at=expires_at)
        db_session.add(session2)
        
        # Should raise error on commit
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            db_session.commit()


class TestEnvironmentModel:
    """Test Environment model"""
    
    @pytest.fixture
    def db_session(self):
        """Create in-memory database session for testing"""
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_environment(self, db_session):
        """Test creating an environment"""
        env = Environment(
            code='PRD',
            name='Production',
            description='Production environment',
            color='red',
            icon_emoji='🔴'
        )
        db_session.add(env)
        db_session.commit()
        
        retrieved = db_session.query(Environment).first()
        assert retrieved is not None
        assert retrieved.code == 'PRD'
        assert retrieved.name == 'Production'
    
    def test_environment_default_values(self, db_session):
        """Test environment default values"""
        env = Environment(code='DEV', name='Development')
        db_session.add(env)
        db_session.commit()
        
        retrieved = db_session.query(Environment).first()
        assert retrieved.color == 'gray'  # Default
        assert retrieved.icon_emoji == '🔵'  # Default
        assert retrieved.display_order == 999  # Default
        assert retrieved.require_confirmation is False
        assert retrieved.prevent_auto_update is False
    
    def test_environment_unique_code(self, db_session):
        """Test that environment code must be unique"""
        env1 = Environment(code='PRD', name='Production')
        db_session.add(env1)
        db_session.commit()
        
        # Try to create duplicate code
        env2 = Environment(code='PRD', name='Production 2')
        db_session.add(env2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_environment_production_settings(self, db_session):
        """Test production environment settings"""
        env = Environment(
            code='PRD',
            name='Production',
            require_confirmation=True,
            prevent_auto_update=True
        )
        db_session.add(env)
        db_session.commit()
        
        retrieved = db_session.query(Environment).first()
        assert retrieved.require_confirmation is True
        assert retrieved.prevent_auto_update is True


class TestDatabaseHelpers:
    """Test database helper functions"""
    
    def test_get_db_generator(self):
        """Test that get_db returns a generator"""
        db_gen = get_db()
        
        # Should be a generator
        assert hasattr(db_gen, '__next__')
    
    def test_get_db_yields_session(self):
        """Test that get_db yields a database session"""
        db_gen = get_db()
        db = next(db_gen)
        
        # Should be a session
        from sqlalchemy.orm import Session
        assert isinstance(db, Session)
        
        # Close generator
        try:
            next(db_gen)
        except StopIteration:
            pass


class TestDatabaseRelationships:
    """Test database relationships and foreign keys"""
    
    @pytest.fixture
    def db_session(self):
        """Create in-memory database session for testing"""
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_multiple_sessions_per_user(self, db_session):
        """Test that user can have multiple sessions"""
        # Create user
        user = User(password_hash='test_hash')
        db_session.add(user)
        db_session.commit()
        
        # Create multiple sessions
        expires_at = datetime.utcnow() + timedelta(hours=8)
        for i in range(3):
            session = SessionModel(
                token_hash=str(i) * 64,
                expires_at=expires_at
            )
            db_session.add(session)
        db_session.commit()
        
        # Should have 3 sessions
        sessions = db_session.query(SessionModel).all()
        assert len(sessions) == 3
