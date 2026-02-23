# This file defines the routes for the main blueprint of the Flask application. It includes routes for the home page, features page, documentation page, tutorial page, and dashboard page. The dashboard page is protected by a login_required decorator, meaning that only authenticated users can access it. The routes will render the appropriate templates for each page.
from pathlib import Path
from flask import Blueprint, render_template, request, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from . import db
from .models import Experiment, Variant

main_bp = Blueprint('main', __name__)

# Creates the route for the home page
@main_bp.route('/')
def home():
    """Renders the home page."""

    return render_template('index.html')

# Creates the route for the features page
@main_bp.route('/features')
def features():
    """Renders the features page."""

    return render_template('features.html')

# Creates the route for the documentation page
@main_bp.route('/documentation')
def documentation():
    """Renders the documentation page."""

    return 'soon rendering template documentation'

# Creates the route for the tutorial page
@main_bp.route('/tutorial')
def tutorial():
    """Renders the tutorial page."""
    return render_template('tutorial.html')


@main_bp.route('/tutorial/docs/')
@main_bp.route('/tutorial/docs/<path:doc_path>')
def tutorial_docs(doc_path='index.html'):
    """Serves built MkDocs pages under the tutorial route."""
    docs_dir = Path(current_app.root_path).parent / 'site'
    if not docs_dir.exists():
        abort(404, description='Documentation is not built yet. Run "mkdocs build".')
    return send_from_directory(docs_dir, doc_path)

# Creates the route for the staging page, which is only accessible to authenticated users.
@main_bp.route('/upload')
@login_required
def upload_data():
    """Route for uploading experimental data."""
    return render_template('upload.html')

# Creates the route for the dashboard page, which is only accessible to authenticated users. 
# The dashboard route retrieves and processes experiment data for the logged-in user, allowing them to view and manage their directed evolution campaigns. It supports filtering, searching, and sorting of experiments based on various criteria such as status, name, generation count, and last updated time. The processed data is then passed to the dashboard template for rendering.
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Renders the dashboard page for the authenticated user, displaying their
    directed evolution analyses with support for filtering, sorting, and searching.
    """

    # 1. Parse and validate request parameters for filtering/sorting
    status_filter = request.args.get('status', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'updated').strip().lower()
    sort_dir = request.args.get('dir', 'desc').strip().lower()

    if status_filter not in {'all', 'in_progress', 'completed'}:
        status_filter = 'all'
    if sort_by not in {'updated', 'name', 'generation', 'status'}:
        sort_by = 'updated'
    if sort_dir not in {'asc', 'desc'}:
        sort_dir = 'desc'

    # 2. Define expressions for sorting and aggregation using SQLAlchemy functions. 
    # The max_variant_created expression calculates the latest creation timestamp among variants for each experiment, while max_generation computes the highest generation number. The variant_count expression counts the total number of variants associated with each experiment. The last_updated_expr uses the COALESCE function to determine the last updated time for an experiment, defaulting to the experiment's creation time if no variants exist.
    max_variant_created = func.max(Variant.created_at) 
    max_generation = func.max(Variant.generation)
    variant_count = func.count(Variant.variant_id)
    last_updated_expr = func.coalesce(max_variant_created, Experiment.created_at)

    sort_options = {
        'updated': last_updated_expr,
        'name': Experiment.experiment_name,
        'generation': max_generation,
        'status': Experiment.status,
    }
    sort_expr = sort_options[sort_by]
    order_clause = sort_expr.asc() if sort_dir == 'asc' else sort_expr.desc()

    # 3. Constructs a SQLAlchemy query to retrieve experiments for the current user.
    experiments_query = (
        db.select(
            Experiment.experiment_id,
            Experiment.experiment_name,
            Experiment.uniprot_id,
            Experiment.status,
            Experiment.created_at,
            max_variant_created.label('last_variant_at'),
            max_generation.label('max_generation'),
            variant_count.label('variant_count'),
        )
        .outerjoin(Variant, Variant.experiment_id == Experiment.experiment_id)
        .where(Experiment.user_id == current_user.user_id)
    )
    # Apply search filter if provided
    if search_query:
        pattern = f"%{search_query.lower()}%"
        experiments_query = experiments_query.where(
            or_(
                func.lower(Experiment.experiment_name).like(pattern),
                func.lower(Experiment.uniprot_id).like(pattern),
            )
        )
    # 4. Groups the query results by experiment attributes and sorts them in the specified order. 
        experiments_query = (
        experiments_query.group_by(
            Experiment.experiment_id,
            Experiment.experiment_name,
            Experiment.uniprot_id,
            Experiment.status,
            Experiment.created_at,
        )
        .order_by(order_clause, Experiment.experiment_id.desc())
    )
    # 5. Executes the query and processes the results to determine the status of each experiment based on its raw status and variant count. 
    all_experiments = []
    for row in db.session.execute(experiments_query):
        raw_status = (row.status or '').strip().lower()
        variant_total = int(row.variant_count or 0)
        if raw_status in ('completed', 'complete', 'done'):
            status = 'Completed'
        elif raw_status in ('in-progress', 'in progress', 'active', 'ongoing', 'paused', 'hold', 'on hold'):
            status = 'In Progress'
        else:
            # Fallback: if variants exist, treat as work-in-progress; otherwise staged.
            status = 'In Progress' if variant_total > 0 else 'Staged'
            
        # Structure the experiment data for rendering in the dashboard template, including the experiment ID, name, UniProt ID, determined status, maximum generation number, total variant count, and last updated timestamp.
        all_experiments.append({
            'experiment_id': row.experiment_id,
            'experiment_name': row.experiment_name,
            'uniprot_id': row.uniprot_id,
            'status': status,
            'max_generation': int(row.max_generation or 0),
            'variant_count': variant_total,
            'last_updated': row.last_variant_at or row.created_at,
        })

    totals = {
        'all': len(all_experiments),
        'in_progress': sum(1 for exp in all_experiments if exp['status'] == 'In Progress'),
        'completed': sum(1 for exp in all_experiments if exp['status'] == 'Completed'),
    }

    # 6. Applies the selected status filter to the list of experiments, allowing the user to view only experiments that match the chosen status category (e.g., all, staged, in-progress, completed). The filtered list of experiments is then passed to the dashboard template for rendering, along with the summary totals and current filter/sort settings for display on the dashboard page.
    if status_filter == 'all':
        experiments = all_experiments
    else:
        experiments = [exp for exp in all_experiments if exp['status'].lower() == status_filter]

    return render_template(
        'dashboard.html',
        experiments=experiments,
        totals=totals,
        status_filter=status_filter,
        search_query=search_query,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@main_bp.route('/experiments/<int:experiment_id>/report')
@login_required
def view_report(experiment_id):
    """Placeholder report route for an experiment owned by the logged-in user."""
    experiment = db.session.scalar(
        db.select(Experiment).where(
            Experiment.experiment_id == experiment_id,
            Experiment.user_id == current_user.user_id,
        )
    )
    if experiment is None:
        abort(404)
    return f"Report view coming soon for experiment: {experiment.experiment_name}"

@main_bp.route('/experiments/new')
@login_required
def new_experiment():
    return render_template('staging.html')

