# FaceGuard
## Face Recognition Authorization System

> **Implementation Specification**
>
> This document is the source of truth for implementing the FaceGuard project. The implementation should follow this document rather than adding unnecessary technologies or features.

---

# 1. Project Overview

FaceGuard is a face-recognition-based authorization system for organizations.

The system allows an organization to:

- Register employees/personnel.
- Register their facial data.
- Create restricted areas.
- Assign personnel access permissions to specific areas.
- Verify a person using a camera.
- Generate a face embedding using a pretrained ArcFace model.
- Compare the incoming face against the authorized gallery for the current access point.
- Grant or deny access.
- Record every access attempt.

The most important architectural principle is:

> **Face recognition and authorization are separate concepts.**

Face recognition determines who a person is.

Authorization determines whether that person is allowed to access a particular location.

---

# 2. Main Objective

The system should demonstrate a practical application of:

- Computer Vision
- Face Recognition
- Pretrained Deep Learning
- Face Embeddings
- Similarity Matching
- Access Control
- REST APIs
- Relational Database
- Web Interface

The project should remain understandable and suitable for an academic/interview project.

---

# 3. Technology Stack

## 3.1 Programming Language

```text
Python 3.11+
```

Python will be used for:

- Backend
- Face recognition
- Database interaction
- Business logic

---

## 3.2 Face Recognition

```text
DeepFace
ArcFace
OpenCV
NumPy
```

ArcFace will be used as the pretrained face-recognition model.

The model will NOT be trained from scratch.

---

## 3.3 Backend

```text
FastAPI
Uvicorn
```

FastAPI provides REST API endpoints that connect the frontend with the backend.

---

## 3.4 Database

```text
SQLite
```

SQLite is sufficient for the prototype.

The database will contain:

- Personnel
- Areas
- Permissions
- Face embeddings
- Access logs

---

## 3.5 Frontend

```text
HTML
CSS
Vanilla JavaScript
```

Do NOT use React, Next.js, Vue, Angular, or other frontend frameworks.

The frontend should remain simple and easy to maintain.

---

# 4. High-Level Architecture

```text
                         FACEGUARD
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
      ADMIN DASHBOARD                ACCESS TERMINAL
      HTML/CSS/JS                    Camera + Browser
            │                               │
            └───────────────┬───────────────┘
                            │
                            ▼
                     FASTAPI BACKEND
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
          Database      Face Engine   Authorization
           SQLite       ArcFace       Service
              │             │             │
              └─────────────┼─────────────┘
                            │
                            ▼
                       Access Logs
```

---

# 5. Core System Concept

The system has two important data layers.

## Master Personnel Repository

Contains all registered personnel and their face embeddings.

```text
Personnel
   │
   └── Face Embedding
```

## Authorization Galleries

Each restricted area has an authorization gallery containing references to personnel allowed in that area.

Example:

```text
MASTER
────────────────────
Rahul
Amit
Priya
Neha
Rohan


SERVER ROOM
────────────────────
Rahul
Neha


RESEARCH LAB
────────────────────
Priya
Neha
Rohan
```

The system does NOT retrain ArcFace when personnel are added.

It also does NOT require personnel to register their face again when their permissions change.

---

# 6. Why Authorization Galleries Are Used

Suppose an organization has:

```text
10,000 employees
```

but only:

```text
150 employees
```

are allowed inside the server room.

Searching against all 10,000 embeddings is unnecessary.

Instead:

```text
Incoming Face
      ↓
Generate Embedding
      ↓
Server Room Gallery
      ↓
Compare against 150 authorized embeddings
```

This provides:

- Smaller search space
- Faster verification
- Cleaner authorization logic
- Better separation between identity and access permissions

---

# 7. Important Rule

The system should NOT physically duplicate employee records every time authorization changes.

Instead:

```text
Personnel
    │
    └── personnel_id
           │
           ▼
       Permission
           │
           ▼
       Area
```

The authorization gallery is logically derived from these relationships.

Embeddings remain associated with the main personnel record.

---

# 8. Face Recognition Pipeline

The face-recognition pipeline is:

```text
Camera Image
     ↓
Face Detection
     ↓
Face Preprocessing
     ↓
ArcFace
     ↓
Face Embedding
     ↓
Similarity Comparison
     ↓
Identity / No Match
```

ArcFace is a pretrained neural-network-based face-recognition model.

The system uses the model for inference.

It does not retrain the model for individual employees.

---

# 9. Employee Registration Flow

When an employee is registered:

```text
Admin
  ↓
Enter employee information
  ↓
Capture face images
  ↓
Detect face
  ↓
Validate image
  ↓
Generate ArcFace embedding
  ↓
Store embedding
  ↓
Registration complete
```

The employee should ideally provide multiple images with slight variations.

For example:

```text
Front
Slight left
Slight right
```

Multiple embeddings can be stored for improved robustness.

---

# 10. Registration Validation

The system should reject registration if:

### No face detected

```text
"No face detected."
```

### Multiple faces detected

```text
"Multiple faces detected. Please capture one person at a time."
```

### Poor image

If possible, reject extremely poor-quality images.

### Duplicate employee ID

Do not allow duplicate employee IDs.

---

# 11. Face Embeddings

An embedding is a numerical representation of facial characteristics.

Conceptually:

```text
Face Image
    ↓
ArcFace
    ↓
[0.12, -0.43, 0.81, ...]
```

The exact embedding size depends on the selected implementation/model configuration.

The application should not hard-code assumptions about the dimensionality unless required by the actual model.

---

# 12. Face Matching

When an access attempt occurs:

```text
Camera
  ↓
Face
  ↓
ArcFace
  ↓
Query Embedding
  ↓
Authorized Gallery
  ↓
Compare embeddings
```

A distance/similarity metric will be used.

For example:

```text
Query → Rahul = close
Query → Amit  = far
Query → Priya = far
```

The closest acceptable match is selected.

The system must use the distance/similarity metric appropriate to the selected ArcFace implementation.

---

# 13. Threshold

A recognition threshold determines whether a candidate is considered a valid match.

Conceptually:

```text
Distance <= threshold
        ↓
      MATCH
```

Otherwise:

```text
Distance > threshold
        ↓
    NO MATCH
```

The threshold must NOT be arbitrarily invented.

It should be configurable and tested using actual project data.

Configuration example:

```text
FACE_MATCH_THRESHOLD
```

The value should be documented after testing.

---

# 14. Access Point Concept

Each physical or virtual access point has a predefined area.

Example:

```text
Camera 1 → Main Office
Camera 2 → Server Room
Camera 3 → Research Lab
```

Therefore, the system does not need the user to manually select the area during normal verification.

The access terminal already knows:

```text
current_area_id
```

---

# 15. Verification Flow

Suppose an employee approaches the Server Room.

```text
Camera
   ↓
Server Room Access Point
   ↓
Capture Face
   ↓
Generate Embedding
   ↓
Load Server Room Authorized Gallery
   ↓
Compare Embedding
   ↓
Match?
```

If match:

```text
MATCH
 ↓
ACCESS GRANTED
```

If no acceptable match:

```text
NO MATCH
 ↓
ACCESS DENIED
```

---

# 16. Why We Do Not Search the Entire Database

During normal access verification, the system should NOT:

```text
Face
 ↓
Search all employees
 ↓
Identify person
 ↓
Check authorization
```

Instead:

```text
Face
 ↓
Current Area
 ↓
Authorized Gallery
 ↓
Match
 ↓
Grant/Deny
```

This means an unauthorized employee does not need to be identified before access is denied.

---

# 17. Example

Master database:

```text
Rahul
Amit
Priya
Neha
Rohan
```

Server Room authorized personnel:

```text
Rahul
Neha
```

Amit approaches the Server Room.

The system compares Amit's face only against:

```text
Rahul
Neha
```

If there is no valid match:

```text
ACCESS DENIED
```

Even though Amit exists in the master employee database.

---

# 18. Authorization Update

If Rahul is granted access to the Research Lab:

```text
Admin
 ↓
Grant Rahul → Research Lab
 ↓
Permission record updated
 ↓
Research Lab gallery refreshed
```

No face registration is required.

No ArcFace retraining is required.

---

# 19. Permission Revocation

If Rahul loses access:

```text
Admin
 ↓
Revoke Rahul → Research Lab
 ↓
Permission record updated
 ↓
Research Lab gallery refreshed
```

Future verification attempts will no longer match Rahul against the Research Lab gallery.

---

# 20. Gallery Caching

For better performance, each access terminal should cache its authorized gallery.

Example:

```text
Server Room Terminal
        ↓
Load authorized embeddings
        ↓
RAM / application memory
```

Verification then happens against the cached embeddings.

When permissions change:

```text
Permission Changed
       ↓
Gallery Invalidated
       ↓
Reload Gallery
```

The first implementation can use an in-memory cache.

No Redis or external caching system is required.

---

# 21. Database Design

Use SQLite.

## Personnel

```text
personnel

id
employee_id
name
department
role
status
created_at
```

---

## Face Embeddings

```text
face_embeddings

id
personnel_id
embedding
model_name
created_at
```

The embedding can be serialized safely for the prototype.

The API must never expose raw embeddings unnecessarily.

---

## Areas

```text
areas

id
name
description
status
created_at
```

---

## Access Permissions

```text
permissions

id
personnel_id
area_id
created_at
```

---

## Access Logs

```text
access_logs

id
personnel_id
area_id
match_score
result
reason
timestamp
```

`personnel_id` may be NULL when no identity is identified.

---

# 22. Database Relationships

```text
PERSONNEL
    │
    ├───────────────┐
    │               │
    ▼               ▼
FACE EMBEDDINGS   PERMISSIONS
                    │
                    ▼
                  AREAS

PERSONNEL ──────────────── ACCESS LOGS
AREAS ──────────────────── ACCESS LOGS
```

---

# 23. Backend Architecture

Use a simple layered architecture.

```text
API Routes
    ↓
Services
    ↓
Database / Face Engine
```

Example:

```text
POST /api/access/verify
        ↓
access route
        ↓
recognition service
        ↓
authorization service
        ↓
logging service
        ↓
database
```

Do not place all logic inside `main.py`.

---

# 24. Backend Directory Structure

```text
backend/
│
├── main.py
├── config.py
├── database.py
├── models.py
│
├── routes/
│   ├── personnel.py
│   ├── recognition.py
│   ├── authorization.py
│   ├── areas.py
│   └── logs.py
│
├── services/
│   ├── face_engine.py
│   ├── gallery_service.py
│   ├── authorization_service.py
│   └── logging_service.py
│
└── utils/
    └── helpers.py
```

---

# 25. Face Engine

`face_engine.py` is responsible only for face-related processing.

Responsibilities:

- Face detection
- Face embedding generation
- Embedding comparison
- Recognition result

Conceptual functions:

```python
detect_face(image)

generate_embedding(image)

compare_embeddings(query, stored)

recognize_against_gallery(image, gallery)
```

The rest of the backend should not need to know the internal details of DeepFace.

---

# 26. Gallery Service

`gallery_service.py` manages area-specific galleries.

Responsibilities:

- Build gallery for an area
- Load gallery
- Cache gallery
- Refresh gallery
- Invalidate gallery
- Retrieve authorized embeddings

Conceptual functions:

```python
get_area_gallery(area_id)

refresh_area_gallery(area_id)

invalidate_area_gallery(area_id)
```

---

# 27. Authorization Service

`authorization_service.py` handles access rules.

Responsibilities:

- Check whether a person has permission.
- Grant access.
- Deny access.
- Handle inactive personnel.

Conceptual logic:

```text
Recognized Person
       ↓
Active?
       ↓
Has Area Permission?
       ↓
YES → GRANT
NO  → DENY
```

---

# 28. Important Authorization Rule

A recognized person should never automatically receive access.

For example:

```text
Recognized = Rahul
```

does not mean:

```text
Authorized = TRUE
```

Authorization must depend on the area.

---

# 29. API Endpoints

The following endpoints should be implemented.

## Personnel

```http
POST /api/personnel
GET /api/personnel
GET /api/personnel/{id}
PUT /api/personnel/{id}
DELETE /api/personnel/{id}
```

---

## Face Registration

```http
POST /api/personnel/{id}/register-face
```

---

## Areas

```http
POST /api/areas
GET /api/areas
GET /api/areas/{id}
PUT /api/areas/{id}
DELETE /api/areas/{id}
```

---

## Permissions

```http
POST /api/areas/{area_id}/permissions/{personnel_id}
DELETE /api/areas/{area_id}/permissions/{personnel_id}
GET /api/areas/{area_id}/permissions
```

---

## Recognition

```http
POST /api/recognize
```

This endpoint performs recognition against a specified gallery.

---

## Access Verification

```http
POST /api/access/verify
```

This is the main endpoint used by the access terminal.

Input:

```text
Image
Access Point / Area ID
```

Processing:

```text
Image
 ↓
Face Detection
 ↓
Embedding
 ↓
Area Gallery
 ↓
Matching
 ↓
Access Decision
 ↓
Logging
```

---

## Logs

```http
GET /api/logs
GET /api/logs/{id}
```

Optional filters:

```text
area
result
date
personnel
```

---

# 30. Access Verification Response

Successful access:

```json
{
    "result": "ACCESS_GRANTED",
    "person": {
        "id": 1024,
        "name": "Rahul Sharma"
    },
    "area": "Server Room",
    "match_score": 0.21,
    "timestamp": "2026-10-07T10:42:31"
}
```

Denied:

```json
{
    "result": "ACCESS_DENIED",
    "person": null,
    "area": "Server Room",
    "reason": "NO_MATCH",
    "timestamp": "2026-10-07T10:45:12"
}
```

The exact score representation should depend on whether the implementation uses distance or similarity.

Do not label a distance value as a percentage unless it has actually been converted into a meaningful confidence metric.

---

# 31. Frontend Design

The frontend should be a simple security dashboard.

Style:

- Professional
- Minimal
- Dark/neutral
- Clear status indicators
- Large verification area
- No unnecessary animations

Technology:

```text
HTML
CSS
JavaScript
```

---

# 32. Frontend Pages

## Dashboard

Display:

- Total personnel
- Active personnel
- Access granted today
- Access denied today
- Recent access events

---

## Personnel

Display:

```text
Employee ID
Name
Department
Role
Status
Face Registration
```

Actions:

```text
Register
Edit
Deactivate
Manage Access
```

---

## Access Verification

Main screen:

```text
┌──────────────────────────────────────┐
│          ACCESS VERIFICATION         │
│                                      │
│           CAMERA PREVIEW             │
│                                      │
│         [ VERIFY ACCESS ]             │
│                                      │
│          SERVER ROOM                 │
│                                      │
│        ACCESS GRANTED                │
│        Rahul Sharma                  │
└──────────────────────────────────────┘
```

---

## Areas

Display:

```text
Area Name
Description
Authorized Personnel Count
Status
```

Allow administrator to:

- Create area
- Edit area
- Manage permissions

---

## Logs

Display:

```text
Time
Person
Area
Match Score
Result
Reason
```

Filters:

```text
Area
Date
Result
Person
```

---

# 33. Camera Handling

The browser frontend will request camera access using JavaScript.

Conceptually:

```text
Browser
   ↓
Camera permission
   ↓
Video stream
   ↓
Capture frame
   ↓
Send image to FastAPI
   ↓
Receive result
   ↓
Display result
```

The browser should not perform the face-recognition model itself.

The backend will handle face recognition.

---

# 34. Access Terminal Configuration

Each access terminal should have a configured area.

Example:

```text
Terminal ID: SERVER-01
Area: Server Room
```

When the terminal calls:

```text
POST /api/access/verify
```

the backend knows which area is being verified.

For the MVP, the area can be supplied as an API parameter.

---

# 35. Security Model

The following rules must be enforced:

### Rule 1

Unknown faces are denied.

### Rule 2

Inactive personnel are denied.

### Rule 3

Personnel without area permission are denied.

### Rule 4

Recognition and authorization must remain separate.

### Rule 5

Face embeddings should not be exposed through normal frontend API responses.

### Rule 6

Access attempts should be logged.

---

# 36. Error Handling

The application should handle:

### No face

```text
NO_FACE_DETECTED
```

### Multiple faces

```text
MULTIPLE_FACES_DETECTED
```

### Unknown person

```text
NO_MATCH
```

### Unauthorized person

```text
NOT_AUTHORIZED
```

### Inactive personnel

```text
PERSONNEL_INACTIVE
```

### Camera unavailable

```text
CAMERA_UNAVAILABLE
```

### Database error

```text
DATABASE_ERROR
```

Internal error details must not be exposed to the user.

---

# 37. Logging

Every verification attempt must create an access log.

Example:

```text
2026-10-07 10:42:31
Rahul Sharma
Server Room
MATCH
GRANTED
```

Unknown:

```text
2026-10-07 10:45:12
Unknown
Server Room
NO_MATCH
DENIED
```

Unauthorized:

```text
2026-10-07 10:48:03
Amit Kumar
Server Room
MATCH
DENIED
NOT_AUTHORIZED
```

---

# 38. Testing

Testing should cover:

## Face Recognition

- Registered face
- Unknown face
- Different lighting
- Slight head rotation
- Multiple faces
- No face

---

## Authorization

```text
Recognized + Authorized → GRANTED

Recognized + Unauthorized → DENIED

Unknown → DENIED

Inactive Personnel → DENIED
```

---

## Gallery Updates

Test:

```text
Grant access
    ↓
Gallery updated
    ↓
Verification succeeds
```

Then:

```text
Revoke access
    ↓
Gallery updated
    ↓
Verification denied
```

No face re-registration should be required.

---

# 39. Performance Considerations

The MVP should prioritize correctness over extreme performance.

Basic optimization:

```text
Load gallery
      ↓
Cache in memory
      ↓
Perform comparisons
```

Do not introduce:

- Redis
- Kubernetes
- Microservices
- Message queues
- Cloud infrastructure

unless genuinely required.

---

# 40. Project Directory

Final project structure:

```text
FaceGuard/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   │
│   ├── routes/
│   │   ├── personnel.py
│   │   ├── recognition.py
│   │   ├── authorization.py
│   │   ├── areas.py
│   │   └── logs.py
│   │
│   ├── services/
│   │   ├── face_engine.py
│   │   ├── gallery_service.py
│   │   ├── authorization_service.py
│   │   └── logging_service.py
│   │
│   └── utils/
│       └── helpers.py
│
├── frontend/
│   ├── index.html
│   ├── personnel.html
│   ├── verification.html
│   ├── areas.html
│   ├── logs.html
│   │
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       ├── app.js
│       ├── personnel.js
│       ├── verification.js
│       ├── areas.js
│       └── logs.js
│
├── database/
│   └── faceguard.db
│
├── data/
│   └── faces/
│
├── tests/
│   ├── test_face_engine.py
│   ├── test_authorization.py
│   ├── test_gallery.py
│   └── test_api.py
│
├── requirements.txt
├── README.md
├── IMPLEMENTATION.md
└── .gitignore
```

---

# 41. Implementation Order

Do NOT attempt to build everything simultaneously.

Implement in this order.

## Phase 1 — Environment

1. Create Python virtual environment.
2. Create project structure.
3. Install dependencies.
4. Verify OpenCV.
5. Verify DeepFace.
6. Verify ArcFace model can generate an embedding.

---

## Phase 2 — Face Engine

Implement:

```text
Image
 ↓
Face Detection
 ↓
ArcFace
 ↓
Embedding
 ↓
Comparison
```

Test this independently before creating the web application.

---

## Phase 3 — Database

Create:

```text
personnel
face_embeddings
areas
permissions
access_logs
```

Test CRUD operations.

---

## Phase 4 — Personnel Registration

Implement:

```text
Create personnel
 ↓
Capture image
 ↓
Generate embedding
 ↓
Store embedding
```

---

## Phase 5 — Areas and Permissions

Implement:

```text
Create area
 ↓
Assign personnel
 ↓
Revoke personnel
```

---

## Phase 6 — Authorization Gallery

Implement:

```text
Area
 ↓
Get authorized personnel
 ↓
Get embeddings
 ↓
Build gallery
 ↓
Cache gallery
```

Add refresh/invalidation when permissions change.

---

## Phase 7 — Access Verification

Implement:

```text
Camera
 ↓
Face
 ↓
Embedding
 ↓
Area gallery
 ↓
Match
 ↓
Grant/Deny
 ↓
Log
```

This is the most important application workflow.

---

## Phase 8 — API

Expose the backend through FastAPI.

Implement the required endpoints.

---

## Phase 9 — Frontend

Create:

- Dashboard
- Personnel
- Verification
- Areas
- Logs

Connect frontend to backend APIs.

---

## Phase 10 — Testing

Test the complete workflow.

---

## Phase 11 — Documentation

Create:

- README
- Architecture diagram
- Setup instructions
- Screenshots
- API explanation
- ML explanation
- Limitations

---

# 42. MVP Completion Criteria

The project is complete when this workflow works:

```text
Admin
  ↓
Register Rahul
  ↓
Register Rahul's face
  ↓
Create Server Room
  ↓
Give Rahul Server Room access
  ↓
Server Room gallery updated
  ↓
Rahul approaches camera
  ↓
ArcFace generates embedding
  ↓
Embedding compared with Server Room gallery
  ↓
Rahul matched
  ↓
ACCESS GRANTED
  ↓
Log created
```

Then:

```text
Revoke Rahul's access
  ↓
Gallery updated
  ↓
Rahul approaches camera
  ↓
No valid authorized match
  ↓
ACCESS DENIED
  ↓
Log created
```

No retraining should occur during either process.

---

# 43. ML Explanation

The project's ML pipeline is:

```text
Face Image
    ↓
Pretrained ArcFace Neural Network
    ↓
Face Embedding
    ↓
Similarity/Distance Calculation
    ↓
Identity Match
```

ArcFace is not retrained for every organization.

The pretrained model is used for inference.

The organization's employee data is represented through embeddings.

---

# 44. Interview Explanation

## Short Explanation

> FaceGuard is a face-recognition-based authorization system designed for organizations with restricted areas. I use a pretrained ArcFace model to generate facial embeddings and compare an incoming face against the authorized gallery of the current access point. If a valid match is found, the system grants access; otherwise it denies access. Permissions are managed separately, so changing an employee's access does not require retraining or re-registering their face. Every access attempt is recorded in an audit log.

---

## If Asked "Why ArcFace?"

> ArcFace is designed to generate discriminative facial embeddings. Instead of training a new classifier whenever an employee is added, I can generate an embedding for the new employee and store it. This makes employee registration and permission changes much easier to manage.

---

## If Asked "Do you train the model?"

> No. I use a pretrained ArcFace model for inference. The model has already learned facial representations during its original training. My application generates embeddings from that model and performs similarity matching against registered personnel.

---

## If Asked "Why not train a classifier?"

> A classifier would tie the model's classes to specific employees. Adding or removing employees could require retraining. Embedding-based recognition is more suitable for a system where the set of authorized personnel changes over time.

---

## If Asked "What is an embedding?"

> An embedding is a numerical representation of a face generated by the neural network. Faces that are similar should have embeddings that are relatively close according to the selected distance or similarity metric.

---

## If Asked "What is the difference between recognition and authorization?"

> Recognition determines who the person is. Authorization determines whether that person is allowed to access the requested area. I keep those two processes separate in my system.

---

# 45. Limitations

The prototype may have limitations.

- Lighting can affect recognition.
- Extreme angles can reduce recognition performance.
- Face occlusion can affect results.
- Camera quality affects performance.
- Threshold selection affects false acceptance and false rejection.
- Basic face recognition is vulnerable to spoofing without liveness detection.
- A prototype should not be treated as a production-grade physical security system.

Do not claim security properties that have not actually been implemented and tested.

---

# 46. Future Enhancements

Possible future improvements:

1. Liveness detection
2. Anti-spoofing
3. Multiple cameras
4. Visitor management
5. Security alerts
6. Email notifications
7. Role-based access control
8. PostgreSQL
9. Cloud deployment
10. Containerization
11. Advanced access analytics
12. Multi-factor authentication

These should remain future enhancements unless there is sufficient time to implement and test them properly.

---

# 47. Development Rules

The implementation must follow these rules:

### Rule 1

Do not add technologies that are not required.

### Rule 2

Do not train ArcFace from scratch.

### Rule 3

Do not retrain the face-recognition model when personnel change.

### Rule 4

Do not duplicate employee biometric records unnecessarily between areas.

### Rule 5

Keep authorization separate from recognition.

### Rule 6

Unknown users must not receive access.

### Rule 7

Do not expose raw face embeddings through the frontend.

### Rule 8

Do not invent ML accuracy numbers.

### Rule 9

Do not claim features that are not implemented.

### Rule 10

Prioritize a working end-to-end MVP over additional features.

---

# 48. Final Architecture

```text
                         FACEGUARD
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
      ADMIN UI                          ACCESS TERMINAL
   HTML/CSS/JS                         Camera + Browser
          │                                   │
          └─────────────────┬─────────────────┘
                            │
                            ▼
                         FastAPI
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
      Personnel         Face Engine       Authorization
      Management       OpenCV + ArcFace      Service
          │                 │                 │
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                         SQLite
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
      Personnel        Embeddings        Permissions
                            │                 │
                            └────────┬────────┘
                                     ▼
                              Area Galleries
                                     │
                                     ▼
                                  Matching
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                           GRANTED        DENIED
                              │             │
                              └──────┬──────┘
                                     ▼
                                Access Logs
```

---

# 49. Final Principle

FaceGuard should demonstrate a complete, understandable system rather than simply demonstrate that a face-recognition library can identify a person.

The important technical idea is:

```text
Pretrained Face Model
        +
Face Embeddings
        +
Authorization-Specific Galleries
        +
Access-Control Rules
        +
Audit Logging
        =
FaceGuard
```

The system should remain simple enough that every implemented component can be explained honestly during an interview.