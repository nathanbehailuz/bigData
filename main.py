import os.path
import pandas as pd
import re
import html
import time

from sortedcontainers import SortedDict
from autocorrect import Speller
from Griffiths import *

import googleSheets

start_time = time.time()

NUM_OF_FILES = 45410

def reorder(df,filename):
    if 'Total_valuation' in df.columns:
        df.rename(columns={'Total_valuation': 'Total_Valuation'}, inplace=True)
    new_order = ['original_filename', 'Reference_to_map', 'Names_occupiers', 'Name_immediate_lessors', 'Description', 'Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_Valuation']
    df = df[new_order]
    df.to_excel(filename, index=False)
    return df


def clean_names(text):
    text = str(text)
    text = html.unescape(text)
    
    # Remove common titles
    titles = ['Rev', 'Sir', 'Lord', 'jun', 'Reps', "Bt"]
    for title in titles:
        text = re.sub(r'\b' + title + r'\b', '', text, flags=re.IGNORECASE)
    
    # Check if the string has at least 2 characters to avoid IndexError
    if len(text) > 1 and text[1].isupper():
        last_upper_pos = -1
        for i in range(len(text) - 1):
            if text[i].isupper() and text[i + 1].isupper():
                last_upper_pos = i + 1
        
        if last_upper_pos != -1:
            text = text[:last_upper_pos + 1]
    
    pattern = '[^a-zA-Z. ]'
    
    cleaned_text = re.sub(pattern, '', text)

    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # Remove leading and trailing non-alpha characters
    while len(cleaned_text) > 0 and not cleaned_text[0].isalpha():
        cleaned_text = cleaned_text[1:]
        
    while len(cleaned_text) > 0 and not cleaned_text[-1].isalpha():
        cleaned_text = cleaned_text[:-1]
    
    return cleaned_text

def shorten_filename(df):
    for i in range(len(df["original_filename"])):
        file_name = df.at[i, "original_filename"]
        file_name = file_name[11:]
        df.at[i, "original_filename"] = file_name
    return df

def split_names(name):
    # Ensure there's a space after a period if directly followed by a letter
    name = re.sub(r'\.([A-Za-z])', r'. \1', name)
    
    # Split the name into first and last based on the last space found
    parts = name.rsplit(' ', 1)
    
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return name, ''
    
def uppercase_limit_idx(word):
    idx = 0
    for char in word:
        if char.isupper():
            idx +=1
        else:
            return idx
    return idx

def remove_continued(text):
    # Replace 'continued' with an empty string
    text = str(text)
    text = text.replace('continued', '')
    text = text.replace('con', '')
    return text

def occupiers(df):
    # Create a new column named "Townland"
    df['Townland'] = ''
    
    # Apply cleaning and splitting functions
    df['Names_occupiers'] = df['Names_occupiers'].apply(lambda x: clean_names(x))
    df['Names_occupiers'] = df['Names_occupiers'].apply(lambda x: remove_continued(x))
    df['Occupiers_First_Name'] = df['Names_occupiers'].apply(lambda x: split_names(x)[0])
    df['Occupiers_Last_Name'] = df['Names_occupiers'].apply(lambda x: split_names(x)[1])

    # create townlands_list (a sorted list of all townlands we have in GV.csv)
    townlands_list = TownlandList()
    townlands_list.add_entries("../files/townlands_output.csv")

    rows_to_drop = []

    townland = ""   
    for index, row in df.iterrows():
        
        if row['Names_occupiers'].isupper():
            townland = row['Names_occupiers']
            townland_match = townlands_list.find_townland(townland)
            if (townland_match != -1):
                df.at[ index, 'Townland'] = townland_match 
             
            df.at[ index, 'Townland'] = townland
            # rows_to_drop.append(index)
        else:
            print(f"case2: {townland}")
            df.at[ index, 'Townland'] = townland



    # Drop rows where 'Names_occupiers' is all uppercase
    df = df.drop(rows_to_drop)
    df.reset_index(drop=True, inplace=True)

    # Reorder columns
    new_order = ['original_filename', 'Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 'Description', 'Townland', 'Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_Valuation']
    df = df[new_order]
    df.to_excel("../files/output/fromOccupiers.xlsx",index=False)
    return df

def lessors(df):
    df['Name_immediate_lessors'] = df['Name_immediate_lessors'].apply(lambda x: clean_names(x))

    # replace 'same' with the value from the previous row in 'Name_immediate_lessors'
    filler = "" 
    for i in range(1, len(df)):
        if similarity_rate(df.loc[i, 'Name_immediate_lessors'].lower(), 'same') < 0.4 and df.loc[i, 'Name_immediate_lessors'] != "nan" :
            filler = df.loc[i, 'Name_immediate_lessors']
        if similarity_rate(df.loc[i, 'Name_immediate_lessors'].lower(), 'same') > 0.4:
            df.loc[i, 'Name_immediate_lessors'] = filler

    df['Lessors_first_name'] = df['Name_immediate_lessors'].apply(lambda x: split_names(x)[0])
    df['Lessors_last_name'] = df['Name_immediate_lessors'].apply(lambda x: split_names(x)[1])

    # col_idx = df.columns.get_loc('Name_immediate_lessors')
    # new_order = list(df.columns[:col_idx + 1]) + ['Lessors_first_name'] + ['Lessors_last_name'] + list(df.columns[col_idx + 1:-1])


    # Reorder the DataFrame columns
    new_order = ['original_filename','Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 
                 'Lessors_first_name', 'Lessors_last_name','Description','Townland','Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_Valuation']
    df = df.reindex(columns=new_order)
    df = df[new_order]

    return df

def ordnance(entry:str)->tuple:
    has_ordance = False
    for i in range(len(entry)-4):
        if entry[i:i+4] == "(Ord":
            entry = entry[:i]
            has_ordance = True
            break
    
    return entry, has_ordance

def have_ordance(entry:str)->bool:
    ret = False
    for i in range(len(entry)-4):
        if entry[i:i+4] == "(Ord":
            ret = True
            break
    
    return ret
        

def description(df):
    # Initialize spell checker
    spell = Speller()
    
    # Clean description, remove " and ", and use auto corrector
    df['Description'] = df['Description'].apply(lambda x: clean_names(x))
    df['Description'] = df['Description'].apply(lambda x: x.replace(' and ', ' '))
    df['Description'] = df['Description'].apply(lambda x: spell(x))
    
    # Put them to a set
    description_set = set(df['Description'])
    
    # Create a 2D array containing (element in set, initials)
    # intials is the first 2 characters of a word
    description_list = []
    for desc in description_set:
        initials = ''.join([word[:2].title() for word in desc.split()])
        description_list.append((desc, initials))
    
    # Sort the array alphabetically
    description_list.sort(key=lambda x: x[0])
    
    # Create a new column named description_shortened
    df['Description_shortened'] = df['Description'].map({item[0]: item[1] for item in description_list})

    original_col_idx = df.columns.get_loc("Description")
    new_columns = list(df.columns[:original_col_idx + 1]) + ["Description_shortened"] + list(df.columns[original_col_idx + 1:])
    df = df[new_columns]

    return df

def process_cell(cell):
        # Convert the cell to a string
        cell_str = str(cell)
        # Remove non-numeric characters except spaces
        cleaned_str = re.sub(r'[^0-9\s]', '', cell_str)
        # Remove extra spaces
        cleaned_str = ' '.join(cleaned_str.split())

        parts = [part for part in cleaned_str.split() if part.isdigit()]

        if len(parts) % 3 == 0:
            return ''
        else:
            return 'Flag'
        
def clean_nums(df):
    column_names = ['Area','Annual_valuation_land','AV_Buildings','Total_Valuation']

    for column_name in column_names:
        flag_column_name = column_name + '_flag'
        df[flag_column_name] = ''
    
        df[column_name] = df[column_name].apply(lambda cell: ' '.join(re.sub(r'[^0-9\s]', '', str(cell)).split()))
        df[flag_column_name] = df[column_name].apply(process_cell)

    new_order = ['original_filename','Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 
                'Lessors_first_name', 'Lessors_last_name','Description','Townland','Area','Area_flag', 'Annual_valuation_land',"Annual_valuation_land_flag",
                  'AV_Buildings',"AV_Buildings_flag", 'Total_Valuation','Total_Valuation_flag']
    df = df.reindex(columns=new_order)
    df = df[new_order]
    df.to_excel("../files/output/sample.xlsx",index=False)

    return df

def fuzzy_match(df):
    file_path = "../files/townlands_sorted"
    # Create new columns
    df["Ref_GV"] = ""
    df["Tenant_first"] = ""
    df["Tenant_last"] = ""
    df["Landlord_first"] = ""
    df["Landlord_last"] = ""

    try:
        row_idx = 0
        townland = df["Townland"][row_idx]
        output_file_path = '../files/output/occupiers.xlsx'
        df.to_excel(output_file_path, index=False)

        gv_list = GVList()
        gv_list.add_entries(file_path+"/"+townland+".csv")
        CTR = 0
        while row_idx < len(df):
            if df["Townland"][row_idx] == townland: 
                first_name = df["Occupiers_First_Name"][row_idx]
                last_name = df["Occupiers_Last_Name"][row_idx]
                if pd.notna(first_name) and pd.notna(last_name) and first_name.strip() != "" and last_name.strip() != "":
                    key = (str(first_name) +" "+ str(last_name)).upper()
                    result = gv_list.find_entry(key)
                    # print(f"key = {key} | result = {result}")
                    if result != -1:
                        df.at[row_idx, "Ref_GV"] = result.map_reference
                        df.at[row_idx, "Tenant_first"] = result.tenant_first
                        df.at[row_idx, "Tenant_last"] = result.tenant_last
                        df.at[row_idx, "Landlord_first"] = result.landlord_first
                        df.at[row_idx, "Landlord_last"] = result.landlord_last
            else:
                # print("another townland")     
                
                if os.path.exists(file_path +"/"+ df["Townland"][row_idx] +".csv"):
                    gv_list = GVList()
                    gv_list.add_entries(file_path +"/"+ df["Townland"][row_idx] +".csv")
                    townland = df["Townland"][row_idx]
                else:
                    CTR += 1
            row_idx += 1

        # Check for duplicate columns and handle them
        duplicate_columns = df.columns[df.columns.duplicated()]
        if not duplicate_columns.empty:
            df = df.loc[:, ~df.columns.duplicated()]

        # Ensure no duplicate column names before reindexing
        df = df.loc[:, ~df.columns.duplicated()]
        print(f"CTR {CTR}")
        # Reorder columns
        columns_order = ["original_filename", "Reference_to_map", "Ref_GV", "Names_occupiers", 
                         "Occupiers_First_Name", "Occupiers_Last_Name", "Tenant_first", "Tenant_last", 
                         "Name_immediate_lessors", "Lessors_first_name", "Lessors_last_name", "Landlord_first", 
                         "Landlord_last", "Description", "Description_shortened", "Townland", "Parish", "Area", 
                         "Area_flag", "Annual_valuation_land", "Annual_valuation_land_flag", "AV_Buildings", 
                         "AV_Buildings_flag", "Total_Valuation", "Total_Valuation_flag"]
        
        # Ensures only columns that exist in df are used
        columns_order = [col for col in columns_order if col in df.columns]
        df = df.reindex(columns=columns_order)

        return df

    except FileNotFoundError:
        print(f"File not found: {file_path}")

# binary search algorithm to ease file search (not used yet)
def find_file(filename, directory_list, left=0, right=NUM_OF_FILES):
    if right >= left:
        mid = (left + right)  // 2
        if directory_list[mid] == filename:  
            return mid
        elif directory_list[mid] > filename:
            return find_file(filename, directory_list,left, mid - 1)
        else:
            return find_file(filename, directory_list,mid + 1, right)
    return -1

def calculate_sum(nums_1, nums_2):
    '''1 pound (£) = 20 shillings (s).
    1 shilling (s) = 12 pence (d). '''    
    total_pounds = nums_1[0] + nums_2[0]
    total_shillings = nums_1[1] + nums_2[1]
    total_pence = nums_1[2] + nums_2[2]
    
    if total_pence >= 12:
        total_shillings += total_pence // 12
        total_pence %= 12
        
    if total_shillings >= 20:
        total_pounds += total_shillings // 20
        total_shillings %= 20
    
    return [total_pounds, total_shillings, total_pence]


# add_in_cell -> not a great name 
def add_in_cell(values_array):
    num_of_elts = len(values_array)
    if num_of_elts % 3 == 0 and num_of_elts >=3:
        cell_sum = [0,0,0]
        col_size = num_of_elts // 3
        for i in range(col_size):
            cell_sum = calculate_sum(cell_sum,[values_array[i*3],values_array[i*3+1],values_array[i*3+2]])
        return cell_sum
    
# checks vertical sum 
def vertical_check_sum(df):
    area_sum = land_sum = building_sum = total_sum = [0, 0, 0]
    indices_to_drop = []

    for i in range(len(df) - 1):
        description = df.at[i, "Description"]

        if description[:5] != 'Total':
            # row contains "PARISH OF ...."
            if str(df.at[i, 'Name_immediate_lessors'])[:6] == "PARISH":
                indices_to_drop.append(i)
                continue
            
            # extract the numbers from the cell then sum them up to a be a 3 value cell
            area_values = add_in_cell(extract_values(df.at[i, "Area"]))
            land_values = add_in_cell(extract_values(df.at[i, "Annual_valuation_land"]))
            building_values = add_in_cell(extract_values(df.at[i, "AV_Buildings"]))
            total_values = add_in_cell(extract_values(df.at[i, "Total_Valuation"]))

            if type(area_values) == list and len(area_values) >= 3:
                area_sum = calculate_sum(area_sum, area_values)
            if type(land_values) == list and len(land_values) >= 3:
                land_sum = calculate_sum(land_sum, land_values)
            if type(building_values) == list and len(building_values) >= 3:
                building_sum = calculate_sum(building_sum, building_values)
            if type(total_values) == list and len(total_values) >= 3:
                total_sum = calculate_sum(total_sum, total_values)
        else:
            area_flag = "correct" if area_sum == extract_values(df.at[i, "Area"]) else "flag"
            land_flag = "correct" if land_sum == extract_values(df.at[i, "Annual_valuation_land"]) else "flag"
            building_flag = "correct" if building_sum == extract_values(df.at[i, "AV_Buildings"]) else "flag"
            total_flag = "correct" if total_sum == extract_values(df.at[i, "Total_Valuation"]) else "flag"

            # print(f"Area_total = {df.at[i, 'Area']} | our_sum = {area_sum}")
            df.at[i, "Area_flag"] = area_flag
            df.at[i, "Annual_valuation_land_flag"] = land_flag
            df.at[i, "AV_Buildings_flag"] = building_flag
            df.at[i, "Total_Valuation_flag"] = total_flag

            # Check if the next row is part of the same "total" group
            if df.at[i, "Townland"] != df.at[i + 1, "Townland"]:
                # Reset the sums for the next group(rows with the same townland name)
                area_sum = land_sum = building_sum = total_sum = [0, 0, 0]

    # Drop all the identified indices at once
    df = df.drop(index=indices_to_drop)

    # Reset the index if needed
    df.reset_index(drop=True, inplace=True)

    return df


def extract_values(cell):
    cell_str = str(cell)
    # Split the cleaned string into parts
    parts = [int(part) for part in cell_str.split() if part.isdigit()]
    # Check if the number of parts is a multiple of 3
    if len(parts) % 3 == 0:
        return parts
    else:
        return []
    
def split_rows(df: pd.DataFrame) -> pd.DataFrame:
    # Helper function to split a column value into chunks of size 3
    def split_into_chunks(value, chunk_size=3):
        if isinstance(value, str):
            return [value[i:i+chunk_size] for i in range(0, len(value), chunk_size)]
        return [value]
    
    # Create an empty DataFrame to store the new rows
    new_df = pd.DataFrame(columns=df.columns)

    for i in range(len(df)):
        # Get the current row
        row = df.iloc[i]
        
        # Split the columns into chunks of size 3
        area_chunks = split_into_chunks(row['Area'])
        annual_valuation_land_chunks = split_into_chunks(row['Annual_valuation_land'])
        av_buildings_chunks = split_into_chunks(row['AV_Buildings'])
        total_valuation_chunks = split_into_chunks(row['Total_Valuation'])
        
        # Find the maximum number of chunks
        maxEntry = max(len(area_chunks), len(annual_valuation_land_chunks), len(av_buildings_chunks), len(total_valuation_chunks))
        
        # Create new rows based on the maximum number of chunks
        for j in range(maxEntry):
            new_row = row.copy()
            
            # Assign chunks to the new row, or empty string if no more chunks
            new_row['Area'] = area_chunks[j] if j < len(area_chunks) else ''
            new_row['Annual_valuation_land'] = annual_valuation_land_chunks[j] if j < len(annual_valuation_land_chunks) else ''
            new_row['AV_Buildings'] = av_buildings_chunks[j] if j < len(av_buildings_chunks) else ''
            new_row['Total_Valuation'] = total_valuation_chunks[j] if j < len(total_valuation_chunks) else ''
            
            # Append the new row to the new DataFrame
            new_df = new_df.append(new_row, ignore_index=True)
    
    return new_df
    
def counter(df:pd.DataFrame) -> pd.DataFrame:
    per_page_ctr, total_ctr = 1, 0
    page_no = ''
    df['per_page_counter'] = ''
    df['total_counter'] = ''

    for i in range(len(df['original_filename'])):
        if df.at[i,'original_filename'] != page_no:
            page_no = df.at[i,'original_filename']
            per_page_ctr = 1
        else:
            per_page_ctr += 1
        df.at[i,'per_page_counter'] = per_page_ctr
        total_ctr += 1
        df.at[i, 'total_counter'] = total_ctr

    new_order = ['per_page_counter','total_counter','original_filename','Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 
                'Lessors_first_name', 'Lessors_last_name','Description','Townland','Area','Area_flag', 'Annual_valuation_land',"Annual_valuation_land_flag",
                  'AV_Buildings',"AV_Buildings_flag", 'Total_Valuation','Total_Valuation_flag']
    df = df.reindex(columns=new_order)
    df = df[new_order]

    df.to_excel('../files/output/1.xlsx')

    return df


            


def process_excel(filename):
    outputPath = '../files/output'
    df = pd.read_excel(filename)
    df = reorder(df,filename)


    df = occupiers(df)
    df = lessors(df)
    # df = shorten_filename(df)

    df = clean_nums(df)
    
    df = description(df)
    df = fuzzy_match(df)

    df = vertical_check_sum(df)



    df = counter(df)


    df.to_excel(outputPath+filename[14:], index = False)

#----------------------------------------------------#

process_excel("../files/input/allFiles.xlsx")




#----------------------------------------------------#
end_time = time.time()
total_runtime = end_time - start_time
print(f"The total runtime: {total_runtime} seconds.")

#----------------------------------------------------#
