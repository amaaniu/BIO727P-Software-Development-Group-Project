"""Routes for the main blueprint, including dashboard and user-guide docs."""
from pathlib import Path
from flask import Blueprint, render_template, request, abort, current_app, send_from_directory, redirect, url_for
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

# Creates the route for the user guide page and the MkDocs documentation sub-routes.
# The user_guide_docs route serves the built MkDocs documentation.
@main_bp.route('/user-guide')
def user_guide():
    """Renders the user guide page."""
    return render_template('tutorial.html')

@main_bp.route('/user-guide/docs')
def user_guide_docs_root():
    """Normalises docs root URL to include trailing slash."""
    return redirect(url_for('main.user_guide_docs', doc_path='index.html'))

@main_bp.route('/user-guide/docs/')
@main_bp.route('/user-guide/docs/<path:doc_path>')
def user_guide_docs(doc_path='index.html'):
    """Serves built MkDocs pages under the user guide route."""
    docs_dir = Path(current_app.root_path).parent / 'site'
    if not docs_dir.exists():
        abort(404, description='Documentation is not built yet. Run "mkdocs build".')

    doc_path = (doc_path or 'index.html').lstrip('/')
    if doc_path.endswith('/'):
        doc_path = f'{doc_path}index.html'
    elif '.' not in Path(doc_path).name:
        doc_path = f'{doc_path}/index.html'

    return send_from_directory(docs_dir, doc_path)

# Creates the route for the staging page, which is only accessible to authenticated users.
@main_bp.route('/upload')
@login_required
def upload_data():
    """Route for uploading experimental data."""
    return render_template('upload.html')

# Creates the authenticated dashboard route with filtering, searching, and sorting.
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

    # 2. Pre-aggregate variant stats per experiment to guarantee one row per experiment.
    variant_stats = (
        db.select(
            Variant.experiment_id.label('experiment_id'),
            func.max(Variant.created_at).label('last_variant_at'),
            func.max(Variant.generation).label('max_generation'),
            func.count(Variant.variant_id).label('variant_count'),
        )
        .group_by(Variant.experiment_id)
        .subquery()
    )
    last_updated_expr = func.coalesce(variant_stats.c.last_variant_at, Experiment.created_at)
    max_generation_expr = func.coalesce(variant_stats.c.max_generation, 0)

    sort_options = {
        'updated': last_updated_expr,
        'name': Experiment.experiment_name,
        'generation': max_generation_expr,
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
            variant_stats.c.last_variant_at,
            variant_stats.c.max_generation,
            func.coalesce(variant_stats.c.variant_count, 0).label('variant_count'),
        )
        .outerjoin(variant_stats, variant_stats.c.experiment_id == Experiment.experiment_id)
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
    # 4. Sorts the per-experiment rows returned from the pre-aggregated subquery.
    experiments_query = experiments_query.order_by(order_clause, Experiment.experiment_id.desc())
    # 5. Executes the query and processes the results to determine the status of each experiment based on its raw status and variant count. 
    all_experiments = []
    for row in db.session.execute(experiments_query):

        if not row.experiment_id: 
            continue

        raw_status = (row.status or '').strip().lower()
        variant_total = int(row.variant_count or 0)

        # Dashboard tracker only shows experiments that have uploaded run data.
        # Experiments with no variants are treated as not-yet-uploaded and stay out of the tracker table.
        if variant_total == 0:
            continue

        if raw_status in {'completed', 'complete', 'done'}:
            status = 'Completed'
        else:
            status = 'In Progress'
            
        # Structures the experiment data for rendering in the dashboard template, including the experiment ID, name, UniProt ID, determined status, maximum generation number, total variant count, and last updated timestamp.
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

    # 6. Applies the selected status filter and passes results to the template.
    if status_filter == 'all':
        experiments = all_experiments
    else:
        experiments = [
            exp for exp in all_experiments 
            if exp['status'].lower().replace(' ', '_') == status_filter]

    return render_template(
        'dashboard.html',
        experiments=experiments,
        totals=totals,
        status_filter=status_filter,
        search_query=search_query,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

# Creates the route for viewing an experiment report. The route checks if the experiment belongs to the logged-in user and redirects to the report view if it exists, otherwise it returns a 404 error.
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
    return redirect(url_for('report.view_report', experiment_id=experiment_id))

# Creates the route for downloading an experiment report as a PDF. The route checks if the experiment belongs to the logged-in user and redirects to the PDF download view if it exists, otherwise it returns a 404 error.
@main_bp.route('/experiments/<int:experiment_id>/download_pdf')
@login_required
def download_pdf(experiment_id):
    """Redirects to report PDF download for an experiment owned by the logged-in user."""
    experiment = db.session.scalar(
        db.select(Experiment).where(
            Experiment.experiment_id == experiment_id,
            Experiment.user_id == current_user.user_id,
        )
    )
    if experiment is None:
        abort(404)
    return redirect(url_for('report.download_report_pdf', experiment_id=experiment_id))

# Creates the route for starting a new experiment. The route renders the staging page where users can upload their experimental data to start a new directed evolution campaign.
@main_bp.route('/experiments/new')
@login_required
def new_experiment():
    """Renders the page used to start a new experiment."""
    return render_template('upload.html')
