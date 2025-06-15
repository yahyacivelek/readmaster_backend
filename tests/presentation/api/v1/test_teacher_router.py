import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

# Assuming TestClient fixture `client` and auth override fixtures are available from conftest.py

# --- Tests for Teacher Router ---

# Test for POST /api/v1/teacher/students
def test_teacher_create_student_account_success(client: TestClient, mock_override_auth_teacher):
    """
    Test successful creation of a student account by a teacher.
    Requires client fixture and an auth override fixture for a teacher user.
    """
    student_email = f"teststudent_by_teacher_{uuid4()}@example.com"
    response = client.post(
        "/api/v1/teacher/students",
        json={
            "email": student_email,
            "password": "studentpassword123",
            "first_name": "Student",
            "last_name": "ByTeacher"
        }
        # Auth headers handled by mock_override_auth_teacher or client fixture
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == student_email
    assert data["role"] == "student"
    assert "user_id" in data

def test_teacher_create_student_account_email_exists(client: TestClient, mock_override_auth_teacher):
    """
    Test attempting to create a student with an email that already exists.
    """
    existing_email = f"existing.student_{uuid4()}@example.com"
    # First, create the student
    client.post(
        "/api/v1/teacher/students",
        json={"email": existing_email, "password": "password1", "first_name": "Existing"}
    )
    # Attempt to create again
    response = client.post(
        "/api/v1/teacher/students",
        json={"email": existing_email, "password": "password2", "first_name": "Another"}
    )
    assert response.status_code == 409 # Based on router's exception handling for InvalidInputError
    assert "already exists" in response.json()["detail"]

def test_teacher_create_student_auth_errors(client: TestClient): # No auth override
    """
    Test auth errors when creating a student without proper teacher authentication.
    """
    response = client.post(
        "/api/v1/teacher/students",
        json={
            "email": "student_no_auth@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 401 # Or 403 if token is present but not teacher

# Notes for actual implementation:
# - `mock_override_auth_teacher` is a placeholder fixture for mocking `require_role(UserRole.TEACHER)`.
# - Need to test for non-teacher authenticated user (should be 403).
# - Test for validation errors (e.g., invalid email, weak password) (422).
