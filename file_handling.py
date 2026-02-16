import os
import pandas as pd
from io import BytesIO
from werkzeug.utils import secure_filename
from thefuzz import fuzz, process

ALLOWED_EXTENSIONS = {'.tsv', '.json'}

# Mapping: lowercase variation → canonical database field name.
# Columns are lowercased before lookup, so only lowercase keys are needed.
COLUMN_NAME_MAP = {
    # --- Variant fields ---
    # generation
    'directed_evolution_generation': 'generation',
    'evolution_generation': 'generation',
    'gen': 'generation',
    'round': 'generation',
    # plasmid_variant_index
    'plasmid_variant_index': 'plasmid_variant_index',
    'variant_index': 'plasmid_variant_index',
    'plasmid_index': 'plasmid_variant_index',
    'variant_id_index': 'plasmid_variant_index',
    # dna_sequence
    'assembled_dna_sequence': 'dna_sequence',
    'assembled_sequence': 'dna_sequence',
    'dna_seq': 'dna_sequence',
    'variant_dna_sequence': 'dna_sequence',
    # protein_yield
    'protein_quantification_pg': 'protein_yield',
    'protein_quantification': 'protein_yield',
    'protein_quantity': 'protein_yield',
    'protein_quant': 'protein_yield',
    'protein_concentration': 'protein_yield',
    'protein_amount': 'protein_yield',
    # dna_yield
    'dna_quantification_fg': 'dna_yield',
    'dna_quantification_f': 'dna_yield',
    'dna_quantification': 'dna_yield',
    'dna_quantity': 'dna_yield',
    'dna_quant': 'dna_yield',
    'dna_concentration': 'dna_yield',
    'dna_amount': 'dna_yield',
    # protein_sequence
    'translated_protein_sequence': 'protein_sequence',
    'protein_seq': 'protein_sequence',
    'variant_protein_sequence': 'protein_sequence',
    # activity_score
    'activity': 'activity_score',
    'score': 'activity_score',
    # mutation_count
    'number_of_mutations': 'mutation_count',
    'num_mutations': 'mutation_count',
    'total_mutations': 'mutation_count',
    # parent_variant_id  (not in VARIANT_REQUIRED but useful to capture)
    'parent_plasmid_variant': 'parent_variant_id',
    'parent_variant': 'parent_variant_id',
    'parent': 'parent_variant_id',

    # --- Experiment fields ---
    # experiment_name
    'experiment': 'experiment_name',
    'exp_name': 'experiment_name',
    'name': 'experiment_name',
    # uniprot_id
    'uniprot': 'uniprot_id',
    'uniprotid': 'uniprot_id',
    'uniprot_accession': 'uniprot_id',
    'accession': 'uniprot_id',
    'uniprot_entry': 'uniprot_id',
    # wt_protein_sequence
    'wild_type_protein_sequence': 'wt_protein_sequence',
    'wildtype_protein_sequence': 'wt_protein_sequence',
    'wt_sequence': 'wt_protein_sequence',
    'wt_seq': 'wt_protein_sequence',
    'wild_type_sequence': 'wt_protein_sequence',
    # protein_features
    'features': 'protein_features',
    # plasmid_sequence
    'wt_plasmid_sequence': 'plasmid_sequence',
    'plasmid_seq': 'plasmid_sequence',
    'plasmid_dna_sequence': 'plasmid_sequence',

    # --- Mutation fields ---
    # position
    'mutation_position': 'position',
    'residue_position': 'position',
    'residue_number': 'position',
    'pos': 'position',
    # wt_residue
    'wild_type_residue': 'wt_residue',
    'wildtype_residue': 'wt_residue',
    'original_residue': 'wt_residue',
    'wt_amino_acid': 'wt_residue',
    'from_residue': 'wt_residue',
    # mutant_residue
    'mut_residue': 'mutant_residue',
    'new_residue': 'mutant_residue',
    'substituted_residue': 'mutant_residue',
    'mutant_amino_acid': 'mutant_residue',
    'to_residue': 'mutant_residue',
    # mutation_type
    'type_of_mutation': 'mutation_type',
    'mut_type': 'mutation_type',
    # codon_change
    'codon_substitution': 'codon_change',
    'codon': 'codon_change',

    # --- Activity fields ---
    # measurement_type
    'assay_type': 'measurement_type',
    'measurement': 'measurement_type',
    'assay': 'measurement_type',
    # raw_value
    'value': 'raw_value',
    'measurement_value': 'raw_value',
    'raw_measurement': 'raw_value',
    'result': 'raw_value',
    # qc_pass
    'qc': 'qc_pass',
    'quality_control': 'qc_pass',
    'quality_control_pass': 'qc_pass',

    # --- Control fields ---
    # control_type
    'control': 'control_type',
    'control_name': 'control_type',
}


def normalize_columns(df, fuzzy_threshold=85):
    """
    Normalize DataFrame column names to canonical database field names.

    Steps:
        1. Strip whitespace and lowercase all column names
        2. Replace spaces with underscores
        3. Map known aliases to canonical names via COLUMN_NAME_MAP
        4. For unmatched columns, attempt fuzzy matching against known aliases

    Args:
        df: pandas DataFrame with raw column names
        fuzzy_threshold: minimum score (0-100) for a fuzzy match to be accepted

    Returns:
        DataFrame with normalized column names
    """
    # Lowercase, strip whitespace, replace spaces with underscores
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

    alias_keys = list(COLUMN_NAME_MAP.keys())
    new_columns = []

    for col in df.columns:
        # Exact match first
        if col in COLUMN_NAME_MAP:
            new_columns.append(COLUMN_NAME_MAP[col])
        else:
            # Fuzzy match fallback
            result = process.extractOne(col, alias_keys, scorer=fuzz.token_sort_ratio)
            if result and result[1] >= fuzzy_threshold:
                new_columns.append(COLUMN_NAME_MAP[result[0]])
            else:
                new_columns.append(col)

    df.columns = new_columns
    return df


# Required fields for each data type (fields that cannot be None)
EXPERIMENT_REQUIRED = {'experiment_name', 'uniprot_id'}
VARIANT_REQUIRED = {'generation', 'plasmid_variant_index', 'dna_sequence', 'protein_yield', 'dna_yield'}
MUTATION_REQUIRED = {'position', 'wt_residue', 'mutant_residue', 'mutation_type', 'generation'}
ACTIVITY_REQUIRED = {'measurement_type', 'raw_value'} 
CONTROL_REQUIRED = {'control_type', 'generation', 'protein_yield', 'dna_yield'}  

# All fields for each data type
EXPERIMENT_FIELDS = ['experiment_name', 'uniprot_id', 'wt_protein_sequence', 'protein_features', 'plasmid_sequence', 'status']
VARIANT_FIELDS = ['generation', 'plasmid_variant_index', 'dna_sequence', 'protein_sequence', 'protein_yield', 'dna_yield', 'activity_score', 'mutation_count']
MUTATION_FIELDS = ['position', 'wt_residue', 'mutant_residue', 'mutation_type', 'generation', 'codon_change']
ACTIVITY_FIELDS = ['measurement_type', 'raw_value', 'qc_pass']  
CONTROL_FIELDS = ['generation', 'control_type', 'protein_yield', 'dna_yield']  


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
    if not file_content or not file_content.strip():
        raise ValueError("File is empty. Please upload a TSV file with data.")
    try:
        df = pd.read_csv(BytesIO(file_content), sep='\t')
    except Exception as e:
        raise ValueError(f"Failed to parse TSV file: {e}. Ensure the file is a valid tab-separated format.")
    if df.empty:
        raise ValueError("TSV file contains headers but no data rows.")
    return df


def parse_json(file_content):
    """
    Parse JSON file content using pandas.

    Args:
        file_content: Raw bytes from file

    Returns:
        pandas DataFrame
    """
    if not file_content or not file_content.strip():
        raise ValueError("File is empty. Please upload a JSON file with data.")
    try:
        df = pd.read_json(BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Failed to parse JSON file: {e}. Ensure the file contains valid JSON.")
    if df.empty:
        raise ValueError("JSON file was parsed but contains no data records.")
    return df


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
        raise ValueError("The file contains no data rows.")

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
        raise ValueError(
            f"Cannot determine data type from columns: {columns}. "
            f"Your file must contain one of the following sets of required columns: "
            f"Experiment: {EXPERIMENT_REQUIRED}, "
            f"Variant: {VARIANT_REQUIRED}, "
            f"Mutation: {MUTATION_REQUIRED}, "
            f"Activity: {ACTIVITY_REQUIRED}, "
            f"Control: {CONTROL_REQUIRED}."
        )


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
        raise ValueError(f"Missing required experiment columns: {missing}. "
                         f"Required columns are: {EXPERIMENT_REQUIRED}")

    # Select only relevant columns, add missing optional columns as NaN
    for field in EXPERIMENT_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Check for null values in required fields
    for field in EXPERIMENT_REQUIRED:
        null_rows = df[df[field].isna() | (df[field].astype(str).str.strip() == '')]
        if not null_rows.empty:
            row_nums = [str(i + 2) for i in null_rows.index[:5]]
            raise ValueError(f"Required field '{field}' has empty values in row(s): {', '.join(row_nums)}.")

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
        raise ValueError(f"Missing required variant columns: {missing}. "
                         f"Required columns are: {VARIANT_REQUIRED}")

    for field in VARIANT_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Check for null values in required fields
    for field in VARIANT_REQUIRED:
        null_rows = df[df[field].isna() | (df[field].astype(str).str.strip() == '')]
        if not null_rows.empty:
            row_nums = [str(i + 2) for i in null_rows.index[:5]]
            raise ValueError(f"Required field '{field}' has empty values in row(s): {', '.join(row_nums)}.")

    # Convert numeric fields
    numeric_int = ['generation', 'mutation_count']
    numeric_float = ['protein_yield', 'dna_yield', 'activity_score']

    for col in numeric_int:
        if col in df.columns:
            original_non_null = df[col].dropna()
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            failed = original_non_null[pd.to_numeric(original_non_null, errors='coerce').isna()]
            if not failed.empty:
                bad_vals = failed.head(3).tolist()
                raise ValueError(f"Column '{col}' contains non-numeric values: {bad_vals}. Expected integer values.")

    for col in numeric_float:
        if col in df.columns:
            original_non_null = df[col].dropna()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            failed = original_non_null[pd.to_numeric(original_non_null, errors='coerce').isna()]
            if not failed.empty:
                bad_vals = failed.head(3).tolist()
                raise ValueError(f"Column '{col}' contains non-numeric values: {bad_vals}. Expected numeric values.")

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
        raise ValueError(f"Missing required mutation columns: {missing}. "
                         f"Required columns are: {MUTATION_REQUIRED}")

    for field in MUTATION_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Check for null values in required fields
    for field in MUTATION_REQUIRED:
        null_rows = df[df[field].isna() | (df[field].astype(str).str.strip() == '')]
        if not null_rows.empty:
            row_nums = [str(i + 2) for i in null_rows.index[:5]]
            raise ValueError(f"Required field '{field}' has empty values in row(s): {', '.join(row_nums)}.")

    # Convert numeric fields
    numeric_int = ['position', 'generation']
    for col in numeric_int:
        if col in df.columns:
            original_non_null = df[col].dropna()
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            failed = original_non_null[pd.to_numeric(original_non_null, errors='coerce').isna()]
            if not failed.empty:
                bad_vals = failed.head(3).tolist()
                raise ValueError(f"Column '{col}' contains non-numeric values: {bad_vals}. Expected integer values.")

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
        raise ValueError(f"Missing required activity columns: {missing}. "
                         f"Required columns are: {ACTIVITY_REQUIRED}")

    for field in ACTIVITY_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Check for null values in required fields
    for field in ACTIVITY_REQUIRED:
        null_rows = df[df[field].isna() | (df[field].astype(str).str.strip() == '')]
        if not null_rows.empty:
            row_nums = [str(i + 2) for i in null_rows.index[:5]]
            raise ValueError(f"Required field '{field}' has empty values in row(s): {', '.join(row_nums)}.")

    # Convert numeric fields
    if 'raw_value' in df.columns:
        original_non_null = df['raw_value'].dropna()
        df['raw_value'] = pd.to_numeric(df['raw_value'], errors='coerce')
        failed = original_non_null[pd.to_numeric(original_non_null, errors='coerce').isna()]
        if not failed.empty:
            bad_vals = failed.head(3).tolist()
            raise ValueError(f"Column 'raw_value' contains non-numeric values: {bad_vals}. Expected numeric values.")

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
        raise ValueError(f"Missing required control columns: {missing}. "
                         f"Required columns are: {CONTROL_REQUIRED}")

    for field in CONTROL_FIELDS:
        if field not in df.columns:
            df[field] = None

    # Check for null values in required fields
    for field in CONTROL_REQUIRED:
        null_rows = df[df[field].isna() | (df[field].astype(str).str.strip() == '')]
        if not null_rows.empty:
            row_nums = [str(i + 2) for i in null_rows.index[:5]]
            raise ValueError(f"Required field '{field}' has empty values in row(s): {', '.join(row_nums)}.")

    # Convert numeric fields
    numeric_int = ['generation']
    numeric_float = ['protein_yield', 'dna_yield']

    for col in numeric_int:
        if col in df.columns:
            original_non_null = df[col].dropna()
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            failed = original_non_null[pd.to_numeric(original_non_null, errors='coerce').isna()]
            if not failed.empty:
                bad_vals = failed.head(3).tolist()
                raise ValueError(f"Column '{col}' contains non-numeric values: {bad_vals}. Expected integer values.")

    for col in numeric_float:
        if col in df.columns:
            original_non_null = df[col].dropna()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            failed = original_non_null[pd.to_numeric(original_non_null, errors='coerce').isna()]
            if not failed.empty:
                bad_vals = failed.head(3).tolist()
                raise ValueError(f"Column '{col}' contains non-numeric values: {bad_vals}. Expected numeric values.")

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
    if not file or not file.filename:
        raise ValueError("No file provided. Please select a file to upload.")

    filename = secure_filename(file.filename)
    if not filename:
        raise ValueError("Invalid filename. The filename contains no valid characters.")

    extension = validate_file_extension(filename)

    try:
        file_content = file.read()
    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")

    if not file_content:
        raise ValueError("The uploaded file is empty.")

    # Parse based on extension
    if extension == '.tsv':
        df = parse_tsv(file_content)
    elif extension == '.json':
        df = parse_json(file_content)

    # Normalize column names to canonical database field names
    df = normalize_columns(df)

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
