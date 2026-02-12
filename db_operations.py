# db_operations.py

from models import db, Experiment, Variant, Mutations, Activity, ControlData
from datetime import datetime
import json

def insert_experiment_records(records, user_id):
    """
    Insert experiment records into database.
    
    Args:
        records: List of experiment dicts from file_processor
        user_id: ID of user creating experiments
        
    Returns:
        List of created Experiment objects with experiment_id populated
    """
    experiment_objects = []
    
    for record in records:
        experiment = Experiment(
            user_id=user_id,
            experiment_name=record['experiment_name'],
            uniprot_id=record['uniprot_id'],
            wt_protein_sequence=record.get('wt_protein_sequence'),
            protein_features=record.get('protein_features'),
            plasmid_sequence=record.get('plasmid_sequence'),
            status=record.get('status'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(experiment)
        experiment_objects.append(experiment)
    
    db.session.commit()
    return experiment_objects


def insert_variant_records(records, experiment_id):
    """
    Insert variant records into database.
    
    Args:
        records: List of variant dicts from file_processor
        experiment_id: ID of experiment these variants belong to
        
    Returns:
        List of created Variant objects with variant_id populated
    """
    variant_objects = []
    
    for record in records:
        variant = Variant(
            experiment_id=experiment_id,
            generation=record['generation'],
            plasmid_variant_index=record['plasmid_variant_index'],
            parent_variant_id=None,  
            dna_sequence=record['dna_sequence'],
            protein_sequence=record.get('protein_sequence'),
            protein_yield=record['protein_yield'],
            dna_yield=record['dna_yield'],
            activity_score=record.get('activity_score'),
            mutation_count=record.get('mutation_count'),
            created_at=datetime.utcnow(),
            metadata_=None
        )
        
        db.session.add(variant)
        variant_objects.append(variant)
    
    db.session.commit()
    return variant_objects


def insert_mutation_records(records, variant_id):
    """
    Insert mutation records into database.
    
    Args:
        records: List of mutation dicts from file_processor
        variant_id: ID of variant these mutations belong to
        
    Returns:
        List of created Mutations objects
    """
    mutation_objects = []
    
    for record in records:
        mutation = Mutations(
            variant_id=variant_id,
            position=record['position'],
            wt_residue=record['wt_residue'],
            mutant_residue=record['mutant_residue'],
            mutation_type=record['mutation_type'],
            generation=record['generation'],
            codon_change=record.get('codon_change')
        )
        
        db.session.add(mutation)
        mutation_objects.append(mutation)
    
    db.session.commit()
    return mutation_objects


def insert_activity_records(records, variant_id):
    """
    Insert activity records into database.
    
    Args:
        records: List of activity dicts from file_processor
        variant_id: ID of variant these activities belong to
        
    Returns:
        List of created Activity objects
    """
    activity_objects = []
    
    for record in records:
        activity = Activity(
            variant_id=variant_id,
            qc_pass=record.get('qc_pass', 1), 
            measurement_type=record['measurement_type'],
            raw_value=record['raw_value']
        )
        
        db.session.add(activity)
        activity_objects.append(activity)
    
    db.session.commit()
    return activity_objects


def insert_control_records(records, experiment_id):
    """
    Insert control records into database.
    
    Args:
        records: List of control dicts from file_processor
        experiment_id: ID of experiment these controls belong to
        
    Returns:
        List of created ControlData objects
    """
    control_objects = []
    
    for record in records:
        control = ControlData(
            experiment_id=experiment_id,
            generation=record['generation'],
            control_type=record['control_type'],
            protein_yield=record['protein_yield'],
            dna_yield=record['dna_yield']
        )
        
        db.session.add(control)
        control_objects.append(control)
    
    db.session.commit()
    return control_objects


def process_and_insert(file, experiment_id=None, user_id=None):
    """
    Main function: Process file and insert to appropriate table.
    
    Args:
        file: Flask FileStorage object
        experiment_id: Required for variant/mutation/activity/control data
        user_id: Required for experiment data
        
    Returns:
        Dict with insertion results
        
    Raises:
        ValueError: If required IDs not provided or insertion fails
    """
    from file_processor import process_file
    
    # Process file
    result = process_file(file)
    data_type = result['data_type']
    records = result['records']
    
    # Insert based on data type
    try:
        if data_type == 'experiment':
            if not user_id:
                raise ValueError("user_id required for experiment data")
            
            created = insert_experiment_records(records, user_id)
            return {
                'success': True,
                'data_type': data_type,
                'count': len(created),
                'objects': created
            }
        
        elif data_type == 'variant':
            if not experiment_id:
                raise ValueError("experiment_id required for variant data")
            
            created = insert_variant_records(records, experiment_id)
            return {
                'success': True,
                'data_type': data_type,
                'count': len(created),
                'objects': created
            }
        
        elif data_type == 'mutation':
            if not experiment_id:
                raise ValueError("experiment_id required for mutation data")
            
           
            variant = Variant.query.filter_by(experiment_id=experiment_id).first()
            if not variant:
                raise ValueError("No variants found for this experiment")
            
            created = insert_mutation_records(records, variant.variant_id)
            return {
                'success': True,
                'data_type': data_type,
                'count': len(created),
                'objects': created
            }
        
        elif data_type == 'activity':
            if not experiment_id:
                raise ValueError("experiment_id required for activity data")
            
            
            variant = Variant.query.filter_by(experiment_id=experiment_id).first()
            if not variant:
                raise ValueError("No variants found for this experiment")
            
            created = insert_activity_records(records, variant.variant_id)
            return {
                'success': True,
                'data_type': data_type,
                'count': len(created),
                'objects': created
            }
        
        elif data_type == 'control':
            if not experiment_id:
                raise ValueError("experiment_id required for control data")
            
            created = insert_control_records(records, experiment_id)
            return {
                'success': True,
                'data_type': data_type,
                'count': len(created),
                'objects': created
            }
    
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Database insertion failed: {str(e)}")