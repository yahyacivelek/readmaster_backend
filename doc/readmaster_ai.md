# **Readmaster.ai \- Definitive Technical Documentation**

This document provides a comprehensive technical overview of the Readmaster.ai platform, including its architecture, database design, core components, and operational strategies. It is intended for software engineers, architects, and technical stakeholders.

## **Table of Contents**

* System Overview
  * Assignment vs. Assessment
* UML Diagrams
  * Database Entity Relationship Diagram (ERD)
  * System Architecture Diagram
  * User Role Activity Diagram
  * Assessment Process Sequence Diagram
  * Class Diagram \- Core Domain Models
* System Capabilities
  * Frontend Application
  * Backend Service (RESTful API)
* Core Components & Design
  * Clean Architecture Structure
  * Design Patterns Implementation
  * Database Layer (SQLAlchemy)
  * Authentication & Authorization
  * API Endpoints with Request/Response Schemas
  * File Handling Strategy
* Technical Requirements
  * Database Schema (PostgreSQL)
* Performance Considerations
  * Integration Points
  * Error Handling and Logging Strategy
  * Deployment Architecture

## **1\. System Overview**

Readmaster.ai is a web-based reading assessment and development platform that uses artificial intelligence to analyze and help improve students' reading performance. The system is designed to serve a diverse user base—including students, parents, teachers, and administrators—by providing tailored tools for each role. At its core, the platform aims to transform the traditionally subjective process of reading assessment into an objective, data-driven, and scalable practice.

The system consists of a modern frontend web application and a robust backend service that handles business logic, AI processing, and database operations.

### **Key Features**

* AI-Powered Reading Fluency Analysis: Measures words per minute, accuracy, and prosody.
* Pronunciation Assessment: Pinpoints mispronounced words and provides phonetic feedback.
* Reading Comprehension Evaluation: Uses AI-assisted quizzes to test understanding.
* Multi-language Support: The platform is designed to accommodate various languages for both content and user interface.
* Real-time Progress Tracking: Offers dashboards with detailed analytics on student performance over time.
* Role-Based Access Control (RBAC): A granular permission system ensures that users can only access features and data relevant to their specific roles (Student, Parent, Teacher, Admin).

### **Assignment vs. Assessment**

In the context of the Readmaster.ai platform, it's important to distinguish between "Assignment" and "Assessment":

* Assignment: An assignment refers to the administrative action taken by a teacher or parent (or potentially an admin) to designate a specific reading material to one or more students or an entire class. It's the act of distributing the task or setting the learning objective. The system provides APIs for Teacher Assign Reading To Students and similar functionality for parents to facilitate this action.
* Assessment: An assessment is the actual activity a student performs in response to an assignment or a self-initiated learning goal. It involves the student actively engaging with the reading material by selecting it, recording their audio while reading, answering comprehension quizzes, and subsequently having their performance analyzed by the AI. The detailed workflow is illustrated in the "Assessment Process Sequence Diagram" and supported by student-facing APIs such as Start New Assessment, Request Assessment Audio Upload URL, Confirm Assessment Audio Upload, Submit Quiz Answers For Assessment, and Get Assessment Results.

In essence: A teacher or parent assigns a reading as a task, and a student then takes an assessment based on that assigned reading (or a reading they choose) to complete the task and get evaluated. The assignment is the directive; the assessment is the execution and evaluation of that directive.

## **2\. UML Diagrams**

The following UML diagrams visualize the system's structure, behavior, and data relationships from different perspectives.

### **2.1. Database Entity Relationship Diagram (ERD)**

This diagram illustrates the database schema, showing the different tables (entities), their attributes (columns), and the relationships between them.

```mermaid
erDiagram
    Users {
        UUID user\_id PK
        VARCHAR email UK
        VARCHAR password\_hash
        VARCHAR first\_name
        VARCHAR last\_name
        ENUM role
        UUID class\_id FK "Nullable, for students"
        TIMESTAMPTZ created\_at
        TIMESTAMPTZ updated\_at
        VARCHAR preferred\_language
    }
    Classes {
        UUID class\_id PK
        VARCHAR class\_name
        VARCHAR grade\_level
        UUID created\_by\_teacher\_id FK
        TIMESTAMPTZ created\_at
        TIMESTAMPTZ updated\_at
    }
    Readings {
        UUID reading\_id PK
        VARCHAR title
        TEXT content\_text
        VARCHAR content\_image\_url
        VARCHAR age\_category
        ENUM difficulty\_level
        VARCHAR language
        VARCHAR genre
        UUID added\_by\_admin\_id FK
        TIMESTAMPTZ created\_at
        TIMESTAMPTZ updated\_at
    }
    Assessments {
        UUID assessment\_id PK
        UUID student\_id FK
        UUID reading\_id FK
        UUID assigned\_by\_teacher\_id FK "Nullable, if assigned by parent or self-started"
        UUID assigned\_by\_parent\_id FK "Nullable, if assigned by teacher or self-started"
        VARCHAR audio\_file\_url
        INTEGER audio\_duration\_seconds
        ENUM status
        TIMESTAMPTZ assessment\_date
        TEXT ai\_raw\_speech\_to\_text
        TIMESTAMPTZ updated\_at
    }
    AssessmentResults {
        UUID result\_id PK
        UUID assessment\_id FK
        JSONB analysis\_data
        FLOAT comprehension\_score
        TIMESTAMPTZ created\_at
    }
    QuizQuestions {
        UUID question\_id PK
        UUID reading\_id FK
        TEXT question\_text
        JSONB options
        VARCHAR correct\_option\_id
        VARCHAR language
        UUID added\_by\_admin\_id FK
        TIMESTAMPTZ created\_at
    }
    StudentQuizAnswers {
        UUID answer\_id PK
        UUID assessment\_id FK
        UUID question\_id FK
        UUID student\_id FK
        VARCHAR selected\_option\_id
        BOOLEAN is\_correct
        TIMESTAMPTZ answered\_at
    }
    Parents\_Students {
        UUID parent\_id FK
        UUID student\_id FK
        VARCHAR relationship\_type
        TIMESTAMPTZ linked\_at
    }
    Teachers\_Classes {
        UUID teacher\_id FK
        UUID class\_id FK
        TIMESTAMPTZ assigned\_at
    }
    ProgressTracking {
        UUID progress\_id PK
        UUID student\_id FK
        VARCHAR metric\_type
        FLOAT value
        DATE period\_start\_date
        DATE period\_end\_date
        TIMESTAMPTZ last\_calculated\_at
    }
    Notifications {
        UUID notification\_id PK
        UUID user\_id FK
        ENUM type
        TEXT message
        UUID related\_entity\_id
        BOOLEAN is\_read
        TIMESTAMPTZ created\_at
    }
    Users ||--o{ Assessments : "takes/assigns"
    Users ||--o{ Readings : "adds"
    Users ||--o{ QuizQuestions : "creates"
    Users ||--o{ StudentQuizAnswers : "answers"
    Users ||--o{ ProgressTracking : "tracks"
    Users ||--o{ Notifications : "receives"
    Users ||--o{ Parents\_Students : "links"
    Classes }o--|| Users : "contains"
    Classes ||--o{ Teachers\_Classes : "assigned\_to"
    Readings ||--o{ Assessments : "assessed\_in"
    Readings ||--o{ QuizQuestions : "has"
    Assessments ||--|| AssessmentResults : "produces"
    Assessments ||--o{ StudentQuizAnswers : "includes"
    QuizQuestions ||--o{ StudentQuizAnswers : "answered\_in"
    Teachers\_Classes |o--|| Users : "teaches"
```

Intention and Explanation

The ERD is a normalized relational model serving as the application's single source of truth.

* Core Entities: Users, Readings, Assessments, and AssessmentResults form the core of the system.
* Relational Structure: A one-to-many relationship exists between Classes and Users (for students), enforced by a nullable class\_id foreign key on the Users table. Many-to-many relationships, such as between parents and students or teachers and classes, are managed via junction tables (Parents\_Students, Teachers\_Classes). The Assessments table now includes both assigned\_by\_teacher\_id and assigned\_by\_parent\_id, allowing an assessment to be assigned by either role, or self-initiated by a student (if both are null).
* Data Types: UUID is used for primary keys for global uniqueness. TIMESTAMPTZ is used for all temporal data to ensure timezone consistency. JSONB stores complex, queryable AI analysis data efficiently.

### **2.2. System Architecture Diagram**

This diagram provides a high-level overview of the system's architecture.

```mermaid
graph TB
    subgraph "Client Layer"
        A\[React Frontend\<br/\>TypeScript \+ i18n\]
        B\[Mobile Browser\]
        C\[Desktop Browser\]
    end
    subgraph "CDN & Static Assets"
        D\[CDN\<br/\>Static Files\]
    end
    subgraph "API Gateway"
        E\[Load Balancer\<br/\>HTTPS/TLS\]
    end
    subgraph "Application Layer"
        F\[Backend API\<br/\>RESTful Service\]
        G\[Authentication\<br/\>JWT Service\]
        H\[WebSocket Server\<br/\>Real-time Notifications\]
    end
    subgraph "Processing Layer"
        I\[AI Processing Service\<br/\>Async Workers\]
        J\[Queue System\<br/\>FastAPI BackgroundTasks / Celery\]
    end
    subgraph "External Services"
        K\[Google AI APIs\<br/\>Speech-to-Text\<br/\>Gemini Models\]
    end
    subgraph "Data Layer"
        L\[PostgreSQL\<br/\>Primary Database\]
        M\[Redis Cache\<br/\>Session & Data Cache\]
        N\[Cloud Storage\<br/\>Audio Files\]
    end
    subgraph "Monitoring & Logging"
        O\[Logging Service\<br/\>ELK Stack\]
        P\[Monitoring\<br/\>Metrics & Alerts\]
    end
    A \--\> D
    B \--\> E
    C \--\> E
    D \--\> E
    E \--\> F
    E \--\> G
    E \--\> H
    F \--\> M
    F \--\> L
    F \--\> J
    F \--\> N
    G \--\> M
    G \--\> L
    H \--\> M
    J \--\> I
    I \--\> K
    I \--\> L
    I \--\> N
    F \--\> O
    I \--\> O
    F \--\> P
    I \--\> P
```

Intention and Explanation

The architecture uses a decoupled, microservices-oriented approach for scalability and maintainability.

* Client & Delivery: A React frontend is accessed via browsers, with static assets served from a CDN for low latency. A Load Balancer handles traffic and TLS termination.
* Application Layer: The backend consists of a main RESTful API, a dedicated Authentication Service (JWT), and a WebSocket Server for real-time notifications.
* Processing Layer (Asynchronous): Long-running tasks like AI analysis are offloaded to a queue system and handled by independent async workers to keep the API responsive.
* Data Layer: PostgreSQL is the primary database, Redis is used for caching, and a Cloud Storage service (like GCS/S3) stores large binary files.
* Observability: Centralized logging and monitoring services provide insights into system health and performance.

### **2.3. User Role Activity Diagram**

This diagram shows the workflows available to each user role.

```mermaid
graph TD
     A\[User Login\] \--\> B{Role Check}

     B \--\>|Student| C\[Student Dashboard\]
     B \--\>|Parent| D\[Parent Dashboard\]
     B \--\>|Teacher| E\[Teacher Dashboard\]
     B \--\>|Admin| F\[Admin Dashboard\]

     C \--\> C1\[View Assignments\]
     C \--\> C2\[Take Reading Assessment\]
     C \--\> C3\[View Progress Report Summary\]

     C2 \--\> C21\[Select Reading\]
     C21 \--\> C22\[Record Audio\]
     C22 \--\> C23\[Answer Quiz\]
     C23 \--\> C24\[Submit Assessment\]
     C24 \--\> C25\[View Results\]

     D \--\> D1\[View Children's Progress\]
     D \--\> D2\[View Assessment Results\]
     D \--\> D3\[Receive Notifications\]
     D \--\> D4\[Assign Readings to Child\]
     D4 \--\> D41\[Select Reading Material\]
     D4 \--\> D42\[Assign to Child Individually\]
     D4 \--\> D43\[Manage Child's Assignments (CRUD)\]

     E \--\> E1\[Manage Classes\]
     E \--\> E2\[Assign Readings\]
     E \--\> E3\[Monitor Student Progress\]
     E \--\> E4\[View Reports\]

     E1 \--\> E11\[Create Class\]
     E1 \--\> E12(Manage Students in Class)
     E12 \--\> E12a\[Add Student\]
     E12 \--\> E12b\[View/Update Student\]
     E12 \--\> E12c\[Remove Student\]

     E2 \--\> E21\[Select Reading Material\]
     E2 \--\> E22\[Assign to Student/Class\]

     F \--\> F1\[Manage Users\]
     F \--\> F2\[Manage Reading Materials\]
     F \--\> F3\[System Configuration\]
     F \--\> F4\[View System Analytics\]

     F2 \--\> F21\[Add New Reading\]
     F2 \--\> F22\[Create Quiz Questions\]
     F2 \--\> F23\[Manage Content Library\]
```

The diagram illustrates a multi-role educational platform's user experience, starting from login and branching into different functionalities based on the user's role:

1.  **User Login (A)**: The entry point to the system.
2.  **Role Check (B)**: A decision point that determines the user's access level.
3.  **Dashboard Redirection (C, D, E, F)**: Based on the role check, the user is directed to their specific dashboard:
    *   **Student (C)**: Can view assignments, take assessments, and view progress.
        *   *Taking Assessment Sub-flow (C2 -> C25)*: A detailed sequence from selecting a reading to viewing results.
    *   **Parent (D)**: Can view children's progress and assessment results, receive notifications, and assign readings to their children.
        *   *Assign Readings Sub-flow (D4 -> D43)*: Details the process of selecting material and managing assignments.
    *   **Teacher (E)**: Can manage classes, assign readings, monitor student progress, and view reports.
        *   *Manage Classes Sub-flow (E1 -> E12c)*: Includes creating classes and managing students within them. **A teacher must create a class (E11) before adding students (E12a) to it.** Student management operations (CRUD: Create, Read/Update, Delete) occur within the context of a class.
        *   *Assign Readings Sub-flow (E2 -> E22)*: Selecting material and assigning it.
    *   **Admin (F)**: Has overarching control, managing users, reading materials, system configuration, and viewing analytics.
        *   *Manage Reading Materials Sub-flow (F2 -> F23)*: Adding new readings, creating quizzes, and managing the content library.

### **2.4. Assessment Process Sequence Diagram**

This diagram details the interactions for a reading assessment.

```mermaid
sequenceDiagram
    participant S as Student
    participant FE as Frontend
    participant API as Backend API
    participant DB as Database
    participant Q as Queue System
    participant AI as AI Service
    participant CS as Cloud Storage
    participant WS as WebSocket
    S-\>\>FE: Select Reading
    FE-\>\>API: GET /readings/{id}
    API-\>\>DB: Fetch reading content
    DB--\>\>API: Reading data
    API--\>\>FE: Display reading
    S-\>\>FE: Start Assessment
    FE-\>\>API: POST /assessments (body: reading\_id)
    API-\>\>DB: Create assessment record (status: 'pending\_audio')
    DB--\>\>API: Assessment ID
    API--\>\>FE: Assessment created
    S-\>\>FE: Record Audio
    FE-\>\>API: POST /assessments/{id}/request-upload-url
    API--\>\>FE: {upload\_url, blob\_name}
    FE-\>\>CS: PUT audio file to upload\_url
    FE-\>\>API: POST /assessments/{id}/confirm-upload (body: blob\_name)
    API-\>\>DB: Update assessment status to 'processing'
    API-\>\>Q: Queue AI processing job
    API--\>\>FE: Upload confirmed
    S-\>\>FE: Answer Quiz Questions
    FE-\>\>API: POST /assessments/{id}/quiz-answers
    API-\>\>DB: Store quiz answers
    API--\>\>FE: Quiz submitted
    Q-\>\>AI: Process audio analysis
    AI-\>\>CS: Download audio file
    AI-\>\>AI: Speech-to-text, fluency, etc.
    AI-\>\>DB: Store analysis results & update status to 'completed'
    AI-\>\>WS: Notify processing complete (to user\_id)
    WS-\>\>FE: Real-time notification
    FE-\>\>API: GET /assessments/{id}/results
    API-\>\>DB: Fetch complete results
    API--\>\>FE: Complete analysis
    FE--\>\>S: Display results
```

Intention and Explanation

This sequence illustrates the asynchronous assessment flow designed for a responsive user experience.

* Initiation: The student starts an assessment for a specific reading.
* File Upload: The frontend requests a pre-signed URL from the API, uploads the audio file directly to a cloud storage bucket. This avoids proxying large files through the backend server.
* Background Processing: Upon confirmation, the API queues a job for the AI Service, which processes the audio asynchronously.
* Notification & Retrieval: Once processing is complete, a WebSocket notification alerts the user, who can then fetch the detailed results.

### **2.5. Class Diagram \- Core Domain Models**

This diagram shows the object-oriented representation of core business entities.

```mermaid
classDiagram
    class User {
        \+UUID userId
        \+String email
        \+String passwordHash
        \+UserRole role
        \+login()
        \+updateProfile()
    }
    class Student {
        \+Class class
        \+List\~Assessment\~ assessments
        \+takeAssessment(Reading)
        \+viewProgress()
    }
    class Teacher {
        \+List\~Class\~ classes
        \+createClass()
        \+assignReading(Student, Reading)
        \+addStudentToClass(Student, Class)
        \+removeStudentFromClass(Student, Class)
        \+updateStudentInClass(Student)
    }
    class Parent {
        \+List\~Student\~ children
        \+assignReading(Student, Reading)
        \+viewChildProgress(Student)
        \+manageAssignment(Assignment)
    }
    class Admin {
        \+manageUsers()
        \+manageReadings()
    }
    class Reading {
        \+UUID readingId
        \+String title
        \+String contentText
        \+DifficultyLevel difficulty
        \+List\~QuizQuestion\~ questions
    }
    class Assessment {
        \+UUID assessmentId
        \+UUID studentId
        \+UUID readingId
        \+String audioFileUrl
        \+AssessmentStatus status
        \+AssessmentResult result
        \+processAudio()
        \+calculateScores()
    }
    class AssessmentResult {
        \+UUID resultId
        \+Object analysisData
        \+Float comprehensionScore
        \+generateReport()
    }
    class QuizQuestion {
        \+UUID questionId
        \+String questionText
        \+Object options
        \+validateAnswer(String)
    }
    class QuizAnswer {
        \+UUID answerId
        \+UUID questionId
        \+String selectedOptionId
        \+Boolean isCorrect
    }
    class Class {
        \+UUID classId
        \+String className
        \+List\~Student\~ students
        \+List\~Teacher\~ teachers
        \+addStudent(Student)
        \+removeStudent(Student)
    }
    User \<|-- Student
    User \<|-- Teacher
    User \<|-- Parent
    User \<|-- Admin
    Student "1" \-- "\*" Assessment : takes
    Student "\*" \-- "1" Class : enrolls in
    Teacher "1" \-- "\*" Class : manages
    Teacher "1" \-- "\*" Assessment : assigns
    Parent "1" \-- "\*" Assessment : assigns
    Parent "1" \-- "\*" Assignment : manages
    Reading "1" \-- "\*" Assessment : is subject of
    Reading "1" \-- "\*" QuizQuestion : has
    Assessment "1" \-- "1" AssessmentResult : produces
    Assessment "1" \-- "\*" QuizAnswer : includes
    QuizQuestion "1" \-- "\*" QuizAnswer : is answered by
```

Intention and Explanation

This class diagram maps domain concepts to software objects.

* Inheritance: Student, Teacher, Parent, and Admin inherit from a base User class.
* Relationships & Methods: The Student class has a single Class attribute, reflecting the one-to-many relationship. The Teacher and now Parent classes include methods for assigning readings, with Parent also gaining a manageAssignment(Assignment) method reflecting CRUD capabilities.
* Encapsulation: Each class bundles its data and the logic that operates on it.

## **3\. System Capabilities**

### **3.1. Frontend Application**

* Technology Stack: React, TypeScript
* Internationalization: i18n library implementation
* State Management: Potentially uses React Context API or Zustand for global state management to ensure efficient data flow and component re-rendering.
* UI Component Library: May leverage a UI component library (e.g., Shadcn UI or custom components) to ensure consistency and accelerate development.
* Key Features: Role-based panels for Students, Parents, and Teachers, providing access to assignments, progress tracking, class management, and detailed performance analytics. A settings panel allows for profile and preference management.

### **3.2. Backend Service (RESTful API)**

* Technology Stack: FastAPI (Python), SQLAlchemy, Pydantic, JWT, pytest, Redis, Celery.
* Architecture Pattern: Clean Architecture.
* Core Responsibilities: Database operations, business logic, asynchronous AI processing via job queues, and progress tracking.

## **4\. Core Components & Design**

### **4.1. Clean Architecture Structure**

The backend isolates business rules from frameworks and external dependencies for maintainability and testability.

* src/
* ├── domain/              \# Enterprise Business Rules (Entities, Value Objects) \- Contains core business rules independent of any application layer.
* │                        \# Defines entities, value objects, and interfaces that represent the fundamental concepts of Readmaster.ai.
* ├── application/         \# Application Business Rules (Use Cases, DTOs) \- Orchestrates domain entities to implement specific application features.
* │                        \# Contains use cases (interactors) that define application-specific logic, and Data Transfer Objects (DTOs) for data exchange.
* ├── infrastructure/      \# Frameworks & Drivers (DB, external APIs, file storage) \- Handles external concerns and implements interfaces defined in domain/application.
* │                        \# This layer includes concrete implementations for database access (SQLAlchemy), external AI API clients, and cloud storage interactions.
* ├── presentation/        \# Interface Adapters (API endpoints, schemas) \- Adapts data and requests from the outside world to the format required by the application layer.
* │                        \# Contains FastAPI endpoints, Pydantic schemas for request/response validation, and authentication/authorization logic.
* └── shared/              \# Shared utilities (exceptions, constants) \- Provides common functionalities and definitions used across multiple layers.
*                          \# Includes custom exception classes, constants, and helper functions.
*

### **4.2. Design Patterns Implementation**

* Repository Pattern: Abstracts the data layer, providing a consistent interface for data access regardless of the underlying database technology.
* Service Layer Pattern (Use Cases): Encapsulates business logic, making the core application functionality reusable and testable independently of the presentation or data layers.
* Factory Pattern: Decouples creation of complex objects like AI service clients, allowing for flexible instantiation and easier swapping of implementations.
* Observer Pattern: Used for handling notifications, allowing components to react to events without tight coupling to the event source.
* Dependency Injection: Managed via FastAPI's built-in system, promoting loose coupling and making components easier to test and manage.

### **4.3. Database Layer (SQLAlchemy)**

SQLAlchemy is used as the ORM for database interaction, with Alembic managing schema migrations. An asynchronous engine and session maker are configured for non-blocking database operations. Repositories implement the data access logic using the async session.

### **4.4. Authentication & Authorization**

* Authentication: Implemented using JSON Web Tokens (JWT).
  * Access Tokens: Short-lived (e.g., 15 minutes) and sent with every API request to authenticate the user.
  * Refresh Tokens: Long-lived (e.g., 7 days or more) and securely stored (e.g., HTTP-only cookie). They are used to obtain new access tokens without requiring the user to re-enter credentials.
  * Token Revocation: Refresh tokens can be revoked (e.g., upon logout, account compromise) by maintaining a blacklist or by storing active sessions in Redis.
* Authorization: The system employs a robust Role-Based Access Control (RBAC) model.
  * Enforcement: RBAC is enforced at the API endpoint level using FastAPI's dependency injection system, where custom dependencies or decorators verify the authenticated user's role against the required permissions for a given operation. Business logic further validates permissions within use cases.
  * Each API endpoint is protected, and the business logic verifies that the authenticated user's role grants them the necessary permissions to perform the requested action. This ensures a strict separation of duties and data access privileges.

#### **Detailed Role Capabilities**

Below is a detailed breakdown of the capabilities and data access restrictions for each user role.

Student

The Student role is focused on the core learning experience. All actions are scoped to the student's own data.

* Profile Management: Read and update their own user profile (/api/v1/users/me).
* Reading Materials: List and browse all available reading materials (/api/v1/readings). View details of a specific reading, including quiz questions (without correct answers).
* Assessments: Create new assessments for themself (/api/v1/assessments). Perform all steps of an assessment: request upload URLs, confirm uploads, and submit quiz answers. Read detailed results and analysis for their own completed assessments (/api/v1/assessments/{assessment\_id}/results).
* Progress Tracking: View their own progress report summary (GET /api/v1/student/progress-summary). This dashboard provides key metrics such as average words per minute, accuracy, comprehension scores, and a history of recent assessments.
* Notifications: Receive and manage their own notifications (e.g., new assignment, results ready).

Parent

The Parent role is supervisory, providing read-only access to their linked children's activities, and now includes robust assignment capabilities.

* Profile Management: Read and update their own user profile.
* Child Management (MVP): For the Minimum Viable Product (MVP), parents will directly create and manage child accounts that they own. This includes creating new child accounts via the new API endpoint:
  * POST /api/v1/parent/children: Create a new student account linked to the parent.
    They can also list all linked children (/api/v1/parent/my-children) and unlink a child from their account. The ability for students to initiate linking via an invitation process is planned for future iterations.
* Assignments: Parents can individually assign readings to their linked children via dedicated API endpoints and perform comprehensive CRUD operations on these assignments. This capability is a core feature for parental involvement in a child's reading journey.
  * Creating assignments: Designating a reading for a specific child (POST /api/v1/parent/children/{child\_id}/assignments).
  * Reading assignments: Viewing current and past assignments for their children (GET /api/v1/parent/children/{child\_id}/assignments).
  * Updating assignments: Modifying assignment details (e.g., due date) for a specific assignment (PUT /api/v1/parent/children/{child\_id}/assignments/{assignment\_id}).
  * Deleting assignments: Removing an assigned reading. (Note: Deleting an assignment removes the administrative link. It does not delete the child's associated assessment record if the assessment has already been started or completed.) (DELETE /api/v1/parent/children/{child\_id}/assignments/{assignment\_id}).
* Progress Monitoring: Read the progress summary for each linked child (/api/v1/parent/children/{child\_id}/progress). Read detailed results of any specific assessment taken by a linked child (/api/v1/parent/children/{child\_id}/assessments/{assessment\_id}/results).
* Notifications: Receive and manage their own notifications, which may pertain to their children's activities.

Teacher

The Teacher role is focused on class and student management within their assigned scope.

* Profile Management: Read and update their own user profile.
* Class Management: Perform full CRUD operations (Create, Read, Update, Delete) on classes they own (/api/v1/teacher/classes). A teacher must create at least one class before they can create student accounts.
* Student Management (within their classes \- MVP): For the Minimum Viable Product (MVP), teachers will directly create and manage student accounts. Student accounts created by a teacher must be associated with one of their existing classes. This includes adding new students to a class they own (which may involve creating the student account as part of this process), removing students from a class they own, and listing all students enrolled in their classes.
    *   If a teacher wishes to create a student account, they must first have created at least one class.
    *   The primary mechanism for adding students is typically by adding them to a specific class (e.g., using an endpoint like POST /api/v1/teacher/classes/{class_id}/students, which would handle the creation of the student record and associating it with the class).
    *   The standalone endpoint POST /api/v1/teacher/students, if still used, would require a `class_id` to associate the new student with one of the teacher's classes.
    The ability for students to initiate linking via an invitation process is planned for future iterations.
* Assignments & Monitoring: Assign readings to individual students or entire classes they own (/api/v1/teacher/assignments/readings). Read class-level progress reports for their classes (/api/v1/teacher/classes/{class\_id}/progress-report). Read progress summaries for any student within their classes (/api/v1/teacher/students/{student\_id}/progress-summary).

Admin

The Admin role has the highest level of privilege, with system-wide management capabilities.

* User Management: Perform full CRUD operations on any user account (Student, Parent, Teacher), except for other Admins. Can reassign roles and manage user details.
* Content Management: Perform full CRUD operations on all reading materials (/api/v1/admin/readings). Perform full CRUD operations on all quiz questions for any reading (/api/v1/admin/questions).
* System Configuration: Read and update system-wide configuration settings (/api/v1/admin/system-configurations).
* Analytics & Reporting: Access system-wide analytics and reports (endpoints to be defined).

### **4.5. API Endpoints with Request/Response Schemas**

API endpoints are versioned (/api/v1/...) and logically grouped by resource and user role. All request and response bodies are strictly validated using Pydantic schemas. Standardized pagination is used for all list endpoints.

New API Endpoints for Account Creation:

* POST /api/v1/parent/children
  * Summary: Parent Create Child Account
  * Description: Allows an authenticated parent to create a new student account that is automatically linked as their child. The created user's role will be 'student'.
  * Request Body:
* class ParentChildCreateRequest(UserCreateRequest):
*     \# Inherits email, password, first\_name, last\_name, preferred\_language from UserCreateRequest
*     role: Literal\["student"\] \= "student" \# Role is fixed to 'student'
  *
  * Responses:
    * 201 Created: UserResponseDTO (details of the newly created student account)
    * 401 Unauthorized: Invalid or missing authentication token.
    * 403 Forbidden: Authenticated user is not a parent.
    * 422 Validation Error: Invalid request body.
* POST /api/v1/teacher/students
  * Summary: Teacher Create Student Account (association with a class required)
  * Description: Allows an authenticated teacher to create a new student account, which **must be associated with one of their existing classes**. If a teacher does not have any classes, they must create one first. The request body for this endpoint (see `TeacherStudentCreateRequest`) would need to include a `class_id` to link the student to one of the teacher's classes. Alternatively, student creation may primarily occur via an "add student to class" operation (e.g., POST /api/v1/teacher/classes/{class_id}/students), which would handle creating the student and associating them simultaneously.
  * Request Body:
* class TeacherStudentCreateRequest(UserCreateRequest):
*     \# Inherits email, password, first\_name, last\_name, preferred\_language from UserCreateRequest
*     role: Literal\["student"\] \= "student" \# Role is fixed to 'student'
*     class_id: UUID # Required: ID of the teacher's class to associate the student with.
  *
  * Responses:
    * 201 Created: UserResponseDTO (details of the newly created student account, now associated with a class)
    * 401 Unauthorized: Invalid or missing authentication token.
    * 403 Forbidden: Authenticated user is not a teacher.
    * 422 Validation Error: Invalid request body.

New API Endpoints for Parent Assignments (CRUD):

* POST /api/v1/parent/children/{child\_id}/assignments
  * Summary: Parent Assign Reading to Child
  * Description: Allows an authenticated parent to assign a specific reading material to one of their linked children.
  * Request Body: AssignReadingRequestDTO (modified to accept only one student\_id, which is taken from the path, and a reading\_id)
  * Responses: 201 Created (AssignmentResponseDTO)
* GET /api/v1/parent/children/{child\_id}/assignments
  * Summary: Parent List Child's Assignments
  * Description: Retrieves a list of all readings assigned by the parent to a specific child.
  * Responses: 200 OK (list of AssignmentResponseDTO or similar)
* PUT /api/v1/parent/children/{child\_id}/assignments/{assignment\_id}
  * Summary: Parent Update Child's Assignment
  * Description: Allows an authenticated parent to update details (e.g., due date) of an existing assignment for their child.
  * Request Body: AssignmentUpdateDTO (new DTO for assignment updates)
  * Responses: 200 OK (AssignmentResponseDTO)
* DELETE /api/v1/parent/children/{child\_id}/assignments/{assignment\_id}
  * Summary: Parent Delete Child's Assignment
  * Description: Allows an authenticated parent to delete a specific assignment for their child.
  * Responses: 204 No Content

New API Endpoint for Student Progress Summary:

```
* GET /api/v1/student/progress-summary
  * Summary: Get Student Progress Summary
  * Description: Retrieves a detailed progress summary for the authenticated student. This includes key performance metrics, recent assessment attempts, and overall progress trends.
  * Responses: 200 OK (StudentProgressSummaryDTO)
  * Security: OAuth2PasswordBearer (student role required)

Example Schema: User Creation (Existing)

 \# presentation/schemas/user\_schemas.py
 from pydantic import BaseModel, EmailStr
 from uuid import UUID

 class UserCreateRequest(BaseModel):
     email: EmailStr
     password: str
     first\_name: str | None \= None
     last\_name: str | None \= None
     role: str | None \= None

 class UserResponse(BaseModel):
     user\_id: UUID
     email: EmailStr
     role: str
     first\_name: str | None
     last\_name: str | None

     class Config:
         from\_attributes \= True \# Formerly orm\_mode
```

### **4.6. File Handling Strategy**

* Upload Strategy: The frontend requests a pre-signed URL from the backend to upload audio files directly to a cloud storage bucket. This avoids proxying large files through the backend service.
* File Processing: Audio files are validated for format, duration, and size. They are then standardized to a consistent format (e.g., FLAC) for reliable AI processing. Files are organized logically within the cloud storage bucket. For example, audio files for assessments might be stored under a path like /assessments/audio/{assessment\_id}/{student\_id}/{timestamp}\_recording.flac.

## **5\. Technical Requirements**

### **5.1. Database Schema (PostgreSQL)**

The schema uses specific enum types for controlled vocabularies and is indexed for performance.

```sql
* \-- Enum types for controlled vocabularies
* CREATE TYPE user\_role\_enum AS ENUM ('student', 'parent', 'teacher', 'admin');
* CREATE TYPE assessment\_status\_enum AS ENUM ('pending\_audio', 'processing', 'completed', 'error');
* CREATE TYPE difficulty\_level\_enum AS ENUM ('beginner', 'intermediate', 'advanced');
*
* \-- Table creation with indexes
* CREATE TABLE Users (
*     user\_id UUID PRIMARY KEY,
*     email VARCHAR(255) UNIQUE NOT NULL,
*     password\_hash VARCHAR(255) NOT NULL,
*     first\_name VARCHAR(100),
*     last\_name VARCHAR(100),
*     role user\_role\_enum NOT NULL,
*     class\_id UUID REFERENCES Classes(class\_id), \-- Nullable FK for students
*     preferred\_language VARCHAR(10) DEFAULT 'en',
*     created\_at TIMESTAMPTZ DEFAULT NOW(),
*     updated\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE Classes (
*     class\_id UUID PRIMARY KEY,
*     class\_name VARCHAR(100) NOT NULL,
*     grade\_level VARCHAR(50),
*     created\_by\_teacher\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     created\_at TIMESTAMPTZ DEFAULT NOW(),
*     updated\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE Readings (
*     reading\_id UUID PRIMARY KEY,
*     title VARCHAR(255) NOT NULL,
*     content\_text TEXT,
*     content\_image\_url VARCHAR(2083),
*     age\_category VARCHAR(50),
*     difficulty\_level difficulty\_level\_enum,
*     language VARCHAR(10) DEFAULT 'en',
*     genre VARCHAR(100),
*     added\_by\_admin\_id UUID REFERENCES Users(user\_id),
*     created\_at TIMESTAMPTZ DEFAULT NOW(),
*     updated\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE Assessments (
*     assessment\_id UUID PRIMARY KEY,
*     student\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     reading\_id UUID REFERENCES Readings(reading\_id) NOT NULL,
*     assigned\_by\_teacher\_id UUID REFERENCES Users(user\_id), \-- Nullable if assigned by parent or self-started
*     assigned\_by\_parent\_id UUID REFERENCES Users(user\_id), \-- Nullable if assigned by teacher or self-started
*     audio\_file\_url VARCHAR(2083),
*     audio\_duration\_seconds INTEGER,
*     status assessment\_status\_enum NOT NULL,
*     assessment\_date TIMESTAMPTZ DEFAULT NOW(),
*     ai\_raw\_speech\_to\_text TEXT,
*     updated\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE AssessmentResults (
*     result\_id UUID PRIMARY KEY,
*     assessment\_id UUID UNIQUE REFERENCES Assessments(assessment\_id) NOT NULL,
*     analysis\_data JSONB, \-- Stores detailed AI analysis (e.g., words per minute, accuracy breakdown)
*     comprehension\_score REAL, \-- FLOAT in SQL, using REAL for single precision float
*     created\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE QuizQuestions (
*     question\_id UUID PRIMARY KEY,
*     reading\_id UUID REFERENCES Readings(reading\_id) NOT NULL,
*     question\_text TEXT NOT NULL,
*     options JSONB NOT NULL, \-- Stores key-value pairs for options (e.g., {"A": "Opt1", "B": "Opt2"})
*     correct\_option\_id VARCHAR(10) NOT NULL, \-- Key of the correct option (e.g., "A")
*     language VARCHAR(10) DEFAULT 'en',
*     added\_by\_admin\_id UUID REFERENCES Users(user\_id),
*     created\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE StudentQuizAnswers (
*     answer\_id UUID PRIMARY KEY,
*     assessment\_id UUID REFERENCES Assessments(assessment\_id) NOT NULL,
*     question\_id UUID REFERENCES QuizQuestions(question\_id) NOT NULL,
*     student\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     selected\_option\_id VARCHAR(10) NOT NULL,
*     is\_correct BOOLEAN NOT NULL,
*     answered\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE Parents\_Students (
*     parent\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     student\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     relationship\_type VARCHAR(50), \-- e.g., 'biological', 'adoptive', 'guardian'
*     linked\_at TIMESTAMPTZ DEFAULT NOW(),
*     PRIMARY KEY (parent\_id, student\_id)
* );
*
* CREATE TABLE Teachers\_Classes (
*     teacher\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     class\_id UUID REFERENCES Classes(class\_id) NOT NULL,
*     assigned\_at TIMESTAMPTZ DEFAULT NOW(),
*     PRIMARY KEY (teacher\_id, class\_id)
* );
*
* CREATE TABLE ProgressTracking (
*     progress\_id UUID PRIMARY KEY,
*     student\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     metric\_type VARCHAR(50) NOT NULL, \-- e.g., 'wpm', 'accuracy', 'comprehension\_score'
*     value REAL NOT NULL,
*     period\_start\_date DATE NOT NULL,
*     period\_end\_date DATE NOT NULL,
*     last\_calculated\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
* CREATE TABLE Notifications (
*     notification\_id UUID PRIMARY KEY,
*     user\_id UUID REFERENCES Users(user\_id) NOT NULL,
*     type ENUM ('assignment', 'result', 'feedback', 'system') NOT NULL,
*     message TEXT NOT NULL,
*     related\_entity\_id UUID, \-- Can be assessment\_id, reading\_id, etc.
*     is\_read BOOLEAN DEFAULT FALSE,
*     created\_at TIMESTAMPTZ DEFAULT NOW()
* );
*
*
* \-- Indexes are crucial for query performance
* CREATE INDEX idx\_assessment\_student\_date ON Assessments (student\_id, assessment\_date);
* CREATE INDEX idx\_assessment\_status ON Assessments (status);
* CREATE INDEX idx\_users\_class\_id ON Users (class\_id);
* CREATE INDEX idx\_readings\_language\_difficulty ON Readings (language, difficulty\_level);
* CREATE INDEX idx\_quizquestions\_reading\_id ON QuizQuestions (reading\_id);
* CREATE INDEX idx\_studentquizanswers\_assessment\_id ON StudentQuizAnswers (assessment\_id);
* CREATE INDEX idx\_parents\_students\_parent\_id ON Parents\_Students (parent\_id);
* CREATE INDEX idx\_teachers\_classes\_teacher\_id ON Teachers\_Classes (teacher\_id);
* CREATE INDEX idx\_progresstracking\_student\_metric ON ProgressTracking (student\_id, metric\_type, period\_end\_date);
* CREATE INDEX idx\_notifications\_user\_id ON Notifications (user\_id, created\_at DESC);
```

## **6\. Performance Considerations**

### **Integration Points**

Readmaster.ai will integrate with various external services to enhance its functionality and observability:

* Google AI Platform: For advanced AI models beyond basic Speech-to-Text (e.g., custom models for prosody analysis, natural language understanding for comprehension).
* Payment Gateway (e.g., Stripe, PayPal): For managing subscriptions, one-time purchases, or other monetization strategies.
* Email/SMS Service (e.g., SendGrid, Twilio): For sending transactional emails (account verification, password resets) and notifications.
* Analytics Platform (e.g., Google Analytics, Mixpanel): For detailed user behavior tracking and data-driven insights.
* Monitoring & Alerting Tools (e.g., Prometheus, Grafana): Beyond the basic ELK stack, for advanced metrics collection, dashboarding, and alerting on system health and performance anomalies.

### **Error Handling and Logging Strategy**

A robust strategy is crucial for debugging and maintaining system stability:

* Centralized Logging: All application logs (backend, AI workers, frontend) will be sent to a centralized logging system (e.g., ELK Stack \- Elasticsearch, Logstash, Kibana; or cloud-native solutions like Google Cloud Logging/Azure Monitor).
* Structured Logging: Logs will be structured (JSON format) to facilitate easy parsing, querying, and analysis. Each log entry will include context (timestamp, service name, request ID, user ID, error code, stack trace).
* Error Levels: Standard logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) will be consistently applied.
* Exception Handling:
  * Backend: Use FastAPI's exception handlers to gracefully convert internal exceptions into standardized HTTP error responses (e.g., 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error).
  * Frontend: Implement error boundaries in React to catch UI errors and display fallback UIs without crashing the entire application. Global error handlers will log client-side errors to the centralized logging system.
* Alerting: Critical errors and performance anomalies will trigger automated alerts to the operations team via integrated monitoring tools (e.g., PagerDuty, Slack).

### **Deployment Architecture**

The platform will utilize a cloud-native, containerized deployment strategy for scalability, reliability, and ease of management:

* Cloud Provider: Primary deployment on a major cloud provider (e.g., Google Cloud Platform, AWS, Azure).
* Containerization: All services (Backend API, AI Processing Service, WebSocket Server) will be containerized using Docker.
* Orchestration: Kubernetes (or a managed Kubernetes service like GKE/EKS/AKS) will be used for container orchestration, enabling automated deployment, scaling, and management of containerized applications.
* CI/CD Pipeline: A Continuous Integration/Continuous Deployment (CI/CD) pipeline (e.g., GitLab CI/CD, GitHub Actions, Jenkins) will automate the build, test, and deployment processes, ensuring rapid and reliable delivery of new features and bug fixes.
* Database Deployment: PostgreSQL will be deployed as a managed database service (e.g., Cloud SQL, RDS) for high availability, backups, and simplified administration.
* Storage: Cloud Storage buckets (e.g., GCS, S3) for audio files and other large binaries. Redis will be deployed as a managed caching service.
* Scalability: Services will be configured for horizontal scaling based on load (e.g., Kubernetes Horizontal Pod Autoscaler). Asynchronous processing ensures that the API remains responsive under heavy load.
* Asynchronous Operations: The entire backend leverages async/await for non-blocking I/O.
* Background Jobs: Time-consuming AI analysis is offloaded to background workers using Celery.
* Caching Strategy: Redis caches user sessions, permissions, and frequently accessed static data like reading materials to reduce database load.
* Database Optimization: All foreign keys and frequently filtered columns are indexed. SQLAlchemy's connection pool is used to manage database connections efficiently.
*
*