# BIO727P-Software-Development-Group-Project
1. The Directed Evolution Monitoring & Analytics Portal
A Flask-based web application for staging directed evolution experimental data, running analyses, and visualising results on in one place.
2. Project Overview
The purpose of the portal is to transform raw experimental outputs into interpretable biological information. Specifically, the platform enables researchers to:
track genetic variants generated during directed evolution experiments
analyse sequence changes and identify mutations relative to the wild-type enzyme
quantify enzyme performance using a unified activity metric
visualise evolutionary trends across experimental generations
By integrating data storage, sequence analysis and visualisation within a single web application, the platform supports researchers in understanding and analysing Directed Evolution experiments and seeing if polymerase performance is improved successfully.
3. Key Features
User registration and authentication
Experiment staging and data upload
Automated analysis pipeline
Visualisation of analysis results
Results can be downloaded and shared (.pdf or .png)
Experiment tracking
4. Installation and running the application
Clone the Repository
git clone <repo-url>
cd project-name
Create the Environment
conda env create -f environment.yml
conda activate myenv
Run the application in Terminal and visit the website
python run.py
http://127.0.0.1:5000
5. Workflow Guide
Register an account
Log in to access the dashboard
Stage an experiment and provide a UniProt accession ID, plasmid FASTA and experimental run data files (TSV or JSON) containing assay outputs and variant identifiers.
Run the analysis pipeline to produce Activity Scores, a ranked variants table, generation/round-level summary statistics, and mutation tracking.
View the results and export them as a `.pdf` or `.png`. Users can highlight top performing variants, compare activity across rounds, and export visuals for reporting.
Track experiments in the dashboard, where all analyses are saved.
6. Technology Stack
Backend: Python, Flask, Flask-Login, Flask-SQLAlchemy
Frontend: HTML,CSS, JavaScript & Bootstrap
Database: SQLite / SQLAlchemy ORM
Data Analysis and Visualisation: Pandas, Matplotlib, Plotly, BioPython, Kaleido
Other Tools: Git version control, Conda environment management
7. Contributors (github names)
Emmanuel Rabiu (madebyemmanuel-r)
Amaani Uvais (amaaniu)
Shams Al-Ameri (shamsAl-ameri)
Hamsy Aravinthan (hamsy-aravin)
Summer Lee (summerllee33)