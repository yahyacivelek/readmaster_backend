-- Enum Types
CREATE TYPE user_role_enum AS ENUM ('student', 'parent', 'teacher', 'admin');
CREATE TYPE assessment_status_enum AS ENUM ('pending_audio', 'processing', 'completed', 'error');
CREATE TYPE difficulty_level_enum AS ENUM ('beginner', 'intermediate', 'advanced'); -- Based on ReadingModel
CREATE TYPE notification_type_enum AS ENUM ('assignment', 'result', 'feedback', 'system'); -- Based on NotificationModel

-- Tables

CREATE TABLE Users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    role user_role_enum NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    preferred_language VARCHAR DEFAULT 'en'
);
CREATE INDEX idx_users_email ON Users (email);
CREATE INDEX idx_users_role ON Users (role);

CREATE TABLE Classes (
    class_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_name VARCHAR NOT NULL,
    grade_level VARCHAR,
    created_by_teacher_id UUID REFERENCES Users(user_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_classes_created_by ON Classes (created_by_teacher_id);

CREATE TABLE Readings (
    reading_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR NOT NULL,
    content_text TEXT,
    content_image_url VARCHAR,
    age_category VARCHAR,
    difficulty_level difficulty_level_enum,
    language VARCHAR DEFAULT 'en',
    genre VARCHAR,
    added_by_admin_id UUID REFERENCES Users(user_id), -- Assuming admin adds readings
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_readings_language ON Readings (language);
CREATE INDEX idx_readings_difficulty ON Readings (difficulty_level);
CREATE INDEX idx_readings_added_by ON Readings (added_by_admin_id);

CREATE TABLE Assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES Users(user_id),
    reading_id UUID NOT NULL REFERENCES Readings(reading_id),
    assigned_by_teacher_id UUID REFERENCES Users(user_id),
    audio_file_url VARCHAR,
    audio_duration_seconds INTEGER,
    status assessment_status_enum NOT NULL DEFAULT 'pending_audio',
    assessment_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ai_raw_speech_to_text TEXT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assessment_student_date ON Assessments (student_id, assessment_date);
CREATE INDEX idx_assessment_status ON Assessments (status);
CREATE INDEX idx_assessment_reading_id ON Assessments (reading_id);
CREATE INDEX idx_assessment_assigned_by ON Assessments (assigned_by_teacher_id);

CREATE TABLE AssessmentResults (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL UNIQUE REFERENCES Assessments(assessment_id) ON DELETE CASCADE,
    analysis_data JSONB,
    comprehension_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assessmentresults_assessment_id ON AssessmentResults (assessment_id);

CREATE TABLE QuizQuestions (
    question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reading_id UUID NOT NULL REFERENCES Readings(reading_id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    options JSONB, -- Example: '[{"id": "A", "text": "..."}, {"id": "B", "text": "..."}]'
    correct_option_id VARCHAR NOT NULL,
    language VARCHAR DEFAULT 'en',
    added_by_admin_id UUID REFERENCES Users(user_id), -- Assuming admin adds questions
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_quizquestions_reading_id ON QuizQuestions (reading_id);
CREATE INDEX idx_quizquestions_language ON QuizQuestions (language);

CREATE TABLE StudentQuizAnswers (
    answer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES Assessments(assessment_id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES QuizQuestions(question_id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES Users(user_id), -- Denormalized for easier access
    selected_option_id VARCHAR NOT NULL,
    is_correct BOOLEAN,
    answered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_studentquizanswers_assessment_id ON StudentQuizAnswers (assessment_id);
CREATE INDEX idx_studentquizanswers_question_id ON StudentQuizAnswers (question_id);
CREATE INDEX idx_studentquizanswers_student_id ON StudentQuizAnswers (student_id);

-- Association Tables
CREATE TABLE Students_Classes (
    student_id UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES Classes(class_id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, class_id)
);

CREATE TABLE Parents_Students (
    parent_id UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    relationship_type VARCHAR,
    linked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (parent_id, student_id)
);

CREATE TABLE Teachers_Classes (
    teacher_id UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES Classes(class_id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (teacher_id, class_id)
);

CREATE TABLE ProgressTracking (
    progress_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    metric_type VARCHAR NOT NULL, -- e.g., "words_per_minute", "accuracy_score"
    value FLOAT NOT NULL,
    period_start_date DATE,
    period_end_date DATE,
    last_calculated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_progresstracking_student_metric ON ProgressTracking (student_id, metric_type);

CREATE TABLE Notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    type notification_type_enum NOT NULL,
    message TEXT NOT NULL,
    related_entity_id UUID, -- Can refer to assessment_id, class_id, etc.
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notifications_user_id ON Notifications (user_id);
CREATE INDEX idx_notifications_is_read ON Notifications (is_read);

-- Trigger function to update 'updated_at' columns
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with 'updated_at'
CREATE TRIGGER set_users_updated_at
BEFORE UPDATE ON Users
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_classes_updated_at
BEFORE UPDATE ON Classes
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_readings_updated_at
BEFORE UPDATE ON Readings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_assessments_updated_at
BEFORE UPDATE ON Assessments
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Note: AssessmentResults, QuizQuestions, StudentQuizAnswers, ProgressTracking, Notifications
-- primarily record events, so 'updated_at' might be less critical or handled differently.
-- The ERD shows updated_at for Assessments and Readings.
-- UserModel and ClassModel also have updated_at.
