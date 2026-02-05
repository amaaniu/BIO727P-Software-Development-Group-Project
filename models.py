from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, MetaData, table, create_engine
from sqlalchemy.orm import declarative_base

db_url = 'sqlite:///experiment.db'  # do we need to change this to the uploaded database file?
engine = create_engine(db_url)
base = declarative_base()
class User(base):
    __tablename__ = 'User'
    user_id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)  
    last_login = Column(DateTime)  

class Experiment(base):
    __tablename__ = 'Experiment'
    experiment_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('User.user_id'), nullable=False)
    experiment_name = Column(String, nullable=False)
    uniprot_id = Column(String, nullable=False)
    wt_protein_sequence = Column(String)
    protein_features = Column(String)
    plasmid_sequence = Column(String)
    created_at = Column(DateTime, nullable=False)  
    status = Column(String)

class Variant(base):
    __tablename__ = 'Variant'
    variant_id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey('Experiment.experiment_id'), nullable=False)
    generation = Column(Integer, nullable=False)
    plasmid_variant_index = Column(String, nullable=False)
    parent_variant_id = Column(Integer, ForeignKey('Variant.variant_id'))
    dna_sequence = Column(String, nullable=False)
    protein_sequence = Column(String)
    protein_yield = Column(Float, nullable=False)
    dna_yield = Column(Float, nullable=False)
    activity_score = Column(Float)
    mutation_count = Column(Integer)
    created_at = Column(DateTime, nullable=False)  
    variant_metadata = Column(String)

class Mutations(base):
    __tablename__ = 'Mutations'
    mutation_id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(Integer, ForeignKey('Variant.variant_id'), nullable=False)
    position = Column(Integer, nullable=False)
    wt_residue = Column(String, nullable=False)
    mutant_residue = Column(String, nullable=False)
    mutation_type = Column(String, nullable=False)
    generation = Column(Integer, nullable=False)
    codon_change = Column(String)

class Activity(base):
    __tablename__ = 'Activity'
    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(Integer, ForeignKey('Variant.variant_id'), nullable=False)
    predicted_activity_score = Column(Float, nullable=False)
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

class Control(base):
    __tablename__ = 'Control'
    control_id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey('Experiment.experiment_id'), nullable=False)
    control_name = Column(String, nullable=False)
    dna_sequence = Column(String, nullable=False)
    protein_yield = Column(Float, nullable=False)
    dna_yield = Column(Float, nullable=False)
    activity_score = Column(Float)
    created_at = Column(DateTime, nullable=False)