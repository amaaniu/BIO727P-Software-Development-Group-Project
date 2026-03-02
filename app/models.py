from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from . import db

class User(db.Model, UserMixin):
    __tablename__ = 'User'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    # Relationships
    experiments = db.relationship('Experiment', backref='user', lazy='dynamic')
    
    # Flask-Login requires a method to get the user ID, which is used to manage user sessions. Since the primary key column is named 'user_id' instead of the default 'id', we need to define the get_id method to return the user_id as a string for Flask-Login to function correctly. 
    # The alternative is to set the primary key column name to 'id' and Flask-Login will automatically use it without needing to define a get_id method. However, since the primary key column is named 'user_id', we need to define the get_id method to return the user_id as a string for Flask-Login to function correctly.
    def get_id(self):
        return str(self.user_id)
    
class Experiment(db.Model):
    __tablename__ = 'Experiment'
    experiment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), nullable=False)
    experiment_name = db.Column(db.Text, nullable=False)
    uniprot_id = db.Column(db.Text, nullable=False)
    wt_protein_sequence = db.Column(db.Text)
    plasmid_sequence = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.Text)
    
    # Relationships
    variants = db.relationship('Variant', backref='experiment', lazy='dynamic')

class Variant(db.Model):
    __tablename__ = 'Variant'
    variant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('Experiment.experiment_id'), nullable=False)
    generation = db.Column(db.Integer, nullable=False)
    experiment_variant_id = db.Column(db.Integer, nullable=False)
    plasmid_variant_index = db.Column(db.Text, nullable=False)
    parent_variant_id = db.Column(db.Integer, db.ForeignKey('Variant.variant_id'))
    dna_sequence = db.Column(db.Text, nullable=False)
    protein_sequence = db.Column(db.Text)
    protein_yield = db.Column(db.Float, nullable=False)
    dna_yield = db.Column(db.Float, nullable=False)
    activity_score = db.Column(db.Float)
    mutation_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    custom_metadata = db.Column(db.Text)  
    
    # Relationships
    mutations = db.relationship('Mutations', backref='variant', lazy='dynamic')
    parent = db.relationship('Variant', remote_side=[variant_id], backref='children')

class Mutations(db.Model):
    __tablename__ = 'Mutations'
    mutation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('Variant.variant_id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    wt_residue = db.Column(db.Text, nullable=False)
    mutant_residue = db.Column(db.Text, nullable=False)
    mutation_type = db.Column(db.Text, nullable=False)
    generation = db.Column(db.Integer, nullable=False)
    codon_change = db.Column(db.Text)


class UniProtData(db.Model):
    __tablename__ = 'UniProt_Data'

    uniprot_id = db.Column(db.Text, primary_key=True)
    protein_name = db.Column(db.Text)
    organism_name = db.Column(db.Text)
    protein_length = db.Column(db.Integer, nullable=False)
    protein_sequence = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class UniProtFeature(db.Model):
    __tablename__ = 'UniProt_Feature'
    __table_args__ = (
        db.UniqueConstraint(
            'uniprot_id',
            'feature_type',
            'start_pos',
            'end_pos',
            'description',
            name='uq_uniprot_feature_identity',
        ),
    )

    feature_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uniprot_id = db.Column(db.Text, db.ForeignKey('UniProt_Data.uniprot_id'), nullable=False)

    feature_type = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    start_pos = db.Column(db.Integer, nullable=False)
    end_pos = db.Column(db.Integer, nullable=False)
