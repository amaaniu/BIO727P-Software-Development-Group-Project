import os
import pandas as pd
from io import BytesIO
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'.tsv', '.json'}

# Required fields for each data type (fields that cannot be None)
EXPERIMENT_REQUIRED = {'experiment_name', 'uniprot_id'}
VARIANT_REQUIRED = {'generation', 'plasmid_variant_index', 'dna_sequence', 'protein_yield', 'dna_yield'}
MUTATION_REQUIRED = {'position', 'wt_residue', 'mutant_residue', 'mutation_type', 'generation'}
ACTIVITY_REQUIRED = {'predicted_activity_score', 'model_name'}
CONTROL_REQUIRED = {'control_name', 'dna_sequence', 'protein_yield', 'dna_yield'}

# All fields for each data type
EXPERIMENT_FIELDS = ['experiment_name', 'uniprot_id', 'wt_protein_sequence', 'protein_features', 'plasmid_sequence', 'status']
VARIANT_FIELDS = ['generation', 'plasmid_variant_index', 'dna_sequence', 'protein_sequence', 'protein_yield', 'dna_yield', 'activity_score', 'mutation_count']
MUTATION_FIELDS = ['position', 'wt_residue', 'mutant_residue', 'mutation_type', 'generation', 'codon_change']
ACTIVITY_FIELDS = ['predicted_activity_score', 'model_name']
CONTROL_FIELDS = ['control_name', 'dna_sequence', 'protein_yield', 'dna_yield', 'activity_score']


def validate_file_extension(filename):
    """
    Extract and validate file extension from filename.

    Args:
        filename: Original filename from user upload

    Returns:
        Lowercase file extension (e.g., '.tsv', '.json')

    Raises:
        ValueError: If extension is not in allowed formats
    """
    _, extension = os.path.splitext(filename)
    extension = extension.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {extension}. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}")

    return extension


def parse_tsv(file_content):
    """
    Parse TSV file content using pandas.

    Args:
        file_content: Raw bytes from file

    Returns:
        pandas DataFrame
    """
    return pd.read_csv(BytesIO(file_content), sep='\t')


def parse_json(file_content):
    """
    Parse JSON file content using pandas.

    Args:
        file_content: Raw bytes from file

    Returns:
        pandas DataFrame
    """
    return pd.read_json(BytesIO(file_content))


def detect_data_type(df):
    """
    Detect which database table the data belongs to based on column names.

    Args:
        df: pandas DataFrame from parsed file

    Returns:
        String indicating data type: 'experiment', 'variant', 'mutation', 'activity', 'control'

    Raises:
        ValueError: If data type cannot be determined
    """
    if df.empty:
        raise ValueError("Empty data provided")

    columns = set(df.columns)

    if EXPERIMENT_REQUIRED.issubset(columns):
        return 'experiment'
    elif VARIANT_REQUIRED.issubset(columns):
        return 'variant'
    elif MUTATION_REQUIRED.issubset(columns):
        return 'mutation'
    elif ACTIVITY_REQUIRED.issubset(columns):
        return 'activity'
    elif CONTROL_REQUIRED.issubset(columns):
        return 'control'
    else:
        raise ValueError(f"Cannot determine data type from columns: {columns}")


def process_experiment_data(df):
    """
    Validate and structure experiment records.

    Args:
        df: pandas DataFrame with experiment data

    Returns:
        List of validated experiment dictionaries ready for database
    """
    missing = EXPERIMENT_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Select only relevant columns, add missing optional columns as NaN
    for field in EXPERIMENT_FIELDS:
        if field not in df.columns:
            df[field] = None

    df = df[EXPERIMENT_FIELDS].replace({pd.NA: None, '': None})
    return df.where(pd.notnull(df), None).to_dict('records')


def process_variant_data(df):
    """
    Validate and structure variant records.

    Args:
        df: pandas DataFrame with variant data

    Returns:
        List of validated variant dictionaries ready for database
    """
    missing = VARIANT_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    for field in VARIANT_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Convert numeric fields
    numeric_int = ['generation', 'mutation_count']
    numeric_float = ['protein_yield', 'dna_yield', 'activity_score']

    for col in numeric_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    for col in numeric_float:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df[VARIANT_FIELDS].replace({pd.NA: None, '': None})
    return df.where(pd.notnull(df), None).to_dict('records')


def process_mutation_data(df):
    """
    Validate and structure mutation records.

    Args:
        df: pandas DataFrame with mutation data

    Returns:
        List of validated mutation dictionaries ready for database
    """
    missing = MUTATION_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    for field in MUTATION_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Convert numeric fields
    numeric_int = ['position', 'generation']
    for col in numeric_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    df = df[MUTATION_FIELDS].replace({pd.NA: None, '': None})
    return df.where(pd.notnull(df), None).to_dict('records')


def process_activity_data(df):
    """
    Validate and structure activity records.

    Args:
        df: pandas DataFrame with activity data

    Returns:
        List of validated activity dictionaries ready for database
    """
    missing = ACTIVITY_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    for field in ACTIVITY_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Convert numeric fields
    if 'predicted_activity_score' in df.columns:
        df['predicted_activity_score'] = pd.to_numeric(df['predicted_activity_score'], errors='coerce')

    df = df[ACTIVITY_FIELDS].replace({pd.NA: None, '': None})
    return df.where(pd.notnull(df), None).to_dict('records')


def process_control_data(df):
    """
    Validate and structure control records.

    Args:
        df: pandas DataFrame with control data

    Returns:
        List of validated control dictionaries ready for database
    """
    missing = CONTROL_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    for field in CONTROL_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Convert numeric fields
    numeric_float = ['protein_yield', 'dna_yield', 'activity_score']
    for col in numeric_float:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df[CONTROL_FIELDS].replace({pd.NA: None, '': None})
    return df.where(pd.notnull(df), None).to_dict('records')


def process_file(file):
    """
    Main entry point for file processing.

    Validates file extension, parses content, detects data type,
    and processes data for database insertion.

    Args:
        file: Flask FileStorage object from request.files

    Returns:
        Dictionary with:
            - 'data_type': string indicating the type of data
            - 'records': list of validated records ready for database

    Raises:
        ValueError: If file format is invalid, data type cannot be determined,
                   or required fields are missing
    """
    filename = secure_filename(file.filename)
    extension = validate_file_extension(filename)
    file_content = file.read()

    # Parse based on extension
    if extension == '.tsv':
        df = parse_tsv(file_content)
    elif extension == '.json':
        df = parse_json(file_content)

    # Detect data type
    data_type = detect_data_type(df)

    # Process based on data type
    processors = {
        'experiment': process_experiment_data,
        'variant': process_variant_data,
        'mutation': process_mutation_data,
        'activity': process_activity_data,
        'control': process_control_data
    }

    records = processors[data_type](df.copy())

    return {
        'data_type': data_type,
        'records': records
    }
