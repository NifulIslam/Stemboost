#!/usr/bin/env bash
# ============================================================
#  STEMboost – One-Command Setup Script
#  Usage:  bash setup.sh
# ============================================================

set -e   # Exit immediately on error

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   STEMboost Setup – BVI Learning Platform ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Create & activate virtual environment ──────────────────
echo "▶  Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# ── 2. Install dependencies ───────────────────────────────────
echo "▶  Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── 3. Run migrations ─────────────────────────────────────────
echo "▶  Applying database migrations..."
python manage.py makemigrations core
python manage.py migrate

# ── 4. Collect static files ───────────────────────────────────
echo "▶  Collecting static files..."
python manage.py collectstatic --noinput --quiet

# ── 5. Seed demo users ────────────────────────────────────────
echo "▶  Creating demo users..."
python manage.py shell -c "
from core.models import User

def make(email, pw, role):
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(email=email, password=pw, role=role)
        print(f'  ✓ Created {role}: {email}')
    else:
        print(f'  – Already exists: {email}')

make('learner@stemboost.io', 'STEMlearn1!', 'learner')
make('mentor@stemboost.io',  'STEMmentor1!', 'mentor')
make('admin@stemboost.io',   'STEMadmin1!', 'admin')
print('  Done.')
"

# ── 6. Print credentials & instructions ───────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅  STEMboost is Ready!                     ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Run:  source venv/bin/activate                          ║"
echo "║        python manage.py runserver                        ║"
echo "║  Then open: http://127.0.0.1:8000/                       ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Demo Accounts (all passwords below)                     ║"
echo "║                                                          ║"
echo "║  Learner →  learner@stemboost.io   / STEMlearn1!         ║"
echo "║  Mentor  →  mentor@stemboost.io    / STEMmentor1!        ║"
echo "║  Admin   →  admin@stemboost.io     / STEMadmin1!         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Pages                                                   ║"
echo "║   /             Landing page  (audio welcome)            ║"
echo "║   /login/       Login                                    ║"
echo "║   /register/    Registration                             ║"
echo "║   /learner/     Learner dashboard                        ║"
echo "║   /mentor/      Mentor dashboard                         ║"
echo "║   /admin-dashboard/  Admin dashboard                     ║"
echo "║   /django-admin/     Django built-in admin               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
