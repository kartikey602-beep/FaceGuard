# FaceGuard

FaceGuard is a local prototype for personnel face registration and area-based access decisions. A browser dashboard talks to a FastAPI backend, which uses SQLite for personnel, face embeddings, areas, permissions, and access logs.

## Technologies

- Python 3.11 or newer, FastAPI, and Uvicorn
- SQLite through Python's built-in `sqlite3` module
- DeepFace with the pretrained ArcFace model, OpenCV, NumPy, and `tf-keras`
- Plain HTML, CSS, and vanilla JavaScript

## Architecture

The browser pages call JSON or multipart endpoints on the same FastAPI server. Routes validate API requests and call the database or service layer. `face_engine.py` handles image validation, face detection, embedding generation, and embedding comparison. `gallery_service.py` reads the active area's permitted personnel and their existing embeddings. `access_service.py` coordinates recognition against that gallery, makes the access decision, and records it through `logging_service.py`.

```text
HTML/CSS/JavaScript
        │ same-origin fetch
        ▼
FastAPI routes ── services ── SQLite
                       │          ├─ personnel
                       │          ├─ face_embeddings
                       │          ├─ permissions ─ areas
                       │          └─ access_logs
                       └─ pretrained ArcFace face engine
```

## Face recognition and authorization

ArcFace is pretrained and used for inference. FaceGuard does not train or fine-tune ArcFace, and adding personnel does not require training an identity classifier. The engine converts one detected face into a numerical embedding. It compares embeddings using cosine distance: smaller distances mean more similar vectors. `FACE_MATCH_THRESHOLD` can override DeepFace's ArcFace/cosine default; evaluate a threshold with representative images before relying on it. A distance is not a confidence percentage, and this project does not claim a particular accuracy.

The authorization gallery is a temporary in-memory Python collection, not a database table. For a verification request, FaceGuard queries only the selected active area's permission links, active personnel, and their stored embeddings. It does not search all personnel as a fallback. Permission changes affect the next gallery build; embeddings stay in `face_embeddings` and are not copied into areas or galleries.

## Database

SQLite creates `database/faceguard.db` on application startup. Foreign keys are enabled for each connection.

- `personnel`: employee details and active status.
- `face_embeddings`: one or more ArcFace vectors linked to a person.
- `areas`: restricted locations and active status.
- `permissions`: unique links between personnel and areas.
- `access_logs`: each grant or denial, linked to an area and optionally to a recognized person.

The API's normal personnel, area, access, and log responses do not return embedding vectors. The local database contains biometric data and is excluded from Git.

## Install and run on Windows

Use Python 3.11 or newer. From the project root, open PowerShell and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Open <http://127.0.0.1:8000/> for the dashboard and <http://127.0.0.1:8000/docs> for interactive API documentation. FastAPI serves all five frontend pages and their static assets. The first face-engine request may download pretrained ArcFace weights through DeepFace; model training does not occur.

For a custom comparison threshold, set it in the same PowerShell session before starting the server, for example:

```powershell
$env:FACE_MATCH_THRESHOLD = "0.4"
```

This is only a configuration example, not a recommended universal threshold.

## Frontend pages

- **Dashboard** derives personnel, active-area, daily access counts, and recent events from the backend APIs. Daily counts and date filtering use the UTC date stored by SQLite.
- **Personnel** creates and edits personnel, changes active status, and registers a face through `POST /api/personnel/{id}/register-face`.
- **Areas** creates and edits areas and manages actual personnel-area permission links through the API.
- **Access verification** selects an area and uploads an image to `POST /api/access/verify`. It also offers optional browser camera capture using `getUserMedia`; camera access requires the browser's permission and a secure context such as localhost.
- **Access logs** displays backend log rows and filters by area, result, UTC date, or person text.

The frontend uses a shared request helper in `frontend/js/app.js`; page-specific behavior is in separate JavaScript files. It does not store a frontend-only permission list or display raw embeddings.

## Test the project

Run the complete unittest suite and JavaScript syntax checks from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
Get-ChildItem frontend\js -Filter *.js | ForEach-Object { node --check $_.FullName }
```

The automated face-engine unit tests use a small fake DeepFace object to exercise image/error handling and comparison without model downloads. Access verification, gallery, database, personnel, permission, route-schema, and log tests use isolated temporary SQLite databases. These tests do not substitute for testing with your own varied images.

If the local sample images are present, test the real face engine on two images of the same person:

```powershell
.\.venv\Scripts\python.exe -m tests.test_face_engine data/faces/person_front.jpg data/faces/person_front_2.jpg --expect-match
```

The command reports the measured cosine distance and configured/default threshold. Do not interpret the distance as a percentage.

## Five-minute demonstration

1. Start the server and open `http://127.0.0.1:8000/`.
2. Open **Personnel**. Use an active personnel record or create one, then choose **Register face** and upload one clear image containing that person.
3. Open **Areas**. Create or use an active area, then **Manage access** and grant the same active person permission.
4. Open **Access verification**, select that area, upload a different clear image of that person, then click **Verify access**. The page displays the backend's grant or denial, person/area details, cosine distance, and timestamp.
5. Open **Access logs** and confirm the attempt appears. Revoke the permission from Areas and repeat verification to demonstrate a denial.

This repository ignores local face images and the SQLite database. For a fresh clone, supply your own test image and create personnel, area, permission, and face-registration data through the UI before the demonstration. In this workspace, the existing sample data was tested with personnel ID `2` (`EMP-001`, Kartikey Test), area ID `1` (Server Room), a registered image, and a different image of the same person.

## Limitations

FaceGuard is an educational prototype, not production-grade physical security software. It has no login/authentication, liveness detection, or anti-spoofing. Lighting, pose, image quality, and threshold selection can affect results. The SQLite setup is intended for a local demonstration. Protect the database and image files as sensitive biometric data, and do not claim an access decision is secure against spoofing.
