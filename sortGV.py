import pandas as pd
import os
import time

start_time = time.time()

def parse_csv_line(line):
    result = []
    current_field = []
    counter = 0  

    for char in line:
        if char == '"':
            counter = 1 - counter
        elif char == ',' and counter == 1:
            continue
        elif char == ',' and counter == 0:
            result.append(''.join(current_field).strip())
            current_field = [] 
        else:
            current_field.append(char)
    if current_field:
        result.append(''.join(current_field).strip())

    return result

def clean_csv(file_name):
    base, ext = os.path.splitext(file_name)
    edited_file_name = f"{base}_edited{ext}"
    with open(edited_file_name, 'w') as outFile:
        with open(file_name, 'r') as inFile:
            for line in inFile:
                parsed_line = parse_csv_line(line)
                outFile.write(','.join(parsed_line) + '\n') 

def sort_by_townland(filename):
    df = pd.read_csv(filename)
    df = df.sort_values(by='townland')
    df.to_csv('../files/sorted_by_townland.csv', index=False)

def sort_by_Names_Occupiers(filename):
    df = pd.read_csv(filename)

    # Remove leading and trailing spaces
    df['tenant_first'] = df['tenant_first'].str.strip()
    df['tenant_last'] = df['tenant_last'].str.strip()
    
    df["tenant_full"] = df['tenant_first'].astype(str) + ' ' + df['tenant_last'].astype(str)
    
    df = df.sort_values(by='tenant_full')
    df = df.drop(columns='tenant_full')
    
    df.to_csv('../files/sorted_by_occupiers.csv', index=False)


def sort_by_concatenation(filename, col1, col2):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(filename)
    
    # Create a new column that concatenates the two columns
    df['combined'] = df[col1].astype(str) + df[col2].astype(str)
    
    # Perform a case-insensitive sort on the combined column
    df = df.sort_values(by='combined', key=lambda col: col.str.lower())
    
    # Drop the temporary combined column
    df = df.drop(columns=['combined'])
    
    # Write the sorted DataFrame back to a CSV file
    df.to_csv('../files/sorted_by_combined.csv', index=False)

def list_of_townlands(df):
    townlands = df['townland'].unique()
    with open('../files/townlands_output.csv', 'w') as file:
        for townland in townlands:
            file.write(f"{townland}\n")


# Run time: 112 seconds
def divide_csv():
    big_df = pd.read_csv("../files/sorted_by_townland.csv")
    output_dir = "../files/townlands"
    output_dir1 = "../files/townlands_sorted"

    # Ensure output directories exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(output_dir1, exist_ok=True)

    row_idx = 0
    townland = big_df["townland"][row_idx]
    file_path = os.path.join(output_dir1, f"{townland}.csv")

    # Open the first file
    file = open(file_path, 'w')
    file.write(','.join(big_df.columns) + '\n')  # Write header

    while row_idx < len(big_df):
        current_townland = big_df["townland"][row_idx]
        
        if current_townland == townland:
            # Write the row into the file
            row = ','.join(big_df.iloc[row_idx].astype(str)) + '\n'
            file.write(row)
        else:
            # Close the previous file and open a new one for the new townland
            file.close()
            townland = current_townland
            file_path = os.path.join(output_dir1, f"{townland}.csv")
            file = open(file_path, 'w')
            file.write(','.join(big_df.columns) + '\n')  # Write header
            row = ','.join(big_df.iloc[row_idx].astype(str)) + '\n'
            file.write(row)
        
        row_idx += 1

    # Close the last file
    file.close()

# Run time: 92 seconds
def sort_and_overwrite_files(directory):
    output_dir = "../files/townlands_sorted/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    total_files = 0
    processed_files = 0

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and file_path.endswith('.csv'):
            total_files += 1
            try:
                df = pd.read_csv(file_path)
                if 'tenant_first' in df.columns and 'tenant_last' in df.columns:
                    df['sort_key'] = df['tenant_first'].fillna('') + df['tenant_last'].fillna('')
                    df = df.sort_values(by='sort_key')
                    df.drop('sort_key', axis=1, inplace=True)
                    df.to_csv(file_path, index=False)

                    # Move sorted files to the new directory
                    sorted_file_path = os.path.join(output_dir, filename)
                    os.rename(file_path, sorted_file_path)
                    processed_files += 1
                else:
                    print(f"Skipping {filename}: 'tenant_first' or 'tenant_last' column missing.")
            except FileNotFoundError:
                print(f"File not found: {file_path}")
            except Exception as e:
                print(f"An error occurred while processing {file_path}: {e}")

    print(f"Total files: {total_files}")
    print(f"Processed files: {processed_files}")


# clean_csv("../files/GV_full.csv")
# print("csv is cleaned")
# sort_by_townland("../files/GV_full_edited.csv")
# print("csv sorted by townland")

# big_df = pd.read_csv("../files/sorted_by_townland.csv")
# list_of_townlands(big_df)

# divide_csv()
# print("divided csv")

# sort_and_overwrite_files("../files/townlands_sorted/")
# print("overwritten the csv files")


sort_by_Names_Occupiers("../files/GV_full_edited.csv")

end_time = time.time()
total_runtime = end_time - start_time
print(f"The total runtime: {total_runtime} seconds.")
