from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'User'
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    last_login = db.Column(db.DateTime)

class Experiment(db.Model):
    __tablename__ = 'Experiment'
    experiment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), nullable=False)
    experiment_name = db.Column(db.String, nullable=False)
    uniprot_id = db.Column(db.String, nullable=False)
    wt_protein_sequence = db.Column(db.String)
    protein_features = db.Column(db.String)
    plasmid_sequence = db.Column(db.String)
    created_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String)

class Variant(db.Model):
    __tablename__ = 'Variant'
    variant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('Experiment.experiment_id'), nullable=False)
    generation = db.Column(db.Integer, nullable=False)
    plasmid_variant_index = db.Column(db.String, nullable=False)
    parent_variant_id = db.Column(db.Integer, db.ForeignKey('Variant.variant_id'))
    dna_sequence = db.Column(db.String, nullable=False)
    protein_sequence = db.Column(db.String)
    protein_yield = db.Column(db.Float, nullable=False)
    dna_yield = db.Column(db.Float, nullable=False)
    activity_score = db.Column(db.Float)
    mutation_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False)
    variant_metadata = db.Column(db.String)

class Mutations(db.Model):
    __tablename__ = 'Mutations'
    mutation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('Variant.variant_id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    wt_residue = db.Column(db.String, nullable=False)
    mutant_residue = db.Column(db.String, nullable=False)
    mutation_type = db.Column(db.String, nullable=False)
    generation = db.Column(db.Integer, nullable=False)
    codon_change = db.Column(db.String)

class Activity(db.Model):
    __tablename__ = 'Activity'
    prediction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('Variant.variant_id'), nullable=False)
    predicted_activity_score = db.Column(db.Float, nullable=False)
    model_name = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

class Control(db.Model):
    __tablename__ = 'Control'
    control_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('Experiment.experiment_id'), nullable=False)
    control_name = db.Column(db.String, nullable=False)
    dna_sequence = db.Column(db.String, nullable=False)
    protein_yield = db.Column(db.Float, nullable=False)
    dna_yield = db.Column(db.Float, nullable=False)
    activity_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False)
