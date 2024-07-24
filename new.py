import os
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

def split_names(name):
    # Ensure there's a space after a period if directly followed by a letter
    name = re.sub(r'\.([A-Za-z])', r'. \1', name)
    
    # Split the name into first and last based on the last space found
    parts = name.rsplit(' ', 1)
    
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return name, ''
    
def occupiers(df):
    # create a new column of name "Townland"
    df['Townland'] = ''
    # if a cell in Names_occupiers is all cap, save it to a variable and fill the area column with that value until you reach another all cap variable
    df['Names_occupiers'] = df['Names_occupiers'].apply(lambda x: clean_names(x))
    df['Occupiers_First_Name'] = df['Names_occupiers'].apply(lambda x: split_names(x)[0])
    df['Occupiers_Last_Name'] = df['Names_occupiers'].apply(lambda x: split_names(x)[1])

    current_area = ''
    rows_to_drop = []
    for index, row in df.iterrows():
        if row['Names_occupiers'].isupper():
            current_area = row['Names_occupiers']
            rows_to_drop.append(index)            
        else:
            df.at[index, 'Townland'] = current_area
 
    # Drop rows where 'Names_occupiers' is all uppercase
    df = df.drop(rows_to_drop)
    df.reset_index(drop=True, inplace=True)

    new_order = ['original_filename', 'Reference_to_map', 'Names_occupiers','Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 'Description','Townland', 'Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_valuation']
    df = df[new_order]
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

    # Reorder the DataFrame columns
    new_order = ['nanonets_orginal_filename','Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 
                 'Lessors_first_name', 'Lessors_last_name','Description','Townland','Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_Valuation']
    df = df.reindex(columns=new_order)
    df = df[new_order]

    return df

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
    description_list = []
    for desc in description_set:
        initials = ''.join([word[0].upper() for word in desc.split()])
        description_list.append((desc, initials))
    
    #Sort the array alphabetically
    description_list.sort(key=lambda x: x[0])
    
    # Create a new column named description_shortened
    df['Description_shortened'] = ''
    
    # Convert the list to a dictionary for faster lookup
    description_dict = {item[0]: item[1] for item in description_list}
    
    # Find and replace descriptions with their initials
    df['Description_shortened'] = df['Description'].apply(lambda x: description_dict[x])

    new_order = ['nanonets_orginal_filename','Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name', 'Name_immediate_lessors', 
                 'Lessors_first_name', 'Lessors_last_name','Description',"Description_shortened",'Townland','Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_Valuation']
    df = df.reindex(columns=new_order)
    df = df[new_order]
    
    return df

def clean_nums(df, column_name):
    flag_column_name = column_name + '_flag'
    df[flag_column_name] = ''

    def process_cell(cell):
        cell_str = str(cell)

        parts = [part for part in cell_str.split() if part.isdigit()]

        if len(parts) == 0 or len(parts) == 3 or len(parts) == 6:
            return ''
        else:
            return 'Flag'

    df[flag_column_name] = df[column_name].apply(process_cell)
    original_col_idx = df.columns.get_loc(column_name)
    new_columns = list(df.columns[:original_col_idx + 1]) + [flag_column_name] + list(df.columns[original_col_idx + 1:-1])
    df = df[new_columns]

    return df

def process_entries(df,filename):
    df['Ref_GV'] = None
    df['Parish'] = None

    for index, row in df.iterrows():
        key = f"{row['Occupiers_First_Name']} {row['Occupiers_Last_Name']} {row['Townland']}".lower()
        key = key.replace(" ","")
        
        my_gv_list = GVList()
        my_gv_list.add_entries(filename)
        ret_val = my_gv_list.find_entry(key)
        
        if ret_val != -1 and ret_val != None:
            df.at[index, 'Ref_GV'] = ret_val.get_map_ref()
            df.at[index, 'Parish'] = ret_val.get_parish()
    
    original_col_idx = df.columns.get_loc("Reference_to_map")
    original_col_idx2 = df.columns.get_loc("Townland")
    new_order = list(df.columns[:original_col_idx + 1]) + ['Ref_GV'] + list(df.columns[original_col_idx + 1: original_col_idx2+1]) + ['Parish'] + list(df.columns[original_col_idx2 + 1:-1])
    df = df[new_order]

    return df

def fuzzy_match(df):
    file_path = "./files/townlands_sorted"
    
    #Create new columns
    df["Tenant_first"] = ""
    df["Tenant_last"] = ""
    df["Landlord_first"] = ""
    df["Landlord_last"] = ""

    try:
        row_idx = 0
        townland = SortedDict()
        with open(file_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                key, value = line.strip().split(',')
                townland[key] = value

        for row in df.iterrows():
            occupier_first = row[1]['Occupiers_First_Name']
            occupier_last = row[1]['Occupiers_Last_Name']
            lessor_first = row[1]['Lessors_first_name']
            lessor_last = row[1]['Lessors_last_name']
            curr_townland = row[1]['Townland']

            if curr_townland in townland.keys():
                parish = townland[curr_townland]
                df.at[row_idx, 'Tenant_first'] = f"{occupier_first}"
                df.at[row_idx, 'Tenant_last'] = f"{occupier_last}"
                df.at[row_idx, 'Landlord_first'] = f"{lessor_first}"
                df.at[row_idx, 'Landlord_last'] = f"{lessor_last}"
            row_idx += 1
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    df.reset_index(drop=True, inplace=True)

    new_order = ['nanonets_orginal_filename', 'Reference_to_map', 'Names_occupiers', 'Occupiers_First_Name', 'Occupiers_Last_Name',
                 'Name_immediate_lessors', 'Lessors_first_name', 'Lessors_last_name', 'Description', 'Description_shortened',
                 'Townland', 'Area', 'Annual_valuation_land', 'AV_Buildings', 'Total_Valuation', 'Tenant_first', 'Tenant_last', 'Landlord_first', 'Landlord_last']
    df = df[new_order]

    return df



def process_excel(filename):
    outputPath = "./files/output"
    df = pd.read_excel(filename)
    df = occupiers(df)

    df = lessors(df)

    

    df = clean_nums(df, 'Area')
    df = clean_nums(df, 'Annual_valuation_land')
    df = clean_nums(df, "AV_Buildings")
    df = clean_nums(df, 'Total_Valuation')
    df = process_entries(df,filename)
    df = description(df)

    df = fuzzy_match(df)

    df.to_excel(outputPath+filename[13:], index = False)

#----------------------------------------------------#

process_excel("./files/trial/05_13-18.xlsx")
