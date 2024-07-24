'''
    Searching algorithm to find if a specific filename is in folder.
    Filenames are in a list
    Filenames in the folder are alphabetically sorted -> use binarysearch
'''

import os
import pandas as pd
from Griffiths import *
import math

NUM_OF_FILES = 45410

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

def first_occurence(directory_list):
    directory_list.sort()
    char = ""
    ctr = 0
    occurence_list = []
    for directory in directory_list:
        if directory[0] != char:
            char = directory[0]
            occurence_list.append([char,ctr])
        ctr += 1
    return occurence_list


'''What is the length of the shortest townland and its name?'''
"Ans: length = 3 | Name = ALT"
def shortest_townland(townlands_file):
    with open (townlands_file, 'r') as inFile:
        townland_length = 10
        townland_name = ""
        for line in inFile:
            if len(line) < townland_length:
                townland_length = len(line)
                townland_name = line
        
        # to exclude the \n character 
        townland_length -= 1
        print(townland_name, townland_length)

'''Saves the townlands in all.xlsx in a csv file in files/output'''
def list_of_townlands(df):
    townlands = pd.DataFrame()
    townlands["list"] = ""
    townlands["image_id"] = ""
    idx = 0
    townland = ""
    for index, row in df.iterrows():
        entry = df.at[index, "Townland"]
        if entry != townland: 
            townlands.at[idx,"list"] = entry
            townlands.at[idx,"image_id"] = df.at[index, "original_filename"]
            townland = entry
            idx+=1
    
    townlands.to_csv("../files/output/townlands_in_all.csv")



''' returns a file containing file_no, name_occupier and column where "Flag" is detected'''
def entries_having_Flag(df):
    log = pd.DataFrame(columns=["File_no", "Names_occupier", "Flag_Location"])
    idx = 0

    for index in range(len(df)):
        flag_location = ""

        if df.at[index, "Area_flag"] == "Flag":
            flag_location += "Area"

        if df.at[index, "Annual_valuation_land_flag"] == "Flag":
            if flag_location:
                flag_location += ", "
            flag_location += "Land"
        
        if df.at[index, "AV_Buildings_flag"] == "Flag":
            if flag_location:
                flag_location += ", "
            flag_location += "Buildings"
        
        if df.at[index, "Total_Valuation_flag"] == "Flag":
            if flag_location:
                flag_location += ", "
            flag_location += "Total"

        if flag_location:  # Only add to log if there is any flag
            log.at[idx, "File_no"] = df.at[index, "original_filename"]
            log.at[idx, "Names_occupier"] = df.at[index, "Names_occupiers"]
            log.at[idx, "Flag_Location"] = flag_location
            idx += 1

    log.to_csv("../files/output/error1log.csv", index=False)

def check_townland(file_name: str, df: pd.DataFrame, image_name: str):
    
    with open('../files/log/townlandslog.csv', 'w') as inFile:
        gv_hash = GVHash(file_name)
        
        for i in range(len(df)):
            if df.at[i, 'original_filename'] == image_name:
                name = str(df.at[i,'Names_occupiers']).upper()
                # binary search the key
                results = gv_hash.find_entry(name)  
                if results != -1:
                    for val in results:
                        content_str = ', '.join(val.get_content())  
                        inFile.write(name + " | " + content_str + "\n")
                else:
                    inFile.write(name + " | Not Found \n")


def list_of_description(df:pd.DataFrame):
    description_set = set()
    for i in range(len(df['Description'])):
        description_set.add(df.at[i,'Description'])
    description_df = pd.DataFrame(list(description_set), columns=["Descriptions"])
    description_df.to_csv('../files/log/list_of_descriptions.csv')
        
def split_rows(df: pd.DataFrame) -> pd.DataFrame:
    # split a column value into numeric chunks based on spaces or newline characters
    def split_into_chunks(value):
        if isinstance(value, str):
            return value.split()  
        elif pd.isna(value):
            return [] 
        return [str(value)]
    
    # create a file to log rows where maxEntry // 3 != 0:
    error_log = pd.DataFrame(columns=df.columns)    

    # Create an empty DataFrame to store the new rows
    new_df = pd.DataFrame(columns=df.columns)

    for i in range(len(df)):
        # Get the current row
        row = df.iloc[i]

        # Split the columns into chunks
        area_chunks = split_into_chunks(row['Area'])
        annual_valuation_land_chunks = split_into_chunks(row['Annual_valuation_land'])
        av_buildings_chunks = split_into_chunks(row['AV_Buildings'])
        total_valuation_chunks = split_into_chunks(row['Total_Valuation'])

        # Find the maximum number of chunks
        maxEntry = max(len(area_chunks), len(annual_valuation_land_chunks), len(av_buildings_chunks), len(total_valuation_chunks))
        if maxEntry // 3 != 0:
            error_log = pd.concat([error_log, pd.DataFrame([row])], ignore_index=True)
            

        maxEntry = math.floor(maxEntry / 3)

        # Create new rows based on the maximum number of chunks
        for j in range(maxEntry):
            new_row = row.copy()
            
            # Assign chunks to the new row, join them into strings
            new_row['Area'] = ' '.join(area_chunks[3 * j: 3 * j + 3]) if j < len(area_chunks) else ''
            new_row['Annual_valuation_land'] = ' '.join(annual_valuation_land_chunks[3 * j: 3 * j + 3]) if j < len(annual_valuation_land_chunks) else ''
            new_row['AV_Buildings'] = ' '.join(av_buildings_chunks[3 * j: 3 * j + 3]) if j < len(av_buildings_chunks) else ''
            new_row['Total_Valuation'] = ' '.join(total_valuation_chunks[3 * j: 3 * j + 3]) if j < len(total_valuation_chunks) else ''
            
            # Append the new row to the new DataFrame
            new_df = pd.concat([new_df, pd.DataFrame([new_row])], ignore_index=True)

    # Save the error log to CSV
    error_log.to_csv("../files/log/number_of_entires.csv", index=False)

    return new_df


df = pd.read_excel('../files/output/05_13-18.xlsx')
df = split_rows(df)

df.to_excel('../files/output/1.xlsx')

