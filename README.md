# STEMboost

**An accessible STEM learning platform for blind and visually-impaired (BVI) learners.**

STEMboost connects learners with mentors through structured, audio-first courses. Admins manage courses and assignments; mentors track learner progress and chat directly with their assigned students; learners read chapters aloud using built-in text-to-speech.
## Installation & Setup

### Prerequisites

- Python 3.11+

### Steps


```bash
# 1. Clone/download the repository in your local machine

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate     

# 3. Install dependencies
pip install -r requirements.txt

pip install transformers torch Pillow
```

---

## Run the project

```bash
# Apply all migrations (creates the SQLite database)
python manage.py migrate
# start the Django server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to find the running website
