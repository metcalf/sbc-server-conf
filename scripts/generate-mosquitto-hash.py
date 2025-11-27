#!/usr/bin/env python3
"""
Helper script to generate mosquitto password hashes.
Usage: ./generate-mosquitto-hash.py <password>
"""
import sys
import os
import base64
import hashlib

def generate_mosquitto_hash(password):
    """Generate a mosquitto-compatible password hash."""
    # Generate random salt
    salt = base64.b64encode(os.urandom(12)).decode('ascii')

    # Use PBKDF2 with SHA512 (mosquitto's default with $7$)
    iterations = 101
    hash_obj = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                     base64.b64decode(salt), iterations)
    hash_b64 = base64.b64encode(hash_obj).decode('ascii')

    # Return in mosquitto format: $7$iterations$salt$hash
    return f"$7${iterations:02d}${salt}${hash_b64}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ./generate-mosquitto-hash.py <password>", file=sys.stderr)
        sys.exit(1)

    password = sys.argv[1]
    print(generate_mosquitto_hash(password))
