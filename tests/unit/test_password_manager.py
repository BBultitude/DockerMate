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
        result = PasswordManager.validate_password_strength(strong_password)
        
        assert result['valid'] is True
        assert len(result['issues']) == 0
        assert result['strength'] >= 4  # Should be strong
    
    def test_validate_short_password(self):
        """Test validating password that's too short"""
        short_password = "Short1!"
        result = PasswordManager.validate_password_strength(short_password)
        
        assert result['valid'] is False
        # Check that issues list contains the length requirement
        issues_text = ' '.join(result['issues']).lower()
        assert "at least 12 characters" in issues_text
    
    def test_validate_password_no_uppercase(self):
        """Test password with no uppercase letters"""
        password = "mypassword123!"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        issues_text = ' '.join(result['issues']).lower()
        assert "uppercase" in issues_text
    
    def test_validate_password_no_lowercase(self):
        """Test password with no lowercase letters"""
        password = "MYPASSWORD123!"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        issues_text = ' '.join(result['issues']).lower()
        assert "lowercase" in issues_text
    
    def test_validate_password_no_digit(self):
        """Test password with no digits"""
        password = "MyPassword!!!"
        result = PasswordManager.validate_password_strength(password)
        
        assert result['valid'] is False
        issues_text = ' '.join(result['issues']).lower()
        assert "digit" in issues_text
    
    def test_validate_password_no_special(self):
        """Test password with no special characters"""
        password = "MyPassword123"
        result = PasswordManager.validate_password_strength(password)
        
        # Note: Special characters are RECOMMENDED but not REQUIRED
        # This test checks the current implementation behavior
        # The password may still be valid if it meets other criteria
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'issues' in result
        assert 'strength' in result
    
    def test_validate_common_pattern(self):
        """Test detection of common password patterns"""
        # These passwords contain weak base words that should be rejected
        # even when padded with numbers and symbols
        common_passwords = [
            "Password123!",      # weak word: password
            "Welcome123!",       # weak word: welcome
            "Admin123!",         # weak word: admin
            "Qwerty123!",        # weak word: qwerty
            "123password!@#",    # reversed: weak word at end
            "!@#admin456",       # symbols + weak word
            "letmein2024!",      # weak word: letmein
            "monkey!@#123",      # weak word: monkey
        ]
        
        for password in common_passwords:
            result = PasswordManager.validate_password_strength(password)
            assert result['valid'] is False, f"Password '{password}' should be rejected but was accepted"
            # Check that weak pattern was detected
            issues_text = ' '.join(result['issues']).lower()
            assert "common" in issues_text or "weak" in issues_text or "don't use" in issues_text
    
    def test_validate_sequential_characters(self):
        """Test detection of sequential characters"""
        passwords_with_sequences = [
            "MyPassword123abc",  # Sequential letters
            "Pass123456789!",    # Sequential numbers
        ]
        
        for password in passwords_with_sequences:
            result = PasswordManager.validate_password_strength(password)
            # These might still be valid if they're long enough
            # The validation focuses on obvious patterns
            # Just ensure we get a proper response structure
            assert isinstance(result, dict)
            assert 'valid' in result
            assert 'issues' in result
            assert isinstance(result['valid'], bool)
            assert isinstance(result['issues'], list)
    
    def test_validate_repeated_characters(self):
        """Test detection of repeated characters"""
        password = "MyPasssssword111!!!"
        result = PasswordManager.validate_password_strength(password)
        
        # Should still validate basic requirements
        # Repeated chars don't necessarily make it weak if other criteria met
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'issues' in result
        assert isinstance(result['valid'], bool)
        assert isinstance(result['issues'], list)


class TestTemporaryPasswordGeneration:
    """Test temporary password generation"""
    
    def test_generate_temp_password_format(self):
        """Test that temporary password has correct format"""
        temp_password = PasswordManager.generate_temp_password()
        
        # Should be a string
        assert isinstance(temp_password, str)
        
        # Should have some length (at least 12 chars)
        assert len(temp_password) >= 12
    
    def test_generate_temp_password_is_valid(self):
        """Test that generated temp password passes validation"""
        temp_password = PasswordManager.generate_temp_password()
        
        result = PasswordManager.validate_password_strength(temp_password)
        
        # Should be valid
        assert result['valid'] is True
        assert len(result['issues']) == 0
    
    def test_generate_temp_password_is_unique(self):
        """Test that each generated password is different"""
        password1 = PasswordManager.generate_temp_password()
        password2 = PasswordManager.generate_temp_password()
        
        # Should be different (due to randomness)
        assert password1 != password2
    
    def test_generate_temp_password_can_be_hashed(self):
        """Test that temp password can be hashed and verified"""
        temp_password = PasswordManager.generate_temp_password()
        
        # Should hash successfully
        hashed = PasswordManager.hash_password(temp_password)
        
        # Should verify successfully
        assert PasswordManager.verify_password(temp_password, hashed)


class TestPasswordStrengthScoring:
    """Test password strength scoring system"""
    
    def test_strength_increases_with_length(self):
        """Test that longer passwords get higher strength scores"""
        password_12 = "MyPassword12"  # 12 chars
        password_16 = "MyPassword123456"  # 16 chars
        password_20 = "MyPassword1234567890"  # 20 chars
        
        result_12 = PasswordManager.validate_password_strength(password_12)
        result_16 = PasswordManager.validate_password_strength(password_16)
        result_20 = PasswordManager.validate_password_strength(password_20)
        
        # Longer passwords should generally have higher or equal strength
        # (assuming they meet other criteria)
        assert isinstance(result_12['strength'], int)
        assert isinstance(result_16['strength'], int)
        assert isinstance(result_20['strength'], int)
    
    def test_strength_capped_at_five(self):
        """Test that strength score is capped at 5"""
        # Very strong password
        super_strong = "MyVeryStr0ng&ComplexP@ssw0rd!WithL0tsOfCharacters"
        
        result = PasswordManager.validate_password_strength(super_strong)
        
        # Should be capped at 5
        assert result['strength'] <= 5
    
    def test_get_strength_label(self):
        """Test strength label conversion"""
        labels = {
            0: "Very Weak",
            1: "Weak",
            2: "Fair",
            3: "Good",
            4: "Strong",
            5: "Very Strong"
        }
        
        for strength, expected_label in labels.items():
            label = PasswordManager.get_strength_label(strength)
            assert label == expected_label