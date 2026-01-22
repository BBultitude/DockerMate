"""
Password Manager - Bcrypt Password Hashing and Validation

This module handles all password-related operations for DockerMate.

Security Design:
- Bcrypt hashing with work factor 12 (good balance for home labs)
- Minimum 12 character passwords
- Password strength validation
- Temporary password generation for resets
- Never store plain text passwords

Why Bcrypt:
- Specifically designed for password hashing
- Slow by design (prevents brute force)
- Automatic salting
- Work factor adjustable for future-proofing

Work Factor 12:
- Good balance for home lab hardware (Raspberry Pi to servers)
- Fast enough for login (<1 second)
- Slow enough to prevent brute force attacks
- Can increase in future if needed

Usage:
    from backend.auth.password_manager import PasswordManager
    
    # Hash password (during setup or password change)
    hashed = PasswordManager.hash_password("MySecurePassword123")
    
    # Verify password (during login)
    if PasswordManager.verify_password("MySecurePassword123", hashed):
        print("Login successful")
    
    # Validate strength before accepting
    result = PasswordManager.validate_password_strength("weak")
    if not result['valid']:
        print(f"Password too weak: {result['issues']}")

Verification:
    python3 -c "from backend.auth.password_manager import PasswordManager; \
                h = PasswordManager.hash_password('Test123456789'); \
                print('Valid:', PasswordManager.verify_password('Test123456789', h))"
"""

import bcrypt
import secrets
import string
import re
from typing import Dict, List

class PasswordManager:
    """
    Password hashing and validation using bcrypt
    
    All password operations for DockerMate authentication.
    Never stores plain text passwords - only bcrypt hashes.
    
    Security Features:
    - Bcrypt with work factor 12
    - Automatic salting
    - Minimum 12 character requirement
    - Strength validation
    - Temporary password generation
    
    Example:
        # During initial setup
        password = input("Enter password: ")
        
        # Validate strength
        validation = PasswordManager.validate_password_strength(password)
        if not validation['valid']:
            print(f"Password too weak: {validation['issues']}")
            return
        
        # Hash for storage
        hashed = PasswordManager.hash_password(password)
        
        # Store in database
        user.password_hash = hashed
        db.commit()
        
        # Later during login
        entered_password = input("Password: ")
        if PasswordManager.verify_password(entered_password, user.password_hash):
            print("Login successful!")
    """
    
    # Bcrypt work factor - balance between security and speed
    # 12 = ~250ms on modern hardware, ~1s on Raspberry Pi
    BCRYPT_ROUNDS = 12
    
    # Minimum password length
    MIN_PASSWORD_LENGTH = 12
    
    # ==========================================================================
    # Core Password Operations
    # ==========================================================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with work factor 12
        
        This is the ONLY way passwords should be stored in the database.
        NEVER store plain text passwords!
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Bcrypt hash string (60 characters, starts with $2b$12$)
            
        Raises:
            ValueError: If password is empty
            
        Example:
            hashed = PasswordManager.hash_password("MyPassword123")
            # Returns: '$2b$12$abc...xyz' (60 chars)
            
            # Store in database
            user.password_hash = hashed
            db.commit()
            
        Verification:
            echo -n "TestPassword123" | python3 -c "
            import bcrypt, sys
            pw = sys.stdin.read()
            hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12))
            print(hashed.decode())
            "
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Convert to bytes
        password_bytes = password.encode('utf-8')
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=PasswordManager.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Return as string for database storage
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against stored bcrypt hash
        
        Used during login to check if entered password is correct.
        Safe against timing attacks (bcrypt handles this internally).
        
        Args:
            password: Plain text password entered by user
            password_hash: Bcrypt hash from database
            
        Returns:
            True if password matches, False otherwise
            
        Example:
            # During login
            entered_password = request.form.get('password')
            user = db.query(User).first()
            
            if PasswordManager.verify_password(entered_password, user.password_hash):
                # Create session, login successful
                session_token = SessionManager.create_session()
                return redirect('/dashboard')
            else:
                # Invalid password
                return "Invalid credentials", 401
                
        Security Note:
            This function takes constant time regardless of password length
            to prevent timing attacks. Bcrypt handles this internally.
        """
        if not password or not password_hash:
            return False
        
        try:
            # Convert to bytes
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            
            # Verify (constant time comparison)
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            # Invalid hash format or other error
            return False
    
    # ==========================================================================
    # Password Strength Validation
    # ==========================================================================
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict:
        """
        Validate password meets minimum requirements
        
        Requirements:
        - At least 12 characters
        - Contains uppercase letter (A-Z)
        - Contains lowercase letter (a-z)
        - Contains digit (0-9)
        - Special characters recommended but not required
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with:
            - valid (bool): True if meets requirements
            - strength (int): 0-5 score (higher is better)
            - issues (list): List of problems found
            - suggestions (list): How to improve
            
        Example:
            result = PasswordManager.validate_password_strength("weak")
            
            if not result['valid']:
                print("Password rejected:")
                for issue in result['issues']:
                    print(f"  - {issue}")
                
                print("\nSuggestions:")
                for suggestion in result['suggestions']:
                    print(f"  - {suggestion}")
            
            # Output:
            # Password rejected:
            #   - Must be at least 12 characters
            #   - Must contain uppercase letter
            #   - Must contain digit
            # 
            # Suggestions:
            #   - Use a passphrase: 4-5 random words
            #   - Use a password manager
        """
        issues = []
        strength = 0
        
        # Length check
        if len(password) < PasswordManager.MIN_PASSWORD_LENGTH:
            issues.append(f"Must be at least {PasswordManager.MIN_PASSWORD_LENGTH} characters")
        else:
            strength += 1
            # Bonus for extra length
            if len(password) >= 16:
                strength += 1
            if len(password) >= 20:
                strength += 1
        
        # Uppercase check
        if not re.search(r'[A-Z]', password):
            issues.append("Must contain at least one uppercase letter (A-Z)")
        else:
            strength += 1
        
        # Lowercase check
        if not re.search(r'[a-z]', password):
            issues.append("Must contain at least one lowercase letter (a-z)")
        else:
            strength += 1
        
        # Digit check
        if not re.search(r'\d', password):
            issues.append("Must contain at least one digit (0-9)")
        else:
            strength += 1
        
        # Special character check (recommended, not required)
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            strength += 1
        
        # ===== IMPROVED WEAK PASSWORD DETECTION =====
        # Check for common weak patterns that should be rejected
        password_lower = password.lower()
        
        # Check 1: Weak base words with only number/symbol padding
        # Catches: password123, 123password, admin!, !@#admin123, etc.
        # Pattern explanation:
        # - ^[\d!@#$...]* = starts with any number of digits/symbols
        # - (password|admin|...) = followed by a weak base word
        # - [\d!@#$...]* = followed by any number of digits/symbols
        # - $ = end of string
        weak_pattern = r'^[\d!@#$%^&*()_+=\-\[\]{};:,.<>?/\\|~`]*(password|admin|welcome|letmein|qwerty|monkey|dragon|master|login|user)[\d!@#$%^&*()_+=\-\[\]{};:,.<>?/\\|~`]*$'
        
        if re.match(weak_pattern, password_lower):
            issues.append("Don't use common words (password, admin, etc.) with just numbers/symbols")
            strength = max(0, strength - 2)
        
        # Check 2: Sequential patterns (only flag if not already flagged)
        elif re.search(r'(12345|23456|34567|78901|67890|abcde|qwerty|asdfg|zxcvb)', password_lower):
            issues.append("Avoid sequential patterns (12345, qwerty, etc.)")
            strength = max(0, strength - 1)
        
        # Check 3: Repeated characters (only flag if not already flagged)
        elif re.search(r'(.)\1{3,}', password):
            issues.append("Avoid repeated characters (aaaa, 1111, etc.)")
            strength = max(0, strength - 1)
        
        # Build result
        result = {
            "valid": len(issues) == 0,
            "strength": min(5, strength),  # Cap at 5
            "issues": issues,
            "suggestions": []
        }
        
        # Add suggestions if password is weak
        if not result['valid'] or strength < 3:
            result['suggestions'] = [
                "Use a passphrase: 4-5 random words (e.g., 'correct-horse-battery-staple')",
                "Use a password manager to generate strong passwords",
                "Mix uppercase, lowercase, numbers, and symbols",
                f"Aim for at least {PasswordManager.MIN_PASSWORD_LENGTH} characters"
            ]
        
        return result
    
    # ==========================================================================
    # Temporary Password Generation
    # ==========================================================================
    
    @staticmethod
    def generate_temp_password() -> str:
        """
        Generate temporary password for password resets
        
        Used by reset_password.py script when admin forgets password.
        Generates a memorable but secure temporary password.
        
        Format: word1-word2-word3-number
        Example: correct-horse-battery-42
        
        Returns:
            Temporary password (easy to type, meets strength requirements)
            
        Example:
            # In reset_password.py
            temp_password = PasswordManager.generate_temp_password()
            hashed = PasswordManager.hash_password(temp_password)
            
            user.password_hash = hashed
            user.force_password_change = True
            db.commit()
            
            print(f"Temporary password: {temp_password}")
            print("User must change on next login")
            
        Verification:
            python3 -c "
            from backend.auth.password_manager import PasswordManager
            temp = PasswordManager.generate_temp_password()
            print(f'Generated: {temp}')
            
            validation = PasswordManager.validate_password_strength(temp)
            print(f'Valid: {validation[\"valid\"]}')
            print(f'Strength: {validation[\"strength\"]}/5')
            "
        """
        # Simple word list (memorable, easy to type)
        words = [
            'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot',
            'golf', 'hotel', 'india', 'juliet', 'kilo', 'lima',
            'correct', 'horse', 'battery', 'staple', 'purple',
            'monkey', 'dragon', 'castle', 'forest', 'ocean'
        ]
        
        # Pick 3 random words
        word1 = secrets.choice(words)
        word2 = secrets.choice(words)
        word3 = secrets.choice(words)
        
        # Add random 2-digit number
        number = secrets.randbelow(100)
        
        # Format: word1-word2-word3-number
        # Example: correct-horse-battery-42
        temp_password = f"{word1}-{word2}-{word3}-{number}"
        
        # Capitalize first letter to meet uppercase requirement
        temp_password = temp_password[0].upper() + temp_password[1:]
        
        return temp_password
    
    # ==========================================================================
    # Utility Functions
    # ==========================================================================
    
    @staticmethod
    def get_strength_label(strength: int) -> str:
        """
        Get human-readable label for password strength score
        
        Args:
            strength: Strength score (0-5)
            
        Returns:
            Label: "Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"
            
        Example:
            validation = PasswordManager.validate_password_strength(password)
            label = PasswordManager.get_strength_label(validation['strength'])
            print(f"Password strength: {label}")
        """
        labels = {
            0: "Very Weak",
            1: "Weak",
            2: "Fair",
            3: "Good",
            4: "Strong",
            5: "Very Strong"
        }
        return labels.get(strength, "Unknown")

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the PasswordManager when run directly
    
    Usage:
        python3 backend/auth/password_manager.py
    """
    print("=" * 80)
    print("DockerMate Password Manager Test")
    print("=" * 80)
    
    # Test 1: Password hashing
    print("\n1. Testing password hashing...")
    password = "TestPassword123"
    hashed = PasswordManager.hash_password(password)
    print(f"   Original: {password}")
    print(f"   Hashed:   {hashed[:20]}... ({len(hashed)} chars)")
    print(f"   ✅ Hash generated")
    
    # Test 2: Password verification
    print("\n2. Testing password verification...")
    if PasswordManager.verify_password(password, hashed):
        print("   ✅ Correct password verified")
    else:
        print("   ❌ Verification failed")
    
    if not PasswordManager.verify_password("WrongPassword", hashed):
        print("   ✅ Wrong password rejected")
    else:
        print("   ❌ Wrong password accepted (BAD!)")
    
    # Test 3: Password strength validation
    print("\n3. Testing password strength validation...")
    
    test_passwords = [
        ("weak", False),
        ("StrongPassword123", True),
        ("correct-horse-battery-staple", True),
    ]
    
    for test_pw, should_be_valid in test_passwords:
        result = PasswordManager.validate_password_strength(test_pw)
        label = PasswordManager.get_strength_label(result['strength'])
        
        if result['valid'] == should_be_valid:
            print(f"   ✅ '{test_pw}': {label} (valid={result['valid']})")
        else:
            print(f"   ❌ '{test_pw}': Expected valid={should_be_valid}, got {result['valid']}")
        
        if result['issues']:
            for issue in result['issues']:
                print(f"      - {issue}")
    
    # Test 4: Temporary password generation
    print("\n4. Testing temporary password generation...")
    temp_password = PasswordManager.generate_temp_password()
    print(f"   Generated: {temp_password}")
    
    validation = PasswordManager.validate_password_strength(temp_password)
    if validation['valid']:
        print(f"   ✅ Temporary password is valid (strength: {validation['strength']}/5)")
    else:
        print(f"   ❌ Temporary password invalid: {validation['issues']}")
    
    print("\n" + "=" * 80)
    print("Password Manager test complete!")
    print("=" * 80)
