"""
Unit Tests for Password Manager

Tests the password hashing and validation functionality using bcrypt.

Test Coverage:
- Password hashing (creates unique hashes)
- Password verification (correct and incorrect passwords)
- Password strength validation (all requirements)
- Edge cases (empty passwords, very long passwords, special characters)

Design Philosophy:
- Each test is independent (can run in any order)
- Clear test names describe what is being tested
- Comments explain WHY we test certain things
- Comprehensive coverage of edge cases

Run tests:
    pytest tests/unit/test_password_manager.py -v
    pytest tests/unit/test_password_manager.py -v --cov=backend/auth/password_manager
"""

import pytest
from backend.auth.password_manager import PasswordManager


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password_creates_valid_hash(self):
        """Test that hashing a password creates a valid bcrypt hash"""
        password = "MySecurePassword123"
        hashed = PasswordManager.hash_password(password)
        
        # Bcrypt hashes are 60 characters long
        assert len(hashed) == 60
        # Bcrypt hashes start with $2b$ (bcrypt identifier)
        assert hashed.startswith('$2b$')
    
    def test_hash_password_creates_unique_hashes(self):
        """Test that same password creates different hashes (due to salt)"""
        password = "MySecurePassword123"
        hash1 = PasswordManager.hash_password(password)
        hash2 = PasswordManager.hash_password(password)
        
        # Same password should create different hashes (bcrypt uses random salt)
        assert hash1 != hash2
    
    def test_verify_password_with_correct_password(self):
        """Test password verification with correct password"""
        password = "MySecurePassword123"
        hashed = PasswordManager.hash_password(password)
        
        # Correct password should verify successfully
        assert PasswordManager.verify_password(password, hashed) is True
    
    def test_verify_password_with_incorrect_password(self):
        """Test password verification with incorrect password"""
        password = "MySecurePassword123"
        wrong_password = "WrongPassword456"
        hashed = PasswordManager.hash_password(password)
        
        # Wrong password should fail verification
        assert PasswordManager.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive"""
        password = "MySecurePassword123"
        hashed = PasswordManager.hash_password(password)
        
        # Different case should fail
        assert PasswordManager.verify_password("mysecurepassword123", hashed) is False
        assert PasswordManager.verify_password("MYSECUREPASSWORD123", hashed) is False
    
    def test_hash_empty_password(self):
        """Test hashing an empty password (should raise ValueError)"""
        # Empty passwords should be rejected
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordManager.hash_password("")
    
    def test_hash_very_long_password(self):
        """Test hashing a very long password (bcrypt has 72 byte limit)"""
        # Bcrypt has a 72-byte limit, should raise ValueError
        long_password = "A" * 200
        with pytest.raises(ValueError, match="password cannot be longer than 72 bytes"):
            PasswordManager.hash_password(long_password)
    
    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters"""
        password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        hashed = PasswordManager.hash_password(password)
        assert PasswordManager.verify_password(password, hashed) is True
    
    def test_hash_password_with_unicode(self):
        """Test hashing password with unicode characters"""
        password = "Pässwörd123🔐"
        hashed = PasswordManager.hash_password(password)
        assert PasswordManager.verify_password(password, hashed) is True


class TestPasswordStrengthValidation:
    """Test password strength validation"""
    
    def test_valid_strong_password(self):
        """Test that a strong password passes validation"""
        password = "MySecurePassword123"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is True
        assert result['strength'] >= 4  # Should have good strength
        assert len(result['issues']) == 0
    
    def test_password_too_short(self):
        """Test that password shorter than 12 characters fails"""
        password = "Short1"  # Only 6 characters
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        assert any("12 characters" in issue for issue in result['issues'])
    
    def test_password_exactly_minimum_length(self):
        """Test password exactly at minimum length (12 characters)"""
        # This password is 11 characters - one short of minimum
        password = "Passw0rd123"  # P-a-s-s-w-0-r-d-1-2-3 = 11 chars
        result = PasswordManager.validate_password_strength(password)
        
        # Should fail because it's 11 chars, not 12
        assert result['valid'] is False
        
        # Test actual 12 character password
        password_12 = "MyPassword12"  # M-y-P-a-s-s-w-o-r-d-1-2 = 12 chars
        result_12 = PasswordManager.validate_password_strength(password_12)
        
        # Should be valid if it meets other requirements
        assert result_12['valid'] is True
    
    def test_password_missing_uppercase(self):
        """Test that password without uppercase fails"""
        password = "mysecurepassword123"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        assert any("uppercase" in issue.lower() for issue in result['issues'])
    
    def test_password_missing_lowercase(self):
        """Test that password without lowercase fails"""
        password = "MYSECUREPASSWORD123"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        assert any("lowercase" in issue.lower() for issue in result['issues'])
    
    def test_password_missing_digit(self):
        """Test that password without digit fails"""
        password = "MySecurePassword"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        assert any("digit" in issue.lower() for issue in result['issues'])
    
    def test_password_with_special_characters_bonus(self):
        """Test that special characters increase strength score"""
        password_without = "MySecurePassword123"
        password_with = "MySecurePassword123!"
        
        result_without = PasswordManager.validate_password_strength(password_without)
        result_with = PasswordManager.validate_password_strength(password_with)
        
        # Both should be valid
        assert result_without['valid'] is True
        assert result_with['valid'] is True
        
        # Password with special chars should have higher strength
        assert result_with['strength'] >= result_without['strength']
    
    def test_password_strength_increases_with_length(self):
        """Test that longer passwords get higher strength scores"""
        password_12 = "Password123!"  # 12 characters
        password_16 = "LongerPassword123!"  # 18 characters
        
        result_12 = PasswordManager.validate_password_strength(password_12)
        result_16 = PasswordManager.validate_password_strength(password_16)
        
        # Longer password should have higher or equal strength
        assert result_16['strength'] >= result_12['strength']
    
    def test_password_multiple_issues(self):
        """Test that multiple issues are all reported"""
        password = "short"  # Too short, no uppercase, no digit
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        # Should report multiple issues
        assert len(result['issues']) > 1
    
    def test_password_validation_provides_suggestions(self):
        """Test that validation provides helpful suggestions"""
        password = "weak"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0
    
    def test_very_strong_password_max_strength(self):
        """Test that very strong password gets maximum strength score"""
        password = "MyVerySecurePassword123!@#"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is True
        assert result['strength'] == 5  # Maximum strength
    
    def test_empty_password_validation(self):
        """Test validation of empty password"""
        password = ""
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        assert len(result['issues']) > 0


class TestPasswordManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_verify_password_with_invalid_hash(self):
        """Test verification with malformed hash (bcrypt handles this gracefully)"""
        password = "MyPassword123"
        invalid_hash = "not_a_valid_bcrypt_hash"
        
        # bcrypt's checkpw returns False for invalid hashes rather than raising
        result = PasswordManager.verify_password(password, invalid_hash)
        assert result is False
    
    def test_hash_password_with_null_bytes(self):
        """Test hashing password with null bytes"""
        # Bcrypt has issues with null bytes - test handling
        password = "Password\x00123"
        hashed = PasswordManager.hash_password(password)
        # Bcrypt truncates at null byte
        assert PasswordManager.verify_password("Password\x00123", hashed) is True
    
    def test_password_strength_with_whitespace(self):
        """Test password strength with leading/trailing whitespace"""
        password = "  MyPassword123  "
        result = PasswordManager.validate_password_strength(password)
        
        # Whitespace counts toward length
        assert result['valid'] is True
    
    def test_password_strength_all_same_character(self):
        """Test password that's all same character"""
        password = "AAAAAAAAAAAA"  # 12 As
        result = PasswordManager.validate_password_strength(password)
        
        # Should fail validation (missing lowercase and digit)
        assert result['valid'] is False


class TestPasswordManagerConstants:
    """Test that password manager constants are set correctly"""
    
    def test_bcrypt_rounds_is_reasonable(self):
        """Test that bcrypt rounds is set to reasonable value"""
        # Work factor should be between 10 and 14 for home lab
        # Too low = insecure, too high = slow
        assert 10 <= PasswordManager.BCRYPT_ROUNDS <= 14
    
    def test_minimum_password_length_is_secure(self):
        """Test that minimum password length is secure"""
        # Should be at least 12 characters for good security
        assert PasswordManager.MIN_PASSWORD_LENGTH >= 12
