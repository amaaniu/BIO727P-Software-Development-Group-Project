import sqlite3

connection = sqlite3.connect('experiment.db') #this should be the uploded database file
cursor = connection.cursor()

# Enable foreign key support (disabled by default in SQLite)
cursor.execute('PRAGMA foreign_keys = ON')

# Create User table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS User (
        user_id INTEGER PRIMARY KEY,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        last_login TIMESTAMP
    )
''')

# Create Experiment table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Experiment (
        experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        experiment_name TEXT NOT NULL,
        uniprot_id TEXT NOT NULL,
        wt_protein_sequence TEXT,
        protein_features TEXT,
        plasmid_sequence TEXT,
        created_at TIMESTAMP NOT NULL,
        status TEXT,
        FOREIGN KEY (user_id) REFERENCES User (user_id)
        FOREIGN KEY (uniprot_id) REFERENCES UniProt_Data (uniprot_id)
    )
''')

# Create Variant table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Variant (
        variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL,
        generation INTEGER NOT NULL,
        plasmid_variant_index TEXT NOT NULL,
        parent_variant_id INTEGER,
        dna_sequence TEXT NOT NULL,
        protein_sequence TEXT,
        protein_yield REAL NOT NULL,
        dna_yield REAL NOT NULL,
        activity_score REAL,
        mutation_count INTEGER,
        created_at TIMESTAMP NOT NULL,
        metadata TEXT,
        FOREIGN KEY (experiment_id) REFERENCES Experiment (experiment_id),
        FOREIGN KEY (parent_variant_id) REFERENCES Variant (variant_id)
    )
''')

# Create Mutations table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Mutations (
        mutation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id INTEGER NOT NULL,
        position INTEGER NOT NULL,
        wt_residue TEXT NOT NULL,
        mutant_residue TEXT NOT NULL,
        mutation_type TEXT NOT NULL,
        generation INTEGER NOT NULL,
        codon_change TEXT,
        FOREIGN KEY (variant_id) REFERENCES Variant (variant_id)
    )
''')

# Create Activity table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Activity (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id INTEGER NOT NULL,
        qc_pass INTEGER NOT NULL,
        measurement_type TEXT NOT NULL,
        raw_value REAL NOT NULL,
        FOREIGN KEY (variant_id) REFERENCES Variant (variant_id)
    )
''')

# Create Control_Data table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Control_Data (
        control_id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL,
        generation INTEGER NOT NULL,
        control_type TEXT NOT NULL,
        protein_yield REAL NOT NULL,
        dna_yield REAL NOT NULL,
        FOREIGN KEY (experiment_id) REFERENCES Experiment (experiment_id)
    )
''')
# Create UniProt_Data table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS UniProt_Data (
        uniprot_id TEXT PRIMARY KEY,
        protein_name TEXT,
        protein_length INTEGER NOT NULL,
        protein_sequence TEXT NOT NULL
    )
''')


# Create UniProt_Feature table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS UniProt_Feature (
        feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
        uniprot_id TEXT NOT NULL,
        feature_type TEXT NOT NULL,
        description TEXT,
        start_pos INTEGER,
        end_pos INTEGER,
        FOREIGN KEY (uniprot_id) REFERENCES UniProt_Data (uniprot_id)
    )
''')

connection.commit()
connection.close()