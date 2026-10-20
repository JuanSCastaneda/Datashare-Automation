import sqlite3
def createTable(database: str, volume_filename: str) -> None:
    import re
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Volumes (
        volume_name TEXT,
        number_files INT,
        volume_size INT,
        review_status TEXT,
        volume_directory TEXT
        survey_filename TEXT,
        impact_filename TEXT,
        survey_date TEXT,
        impact_date TEXT,
        survey_duration INT,
        impact_duration INT)
    """)
    with open(volume_filename, "r") as file:
        for line in file:
            split_line = re.split(r"\s", line)
            name = split_line[-2]
            print(f"[INFO] Adding {name} to Volumes Table in {database}...", end=" ")
            cursor.execute(" INSERT INTO Volumes (volume_name) VALUES (?)", (name,))
            print("Success")
    connection.commit()
    connection.close()

def DisplayTabulatedItems(lov, width, cols) -> str:
    outputString = []
    for i, item in enumerate(lov):
        # Print the item padded to column width, without newline
        outputString += [str(item).ljust(width)]
        # Newline every `cols` items
        if (i + 1) % cols == 0:
            outputString += ['\n']
    return "".join(outputString)

def formatDate(time):
    return f"{time.day}-{time.month}-{time.year} {time.hour}:{time.minute}:{time.second}"

def getVolumeAttributes(filename: str) -> tuple:
    with open(filename, "r", encoding="mbcs", errors='ignore') as file:
        line = file.readlines()[1]
 
    array = line.split(" ")
    Nfiles = array[3]
    size = array[6]
    directory = array[-1][:-1]
 
    return (Nfiles, size, directory)
 
#%%
#%%
def reviewVolume(database: str):
    import subprocess
    from datetime import datetime
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    volume_names = [i[0] for i in cursor.execute("SELECT volume_name FROM Volumes WHERE review_status IS NULL").fetchall()]
    N = len(volume_names)
    count = 1
    title = f"VOLUME REVIEW"
    print(f"{'='*150}\n{' '*int((150 - len(title)) / 2)}{title}\n{'='*150}\n")
    print(DisplayTabulatedItems(volume_names, 30, 4))
    
    for volume in volume_names:
       
        # PRINT HEADER
        title = f"VOLUME REVIEW OF {volume} ({count}/{N})"
        print(f"{'-'*150}\n{' '*int((150 - len(title)) / 2)}{title}\n{'-'*150}")
 
        # SET STATUS TO SURVEYING
        print(f"[INFO] Starting survey of volume {volume}...")
        cursor.execute(f"UPDATE Volumes SET review_status = 'SURVEYING IN PROGRESS' WHERE volume_name ='{volume}'")
 
        # DEFINING FILES
        survey_file_loc = rf"VolumeReview\SurveyReport\{volume}-Review_Volume-Survey.txt"
        impact_file_loc = rf"VolumeReview\ImpactReport\{volume}-Review_Volume-Impact.txt"
 
        # STARTING SURVEY SUBPROCESS
        starttime = datetime.now()
        survey_args = ["review_volumes", "-u=infodba", "-p=infodba", "-g=dba", f"-v={volume}", f"-rf={survey_file_loc}"]
        print(f"\n[INFO] Running...\n\n     {" ".join(survey_args)}")
        survey = subprocess.run(survey_args, shell=True, text=True, capture_output=True)
        print(survey.stdout)
        endtime = datetime.now()
        survey_duration = int((endtime -starttime).total_seconds() / 60)
        
        # IF SURVEY SUCCESSFULLY RAN
        if survey.returncode == 0:
            print("\n[INFO] The survey ran successfully")
           
            # GETTING/PRINTING VOLUME ATTRIBUTES
            print(f"\n[INFO] Collecting volume metrics from {survey_file_loc}...", end=" ")
            
            Nfiles, size, directory = getVolumeAttributes(survey_file_loc)
            print("Success")
            print(f"""\n[INFO] Information Relevant to {volume}:
                               Directory: {directory}
                               # of File: {Nfiles}
                               Volumetry: {size}  """)
           
            # UPDATE DATABASE WITH SUCESS RESULT
            print("\n[INFO] Updating SQLite Database...", end=" ")
            cursor.execute("""UPDATE Volumes SET number_files = ?, volume_size = ?, review_status = ?, volume_directory = ?,
                           survey_filename = ?, survey_duration = ?, survey_date = ? WHERE volume_name = ? """, \
                            (Nfiles, size, "IMPACT IN PROGRESS", directory, survey_file_loc, survey_duration, formatDate(starttime), volume))
            connection.commit()
            print("Success")
 
            # STARTING IMPACT SUBPROCESS
            print("\n[INFO] Now proceeding to review. This process will delete unreferenced files.")
            impact_args = ["review_volumes", "-u=infodba", "-p=infodba", "-g=dba", f"-v={volume}",
                           rf"-if={survey_file_loc}", rf"-of={impact_file_loc}"]
            print(f"\n[INFO] Running...\n\n     {" ".join(impact_args)}")        
            starttime = datetime.now()
            impact = subprocess.run(impact_args, shell=True, text=True, capture_output=True)
            print(impact.stdout)
            endtime = datetime.now()
            impact_duration = int((endtime -starttime).total_seconds() / 60)  
 
 
            if impact.returncode == 0:
                print("[INFO] Impact on volume executed successfully.")
                print("[INFO] Updating SQLite Database...", end=" ")
                cursor.execute(f"""UPDATE Volumes SET review_status = 'IMPACT SUCCESSFUL', impact_filename = '{impact_file_loc}',
                impact_date ='{formatDate(starttime)}', impact_duration={impact_duration} WHERE volume_name = '{volume}'""")
                print("Success")
 
            else:
                print(f"[WARN] Skipping {volume}. Surveying process failed with {impact.returncode} Please evaluate.")
                print("[INFO] Updating SQLite Database...", end=" ")
                cursor.execute(f"""UPDATE Volumes SET review_status = 'IMPACT FAILED', impact_filename = '{impact_file_loc}',
                impact_date ='{formatDate(starttime)}', impact_duration={impact_duration} WHERE volume_name = '{volume}'""")
                print("Success")
           
           
        # REPORT FAILED SURVEY
        else:
            print(f"\n[WARN] Skipping {volume}. Surveying process failed with {survey.returncode}. Please evaluate.")
            cursor.execute(f"""UPDATE Volumes SET review_status = 'SURVEY FAILED', survey_date ='{formatDate(starttime)}', survey_duration = '{survey_duration}' WHERE volume_name = '{volume}'""")
       
        connection.commit()
        count += 1
 
    connection.close()
    print("[INFO] Volume review is complete on all volumes.")
 
if __name__ == "__main__":
    reviewVolume("migration.db")