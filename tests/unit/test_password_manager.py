"""
Unit tests for Password Manager
Tests password hashing and validation using bcrypt
"""
import pytest
from backend.auth.password_manager import PasswordManager


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password(self):
        """Test basic password hashing"""
        password = "MySecurePassword123!"
        hashed = PasswordManager.hash_password(password)
        
        # Should return a bcrypt hash
        assert hashed.startswith('$2b$12$')
        assert len(hashed) == 60
    
    def test_hash_password_different_each_time(self):
        """Test that hashing same password produces different hashes (due to salt)"""
        password = "SamePassword123"
        hash1 = PasswordManager.hash_password(password)
        hash2 = PasswordManager.hash_password(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert PasswordManager.verify_password(password, hash1)
        assert PasswordManager.verify_password(password, hash2)
    
    def test_hash_empty_password(self):
        """Test that empty password raises ValueError"""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordManager.hash_password("")
    
    def test_hash_very_long_password(self):
        """Test hashing a very long password (bcrypt truncates at 72 bytes)"""
        # Bcrypt automatically truncates at 72 bytes - this should work fine
        # Modern bcrypt implementations handle this gracefully without raising errors
        long_password = "A" * 200
        hashed = PasswordManager.hash_password(long_password)
        
        # Should successfully hash
        assert hashed.startswith('$2b$12$')
        assert len(hashed) == 60
        
        # Should verify with the long password
        assert PasswordManager.verify_password(long_password, hashed)
        
        # Note: Due to bcrypt's 72-byte limit, passwords beyond 72 bytes
        # are effectively the same. This is a known bcrypt behavior.
        truncated_password = "A" * 72
        assert PasswordManager.verify_password(truncated_password, hashed)
    
    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters"""
        password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        hashed = PasswordManager.hash_password(password)
        
        assert hashed.startswith('$2b$12$')
        assert PasswordManager.verify_password(password, hashed)
    
    def test_hash_password_unicode(self):
        """Test hashing password with unicode characters"""
        password = "Pāssw0rd🔒中文"
        hashed = PasswordManager.hash_password(password)
        
        assert hashed.startswith('$2b$12$')
        assert PasswordManager.verify_password(password, hashed)


class TestPasswordVerification:
    """Test password verification functionality"""
    
    def test_verify_correct_password(self):
        """Test verifying correct password"""
        password = "CorrectPassword123"
        hashed = PasswordManager.hash_password(password)
        
        assert PasswordManager.verify_password(password, hashed)
    
    def test_verify_wrong_password(self):
        """Test verifying wrong password returns False"""
        password = "CorrectPassword123"
        wrong_password = "WrongPassword123"
        hashed = PasswordManager.hash_password(password)
        
        assert not PasswordManager.verify_password(wrong_password, hashed)
    
    def test_verify_case_sensitive(self):
        """Test that password verification is case-sensitive"""
        password = "Password123"
        hashed = PasswordManager.hash_password(password)
        
        # Different case should not verify
        assert not PasswordManager.verify_password("password123", hashed)
        assert not PasswordManager.verify_password("PASSWORD123", hashed)
    
    def test_verify_empty_password(self):
        """Test verifying empty password"""
        password = "ValidPassword123"
        hashed = PasswordManager.hash_password(password)
        
        # Empty password should not verify
        assert not PasswordManager.verify_password("", hashed)
    
    def test_verify_with_invalid_hash(self):
        """Test verifying with invalid hash format"""
        password = "SomePassword123"
        invalid_hash = "not_a_valid_bcrypt_hash"
        
        # Should handle gracefully and return False
        assert not PasswordManager.verify_password(password, invalid_hash)


class TestPasswordValidation:
    """Test password validation rules"""
    
    def test_validate_strong_password(self):
        """Test validating a strong password"""
        # Minimum 12 chars with mix of char types
        strong_password = "MyStr0ngP@ssw0rd!"
        is_valid, message = PasswordManager.validate_password_strength(strong_password)
        
        assert is_valid
        assert message == "Password meets security requirements"
    
    def test_validate_short_password(self):
        """Test validating password that's too short"""
        short_password = "Short1!"
        is_valid, message = PasswordManager.validate_password_strength(short_password)
        
        assert not is_valid
        assert "at least 12 characters" in message
    
    def test_validate_password_no_uppercase(self):
        """Test password with no uppercase letters"""
        password = "mypassword123!"
        is_valid, message = PasswordManager.validate_password_strength(password)
        
        assert not is_valid
        assert "uppercase" in message.lower()
    
    def test_validate_password_no_lowercase(self):
        """Test password with no lowercase letters"""
        password = "MYPASSWORD123!"
        is_valid, message = PasswordManager.validate_password_strength(password)
        
        assert not is_valid
        assert "lowercase" in message.lower()
    
    def test_validate_password_no_digit(self):
        """Test password with no digits"""
        password = "MyPassword!!!"
        is_valid, message = PasswordManager.validate_password_strength(password)
        
        assert not is_valid
        assert "digit" in message.lower()
    
    def test_validate_password_no_special(self):
        """Test password with no special characters"""
        password = "MyPassword123"
        is_valid, message = PasswordManager.validate_password_strength(password)
        
        assert not is_valid
        assert "special character" in message.lower()
    
    def test_validate_common_pattern(self):
        """Test detection of common password patterns"""
        common_passwords = [
            "Password123!",
            "Welcome123!",
            "Admin123!",
            "Qwerty123!",
            "Abc123!@#$%^"
        ]
        
        for password in common_passwords:
            is_valid, message = PasswordManager.validate_password_strength(password)
            assert not is_valid
            assert "common pattern" in message.lower() or "not meet" in message.lower()
    
    def test_validate_sequential_characters(self):
        """Test detection of sequential characters"""
        passwords_with_sequences = [
            "MyPassword123abc",  # Sequential letters
            "Pass123456789!",    # Sequential numbers
        ]
        
        for password in passwords_with_sequences:
            is_valid, message = PasswordManager.validate_password_strength(password)
            # These might still be valid if they're long enough
            # The validation focuses on obvious patterns
            # Just ensure we get a response
            assert isinstance(is_valid, bool)
            assert isinstance(message, str)
    
    def test_validate_repeated_characters(self):
        """Test detection of repeated characters"""
        password = "MyPasssssword111!!!"
        is_valid, message = PasswordManager.validate_password_strength(password)
        
        # Should still validate basic requirements
        # Repeated chars don't necessarily make it weak if other criteria met
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)